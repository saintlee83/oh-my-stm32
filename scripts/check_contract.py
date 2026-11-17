"""Check real CLI transcripts against the published schema; development dependency: jsonschema."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from contract_samples import collect_samples


def main() -> int:
    schema_path = ROOT / ".agents/skills/stm32-workbench/references/result-v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    with tempfile.TemporaryDirectory() as directory:
        samples = collect_samples(Path(directory).resolve())
        for name, sample in samples.items():
            errors = list(validator.iter_errors(sample["document"]))
            if errors:
                raise ValueError(f"{name} violates the published contract: {errors[0].message}")
        # Verify that the schema rejects changes that would break consumers.
        invalid = []
        frame = samples["frame.encode"]["document"]
        invalid.append({**frame, "command": "16"})
        invalid.append({**frame, "schema_version": "2.0"})
        invalid.append({key: value for key, value in frame.items() if key != "operation"})
        invalid.append({**samples["build-plan"]["document"], "executed": True})
        invalid.append({**samples["inventory"]["document"], "projects": {}})
        invalid.append({**samples["input-error"]["document"], "error": []})
        missing_field = copy.deepcopy(samples["inspect"]["document"])
        del missing_field["configurations"][0]["linker_scripts"]
        invalid.append(missing_field)
        for document in invalid:
            if validator.is_valid(document):
                raise ValueError("The schema accepted a deliberately incompatible result.")
        validator.validate({**frame, "schema_version": "1.99", "future_field": {"enabled": True}})
    print(f"JSON contract: {len(samples)} transcripts accepted; {len(invalid)} incompatible results rejected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
