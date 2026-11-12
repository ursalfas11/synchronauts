#!/usr/bin/env python3
"""For e2e.sh: the id of a room (room_id, derive_room, refresh_room) and what signed mission mail does with it.
No watcher, no real room: fake `git`, `gh` and `ssh` on the PATH log what is asked of them. Prints `ok   <what>` per
check and `FAIL <what>` with the details; exit 1 if anything failed.
Usage: rooms_check.py <repo root> <temp folder>; the environment of e2e.sh (SYN_KEYS_URL, the key of sam-gh) is used.
The fake commands are shell scripts, so on Windows only the pure checks run. Python 3.9 syntax."""
import io
import json
import os
import shutil
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path

ROOT, TMP = Path(sys.argv[1]), Path(sys.argv[2])
HOME = TMP / 'home-rooms'
BIN, LOG = TMP / 'fakebin', TMP / 'fakebin' / 'calls.log'
os.environ['SYN_HOME'] = str(HOME)
for name in ('SYN_REMOTE', 'SYN_ME', 'SYN_MACHINE', 'SYN_NAME'):  # config() must say what config.json says
    os.environ.pop(name, None)
sys.path.insert(0, str(ROOT))
import syn  # noqa: E402

failures = []
WIN = os.name == 'nt'


def check(condition, what, detail=''):
    if condition:
        print(f'ok   {what}')
    else:
        failures.append(what)
        print(f'FAIL {what}')
        if detail:
            print(f'---- {detail}')


# --- the id is the same for every way to name one repo --------------------------------------------------------------
forms = ['git@git.example.org:acme/team.git', 'https://git.example.org/Acme/Team', 'ssh://git@git.example.org:2222/acme/team',
         'https://git@git.example.org/acme/team.git/', 'git://git.example.org/acme/team', 'GIT.example.ORG:acme/team']
ids = {syn.norm_remote(f) for f in forms}
check(ids == {'git.example.org/acme/team'}, 'the scp, https, ssh and git forms of one repo give one room id', str(ids))
check(syn.norm_remote('https://other.example.org/acme/team') != 'git.example.org/acme/team',
      'the same owner and repo on another host is another room')
check(syn.norm_remote('acme/room') == 'github.com/acme/room', 'owner/repo is a GitHub repo')
check(syn.norm_remote('ssh://git@ssh.github.com:443/Acme/Room.git') == 'github.com/acme/room',
      "GitHub's SSH over port 443 is GitHub")
bare = TMP / 'rooms-bare.git'
bare.mkdir(exist_ok=True)
check(syn.norm_remote(str(bare)) == bare.resolve().as_posix() and syn.norm_remote(bare.as_uri()) == bare.resolve().as_posix(),
      'a local bare repo is its resolved path, also as a file:// URL')
check(syn.norm_remote('') == '' and syn.room_id({}) == '', 'no remote, no id')
check(syn.room_id({'room': 'Git.Example.Org/Acme/Team.git/', 'remote': 'x/y'}) == 'git.example.org/acme/team',
      'a stored room wins over the remote, in the same form')
check(syn.norm_room(syn.room_id({'remote': forms[0]})) == syn.room_id({'remote': forms[0]}),
      'room_id() is stable under norm_room()')
check(syn.room_ids({'room': 'a/b/c', 'room_alt': ['D/E/F.git', 5, None]}) == {'a/b/c', 'd/e/f'},
      'the ids of a room are its own and the earlier ones')
azure = ['https://dev.azure.com/acme/My%20Project/_git/room', 'https://git@dev.azure.com/acme/My%20Project/_git/room',
         'git@ssh.dev.azure.com:v3/acme/My%20Project/room', 'https://acme.visualstudio.com/My%20Project/_git/room',
         'https://acme.visualstudio.com/DefaultCollection/My%20Project/_git/room',
         'git@vs-ssh.visualstudio.com:v3/acme/My%20Project/room']
ids = {syn.norm_remote(f) for f in azure}
check(len(ids) == 1 and syn.fits(syn.ROOM_RE, ids.pop()), "Azure DevOps' https, ssh and visualstudio.com forms give one id",
      str({syn.norm_remote(f) for f in azure}))
