"""Exercise installation with a fresh HOME, no desktop or network needed."""
import importlib.util
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('jev_install', ROOT / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def test_fresh_install_copies_runtime_without_credentials_or_binding_edits(self):
        with tempfile.TemporaryDirectory() as home, patch.object(Path, 'home', return_value=Path(home)), patch.dict(os.environ, {'TYPESAFE_API_KEY':'synthetic-private-token'}), patch('sys.stdout', io.StringIO()):
            installer.install()
            plugin = Path(home)/'.config/omarchy/plugins/io.github.cozidian.jev'
            for name in installer.FILES: self.assertEqual((plugin/name).read_bytes(), (ROOT/name).read_bytes())
            self.assertFalse((Path(home)/'.config/omarchy/jev').exists())
            self.assertFalse((Path(home)/'.config/hypr').exists())
            installer.install()  # Reinstallation is safe.

    def test_symlink_parent_refused(self):
        with tempfile.TemporaryDirectory() as home, patch.object(Path, 'home', return_value=Path(home)):
            outside = Path(home)/'outside'
            outside.mkdir()
            (Path(home)/'.config').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(OSError): installer.install()
            self.assertEqual(list(outside.iterdir()), [])

    def test_symlink_leaf_refused_before_other_files_change(self):
        with tempfile.TemporaryDirectory() as home, patch.object(Path, 'home', return_value=Path(home)):
            plugin = Path(home)/'.config/omarchy/plugins/io.github.cozidian.jev'
            plugin.mkdir(parents=True)
            outside = Path(home)/'outside'
            outside.write_text('keep this')
            (plugin/'worker.py').symlink_to(outside)
            with self.assertRaises(ValueError): installer.install()
            self.assertEqual(outside.read_text(), 'keep this')
            self.assertFalse((plugin/'manifest.json').exists())
