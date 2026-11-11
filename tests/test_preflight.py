import importlib.util
import json
import os
from pathlib import Path
import shutil
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

    def test_dev_base_discovery(self):
        dev_repo_tmp = tempfile.TemporaryDirectory()
        dev_repo = Path(dev_repo_tmp.name)
        subprocess.run(['git', '-C', str(dev_repo), 'init', '-b', 'dev'], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(dev_repo), 'config', 'user.name', 'Test'], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(dev_repo), 'config', 'user.email', 'test@example.invalid'], check=True, capture_output=True)
        (dev_repo / 'file.txt').write_text('initial\n')
        subprocess.run(['git', '-C', str(dev_repo), 'add', '.'], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(dev_repo), 'commit', '-m', 'initial'], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(dev_repo), 'checkout', '-b', 'feature/test'], check=True, capture_output=True)
        (dev_repo / 'file.txt').write_text('modified\n')
        r = pf.collect(dev_repo)
        self.assertEqual(r['base'], 'dev')
        dev_repo_tmp.cleanup()

    def test_commit_hygiene_and_branch_tracking(self):
        self.git('checkout', '-b', 'bugfix/OB-213')
        (self.repo / 'price.py').write_text('price = 10\n')
        self.git('commit', '-am', 'OB-213. Expose full ancestor chain')
        (self.repo / 'price.py').write_text('price = 11\n')
        self.git('commit', '-am', 'wip: fixup test')
        r = pf.collect(self.repo)
        self.assertEqual(r['branch'], 'bugfix/OB-213')
        self.assertEqual(len(r['commits']), 2)
        warnings = r.get('commit_hygiene_warnings', [])
        self.assertTrue(any("has work-in-progress subject: 'wip: fixup test'" in w for w in warnings))

    def test_affected_modules(self):
        (self.repo / 'apps' / 'gam').mkdir(parents=True)
        (self.repo / 'apps' / 'gam' / 'app.ts').write_text('export const a = 1;\n')
        (self.repo / 'libs' / 'auth').mkdir(parents=True)
        (self.repo / 'libs' / 'auth' / 'auth.ts').write_text('export const auth = 1;\n')
        r = pf.collect(self.repo, scope='working')
        self.assertIn('apps/gam', r.get('affected_modules', []))
        self.assertIn('libs/auth', r.get('affected_modules', []))

    def test_check_with_env(self):
        r = pf.check(self.repo, 'env_test', [sys.executable, '-c', 'import os; print(os.environ.get("MY_ENV_VAR"))'],
                     env_vars=['MY_ENV_VAR=PREFLIGHT_OK'])
        self.assertEqual(r['status'], 'PASS')
        self.assertEqual(r['output'].strip(), 'PREFLIGHT_OK')

    def test_installer_with_rules(self):
        dest_tmp = tempfile.TemporaryDirectory()
        dest_repo = Path(dest_tmp.name)
        command = [sys.executable, str(ROOT / 'install.py'), '--repo', str(dest_repo), '--init-rules']
        res = subprocess.run(command, capture_output=True)
        self.assertEqual(res.returncode, 0)
        rules_path = dest_repo / '.pre-flight' / 'rules.md'
        self.assertTrue(rules_path.exists())
        self.assertIn('Pre-Flight Repository Rules Template', rules_path.read_text())
        dest_tmp.cleanup()

    def test_commit_hygiene_conventional_and_fixup(self):
        self.git('checkout', '-b', 'bugfix/OB-999')
        (self.repo / 'price.py').write_text('price = 10\n')
        self.git('commit', '-am', 'fixup! OB-999. some fix')
        (self.repo / 'price.py').write_text('price = 11\n')
        self.git('commit', '-am', 'squash! OB-999. another fix')
        (self.repo / 'price.py').write_text('price = 12\n')
        self.git('commit', '-am', 'feat(core): add pricing')
        r = pf.collect(self.repo)
        warnings = r.get('commit_hygiene_warnings', [])
        self.assertTrue(any("has work-in-progress subject: 'fixup! OB-999. some fix'" in w for w in warnings))
        self.assertTrue(any("has work-in-progress subject: 'squash! OB-999. another fix'" in w for w in warnings))
        self.assertFalse(any('feat(core)' in w for w in warnings))

    def test_commit_hygiene_breaking_change(self):
        self.git('checkout', '-b', 'bugfix/OB-999')
        (self.repo / 'price.py').write_text('price = 10\n')
        self.git('commit', '-am', 'feat!: breaking change')
        (self.repo / 'price.py').write_text('price = 11\n')
        self.git('commit', '-am', 'fix(api)!: another breaking')
        r = pf.collect(self.repo)
        self.assertEqual(len(r.get('commit_hygiene_warnings', [])), 0)

    def test_installer_recovery(self):
        # Install first
        subprocess.run([sys.executable, str(ROOT / 'install.py'), '--repo', str(self.repo), '--init-rules'], check=True)
        # Mock failure by turning a destination directory into a file, causing rename to fail
        dest_file = self.repo / '.claude/skills/pre-flight'
        shutil.rmtree(dest_file)
        dest_file.write_text('blocked')
        # Attempt force install
        res = subprocess.run([sys.executable, str(ROOT / 'install.py'), '--repo', str(self.repo), '--force'], capture_output=True)
        self.assertNotEqual(res.returncode, 0)
        self.assertTrue(dest_file.is_file()) # Remained as the file (rollback succeeded)
        self.assertTrue((self.repo / '.gemini/skills/pre-flight/SKILL.md').exists()) # Untouched and restored


if __name__ == '__main__':
    unittest.main()
