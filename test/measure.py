#!/usr/bin/env python3
"""Measures how much text Synchronauts writes into Claude's context in a typical flow.
Usage: measure.py <syn.py> <SKILL.md>   (SHOW=1 also prints the texts)"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SYN = str(Path(sys.argv[1]).resolve())
SKILL = Path(sys.argv[2]).read_text(encoding='utf-8')
REAL = '~/.synchronauts/syn.py'  # the path in real use, in case a version prints it
T = Path(tempfile.mkdtemp())
BASE = {k: v for k, v in os.environ.items() if k not in ('CLAUDE_PID', 'CLAUDE_CODE_ENTRYPOINT', 'CLAUDE_CODE_SESSION_ID')}
BASE.update(SYN_REMOTE=str(T / 'remote.git'), SYN_ORGS='acme', SYN_TICK='0.3', SYN_IDLE='60')


def sh(*a):
    subprocess.run(a, check=True, capture_output=True)


def repo(name, slug):
    d = T / name
    sh('git', 'init', '-q', '-b', 'main', str(d))
    sh('git', '-C', str(d), 'remote', 'add', 'origin', f'https://github.com/{slug}.git')
    (d / 'src').mkdir()
    (d / 'src' / 'a.ts').write_text('x')
    sh('git', '-C', str(d), 'add', '-A')
    sh('git', '-C', str(d), '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '-m', 'init')
    return d


def env(who, sid=None):
    e = dict(BASE, SYN_HOME=str(T / f'home-{who}'), SYN_ME=f'{who}-gh', SYN_NAME=who.capitalize(), SYN_MACHINE='one')
    if sid:
        e['CLAUDE_CODE_SESSION_ID'] = f'{sid}-0000-0000'
    return e


def syn(who, *a, sid=None):
    return subprocess.run([sys.executable, SYN, *a], capture_output=True, text=True, env=env(who, sid), timeout=60)


def hook(who, event, sid, cwd, tool=None, path=None):
    d = {'session_id': sid, 'cwd': str(cwd), 'source': 'startup'}
    if tool:
        d.update(tool_name=tool, tool_input={'file_path': str(path)} if path else {})
    r = subprocess.run([sys.executable, SYN, 'hook', event], input=json.dumps(d), capture_output=True, text=True,
                       env=env(who), timeout=60)
    return (json.loads(r.stdout).get('hookSpecificOutput') or {}).get('additionalContext', '') if r.stdout.strip() else ''


def question(who, sid, cwd, path):
    """The hook's answer before an edit; the reason of a permission prompt is only shown to the human."""
    d = {'session_id': sid, 'cwd': str(cwd), 'tool_name': 'Edit', 'tool_input': {'file_path': str(path)}}
    r = subprocess.run([sys.executable, SYN, 'hook', 'PreToolUse'], input=json.dumps(d), capture_output=True,
                       text=True, env=env(who), timeout=60)
    return json.loads(r.stdout).get('hookSpecificOutput') or {} if r.stdout.strip() else {}


def real(text):
    text = text.replace(SYN, REAL)
    for who in ('sam', 'alex'):
        text = text.replace(str(T / f'home-{who}'), '~/.synchronauts')
    return text


results = []


def measure(what, text):
    text = real(text)
    results.append((what, len(text)))
    if os.environ.get('SHOW'):
        print(f'--- {what}\n{text}\n')


def until(check, limit=20):
    end = time.time() + limit
    while not check():
        if time.time() > end:
            raise SystemExit('timeout')
        time.sleep(0.2)


def text_in(path, *parts):
    return lambda: path.exists() and all(p in path.read_text() for p in parts)


def wait_for_mail(sid, cwd):
    w = subprocess.Popen([sys.executable, SYN, 'hook', 'Stop'], stdin=subprocess.PIPE, stderr=subprocess.PIPE,
                         stdout=subprocess.DEVNULL, text=True, env=env('alex'))
    w.stdin.write(json.dumps({'session_id': sid, 'cwd': str(cwd)}))
    w.stdin.close()
    time.sleep(0.5)
    return w


