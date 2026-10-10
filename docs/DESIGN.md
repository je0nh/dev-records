# 설계와 결정

## ADR-001: 로컬 핵심과 개인 플러그인
하나의 Python 패키지에 파일 관리/실행 로직을 두고 CLI와 번들 scripts/dev-records.py가 공유한다. root plugin.json, skills/dev-records/SKILL.md를 패키징한다. hooks/MCP는 포함하지 않는다. Python 3.11+를 목표로 하되 macOS/Python 3.14에서 시작했고 uv 전환 후 Python 3.11.5도 검증했다. uv.lock과 pyproject.toml로 프로젝트 .venv를 관리하며, Codex에 전체 소스를 번들하므로 uv application(package=false)으로 실행한다. setuptools 빌드/전역 pip 설치는 필요하지 않다.

uv 환경 생성과 실행은 [Astral 공식 프로젝트 설정 문서](https://docs.astral.sh/uv/concepts/projects/config/) 기준이다. 플러그인 설치 위치마다 가상환경을 분리하며 대상 프로젝트의 테스트 환경은 argv로 명시한다.

## ADR-002: 기록 분리와 동시성
`--store`를 필수 명시(또는 환경변수 설정)하고 소스와 조상/자손 관계를 거부한다. 모든 경로는 resolve하고 저장소 밖으로 나가는 symlink를 거부한다. 프로젝트/작업 mkdir는 독점 생성, JSON은 임시 파일+os.replace로 교체. 공유 프로젝트 목록/현재 작업 파일이 없으므로 서로 다른 작업/실행은 동일 파일을 수정하지 않는다. 생성 도중 프로세스가 강제 종료되면 불완전 디렉터리가 남을 수 있으며 재등록은 덮어쓰지 않는다.

```text
config.json
projects/<project-id>/
  project.json
  overview.md
  tasks/<task-id>/
    task.json
    plan.md
    implementation.md
    testing.md
  runs/<run-id>/
    metadata.json
    stdout.log
    stderr.log
    testing.md
```

## ADR-003: 실행 증거
실행 전 argv/cwd/ID/offset 포함 시각/Git snapshot/실행기 OS와 Python 버전을 기록. monotonic으로 wall time 측정. 직접 파일로 출력해 큰 로그를 메모리에 쌓지 않는다. target 의존성/데이터 ID는 null, 실행기 Python을 target runtime으로 오인하지 않는다. timeout/중단 시 POSIX process group에 종료→kill, Windows는 직접 자식 종료(자손 보장 미검증). SIGKILL/전원 중단 복구는 running 상태 보존까지만 지원한다.

Git 정보는 source가 상위 Git 저장소 안에 있으면 해당 repository root를 명시한다. branch/commit/dirty는 조회 실패 시 null. dirty=true인 소스는 commit만으로 재현 불가. 성공은 종료 코드 0일 뿐 모든 테스트가 PASS라는 의미는 아니다. sync 상태는 항상 local_only, document_commit=null이다.

## 호환성 근거
2026-10-10 확인: [OpenAI 공식 패키징 문서](https://developers.openai.com/plugins/build/plugins)는 root plugin.json와 skills/를 지원하며 .codex-plugin/plugin.json도 호환 fallback으로 설명한다. 이 저장소는 두 manifest를 제공한다. 로컬 marketplace/설치는 docs/PLUGIN.md에서 안내하며 실제 설치/Skill 호출은 미검증이다. 전역 설정과 credentials는 수정하지 않는다.

## ADR-004: 실행용 래퍼 사본과 정리 소유권

래퍼는 일반 argv 실행의 선택 기능으로 추가한다. 실행 전 입력 원문을 읽고 실행 기록에 snapshot/sha256을 저장한다. 같은 bytes로 임시 복사본을 만들어 argv의 `{wrapper}` 한 토큰만 치환한다. 전역 shell 해석은 추가하지 않는다. 원문 보존과 실행 복사본이 동일하므로 실행 중 입력 파일 변경의 영향을 받지 않는다.

정리 책임은 도구가 생성한 실행 임시 디렉터리에 한정한다. 원본 입력과 실패 증거를 보존하고 cleanup_status를 metadata에 남긴다. wrapper metadata는 schema_version 1의 선택 필드이며 기존 run 호출은 그대로 지원한다. 강제 종료 복구·잔여 디렉터리 GC·의존 파일 수집은 후속 범위다.
