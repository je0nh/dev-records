import concurrent.futures
import contextlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from dev_records.cli import main

ROOT = Path(__file__).resolve().parents[1]

def cli_command():
    if os.environ.get("DEV_RECORDS_TRACE_DIR"):
        return [sys.executable, str(ROOT / "tests/trace_cli.py")]
    return [sys.executable, "-m", "dev_records"]


class Fixtures(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='개발 기록 ')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.store = self.base / 'records'
        self.source = self.base / '소스 프로젝트'
        self.source.mkdir()

    def call(self, *args, expected=0):
        p = subprocess.run([*cli_command(), '--store', str(self.store), *args], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(p.returncode, expected, p.stderr + p.stdout)
        return json.loads(p.stdout if expected == 0 else p.stderr)

    def setup_task(self, project='alpha'):
        self.call('init')
        self.call('project', 'add', '--id', project, '--source', str(self.source))
        return self.call('task', 'start', '--project', project, '--title', '첫 작업')['task_id']

    def run_cmd(self, task, code, expected=0, extra=()):
        p = subprocess.run([*cli_command(), '--store', str(self.store), 'run', '--project', 'alpha', '--task', task, *extra, '--', sys.executable, '-c', code], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(p.returncode, expected, p.stderr)
        result = json.loads(p.stdout)
        return Path(result['path']), json.loads((Path(result['path']) / 'metadata.json').read_text())



class CLI(Fixtures):
    def test_supported_runtime_platforms(self):
        for runtime in ('linux', 'darwin', 'win32'):
            with self.subTest(runtime=runtime), patch('dev_records.cli.sys.platform', runtime), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['--store', str(self.store), 'init']), 0)

    def test_success_argv_and_logs(self):
        task = self.setup_task()
        path, m = self.run_cmd(task, 'import sys; print("한글 ; $HOME"); print("warning", file=sys.stderr)')
        self.assertEqual(m['status'], 'succeeded')
        self.assertIn('한글 ; $HOME', (path / 'stdout.log').read_text())
        self.assertIn('warning', (path / 'stderr.log').read_text())
        self.assertGreaterEqual(m['wall_seconds'], 0)
        self.assertIsNone(m['git']['commit'])
        self.assertEqual(m['sync_status'], 'local_only')
        self.assertTrue(m['started_at'].endswith('+00:00'))
        self.assertTrue((path / 'testing.md').exists())
        self.assertEqual(m['cwd'], str(self.source.resolve()))

    def test_failure_retry_and_missing_program(self):
        task = self.setup_task()
        a, m = self.run_cmd(task, 'raise SystemExit(7)', expected=7)
        self.assertEqual(m['status'], 'failed')
        b, _ = self.run_cmd(task, 'print("retry")')
        self.assertNotEqual(a, b)
        p = subprocess.run([*cli_command(), '--store', str(self.store), 'run', '--project', 'alpha', '--task', task, '--', 'dev-records-no-such-executable-123'], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(p.returncode, 127)
        self.assertEqual(json.loads((Path(json.loads(p.stdout)['path']) / 'metadata.json').read_text())['status'], 'launch_error')

    def test_timeout(self):
        task = self.setup_task()
        _, m = self.run_cmd(task, 'import time; print("started", flush=True); time.sleep(10)', expected=124, extra=('--timeout', '0.1'))
        self.assertEqual(m['status'], 'timed_out')

    def test_validation(self):
        self.call('init')
        self.call('init')
        self.call('project', 'add', '--id', '../bad', '--source', str(self.source), expected=2)
        self.call('project', 'add', '--id', 'alpha', '--source', str(self.store), expected=2)
        self.call('project', 'add', '--id', 'alpha', '--source', str(self.source))
        self.call('project', 'add', '--id', 'alpha', '--source', str(self.source), expected=2)
        self.call('task', 'start', '--project', 'alpha', '--title', '작업', '--id', 'fixed')
        self.call('task', 'start', '--project', 'alpha', '--title', '작업', '--id', 'fixed', expected=2)
        self.call('run', '--project', 'alpha', '--task', 'fixed', '--cwd', str(self.base), '--', 'anything', expected=2)
        self.call('run', '--project', 'alpha', '--task', 'fixed', '--timeout', 'nan', '--', 'anything', expected=2)

    def test_concurrent_tasks_and_runs(self):
        task = self.setup_task()
        def work(i):
            t = self.call('task', 'start', '--project', 'alpha', '--title', str(i))['task_id']
            return self.run_cmd(t, f'print({i})')[0]
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            paths = list(pool.map(work, range(4)))
        self.assertEqual(len(set(paths)), 4)
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            paths = list(pool.map(lambda i: self.run_cmd(task, f'print({i})')[0], range(3)))
        self.assertEqual(len(set(paths)), 3)
        self.assertEqual(len(self.call('status')['projects'][0]['runs']), 7)

    @unittest.skipUnless(os.name == 'posix', 'POSIX signal test')
    def test_interrupt(self):
        task = self.setup_task()
        p = subprocess.Popen([*cli_command(), '--store', str(self.store), 'run', '--project', 'alpha', '--task', task, '--', sys.executable, '-c', 'import time; print("ready", flush=True); time.sleep(20)'], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                logs = list(self.store.glob('projects/alpha/runs/*/stdout.log'))
                if logs and 'ready' in logs[0].read_text():
                    break
                time.sleep(0.02)
            else:
                self.fail('child never ready')
            p.send_signal(signal.SIGINT)
            out, err = p.communicate(timeout=5)
            self.assertEqual(p.returncode, 130, err)
            m = json.loads((Path(json.loads(out)['path']) / 'metadata.json').read_text())
            self.assertEqual(m['status'], 'interrupted')
        finally:
            if p.poll() is None:
                p.kill()
                p.communicate()

    def test_two_projects_and_preserved_records(self):
        task = self.setup_task()
        self.run_cmd(task, 'print("python project")')
        second = self.base / 'second project'
        second.mkdir()
        self.call('project', 'add', '--id', 'shell', '--source', str(second))
        t = self.call('task', 'start', '--project', 'shell', '--title', 'shell test')['task_id']
        self.call('run', '--project', 'shell', '--task', t, '--', sys.executable, '-c', 'print("second project")')
        second.rmdir()
        self.assertEqual(len(self.call('status')['projects']), 2)

    @unittest.skipUnless(os.name == 'posix' and Path('/bin/sh').is_file(), 'requires POSIX /bin/sh')
    def test_posix_shell_command(self):
        task = self.setup_task()
        result = self.call('run', '--project', 'alpha', '--task', task, '--', '/bin/sh', '-c', 'printf "shell project"')
        self.assertEqual((Path(result['path']) / 'stdout.log').read_text(), 'shell project')

if __name__ == '__main__':
    unittest.main()
