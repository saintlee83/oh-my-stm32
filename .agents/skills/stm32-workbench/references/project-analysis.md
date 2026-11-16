# 프로젝트 선택과 근거 수집

## 타깃 식별

1. 사용자 경로에서 프로젝트별 지침과 빌드 파일을 찾는다. MCU 계열, 보드 리비전, 앱/부트로더/시험 이미지, 호스트 연동 여부를 소스 근거로 정리한다.
2. CubeIDE는 `inventory`로 후보를 찾고 `.project` 이름과 절대 경로를 함께 기록한다. 이름이 같아도 상대 경로가 다르면 별개 후보다. `.cproject`가 없는 항목은 빌드 가능한 프로젝트로 간주하지 않는다.
3. `inspect`의 configuration별 MCU, defines, include, 링커, build hooks를 비교한다. IOC의 프로젝트명과 폴더명이 다른 경우도 별도로 확인한다.
4. 메타데이터와 소스·산출물·배포 문서의 관찰 시점을 구분한다. 최신 날짜나 성공 로그만으로 기준 타깃을 정하지 않는다.

CLI의 `inventory`와 `inspect`는 Eclipse/CubeIDE 형식에 한정된다. 다른 형식은 CMake preset/toolchain, Make target, Keil project/scatter file, IAR project/linker configuration 등 실제 파일에서 같은 항목을 확인한다. `compare-projects`의 기본 파일 범위는 CLI 안내를 참고하고, 범위 밖 빌드 파일은 직접 비교한다.

## 후속 조사

해시가 그대로여도 새로운 프로젝트가 생길 수 있다. 전체 인벤토리를 다시 수집하고 기존 보고서와 비교한 뒤, 관련 프로젝트만 상세 비교한다.

```text
python stm32tool.py --output reports/inventory-before.json inventory --root /path/to/firmware
python stm32tool.py --output reports/inventory-after.json inventory --root /path/to/firmware
python stm32tool.py inventory-diff --before reports/inventory-before.json --after reports/inventory-after.json
python stm32tool.py compare-projects --before /path/to/baseline --after /path/to/variant --text-diff
```

`reports/`는 먼저 생성한다. 인벤토리는 같은 루트 범위와 제외 정책으로 수집한다. 부분 읽기 실패는 추가·삭제 확정과 구분한다. `inventory-diff`는 소스 변화나 rename을 판정하지 않는다.

`compare-projects`는 기본적으로 vendor/생성물/링크된 파일을 제외한다. 필요한 경우 `--include-vendor`를 사용한다. 문서·BIN·범위 밖 파일은 별도 대조한다. 원시 바이트 해시와 줄바꿈을 정규화한 text preview를 구분한다.

## 근거 관리

로컬 보고서에는 분석한 절대 경로와 프로젝트명을 남긴다. 공유할 근거가 필요하면 허용된 내용만 상대 경로·SHA-256·관찰 시점으로 작성한다. 실제 프로젝트 인벤토리, 조직·제품명, 전용 핀맵·통신·메모리 배치를 툴킷의 기본 문서나 테스트 fixture로 복사하지 않는다.
