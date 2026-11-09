#!/usr/bin/env python3
"""For e2e.sh: signing with a key that an ssh-agent holds, one on a security key or one named by its .pub (S06), and the
outbox for what a hook may not sign. choose_key() in its order (a key file, a key an agent holds, a key on a security
key, also one saved under a key file's name; an agent that cannot be asked keeps its key), the IdentityAgent of ssh's
config, signing.json of 0.5, sign() through an agent, its time limit and the agents it falls back to, a key file that
no hanging agent holds up, the yes of a mission in its hook (hook_post), the line a command prints before it waits for
the key, outbox_put(), drain_outbox() (sealed records, only while their mission wants them) and the watcher's Outbox,
the end of a mission (ended here at once, queued before the key is asked: a key that does not sign, a drain that runs,
Ctrl-C, and `syn mission end` killed or interrupted in a process of its own leave it queued), numbers in the
environment that are none, and the questions to a key that the watcher ends with it. The checks that need a real ssh-agent, a Unix
socket or ssh's config print `ok   skipped: <what>` where there is none (Windows, no ssh-agent, or NO_AGENT=1 as in
e2e.sh), so the count stays the same. Prints `ok   <what>` per check and `FAIL <what>` with the details; exit 1 if
anything failed. Usage: sign_check.py <repo root> <temp folder>. Python 3.9 syntax."""
import atexit
import io
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import redirect_stderr, redirect_stdout
from datetime import timedelta
from pathlib import Path

ROOT, TMP = Path(sys.argv[1]), Path(sys.argv[2])
S = TMP / 'sign'
HOME = S / 'home'
os.environ['SYN_HOME'] = str(HOME)
os.environ['SYN_KEYS_URL'] = f"file://{'/' if os.name == 'nt' else ''}{(S / 'keys').as_posix()}/{{login}}.keys"
for var in ('SYN_REMOTE', 'SYN_ME', 'SYN_MACHINE', 'SYN_NAME', 'SYN_SIGNING_KEY', 'SYN_SIGN_WAIT', 'SSH_AUTH_SOCK'):
    os.environ.pop(var, None)  # no agent of the machine that runs the tests is asked
sys.path.insert(0, str(ROOT))
import syn  # noqa: E402

failures = []
POSIX = os.name != 'nt'
AGENT = POSIX and not os.environ.get('NO_AGENT') and bool(shutil.which('ssh-agent') and shutil.which('ssh-add'))
REAL = {f: getattr(syn, f) for f in ('agent_sockets', 'agent_keys', 'identity_agent', 'sign', 'drain_outbox')}
SIG = '-----BEGIN SSH SIGNATURE-----\nU1NIU0lH\n-----END SSH SIGNATURE-----'  # what a sign() that signs returns here


def check(condition, what, detail=''):
    if condition:
        print(f'ok   {what}')
    else:
        failures.append(what)
        print(f'FAIL {what}')
        if detail:
            print(f'---- {detail}')


def skipped(names, why):
    for what in names:
        print(f'ok   skipped: {what} ({why})')


def mode(path):
    return os.stat(path).st_mode & 0o777


def keygen(name, comment, passphrase=''):
    path = S / name
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', passphrase, '-C', comment, '-f', str(path)],
                   check=True, stdin=subprocess.DEVNULL, capture_output=True)
    return path


def line(key):
    """The public key line of a key file: `ssh-ed25519 AAAA… comment`."""
    return Path(f'{key}.pub').read_text(encoding='utf-8').strip()


def fake_home(name, **keys):
    """A home folder (HOME and USERPROFILE, which Path.home() follows) with these files in .ssh: id_ed25519=<key file>
    copies a key and its .pub, <name>=<public line of a key on a security key> writes a key handle and that public
    key under that name."""
    h = S / name
    (h / '.ssh').mkdir(parents=True, exist_ok=True)
    for file, key in keys.items():
        if str(key).startswith('sk-'):
            (h / '.ssh' / file).write_text('a key handle, the key itself is on the security key\n', encoding='utf-8')
            (h / '.ssh' / f'{file}.pub').write_text(f'{key}\n', encoding='utf-8')
        else:
            shutil.copy(key, h / '.ssh' / file)
            shutil.copy(f'{key}.pub', h / '.ssh' / f'{file}.pub')
    os.environ['HOME'] = os.environ['USERPROFILE'] = str(h)
    return h


def agents(held):
    """The ssh-agents as choose_key() and sign() see them, {socket: [public key lines]}; no real agent is asked."""
    syn.agent_sockets = lambda config=None: list(held)
    syn.agent_keys = lambda sock=None: list(held.get(sock, []))


def no_config(config=None):
    """identity_agent() for the checks: the ssh config of the machine that runs them stays out of it (its
    IdentityAgent may be a real 1Password); a config file that a check names is read as ssh reads it."""
    return REAL['identity_agent'](config) if config else None


def restore():
    for f, v in REAL.items():
        setattr(syn, f, v)
    syn.identity_agent = no_config
    syn.SIGN_WAIT, syn.AGENT_WAIT, syn.HOOK_SIGN, syn.COMMAND, syn.ENDING = 30, 5, 3, False, False


def noted():
    return syn.load(HOME / 'signing.json', {})


def note(**d):
    syn.save(HOME / 'signing.json', {'time': time.time(), **d})


def mail():
    return syn.load(HOME / 'mail.json', [])


def message(text):
    """A message as post() makes it, from jule-gh to kim-gh, before its signature."""
    return {'id': f"{syn.now().strftime('%Y%m%dT%H%M%SZ')}-jule-gh-{os.urandom(3).hex()}", 'to': ['kim-gh'],
            'time': syn.iso(), 'text': text}


def signed(text):
    """'ok', 'bad' or 'unsigned': what the receiving side makes of a message that sign() signed here."""
    n = message(text)
    sig = syn.sign(n, K)
    if not sig:
        return 'unsigned (sign() returned None)'
    n.update({'sig': sig, 'from': 'jule-gh'})
    return syn.verify(n, K)


