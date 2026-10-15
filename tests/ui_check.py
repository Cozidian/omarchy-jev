"""Graphical checks: catalogue browsing, read-only result and a denied power request."""
import json
import subprocess
import time


def run(argv):
    return subprocess.run(argv, check=True, capture_output=True, text=True, timeout=45).stdout.strip()


def status():
    try: return json.loads(run(['omarchy-shell','shell','call','io.github.cozidian.jev','status','{}']))
    except (ValueError,subprocess.SubprocessError): return {}


def wait_for(predicate, timeout=12):
    end = time.monotonic()+timeout
    while time.monotonic() < end:
        state = status()
        if predicate(state): return state
        time.sleep(.2)
    raise AssertionError('UI did not reach expected state: '+str(status()))


def open_launcher():
    run(['omarchy-shell','shell','summon','io.github.cozidian.jev','{}'])
    end = time.monotonic() + 12
    while True:
        try:
            state = wait_for(lambda s:s.get('opened') and s.get('count',0)>0, timeout=2)
            break
        except AssertionError:
            if time.monotonic() >= end: raise
            run(['omarchy-shell','shell','summon','io.github.cozidian.jev','{}'])
    layers = json.loads(run(['hyprctl','-j','layers']))
    found = any(r.get('namespace')=='omarchy-jev-launcher' for monitor in layers.values() for group in monitor['levels'].values() for r in group)
    if not found: raise AssertionError('No JEV layer; will not type into another application.')
    time.sleep(.5)
    return state


def main():
    try:
        first = open_launcher()
        run(['wtype','-M','ctrl','b','-m','ctrl'])
        wait_for(lambda s:s.get('browsing'))
        run(['wtype','brightness'])
        filtered = wait_for(lambda s:0<s.get('filtered',0)<s.get('count',0))
        run(['grim','/tmp/jev-catalogue-browse.png'])
        print('Catalogue:',first['count'],'entries; brightness filter:',filtered['filtered'],'matches.',flush=True)
        run(['wtype','-k','Return'])
        inspected = wait_for(lambda s:not s.get('browsing') and s.get('heading')=='Safe options available')
        if inspected.get('outcome'): raise AssertionError('Inspecting a catalogue row must not execute it.')
        print('Inspecting a row did not execute it.',flush=True)

        open_launcher()
        run(['wtype','Which Omarchy version is installed?','-k','Return'])
        state = wait_for(lambda s:s.get('outcome')=='applied',timeout=50)
        if state.get('heading')!='omarchy version': raise AssertionError(state)
        run(['grim','/tmp/jev-catalogue-result.png'])
        print('Read-only version result rendered.',flush=True)

        open_launcher()
        run(['wtype','Reboot the computer','-k','Return'])
        state = wait_for(lambda s:s.get('outcome')=='suggestion',timeout=50)
        if state.get('heading')!='omarchy system reboot': raise AssertionError(state)
        run(['grim','/tmp/jev-catalogue-suggestion.png'])
        print('Reboot showed suggestion-only guidance.',flush=True)
    finally:
        run(['omarchy-shell','shell','hide','io.github.cozidian.jev'])


if __name__ == '__main__': main()
