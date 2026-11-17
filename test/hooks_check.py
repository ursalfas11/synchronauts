"""The hooks as Claude Code runs them: each command line of hooks/hooks.json through sh, with CLAUDE_PLUGIN_ROOT set
and the input Claude Code really sends (test/fixtures/claude-code, recorded from Claude Code 2.1.326 in `claude -p`
with a hook that saved its stdin, then made neutral: paths and the session id are placeholders, texts rewritten).
Without a room, on this machine only. To record anew, run such a hook for every event and replace the files.

python3 test/hooks_check.py <root of the plugin>
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
WIN = os.environ.get('OS') == 'Windows_NT'
FIX = ROOT / 'test' / 'fixtures' / 'claude-code'
HOOKS = json.loads((ROOT / 'hooks' / 'hooks.json').read_text(encoding='utf-8'))['hooks']
T = Path(tempfile.mkdtemp(prefix='syn-hooks-'))
failed = []


def check(cond, what, detail=''):
    print(('ok   ' if cond else 'FAIL ') + what, flush=True)
    if not cond:
        failed.append(what)
        if detail:
            print('---- output:\n' + str(detail)[-1500:])


def command(event, tool=None):
    """The command line of hooks.json that Claude Code runs for this event and tool."""
    for entry in HOOKS[event]:
        if 'matcher' not in entry or tool in entry['matcher'].split('|'):
            return entry['hooks'][0]['command']
    return None


ENV = {k: v for k, v in os.environ.items() if not k.startswith(('SYN_', 'CLAUDE'))}
ENV.update(CLAUDE_PLUGIN_ROOT=str(ROOT), SYN_HOME=str(T / 'home'), SYN_REMOTE='', SYN_INVITES='off', SYN_NOTIFY='log',
           SYN_UI_PORT='0', CLAUDE_CODE_ENTRYPOINT='cli', LC_MESSAGES='en_US.UTF-8', PYTHONUTF8='1')


def run(event, text, tool=None, cwd=None):
    """(exit code, stdout, stderr) of the hook for this event, given text on stdin."""
    r = subprocess.run(['sh', '-c', command(event, tool)], input=text.encode('utf-8'), capture_output=True,
                       env=ENV, cwd=str(cwd or T), timeout=60)
    return r.returncode, r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')


def fixture(name, work, session):
    """A recorded input with its placeholders filled in: this test's repo, session and transcript."""
    raw = (FIX / f'{name}.json').read_text(encoding='utf-8')
    path = work.as_posix()
    raw = raw.replace('{WORK}', path).replace('{SESSION}', session).replace('{TRANSCRIPT}', f'{path}/t.jsonl')
    return json.loads(raw)


def git(*args, cwd):
    subprocess.run(['git', '-c', 'user.name=test', '-c', 'user.email=test@example.com', *args], cwd=str(cwd),
                   check=True, capture_output=True)


def answer_ok(event, out):
    """Empty, or one JSON object; what it says for Claude is about this event."""
    if not out.strip():
        return True
    try:
        d = json.loads(out)
    except ValueError:
        return False
    h = d.get('hookSpecificOutput')
    return isinstance(d, dict) and (h is None or h.get('hookEventName') == event)


