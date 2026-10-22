# -*- coding: utf-8 -*-
"""Coverage, datapoint by datapoint: what is held, and what is left.

    python tools/progress.py                 report, and save it
    python tools/progress.py --no-save       report only
    python tools/progress.py --estate margaux --estate latour

Saving writes PROGRESS.md - the classified growths table and how the
totals have moved - and appends a row to progress-history.tsv. Both
are tracked, because reports/ is gitignored and a progress table with
no history cannot say whether anything is moving. A run with --estate
saves nothing: the figures are then a part and not the whole.

Three questions, in the order they are worth asking.

WHAT IS HELD. Each datapoint as a share of the records that exist, and
of the grid the dashboard draws - 468 estates by the 44 vintages
data/vintages.js rates. The grid share is a floor and not a score: no
estate made and published all 44 vintages, and the fiche technique
barely existed before the 1990s, which the decade columns show.

WHAT IS STILL GETTABLE. A field a document states and the record does
not hold is work outstanding; a field nothing states is not. The
figure comes from reports/fiches-read.json, so it is as fresh as the
last run of read-fiches.

WHETHER IT CAN BE SHOWN AND CHECKED. A record that names no source
cannot be audited, and one whose source has no address cannot be
linked to from the app - which is a coverage question of its own, and
the reason the url column is here. The Dutch column is the same
question for a bilingual reader.
"""
import argparse
import collections
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, ROOT + 'tools')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import sheetreader as sr

STR = r"((?:[^'\\]|\\.)*)"

# The datapoints, in the order a member would ask for them, with what
# each one is - because "note" says nothing and "the growing season"
# says what it is.
POINTS = (
    ('blend', 'the assemblage, variety by variety'),
    ('taste', 'the tasting note'),
    ('note', 'the growing season'),
    ('alc', 'alcohol'),
    ('ph', 'pH'),
    ('yld', 'yield, hl/ha'),
    ('months', 'months in barrel'),
    ('oak', 'new oak, per cent'),
    ('pick', 'picking dates'),
    ('harvest', 'harvest, as the sheet words it'),
    ('temp', 'serving temperature'),
    ('wy', 'drinking window, as years'),
    ('window', 'drinking window, in words'),
    ('decant', 'decanting'),
    ('food', 'food pairing'),
)
# And the three that are about the record rather than the wine.
META = (
    ('src', 'names the document it was read from'),
    ('url', 'can link to that document in the app'),
    ('nl', 'has Dutch for its prose'),
)


def fields_in(body):
    return set(re.findall(r'(?:^|,)([a-z]+[a-z0-9]*)[:\{]', body))


def load(path):
    out = {}
    for line in io.open(path, encoding='utf-8'):
        m = re.match(r"^'([a-z0-9-]+)\|(\d{4})':\{(.*)\},$", line.rstrip())
        if m:
            out[(m.group(1), int(m.group(2)))] = m.group(3)
    return out


# ----------------------------------------------------------------- #
# Keeping the report.

HISTORY = 'progress-history.tsv'
MARKDOWN = 'PROGRESS.md'
# The fields the history tracks, in the order the columns go.
TRACKED = ('blend', 'taste', 'note', 'alc', 'ph', 'yld', 'months',
           'oak', 'pick', 'harvest', 'temp', 'wy', 'window', 'decant',
           'food')
# How many days of the trend to print. Enough to see a direction
# without the file becoming the report.
TREND = 14


class _tee(object):
    """Write to the terminal and keep a copy.

    The report is three hundred print statements and rewriting them to
    return a string would change every line of this file for no gain.
    """

    def __init__(self, out):
        self.out = out
        self.kept = []

    def write(self, s):
        self.out.write(s)
        self.kept.append(s)
        return len(s)

    def flush(self):
        self.out.flush()

    def __getattr__(self, name):
        return getattr(self.out, name)

    def text(self):
        return ''.join(self.kept)


