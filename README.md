# dev-records

**개발 작업의 기획, 구현 내용, 테스트 결과를 프로젝트별로 남기는 도구입니다.** Python CLI로 단독 사용하거나 Codex 개인 플러그인의 Skill과 함께 사용할 수 있도록 만들고 있습니다.

여러 프로젝트에서 같은 기록 방식을 사용하고, 소스 폴더를 삭제해도 기록이 남도록 도구·소스·기록의 저장 위치를 분리합니다. 장기적으로 기록을 별도 GitHub 저장소에 백업하는 것이 목표입니다.

## 현재 제공하는 기능

| 기능 | 설명 |
|---|---|
| 프로젝트 등록 | 프로젝트 ID와 소스 경로를 연결합니다. Git 저장소가 아니어도 가능합니다. |
| 작업 생성 | 기획·구현·검증 문서의 틀을 만듭니다. 문서 내용은 사용자나 Codex가 작성합니다. |
| 실행 기록 | 실제 명령, 실행 위치, 시작·종료 시각, 소요 시간, 종료 코드, Git 상태와 원본 출력을 저장합니다. |
| 실패 보존 | 실패·실행 불가·시간 초과·중단을 구분하고 재실행 결과를 새 ID로 남깁니다. |
| 기록 조회 | 등록된 프로젝트와 작업·실행 상태를 JSON으로 확인합니다. |

현재는 **로컬 기록 기능이 구현된 초기 버전**입니다. Codex 플러그인 manifest와 Skill은 준비했지만 실제 앱 설치·호출 검증은 남아 있습니다. GitHub 기록 동기화와 hooks/MCP를 통한 자동 기록은 아직 제공하지 않습니다.

## 프로젝트 구조

```text
dev-records/                  # 이 도구의 소스 저장소
├── AGENTS.md                 # Codex가 참고할 개발 지침
├── dev_records/              # CLI와 기록·실행 로직
├── scripts/                  # 플러그인용 실행 진입점과 커버리지 도구
├── skills/dev-records/       # Codex의 기록 작업 흐름
├── plugin.json              # 플러그인 manifest
├── .codex-plugin/            # 호환 manifest
├── tests/                    # 기능·회귀 테스트 코드
├── docs/                     # 명세·설계·검증 가이드
│   └── archive/              # 과거 인수인계·검증 이력
├── pyproject.toml            # Python/uv 프로젝트 설정
└── uv.lock                   # 의존성 lockfile
```

작업 기록은 **이 저장소 밖**에 저장합니다. 기록 폴더가 도구나 등록할 소스 폴더 안에 있거나, 그 폴더를 포함하면 등록을 거부합니다.

## 준비

