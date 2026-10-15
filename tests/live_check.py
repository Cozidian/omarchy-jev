"""Live full-catalogue classification only: no action executor is called."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import worker
import catalogue
import routing

cases = [
 ('Open Bluetooth settings', 'desktop settings bluetooth', 'preview'),
 ('Open Wi-Fi settings', 'desktop settings wifi', 'preview'),
 ('Åpne wifi-innstillinger', 'desktop settings wifi', 'preview'),
 ('What keyboard shortcut opens the browser?', 'shortcut', 'suggestion'),
 ('Which keyboard shortcut closes a window?', 'shortcut', 'suggestion'),
 ('My eyes feel tired', 'omarchy toggle nightlight', 'preview'),
 ('my eyes feel fired', 'omarchy toggle nightlight', 'preview'),
 ('Øynene mine er slitne', 'omarchy toggle nightlight', 'preview'),
 ('Turn off night light', 'omarchy toggle nightlight', 'preview'),
 ('It is too loud', 'omarchy audio output volume', 'preview'),
 ('Skjermen er for lys', 'omarchy brightness display', 'preview'),
 ('Set brightness to 45%', 'omarchy brightness display', 'preview'),
 ('Set speaker volume to 35%', 'omarchy audio output volume', 'preview'),
 ('Make the keyboard backlight brighter', 'omarchy brightness keyboard', 'preview'),
 ('I need my downloads', 'desktop folders', 'preview'),
 ('Open a terminal', 'omarchy launch terminal', 'preview'),
 ('Mute my microphone', {'desktop microphone mute','omarchy audio input mute'}, {'preview','suggestion'}),
 ('Remind me to stretch in twenty minutes', 'omarchy reminder', 'preview'),
 ('Minn meg på å strekke meg om tjue minutter', 'omarchy reminder', 'preview'),
 ('Show my reminders', 'omarchy reminder', 'preview'),
 ('Clear all my reminders', 'omarchy reminder', 'suggestion'),
 ('Which Omarchy version is installed?', 'omarchy version', 'preview'),
 ('List the available themes', 'omarchy theme list', 'preview'),
 ('Switch to the Tokyo Night theme', 'omarchy theme set', 'suggestion'),
 ('Reboot the computer', 'omarchy system reboot', 'suggestion'),
 ('Install Spotify', {'omarchy install service spotify','omarchy pkg add'}, 'suggestion'),
 ('Remove the Minecraft launcher', 'omarchy remove gaming minecraft', 'suggestion'),
 ('Do not turn on night light', None, 'unchanged'),
 ('Warm the screen and delete my downloads', None, {'suggestion','unchanged'}),
 ('Run touch /tmp/jev-untrusted', None, {'suggestion','unchanged'}),
 ('Delete all my downloads', None, {'suggestion','unchanged'}),
]
rows, warnings = worker.load_catalogue()
print('Catalogue:',len(rows),'entries;',sum(r.get('kind')=='shortcut' for r in rows),'shortcuts.',flush=True)
failures = 0
for phrase, expected, status in cases:
    decision = worker.decide(phrase, rows)
    def forbidden(_): raise AssertionError('preview must never execute')
    result = routing.apply(decision['route'],decision['params'],decision['intent'],forbidden,
                           preview=True,source=decision['source'],rows=rows)
    # For unsupported/mixed requests, only verify that execution was rejected.
    route_ok = result['route'] in expected if isinstance(expected,set) else result['route']==expected
    if expected == 'shortcut': route_ok = str(result.get('route','')).startswith('shortcut ')
    if expected is None and result['status'] in ('suggestion','unchanged'): route_ok = True
    status_ok = result['status'] in status if isinstance(status,set) else result['status']==status
    ok = route_ok and status_ok
    print(('PASS' if ok else 'FAIL'), repr(phrase), '=>', result.get('route'), result['status'], flush=True)
    if not ok:
        failures += 1
        print('Decision:', decision, flush=True)
    if result['status']=='preview' and phrase.startswith('Remind me'):
        print('Reminder preview:',result['detail'],flush=True)
print(f'{len(cases)-failures}/{len(cases)} checks passed; no desktop actions executed.')
raise SystemExit(bool(failures))
