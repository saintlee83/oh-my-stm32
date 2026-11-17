# CLI reference

Run `python stm32tool.py` from the repository root. With a standalone copy of the skill, run `python PATH/scripts/stm32_toolkit.py`. Both entry points use the same Python 3.10+ standard-library implementation.

```text
python stm32tool.py [--profile JSON] [--output NEW_JSON_FILE] COMMAND ...
```

Global options precede the command. Use `--help` on the entry point or a subcommand for its argument list.

## Results and exit codes

Successful command results are JSON on stdout, or in the file named by `--output`. The output file is created exclusively: its parent directory must exist, and an existing file is never overwritten. Input and file-access errors are returned as a JSON `error` on stderr. Argument-parser errors and help use ordinary CLI text.

Since toolkit 0.3.0, JSON results and caught runtime errors include `schema_version`, `toolkit_version`, and `operation`. Existing result fields are preserved. Read the [output contract](output-contract.md) for the schema, compatibility policy, and legacy inventory support.

| Code | Meaning |
|---|---|
| `0` | The operation returned no entries in its `errors` list |
| `1` | The result contains errors, such as an incomplete scan or a reference-vector mismatch |
| `2` | Invalid input, malformed source/metadata, or a file-access failure prevented completion |

Inspect the result as well as the exit code. For example, `doctor.missing` reports absent tools without a failing exit code, and inspection warnings can accompany a successful result.

## Commands

| Command | Inputs | Result |
|---|---|---|
| `inventory` | `--root PATH`, or `workspace` from the profile | Eclipse projects, names, configurations, MCU identifiers, IOC files, duplicate names, skips, and errors |
| `inspect` | `--project PATH_OR_ALIAS` | Build settings, IOC data, linker declarations, source observations, warnings, and evidence hashes |
| `doctor` | Optional `--ide PATH` and `--pc-app PATH`, with profile fallbacks | Tool candidates, missing/ambiguous tools, host manifests, and Python environment paths |
| `build-plan` | `--project`, `--workspace`, and `--ide` or profile `ide`; optional `--configuration` (default `Debug`) | Selected configuration, argv, PowerShell and POSIX commands, and effects if executed |
| `ioc-diff` | `--before FILE --after FILE`; optional `--all-settings` | Changed pin, MCU, RCC, and NVIC keys; all keys when requested |
| `inventory-diff` | `--before JSON --after JSON` | Project presence and metadata changes matched by relative path |
| `compare-projects` | `--before PATH_OR_ALIAS --after PATH_OR_ALIAS`; optional `--include-vendor` and `--text-diff` | File changes, raw SHA-256 hashes, optional text previews, skips, and completeness |
| `frame encode` | `--spec JSON`; optional `--id`, `--command`, and `--payload HEX` | Encoded hex and decoded fields; ID and command default to zero, payload to empty |
| `frame decode` | `--spec JSON HEX` | Fields from one complete frame after configured marker, length, and checksum checks |
| `frame verify` | `--spec JSON --vectors JSON` | Agreement with independent reference bytes and rejection of supplied invalid frames |
| `contract` | One or more `--commands PYTHON_FILE`; optional repeated `--enum NAME` and `--firmware C_FILE` | Python enum members, unresolved members, numeric C case locations, and source hashes |

## Profiles and paths

A profile names reusable roots and exact project aliases:

```json
{
  "workspace": "../firmware",
  "pc_app": "../host-app",
  "ide": "../tools/STM32CubeIDE",
  "targets": {
    "app": "BoardApp",
    "bootloader": "BoardBootloader",
    "variant": "BoardAppVariant"
  }
}
```

Keep personal profiles in `profiles/*.local.json`. Replace the example paths with your own.

| Path source | Resolution |
|---|---|
| Profile `workspace`, `pc_app`, `ide` | Relative to the profile file's parent |
| Profile target alias | Relative to profile `workspace`, which is required for aliases |
| CLI `--root`, `--ide`, `--pc-app`, or a direct project path | Relative to the current working directory; overrides the corresponding profile root where applicable |
| Other file arguments and build `--workspace` | Filesystem paths relative to the current working directory |

The root and project-path resolver expands `~` and OS environment variables. File arguments such as `--spec`, `--vectors`, and `--output` do not use that resolver; pass resolved paths or let the shell expand them.

Aliases select directories only. They do not identify a deployment target or resolve ambiguity between similarly named projects.

## Discovery and build planning

`doctor` searches PATH and, when supplied, the IDE installation tree. It recognizes Windows executable names and names without extensions. Tool keys use names without extensions. It discovers files without running them or checking tool versions, executable permissions, or OS compatibility.

`build-plan --ide` accepts an explicit launcher file or an installation directory with one recognized launcher. If discovery finds none or several, supply the exact file. The requested configuration must exist and have a unique name. The build workspace must be new or empty and separate from the project, its descendants, and its ancestors.

The generated plan imports the selected project and uses its Eclipse name. Referenced projects require separate preparation. Review build hooks, linked resources, and the plan's `effects_if_executed` before running it. See [build and debug](build-debug.md) for source isolation.

## Compare investigations

Create `reports/` before saving results:

```text
python stm32tool.py --profile profiles/workspace.local.json --output reports/inventory-next.json inventory
python stm32tool.py inventory-diff --before reports/inventory-before.json --after reports/inventory-next.json
python stm32tool.py --profile profiles/workspace.local.json compare-projects --before app --after variant --include-vendor --text-diff
```

Collect inventories with the same root scope and exclusions. `inventory-diff` matches relative paths, so moving the entire root does not itself count as a change. If either report has read errors, `comparison_complete` is false and unmatched entries become `newly_observed` or `unobserved_after`. It does not detect source-only changes or establish renames.

`compare-projects` includes C/C++/assembly, GNU linker scripts, IOC and launch files, Eclipse project metadata, and supported files in `.settings`. It excludes common build-output directories, documentation, binary images, and linked resources. `--include-vendor` adds Drivers and Middlewares. Compare CMake, Keil, IAR, and other files outside this scope separately.

Hashes describe raw bytes. Optional UTF-8 previews normalize line endings, omit files larger than 1 MiB, and cap each diff at 200 lines with a truncation flag. Equal normalized text can still have different hashes. Read failures make the comparison incomplete; a missing file during a partial scan is not a confirmed deletion.

## Interpretation limits

`inspect` collects selected vector/application-address and version macros plus HAL baud assignments from C and header files under `Core/`. These are textual observations. It does not preprocess branches, evaluate arbitrary linker expressions, inspect other source layouts comprehensively, or establish ELF provenance. Listed linker files may be inactive; check the selected configuration.

For frame schemas and command-index limitations, read [protocols](protocol.md). Since version 0.2, `frame` requires an explicit `--spec`, and `contract` accepts source files through `--commands`. Use JSON reference vectors with `frame verify` instead of importing an external application.
