# -*- coding: utf-8 -*-
"""The 56 wine-identity cases, with the reasoning shown.

    python tools/wine-identity.py
    python tools/wine-identity.py --write   data/wine-identity.jsonl
    python tools/wine-identity.py --estate lynch-bages

Writes one file. The manifest is not touched and nothing is
reassigned; each row says what the manifest claims, what the document
shows, and what follows - separately.

                    WHY A NAIVE TEST IS DANGEROUS

Phase 1 reached this number three times and was wrong twice.

"The filename names a different listed wine" gives 122 cases, and the
extra 66 are false. `2010-Opalie-de-ChateauCoutet.pdf` is filed as
`Opalie de Chateau Coutet Blanc`, which is correct; the filename just
omits the word "Blanc", so `says()` matches only the shorter
`Chateau Coutet` and the test cries foul at a manifest that is right.

Requiring the two names to be DISJOINT gives 3 cases, and now 53 are
missed - because treating "blanc" as a generic qualifier discards the
one word that separates `Blanc de Lynch-Bages` from `Echo de
Lynch-Bages`. The qualifier is the identity.

What holds is SUBSET. A longer spelling of the same wine contains the
shorter one as a word-set; a different wine does not.

    Chateau Coutet            {coutet}
    Opalie de Chateau Coutet Blanc  {opalie, coutet, blanc}
      -> {coutet} is a subset: the same wine, spelled longer. No case.

    Echo de Lynch-Bages       {echo, lynch, bages}
    Blanc de Lynch-Bages      {blanc, lynch, bages}
      -> neither contains the other: different wines. A case.

Only the house words are stripped - chateau, clos, domaine and the
articles. Colour words are NOT stripped, and that is the whole lesson.

Each row records which rule fired and on what, so the reasoning can
be argued with rather than trusted.
"""
import argparse
import collections
import datetime
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr

TOOL_VERSION = 1
OUT = ROOT + 'data/wine-identity.jsonl'
CENSUS = ROOT + 'data/artifact-census.jsonl'

# The house words and articles only. NOT blanc, rouge, reserve or any
# other qualifier: see the docstring.
HOUSE = set('chateau clos domaine la le les de du des l d'.split())


def mark(nm):
    return set(w for w in re.split(r'[^a-z0-9]+', sr.norm(nm or ''))
               if w and w not in HOUSE)


def wines_of(e):
    out = []
    if e.get('name'):
        out.append(('grand', e['name']))
    if e.get('second'):
        out.append(('second', e['second']))
    for c in (e.get('cuvees') or ()):
        out.append(('other', c))
    return out


