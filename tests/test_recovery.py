import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer', ROOT / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.source = ROOT / 'pre-flight'
        self.dests = [self.root / p / 'pre-flight' for p in installer.TARGETS.values()]
        for dest in self.dests:
            dest.mkdir(parents=True)
            (dest / 'custom').write_text('old')

    def tearDown(self):
        self.temp.cleanup()

    def run_install(self):
        return installer.install(self.source, self.root, list(installer.TARGETS), force=True)

    def assert_originals(self):
        for dest in self.dests:
            self.assertEqual((dest / 'custom').read_text(), 'old')
        self.assertFalse(list(self.root.rglob('.pre-flight-install-*')))

    def test_partial_copy_failure(self):
        def fail(src, dest, **kwargs):
            Path(dest).mkdir()
            (Path(dest) / 'partial').write_text('partial')
            raise OSError('copy failure')
        with patch.object(installer.shutil, 'copytree', side_effect=fail):
            with self.assertRaises(OSError):
                self.run_install()
        self.assert_originals()

    def test_second_swap_failure_restores_all(self):
        rename = Path.rename
        def fail(path, dest):
            if path.name == 'new' and Path(dest) == self.dests[1]:
                raise OSError('swap failure')
            return rename(path, dest)
        with patch.object(Path, 'rename', fail):
            with self.assertRaises(OSError):
                self.run_install()
        self.assert_originals()

    def test_symlink_restored_on_swap_failure(self):
        dest = self.dests[0]
        installer.shutil.rmtree(dest)
        target = self.root / 'shared'
        target.mkdir()
        (target / 'custom').write_text('old')
        dest.symlink_to(target, target_is_directory=True)
        rename = Path.rename
        def fail(path, to):
            if path.name == 'new':
                raise OSError('swap failure')
            return rename(path, to)
        with patch.object(Path, 'rename', fail):
            with self.assertRaises(OSError):
                self.run_install()
        self.assertTrue(dest.is_symlink())
        self.assertEqual(dest.resolve(), target)
        self.assert_originals()

    def test_stages_are_beside_destinations_and_backups_untouched(self):
        backup = self.dests[0].with_name('pre-flight.bak')
        backup.mkdir()
        (backup / 'saved').write_text('keep')
        rename = Path.rename
        def inspect(path, to):
            if path.name == 'new':
                self.assertEqual(path.parent.parent, Path(to).parent)
            return rename(path, to)
        with patch.object(Path, 'rename', inspect):
            self.run_install()
        self.assertEqual((backup / 'saved').read_text(), 'keep')
        for dest in self.dests:
            self.assertTrue((dest / 'SKILL.md').exists())

    def test_failed_restoration_retains_recovery_files(self):
        rename = Path.rename
        def fail(path, to):
            if path.name in ('new', 'previous'):
                raise OSError('simulated storage failure')
            return rename(path, to)
        with patch.object(Path, 'rename', fail):
            with self.assertRaisesRegex(RuntimeError, 'Recovery incomplete'):
                self.run_install()
        backups = list(self.root.rglob('previous/custom'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), 'old')

    def test_rules_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.root / '.pre-flight').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                installer.install(self.source, self.root, ['claude'], True, True)
        self.assert_originals()
