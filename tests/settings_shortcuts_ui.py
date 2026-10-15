"""Open settings without modifying connections; inspect an actual shortcut."""
import json
import time
from ui_check import run, open_launcher, wait_for


def plugins():
    return json.loads(run(['omarchy-shell','shell','listPlugins']))


def wait_panel(target):
    end = time.monotonic()+45
    while time.monotonic()<end:
        layers = json.loads(run(['hyprctl','-j','layers']))
        namespaces = {r.get('namespace') for monitor in layers.values() for rows in monitor['levels'].values() for r in rows}
        if 'omarchy-keyboard-panel' in namespaces and 'omarchy-jev-launcher' not in namespaces:
            return
        time.sleep(.25)
    raise AssertionError('Panel did not open and receive handoff: '+target)


try:
    catalogue = json.loads(run(['python3','worker.py','--catalogue']))
    known_chords = {r['chord'] for r in catalogue['entries'] if r.get('kind')=='shortcut'}
    state = open_launcher()
    assert state['shortcutCount']>0,state
    run(['wtype','-M','ctrl','b','-m','ctrl'])
    wait_for(lambda s:s.get('browsing'))
    run(['wtype','shortcut Super+B'])
    wait_for(lambda s: s.get('filtered',0)>0 and s.get('filtered',0)<s.get('count',0))
    run(['wtype','-k','Return'])
    state = wait_for(lambda s:s.get('heading') in known_chords)
    assert not state.get('outcome'),state
    run(['grim','/tmp/jev-shortcut-discovery.png'])
    print('Actual shortcut '+state['heading']+' inspected; no keys invoked.',flush=True)
    for phrase,target,name in [('Open Bluetooth settings','omarchy.bluetooth','bluetooth'),
                               ('Open Wi-Fi settings','omarchy.network','wifi')]:
        open_launcher()
        run(['wtype',phrase,'-k','Return'])
        wait_panel(target)
        time.sleep(.5)
        run(['grim','/tmp/jev-settings-'+name+'.png'])
        print(phrase+': panel active, JEV dismissed.',flush=True)
        run(['omarchy-shell','shell','hide',target])
finally:
    for target in ['io.github.cozidian.jev','omarchy.bluetooth','omarchy.network']:
        run(['omarchy-shell','shell','hide',target])
