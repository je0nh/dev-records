# dev-records

Codex 개발 작업의 기획·구현·실제 테스트 실행을 프로젝트별로 기록하는 개인 로컬 도구입니다. 도구 소스는 `je0nh/dev-records`, 사용자 기록은 별도 디렉터리에 둡니다.

현재: 프로젝트 등록, 작업 문서 생성, 실행 기록 CLI와 Codex Skill 패키지 구현. GitHub 동기화와 앱 설치 검증은 다음 단계입니다. 기록은 `local_only`이며 원격 백업된 상태가 아닙니다.

uv와 Python 3.11+를 사용합니다. `uv sync --locked`가 프로젝트 `.venv`를 만들고, `uv run`이 해당 가상환경으로 실행합니다. 런타임 외부 의존성은 없습니다. 저장소 루트에서:

```sh
uv sync --locked
uv run --locked python -m dev_records --store /absolute/records init
uv run --locked python -m dev_records --store /absolute/records project add --id my-project --source /absolute/source
uv run --locked python -m dev_records --store /absolute/records task start --project my-project --title '기능 구현'
uv run --locked python -m dev_records --store /absolute/records run --project my-project --task TASK_ID -- uv run --project /absolute/source python -m unittest
uv run --locked python -m dev_records --store /absolute/records status
```

반환된 작업 경로의 plan.md를 작성하고, 구현 후 implementation.md를 갱신하세요. 각 실행 디렉터리에는 원본 stdout/stderr 로그, 명령/시간/종료 코드/Git metadata, testing.md가 남습니다. 테스트 해석은 실제 로그를 보고 작성합니다. 재실행은 새 ID로 보존합니다. 명령은 shell 없이 argv로 실행하며 로그는 파일에 직접 저장합니다.

다른 프로젝트에서는 `uv run --locked --project /absolute/path/dev-records python /absolute/path/dev-records/scripts/dev-records.py ...`로 호출하세요. `--project`는 도구의 가상환경을 선택하며 기록할 테스트의 cwd는 CLI `--cwd`로 별도 지정합니다. 테스트 명령은 해당 프로젝트가 사용하는 환경을 명시하세요. Python 프로젝트는 위 예시처럼 별도의 `uv run --project /absolute/source`를 전달할 수 있습니다.

이 프로젝트는 Codex에 소스·스크립트를 함께 배포하는 uv application입니다. `uv.lock`을 관리하며 wheel 설치와 전역 pip 설치는 필요하지 않습니다.

- [기획](docs/PLAN.md), [CLI 명세](docs/CLI.md), [설계·결정](docs/DESIGN.md)
- [개인 플러그인](docs/PLUGIN.md), [검증 증거](docs/TESTING.md)
- [초기 인수인계 · 보관](docs/archive/DEV_RECORDS_HANDOFF.md)

검증: `uv run --locked python -m unittest discover -s tests -v`

커버리지: `uv run --locked python scripts/measure-coverage.py`

기록 저장소는 소스·도구와 경로가 겹치면 거부합니다. 강제 종료/전원 중단으로 남은 running 상태는 성공으로 판정하지 않습니다. stdout/stderr는 원본이며 비밀정보 제거와 로그 용량 제한은 아직 제공하지 않습니다.
