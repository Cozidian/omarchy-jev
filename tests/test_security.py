"""Offline regressions: credentials and HTTP requests must fail closed."""
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import worker


class SecurityTests(unittest.TestCase):
    def test_invalid_header_never_reaches_transport(self):
        with patch.dict(os.environ, {'TYPESAFE_API_KEY': 'synthetic\ncredential'}), patch.object(Path, 'home', return_value=Path('/nonexistent-jev-test')):
            with patch.object(worker, 'perform', side_effect=ValueError('synthetic-private-value')):
                output = io.StringIO()
                with patch.object(sys, 'argv', ['worker.py']), patch.object(sys, 'stdin', type('Input', (), {'buffer': io.BytesIO(b'{"text":"test"}')})()), patch('sys.stdout', output):
                    worker.main()
                self.assertNotIn('synthetic-private-value', output.getvalue())

    def test_file_takes_precedence_over_environment(self):
        with tempfile.TemporaryDirectory() as home:
            folder = Path(home) / '.config/omarchy/jev'
            folder.mkdir(parents=True, mode=0o700)
            key = folder / 'api-key'
            key.write_text('synthetic-file-token\n')
            key.chmod(0o600)
            with patch.object(Path, 'home', return_value=Path(home)), patch.dict(os.environ, {'TYPESAFE_API_KEY':'synthetic-env-token'}):
                self.assertEqual(worker.api_key(), 'synthetic-file-token')


import credentials
import transport
import importlib.util
spec = importlib.util.spec_from_file_location('jev_setup', Path(__file__).resolve().parents[1] / 'setup.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)
from urllib.request import Request
from urllib.error import HTTPError


class CredentialStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.patcher = patch.object(Path, 'home', return_value=self.home)
        self.patcher.start()
        credentials.save('synthetic-original-token')
        self.folder = self.home / '.config/omarchy/jev'
        self.key = self.folder / 'api-key'

    def tearDown(self):
        self.patcher.stop()
        self.temp.cleanup()

    def test_atomic_private_rotation(self):
        credentials.save('synthetic-replacement-token')
        self.assertEqual(credentials.load(), 'synthetic-replacement-token')
        self.assertEqual(self.key.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.folder.stat().st_mode & 0o777, 0o700)
        self.assertEqual([p.name for p in self.folder.iterdir()], ['api-key'])

    def test_fifo_symlink_hardlink_rejected_without_blocking(self):
        self.key.unlink()
        os.mkfifo(self.key, 0o600)
        with self.assertRaises(credentials.SetupError): credentials.load()
        with self.assertRaises(credentials.SetupError): credentials.save('synthetic-replacement-token')
        self.key.unlink()
        outside = self.home / 'outside'
        outside.write_text('synthetic-outside-token')
        self.key.symlink_to(outside)
        with self.assertRaises(OSError): credentials.load()
        with self.assertRaises(OSError): credentials.save('synthetic-replacement-token')
        self.key.unlink()
        os.link(outside, self.key)
        with self.assertRaises(credentials.SetupError): credentials.load()
        self.assertEqual(outside.read_text(), 'synthetic-outside-token')

    def test_parent_symlink_rejected(self):
        self.key.unlink()
        self.folder.rmdir()
        other = self.home / 'other'
        other.mkdir()
        self.folder.symlink_to(other, target_is_directory=True)
        with self.assertRaises(OSError): credentials.save('synthetic-replacement-token')
        self.assertEqual(list(other.iterdir()), [])

    def test_overly_open_permissions_fail_then_setup_repairs(self):
        self.folder.chmod(0o755)
        self.key.chmod(0o644)
        with self.assertRaises(credentials.SetupError): credentials.load()
        credentials.prepare()
        self.assertEqual(credentials.load(), 'synthetic-original-token')
        self.assertEqual(self.key.stat().st_mode & 0o777, 0o600)

    def test_invalid_and_oversized_tokens_rejected(self):
        for token in ('synthetic\nprivate-token', 'synthetic\rprivate-token', 'a'*4097, ' short ', ''):
            with self.assertRaises(credentials.SetupError): credentials.validate(token)
        self.key.write_text('a'*5000)
        with self.assertRaises(credentials.SetupError): credentials.load()

    def test_failed_validation_preserves_previous_key_and_redacts(self):
        output = io.StringIO()
        with patch.object(sys, 'argv', ['setup.py','--from-env']), patch.dict(os.environ, {'TYPESAFE_API_KEY':'synthetic-replacement-token'}), patch.object(setup, 'check', side_effect=RuntimeError('synthetic-replacement-token')), patch('sys.stderr', output):
            self.assertEqual(setup.main(), 1)
        self.assertNotIn('synthetic-replacement-token', output.getvalue())
        self.assertEqual(credentials.load(), 'synthetic-original-token')

    def test_successful_validation_saves_only_after_check(self):
        observed = []
        def check(key):
            observed.append(credentials.load())
        with patch.object(sys, 'argv', ['setup.py','--from-env']), patch.dict(os.environ, {'TYPESAFE_API_KEY':'synthetic-replacement-token'}), patch.object(setup, 'check', check), patch('sys.stdout', io.StringIO()):
            self.assertEqual(setup.main(), 0)
        self.assertEqual(observed, ['synthetic-original-token'])
        self.assertEqual(credentials.load(), 'synthetic-replacement-token')


class TransportTests(unittest.TestCase):
    def test_all_redirects_refused_including_same_host(self):
        request = Request(transport.ENDPOINT, data=b'{}', headers={'Authorization':'Bearer synthetic-token'})
        for code in (301,302,303,307,308):
            for destination in ('https://other.invalid/collect', transport.ENDPOINT, 'http://api.typesafe.ai/'):
                with self.assertRaises(HTTPError) as caught:
                    transport.NoRedirect().redirect_request(request, None, code, '', {}, destination)
                caught.exception.close()

    def test_invalid_header_rejected_before_network(self):
        with patch.object(transport, 'build_opener') as opener:
            with self.assertRaises(credentials.SetupError): transport.ask({}, 'synthetic\nprivate-token')
            opener.assert_not_called()

    def test_response_size_enforced(self):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'x'*(transport.MAX_RESPONSE+1)
        with patch.object(transport, 'build_opener') as opener:
            opener.return_value.open.return_value = response
            with self.assertRaises(credentials.SetupError): transport.ask({}, 'synthetic-token')
        response.__enter__.return_value.read.assert_called_once_with(transport.MAX_RESPONSE+1)

class SetupLaunchTests(unittest.TestCase):
    def test_terminal_is_detached_and_does_not_inherit_key(self):
        with patch.object(sys, 'argv', ['setup.py','--launch']), patch.dict(os.environ, {'TYPESAFE_API_KEY':'synthetic-private-token'}), patch.object(setup.subprocess, 'Popen') as launch:
            self.assertEqual(setup.main(), 0)
        self.assertEqual(launch.call_args.args[0][:4], ['omarchy','launch','terminal','python3'])
        self.assertTrue(launch.call_args.kwargs['start_new_session'])
        self.assertNotIn('TYPESAFE_API_KEY',launch.call_args.kwargs['env'])
        self.assertEqual(launch.call_args.kwargs['stdout'], setup.subprocess.DEVNULL)
