# 주변장치와 펌웨어 변경

## CubeMX와 초기화

- `.ioc`, `Core/Inc/main.h`, GPIO 초기화, peripheral MSP, clock 설정, startup/system 파일을 함께 읽는다. 레거시 구조라면 실제 소스 위치를 따른다.
- `ioc-diff`는 설정 파일 차이다. 생성된 C, 핀 이름·극성, 초기 출력 레벨, 주변장치 대체 기능, 부트로더에서 남은 상태를 별도로 비교한다.
- 생성 코드 밖의 수동 수정, `USER CODE` 블록, middleware 설정, 외부 의존성을 확인하고 필요한 범위만 수정한다. 재생성이 요청되면 도구·패키지 버전을 기록하고 변경 diff를 검토한다.

## 클록과 타이밍

실제 MCU와 clock tree, 외부 발진기, prescaler, timer clock, tick 단위를 확인한다. 타이머 reload·compare, baud rate, DMA 전송 주기, timeout 사이의 단위 변환을 추적한다. 최소·최대·0·overflow·반올림 경계를 기존 테스트나 계산으로 검증한다. 다른 계열의 클록 규칙과 메모리 제약을 복사하지 않는다.

## 인터럽트·DMA·RTOS

버퍼의 생성자/소비자, 길이·인덱스, ISR과 task의 공유 상태, callback 이후 재사용 시점을 확인한다. blocking 호출을 ISR에 넣거나 기존 타임아웃을 제거해 동작을 맞추지 않는다. RTOS가 있으면 task 우선순위, queue 소유권, ISR용 API, stack/heap 설정과 watchdog 경로를 확인한다.

캐시·다중 코어·메모리 보호·보안 영역이 있는 타깃은 해당 프로젝트 설정과 MCU 문서를 기준으로 DMA 접근 가능 영역과 데이터 공유를 확인한다. CLI는 이 조건을 검증하지 않는다.

## 변경별 검증

핀 설정은 IOC/C 및 회로·보드 리비전, 시간 계산은 단위·범위, 상태 전이는 timeout·재시도·취소·재진입을 확인한다. 기존 host/HAL fake 테스트가 있으면 재사용한다. 컴파일 성공, 전기적 파형, 실제 장치 동작은 각각 별도 결과로 기록한다. 하드웨어 관찰이 요청된 경우에만 장비 연결을 진행한다.
