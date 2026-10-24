# -*- coding: utf-8 -*-
"""What the corrected reader changed: v2 against v3, context by context.

    python tools/compare-v3.py
    python tools/compare-v3.py --write    data/v3-recharacterization.jsonl

Reads the evidence store, data/evidence/. Writes nothing else, and never a
canonical file. v2 rows are not altered: this compares them with the v3
rows appended beside them.

Three questions.

  1. Did the grand-vin path really not move? Phase 2.3 changed only
     second-wine mode and the sibling-aware marks second-wine mode
     uses. So every grand-vin context should have the same verdict in
     v3 as in v2. Any difference is a regression, and this says so.

  2. What happened to the 4,416 second-wine acceptances v2 gave to
     documents the manifest files as the grand vin's or no wine's?
     Each is classified by its v3 verdict. The old acceptance is not
     treated as truth - it was made by a reader that never asked a
     document to be the second wine's.

  3. The Echo, and its five missing vintages, under v3.

A context is the row identity with the version removed - artifact,
folder, estate, wine, field, vintage, target estate, wine, role and
vintage - so the same question asked of two readers lines up.
"""
import argparse
import collections
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evidence as EV

OUT = ROOT + 'data/v3-recharacterization.jsonl'
MISSING = (2008, 2009, 2010, 2015, 2016)


