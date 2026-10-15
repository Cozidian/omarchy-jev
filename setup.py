#!/usr/bin/env python3
"""Configure a TypeSafe key in a hidden terminal prompt, or check the saved key."""
import sys
sys.dont_write_bytecode = True
import argparse
import getpass
import credentials
import transport


def check(key):
    response = transport.ask({'model':'jev-latest', 'state':'Connection test.', 'questions':{
        'connection': {'type':'choice', 'instructions':'Select ready.', 'criteria':{'ready':'Connection is ready.', 'other':'Other.'}}}}, key)
    if not isinstance(response, dict) or response.get('answers', {}).get('connection', {}).get('choice') != 'ready':
        raise credentials.SetupError('Unexpected API response; previous key preserved.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--from-env', action='store_true', help='Validate and save TYPESAFE_API_KEY; never pass a key as an argument')
    group.add_argument('--check', action='store_true', help='Make a small live API request with the configured key')
    args = parser.parse_args()
    interactive = not args.from_env and not args.check
    try:
        if args.check:
            check(credentials.load())
            print('TypeSafe connection verified. Key not displayed.')
        else:
            if interactive and (not sys.stdin.isatty() or not sys.stderr.isatty()):
                raise credentials.SetupError('Run setup.py in a terminal for a hidden prompt, or use --from-env.')
            credentials.prepare()
            key = credentials.environment() if args.from_env else credentials.validate(getpass.getpass('TypeSafe API key (hidden): '))
            check(key)
            credentials.save(key)
            print('Verified and saved privately to ~/.config/omarchy/jev/api-key (600).')
            print('The saved file takes precedence over TYPESAFE_API_KEY. Reopen JEV to use it.')
    except credentials.SetupError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (Exception, KeyboardInterrupt):
        print('Setup could not complete. Check the connection, key and file permissions. Previous key preserved.', file=sys.stderr)
        return 1
    finally:
        if interactive and sys.stdin.isatty():
            try: input('Press Enter to close…')
            except (EOFError, KeyboardInterrupt): pass
    return 0

if __name__ == '__main__': sys.exit(main())
