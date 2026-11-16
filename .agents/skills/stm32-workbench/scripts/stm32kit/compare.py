"""Offline comparison of inventories and project files; never execute inputs."""
from __future__ import annotations

import difflib
from itertools import islice
import json
import os
from pathlib import Path, PurePosixPath

from .project import PRUNED, digest, read_text, require_dir


INVENTORY_FIELDS = ("name", "has_cproject", "configurations", "mcu", "ioc_files",
                    "linked_resources", "referenced_projects")
SOURCE_SUFFIXES = frozenset({".c", ".h", ".cpp", ".hpp", ".cc", ".cxx", ".s", ".inc"})
PROJECT_SUFFIXES = SOURCE_SUFFIXES | {".ld", ".ioc", ".launch"}
PROJECT_NAMES = frozenset({".project", ".cproject", ".mxproject"})


def _inventory(path: Path) -> tuple[dict, dict]:
    report = json.loads(read_text(path))
    if (not isinstance(report, dict) or not isinstance(report.get("projects"), list)
            or not isinstance(report.get("errors"), list)):
        raise ValueError(f"Expected an inventory report with projects/errors lists: {path}")
    indexed = {}
    for item in report["projects"]:
        if not isinstance(item, dict) or not isinstance(item.get("relative_path"), str) or not isinstance(item.get("name"), str):
            raise ValueError(f"Invalid inventory project entry: {path}")
        relative = item["relative_path"].replace("\\", "/")
        parts = PurePosixPath(relative)
        if not relative or parts.is_absolute() or ".." in parts.parts or ":" in relative:
            raise ValueError(f"Inventory project path must be relative: {relative}")
        key = parts.as_posix()
        if key in indexed:
            raise ValueError(f"Duplicate relative project path in inventory: {key}")
        indexed[key] = {field: item.get(field) for field in INVENTORY_FIELDS}
    return report, indexed


def inventory_diff(before: Path, after: Path) -> dict:
    old_report, old = _inventory(before)
    new_report, new = _inventory(after)
    complete = not old_report["errors"] and not new_report["errors"]
    new_only = [{"relative_path": key, **new[key]} for key in sorted(new.keys() - old.keys())]
    old_only = [{"relative_path": key, **old[key]} for key in sorted(old.keys() - new.keys())]
    changed = []
    for key in sorted(old.keys() & new.keys()):
        fields = {field: {"before": old[key][field], "after": new[key][field]}
                  for field in INVENTORY_FIELDS if old[key][field] != new[key][field]}
        if fields:
            changed.append({"relative_path": key, "fields": fields})
    return {"before": str(before.resolve()), "after": str(after.resolve()),
            "before_sha256": digest(before), "after_sha256": digest(after),
            "comparison_complete": complete, "before_count": len(old), "after_count": len(new),
            "added": new_only if complete else [], "removed": old_only if complete else [],
            "newly_observed": new_only if not complete else [],
            "unobserved_after": old_only if not complete else [], "changed": changed,
            "errors": [{"side": side, "detail": error} for side, report in
                       (("before", old_report), ("after", new_report)) for error in report["errors"]],
            "limitations": ["Compare inventories captured with the same scanning scope and exclusions.",
                            "Metadata comparison does not detect source-only changes or prove a rename.",
                            "Partial scans report observations instead of confirmed additions/removals."]}


def file_category(relative: str) -> str:
    path = PurePosixPath(relative)
    if path.suffix.lower() in SOURCE_SUFFIXES:
        return "source"
    if path.suffix.lower() == ".ld":
        return "linker"
    if path.suffix.lower() == ".ioc":
        return "cubemx"
    return "project_metadata"


