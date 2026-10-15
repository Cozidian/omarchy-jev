"""Exercise the installed overlay and restore the original screen temperature."""
import json
from pathlib import Path
import subprocess
import time
from ui_check import open_launcher


def run(argv):
    return subprocess.run(argv, check=True, capture_output=True, text=True, timeout=30).stdout.strip()

before = json.loads(run(['omarchy', 'toggle', 'nightlight', '--status']))
try:
    open_launcher()
    run(['wtype', 'my eyes feel tired', '-k', 'Return'])
    time.sleep(12)
    after = json.loads(run(['omarchy', 'toggle', 'nightlight', '--status']))
    run(['grim', '/tmp/jev-action.png'])
    print('Night light after submitting tired-eyes request:', after, flush=True)
    if after.get('enabled') is not True:
        raise SystemExit('Night light was not enabled. Inspect /tmp/jev-action.png')
finally:
    if type(before.get('temperature')) is int:
        try:
            run(['hyprctl', 'hyprsunset', 'temperature', str(before['temperature'])])
        finally:
            run(['omarchy-shell', 'shell', 'hide', 'io.github.cozidian.jev'])
    elif not before.get('enabled'):
        state = json.loads(run(['omarchy', 'toggle', 'nightlight', '--status']))
        if state.get('enabled'): run(['omarchy', 'toggle', 'nightlight'])
    run(['omarchy-shell', 'shell', 'hide', 'io.github.cozidian.jev'])
    print('Restored original night light state:', run(['omarchy', 'toggle', 'nightlight', '--status']))
