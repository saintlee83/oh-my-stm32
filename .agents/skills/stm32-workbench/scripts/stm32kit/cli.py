"""JSON CLI. Input errors exit 2; partial inventory exits 1."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from . import __version__, compare, project, protocol


def expanded(value: str, base: Path) -> Path:
    result = Path(os.path.expandvars(value)).expanduser()
    return (base / result).resolve() if not result.is_absolute() else result.resolve()


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description="Offline STM32 agent toolkit (no hardware access).")
    cli.add_argument("--version", action="version", version=__version__)
    cli.add_argument("--profile", type=Path, help="JSON roots/target aliases; paths resolve relative to this file")
    cli.add_argument("--output", type=Path, help="Write JSON exclusively to a new file, never overwrite")
    commands = cli.add_subparsers(dest="action", required=True)
    inv = commands.add_parser("inventory", help="List Eclipse projects, including archives and duplicate names")
    inv.add_argument("--root", help="Workspace root; overrides profile.workspace")
    inspect = commands.add_parser("inspect", help="Read project metadata, IOC, linker and source evidence")
    inspect.add_argument("--project", required=True, help="Exact directory or profile target alias")
    doc = commands.add_parser("doctor", help="Locate installed tools without starting them")
    doc.add_argument("--ide", help="IDE directory to search; overrides profile.ide")
    doc.add_argument("--pc-app", help="PC repository; overrides profile.pc_app")
    build = commands.add_parser("build-plan", help="Generate a headless command; never execute it")
    build.add_argument("--project", required=True)
    build.add_argument("--ide", help="IDE directory or explicit launcher file")
    build.add_argument("--workspace", required=True, help="New/empty Eclipse build workspace")
    build.add_argument("--configuration", default="Debug")
    diff = commands.add_parser("ioc-diff", help="Compare IOC settings; does not validate generated C")
    diff.add_argument("--before", type=Path, required=True)
    diff.add_argument("--after", type=Path, required=True)
    diff.add_argument("--all-settings", action="store_true")
    inventories = commands.add_parser("inventory-diff", help="Compare two saved inventory reports")
    inventories.add_argument("--before", type=Path, required=True)
    inventories.add_argument("--after", type=Path, required=True)
    sources = commands.add_parser("compare-projects", help="Compare source/settings hashes in two project trees")
    sources.add_argument("--before", required=True, help="Directory or profile target alias")
    sources.add_argument("--after", required=True, help="Directory or profile target alias")
    sources.add_argument("--include-vendor", action="store_true", help="Also inspect Drivers/Middlewares")
    sources.add_argument("--text-diff", action="store_true", help="Include bounded UTF-8 text previews")
    frame = commands.add_parser("frame", help="Encode/decode/verify bytes using an explicit JSON envelope spec")
    operations = frame.add_subparsers(dest="operation", required=True)
    encode = operations.add_parser("encode")
    encode.add_argument("--spec", type=Path, required=True)
    encode.add_argument("--id", type=lambda v: int(v, 0), default=0)
    encode.add_argument("--command", type=lambda v: int(v, 0), default=0)
    encode.add_argument("--payload", default="", help="Hex bytes, e.g. '01 02 03'")
    decode = operations.add_parser("decode")
    decode.add_argument("--spec", type=Path, required=True)
    decode.add_argument("hex", help="Exactly one complete hex frame")
    verify = operations.add_parser("verify")
    verify.add_argument("--spec", type=Path, required=True)
    verify.add_argument("--vectors", type=Path, required=True)
    contract = commands.add_parser("contract", help="Statically index Python enums and C case-label locations")
    contract.add_argument("--commands", type=Path, action="append", required=True, help="Python source file; repeat as needed")
    contract.add_argument("--enum", dest="enum_names", action="append", help="Select a class by name, including custom enum bases")
    contract.add_argument("--firmware", type=Path, action="append", default=[], help="C source; repeat as needed")
    return cli


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        profile = {}
        base = Path.cwd()
        if args.profile:
            profile = json.loads(project.read_text(args.profile))
            base = args.profile.resolve().parent
            if not isinstance(profile, dict):
                raise ValueError("Profile must be a JSON object.")
            for key in ("workspace", "pc_app", "ide"):
                if key in profile and not isinstance(profile[key], str):
                    raise ValueError(f"Profile {key} must be a path string.")
            targets = profile.get("targets", {})
            if not isinstance(targets, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in targets.items()):
                raise ValueError("Profile targets must map aliases to path strings.")

        def path_arg(key, required=False):
            value = getattr(args, key, None)
            if value:
                return expanded(value, Path.cwd())
            if profile.get(key):
                return expanded(profile[key], base)
            if required:
                raise ValueError(f"Supply --{key.replace('_', '-')} or profile.{key}.")
            return None

        def selected_project(requested=None):
            requested = requested if requested is not None else args.project
            value = profile.get("targets", {}).get(requested)
            if value is not None:
                if "workspace" not in profile:
                    raise ValueError("Profile target aliases require profile.workspace.")
                return expanded(value, expanded(profile["workspace"], base))
            return expanded(requested, Path.cwd())

        if args.action == "inventory":
            root = expanded(args.root, Path.cwd()) if args.root else path_arg("workspace", required=True)
            result = project.inventory(root)
        elif args.action == "inspect":
            result = project.inspect_project(selected_project())
        elif args.action == "doctor":
            result = project.doctor(path_arg("ide"), path_arg("pc_app"))
        elif args.action == "build-plan":
            result = project.build_plan(selected_project(), path_arg("ide", required=True),
                                        Path(args.workspace), args.configuration)
        elif args.action == "ioc-diff":
            result = project.ioc_diff(args.before, args.after, args.all_settings)
        elif args.action == "inventory-diff":
            result = compare.inventory_diff(args.before, args.after)
        elif args.action == "compare-projects":
            result = compare.project_diff(selected_project(args.before), selected_project(args.after),
                                          args.include_vendor, args.text_diff)
        elif args.action == "frame":
            spec = json.loads(project.read_text(args.spec))
            if args.operation == "verify":
                result = protocol.verify_vectors(spec, json.loads(project.read_text(args.vectors)))
                result.update(vectors_file=str(args.vectors.resolve()), vectors_sha256=project.digest(args.vectors))
            else:
                raw = (protocol.encode(spec, args.id, args.command, bytes.fromhex(args.payload))
                       if args.operation == "encode" else bytes.fromhex(args.hex))
                result = protocol.decode(spec, raw)
            result.update(spec_file=str(args.spec.resolve()), spec_sha256=project.digest(args.spec))
        else:
            result = protocol.contract(args.commands, args.firmware, args.enum_names)
        output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            # Exclusive create protects unrelated source files even when a path is mistyped.
            with args.output.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(output)
        else:
            print(output, end="")
        return 1 if result.get("errors") else 0
    except (OSError, ValueError, ET.ParseError, SyntaxError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
