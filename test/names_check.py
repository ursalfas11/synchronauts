#!/usr/bin/env python3
"""For e2e.sh: display names and logins (S03), from fixed states instead of a running room. The labels, resolve(),
message headers, the approval prompt, the notification title, the board's people, unsigned mail of a case variant, and
a fetch that keeps two branches apart whose logins differ only in case, also on a file system that ignores case
(macOS, Windows). Prints `ok   <what>` per check and `FAIL <what>` with the details; exit 1 if anything failed.
Usage: names_check.py <repo root> <temp folder>. Python 3.9 syntax."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT, TMP = Path(sys.argv[1]), Path(sys.argv[2])
HOME = TMP / 'home-names'
os.environ['SYN_HOME'] = str(HOME)
os.environ['SYN_NOTIFY'] = 'log'
os.environ['GIT_DEFAULT_REF_FORMAT'] = 'files'  # packed() writes packed-refs, also where git defaults to reftable
for var in ('SYN_REMOTE', 'SYN_ME', 'SYN_MACHINE', 'SYN_NAME', 'SYN_SIGNING_KEY'):  # config() must not be steered
    os.environ.pop(var, None)
sys.path.insert(0, str(ROOT))
import syn  # noqa: E402

failures = []
K = {'me': 'alex-gh', 'name': 'Alex', 'machine': 'one', 'remote': str(TMP / 'names-remote.git')}


def check(condition, what, detail=''):
    if condition:
        print(f'ok   {what}')
    else:
        failures.append(what)
        print(f'FAIL {what}')
        if detail:
            print(f'---- {detail}')


def branch(login, name, machine='one', task='', mail=()):
    """The state of syn/<login>/<machine> as the fetch keeps it (tidy() of what the branch says)."""
    sessions = {'s1': {'repos': {'acme/demo': {'files': ['src/a.ts'], 'branch': 'main', 'last': syn.iso()}}, 'task': task,
                       'state': 'working', 'last': syn.iso(), 'start': syn.iso()}} if task else {}
    return syn.tidy({'login': login, 'name': name, 'sessions': sessions, 'mail': list(mail)}, login, machine)


def room(*states):
    """others.json with these branches; returns names(K)."""
    others_ = {f"{d['login']}/{d['machine']}": d for d in states}
    syn.save(HOME / 'others.json', others_)
    return syn.names(K)


def refused(person):
    """The text resolve() refuses person with, '' if it resolves."""
    try:
        syn.resolve(K, person)
        return ''
    except ValueError as f:
        return str(f)


# --- labels -----------------------------------------------------------------------------------------------------------
nm = room(branch('sam-gh', 'Sam'), branch('jule-gh', 'Jule'))
check(nm == {'alex-gh': 'Alex', 'sam-gh': 'Sam', 'jule-gh': 'Jule'}, 'nobody to mix up: the names alone', str(nm))
check(syn.full('sam-gh', nm) == 'Sam (@sam-gh)' and syn.full('kim-gh', nm) == 'kim-gh', 'full() adds the login', str(nm))
check(syn.resolve(K, 'sam') == 'sam-gh' and syn.resolve(K, 'Sam') == 'sam-gh' and syn.resolve(K, '@jule-gh') == 'jule-gh',
      'a name that fits one person reaches that person, so does @login')
check(refused('kim') == 'Unknown: kim. In the room: Jule (@jule-gh), Sam (@sam-gh)', 'an unknown name lists the room',
      refused('kim'))
check(refused('alex') and refused('alex-gh'), 'I am not one of the recipients')
check(refused('sarn').startswith('Unknown: sarn.'), 'a look-alike of a name is not taken for it', refused('sarn'))

# T-S3 1, 3: Mallory calls herself Sam
nm = room(branch('sam-gh', 'Sam'), branch('mal-gh', 'Sam'))
check(nm['sam-gh'] == 'Sam (@sam-gh)' and nm['mal-gh'] == 'Sam (@mal-gh)', 'two people named Sam: both with the login',
      str(nm))
err = refused('Sam')
check(err == 'Sam is ambiguous: Sam (@mal-gh), Sam (@sam-gh). Ask Alex which login is meant; never pick one yourself.'
      and 'ambiguous' in refused('sam'), 'the name Sam is refused as ambiguous, with both logins: Claude asks its human', err)
check(syn.resolve(K, 'sam-gh') == 'sam-gh' and syn.resolve(K, 'mal-gh') == 'mal-gh', 'each login reaches its person only')

# T-S3 4: the exact login wins over a name
nm = room(branch('sam-gh', 'Sam'), branch('mal-gh', 'sam-gh'))
check(nm['sam-gh'] == 'Sam' and nm['mal-gh'] == 'sam-gh (@mal-gh)', "a name that is somebody's login gets the login",
      str(nm))
check(syn.resolve(K, 'sam-gh') == 'sam-gh', 'the exact login wins over the same text as a name')

# T-S3 5: sanitizing, Cyrillic and other scripts
for raw in ('Sam (@sam-gh)', '[unsigned] Sam', 'Sam @sam-gh', 'Sam)(@sam-gh'):
    nm = room(branch('sam-gh', 'Sam'), branch('mal-gh', raw))
    label = nm['mal-gh']
    check('(@sam-gh)' not in label and not set(label) & set('@()[]') and syn.full('mal-gh', nm).endswith('(@mal-gh)'),
          f'the name {raw!r} cannot render a label of somebody else', label)
nm = room(branch('sam-gh', 'Sam'), branch('mal-gh', 'Sаm'))  # a Cyrillic a
check(nm['sam-gh'] == 'Sam (@sam-gh)' and nm['mal-gh'] == 'Sаm (@mal-gh)', 'a Cyrillic look-alike: both with the login',
      str(nm))
for fake in ('Al\u0131ce', 'Al\u026ace', '\u1d00lice', 'A\u029fice'):  # dotless i, small capital i, a and l
    nm = room(branch('alice-gh', 'Alice'), branch('mal-gh', fake))
    check(nm['alice-gh'] == 'Alice (@alice-gh)' and nm['mal-gh'] == f'{fake} (@mal-gh)',
          f'a Latin letter that only looks plain ({fake!a}): both with the login', str(nm))
nm = room(branch('sam-gh', '李华'), branch('jule-gh', 'Jürgen'), branch('kim-gh', 'Søren'))
check(nm['sam-gh'] == '李华 (@sam-gh)' and nm['kim-gh'] == 'Søren (@kim-gh)' and nm['jule-gh'] == 'Jürgen',
      'a name in another script, or with a letter that is not plain Latin, always shows the login; an umlaut does not',
      str(nm))

# T-S3 6: branches of one login that disagree about the name
nm = room(branch('sam-gh', 'Sam'), branch('sam-gh', 'Evil', 'zzz'), branch('jule-gh', 'Jule'))
check(nm['sam-gh'] == 'sam-gh' and syn.resolve(K, 'sam-gh') == 'sam-gh' and refused('Evil') and refused('sam'),
      'two branches of one login with two names: the bare login', str(nm))

# --- logins: case variants and look-alikes (rev 4) ----------------------------------------------------------------------
nm = room(branch('alice-gh', 'Alice', task='Real task'), branch('Alice-gh', 'Alice', 'x', task='Variant task'),
          branch('a1ice-gh', 'Alice', 'x', task='Look-alike task'), branch('sam-gh', 'Sam'))
check(nm['alice-gh'] == '⚠ Alice (@alice-gh)' and nm['Alice-gh'] == '⚠ Alice (@Alice-gh)'
      and nm['a1ice-gh'] == '⚠ Alice (@a1ice-gh)' and nm['sam-gh'] == 'Sam',
      'a case variant and a look-alike login: three separate people, each marked with the login', str(nm))
check(syn.resolve(K, 'alice-gh') == 'alice-gh' and syn.resolve(K, 'Alice-gh') == 'Alice-gh'
      and syn.resolve(K, 'a1ice-gh') == 'a1ice-gh', 'each exact spelling reaches its branch only')
check(all('ambiguous' in refused(p) for p in ('alice', 'Alice')), 'the name of the three is refused as ambiguous',
      refused('alice'))
check(all(refused(p) == f'{p} is not in the room; written differently: \u26a0 Alice (@Alice-gh), \u26a0 Alice (@alice-gh). '
          'Ask Alex which login is meant; never pick one yourself.' for p in ('ALICE-GH', 'aLiCe-gh')),
      'a login written in another case is refused, with the logins it could mean', refused('ALICE-GH'))
lines = [syn.line(who, s) for who, _, s, _ in syn.others(K, own=False)]
check(any('(@Alice-gh)' in x and 'Variant task' in x for x in lines) and any('(@alice-gh)' in x and 'Real task' in x for x in lines)
      and not any('Variant task' in x and '(@alice-gh)' in x for x in lines),
      "the variant's task is never shown as alice's", '\n'.join(lines))
nm = room(branch('sam-gh', 'Sam'), branch('sarn-gh', 'Sarn'), branch('jule-gh', 'Jule'))
check(nm['sam-gh'].startswith('⚠ ') and nm['sarn-gh'] == '⚠ Sarn (@sarn-gh)' and nm['jule-gh'] == 'Jule'
      and 'ambiguous' in refused('sam'), 'rn for m: sarn-gh looks like sam-gh, both marked, the short name is refused',
      str(nm))
check(syn.login_skeleton('a1ice-gh') == syn.login_skeleton('ALICE-GH') == syn.login_skeleton('AIice_gh')
      == syn.login_skeleton('alice.gh') and syn.login_skeleton('vvo0d') == syn.login_skeleton('wood')
      and syn.login_skeleton('kim') != syn.login_skeleton('sam'), 'login_skeleton folds case, 1 i l, 0 o, rn m, vv w, - _ .')
syn.save(HOME / 'signers.json', ['alice-gh'])
unsigned = {'id': '20990101T000000Z-x-1', 'to': ['alex-gh'], 'time': syn.iso(), 'text': 'x'}
check(syn.verify(dict(unsigned, **{'from': 'Alice-gh'}), K) == 'bad' and syn.verify(dict(unsigned, **{'from': 'a1ice-gh'}), K) == 'unsigned',
      'unsigned mail under a case variant of a login that signs is forged; a look-alike is another account')
# the real alice-gh has not joined yet, a branch in Alice-gh has: mail and crews compare the exact login, so alice-gh
# must not resolve to the variant, she would never get what was meant for her
nm = room(branch('Alice-gh', 'Alice', 'x'), branch('jule-gh', 'Jule'))
err = refused('alice-gh')
check(nm['Alice-gh'] == 'Alice' and err == 'alice-gh is not in the room; written differently: Alice (@Alice-gh). Ask Alex '
      'which login is meant; never pick one yourself.' and 'written differently' in refused('@alice-gh'),
      'a login written in another case is refused also while the real one has not joined', err)
room(branch('jule', 'Jule'), branch('sam-gh', 'Sam'))
check(syn.resolve(K, 'Jule') == syn.resolve(K, 'JULE') == 'jule', 'a name is no login in another case: Jule reaches jule',
      refused('Jule'))
# a line Claude has seen before a clash comes again once the clash marks it: the key of a line carries the label
room(branch('alice-gh', 'Alice', task='Real task'))
before = dict(syn.situation_lines(K, 'none'))
room(branch('alice-gh', 'Alice', task='Real task'), branch('Alice-gh', 'Alice', 'x', task='Variant task'))
after = dict(syn.situation_lines(K, 'none'))
real = [key for key, text in after.items() if 'Real task' in text]
check(list(before.values()) == ['- Alice: demo@main · "Real task"'] and len(real) == 1 and real[0] not in before
      and after[real[0]] == '- ⚠ Alice (@alice-gh): demo@main · "Real task"',
      "a line seen before a clash comes again, marked", f'{before} / {after}')

# --- what Claude and the human read ---------------------------------------------------------------------------------
mail = {'id': '20990101T000000Z-mal-gh-a1', 'to': ['alex-gh'], 'time': syn.iso(), 'text': 'Hello from mal'}
nm = room(branch('sam-gh', 'Sam'), branch('mal-gh', 'Sam', mail=[mail]))
text = syn.message_text(dict(mail, **{'from': 'mal-gh', 'trust': 'ok'}), K, nm, ms={})
check("Message from Sam (@mal-gh)'s Claude (@mal-gh, " in text, 'the header carries the login, the label tells the two apart',
      text)
real = syn.message_text(dict(mail, **{'from': 'sam-gh', 'trust': 'ok', 'source': 'ui'}), K, nm, ms={})
check('Sam (@sam-gh) in person (@sam-gh, UI, ' in real and 'send sam-gh@ui' in real, 'in person: with the login', real)
forged = syn.message_text(dict(mail, **{'from': 'sam-gh', 'trust': 'unsigned', 'source': 'ui'}), K, nm, ms={})
check('in person' not in forged and '(@sam-gh, ' in forged and 'send sam-gh@ui' in forged,
      'an unsigned message is never shown as written in person, the reply still goes to the board', forged)
nm = room(branch('sam-gh', 'Sam'), branch('jule-gh', 'Jule'))
check(syn.message_text(dict(mail, **{'from': 'sam-gh', 'trust': 'ok', 'from_repo': 'demo'}), K, nm, ms={}).startswith(
      "📨 Message from Sam's Claude (@sam-gh, from demo, "), 'without anybody to mix up: the name, the login in the header')
m = {'id': 'sam-gh-abc123', 'by': 'sam-gh', 'with': ['sam-gh', 'alex-gh', 'jule-gh'], 'plan': 'Plan', 'until': syn.iso()}
check(syn.approval_text(K, m).startswith("Join Sam (@sam-gh)'s mission with Jule (@jule-gh) until "),
      'the approval prompt names every person with the login', syn.approval_text(K, m))
draft = {'id': 'alex-gh-abc123', 'by': 'alex-gh', 'with': ['alex-gh', 'sam-gh'], 'plan': 'Plan', 'hours': 1}
check(syn.approval_text(K, draft).startswith('Start this mission with Sam (@sam-gh) for up to 1 h?'),
      'so does the prompt of a draft', syn.approval_text(K, draft))

# the notification title and the board, Mallory named Sam again
nm = room(branch('sam-gh', 'Sam'), branch('mal-gh', 'Sam', mail=[mail]))
syn.save(HOME / 'inbox.json', {mail['id']: syn.iso()})
syn.save(HOME / 'notified.json', {'mail': [], 'conflicts': [], 'sent': []})
syn.notify_tick(K)
log = (HOME / 'notifications.log').read_text(encoding='utf-8') if (HOME / 'notifications.log').exists() else ''
check('"title": "Message from Sam (@mal-gh)"' in log, 'the notification title tells the two apart', log)
people = {p['login']: p['name'] for p in syn.ui_data(K)['people']}
check(people == {'alex-gh': 'Alex', 'sam-gh': 'Sam (@sam-gh)', 'mal-gh': 'Sam (@mal-gh)'}, 'the board shows the labels',
      str(people))

# --- a fetch that keeps case variants apart -------------------------------------------------------------------------
logins = ['alice-gh', 'Alice-gh', 'ALICE-GH', 'a.b', 'a_b', 'a-b', 'con', 'x' * 39, 'X' * 39]
refs = [syn.branch_ref(f'{x}/{m}') for x in logins for m in ('one', 'One', 'x' * 30, 'X' * 30)]
check(len(set(refs)) == len(refs) and all(r == r.lower() and len(r) < 120 for r in refs),
      'every branch has its own local ref, without capitals, short enough for Windows')
bad = [r for r in refs if subprocess.run(['git', 'check-ref-format', r], capture_output=True).returncode]
check(not bad, 'the local refs are valid ref names', str(bad))

REMOTE, SHAS = Path(K['remote']), {}


def g(*args, stdin=None):
    """git in the remote; bytes in and out, so Windows does not write \\r\\n into mktree's input."""
    out = subprocess.run(['git', '-C', str(REMOTE), *args], input=(stdin or '').encode('utf-8'), capture_output=True,
                         check=True).stdout
    return out.decode('utf-8').strip()


