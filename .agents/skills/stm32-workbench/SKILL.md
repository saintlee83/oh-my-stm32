---
name: stm32-workbench
description: Inspect and change STM32 firmware and related host applications. Use for project selection, peripheral configuration, protocol integration, build preparation, bootloader work, and hardware diagnosis. Includes an offline CLI for CubeIDE metadata, source comparisons, and explicit byte-frame specifications.
---

# STM32 Workbench

Use the user's board, MCU, project, and requested outcome to define the work. Derive pin assignments, addresses, baud rates, command meanings, and host language from that target. The bundled CLI reads files and generates commands; firmware edits, builds, and hardware work follow the scope of the user's request.

## Establish the target

Read the target's `AGENTS.md` and build files. For CubeIDE projects, keep the absolute directory and `.project` name together. When several candidates exist, use `scripts/stm32_toolkit.py inventory --root PATH`, then `inspect --project PATH` to examine configurations, MCU settings, IOC files, and source evidence.

Select the linker from the active build configuration. A nearby `*_RAM.ld` file, a recent timestamp, or a deployment log does not establish the active memory map or source tree. Analysis may cover several candidates; edits and builds need an identified target.

For CMake/Make, Keil, and IAR projects, inspect their own target, toolchain, and linker settings. The CubeIDE metadata reader does not interpret those formats.

## Load the relevant guide

| Work | Reference | Key decision |
|---|---|---|
| Select or compare projects | [Project analysis](references/project-analysis.md) | Which target and observations support the change? |
| Change peripherals or timing | [Firmware](references/firmware.md) | How do IOC settings, generated code, initialization, and buffer ownership interact? |
| Change host/firmware communication | [Protocols](references/protocol.md) | What happens from encoding through transport, parsing, handling, and response? |
| Build, debug, or change a bootloader | [Build and debug](references/build-debug.md) | Which toolchain, linker, image, and memory regions are actually used? |
| Inspect diagnostic images or RAM | [Diagnostics](references/diagnostics.md) | Which image and observation method produced the evidence? |
| Run the bundled tools | [CLI reference](references/cli.md) | Which arguments, paths, result fields, and limits apply? |

## Make and verify the change

Before CubeMX regeneration, inspect manual edits both inside and outside `USER CODE` blocks. Preserve relevant project metadata, generated-code customizations, and HAL dependencies.

For concurrent firmware, establish buffer ownership across interrupts, DMA callbacks, RTOS tasks, and the main loop. Queueing, transmission completion, command acceptance, and completion of the requested operation are distinct events.

Start with the relevant existing checks. Protocol changes need independent wire bytes and failure cases; timing changes need units and boundary values; bootloader changes need image boundaries and recovery paths. Report static analysis, host tests, ARM compilation/linking, and hardware tests as separate evidence. Existing ELF files need their own provenance checks.

Analysis alone does not call for a hardware connection. When hardware work is requested, identify the board, probe, and image and proceed within the existing authorization. Account for timing changes caused by halting the CPU.

Keep full investigations in local reports. Shared examples, fixtures, and documentation use synthetic data rather than private project details. Finish with the changed files, checks and results, unresolved behavior, and target information needed to continue.
