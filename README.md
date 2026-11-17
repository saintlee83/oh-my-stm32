<div align="center">

# oh-my-stm32

**Inspect firmware. Compare changes. Prepare the next build.**

An offline STM32 toolkit with structured JSON reports and a portable agent skill.

[![CLI version 0.3.0](https://img.shields.io/badge/CLI-v0.3.0-2563eb?style=flat-square)](.agents/skills/stm32-workbench/scripts/stm32kit/__init__.py)
[![Python 3.10 or newer](https://img.shields.io/badge/Python-3.10%2B-3776ab?style=flat-square)](#requirements)
[![Standard library only](https://img.shields.io/badge/runtime-standard_library-0f766e?style=flat-square)](#requirements)
[![MIT license](https://img.shields.io/badge/license-MIT-64748b?style=flat-square)](LICENSE)

[Quick start](#quick-start) · [Inside the kit](#inside-the-kit) · [Agent setup](#agent-setup) · [Workflows](#workflows) · [Validation](#validation)

</div>

---

Move from an unfamiliar firmware workspace to an identified project, a reviewable comparison, and a build plan. The kit combines a Python CLI for repeatable file analysis with task guides for firmware, host protocols, bootloaders, and debugging.

All CLI operations run locally. Project paths, board settings, and wire protocols come from your inputs. Tool execution and hardware sessions remain separate, explicit operations.

## Quick start

### 1. Get the source kit

```sh
git clone https://github.com/saintlee83/oh-my-stm32.git
cd oh-my-stm32
python stm32tool.py --version
```

Expected version: `0.3.0`. Use `python3` if that is your Python 3 command.

### 2. Run the bundled demo

Verify the synthetic protocol fixtures included in the kit. This works immediately after cloning, without a firmware project or connected board.

```sh
python stm32tool.py frame verify --spec .agents/skills/stm32-workbench/references/frame.example.json --vectors .agents/skills/stm32-workbench/references/frame-vectors.example.json
```

Key fields from the JSON result:

```json
{
  "protocol": "example-packet",
  "vectors_checked": 2,
  "invalid_frames_checked": 3,
  "errors": [],
  "hardware_access": false,
  "schema_version": "1.0",
  "toolkit_version": "0.3.0",
  "operation": "frame.verify"
}
```

### 3. Point it at your firmware

Replace the example paths with your own. Quote paths containing spaces.

```sh
python stm32tool.py inventory --root /path/to/firmware
python stm32tool.py inspect --project /path/to/firmware/BoardApp
```

`inventory` finds candidates and duplicate Eclipse names. `inspect` reads the selected project's configurations, IOC settings, linker declarations, source observations, and evidence hashes.

## Requirements

| Component | Requirement |
|---|---|
| CLI runtime | Python 3.10+; standard library only |
| Installation | Run directly from the checkout; no `pip install` step |
| Project discovery and build planning | STM32CubeIDE/Eclipse metadata |
| Frame verification | An explicit JSON specification and independent reference bytes |
| Build execution | A separately installed toolchain and a reviewed build plan |
| Hardware work | A separately configured board/probe session within the requested task |

For CMake/Make, Keil, and IAR projects, the agent guides cover inspection of native build files. Automatic metadata parsing and command generation target CubeIDE/Eclipse.

## Inside the kit

| Component | Location | Purpose |
|---|---|---|
| Repository CLI | [`stm32tool.py`](stm32tool.py) | One entry point for discovery, inspection, comparisons, and protocol checks |
| Portable agent skill | [`stm32-workbench/`](.agents/skills/stm32-workbench/) | Instructions, reference guides, and a bundled copy of the CLI |
| Workspace profile | [`stm32.example.json`](profiles/stm32.example.json) | Reusable roots, tool locations, and project aliases |
| Protocol demo | [Specification](.agents/skills/stm32-workbench/references/frame.example.json) · [Reference vectors](.agents/skills/stm32-workbench/references/frame-vectors.example.json) | A runnable example with valid and invalid frames |
| Regression suite | [`tests/`](tests/) | Synthetic fixtures for project, comparison, protocol, and CLI behavior |
| Verification record | [`docs/validation.md`](docs/validation.md) | Recorded environments, results, coverage, and limits |
| JSON result contract | [Schema](.agents/skills/stm32-workbench/references/result-v1.schema.json) · [Compatibility policy](.agents/skills/stm32-workbench/references/output-contract.md) | Versioned output for automation consumers |
| Build verification | [`verify_cubeide.py`](scripts/verify_cubeide.py) | Explicit compilation of a copied synthetic fixture with an installed CubeIDE |

The complete `.agents/skills/stm32-workbench/` folder also works independently of the repository entry point.

## Agent setup

Copy the complete skill folder to `<your-workspace>/.agents/skills/stm32-workbench/`, or give the agent the path to its [`SKILL.md`](.agents/skills/stm32-workbench/SKILL.md). Keep `scripts/` and `references/` with it.

Start with a concrete task:

```text
Use $stm32-workbench to inspect /path/to/firmware/BoardApp.
Identify the active build configuration, pin initialization, and host
command handling. List the files and checks needed for my requested change.
```

The copied skill includes its own CLI entry point:

```sh
python /path/to/stm32-workbench/scripts/stm32_toolkit.py --help
```

## Workflows

<details open>
<summary><strong>Inspect a workspace with reusable project aliases</strong></summary>

Copy [the example profile](profiles/stm32.example.json) to `profiles/workspace.local.json`. Set `workspace`, `ide`, `pc_app`, and `targets` for your environment.

```sh
python stm32tool.py --profile profiles/workspace.local.json inventory
python stm32tool.py --profile profiles/workspace.local.json inspect --project app
```

Profile roots resolve relative to the profile file; target aliases resolve relative to its `workspace`. Identify a target by both its exact directory and Eclipse project name. Check configuration-specific linker selection and inspection warnings before editing.

</details>

<details>
<summary><strong>Compare a baseline, a variant, or a fresh inventory</strong></summary>

```sh
python stm32tool.py compare-projects --before /path/to/baseline --after /path/to/variant --text-diff
python stm32tool.py ioc-diff --before /path/to/baseline/board.ioc --after /path/to/variant/board.ioc
python stm32tool.py inventory-diff --before reports/inventory-before.json --after reports/inventory-after.json
```

Project comparisons report raw SHA-256 differences with optional text previews. Add `--include-vendor` for Drivers and Middlewares, or `--all-settings` to compare every IOC key.

Collect inventories with the same scope and exclusions. An incomplete scan reports unmatched entries as observations; it cannot confirm additions or deletions. Source comparison excludes linked resources, binary images, documentation, and common build-output directories. See the [CLI reference](.agents/skills/stm32-workbench/references/cli.md) for the exact scope.

</details>

<details>
<summary><strong>Locate tools and prepare a CubeIDE build</strong></summary>

```sh
python stm32tool.py doctor --ide /path/to/STM32CubeIDE
python stm32tool.py build-plan --project /path/to/firmware/BoardApp --ide /path/to/launcher --workspace .build-workspaces/app --configuration Debug
```

`doctor` discovers tool files without running them. `build-plan` returns argv plus PowerShell and POSIX commands for the selected configuration.

Choose a new or empty build workspace separate from the source project. Executing the generated command can write outputs and run hooks in the imported source directory. Prepare a project copy when source isolation matters, and review linked resources and dependencies before execution.

</details>

<details>
<summary><strong>Inspect host commands and check protocol bytes</strong></summary>

```sh
python stm32tool.py contract --commands /path/to/host/commands.py --firmware /path/to/firmware/parser.c
python stm32tool.py frame encode --spec .agents/skills/stm32-workbench/references/frame.example.json --id 7 --command 0x10 --payload "01 02 03"
```

`contract` indexes Python enums and numeric C case locations without importing the host application. `frame encode`, `decode`, and `verify` require `--spec`; there is no built-in STM32 application protocol.

The codec supports a fixed byte envelope with configurable integer fields and simple checksums. Use independently established wire bytes for verification. Stream reassembly, escaping, CRC, and application response semantics require the project's own implementation and tests.

</details>

## Output contract

Commands return JSON to stdout. Add `--output NEW_FILE` before the command to save a report; create its parent directory first. Existing files are never overwritten.

JSON results and caught runtime errors include `schema_version`, `toolkit_version`, and `operation`. Existing fields stay at the top level, including the numeric wire `command` in frame results. See the [output contract](.agents/skills/stm32-workbench/references/output-contract.md) for compatibility rules and the published schema.

```sh
python stm32tool.py --output reports/inventory-first.json inventory --root /path/to/firmware
```

| Exit code | Meaning |
|---|---|
| `0` | Completed without reported errors |
| `1` | Partial results or a reference-vector mismatch; inspect `errors` |
| `2` | Invalid input or a file-access failure |

Argument-parser errors and help use ordinary CLI text. Missing tools in `doctor.missing` do not cause a failing exit code.

Keep local reports in git-ignored `reports/` and personal paths in `profiles/*.local.json`. Shared examples and tests use synthetic data.

## Validation

**59 tests passed on each of five Python versions**, from 3.10 through 3.14, on Windows. A separate real CubeIDE smoke run compiled and linked both Debug and Release. The [validation record](docs/validation.md) records exact versions, artifact hashes, and scope.

| Check | Recorded result |
|---|---|
| Regression suite | 59 passed per interpreter on Windows; Python 3.10, 3.11, 3.12, 3.13, and 3.14 |
| Standalone skill | Two reference frames matched; three invalid frames rejected |
| JSON result contract | 16 CLI transcripts accepted; seven incompatible samples rejected |
| Real CubeIDE build | Debug and Release produced ARM ELF and map files; original fixture hashes unchanged |
| CI configuration | 15 jobs across Ubuntu, Windows, macOS, and Python 3.10–3.14 |

Run the suite from the repository root:

```sh
python -m unittest discover -s tests -v
```

The [CI workflow](.github/workflows/ci.yml) runs the suite, standalone check, and schema validation. Configured matrix jobs are separate from recorded execution results. The local CubeIDE run validates the synthetic fixture; board operation, flashing, serial communication, and ST-LINK remain untested.

See [development and build verification](docs/development.md) to reproduce the checks or run the explicit CubeIDE harness. The CLI's `build-plan` command continues to generate commands without executing them.

## Reference library

| Guide | Coverage |
|---|---|
| [Project analysis](.agents/skills/stm32-workbench/references/project-analysis.md) | Target selection, fresh inventories, variant comparisons, and evidence |
| [Firmware](.agents/skills/stm32-workbench/references/firmware.md) | CubeMX, initialization, clocks, interrupts, DMA, and RTOS |
| [Protocols](.agents/skills/stm32-workbench/references/protocol.md) | Host contracts, frame specifications, reference vectors, and failure cases |
| [Build and debug](.agents/skills/stm32-workbench/references/build-debug.md) | Toolchains, source isolation, memory maps, bootloaders, and ST-LINK |
| [Diagnostics](.agents/skills/stm32-workbench/references/diagnostics.md) | Diagnostic images, RAM layouts, and observation methods |
| [CLI reference](.agents/skills/stm32-workbench/references/cli.md) | Arguments, path resolution, comparison scope, and exit behavior |

---

Released under the [MIT License](LICENSE). Copyright © 2026 Saint Lee.
