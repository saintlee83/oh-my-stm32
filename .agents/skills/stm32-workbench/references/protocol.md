# 통신과 호스트 계약

## 실제 계약 추적

STM32 자체는 애플리케이션 프레임을 정하지 않는다. UART/USB/CAN/SPI/I2C/네트워크 등 실제 링크, host 언어와 transport, parser/handler/응답 경로를 선택한 프로젝트에서 확인한다. 중간 제어기나 여러 보드가 있는 경우에만 forwarding과 주소 변환도 추적한다.

변경 전 방향, 주소, 전체 길이, payload offset, endian, 단위, 범위, 버전 처리, ACK·실제 적용 시점을 기록한다. 큐 등록, write 성공, 명령 수락, 적용 완료, 여러 대상의 성공을 구분한다. timeout·재시도·취소·늦은 응답·재연결이 상태 전이를 잘못 되돌리지 않는지 확인한다.

`contract`는 지정한 Python 소스를 AST로 읽고 enum과 정수 literal을 인덱싱한다. 앱을 import하거나 transport를 생성하지 않는다.

```text
python stm32tool.py contract --commands /path/to/host/commands.py --firmware /path/to/firmware/parser.c
python stm32tool.py contract --commands /path/to/request.py --commands /path/to/response.py --enum Request --enum Response
```

기본은 최상위 `Enum`/`IntEnum`/`Flag`/`IntFlag` 클래스다. import alias를 인식하며 커스텀 기반 클래스는 `--enum NAME`으로 선택한다. 정수 literal과 음수만 해석하고 `auto()`, 식, alias 등은 `unresolved_members`에 남긴다. C numeric case는 전처리·문자열·switch 문맥을 해석하지 않는 위치 힌트다. C enum, C#/C++ 등 다른 형식의 명령 정의는 실제 소스를 직접 확인한다. 이 인덱스는 호환성 판정기가 아니다.

## 명시적 프레임 명세

`frame`은 아래 순서의 단순 바이트 envelope만 지원한다. 제공된 [명세](frame.example.json)와 [벡터](frame-vectors.example.json)는 가상 예제이며 보드 설정이 아니다.

```text
START | LENGTH | ID | COMMAND | PAYLOAD | CHECKSUM | END
```

JSON 필드는 모두 필수이며 알 수 없는 키는 오류다.

| 필드 | 의미 |
|---|---|
| `name` | 사용자 프로토콜 식별 문자열 |
| `start_hex`, `end_hex` | 고정 시작·끝 바이트. 빈 문자열 허용 |
| `length_bytes` | 길이 필드 폭: 0(없음), 1, 2, 4 |
| `length_counts` | `payload`: payload 바이트 수, `frame`: marker/checksum을 포함한 전체 길이 |
| `id_bytes`, `command_bytes` | 각 정수 필드 폭: 0, 1, 2, 4. 없는 필드의 입력값은 0 |
| `byteorder` | 모든 정수 필드의 `little` 또는 `big` |
| `checksum` | `none`, `sum8`, `neg_sum8`, `xor8` |
| `checksum_scope` | `body`: LENGTH부터 PAYLOAD까지, `payload`: PAYLOAD만, `frame_prefix`: START부터 PAYLOAD까지 |

`sum8`은 대상 바이트 합의 하위 8bit, `neg_sum8`은 그 합의 음수의 하위 8bit, `xor8`은 대상 바이트의 XOR다. checksum은 1바이트이며 자기 자신과 END를 계산에 포함하지 않는다. 정수 overflow는 wrap하지 않고 거절한다. 필드가 없으면 해당 길이/체크섬 검증도 수행하지 않는다.

```text
python stm32tool.py frame encode --spec .agents/skills/stm32-workbench/references/frame.example.json --id 7 --command 0x10 --payload "01 02 03"
python stm32tool.py frame decode --spec .agents/skills/stm32-workbench/references/frame.example.json "A5 5A 03 00 07 10 01 02 03 14 0D 0A"
python stm32tool.py frame verify --spec .agents/skills/stm32-workbench/references/frame.example.json --vectors .agents/skills/stm32-workbench/references/frame-vectors.example.json
```

스킬만 복사한 경우 `scripts/stm32_toolkit.py`와 `references/` 경로를 사용한다. 실제 명세와 독립적인 기준 벡터는 로컬 JSON으로 제공한다. `verify`는 `vectors`의 id/command/payload_hex/frame_hex를 양방향 비교하고 선택 `invalid_frames`가 거절되는지 확인한다. 불일치는 `errors`와 종료 코드 1, 잘못된 입력은 2다.

이 도구는 스트림 분할·escaping·CRC·인증·bit field·가변 header·응답 의미를 처리하지 않는다. 해당 프로토콜은 기존 codec과 테스트를 사용한다. 명세의 이름을 바꾼 것만으로 실제 프로토콜 지원을 의미하지 않는다. golden bytes, 최소·최대 길이, 잘못된 checksum, 누락 ACK, 취소와 재연결을 실제 계약별로 검증한다. 오프라인 envelope 일치는 펌웨어 명령·타이밍·출력의 호환성을 증명하지 않는다.
