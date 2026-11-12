#!/usr/bin/env python3
"""For e2e.sh: the documents, repo files and the board's texts stay in step with the code. Pure file reading, no
watchers, about a second. Prints `ok   <what>` per check and `FAIL <what>` with the details; exit 1 if anything failed.
Usage: docs_check.py [<repo root>], by default the repo this file is in. Python 3.9 syntax."""
import ast
import json
import os
import py_compile
import re
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(errors='backslashreplace')
ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent.parent).resolve()
failures = []


def ok(what):
    print(f'ok   {what}')


def check(condition, what, detail=''):
    if condition:
        ok(what)
    else:
        failures.append(what)
        print(f'FAIL {what}')
        if detail:
            print(f'---- {detail}')


def text(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


def tree_files():
    """Every file of the working tree that is not git's, not a bytecode cache and not binary."""
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in ('.git', '__pycache__', 'node_modules'))
        for name in sorted(files):
            if name != '.git':  # a worktree has a file of that name
                yield Path(base, name)


# --- Version: one number everywhere ----------------------------------------------------------------------------------

SYN = text('syn.py')
VERSION = re.search(r"^VERSION = '(.+)'", SYN, re.M).group(1)
short = '.'.join(VERSION.split('.')[:2])
plugin = json.loads(text('.claude-plugin/plugin.json'))
market = json.loads(text('.claude-plugin/marketplace.json'))
versions = {'syn.py': VERSION, 'plugin.json': plugin['version'], **{f'marketplace.json {p["name"]}': p['version']
                                                                  for p in market['plugins']}}
changelog = text('CHANGELOG.md') if (ROOT / 'CHANGELOG.md').exists() else ''
released = re.search(r'^## \[(\d+\.\d+\.\d+)\]', changelog, re.M)
versions['CHANGELOG.md'] = released.group(1) if released else '(no version heading)'
footers = {
    'README.md': r'Early \((\d+\.\d+)\)', 'README.de.md': r'Früh \((\d+\.\d+)\)',
    'docs/guide.md': r'Status: early \((\d+\.\d+)\)', 'docs/guide.de.md': r'Stand: früh \((\d+\.\d+)\)'}
short_versions = {}
for rel, pattern in footers.items():
    found = re.search(pattern, text(rel))
    short_versions[rel] = found.group(1) if found else '(none)'
check(len(set(versions.values())) == 1 and set(short_versions.values()) == {short},
      f'one version in script, plugin, marketplace, changelog and docs ({VERSION})',
      f'versions {versions}, footers {short_versions}, expected {short}')

# the longest mission: one constant, quoted in the guides and the skill
max_hours = float(re.search(r'^MISSION_MAX_HOURS = ([\d.]+)', SYN, re.M).group(1))
quoted = {
    'docs/guide.md': re.search(r'by default, at most ([\d.]+) hours', text('docs/guide.md')),
    'docs/guide.de.md': re.search(r'höchstens ([\d,]+) Stunden', text('docs/guide.de.md')),
    'SKILL.md': re.search(r'default 2 h, at most ([\d.]+)', text('skills/synchronauts/SKILL.md'))}
numbers = {rel: float(m.group(1).replace(',', '.')) if m else None for rel, m in quoted.items()}
check(all(n == max_hours for n in numbers.values()), f'the longest mission is {max_hours:g} h in code, guides and skill',
      f'{numbers}')

# --- Files -----------------------------------------------------------------------------------------------------------

needed = ['SECURITY.md', 'CONTRIBUTING.md', 'CODE_OF_CONDUCT.md', 'CHANGELOG.md', '.github/dependabot.yml',
          '.github/ISSUE_TEMPLATE/bug_report.yml', '.github/ISSUE_TEMPLATE/feature_request.yml',
          '.github/ISSUE_TEMPLATE/config.yml', '.github/pull_request_template.md', '.github/workflows/test.yml',
          'test/budget.json', 'test/measure.py']
missing = [rel for rel in needed if not (ROOT / rel).is_file()]
check(not missing, 'the repo files exist (security, contributing, code of conduct, changelog, templates, dependabot, budget)', str(missing))
if not missing:
    check(re.search(r'package-ecosystem:\s*["\']?github-actions["\']?', text('.github/dependabot.yml')),
          'dependabot watches the GitHub actions')
    ci = text('.github/workflows/test.yml')
    check('timeout-minutes: 20' in ci and 'concurrency:' in ci and 'measure.py --check test/budget.json' in ci,
          'CI has a 20 minute limit, cancels superseded runs and checks the token budget')
