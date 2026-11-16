from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / ".agents/skills/stm32-workbench/scripts"
sys.path.insert(0, str(SCRIPTS))
from stm32kit import project
from stm32kit.cli import main


def fixture(root: Path, folder="App", name="App", mcu="STM32F407VGTx", device_define="STM32F407xx") -> Path:
    directory = root / folder
    directory.mkdir(parents=True)
    (directory / ".project").write_text(
        f"<projectDescription><name>{name}</name><projects/><linkedResources/>"
        "</projectDescription>", encoding="utf-8")
    (directory / ".cproject").write_text('''<cproject><storageModule><cconfiguration>
    <storageModule><configuration name="Debug" artifactName="${ProjName}" artifactExtension="elf">
      <folderInfo><toolChain>
        <option superClass="st.target_mcu" value="STM32F407VGTx"/>
        <builder buildPath="${workspace_loc:/App}/Debug"/>
        <tool><option superClass="st.compiler.option.definedsymbols">
          <listOptionValue value="USE_HAL_DRIVER"/><listOptionValue value="STM32F407xx"/>
        </option><option superClass="st.linker.option.script" value="${workspace_loc:/${ProjName}/app.ld}"/></tool>
      </toolChain></folderInfo>
    </configuration></storageModule></cconfiguration></storageModule></cproject>'''.replace("STM32F407VGTx", mcu).replace("STM32F407xx", device_define), encoding="utf-8")
    (directory / "board.ioc").write_text(
        f"Mcu.Name={mcu}\nProjectManager.ProjectName={name}\n"
        "PA1.Signal=GPIO_Output\nPA1.PinState=GPIO_PIN_RESET\nUART4.BaudRate=115200\n", encoding="utf-8")
    (directory / "app.ld").write_text('''/* FLASH (rx) : ORIGIN = 0, LENGTH = 999K */
MEMORY
{
 RAM (xrw) : ORIGIN = 0x20000000, LENGTH = 128K
 FLASH (rx) : ORIGIN = 0x08000000, LENGTH = 1024K
}
''', encoding="utf-8")
    return directory


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def test_inventory_duplicates_stubs_archives_and_exclusions(self):
        fixture(self.root, "current", "SameName")
        fixture(self.root, "99. history/copy", "SameName")
        fixture(self.root, "Drivers/hidden", "Hidden")
        stub = self.root / "old"
        stub.mkdir()
        (stub / ".project").write_text("<projectDescription><name>Old</name></projectDescription>")
        result = project.inventory(self.root)
        self.assertEqual(result["project_count"], 3)
        self.assertEqual(result["duplicate_names"]["SameName"], ["99. history/copy", "current"])
        self.assertEqual(result["skipped_directories"], {"drivers": 1})
        self.assertFalse(next(p for p in result["projects"] if p["name"] == "Old")["has_cproject"])

    def test_invalid_xml_is_reported_without_hiding_good_projects(self):
        fixture(self.root)
        bad = self.root / "bad"
        bad.mkdir()
        (bad / ".project").write_text("<broken")
        result = project.inventory(self.root)
        self.assertEqual(result["project_count"], 1)
        self.assertEqual(len(result["errors"]), 1)

    def test_inspect_preserves_source_and_selects_config_metadata(self):
        directory = fixture(self.root, "renamed", "RealApp")
        core = directory / "Core/Src"
        core.mkdir(parents=True)
        (core / "usart.c").write_text("huart4.Init.BaudRate = 115200;\n")
        before = {str(p): p.read_bytes() for p in directory.rglob("*") if p.is_file()}
        result = project.inspect_project(directory)
        self.assertEqual(result["name"], "RealApp")
        self.assertTrue(result["warnings"])
        self.assertEqual(result["configurations"][0]["mcu"], ["STM32F407VGTx"])
        self.assertIn("STM32F407xx", result["configurations"][0]["defines"])
        flash = result["linker_files"][0]["regions"][1]
        self.assertEqual((flash["origin"], flash["length"]), (0x08000000, 1024 * 1024))
        self.assertEqual(result["source_observations"][0]["matches"][0]["line"], 1)
        self.assertEqual(before, {str(p): p.read_bytes() for p in directory.rglob("*") if p.is_file()})

    def test_unknown_linker_expression_is_not_guessed(self):
        path = self.root / "expr.ld"
        path.write_text("MEMORY { FLASH(rx): ORIGIN = APP_BASE, LENGTH = (TOTAL - BOOT) }")
        region = project.memory_regions(path)[0]
        self.assertIsNone(region["origin"])
        self.assertIsNone(region["length"])
        self.assertEqual(region["length_expression"], "(TOTAL - BOOT)")

    def test_different_mcu_families_are_read_from_metadata(self):
        for mcu, define in (("STM32G071RBTx", "STM32G071xx"), ("STM32L476RGTx", "STM32L476xx"),
                            ("STM32H743ZITx", "STM32H743xx"), ("STM32U575ZITx", "STM32U575xx")):
            with self.subTest(mcu=mcu):
                directory = fixture(self.root, mcu, "App", mcu, define)
                result = project.inspect_project(directory)
                self.assertEqual(result["configurations"][0]["mcu"], [mcu])
                self.assertEqual(result["ioc"][0]["mcu"], mcu)
                self.assertIn(define, result["configurations"][0]["defines"])

    def test_ioc_diff_includes_removed_pins_polarity_and_optional_peripheral_settings(self):
        before, after = self.root / "a.ioc", self.root / "b.ioc"
        before.write_text("PA0.Signal=UART4_TX\nPA1.PinState=GPIO_PIN_SET\nUART4.BaudRate=9600\n")
        after.write_text("PA1.PinState=GPIO_PIN_RESET\nUART4.BaudRate=115200\n")
        result = project.ioc_diff(before, after)
        self.assertEqual(result["changed"], 2)
        self.assertIsNone(result["changes"][0]["after"])
        self.assertEqual(project.ioc_diff(before, after, True)["changed"], 3)

    def test_build_plan_uses_eclipse_name_and_quotes_without_execution(self):
        directory = fixture(self.root, "보드 (복사본)", "App.v2")
        ide = self.root / "IDE 'tools'"
        ide.mkdir()
        (ide / "stm32cubeidec.exe").write_text("not executable")
        workspace = self.root / "scratch"
        result = project.build_plan(directory, ide, workspace, "Debug")
        self.assertFalse(result["executed"])
        self.assertFalse(workspace.exists())
        self.assertEqual(result["argv"][-1], r"App\.v2/Debug")
        self.assertIn("IDE ''tools''", result["powershell"])
        self.assertEqual(result["argv"][result["argv"].index("-import") + 1], str(directory))

    def test_build_plan_rejects_wrong_config_and_existing_workspace(self):
        directory = fixture(self.root)
        ide = self.root / "IDE"
        ide.mkdir()
        (ide / "stm32cubeidec.exe").touch()
        for workspace, config in [(self.root / "new", "Typo"), (self.root, "Debug"),
                                  (directory / "inside", "Debug")]:
            with self.assertRaises(ValueError):
                project.build_plan(directory, ide, workspace, config)
        used = self.root / "used"
        used.mkdir()
        (used / "keep.txt").write_text("keep")
        with self.assertRaises(ValueError):
            project.build_plan(directory, ide, used, "Debug")
        self.assertEqual((used / "keep.txt").read_text(), "keep")

    def test_doctor_returns_all_candidates_without_running_them(self):
        for version in ("12.3", "14.3"):
            path = self.root / version
            path.mkdir()
            (path / "arm-none-eabi-gcc.exe").write_text("not executable")
        with patch("shutil.which", return_value=None):
            result = project.doctor(self.root)
        self.assertEqual(len(result["tools"]["arm-none-eabi-gcc"]), 2)
        self.assertIn("arm-none-eabi-gcc", result["ambiguous"])

    def test_build_plan_accepts_platform_launchers_and_explicit_file(self):
        directory = fixture(self.root)
        for index, name in enumerate(("stm32cubeide", "Contents/MacOS/stm32cubeide", "custom-launcher")):
            launcher = self.root / str(index) / name
            launcher.parent.mkdir(parents=True)
            launcher.write_text("must not execute", encoding="utf-8")
            ide = launcher if name == "custom-launcher" else self.root / str(index)
            result = project.build_plan(directory, ide, self.root / "scratch", "Debug")
            self.assertEqual(result["argv"][0], str(launcher))
            self.assertIn(str(launcher), result["posix_shell"])
            self.assertFalse((self.root / "scratch").exists())

    def test_build_plan_requires_explicit_choice_for_multiple_launchers(self):
        directory = fixture(self.root)
        ide = self.root / "IDE"
        ide.mkdir()
        for name in ("stm32cubeidec.exe", "stm32cubeide"):
            (ide / name).touch()
        with self.assertRaisesRegex(ValueError, "Multiple CubeIDE launchers"):
            project.build_plan(directory, ide, self.root / "scratch", "Debug")
        result = project.build_plan(directory, ide / "stm32cubeide", self.root / "scratch", "Debug")
        self.assertEqual(result["argv"][0], str(ide / "stm32cubeide"))

    def test_doctor_finds_extensionless_tools_and_host_manifests(self):
        ide, host = self.root / "IDE", self.root / "host"
        ide.mkdir()
        (ide / "arm-none-eabi-gcc").touch()
        (host / ".venv/bin").mkdir(parents=True)
        (host / ".venv/bin/python").write_text("must not execute", encoding="utf-8")
        (host / "package.json").write_text("{}", encoding="utf-8")
        (host / "Control.csproj").write_text("<Project/>", encoding="utf-8")
        with patch("shutil.which", return_value=None):
            result = project.doctor(ide, host)
        self.assertEqual(result["tools"]["arm-none-eabi-gcc"], [str(ide / "arm-none-eabi-gcc")])
        self.assertEqual(result["pc_app"]["manifests"], ["Control.csproj", "package.json"])
        self.assertEqual(result["pc_app"]["python_environments"], [str(host / ".venv/bin/python")])

    def test_duplicate_configurations_are_reported_and_build_is_ambiguous(self):
        import copy
        import xml.etree.ElementTree as ET
        directory = fixture(self.root)
        path = directory / ".cproject"
        tree = ET.parse(path)
        storage = tree.getroot().find("storageModule")
        storage.append(copy.deepcopy(storage.find("cconfiguration")))
        tree.write(path, encoding="utf-8")
        self.assertTrue(any("Duplicate configuration" in warning for warning in project.inspect_project(directory)["warnings"]))
        ide = self.root / "IDE"
        ide.mkdir()
        (ide / "stm32cubeidec.exe").touch()
        with self.assertRaisesRegex(ValueError, "Ambiguous configuration"):
            project.build_plan(directory, ide, self.root / "scratch", "Debug")



