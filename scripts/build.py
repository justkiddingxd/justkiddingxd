#!/usr/bin/env python3
"""Draws the profile's images in the style of rin.ms: assets/header.svg, assets/projects/*.svg, assets/activity.svg.

Text is turned into outlines (Onest + JetBrains Mono), so GitHub shows it exactly like the site.
    pip install fonttools
    FONTS=/path/with/Onest.ttf+JBMono.ttf python scripts/build.py          # everything
    python scripts/build.py activity                                         # only the commit tile (what the action reruns)
"""
import datetime, json, os, sys, urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

# ── edit me ──────────────────────────────────────────────
USER = 'justkiddingxd'
TZ = ZoneInfo('Europe/Moscow')
PROJECTS = [
    # file, name, label (top left), description, footer (bottom left)
    ('gridstudio', 'gridstudio', 'with linsisss · react',
     'a site for customizing dota 2: hero grids drawn with symbols, main menu backgrounds and fonts, plus a workshop to share them', 'gridstudio.me'),
    ('embedcat', 'embed.cat', 'next.js · react',
     'discord embed & components v2 builder', 'embed.cat'),
    ('gramhistory', 'gramhistory', 'python · sqlite',
     'historical gram / ton prices: a fast api, full sqlite snapshots and an inline telegram bot', 'gram.rin.ms'),
    ('dota-loadout', 'dota-loadout', 'three.js · webgl',
     "every dota 2 hero live in the browser, with the game's own shader, animations and particles", 'loadout.nyan.cafe'),
]
# ─────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
FONTS = Path(os.environ.get('FONTS', ROOT / '.fonts'))
INK, SOFT, DIM, CAT, ACC = '#ececf1', '#a5a5b0', '#6c6c78', '#5865f2', '#8e96ff'
CARD, CARD2, R = '#121215', '#1b1b20', 16

CAT_SVG = ('<path d="M26 43 L22.5 22 Q22 19 25 19.6 L43 29.5 Q50 26.5 57 29.5 L75 19.6 Q78 19 77.5 22 L74 43 Q80 51 79.5 58 Q79 78 50 79 Q21 78 20.5 58 Q20 51 26 43 Z" fill="none" stroke="#5865f2" stroke-width="4.6" stroke-linejoin="round"/>'
           '<rect x="35.4" y="53" width="4.6" height="7.4" rx="2.3" fill="#5865f2"/><rect x="60" y="53" width="4.6" height="7.4" rx="2.3" fill="#5865f2"/>'
           '<path d="M46.6 63 H53.4 L50 67 Z" fill="#5865f2" stroke="#5865f2" stroke-width="2.4" stroke-linejoin="round"/>')
TG_ICON = 'M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z'
SPARK = 'M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594z'
ARROW = '<path d="M7 7h10v10"/><path d="M7 17 17 7"/>'

# ── text as outlines ──
_fonts, _kerns = {}, {}

def _font(name, wght):
    if (name, wght) not in _fonts:
        _fonts[(name, wght)] = instantiateVariableFont(TTFont(FONTS / f'{name}.ttf'), {'wght': wght})
    return _fonts[(name, wght)]

def _kern(f):
    pairs = {}
    if 'GPOS' not in f:
        return pairs
    for lk in f['GPOS'].table.LookupList.Lookup:
        subs = [s.ExtSubTable for s in lk.SubTable] if lk.LookupType == 9 else lk.SubTable
        for st in subs:
            if getattr(st, 'LookupType', lk.LookupType) != 2 or not hasattr(st, 'Coverage'):
                continue
            x = lambda v: getattr(v, 'XAdvance', 0) if v else 0
            if st.Format == 1:
                for i, g1 in enumerate(st.Coverage.glyphs):
                    for pv in st.PairSet[i].PairValueRecord:
                        if x(pv.Value1): pairs.setdefault((g1, pv.SecondGlyph), x(pv.Value1))
            elif st.Format == 2:
                c1, c2 = st.ClassDef1.classDefs, st.ClassDef2.classDefs
                for g1 in st.Coverage.glyphs:
                    row = st.Class1Record[c1.get(g1, 0)].Class2Record
                    for g2, k2 in c2.items():
                        if x(row[k2].Value1): pairs.setdefault((g1, g2), x(row[k2].Value1))
    return pairs

def measure(s, size, name='Onest', wght=400, tracking=0.0):
    return _layout(s, size, name, wght, tracking)[1]

