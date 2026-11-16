# CLI 사용법

Python 3.10+ 표준 라이브러리만 필요하다. 저장소는 `python stm32tool.py`, 스킬 폴더만 복사했다면 `python PATH/scripts/stm32_toolkit.py`로 실행한다.

```text
stm32tool.py [--profile JSON] [--output NEW_JSON_FILE] COMMAND ...
```

전역 옵션은 COMMAND 앞에 둔다. 출력은 JSON이다. 정상 종료 0, 부분 읽기 실패/기준 벡터 불일치 1, 입력/읽기 오류 2다. argparse의 누락 옵션·도움말은 일반 CLI 텍스트다. `doctor.missing`은 탐색 결과이며 종료 실패로 간주하지 않는다. 출력 부모 폴더는 먼저 만들고 `--output`은 기존 파일을 덮어쓰지 않는다.

| COMMAND | 입력 | 결과 |
|---|---|---|
| `inventory` | `--root PATH` 또는 profile.workspace | Eclipse 이름, MCU, configs, IOC, 중복 이름, skip/error |
| `inspect` | `--project PATH_OR_ALIAS` | config, memory, IOC, source observations, SHA-256 |
| `doctor` | 선택 `--ide PATH`, `--pc-app PATH` | PATH/설치 경로의 도구 후보, host manifest와 venv 파일; 실행하지 않음 |
| `build-plan` | `--project`, `--workspace`, `--ide` 또는 profile.ide, 선택 `--configuration Debug` | CubeIDE headless argv/PowerShell/POSIX shell; 실행하지 않음 |
| `ioc-diff` | `--before FILE --after FILE`, 선택 `--all-settings` | 핀/MCU/RCC/NVIC 변경; all은 모든 키 |
| `inventory-diff` | `--before JSON --after JSON` | 상대 경로별 프로젝트 추가·삭제·메타데이터 변경 |
| `compare-projects` | `--before PATH_OR_ALIAS --after PATH_OR_ALIAS`, 선택 `--include-vendor`, `--text-diff` | 소스·설정 파일 추가/삭제/수정 및 SHA-256 |
| `frame encode` | `--spec JSON`, 선택 `--id 7 --command 0x10 --payload "01 02 03"` | 명시적 envelope의 hex와 해석 |
| `frame decode` | `--spec JSON HEX` | 완전한 단일 프레임의 구성/길이/checksum 검증 |
| `frame verify` | `--spec JSON --vectors JSON` | 독립적인 기준 바이트와 encode/decode 대조 |
| `contract` | 반복 `--commands PYTHON_FILE`, 선택 반복 `--enum NAME`, `--firmware C_FILE` | Python enum AST와 C numeric case 위치 |

## 프로파일과 경로

```json
{
  "workspace": "../firmware",
  "pc_app": "../host-app",
  "ide": "../tools/STM32CubeIDE",
  "targets": {"app": "BoardApp", "bootloader": "BoardBootloader", "variant": "BoardAppVariant"}
}
```

프로파일 경로는 파일의 부모 기준, target은 workspace 기준, CLI 경로는 현재 디렉터리 기준이다. `~`와 OS 환경변수를 확장한다. 개인 설정은 `profiles/*.local.json`에 둔다. 별칭은 정확한 디렉터리를 가리키며 배포 대상을 자동 선정하지 않는다. 예제 경로는 실제 사용자 경로로 변경한다.

`doctor`는 실행 파일 확장자가 있는 이름과 없는 이름을 모두 찾는다. `build-plan --ide`는 설치 폴더 또는 명시적 launcher 파일을 받으며, 여러 launcher가 있으면 파일 선택을 요구한다. `tools`의 키는 확장자 없는 도구명으로 정규화된다. 실행 파일의 실제 실행 가능 여부와 OS 호환성은 확인하지 않는다.

## 조사 결과 비교

```text
python stm32tool.py --profile profiles/workspace.local.json --output reports/inventory-next.json inventory
python stm32tool.py inventory-diff --before reports/inventory-before.json --after reports/inventory-next.json
python stm32tool.py --profile profiles/workspace.local.json compare-projects --before app --after variant --include-vendor --text-diff
```

`inventory-diff`는 같은 범위/제외 정책의 보고서를 비교한다. 루트의 절대 경로 변경은 무시하고 중복 Eclipse 이름은 상대 경로로 구별한다. 읽기 실패가 있으면 `comparison_complete=false`이며 추가/삭제 대신 `newly_observed`/`unobserved_after`를 표시한다. 소스 내용과 rename은 판정하지 않는다.

`compare-projects`의 범위는 C/C++/assembly, GNU 링커, IOC, launch, Eclipse 설정이다. 기본은 Drivers/Middlewares를 제외하며 `--include-vendor`로 포함한다. 생성물·문서·linked resource는 제외하고 skip 목록을 반환한다. CMake/Keil/IAR 등 범위 밖 파일은 별도 대조한다. 읽기 실패가 있으면 전체 비교 완료를 주장하지 않는다. UTF-8 preview는 파일당 1MiB/200줄로 제한하고 잘림을 표시한다. 정규화한 preview가 같아도 원시 바이트 해시 차이는 유지한다.

`inspect`의 source observations는 `Core/`의 일부 vector/app 주소·버전 매크로·HAL baud 대입을 문자로 찾는다. 전처리, 다른 소스 레이아웃, 링커 식 평가, ELF 검증, 실기 진단을 대신하지 않는다. 통신 명세와 결과 한계는 [protocol.md](protocol.md)를 따른다.

## 인터페이스 변경

0.2부터 `frame`은 명시적 `--spec`을 요구한다. `contract`는 앱 루트 대신 `--commands FILE`을 받으며 `command_sources`로 파일별 enum과 해시를 반환한다. 외부 앱 import 방식의 검증은 `frame verify`의 JSON 기준 벡터로 대체한다. 실제 입력 조사 자료와 프로파일은 로컬 보고서·개인 설정으로 관리한다.