def commit():
    try:
        return subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT,
            stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--estate')
    ap.add_argument('--limit', type=int, default=12)
    a = ap.parse_args()

    E = sr.estates(ROOT)
    man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))

    # What the documents were observed to say, from Phase 1.
    obs = {}
    if os.path.exists(CENSUS):
        with io.open(CENSUS, encoding='utf-8') as f:
            f.readline()
            for line in f:
                d = json.loads(line)
                obs[d['path'].split('/')[-1]] = d

    rows = []
    for s in man.get('sheets', []):
        eid, fn, mw = s.get('estate'), s.get('file'), s.get('wine')
        if not (eid and fn and mw):
            continue
        if a.estate and eid != a.estate:
            continue
        e = E.get(eid) or {}
        ws = wines_of(e)
        if mw not in [nm for _r, nm in ws]:
            continue
        # The longest name the filename spells, so a specific cuvee
        # beats the estate's own name sitting inside it.
        named, role = None, None
        for r, nm in sorted(ws, key=lambda w: -len(w[1])):
            if sr.says(fn, nm):
                named, role = nm, r
                break
        if not named or named == mw:
            continue
        a_set, b_set = mark(named), mark(mw)
        if not a_set or not b_set:
            continue
        if a_set <= b_set:
            continue          # a shorter spelling of the manifest wine
        if b_set <= a_set:
            continue          # a longer spelling of it
        # A real disagreement.
        o = obs.get(fn) or {}
        doc_wines = [w for w in (o.get('o', {}).get('wine') or [])
                     if w != 'UNKNOWN']
        # The estate's OWN name inside a cuvee's sheet is the house,
        # not a second wine: every Echo de Lynch-Bages sheet carries
        # "Chateau Lynch-Bages 33250 Pauillac" in its footer. Counting
        # it as a wine made all 50 look like multi-wine documents.
        #
        # Kept as evidence rather than discarded, because on a sheet
        # that really does cover two wines the house name is also
        # there and the distinction is then doing real work.
        house = e.get('name')
        cuvees_named = [w for w in doc_wines if w != house]
        names_house = bool(house and house in doc_wines)
        multi = len(cuvees_named) > 1
        doc_wines = cuvees_named or doc_wines
        if multi:
            state = 'MULTI_WINE_DOCUMENT'
            why = ('the document names %d of the estate\'s wines (%s), '
                   'so no single attribution is right'
                   % (len(doc_wines), ', '.join(doc_wines[:3])))
        elif doc_wines and doc_wines[0] == named:
            state = 'MANIFEST_METADATA_WRONG'
            why = ('both the filename and the document text name %r; '
                   'the manifest says %r' % (named, mw))
        elif doc_wines and doc_wines[0] == mw:
            state = 'FILENAME_MISLEADING'
            why = ('the document text agrees with the manifest (%r); '
                   'only the filename names %r' % (mw, named))
        else:
            state = 'UNRESOLVED'
            why = ('the filename names %r and the manifest says %r; '
                   'the document settles neither' % (named, mw))
        rows.append({
            'artifact': fn,
            'manifest': {'estate': eid, 'wine': mw,
                         'vintage': s.get('year'), 'role': s.get('role')},
            'observed': {
                'wine_from_filename': named,
                'wine_role': role,
                'wine_from_text': doc_wines or ['UNKNOWN'],
                'also_names_the_estate': names_house,
                'vintage': (o.get('o', {}) or {}).get('vintage',
                                                      'UNKNOWN'),
                'document_type': (o.get('o', {}) or {}).get('type'),
            },
            'rule': {
                'test': 'subset',
                'filename_words': sorted(a_set),
                'manifest_words': sorted(b_set),
                'neither_contains_the_other': True,
            },
            'url': s.get('url'),
            'state': state,
            'why': why,
            'confidence': ('HIGH' if state in ('MANIFEST_METADATA_WRONG',
                                               'FILENAME_MISLEADING')
                           else 'MEDIUM' if multi else 'LOW'),
            'v': TOOL_VERSION,
            'at': datetime.date.today().isoformat(),
            'commit': commit(),
        })

    print('%d wine-identity case(s), by the subset test\n' % len(rows))
    print('%-28s %6s  %s' % ('STATE', 'n', 'confidence'))
    print('-' * 56)
    for k, c in collections.Counter(r['state'] for r in rows).most_common():
        cf = collections.Counter(r['confidence'] for r in rows
                                 if r['state'] == k)
        print('   %-26s %5d  %s'
              % (k, c, ', '.join('%s %d' % kv for kv in cf.most_common())))
    print()
    print('BY ESTATE')
    print('-' * 56)
    for k, c in collections.Counter(
            r['manifest']['estate'] for r in rows).most_common():
        wines = collections.Counter(
            '%s -> %s' % (r['manifest']['wine'],
                          r['observed']['wine_from_filename'])
            for r in rows if r['manifest']['estate'] == k)
        print('   %-28s %4d' % (k[:28], c))
        for w, n in wines.most_common(3):
            print('      %-46s %d' % (w[:46], n))

    print()
    print('EXAMPLES')
    print('-' * 56)
    for r in rows[:a.limit]:
        print('   %-44s %s' % (r['artifact'][:44], r['state']))
        print('      %s' % r['why'][:72])

    if a.write:
        with io.open(OUT, 'w', encoding='utf-8', newline='') as f:
            f.write(json.dumps({
                '_': 'Wine-identity disagreements between the manifest '
                     'and the documents. Nothing is reassigned; the '
                     'manifest is unchanged. The test is subset, not '
                     'difference - see tools/wine-identity.py.',
                'tool_version': TOOL_VERSION, 'rows': len(rows),
            }, ensure_ascii=False, sort_keys=True) + '\n')
            for r in sorted(rows, key=lambda x: x['artifact']):
                f.write(json.dumps(r, ensure_ascii=False,
                                   sort_keys=True) + '\n')
        print('\nwritten to data/wine-identity.jsonl (%d)' % len(rows))
    else:
        print('\nnothing written; pass --write')


if __name__ == '__main__':
    main()
