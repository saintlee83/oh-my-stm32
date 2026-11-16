# 빌드, 메모리, 부트로더, 디버깅

## 빌드 준비

`doctor --ide PATH`는 PATH와 지정 설치 경로에서 파일을 찾는다. 실행하거나 버전을 추정하지 않는다. `inspect`는 configuration별 defines, includes, linker, pre/post-build step을 반환한다.

```text
python stm32tool.py doctor --ide /path/to/STM32CubeIDE
python stm32tool.py inspect --project /path/to/firmware/BoardApp
python stm32tool.py build-plan --project /path/to/firmware/BoardApp --ide /path/to/launcher --workspace .build-workspaces/app --configuration Debug
```

`build-plan`은 CubeIDE headless argv, PowerShell, POSIX shell 문자열만 제공한다. `--ide`에는 설치 폴더 또는 실행 파일을 지정한다. 알려진 이름의 실행 파일이 없거나 여러 개면 정확한 실행 파일을 지정한다. OS별 실제 실행 성공 여부는 별도 검증한다.

빌드가 요청되면:

- 소스를 보존해야 할 경우 별도 프로젝트 복사본을 준비하고 linked resources·참조 프로젝트·절대경로를 검토한다.
- 새 `-data`는 Eclipse 메타데이터를 분리한다. `-import`는 소스를 복사하지 않아 산출물과 hooks가 import한 디렉터리를 수정할 수 있다.
- 실제 프로젝트명과 configuration을 사용한다. 중복 이름·실험본이 있는 전체 워크스페이스 대신 필요한 타깃과 의존 프로젝트를 선택한다.
- 실제 compiler, configuration, 링커, 경고, 종료 코드와 ELF/map/size를 기록한다. 생성 makefile의 stale path는 원본 metadata와 비교한다.

CMake/Make/Keil/IAR 등은 프로젝트가 정의한 toolchain·target·output 설정을 따른다. CubeIDE headless 명령을 적용하지 않는다.

## 메모리와 부트로더

MCU 용량과 보드별 파티션은 선택한 타깃에서 읽는다. 활성 링커의 FLASH/RAM 영역, vector 위치, startup/system 정의, bootloader의 app jump 주소, erase/write 범위와 host 이미지 검사를 대조한다. 매크로·링커 식은 CLI의 문자 분석만으로 평가하지 않는다.

이미지 종류(앱/boot/합본), 로드 주소, vector/MSP/Reset_Handler, 크기, 해시를 확인한다. flash bank/sector 경계, 보호 영역, 옵션 바이트, 보안·다중 코어 설정이 있으면 해당 타깃 근거를 사용한다. 다른 프로젝트의 주소나 erase 단위를 재사용하지 않는다.

업데이트 경로가 있으면 host와 bootloader의 framing, block 크기·번호, retry/timeout, 검증·완료 응답, 전원 중단 후 복구를 함께 확인한다. 일반 명령 큐와 업데이트 transport의 소유권, 취소·실패·재연결 경로를 검증한다. 특정 전송 프로토콜을 기본으로 가정하지 않는다.

## ST-LINK와 실기 진단

기존 디버그 설정·스크립트·ELF 도구를 먼저 확인한다. 진단이 요청되면 보드 종류와 리비전, 프로브 식별자, 연결 모드, 앱/boot ELF와 이미지 해시를 남긴다. ELF 심볼 존재만으로 보드 이미지와 같다고 판단하지 않는다.

attach/reset/download, breakpoint, 메모리 읽기 방식이 CPU와 주변장치 타이밍에 주는 영향을 확인한다. 실패 시점과 종료 후 halt/resume 상태를 기록한다. `doctor`와 `build-plan`은 장비 접근을 수행하지 않는다. RAM 진단 구조와 진단 이미지 구별은 [diagnostics.md](diagnostics.md)를 따른다.
