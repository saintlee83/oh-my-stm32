from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".agents/skills/stm32-workbench/scripts"))
from stm32kit import compare


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.before, self.after = self.root / "before", self.root / "after"
        self.before.mkdir()
        self.after.mkdir()

    def inventory(self, name, entries, errors=None, root="D:/fw"):
        path = self.root / name
        path.write_text(json.dumps({"root": root, "projects": entries, "errors": errors or []}), encoding="utf-8")
        return path

    def write(self, directory, relative, content):
        path = directory / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def test_inventory_add_remove_metadata_and_root_relocation(self):
        old = self.inventory("old.json", [{"relative_path": "A", "name": "Old", "path": "C:/A"},
                                          {"relative_path": "Gone", "name": "Gone"}])
        new = self.inventory("new.json", [{"relative_path": "A", "name": "New", "path": "E:/A"},
                                          {"relative_path": "Added", "name": "Added"}], root="E:/fw")
        result = compare.inventory_diff(old, new)
        self.assertTrue(result["comparison_complete"])
        self.assertEqual(result["added"][0]["relative_path"], "Added")
        self.assertEqual(result["removed"][0]["relative_path"], "Gone")
        self.assertEqual(result["changed"][0]["fields"], {"name": {"before": "Old", "after": "New"}})

    def test_duplicate_eclipse_names_remain_distinct_by_relative_path(self):
        entries = [{"relative_path": p, "name": "Same"} for p in ("one/App", "two/App")]
        old = self.inventory("old.json", entries)
        new = self.inventory("new.json", list(reversed(entries)), root="E:/moved")
        result = compare.inventory_diff(old, new)
        self.assertFalse(result["added"] or result["removed"] or result["changed"])

    def test_partial_inventory_does_not_confirm_removal_or_addition(self):
        old = self.inventory("old.json", [{"relative_path": "A", "name": "A"}])
        new = self.inventory("new.json", [{"relative_path": "B", "name": "B"}], [{"error": "unreadable A"}])
        result = compare.inventory_diff(old, new)
        self.assertFalse(result["comparison_complete"])
        self.assertEqual(result["added"], [])
        self.assertEqual(result["removed"], [])
        self.assertEqual(result["unobserved_after"][0]["relative_path"], "A")
        self.assertEqual(result["newly_observed"][0]["relative_path"], "B")

    def test_inventory_rejects_invalid_or_duplicate_relative_paths(self):
        valid = self.inventory("valid.json", [])
        bad = self.root / "bad.json"
        for value in ([], {}, {"projects": [], "errors": "error"}):
            bad.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                compare.inventory_diff(bad, valid)
        for path in ("../escape", "/absolute", "C:/absolute", ""):
            invalid = self.inventory("bad.json", [{"relative_path": path, "name": "A"}])
            with self.assertRaises(ValueError):
                compare.inventory_diff(invalid, valid)
        duplicates = self.inventory("bad.json", [{"relative_path": "A", "name": "A"}] * 2)
        with self.assertRaises(ValueError):
            compare.inventory_diff(duplicates, valid)

    def test_source_diff_captures_add_remove_and_single_line(self):
        self.write(self.before, "Core/Src/spi.c", b"pull = UP;\n")
        self.write(self.after, "Core/Src/spi.c", b"pull = DOWN;\n")
        self.write(self.before, "Core/Inc/old.h", b"old")
        self.write(self.after, "Core/Inc/new.h", b"new")
        result = compare.project_diff(self.before, self.after, text_diff=True)
        self.assertEqual(result["changed_count"], 3)
        spi = next(c for c in result["changes"] if c["path"].endswith("spi.c"))
        self.assertEqual(spi["status"], "modified")
        self.assertIn("-pull = UP;", spi["text_diff"])
        self.assertIn("+pull = DOWN;", spi["text_diff"])
        self.assertEqual((self.before / "Core/Src/spi.c").read_bytes(), b"pull = UP;\n")

    def test_vendor_opt_in_does_not_include_generated_outputs(self):
        for relative in ("Drivers/vendor.c", "Middlewares/middleware.h", "Debug/generated.c", "readme.md", "output.bin"):
            self.write(self.before, relative, b"old")
            self.write(self.after, relative, b"new")
        self.assertEqual(compare.project_diff(self.before, self.after)["changed_count"], 0)
        result = compare.project_diff(self.before, self.after, include_vendor=True)
        self.assertEqual([c["path"] for c in result["changes"]], ["Drivers/vendor.c", "Middlewares/middleware.h"])

    def test_ioc_and_c_source_are_independent_evidence(self):
        for directory in (self.before, self.after):
            self.write(directory, "board.ioc", b"PA5.GPIO_PuPd=GPIO_PULLUP\n")
        self.write(self.before, "Core/Src/spi.c", b"GPIO_PULLUP\n")
        self.write(self.after, "Core/Src/spi.c", b"GPIO_PULLDOWN\n")
        result = compare.project_diff(self.before, self.after)
        self.assertEqual(result["changed_count"], 1)
        self.assertEqual(result["changes"][0]["category"], "source")

    def test_raw_line_ending_changes_are_preserved(self):
        self.write(self.before, "main.c", b"int x;\r\n")
        self.write(self.after, "main.c", b"int x;\n")
        item = compare.project_diff(self.before, self.after, text_diff=True)["changes"][0]
        self.assertNotEqual(item["before"]["sha256"], item["after"]["sha256"])
        self.assertTrue(item["normalized_text_equal"])
        self.assertEqual(item["text_diff"], [])

    def test_diff_preview_is_bounded_and_reports_truncation(self):
        self.write(self.before, "main.c", b"old\n" * 1000)
        self.write(self.after, "main.c", b"new\n" * 1000)
        item = compare.project_diff(self.before, self.after, text_diff=True)["changes"][0]
        self.assertEqual(len(item["text_diff"]), 200)
        self.assertTrue(item["text_diff_truncated"])

    def test_unreadable_file_makes_result_incomplete(self):
        self.write(self.before, "main.c", b"x")
        with patch.object(compare, "digest", side_effect=PermissionError("denied")):
            result = compare.project_diff(self.before, self.after)
        self.assertFalse(result["comparison_complete"])
        self.assertIn("denied", result["errors"][0]["error"])

    def test_partial_source_scan_does_not_claim_removal(self):
        for directory in (self.before, self.after):
            self.write(directory, "main.c", b"unchanged")
        real_digest = compare.digest
        def fail_after(path):
            if path.parent == self.after:
                raise PermissionError("cannot read after")
            return real_digest(path)
        with patch.object(compare, "digest", side_effect=fail_after):
            result = compare.project_diff(self.before, self.after)
        self.assertFalse(result["comparison_complete"])
        self.assertEqual(result["changes"][0]["status"], "unobserved_after")

    def test_symlink_files_are_not_followed(self):
        external = self.root / "outside.c"
        external.write_text("private outside source")
        try:
            (self.before / "linked.c").symlink_to(external)
        except OSError:
            self.skipTest("Symlink creation unavailable on this host")
        result = compare.project_diff(self.before, self.after)
        self.assertEqual(result["file_counts"]["before"], 0)
        self.assertEqual(result["skipped"]["before"][0]["reason"], "linked_file")


if __name__ == "__main__":
    unittest.main()