def commit(login, name, task):
    blob = g('hash-object', '-w', '--stdin', stdin=json.dumps({'login': login, 'name': name, 'sessions': branch(
        login, name, task=task)['sessions'], 'mail': []}))
    return g('commit-tree', g('mktree', stdin=f'100644 blob {blob}\tstate.json\n'), '-m', 'x')


def packed(lines, repo=REMOTE, add=False):
    """The packed-refs of repo (the remote) with these `<sha> <ref>` lines, add: and those it has: a ref that differs
    from another only in case, which a loose ref file could not hold apart on macOS or Windows (as GitHub could)."""
    old = []
    if add and (repo / 'packed-refs').exists():
        old = [x for x in (repo / 'packed-refs').read_text(encoding='utf-8').splitlines() if x[:1] not in ('', '#', '^')]
    body = ''.join(f'{x}\n' for x in sorted(old + list(lines), key=lambda x: x.split(' ', 1)[1]))
    with open(repo / 'packed-refs.lock', 'x', encoding='utf-8', newline='\n') as f:
        f.write('# pack-refs with: peeled fully-peeled sorted \n' + body)
    os.replace(repo / 'packed-refs.lock', repo / 'packed-refs')


subprocess.run(['git', 'init', '-q', '--bare', str(REMOTE)], check=True)
g('config', 'user.name', 'x')
g('config', 'user.email', 'x@x')
g('update-ref', 'refs/heads/syn/alice-gh/one', commit('alice-gh', 'Alice', 'Real task'))
g('update-ref', 'refs/heads/syn/sam-gh/one', commit('sam-gh', 'Sam', 'Sam task'))
variant = commit('Alice-gh', 'Alice', 'Variant task')
packed([f'{variant} refs/heads/syn/Alice-gh/one'])  # the same machine name: on macOS the very same file
subprocess.run(['git', 'init', '-q', '--bare', str(syn.GIT)], check=True)
syn.git('remote', 'add', 'origin', K['remote'])  # as 0.5 joined a room: with a fetch refspec
k = dict(K, me='kim-gh', name='Kim')


