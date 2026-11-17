"""Synthetic CLI transcripts shared by behavioral and JSON Schema checks."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
from unittest.mock import patch

from test_toolkit import fixture, SCRIPTS
from stm32kit.cli import main


def capture(args: list[str]) -> dict:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        status = main(args)
    return {"status": status, "stdout": out.getvalue(), "stderr": err.getvalue(),
            "document": json.loads(err.getvalue() if status == 2 else out.getvalue())}


def collect_samples(root: Path) -> dict[str, dict]:
    before = fixture(root / "workspace", "before", "Example")
    after = fixture(root / "workspace", "after", "Example")
    (after / "board.ioc").write_text("PA1.PinState=GPIO_PIN_SET\n", encoding="utf-8")
    ide = root / "tools"
    ide.mkdir()
    (ide / "stm32cubeidec.exe").touch()
    spec = SCRIPTS.parent / "references/frame.example.json"
    vectors = SCRIPTS.parent / "references/frame-vectors.example.json"
    commands = root / "commands.py"
    commands.write_text("from enum import IntEnum\nclass Request(IntEnum):\n    READ = 16\n", encoding="utf-8")
    firmware = root / "parser.c"
    firmware.write_text("void parse(int code) { switch(code) { case 16: break; } }\n", encoding="utf-8")
    result = {}
    args_by_operation = {
        "inventory": ["inventory", "--root", str(root / "workspace")],
        "inspect": ["inspect", "--project", str(before)],
        "doctor": ["doctor", "--ide", str(ide)],
        "build-plan": ["build-plan", "--project", str(before), "--ide", str(ide),
                       "--workspace", str(root / "build workspace")],
        "ioc-diff": ["ioc-diff", "--before", str(before / "board.ioc"), "--after", str(after / "board.ioc")],
        "compare-projects": ["compare-projects", "--before", str(before), "--after", str(after), "--text-diff"],
        "frame.encode": ["frame", "encode", "--spec", str(spec), "--id", "7", "--command", "16", "--payload", "01 02 03"],
        "frame.decode": ["frame", "decode", "--spec", str(spec), "A5 5A 03 00 07 10 01 02 03 14 0D 0A"],
        "frame.verify": ["frame", "verify", "--spec", str(spec), "--vectors", str(vectors)],
        "contract": ["contract", "--commands", str(commands), "--firmware", str(firmware)],
    }
    with patch("shutil.which", return_value=None):
        for operation, args in args_by_operation.items():
            result[operation] = capture(args)
    saved = root / "inventory.json"
    saved.write_text(json.dumps(result["inventory"]["document"]), encoding="utf-8")
    result["inventory-diff"] = capture(["inventory-diff", "--before", str(saved), "--after", str(saved)])

    partial = root / "partial"
    partial.mkdir()
    (partial / ".project").write_text("<broken", encoding="utf-8")
    result["partial-inventory"] = capture(["inventory", "--root", str(partial)])

    bad_vectors = json.loads(vectors.read_text(encoding="utf-8"))
    bad_vectors["vectors"][0]["frame_hex"] = "00"
    mismatch = root / "mismatch.json"
    mismatch.write_text(json.dumps(bad_vectors), encoding="utf-8")
    result["vector-mismatch"] = capture(["frame", "verify", "--spec", str(spec), "--vectors", str(mismatch)])

    result["input-error"] = capture(["inspect", "--project", str(root / "missing")])
    result["frame-input-error"] = capture(["frame", "decode", "--spec", str(spec), "00"])
    result["output-error"] = capture(["--output", str(saved), "inventory", "--root", str(root / "workspace")])
    return result
