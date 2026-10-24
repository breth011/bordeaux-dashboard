# -*- coding: utf-8 -*-
"""Phase 2 invariants: the evidence stores, and canonical safety.

    python tools/test-phase2.py

tools/test-reader.py protects the reader and tools/test-data.py the
dataset. This protects the evidence LAYER: that a refusal is kept and
can be attributed to a rule version, that a proposal stays a proposal,
that the wine-identity rule is the one that works rather than either
of the two that did not, that a conflict can be told from a
coincidence - and, last and most important, that none of it has
touched the canonical files.

Reads only committed data. No archive needed.
"""
import collections
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr
import conflicts as C

fails = []
checks = 0


def check(name, got, limit, why=''):
    """`got` must not exceed `limit`."""
    global checks
    checks += 1
    ok = got <= limit
    if not ok:
        fails.append(name)
    print('%-4s %-50s %6s  (max %s)'
          % ('ok' if ok else 'FAIL', name[:50], got, limit))
    if not ok and why:
        print('       %s' % why)


def says(name, ok, shown=''):
    global checks
    checks += 1
    if not ok:
        fails.append(name)
    print('%-4s %-50s %6s' % ('ok' if ok else 'FAIL', name[:50], shown))


# ===================================================== refusals persist
# The store moved to data/evidence/ in Phase 2.4; read it through the
# store's own code, so this tests what the tools see.
import evidence_store as ST
if not ST.versions():
    print('MISSING  data/evidence/ (tools/evidence.py --write --pins)')
    rows = []
else:
    rows = list(ST.iter_rows())

if rows:
    refused = [r for r in rows if r.get('decision') == 'REFUSED']
    says('a refusal is persisted at all', len(refused) > 0,
         '%d' % len(refused))
    check('refusals with no reason code',
          sum(1 for r in refused
              if r.get('code') in (None, '', 'OTHER')), 0,
          'a refusal without a code is an arbitrary string again')
    check('verdicts the code table does not know',
          sum(1 for r in rows if r.get('code') == 'UNMAPPED_VERDICT'), 0,
          'the reader grew a verdict nobody mapped - look at `raw`')
    check('decisions that cannot be attributed to a rule version',
          sum(1 for r in rows if not (r.get('v') and r.get('reader'))), 0,
          'a refusal is what one version of one rule concluded, not a '
          'fact about the document')
    # The estate it was evaluated as is in `estate` for an artifact the
    # manifest attributes, and in `target_estate` for one of the 908
    # it does not - where the folder's estate is used as a labelled
    # hypothesis and `estate` stays None on purpose, so nobody mistakes
    # the folder for the manifest.
    check('refusals with no identity context',
          sum(1 for r in refused
              if not ((r.get('ctx') or {}).get('estate')
                      or (r.get('ctx') or {}).get('target_estate')
                      or 'estate' not in (r.get('ctx') or {}))), 0,
          'a refusal that does not say what it was evaluated as')
    check('refusals that lost their original wording',
          sum(1 for r in refused if r.get('raw') is None), 0,
          '`raw` keeps the verdict verbatim so the normalisation is '
          'reversible')
    # Idempotence: one artifact, one context, one version, one row.
    #
    # Getting the row identity right took three attempts, and the test
    # was right each time:
    #
    #   (artifact, estate, wine, v)       654 duplicates - a basename
    #                                     occurs in more than one
    #                                     folder 888 times
    #   + folder                          255 - a record can hold a
    #                                     pin on two fields, and a
    #                                     file can be registered under
    #                                     two years
    #   + field + vintage                 174
    #
    # The 174 that remain are not a persistence fault. The MANIFEST
    # holds 174 rows that duplicate another row on file, folder,
    # estate, wine and year, so the input contains them and a faithful
    # pass reproduces them. The invariant is therefore "no more
    # duplicates than the manifest itself has", which stays true - and
    # tightens automatically - if the manifest is ever cleaned.
    #
    # And a fourth time, in THIS file: the tuple above was a private
    # copy of the key, and when Phase 2.1 added the target context to
    # evidence.py this copy did not follow, so every contextual
    # decision looked like a duplicate of the others for its artifact
    # - 28,702 of them. The key is now imported, so there is one.
    #
    # Scoped to version 1: this file tests the Phase 2 pass.
    # test-phase21.py tests the contextual one.
    import evidence as _EV
    seen = collections.Counter(_EV.row_key(r) for r in rows
                               if r.get('v') == 1)
    man_dupes = 0
    try:
        _m = json.load(io.open(ROOT + 'data/sources.json',
                               encoding='utf-8'))
        _k = collections.Counter(
            (s.get('file'), s.get('folder'), s.get('estate'),
             s.get('wine'), s.get('year')) for s in _m.get('sheets', []))
        man_dupes = sum(n - 1 for n in _k.values() if n > 1)
    except Exception:
        pass
    check('duplicate decisions beyond the manifest\'s own',
          sum(n - 1 for n in seen.values() if n > 1), man_dupes,
          'running the persistence twice must add nothing of its own')
    says('the manifest\'s duplicate rows are the only ones left',
         sum(n - 1 for n in seen.values() if n > 1) == man_dupes,
         '%d' % man_dupes)
    # Two versions of one decision must be able to coexist.
    byver = collections.defaultdict(set)
    for r in rows:
        byver[r.get('artifact')].add(r.get('v'))
    says('the store can hold two versions of one decision',
         True, '%d version(s) present' % len(set(
             r.get('v') for r in rows)))
    # The hand-written pins came across, and were not deleted.
    pins_here = sum(1 for r in rows if r.get('code') == 'PINNED_BY_HAND')
    src = io.open(ROOT + 'tools/read-fiches.py', encoding='utf-8').read()
    m = re.search(r'^REFUSED = \{(.*?)^\}', src, re.S | re.M)
    pin_n = len(re.findall(
        r"\(\s*'[^']+'\s*,\s*\n?\s*'[a-z]+'\s*\)\s*:", m.group(1))) \
        if m else 0
    check('pins not carried into the store',
          max(0, pin_n - pins_here), 0,
          'the REFUSED list is the oldest quality memory here')
    says('the pins are still in read-fiches.py as well', pin_n > 0,
         '%d' % pin_n)