def _section(text, head, upto=None):
    """One titled block of the report, by the line it starts on."""
    i = text.find(head)
    if i < 0:
        return None
    j = text.find(upto, i + len(head)) if upto else -1
    return text[i:j if j > 0 else len(text)].rstrip() + '\n'


def _counts(text):
    """The per-field record counts, read back out of the table.

    Out of the printed report rather than recomputed, so the number in
    the history is the number that was shown. A second count computed
    a second way is a second thing to be wrong.
    """
    out = {}
    for f in TRACKED:
        m = re.search(r'(?m)^' + f + r'\s+\S.*?([\d,]+)\s+\d+%',
                      text)
        if m:
            out[f] = int(m.group(1).replace(',', ''))
    m = re.search(r'(?m)^([\d,]+) records,', text)
    if m:
        out['records'] = int(m.group(1).replace(',', ''))
    m = re.search(r'(?m)^\s+url\s+.*?([\d,]+)\s+\d+% of records',
                  text)
    if m:
        out['url'] = int(m.group(1).replace(',', ''))
    m = re.search(r'(?m)^\s+nl\s+.*?([\d,]+)\s+\d+% of records',
                  text)
    if m:
        out['nl'] = int(m.group(1).replace(',', ''))
    return out


def _history(row):
    """Append today's figures, replacing an earlier run of the day."""
    path = ROOT + HISTORY
    cols = ('date', 'records', 'url', 'nl') + TRACKED
    rows = []
    if os.path.exists(path):
        for i, line in enumerate(io.open(path, encoding='utf-8')):
            line = line.rstrip('\n')
            if not line or (i == 0 and line.startswith('date')):
                continue
            rows.append(line.split('\t'))
    today = row['date']
    rows = [r for r in rows if r[:1] != [today]]
    rows.append([str(row.get(c, '')) for c in cols])
    rows.sort(key=lambda r: r[0])
    out = ['\t'.join(cols)] + ['\t'.join(r) for r in rows]
    io.open(path, 'w', encoding='utf-8', newline='').write(
        '\n'.join(out) + '\n')
    return cols, rows


def _trend(cols, rows):
    """The last few days of the headline figures, oldest first."""
    show = ('records', 'blend', 'taste', 'note', 'url', 'nl')
    idx = [cols.index(c) for c in show]
    lines = ['   %-12s %s' % ('date', ' '.join('%7s' % c
                                               for c in show))]
    for r in rows[-TREND:]:
        lines.append('   %-12s %s'
                     % (r[0], ' '.join('%7s' % (r[i] if i < len(r)
                                                else '') for i in idx)))
    if len(rows) > 1:
        first, last = rows[0], rows[-1]
        moved = []
        for c, i in zip(show, idx):
            try:
                d = int(last[i]) - int(first[i])
            except (ValueError, IndexError):
                continue
            if d:
                moved.append('%s %+d' % (c, d))
        if moved:
            lines.append('')
            lines.append('   since %s: %s' % (first[0],
                                              ', '.join(moved)))
    return '\n'.join(lines) + '\n'


