#!/usr/bin/env python3
"""The board in a real browser: starts the board of a temp home, opens it in headless Chrome or Chromium and checks the
rendered page: no uncaught JavaScript error, the session of the test state is on it, and with a German browser the
German texts. Without a Chrome it prints `skip` and ends with 0, so `bash test/e2e.sh` and a developer machine are not
affected; CI runs it as its own job (.github/workflows/test.yml). SYN_CHROME names the browser to use.
Usage: python3 test/board_check.py [path of syn.py]. Standard library only, Python 3.9 syntax."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SYN = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'syn.py'
HOOK = SYN.with_name('hook.py')
MAC = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'


def ok(what):
    print(f'ok   {what}', flush=True)


def fail(what, seen=''):
    print(f'FAIL {what}', flush=True)
    if seen:
        print('---- seen:\n' + seen[-3000:], flush=True)
    sys.exit(1)


def chrome():
    named = os.environ.get('SYN_CHROME')
    if named:
        return named if shutil.which(named) or Path(named).is_file() else None
    for x in ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'chrome'):
        if shutil.which(x):
            return shutil.which(x)
    return MAC if Path(MAC).is_file() else None


browser = chrome()
if not browser and os.environ.get('SYN_REQUIRE_CHROME'):
    print('FAIL no Chrome or Chromium found, and SYN_REQUIRE_CHROME is set')
    sys.exit(1)
if not browser:
    print('ok   skipped: board in a browser (no Chrome or Chromium found; SYN_CHROME names one)')
    sys.exit(0)

tmp = Path(tempfile.mkdtemp(prefix='syn-board-'))
home, repo = tmp / 'home', tmp / 'demo'
env = {k: v for k, v in os.environ.items() if not k.startswith(('SYN_', 'CLAUDE'))}
env.update(SYN_HOME=str(home), SYN_REMOTE='', SYN_ME='', SYN_NAME='', SYN_MACHINE='', SYN_UI_PORT='0',
           SYN_INVITES='off', SYN_NOTIFY='log', GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)
py = sys.executable


def run(cmd, **kw):
    if 'input' not in kw:
        kw['stdin'] = subprocess.DEVNULL
    return subprocess.run(cmd, env=env, capture_output=True, timeout=60, **kw)


def dump(url, lang, profile, extra=()):
    """(DOM, log of the browser) of the page after its scripts ran; virtual time lets the board's timers run at once."""
    cmd = [browser, '--headless=new', '--disable-gpu', '--no-sandbox', '--no-first-run', '--disable-extensions',
           '--disable-background-networking', f'--user-data-dir={profile}', f'--lang={lang}', f'--accept-lang={lang}',
           '--enable-logging=stderr', '--v=0', '--virtual-time-budget=6000', '--dump-dom', *extra, url]
    r = subprocess.run(cmd, capture_output=True, timeout=90, stdin=subprocess.DEVNULL,
                       env=dict(env, LANGUAGE=lang, LC_ALL=lang.replace('-', '_') + '.UTF-8'))
    return r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')


def main():
    run(['git', 'init', '-q', '-b', 'main', str(repo)])
    (repo / 'src').mkdir()
    (repo / 'src' / 'a.ts').write_text('one\n', encoding='utf-8')
    run(['git', '-C', str(repo), 'add', '.'])
    run(['git', '-C', str(repo), '-c', 'user.name=test', '-c', 'user.email=test@example.com', 'commit', '-q', '-m', 'init'])
    sid = 'brd11111'
    for event, extra in (('SessionStart', {'source': 'startup'}),
                         ('UserPromptSubmit', {'prompt': 'Build tickets API'}),
                         ('PostToolUse', {'tool_name': 'Edit', 'tool_input': {'file_path': str(repo / 'src' / 'a.ts')}})):
        r = run([py, str(HOOK), event], input=json.dumps(dict(session_id=sid, cwd=str(repo), **extra)).encode())
        if r.returncode:
            fail(f'hook {event} for the test state', r.stderr.decode('utf-8', 'replace'))
    r = run([py, str(SYN), 'ui', '--pair'])
    m = re.search(r'(http://127\.0\.0\.1:\d+)/?#p=([0-9a-z]+)', r.stdout.decode('utf-8', 'replace'))
    if not m:
        fail('syn ui --pair prints an address', (r.stdout + r.stderr).decode('utf-8', 'replace'))
    base = m.group(1)
    ok('the board of a temp home is running')

    for lang, label, words in (('en-US', 'English', ('Messages', 'History')), ('de-DE', 'German', ('Nachrichten', 'Verlauf'))):
        r = run([py, str(SYN), 'ui', '--pair'])  # a code is good once
        url = re.search(r'http://127\.0\.0\.1:\d+/?#p=[0-9a-z]+', r.stdout.decode('utf-8', 'replace')).group(0)
        dom, log = dump(url, lang, tmp / f'profile-{lang}')
        if os.environ.get('BOARD_DUMP'):  # for looking at what the browser made of the page
            Path(os.environ['BOARD_DUMP'] + f'-{lang}.html').write_text(dom + '\n<!-- ' + log + ' -->', encoding='utf-8')
        errors = [x for x in log.splitlines() if 'Uncaught' in x or 'SyntaxError' in x]
        if errors:
            fail(f'the board renders without a JavaScript error ({label})', '\n'.join(errors))
        if '<body' not in dom or len(dom) < 2000:
            fail(f'the board renders ({label})', dom + '\n' + log)
        ok(f'the board renders without a JavaScript error ({label} browser)')
        if f'/{sid}"' not in dom or 'src/a.ts' not in dom or '<span class="name">demo</span>' not in dom:
            fail(f'the session of the test state is on the board ({label})', dom)
        ok(f'the session of the test state is on the board ({label} browser)')
        want = re.search(r'<html[^>]*\blang="([a-z]+)"', dom)
        if not want or want.group(1) != lang[:2]:
            fail(f'the page language follows the browser ({label})', dom[:500])
        ok(f'the page language is {lang[:2]} in the {label} browser')
        for key, w in zip(('nav.messages', 'nav.history'), words):  # the text of the tab, not the script's word list
            if f'data-t="{key}">{w}<' not in dom:
                fail(f'"{w}" is on the {label} tab bar', dom)
        ok(f'the board speaks {label} ({", ".join(words)})')


try:
    main()
finally:
    try:  # the board server of the temp home, as e2e.sh's cleanup ends it
        pid = json.loads((home / 'ui.json').read_text(encoding='utf-8'))['pid']
        if os.name == 'nt':
            subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True)
        else:
            os.kill(pid, 15)
    except (OSError, ValueError, KeyError):
        pass
    shutil.rmtree(tmp, ignore_errors=True)
