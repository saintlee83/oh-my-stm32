# Working on oh-my-stm32

This repository contains an offline analysis toolkit and a portable agent skill. Firmware and host application paths supplied to the toolkit are inputs, outside the scope of toolkit maintenance.

## Repository conventions

- Keep the runtime on the Python 3.10+ standard library. Preserve JSON results, explicit error reporting, and documented exit codes.
- Write documentation, instructions, examples, and messages in English. Preserve Unicode path support in the implementation and tests.
- Read and write text as UTF-8. If an input uses another encoding, identify it before proposing a separate conversion.
- Keep examples and fixtures synthetic. Do not add real organization, product, or customer identifiers, project paths, pin maps, memory layouts, private command definitions, or analysis snapshots.
- Store full local reports in `reports/` and personal profiles in `profiles/*.local.json`. Shared evidence should use relative paths, hashes, and observation times.

## Behavior to preserve

- `build-plan` generates commands only. Toolkit changes must not introduce implicit tool execution, flashing, or serial access.
- Read command definitions statically. Do not import a host application to inspect or verify its protocol.
- Identify CubeIDE targets by both absolute directory and `.project` name. Folder names, timestamps, and deployment history are insufficient to select the active target.
- For follow-up investigations, collect a fresh `inventory`, compare it with the previous report using `inventory-diff`, then use `compare-projects` for relevant candidates. Retain earlier observations separately from new evidence.

For work on a user's STM32 project, start with [.agents/skills/stm32-workbench/SKILL.md](.agents/skills/stm32-workbench/SKILL.md) and load the references needed for that task.

## Validation

Run `python -m unittest discover -s tests -v` and `git diff --check`. For a supplied wire protocol, compare independent reference bytes with `frame verify --spec SPEC --vectors VECTORS`. Report static checks, host tests, compilation, and hardware observations separately.
