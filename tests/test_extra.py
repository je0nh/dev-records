import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import unittest
from test_cli import Fixtures, ROOT, cli_command


class Extra(Fixtures):
    def test_git_snapshot(self):
        subprocess.run(['git', 'init', '-q', str(self.source)], check=True)
        subprocess.run(['git', '-C', str(self.source), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '--allow-empty', '-qm', 'fixture'], check=True)
        (self.source / 'dirty.txt').write_text('local change')
        task = self.setup_task()
        _, m = self.run_cmd(task, 'print("git")')
        self.assertTrue(m['git']['dirty'])
        self.assertEqual(len(m['git']['commit']), 40)
        self.assertEqual(m['git']['root'], str(self.source.resolve()))

    def test_literal_argv_and_cwd(self):
        task = self.setup_task()
        sub = self.source / '하위 경로'
        sub.mkdir()
        p = self.call('run', '--project', 'alpha', '--task', task, '--cwd', str(sub), '--', sys.executable, '-c', 'import sys; print(sys.argv[1])', 'space ; $(echo unsafe) 한글')
        path = Path(p['path'])
        m = json.loads((path / 'metadata.json').read_text())
        self.assertEqual(m['argv'][-1], 'space ; $(echo unsafe) 한글')
        self.assertEqual(m['cwd'], str(sub.resolve()))
        self.assertEqual((path / 'stdout.log').read_text().strip(), m['argv'][-1])

    def test_symlink_escape(self):
        task = self.setup_task()
        external = self.base / 'external'
        external.mkdir()
        try:
            (self.store / 'projects' / 'escape').symlink_to(external, target_is_directory=True)
        except OSError as exc:
            if os.name == 'nt' and getattr(exc, 'winerror', None) == 1314:
                self.skipTest('Windows symlink creation privilege is unavailable')
            raise
        self.call('task', 'start', '--project', 'escape', '--title', 'blocked', expected=2)
        (self.source / 'outside').symlink_to(external, target_is_directory=True)
        self.call('run', '--project', 'alpha', '--task', task, '--cwd', str(self.source / 'outside'), '--', 'anything', expected=2)
        self.assertEqual(list(external.iterdir()), [])

    def test_invalid_records_and_arguments(self):
        self.call('status', expected=2)
        self.call('init')
        self.call('project', 'add', '--id', 'missing', '--source', str(self.base / 'absent'), expected=2)
        f = self.base / 'file'
        f.write_text('not directory')
        self.call('project', 'add', '--id', 'file', '--source', str(f), expected=2)
        self.call('project', 'add', '--id', 'alpha', '--source', str(self.source))
        self.call('task', 'start', '--project', 'alpha', '--title', '  ', expected=2)
        self.call('task', 'start', '--project', 'absent', '--title', 'missing', expected=2)
        t = self.call('task', 'start', '--project', 'alpha', '--title', 't')['task_id']
        self.call('run', '--project', 'alpha', '--task', t, '--', expected=2)
        self.call('run', '--project', 'alpha', '--task', t, expected=2)
        for timeout in ('0', '-1', 'inf'):
            self.call('run', '--project', 'alpha', '--task', t, '--timeout', timeout, '--', 'anything', expected=2)
        (self.store / 'config.json').write_text('{"schema_version": 99}')
        self.call('init', expected=2)

    def test_bundle_from_other_cwd(self):
        copy = self.base / '설치 복사본'
        copy.mkdir()
        for name in ('dev_records', 'scripts', 'skills', 'docs', '.codex-plugin'):
            shutil.copytree(ROOT / name, copy / name, ignore=shutil.ignore_patterns('__pycache__'))
        for name in ('plugin.json', 'pyproject.toml', 'uv.lock'):
            shutil.copyfile(ROOT / name, copy / name)
        p = subprocess.run([sys.executable, str(copy / 'scripts/dev-records.py'), '--store', str(self.store), 'init'], cwd=self.source, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)['sync_status'], 'local_only')
        manifest = json.loads((copy / 'plugin.json').read_text())
        self.assertEqual(manifest['name'], 'dev-records')
        self.assertTrue((copy / 'skills/dev-records/SKILL.md').exists())

    @unittest.skipUnless(os.name == 'posix', 'POSIX signal test')
    def test_sigterm_and_child_signal(self):
        t = self.setup_task()
        _, m = self.run_cmd(t, 'import os, signal; os.kill(os.getpid(), signal.SIGTERM)', expected=143)
        self.assertEqual(m['exit_code'], -15)
        self.assertEqual(m['status'], 'failed')
        p = subprocess.Popen([*cli_command(), '--store', str(self.store), 'run', '--project', 'alpha', '--task', t, '--', sys.executable, '-c', 'import time; print("ready", flush=True); time.sleep(20)'], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if any('ready' in x.read_text() for x in self.store.glob('projects/alpha/runs/*/stdout.log')):
                    break
                time.sleep(0.02)
            else:
                self.fail('child never ready')
            p.terminate()
            out, err = p.communicate(timeout=5)
            self.assertEqual(p.returncode, 143, err)
            self.assertEqual(json.loads(out)['status'], 'interrupted')
        finally:
            if p.poll() is None:
                p.kill()
                p.communicate()


    def test_tool_can_record_its_own_development(self):
        self.call('init')
        self.call('project', 'add', '--id', 'self', '--source', str(ROOT))
        task = self.call('task', 'start', '--project', 'self', '--title', 'self validation')['task_id']
        self.call('run', '--project', 'self', '--task', task, '--', sys.executable, '-c', 'print("self")')

    def test_uv_plugin_environment_from_other_project(self):
        copy = self.base / 'uv 설치 복사본'
        copy.mkdir()
        for name in ('dev_records', 'scripts', 'skills', 'docs', '.codex-plugin'):
            shutil.copytree(ROOT / name, copy / name, ignore=shutil.ignore_patterns('__pycache__'))
        for name in ('pyproject.toml', 'uv.lock', 'plugin.json'):
            shutil.copyfile(ROOT / name, copy / name)
        uv = shutil.which('uv')
        self.assertIsNotNone(uv, 'uv is required for development')
        args = [uv, 'run', '--locked', '--offline', '--no-python-downloads', '--cache-dir', str(self.base / 'uv-cache'), '--project', str(copy), '--python', sys.executable]
        p = subprocess.run([*args, 'python', '-c', 'import sys,json; print(json.dumps({"isolated": sys.prefix != sys.base_prefix, "prefix": sys.prefix}))'], cwd=self.source, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        environment = json.loads(p.stdout)
        self.assertTrue(environment['isolated'])
        self.assertEqual(Path(environment['prefix']).resolve(), (copy / '.venv').resolve())
        p = subprocess.run([*args, 'python', str(copy / 'scripts/dev-records.py'), '--store', str(self.store), 'init'], cwd=self.source, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)['sync_status'], 'local_only')