def fetched():
    return {who: (d['name'], [s['task'] for s in d['sessions'].values()]) for who, d in syn.load(HOME / 'others.json', {}).items()}


try:
    syn.fetch(k)
    error = ''
except (RuntimeError, OSError) as f:
    error = str(f)
got = fetched()
check(not error and got.get('alice-gh/one') == ('Alice', ['Real task']) and got.get('Alice-gh/one') == ('Alice', ['Variant task'])
      and got.get('sam-gh/one') == ('Sam', ['Sam task']), 'a branch in a case variant of a login and the real one: both '
      'fetched, each with its own state, also on a file system that ignores case', error or str(got))
check(not syn.git('for-each-ref', 'refs/remotes'), 'no remote-tracking refs: neither those of 0.5 nor new ones',
      syn.git('for-each-ref', 'refs/remotes'))
syn.git('update-ref', 'refs/remotes/origin/syn/old-gh/one', variant)  # a ref the fetch of 0.5 left behind
g('update-ref', 'refs/heads/syn/alice-gh/one', commit('alice-gh', 'Alice', 'Real task, later'))
packed([])  # the variant is gone; deleting it with git would remove alice's loose ref on macOS
syn.fetch(k)
got = fetched()
check(got.get('alice-gh/one') == ('Alice', ['Real task, later']) and 'Alice-gh/one' not in got,
      'a changed branch is fetched again, a deleted one leaves the room', str(got))
