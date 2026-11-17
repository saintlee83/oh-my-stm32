# Validation record

The toolkit is checked with synthetic projects, source files, memory-independent protocol fixtures, and temporary directories. Real company or product sources are not used as test fixtures.

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

The Python 3.10 check verifies syntax, not execution under that interpreter. Synthetic launcher files exercise discovery and command generation, not real CubeIDE execution on each OS.

These checks do not include ARM compilation/linking, matching an ELF to a board image, flashing, serial communication, ST-LINK sessions, or waveform measurements. Static analysis and host tests cannot establish device compatibility or build success.
