"""Private Linux credential storage. Values never enter argv, logs or QML."""
import os
from pathlib import Path
import re
import secrets
import stat

MAX_KEY_BYTES = 4096


class SetupError(ValueError):
    """Only fixed, credential-free messages may use this exception."""


def validate(key):
    if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9._~+/=-]{8,4096}', key):
        raise SetupError('Invalid API key format. Paste only the token, without spaces or control characters.')
    return key


def folder_fd(create=False):
    # Walk each component by fd: no ancestor symlink may redirect credentials.
    fd = os.open(Path.home(), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in ('.config', 'omarchy', 'jev'):
            if create:
                try: os.mkdir(part, mode=0o700, dir_fd=fd)
                except FileExistsError: pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
            if os.fstat(fd).st_uid != os.getuid():
                raise SetupError('Credential directories must belong to the current user.')
        if create: os.fchmod(fd, 0o700)
        elif os.fstat(fd).st_mode & 0o077:
            raise SetupError('API key directory must be private. Run setup.py to repair permissions.')
        return fd
    except BaseException:
        os.close(fd)
        raise


def read_at(directory, repair=False, content=True):
    fd = os.open('api-key', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
            raise SetupError('API key must be a user-owned regular file with one link.')
        if repair: os.fchmod(fd, 0o600)
        elif info.st_mode & 0o077:
            raise SetupError('API key file must be private. Run setup.py to repair permissions.')
        if not content: return None
        data = os.read(fd, MAX_KEY_BYTES + 2)
        if len(data) > MAX_KEY_BYTES + 1:
            raise SetupError('API key file is too large.')
        try: key = data.decode('ascii').removesuffix('\n')
        except UnicodeError: raise SetupError('Invalid API key encoding.') from None
        return validate(key)
    finally:
        os.close(fd)


def load():
    try: directory = folder_fd()
    except FileNotFoundError: return environment()
    try:
        try: return read_at(directory)
        except FileNotFoundError: return environment()
    finally: os.close(directory)


def environment():
    key = os.environ.get('TYPESAFE_API_KEY', '')
    if not key: raise SetupError('Configure your TypeSafe API key using Configure key or setup.py.')
    return validate(key)


def prepare():
    directory = folder_fd(create=True)
    try:
        try: read_at(directory, repair=True, content=False)
        except FileNotFoundError: pass
    finally: os.close(directory)


def save(key):
    key = validate(key)
    directory = folder_fd(create=True)
    temporary = '.key-' + secrets.token_hex(16)
    try:
        try: read_at(directory, repair=True, content=False)
        except FileNotFoundError: pass
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write((key+'\n').encode('ascii'))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, 'api-key', src_dir_fd=directory, dst_dir_fd=directory)
            os.fsync(directory)
        finally:
            try: os.unlink(temporary, dir_fd=directory)
            except FileNotFoundError: pass
    finally: os.close(directory)
