---
name: dev-records
description: Record a development task's plan, implementation decisions, and actual test command results using the bundled local Python CLI. Use when the user requests development records or invokes dev-records.
---

# Development records

Use the bundled CLI at `../../scripts/dev-records.py` relative to this skill directory. Resolve its absolute path from the actual installed skill location, rather than assuming a cache path. Use uv for every recorder invocation: `uv run --locked --project /absolute/plugin python /absolute/plugin/scripts/dev-records.py --store /absolute/records ...`. First run `uv sync --locked --project /absolute/plugin` to prepare the plugin’s own `.venv`. Read `../../docs/CLI.md` for the command contract. uv and Python 3.11+ are required. Bundle pyproject.toml and uv.lock with the plugin; do not copy .venv or install into global Python. The recorder has no external runtime dependencies. `--project /absolute/plugin` selects the recorder environment; it must not silently replace the target project’s runtime. For Python target tests, pass an explicit `uv run --project /absolute/source ...` as the recorded argv when appropriate.

1. Establish the user's record store and source directory. Use an existing `DEV_RECORDS_STORE` or explicit store choice. If missing, ask for the store location; never silently put private records into the tool or source repository. Initialize only the authorized local store. Register source with a stable project ID if needed (`status` lists existing records).
2. Start a task with explicit `--project` and title; retain the returned task ID/path for this task. Write purpose, scope, method, and acceptance criteria in the returned plan.md before implementation. For resumed work, use its explicit existing task ID.
3. Implement the user's requested change. Update implementation.md with actual changed files, decisions and reasons, previous/new behavior and remaining work.
4. Execute each authorized validation through `run --project ID --task ID -- PROGRAM ARG...`. Supply argv tokens directly; do not construct implicit shell strings. Respect the project's execution permissions. Use explicit --cwd when appropriate. Never report an unexecuted command as tested.
5. Read the returned run's metadata.json, stdout.log, stderr.log. Write the interpretation in that run's testing.md while retaining its collected facts and links. Exit code 0 alone does not prove that every test passed. Report failures, warnings, skips and unexecuted checks accurately. Update task testing.md with selected run links if useful, taking care with simultaneous sessions.
6. Report task/run locations and remaining work. All current records are local_only. Do not claim GitHub backup: sync is not implemented. Remote writes and installation require the user's explicit instruction. Do not modify global settings or credentials.

This Skill guides recording when used; it is not an automatic hook and cannot capture commands executed outside the recorder. Logs and argv preserve raw input/output and may contain secrets: avoid putting credentials into commands. Do not duplicate run metadata into unrelated documents or erase failed runs on retry.