spaced = TMP / 'team room+1'
spaced.mkdir(exist_ok=True)
odd = [str(spaced), spaced.as_uri(), 'ssh://git@[2001:db8::1]:22/acme/c++.git', 'https://git.example.org/' + 'a/' * 150 + 'r']
check(all(syn.fits(syn.ROOM_RE, syn.norm_remote(x)) and syn.norm_room(syn.norm_remote(x)) == syn.norm_remote(x)
          for x in odd) and syn.norm_remote(odd[0]) == syn.norm_remote(odd[1]),
      'a path with a space or +, an IPv6 host and a very long URL give ids that fit what mail may carry, stable under '
      'norm_room', str([syn.norm_remote(x) for x in odd]))
check(all(syn.parse(s) == syn.parse('2030-01-01T00:00:00+00:00') for s in ('2030-01-01T00:00:00Z', '2030-01-01T00:00:00+00:00')),
      'an end time is read with and without Z')

# --- signed mission mail between members who name the room differently ----------------------------------------------
syn.private_dir(HOME)
syn.git('init', '-q', '--bare', str(HOME / 'git'), cwd=TMP)
base = {'me': 'alex-gh', 'machine': 'one', 'name': 'Alex'}
sam = {'me': 'sam-gh', 'machine': 'one', 'name': 'Sam'}


def invite(room, **more):
    """A mission invite of Sam's, signed with his key, for the room `room` (None: without one)."""
    n = {'id': '20300101T000000Z-sam-gh-r00001', 'to': ['alex-gh'], 'time': syn.iso(), 'text': 'Plan', 'kind': 'invite',
         'mission': 'sam-gh-r00001', 'crew': ['sam-gh', 'alex-gh'], 'until': syn.iso(syn.now() + syn.timedelta(hours=1)),
         **({'room': room} if room is not None else {}), **more}
    n['sig'] = syn.sign(n, sam)
    return dict(n, **{'from': 'sam-gh'})


mine = syn.room_id({'remote': 'git@git.example.org:acme/team.git'})
n = invite(mine)
for form in forms[:5]:
    check(syn.verify(n, dict(base, remote=form)) == 'ok', f'mission mail signed for one form of the room verifies in {form}')
check(syn.verify(n, dict(base, remote='https://other.example.org/acme/team')) == 'bad',
      'the same repo name on another host stays bad')
check('sam-gh' in syn.load(HOME / 'room-mismatch.json', {}), 'a room that differs is noted with the sender, for doctor')
check(syn.verify(invite(None), dict(base, remote=forms[0])) == 'ok'
      and syn.mission_of(dict(invite(None), trust='ok'), dict(base, remote=forms[0])) is None,
      'mission mail without a room is signed fine, but is no mission')
check(syn.mission_of(dict(n, trust='ok'), dict(base, remote=forms[1])) is not None
      and syn.mission_of(dict(n, trust='bad'), dict(base, remote=forms[1])) is None,
      'a signed invite of the room is a mission, a forged one is not')
plain = {'id': '20300101T000000Z-sam-gh-p00001', 'to': ['alex-gh'], 'time': syn.iso(), 'text': 'Hi'}
plain['sig'] = syn.sign(plain, sam)
check('room' not in syn.post(dict(sam, remote=forms[0]), ['alex-gh'], 'Hi') and 'room' in syn.post(
    dict(sam, remote=forms[0]), ['alex-gh'], 'Plan', mission='sam-gh-abcdef', kind='invite'),
      'post() signs the room on mission mail only, plain mail of a one-room sender stays as 0.5 reads it')
check(syn.verify(dict(plain, **{'from': 'sam-gh'}), dict(base, remote=forms[0])) == 'ok',
      'plain mail without a room verifies as before')
stolen = invite(mine, id='20300101T000000Z-sam-r00009')  # Sam's valid signature, but the id names the login `sam`
check(syn.verify(stolen, dict(base, remote=forms[0])) == 'bad',
      'a signed message under an id that names somebody else is forged: post() writes the sender into every id')
