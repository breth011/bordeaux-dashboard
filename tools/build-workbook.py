# -*- coding: utf-8 -*-
"""Build reports/bordeaux-coverage.xlsx: what is held, and what is not.

    python tools/build-workbook.py
    python tools/build-workbook.py --scores mylist.csv

One row per estate and vintage, so the gaps are as visible as the
figures. The value columns carry the figure itself rather than a yes,
because "28 septembre" is more use than "present".

This lived in a scratch directory until now, which meant the workbook
went stale the moment anything changed and nobody could tell: it was a
day old and two hundred record changes behind when Sjoerd asked. It is
in the repo now and belongs to the yearly run.

Critic ratings and prices come from a list this repo does not hold -
pass it with --scores and those columns fill, leave it out and they are
blank. Everything else is built from data/ and data/sources.json, so it
works on a fresh clone with no sources/ directory at all.

Needs openpyxl.
"""
import io, os, re, sys, json, csv, argparse, collections, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
except ImportError:
    sys.exit('openpyxl is needed: python -m pip install openpyxl')

ap = argparse.ArgumentParser()
ap.add_argument('--scores', help='a CSV of critic ratings, if you have one')
ap.add_argument('--out', default='reports/bordeaux-coverage.xlsx')
a = ap.parse_args()

HEAD = Font(bold=True, color='FFFFFF')
HEADFILL = PatternFill('solid', fgColor='1E3064')
GREY = Font(color='808080')

GRAPE = ['CS', 'ME', 'CF', 'PV', 'CA', 'MA', 'SEM', 'SB', 'SG', 'MU']
FULL = {'CS': 'Cabernet Sauvignon', 'ME': 'Merlot', 'CF': 'Cabernet Franc',
        'PV': 'Petit Verdot', 'CA': 'Carmenere', 'MA': 'Malbec',
        'SEM': 'Semillon', 'SB': 'Sauvignon Blanc', 'SG': 'Sauvignon Gris',
        'MU': 'Muscadelle'}


def js_block(path, var):
    """The literal assigned to a window.X, as text."""
    t = io.open(ROOT + path, encoding='utf-8').read()
    m = re.search(re.escape(var) + r'\s*=\s*', t)
    if not m:
        return ''
    i, depth = m.end(), 0
    open_c = t[i]
    close_c = ']' if open_c == '[' else '}'
    j = i
    while j < len(t):
        if t[j] == open_c:
            depth += 1
        elif t[j] == close_c:
            depth -= 1
            if depth == 0:
                break
        j += 1
    return t[i:j + 1]


# ------------------------------------------------------------ the data
E = sr.estates(ROOT)

records = {}
for line in io.open(ROOT + 'data/fiches.js', encoding='utf-8'):
    m = re.match(r"^'([a-z0-9-]+)\|(\d{4})':\{(.*)\},$", line.rstrip())
    if m:
        records[(m.group(1), int(m.group(2)))] = m.group(3)

# Which years the dashboard shows at all.
vt = js_block('data/vintages.js', 'window.BDX_VINTAGES')
years = sorted(set(int(y) for y in re.findall(r"'(\d{4})'\s*:", vt)))
if not years:
    years = sorted(set(y for e, y in records)) or [2024]

# Appellation and classification, from the estate files.
meta = {}
for f in sr.ESTATE_FILES:
    p = ROOT + 'data/' + f
    if not os.path.exists(p):
        continue
    t = io.open(p, encoding='utf-8').read()
    for m in re.finditer(r"id:'([a-z0-9-]+)'", t):
        win = t[m.end():m.end() + 900]
        nxt = re.search(r"id:'[a-z0-9-]+'", win)
        if nxt:
            win = win[:nxt.start()]
        d = meta.setdefault(m.group(1), {})
        for key in ('appellation', 'commune', 'cls', 'owner', 'second'):
            v = sr.js_strings_after(key + ':', win)
            if v and key not in d:
                d[key] = v[0]
        g = re.search(r'growth:(\d+)', win)
        ha = re.search(r'ha:([\d.]+)', win)
        if g:
            d.setdefault('growth', int(g.group(1)))
        if ha:
            d.setdefault('ha', float(ha.group(1)))

