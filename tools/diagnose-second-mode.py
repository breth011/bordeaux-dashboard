# -*- coding: utf-8 -*-
"""Why the reader refuses the Echo as the Echo, and what a fix must do.

    python tools/diagnose-second-mode.py            Lynch-Bages
    python tools/diagnose-second-mode.py --all      every estate

Changes nothing. Imports sheetreader and calls it; no file is opened
for writing. This is the Stage A validation gate run BEFORE any change,
to establish what a correct change has to achieve.

                            THE PREMISE WAS WRONG

Phase 2.1 reported that "Lynch-Bages lists the Echo as BOTH its second
wine and a cuvee", and Phase 2.2 was planned as removing that double
listing from the data. The data does not double-list it:

    chateaux.js      second: 'Echo de Lynch-Bages'
    cuvees.js        'lynch-bages': [ ...Blanc (role other)...,
                                      ...Echo (role second)... ]

The Echo appears once in BDX_CUVEE_WINES, correctly marked
role:'second'. The doubling is made by the LOADER, sr.estates():

    e['cuvees'] = js_strings_after('name:', ...)   # ignores `role`
    ...
    if e['second'] and e['second'] not in e['cuvees']:
        e['cuvees'].append(e['second'])            # on purpose

and on purpose: when the reader evaluates the GRAND VIN it must refuse
a second wine's sheet as "another of the estate's wines", and it finds
the second wine by looking in `cuvees`. That is correct and essential.

So removing the Echo from cuvees.js would delete the Echo's wine
definition - its slug, colour and role, which the cuvee reader and the
app both depend on - and would not even fix the refusal, because the
loader re-adds the second wine from chateaux.js. The spec warned
against exactly this: "do not simply delete a string from a file
because it looks duplicated". That warning was right and my Phase 2.1
summary was imprecise.

                            THE REAL FAULT

whose_sheet() answers one question: "is this the GRAND VIN's sheet?"
It has three guards that recognise the second wine, and `is_second`
switches off only one of them:

    naming_spells_cuvee(named, grand, others, second)   still runs
    if not is_second and is_second_wine(path)            switched off
    for nm in (second,) + others: names_another_wine    still runs

So in second-wine mode the reader still refuses the second wine's own
sheet, for naming the second wine.

                         THE TRAP IN THE OBVIOUS FIX

The obvious fix is "in second-wine mode, leave the second wine out of
the competing set". It makes every Echo sheet accepted - and it ALSO
makes every GRAND VIN sheet accepted as the Echo, because nothing in
whose_sheet ever required a document to BE the second wine's; it only
refused documents that named something else. That is precisely
"weakening the reader to make the records appear".

A correct second-wine mode needs a POSITIVE requirement as well: the
document must identify itself as the second wine - by its name, or by
is_second_wine() - and not merely fail to name the others.

This tool measures all three versions side by side:

    CURRENT     whose_sheet as it is
    NAIVE       second wine excluded from the competing set
    CORRECT     excluded, AND the document must name the second wine

on three populations whose right answer is known: the Echo's sheets
(should be accepted), the grand vin's (must be refused as the Echo),
and the Blanc's (must be refused as the Echo).
"""
import argparse
import collections
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr


def verdict_current(p, fn, e, yr):
    return sr.whose_sheet(p, fn, e['name'], e['cuvees'], e['second'],
                          e['cat'], year=yr, is_second=True)


def verdict_naive(p, fn, e, yr):
    """The second wine left out of the competing set, nothing else."""
    others = [c for c in e['cuvees'] if c != e['second']]
    return sr.whose_sheet(p, fn, e['name'], others, None, e['cat'],
                          year=yr, is_second=True)


def names_second(p, fn, e):
    """Does the document identify itself as the second wine?"""
    sec = e.get('second')
    if not sec:
        return False
    if sr.says(fn, sec):
        return True
    try:
        if sr.is_second_wine(p):
            return True
        head = ' '.join(sr.flat(p).split())[:1500]
    except Exception:
        return False
    return sr.says(head, sec)


def verdict_correct(p, fn, e, yr):
    """Naive, plus the positive requirement."""
    v = verdict_naive(p, fn, e, yr)
    if v:
        return v
    if not names_second(p, fn, e):
        return {'why': 'the document does not identify itself as %s'
                       % e['second'], 'role': None, 'wine': None}
    return None


def population(fn, e):
    """Which wine's sheet this is known to be, from its own filename."""
    sec = e.get('second') or ''
    for nm in sorted(e['cuvees'], key=len, reverse=True):
        if sr.says(fn, nm):
            return 'second' if nm == sec else 'other cuvee'
    return 'grand vin'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estate', default='lynch-bages')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()

    E = sr.estates(ROOT)
    man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))
    disk = {}
    for root, dirs, files in os.walk(ROOT + 'sources'):
        for f in files:
            disk.setdefault(f, os.path.join(root, f))

    if a.all:
        targets = sorted(eid for eid, e in E.items()
                         if e.get('second') and e['second']
                         in (e.get('cuvees') or ()))
    else:
        targets = [a.estate]

    grid = collections.defaultdict(collections.Counter)
    false_accept = collections.Counter()
    ex = collections.defaultdict(list)
    n = 0
    for eid in targets:
        e = E.get(eid)
        if not e or not e.get('second'):
            continue
        for s in man.get('sheets', []):
            if s.get('estate') != eid or not s.get('file'):
                continue
            p = disk.get(s['file'])
            if not p:
                continue
            fn = s['file']
            yr = s.get('year')
            try:
                yr = int(yr) if yr else None
            except Exception:
                yr = None
            pop = population(fn, e)
            n += 1
            if a.limit and n > a.limit:
                break
            for name, fnc in (('CURRENT', verdict_current),
                              ('NAIVE', verdict_naive),
                              ('CORRECT', verdict_correct)):
                try:
                    v = fnc(p, fn, e, yr)
                except Exception as ex2:
                    v = {'why': 'error: %s' % type(ex2).__name__}
                res = 'ACCEPTED' if v is None else 'refused'
                grid[(name, pop)][res] += 1
                # A false acceptance: something that is NOT the second
                # wine's sheet accepted as the second wine.
                if res == 'ACCEPTED' and pop != 'second':
                    false_accept[name] += 1
                    if len(ex[name]) < 4:
                        ex[name].append('%s (%s)' % (fn[:44], pop))

    print('%d document(s) at %d estate(s), each evaluated as the SECOND '
          'wine\n' % (n, len(targets)))
    print('%-9s %-12s %10s %10s' % ('VERSION', 'the sheet is', 'ACCEPTED',
                                    'refused'))
    print('-' * 46)
    for name in ('CURRENT', 'NAIVE', 'CORRECT'):
        for pop in ('second', 'grand vin', 'other cuvee'):
            c = grid.get((name, pop))
            if not c:
                continue
            print('%-9s %-12s %10d %10d' % (name, pop, c['ACCEPTED'],
                                            c['refused']))
        print()
    print('FALSE ACCEPTANCES - a sheet that is not the second wine\'s, '
          'accepted as it')
    print('-' * 46)
    for name in ('CURRENT', 'NAIVE', 'CORRECT'):
        print('   %-9s %d' % (name, false_accept[name]))
        for x in ex[name]:
            print('      %s' % x)


if __name__ == '__main__':
    main()
