import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import catalogue


def command(route, args='', **extra):
    return dict(route=route, group=route.split()[1], summary='A command', args=args,
                examples=[], aliases=[], requires_sudo=False, hidden=False, **extra)


class CatalogueTests(unittest.TestCase):
    def test_every_discovered_route_has_a_group_and_is_searchable(self):
        rows = catalogue.normalize({'ok': True, 'commands': [command('omarchy version'), command('omarchy system reboot')]})
        groups = catalogue.groups(rows)
        self.assertEqual({r['route'] for bucket in groups.values() for r in bucket}, {r['route'] for r in rows})
        self.assertEqual(len(rows), 2)

    def test_large_groups_are_split_below_choice_limit_without_losing_routes(self):
        rows = catalogue.normalize({'ok': True, 'commands': [command(f'omarchy test action{i}') for i in range(600)]})
        groups = catalogue.groups(rows)
        self.assertEqual(sum(map(len, groups.values())), 600)
        self.assertTrue(all(len(bucket) <= 220 for bucket in groups.values()))

    def test_unknown_no_sudo_and_malicious_routes_are_not_execution_permission(self):
        self.assertEqual(catalogue.policy('omarchy future harmless')['mode'], 'suggestion')
        rows = catalogue.normalize({'ok': True, 'commands': [command('omarchy version; touch /tmp/pwned')]})
        self.assertEqual(rows, [])

    def test_shortcuts_are_discovered_without_command_payloads_or_execution(self):
        rows = catalogue.discover_shortcuts(lambda: [
            {'modmask':64,'key':'B','description':'Browser','dispatcher':'exec','arg':'secret-command'},
            {'modmask':65,'key':'Q','description':'Close window','dispatcher':'killactive','arg':''},
        ])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['kind'], 'shortcut')
        self.assertTrue(all(r['mode']=='suggestion' for r in rows))
        self.assertNotIn('secret-command', str(rows))
        self.assertEqual({r['chord'] for r in rows}, {'Super+B','Shift+Super+Q'})

    def test_shortcut_context_and_release_are_preserved(self):
        rows = catalogue.discover_shortcuts(lambda: [
            {'modmask':0,'key':'R','description':'Resize','submap':'resize','release':True},
            {'modmask':0,'key':'R','description':'Regular action','submap':''},
        ])
        self.assertEqual(len(rows), 2)
        self.assertIn('resize',str(rows))
        self.assertTrue(any('release' in r['summary'].lower() for r in rows))

    def test_refresh_does_not_use_a_stale_snapshot(self):
        values = iter([{'ok': True, 'commands': [command('omarchy version')]},
                       {'ok': True, 'commands': [command('omarchy version'), command('omarchy future command')]}])
        self.assertEqual(len(catalogue.discover(lambda: next(values))), 1)
        self.assertEqual(len(catalogue.discover(lambda: next(values))), 2)


if __name__ == '__main__': unittest.main()
