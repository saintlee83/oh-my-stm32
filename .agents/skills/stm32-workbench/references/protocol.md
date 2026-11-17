# Host and firmware protocols

Start from the selected project's actual communication path: encoder, transport, parser, handler, and response. Identify the link and host implementation from source. Trace forwarding and address translation when intermediate controllers or multiple boards are involved.

Before changing the contract, record direction, addresses, frame length, payload offsets, byte order, units, ranges, version handling, and response timing. Keep queue acceptance, successful writes, command acceptance, and completed device actions distinct. Check how timeouts, retries, cancellation, late responses, and reconnection affect state.

## Locate command definitions

`contract` reads Python syntax trees and indexes numeric C case labels without importing the host application or opening a transport:

```text
python stm32tool.py contract --commands /path/to/host/commands.py --firmware /path/to/firmware/parser.c
python stm32tool.py contract --commands /path/to/request.py --commands /path/to/response.py --enum Request --enum Response
```

By default, it selects top-level classes based on `Enum`, `IntEnum`, `Flag`, or `IntFlag`, including recognized import aliases. Use `--enum NAME` to select named classes, including classes with custom bases. Repeat `--commands` and `--firmware` for multiple files.

Integer literals, including negative values, are resolved. Expressions, `auto()`, and member aliases remain in `unresolved_members`. C case labels provide locations to inspect; they do not establish switch context or active preprocessor branches and can be affected by text in strings. Inspect C enums and definitions in other host languages directly.

Use the index to find relevant code. Compatibility still requires checking field meanings, direction, units, and response behavior.

## Define a byte envelope

The `frame` commands support this field order:

```text
START | LENGTH | ID | COMMAND | PAYLOAD | CHECKSUM | END
```

Every operation requires an explicit JSON specification. The [example specification](frame.example.json) and [example vectors](frame-vectors.example.json) demonstrate the format using synthetic data.

All fields below are required. Extra keys are rejected.

| Field | Accepted value and meaning |
|---|---|
| `name` | Nonempty string identifying the supplied specification |
| `start_hex`, `end_hex` | Fixed marker bytes as hex strings; empty strings are allowed |
| `length_bytes` | Integer width of the length field: `0`, `1`, `2`, or `4`; zero omits it |
| `length_counts` | `payload` for payload bytes, or `frame` for total bytes including markers and checksum |
| `id_bytes`, `command_bytes` | Integer field widths: `0`, `1`, `2`, or `4`; an omitted field requires input value zero |
| `byteorder` | `little` or `big`, applied to all integer fields |
| `checksum` | `none`, `sum8`, `neg_sum8`, or `xor8` |
| `checksum_scope` | `body` for LENGTH through PAYLOAD, `payload` for PAYLOAD only, or `frame_prefix` for START through PAYLOAD |

A present checksum occupies one byte. `sum8` uses the low eight bits of the byte sum, `neg_sum8` uses the low eight bits of its negation, and `xor8` XORs the selected bytes. The checksum byte and END marker are excluded from every checksum scope.

Integer values must fit their fields; overflow is rejected. Omitting length or checksum also removes that validation. Frame decoding expects a complete frame, so the caller must establish message boundaries.

## Encode, decode, and verify

```text
python stm32tool.py frame encode --spec .agents/skills/stm32-workbench/references/frame.example.json --id 7 --command 0x10 --payload "01 02 03"
python stm32tool.py frame decode --spec .agents/skills/stm32-workbench/references/frame.example.json "A5 5A 03 00 07 10 01 02 03 14 0D 0A"
python stm32tool.py frame verify --spec .agents/skills/stm32-workbench/references/frame.example.json --vectors .agents/skills/stm32-workbench/references/frame-vectors.example.json
```

From a standalone skill copy, use `scripts/stm32_toolkit.py` and paths under `references/`.

A vector document contains a nonempty `vectors` list. Each entry must contain exactly `id`, `command`, `payload_hex`, and `frame_hex`. The optional `invalid_frames` list contains hex strings that decoding must reject.

`verify` compares encoded bytes with each reference frame, decodes that reference frame back into its expected fields, and checks invalid-frame rejection. Disagreements appear in `errors` with exit code `1`; invalid inputs return `2`. Use independently established bytes, such as authoritative fixtures or verified captures, rather than only round-tripping the same implementation.

## Validate the application contract

This codec does not implement stream reassembly, escaping, CRC, authentication, bit fields, variable headers, or response semantics. Use the project's existing codec and tests for formats outside the supported envelope. Changing a specification's name does not add protocol support.

For the real application, test minimum and maximum lengths, malformed checksums, missing acknowledgments, timeout and retry behavior, cancellation, and reconnection. Matching envelope bytes establishes only those byte-level checks. Firmware command meanings, timing, and outputs require separate evidence.