Git, [uv](https://docs.astral.sh/uv/getting-started/installation/), Python 3.11+가 필요합니다. Python 실행은 uv가 관리하는 `.venv`를 사용하며 외부 런타임 패키지는 필요하지 않습니다.

```sh
git clone https://github.com/je0nh/dev-records.git
cd dev-records
uv sync --locked
uv run --locked python -m dev_records --help
```

이미 저장소를 받았다면 clone은 생략하세요. 초기 검증 환경은 macOS의 Python 3.11/3.14이며, Linux·Windows 실기 검증은 남아 있습니다.

## 사용 방법

아래 명령은 도구 저장소 루트에서 실행합니다. 예시의 `/absolute/path/to/your-project`는 **이미 존재하는 개발 프로젝트 경로**로 바꾸세요.

### 1. 기록 폴더 준비

```sh
export DEV_RECORDS_STORE="$HOME/dev-records-data"
uv run --locked python -m dev_records init
```

`DEV_RECORDS_STORE`는 현재 셸에서 사용할 기록 경로입니다. 환경변수 대신 각 명령에 `--store /absolute/records`를 넣어도 됩니다. `--store`는 `init`, `run` 같은 서브명령 **앞**에 둡니다.

### 2. 프로젝트 등록

```sh
uv run --locked python -m dev_records project add \
  --id my-project --source /absolute/path/to/your-project
```

프로젝트 ID는 소문자·숫자로 시작하는 1–64자의 소문자·숫자·하이픈 조합입니다. 프로젝트 등록은 한 번만 합니다. 다른 프로젝트는 다른 ID로 등록하세요.

### 3. 작업 생성과 기획 작성

```sh
uv run --locked python -m dev_records task start \
  --project my-project --id first-task --title "첫 기능 구현"
```

명령이 반환하는 JSON의 `path`가 작업 문서 위치입니다.

| 파일 | 작성할 내용 |
|---|---|
| `plan.md` | 목적, 범위, 방법, 완료 기준 |
| `implementation.md` | 변경 파일, 이전/이후 동작, 결정 이유, 남은 작업 |
| `testing.md` | 관련 실행 링크와 검증 요약 |

먼저 `plan.md`를 작성하고 구현 후 `implementation.md`를 갱신합니다. 예시는 따라 하기 쉽도록 작업 ID를 지정했으며, `--id`를 생략하면 자동 생성합니다. 새 작업에는 새 ID를 사용하세요.

### 4. 테스트 실행과 결과 확인

예를 들어 대상 프로젝트가 uv와 unittest를 사용한다면:

```sh
uv run --locked python -m dev_records run \
  --project my-project --task first-task --timeout 300 \
  -- uv run --project /absolute/path/to/your-project python -m unittest discover
```

`--` 뒤에는 **해당 프로젝트의 실제 테스트 명령**을 넣습니다. Python 이외에도 `npm test`, `cargo test` 등을 실행할 수 있습니다. 기본 실행 위치는 등록한 소스 경로이고, 다른 하위 디렉터리는 `--cwd`로 지정합니다. `--timeout`은 선택 사항이며 단위는 초입니다.

반환된 실행 `path`에서 `metadata.json`, `stdout.log`, `stderr.log`를 확인하고 해당 실행의 `testing.md`에 결과 해석을 작성하세요. 로그는 실행 디렉터리에 저장되고 CLI 출력은 JSON입니다. 종료 코드 0만으로 모든 테스트가 통과했다고 판단하지 않습니다.

같은 명령을 다시 실행하면 새 실행 ID가 생성되고 이전 실패 결과도 남습니다. 실행 명령의 실패는 CLI 종료 코드에도 반영됩니다.

### 5. 기록 조회

```sh
uv run --locked python -m dev_records status
```

등록된 프로젝트와 작업·실행 상태를 확인합니다. 전체 옵션과 종료 코드 규칙은 [CLI 명세](docs/CLI.md)에 정리되어 있습니다.

## 기록은 어디에 저장되나요?

```text
기록 폴더/                    # 예: ~/dev-records-data
├── config.json
└── projects/<project-id>/
    ├── project.json
    ├── overview.md
    ├── tasks/<task-id>/
    │   ├── task.json
    │   ├── plan.md
    │   ├── implementation.md
    │   └── testing.md
    └── runs/<run-id>/
        ├── metadata.json
        ├── stdout.log
        ├── stderr.log
        └── testing.md
```

작업은 기획·구현을 묶는 단위이고, 실행은 테스트 명령을 한 번 호출한 기록입니다. 한 작업에 여러 실행이 연결됩니다. 실행별 로그와 결과는 도구 소스 저장소에 커밋하지 않습니다.

현재 기록 상태는 `local_only`입니다. 이 도구의 GitHub 업로드와 사용자 기록의 백업은 별개이며, 도구가 기록을 자동 commit·push하지 않습니다.

## Codex와 함께 사용하기

다른 프로젝트 경로에서도 도구의 가상환경을 지정해 호출할 수 있습니다.

```sh
uv run --locked --project /absolute/path/to/dev-records python \
  /absolute/path/to/dev-records/scripts/dev-records.py \
  --store /absolute/records status
```

플러그인 Skill에는 프로젝트 등록 → 기획 작성 → 구현 기록 → 실제 테스트 수집 흐름이 정의되어 있습니다. 패키지 구성과 설치 검증 범위는 [플러그인 안내](docs/PLUGIN.md)를 참고하세요.

저장소 루트의 [AGENTS.md](AGENTS.md)는 **이 도구를 개발할 때** 읽는 지침입니다. Skill이나 AGENTS.md만으로 모든 수정과 명령이 자동 수집되지는 않으며, 실행 기록기는 `run`으로 호출한 명령만 수집합니다.

## 개발 및 참고 문서

```sh
uv run --locked python -m unittest discover -s tests -v
uv run --locked python scripts/measure-coverage.py
```

| 문서 | 내용 |
|---|---|
| [기획](docs/PLAN.md) | 구현 범위와 다음 단계 |
| [CLI 명세](docs/CLI.md) | 명령·옵션·데이터 계약 |
| [설계](docs/DESIGN.md) | 구조와 결정 이유 |
| [검증 가이드](docs/TESTING.md) | 테스트 실행 방법과 검증 범위 |
| [문서 관리](docs/README.md) · [테스트 관리](tests/README.md) | 갱신·확장·보관 기준 |

명령 인자와 로그는 원본으로 저장하므로 인증 정보를 넣지 마세요. 자동 비밀정보 제거와 로그 용량 제한은 아직 없습니다. 강제 종료나 전원 중단으로 남은 `running` 상태는 성공으로 추정하지 않습니다.
