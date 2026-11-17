"""Explicit development-only execution of the bundled synthetic CubeIDE fixture."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".agents/skills/stm32-workbench/scripts"))
from stm32kit import __version__
from stm32kit.project import build_plan

FIXTURE = ROOT / "tests/fixtures/cubeide-smoke"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(root: Path) -> dict[str, str]:
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Linked fixture paths are not supported: {path}")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = digest(path)
    return result


def elf_evidence(path: Path) -> dict:
    raw = path.read_bytes()
    if len(raw) < 52 or raw[:7] != b"\x7fELF\x01\x01\x01":
        raise ValueError(f"Expected a complete ELF32 little-endian header: {path}")
    (elf_type, machine, version, entry, program_offset, _, _, header_size,
     program_size, program_count, _, _, _) = struct.unpack_from("<HHIIIIIHHHHHH", raw, 16)
    if (elf_type, machine, version) != (2, 40, 1):
        raise ValueError(f"Expected an ARM executable ELF: {path}")
    if not (0x08000000 <= (entry & ~1) < 0x08004000) or not entry & 1:
        raise ValueError(f"Entry point is outside the synthetic Thumb code region: {path}")
    if (header_size != 52 or program_size != 32 or program_count == 0
            or program_offset < header_size or program_offset + program_count * program_size > len(raw)):
        raise ValueError(f"Missing or truncated ELF program headers: {path}")
    executable_entry = False
    load_segments = 0
    for index in range(program_count):
        kind, offset, address, _, file_size, memory_size, flags, _ = struct.unpack_from(
            "<IIIIIIII", raw, program_offset + index * program_size)
        if kind != 1:  # PT_LOAD
            continue
        load_segments += 1
        if file_size > memory_size or offset + file_size > len(raw):
            raise ValueError(f"Truncated ELF load segment: {path}")
        if flags & 1 and address <= (entry & ~1) < address + file_size:
            executable_entry = True
    if not executable_entry:
        raise ValueError(f"ELF entry point has no executable load segment: {path}")
    return {"file": path.name, "bytes": len(raw), "sha256": digest(path),
            "machine": "ARM", "entry": f"0x{entry:08X}", "load_segments": load_segments,
            "compiler_markers": sorted({value.decode("ascii", errors="replace")
                                       for value in re.findall(rb"GCC: [^\x00\r\n]+", raw)})}


def run_build(argv: list[str], cwd: Path, log_path: Path, timeout: int) -> int:
    options = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
               if os.name == "nt" else {"start_new_session": True})
    with log_path.open("w", encoding="utf-8", newline="\n") as log:
        process = subprocess.Popen(argv, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, **options)
        try:
            return process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            else:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise ValueError(f"Build exceeded {timeout} seconds; process tree terminated.") from None


def verify(ide: Path, output: Path, configurations: list[str], timeout: int) -> dict:
    if timeout <= 0:
        raise ValueError("Timeout must be positive.")
    if not configurations or len(set(configurations)) != len(configurations):
        raise ValueError("Choose each configuration at most once.")
    if any(name not in ("Debug", "Release") for name in configurations):
        raise ValueError("The fixture supports Debug and Release.")
    output = output.resolve()
    if output.is_relative_to(FIXTURE.resolve()):
        raise ValueError("Output must be outside the committed fixture.")
    before = snapshot(FIXTURE)
    output.mkdir(parents=True, exist_ok=False)
    copied = output / "source copy"
    shutil.copytree(FIXTURE, copied)
    report = {"report_version": 1, "toolkit_version": __version__,
              "observed_at": datetime.now(timezone.utc).isoformat(),
              "fixture": FIXTURE.relative_to(ROOT).as_posix(),
              "source_sha256": before, "hardware_access": False,
              "builds": [], "success": False}
    try:
        for configuration in configurations:
            workspace = output / "workspaces" / configuration
            plan = build_plan(copied, ide, workspace, configuration)
            (output / f"{configuration}-plan.json").write_text(
                json.dumps(plan, indent=2) + "\n", encoding="utf-8")
            elf = copied / configuration / "Toolkit.Smoke.elf"
            map_file = elf.with_suffix(".map")
            if elf.exists() or map_file.exists():
                raise ValueError("Build artifacts must not exist before execution.")
            log_path = output / f"{configuration}-build.log"
            print(f"Building {configuration}; log: {log_path}", flush=True)
            status = run_build(plan["argv"], copied, log_path, timeout)
            build = {"configuration": configuration, "exit_code": status,
                     "log": log_path.name, "log_sha256": digest(log_path),
                     "launcher": plan["argv"][0], "success": False}
            report["builds"].append(build)
            metadata_log = workspace / ".metadata/.log"
            if metadata_log.exists():
                text = metadata_log.read_text(encoding="utf-8", errors="replace")
                match = re.search(r"^eclipse.buildId=(.+)$", text, flags=re.M)
                build["ide_build_id"] = match[1].strip() if match else None
            if status:
                raise ValueError(f"{configuration} build exited {status}; see {log_path}.")
            # CubeIDE can exit zero when no project/configuration matched.
            if not elf.is_file() or not map_file.is_file() or map_file.stat().st_size == 0:
                raise ValueError(f"{configuration} did not produce a fresh ELF and map.")
            build["elf"] = elf_evidence(elf)
            build["map"] = {"file": map_file.name, "sha256": digest(map_file)}
            build["success"] = True
        report["fixture_unchanged"] = snapshot(FIXTURE) == before
        if not report["fixture_unchanged"]:
            raise ValueError("The committed fixture changed during verification.")
        report["success"] = True
    except (OSError, ValueError) as exc:
        report["error"] = str(exc)
        report["fixture_unchanged"] = snapshot(FIXTURE) == before
    finally:
        (output / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ide", type=Path, required=True, help="CubeIDE launcher or installation directory")
    parser.add_argument("--output-dir", type=Path, required=True, help="New directory for copies, logs, and artifacts")
    parser.add_argument("--configuration", action="append", choices=("Debug", "Release"))
    parser.add_argument("--timeout", type=int, default=180, help="Maximum seconds per build")
    args = parser.parse_args()
    try:
        result = verify(args.ide, args.output_dir, args.configuration or ["Debug", "Release"], args.timeout)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
