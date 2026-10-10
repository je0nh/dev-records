import concurrent.futures
import os
import signal
import time
import unittest
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from test_cli import Fixtures, ROOT, cli_command


class Wrappers(Fixtures):
    def execute(self, task, wrapper, expected=0, timeout=None, program=None):
        options = ['--timeout', str(timeout)] if timeout else []
        p = subprocess.run([*cli_command(), '--store', str(self.store), 'run', '--project', 'alpha', '--task', task, '--wrapper', str(wrapper), *options, '--', program or sys.executable, '{wrapper}', '한글 인자'], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(p.returncode, expected, p.stderr)
        path = Path(json.loads(p.stdout)['path'])
        return path, json.loads((path / 'metadata.json').read_text())

    def assert_preserved_and_cleaned(self, path, m, content):
        w = m['wrapper']
        self.assertEqual((path / w['snapshot']).read_bytes(), content)
        self.assertEqual(w['sha256'], hashlib.sha256(content).hexdigest())
        self.assertFalse(Path(w['execution_path']).parent.exists())
        self.assertEqual(w['cleanup_status'], 'removed')
        self.assertEqual(m['requested_argv'][1], '{wrapper}')
        self.assertEqual(m['argv'][1], w['execution_path'])

    def test_wrapper_calls_project_script_and_preserves_source(self):
        task = self.setup_task()
        (self.source / 'target.py').write_text('print("target executed")')
        wrapper = self.base / '일회성 래퍼.py'
        content = b'import runpy, sys\nprint(sys.argv[1])\nrunpy.run_path("target.py")\n'
        wrapper.write_bytes(content)
        path, m = self.execute(task, wrapper)
        self.assert_preserved_and_cleaned(path, m, content)
        self.assertEqual(wrapper.read_bytes(), content)
        self.assertEqual(m['cwd'], str(self.source.resolve()))
        self.assertIn('target executed', (path / 'stdout.log').read_text())
        self.assertIn('한글 인자', (path / 'stdout.log').read_text())
        self.assertEqual(sorted(p.name for p in self.source.iterdir()), ['target.py'])

    def test_failure_timeout_and_launch_error_keep_wrapper(self):
        task = self.setup_task()
        wrapper = self.base / 'launch.py'
        for content, expected, timeout, program, status in (
            (b'raise SystemExit(9)\n', 9, None, None, 'failed'),
            (b'import time\ntime.sleep(10)\n', 124, 0.1, None, 'timed_out'),
            (b'print("unused")\n', 127, None, 'dev-records-missing-program', 'launch_error'),
        ):
            with self.subTest(status=status):
                wrapper.write_bytes(content)
                path, m = self.execute(task, wrapper, expected, timeout, program)
                self.assertEqual(m['status'], status)
                self.assert_preserved_and_cleaned(path, m, content)

    def test_wrapper_validation_before_creating_run(self):
        task = self.setup_task()
        wrapper = self.base / 'launch.py'
        wrapper.write_text('print("unused")')
        self.call('run', '--project', 'alpha', '--task', task, '--wrapper', str(wrapper), '--', sys.executable, '-c', 'print("unused")', expected=2)
        self.call('run', '--project', 'alpha', '--task', task, '--wrapper', str(wrapper), '--', sys.executable, '{wrapper}', '{wrapper}', expected=2)
        self.call('run', '--project', 'alpha', '--task', task, '--wrapper', str(self.base/'missing'), '--', sys.executable, '{wrapper}', expected=2)
        self.call('run', '--project', 'alpha', '--task', task, '--wrapper', str(self.base), '--', sys.executable, '{wrapper}', expected=2)
        self.assertEqual(list(self.store.glob('projects/alpha/runs/*')), [])

    def test_concurrent_wrapper_runs_are_independent(self):
        task = self.setup_task()
        wrapper = self.base / 'launch.py'
        content = b'import time\nprint("ready", flush=True)\ntime.sleep(0.1)\n'
        wrapper.write_bytes(content)
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(lambda _: self.execute(task, wrapper), range(3)))
        self.assertEqual(len({m['wrapper']['execution_path'] for _, m in results}), 3)
        for path, m in results:
            self.assert_preserved_and_cleaned(path, m, content)

    @unittest.skipUnless(os.name == 'posix', 'POSIX signal test')
    def test_interrupt_cleans_only_execution_copy(self):
        task = self.setup_task()
        wrapper = self.base / 'launch.py'
        content = b'import time\nprint("ready", flush=True)\ntime.sleep(20)\n'
        wrapper.write_bytes(content)
        p = subprocess.Popen([*cli_command(), '--store', str(self.store), 'run', '--project', 'alpha', '--task', task, '--wrapper', str(wrapper), '--', sys.executable, '{wrapper}'], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic()+5
            while time.monotonic() < deadline:
                if any('ready' in log.read_text() for log in self.store.glob('projects/alpha/runs/*/stdout.log')):
                    break
                time.sleep(0.02)
            else:
                self.fail('wrapper never ready')
            p.send_signal(signal.SIGTERM)
            out, err = p.communicate(timeout=5)
            self.assertEqual(p.returncode, 143, err)
            path = Path(json.loads(out)['path'])
            m = json.loads((path/'metadata.json').read_text())
            self.assertEqual(m['status'], 'interrupted')
            self.assert_preserved_and_cleaned(path, m, content)
            self.assertEqual(wrapper.read_bytes(), content)
        finally:
            if p.poll() is None:
                p.kill()
                p.communicate()
