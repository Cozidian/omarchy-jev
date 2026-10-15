#!/usr/bin/env python3
"""Install user-owned files; never modifies packaged Omarchy files."""
from datetime import datetime
import os
from pathlib import Path
import shutil
import stat

root = Path(__file__).resolve().parent
home = Path.home()
plugin = home / '.config/omarchy/plugins/io.github.cozidian.jev'
stamp = datetime.now().strftime('%Y%m%d%H%M%S')
plugin.mkdir(parents=True, exist_ok=True)
for name in ('manifest.json', 'Overlay.qml', 'BarWidget.qml', 'worker.py', 'catalogue.py', 'routing.py', 'README.md'):
    dest = plugin / name
    if dest.is_symlink(): raise SystemExit(f'Refusing symlink: {dest}')
    if dest.exists() and dest.read_bytes() == (root / name).read_bytes(): continue
    if dest.exists(): shutil.copy2(dest, dest.with_name(name + '.bak.' + stamp))
    shutil.copy2(root / name, dest)
key = os.environ.get('TYPESAFE_API_KEY', '').strip()
if key:
    folder = home / '.config/omarchy/jev'
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = folder / 'api-key'
    if not path.exists() and not path.is_symlink():
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as stream: stream.write(key + '\n')
        print('Configured private API key file; key not displayed.')
    else:
        print('Existing API key file preserved.')
bindings = home / '.config/hypr/bindings.lua'
line = 'o.bind("SUPER + ALT + J", "JEV Launcher", "omarchy-shell shell toggle io.github.cozidian.jev")'
text = bindings.read_text()
if line not in text:
    if 'SUPER + ALT + J' in text:
        raise SystemExit('Shortcut already appears in user bindings; plugin installed, binding left unchanged.')
    shutil.copy2(bindings, bindings.with_name('bindings.lua.bak.jev.' + stamp))
    bindings.write_text(text.rstrip() + '\n\n-- Natural language desktop launcher\n' + line + '\n')
print('Installed:', plugin)
print('Shortcut: Super+Alt+J')
print('Next: omarchy-shell shell rescanPlugins; omarchy plugin enable io.github.cozidian.jev')
