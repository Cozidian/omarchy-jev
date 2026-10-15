import sys
import unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import worker
import routing


class ExecutorTests(unittest.TestCase):
    def test_launch_commands_do_not_hold_output_pipes_open(self):
        with patch.object(worker.subprocess, 'run') as command:
            command.return_value.stdout = ''
            worker.execute(routing.plan('omarchy launch browser', {'launch_payload':'plain'}))
        self.assertEqual(command.call_args.kwargs.get('stdout'), worker.subprocess.DEVNULL)
        self.assertEqual(command.call_args.kwargs.get('stderr'), worker.subprocess.DEVNULL)

    def test_night_light_on_is_idempotent(self):
        calls = []
        def run(argv, capture=True):
            calls.append(argv)
            return '{"enabled": true}'
        with patch.object(worker, 'run', run):
            worker.execute(routing.plan('omarchy toggle nightlight', {'nightlight':'on'}))
        self.assertEqual(len(calls), 2)
        self.assertTrue(all('--status' in call for call in calls))

    def test_night_light_change_checks_final_state(self):
        calls = []
        answers = iter(['{"enabled": false}', '', '{"enabled": true}'])
        def run(argv, capture=True):
            calls.append(argv)
            return next(answers)
        with patch.object(worker, 'run', run):
            worker.execute(routing.plan('omarchy toggle nightlight', {'nightlight':'on'}))
        self.assertEqual(calls[1], ['omarchy', 'toggle', 'nightlight'])
        self.assertIn('--status', calls[2])

    def test_failed_state_change_does_not_report_success(self):
        with patch.object(worker, 'run', return_value='{"enabled": false}'):
            with self.assertRaises(RuntimeError):
                worker.execute(routing.plan('omarchy toggle nightlight', {'nightlight':'on'}))

    def test_missing_panel_acknowledgement_is_an_error(self):
        with patch.object(worker, 'run', return_value='unknown'):
            with self.assertRaises(RuntimeError):
                worker.execute(routing.plan('desktop settings wifi', {}))

    def test_read_only_output_is_returned(self):
        with patch.object(worker, 'run', return_value='3.2.1') as run:
            self.assertEqual(worker.execute(routing.plan('omarchy version',{})), '3.2.1')
            self.assertTrue(run.call_args.kwargs['capture'])


if __name__ == '__main__': unittest.main()
