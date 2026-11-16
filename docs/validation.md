# 검증 기록

2026-11-17, macOS / Python 3.14.4에서 실행했다. 입력은 임시 디렉터리의 합성 프로젝트와 가상 통신 명세다. 실제 회사·제품의 소스나 분석 스냅샷을 검증 fixture로 사용하지 않는다.

| 검증 | 결과 |
|---|---|
| `python3 -m unittest discover -s tests -v` | 46개 통과 |
| 스킬 폴더 단독 실행 | 임시 디렉터리에 복사한 CLI에서 기준 프레임 2개 일치, 잘못된 프레임 3개 거절 |
| skill-creator `quick_validate.py` | `Skill is valid!` |
| Python 3.10 문법 검사 | Python 파일 10개를 `ast.parse(feature_version=(3, 10))`로 확인 |
| 상대 문서 링크 | 20개, 누락 없음 |
| `git diff --check` | 통과 |

단위 테스트는 다음을 확인한다.

- 프로젝트 탐색, 중복 Eclipse 이름, 누락 metadata, 잘못된 XML의 부분 실패, 여러 MCU 계열의 metadata 파싱.
- IOC/소스 변경의 독립성, 원시 바이트와 줄바꿈 정규화 차이, vendor 선택, symlink 제외, 부분 스캔 시 추가·삭제 단정 방지.
- 공백·한글·따옴표 경로, 프로파일 상대 경로, 기존 출력 파일 보호, 별도 build workspace와 configuration 선택.
- Windows/확장자 없는 실행 파일과 합성 macOS app 경로 탐색, 여러 launcher의 명시적 선택, 빌드·도구 미실행.
- JSON 프레임 명세의 필드 폭·endianness·길이 모드·checksum 범위, 독립 golden bytes, 한 바이트 길이의 모든 payload 크기, overflow·잘못된 입력 거절.
- 기준 벡터 불일치의 종료 코드, 임의 Python 소스·enum alias·커스텀 기반 클래스, 미해석 enum 멤버 표시와 입력 코드 미실행.

macOS의 `/var`와 `/private/var` 경로 차이는 테스트 입력을 `resolve()`하여 처리한다. 스킬 검증기는 개발 도구인 `uv run --no-project --with pyyaml python …/quick_validate.py`로 실행했다. 툴킷 실행에는 외부 Python 패키지가 필요 없다.

Python 3.10 검사는 문법 확인이며 해당 버전에서의 실제 실행 결과는 아니다. 다른 OS의 실제 CubeIDE 실행, ARM 컴파일·링크, ELF와 보드 이미지 대조, 플래시, 시리얼, ST-LINK, 파형 시험은 수행하지 않았다. 정적 분석과 합성 테스트는 실제 장치 호환성이나 빌드 성공을 보증하지 않는다.
