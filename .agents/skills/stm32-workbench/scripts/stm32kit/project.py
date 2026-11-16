"""Read CubeIDE/CubeMX metadata. Never execute project-supplied code."""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import os
from pathlib import Path
import re
import shlex
import shutil
import xml.etree.ElementTree as ET


PRUNED = frozenset({
    ".git", ".metadata", ".venv", "__pycache__", ".pytest_cache", "node_modules",
    "drivers", "middlewares", "debug", "release", "build", "build_new", "dist",
    "dist_new", "packages", "bin", "obj",
})


def read_text(path: Path) -> str:
    # Metadata and modern application code are UTF-8; do not silently corrupt it.
    return path.read_text(encoding="utf-8-sig")


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def require_dir(path: Path) -> Path:
    path = path.resolve()
    if not path.is_dir():
        raise ValueError(f"Directory does not exist: {path}")
    return path


def read_ioc(path: Path) -> dict[str, str]:
    values = {}
    for line in read_text(path).splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "!")) or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def strip_c_comments(source: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", source, flags=re.S)


def memory_regions(path: Path) -> list[dict]:
    """Parse literal GNU ld MEMORY regions; preserve unparsed expressions."""
    source = strip_c_comments(read_text(path))
    block = re.search(r"\bMEMORY\s*\{(.*?)\}", source, re.S)
    if not block:
        return []
    regions = []
    pattern = r"(\w+)\s*(?:\([^)]*\))?\s*:\s*ORIGIN\s*=\s*([^,\n]+),\s*LENGTH\s*=\s*([^\n;}]+)"
    for name, origin, length in re.findall(pattern, block[1], re.I):
        def literal(value):
            value = value.strip()
            match = re.fullmatch(r"(0x[0-9a-fA-F]+|[0-9]+)\s*([kKmM]?)", value)
            if not match:
                return None
            base = 16 if match[1].lower().startswith("0x") else 10
            return int(match[1], base) * {"": 1, "k": 1024, "m": 1024 ** 2}[match[2].lower()]
        regions.append({"name": name, "origin": literal(origin), "length": literal(length),
                        "origin_expression": origin.strip(), "length_expression": length.strip()})
    return regions


def configurations(path: Path) -> list[dict]:
    root = ET.parse(path).getroot()
    result = []
    for config in root.findall(".//cconfiguration/storageModule/configuration"):
        item = {"name": config.get("name"), "id": config.get("id"), "artifact_name": config.get("artifactName"),
                "artifact_extension": config.get("artifactExtension"), "mcu": [],
                "linker_scripts": [], "defines": [], "include_paths": [], "build_paths": [],
                "prebuild_step": config.get("prebuildStep", ""),
                "postbuild_step": config.get("postbuildStep", "")}
        for option in config.findall(".//option"):
            key = option.get("superClass", option.get("id", ""))
            value = option.get("value")
            children = [entry.get("value", "") for entry in option.findall("listOptionValue")]
            if ".target_mcu" in key and value:
                item["mcu"].append(value)
            elif ".linker.option.script" in key and value:
                item["linker_scripts"].append(value)
            elif ".compiler.option.definedsymbols" in key:
                item["defines"].extend(children)
            elif ".compiler.option.includepaths" in key:
                item["include_paths"].extend(children)
        item["build_paths"] = [b.get("buildPath", "") for b in config.findall(".//builder")]
        for key in ("mcu", "linker_scripts", "defines", "include_paths", "build_paths"):
            item[key] = sorted(set(item[key]))
        result.append(item)
    return result


def project_summary(project: Path) -> dict:
    project = require_dir(project)
    root = ET.parse(project / ".project").getroot()
    name = root.findtext("name")
    if not name:
        raise ValueError(f"Missing Eclipse project name: {project / '.project'}")
    cproject = project / ".cproject"
    configs = configurations(cproject) if cproject.is_file() else []
    return {"path": str(project), "name": name, "folder_name": project.name,
            "has_cproject": cproject.is_file(),
            "configurations": [c["name"] for c in configs],
            "mcu": sorted({m for c in configs for m in c["mcu"]}),
            "ioc_files": [p.name for p in sorted(project.glob("*.ioc"))],
            "linked_resources": [{child.tag: child.text for child in link}
                                 for link in root.findall("./linkedResources/link")],
            "referenced_projects": [p.text for p in root.findall("./projects/project") if p.text]}


def inventory(root: Path) -> dict:
    root = require_dir(root)
    projects, errors, skipped = [], [], Counter()

    def error(exc):
        errors.append({"path": str(exc.filename), "error": str(exc)})

    for current, dirs, files in os.walk(root, onerror=error, followlinks=False):
        retained = []
        for name in sorted(dirs):
            child = Path(current) / name
            # Do not follow junctions out of the selected tree, including Windows 3.10.
            try:
                resolved = child.resolve()
                outside = not resolved.is_relative_to(root)
                junction = resolved != child.absolute()
            except OSError as exc:
                error(exc)
                continue
            if name.lower() in PRUNED or child.is_symlink() or outside or junction:
                skipped[name.lower()] += 1
            else:
                retained.append(name)
        dirs[:] = retained
        if ".project" in files:
            project = Path(current)
            try:
                record = project_summary(project)
                record["relative_path"] = project.relative_to(root).as_posix()
                projects.append(record)
            except (OSError, ValueError, ET.ParseError) as exc:
                errors.append({"path": str(project), "error": str(exc)})
    by_name = defaultdict(list)
    for project in projects:
        by_name[project["name"]].append(project["relative_path"])
    return {"root": str(root), "project_count": len(projects), "projects": projects,
            "duplicate_names": {k: v for k, v in sorted(by_name.items()) if len(v) > 1},
            "skipped_directories": dict(sorted(skipped.items())), "errors": errors,
            "note": "Includes history and experiments. No active project is inferred from its name."}


def inspect_project(project: Path) -> dict:
    result = project_summary(project)
    project = Path(result["path"])
    result["configurations"] = configurations(project / ".cproject") if result["has_cproject"] else []
    result["ioc"] = []
    evidence = [project / ".project"]
    if result["has_cproject"]:
        evidence.append(project / ".cproject")
    for path in sorted(project.glob("*.ioc")):
        values = read_ioc(path)
        result["ioc"].append({"file": path.name, "mcu": values.get("Mcu.Name"),
                              "part_number": values.get("Mcu.CPN"),
                              "project_name": values.get("ProjectManager.ProjectName"),
                              "firmware_package": values.get("ProjectManager.FirmwarePackage"),
                              "settings": {k: v for k, v in values.items()
                                           if re.match(r"^(RCC\.|NVIC\.|.*\.BaudRate$)", k)}})
        evidence.append(path)
    result["linker_files"] = []
    for path in sorted(project.glob("*.ld")):
        result["linker_files"].append({"file": path.name, "regions": memory_regions(path)})
        evidence.append(path)
    result["source_observations"] = []
    # These are lexical observations, not a preprocessed program or runtime state.
    pattern = re.compile(r"^\s*#\s*define\s+(?:VECT_TAB_OFFSET|APPLICATION_ADDRESS|FW_VERSION_\w+)\b"
                         r"|\b\w+\.Init\.BaudRate\s*=")
    core = project / "Core"
    if core.is_dir():
        for path in sorted(core.rglob("*")):
            if path.suffix.lower() not in (".c", ".h") or not path.is_file():
                continue
            source = read_text(path)
            matches = [{"line": n, "text": line.strip()} for n, line in enumerate(source.splitlines(), 1)
                       if pattern.search(line)]
            if matches:
                result["source_observations"].append({"file": path.relative_to(project).as_posix(),
                                                       "matches": matches})
                evidence.append(path)
    result["warnings"] = []
    if not result["has_cproject"]:
        result["warnings"].append("Missing .cproject: this may be an Eclipse stub, not a buildable project.")
    duplicate_configs = [name for name, count in Counter(c["name"] for c in result["configurations"]).items() if count > 1]
    if duplicate_configs:
        result["warnings"].append(f"Duplicate configuration names: {duplicate_configs}; inspect configuration IDs before building.")
    if result["folder_name"] != result["name"]:
        result["warnings"].append("Folder and Eclipse project names differ; build using the Eclipse name.")
    if len(result["ioc"]) > 1:
        result["warnings"].append("Multiple IOC files; choose the authoritative one explicitly.")
    for entry in result["ioc"]:
        if entry["project_name"] and entry["project_name"] != result["name"]:
            result["warnings"].append(f"{entry['file']}: IOC project name differs from .project.")
    if result["linked_resources"]:
        result["warnings"].append("Linked resources require separate path validation before an isolated build.")
    result["evidence"] = [{"file": p.relative_to(project).as_posix(), "sha256": digest(p)}
                          for p in evidence]
    result["limitations"] = ["Source observations do not evaluate #if branches or macro overrides.",
                              "Linker files listed here are not necessarily active; use configuration.linker_scripts.",
                              "Inspection does not prove that an existing ELF was built from these sources."]
    return result


def ioc_diff(before: Path, after: Path, all_settings: bool = False) -> dict:
    old, new = read_ioc(before), read_ioc(after)
    def relevant(key):
        return all_settings or bool(re.match(r"^(P[A-Z]\d+(?:[^.]*)\.|VP_|Mcu\.|RCC\.|NVIC\.)", key))
    changes = [{"key": key, "before": old.get(key), "after": new.get(key)}
               for key in sorted(old.keys() | new.keys()) if relevant(key) and old.get(key) != new.get(key)]
    return {"before": str(before.resolve()), "after": str(after.resolve()),
            "before_sha256": digest(before), "after_sha256": digest(after),
            "scope": "all" if all_settings else "pins, MCU, RCC, NVIC",
            "changed": len(changes), "changes": changes,
            "note": "IOC comparison only; also inspect main.h, gpio.c and peripheral MSP initialization."}


TOOL_NAMES = {
    "stm32cubeide": ("stm32cubeidec.exe", "stm32cubeidec", "stm32cubeide"),
    "arm-none-eabi-gcc": ("arm-none-eabi-gcc.exe", "arm-none-eabi-gcc"),
    "arm-none-eabi-gdb": ("arm-none-eabi-gdb.exe", "arm-none-eabi-gdb"),
    "arm-none-eabi-size": ("arm-none-eabi-size.exe", "arm-none-eabi-size"),
    "make": ("make.exe", "make"),
    "ST-LINK_gdbserver": ("ST-LINK_gdbserver.exe", "ST-LINK_gdbserver"),
    "STM32_Programmer_CLI": ("STM32_Programmer_CLI.exe", "STM32_Programmer_CLI"),
}


def ide_launcher(ide: Path) -> Path:
    """Allow an explicit platform launcher; directory discovery must be unambiguous."""
    ide = ide.resolve()
    if ide.is_file():
        return ide
    ide = require_dir(ide)
    candidates = [ide / name for name in TOOL_NAMES["stm32cubeide"]]
    candidates.extend(ide / subdir / name for subdir in
                      ("Contents/MacOS", "STM32CubeIDE.app/Contents/MacOS")
                      for name in ("stm32cubeide", "stm32cubeidec"))
    found = [path for path in candidates if path.is_file()]
    if not found:
        raise ValueError(f"No CubeIDE launcher found; supply --ide with an explicit launcher file: {ide}")
    if len(found) > 1:
        raise ValueError(f"Multiple CubeIDE launchers found; supply --ide with one launcher file: {found}")
    return found[0]


def doctor(ide: Path | None, pc_app: Path | None = None) -> dict:
    found = {name: set() for name in TOOL_NAMES}
    for name, filenames in TOOL_NAMES.items():
        for filename in filenames:
            path = shutil.which(filename)
            if path:
                found[name].add(str(Path(path).resolve()))
    if ide:
        ide = ide.resolve()
        root = require_dir(ide.parent if ide.is_file() else ide)
        for current, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not (Path(current) / d).is_symlink()
                             and (Path(current) / d).resolve() == (Path(current) / d).absolute())
            for name, filenames in TOOL_NAMES.items():
                for filename in filenames:
                    if filename in files:
                        found[name].add(str(Path(current) / filename))
    result = {"ide": str(ide) if ide else None,
              "tools": {k: sorted(v) for k, v in found.items()},
              "missing": [k for k, v in found.items() if not v],
              "ambiguous": [k for k, v in found.items() if len(v) > 1],
              "note": "File discovery only. No tool, debugger, serial port or target was started."}
    if pc_app:
        pc_app = require_dir(pc_app)
        manifests = {"pyproject.toml", "package.json", "CMakeLists.txt", "Cargo.toml", "requirements.txt"}
        result["pc_app"] = {"path": str(pc_app),
                            "manifests": sorted(p.name for p in pc_app.iterdir() if p.is_file()
                                                and (p.name in manifests or p.suffix in {".csproj", ".sln"})),
                            "python_environments": [str(pc_app / relative) for relative in
                                                    (".venv/Scripts/python.exe", ".venv/bin/python", ".venv/bin/python3")
                                                    if (pc_app / relative).is_file()]}
    return result