check(not syn.git('for-each-ref', 'refs/remotes'), 'the refs the fetch of 0.5 left behind are deleted',
      syn.git('for-each-ref', 'refs/remotes'))
check(sorted(syn.git('for-each-ref', '--format=%(refname)', syn.IN_REFS).splitlines())
      == sorted(syn.branch_ref(x) for x in ('alice-gh/one', 'sam-gh/one')), 'and its local ref is deleted',
      syn.git('for-each-ref', syn.IN_REFS))
check(subprocess.run(['git', '-C', str(syn.GIT), 'config', '--get-all', 'remote.origin.fetch']).returncode == 1,
      "so is the fetch refspec of 0.5's `git remote add`, which wrote the own branch there at every push")
syn.publish(k)
check(not syn.git('for-each-ref', 'refs/remotes'), 'a push writes no remote-tracking ref any more',
      syn.git('for-each-ref', 'refs/remotes'))

# 0.5 could leave refs on macOS and Windows that differ only in case, one packed and one a file, which cannot be deleted
# in one go there; a stale lock does that on every system. The fetch goes on, and deletes them one by one
old = syn.OLD_REFS
syn.git('update-ref', f'{old}alice-gh/one', variant)
syn.git('update-ref', f'{old}stale-gh/one', variant)
packed([f'{variant} {old}Alice-gh/one'], syn.GIT, add=True)
lock = syn.GIT / 'refs' / 'remotes' / 'origin' / 'syn' / 'stale-gh' / 'one.lock'
lock.write_bytes(b'')
try:
    syn.fetch(k)
    error = ''
