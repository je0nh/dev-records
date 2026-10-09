> 보관 문서: 초기 MVP 검증 이력입니다. 현재 검증 절차는 [검증 가이드](../TESTING.md)를 확인하세요.

# 검증 증거 · 2026-10-10 (Asia/Seoul)

기준: [초기 인수인계](DEV_RECORDS_HANDOFF.md)와 [기획](../PLAN.md). 환경: macOS, Python 3.14.8, Codex CLI 0.160.0.

## 최신 검증: uv 가상환경 전환

uv 0.12.21의 `uv sync`로 저장소 `.venv` 생성. `uv run ... python`의 sys.prefix != sys.base_prefix=True와 `.venv/bin/python`을 확인했다. Python 3.11.5로 전체 **15 tests OK**, 종료 코드 0.

`uv run --locked python scripts/measure-coverage.py`를 recorder를 통해 실행했다(검증에서는 offline/no-python-downloads와 쓰기 가능한 임시 cache 경로도 지정).

- 시작: 2026-10-09T17:42:40.183227+00:00
- 종료: 2026-10-09T17:42:46.529534+00:00
- monotonic wall time: 6.309301 seconds
- core 줄 커버리지 92%, CLI 94% (Python 3.11 trace는 정수 퍼센트로 출력)
- 플러그인 복사본에서 별도 `.venv` 생성 및 다른 프로젝트 cwd 호출 검증 추가
- 실행 ID: `run-c56f7c7e6f0e48bd8485054990c2a6b5` (이전 14 tests 실행도 로컬 기록에 보존)

현재 사용/테스트 명령은 README의 uv 기준을 따른다. 전역 pip 설치·빌드 백엔드 의존성 없이 uv application으로 실행한다. uv.lock을 버전 관리하며 `.venv`는 제외한다. macOS Python 3.11/3.14를 확인했고 Linux/Windows와 실제 Codex 설치는 후속이다.

아래는 uv 전환 전의 검증 이력이다.

## 사용자 흐름과 TDD
사용자는 서로 다른 프로젝트를 같은 기록 루트에 등록하고, 독립 작업 문서를 만들며, 실제 테스트의 명령/시간/출력/실패를 보존한다.

RED: `python3 -m unittest discover -s tests -v`에서 초기 8개 테스트가 CLI 진입점 미구현(`No module named dev_records.__main__`)으로 실패했다. 초기 잘못 작성된 테스트 하나를 제거하고 흐름 테스트를 확장했다. 자체 개발 기록 회귀 테스트도 수정 전 `source must be separate from records and tool source`로 실패했으며, 외부 기록 루트 분리를 유지하면서 자체 프로젝트 등록을 허용한 뒤 통과했다.

GREEN: 최종 동일 unittest 명령을 **구현한 recorder를 통해 실제 실행**했다. 종료 코드 0, 상태 `succeeded`.

- 시작: 2026-10-09T17:38:41.303663+00:00
- 종료: 2026-10-09T17:38:54.963618+00:00
- monotonic wall time: 13.615276 seconds
- 결과: 전체 14 tests, OK, skip 없음
- 작업 ID: `task-482a06fdb8574a1a92fe756326fe6a71`
- 실행 ID: `run-e4c96a5087ad485dbc1f2d6b233bd7d5`

검증용 기록 루트는 외부 임시 디렉터리다. 컴퓨터마다 달라지는 로컬 경로 포인터 파일은 공유 저장소에서 제거하고 실행 ID·측정 결과·재현 명령만 이 문서에 보존했다. 운영용 저장소가 아니며 OS 정리로 사라질 수 있다. GitHub 백업은 수행하지 않았다. Git checkpoint commit도 생성하지 않았다.

## 검증 보장

| 보장 | 테스트 | 결과 |
|---|---|---|
| 공백/한글 경로, stdout/stderr, argv 원문, 명시 cwd | success_argv_and_logs, literal_argv_and_cwd | PASS |
| 실패(7), 재시도 새 ID, 실행 파일 없음(127) | failure_retry_and_missing_program | PASS |
| timeout(124), SIGINT(130), SIGTERM(143), 자식 signal 코드 | timeout, interrupt, sigterm_and_child_signal | PASS |
| 중복 ID, 미등록 작업, 빈 명령/제목, 무효 timeout, schema 오류 | validation, invalid_records_and_arguments | PASS |
| symlink 이탈과 source/store 겹침 거부 | symlink_escape, validation | PASS |
| 4개 동시 작업, 같은 작업의 3개 동시 실행 기록 분리 | concurrent_tasks_and_runs | PASS |
| Python와 shell 프로젝트 흐름, source 삭제 후 기록 유지 | two_projects_and_preserved_records | PASS |
| Git commit/dirty 수집, 비 Git 프로젝트 | git_snapshot, success_argv_and_logs | PASS |
| 복사한 전체 플러그인의 다른 cwd 실행과 manifest/Skill 존재 | bundle_from_other_cwd | PASS |
| 도구 자체를 프로젝트로 등록 | tool_can_record_its_own_development | PASS |

## 커버리지와 추가 확인

`python3 scripts/measure-coverage.py` 실행: 14 tests OK. 표준 라이브러리 trace의 subprocess 측정 결과:

| 모듈 | 측정 줄 | 줄 커버리지 |
|---|---:|---:|
| dev_records.core | 214 | 92.1% |
| dev_records.cli | 55 | 94.5% |
| dev_records.__init__ / __main__ | 각 2 | 100% |

이 수치는 trace가 계산하는 실행 가능 줄 기준이며 branch coverage가 아니다. Windows 종료 경로, 저장장치 오류, 모든 강제 종료 지점은 검증하지 않았다. Python 3.11/Linux/Windows 실기 검증은 후속이다.

`python3 -m compileall -q dev_records scripts tests`와 번들 `--help` 실행 성공. `git diff --check` 오류 없음(현재 모두 신규/untracked 파일이므로 tracked diff 검증 범위는 비어 있음). Codex CLI plugin 명령 help 확인. manifest JSON 파싱과 복사본 실행은 확인했으나 실제 앱 설치/Skill 호출, wheel 설치, Git sync/bare remote는 아직 검증하지 않았다.

런타임 외부 의존성은 0개. pip-audit/coverage 설치는 sandbox DNS 실패 후 설치 승인 거절로 수행하지 않았다. 의존성 감사 완료로 표시하지 않는다. 커버리지는 추가 설치 없이 stdlib trace로 측정했다.

## 초기 커밋 전 확인

uv 가상환경에서 unittest 15개 재실행: OK. pip-audit 호출은 모듈 미설치로 실행 불가. 대체로 `uv audit --locked --offline --no-python-downloads --cache-dir /private/tmp/dev-records-uv-cache` 실행 성공: 외부 패키지 0개, 알려진 취약점 없음. 이는 프로젝트 의존성 검사이며 Python/OS 전체 보안 감사가 아니다.
