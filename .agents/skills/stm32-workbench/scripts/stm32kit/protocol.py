"""User-defined byte envelopes and static command indexes; no transport or imports."""
from __future__ import annotations

import ast
from functools import reduce
from operator import xor
from pathlib import Path
import re

from .project import digest, read_text


SPEC_KEYS = frozenset({"name", "start_hex", "end_hex", "length_bytes", "length_counts",
                       "id_bytes", "command_bytes", "byteorder", "checksum", "checksum_scope"})


def validate_spec(spec: dict) -> dict:
    """Require an explicit layout: there is no default STM32 wire protocol."""
    if not isinstance(spec, dict) or set(spec) != SPEC_KEYS:
        raise ValueError(f"Frame spec must contain exactly: {', '.join(sorted(SPEC_KEYS))}.")
    if not isinstance(spec["name"], str) or not spec["name"].strip():
        raise ValueError("Frame spec name must be a nonempty string.")
    for key in ("start_hex", "end_hex"):
        if not isinstance(spec[key], str):
            raise ValueError(f"Frame spec {key} must be hex text (empty is allowed).")
        bytes.fromhex(spec[key])
    for key in ("length_bytes", "id_bytes", "command_bytes"):
        if type(spec[key]) is not int or spec[key] not in (0, 1, 2, 4):
            raise ValueError(f"Frame spec {key} must be 0, 1, 2 or 4.")
    choices = {"length_counts": ("frame", "payload"), "byteorder": ("big", "little"),
               "checksum": ("none", "sum8", "neg_sum8", "xor8"),
               "checksum_scope": ("body", "payload", "frame_prefix")}
    for key, values in choices.items():
        if spec[key] not in values:
            raise ValueError(f"Frame spec {key} must be one of {values}.")
    # Copy so the caller's object is never mutated.
    return dict(spec)


def _integer(value: int, size: int, byteorder: str, field: str) -> bytes:
    if type(value) is not int or not 0 <= value < 256 ** size:
        raise ValueError(f"{field} must fit {size} byte(s); an absent field requires 0.")
    return value.to_bytes(size, byteorder)


def _checksum(spec: dict, body: bytes, payload: bytes) -> bytes:
    if spec["checksum"] == "none":
        return b""
    data = {"body": body, "payload": payload,
            "frame_prefix": bytes.fromhex(spec["start_hex"]) + body}[spec["checksum_scope"]]
    value = (reduce(xor, data, 0) if spec["checksum"] == "xor8" else
             -sum(data) if spec["checksum"] == "neg_sum8" else sum(data))
    return bytes([value & 255])


def encode(spec: dict, dev_id: int = 0, command: int = 0, payload: bytes = b"") -> bytes:
    spec = validate_spec(spec)
    start, end = bytes.fromhex(spec["start_hex"]), bytes.fromhex(spec["end_hex"])
    overhead = (len(start) + len(end) + spec["length_bytes"] + spec["id_bytes"]
                + spec["command_bytes"] + (spec["checksum"] != "none"))
    length = len(payload) + overhead if spec["length_counts"] == "frame" else len(payload)
    size, order = spec["length_bytes"], spec["byteorder"]
    body = (_integer(length, size, order, "Length") if size else b"")
    body += (_integer(dev_id, spec["id_bytes"], order, "ID")
             + _integer(command, spec["command_bytes"], order, "Command") + payload)
    return start + body + _checksum(spec, body, payload) + end


def decode(spec: dict, raw: bytes) -> dict:
    spec = validate_spec(spec)
    start, end = bytes.fromhex(spec["start_hex"]), bytes.fromhex(spec["end_hex"])
    checksum_size = int(spec["checksum"] != "none")
    header_size = len(start) + spec["length_bytes"] + spec["id_bytes"] + spec["command_bytes"]
    if len(raw) < header_size + checksum_size + len(end):
        raise ValueError("Frame is shorter than the configured envelope.")
    if not raw.startswith(start) or not raw.endswith(end):
        raise ValueError("Frame markers do not match the spec.")
    cursor = len(start)

    def take(size):
        nonlocal cursor
        value = int.from_bytes(raw[cursor:cursor + size], spec["byteorder"])
        cursor += size
        return value

    declared = take(spec["length_bytes"])
    dev_id, command = take(spec["id_bytes"]), take(spec["command_bytes"])
    payload_end = len(raw) - len(end) - checksum_size
    payload = raw[cursor:payload_end]
    actual = len(raw) if spec["length_counts"] == "frame" else len(payload)
    if spec["length_bytes"] and declared != actual:
        raise ValueError(f"Length mismatch: declared {declared}, actual {actual}.")
    expected = _checksum(spec, raw[len(start):payload_end], payload)
    received = raw[payload_end:payload_end + checksum_size]
    if received != expected:
        raise ValueError(f"Checksum mismatch: received {received.hex()}, expected {expected.hex()}.")
    return {"protocol": spec["name"], "length": len(raw), "id": dev_id, "command": command,
            "payload_hex": payload.hex(" ").upper(), "checksum": received[0] if received else None,
            "hex": raw.hex(" ").upper()}