# The estate's usual blend, for comparison with each vintage's.
usual = {}
for f in sr.ESTATE_FILES:
    p = ROOT + 'data/' + f
    if not os.path.exists(p):
        continue
    t = io.open(p, encoding='utf-8').read()
    for m in re.finditer(r"id:'([a-z0-9-]+)'(.{0,900}?)blend:\{([^}]*)\}",
                         t, re.S):
        d = dict((k, float(v)) for k, v in
                 re.findall(r'(\w+):([\d.]+)', m.group(3)))
        if d:
            usual.setdefault(m.group(1), d)

# How many documents the manifest holds per estate, so it is clear where
# more could still be read out of what is already on disk.
man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))
docs = collections.Counter()
readable = collections.Counter()
for s in man['sheets']:
    if s.get('estate'):
        docs[s['estate']] += 1
        if s.get('role') in ('grand', 'unknown', 'combined'):
            readable[s['estate']] += 1

scores = {}
if a.scores:
    CRITICS = ('RP', 'NM', 'JR', 'TA', 'BD', 'WS', 'JL', 'De', 'RVF', 'JA',
               'LeP', 'PW', 'RG', 'CK')
    with io.open(a.scores, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            nm = sr.packed(r.get('wine') or '')
            yr = (r.get('year') or '').strip()
            if not (nm and yr.isdigit()):
                continue
            got = [(c, r[c]) for c in CRITICS if r.get(c)]
            if got:
                scores[(nm, int(yr))] = got

NOT_MADE = set()
nm_block = js_block('data/overrides.js', 'window.BDX_NOT_PRODUCED')
for m in re.finditer(r"'([a-z0-9-]+)'\s*:\s*\[([^\]]*)\]", nm_block):
    for y in re.findall(r'\d{4}', m.group(2)):
        NOT_MADE.add((m.group(1), int(y)))


def field(body, key):
    m = re.search(key + r":'((?:[^'\\]|\\.)*)'", body or '')
    if m:
        return re.sub(r'\\(.)', r'\1', m.group(1))
    m = re.search(key + r':([\d.]+)', body or '')
    return m.group(1) if m else ''


def blend_of(body):
    m = re.search(r'blend:\{([^}]*)\}', body or '')
    if not m:
        return None
    return dict((k, float(v)) for k, v in
                re.findall(r'(\w+):([\d.]+)', m.group(1)))


def blendstr(d):
    if not d:
        return ''
    return ', '.join('%s %g%%' % (FULL.get(k, k), d[k])
                     for k in GRAPE if k in d)


wb = Workbook()

# ------------------------------------------------- sheet 1: by wine
ws = wb.active
ws.title = 'Detail by wine'
cols = [('Estate', 26), ('Estate id', 20), ('Appellation', 17),
        ('Classification', 15), ('Type', 7), ('Vintage', 8),
        ('Grand vin made', 13), ('Critic ratings', 26),
        ('Any record', 11), ('Blend', 34), ('Blend sums to', 12),
        ('Estate typical blend', 30), ('Season note', 11),
        ('Tasting note', 12), ('Harvest date', 16), ('Yield hl/ha', 11),
        ('Alcohol', 9), ('Months in barrel', 15), ('pH', 7),
        ('Drink window', 13), ('Source document', 46)]
for i, (h, w) in enumerate(cols, 1):
    c = ws.cell(row=1, column=i, value=h)
    c.font, c.fill = HEAD, HEADFILL
    c.alignment = Alignment(vertical='center', wrap_text=True)
    ws.column_dimensions[get_column_letter(i)].width = w
ws.freeze_panes = 'A2'

CLS = {'1855': '1855 Médoc', 'sauternes': '1855 Sauternes',
       'graves': 'Graves 1959', 'stem': 'Saint-Émilion',
       'pomerol': 'Pomerol', 'bourgeois': 'Cru Bourgeois',
       'artisan': 'Cru Artisan'}

r = 2
for eid in sorted(E, key=lambda k: (E[k].get('name') or k)):
    e, md = E[eid], meta.get(eid, {})
    cls = md.get('cls') or ('sauternes' if e.get('cat') == 'sweet'
                            else ('bourgeois' if eid.startswith('bourgeois-')
                                  else ('artisan' if eid.startswith('artisan-')
                                        else ('stem' if eid.startswith('stem-')
                                              else ('pomerol' if eid.startswith('pomerol-')
                                                    else '1855')))))
    for y in years:
        body = records.get((eid, y))
        b = blend_of(body)
        sc = scores.get((sr.packed(e.get('name') or ''), y)) or []
        ws.append([
            e.get('name') or eid, eid, md.get('appellation', ''),
            CLS.get(cls, cls), e.get('cat') or '', y,
            '' if (eid, y) in NOT_MADE else 'yes',
            ', '.join('%s %s' % g for g in sc),
            'yes' if body else '',
            blendstr(b), (round(sum(b.values()), 1) if b else ''),
            blendstr(usual.get(eid)),
            'yes' if field(body, 'note') else '',
            'yes' if field(body, 'taste') else '',
            field(body, 'harvest'), field(body, 'yld'), field(body, 'alc'),
            field(body, 'months'), field(body, 'ph'),
            field(body, 'window') and 'yes' or '',
            field(body, 'src'),
        ])
        r += 1

# -------------------------------------------- sheet 2: by estate
ws2 = wb.create_sheet('Summary by estate')
cols2 = [('Estate', 26), ('Estate id', 20), ('Appellation', 17),
         ('Classification', 15), ('Records', 9), ('With a blend', 12),
         ('Earliest', 9), ('Latest', 8), ('Documents held', 14),
         ('Still unread', 12), ('Typical blend', 30)]
for i, (h, w) in enumerate(cols2, 1):
    c = ws2.cell(row=1, column=i, value=h)
    c.font, c.fill = HEAD, HEADFILL
    c.alignment = Alignment(vertical='center', wrap_text=True)
    ws2.column_dimensions[get_column_letter(i)].width = w
ws2.freeze_panes = 'A2'
for eid in sorted(E, key=lambda k: (E[k].get('name') or k)):
    mine = [(y, body) for (x, y), body in records.items() if x == eid]
    md = meta.get(eid, {})
    ws2.append([
        E[eid].get('name') or eid, eid, md.get('appellation', ''),
        CLS.get(md.get('cls', ''), md.get('cls', '')),
        len(mine), sum(1 for y, b in mine if blend_of(b)),
        min([y for y, b in mine]) if mine else '',
        max([y for y, b in mine]) if mine else '',
        docs.get(eid, 0), readable.get(eid, 0),
        blendstr(usual.get(eid)),
    ])

# ------------------------------------------- sheet 3: by field
ws3 = wb.create_sheet('Coverage by field')
for i, (h, w) in enumerate([('Field', 22), ('Records with it', 16),
                            ('Share of records', 16)], 1):
    c = ws3.cell(row=1, column=i, value=h)
    c.font, c.fill = HEAD, HEADFILL
    ws3.column_dimensions[get_column_letter(i)].width = w
n = len(records) or 1
# Top-level keys only. Matching any lowercase word before a colon also
# counts what is inside the strings - a url:'https://...' contributed a
# field called https, and the sheet listed eighty-six of them.
KEY = re.compile(r"(?:^|,)([a-z]+):")
counts = collections.Counter()
for body in records.values():
    for f in set(KEY.findall(body)):
        counts[f] += 1
NAMES = {'blend': 'Blend', 'note': 'Season note', 'taste': 'Tasting note',
         'harvest': 'Harvest date', 'yld': 'Yield', 'alc': 'Alcohol',
         'months': 'Months in barrel', 'ph': 'pH', 'temp': 'Serving temp',
         'decant': 'Decant advice', 'window': 'Drink window',
         'press': 'Press scores', 'pick': 'Picking dates', 'src': 'Source',
         'oak': 'New oak %', 'url': 'Source URL', 'via': 'Via the trade',
         'wy': 'Drink window years', 'food': 'Food pairing',
         'xsrc': 'A second source',
         # The flags that say a Dutch translation of that field exists.
         'ntl': 'Season note, translated',
         'ttl': 'Tasting note, translated',
         'wtl': 'Drink window, translated',
         'dtl': 'Decant advice, translated',
         'ftl': 'Food pairing, translated'}
for f, c in counts.most_common():
    ws3.append([NAMES.get(f, f), c, round(100.0 * c / n, 1)])

# ------------------------------------- sheet 4: blends to look at
ws4 = wb.create_sheet('Blends to check')
for i, (h, w) in enumerate([('Estate', 26), ('Vintage', 8), ('Blend', 32),
                            ('Sums to', 9), ('Typical', 30),
                            ('Why it is here', 44), ('Source', 40)], 1):
    c = ws4.cell(row=1, column=i, value=h)
    c.font, c.fill = HEAD, HEADFILL
    c.alignment = Alignment(vertical='center', wrap_text=True)
    ws4.column_dimensions[get_column_letter(i)].width = w
ws4.freeze_panes = 'A2'


def lead(d):
    return max(d.items(), key=lambda kv: kv[1])[0] if d else None


flagged = 0
for (eid, y), body in sorted(records.items()):
    b = blend_of(body)
    if not b:
        continue
    why = []
    if abs(sum(b.values()) - 100) > 1.5:
        why.append('does not sum to 100')
    if len(b) == 1:
        why.append('a single variety')
    u = usual.get(eid)
    if u and lead(u) and lead(b) and lead(u) != lead(b) and u[lead(u)] >= 58:
        why.append('leads on %s where the estate leads on %s'
                   % (FULL.get(lead(b)), FULL.get(lead(u))))
    if not why:
        continue
    flagged += 1
    ws4.append([E.get(eid, {}).get('name') or eid, y, blendstr(b),
                round(sum(b.values()), 1), blendstr(u), '; '.join(why),
                field(body, 'src')])

# ------------------------------------------------ sheet 5: read me
ws5 = wb.create_sheet('Read me')
ws5.column_dimensions['A'].width = 110
for line in [
    'Bordeaux Dashboard - coverage workbook',
    'Built %s by tools/build-workbook.py' % datetime.date.today().isoformat(),
    '',
    '%d estates x %d vintages. %d records, %d of them with a blend.'
    % (len(E), len(years), len(records),
       sum(1 for b in records.values() if blend_of(b))),
    '%d documents in data/sources.json are attributed to an estate; %d of '
    'those are the grand vin’s or not yet identified, and so might '
    'still be read.' % (sum(docs.values()), sum(readable.values())),
    '',
    'Detail by wine - one row per estate and vintage, so the gaps show. A '
    'value column carries the figure, not a yes.',
    'Summary by estate - how much is held per estate, and how many '
    'documents remain unread.',
    'Coverage by field - how often each field is filled.',
    'Blends to check - %d blends that do not sum, stand on one variety, or '
    'lead on a variety the estate does not. Each needs its sheet read; '
    'tools/check-data.py is the same questions with the exceptions '
    'recorded.' % flagged,
    '',
    'Critic ratings come from a list this repo does not hold. Pass it with '
    '--scores to fill that column.',
    'Everything else is built from data/ and data/sources.json, so this '
    'runs on a fresh clone with no sources/ directory.',
]:
    ws5.append([line])
for row in ws5.iter_rows():
    row[0].alignment = Alignment(wrap_text=True, vertical='top')
ws5['A1'].font = Font(bold=True, size=14)
ws5['A2'].font = GREY

out = ROOT + a.out
if not os.path.isdir(os.path.dirname(out)):
    os.makedirs(os.path.dirname(out))
wb.save(out)
print('%s' % a.out)
print('   %d estates x %d vintages = %d rows on Detail by wine'
      % (len(E), len(years), len(E) * len(years)))
print('   %d records, %d with a blend' % (len(records),
      sum(1 for b in records.values() if blend_of(b))))
print('   %d blends on Blends to check' % flagged)
if not a.scores:
    print('   critic ratings left blank; pass --scores <csv> to fill them')