def _project_files(root: Path, include_vendor: bool) -> dict:
    root = require_dir(root)
    files, errors, skipped = {}, [], []
    exclusions = PRUNED - {"drivers", "middlewares"} if include_vendor else PRUNED

    def onerror(exc):
        errors.append({"path": str(exc.filename), "error": str(exc)})

    for current, dirs, names in os.walk(root, onerror=onerror, followlinks=False):
        retained = []
        for name in sorted(dirs):
            child = Path(current) / name
            if name.lower() in exclusions:
                skipped.append({"path": child.relative_to(root).as_posix(), "reason": "excluded_directory"})
                continue
            try:
                if child.is_symlink() or child.resolve() != child.absolute():
                    skipped.append({"path": child.relative_to(root).as_posix(), "reason": "linked_directory"})
                    continue
                retained.append(name)
            except OSError as exc:
                onerror(exc)
        dirs[:] = retained
        for name in sorted(names):
            path = Path(current) / name
            relative = path.relative_to(root).as_posix()
            if not (name in PROJECT_NAMES or path.suffix.lower() in PROJECT_SUFFIXES
                    or (".settings" in path.relative_to(root).parts and path.suffix in {".prefs", ".xml"})):
                continue
            try:
                if path.is_symlink() or path.resolve() != path.absolute():
                    skipped.append({"path": relative, "reason": "linked_file"})
                    continue
                before = path.stat()
                sha256 = digest(path)
                after = path.stat()
                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    raise ValueError("File changed while hashing; retry after edits finish.")
                files[relative] = {"sha256": sha256, "bytes": after.st_size,
                                   "category": file_category(relative)}
            except (OSError, ValueError) as exc:
                errors.append({"path": relative, "error": str(exc)})
    return {"root": str(root), "files": files, "errors": errors, "skipped": skipped}


def project_diff(before: Path, after: Path, include_vendor: bool = False, text_diff: bool = False) -> dict:
    old, new = _project_files(before, include_vendor), _project_files(after, include_vendor)
    a, b = old["files"], new["files"]
    errors = [{"side": side, **error} for side, report in (("before", old), ("after", new)) for error in report["errors"]]
    partial_scan = bool(errors)
    changes = []
    for path in sorted(a.keys() | b.keys()):
        left, right = a.get(path), b.get(path)
        if left == right:
            continue
        change = {"path": path, "category": (left or right)["category"],
                  "status": (("newly_observed" if partial_scan else "added") if left is None else
                             ("unobserved_after" if partial_scan else "removed") if right is None else "modified"),
                  "before": left, "after": right}
        if text_diff and left and right:
            if max(left["bytes"], right["bytes"]) > 1024 * 1024:
                change["text_diff_omitted"] = "File exceeds the 1 MiB text preview limit."
            else:
                try:
                    paths = (Path(old["root"]) / path, Path(new["root"]) / path)
                    texts = [read_text(p) for p in paths]
                    if any(digest(p) != entry["sha256"] for p, entry in zip(paths, (left, right))):
                        raise ValueError("File changed before diff preview; retry after edits finish.")
                    # Line endings are normalized only for this optional preview; hashes remain byte exact.
                    lines = list(islice(difflib.unified_diff(texts[0].splitlines(), texts[1].splitlines(),
                                                           fromfile="before/" + path, tofile="after/" + path,
                                                           lineterm=""), 201))
                    change["text_diff"] = lines[:200]
                    change["text_diff_truncated"] = len(lines) > 200
                    change["normalized_text_equal"] = texts[0] == texts[1]
                except (OSError, ValueError) as exc:
                    change["text_diff_omitted"] = str(exc)
                    errors.append({"path": path, "error": str(exc)})
        changes.append(change)
    return {"before": old["root"], "after": new["root"], "include_vendor": include_vendor,
            "comparison_complete": not errors, "file_counts": {"before": len(a), "after": len(b)},
            "changed_count": len(changes), "changes": changes,
            "skipped": {"before": old["skipped"], "after": new["skipped"]}, "errors": errors,
            "limitations": ["Scope: C/C++/assembly, linker, IOC, launch, Eclipse metadata/settings files.",
                            "No generated outputs, documentation, binary images or linked resources are compared.",
                            "A missing file in a partial scan is an observation, not proof of removal.",
                            "Source equality does not establish build provenance or hardware behavior."]}
