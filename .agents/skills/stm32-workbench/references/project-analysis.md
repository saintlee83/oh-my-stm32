# Project selection and evidence

Establish which source tree, build configuration, and image the user means before making a change. A workspace may contain archives, experiments, and several directories with the same Eclipse name.

## Identify the target

Read project-specific instructions and build files under the supplied path. Record the absolute directory, project name, MCU family, board revision, image role (application, bootloader, or test), and any host application involved. Mark details that the available files do not establish.

For CubeIDE, use `inventory` to find candidates and `inspect` to examine each relevant configuration. Compare MCU identifiers, defines, include paths, linker selection, and build hooks. Resolve differences between folder, Eclipse, and IOC names explicitly. A `.project` without `.cproject` may be an Eclipse stub and is insufficient evidence of a buildable target.

Keep source observations, metadata, existing artifacts, and deployment records separate. Their timestamps describe different events; a recent file or successful historical log does not select the current target.

The CLI's metadata reader covers Eclipse/CubeIDE. For other build systems, inspect the corresponding CMake presets/toolchain, Make targets, Keil project/scatter files, or IAR project/linker settings. Check the [CLI comparison scope](cli.md) before relying on a source diff.

## Refresh an investigation

Unchanged hashes for known files do not rule out newly added projects. Collect a fresh inventory over the same scope, compare saved inventories, then examine relevant project pairs.

Create `reports/` first and choose unused output filenames:

```text
python stm32tool.py --output reports/inventory-before.json inventory --root /path/to/firmware
python stm32tool.py --output reports/inventory-after.json inventory --root /path/to/firmware
python stm32tool.py inventory-diff --before reports/inventory-before.json --after reports/inventory-after.json
python stm32tool.py compare-projects --before /path/to/baseline --after /path/to/variant --text-diff
```

Use consistent scan roots and exclusion policies. If a scan is incomplete, treat unmatched entries as observations rather than confirmed additions or removals. Inventory comparison does not detect source-only changes or prove a rename.

Project comparison excludes vendor directories by default; add `--include-vendor` when those sources matter. Linked resources, build outputs, binary images, documentation, and unsupported build files need separate comparison. Raw hashes preserve byte differences even when a normalized text preview is identical.

## Keep evidence attributable

Local reports should retain exact analyzed paths, project names, observation times, input hashes, and known gaps. Preserve previous reports so later findings can be distinguished from earlier observations.

For shared evidence, use permitted relative paths, SHA-256 hashes, and observation times. Keep real project inventories, organization and product identifiers, and private pin maps, memory layouts, and protocol contracts out of toolkit examples, fixtures, and general documentation.
