from __future__ import annotations

import contextlib
import io
import itertools
import json
from pathlib import Path
import random
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / ".agents/skills/stm32-workbench/scripts"
sys.path.insert(0, str(SCRIPTS))
from stm32kit import protocol
from stm32kit.cli import main


BASE = {"name": "test-packet", "start_hex": "AA 55", "end_hex": "EE", "length_bytes": 1,
        "length_counts": "payload", "id_bytes": 1, "command_bytes": 1, "byteorder": "big",
        "checksum": "xor8", "checksum_scope": "body"}


class ProtocolTests(unittest.TestCase):
    def test_independent_golden_bytes_for_checksum_algorithms_and_scopes(self):
        for algorithm, scope, expected in (("none", "body", ""), ("sum8", "body", "19"),
                                            ("neg_sum8", "body", "E7"), ("xor8", "body", "15"),
                                            ("sum8", "payload", "03"), ("sum8", "frame_prefix", "18"),
                                            ("xor8", "frame_prefix", "EA")):
            with self.subTest(algorithm=algorithm, scope=scope):
                spec = {**BASE, "checksum": algorithm, "checksum_scope": scope}
                raw = protocol.encode(spec, 4, 16, b"\x01\x02")
                self.assertEqual(raw, bytes.fromhex("AA 55 02 04 10 01 02 " + expected + " EE"))
                parsed = protocol.decode(spec, raw)
                self.assertEqual((parsed["id"], parsed["command"], parsed["payload_hex"]), (4, 16, "01 02"))

    def test_multibyte_little_endian_fields_and_total_frame_length(self):
        spec = {**BASE, "start_hex": "", "end_hex": "", "length_bytes": 2, "length_counts": "frame",
                "id_bytes": 2, "command_bytes": 2, "byteorder": "little", "checksum": "sum8"}
        golden = bytes.fromhex("09 00 34 12 CD AB 41 42 4A")
        self.assertEqual(protocol.encode(spec, 0x1234, 0xABCD, b"AB"), golden)
        self.assertEqual(protocol.decode(spec, golden)["command"], 0xABCD)

    def test_configured_field_widths_orders_and_length_modes_roundtrip(self):
        rng = random.Random(21)
        for width, order, counts, checksum in itertools.product((0, 1, 2, 4), ("big", "little"),
                                                               ("frame", "payload"), ("none", "xor8")):
            spec = {**BASE, "length_bytes": width, "id_bytes": width, "command_bytes": width,
                    "byteorder": order, "length_counts": counts, "checksum": checksum}
            value = 256 ** width - 1 if width else 0
            payload = bytes(rng.randrange(256) for _ in range(23))
            raw = protocol.encode(spec, value, value, payload)
            result = protocol.decode(spec, raw)
            self.assertEqual((result["id"], result["command"], bytes.fromhex(result["payload_hex"])),
                             (value, value, payload))

    def test_every_one_byte_payload_length_with_embedded_markers(self):
        for size in range(256):
            payload = (b"\xAA\x55\xEE\x00" * 64)[:size]
            raw = protocol.encode(BASE, 255, 0, payload)
            self.assertEqual(raw[2], size)
            self.assertEqual(bytes.fromhex(protocol.decode(BASE, raw)["payload_hex"]), payload)

    def test_overflow_and_absent_fields_are_not_wrapped(self):
        for ident, command in ((-1, 0), (256, 0), (0, -1), (0, 256), (True, 0)):
            with self.assertRaises(ValueError):
                protocol.encode(BASE, ident, command)
        with self.assertRaises(ValueError):
            protocol.encode(BASE, payload=b"x" * 256)
        spec = {**BASE, "length_counts": "frame"}
        self.assertEqual(len(protocol.encode(spec, payload=b"x" * 248)), 255)
        with self.assertRaises(ValueError):
            protocol.encode(spec, payload=b"x" * 249)
        with self.assertRaises(ValueError):
            protocol.encode({**BASE, "id_bytes": 0}, 1)

    def test_no_markers_length_fields_or_checksum(self):
        spec = {**BASE, "start_hex": "", "end_hex": "", "length_bytes": 0,
                "id_bytes": 0, "command_bytes": 0, "checksum": "none"}
        for payload in (b"", b"data"):
            self.assertEqual(protocol.encode(spec, payload=payload), payload)
            self.assertEqual(bytes.fromhex(protocol.decode(spec, payload)["payload_hex"]), payload)

    def test_malformed_markers_lengths_checksums_and_concatenated_frames(self):
        valid = bytes.fromhex("AA 55 02 04 10 01 02 15 EE")
        invalid = [b"", valid[:-1], b"\x00" + valid[1:], valid[:-1] + b"\x00",
                   valid[:2] + b"\x01" + valid[3:], valid[:-2] + b"\x00\xEE", valid + valid]
        for raw in invalid:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                protocol.decode(BASE, raw)

    def test_incomplete_unknown_and_invalid_specs_fail_explicitly(self):
        bad = [None, [], {}, {**BASE, "typo": 1}]
        for key, value in (("name", ""), ("start_hex", "GG"), ("end_hex", 2),
                           ("length_bytes", -1), ("id_bytes", True), ("command_bytes", 3),
                           ("length_counts", "guess"), ("byteorder", "native"),
                           ("checksum", "unknown"), ("checksum_scope", [])):
            bad.append({**BASE, key: value})
        for spec in bad:
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                protocol.encode(spec)

    def test_vectors_detect_inconsistent_encoders_and_invalid_frame_expectations(self):
        vector = {"id": 4, "command": 16, "payload_hex": "01 02",
                  "frame_hex": "AA 55 02 04 10 01 02 15 EE"}
        document = {"vectors": [vector], "invalid_frames": ["", "AA 55 02 04 10 01 02 00 EE"]}
        self.assertEqual(protocol.verify_vectors(BASE, document)["errors"], [])
        mismatch = {**vector, "command": 17}
        self.assertTrue(protocol.verify_vectors(BASE, {"vectors": [mismatch]})["errors"])
        accepted = {"vectors": [vector], "invalid_frames": [vector["frame_hex"]]}
        self.assertIn("invalid_frame", protocol.verify_vectors(BASE, accepted)["errors"][0])
        for value in ({}, {"vectors": []}, {"vectors": [None]}, {"vectors": [vector], "invalid_frames": [1]}):
            with self.assertRaises(ValueError):
                protocol.verify_vectors(BASE, value)


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def source(self, name, contents):
        path = self.root / name
        path.write_text(contents, encoding="utf-8")
        return path

    def test_sources_in_any_package_are_indexed_without_execution(self):
        commands = self.source("requests.py", "raise RuntimeError('must not execute')\n"
                               "from enum import IntEnum as Code\nclass Request(Code):\n"
                               "    SET = 0x10\n    NEGATIVE: int = -1\n    NEXT = auto()\n    ALIAS = SET\n")
        firmware = self.source("parser.c", "/* case 999: */\ncase 0x10: break;\ncase 17U: break;\n")
        before = {path.name: path.read_bytes() for path in self.root.iterdir()}
        result = protocol.contract([commands], [firmware])
        source = result["command_sources"][0]
        self.assertEqual([m["value"] for m in source["enums"]["Request"]], [16, -1])
        self.assertEqual([m["name"] for m in source["unresolved_members"]], ["NEXT", "ALIAS"])
        self.assertEqual(result["firmware_sources"][0]["numeric_case_labels"],
                         [{"value": 16, "line": 2}, {"value": 17, "line": 3}])
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.root.iterdir()})

    def test_multiple_files_enum_module_aliases_and_custom_bases(self):
        a = self.source("a.py", "import enum as e\nclass Codes(e.IntFlag):\n    ENABLE = 1\n")
        b = self.source("b.py", "class Codes(CustomBase):\n    READY = 2\nclass Other(IntEnum):\n    NONE = 0\n")
        default = protocol.contract([a, b], [])
        self.assertEqual(set(default["command_sources"][1]["enums"]), {"Other"})
        selected = protocol.contract([a, b], [], ["Codes"])
        self.assertEqual([s["enums"]["Codes"][0]["value"] for s in selected["command_sources"]], [1, 2])
        with self.assertRaisesRegex(ValueError, "not found"):
            protocol.contract([a], [], ["Codes", "Missing"])

    def test_ordinary_classes_are_not_guessed_to_be_command_enums(self):
        path = self.source("config.py", "class Config:\n    SIZE = 2\n")
        with self.assertRaisesRegex(ValueError, "No command enums"):
            protocol.contract([path], [])
        self.assertEqual(protocol.contract([path], [], ["Config"])["command_sources"][0]["enums"]["Config"][0]["value"], 2)


class ProtocolCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.spec = self.root / "spec.json"
        self.spec.write_text(json.dumps(BASE), encoding="utf-8")

    def run_cli(self, args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = main(args)
        return status, out.getvalue(), err.getvalue()

    def test_cli_reports_vector_mismatch_with_status_one(self):
        vectors = self.root / "vectors.json"
        vectors.write_text(json.dumps({"vectors": [{"id": 4, "command": 16, "payload_hex": "01 02",
                                                   "frame_hex": "AA 55 02 04 10 01 02 00 EE"}]}), encoding="utf-8")
        status, out, err = self.run_cli(["frame", "verify", "--spec", str(self.spec), "--vectors", str(vectors)])
        self.assertEqual((status, err), (1, ""))
        self.assertTrue(json.loads(out)["errors"])
        self.assertEqual(len(json.loads(out)["spec_sha256"]), 64)

    def test_invalid_spec_is_json_input_error(self):
        self.spec.write_text('[]', encoding="utf-8")
        status, out, err = self.run_cli(["frame", "encode", "--spec", str(self.spec)])
        self.assertEqual((status, out), (2, ""))
        self.assertIn("error", json.loads(err))

    def test_explicit_contract_source_from_cli(self):
        path = self.root / "commands.py"
        path.write_text("class Message(CustomBase):\n    READY = 1\n", encoding="utf-8")
        status, out, err = self.run_cli(["contract", "--commands", str(path), "--enum", "Message"])
        self.assertEqual((status, err), (0, ""))
        self.assertEqual(json.loads(out)["command_sources"][0]["enums"]["Message"][0]["value"], 1)


if __name__ == "__main__":
    unittest.main()