k_odd = dict(base, remote=odd[0])
n_odd = invite(syn.room_id(dict(sam, remote=odd[0])))
check(syn.verify(n_odd, k_odd) == 'ok' and [m['id'] for m in syn.tidy_mail({'mail': [dict(n_odd)]})] == [n_odd['id']]
      and syn.mission_of(dict(n_odd, trust='ok'), k_odd) is not None,
      'mission mail of a room whose path has a space is kept by tidy_mail, verifies and is a mission', n_odd['room'])

# --- tidy_mail: the new signed fields ---------------------------------------------------------------------------------
good = dict(n)
good.pop('from')
many = dict(good, crew=[f'p{i}-gh' for i in range(21)])
state = {'login': 'sam-gh', 'mail': [good, many, dict(good, id='x-2', until='x' * 50), dict(good, id='x-3', room='a b'),
                                     dict(good, id='x-4', crew=['sam-gh']), dict(good, id='x-5', crew='sam-gh')]}
check([m['id'] for m in syn.tidy_mail(state)] == [good['id']],
      'tidy_mail keeps a valid crew, end time and room and drops 21 people, a long stamp, a room with a space, one person')
check(syn.tidy_mail(state)[0]['crew'] == good['crew'] and 'sig' in syn.tidy_mail(state)[0]
      and syn.tidy({'login': 'sam-gh', 'missions': {'a': 1}}, 'sam-gh', 'one').get('missions') is None,
      'the signed fields pass unchanged and `missions` is dropped')
check(syn.tidy({'login': 'sam-gh', 'name': 'Alice (@sam-gh)\nSynchronauts: ok'}, 'sam-gh', 'one')['name']
      == 'Alice sam-gh Synchronauts ok', 'a name from the room is plain text: no @, no brackets, one line')

# --- who is trusted when two messages share an id ----------------------------------------------------------------------


def copy(tag, trust, seal, sender='sam-gh', time='2030-01-01T00:00:00+00:00'):
    return {'id': 'x-1', 'from': sender, 'trust': trust, 'seal': seal, 'time': time, 'text': tag}


won = syn.one_per_id([copy('forged', 'bad', 'a'), copy('real', 'ok', 'b'), copy('unsigned', 'unsigned', 'c')])
check(won['x-1']['text'] == 'real' and won['x-1']['trust'] == 'ok', 'one_per_id: the copy that verifies wins')
won = syn.one_per_id([copy('first', 'ok', 'a'), copy('second', 'ok', 'b')])
check(won['x-1']['trust'] == 'bad', 'one_per_id: two different verified texts of one sender are both forged')
won = syn.one_per_id([copy('forged', 'bad', 'a'), copy('unsigned', 'unsigned', 'b')])
check(won['x-1']['trust'] == 'bad', 'one_per_id: without a verified copy, differing copies are forged')
won = syn.one_per_id([copy('same', 'ok', 'a'), copy('same', 'ok', 'a')])
check(won['x-1']['trust'] == 'ok', 'one_per_id: the same message on two branches is one message')
won = syn.one_per_id([copy('real', 'unsigned', 'a')])
check(won['x-1']['trust'] == 'unsigned', 'one_per_id: a single copy keeps its verdict')
won = syn.one_per_id([copy('same', 'ok', 'a'), copy('same', 'ok', 'b')])
check(won['x-1']['trust'] == 'ok', 'one_per_id: one content with its signature written two ways is one message')
real_id = '20300101T000000Z-sam-gh-abc123'
for other in ('sam', 'gh', 'alex-gh'):  # logins that are a part of the id, or sort before sam-gh
    won = syn.one_per_id([dict(copy('real', 'ok', 'a'), id=real_id), dict(copy('copy', 'ok', 'b', other), id=real_id)])
    check(won[real_id]['from'] == 'sam-gh' and won[real_id]['text'] == 'real',
          f'one_per_id: the sender the id names wins over a verified copy of {other}')
