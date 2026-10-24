# -*- coding: utf-8 -*-
"""The 908 unattributed artifacts, asked in context.

    python tools/recharacterize.py
    python tools/recharacterize.py --write
    python tools/recharacterize.py --estate doisy-daene

Appends to the evidence store (data/evidence/) - the same store, the same
row_key - and writes nothing else.

                          WHY A SEPARATE PASS

evidence-wines.py iterates the manifest's sheets and skips any with no
`estate`, because without one there is no estate whose wines could be
the contexts. That is exactly the 908. So the contextual pass covers
12,124 artifacts and not these, and they would have stayed
characterised only by Phase 2's "NO_ESTATE_IN_MANIFEST" - which is a
fact about the manifest and says nothing about the document.

Here the folder's estate is used as the context, and that is a
HYPOTHESIS, not an attribution. The decision rows say so:
`target_estate_from` records that the estate came from the folder
rather than from the manifest, so no later reader can mistake one for
the other. The folder has been wrong before - the whole de
Braude/Mongravey pattern is a crawler filing documents under the wrong
estate - which is the reason for labelling it rather than trusting it.

                        WHAT THIS CHANGES

A HIGH_CONFIDENCE estate attribution from Phase 2 meant "the document
names the estate its folder does". It never meant the document is any
particular WINE of that estate, or of any particular year. Asked per
wine and per vintage, an artifact can be:

    the estate's grand vin of a stated year        ACCEPTED
    the estate's but refused for the year asked    WRONG_VINTAGE
    another of the estate's wines                  WRONG_WINE
    not that estate's at all                       WRONG_ESTATE
    unanswerable for a named cuvee                 GUARD_HAS_NO_CUVEE_MODE

and the first is the only one that supports a record.
"""
import argparse
import collections
import datetime
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

# 3: Phase 2.3, the corrected reader. 4: Phase 2.7, the Phase 2.6
# reader with established provenance. See evidence-wines.py.
DECIDER_VERSION = 4
YEAR_IN = re.compile(r'(?<!\d)((?:19|20)\d\d)(?!\d)')
YEAR_DECLARED = re.compile(
    r'(?i)\b(?:mill[eé]sime|vintage|a[nñ]ada|annata)\b'
    r'[^0-9]{0,24}((?:19|20)\d\d)')


def wines_of(e):
    out = [('grand', e.get('name'))]
    if e.get('second'):
        out.append(('second', e['second']))
    for c in (e.get('cuvees') or ()):
        out.append(('other', c))
    return [(r, n) for r, n in out if n]