def save(text):
    """Write PROGRESS.md and add today's row to the history."""
    import datetime
    row = _counts(text)
    row['date'] = datetime.date.today().isoformat()
    cols, rows = _history(row)

    growths = _section(text, 'A ROW EACH, FOR THE CLASSIFIED GROWTHS')
    held = _section(text, 'THE GRID:', 'WHAT IS STILL GETTABLE')
    if held is None:
        held = _section(text, 'THE GRID:', 'THE CLASSIFIED GROWTHS')
    out = ['# Coverage',
           '',
           'Generated by `tools/progress.py`. Do not edit by hand -'
           ' a run overwrites it.',
           '',
           '## How it has moved',
           '',
           'One row per day, from `progress-history.tsv`.',
           '',
           '```',
           _trend(cols, rows).rstrip(),
           '```',
           '']
    if held:
        out += ['## What is held', '', '```', held.rstrip(), '```', '']
    if growths:
        out += ['## A row each, for the classified growths', '',
                '```', growths.rstrip(), '```', '']
    io.open(ROOT + MARKDOWN, 'w', encoding='utf-8',
            newline='').write('\n'.join(out))
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estate', action='append', default=[])
    ap.add_argument('--no-save', action='store_true',
                    help='print the report without writing PROGRESS.md')
    a = ap.parse_args()

    years = sorted(int(m.group(1)) for m in re.finditer(
        r'(?m)^(\d{4}):', io.open(ROOT + 'data/vintages.js',
                                  encoding='utf-8').read()))
    lo, hi = years[0], years[-1]
    E = sr.estates(ROOT)
    recs = load(ROOT + 'data/fiches.js')
    nl = load(ROOT + 'data/fiches-nl.js')
    url = {}
    p = ROOT + 'data/fiches-url.js'
    if os.path.exists(p):
        for line in io.open(p, encoding='utf-8'):
            m = re.match(r"^'([a-z0-9-]+)\|(\d{4})':'", line)
            if m:
                url[(m.group(1), int(m.group(2)))] = True

    if a.estate:
        E = dict((k, v) for k, v in E.items() if k in a.estate)
        recs = dict((k, v) for k, v in recs.items() if k[0] in a.estate)
    cells = len(E) * len(years)

    held = collections.defaultdict(set)
    for (eid, yr), body in recs.items():
        got = fields_in(body)
        for f, _ in POINTS:
            if f in got:
                held[f].add((eid, yr))
        if 'src' in got:
            held['src'].add((eid, yr))
        if (eid, yr) in url:
            held['url'].add((eid, yr))
        prose = [f for f in ('taste', 'note', 'window', 'decant', 'food')
                 if f in got]
        if prose:
            dutch = fields_in(nl.get((eid, yr), ''))
            if all(f in dutch for f in prose):
                held['nl'].add((eid, yr))

    # What a document states and no record holds, from the last read.
    left = collections.Counter()
    rp = ROOT + 'reports/fiches-read.json'
    stale = None
    if os.path.exists(rp):
        try:
            rows = json.load(io.open(rp, encoding='utf-8'))
            rows = rows if isinstance(rows, list) else (
                rows.get('found') or [])
            seen = set()
            for r in rows:
                if a.estate and r['estate'] not in a.estate:
                    continue
                for f in (r.get('new') or []):
                    k = (r['estate'], str(r['year']), f)
                    if k not in seen:
                        seen.add(k)
                        left[f] += 1
            stale = os.path.getmtime(rp)
        except Exception:
            stale = None

    print('THE GRID: %d estates x %d vintages (%d-%d) = %s cells'
          % (len(E), len(years), lo, hi, '{:,}'.format(cells)))
    ongrid = [k for k in recs if lo <= k[1] <= hi]
    print('%s records, %s on the grid, %d older than %d; %d of %d '
          'estates have one'
          % ('{:,}'.format(len(recs)), '{:,}'.format(len(ongrid)),
             len(recs) - len(ongrid), lo,
             len(set(e for e, y in recs)), len(E)))
    print()

    decades = [(1982, 1989), (1990, 1999), (2000, 2009), (2010, 2019),
               (2020, hi)]
    head = ('%-9s %-34s %7s %5s %6s  %s'
            % ('field', 'what it is', 'records', 'of', 'of grid',
               ' '.join('%-5s' % ('%ds' % (x // 10 * 10))
                        for x, y in decades)))
    print(head)
    print('%-9s %-34s %7s %5s %6s' % ('', '', '', 'recs', ''))
    for f, what in POINTS:
        if not held[f]:
            continue
        on = [k for k in held[f] if lo <= k[1] <= hi]
        bits = []
        for x, y in decades:
            cell = len(E) * len([v for v in years if x <= v <= y])
            got = len([k for k in on if x <= k[1] <= y])
            bits.append('%-5s' % ('%.1f%%' % (100.0 * got / cell)
                                  if cell else '-'))
        print('%-9s %-34s %7s %4.0f%% %5.1f%%  %s'
              % (f, what, '{:,}'.format(len(held[f])),
                 100.0 * len(held[f]) / max(len(recs), 1),
                 100.0 * len(on) / max(cells, 1), ' '.join(bits)))

    print()
    print('ABOUT THE RECORD ITSELF:')
    for f, what in META:
        print('   %-6s %-44s %7s %4.0f%% of records'
              % (f, what, '{:,}'.format(len(held[f])),
                 100.0 * len(held[f]) / max(len(recs), 1)))

    if left:
        print()
        print('STILL TO MERGE - a document states it and no record '
              'holds it:')
        for f, n in left.most_common():
            print('   %-9s %4d' % (f, n))
        print('   (from reports/fiches-read.json; re-run '
              'tools/read-fiches.py --prose to refresh)')


    # The classified growths apart from the rest. Every figure above is
    # divided by 468 estates, 270 of which hold nothing, so it
    # understates the state of the wines the dashboard is for.
    CLASSIFIED = set()
    t = io.open(ROOT + 'data/chateaux.js', encoding='utf-8').read()
    for m in re.finditer(r"id:'([a-z0-9-]+)'", t):
        CLASSIFIED.add(m.group(1))
    if CLASSIFIED and not a.estate:
        print()
        print('THE %d CLASSIFIED GROWTHS, APART FROM THE LONG TAIL:'
              % len(CLASSIFIED))
        print('   %-9s %-22s %9s   %9s' % ('field', '', 'classified',
                                           'the rest'))
        for f, what in POINTS[:9]:
            mine = [k for k in held[f] if k[0] in CLASSIFIED]
            rest = [k for k in held[f] if k[0] not in CLASSIFIED]
            cm = len(CLASSIFIED) * len(years)
            cr = (len(E) - len(CLASSIFIED)) * len(years)
            print('   %-9s %-22s %4d %4.0f%%   %4d %4.0f%%'
                  % (f, what[:22], len(mine),
                     100.0 * len(mine) / max(cm, 1),
                     len(rest), 100.0 * len(rest) / max(cr, 1)))
        inboth = len(set(e for e, y in recs) & CLASSIFIED)
        print('   %d of the %d classified growths have at least one '
              'record' % (inboth, len(CLASSIFIED)))

    # How much of the prose is a translation.
    tl = collections.Counter()
    for (eid, yr), body in recs.items():
        for f, flag in (('taste', 'ttl'), ('note', 'ntl')):
            if re.search(r'(?:^|,)' + f + r":'", body):
                tl[(f, bool(re.search(r'(?:^|,)' + flag + r':1\b',
                                      body)))] += 1
    print()
    print('WHOSE WORDS THE PROSE IS:')
    for f in ('taste', 'note'):
        own, mine = tl[(f, False)], tl[(f, True)]
        print('   %-6s %4d the estate’s own English, %4d translated '
              'from its French' % (f, own, mine))

    # Deliberate absences.
    try:
        rf = io.open(ROOT + 'tools/read-fiches.py',
                     encoding='utf-8').read()
        pins = len(re.findall(r"\('[a-z0-9-]+\|\d{4}', '[a-z]+'\):",
                              rf))
        if pins:
            print()
            print('%d fields are pinned absent - the document states '
                  'something and it was judged not to belong' % pins)
    except Exception:
        pass

    # The plantings, which are an estate's and not a vintage's.
    pl = ROOT + 'data/plantings.js'
    if os.path.exists(pl):
        n = len(re.findall(r"(?m)^'[a-z0-9-]+':\{",
                           io.open(pl, encoding='utf-8').read()))
        print()
        print('%d estates have a recorded planting, which is the '
              'vineyard’s and not a vintage’s' % n)

    print()
    man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))
    man_rows = man['sheets']
    docs = collections.defaultdict(collections.Counter)
    for s in man['sheets']:
        if s.get('estate'):
            docs[s['estate']][s.get('role') or '-'] += 1
    has = set(e for e, y in recs)
    empty = [e for e in E if e not in has]
    waiting = [e for e in empty
               if sum(docs.get(e, {}).get(r, 0)
                      for r in ('grand', 'combined', 'page', 'unknown'))]
    print('THE ESTATES WITH NOTHING: %d of %d' % (len(empty), len(E)))
    print('   %d have documents that might still be read' % len(waiting))
    print('   %d have no document at all'
          % len([e for e in empty if e not in waiting]))

    # A row for each classified growth, sorted by what is missing.
    # The totals say how things stand; this says what to do next.
    if CLASSIFIED and not a.estate:
        growth = {}
        for m in re.finditer(r"id:'([a-z0-9-]+)'[^}]{0,400}?"
                             r"growth:(\d+)", t):
            growth[m.group(1)] = int(m.group(2))
        # Documents the manifest holds for a vintage with no record,
        # which is the part of a gap that is recoverable on disk.
        spare = collections.Counter()
        for s in man_rows:
            if s.get('role') not in ('grand', 'combined', 'page'):
                continue
            eid, yr = s.get('estate'), s.get('year')
            if not (eid and yr) or eid not in CLASSIFIED:
                continue
            if (eid, int(yr)) not in recs:
                spare[eid] += 1
        rows = []
        for eid in CLASSIFIED:
            mine = [k for k in recs if k[0] == eid]
            if not mine and not spare[eid]:
                continue
            got = {}
            for f in ('blend', 'taste', 'note'):
                got[f] = len([k for k in held[f] if k[0] == eid])
            u = len([k for k in held['url'] if k[0] == eid])
            missing = 3 * len(mine) - sum(got.values())
            rows.append((missing, eid, len(mine), got, u,
                         spare[eid]))
        rows.sort(key=lambda r: (-r[0], r[1]))
        print()
        print('A ROW EACH, FOR THE CLASSIFIED GROWTHS - sorted by '
              'how much of blend,')
        print('tasting note and growing season is absent across the estate\u2019s records:')
        print()
        print('   %-26s %2s %5s %5s %5s %5s %5s %6s'
              % ('estate', 'gc', 'recs', 'blend', 'taste', 'note',
                 'link', 'spare'))
        for missing, eid, n, got, u, sp in rows:
            print('   %-26s %2s %5d %5d %5d %5d %5d %6d'
                  % (eid[:26], growth.get(eid, '-'), n,
                     got['blend'], got['taste'], got['note'], u,
                     sp))
        print()
        print('   gc    the 1855 or Graves rank, where recorded')
        print('   recs  records this estate has')
        print('   link  records whose source has an address, so the app can link')
        print('   spare documents the manifest holds for a vintage with no record.')
        print('         Not a worklist: asked of all 124 of them, 110 state none of')
        print('         these fields and the three that state anything are one site')
        print('         blurb standing over 25 vintages. read-fiches.py is what asks.')



if __name__ == '__main__':
    # Tee rather than restructure: the terminal sees what it always
    # saw and the same text is kept, cut into sections and written to
    # PROGRESS.md.
    _real = sys.stdout
    _keep = _tee(_real)
    sys.stdout = _keep
    try:
        main()
    finally:
        sys.stdout = _real
    if '--no-save' not in sys.argv and '--estate' not in ' '.join(
            sys.argv):
        row = save(_keep.text())
        print()
        print('saved %s and today\u2019s row in %s (%s records)'
              % (MARKDOWN, HISTORY, row.get('records', '?')))