def until(test, limit=10):
    end = time.time() + limit
    while not test():
        if time.time() > end:
            return False
        time.sleep(0.05)
    return True


def own_mission(mid, crew, hours=1.0, sid='jul11111'):
    """Jule's own record of a mission she proposed and approved, sealed as approved() writes it, with her session sid
    in it."""
    x = {'id': mid, 'by': 'jule-gh', 'with': list(crew), 'plan': 'Ship it.', 'start': syn.iso(),
         'until': syn.iso(syn.now() + timedelta(hours=hours)), 'joined': {sid: syn.iso()}}
    with syn.Lock('missions'):
        own = syn.own_missions()
        own[mid] = syn.with_mac(x)
        syn.save(HOME / 'missions.json', own)
    return x


def queued():
    """What waits in the outbox, as JSON, oldest first."""
    return [json.loads(p.read_text(encoding='utf-8')) for p in syn.outbox_records()]


def empty_outbox():
    for p in syn.outbox_records():
        p.unlink()


def dropped():
    log = HOME / 'outbox' / 'dropped.log'
    return log.read_text(encoding='utf-8') if log.exists() else ''


def never_answers(path):
    """A Unix socket at path that takes every connection and never answers, as an ssh-agent that waits for an unlock
    nobody gives. Returns the socket and the connections it holds."""
    server, held = socket.socket(socket.AF_UNIX), []
    server.bind(str(path))
    server.listen(16)

    def hold():
        while True:
            try:
                held.append(server.accept()[0])
            except OSError:
                return

    threading.Thread(target=hold, daemon=True).start()
    return server, held


def close(server, held):
    server.close()
    for c in held:
        c.close()


restore()
S.mkdir(parents=True, exist_ok=True)
(S / 'keys').mkdir(exist_ok=True)
SOCKS = S  # Unix sockets: their path must be short (104 characters on macOS, 108 on Linux)
if POSIX and len(str(S)) >= 80:
    SOCKS = Path(tempfile.mkdtemp(prefix='syn', dir='/tmp'))
    atexit.register(shutil.rmtree, SOCKS, True)
JULE, EVIL, AGKEY, KIM, KIMSK = (keygen(n, c) for n, c in (('jule-key', 'jule'), ('evil-key', 'evil'),
                                                         ('agent-key', 'jule'), ('kim-key', 'kim'), ('kim-sk', 'kim')))
LOCKED = keygen('jule-locked', 'jule', 'a passphrase')  # a key file with a passphrase: signs only through an agent
# not a key on a security key: its public line in the form of one. Only how it is listed counts here, nothing signs
SKLINE = line(KIMSK).replace('ssh-ed25519 ', 'sk-ssh-ed25519@openssh.com ', 1)
(S / 'keys' / 'jule-gh.keys').write_text(f'{line(JULE)}\n{line(AGKEY)}\n', encoding='utf-8')
(S / 'keys' / 'kim-gh.keys').write_text(f'{line(KIM)}\n{SKLINE}\n', encoding='utf-8')
K = {'me': 'jule-gh', 'name': 'Jule', 'machine': 'one', 'remote': str(S / 'room.git')}
KK = {'me': 'kim-gh', 'name': 'Kim', 'machine': 'one', 'remote': str(S / 'room.git')}

# --- choose_key(): which key, in which order ---------------------------------------------------------------------------
h = fake_home('home-file', id_ed25519=JULE)
agents({'/agents/one': [line(AGKEY)]})
syn.choose_key(K)
d = noted()
check(d.get('kind') == 'file' and d.get('key') == str(h / '.ssh' / 'id_ed25519') and d.get('agent') is None,
      'a key file that the keys URL lists comes first, before a key that an ssh-agent holds', d)
h = fake_home('home-kim', id_ed25519=KIM, id_ed25519_sk=SKLINE)
syn.choose_key(KK)
d = noted()
check(d.get('kind') == 'file' and d.get('key') == str(h / '.ssh' / 'id_ed25519'),
      'and before a key on a security key', d)

fake_home('home-agent', id_ed25519=EVIL)
agents({'/agents/one': [line(EVIL), line(AGKEY)]})
syn.choose_key(K)
d, pub = noted(), HOME / 'signing-agent.pub'
check(d.get('kind') == 'agent' and d.get('agent') == '/agents/one' and d.get('key') == str(pub)
      and pub.read_text(encoding='utf-8') == f'{line(AGKEY)}\n',
      'without a listed key file: a key that an ssh-agent holds, its public key in signing-agent.pub', d)
if POSIX:
    check(mode(pub) == 0o600, 'signing-agent.pub has mode 0600', oct(mode(pub)))
else:
    print('ok   skipped: signing-agent.pub has mode 0600')
agents({'/agents/one': [line(EVIL)], '/agents/two': [line(AGKEY)]})
syn.choose_key(K)
check(noted().get('agent') == '/agents/two', 'each ssh-agent is asked in turn, the one that holds a listed key counts',
      noted())

h = fake_home('home-sk', id_ed25519_sk=SKLINE)
agents({'/agents/one': [line(EVIL)]})
syn.choose_key(KK)
d = noted()
check(d.get('kind') == 'sk' and d.get('key') == str(h / '.ssh' / 'id_ed25519_sk') and d.get('agent') is None,
      'without a key file or a key in an agent: a key on a security key (kind sk)', d)
h = fake_home('home-skname', id_ed25519=SKLINE)  # a key on a security key, saved as id_ed25519
syn.choose_key(KK)
d = noted()
agents({'/agents/one': [line(KIM)]})
syn.choose_key(KK)
check(d.get('kind') == 'sk' and d.get('key') == str(h / '.ssh' / 'id_ed25519') and noted().get('kind') == 'agent',
      'a key on a security key saved as id_ed25519 counts as one (kind sk: no hook signs with it), after a key in an '
      'agent', [d, noted()])

fake_home('home-none', id_ed25519=EVIL)
agents({'/agents/one': [line(EVIL)]})
syn.choose_key(K)
d = noted()
check(d.get('key') is None and d.get('kind') is None and not syn.can_sign(K) and syn.sign(message('x'), K) is None,
      'no key that the keys URL lists: none is noted, can_sign() is false and sign() returns None', d)