check('eol=lf' in text('.gitattributes'), '.gitattributes keeps LF line ends')
crlf = [str(p.relative_to(ROOT)) for p in tree_files()
        if p.suffix in ('.py', '.sh', '.md', '.json', '.yml', '.html', '.js') and b'\r' in p.read_bytes()]
check(not crlf, 'no CRLF in text files (they would break bash scripts on Windows)', str(crlf))

# --- No company data, no e-mail addresses in the tree ----------------------------------------------------------------

DENY = ['bro' + 'gno', 'tinten' + 'dienst', 'urs.' + 'alfas']  # built from parts: this file would hit itself
EMAIL = re.compile(r'[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)')
# hidden and direction characters as such: a line with one reads differently than it runs, so the tests write them as
# escapes (the set of syn.py's INVISIBLE)
HIDDEN = re.compile('[\u00ad\u034f\u061c\u115f\u1160\u17b4\u17b5\u180b-\u180f\u200b-\u200f\u2028-\u202e\u2060-\u2069'
                    '\u3164\ufeff\uffa0\ufff9-\ufffb\U000e0000-\U000e007f]')
hits, hidden = [], []
for p in tree_files():
    try:
        body = p.read_text(encoding='utf-8')
    except (UnicodeDecodeError, OSError):
        continue  # binary: images
    rel = str(p.relative_to(ROOT))
    hidden += [f'{rel}: line {body[:m.start()].count(chr(10)) + 1}, U+{ord(m.group()):04X}' for m in HIDDEN.finditer(body)]
    hits += [f'{rel}: {w}' for w in DENY if w in body.lower()]
    for m in EMAIL.finditer(body):  # OpenSSH names key types so: sk-ssh-ed25519@openssh.com is no address
        local = m.group(0).split('@')[0]
        if local not in ('git', 'noreply') and not re.fullmatch(
                r'example\.(com|org|net)|[\w.-]*noreply\.github\.com|openssh\.com', m.group(1)):
            hits.append(f'{rel}: {m.group(0)}')
check(not hits, 'no company data and no e-mail addresses in the tree', '\n'.join(hits))
check(not hidden, 'no file in the tree holds a hidden or direction character as such, only as an escape',
      '\n'.join(hidden[:20]))

# --- JSON, hooks, Python ---------------------------------------------------------------------------------------------

jsons = ['.claude-plugin/plugin.json', '.claude-plugin/marketplace.json', 'hooks/hooks.json', 'test/budget.json',
         'ui/manifest.webmanifest'] + [rel for rel in ('.mcp.json',) if (ROOT / rel).exists()]
bad = []
for rel in jsons:
    try:
        json.loads(text(rel))
    except ValueError as error:
        bad.append(f'{rel}: {error}')
check(not bad, 'the JSON files parse', '\n'.join(bad))

ALLOWED_EVENTS = {'SessionStart', 'UserPromptSubmit', 'PreToolUse', 'PostToolUse', 'PermissionRequest', 'Notification',
                  'Stop', 'StopFailure', 'SubagentStart', 'SubagentStop', 'CwdChanged', 'PostCompact', 'PreCompact',
                  'SessionEnd'}
hooks = json.loads(text('hooks/hooks.json'))['hooks']
templates, tools = set(), {}
for event, groups in hooks.items():
    for group in groups:
        for h in group['hooks']:
            templates.add(h['command'].replace(f'hook.py" {event}', 'hook.py" EVENT'))
        tools.setdefault(event, set()).update((group.get('matcher') or '').split('|'))
check(set(hooks) <= ALLOWED_EVENTS and all(f"'{e}'" in SYN or f'"{e}"' in SYN or e in SYN for e in hooks),
      'every event in hooks.json is a known one that syn.py handles', f'{sorted(set(hooks) - ALLOWED_EVENTS)}')
