"""Filesystem records and command execution; no network or implicit shell."""
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import tempfile
import time
import uuid

TOOL_ROOT = Path(__file__).resolve().parents[1]


def now():
    return datetime.now(timezone.utc).isoformat()


def identifier(value):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', value):
        raise ValueError('ID must be 1–64 lowercase letters, digits or hyphens')
    return value


def overlaps(a, b):
    return a == b or a in b.parents or b in a.parents


def write_json(path, value):
    # Same-directory replacement: readers never see partially written JSON.
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as f:
        temp = Path(f.name)
        try:
            json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        except BaseException:
            temp.unlink(missing_ok=True)
            raise
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def read_json(path):
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict) or value.get('schema_version') != 1:
        raise ValueError(f'unsupported or invalid record: {path}')
    return value


def git_snapshot(cwd):
    def get(*args):
        try:
            p = subprocess.run(['git', '-C', str(cwd), *args], capture_output=True, text=True, timeout=5)
            return p.stdout.strip() if p.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            return None
    root = get('rev-parse', '--show-toplevel')
    dirty = get('status', '--porcelain') if root else None
    return {'root': root, 'branch': get('symbolic-ref', '--short', 'HEAD') if root else None,
            'commit': get('rev-parse', '--verify', 'HEAD') if root else None,
            'dirty': bool(dirty) if dirty is not None else None}