note(key='/keys/before.pub', kind='agent', agent='/agents/one')
syn.agent_sockets = lambda config=None: ['/agents/one']
syn.agent_keys = lambda sock=None: None  # the agent app is quit or restarts: it cannot be asked
syn.choose_key(K)
kept = noted()
note(key=None, kind=None, agent=None)
syn.choose_key(K)
check(kept.get('key') == '/keys/before.pub' and kept.get('kind') == 'agent' and kept.get('agent') == '/agents/one'
      and 82700 < time.time() - kept.get('time', 0) < 82900 and noted().get('key') is None,
      'an ssh-agent that cannot be asked right now keeps the agent key noted before, looked at again in an hour (with '
      'none noted, none is found)', [kept, noted()])

asked = []
syn.agent_sockets = lambda config=None: asked.append(1) or []
note(key='/keys/before.pub', kind='agent', agent='/agents/one')
syn.choose_key(K, agents=False)
d = noted()
check(not asked and d.get('time') == 0 and d.get('key') == '/keys/before.pub' and d.get('kind') == 'agent'
      and syn.key_due(), "a hook's setup (agents=False) asks no ssh-agent: it keeps what was noted and the watcher looks "
                         "at once", d)
h = fake_home('home-file')
syn.choose_key(K, agents=False)
check(not asked and noted().get('kind') == 'file' and noted().get('key') == str(h / '.ssh' / 'id_ed25519'),
      'with agents=False a listed key file is still found', noted())

note(key='/keys/sk', kind='sk', agent=None)
syn.choose_key({'me': 'alex-gh'})  # the keys URL has nothing for alex-gh and nothing is cached: it cannot be asked
d = noted()
check(d.get('key') == '/keys/sk' and d.get('kind') == 'sk' and 82700 < time.time() - d.get('time', 0) < 82900,
      'while the keys URL cannot be asked, the noted key and its kind stay, looked at again in an hour', d)
restore()

# --- the kinds of key and signing.json --------------------------------------------------------------------------------
kinds = []
for key in (f'{AGKEY}.pub', str(S / 'home-sk' / '.ssh' / 'id_ed25519_sk'), str(KIMSK), str(JULE)):
    os.environ['SYN_SIGNING_KEY'] = key
    kinds.append(syn.signing()['kind'])
Path(f'{KIMSK}.pub').write_text(f'{SKLINE}\n', encoding='utf-8')  # now its public key is that of a security key
os.environ['SYN_SIGNING_KEY'] = str(KIMSK)
kinds.append(syn.signing()['kind'])
os.environ.pop('SYN_SIGNING_KEY')
check(kinds == ['agent', 'sk', 'file', 'file', 'sk'], 'SYN_SIGNING_KEY: a .pub signs through an ssh-agent, an id_*_sk '
      'file or a key whose public key is sk-… on a security key, any other key file at once', kinds)
syn.save(HOME / 'signing.json', {'key': str(JULE), 'time': time.time()})
old, due = syn.signing(), [syn.key_due()]
syn.save(HOME / 'signing.json', {'key': str(JULE), 'kind': 'file', 'agent': None, 'time': time.time()})
due.append(syn.key_due())
check(due == [True, False], 'after the update from 0.5 the watcher looks for the key at once, to note its kind', due)
seen = []
for junk in (['x'], {'key': 5, 'kind': 'usb', 'agent': 7}, {'key': ''}):
    syn.save(HOME / 'signing.json', junk)
    seen.append(syn.signing())
check(old == {'key': str(JULE), 'kind': None, 'agent': None} and all(x == {'key': None, 'kind': None, 'agent': None}
                                                                      for x in seen),
      'a signing.json of 0.5 ({key, time}) still names the key, of a kind not known; odd values count as no key',
      [old, seen])

# --- the IdentityAgent of ssh's config, the agents to ask ---------------------------------------------------------------
NAMES = ("IdentityAgent in ssh's config for github.com: a path with a space, in quotes",
         'IdentityAgent none: no agent',
         'IdentityAgent SSH_AUTH_SOCK or $NAME: the socket that variable names',
         'the ssh-agents to ask: SSH_AUTH_SOCK, then the IdentityAgent, each once and only if its socket exists')
if not POSIX:  # Windows: ssh-add finds the agent itself (agent_sockets() is [None])
    for what in NAMES:
        print(f'ok   skipped: {what}')
else:
    config = S / 'ssh_config'

    def agent_in(value):
        config.write_text(f'Host github.com\n  IdentityAgent {value}\n', encoding='utf-8')
        return syn.identity_agent(config)

    spaced = S / 'with space' / 'agent.sock'
    check(agent_in(f'"{spaced}"') == str(spaced), NAMES[0], agent_in(f'"{spaced}"'))
    check(agent_in('none') is None, NAMES[1], agent_in('none'))
    os.environ.update(SSH_AUTH_SOCK='/from/the/environment', SYN_TEST_AGENT='/from/a/variable')
    got = (agent_in('SSH_AUTH_SOCK'), agent_in('$SYN_TEST_AGENT'))
    check(got == ('/from/the/environment', '/from/a/variable'), NAMES[2], got)
    a, b = S / 'a.sock', S / 'b.sock'  # only whether they exist counts
    a.touch()
    b.touch()
    syn.identity_agent = lambda config=None: str(b)
    got = []
    for env in (a, b, S / 'gone.sock'):
        os.environ['SSH_AUTH_SOCK'] = str(env)
        got.append(syn.agent_sockets())
    check(got == [[str(a), str(b)], [str(b)], [str(b)]], NAMES[3], got)
    os.environ.pop('SSH_AUTH_SOCK')
    os.environ.pop('SYN_TEST_AGENT')
    restore()

