import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('preflight', ROOT / 'pre-flight/scripts/preflight.py')
pf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pf)


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')
        (self.repo / 'price.py').write_text('price = 1\n')
        self.git('add', '.')
        self.git('commit', '-m', 'initial')
        self.git('checkout', '-b', 'feature')

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], check=True, capture_output=True)

    def test_all_layers_and_spaces(self):
        (self.repo / 'price.py').write_text('price = 2\n')
        self.git('commit', '-am', 'change')
        (self.repo / 'staged name.py').write_text('x=1\n')
        self.git('add', '.')
        (self.repo / 'price.py').write_text('price = 3\n')
        (self.repo / 'new\nname.py').write_text('x=2\n')
        r = pf.collect(self.repo)
        self.assertEqual(r['layers']['branch'], ['price.py'])
        self.assertIn('staged name.py', r['layers']['staged'])
        self.assertIn('price.py', r['layers']['unstaged'])
        self.assertIn('new\nname.py', r['layers']['untracked'])

    def test_staged_reverted_in_worktree(self):
        (self.repo / 'price.py').write_text('price = 2\n')
        self.git('add', '.')
        (self.repo / 'price.py').write_text('price = 1\n')
        self.assertIn('price.py', pf.collect(self.repo)['layers']['staged'])

    def test_missing_base(self):
        with self.assertRaises(ValueError):
            pf.collect(self.repo, base='does-not-exist')
        self.git('branch', '-D', 'main')
        self.assertEqual(pf.collect(self.repo, 'staged')['scope'], 'staged')

    def test_deleted_and_ignored(self):
        (self.repo / 'price.py').unlink()
        (self.repo / '.gitignore').write_text('ignored\n')
        (self.repo / 'ignored').write_text('secret')
        r = pf.collect(self.repo)
        self.assertIn('price.py', r['files'])
        self.assertNotIn('ignored', r['files'])

    def test_statuses(self):
        for status, script in [('PASS', 'print("ok")'), ('FAIL', 'raise SystemExit(3)')]:
            r = pf.check(self.repo, 'test', [sys.executable, '-c', script])
            self.assertEqual(r['status'], status)
        self.assertEqual(pf.check(self.repo, 'missing', ['nonexistent-preflight-command'])['status'], 'ERROR')
        self.assertEqual(pf.check(self.repo, 'timeout', [sys.executable, '-c', 'import time; time.sleep(3)'], .05)['status'], 'TIMEOUT')

    def test_truncation_and_literal_args(self):
        r = pf.check(self.repo, 'output', [sys.executable, '-c', 'print("x" * 17000)'])
        self.assertTrue(r['output_truncated'])
        r = pf.check(self.repo, 'literal', [sys.executable, '-c', 'import sys; print(sys.argv[1])', '$(echo unsafe)'])
        self.assertEqual(r['output'].strip(), '$(echo unsafe)')

    def test_installer(self):
        command = [sys.executable, str(ROOT / 'install.py'), '--repo', str(self.repo)]
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
        for path in ['.claude', '.agents', '.gemini']:
            self.assertTrue((self.repo / path / 'skills/pre-flight/SKILL.md').exists())
        self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)


if __name__ == '__main__':
    unittest.main()