def _layout(s, size, name, wght, tracking):
    f = _font(name, wght)
    if (name, wght) not in _kerns:
        _kerns[(name, wght)] = _kern(f)
    kern, cmap, gs, upm = _kerns[(name, wght)], f.getBestCmap(), f.getGlyphSet(), f['head'].unitsPerEm
    names = [cmap.get(ord(c), '.notdef') for c in s]
    adv = [gs[g].width + (kern.get((g, names[i + 1]), 0) if i + 1 < len(names) else 0) + tracking * upm for i, g in enumerate(names)]
    width = (sum(adv[:-1]) + gs[names[-1]].width) * size / upm if names else 0
    return names, width, adv, gs, size / upm

def text(s, x, y, size, name='Onest', wght=400, fill=INK, tracking=0.0, anchor='start'):
    names, width, adv, gs, k = _layout(s, size, name, wght, tracking)
    x -= width if anchor == 'end' else width / 2 if anchor == 'middle' else 0
    pen, cx = SVGPathPen(gs), 0
    for g, a in zip(names, adv):
        gs[g].draw(TransformPen(pen, (k, 0, 0, -k, x + cx * k, y)))
        cx += a
    return f'<path fill="{fill}" d="{pen.getCommands()}"/>'

def wrap(s, size, maxw, **kw):
    lines, cur = [], ''
    for word in s.split():
        nxt = (cur + ' ' + word).strip()
        if cur and measure(nxt, size, **kw) > maxw:
            lines.append(cur)
            cur = word
        else:
            cur = nxt
    return lines + [cur] if cur else lines

def svg(w, h, title, body):
    esc = title.replace('&', '&amp;').replace('<', '&lt;')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">'
            f'<title>{esc}</title>{body}</svg>')

def tile(x, y, w, h, fill=CARD):
    return f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{R}" fill="{fill}"/>'

def arrow(x, y, color, s=0.84):
    return f'<g transform="translate({x:g} {y:g}) scale({s})" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{ARROW}</g>'

# ── header: the top row of rin.ms ──
def header():
    W, H, G = 1200, 316, 12
    col = (W - 3 * G) / 4
    hw = col * 2 + G
    o = [tile(0, 0, hw, H)]
    o.append(text("hi, i'm", 30, 50, 17, fill=DIM))
    o.append(text('first time here? hi :3', hw - 28, 48, 13, fill=DIM, anchor='end'))
    o.append(f'<g transform="translate({hw - 28 - measure("first time here? hi :3", 13) - 18:.1f} 37) scale(.5)"><path fill="{ACC}" d="{SPARK}"/></g>')
    o.append(text('Leon', 24, 150, 108, wght=800, tracking=-0.045))
    w1 = measure('aka ', 19)
    w2 = measure('dissonance', 19, wght=600)
    o += [text('aka ', 30, 206, 19, fill=SOFT), text('dissonance', 30 + w1, 206, 19, wght=600, fill=ACC),
          text(' on the internet', 30 + w1 + w2, 206, 19, fill=SOFT), text('and i barely do anything cool', 30, 238, 19)]
    o.append(text('rin.ms', 30, H - 30, 13, name='JBMono', fill=DIM))
    cx = hw + G
    o.append(tile(cx, 0, col, H))
    s = col * 0.72 / 100
    o.append(f'<g transform="translate({cx + col / 2 - 50 * s:.1f} {H / 2 - 54 * s:.1f}) scale({s:.3f})">{CAT_SVG}</g>')
    o.append(text('pat me at rin.ms', cx + col / 2, H - 30, 13, name='JBMono', fill=DIM, anchor='middle'))
    tx, th = cx + col + G, 140
    o.append(tile(tx, 0, col, th, CAT))
    o.append(f'<g transform="translate({tx + 20:g} 20) scale(1.1667)"><path fill="#fff" d="{TG_ICON}"/></g>')
    o.append(arrow(tx + col - 42, 20, '#fff', 0.92))
    o += [text('hit me up', tx + 20, th - 42, 23, wght=700, fill='#fff', tracking=-0.02), text('@dissonance', tx + 20, th - 20, 15, fill='#c7cbff')]
    ay = th + G
    o.append(tile(tx, ay, col, H - ay))
    o += [text('about', tx + 20, ay + 32, 12, wght=500, fill=DIM), text("maybe someday i'll", tx + 20, ay + 66, 16, fill=SOFT),
          text('fill this in.', tx + 20, ay + 88, 16, fill=SOFT), text('but for now: idk + idc', tx + 20, ay + 120, 16, fill=SOFT)]
    return svg(W, H, "hi, i'm Leon, aka dissonance on the internet, and i barely do anything cool", ''.join(o))