def folder_estate(path, E):
    parts = str(path or '').split('/')
    for cand in (parts[1] if len(parts) > 1 else None,
                 parts[0] if parts else None):
        if cand and cand in E:
            return cand
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estate')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--allow-dirty', action='store_true')
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()

    E = sr.estates(ROOT)
    man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))
    sheets = [s for s in man.get('sheets', [])
              if s.get('file') and not s.get('estate')]

    # What Phase 2's attribution concluded, so the change is reportable.
    prev = {}
    p = ROOT + 'data/attribution-candidates.jsonl'
    if os.path.exists(p):
        with io.open(p, encoding='utf-8') as f:
            f.readline()
            for line in f:
                d = json.loads(line)
                # By the full path: a basename occurs in more than one
                # folder 888 times, and keying on it merged 908 rows
                # into 727 and misreported the cross-tab.
                prev[d['artifact']] = d['state']

    # Found from its own folder and name, hashed around the reading:
    # tools/provenance.py. Never by basename alone.
    run = PV.Run(DECIDER_VERSION)

    rows, counts, ctxs = [], collections.Counter(), 0
    best = {}            # artifact -> the strongest decision seen
    for s in sheets:
        fn = s['file']
        folder = s.get('folder') or ''
        akey = folder + '/' + fn
        eid = folder_estate(folder + '/' + fn, E) or \
            folder_estate(folder, E)
        if a.estate and eid != a.estate:
            continue
        if not eid:
            counts['NO_ESTATE_ANYWHERE'] += 1
            best[akey] = 'NO_ESTATE_ANYWHERE'
            continue
        e = E.get(eid) or {}
        wines = wines_of(e)
        if not wines:
            counts['NO_WINES'] += 1
            best[akey] = 'NO_WINES'
            continue
        base = {'estate': None, 'wine': s.get('wine'),
                'vintage': s.get('year'), 'folder': s.get('folder'),
                'target_estate': eid}
        art = run.resolve(s, base)
        if not art:
            # Not a decision: we could not say which file to read.
            counts['(provenance failure)'] += 1
            best[akey] = 'PROVENANCE_FAILURE'
            continue
        p2 = art.path
        first = len(rows)
        try:
            text = sr.flat(p2)
        except Exception:
            text = ''
        years = []
        for y in YEAR_DECLARED.findall(text or ''):
            if int(y) not in years:
                years.append(int(y))
        for y in YEAR_IN.findall(fn):
            if 1800 < int(y) < 2100 and int(y) not in years:
                years.append(int(y))
        years = years[:3] or [None]

        for role, wname in wines:
            for yr in years:
                ctxs += 1
                if role == 'other':
                    code, dec = 'GUARD_HAS_NO_CUVEE_MODE', 'NOT_EVALUATED'
                    raw = ('whose_sheet has no mode for a named cuvee, '
                           'so it cannot judge whether this is '
                           '%s’s sheet' % wname)
                else:
                    try:
                        v = sr.whose_sheet(
                            p2, fn, e.get('name'),
                            e.get('cuvees') or (), e.get('second'),
                            e.get('cat'), year=yr,
                            is_second=(role == 'second'))
                    except Exception as ex:
                        v = {'why': 'a guard could not read it: %s'
                                    % type(ex).__name__}
                    if v:
                        code, raw = EV.code_for(v.get('why'))
                        dec = 'REFUSED'
                    else:
                        code, raw, dec = 'ACCEPTED', '', 'ACCEPTED'
                counts[code] += 1
                # ACCEPTED anywhere is the strongest thing to know.
                if code == 'ACCEPTED' or akey not in best:
                    best[akey] = code
                rows.append({
                    'artifact': fn, 'kind': 'guard',
                    'ctx': {
                        'estate': None,
                        'wine': s.get('wine'),
                        'vintage': s.get('year'),
                        'folder': s.get('folder'),
                        'target_estate': eid,
                        'target_estate_from': 'folder, a hypothesis - '
                                              'the manifest gives none',
                        'target_wine': wname,
                        'target_role': role,
                        'target_vintage': yr,
                        'evaluated_as': '%s / %s, vintage %s'
                                        % (eid, wname, yr or 'unstated'),
                    },
                    'decision': dec, 'code': code, 'raw': raw,
                    **run.stamp(s, art),
                    'evidence': ['the manifest gives no estate; the '
                                 'folder names %s' % eid,
                                 'whose_sheet with year=%s, is_second=%s'
                                 % (yr, role == 'second')],
                    'v': DECIDER_VERSION,
                    'reader': EV.reader_fingerprint(),
                    'at': datetime.date.today().isoformat(),
                    're_evaluable': True,
                })
        if not run.confirm(art, s, base):
            del rows[first:]
            best[akey] = 'PROVENANCE_FAILURE'

    print('%d unattributed artifact row(s), %d distinct filename(s), '
          '%d context(s), %d decision(s)\n'
          % (len(sheets), len(set(s['file'] for s in sheets)), ctxs,
             len(rows)))
    print('%-32s %s' % ('DECISION', 'n'))
    print('-' * 46)
    for k, c in counts.most_common():
        print('   %-30s %6d' % (k, c))

    print()
    print('STRONGEST RESULT PER ARTIFACT')
    print('-' * 46)
    for k, c in collections.Counter(best.values()).most_common():
        print('   %-30s %6d' % (k, c))

    print()
    print('AGAINST PHASE 2\'S ATTRIBUTION STATE')
    print('-' * 60)
    print('%-20s %-28s %s' % ('phase 2', 'now (strongest)', 'n'))
    cross = collections.Counter(
        (prev.get(fn, '(not in that file)'), st)
        for fn, st in best.items())
    for (was, now), c in cross.most_common(14):
        print('   %-18s %-28s %5d' % (was[:18], now[:28], c))

    if a.write:
        n, nf = PV.write(run, rows, a.allow_dirty)
        print('\n%d decision(s) appended' % n)
        if nf:
            print('%d provenance failure(s) recorded, apart from the '
                  'decisions' % nf)
        if n != len(rows):
            print('%d already recorded and left alone' % (len(rows) - n))
    else:
        print('\nnothing written; pass --write')


if __name__ == '__main__':
    main()