def status():
    try:
        return json.loads((T / 'home' / 'status.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


try:
    # two worktrees of one repo, as two sessions of one person would have them
    work, other = T / 'work', T / 'work-feature'
    work.mkdir()
    git('init', '-q', '-b', 'main', cwd=work)
    (work / 'app.py').write_text('a = 1\n', encoding='utf-8')
    git('add', 'app.py', cwd=work)
    git('commit', '-q', '-m', 'init', cwd=work)
    git('worktree', 'add', '-q', '-b', 'feature', str(other), cwd=work)
    one, two = 'c64c8273-6325-4247-8bf6-d9f1e6c092c3', '5e1f0a9b-2c3d-4e5f-8a6b-7c8d9e0f1a2b'

    # every recorded input, in the order of the recorded session, through its own command line
    order = ['SessionStart', 'UserPromptSubmit', 'PreToolUse-Read', 'PostToolUse-Read', 'PreToolUse-Edit',
             'PostToolUse-Edit', 'PreToolUse-Bash', 'PostToolUse-Bash', 'PreToolUse-Write', 'PostToolUse-Write']
    check(sorted(order + ['Stop', 'SessionEnd']) == sorted(p.stem for p in FIX.glob('*.json')),
          'every recorded input is played', sorted(p.stem for p in FIX.glob('*.json')))
    times = []
    for name in order:
        d = fixture(name, work, one)
        event, tool = d['hook_event_name'], d.get('tool_name')
        if tool == 'Edit':
            (work / 'app.py').write_text('a = 2\n', encoding='utf-8')
        if tool == 'Write' and name.startswith('Post'):
            (work / 'notes.md').write_text(d['tool_input']['content'], encoding='utf-8')
        if command(event, tool) is None:
            print(f'ok   {name}: hooks.json has no hook for it, so Claude Code runs none')
            continue
        t0 = time.time()
        rc, out, err = run(event, json.dumps(d), tool, work)
        times.append(time.time() - t0)
        check(rc == 0 and 'Traceback' not in err and answer_ok(event, out),
              f'{name}: the recorded input runs through hooks.json, exit 0, an answer Claude Code takes',
              f'exit {rc}\n{out}\n{err}')
    files = [f for x in status().get('sessions', {}).values() for f in x.get('repos', {}).get('local/work', {}).get('files', [])]
    check('app.py' in files and 'notes.md' in files, 'Edit and Write of the recorded session are noted as its files',
          json.dumps(status(), indent=1))
    times.sort()
    print(f'     hooks took {times[len(times) // 2] * 1000:.0f} ms in the middle, {times[-1] * 1000:.0f} ms at most')

    # a second session in the other worktree: a file the first one claimed makes Claude Code ask first
    run('SessionStart', json.dumps(fixture('SessionStart', other, two)), cwd=other)
    r = subprocess.run([sys.executable, str(ROOT / 'syn.py'), 'claim', 'app.py'], capture_output=True, cwd=str(work),
                       env=dict(ENV, CLAUDE_CODE_SESSION_ID=one), timeout=60)
    check(r.returncode == 0, 'the first session claims app.py', r.stdout + r.stderr)
    rc, out, err = run('PreToolUse', json.dumps(fixture('PreToolUse-Edit', other, two)), 'Edit', other)
    try:
        h = json.loads(out).get('hookSpecificOutput', {})
    except ValueError:
        h = {}
    check(h.get('permissionDecision') == 'ask' and 'app.py' in h.get('permissionDecisionReason', ''),
          'the recorded Edit of the claimed file in the other worktree makes Claude Code ask first', out + err)

    # Stop without a room waits for no mail; SessionEnd ends the session
    for name in ('Stop', 'SessionEnd'):
        rc, out, err = run(name, json.dumps(fixture(name, work, one)), cwd=work)
        check(rc == 0 and 'Traceback' not in err and answer_ok(name, out), f'{name}: the recorded input, exit 0',
              f'exit {rc}\n{out}\n{err}')

    # input Claude Code never sends must not stop a session either: exit 0, no traceback, nothing for Claude
    for event, entries in HOOKS.items():
        tool = entries[0].get('matcher', '').split('|')[0] or None
        bad = []
        for x in ('', 'not json', '[]', '{}', '{"session_id": 5, "cwd": null, "tool_input": "x"}'):
            rc, out, err = run(event, x, tool)
            if rc != 0 or 'Traceback' in err or not answer_ok(event, out):
                bad.append(f'{x!r}: exit {rc} {out} {err}')
        check(not bad, f'{event}: empty, broken or odd input ends with exit 0 and no traceback', bad)
finally:
    for f in (T / 'home').glob('*.json') if (T / 'home').exists() else []:
        if f.stem in ('watcher', 'ui'):
            try:
                pid = json.loads(f.read_text(encoding='utf-8'))['pid']
                subprocess.run(['taskkill', '/F', '/PID', str(pid)] if WIN else ['kill', str(pid)], capture_output=True)
            except (OSError, ValueError, KeyError):
                pass
    shutil.rmtree(T, ignore_errors=True)
sys.exit(1 if failed else 0)