def ctx_key(d):
    """row_key without the version, so v2 and v3 of one question meet."""
    return EV.row_key(d)[:-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()

    v2, v3 = {}, {}
    for d in EV.ST.iter_rows([2, 3]):
        if d.get('v') == 2:
            v2[ctx_key(d)] = d
        elif d.get('v') == 3:
            v3[ctx_key(d)] = d

    print('v2 contexts %d, v3 contexts %d, in both %d\n'
          % (len(v2), len(v3), len(set(v2) & set(v3))))

    # ------------------------------------------------ 1. the grand vin
    moved = collections.Counter()
    ex = []
    same = 0
    for k in set(v2) & set(v3):
        a2, a3 = v2[k], v3[k]
        if (a2.get('ctx') or {}).get('target_role') != 'grand':
            continue
        if (a2.get('decision'), a2.get('code')) == \
                (a3.get('decision'), a3.get('code')):
            same += 1
        else:
            moved[(a2.get('code'), a3.get('code'))] += 1
            if len(ex) < 6:
                ex.append((a2['artifact'], a2.get('code'), a3.get('code')))
    print('1. GRAND-VIN CONTEXTS - should not have moved')
    print('-' * 60)
    print('   unchanged %d, changed %d' % (same, sum(moved.values())))
    for (x, y), n in moved.most_common(8):
        print('      %-22s -> %-22s %d' % (x, y, n))
    for art, x, y in ex:
        print('      e.g. %s: %s -> %s' % (art[:44], x, y))

    # ------------------------------------- all verdicts, v2 against v3
    print()
    print('VERDICTS BY ROLE, v2 -> v3')
    print('-' * 60)
    for role in ('grand', 'second', 'other'):
        c2 = collections.Counter(d.get('code') for d in v2.values()
                                 if (d.get('ctx') or {}).get(
                                     'target_role') == role)
        c3 = collections.Counter(d.get('code') for d in v3.values()
                                 if (d.get('ctx') or {}).get(
                                     'target_role') == role)
        print('   %s' % role)
        for code in sorted(set(c2) | set(c3),
                           key=lambda c: -(c3.get(c, 0) + c2.get(c, 0))):
            print('      %-26s %7d -> %7d' % (code, c2.get(code, 0),
                                                c3.get(code, 0)))

    # ------------------------------------------- 2. the 4,416
    rows = []
    for k, d2 in v2.items():
        c = d2.get('ctx') or {}
        if c.get('target_role') != 'second':
            continue
        if d2.get('decision') != 'ACCEPTED':
            continue
        mw = c.get('wine')
        if mw and mw != c.get('estate'):
            continue
        d3 = v3.get(k)
        if d3 is None:
            cls = 'NOT_RE_EVALUATED'
        elif d3.get('decision') == 'ACCEPTED':
            cls = 'CONFIRMED_ACCEPTANCE'
        elif d3.get('decision') == 'REFUSED':
            cls = 'REJECTED_BY_V3'
        else:
            cls = 'CHANGED_TO_OTHER_VERDICT'
        rows.append({
            'artifact': d2['artifact'],
            'ctx': c,
            'v2': {'decision': d2.get('decision'), 'code': d2.get('code')},
            'v3': ({'decision': d3.get('decision'), 'code': d3.get('code'),
                    'raw': (d3.get('raw') or '')[:120]}
                   if d3 else None),
            'class': cls,
        })
    print()
    print('2. THE SECOND-WINE ACCEPTANCES OF GRAND-VIN-FILED DOCUMENTS')
    print('-' * 60)
    print('   %d in v2' % len(rows))
    for k, n in collections.Counter(r['class'] for r in rows).most_common():
        print('      %-26s %6d' % (k, n))
    why = collections.Counter((r['v3'] or {}).get('raw', '')[:60]
                              for r in rows
                              if r['class'] == 'REJECTED_BY_V3')
    print('   the v3 reasons for rejecting them:')
    for k, n in why.most_common(6):
        print('      %5d  %s' % (n, k))
    keep = collections.Counter(r['ctx'].get('estate') or
                               r['ctx'].get('target_estate')
                               for r in rows
                               if r['class'] == 'CONFIRMED_ACCEPTANCE')
    print('   still accepted, by estate (top 8):')
    for k, n in keep.most_common(8):
        print('      %-34s %d' % (k, n))

    # ---------------------------------------------- 3. the Echo
    echo = [d for d in v3.values()
            if (d.get('ctx') or {}).get('estate') == 'lynch-bages'
            and (d.get('ctx') or {}).get('target_role') == 'second'
            and d['artifact'].lower().startswith('echo')]
    print()
    print('3. ECHO SHEETS ASKED AS THE ECHO, v3')
    print('-' * 60)
    c = collections.Counter(d.get('code') for d in echo)
    print('   %d evaluations' % len(echo))
    for k, n in c.most_common():
        print('      %-26s %d' % (k, n))
    echo2 = [d for d in v2.values()
             if (d.get('ctx') or {}).get('estate') == 'lynch-bages'
             and (d.get('ctx') or {}).get('target_role') == 'second'
             and d['artifact'].lower().startswith('echo')]
    c2 = collections.Counter(d.get('code') for d in echo2)
    print('   v2 for comparison: %s' % dict(c2))

    print()
    print('FIVE MISSING VINTAGES - the Echo document, asked as the Echo for '
          'its year')
    print('-' * 60)
    for y in MISSING:
        hits = [d for d in echo
                if (d.get('ctx') or {}).get('target_vintage') == y]
        acc = [d for d in hits if d.get('decision') == 'ACCEPTED']
        print('   %d   %d evaluation(s), %d accepted   %s'
              % (y, len(hits), len(acc),
                 ', '.join(sorted(set(d['artifact'] for d in acc)))[:60]))

    if a.write:
        with io.open(OUT, 'w', encoding='utf-8', newline='') as f:
            f.write(json.dumps({
                '_': 'The v2 second-wine acceptances of documents the '
                     'manifest files as the grand vin\'s, and what the '
                     'corrected v3 reader concludes about each. Neither '
                     'is canonical; the v2 rows are unchanged in the '
                     'decision store.',
                'rows': len(rows),
                'classes': dict(collections.Counter(
                    r['class'] for r in rows)),
            }, ensure_ascii=False, sort_keys=True) + '\n')
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False,
                                   sort_keys=True) + '\n')
        print('\nwritten to data/v3-recharacterization.jsonl (%d)'
              % len(rows))


if __name__ == '__main__':
    main()
