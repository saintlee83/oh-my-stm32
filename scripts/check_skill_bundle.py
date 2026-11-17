"""Exercise the copied skill without the repository entry point or local imports."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents/skills/stm32-workbench"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="stm32-bundle-") as directory:
        scratch = Path(directory).resolve()
        copied = scratch / "portable skill"
        shutil.copytree(SKILL, copied, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        unrelated = scratch / "caller"
        unrelated.mkdir()
        cli = copied / "scripts/stm32_toolkit.py"
        run = subprocess.run(
            [sys.executable, "-E", str(cli), "frame", "verify",
             "--spec", str(copied / "references/frame.example.json"),
             "--vectors", str(copied / "references/frame-vectors.example.json")],
            cwd=unrelated, capture_output=True, text=True, encoding="utf-8", check=True)
        result = json.loads(run.stdout)
        expected = {"vectors_checked": 2, "invalid_frames_checked": 3, "errors": [],
                    "hardware_access": False, "schema_version": "1.0", "operation": "frame.verify"}
        if any(result.get(key) != value for key, value in expected.items()):
            raise ValueError(f"Unexpected standalone result: {result}")
        if not (copied / "references/result-v1.schema.json").is_file():
            raise ValueError("The standalone skill is missing its result schema.")
    print("Standalone skill: 2 reference frames matched; 3 invalid frames rejected; versioned JSON available.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
