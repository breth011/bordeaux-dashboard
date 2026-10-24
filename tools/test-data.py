# -*- coding: utf-8 -*-
"""Invariants over the committed data. No archive needed.

    python tools/test-data.py

tools/test-reader.py protects the READER, and most of it needs
sources/, which is not committed - so on a fresh clone it prints
MISSING and protects nothing. This protects the DATA, from the files
that are committed, so it runs anywhere and in seconds.

Each case is a defect found during the evidence census, with the count
it stood at when it was found. The assertion is "no worse than this",
not "equal to this": every one of these is expected to go DOWN, and a
rise means something put it back.

A baseline is not an endorsement. 56 mis-filed sheets is a defect
recorded at its size, not a target.
"""
import collections
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr

E = sr.estates(ROOT)
MAN = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))
SHEETS = MAN.get('sheets', [])

# Only the house word and articles. "blanc" is NOT common here: it is
# exactly what separates Blanc de Lynch-Bages from Echo de Lynch-Bages.
HOUSE = set('chateau clos domaine la le les de du des l d'.split())

fails = []
checks = 0


def check(name, got, limit, why):
    """`got` must not exceed `limit`."""
    global checks
    checks += 1
    ok = got <= limit
    if not ok:
        fails.append(name)
    print('%-4s %-46s %5s  (baseline %s)%s'
          % ('ok' if ok else 'FAIL', name[:46], got, limit,
             '' if ok else '  WORSE'))
    if not ok:
        print('       %s' % why)


def wines_of(e):
    out = []
    if e.get('name'):
        out.append(e['name'])
    if e.get('second'):
        out.append(e['second'])
    out.extend(e.get('cuvees') or ())
    return out


def mark(nm):
    return set(w for w in re.split(r'[^a-z0-9]+', sr.norm(nm))
               if w and w not in HOUSE)


def records():
    recs, per = {}, collections.defaultdict(dict)
    for name, nkey in (('fiches.js', 2), ('cuvees.js', 3)):
        pat = re.compile(r"^'([a-z0-9-]+)\|" +
                         (r"([a-z0-9-]+)\|" if nkey == 3 else '') +
                         r"(\d{4})':\{(.*)\},$")
        for line in io.open(ROOT + 'data/' + name, encoding='utf-8'):
            m = pat.match(line.rstrip())
            if not m:
                continue
            key = '|'.join(m.group(i + 1) for i in range(nkey))
            s = re.search(r"src:'([^']*)'", m.group(nkey + 1))
            recs[key] = {'estate': m.group(1), 'year': int(m.group(nkey)),
                         'src': s.group(1) if s else None}
    for name in ('field-src.js', 'cuvee-src.js'):
        for line in io.open(ROOT + 'data/' + name, encoding='utf-8'):
            m = re.match(r"^'([^']+)':\{(.*)\},$", line.rstrip())
            if not m or m.group(1) not in recs:
                continue
            for f, v in re.findall(r"([a-z]+):'([^']*)'", m.group(2)):
                per[m.group(1)][f] = v
    return recs, per


RECS, PER = records()
BYFILE = dict((s['file'], s) for s in SHEETS if s.get('file'))

# ------------------------------------------------------------------ 1
# The Echo class: a filename naming a wine that is neither the
# manifest's wine nor a shorter spelling of it. 50 of the 56 are
# Echo de Lynch-Bages sheets filed as the Blanc, which cost the second
# wine five vintages - a document existed and no record did.
misfiled = collections.Counter()
for s in SHEETS:
    eid, fn, mw = s.get('estate'), s.get('file'), s.get('wine')
    if not (eid and fn and mw):
        continue
    ws = wines_of(E.get(eid) or {})
    if mw not in ws:
        continue
    for nm in sorted(ws, key=len, reverse=True):
        if not sr.says(fn, nm):
            continue
        a, b = mark(nm), mark(mw)
        if a and b and not (a <= b) and not (b <= a):
            misfiled[eid] += 1
        break
check('manifest wine != the wine the filename names',
      sum(misfiled.values()), 56,
      'a sheet is being offered to the wrong wine, so the guards '
      'refuse it and its own wine never sees it')

# ------------------------------------------------------------------ 2
# Artifacts with no estate on them are offered to no reader at all,
# because every reader iterates sheets by estate. 904 of the 908 sit
# in a folder that names an estate.
noestate = [s for s in SHEETS if not s.get('estate')]
check('artifacts with no estate in the manifest', len(noestate), 908,
      'a reader iterates by estate, so these are invisible to all of '
      'them however good the document is')

