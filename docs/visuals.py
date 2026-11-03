"""Animated SVGs for the README: hero and how-it-works, dark and light, English and German. Run: python3 docs/visuals.py docs"""
import sys
from pathlib import Path

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)

THEMES = {
    'dark': dict(bg='#07070c', text='#f5f5f7', muted='#b4b4c0', muted2='#8b8b99', card='#ffffff', card_o='.06',
                 line='#ffffff', line_o='.13', accent='#818cf8', green='#4ade80', blue='#60a5fa', amber='#fbbf24',
                 blob_o='.55', pink='#ec4899', sky='#0ea5e9', indigo='#6366f1', on_amber='#1a1300'),
    'light': dict(bg='#f4f6fb', text='#0b0b12', muted='#3f4654', muted2='#6b7280', card='#ffffff', card_o='.78',
                  line='#0f172a', line_o='.12', accent='#4f46e5', green='#16a34a', blue='#2563eb', amber='#d97706',
                  blob_o='.38', pink='#f472b6', sky='#38bdf8', indigo='#818cf8', on_amber='#ffffff'),
}
TEXT = {
    'en': dict(tag="Your team's coding agents, in sync.",
               sub='claude code · codex · no server · a private repo is the bus',
               warn='⚠ same file · src/routes.ts', mail='✉ done with routes.ts?',
               anna="Anna's laptop", ben="Ben's laptop", room='github.com/acme/agents-room · private',
               c1='Every session reports repo, branch and files to its own branch.',
               c2='Each machine fetches the others every few seconds.',
               c3='Overlaps warn before the merge. Messages wake the waiting session.',
               overlap='⚠ Anna is in shop too', woken='woken', waiting='waiting', working='working'),
    'de': dict(tag='Die Coding-Agenten deines Teams, im Gleichtakt.',
               sub='claude code · codex · kein server · privates repo als bus',
               warn='⚠ selbe Datei · src/routes.ts', mail='✉ fertig mit routes.ts?',
               anna='Annas Laptop', ben='Bens Laptop', room='github.com/acme/agents-room · privat',
               c1='Jede Session meldet Repo, Branch und Dateien in ihren eigenen Branch.',
               c2='Jeder Rechner holt alle paar Sekunden die der anderen.',
               c3='Überschneidungen warnen vor dem Merge. Nachrichten wecken die wartende Session.',
               overlap='⚠ Anna ist auch in shop', woken='geweckt', waiting='wartet', working='arbeitet'),
}
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Roboto, Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def backdrop(c, w, h):
    return f'''<defs>
  <radialGradient id="b1"><stop offset="0" stop-color="{c['indigo']}" stop-opacity="{c['blob_o']}"/><stop offset="1" stop-color="{c['indigo']}" stop-opacity="0"/></radialGradient>
  <radialGradient id="b2"><stop offset="0" stop-color="{c['pink']}" stop-opacity="{c['blob_o']}"/><stop offset="1" stop-color="{c['pink']}" stop-opacity="0"/></radialGradient>
  <radialGradient id="b3"><stop offset="0" stop-color="{c['sky']}" stop-opacity="{c['blob_o']}"/><stop offset="1" stop-color="{c['sky']}" stop-opacity="0"/></radialGradient>
  <linearGradient id="word" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="{c['text']}"/><stop offset=".55" stop-color="{c['text']}"/><stop offset="1" stop-color="{c['accent']}"/></linearGradient>
  <clipPath id="frame"><rect width="{w}" height="{h}" rx="28"/></clipPath>
</defs>
<g clip-path="url(#frame)">
<rect width="{w}" height="{h}" fill="{c['bg']}"/>
<circle cx="{w * .12:.0f}" cy="{h * .15:.0f}" r="{h * .8:.0f}" fill="url(#b1)"><animateTransform attributeName="transform" type="translate" values="0 0;70 40;0 0" dur="14s" repeatCount="indefinite"/></circle>
<circle cx="{w * .92:.0f}" cy="{h * .1:.0f}" r="{h * .7:.0f}" fill="url(#b2)"><animateTransform attributeName="transform" type="translate" values="0 0;-60 35;0 0" dur="17s" repeatCount="indefinite"/></circle>
<circle cx="{w * .68:.0f}" cy="{h * 1.05:.0f}" r="{h * .85:.0f}" fill="url(#b3)"><animateTransform attributeName="transform" type="translate" values="0 0;-50 -35;0 0" dur="19s" repeatCount="indefinite"/></circle>
'''


def frame_end(c, w, h):
    return f'''</g>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="28" fill="none" stroke="{c['line']}" stroke-opacity="{c['line_o']}"/>
</svg>
'''


