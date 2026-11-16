---
name: stm32-workbench
description: Analyze, modify and validate STM32 firmware and optional host applications. Use for project selection, CubeMX and peripheral changes, protocol analysis, bootloader boundaries, build preparation and ST-LINK diagnosis. Includes an offline Python CLI for CubeIDE metadata and source comparisons.
---

# STM32 Workbench

사용자가 지정한 보드·MCU·프로젝트·작업 범위를 고정한다. 보드별 이름, 핀, 주소, baud rate, 명령, 호스트 언어를 미리 가정하지 않는다. 동봉 CLI는 파일 분석과 명령 생성만 수행한다. 펌웨어 수정·빌드·장비 진단은 사용자의 요청 범위에서 진행한다.

## 프로젝트 선택

- 대상 경로의 `AGENTS.md`와 빌드 메타데이터를 읽는다. CubeIDE는 `.project`의 이름과 절대 경로를 함께 기록한다. 후보가 많으면 `scripts/stm32_toolkit.py inventory --root PATH`로 찾는다.
- `inspect --project PATH`로 MCU, configuration, 선택된 링커, IOC, 소스 관찰을 읽는다. 폴더명·mtime·기존 배포 기록으로 현재 타깃을 결정하지 않는다. `*_RAM.ld`의 존재만으로 활성 메모리맵을 판단하지 않는다.
- CubeIDE가 아닌 프로젝트는 CMake/Make, Keil, IAR 등 실제 빌드 파일에서 타깃·도구·메모리맵을 확인한다. CubeIDE CLI 결과로 대체하지 않는다.
- 여러 후보의 분석은 계속할 수 있다. 수정·빌드에는 식별된 타깃을 사용한다. 기준본·변형·근거 비교는 [project-analysis.md](references/project-analysis.md)를 읽는다.

## 작업별 참고

- **GPIO / CubeMX / 클록 / DMA / RTOS:** [firmware.md](references/firmware.md). IOC, 생성 코드, 사용자 코드, 초기화 순서와 동시성 경계를 비교한다.
- **통신 / 호스트 연동:** [protocol.md](references/protocol.md). 실제 encoder → transport → parser → handler → 응답을 추적한다. `contract`는 위치 인덱스이며 `frame`은 명시적 JSON 명세가 필요하다.
- **빌드 / 메모리 / 부트로더 / 디버깅:** [build-debug.md](references/build-debug.md). 실제 툴체인·선택된 링커·ELF를 근거로 판단한다.
- **진단 이미지 / RAM 구조 / trace:** [diagnostics.md](references/diagnostics.md). 일반 이미지와 진단 이미지, 반복 관찰과 최초 부팅 기록을 구분한다.
- **CLI 사용:** [cli.md](references/cli.md). Python 3.10+ 표준 라이브러리로 실행하며 스킬 폴더만 복사해도 동작한다.

## 변경과 검증

- CubeMX 재생성 전 `USER CODE` 블록 밖의 수동 수정도 확인한다. 생성 코드·프로젝트 메타데이터·HAL 라이브러리를 일괄 교체하지 않는다.
- ISR·DMA callback·RTOS task·메인 루프 사이의 버퍼 소유권과 완료 시점을 확인한다. 큐 등록, 전송 완료, 명령 수락, 실제 적용 완료를 구분한다.
- 관련 기존 검증부터 실행한다. 통신은 기준 바이트·잘못된 프레임·타임아웃·취소, timing은 단위와 경계값, 부트로더는 이미지 영역·실패·재연결을 확인한다.
- 정적 분석, host test, ARM 컴파일/링크, 실기 시험을 구분해서 보고한다. 기존 ELF와 현재 소스의 일치 여부도 별도 근거다.
- 분석 요청에서 장비 연결을 시작하지 않는다. 장비 작업이 요청되면 보드·프로브·이미지를 식별하고 기존 권한 범위에서 진행한다. attach 시 CPU 정지가 타이밍에 영향을 줄 수 있다.
- 전체 조사 자료는 로컬 보고서로 보관한다. 공용 예제·테스트·문서에는 실제 조직·제품·고객의 식별 정보와 전용 계약을 넣지 않는다.
- 마무리에 변경 파일, 실행한 검증과 결과, 미확인 동작, 다음 작업에 필요한 타깃을 남긴다.
