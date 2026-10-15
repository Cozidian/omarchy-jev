"""Discover Omarchy routes. Discovery never grants execution permission."""
import json
import re
import subprocess

# Explicit operation schemas. Everything outside this table is suggestion-only.
PARAMETERS = {
    'omarchy toggle nightlight': 'nightlight',
    'omarchy brightness display': 'brightness',
    'omarchy brightness keyboard': 'keyboard',
    'omarchy audio output volume': 'volume',
    'omarchy audio input mute': 'microphone',
    'omarchy reminder': 'reminder',
    'desktop folders': 'folder',
    'desktop speaker mute': 'speaker',
    'desktop microphone mute': 'microphone',
}
CAPABILITIES = {
    'nightlight': 'Screen colour temperature: turn night light ON for tired/burning eyes, OFF for neutral colours, or explicitly toggle. Adapter sets desired state idempotently.',
    'brightness': 'Display too bright/dark: decrease/increase brightness; set a stated absolute percentage from 5% to 100%. Display off is suggestion-only.',
    'volume': 'Speaker too loud/quiet: decrease/increase volume, mute/unmute, or set a stated absolute percentage 0% to 100%. The adapter supports absolute values as well as relative steps.',
    'keyboard': 'Keyboard backlight brightness up, down, off or restore.',
    'reminder': 'Set a reminder from stated minutes/hours and source text, or show reminders. Clearing reminders is suggestion-only.',
    'folder': 'Open home or Downloads folder; requests such as needing downloaded files count as opening Downloads.',
    'speaker': 'Set speaker mute ON (silence) or OFF (restore sound).',
    'microphone': 'Set microphone mute ON for privacy. This adapter is idempotent; enabling/unmuting is suggestion-only.',
}
UI_PANELS = {
    'desktop settings bluetooth':'omarchy.bluetooth',
    'desktop settings wifi':'omarchy.network',
}
READ_ONLY = {'omarchy version', 'omarchy version branch', 'omarchy version channel',
             'omarchy version pkgs', 'omarchy theme list'}
NO_ARGUMENTS = {'omarchy launch browser', 'omarchy launch nautilus', 'omarchy launch terminal',
                'omarchy notification battery', 'omarchy notification time'} | READ_ONLY | set(UI_PANELS)
SUPPLEMENTS = [
    {'route':'desktop settings bluetooth','group':'bluetooth','summary':'Open Bluetooth settings panel without changing power, pairing or connections','args':''},
    {'route':'desktop settings wifi','group':'network','summary':'Open Wi-Fi / wireless network settings panel without changing connections','args':''},
    {'route': 'desktop folders', 'group': 'desktop', 'summary': 'Open the home or Downloads folder', 'args': '<home|downloads>'},
    {'route': 'desktop speaker mute', 'group': 'desktop', 'summary': 'Set speaker mute on or off without toggling', 'args': '<on|off>'},
    {'route': 'desktop microphone mute', 'group': 'desktop', 'summary': 'Mute microphone for privacy; enabling it is suggestion-only', 'args': '<on>'},
]


def policy(route):
    if route in NO_ARGUMENTS:
        return {'mode': 'automatic', 'label': 'Runs automatically', 'schema': 'no_arguments'}
    if route in PARAMETERS:
        return {'mode': 'validated', 'label': 'Safe options available', 'schema': PARAMETERS[route]}
    return {'mode': 'suggestion', 'label': 'Suggestion only', 'schema': None}


def normalize(body):
    if not isinstance(body, dict) or body.get('ok') is not True or not isinstance(body.get('commands'), list):
        raise ValueError('Omarchy did not return a valid command catalogue.')
    result = {}
    for item in body['commands']:
        if not isinstance(item, dict): continue
        route = item.get('route', '')
        if not isinstance(route, str) or not re.fullmatch(r'omarchy(?: [a-z0-9][a-z0-9-]*)+', route): continue
        group = route.split()[1]
        # Only plain metadata is retained; the binary/executor field is never consumed.
        row = {'route': route, 'group': group, 'summary': str(item.get('summary', ''))[:1200],
               'args': str(item.get('args', ''))[:1200], 'hidden': item.get('hidden') is True,
               'requires_sudo': item.get('requires_sudo') is True,
               'examples': [s[:1500] for s in item.get('examples', []) if isinstance(s, str)][:8],
               'aliases': [s[:500] for s in item.get('aliases', []) if isinstance(s, str)][:8]}
        row.update(policy(route) if not row['requires_sudo'] else {'mode':'suggestion','label':'Suggestion only','schema':None})
        result[route] = row
    return sorted(result.values(), key=lambda r: r['route'])


def discover(read=None, supplements=False):
    if read is None:
        def read():
            output = subprocess.run(['omarchy', 'commands', '--all', '--json'], check=True,
                                    capture_output=True, text=True, timeout=10)
            return json.loads(output.stdout)
    rows = normalize(read())
    if supplements:
        rows.extend(dict(r, examples=[], aliases=[], hidden=False, requires_sudo=False, **policy(r['route'])) for r in SUPPLEMENTS)
    return sorted(rows, key=lambda r: r['route'])


def groups(rows):
    grouped = {}
    for row in rows:
        grouped.setdefault(row['group'], []).append(row)
    # Keep a spare option for 'none' under TypeSafe's 255-option limit.
    output = {}
    for name, bucket in sorted(grouped.items()):
        for start in range(0, len(bucket), 220):
            key = name if len(bucket) <= 220 else f'{name}_{start // 220 + 1}'
            output[key] = bucket[start:start + 220]
    if len(output) > 254:
        raise ValueError('The command catalogue has too many groups; please refine discovery grouping.')
    return output


def discover_shortcuts(read=None):
    """Use actual active bindings; never retain or send dispatcher arguments."""
    if read is None:
        def read():
            output = subprocess.run(['hyprctl','-j','binds'],check=True,capture_output=True,text=True,timeout=5)
            return json.loads(output.stdout)
    bindings = read()
    if not isinstance(bindings,list): raise ValueError('Active shortcuts unavailable.')
    result = {}
    modifiers = [(1,'Shift'),(2,'CapsLock'),(4,'Ctrl'),(8,'Alt'),(64,'Super'),(16,'Mod2'),(32,'Mod3'),(128,'Mod5')]
    for binding in bindings:
        if not isinstance(binding,dict): continue
        mask = binding.get('modmask',0)
        if type(mask) is not int: continue
        key = binding.get('key')
        if not key: key = 'code:'+str(binding['keycode']) if binding.get('keycode') else 'Any key'
        key = str(key)
        chord = '+'.join([label for bit,label in modifiers if mask & bit] + [key.upper() if len(key)==1 else key])
        submap = str(binding.get('submap') or '')
        conditions = []
        if submap: conditions.append('submap: '+submap)
        if binding.get('release'): conditions.append('on release')
        if binding.get('longPress'): conditions.append('long press')
        context = ' ('+', '.join(conditions)+')' if conditions else ''
        route = 'shortcut '+chord+context
        description = str(binding.get('description') or 'Undescribed keyboard shortcut')[:500]
        summary = description+context
        if route in result:
            if summary not in result[route]['summary']: result[route]['summary'] += '; '+summary
            continue
        result[route] = {'route':route,'group':'shortcuts','kind':'shortcut','chord':chord,'context':context,
                         'summary':summary,'args':'','examples':[],'aliases':[chord,description],
                         'hidden':False,'requires_sudo':False,'mode':'suggestion','label':'Keyboard shortcut · information only','schema':None}
    return sorted(result.values(),key=lambda r:r['route'])