except (RuntimeError, OSError) as f:
    error = str(f)
left = syn.git('for-each-ref', '--format=%(refname)', 'refs/remotes').splitlines()
check(not error and 'alice-gh/one' in fetched() and left == [f'{old}stale-gh/one'],
      'old refs that cannot be deleted in one go stop no fetch: deleted one by one, a locked one stays', error or str(left))
lock.unlink()
syn.fetch(k)
check(not syn.git('for-each-ref', 'refs/remotes'), 'and goes at the next fetch', syn.git('for-each-ref', 'refs/remotes'))

# A branch deleted between the listing and the fetch fails a fetch of several branches as a whole: it is left out and
# the rest fetched again, after three such rounds one by one, so nobody holds up the sync by adding and deleting branches
g('update-ref', 'refs/heads/syn/sam-gh/one', commit('sam-gh', 'Sam', 'Sam task, later'))
listing = syn.ls_remote() + [f'refs/heads/syn/gone{i}-gh/one {"1" * 40}' for i in range(5)]
try:
    syn.fetch(k, listing)
    error = ''
except RuntimeError as f:
    error = str(f)
got = fetched()
check(not error and got.get('sam-gh/one') == ('Sam', ['Sam task, later']) and not any(w.startswith('gone') for w in got)
      and sorted(syn.git('for-each-ref', '--format=%(refname)', syn.IN_REFS).splitlines())
      == sorted(syn.branch_ref(x) for x in ('alice-gh/one', 'sam-gh/one')),
      'five branches deleted after the listing: left out, the changed one is fetched all the same', error or str(got))
url = syn.git('config', 'remote.origin.url')
syn.git('config', 'remote.origin.url', str(TMP / 'nowhere.git'))
try:
    syn.fetch(k, listing)
    error = ''
except RuntimeError as f:
    error = str(f)
syn.git('config', 'remote.origin.url', url)
check(error.startswith('git fetch: '), 'a room out of reach still fails the fetch: no branch is taken for gone', error)

if failures:
    sys.exit(1)
print('names: all green')