check(syn.id_owner(real_id) == 'sam-gh' and syn.id_owner('20300101T000000Z-a-b-c-ff00aa') == 'a-b-c'
      and syn.id_owner('x-1') == '' and syn.id_owner('x') == '', 'id_owner reads the login out of an id exactly')
# anyone in the room can multiply copies, and a hook has 10 s: 20000 identical ones, 20000 written another way
many = [copy('same', 'ok', 'a') for _ in range(20000)] + [copy('same', 'ok', f's{i}') for i in range(20000)]
t0 = syn.time.time()
won = syn.one_per_id(many + [copy('forged', 'bad', 'z')])
took = syn.time.time() - t0
check(took < 3 and won['x-1']['trust'] == 'ok', f'one_per_id: 40000 copies of one verified message take {took:.2f} s')
body = {f: v for f, v in n.items() if f != 'from'}  # the same through mail_to_me, as every hook calls it
syn.save(HOME / 'others.json', {f'sam-gh/b{i:02d}': {'login': 'sam-gh', 'name': 'Sam', 'machine': f'b{i:02d}', 'version': '',
                                                    'sessions': {}, 'events': [], 'mail': [body] * 100} for i in range(30)})
syn.save(HOME / 'verified.json', {syn.seal(body, 'sam-gh'): {'v': 'ok', 't': syn.iso(), 'id': body['id']}})
t0 = syn.time.time()
got = syn.mail_to_me(dict(base, remote=forms[0]))
took = syn.time.time() - t0
check(took < 5 and [x['trust'] for x in got] == ['ok'],
      f'mail_to_me: 3000 copies of one signed message on 30 branches take {took:.2f} s and give it once')
for name in ('others.json', 'verified.json'):
    (HOME / name).unlink()
signed = {'id': 'x', 'to': ['kim-gh'], 'sig': 'x'}
check(syn.trust_view(signed, 'sam-gh', {}, 'alex-gh') == 'unchecked' and syn.trust_view(signed, 'sam-gh', {}, 'kim-gh')
      == 'unsigned' and syn.trust_view(dict(signed, sig=None), 'sam-gh', {}, 'alex-gh') == 'unsigned'
      and syn.trust_view(signed, 'sam-gh', {syn.seal(signed, 'sam-gh'): {'v': 'ok'}}, 'alex-gh') == 'ok',
      'trust_view: the verdict; signed mail between two others is unchecked, mail to me without one unsigned')

# --- no network or subprocess for the id in hooks, verify() and post(); the rename heals through refresh_room -------
if WIN:
    print('ok   skipped: the fake git, gh and ssh are shell scripts')
