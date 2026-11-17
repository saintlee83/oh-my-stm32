# Diagnostic images and observations

A diagnostic image can change the behavior being investigated. Establish which image produced each observation and what the observation method can demonstrate.

## Establish the baseline and variant

Refresh the project inventory, compare it with the earlier local report, and use `compare-projects` on the relevant sources. A variant name or date does not identify its baseline. If a manifest exists, verify its source path, hashes, and change list against the files.

Look for diagnostic changes such as locked outputs, replaced reset behavior, altered watchdog handling, extra polling, and logging. Keep IOC comparisons, C initialization, linker changes, and existing BIN comparisons as separate evidence. A saved successful-build log describes an earlier run.

## Reconcile RAM structures with the host reader

Compare the project's C declaration with the host decoder and record the properties needed to interpret a snapshot:

| Area | What to establish |
|---|---|
| Layout | Symbol, magic/version, structure size, alignment, padding, field offsets, types, and byte order |
| Bounds | MCU-accessible memory, intended read range, and host size/address/version checks |
| Consistency | Writer and reader timing, snapshot rules, counter wrap, and valid/incomplete/error states |
| Lifetime | One-time boot record or repeated sample, and whether overflow or reset clears the data |

Use the selected firmware's layout and SRAM ranges. Test the host reader with synthetic memory, including failures for incorrect versions, lengths, alignment, and addresses. Such tests exercise decoder behavior; the actual compiled C ABI and the board's image still need separate evidence.

## State what was observed

Distinguish initial values visible in source, stored ELF/BIN artifacts, a new compilation, simulated memory, probe reads, and measured waveforms. Record the observation time and input identifiers in the report.

Keep a hardware session within the requested board, probe, and image scope. Record CPU halt/resume state and any observation method that could alter timing. This lets later investigators judge whether a result applies to normal operation, a diagnostic variant, or a simulated input.