def card(c, x, y, w, h, who, where, dot, extra=''):
    """A session card: centered at x, y."""
    x0, y0 = x - w / 2, y - h / 2
    return f'''<g>
  <rect x="{x0}" y="{y0}" width="{w}" height="{h}" rx="13" fill="{c['card']}" fill-opacity="{c['card_o']}" stroke="{c['line']}" stroke-opacity="{c['line_o']}"/>
  <circle cx="{x0 + 18}" cy="{y}" r="5" fill="{dot}">{extra}</circle>
  <text x="{x0 + 31}" y="{y + 5}" font-size="15" font-weight="700" fill="{c['text']}">{esc(who)}<tspan font-family="{MONO}" font-size="13" font-weight="400" fill="{c['muted']}" dx="7">{esc(where)}</tspan></text>
</g>
'''


def hero(theme, lang):
    c, t, w, h = THEMES[theme], TEXT[lang], 1280, 440
    hx, hy = 1030, 220
    nodes = [(880, 112, 'sam', 'shop@main', c['green']), (1178, 112, 'alex', 'api@main', c['blue']),
             (880, 328, 'jule', 'shop@main', c['green']), (1178, 328, 'kim', 'docs@main', c['green'])]
    s = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" font-family="{SANS}">\n'
    s += backdrop(c, w, h)
    # logo
    s += f'''<g transform="translate(150 220)">
  <circle r="58" fill="none" stroke="{c['text']}" stroke-width="3" opacity=".2"/>
  <circle r="36" fill="none" stroke="{c['text']}" stroke-width="3" opacity=".5"/>
  <path d="M0 -58 A58 58 0 0 1 58 0" fill="none" stroke="{c['text']}" stroke-width="5" stroke-linecap="round"><animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="5s" repeatCount="indefinite"/></path>
  <path d="M0 36 A36 36 0 0 1 -36 0" fill="none" stroke="{c['accent']}" stroke-width="4" stroke-linecap="round"><animateTransform attributeName="transform" type="rotate" from="0" to="-360" dur="3.5s" repeatCount="indefinite"/></path>
  <circle r="13" fill="{c['green']}" opacity=".45"><animate attributeName="r" values="13;30" dur="2.4s" repeatCount="indefinite"/><animate attributeName="opacity" values=".45;0" dur="2.4s" repeatCount="indefinite"/></circle>
  <circle r="13" fill="{c['green']}"/>
</g>
<text x="240" y="206" font-size="68" font-weight="800" letter-spacing="-2.5" fill="url(#word)">Synchronauts</text>
<text x="243" y="250" font-size="24" fill="{c['muted']}">{esc(t['tag'])}</text>
<text x="243" y="290" font-size="15" font-family="{MONO}" fill="{c['muted2']}">{esc(t['sub'])}</text>
'''
    # network: lines, moving dots, the hub, the cards
    for x, y, *_ in nodes:
        s += f'<line x1="{x}" y1="{y}" x2="{hx}" y2="{hy}" stroke="{c["line"]}" stroke-opacity="{float(c["line_o"]) * 1.6:.2f}" stroke-width="1.5" stroke-dasharray="4 6"><animate attributeName="stroke-dashoffset" values="0;-20" dur="1.6s" repeatCount="indefinite"/></line>\n'
    for i, (x, y, *_) in enumerate(nodes):  # every node syncs with the room, out and back
        for back, begin in ((0, i * .7), (1, i * .7 + 1.4)):
            a, b = ((x, y), (hx, hy)) if not back else ((hx, hy), (x, y))
            s += (f'<circle r="3.5" fill="{c["accent"]}"><animateMotion dur="2.8s" begin="{begin:.1f}s" repeatCount="indefinite" '
                  f'keyPoints="0;1;1" keyTimes="0;.5;1" calcMode="linear" path="M{a[0]} {a[1]} L{b[0]} {b[1]}"/>'
                  f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.5;.5;1" dur="2.8s" begin="{begin:.1f}s" repeatCount="indefinite"/></circle>\n')
    s += f'''<g transform="translate({hx} {hy})">
  <circle r="56" fill="none" stroke="{c['accent']}" stroke-opacity=".5" stroke-width="1.5" stroke-dasharray="3 7"><animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="24s" repeatCount="indefinite"/></circle>
  <circle r="42" fill="{c['card']}" fill-opacity="{c['card_o']}" stroke="{c['accent']}" stroke-width="2"/>
  <text y="2" text-anchor="middle" font-size="15" font-weight="700" font-family="{MONO}" fill="{c['text']}">room</text>
  <text y="20" text-anchor="middle" font-size="10" font-family="{MONO}" fill="{c['muted2']}">git</text>
</g>
'''
    # the message: sam → room → alex; alex wakes up
    s += (f'<g><animateMotion dur="7s" repeatCount="indefinite" keyPoints="0;0;.5;1;1" keyTimes="0;.15;.4;.62;1" calcMode="linear" '
          f'path="M880 112 L{hx} {hy} L1178 112"/><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;.14;.16;.6;.63;1" dur="7s" repeatCount="indefinite"/>'
          f'<rect x="-13" y="-10" width="26" height="20" rx="5" fill="{c["accent"]}"/><path d="M-9 -5 L0 2 L9 -5" fill="none" stroke="{c["bg"]}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></g>\n')
    wake = f'<animate attributeName="fill" values="{c["blue"]};{c["blue"]};{c["green"]};{c["green"]}" keyTimes="0;.62;.63;1" dur="7s" repeatCount="indefinite"/>'
    for x, y, who, where, dot in nodes:
        s += card(c, x, y, 176, 46, who, where, dot, wake if who == 'alex' else '')
    # overlap: sam and jule in the same file
    for x, y in ((880, 112), (880, 328)):
        s += (f'<rect x="{x - 92}" y="{y - 27}" width="184" height="54" rx="16" fill="none" stroke="{c["amber"]}" stroke-width="2">'
              f'<animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;.66;.7;.92;.96;1" dur="7s" repeatCount="indefinite"/></rect>\n')
    s += (f'<g opacity="0"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;.68;.72;.92;.96;1" dur="7s" repeatCount="indefinite"/>'
          f'<rect x="782" y="205" width="196" height="30" rx="15" fill="{c["amber"]}"/>'
          f'<text x="880" y="225" text-anchor="middle" font-size="13" font-weight="700" fill="{c["on_amber"]}">{esc(t["warn"])}</text></g>\n')
    s += frame_end(c, w, h)
    return s


def how(theme, lang):
    c, t, w, h = THEMES[theme], TEXT[lang], 1280, 500
    s = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" font-family="{SANS}">\n'
    s += backdrop(c, w, h)
    D = 10  # seconds per loop

    def box(x, y, bw, bh, title, mono=False):
        fam = f'font-family="{MONO}" ' if mono else ''
        return (f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="20" fill="{c["card"]}" fill-opacity="{c["card_o"]}" '
                f'stroke="{c["line"]}" stroke-opacity="{c["line_o"]}"/>'
                f'<text x="{x + 22}" y="{y + 34}" font-size="{13 if mono else 15}" font-weight="700" '
                f'{fam}fill="{c["muted"]}">{esc(title)}</text>\n')

    # left, middle, right
    s += box(48, 60, 340, 250, t['anna'])
    s += box(470, 60, 340, 250, t['room'], mono=True)
    s += box(892, 60, 340, 250, t['ben'])
    # Anna's sessions
    s += card(c, 218, 140, 290, 50, 'claude', 'shop@feat/auth', c['green'])
    s += card(c, 218, 220, 290, 50, 'codex', 'api@main', c['green'])
    # Ben's sessions: shop waits, then is woken
    wake = (f'<animate attributeName="fill" values="{c["blue"]};{c["blue"]};{c["green"]};{c["green"]}" keyTimes="0;.78;.79;1" '
            f'dur="{D}s" repeatCount="indefinite"/>')
    s += card(c, 1062, 140, 290, 50, 'claude', 'shop@main', c['blue'], wake)
    s += card(c, 1062, 220, 290, 50, 'claude', 'web@main', c['green'])
    # state label under Ben's shop session
    s += (f'<text x="1185" y="145" text-anchor="end" font-size="12" font-weight="600" fill="{c["blue"]}">{esc(t["waiting"])}'
          f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.78;.79;1" dur="{D}s" repeatCount="indefinite"/></text>'
          f'<text x="1185" y="145" text-anchor="end" font-size="12" font-weight="700" fill="{c["green"]}" opacity="0">{esc(t["woken"])}'
          f'<animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;.78;.79;.97;1" dur="{D}s" repeatCount="indefinite"/></text>\n')
    # the room's branches
    for i, (name, kt) in enumerate((('syn/anna/mac', '0;.12;.16;.24;.58;.62;.7;1'), ('syn/ben/pc', '0;.3;.34;.42;.42;.42;.42;1'))):
        y = 130 + i * 80
        s += (f'<g><rect x="494" y="{y - 22}" width="292" height="44" rx="12" fill="{c["accent"]}" fill-opacity="0">'
              f'<animate attributeName="fill-opacity" values="0;0;.22;0;0;.22;0;0" keyTimes="{kt}" dur="{D}s" repeatCount="indefinite"/></rect>'
              f'<circle cx="516" cy="{y}" r="5" fill="none" stroke="{c["accent"]}" stroke-width="2"/>'
              f'<line x1="516" y1="{y + 5}" x2="516" y2="{y + 16}" stroke="{c["accent"]}" stroke-width="2" opacity=".5"/>'
              f'<text x="532" y="{y + 5}" font-size="14" font-family="{MONO}" fill="{c["text"]}">{name}</text>'
              f'<text x="770" y="{y + 5}" text-anchor="end" font-size="12" font-family="{MONO}" fill="{c["muted2"]}">state.json</text></g>\n')
    # arrows between the boxes
    for x1, x2 in ((388, 470), (810, 892)):
        s += (f'<line x1="{x1 + 8}" y1="270" x2="{x2 - 8}" y2="270" stroke="{c["line"]}" stroke-opacity="{float(c["line_o"]) * 2:.2f}" '
              f'stroke-width="1.5" stroke-dasharray="4 6"><animate attributeName="stroke-dashoffset" values="0;-20" dur="1.4s" repeatCount="indefinite"/></line>\n')

    def travel(path, k0, k1, body, kp='0;0;1;1'):
        return (f'<g opacity="0"><animateMotion dur="{D}s" repeatCount="indefinite" keyPoints="{kp}" keyTimes="0;{k0};{k1};1" '
                f'calcMode="linear" path="{path}"/><animate attributeName="opacity" values="0;0;1;1;0;0" '
                f'keyTimes="0;{k0};{k0 + .005:.3f};{k1};{k1 + .005:.3f};1" dur="{D}s" repeatCount="indefinite"/>{body}</g>\n')

    dot = f'<circle r="6" fill="{c["accent"]}"/><circle r="11" fill="{c["accent"]}" opacity=".25"/>'
    # 1. Anna's state goes up, 2. Ben's watcher fetches it
    s += travel('M363 140 L516 130', .04, .14, dot)
    s += travel('M786 130 L937 140', .16, .26, dot)
    # Ben's state goes up and to Anna too
    s += travel('M937 220 L786 210', .24, .32, dot)
    s += travel('M516 210 L363 220', .34, .42, dot)
    # 3. the overlap: Ben's session learns that Anna is in shop
    s += (f'<g opacity="0"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;.27;.29;.5;.52;1" dur="{D}s" repeatCount="indefinite"/>'
          f'<rect x="917" y="168" width="200" height="26" rx="13" fill="{c["amber"]}"/>'
          f'<text x="1017" y="186" text-anchor="middle" font-size="12.5" font-weight="700" fill="{c["on_amber"]}">{esc(t["overlap"])}</text></g>\n')
    # 4. the message: Anna's Claude asks, Ben's waiting session wakes up
    env = (f'<rect x="-82" y="-15" width="164" height="30" rx="15" fill="{c["accent"]}"/>'
           f'<text y="5" text-anchor="middle" font-size="12.5" font-weight="700" fill="{c["bg"]}">{esc(t["mail"])}</text>')
    s += travel('M218 112 L640 100 L1062 112', .55, .78, env)
    # captions
    for i, (x, key) in enumerate(((48, 'c1'), (470, 'c2'), (892, 'c3'))):
        s += (f'<circle cx="{x + 14}" cy="362" r="14" fill="{c["accent"]}"/><text x="{x + 14}" y="367" text-anchor="middle" '
              f'font-size="14" font-weight="800" fill="{c["bg"]}">{i + 1}</text>')
        words, lines, cur = t[key].split(), [], ''
        for wd in words:  # wrap at about 40 characters
            if len(cur) + len(wd) > 40:
                lines.append(cur)
                cur = wd
            else:
                cur = f'{cur} {wd}'.strip()
        lines.append(cur)
        for j, ln in enumerate(lines):
            s += f'<text x="{x + 40}" y="{367 + j * 22}" font-size="15" fill="{c["text"] if j == 0 else c["muted"]}">{esc(ln)}</text>'
        s += '\n'
    s += frame_end(c, w, h)
    return s


for theme in THEMES:
    for lang in TEXT:
        (OUT / f'hero-{lang}-{theme}.svg').write_text(hero(theme, lang), encoding='utf-8')
        (OUT / f'how-{lang}-{theme}.svg').write_text(how(theme, lang), encoding='utf-8')
print('ok')