# the session start alone goes on when Python does not start (missing, the Windows store's placeholder, too old to
# import syn.py): it prints a line for the human instead, and the other hooks show their error
line = 'py=python3; [ "$OS" = Windows_NT ] && py=python; "$py" "${CLAUDE_PLUGIN_ROOT}/hook.py" EVENT'
extra = [t[len(line):] for t in templates if t != line and t.startswith(line)]
start = hooks['SessionStart'][0]['hooks'][0]['command']
said = re.fullmatch(r" \|\| echo '(\{[^']+\})'", extra[0]) if len(extra) == 1 else None
try:
    said = json.loads(said.group(1)) if said else {}
except ValueError:
    said = {}
check(templates - {line + x for x in extra} == {line} and len(extra) == 1 and start.endswith(extra[0]),
      'every hook runs the same command line, and only the session start adds a fallback', str(templates))
check(set(said) == {'systemMessage'} and 'Python 3.9' in said['systemMessage'],
      'whose fallback is a line for the human that names the Python it needs', str(extra))
route = {'Edit', 'Write', 'MultiEdit', 'NotebookEdit', 'Bash'}
check(route <= tools.get('PreToolUse', set()) and route <= tools.get('PostToolUse', set()),
      'Bash and the edit tools go through both tool matchers', str({e: sorted(t) for e, t in tools.items()}))

reads = {'Read', 'Grep', 'Glob'}
check(reads <= tools.get('PreToolUse', set()) and not reads & tools.get('PostToolUse', set()),
      'Read, Grep and Glob go through PreToolUse only, so the refusal of the key files happens',
      str({e: sorted(t) for e, t in tools.items()}))

pyfiles = [p for p in tree_files() if p.suffix == '.py']
broken = []
for p in pyfiles:
    try:
        py_compile.compile(str(p), cfile=os.path.join(tempfile.gettempdir(), f'syn-docs-check-{os.getpid()}.pyc'),
                           doraise=True)
        ast.parse(p.read_text(encoding='utf-8'), feature_version=(3, 9))  # no match statements and the like
    except (py_compile.PyCompileError, SyntaxError) as error:
        broken.append(f'{p.relative_to(ROOT)}: {error}')
check(not broken, 'every Python file compiles with Python 3.9 syntax', '\n'.join(broken))
try:
    os.unlink(os.path.join(tempfile.gettempdir(), f'syn-docs-check-{os.getpid()}.pyc'))
except OSError:
    pass