class Store:
    def __init__(self, path):
        self.root = Path(path).expanduser().resolve()
        if overlaps(self.root, TOOL_ROOT):
            raise ValueError('record store must be separate from tool source')

    def path(self, *parts):
        path = self.root.joinpath(*parts)
        resolved = path.resolve()
        if resolved != self.root and self.root not in resolved.parents:
            raise ValueError('record path escapes store (possibly a symlink)')
        # Managed records cannot alias each other through symlinks.
        for node in (path, *path.parents):
            if node == self.root:
                break
            if node.is_symlink():
                raise ValueError('symlink inside record store is unsupported')
        return path

    def init(self):
        self.root.mkdir(parents=True, exist_ok=True)
        config = self.path('config.json')
        if config.exists():
            read_json(config)
        else:
            # Exclusive create prevents concurrent init from replacing configuration.
            with config.open('x', encoding='utf-8') as f:
                json.dump({'schema_version': 1, 'created_at': now(), 'sync_status': 'local_only'}, f)
        self.path('projects').mkdir(exist_ok=True)
        return {'path': str(self.root), 'sync_status': 'local_only'}

    def ready(self):
        read_json(self.path('config.json'))

    def project(self, project_id):
        self.ready()
        return self.path('projects', identifier(project_id))

    def add_project(self, project_id, source, name=None):
        directory = self.project(project_id)
        source = Path(source).expanduser().resolve(strict=True)
        if not source.is_dir():
            raise ValueError('source must be a directory')
        if overlaps(source, self.root):
            raise ValueError('source must be separate from records')
        directory.mkdir()
        record = {'schema_version': 1, 'project_id': project_id, 'name': name or project_id,
                  'source': str(source), 'created_at': now()}
        write_json(directory / 'project.json', record)
        (directory / 'overview.md').write_text(f'# {record["name"]}\n\n프로젝트: `{project_id}`\n\n목적·환경·데이터 식별 정보: 미작성\n', encoding='utf-8')
        (directory / 'tasks').mkdir()
        (directory / 'runs').mkdir()
        return {**record, 'path': str(directory)}

    def start_task(self, project_id, title, task_id=None):
        project = self.project(project_id)
        read_json(self.path('projects', project_id, 'project.json'))
        if not title.strip():
            raise ValueError('title must not be empty')
        task_id = identifier(task_id or 'task-' + uuid.uuid4().hex)
        directory = self.path('projects', project_id, 'tasks', task_id)
        directory.mkdir()
        record = {'schema_version': 1, 'project_id': project_id, 'task_id': task_id,
                  'title': title, 'created_at': now(), 'sync_status': 'local_only', 'document_commit': None}
        write_json(directory / 'task.json', record)
        templates = {
            'plan.md': '## 목적\n미작성\n\n## 범위와 방법\n미작성\n\n## 완료 기준\n미작성\n',
            'implementation.md': '## 변경 파일과 이전/이후 동작\n미작성\n\n## 결정과 이유\n미작성\n\n## 남은 작업\n미작성\n',
            'testing.md': f'실행 결과는 [../../runs/](../../runs/)의 metadata.json에서 task_id=`{task_id}`로 조회하세요.\n\n각 실행의 testing.md와 원본 stdout.log/stderr.log를 확인하세요. 실행 전 테스트 결과는 미확인입니다.\n'}
        for name, body in templates.items():
            (directory / name).write_text(f'# {title}\n\n{body}', encoding='utf-8')
        return {**record, 'path': str(directory)}

    def status(self):
        self.ready()
        projects = []
        for directory in sorted(self.path('projects').iterdir()):
            project = self.project(directory.name)
            item = read_json(self.path('projects', directory.name, 'project.json'))
            item['tasks'] = [read_json(self.path('projects', directory.name, 'tasks', d.name, 'task.json'))
                             for d in sorted((project / 'tasks').iterdir())]
            item['runs'] = [read_json(self.path('projects', directory.name, 'runs', d.name, 'metadata.json'))
                            for d in sorted((project / 'runs').iterdir())]
            projects.append(item)
        return {'path': str(self.root), 'sync_status': 'local_only', 'projects': projects}

    def run(self, project_id, task_id, argv, cwd=None, timeout=None):
        project = self.project(project_id)
        record = read_json(self.path('projects', project_id, 'project.json'))
        identifier(task_id)
        read_json(self.path('projects', project_id, 'tasks', task_id, 'task.json'))
        if not argv:
            raise ValueError('command required after --')
        if timeout is not None and (not math.isfinite(timeout) or timeout <= 0):
            raise ValueError('timeout must be finite and positive')
        source = Path(record['source']).resolve(strict=True)
        cwd = Path(cwd).expanduser().resolve(strict=True) if cwd else source
        if not cwd.is_dir() or (cwd != source and source not in cwd.parents):
            raise ValueError('cwd must be a directory inside source')
        if overlaps(source, self.root):
            raise ValueError('source now overlaps record store')
        run_id = 'run-' + uuid.uuid4().hex
        directory = self.path('projects', project_id, 'runs', run_id)
        directory.mkdir()
        m = {'schema_version': 1, 'project_id': project_id, 'task_id': task_id, 'run_id': run_id,
             'argv': argv, 'cwd': str(cwd), 'started_at': now(), 'ended_at': None,
             'wall_seconds': None, 'status': 'running', 'exit_code': None, 'cli_exit_code': None,
             'git': git_snapshot(source), 'recorder_environment': {'os': platform.platform(), 'python': platform.python_version()},
             'target_environment': None, 'artifacts': None, 'test_summary': None,
             'logs': {'stdout': 'stdout.log', 'stderr': 'stderr.log'},
             'task_path': f'../../tasks/{task_id}', 'sync_status': 'local_only', 'document_commit': None, 'error': None}
        write_json(directory / 'metadata.json', m)
        started = time.monotonic()
        process = None
        old_handlers = {}

        def interrupted(signum, frame):
            raise InterruptedError(signum)

        def stop():
            if process is None:
                return
            if os.name == 'posix':
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                # Kill group after grace period, including surviving descendants.
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    pass
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            else:
                process.terminate()
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    process.kill()
            process.wait()

        try:
            for sig in (signal.SIGINT, signal.SIGTERM):
                old_handlers[sig] = signal.signal(sig, interrupted)
            with (directory / 'stdout.log').open('wb') as stdout, (directory / 'stderr.log').open('wb') as stderr:
                process = subprocess.Popen(argv, cwd=cwd, stdout=stdout, stderr=stderr, start_new_session=os.name == 'posix')
                m['exit_code'] = process.wait(timeout=timeout)
                code = m['exit_code']
                m['cli_exit_code'] = code if code >= 0 else 128 - code
                m['status'] = 'succeeded' if code == 0 else 'failed'
        except subprocess.TimeoutExpired:
            stop()
            m.update(status='timed_out', exit_code=process.returncode, cli_exit_code=124)
        except (InterruptedError, KeyboardInterrupt) as exc:
            # Ignore additional interrupt signals while preserving the final record.
            for sig in old_handlers:
                signal.signal(sig, signal.SIG_IGN)
            stop()
            signum = exc.args[0] if isinstance(exc, InterruptedError) else signal.SIGINT
            m.update(status='interrupted', exit_code=process.returncode if process else None, cli_exit_code=128 + signum)
        except OSError as exc:
            stop()
            m.update(status='launch_error', cli_exit_code=127, error=str(exc))
        finally:
            m.update(ended_at=now(), wall_seconds=time.monotonic() - started)
            try:
                write_json(directory / 'metadata.json', m)
                (directory / 'testing.md').write_text(
                    f'# 실행 {run_id}\n\n작업: [{task_id}](../../tasks/{task_id}/plan.md)\n\n'
                    f'상태: {m["status"]}\n\n종료 코드: {m["exit_code"]}\n\n'
                    f'시작: {m["started_at"]}\n\n종료: {m["ended_at"]}\n\n'
                    f'Wall seconds: {m["wall_seconds"]}\n\n'
                    '테스트 수·PASS·실패·스킵 해석: 미확인\n\n'
                    '[메타데이터](metadata.json) · [stdout](stdout.log) · [stderr](stderr.log)\n', encoding='utf-8')
            finally:
                for sig, handler in old_handlers.items():
                    signal.signal(sig, handler)
        return {'run_id': run_id, 'path': str(directory), 'status': m['status'], 'exit_code': m['exit_code']}, m['cli_exit_code']
