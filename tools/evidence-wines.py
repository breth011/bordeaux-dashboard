# -*- coding: utf-8 -*-
"""The reader asked properly: which estate, which wine, which vintage.

    python tools/evidence-wines.py --estate lynch-bages
    python tools/evidence-wines.py --write          the whole archive
    python tools/evidence-wines.py --changed        what the vintage changed

Appends to the evidence store (data/evidence/) - the same store Phase 2
wrote, with the same row_key(), so there is one persistence mechanism
and not two. Writes nothing else. No canonical dataset file is opened
for writing.

                      WHAT WAS WRONG BEFORE

Phase 2 evaluated each artifact once, as its estate's grand vin, with
no target vintage. Two consequences, and the second is the serious one:

  whose_sheet() takes `year` and Phase 2 passed None, so the three
  vintage guards - "nothing states this vintage", "the document
  declares the N vintage", "the filename calls this the N vintage" -
  could not fire. WRONG_VINTAGE was absent from 13,065 decisions not
  because no document fails it but because nobody asked.

  And every document was judged as the grand vin's. An estate is not
  one wine. A sheet for the second wine was refused as "names another
  of the estate's wines", which is true and useless: the question
  worth asking is whether it is the SECOND WINE's sheet, and that
  question was never put.

                        THE EVALUATION UNIVERSE

Not every artifact against every context - that invents meaningless
combinations. For each artifact the contexts are drawn from what is
already known about it:

  WINES     every wine the estate makes, from BDX_CUVEE_WINES and
            chateaux.js: the grand vin, the second, each cuvee. This
            is the part Phase 2 skipped.

  VINTAGES  the manifest's year, plus any year the filename spells,
            plus the year the document declares of itself. Capped at
            three, most-likely first.

A year in a filename is EVIDENCE, not truth - Phase 1 found the year
classifier wrong in 8 of 19 cases - so every candidate year is tried
and the decisions are kept side by side rather than one being chosen.

                         THE SECOND-WINE MODE

whose_sheet() takes `is_second`, which turns off the guard that
refuses a document for naming the second wine. Evaluating a cuvee
context without it would refuse every second wine's sheet for being
the second wine's sheet. So the flag is set when the target wine is
the second, and that is what makes a cuvee context mean anything.
"""
import argparse
import collections
import datetime
import importlib.util
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr
import evidence as EV
import provenance as PV

# 3: Phase 2.3. The reader gained a real second-wine mode and
# sibling-aware marks, so its second-wine verdicts mean something
# different from version 2's. A new version, not an overwrite: the v2
# rows stay as the record of what the old reader concluded.
DECIDER_VERSION = 3
MAX_YEARS = 3
YEAR_IN = re.compile(r'(?<!\d)((?:19|20)\d\d)(?!\d)')
YEAR_DECLARED = re.compile(
    r'(?i)\b(?:mill[eé]sime|vintage|a[nñ]ada|annata)\b'
    r'[^0-9]{0,24}((?:19|20)\d\d)')


def wines_of(e):
    """Every wine the estate makes, with its role.

    The role matters: whose_sheet needs is_second for the second wine
    or it refuses that wine's own sheet for being it.
    """
    out = [('grand', e.get('name'))]
    if e.get('second'):
        out.append(('second', e['second']))
    for c in (e.get('cuvees') or ()):
        out.append(('other', c))
    return [(r, n) for r, n in out if n]


