#!/usr/bin/env python3
"""Copy a local checkout into the user plugin directory. No credentials or config edits."""
import sys
sys.dont_write_bytecode = True
import os
from pathlib import Path
import stat

FILES = ('manifest.json', 'Overlay.qml', 'BarWidget.qml', 'worker.py', 'catalogue.py',
         'routing.py', 'credentials.py', 'transport.py', 'setup.py', 'README.md', 'LICENSE', 'SECURITY.md')


def install():
    root = Path(__file__).resolve().parent
    plugin = Path.home() / '.config/omarchy/plugins/io.github.cozidian.jev'
    fd = os.open(Path.home(), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in ('.config','omarchy','plugins','io.github.cozidian.jev'):
            try: os.mkdir(part, mode=0o700, dir_fd=fd)
            except FileExistsError: pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
            if os.fstat(fd).st_uid != os.getuid(): raise ValueError('Destination must be user-owned.')
        # Preflight every target before changing anything. Refuse links/devices/FIFOs.
        for name in FILES:
            try: info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            except FileNotFoundError: continue
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
                raise ValueError('Unsafe plugin destination.')
        for name in FILES:
            if root == plugin.resolve(): continue  # Stock plugin add clones here directly.
            data = (root / name).read_bytes()
            temporary = '.' + name + '.install-' + str(os.getpid())
            target = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
            try:
                with os.fdopen(target, 'wb') as stream: stream.write(data)
                os.replace(temporary, name, src_dir_fd=fd, dst_dir_fd=fd)
            finally:
                try: os.unlink(temporary, dir_fd=fd)
                except FileNotFoundError: pass
    finally: os.close(fd)
    print('Installed:', plugin)
    print('Next: python3 ' + str(plugin / 'setup.py'))
    print('Then: omarchy plugin validate ' + str(plugin))
    print('Enable: omarchy plugin enable io.github.cozidian.jev')
    print('Existing shortcuts and credentials are unchanged. See README for optional shortcut setup.')

if __name__ == '__main__':
    try: install()
    except Exception: sys.exit('Installation refused an unsafe destination or could not copy files. No credentials were accessed.')
