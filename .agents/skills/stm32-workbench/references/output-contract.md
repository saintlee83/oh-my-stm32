# JSON result contract

Toolkit 0.3.0 introduces schema version `1.0` for CLI JSON results. The contract is described by the bundled [JSON Schema](result-v1.schema.json). It uses [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12) and resolves all references within the file, so validation needs no network access.

## Common metadata

Every successful result, partial result, and caught runtime error has these top-level fields:

| Field | Meaning |
|---|---|
| `schema_version` | Result contract version as `MAJOR.MINOR`, currently `1.0` |
| `toolkit_version` | CLI implementation version, currently `0.3.0` |
| `operation` | CLI operation, such as `inventory`, `build-plan`, or `frame.verify` |

Existing command-specific fields remain at the top level. In particular, the `command` field in frame results remains the numeric wire command; `operation` identifies the CLI action.

A caught runtime error on stderr has this shape:

```json
{
  "error": "Directory does not exist: /example/missing",
  "schema_version": "1.0",
  "toolkit_version": "0.3.0",
  "operation": "inspect"
}
```

Global `--output` writes the same result envelope to a new file. Help, `--version`, and argument-parser diagnostics remain ordinary CLI text. The contract does not version the internal Python helper functions or the separate development build-verification report.

## Compatibility policy

- A major version changes when existing fields are removed or renamed, their types or meanings change, or existing status values change incompatibly.
- A minor version may add optional fields or new operations. Existing consumers should ignore unknown fields and accept newer minor versions of the major they support. A consumer needs updated operation-specific support before using a new operation.
- A toolkit version identifies the software release independently of the JSON contract. Bug fixes can change result values without changing the schema when the documented meaning stays the same.
- Required fields and their types for existing operations remain stable within a major version. Human-readable notes, warning/error wording, object key order, and discovery ordering are not a stable parsing interface.
- Consumers must check the process exit code and `errors` when present. Version metadata does not make a partial scan complete or establish hardware compatibility.

`inventory-diff` accepts legacy reports without `schema_version` as well as versioned inventory reports from schema major 1. It ignores additive fields, rejects malformed or unsupported major versions, and requires `operation: "inventory"` in versioned inputs.

## Automated checks

The repository's `scripts/check_contract.py` validates generated CLI transcripts for all operations, partial results, and runtime errors. It also checks that incompatible field types, missing required fields, and unsupported majors are rejected while additive fields and later minor versions remain valid.

The checker uses `jsonschema` as a development dependency. The CLI itself remains standard-library-only. The schema travels with the standalone skill under `references/result-v1.schema.json`.
