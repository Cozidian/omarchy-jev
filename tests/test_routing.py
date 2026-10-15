import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import routing
import catalogue
from test_catalogue import command


def answer(value, probability=.99):
    return {'type': 'choice', 'choice': value, 'confidence': .99, 'probabilities': {value: probability}}


class PolicyTests(unittest.TestCase):
    def test_unknown_destructive_and_unreviewed_routes_never_get_an_executor(self):
        for route in ['omarchy system reboot', 'omarchy pkg add', 'omarchy remove webapps', 'omarchy future harmless', 'omarchy launch 1password']:
            self.assertIsNone(routing.plan(route, {}))

    def test_brightness_supports_validated_percentage_but_not_display_off(self):
        p = routing.plan('omarchy brightness display', {'brightness': '45%'})
        self.assertEqual(p['argv'], ['omarchy', 'brightness', 'display', '45%'])
        for value in ['off', '0%', '101%', '45%; reboot', '--help']:
            self.assertIsNone(routing.plan('omarchy brightness display', {'brightness': value}))

    def test_missing_parameters_clarify_instead_of_defaulting(self):
        self.assertIsNone(routing.plan('omarchy brightness display', {}))
        self.assertIsNone(routing.plan('omarchy reminder', {}))

    def test_reminder_duration_and_message_come_from_source(self):
        params = routing.source_parameters('Remind me to stretch in twenty minutes')
        self.assertEqual(params['duration'], ['20'])
        p = routing.plan('omarchy reminder', {'reminder_operation': 'create', 'duration': '20'}, source=params)
        self.assertEqual(p['argv'][:3], ['omarchy', 'reminder', '20'])
        self.assertIn('stretch', p['argv'][3])
        self.assertIsNone(routing.plan('omarchy reminder', {'reminder_operation': 'create', 'duration': '999'}, source=params))

    def test_fractional_or_negative_durations_are_not_silently_misread(self):
        for text in ['Remind me in 1.5 hours', 'Remind me in -5 minutes']:
            self.assertEqual(routing.source_parameters(text)['duration'], [])
        self.assertEqual(routing.source_parameters('Brightness to 1.5%')['percentages'], [])

    def test_missing_or_privileged_route_cannot_execute(self):
        calls = []
        for rows in [[], [dict(command('omarchy version'), requires_sudo=True)]]:
            result = routing.apply('omarchy version', {}, 'act', calls.append, rows=rows)
            self.assertEqual(result['status'], 'suggestion')
        self.assertEqual(calls, [])

    def test_url_or_shell_payload_is_not_a_plain_app_launch(self):
        for route in ['omarchy launch browser', 'omarchy launch terminal']:
            self.assertIsNone(routing.plan(route, {'launch_payload':'extra'}))
            self.assertIsNone(routing.plan(route, {}))

    def test_reminder_clear_is_suggestion_only(self):
        self.assertIsNone(routing.plan('omarchy reminder', {'reminder_operation': 'clear'}))

    def test_untrusted_argv_or_extra_model_fields_are_ignored(self):
        p = routing.plan('omarchy launch browser', {'launch_payload':'plain', 'argv': ['sh', '-c', 'evil']})
        self.assertEqual(p['argv'], ['omarchy', 'launch', 'browser'])

    def test_negated_or_mixed_request_never_executes_even_with_safe_route(self):
        for intent in ['none', 'suggest']:
            calls = []
            result = routing.apply('omarchy launch browser', {'launch_payload':'plain'}, intent, calls.append)
            self.assertEqual(calls, [])
            self.assertNotEqual(result['status'], 'applied')

    def test_settings_panels_have_fixed_targets_and_handoff(self):
        for route, target in [('desktop settings bluetooth','omarchy.bluetooth'), ('desktop settings wifi','omarchy.network')]:
            operation = routing.plan(route, {})
            self.assertIsNotNone(operation)
            self.assertEqual(operation['argv'], ['omarchy-shell','shell','summon',target,'{}'])
            self.assertEqual(operation['kind'], 'panel')
            calls = []
            result = routing.apply(route, {}, 'act', calls.append)
            self.assertTrue(result['handoff'])
            self.assertEqual(len(calls), 1)
            preview = routing.apply(route, {}, 'act', calls.append, preview=True)
            self.assertFalse(preview.get('handoff',False))
            self.assertEqual(len(calls), 1)

    def test_network_changes_do_not_gain_permission_from_panel_opening(self):
        for route in ['omarchy bluetooth power','omarchy bluetooth device','omarchy network band','omarchy network password']:
            self.assertIsNone(routing.plan(route, {}))

    def test_preview_never_executes(self):
        calls = []
        result = routing.apply('omarchy launch browser', {'launch_payload':'plain'}, 'act', calls.append, preview=True)
        self.assertEqual(result['status'], 'preview')
        self.assertEqual(calls, [])

    def test_group_then_command_questions_include_all_commands_and_ignore_model_argv(self):
        rows = catalogue.normalize({'ok': True, 'commands': [command('omarchy version'), command('omarchy system reboot')]})
        requests = []
        def ask(payload):
            requests.append(payload)
            if len(requests) == 1:
                self.assertIn('system', payload['questions']['group']['criteria'])
                return {'answers': {'group': answer('system'), 'intent': answer('suggest')}}
            self.assertIn('omarchy system reboot', payload['questions']['command']['criteria'])
            return {'answers': {'command': answer('omarchy system reboot')}}
        result = routing.resolve('Reboot my machine', rows, ask)
        self.assertEqual(result['route'], 'omarchy system reboot')
        self.assertEqual(result['intent'], 'suggest')
        self.assertEqual(len(requests), 2)


if __name__ == '__main__': unittest.main()