def candidate_years(s, text):
    """The years this artifact might be about, most likely first."""
    out = []
    my = s.get('year')
    try:
        my = int(my) if my else None
    except Exception:
        my = None
    if my:
        out.append(my)
    for y in YEAR_DECLARED.findall(text or ''):
        y = int(y)
        if y not in out:
            out.append(y)
    for y in YEAR_IN.findall(s.get('file') or ''):
        y = int(y)
        if y not in out and 1800 < y < 2100:
            out.append(y)
    return out[:MAX_YEARS] or [None]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estate')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--changed', action='store_true')
    ap.add_argument('--allow-dirty', action='store_true')
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()

    E = sr.estates(ROOT)
    man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))
    sheets = [s for s in man.get('sheets', []) if s.get('estate')
              and s.get('file')]
    if a.estate:
        sheets = [s for s in sheets if s['estate'] == a.estate]
    if a.limit:
        sheets = sheets[:a.limit]

    # Each sheet's file is found from its own folder and name, and hashed
    # around the reading: tools/provenance.py. Never by basename alone.
    run = PV.Run(DECIDER_VERSION)

    # What the no-vintage pass concluded, so the change is reportable.
    before = {}
    for d in EV.ST.iter_rows([1]):
        if d.get('kind') == 'guard':
            before[(d.get('artifact'),
                    (d.get('ctx') or {}).get('folder'))] = d.get('code')

    fp, cm = EV.reader_fingerprint(), EV.commit()
    rows, counts = [], collections.Counter()
    ctxs = 0
    accepted_for = collections.defaultdict(list)
    n = 0
    # Estate by estate, so sheetreader's 2,000-entry text cache keeps
    # a useful hit rate instead of thrashing.
    for eid in sorted(set(s['estate'] for s in sheets)):
        e = E.get(eid) or {}
        wines = wines_of(e)
        if not wines:
            continue
        for s in [x for x in sheets if x['estate'] == eid]:
            fn = s['file']
            base = {'estate': eid, 'wine': s.get('wine'),
                    'vintage': s.get('year'), 'folder': s.get('folder')}
            art = run.resolve(s, base)
            p = art.path if art else None
            first = len(rows)
            n += 1
            if n % 400 == 0:
                sys.stderr.write('  %d of %d artifacts, %d contexts\n'
                                 % (n, len(sheets), ctxs))
                sys.stderr.flush()
            if not p:
                continue
            try:
                text = sr.flat(p)
            except Exception:
                text = ''
            years = candidate_years(s, text)
            for role, wname in wines:
                for yr in years:
                    ctxs += 1
                    # The guard chain knows two wine modes: the
                    # grand vin, and the second wine via is_second.
                    # There is no mode for an arbitrary cuvee, so
                    # asked about the Blanc it answers "names another
                    # of the estate's wines" - which means "not the
                    # grand vin" and says nothing about the Blanc.
                    # Recorded as unanswerable rather than as an
                    # answer.
                    if role == 'other':
                        code = 'GUARD_HAS_NO_CUVEE_MODE'
                        raw = ('whose_sheet has is_second but no mode '
                               'for a named cuvee, so it cannot judge '
                               'whether this is %s\u2019s sheet'
                               % wname)
                        dec = 'NOT_EVALUATED'
                        v = None
                        counts[code] += 1
                        rows.append({
                            'artifact': fn, 'kind': 'guard',
                            'ctx': {
                                'estate': eid, 'wine': s.get('wine'),
                                'vintage': s.get('year'),
                                'folder': s.get('folder'),
                                'target_wine': wname,
                                'target_role': role,
                                'target_vintage': yr,
                                'evaluated_as': '%s, vintage %s'
                                                % (wname,
                                                   yr or 'unstated'),
                            },
                            'decision': dec, 'code': code, 'raw': raw,
                            **run.stamp(s, art),
                            'evidence': ['the reader has no cuvee mode'],
                            'v': DECIDER_VERSION, 'reader': fp,
                            'at': datetime.date.today().isoformat(),
                            're_evaluable': True,
                        })
                        continue
                    try:
                        v = sr.whose_sheet(
                            p, fn, e.get('name'), e.get('cuvees') or (),
                            e.get('second'), e.get('cat'), year=yr,
                            is_second=(role == 'second'))
                    except Exception as ex:
                        v = {'why': 'a guard could not read it: %s'
                                    % type(ex).__name__,
                             'role': None, 'wine': None}
                    if v:
                        code, raw = EV.code_for(v.get('why'))
                        dec = 'REFUSED'
                    else:
                        code, raw, dec = 'ACCEPTED', '', 'ACCEPTED'
                        accepted_for[(eid, wname, yr)].append(fn)
                    counts[code] += 1
                    rows.append({
                        'artifact': fn, 'kind': 'guard',
                        'ctx': {
                            'estate': eid, 'wine': s.get('wine'),
                            'vintage': s.get('year'),
                            'folder': s.get('folder'),
                            'target_wine': wname,
                            'target_role': role,
                            'target_vintage': yr,
                            'evaluated_as': '%s, vintage %s'
                                            % (wname, yr or 'unstated'),
                        },
                        'decision': dec, 'code': code, 'raw': raw,
                        'points_at': {'role': v.get('role') if v else None,
                                      'wine': v.get('wine') if v else None},
                        **run.stamp(s, art),
                        'evidence': ['whose_sheet with year=%s, '
                                     'is_second=%s'
                                     % (yr, role == 'second')],
                        'v': DECIDER_VERSION, 'reader': fp,
                        'at': datetime.date.today().isoformat(),
                        're_evaluable': True,
                    })
            # The bytes must still be the ones hashed before the reader
            # ran; if not, nothing it said about them is kept.
            if not run.confirm(art, s, base):
                del rows[first:]

    print('%d artifact(s), %d estate/wine/vintage context(s), '
          '%d decision(s)' % (n, ctxs, len(rows)))
    print('decider version %d, reader %s' % (DECIDER_VERSION, fp))
    print('git %s%s' % (run.git['commit'][:12],
                        ' DIRTY ' + run.git['status_hash'][:12]
                        if run.git['dirty'] else ' clean'))
    print(PV.report(run) + '\n')
    print('%-30s %s' % ('DECISION', 'n'))
    print('-' * 46)
    for k, c in counts.most_common():
        print('   %-28s %6d' % (k, c))

    # Vintage behaviour, which is the point of the pass.
    withyr = sum(1 for r in rows if r['ctx']['target_vintage'])
    print()
    print('VINTAGE')
    print('-' * 46)
    print('   %-34s %6d' % ('decisions WITH a target vintage', withyr))
    print('   %-34s %6d' % ('decisions with none available',
                            len(rows) - withyr))
    for k in ('WRONG_VINTAGE', 'NO_VINTAGE_STATED'):
        print('   %-34s %6d' % (k, counts.get(k, 0)))

    # What supplying the vintage changed.
    changed = collections.Counter()
    examples = collections.defaultdict(list)
    for r in rows:
        was = before.get((r['artifact'], r['ctx'].get('folder')))
        if was is None:
            continue
        # Only the context Phase 2 actually asked about: the grand vin
        # at the manifest's own year. Comparing its one verdict against
        # every new context makes a 2017 sheet judged against 2014 look
        # like a verdict that changed, when it is a question nobody put
        # before and WRONG_VINTAGE is the right answer to it.
        if r['ctx']['target_role'] != 'grand':
            continue
        mv = r['ctx'].get('vintage')
        try:
            mv = int(mv) if mv else None
        except Exception:
            mv = None
        if r['ctx']['target_vintage'] != mv:
            continue
        now = r['code']
        if was != now:
            changed[(was, now)] += 1
            if len(examples[(was, now)]) < 3:
                examples[(was, now)].append(
                    '%s  (%s, %s)' % (r['artifact'][:40],
                                      r['ctx']['target_wine'][:18],
                                      r['ctx']['target_vintage']))
    print()
    print('CHANGED: the same context Phase 2 asked (grand vin, manifest year)')
    print('-' * 46)
    if not changed:
        print('   nothing changed')
    for (was, now), c in changed.most_common(12):
        print('   %-22s -> %-22s %5d' % (was, now, c))
        if a.changed:
            for x in examples[(was, now)]:
                print('      %s' % x)

    # Contexts with no accepted document at all.
    print()
    print('CONTEXTS WITH AT LEAST ONE ACCEPTED DOCUMENT')
    print('-' * 46)
    print('   %-34s %6d' % ('estate/wine/vintage', len(accepted_for)))

    if a.write:
        n, nf = PV.write(run, rows, a.allow_dirty)
        print('\n%d decision(s) appended' % n)
        if nf:
            print('%d provenance failure(s) recorded, apart from the '
                  'decisions' % nf)
        if n != len(rows):
            print('%d already recorded at version %d and left alone'
                  % (len(rows) - n, DECIDER_VERSION))
    else:
        print('\nnothing written; pass --write')


if __name__ == '__main__':
    main()