def build_plan(project: Path, ide: Path, workspace: Path, config: str) -> dict:
    info = inspect_project(project)
    project = Path(info["path"])
    launcher = ide_launcher(ide)
    matches = [c for c in info["configurations"] if c["name"] == config]
    if not matches:
        raise ValueError(f"Unknown configuration {config!r}; available: {[c['name'] for c in info['configurations']]}")
    if len(matches) > 1:
        raise ValueError(f"Ambiguous configuration {config!r}: {len(matches)} entries. Resolve duplicate names before generating a build plan.")
    workspace = workspace.resolve()
    if workspace == project or workspace.is_relative_to(project) or project.is_relative_to(workspace):
        raise ValueError("Build workspace must be separate from the project and its ancestors.")
    if workspace.exists() and (not workspace.is_dir() or any(workspace.iterdir())):
        raise ValueError("Choose a new or empty build workspace; existing IDE metadata will not be reused.")
    # Eclipse headless build selectors are regexes, even for a single project/config.
    selector = re.escape(info["name"]) + "/" + re.escape(config)
    argv = [str(launcher), "--launcher.suppressErrors", "-nosplash", "-application",
            "org.eclipse.cdt.managedbuilder.core.headlessbuild", "-data", str(workspace),
            "-import", str(project), "-build", selector]
    quote = lambda s: "'" + s.replace("'", "''") + "'"
    selected = matches[0]
    warnings = list(info["warnings"])
    if info["referenced_projects"]:
        warnings.append("Referenced projects are not imported by this plan; prepare and import them separately.")
    if selected["prebuild_step"] or selected["postbuild_step"]:
        warnings.append("Review the configured pre/post-build commands before executing the plan.")
    return {"executed": False, "project": str(project), "eclipse_project": info["name"],
            "configuration": selected, "workspace": str(workspace), "argv": argv,
            "powershell": "& " + " ".join(quote(v) for v in argv),
            "posix_shell": shlex.join(argv),
            "warnings": warnings,
            "effects_if_executed": ["Creates Eclipse metadata under the requested build workspace.",
                                    "Import references the source directory; generated build outputs and hooks can write there.",
                                    "For source isolation, pass a prepared project copy and validate its linked resources."],
            "note": "Plan only. No directory was created and no build or flash command was executed."}
