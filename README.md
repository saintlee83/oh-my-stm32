# oh-my-stm32

An offline toolkit for agents working with STM32 firmware and host applications. Use it to identify projects, compare source and configuration files, prepare CubeIDE build commands, and check byte frames against a supplied protocol specification.

The CLI runs on Python 3.10+ with the standard library. It reads local files and returns JSON; it does not run project code, start build tools, or connect to hardware. Project paths, board settings, and protocol definitions come from your inputs.

## Inspect a project

Run these commands from the repository root, replacing the example paths with your own:

```text
python stm32tool.py inventory --root /path/to/firmware
python stm32tool.py inspect --project /path/to/firmware/BoardApp
```

Start with `inventory` when several projects or archived copies share a workspace. It reports Eclipse names, relative paths, build configurations, duplicate names, and read errors. Use an exact project directory for `inspect`, then check the configuration's selected linker script and any warnings before making changes.

For repeated work, copy the [example profile](profiles/stm32.example.json) to `profiles/workspace.local.json` and set `workspace`, `ide`, `pc_app`, and `targets`:

```text
python stm32tool.py --profile profiles/workspace.local.json inventory
python stm32tool.py --profile profiles/workspace.local.json inspect --project app
```

Profile root paths resolve relative to the profile file. Target aliases resolve relative to its `workspace`. Put global options such as `--profile` and `--output` before the command.

## Choose the next operation

| Task | Command | What it establishes |
|---|---|---|
| Find projects and inspect configuration | `inventory`, `inspect` | CubeIDE/Eclipse metadata, IOC settings, linker declarations, selected source observations, and file hashes |
| Compare saved project lists | `inventory-diff` | Changes to project presence and metadata, matched by relative path |
| Compare firmware variants | `compare-projects` | File changes and SHA-256 hashes within the supported source and settings scope |
| Compare CubeMX settings | `ioc-diff` | Pin, MCU, RCC, and NVIC changes, or all keys with `--all-settings` |
| Find tools and prepare a build | `doctor`, `build-plan` | Tool locations and a headless command to review and run separately |
| Locate command definitions | `contract` | Python enum members and numeric C case labels, read without executing the inputs |
| Check a byte envelope | `frame encode/decode/verify` | Encoding, decoding, and reference-vector checks for an explicit JSON specification |

```text
python stm32tool.py compare-projects --before /path/to/baseline --after /path/to/variant --text-diff
python stm32tool.py ioc-diff --before /path/to/baseline/board.ioc --after /path/to/variant/board.ioc
python stm32tool.py doctor --ide /path/to/STM32CubeIDE
python stm32tool.py build-plan --project /path/to/firmware/BoardApp --ide /path/to/launcher --workspace .build-workspaces/app --configuration Debug
```

A build plan requires a new or empty workspace separate from the source project. Its JSON includes argument lists and PowerShell/POSIX commands. Executing a generated command can write build outputs and run project hooks in the imported source directory; use a prepared copy when source isolation matters.

## Verify a protocol

There is no built-in STM32 application protocol. Every `frame` operation requires `--spec`. The bundled specification and vectors are synthetic examples:

```text
python stm32tool.py frame encode --spec .agents/skills/stm32-workbench/references/frame.example.json --id 7 --command 0x10 --payload "01 02 03"
python stm32tool.py frame verify --spec .agents/skills/stm32-workbench/references/frame.example.json --vectors .agents/skills/stm32-workbench/references/frame-vectors.example.json
python stm32tool.py contract --commands /path/to/host/commands.py --firmware /path/to/firmware/parser.c
```

Supply independently established wire bytes for real verification. See the [protocol guide](.agents/skills/stm32-workbench/references/protocol.md) for the schema, supported checksums, and boundaries of these checks.

## Use the agent skill

Start with [STM32 Workbench](.agents/skills/stm32-workbench/SKILL.md):

> Use $stm32-workbench to inspect the selected project's build configuration, pin initialization, and host command handling. Identify the files and checks needed for the requested change.

To use it in another workspace, copy the complete `.agents/skills/stm32-workbench` directory into that workspace's skill directory, or provide the path to `SKILL.md`. Its CLI and references are self-contained. From a copied skill, run `python PATH/scripts/stm32_toolkit.py`.

| Guide | Read it for |
|---|---|
| [Project analysis](.agents/skills/stm32-workbench/references/project-analysis.md) | Target selection, fresh inventories, and evidence from multiple variants |
| [Firmware](.agents/skills/stm32-workbench/references/firmware.md) | CubeMX, initialization, clocks, interrupts, DMA, and RTOS changes |
| [Protocols](.agents/skills/stm32-workbench/references/protocol.md) | Host/firmware contracts, frame specifications, and reference vectors |
| [Build and debug](.agents/skills/stm32-workbench/references/build-debug.md) | Toolchains, build isolation, memory layout, bootloaders, and ST-LINK |
| [Diagnostics](.agents/skills/stm32-workbench/references/diagnostics.md) | Diagnostic images, RAM layouts, and the limits of each observation |
| [CLI reference](.agents/skills/stm32-workbench/references/cli.md) | Arguments, path resolution, output fields, and exit codes |

The metadata reader and build planner support CubeIDE/Eclipse projects. For CMake/Make, Keil, or IAR projects, the skill guides inspection of the native build files. Static reports do not establish build success, firmware provenance, or device behavior.

## Reports and development

Use `--output NEW_FILE` to save JSON. Create the parent directory first; the CLI refuses to overwrite an existing file. Exit code `0` means the operation completed without reported errors, `1` means a partial result or vector mismatch, and `2` means invalid input or a read/write error. Missing tools listed by `doctor` do not cause a failing exit code.

Keep full inventories and analysis reports in git-ignored `reports/`, and personal paths in `profiles/*.local.json`. Shared examples and tests use synthetic data.

```text
python -m unittest discover -s tests -v
```

The [validation record](docs/validation.md) describes the checks performed and their limits.
