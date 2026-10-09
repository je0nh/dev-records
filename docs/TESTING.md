# 검증 가이드

## 실행

저장소 루트에서 uv 가상환경으로 실행한다.

```sh
uv sync --locked
uv run --locked python -m unittest discover -s tests -v
uv run --locked python scripts/measure-coverage.py
```

테스트는 임시 디렉터리에 프로젝트·기록 저장소를 만들고 종료 시 정리한다. 실제 사용자 기록이나 GitHub를 변경하지 않는다. uv가 필요하며 POSIX signal 테스트는 지원하지 않는 OS에서 skip된다.

## 검증 범위

- 프로젝트 등록·작업 생성·명령 실행과 조회
- 실패·실행 불가·timeout·SIGINT/SIGTERM 처리
- argv·cwd·원본 출력·Git 상태 수집
- 경로 이탈·중복 ID·입력 오류 방지
- 동시 작업/실행 분리와 소스 삭제 후 기록 유지
- 플러그인 복사본 실행과 uv 가상환경 분리

테스트 배치는 [tests 안내](../tests/README.md)를 따른다. 새 기능의 검증은 관련 테스트에 추가하고, 이 문서는 실행 방법이나 검증 범위가 달라질 때 갱신한다. 매 실행의 결과 파일을 이 폴더에 추가하지 않는다.

## 확인된 환경과 남은 범위

초기 검증은 macOS의 Python 3.11/3.14에서 수행했다. [초기 검증 이력](archive/INITIAL_VALIDATION.md)에 당시 결과와 커버리지를 보존했다. 이력의 성공 결과가 현재 코드의 검증을 대신하지 않으므로 변경 후 위 명령을 실행한다.

Linux/Windows 실기, 실제 Codex 설치/Skill 호출, Git sync는 아직 검증하지 않았다. stdlib trace 결과는 줄 커버리지이며 branch coverage가 아니다.

## 결과 보관

실행별 argv·시각·종료 코드·원본 로그는 도구 소스 밖의 사용자 기록 저장소에 저장한다. CI 도입 후 CI 로그와 보고서는 CI artifact로 보관하고 보관 기간을 설정한다. CI artifact는 현재 구현되지 않았다. 중요한 릴리스 검증 요약만 개발 이력으로 남기며, 실패 원본을 자동 삭제하지 않는다.
