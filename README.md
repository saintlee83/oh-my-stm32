# oh-my-stm32

여러 STM32 프로젝트의 탐색, 소스·핀 설정 비교, 빌드 준비, 통신 분석과 검증을 돕는 에이전트 툴킷입니다. 회사·제품·보드별 설정을 포함하지 않으며, 프로젝트 경로와 통신 명세는 사용자가 지정합니다. Python 3.10+ 표준 라이브러리만 사용합니다.

## 시작하기

```text
python stm32tool.py inventory --root /path/to/firmware
python stm32tool.py inspect --project /path/to/firmware/BoardApp
python stm32tool.py doctor --ide /path/to/STM32CubeIDE
python stm32tool.py build-plan --project /path/to/firmware/BoardApp --ide /path/to/launcher --workspace .build-workspaces/app --configuration Debug
python stm32tool.py compare-projects --before /path/to/baseline --after /path/to/variant --text-diff
python stm32tool.py ioc-diff --before /path/to/baseline/board.ioc --after /path/to/variant/board.ioc
```

예제 경로는 사용자의 경로로 바꿉니다. 반복 작업에는 [예제 프로파일](profiles/stm32.example.json)을 `profiles/workspace.local.json`으로 복사하고 `workspace`, `ide`, `pc_app`, `targets`를 수정하세요. 프로파일의 경로는 프로파일 파일 기준이며 별칭은 `workspace` 기준입니다.

```text
python stm32tool.py --profile profiles/workspace.local.json inventory
python stm32tool.py --profile profiles/workspace.local.json inspect --project app
python stm32tool.py --profile profiles/workspace.local.json build-plan --project app --workspace .build-workspaces/app
```

모든 CLI 명령은 오프라인으로 동작하며 입력 소스를 수정하지 않습니다. `build-plan`은 실행할 명령만 생성합니다. `--output`은 기존 파일을 덮어쓰지 않습니다. 전역 옵션은 명령 앞에 둡니다.

## 제공 기능과 지원 범위

| 기능 | 범위 |
|---|---|
| `inventory`, `inspect` | STM32CubeIDE/Eclipse 프로젝트명, MCU, 빌드 설정, IOC, 링커 메모리, 소스 관찰, SHA-256 |
| `inventory-diff` | 같은 범위로 수집한 인벤토리 간 추가·삭제·메타데이터 변화 |
| `compare-projects`, `ioc-diff` | C/C++/어셈블리·링커·CubeMX·Eclipse 설정 비교 |
| `doctor`, `build-plan` | Windows/확장자 없는 도구 탐색, 명시적 실행 파일 선택, headless 명령 생성 |
| `contract` | 지정 Python 파일의 enum과 C 소스의 숫자 case 위치를 실행 없이 분석 |
| `frame encode/decode/verify` | 사용자 JSON 명세에 따른 바이트 프레임 처리와 기준 벡터 검증 |
| `stm32-workbench` 스킬 | 프로젝트 선택, GPIO·클록·주변장치·RTOS, 통신, 부트로더, 빌드·디버깅 작업 절차 |

CLI의 프로젝트 메타데이터 분석과 빌드 명령 생성은 CubeIDE/Eclipse 형식이 대상입니다. CMake/Make, Keil, IAR 등 다른 STM32 프로젝트는 스킬에서 해당 빌드 파일을 직접 확인하는 절차로 안내합니다. MCU 계열이나 메모리 주소, 보드 역할, baud rate를 공통값으로 가정하지 않습니다. 정적 결과는 실제 빌드·플래시·보드 동작을 증명하지 않습니다.

## 통신 명세 지정

STM32 공통 프레임 형식은 없습니다. 프레임 명령에는 `--spec`이 필수입니다. 다음 명세와 벡터는 툴 사용법을 위한 가상 예제입니다.

```text
python stm32tool.py frame encode --spec .agents/skills/stm32-workbench/references/frame.example.json --id 7 --command 0x10 --payload "01 02 03"
python stm32tool.py frame verify --spec .agents/skills/stm32-workbench/references/frame.example.json --vectors .agents/skills/stm32-workbench/references/frame-vectors.example.json
python stm32tool.py contract --commands /path/to/host/commands.py --firmware /path/to/firmware/parser.c
```

[통신 안내](.agents/skills/stm32-workbench/references/protocol.md)에 명세 필드와 지원 한계를 설명합니다. `contract`는 외부 앱을 import하지 않고 소스만 읽습니다. `frame verify`에는 독립적으로 확인한 기준 바이트를 제공하세요.

## 에이전트에서 사용

[stm32-workbench](.agents/skills/stm32-workbench/SKILL.md)에서 시작합니다.

> `$stm32-workbench`로 지정한 STM32 프로젝트의 빌드 설정, 핀 초기화, 호스트와의 명령 처리를 확인하고 변경에 필요한 파일과 검증을 정리해 줘.

다른 작업 공간에서는 `.agents/skills/stm32-workbench` 전체를 스킬 디렉터리에 복사하거나 `SKILL.md` 경로를 제공하세요. CLI와 참고 문서는 스킬 폴더 안에 함께 들어 있습니다.

| 안내 | 내용 |
|---|---|
| [프로젝트 분석](.agents/skills/stm32-workbench/references/project-analysis.md) | 타깃 식별, 변형 비교, 근거 수집 |
| [펌웨어 작업](.agents/skills/stm32-workbench/references/firmware.md) | CubeMX, GPIO, 클록, 인터럽트, DMA, RTOS |
| [통신](.agents/skills/stm32-workbench/references/protocol.md) | 호스트 계약, 프레임 명세, ACK·취소 검증 |
| [빌드·디버깅](.agents/skills/stm32-workbench/references/build-debug.md) | 툴체인, 메모리, 부트로더, ST-LINK |
| [진단](.agents/skills/stm32-workbench/references/diagnostics.md) | 진단 이미지와 ABI, 관찰 범위 |
| [CLI](.agents/skills/stm32-workbench/references/cli.md) | 입력, 결과, 종료 코드 |

## 로컬 자료와 검증

전체 인벤토리·분석 보고서는 git에서 제외되는 `reports/`, 개인 경로·설정은 `profiles/*.local.json`에 보관합니다. 공유 예제와 테스트에는 합성 데이터만 사용합니다.

```text
python -m unittest discover -s tests -v
```

[검증 기록](docs/validation.md)에 실행 환경과 범위를 기록합니다.