try:
    sh('git', 'init', '-q', '--bare', str(T / 'remote.git'))
    SD, AD, AO = repo('sam-demo', 'acme/demo'), repo('alex-demo', 'acme/demo'), repo('alex-other', 'acme/other')
    NOTES = T / 'notes'
    NOTES.mkdir()
    syn('sam', 'setup')
    syn('alex', 'setup')

    hook('alex', 'SessionStart', 'ale11111', AD)
    hook('alex', 'PostToolUse', 'ale11111', AD, 'Edit', AD / 'src' / 'a.ts')
    syn('alex', 'task', 'Ticket routes in demo, route /tickets/:id', sid='ale11111')
    hook('alex', 'PostToolUse', 'ale11111', AD, 'Bash')
    hook('alex', 'SessionStart', 'ale22222', AO)
    syn('alex', 'task', 'Rebuild the price import for the shop', sid='ale22222')
    hook('alex', 'PostToolUse', 'ale22222', AO, 'Bash')
    hook('sam', 'UserPromptSubmit', 'sam00000', NOTES)  # starts Sam's watcher
    until(text_in(T / 'home-sam' / 'others.json', 'price import', 'Ticket routes'))

    measure('Start in a team repo (Alex has 2 sessions)', hook('sam', 'SessionStart', 'sam11111', SD))
    measure('Start outside the team repos (notes, home)', hook('sam', 'SessionStart', 'sam99999', NOTES))
    measure('Prompt with nothing new', hook('sam', 'UserPromptSubmit', 'sam11111', SD))
    measure('Tool call with nothing new', hook('sam', 'PostToolUse', 'sam11111', SD, 'Bash'))
    q = question('sam', 'sam11111', SD, SD / 'src' / 'a.ts')
    if os.environ.get('SHOW'):
        print(f"--- Permission prompt before the edit, only for Sam ({q.get('permissionDecision')})\n"
              f"{q.get('permissionDecisionReason')}\n")
    measure("Question before the first edit of Alex's file", q.get('additionalContext', ''))
    measure("First edit of Alex's file, after Sam allowed it",
            hook('sam', 'PostToolUse', 'sam11111', SD, 'Edit', SD / 'src' / 'a.ts'))
    syn('sam', 'task', 'Secure the ticket routes', sid='sam11111')
    hook('sam', 'PostToolUse', 'sam11111', SD, 'Bash')
    measure('Second own session in the same repo, start', hook('sam', 'SessionStart', 'sam22222', SD))
    measure('First session, next prompt', hook('sam', 'UserPromptSubmit', 'sam11111', SD))

    hook('alex', 'UserPromptSubmit', 'ale11111', AD)
    w = wait_for_mail('ale11111', AD)
    syn('sam', 'send', 'alex@demo', "I'm changing src/a.ts right now (ticket routes). Are you touching that file today? "
                                    "Otherwise I'll take the tests as well.", sid='sam11111')
    try:
        w.wait(20)
    except subprocess.TimeoutExpired:
        w.kill()
    measure(f'Wake-up with one message (exit {w.returncode})', w.stderr.read())

    syn('sam', 'send', 'alex', 'Quick question: who builds the tests for the price import?', sid='sam11111')
    until(text_in(T / 'home-alex' / 'others.json', 'who builds the tests'))
    measure('Message without a repo, target session at the next prompt', hook('alex', 'UserPromptSubmit', 'ale11111', AD))
    measure("The same message, Alex's other session", hook('alex', 'UserPromptSubmit', 'ale22222', AO))
finally:
    for h in T.glob('home-*'):
        try:
            os.kill(json.loads((h / 'watcher.json').read_text())['pid'], 15)
        except Exception:
            pass
    subprocess.run(['rm', '-rf', str(T)])

description = re.search(r'^description: (.*)$', SKILL, re.M).group(1)
body = SKILL.split('---', 2)[2]
results += [('Skill description (in every session)', len(description)),
            ('Skill text (only when the skill loads)', len(body))]
for what, chars in results:
    print(f'{chars:6} chars  ~{round(chars / 3.3):5} tokens  {what}')
