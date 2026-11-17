# Development and build verification

The runtime remains Python 3.10+ with no external packages. Development checks separate Python behavior, the JSON result contract, portable-skill execution, and real CubeIDE compilation.

## Run the local checks

```sh
python -m unittest discover -s tests -v
python scripts/check_skill_bundle.py
python -m pip install -r requirements-dev.txt
python scripts/check_contract.py
git diff --check
```

Only the schema checker needs the development dependency. To keep it out of the current Python environment, use `uv run --no-project --with jsonschema==4.26.0 python scripts/check_contract.py`.

The standalone check copies the skill into a temporary directory and launches it from an unrelated working directory. It checks reference vectors, result metadata, and the presence of the portable schema.

## CI matrix

[The CI workflow](../.github/workflows/ci.yml) runs on pushes, pull requests, and manual dispatch. It covers Python 3.10, 3.11, 3.12, 3.13, and 3.14 on Ubuntu, Windows, and macOS. Every job runs the unit suite, standalone-skill check, and JSON Schema validation.

The workflow has read-only repository permissions and pins [checkout](https://github.com/actions/checkout) and [setup-python](https://github.com/actions/setup-python) to commit SHAs. Update those pins deliberately when upgrading the actions. Hosted CI does not install or execute CubeIDE.

A committed workflow is configuration, not evidence that its jobs passed. Use the workflow run for the relevant commit to establish remote matrix results; [validation.md](validation.md) records locally observed results separately.

## Compile the synthetic CubeIDE fixture

Install CubeIDE separately, then run the development harness with an explicit launcher and an unused output directory:

```sh
python scripts/verify_cubeide.py --ide /path/to/stm32cubeide-launcher --output-dir reports/cubeide-check
```

By default, the harness builds both Debug and Release. Use `--configuration Debug` to select one, or `--timeout SECONDS` to change the per-build limit.

This command executes CubeIDE and its compiler. It always copies the committed [synthetic fixture](../tests/fixtures/cubeide-smoke/) into the new report directory and generates plans with the toolkit's unchanged `build-plan` implementation. Each configuration gets a fresh Eclipse workspace. Existing output directories are rejected.

The fixture contains a small C reset handler, a vector table, a deliberately small synthetic linker layout, and CubeIDE managed-build metadata. It has no HAL, vendor source dependency, board wiring, external linked resources, or build hooks. The MCU selection exercises the installed toolchain's target handling; the memory layout is not a board configuration. The images are never flashed or executed.

The harness requires all of the following:

- A successful headless process exit.
- A newly generated ELF and a nonempty map file for each selected configuration.
- An ELF32 little-endian ARM executable with complete load segments and an executable Thumb entry within the synthetic flash region.
- Unchanged committed fixture files, checked by SHA-256.

CubeIDE can return zero after skipping an unmatched project/configuration. The artifact checks prevent that from being reported as a successful build. On timeout, the harness terminates the build process tree and records a failure.

## Inspect the evidence

The output directory retains the source copy, generated build plans, per-configuration logs and workspaces, ELF/map artifacts, and `result.json`. The report records input hashes, artifact hashes, time, toolkit version, and the IDE build identifier read from Eclipse's log. Compiler markers are read from the ELF; installation-folder names are not used to infer versions.

This development report uses its own `report_version`. It is not an ordinary CLI result covered by `result-v1.schema.json`. Full reports may contain local paths and remain in git-ignored `reports/`; shared validation records should retain only relative paths, hashes, tool versions, and observations.

The smoke build establishes compilation/linking of this fixture with the observed installation. It does not establish behavior on a real board, equivalence to a user's firmware, or support for every CubeIDE version.

The invocation follows ST's [STM32CubeIDE headless-build documentation](https://www.st.com/resource/en/user_manual/dm00629856-stm32cubeide-user-guide-stmicroelectronics.pdf). The fixture uses the managed-build identifiers exposed by the installed toolchain and ST's [public CubeIDE project metadata](https://github.com/STMicroelectronics/STM32CubeF4/blob/master/Projects/STM32F4-Discovery/Templates_LL/STM32CubeIDE/.cproject).
