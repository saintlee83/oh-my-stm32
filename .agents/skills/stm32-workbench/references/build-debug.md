# Build preparation and debugging

Use the selected project's build configuration to establish the toolchain, linker, and output image. The toolkit can locate tools and prepare commands; an actual build or hardware session provides a separate result.

## Prepare a CubeIDE build

```text
python stm32tool.py doctor --ide /path/to/STM32CubeIDE
python stm32tool.py inspect --project /path/to/firmware/BoardApp
python stm32tool.py build-plan --project /path/to/firmware/BoardApp --ide /path/to/launcher --workspace .build-workspaces/app --configuration Debug
```

`doctor` discovers files on PATH and under the supplied installation path. It does not run them or establish their versions. `inspect` exposes configuration-specific defines, includes, linker settings, and pre/post-build steps.

For `build-plan`, supply either a recognized installation directory with one launcher or the exact launcher file. Choose a unique configuration and a new or empty workspace separate from the project. Review the returned argv, shell commands, warnings, and effects before execution. Command generation alone does not establish that the launcher works on the current OS.

## Execute an authorized build

A fresh Eclipse `-data` directory separates IDE metadata. The `-import` argument still references the source directory, where build outputs and hooks may write. If the source must remain untouched, prepare a project copy and validate its linked resources, referenced projects, and absolute paths.

Import the required targets and dependencies. Use the Eclipse project name and selected configuration, especially when archives or experiments reuse names. The generated plan imports only the selected project; referenced projects need separate preparation.

Record the compiler, configuration, selected linker, warnings, exit status, and ELF/map/size outputs. Compare stale paths in generated makefiles with the source metadata. For CMake/Make, Keil, or IAR, use the project's native toolchain and target configuration.

## Check image and bootloader boundaries

Read MCU capacity and board partitions from the selected target. Reconcile the active linker's FLASH/RAM regions with vector placement, startup/system definitions, the bootloader's application jump address, erase/write ranges, and host image checks. Text extraction from the CLI does not evaluate arbitrary macro or linker expressions.

For each image, establish its role (application, bootloader, or combined), load address, vector table, initial MSP, Reset_Handler, size, and hash. Where relevant, use that target's flash bank/sector boundaries, protected regions, option bytes, security configuration, and multicore setup. Addresses and erase units from another project are insufficient evidence.

When an update path exists, follow framing, block sizes and numbering, retry/timeout behavior, verification and completion responses, and recovery after interrupted power. Check ownership between the normal command queue and update transport, including cancellation, failure, and reconnection. Derive the transfer protocol from the implementation.

## Diagnose with ST-LINK

Inspect existing debug configurations, scripts, and ELF tools first. For requested hardware work, record the board and revision, probe identifier, connection mode, application/bootloader ELF files, and image hashes. Symbols in an ELF do not establish that it matches the image on the board.

Account for how attach, reset, download, breakpoints, and memory reads affect CPU and peripheral timing. Record the point of failure and the final halted or running state. The toolkit's `doctor` and `build-plan` commands never access hardware.

For RAM structures and differences between production and diagnostic images, use the [diagnostics guide](diagnostics.md).
