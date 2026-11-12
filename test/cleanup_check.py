#!/usr/bin/env python3
"""For e2e.sh: the clean-up of the room, from branches with a commit date of our own choosing. Dead branches (STALE):
the own login's other machines are deleted in the room (only those, only at the commit that was found dead, a failure
is ignored), the others' are left out of others.json; over MAX_BRANCHES the live ones come first and the cut is
reported; the git settings against loose objects. Prints `ok   <what>` per check and `FAIL <what>` with the details;
exit 1 if anything failed. Usage: cleanup_check.py <repo root> <temp folder>. Python 3.9 syntax."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT, TMP = Path(sys.argv[1]), Path(sys.argv[2])
HOME = TMP / 'home-cleanup'
REMOTE = TMP / 'cleanup-remote.git'
os.environ['SYN_HOME'] = str(HOME)
os.environ['GIT_DEFAULT_REF_FORMAT'] = 'files'
for var in ('SYN_REMOTE', 'SYN_ME', 'SYN_MACHINE', 'SYN_NAME', 'SYN_SIGNING_KEY'):
    os.environ.pop(var, None)
sys.path.insert(0, str(ROOT))
import syn  # noqa: E402

failures = []
K = {'me': 'jule-gh', 'name': 'Jule', 'machine': 'one', 'remote': str(REMOTE)}


def check(condition, what, detail=''):
    if condition:
        print(f'ok   {what}')
    else:
        failures.append(what)
        print(f'FAIL {what}')
        if detail:
            print(f'---- {detail}')


def g(*args, stdin=None, env=None):
    r = subprocess.run(['git', '-C', str(REMOTE), *args], check=True, capture_output=True, env=env,
                       input=stdin.encode() if stdin else None)
    return r.stdout.decode().strip()


def put(who, days):
    """The branch syn/<who> in the room as one commit dated `days` ago; returns its sha."""
    login = who.split('/')[0]
    blob = g('hash-object', '-w', '--stdin', stdin=json.dumps({'login': login, 'name': login, 'sessions': {}, 'mail': []}))
    tree = g('mktree', stdin=f'100644 blob {blob}\tstate.json\n')
    when = f'{int(time.time() - days * 86400)} +0000'
    env = dict(os.environ, GIT_AUTHOR_NAME='x', GIT_AUTHOR_EMAIL='x@x', GIT_COMMITTER_NAME='x',
               GIT_COMMITTER_EMAIL='x@x', GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)
    sha = g('commit-tree', tree, '-m', f'x {when}', env=env)
    g('update-ref', f'refs/heads/syn/{who}', sha)
    return sha


def in_room():
    return sorted(x[len('refs/heads/syn/'):] for x in g('for-each-ref', '--format=%(refname)', 'refs/heads/syn/').splitlines())


def read():
    return sorted(syn.load(HOME / 'others.json', {}))


subprocess.run(['git', 'init', '-q', '--bare', str(REMOTE)], check=True)
subprocess.run(['git', 'init', '-q', '--bare', str(syn.GIT)], check=True)
syn.git('config', 'remote.origin.url', str(REMOTE))
OLD, NEW = 45, 1
put('jule-gh/laptop', OLD)       # mine, dead: another machine of Jule's that nobody uses any more
put('jule-gh/phone', NEW)        # mine, alive
put('alex-gh/dead', OLD)         # somebody else's, dead
put('alex-gh/live', NEW)
syn.publish(K)                   # the own branch syn/jule-gh/one: never deleted, whatever its age

# --- git settings ------------------------------------------------------------------------------------------------------
syn.tune_git()
conf = {key: syn.git('config', '--get', key) for key, _ in syn.GIT_CONFIG}
check(conf == dict(syn.GIT_CONFIG), 'the room gets gc.pruneExpire, gc.auto and no detached gc', str(conf))
syn.git('config', '--unset', 'gc.pruneExpire')
syn.tune_git()
check(syn.git('config', '--get', 'gc.pruneExpire') == '1.hour.ago', 'an old room gets them at the next start too')

# --- dead branches -----------------------------------------------------------------------------------------------------
note = syn.fetch(K)
check(read() == ['alex-gh/live', 'jule-gh/phone'] and not note and 'jule-gh/laptop' in in_room(),
      "a fetch leaves dead branches out of the room's state, and deletes none without prune", f'{read()} {in_room()}')
laptop = syn.git('rev-parse', syn.branch_ref('jule-gh/laptop'))
put('jule-gh/laptop', OLD + 1)   # pushed again since it was found dead: another commit
syn.delete_dead(K, [('jule-gh/laptop', laptop)])
check('jule-gh/laptop' in in_room(), 'a branch that changed since it was found dead is not deleted (lease)', str(in_room()))
syn.fetch(K, prune=True)
check(in_room() == ['alex-gh/dead', 'alex-gh/live', 'jule-gh/one', 'jule-gh/phone'],
      "prune deletes the own login's dead branch of another machine and nothing else: not the own machine's, not "
      "another person's", str(in_room()))
check(read() == ['alex-gh/live', 'jule-gh/phone'], 'the dead branches of others stay out of the state', str(read()))

calls = []
real = syn.git


def spy(*args, **kw):
    calls.append(args)
    return real(*args, **kw)


syn.git = spy
syn.delete_dead(K, [('alex-gh/dead', '1' * 40), ('Jule-gh/old', '1' * 40), ('jule-gh/one', '1' * 40)])
syn.git = real
check(not [c for c in calls if c[0] == 'push'],
      "no other login, no case variant of mine and not the own machine's branch is ever pushed to a delete", str(calls))
syn.git('config', 'remote.origin.url', str(TMP / 'nowhere.git'))
try:
    syn.delete_dead(K, [('jule-gh/gone', '1' * 40)])
    ok = True
except Exception:  # noqa: BLE001
    ok = False
check(ok, 'a delete that fails (offline, no right) stops nothing')
syn.git('config', 'remote.origin.url', str(REMOTE))

# --- the cut -----------------------------------------------------------------------------------------------------------
put('aaa-gh/dead', OLD)
put('zed-gh/live', NEW)
put('jule-gh/tablet', NEW)
syn.fetch(K)                     # the dead one is known now
syn.MAX_BRANCHES = 3
note = syn.fetch(K)
check(read() == ['alex-gh/live', 'jule-gh/phone', 'jule-gh/tablet'] and '1 of them are not read' in note,
      'over the limit: the own login first, then the live ones, never a dead one before them; the cut is reported',
      f'{read()} {note!r}')
syn.MAX_BRANCHES = 300
check(syn.fetch(K) == '' and read() == ['alex-gh/live', 'jule-gh/phone', 'jule-gh/tablet', 'zed-gh/live'],
      'under the limit there is no note and every live branch is read', str(read()))

sys.exit(1 if failures else 0)
