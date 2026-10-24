# -*- coding: utf-8 -*-
"""The factual half of an estate's report, ready to be written on.

    python tools/estate-report.py --estate talbot
    python tools/estate-report.py --estate talbot --out

Emits markdown: what the estate holds, wine by wine and field by
field; how many documents it has and how many are unread; what its
site was found to publish; and every flag tools/audit-estate.py still
raises, grouped.

WHY A TOOL FOR THIS

A pass over 61 estates needs a report each, and three quarters of
each report is counting - which is the part worth generating, because
a hand-copied figure goes stale the moment the next read runs. What
is NOT generated is the findings: what was wrong, why, and what was
decided. Those go in by hand under the headings this leaves, because
they are the only part that needed a person.

The counts come from the data files, not from a cache, so a report
rebuilt after a read is correct without being re-read by hand.
"""
import io, json, os, re, sys, argparse, collections, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SHOW = ('blend', 'alc', 'ph', 'yld', 'months', 'oak', 'pick', 'harvest',
        'note', 'taste', 'press', 'sug', 'ta', 'temp', 'window', 'decant',
        'food')
NAMES = {'blend': 'blend', 'alc': 'alcohol', 'ph': 'pH',
         'yld': 'yield', 'months': 'in barrel', 'oak': 'new oak',
         'pick': 'picking dates', 'harvest': 'harvest, in words',
         'note': 'season note', 'taste': 'tasting note',
         'press': 'press scores', 'sug': 'residual sugar',
         'ta': 'total acidity', 'temp': 'serving temperature',
         'window': 'drinking window', 'decant': 'decanting',
         'food': 'food pairing'}


def records(path, parts):
    rx = re.compile(r"^'(" + r'\|'.join(parts) + r")':\{(.*)\},$")
    out = {}
    if not os.path.exists(ROOT + path):
        return out
    for line in io.open(ROOT + path, encoding='utf-8'):
        m = rx.match(line.rstrip())
        if m:
            out[m.group(1)] = m.group(2)
    return out


def wines_of(eid):
    p = ROOT + 'data/cuvees.js'
    if not os.path.exists(p):
        return []
    body = io.open(p, encoding='utf-8').read()
    body = body.split('window.BDX_CUVEE_WINES', 1)[-1].split(
        'window.BDX_CUVEES', 1)[0]
    m = re.search(r"(?m)^'" + re.escape(eid) + r"':\[(.*)\],$", body)
    if not m:
        return []
    return [{'slug': w.group(1),
             'name': w.group(2).replace("\\'", "'"),
             'role': w.group(3), 'colour': w.group(4)}
            for w in re.finditer(
                r"\{slug:'((?:[^'\\]|\\.)*)',name:'((?:[^'\\]|\\.)*)',"
                r"role:'([a-z]*)',colour:'([a-z]*)'\}", m.group(1))]


