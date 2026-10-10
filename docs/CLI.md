# CLI 명세 · schema_version 1

아래 `dev-records`는 저장소 루트의 `uv run --locked python -m dev_records` 호출을 뜻한다. 다른 cwd에서는 `uv run --locked --project /absolute/plugin python /absolute/plugin/scripts/dev-records.py`를 사용한다.

전역 옵션 `--store PATH`는 서브명령 앞에 둔다. 생략 시 `DEV_RECORDS_STORE`를 사용하며 둘 다 없으면 오류다. 출력은 한 줄 JSON, 오류는 stderr JSON. ID는 영문 소문자/숫자로 시작하고 소문자/숫자/하이픈 1–64자. 프로젝트 ID는 사용자 지정, 작업/실행 ID는 UUID 기반 자동 생성. 암묵적인 현재 작업은 없다.

```text
dev-records --store PATH init
dev-records --store PATH project add --id ID --source PATH [--name NAME]
dev-records --store PATH task start --project ID --title TITLE [--id TASK_ID]
dev-records --store PATH run --project ID --task TASK_ID [--cwd PATH] [--timeout SECONDS] [--wrapper PATH] -- PROGRAM ARG...
dev-records --store PATH status
```

`init`: 로컬 기록 루트와 config.json을 생성. 재초기화는 기존 설정을 보존. 원격 생성/clone/commit/push 없음.
`project add`: 존재하는 소스 디렉터리 등록. 기록 루트와 겹치는 소스 거부. 같은 ID 재등록은 오류. Git이 없어도 가능.
`task start`: task.json 및 plan.md, implementation.md, testing.md 생성. 내용은 미작성 상태. 중복 ID는 덮어쓰지 않음.
`run`: 기본 cwd는 등록한 source. 지정 cwd는 source 안의 실제 디렉터리. `--` 뒤 argv만 실행하며 shell 해석 없음. timeout은 양의 유한 초. 실행 전 metadata.json을 running으로 저장, 종료 시 원자 교체. 각 실행에 testing.md를 저장하므로 동시 실행이 공유 문서를 덮어쓰지 않음. task testing.md는 runs 폴더를 안내하는 인덱스. 테스트 수/PASS/skip는 로그를 해석하기 전 미확인.
`status`: 등록 프로젝트·작업·실행과 기록 경로/상태를 조회. running은 강제 종료 또는 현재 진행 중일 수 있음.

종료 코드: CLI/입력 오류 2, 정상 실행은 자식 코드(0–255), 실행 불가 127, timeout 124, SIGINT 130, SIGTERM 143, 자식의 기타 signal은 128+signal. 자식 코드와 CLI 코드는 metadata에 별도로 기록.

명령 인자와 원본 로그에는 호출자가 전달한 비밀이 포함될 수 있다. 환경변수 전체·remote URL·Git diff는 수집하지 않는다. 원본 로그를 자동 삭제/업로드하지 않는다.

## 일회성 실행용 래퍼

```sh
uv run --locked python -m dev_records --store /absolute/records run \
  --project my-project --task first-task --wrapper /absolute/temp/launch.py \
  -- uv run --project /absolute/source python '{wrapper}'
```

`--wrapper`가 있으면 argv의 단독 `{wrapper}` 인자가 정확히 한 개 필요하다. 원본을 한 번 읽고 실행 디렉터리의 `wrapper/<filename>`에 원문을 보존한다. metadata.wrapper는 snapshot 상대 경로·SHA-256·execution_path·cleanup_status·cleanup_error를 담는다. requested_argv는 치환 전 명령, argv는 실제 실행한 명령이다. 원본 입력 경로는 metadata에 추가 수집하지 않는다.

실행용 복사본은 프로젝트 밖의 고유 임시 폴더에 두고 source cwd에서 실행한다. 실행 종료·실패·timeout·SIGINT/SIGTERM 처리 후 이 폴더만 정리한다. 원본 입력과 기록 사본은 삭제하지 않는다. cleanup_status는 not_created/pending/removed/failed이며 정리 실패는 cleanup_error에 기록한다. 정리 상태와 자식 명령 성공 여부는 별개다.

래퍼 파일을 기준으로 상대 경로나 옆 파일을 찾는 코드는 복사본에서 동작이 달라질 수 있다. 대상 스크립트는 명시적 경로나 source cwd 기준으로 호출한다. 래퍼가 생성한 source 산출물은 자동 정리하지 않는다. 환경변수 전체·의존 파일·의존성은 자동 보관하지 않으며 원문 하나의 보존이 전체 재현 환경을 보장하지 않는다. SIGKILL/전원 중단 시 running/pending과 임시 폴더가 남을 수 있고 자동 복구·오래된 폴더 일괄 삭제는 지원하지 않는다. 입력 래퍼에는 비밀정보를 넣지 않는다.
