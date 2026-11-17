from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from contract_samples import capture, collect_samples
from stm32kit import __version__, compare
from stm32kit.cli import main
from stm32kit.reporting import SCHEMA_VERSION


class CliContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name).resolve()
        cls.samples = collect_samples(cls.root)

    def test_every_operation_has_versioned_json_without_changing_status(self):
        operations = {"inventory", "inspect", "doctor", "build-plan", "ioc-diff",
                      "inventory-diff", "compare-projects", "frame.encode",
                      "frame.decode", "frame.verify", "contract"}
        for operation in operations:
            with self.subTest(operation=operation):
                sample = self.samples[operation]
                self.assertEqual((sample["status"], sample["stderr"]), (0, ""))
                document = sample["document"]
                self.assertEqual(document["operation"], operation)
                self.assertEqual(document["schema_version"], SCHEMA_VERSION)
                self.assertEqual(document["toolkit_version"], __version__)

    def test_wire_command_remains_numeric(self):
        for operation in ("frame.encode", "frame.decode"):
            document = self.samples[operation]["document"]
            self.assertIs(type(document["command"]), int)
            self.assertEqual(document["command"], 16)

    def test_partial_results_and_runtime_errors_keep_the_contract(self):
        for key, operation, expected_status in (
            ("partial-inventory", "inventory", 1),
            ("vector-mismatch", "frame.verify", 1),
            ("input-error", "inspect", 2),
            ("frame-input-error", "frame.decode", 2),
            ("output-error", "inventory", 2),
        ):
            with self.subTest(key=key):
                sample = self.samples[key]
                self.assertEqual(sample["status"], expected_status)
                self.assertEqual(sample["document"]["operation"], operation)
                self.assertEqual(sample["document"]["schema_version"], SCHEMA_VERSION)
                self.assertEqual(sample["document"]["toolkit_version"], __version__)
                if expected_status == 2:
                    self.assertEqual(sample["stdout"], "")
                    self.assertTrue(sample["document"]["error"])
                else:
                    self.assertEqual(sample["stderr"], "")
                    self.assertTrue(sample["document"]["errors"])

    def test_saved_json_has_the_same_envelope(self):
        output = self.root / "saved-result.json"
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = main(["--output", str(output), "inventory", "--root", str(self.root / "workspace")])
        self.assertEqual((status, out.getvalue(), err.getvalue()), (0, "", ""))
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), self.samples["inventory"]["document"])

    def test_argparse_help_remains_text(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as raised:
            main(["--help"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("usage:", out.getvalue())


class InventoryCompatibilityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.before = self.root / "before.json"
        self.after = self.root / "after.json"
        self.legacy = {"root": "synthetic", "projects": [{"name": "App", "relative_path": "App"}], "errors": []}
        self.before.write_text(json.dumps(self.legacy), encoding="utf-8")

    def test_legacy_and_later_minor_reports_remain_comparable(self):
        for metadata in ({}, {"schema_version": "1.0", "operation": "inventory"},
                         {"schema_version": "1.99", "operation": "inventory", "future_field": True}):
            with self.subTest(metadata=metadata):
                self.after.write_text(json.dumps({**self.legacy, **metadata}), encoding="utf-8")
                result = compare.inventory_diff(self.before, self.after)
                self.assertTrue(result["comparison_complete"])
                self.assertEqual((result["added"], result["removed"], result["changed"]), ([], [], []))

    def test_unknown_major_malformed_versions_and_wrong_operations_fail(self):
        for metadata in ({"schema_version": "2.0", "operation": "inventory"},
                         {"schema_version": "1", "operation": "inventory"},
                         {"schema_version": 1, "operation": "inventory"},
                         {"schema_version": None, "operation": "inventory"},
                         {"schema_version": "1.0", "operation": "inspect"},
                         {"schema_version": "1.0"}):
            with self.subTest(metadata=metadata):
                self.after.write_text(json.dumps({**self.legacy, **metadata}), encoding="utf-8")
                sample = capture(["inventory-diff", "--before", str(self.before), "--after", str(self.after)])
                self.assertEqual(sample["status"], 2)
                self.assertEqual(sample["document"]["operation"], "inventory-diff")
                self.assertIn("error", sample["document"])


if __name__ == "__main__":
    unittest.main()