# ------------------------------------------------------------------ 3
# Zero-byte files registered as artifacts: an OCR run that produced
# nothing and was recorded as though it had.
check('artifacts recording bytes = 0',
      sum(1 for s in SHEETS if s.get('bytes') == 0), 4,
      'an empty file registered as evidence')

# ------------------------------------------------------------------ 4
# Identical bytes under two named estates, with DIFFERENT filenames -
# the same PDF downloaded twice and filed to two estates. The
# same-filename case is a group document (one annual report covering
# four Rothschild estates) and is legitimate, so it is not counted.
byh = collections.defaultdict(list)
for s in SHEETS:
    if s.get('sha1'):
        byh[s['sha1']].append(s)
twice = 0
for h, v in byh.items():
    named = set(e for e in (x.get('estate') for x in v) if e)
    if len(named) > 1 and len(set(x.get('file') for x in v)) > 1:
        twice += 1
check('same bytes, two estates, two filenames', twice, 14,
      'one document downloaded twice and filed to two estates')

# ------------------------------------------------------------------ 5
# A record citing a document that is not in the manifest or not on
# disk. 37 of the 44 are Latour records citing a URL rather than a
# filename, which is a provenance shape rather than missing evidence.
weak = 0
for k, r in RECS.items():
    srcs = set(v for v in PER.get(k, {}).values() if v)
    if r['src']:
        srcs.add(r['src'])
    if not srcs or not (srcs & set(BYFILE)):
        weak += 1
check('records citing no manifest document', weak, 44,
      'the record cannot be traced to a registered artifact')

# ------------------------------------------------------------------ 6
# A record whose year is one off the year its own document spells,
# excluding primeur sheets (published the spring after the vintage,
# so a 2024 filename on a 2023 wine is correct).
offby = 0
cited = collections.defaultdict(set)
for k, r in RECS.items():
    if r['src']:
        cited[r['src']].add(k)
    for v in PER.get(k, {}).values():
        cited[v].add(k)
for fn, keys in cited.items():
    s = BYFILE.get(fn)
    if not s:
        continue
    fy = set(int(y) for y in re.findall(r'(?<!\d)((?:19|20)\d\d)(?!\d)',
                                        fn))
    if not fy or re.search(r'(?i)primeur', fn):
        continue
    for k in keys:
        ry = RECS[k]['year']
        if ry in fy or (s.get('year') and int(s['year']) in fy):
            continue
        if min(abs(y - ry) for y in fy) == 1:
            offby += 1
check('records one year off their own document', offby, 2,
      'an off-by-one between the filename and the record')

# ------------------------------------------------------------------ 7
# The census must stay attributable to the analyzer that made it.
p = ROOT + 'data/artifact-census.jsonl'
if os.path.exists(p):
    with io.open(p, encoding='utf-8') as f:
        head = json.loads(f.readline())
    checks += 1
    ok = bool(head.get('analyzer_version')) and bool(head.get('commit'))
    if not ok:
        fails.append('census header')
    print('%-4s %-46s %5s' % ('ok' if ok else 'FAIL',
                              'census names its analyzer version and '
                              'commit',
                              'v%s @%s' % (head.get('analyzer_version'),
                                           head.get('commit'))))
else:
    print('MISSING  data/artifact-census.jsonl - run tools/census.py '
          '--write && tools/census-compact.py')

# ------------------------------------------------------------------ 8
# Manifest rows that duplicate another on every identifying field.
# Found by the Phase 2 idempotence test failing: a decision store keyed
# on (file, estate, wine) had 654 duplicates, and the cause was not the
# key - the manifest holds two rows for the same physical file in the
# same folder for the same wine and year.
#
# Harmless to the readers, which iterate rows and do the same work
# twice, but it inflates every count taken from the manifest: 13,032
# sheets are 12,858 distinct ones.
dupe = collections.Counter(
    (s.get('file'), s.get('folder'), s.get('estate'), s.get('wine'),
     s.get('year')) for s in SHEETS)
check('manifest rows duplicating another row exactly',
      sum(n - 1 for n in dupe.values() if n > 1), 174,
      'two rows for one file in one folder: every manifest count is '
      'inflated by this much')

print('\n%d check(s), %s'
      % (checks, 'all pass' if not fails
         else '%d FAILED: %s' % (len(fails), ', '.join(fails))))
sys.exit(1 if fails else 0)