stdlib = getattr(sys, 'stdlib_module_names', None)  # Python 3.10 and newer
if stdlib:
    outside = []
    for name in ('syn.py', 'hook.py', 'mcp.py'):
        if (ROOT / name).exists():
            for node in ast.walk(ast.parse(text(name))):
                mods = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                    [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else []
                outside += [f'{name}: {m}' for m in mods if m.split('.')[0] not in stdlib | {'syn', 'mcp'}]
    check(not outside, 'only the standard library is imported', str(outside))
else:
    ok('skipped: the import check needs Python 3.10 (the CI runs it on 3.14)')
check(len(re.findall(r'\.fromisoformat\(', SYN)) == 1 and not re.search(r'zip\([^)]*strict=', SYN),
      'one place reads time stamps (parse) and no zip(strict=): both break on Python 3.9')

# --- English and German keep step ------------------------------------------------------------------------------------


def fenced(md):
    """(lines outside the code blocks, [first line of each code block])."""
    outside, blocks, inside = [], [], False
    for line in md.splitlines():
        if line.startswith('```'):
            inside = not inside
            if inside:
                blocks.append('')
            continue
        if inside:
            if not blocks[-1] and line.strip():
                blocks[-1] = line.strip()
        else:
            outside.append(line)
    return outside, blocks


def headings(md):
    return [(len(m.group(1)), m.group(2)) for m in (re.match(r'(#{1,6})\s+(.*?)\s*#*$', x) for x in fenced(md)[0]) if m]


def slug(heading, seen):
    h = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', heading).replace('`', '').replace('*', '').lower()
    s = ''.join(c for c in h if c.isalnum() or c in '_- ').replace(' ', '-')
    n = seen.get(s, 0)
    seen[s] = n + 1
    return s if not n else f'{s}-{n}'


COMMAND = re.compile(r'(~/\.synchronauts/syn |syn |claude |gh |bash |python3? |set -g )')
pairs = [('README.md', 'README.de.md'), ('docs/guide.md', 'docs/guide.de.md')]
for en, de in pairs:
    a, b = text(en), text(de)
    count = lambda md: len(headings(md)) + len(re.findall(r'<h[1-6]\b', md))  # noqa: E731
    check(count(a) == count(b), f'{en} and {de} have the same number of headings', f'{count(a)} against {count(b)}')
    # the README's placeholders are translated (you/agents-room, du/agents-room): compare the first two words only
    cut = (lambda x: ' '.join(x.split()[:2])) if en.startswith('README') else (lambda x: x)
    ca = [cut(x) for x in fenced(a)[1] if COMMAND.match(x)]
    cb = [cut(x) for x in fenced(b)[1] if COMMAND.match(x)]
    check(ca == cb, f'{en} and {de} show the same commands in the same order', f'{ca}\n{cb}')
guide_en, guide_de = text('docs/guide.md'), text('docs/guide.de.md')


def section(md, *words):
    """The text of the first `##` section whose heading contains one of the words."""
    lines, out, on = md.splitlines(), [], False
    for line in lines:
        if line.startswith('## '):
            on = any(w.lower() in line.lower() for w in words)
            continue
        if on:
            out.append(line)
    return '\n'.join(out)


def table_commands(md, *words):
    return {m.group(1) for m in re.finditer(r'^\|\s*`(?:~/\.synchronauts/)?syn\s+([a-z-]+)', section(md, *words), re.M)}


cmd_en, cmd_de = table_commands(guide_en, 'Commands'), table_commands(guide_de, 'Befehle')
check(cmd_en and cmd_en == cmd_de, 'both guides list the same commands in the Commands table', f'{sorted(cmd_en ^ cmd_de)}')
vars_en, vars_de = set(re.findall(r'\bSYN_[A-Z_]+', guide_en)), set(re.findall(r'\bSYN_[A-Z_]+', guide_de))
check(vars_en == vars_de, 'both guides name the same SYN_ variables', f'{sorted(vars_en ^ vars_de)}')

# every SYN_ variable of the code is in the Settings section of both guides
INTERNAL = {'SYN_NOTE_TITLE', 'SYN_NOTE_BODY'}  # the Windows toast gets its texts through these, nobody sets them
code = ''.join(text(n) for n in ('syn.py', 'mcp.py') if (ROOT / n).exists())
wanted = set(re.findall(r'\bSYN_[A-Z][A-Z_]*', code)) - INTERNAL
fields = re.search(r'^FIELDS = \((.*?)\)', SYN, re.M).group(1)
wanted |= {f'SYN_{f.upper()}' for f in re.findall(r"'(\w+)'", fields)}
for lang, md, words in (('English', guide_en, ('Settings',)), ('German', guide_de, ('Einstellungen',))):
    body = section(md, *words)
    lacking = sorted(v for v in wanted if not re.search(rf'\b{v}\b', body))
    check(body and not lacking, f'the {lang} guide lists every SYN_ variable in its Settings section', str(lacking))

# the room has no private messages: said in the guides and in SECURITY.md
for rel, section_words, pattern in (('docs/guide.md', ('What is shared',), r'(all|every).{0,40}message'),
                                    ('docs/guide.de.md', ('Was geteilt',), r'(alle|jede).{0,40}Nachricht')):
    check(re.search(pattern, section(text(rel), *section_words), re.I | re.S),
          f'{rel} says that every room member can read every message')

# links and anchors resolve, images exist
LINK = re.compile(r'\]\(([^)\s]+)\)|(?:src|srcset|href)="([^"]+)"')
broken = []
for rel in ('README.md', 'README.de.md', 'docs/guide.md', 'docs/guide.de.md', 'SECURITY.md', 'CONTRIBUTING.md',
            'CHANGELOG.md'):
    if not (ROOT / rel).exists():
        continue
    md, base = text(rel), (ROOT / rel).parent
    for m in LINK.finditer(md):
        target = m.group(1) or m.group(2)
        if re.match(r'[a-z]+:', target):
            continue  # https:, mailto:
        path, _, anchor = target.partition('#')
        dest = (base / path).resolve() if path else ROOT / rel
        if not dest.exists():
            broken.append(f'{rel}: {target} does not exist')
        elif anchor and dest.suffix == '.md':
            seen = {}
            slugs = {slug(h, seen) for _, h in headings(dest.read_text(encoding='utf-8'))}
            if anchor not in slugs:
                broken.append(f'{rel}: {target}: no such heading')
check(not broken, 'every link, image and anchor in the documents resolves', '\n'.join(broken))

# --- SECURITY.md, README links ---------------------------------------------------------------------------------------

sec = text('SECURITY.md')
sec_headings = {h.lower() for _, h in headings(sec)}
check({'supported versions', 'reporting', 'threat model'} <= sec_headings,
      'SECURITY.md has the headings Supported versions, Reporting and Threat model', str(sorted(sec_headings)))
signed = re.findall(r"'(\w+)'", re.search(r'^SIGNED = \((.*?)\)', SYN, re.M).group(1))
lacking = [f for f in signed if f'`{f}`' not in sec]
check(not lacking, 'SECURITY.md names every signed mail field', str(lacking))
# every unsigned field of a state that tidy() keeps has a row of its own in the table (S10 adds agents, S19 age_key_fp)
UNSIGNED = ('files', 'claims', 'task', 'branch', 'repo', 'name', 'state', 'tip', 'events')
table = sec.partition('### Unsigned fields of a state')[2].split('\n#')[0]
rows = {w for cell in re.findall(r'^\|([^|\n]*)\|', table, re.M) for w in re.findall(r'[a-z_]+', cell)}
lacking = [f for f in UNSIGNED if f not in rows]
check(table and not lacking, 'SECURITY.md has a row for every unsigned field of a state', str(lacking))
check('security/advisories/new' in sec and not EMAIL.search(sec), 'SECURITY.md reports through the advisory page, no e-mail')
check(re.search(r'(all|every).{0,40}message', sec, re.I | re.S) is not None, 'SECURITY.md says that the room has no private messages')
check(all('SECURITY.md' in text(r) and 'CHANGELOG.md' in text(r) for r in ('README.md', 'README.de.md')),
      'both READMEs link to SECURITY.md and CHANGELOG.md')

# --- The board's texts -----------------------------------------------------------------------------------------------

board = text('ui/index.html')

check("human = n.source === 'ui' && (mine || n.trust === 'ok')" in board,
      "the board's Human badge needs own mail or a valid signature, not the source field alone")


def board_keys(name, lang):
    """The keys of the `lang` object inside `const <name> = {`."""
    body = board[board.index(f'const {name} = {{'):]
    start = body.index(f'\n  {lang}: {{') + 1
    keys = []
    for line in body[start:].splitlines()[1:]:
        if line.startswith('  },'):
            break
        m = re.match(r"    '([^']+)':", line)
        if m:
            keys.append(m.group(1))
    return keys


for name in ('I18N', 'MORE'):
    en, de = board_keys(name, 'en'), board_keys(name, 'de')
    check(en and set(en) == set(de), f'the board has every {name} string in English and German',
          f'only English: {sorted(set(en) - set(de))}; only German: {sorted(set(de) - set(en))}')
    check(len(en) == len(set(en)) and len(de) == len(set(de)), f'no {name} string is defined twice')
# the board's key: in this tab only, never in the browser's lasting storage or a URL, and no address leaves as a Referer
check("localStorage.setItem('syn-key'" not in board and "sessionStorage.setItem('syn-key'" in board
      and not re.search(r'\[#&\]k=|[#&]k=\$\{', board), 'the board keeps its key in the tab only, never in localStorage')
check('<meta name="referrer" content="no-referrer">' in board, 'the board sends no Referer')

# --- The token budget file -------------------------------------------------------------------------------------------

budget = json.loads(text('test/budget.json'))
labels, skill = budget.get('labels'), budget.get('skill_md')
good = (isinstance(labels, dict) and labels and all(isinstance(v, dict) and isinstance(v.get('max'), int) and v['max'] >= 0
                                                   and v.get('why') for v in labels.values())
        and isinstance(skill, dict) and skill.get('label') and skill.get('why')
        and skill['max_chars'] == skill['baseline_chars'] + round(skill['allowance_tokens'] * 3.3))
check(good, 'test/budget.json has a ceiling and a reason for every label, and the SKILL.md allowance')

print(f"\ndocuments and repo files: {'all green' if not failures else str(len(failures)) + ' failed: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