def verify_vectors(spec: dict, document: dict) -> dict:
    """Compare against independently supplied wire bytes without executing app code."""
    spec = validate_spec(spec)
    if (not isinstance(document, dict) or set(document) - {"vectors", "invalid_frames"}
            or not isinstance(document.get("vectors"), list) or not document["vectors"]
            or not isinstance(document.get("invalid_frames", []), list)):
        raise ValueError("Vectors must contain a nonempty vectors list and optional invalid_frames list.")
    errors = []
    for index, vector in enumerate(document["vectors"]):
        if not isinstance(vector, dict) or set(vector) != {"id", "command", "payload_hex", "frame_hex"}:
            raise ValueError("Each vector requires exactly id, command, payload_hex and frame_hex.")
        if not isinstance(vector["payload_hex"], str) or not isinstance(vector["frame_hex"], str):
            raise ValueError("Vector payload_hex and frame_hex must be hex strings.")
        payload, expected = bytes.fromhex(vector["payload_hex"]), bytes.fromhex(vector["frame_hex"])
        actual = encode(spec, vector["id"], vector["command"], payload)
        if actual != expected:
            errors.append({"vector": index, "error": "Encoded bytes differ from the supplied vector.",
                           "expected_hex": expected.hex(" ").upper(), "actual_hex": actual.hex(" ").upper()})
        try:
            parsed = decode(spec, expected)
            if ((parsed["id"], parsed["command"], bytes.fromhex(parsed["payload_hex"]))
                    != (vector["id"], vector["command"], payload)):
                errors.append({"vector": index, "error": "Decoded fields differ from the supplied vector."})
        except ValueError as exc:
            errors.append({"vector": index, "error": str(exc)})
    for index, raw in enumerate(document.get("invalid_frames", [])):
        if not isinstance(raw, str):
            raise ValueError("invalid_frames entries must be hex strings.")
        data = bytes.fromhex(raw)
        try:
            decode(spec, data)
        except ValueError:
            continue
        errors.append({"invalid_frame": index, "error": "Frame marked invalid was accepted."})
    return {"protocol": spec["name"], "vectors_checked": len(document["vectors"]),
            "invalid_frames_checked": len(document.get("invalid_frames", [])), "errors": errors,
            "hardware_access": False, "scope": "Envelope vectors only; command semantics and hardware are not checked."}


def _enum_sources(path: Path, selected: list[str]) -> dict:
    text = read_text(path)
    tree = ast.parse(text, filename=str(path))
    names = {"Enum", "IntEnum", "Flag", "IntFlag"}
    modules = {"enum"}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "enum":
            names.update(alias.asname or alias.name for alias in node.names if alias.name in names)
        elif isinstance(node, ast.Import):
            modules.update(alias.asname or alias.name for alias in node.names if alias.name == "enum")

    def enum_base(node):
        return ((isinstance(node, ast.Name) and node.id in names)
                or (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                    and node.value.id in modules and node.attr in {"Enum", "IntEnum", "Flag", "IntFlag"}))

    enums, unresolved = {}, []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if (node.name not in selected if selected else not any(enum_base(base) for base in node.bases)):
            continue
        members = []
        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                targets, value = stmt.targets, stmt.value
            elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
                targets, value = [stmt.target], stmt.value
            else:
                continue
            for target in targets:
                if not isinstance(target, ast.Name) or target.id.startswith("_"):
                    continue
                try:
                    number = ast.literal_eval(value)
                except (ValueError, TypeError):
                    number = None
                if type(number) is int:
                    members.append({"name": target.id, "value": number, "line": stmt.lineno})
                else:
                    unresolved.append({"enum": node.name, "name": target.id, "line": stmt.lineno})
        enums[node.name] = members
    return {"file": str(path.resolve()), "sha256": digest(path), "enums": enums,
            "unresolved_members": unresolved}


def contract(commands: list[Path], firmware: list[Path], enum_names: list[str] | None = None) -> dict:
    """Index explicit Python files via AST; never import the input application."""
    selected = enum_names or []
    command_sources = [_enum_sources(path, selected) for path in commands]
    found = {name for source in command_sources for name in source["enums"]}
    if not found:
        raise ValueError("No command enums found; use --enum NAME for a custom enum base.")
    if set(selected) - found:
        raise ValueError(f"Requested enums were not found: {sorted(set(selected) - found)}")
    sources = []
    for path in firmware:
        labels = []
        # Preserve line numbers when discarding comments. This remains a lexical index.
        source = re.sub(r"/\*.*?\*/|//[^\n]*", lambda m: "\n" * m[0].count("\n"), read_text(path), flags=re.S)
        for line_number, line in enumerate(source.splitlines(), 1):
            for match in re.finditer(r"\bcase\s+(0[xX][0-9a-fA-F]+|[0-9]+)[uUlL]*\s*:", line):
                literal = match[1]
                labels.append({"value": int(literal, 16 if literal.lower().startswith("0x") else 10),
                               "line": line_number})
        sources.append({"file": str(path.resolve()), "sha256": digest(path), "numeric_case_labels": labels})
    return {"command_sources": command_sources, "firmware_sources": sources,
            "limitations": ["Only top-level Python enums and literal integer members are resolved; other members are listed as unresolved.",
                            "C case labels are lexical hints and may belong to unrelated switches or inactive branches.",
                            "Compare direction, address, length, endianness, units and ACK behavior manually.",
                            "This report does not certify firmware/host compatibility."]}