# --- a real ssh-agent -------------------------------------------------------------------------------------------------
NAMES = ('agent_keys(): the keys an ssh-agent holds, without its certificates',
         'a key that only an ssh-agent holds: choose_key() notes it with the socket of that agent',
         'sign() signs through that agent, and the signature checks out (ok)',
         'the noted agent is gone (a new login): sign() asks the agents it finds now',
         'the noted agent is dead (its socket is left, nobody listens there): sign() asks the agents it finds now',
         'only a socket of this user counts as the noted agent (also through a link), no plain file and no missing path',
         'SYN_SIGNING_KEY naming the .pub of a key that only an agent holds signs through the agent',
         "without SSH_AUTH_SOCK, the IdentityAgent of ssh's config leads to the agent (1Password, Secretive)",
         'an ssh-agent that never answers: sign() gives up after SYN_SIGN_WAIT seconds',
         'and agent_keys() after a few seconds: it cannot be asked (None, not an empty list of keys)')
if not AGENT:
    skipped(NAMES, 'no ssh-agent here')
else:
    sock, stuck, dead = SOCKS / 'agent.sock', SOCKS / 'stuck.sock', SOCKS / 'dead.sock'
    agent = subprocess.Popen(['ssh-agent', '-D', '-a', str(sock)], stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    server, held = never_answers(stuck)
    gone = socket.socket(socket.AF_UNIX)  # bound and closed: the file stays, as after an agent that crashed
    gone.bind(str(dead))
    gone.close()
    try:
        if not until(sock.exists):
            raise SystemExit('FAIL the ssh-agent did not start')
        env = dict(os.environ, SSH_AUTH_SOCK=str(sock))
        ca = keygen('ca-key', 'ca')
        subprocess.run(['ssh-keygen', '-q', '-s', str(ca), '-I', 'jule', '-n', 'jule', f'{AGKEY}.pub'], check=True,
                       capture_output=True)  # a certificate of the key, which ssh-add adds with it
        subprocess.run(['ssh-add', '-q', str(AGKEY)], env=env, check=True, capture_output=True)
        AGKEY.unlink()  # the private key is only in the agent now
        got = syn.agent_keys(str(sock))
        check([x.split()[:2] for x in got] == [line(AGKEY).split()[:2]], NAMES[0], got)

        os.environ['SSH_AUTH_SOCK'] = str(sock)
        fake_home('home-agent')
        syn.choose_key(K)
        d = noted()
        check(d.get('kind') == 'agent' and d.get('agent') == str(sock) and d.get('key') == str(HOME / 'signing-agent.pub'),
              NAMES[1], d)
        os.environ.pop('SSH_AUTH_SOCK')  # sign() takes the noted socket
        verdict = signed('Signed by the agent.')
        check(verdict == 'ok', NAMES[2], verdict)
        os.environ['SSH_AUTH_SOCK'] = str(sock)
        note(key=str(HOME / 'signing-agent.pub'), kind='agent', agent=str(S / 'gone.sock'))
        verdict = signed('Signed by the agent of the new login.')
        check(verdict == 'ok', NAMES[3], verdict)
        note(key=str(HOME / 'signing-agent.pub'), kind='agent', agent=str(dead))
        t = time.time()
        verdict = signed('Signed by the agent that runs now.')
        check(verdict == 'ok' and time.time() - t < 5, NAMES[4], f'{verdict}, {time.time() - t:.1f} s')
        link, plain = SOCKS / 'link.sock', SOCKS / 'plain.sock'
        link.symlink_to(sock)
        plain.write_text('not a socket\n', encoding='utf-8')
        got = [syn.own_socket(str(x)) for x in (sock, link, plain, SOCKS / 'missing.sock', '')]
        check(got == [True, True, False, False, False], NAMES[5], got)
        note(key=None, kind=None, agent=None)
        os.environ['SYN_SIGNING_KEY'] = f'{AGKEY}.pub'
        verdict = signed('Signed by the key that SYN_SIGNING_KEY names.')
        os.environ.pop('SYN_SIGNING_KEY')
        check(verdict == 'ok', NAMES[6], verdict)
        os.environ.pop('SSH_AUTH_SOCK')
        config = S / 'ssh_config'
        config.write_text(f'Host github.com\n  IdentityAgent "{sock}"\n', encoding='utf-8')
        check(syn.agent_socket(config) == str(sock), NAMES[7], syn.agent_socket(config))

        syn.SIGN_WAIT, syn.AGENT_WAIT = 2, 1
        note(key=str(HOME / 'signing-agent.pub'), kind='agent', agent=str(stuck))
        t = time.time()
        sig = syn.sign(message('Nobody unlocks the agent.'), K)
        took = time.time() - t
        check(sig is None and 1.5 < took < 5, NAMES[8], f'{took:.1f} s, {sig}')
        t = time.time()
        got = syn.agent_keys(str(stuck))
        took = time.time() - t
        check(got is None and took < 4, NAMES[9], f'{took:.1f} s, {got}')
    finally:
        restore()
        os.environ.pop('SSH_AUTH_SOCK', None)
        close(server, held)
        agent.terminate()
        agent.wait(10)

# --- a key file, while the agent hangs: the yes of a mission in its hook ------------------------------------------------
NAMES = ('a key file signs at once while SSH_AUTH_SOCK names an agent that never answers: ssh-keygen reads it '
         'without asking any agent',
         'the yes of a mission (hook_post) signs its invites with such a key file in the hook, at once, and queues none',
         'a key file with a passphrase does not sign without the agent: hook_post queues its message and the ones '
         'after it, in order, and asks no agent')
if not POSIX:
    skipped(NAMES, 'no Unix socket here')
else:
    server, held = never_answers(SOCKS / 'hangs.sock')
    os.environ['SSH_AUTH_SOCK'] = str(SOCKS / 'hangs.sock')
    try:
        note(key=str(JULE), kind='file', agent=None)
        t = time.time()
        verdict = signed('Signed by the key file.')
        check(verdict == 'ok' and time.time() - t < 2, NAMES[0], f'{verdict}, {time.time() - t:.1f} s')
        invites = [([x], 'Ship it.', {'mission': 'jule-gh-0c0c0c', 'kind': 'invite', 'crew': ['jule-gh', 'kim-gh',
                                                                                              'alex-gh']})
                   for x in ('kim-gh', 'alex-gh')]
        before, t = mail(), time.time()
        waiting = syn.hook_post(K, invites)
        new, took = mail()[len(before):], time.time() - t
        check(waiting == [] and not queued() and took < 2 and [n['to'] for n in new] == [['kim-gh'], ['alex-gh']]
              and all(n.get('sig') and n.get('kind') == 'invite' for n in new), NAMES[1], f'{took:.1f} s, {new}')
        note(key=str(LOCKED), kind='file', agent=None)
        before, t = mail(), time.time()
        waiting = syn.hook_post(K, invites)
        took = time.time() - t
        check(waiting == ['kim-gh', 'alex-gh'] and [r['to'] for r in queued()] == [['kim-gh'], ['alex-gh']]
              and mail() == before and took < 3 and not held, NAMES[2], f'{took:.1f} s, {waiting}, {len(held)} asked')
    finally:
        os.environ.pop('SSH_AUTH_SOCK', None)
        close(server, held)
        empty_outbox()
asked = []
syn.sign = lambda n, k, quick=None: asked.append(quick) or SIG
note(key=str(HOME / 'signing-agent.pub'), kind='agent', agent=None)
waiting = syn.hook_post(K, [(['kim-gh', 'alex-gh'], 'joined', {'mission': 'jule-gh-0c0c0c', 'kind': 'joined'})])
check(waiting == ['kim-gh', 'alex-gh'] and not asked and [r['fields']['kind'] for r in queued()] == ['joined'],
      'a key in an agent or on a security key: hook_post queues at once, without any question to the key', asked)
empty_outbox()
note(key=None, kind=None, agent=None)
syn.sign = REAL['sign']
waiting = syn.hook_post(K, [(['kim-gh'], 'joined', {'mission': 'jule-gh-0c0c0c', 'kind': 'joined'})])
check(waiting == [] and not queued() and mail()[-1].get('kind') == 'joined' and 'sig' not in mail()[-1],
      'without any key, hook_post posts it unsigned, as in 0.5', mail()[-1])
restore()

# --- the line before a command waits for the key ------------------------------------------------------------------------
waits = []
for kind, command in (('sk', True), ('sk', False), ('file', True)):
    note(key=str(JULE), kind=kind, agent=None)  # a key file noted as one on a security key signs at once all the same
    syn.COMMAND, err = command, io.StringIO()
    with redirect_stderr(err):
        sig = syn.sign(message('A touch, please.'), K)
    waits.append((bool(sig), 'Waiting for your SSH key' in err.getvalue()))
restore()
check(waits == [(True, True), (True, False), (True, False)], 'a command says that it waits for a key in an agent or '
      'on a security key, then signs; a hook or the watcher says nothing, nor does a command with a key file', waits)
why = []
for kind in ('sk', 'agent', 'file'):
    note(key=str(JULE), kind=kind, agent=None)
    why.append(syn.unsigned_why())
check('touch' in why[0] and 'unlock' in why[1] and 'ssh-add' in why[2],
      'what the human is told when the key did not sign says what to do for each kind of key: touch it, unlock it, '
      'add a key file with a passphrase to ssh-agent', why)

# --- the outbox -------------------------------------------------------------------------------------------------------
CREW = ['jule-gh', 'kim-gh', 'alex-gh']
x = own_mission('jule-gh-a1b2c3', CREW)
mid, until_ = x['id'], x['until']
syn.outbox_put(K, ['kim-gh'], 'Ship the price import: Jule writes it, Kim reviews it.', mission=mid, kind='invite',
               repo=None, crew=CREW, until=until_, from_repo='demo', sig='not from the hook')
records = syn.outbox_records()
r = json.loads(records[0].read_text(encoding='utf-8')) if records else {}
check(len(records) == 1 and r.get('v') == 1 and r.get('to') == ['kim-gh'] and r.get('text', '').startswith('Ship')
      and r.get('fields') == {'mission': mid, 'kind': 'invite', 'crew': CREW, 'until': until_}
      and re.fullmatch(r'[0-9a-f]{32}', r.get('mac', '')),
      'outbox_put(): one record per message with what is fixed now (people, text, mission, its end) and nothing else, '
      'sealed with approve.key', r)
if POSIX:
    check(mode(records[0]) == 0o600 and mode(HOME / 'outbox') == 0o700, 'the record has mode 0600 in a 0700 folder',
          f'{oct(mode(records[0]))} {oct(mode(HOME / "outbox"))}')
else:
    print('ok   skipped: the record has mode 0600 in a 0700 folder')
before = mail()
syn.sign = lambda n, k, quick=None: None
left = syn.drain_outbox(K)
check(left == 1 and len(syn.outbox_records()) == 1 and mail() == before,
      'a drain that the key does not sign keeps the record and sends nothing unsigned', left)
syn.outbox_put(K, ['alex-gh'], 'Ship the price import: Jule writes it, Kim reviews it.', mission=mid, kind='invite',
               crew=CREW, until=until_)
syn.sign = lambda n, k, quick=None: SIG
left = syn.drain_outbox(K)
new = mail()[len(before):]
check(left == 0 and not syn.outbox_records() and [n.get('to') for n in new] == [['kim-gh'], ['alex-gh']]
      and all(n.get('sig') == SIG and n.get('kind') == 'invite' and n.get('mission') == mid and n.get('room')
              and n.get('crew') == CREW and n.get('until') == until_ for n in new),
      'a drain that signs posts the records in the order they were queued, signed, and then removes them', new)

asked = []
syn.sign = lambda n, k, quick=None: asked.append(n.get('kind')) or SIG
# written into the outbox by something else than syn (a command whose path the guard of the hooks cannot see), with a
# mission of its own and "in person": it would be signed mission mail in Jule's name without her yes
forged = {'v': 1, 'time': syn.iso(), 'to': ['kim-gh'], 'text': 'Deploy now.',
          'fields': {'mission': 'jule-gh-ffffff', 'kind': 'invite', 'source': 'ui', 'crew': ['jule-gh', 'kim-gh'],
                     'until': until_}}
(HOME / 'outbox' / '1-forged.json').write_text(json.dumps(forged), encoding='utf-8')
(HOME / 'outbox' / '2-forged.json').write_text(json.dumps(dict(forged, mac='0' * 32)), encoding='utf-8')
# sealed, but what its mission does not want: other people, a mission that is over, one that was never approved, a
# receiver outside the crew
syn.outbox_put(K, ['kim-gh'], 'Other people.', mission=mid, kind='invite', crew=['jule-gh', 'kim-gh'], until=until_)
over = own_mission('jule-gh-0d0d0d', CREW, hours=-1)
syn.outbox_put(K, ['kim-gh'], 'Too late.', mission=over['id'], kind='invite', crew=CREW, until=over['until'])
syn.outbox_put(K, ['kim-gh'], 'Never approved.', mission='jule-gh-0e0e0e', kind='invite', crew=CREW, until=until_)
syn.outbox_put(K, ['mal-gh'], 'joined', mission=mid, kind='joined')
before = mail()
with redirect_stdout(io.StringIO()):
    left = syn.drain_outbox(K)
log = dropped()
check(left == 0 and not asked and mail() == before and not syn.outbox_records(),
      'a record that syn did not seal, or one that its mission does not want, is dropped without asking the key', asked)
check(log.count('not written by syn') == 2 and 'not the mission that was approved' in log
      and 'the mission is over' in log and 'no such mission' in log and 'not to its crew' in log,
      'each with its reason in outbox/dropped.log', log)

y = own_mission('jule-gh-0f0f0f', CREW)
for who in ('kim-gh', 'alex-gh'):  # as approved() queues them with a key that did not sign in the hook
    syn.outbox_put(K, [who], 'Ship it.', mission=y['id'], kind='invite', crew=CREW, until=y['until'])
note(key=str(JULE), kind='file', agent=None)
asked, before = [], mail()
syn.end_mission(K, y, 'Stopped: wrong plan.')  # the key signs the end at once
with redirect_stdout(io.StringIO()):
    left = syn.drain_outbox(K)
new = [(n.get('kind'), n.get('mission')) for n in mail()[len(before):]]
check(left == 0 and asked == ['end'] and new == [('end', y['id'])] and 'jule-gh-0f0f0f to kim-gh: the mission has ended'
      in dropped(), 'an invite that still waits when its mission ends is dropped: the drain asks no key for it and posts '
                    'nothing, so no receiver sees the mission start after its end', (asked, new))

syn.outbox_put(K, ['kim-gh'], 'joined', mission=mid, kind='joined')
with syn.Lock('outbox'):
    left = syn.drain_outbox(K)
check(left is None and len(syn.outbox_records()) == 1,
      'one drain at a time: while another one holds the lock of the outbox, drain_outbox() returns None', left)
(HOME / 'outbox' / '0-junk.json').write_text('{"half', encoding='utf-8')
r = json.loads(syn.outbox_records()[-1].read_text(encoding='utf-8'))
r['time'] = syn.iso(syn.now() - timedelta(hours=25))
r['mac'] = syn.record_mac(r, syn.approve_key(), 'outbox record')  # as old as that, sealed by syn
syn.outbox_records()[-1].write_text(json.dumps(r), encoding='utf-8')
before, out = mail(), io.StringIO()
with redirect_stdout(out):
    left = syn.drain_outbox(K)
log = dropped()
check(left == 0 and not syn.outbox_records() and mail() == before and 'joined of mission jule-gh-a1b2c3 to kim-gh, '
      'not signed within 24 h' in log and '0-junk.json: unreadable' in log and 'outbox: dropped' in out.getvalue(),
      'a record older than 24 h is dropped, and so is one that cannot be read, with a line in the log and in '
      'outbox/dropped.log', log)

calls, result = [], [1]
syn.drain_outbox = lambda k: calls.append(time.time()) or result[0]
box, said = syn.Outbox(K), io.StringIO()


def tick():
    with redirect_stdout(said):
        box.run()
        if box.t:
            box.t.join(5)


syn.outbox_put(K, ['kim-gh'], 'joined', mission=mid, kind='joined')
tick()
tick()
check(len(calls) == 1, "the watcher's Outbox drains a new record at once, and while the key does not sign, not again "
                       "within a few seconds of the last try", calls)
box.at = time.time() - syn.Outbox.GAP - 0.1  # the last try started GAP seconds ago
tick()
box.at = time.time() - syn.Outbox.GAP - 0.1
tick()
check(len(calls) == 3 and said.getvalue().count('1 waiting for the signing key') == 1,
      'then it tries again as soon as the last try is a few seconds old, each time anew (the human can touch or unlock '
      'the key whenever they are there), and says so in its log once', (calls, said.getvalue()))
syn.outbox_put(K, ['kim-gh'], 'joined', mission=mid, kind='joined')
result[0] = 0
tick()
check(len(calls) == 4 and box.said is None, 'a new record is tried at once, and a drain that went through ends the '
                                            'waiting', (calls, box.said))
restore()
empty_outbox()

# --- the end of a mission -------------------------------------------------------------------------------------------------
m = own_mission('jule-gh-0a0b0c', ['jule-gh', 'kim-gh'])
note(key=str(JULE), kind='sk', agent=None)
syn.sign = lambda n, k, quick=None: None
before, here = mail(), syn.joined_here(K, syn.missions(K).get(m['id']))
n, why = syn.end_mission(K, m, 'Stopped by Jule in person.', source='ui')
waits = queued()
check(n is None and why == 'key' and mail() == before and (syn.own_missions().get(m['id']) or {}).get('ended')
      and here == {'jul11111'} and not syn.joined_here(K, syn.missions(K).get(m['id']))
      and [(r['to'], r['fields']) for r in waits] == [(['kim-gh'], {'mission': m['id'], 'kind': 'end', 'source': 'ui'})],
      'a mission end that the key does not sign ends the mission here at once (Stop always takes effect), and the end '
      'waits in the outbox, "in person" kept', (n, why, here, syn.own_missions().get(m['id']), waits))
syn.sign = lambda n, k, quick=None: SIG
left = syn.drain_outbox(K)
check(left == 0 and not syn.outbox_records() and mail()[-1].get('kind') == 'end' and mail()[-1].get('sig') == SIG
      and mail()[-1].get('source') == 'ui' and mail()[-1].get('mission') == m['id'],
      'once the key signs, the watcher posts that end, signed', mail()[-1])
seen = []


def look(n, k, quick=None):  # what is on disk while the key is asked
    seen.append(([(r['fields'].get('kind'), r['fields'].get('mission')) for r in queued()],
                 bool((syn.own_missions().get(n.get('mission')) or {}).get('ended'))))
    return SIG


syn.sign = look
m = own_mission('jule-gh-1a1b1c', ['jule-gh', 'kim-gh'])
n, why = syn.end_mission(K, m, 'Shipped.')
check(n and why is None and n.get('sig') == SIG and mail()[-1] == n and not syn.outbox_records()
      and syn.own_missions()[m['id']].get('ended') and seen == [([('end', m['id'])], True)],
      'with a key that signs, the end goes out signed at once; while the key is asked, the mission has ended here and '
      'its end waits in the outbox already, which is empty again once the end is posted', (n, why, seen))
asked = []
syn.sign = lambda n, k, quick=None: asked.append(n.get('kind')) or SIG
m = own_mission('jule-gh-3a3b3c', ['jule-gh', 'kim-gh'])
before = mail()
with syn.Lock('outbox'):  # the watcher drains the outbox right now
    n, why = syn.end_mission(K, m, 'Shipped while the watcher drains.')
waits, then = queued(), list(asked)
left = syn.drain_outbox(K)
check(n is None and why == 'busy' and not then and [r['fields'].get('kind') for r in waits] == ['end']
      and (syn.own_missions().get(m['id']) or {}).get('ended') and left == 0 and asked == ['end']
      and [(x.get('kind'), x.get('mission')) for x in mail()[len(before):]] == [('end', m['id'])],
      'while the watcher drains the outbox, the end asks no key a second time: it ends here and waits there, and the '
      'next drain posts it', (n, why, then, waits, asked))


def interrupted(n, k, quick=None):  # Ctrl-C while the key waits for a touch
    raise KeyboardInterrupt


syn.sign = interrupted
m = own_mission('jule-gh-4a4b4c', ['jule-gh', 'kim-gh'])
before = mail()
try:
    syn.end_mission(K, m, 'Stopped: wrong plan.')
    got = 'not interrupted'
except KeyboardInterrupt:
    got = 'interrupted'
waits = queued()
syn.sign = lambda n, k, quick=None: SIG
left = syn.drain_outbox(K)  # None if the interrupt had left the lock of the outbox taken
check(got == 'interrupted' and (syn.own_missions().get(m['id']) or {}).get('ended')
      and [(r['to'], r['fields']) for r in waits] == [(['kim-gh'], {'mission': m['id'], 'kind': 'end'})] and left == 0
      and [(x.get('kind'), x.get('mission'), x.get('sig')) for x in mail()[len(before):]] == [('end', m['id'], SIG)],
      'an end interrupted while the key waits (KeyboardInterrupt) has ended the mission here and waits in the outbox; '
      'the lock of the outbox is free again, and once the key signs, the watcher posts the end', (got, waits, left))
note(key=None, kind=None, agent=None)
syn.sign = lambda n, k, quick=None: None
m = own_mission('jule-gh-2a2b2c', ['jule-gh', 'kim-gh'])
n, why = syn.end_mission(K, m, 'Shipped too.')
check(n and why is None and mail()[-1].get('mission') == m['id'] and 'sig' not in mail()[-1]
      and not syn.outbox_records(), 'without any key the end goes out unsigned, as before', mail()[-1])
restore()

# --- `syn mission end` killed or interrupted while it waits for the key ---------------------------------------------------
# in a process of its own, as a terminal or Claude Code runs it: a closed terminal or a timeout kills it, Ctrl-C
# interrupts it. The room's repo is left out (is_setup), and so is the watcher it would start
CHILD = S / 'end_child.py'
CHILD.write_text('''import signal, sys, time
signal.signal(signal.SIGINT, signal.default_int_handler)  # Ctrl-C, also where the tests run with SIGINT ignored
sys.path.insert(0, sys.argv[1])
import syn
syn.is_setup = lambda k: True
syn.identity_agent = lambda config=None: None  # no agent of the machine that runs the tests is asked
if sys.argv[2] == 'touch':  # a key that waits for a touch nobody gives, on any system
    def waits(n, k, quick=None):
        print('Waiting for your SSH key: touch it or unlock it if it asks.', file=sys.stderr, flush=True)
        time.sleep(120)
    syn.sign = waits
syn.main(['mission', 'end', 'Stopped: wrong plan.'])
''', encoding='utf-8')
CHILD_ENV = dict(os.environ, SYN_ME='jule-gh', SYN_NAME='Jule', SYN_MACHINE='one', SYN_REMOTE=K['remote'],
                 SYN_SIGN_WAIT='60')


def end_in_child(sid, how, ready, stop):
    """Runs `syn mission end` from session sid in a process of its own; once ready(stderr lines) says that it waits for
    the key, stop(process) kills or interrupts it. Returns its exit code and output."""
    p = subprocess.Popen([sys.executable, str(CHILD), str(ROOT), how], stdin=subprocess.DEVNULL,
                         env=dict(CHILD_ENV, CLAUDE_CODE_SESSION_ID=f'{sid}-5f0e-4c1d'), stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    err = []
    th = threading.Thread(target=lambda: err.extend(x.decode('utf-8', 'replace') for x in p.stderr), daemon=True)
    th.start()
    if until(lambda: ready(err), 30):
        stop(p)
    else:
        p.kill()
    out = p.stdout.read().decode('utf-8', 'replace')
    try:
        p.wait(30)
    except subprocess.TimeoutExpired:
        p.kill()
        p.wait(30)
    th.join(10)
    return p.returncode, out + ''.join(err)


def end_left(mid, before):
    """(the mission ended here, what waits in the outbox, mail posted since before, the drain went through): what a
    killed or interrupted `mission end` left, then a drain of the watcher whose key signs."""
    ended = bool((syn.own_missions().get(mid) or {}).get('ended'))
    waits = [(r['to'], r['fields']) for r in queued()]
    posted = mail()[len(before):]
    syn.sign = lambda n, k, quick=None: SIG
    drained = until(lambda: syn.drain_outbox(K) == 0, 10)  # a killed process's lock may take a moment on Windows
    return ended, waits, posted, drained and [(x.get('kind'), x.get('mission'), x.get('sig'))
                                              for x in mail()[len(before):]] == [('end', mid, SIG)]


empty_outbox()
note(key=str(JULE), kind='sk', agent=None)
m = own_mission('jule-gh-6a6b6c', ['jule-gh', 'kim-gh'], sid='end11111')  # the only mission of that session
before = mail()
code, out = end_in_child('end11111', 'touch', lambda err: any('Waiting for your SSH key' in x for x in err),
                         lambda p: p.terminate())  # SIGTERM; TerminateProcess on Windows
ended, waits, posted, sent = end_left(m['id'], before)
check(code != 0 and ended and waits == [(['kim-gh'], {'mission': m['id'], 'kind': 'end'})] and not posted and sent,
      '`mission end` killed (SIGTERM) while it waits for the key: the mission has ended here and its end waits in the '
      'outbox, which the watcher posts once the key signs', (code, out, ended, waits, posted))
restore()
NAME = ('`mission end` interrupted with Ctrl-C while an ssh-agent that never answers holds the key: it says that the '
        'mission ended here and the end waits, its question to the agent ends, and the watcher posts the end later')
if not POSIX:
    print(f'ok   skipped: {NAME} (no Unix socket here)')
else:
    server, held = never_answers(SOCKS / 'ctrlc.sock')
    try:
        note(key=f'{AGKEY}.pub', kind='agent', agent=str(SOCKS / 'ctrlc.sock'))
        m = own_mission('jule-gh-7a7b7c', ['jule-gh', 'kim-gh'], sid='end22222')
        before = mail()
        code, out = end_in_child('end22222', 'agent', lambda err: bool(held), lambda p: p.send_signal(signal.SIGINT))

        def hung_up(c):  # ssh-keygen was ended: its connection to the agent is closed
            c.settimeout(10)
            try:
                while c.recv(4096):
                    pass
                return True
            except OSError:
                return False

        ended, waits, posted, sent = end_left(m['id'], before)
        check(code == 1 and f"Interrupted. Mission {m['id']} ended here" in out and 'Waiting for your SSH key' in out
              and all(hung_up(c) for c in held) and ended and waits == [(['kim-gh'], {'mission': m['id'], 'kind': 'end'})]
              and not posted and sent, NAME, (code, out, len(held), ended, waits, posted))
    finally:
        close(server, held)
        restore()
empty_outbox()

# --- numbers in the environment -----------------------------------------------------------------------------------------
got = []
for value in ('30s', 'nan', 'inf', '-5', '1000', '12.5', ''):
    os.environ['SYN_SIGN_WAIT'] = value
    got.append(syn.setting('SYN_SIGN_WAIT', 30.0, low=1, high=300))
os.environ.pop('SYN_SIGN_WAIT')
check(got == [30.0, 30.0, 30.0, 1, 300, 12.5, 30.0], 'SYN_SIGN_WAIT: a value that is not a finite number counts as 30, '
      'any other is kept within 1 to 300 seconds', got)
e = {'session_id': 'num11111', 'cwd': str(S), 'tool_name': 'Write',
     'tool_input': {'file_path': str(HOME / 'missions.json'), 'content': '{}'}}
env = dict(os.environ, SYN_SIGN_WAIT='30s', SYN_TICK='fast', SYN_IDLE='nan', SYN_WAKE_MIN='x', SYN_CONFLICT_TICK='1m',
           SYN_UI_PORT='port')
r = subprocess.run([sys.executable, str(ROOT / 'hook.py'), 'PreToolUse'], input=json.dumps(e), capture_output=True,
                   text=True, env=env, timeout=60)
check('"permissionDecision": "deny"' in r.stdout, 'numbers of syn in the environment that are none (SYN_SIGN_WAIT=30s, '
      'SYN_TICK=fast, ...) no longer stop the hooks at start: the guard of ~/.synchronauts still refuses',
      r.stdout + r.stderr)

# --- what the watcher asks a key ends with it -----------------------------------------------------------------------------
NAME = ('end_children(), when the watcher ends: a question to a key that runs now ends, with what it started (as '
        'ssh-keygen starts ssh-sk-helper for a touch), and no new one starts')
if not POSIX:
    print(f'ok   skipped: {NAME} (no process groups here)')
else:
    pids, results = S / 'grandchild.pid', []
    code = ('import subprocess, sys, time; p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"]); '
            'open(sys.argv[1], "w").write(str(p.pid)); time.sleep(60)')

    def ask():
        try:
            results.append(syn.run_child([sys.executable, '-c', code, str(pids)], timeout=60).returncode)
        except OSError as f:
            results.append(f)

    th = threading.Thread(target=ask, daemon=True)
    th.start()
    until(lambda: pids.exists() and pids.read_text().strip(), 20)
    grandchild = int(pids.read_text())
    syn.end_children()
    th.join(10)

    def gone():
        try:
            os.kill(grandchild, 0)
        except ProcessLookupError:
            return True
        except OSError:
            return False
        return False

    ended = until(gone, 10)
    try:
        syn.run_child([sys.executable, '-c', 'pass'])
        refused = False
    except OSError:
        refused = True
    check(not th.is_alive() and ended and refused and not syn.CHILDREN, NAME, (results, ended, refused))
    restore()

if failures:
    sys.exit(1)
print('signing: all green')
