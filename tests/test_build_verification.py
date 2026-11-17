from __future__ import annotations

import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import verify_cubeide


def synthetic_elf(machine=40, entry=0x08000009, flags=5):
    ident = b"\x7fELF\x01\x01\x01" + bytes(9)
    header = struct.pack("<HHIIIIIHHHHHH", 2, machine, 1, entry, 52, 0, 0, 52, 32, 1, 0, 0, 0)
    segment = struct.pack("<IIIIIIII", 1, 84, 0x08000000, 0x08000000, 12, 12, flags, 4)
    contents = struct.pack("<II", 0x20001000, entry) + b"\x00\xbf\xfe\xe7"
    return ident + header + segment + contents


class BuildVerificationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.launcher = self.root / "launcher"
        self.launcher.touch()

    def test_arm_elf_requires_executable_entry_and_complete_segments(self):
        path = self.root / "test.elf"
        path.write_bytes(synthetic_elf())
        result = verify_cubeide.elf_evidence(path)
        self.assertEqual((result["machine"], result["entry"], result["load_segments"]),
                         ("ARM", "0x08000009", 1))
        for raw in (b"", synthetic_elf(machine=62), synthetic_elf(entry=0x20000001),
                    synthetic_elf(entry=0x08000008), synthetic_elf(flags=4),
                    synthetic_elf()[:52], synthetic_elf()[:-1]):
            with self.subTest(raw=raw[:24]):
                path.write_bytes(raw)
                with self.assertRaises(ValueError):
                    verify_cubeide.elf_evidence(path)

    def test_zero_exit_without_artifacts_is_a_failed_build(self):
        def skipped(argv, cwd, log_path, timeout):
            log_path.write_text("No configuration matched. Skipping.", encoding="utf-8")
            return 0
        output = self.root / "result"
        with patch.object(verify_cubeide, "run_build", side_effect=skipped):
            result = verify_cubeide.verify(self.launcher, output, ["Debug"], 10)
        self.assertFalse(result["success"])
        self.assertTrue(result["fixture_unchanged"])
        self.assertIn("fresh ELF and map", result["error"])
        self.assertFalse(json.loads((output / "result.json").read_text(encoding="utf-8"))["success"])

    def test_success_requires_fresh_artifacts_and_preserves_the_fixture(self):
        before = verify_cubeide.snapshot(verify_cubeide.FIXTURE)
        def compile_fixture(argv, cwd, log_path, timeout):
            configuration = argv[-1].split("/")[-1]
            directory = cwd / configuration
            directory.mkdir()
            (directory / "Toolkit.Smoke.elf").write_bytes(synthetic_elf())
            (directory / "Toolkit.Smoke.map").write_text("synthetic test map", encoding="utf-8")
            log_path.write_text("synthetic test compiler", encoding="utf-8")
            return 0
        with patch.object(verify_cubeide, "run_build", side_effect=compile_fixture) as run:
            result = verify_cubeide.verify(self.launcher, self.root / "result", ["Debug", "Release"], 10)
        self.assertTrue(result["success"])
        self.assertEqual(run.call_count, 2)
        self.assertEqual(verify_cubeide.snapshot(verify_cubeide.FIXTURE), before)
        self.assertEqual([build["configuration"] for build in result["builds"]], ["Debug", "Release"])
        self.assertTrue(all(build["elf"]["load_segments"] == 1 for build in result["builds"]))

    def test_nonzero_build_exit_is_recorded_without_claiming_success(self):
        def failed(argv, cwd, log_path, timeout):
            log_path.write_text("Compiler failed", encoding="utf-8")
            return 7
        with patch.object(verify_cubeide, "run_build", side_effect=failed):
            result = verify_cubeide.verify(self.launcher, self.root / "result", ["Debug"], 10)
        self.assertFalse(result["success"])
        self.assertEqual(result["builds"][0]["exit_code"], 7)

    def test_process_timeout_terminates_the_build(self):
        log = self.root / "timeout.log"
        with self.assertRaisesRegex(ValueError, "process tree terminated"):
            verify_cubeide.run_build(
                [sys.executable, "-u", "-c", "import time; print('started'); time.sleep(60)"],
                self.root, log, 1)
        self.assertIn("started", log.read_text(encoding="utf-8"))

    def test_existing_output_invalid_configuration_and_timeout_do_not_execute(self):
        existing = self.root / "existing"
        existing.mkdir()
        keep = existing / "keep.txt"
        keep.write_text("original", encoding="utf-8")
        with patch.object(verify_cubeide, "run_build") as run:
            for output, configs, timeout in ((existing, ["Debug"], 10),
                                             (self.root / "invalid", ["Other"], 10),
                                             (self.root / "duplicate", ["Debug", "Debug"], 10),
                                             (self.root / "timeout", ["Debug"], 0)):
                with self.subTest(output=output), self.assertRaises((OSError, ValueError)):
                    verify_cubeide.verify(self.launcher, output, configs, timeout)
            run.assert_not_called()
        self.assertEqual(keep.read_text(encoding="utf-8"), "original")


if __name__ == "__main__":
    unittest.main()