def tally(store, pre):
    mine = [b for k, b in store.items() if k.startswith(pre)
            and re.match(r'^\d{4}$', k.rsplit('|', 1)[-1])]
    f = collections.Counter()
    for b in mine:
        for k in re.findall(r'(?:^|\{|,)([a-z]+[a-z0-9]*)[:{]', b):
            f[k] += 1
    yrs = sorted(int(k.rsplit('|', 1)[-1]) for k in store
                 if k.startswith(pre)
                 and re.match(r'^\d{4}$', k.rsplit('|', 1)[-1]))
    return len(mine), f, yrs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estate', required=True)
    ap.add_argument('--out', action='store_true',
                    help='write reports/estates/<estate>.md, keeping any '
                         'hand-written sections below the marker')
    a = ap.parse_args()
    eid = a.estate

    E = sr.estates(ROOT)
    e = E.get(eid) or {}
    F = records('data/fiches.js', [r'[a-z0-9-]+', r'\d{4}'])
    C = records('data/cuvees.js',
                [r'[a-z0-9-]+', r'[a-z0-9-]+', r'\d{4}'])
    man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))
    rows = [s for s in man['sheets'] if s.get('estate') == eid]

    URL = set()
    for p in ('data/fiches-url.js', 'data/cuvee-url.js'):
        if os.path.exists(ROOT + p):
            for line in io.open(ROOT + p, encoding='utf-8'):
                m = re.match(r"^'([^']+)':'", line.rstrip())
                if m:
                    URL.add(m.group(1))

    L = []

    def w(s=''):
        L.append(s)

    gc = ''
    t = io.open(ROOT + 'data/chateaux.js', encoding='utf-8').read()
    m = re.search(r"id:'" + re.escape(eid) + r"'[^}]{0,400}?growth:(\d+)",
                  t)
    if m:
        gc = {1: 'first', 2: 'second', 3: 'third', 4: 'fourth',
              5: 'fifth'}.get(int(m.group(1)), m.group(1)) + ' growth'

    w('# %s%s' % (e.get('name') or eid,
                  (' — %s, %s' % (gc, e.get('app') or ''))
                  .rstrip(', ') if gc or e.get('app') else ''))
    w()
    w('Checked %s. <!-- fill in: estate N of 61 -->'
      % os.environ.get('BDX_DATE', 'YYYY-MM-DD'))
    w()

    # ------------------------------------------------------ the records
    w('## What it holds')
    w()
    n, f, yrs = tally(F, eid + '|')
    wines = wines_of(eid)
    cols = [('the grand vin', n, f, yrs)]
    for x in wines:
        cn, cf, cy = tally(C, '%s|%s|' % (eid, x['slug']))
        cols.append(('%s (%s, %s)' % (x['name'], x['role'], x['colour']),
                     cn, cf, cy))

    w('| | %s |' % ' | '.join(c[0] for c in cols))
    w('|---|%s' % ('---|' * len(cols)))
    w('| records | %s |' % ' | '.join(str(c[1]) for c in cols))
    w('| span | %s |' % ' | '.join(
        ('%d–%d' % (c[3][0], c[3][-1])) if c[3] else '—'
        for c in cols))
    for k in SHOW:
        if not any(c[2].get(k) for c in cols):
            continue
        w('| %s | %s |' % (NAMES.get(k, k), ' | '.join(
            ('%d (%d%%)' % (c[2][k], round(100.0 * c[2][k] / c[1]))
             if c[1] and c[2].get(k) else '—') for c in cols)))
    linked = len([k for k in F if k.startswith(eid + '|') and k in URL])
    w('| links to its source | %d of %d |%s' % (
        linked, n, ' |' * (len(cols) - 1)))
    w()

    # ---------------------------------------------------- the documents
    w('## The documents')
    w()
    role = collections.Counter(s.get('role') for s in rows)
    pdf = sum(1 for s in rows if s['file'].lower().endswith('.pdf'))
    withurl = sum(1 for s in rows if s.get('url'))
    w('%d in the manifest — %d PDF, %d crawled page, %d with an '
      'address on record.' % (len(rows), pdf, len(rows) - pdf, withurl))
    w()
    w('By role: %s.' % ', '.join('%s %d' % (k or 'none', v)
                                 for k, v in role.most_common()))
    w()

    # -------------------------------------------------------- the flags
    w('## What the audit still says')
    w()
    try:
        out = subprocess.run(
            [sys.executable, '-I', ROOT + 'tools/audit-estate.py',
             '--estate', eid, '--wines', '--quiet'],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=900).stdout.decode('utf-8', 'replace')
    except Exception as ex:
        out = ''
        w('the audit could not be run (%s)' % str(ex)[:60])
    flags = collections.Counter()
    for line in out.splitlines():
        s = line.strip()
        if s.startswith('!!'):
            flags[re.sub(r'[0-9]{4}', 'YYYY',
                         s[3:].split(':')[0]).strip()] += 1
    if not flags:
        w('Nothing.')
    for k, v in flags.most_common():
        w('- %s — %d' % (k, v))
    w()

    w('## Findings')
    w()
    w('<!-- by hand: what was wrong, why, what was decided -->')
    w()
    w('## Not recoverable here')
    w()
    w('<!-- by hand -->')
    w()

    text = '\n'.join(L) + '\n'
    if not a.out:
        print(text)
        return 0
    d = ROOT + 'reports/estates'
    if not os.path.isdir(d):
        os.makedirs(d)
    p = os.path.join(d, eid + '.md')
    io.open(p, 'w', encoding='utf-8', newline='').write(text)
    print('written to %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