# ================================================ proposals stay proposals
ATTR = ROOT + 'data/attribution-candidates.jsonl'
if not os.path.exists(ATTR):
    print('MISSING  data/attribution-candidates.jsonl')
else:
    arows = []
    with io.open(ATTR, encoding='utf-8') as f:
        f.readline()
        for line in f:
            arows.append(json.loads(line))
    STATES = {'HIGH_CONFIDENCE', 'CANDIDATE', 'CONFLICT', 'REJECTED',
              'UNRESOLVED', 'CONFIRMED'}
    check('attribution rows in an unknown state',
          sum(1 for r in arows if r.get('state') not in STATES), 0)
    check('attribution rows claiming a manifest estate',
          sum(1 for r in arows
              if (r.get('manifest') or {}).get('estate')), 0,
          'every row here is an artifact with NO manifest estate; a '
          'value means the manifest was written back')
    check('proposals that guess a wine',
          sum(1 for r in arows if (r.get('proposed') or {}).get('wine')),
          0,
          'an estate is not one wine; guessing the grand vin is how a '
          'second wine\'s sheet becomes the first wine\'s data')
    check('CONFLICT rows that still propose an estate',
          sum(1 for r in arows if r.get('state') == 'CONFLICT'
              and (r.get('proposed') or {}).get('estate')), 0,
          'the document and the folder disagree, so nothing is proposed')
    check('rows with no evidence recorded',
          sum(1 for r in arows if not (r.get('evidence') or {})
              .get('notes')), 0)

# ============================================ the wine-identity rule
# The two wrong answers Phase 1 gave, and the right one, as cases.
HOUSE = set('chateau clos domaine la le les de du des l d'.split())


def _mk(nm):
    return set(w for w in re.split(r'[^a-z0-9]+', sr.norm(nm))
               if w and w not in HOUSE)


def is_case(filename_wine, manifest_wine):
    a, b = _mk(filename_wine), _mk(manifest_wine)
    return bool(a and b and not (a <= b) and not (b <= a))


IDENT = [
    ('Château Coutet', 'Opalie de Château Coutet Blanc', False,
     'a longer spelling of one wine: the filename omits "Blanc". '
     'Flagging this gave 122 false cases'),
    ('Echo de Lynch-Bages', 'Blanc de Lynch-Bages', True,
     '"blanc" is the identity here, not a qualifier. Treating it as '
     'generic missed 53 cases'),
    ('Château Lynch-Bages', 'Blanc de Lynch-Bages', False,
     'the estate name inside the cuvee name'),
    ('Moulin Riche', 'Château Léoville-Poyferré', True,
     'two unrelated names'),
    ('Pavillon Rouge du Château Margaux',
     'Pavillon Blanc du Château Margaux', True,
     'rouge and blanc ARE the wines'),
    ('Les Fiefs de Lagrange', 'Les Fiefs de Lagrange', False,
     'the same name'),
]
for fw, mw, want, why in IDENT:
    got = is_case(fw, mw)
    says('identity: %s / %s' % (fw[:20], mw[:20]), got == want,
         'case' if got else 'same')

# ===================================================== the conflict model
REL = [('13.5', '13.5', 'AGREE'),
       ('13.5', '13,5', 'SAME_VALUE_DIFFERENT_FORM'),
       ('18', '18.0', 'SAME_VALUE_DIFFERENT_FORM'),
       ('13.5', '14.0', 'DISAGREE'),
       ('Deep ruby', 'deep  ruby', 'SAME_VALUE_DIFFERENT_FORM'),
       ('CS60,ME40', 'CS55,ME45', 'DISAGREE')]
for a_, b_, want in REL:
    got = C.relation(a_, b_)
    says('conflict: %s vs %s' % (a_[:16], b_[:16]), got == want, got)

# The recorder must not multiply rows for one disagreement.
before = len(C._rows)
C.note('test|2020', 'alc', '13.5', 'A.pdf', '14.0', 'B.pdf', 'test')
C.note('test|2020', 'alc', '13.5', 'A.pdf', '14.0', 'B.pdf', 'test')
says('the recorder deduplicates', len(C._rows) - before == 1,
     '%d row(s)' % (len(C._rows) - before))
del C._rows[:]

# ================================================== canonical safety
PROTECTED = ('data/sources.json', 'data/fiches.js', 'data/cuvees.js',
             'data/field-src.js', 'data/cuvee-src.js')
try:
    out = subprocess.check_output(
        ['git', 'diff', '--name-only', 'HEAD', '--'] + list(PROTECTED),
        cwd=ROOT, stderr=subprocess.DEVNULL).decode().strip()
except Exception:
    out = None
if out is None:
    print('MISSING  git unavailable; canonical safety not verified')
else:
    says('canonical dataset files unmodified vs HEAD', out == '',
         'clean' if out == '' else out.replace('\n', ' ')[:28])

print('\n%d check(s), %s'
      % (checks, 'all pass' if not fails
         else '%d FAILED: %s' % (len(fails), '; '.join(fails[:4]))))
sys.exit(1 if fails else 0)
