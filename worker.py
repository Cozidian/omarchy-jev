#!/usr/bin/env python3
"""One-shot catalogue discovery, typed JEV routing and bounded desktop execution."""
import argparse
import json
import os
import subprocess
import sys
from urllib.error import HTTPError, URLError
# Helpers live in a hot-reloaded plugin directory: bytecode writes would
# trigger a plugin reload while its discovery request is still opening the UI.
sys.dont_write_bytecode = True
import catalogue
import routing
import credentials
import transport

EXAMPLES = ['My eyes feel tired', 'Set brightness to 45%', 'It is too loud',
            'Remind me to stretch in twenty minutes', 'Show my reminders',
            'Which Omarchy version is installed?', 'Open my downloads',
            'Øynene mine er slitne', 'Skru ned lyden']


def run(argv, capture=True):
    # A long-lived app must not inherit output pipes that keep communicate() open.
    result = subprocess.run(argv, check=True, stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, text=True, timeout=15,
                            env={k:v for k,v in os.environ.items() if k != 'TYPESAFE_API_KEY'})
    return (result.stdout or '').strip()


def execute(operation):
    if not operation or catalogue.policy(operation.get('route'))['mode'] == 'suggestion':
        raise ValueError('No executable operation.')
    if operation['kind'] == 'nightlight':
        status = json.loads(run(['omarchy', 'toggle', 'nightlight', '--status']))
        if type(status.get('enabled')) is not bool: raise ValueError('Night light status unavailable.')
        state = operation['state']
        target = not status['enabled'] if state == 'toggle' else state == 'on'
        if status['enabled'] != target:
            run(['omarchy', 'toggle', 'nightlight'], capture=False)
        after = json.loads(run(['omarchy', 'toggle', 'nightlight', '--status']))
        if after.get('enabled') != target: raise RuntimeError('Night light did not reach the requested state.')
        return None
    if operation['kind'] == 'panel':
        if run(operation['argv'], capture=True) != 'ok': raise RuntimeError('Settings panel unavailable.')
        return None
    return run(operation['argv'], capture=operation['kind'] == 'read')


def api_key():
    return credentials.load()


def ask(payload):
    return transport.ask(payload, api_key())


def load_catalogue():
    rows = catalogue.discover(supplements=True)
    warnings = []
    try: rows.extend(catalogue.discover_shortcuts())
    except (subprocess.SubprocessError,OSError,ValueError):
        warnings.append('Active keyboard shortcuts unavailable. Open JEV in your Hyprland session.')
    return rows, warnings


def decide(text, rows=None):
    return routing.resolve(text, rows if rows is not None else load_catalogue()[0], ask)


def perform(text, preview=False):
    rows, warnings = load_catalogue()
    if isinstance(text,str) and text.strip().casefold() in ('help','hjelp','?'):
        return {'status':'help','title':f'Browse {len(rows)} available actions',
                'detail':'Use Browse actions to search every discovered command.\n\nTry:\n'+'\n'.join(EXAMPLES)}
    decision = decide(text,rows)
    return routing.apply(decision['route'],decision['params'],decision['intent'],execute,
                         preview=preview,source=decision['source'],rows=rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview', action='store_true', help='Classify and validate without running any desktop action')
    parser.add_argument('--catalogue', action='store_true', help='Discover current Omarchy commands; no JEV request or execution')
    parser.add_argument('--examples', action='store_true')
    args = parser.parse_args()
    request_id = None
    try:
        if args.catalogue:
            rows, warnings = load_catalogue()
            result = {'entries':rows,'count':len(rows),'omarchyCount':sum(r['route'].startswith('omarchy ') for r in rows),
                      'shortcutCount':sum(r.get('kind')=='shortcut' for r in rows),'warnings':warnings}
        elif args.examples:
            result = {'status':'help','title':'Try one of these','detail':'\n'.join(EXAMPLES)}
        else:
            incoming = sys.stdin.buffer.read(8193)
            if len(incoming) > 8192: raise ValueError('Request too large.')
            message = json.loads(incoming)
            request_id = message.get('requestId')
            if request_id is not None and (type(request_id) is not int or not 0 <= request_id <= 2147483647):
                raise ValueError('Invalid request ID.')
            text = message['text']
            result = perform(text, args.preview)
    except HTTPError as error:
        error.close()
        result = {'status':'error','title':'Nothing changed','detail':f'JEV returned HTTP {error.code}. Check your key, quota or connection and try again.'}
    except (URLError,TimeoutError):
        result = {'status':'error','title':'Nothing changed','detail':'Could not reach JEV. Check the connection and try again.'}
    except (subprocess.SubprocessError,OSError):
        result = {'status':'error','title':'Action could not be completed','detail':'A local command failed or timed out. Check the catalogue, device or application before trying again.'}
    except credentials.SetupError as error:
        result = {'status':'error','title':'Configure API key','detail':str(error)}
    except (ValueError,KeyError,TypeError):
        result = {'status':'error','title':'Could not complete the request','detail':'Invalid request, local status or JEV response. Check the desktop state before retrying.'}
    except Exception:
        result = {'status':'error','title':'Action could not be completed','detail':'Check the desktop state before trying again.'}
    if request_id is not None: result['requestId'] = request_id
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__': main()