else:
    BIN.mkdir(exist_ok=True)
    real_git = shutil.which('git')
    (BIN / 'git').write_text(f'#!/bin/sh\necho "git $*" >> "{LOG}"\nexec "{real_git}" "$@"\n')
    # gh repo view answers what gh-answer says, or with gh-echo the repo it is asked about, otherwise it fails
    (BIN / 'gh').write_text(f'#!/bin/sh\necho "gh $*" >> "{LOG}"\n'
                            f'case "$*" in "repo view "*) if [ -e "{BIN}/gh-echo" ]; then echo "$3"; '
                            f'elif [ -s "{BIN}/gh-answer" ]; then cat "{BIN}/gh-answer"; else exit 1; fi ;; '
                            f'*) exit 1 ;; esac\n')
    (BIN / 'ssh').write_text(f'#!/bin/sh\necho "ssh $*" >> "{LOG}"\n'
                             'if [ "$1" = -G ]; then shift; [ "$1" = -- ] && shift; h=$1\n'
                             '[ "$h" = team-alias ] && h=git.example.org; [ "$h" = gh443 ] && h=ssh.github.com\n'
                             'printf "user git\\nhostname %s\\nport 22\\n" "$h"; exit 0; fi\n'
                             'exit 255\n')
    for name in ('git', 'gh', 'ssh'):
        (BIN / name).chmod(0o755)
    os.environ['PATH'] = f'{BIN}{os.pathsep}{os.environ["PATH"]}'
    (BIN / 'gh-answer').write_text('')

    def asked():
        """The calls that find the room's id out: insteadOf, ssh aliases, GitHub."""
        text = LOG.read_text() if LOG.exists() else ''
        return [x for x in text.splitlines() if 'ls-remote --get-url' in x or x.startswith(('gh ', 'ssh -G'))]

    def config(**fields):
        syn.save(HOME / 'config.json', {'me': 'jule-gh', 'machine': 'one', 'name': 'Jule', **fields})
        return syn.config()

    def hook(event, **e):
        r = subprocess.run([sys.executable, str(ROOT / 'hook.py'), event], text=True, capture_output=True, timeout=60,
                           input=json.dumps({'session_id': 'rom11111', 'cwd': str(TMP), **e}),
                           env=dict(os.environ, PYTHONUTF8='1', SYN_WAKE_MIN='0.01'))  # Stop waits 0.6 s
        return r.stdout + r.stderr

    def trusts(k):
        return {n['text']: n['trust'] for n in syn.mail_to_me(k)}

    # an upgrade from 0.5: no `room` in the config. Nothing asks git, ssh or GitHub for the id: not post(), not verify()
    k = config(remote='https://github.com/acme/room.git')
    LOG.write_text('')
    sent = syn.post(dict(k, me='sam-gh'), ['jule-gh'], 'Plan for Jule', mission='sam-gh-abcdef', kind='invite',
                    crew=['sam-gh', 'jule-gh'], until=syn.iso(syn.now() + syn.timedelta(hours=1)))
    check(sent['room'] == 'github.com/acme/room' and syn.verify(dict(sent, **{'from': 'sam-gh'}), k) == 'ok'
          and syn.mission_of(dict(sent, **{'from': 'sam-gh', 'trust': 'ok'}), k) is not None,
          'without a stored room the URL gives the id, and post(), verify() and mission_of() agree on it', str(sent))
    # and not the hooks of a session that gets this invite, as Jule's watcher would have fetched and checked it
    syn.save(HOME / 'others.json', {'sam-gh/one': {'login': 'sam-gh', 'name': 'Sam', 'machine': 'one', 'version': '',
                                                   'sessions': {}, 'mail': [sent], 'events': []}})
    syn.save(HOME / 'verified.json', {syn.seal(sent, 'sam-gh'): {'v': 'ok', 't': syn.iso(), 'id': sent['id']}})
    syn.save(HOME / 'inbox.json', {sent['id']: syn.iso()})
    (HOME / 'fetched').touch()  # the session start does not wait for a fetch
    with syn.Lock('watcher', wait=False):  # as if a watcher ran: the hooks start none (it would fetch and ask)
        out = ''.join([hook('SessionStart', source='startup'), hook('UserPromptSubmit', prompt='go on'),
                       hook('PreToolUse', tool_name='Edit', tool_input={'file_path': str(TMP / 'x.txt')}),
                       hook('PreToolUse', tool_name='Bash', tool_use_id='toolu_r1', permission_mode='auto',
                            tool_input={'command': f'{syn.CMD} mission approve sam-gh-abcdef'}),
                       hook('PostToolUse', tool_name='Bash', tool_use_id='toolu_r2', tool_input={'command': 'ls'}),
                       hook('Stop')])
    check('Mission proposal from Sam' in out and '"permissionDecision": "ask"' in out and 'Error' not in out,
          'the hooks see the mission with the id the URL gives', out)
    check(not asked(), 'post(), verify() and the hooks (start, prompt, tool use, stop) never ask git, ssh or GitHub '
                       'for the room id', '\n'.join(asked()))
    # the positive control: the commands that may ask, do
    syn.derive_room(k)
    check(len(asked()) >= 2, 'derive_room asks git and GitHub (the fake commands are in use)', '\n'.join(asked()))

    # insteadOf and an ssh alias lead to the same id, so their members verify each other's mission mail
    os.environ.update(GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='url.git' + '@git.example.org:acme/team.git.insteadOf',
                      GIT_CONFIG_VALUE_0='https://short.example/team')
    got = syn.derive_room({'remote': 'https://short.example/team'})
    check(got == ('git.example.org/acme/team', True), 'derive_room follows an insteadOf rewrite', str(got))
    syn.refresh_room(config(remote='https://short.example/team'))
    check(syn.verify(n, syn.config()) == 'ok', 'a member behind insteadOf verifies mission mail of the room')
    del os.environ['GIT_CONFIG_COUNT']
    got = syn.derive_room({'remote': 'team-alias:acme/team.git'})
    check(got == ('git.example.org/acme/team', True), 'derive_room resolves an ssh alias with ssh -G', str(got))
    syn.refresh_room(config(remote='team-alias:acme/team.git'))
    check(syn.verify(n, syn.config()) == 'ok', 'and so does a member behind an ssh alias')
    check(syn.derive_room({'remote': 'gh443:acme/room.git'}) == ('github.com/acme/room', False),
          'an ssh config that sends GitHub over port 443 stays GitHub')
    check(syn.derive_room({'remote': str(bare)}) == (bare.resolve().as_posix(), True), 'a local bare repo needs no question')
    LOG.write_text('')
    (BIN / 'gh-answer').write_text('Acme/Room\n')
    check(syn.derive_room({'remote': 'git@github.com:acme/room.git'}) == ('github.com/acme/room', True),
          'on GitHub the name GitHub reports is the id, in lower case')

    # the repo is renamed on GitHub. A member whose watcher saw it first already signs with the new id: until mine sees
    # it too, that mail looks forged
    k = config(remote='https://github.com/acme/room.git', room='github.com/acme/room')
    old = invite('github.com/acme/room')
    early = invite('github.com/acme/newroom', id='20300101T000000Z-sam-gh-r00002', to=['jule-gh'], text='Early plan',
                   mission='sam-gh-r00002', crew=['sam-gh', 'jule-gh'])
    forged = dict(invite('github.com/acme/newroom', id='20300101T000000Z-sam-gh-r00003', to=['jule-gh']), text='Forged')
    syn.save(HOME / 'others.json', {'sam-gh/one': {'login': 'sam-gh', 'name': 'Sam', 'machine': 'one', 'version': '',
                                                   'sessions': {}, 'events': [],
                                                   'mail': [{f: v for f, v in x.items() if f != 'from'}
                                                            for x in (forged, early)]}})
    (HOME / 'keys.json').unlink(missing_ok=True)  # no keys asked for lately; the forgery is checked first, as only a check that asks the keys URL itself is final
    syn.save(HOME / 'verified.json', {syn.seal(x, 'sam-gh'): {'v': syn.verify(x, k), 't': syn.iso(), 'id': x['id']}
                                      for x in (forged, early)})
    check(trusts(k) == {'Early plan': 'bad', 'Forged': 'bad'} and 'sam-gh-r00002' not in syn.missions(k),
          'before my side knows the new name, mail with the new id looks forged', str(trusts(k)))
    (BIN / 'gh-answer').write_text('')  # GitHub does not answer: the id stays
    check(syn.refresh_room(k) == ('github.com/acme/room', 'github.com/acme/room', False)
          and 'room_alt' not in syn.load(HOME / 'config.json', {}), 'no answer from GitHub: the stored id stays')
    # what a watcher or the board, started before the rename, holds; the refresh runs in another process, as a human
    # runs it after the doctor's hint
    snapshot = syn.config()
    (BIN / 'gh-answer').write_text('Acme/Newroom\n')

    def refresh():
        r = subprocess.run([sys.executable, str(ROOT / 'syn.py'), 'rooms', '--refresh'], text=True, capture_output=True,
                           timeout=60, env=dict(os.environ, PYTHONUTF8='1'))
        return r.stdout + r.stderr

    (HOME / 'keys.json').unlink(missing_ok=True)
    out = refresh()
    stored = syn.load(HOME / 'config.json', {})
    check(stored.get('room') == 'github.com/acme/newroom' and stored.get('room_alt') == ['github.com/acme/room']
          and stored.get('me') == 'jule-gh' and 'github.com/acme/newroom' in out,
          '`rooms --refresh` moves the old id to room_alt, keeps the other settings and says what changed', out)
    k = syn.config()
    check(trusts(k) == {'Early plan': 'ok', 'Forged': 'bad'} and syn.missions(k)['sam-gh-r00002']['by'] == 'sam-gh',
          'mail that looked forged only because of the new id is checked again; forged mail stays forged', str(trusts(k)))
    new = invite('github.com/acme/newroom')
    check(syn.verify(old, k) == 'ok' and syn.verify(new, k) == 'ok'
          and syn.verify(invite('github.com/acme/elsewhere'), k) == 'bad',
          'mail signed with the old or the new id verifies, an unrelated id does not')
    held, healing = dict(snapshot), dict(snapshot)
    check(syn.verify(early, held) == 'bad' and syn.adopt_room(held) and syn.verify(early, held) == 'ok'
          and not syn.adopt_room(held), 'a process that holds the config of its start takes the new id over from the file',
          str(held))
    check(syn.refresh_room(healing)[2] is False
          and syn.room_ids(healing) == {'github.com/acme/newroom', 'github.com/acme/room'},
          "and so does the watcher's daily refresh, which finds nothing new itself", str(healing))
    # mail a process checked against the old id after the rename (before it took the new one over) looks forged ...
    late = invite('github.com/acme/newroom', id='20300101T000000Z-sam-gh-r00004', to=['jule-gh'], text='Late plan',
                  mission='sam-gh-r00004', crew=['sam-gh', 'jule-gh'])
    others_ = syn.load(HOME / 'others.json', {})
    others_['sam-gh/one']['mail'].append({f: v for f, v in late.items() if f != 'from'})
    syn.save(HOME / 'others.json', others_)
    syn.save(HOME / 'verified.json', {**syn.load(HOME / 'verified.json', {}), syn.seal(late, 'sam-gh'): {
        'v': syn.verify(late, snapshot), 't': syn.iso(), 'id': late['id']}})
    check(trusts(k)['Late plan'] == 'bad', 'a verdict against the old id stays until it is checked again')
    (HOME / 'keys.json').unlink(missing_ok=True)
    out = refresh()  # ... until the next refresh, which finds nothing new but checks the room's forged mail again
    check('Unchanged' in out and syn.load(HOME / 'config.json', {}).get('room_alt') == ['github.com/acme/room']
          and trusts(k) == {'Early plan': 'ok', 'Forged': 'bad', 'Late plan': 'ok'},
          'a second refresh changes nothing, but checks forged mail of the room again', out + str(trusts(k)))
    out = io.StringIO()
    with redirect_stdout(out):
        syn.dispatch('rooms', [])
    check(out.getvalue().strip() == 'Room github.com/acme/newroom (earlier ids: github.com/acme/room)',
          '`rooms` names the id and the earlier ones', out.getvalue())
    for name in ('one', 'two', 'three', 'four'):  # at most three earlier ids
        (BIN / 'gh-answer').write_text(f'Acme/R{name}\n')
        syn.refresh_room(syn.config())
    check(len(syn.load(HOME / 'config.json', {}).get('room_alt')) == 3, 'at most three earlier ids are kept')

    # setup pointed the room at another repo while a watcher of the old one ran: its refresh derives from the remote
    # the file names now, and keeps the id setup found
    (BIN / 'gh-echo').write_text('')
    config(remote='https://github.com/acme/newroom.git', room='github.com/acme/newroom')
    started = dict(syn.config(), remote='https://github.com/acme/oldroom.git', room='github.com/acme/oldroom')
    got = syn.refresh_room(started)
    stored = syn.load(HOME / 'config.json', {})
    check(stored.get('room') == 'github.com/acme/newroom' and not stored.get('room_alt')
          and syn.room_id(started) == 'github.com/acme/newroom' and started['remote'].endswith('/newroom.git'),
          'a watcher from before setup pointed the room elsewhere keeps the new room, and takes it over', f'{got} {stored}')
    (BIN / 'gh-echo').unlink()

print(f"\nrooms: {'all green' if not failures else str(len(failures)) + ' failed: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
