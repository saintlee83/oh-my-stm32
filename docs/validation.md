# Validation record

The toolkit is checked with synthetic projects, source files, memory-independent protocol fixtures, and temporary directories. Real company or product sources are not used as test fixtures.

## Toolkit 0.3.0 verification

Observed on 2026-11-17. The following are local Windows execution results, separate from the configured GitHub Actions matrix.

| Python runtime | Unit tests | JSON Schema checks | Standalone skill |
|---|---|---|---|
| 3.10.20 | 59 passed | 16 valid transcripts; 7 incompatible samples rejected | Passed |
| 3.11.15 | 59 passed | 16 valid transcripts; 7 incompatible samples rejected | Passed |
| 3.12.13 | 59 passed | 16 valid transcripts; 7 incompatible samples rejected | Passed |
| 3.13.11 | 59 passed | 16 valid transcripts; 7 incompatible samples rejected | Passed |
| 3.14.3 | 59 passed | 16 valid transcripts; 7 incompatible samples rejected | Passed |

No tests were skipped in these runs. The contract checks cover all 11 CLI operations, partial inventories, vector mismatches, runtime errors, and output-file failures. They verify that the numeric frame command remains intact, saved output uses the same metadata, legacy inventories remain readable, additive minor versions are accepted, and incompatible majors are rejected.

The new build-harness tests use controlled process substitutes to exercise success, failure, missing artifacts despite exit code zero, existing-output protection, process timeout termination, and malformed or non-ARM ELF rejection. These unit tests are distinct from the actual compilation below.

### Actual CubeIDE compilation

The explicit development harness copied `tests/fixtures/cubeide-smoke/` into a new local report directory and executed the generated plans. Both configurations used fresh Eclipse workspaces. The runtime log identified CubeIDE as `Version 2.1.1`; ELF compiler markers identified GNU Tools for STM32 `14.3.rel1.20251027-0700`, GCC `14.3.1 20250623`.

| Configuration | Exit | Artifact | Bytes | ELF SHA-256 |
|---|---|---|---|---|
| Debug | 0 | `Debug/Toolkit.Smoke.elf` | 6460 | `908e73e32740be13ee8cf6fdf9d980f09b108d85295652e62b50c9a0d2ce3a0d` |
| Release | 0 | `Release/Toolkit.Smoke.elf` | 6588 | `76115e6622cc1a2e064377d96fd30f4d41322151eed31e4b1cc92233171fd9b2` |

Both artifacts were ELF32 little-endian ARM executables with two load segments, an executable Thumb entry at `0x08000009`, and a nonempty map file. These addresses belong only to the synthetic fixture. No hardware was accessed, and the committed fixture's input hashes remained unchanged:

| Fixture file | SHA-256 |
|---|---|
| `.cproject` | `2cdc184a1b33ae4647f7bfe0fade66a650e1f5294dbccf11f1ecca42bf46fffd` |
| `.project` | `f9b2b4114ee857b0a3e8e37be0dd5ed739e8d6d6bc151e51d4b5209d83db43e6` |
| `Core/Src/main.c` | `333108f8d5021ecc3ccb0cfa23ebfc13c00acf491fde871469ed836ae0c58b5b` |
| `synthetic.ld` | `bbe118b95c589a8b44eb366c5e0189652b382d7f28ad9d1ccd9620770b8d4a66` |

Artifact hashes identify this observation. Debug information and map files can contain build paths, so identical hashes across different checkout locations are not promised. Full logs and build outputs remain in local `reports/`; the reproduction procedure is in [development.md](development.md).

### CI status

The [workflow](../.github/workflows/ci.yml) defines 15 jobs: Ubuntu, Windows, and macOS with Python 3.10 through 3.14. It runs unit tests, standalone packaging checks, and JSON Schema validation. Remote jobs have not been executed as part of this local verification, and no Linux/macOS result for toolkit 0.3.0 is claimed here.

## English rewrite verification

Run on 2026-11-17 using Windows and Python 3.13.11.

| Check | Result |
|---|---|
| `python -m unittest discover -s tests -v` | 46 tests passed, with no skips |
| Skill validation | `Skill is valid!` from the skill-creator validator |
| Standalone skill copy | Two reference frames matched and three invalid frames were rejected |
| Documented frame examples | Encoding produced the documented bytes; decoding succeeded |
| Python 3.10 syntax | All 10 Python files parsed with `ast.parse(feature_version=(3, 10))` |
| Relative documentation links | All 23 targets exist |

The source review covered the CLI parser, profile/path resolution, project inspection, comparison scopes, build planning, frame codec, and static command index. Documentation was rewritten around those behaviors. Test fixture names now use English labels with a Unicode snowman escape to retain non-ASCII path coverage.

The skill validator ran with `uv run --no-project --with pyyaml python -X utf8` and the installed skill-creator `scripts/quick_validate.py`. PyYAML is a validation-tool dependency; the toolkit runtime still uses only the Python standard library.

## What the suite covers

| Area | Coverage |
|---|---|
| Project discovery | Duplicate Eclipse names, archived candidates, missing metadata, malformed XML, partial failures, and metadata from multiple MCU families |
| Comparisons | Independent IOC/source changes, raw hashes versus normalized line endings, optional vendor files, linked-file exclusion, bounded previews, and incomplete scans |
| Paths and output | Spaces, non-ASCII characters, quotes, profile-relative targets, existing-file protection, and separate build workspaces |
| Tool discovery and plans | Windows and extensionless names, synthetic macOS application layouts, explicit launcher choice, configuration selection, and no tool execution |
| Byte envelopes | Field widths, byte order, length modes, checksum algorithms/scopes, independent reference bytes, every one-byte payload length, overflow, and invalid frames |
| Static command analysis | Arbitrary Python source locations, enum import aliases, custom bases, unresolved members, and no input-code execution |
| CLI errors | Invalid profiles/specifications, vector disagreement, partial inventory results, and documented exit statuses |

## Earlier recorded run

The existing record reported a run on 2026-11-17 using macOS and Python 3.14.4: 46 tests passed, the standalone skill matched two reference frames and rejected three invalid frames, skill validation passed, all 10 Python files passed the Python 3.10 syntax check, all 20 documentation links then present resolved, and `git diff --check` passed.

That run resolved temporary test paths to account for macOS `/var` and `/private/var` aliases. Its results describe the earlier checkout and are separate from the Windows checks above.

## Limits of the evidence

The earlier Python 3.10 checks verified syntax only. The toolkit 0.3.0 Windows matrix above executes Python 3.10 directly. Synthetic launcher tests exercise discovery and command generation; actual CubeIDE execution is limited to the separately recorded Windows installation and fixture.

The recorded smoke run includes ARM compilation/linking of the synthetic fixture. Matching an ELF to a physical board image, flashing, serial communication, ST-LINK sessions, and waveform measurements remain untested. The result does not establish compatibility with a user's firmware or hardware.