# ── project cards (two per row in the README) ──
def project(name, label, desc, foot):
    W, H, P = 592, 214, 28
    o = [tile(0, 0, W, H)]
    o.append(text(label, P, 42, 12, name='JBMono', fill=DIM))
    o.append(arrow(W - P - 18, 26, DIM))
    o.append(text(name, P - 1, 100, 34, wght=700, tracking=-0.03))
    for i, line in enumerate(wrap(desc, 16, W - 2 * P)[:2]):
        o.append(text(line, P, 134 + i * 23, 16, fill=SOFT))
    o.append(text(foot, P, H - 26, 12, name='JBMono', fill=ACC))
    return svg(W, H, f'{name}: {desc}', ''.join(o))

# ── commit tile: last push, a year of contributions ──
def fetch(url):
    req = urllib.request.Request(url, headers={'user-agent': f'{USER}-profile'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def ago(ts):
    then = datetime.datetime.fromisoformat(ts.replace('Z', '+00:00')).astimezone(TZ).date()
    days = (datetime.datetime.now(TZ).date() - then).days
    return 'today' if days <= 0 else 'yesterday' if days == 1 else f'{days} days ago' if days < 7 else then.strftime('%b %-d').lower()

def activity():
    heat = fetch(f'https://github-contributions-api.jogruber.de/v4/{USER}?y=last')
    last = fetch('https://rin.ms/api/gh')  # the site's own feed: github events + repo pushes + PRs
    W, H, P = 1200, 214, 28
    o = [tile(0, 0, W, H)]
    o.append(text('github', P, 40, 12, wght=500, fill=DIM))
    o.append(arrow(W - P - 14, 27, DIM, 0.6))
    o.append(text('@' + USER, W - P - 18, 40, 12, fill=DIM, anchor='end'))
    if last.get('t'):
        o.append(text(ago(last['t']), P, 112, 30, wght=700, tracking=-0.03))
        repo = last['repo'].split('/', 1)[1] if last['repo'].startswith(USER + '/') else last['repo']
        verb = last.get('verb', 'pushed to') + ' '
        wv = measure(verb, 13)
        o += [text(verb, P, 142, 13, fill=SOFT), text(repo, P + wv, 142, 13, wght=600)]
        if last.get('ref'):
            rx = P + wv + measure(repo, 13, wght=600) + 6
            rw = measure(last['ref'], 11, name='JBMono') + 12
            o.append(f'<rect x="{rx:.1f}" y="129" width="{rw:.1f}" height="18" rx="6" fill="{CARD2}"/>')
            o.append(text(last['ref'], rx + 6, 142, 11, name='JBMono', fill=DIM))
    total = (heat.get('total') or {}).get('lastYear')
    if total is not None:
        n = f'{total:,}'
        o += [text(n, P, H - 30, 12, wght=700), text(' contributions in the last year', P + measure(n, 12, wght=700), H - 30, 12, fill=DIM)]

    # same grid as github and the site: weeks top to bottom from sunday, the last column is this week
    days = {d['date']: d for d in heat['contributions']}
    today = min(datetime.date.fromisoformat(max(days)), datetime.datetime.now(TZ).date())
    cols, gap, x0, x1, y0 = 53, 3, 300, W - P, 78
    cell = ((x1 - x0) + gap) / cols - gap
    cell = min(cell, (H - y0 - 26 + gap) / 7 - gap)
    x0 = x1 - cols * (cell + gap) + gap
    start = today - datetime.timedelta(days=(today.weekday() + 1) % 7 + (cols - 1) * 7)
    colors = {1: 'rgba(88,101,242,.38)', 2: 'rgba(88,101,242,.6)', 3: 'rgba(88,101,242,.82)', 4: '#7b85ff'}
    last_month = None
    for i in range(cols * 7):
        d = start + datetime.timedelta(days=i)
        c, r = divmod(i, 7)
        x, y = x0 + c * (cell + gap), y0 + r * (cell + gap)
        if r == 0 and d.month != last_month:
            if last_month is not None and c <= cols - 3:
                o.append(text(d.strftime('%b').lower(), x, y0 - 10, 11, fill=DIM))
            last_month = d.month
        if d > today:
            continue
        lvl = (days.get(d.isoformat()) or {}).get('level', 0)
        o.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell:.1f}" height="{cell:.1f}" rx="2.5" fill="{colors.get(lvl, "#1c1c23")}"/>')
    title = f'github activity: {total} contributions in the last year'
    return svg(W, H, title, ''.join(o))

def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.read_text() if path.exists() else None
    if old != content:
        path.write_text(content)
        print('wrote', path.relative_to(ROOT))

if __name__ == '__main__':
    what = sys.argv[1:] or ['header', 'projects', 'activity']
    if 'header' in what:
        write(ROOT / 'assets/header.svg', header())
    if 'projects' in what:
        for file, name, label, desc, foot in PROJECTS:
            write(ROOT / f'assets/projects/{file}.svg', project(name, label, desc, foot))
    if 'activity' in what:
        write(ROOT / 'assets/activity.svg', activity())