class CliTests(unittest.TestCase):
    def run_cli(self, args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = main(args)
        return status, out.getvalue(), err.getvalue()

    def test_invalid_frame_is_json_error(self):
        status, output, error = self.run_cli(["frame", "decode", "--spec", str(SCRIPTS.parent / "references/frame.example.json"),
                                                    "A5 5A 00 00 00 01 FF 0D 0A"])
        self.assertEqual(status, 2)
        self.assertEqual(output, "")
        self.assertIn("Checksum", json.loads(error)["error"])

    def test_profile_relative_target_from_different_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root / "fw", "보드", "App")
            profile = root / "profile.json"
            profile.write_text(json.dumps({"workspace": "fw", "targets": {"alias": "보드"}}), encoding="utf-8")
            status, output, error = self.run_cli(["--profile", str(profile), "inspect", "--project", "alias"])
            self.assertEqual((status, error), (0, ""))
            self.assertEqual(json.loads(output)["name"], "App")

    def test_output_never_overwrites_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "keep.json"
            path.write_text("original")
            status, _, _ = self.run_cli(["--output", str(path), "frame", "encode", "--spec",
                                           str(SCRIPTS.parent / "references/frame.example.json"), "--command", "1"])
            self.assertEqual(status, 2)
            self.assertEqual(path.read_text(), "original")

    def test_compare_projects_resolves_both_profile_aliases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root / "fw", "a", "A")
            fixture(root / "fw", "b", "B")
            profile = root / "profile.json"
            profile.write_text(json.dumps({"workspace": "fw", "targets": {"left": "a", "right": "b"}}))
            status, output, error = self.run_cli(["--profile", str(profile), "compare-projects",
                                                   "--before", "left", "--after", "right"])
            self.assertEqual((status, error), (0, ""))
            self.assertEqual(json.loads(output)["changed_count"], 2)

    def test_inventory_partial_failure_exit_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / ".project").write_text("<broken")
            status, output, _ = self.run_cli(["inventory", "--root", tmp])
            self.assertEqual(status, 1)
            self.assertEqual(len(json.loads(output)["errors"]), 1)

    def test_invalid_profile_returns_input_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            for value in ([], {"workspace": 2}, {"targets": []}, {"targets": {"app": 2}}):
                path.write_text(json.dumps(value))
                status, _, error = self.run_cli(["--profile", str(path), "inventory"])
                self.assertEqual(status, 2)
                self.assertIn("error", json.loads(error))


if __name__ == "__main__":
    unittest.main()
