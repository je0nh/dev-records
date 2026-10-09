# Codex 개인 플러그인

루트가 플러그인 패키지다. plugin.json, 호환 manifest, skills/, scripts/, dev_records/, docs/, pyproject.toml, uv.lock을 함께 배포해야 한다. 실행기는 script 파일 기준으로 Python 모듈을 찾기 때문에 소스 프로젝트 cwd에서 호출 가능하다. uv와 Python 3.11+를 사용하며 플러그인 루트의 `.venv`로 격리한다. `.venv`는 배포하지 않고 설치된 복사본에서 `uv sync --locked --project /absolute/plugin`으로 생성한다.

[공식 패키징 문서](https://developers.openai.com/plugins/build/plugins) 기준 manifest와 Skill을 준비했다(2026-10-10 확인). 설치 경로에 고정된 설정은 없다. 실제 Codex 앱에서 marketplace 등록/설치/새 채팅 Skill 호출은 아직 검증하지 않았다. 계정/클라이언트별 로컬 플러그인 지원은 설치 시 확인한다.

개인 설치 단계는 사용자가 설치를 요청한 뒤 수행한다. 공식 문서의 로컬 marketplace 절차로 이 패키지를 등록하고 설치된 복사본 전체를 검증한다. 기존 marketplace/config.toml은 병합하고 다른 설정을 보존해야 한다. 현재 작업에서는 홈 디렉터리와 전역 설정을 수정하지 않았다.

설치 전 독립 smoke test:

```sh
uv sync --locked --project /absolute/path/dev-records
uv run --locked --project /absolute/path/dev-records python /absolute/path/dev-records/scripts/dev-records.py --help
```

Codex에서 사용할 요청 예시: “dev-records로 이 작업의 기획·구현·테스트를 기록해줘. 기록 루트는 /absolute/records, 프로젝트 ID는 my-project야.”

Skill만으로 모든 코드 수정이 자동 기록되지는 않는다. 실행 도구를 통과한 명령만 수집한다. hooks/MCP는 필요성과 지원 형식을 검증한 뒤 추가한다.
