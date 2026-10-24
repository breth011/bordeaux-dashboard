# -*- coding: utf-8 -*-
"""For every downloaded document, where did it end up?

    python tools/reconcile.py                   the whole archive
    python tools/reconcile.py --estate lafite   one estate, in detail
    python tools/reconcile.py --gaps            the ranked gap list
    python tools/reconcile.py --orphans 40      documents nothing cites

The dataset is a working hypothesis and the archive is the evidence.
This asks the archive what the dataset should look like, and reports
where the two disagree - WITHOUT changing anything. Nothing here
writes.

It answers two questions in both directions:

    for every downloaded document, which record does it support?
    for every record, which documents support it?

and then sorts the disagreements into kinds, because "missing" covers
at least ten different situations and only some of them are missing:

    the document was never downloaded
    it was downloaded and nothing cites it          (ORPHAN)
    it is cited, but by a record for another year   (YEAR CONFLICT)
    it is cited, but by another estate's record     (ESTATE CONFLICT)
    the same bytes are filed twice                  (DUPLICATE)
    a record cites a document not in the manifest   (UNSUPPORTED)
    a record cites a document not on disk           (MISSING FILE)
    the estate published nothing that year          (LEGITIMATE)

                         WHAT COUNTS AS EVIDENCE

Three independent signals per document, deliberately not the one the
manifest already believes:

  the FILENAME        what year and whose name it spells
  the URL             what year and whose site it came from
  the MANIFEST        what we decided it was

and for the dataset side, `field-src.js` and `cuvee-src.js`, which
name one document per field per record. That is the only place the
archive and the dataset actually touch, and it is what makes the
bidirectional question answerable at all.

Document CONTENTS are not read here. That is deliberate: this pass is
metadata-only so it runs over 13,000 documents in seconds and can be
run after every merge. Reading the documents is the next pass, and it
should be aimed by this one rather than replacing it.

                            RANKING GAPS

A gap is more suspicious when the estate has the years either side,
the same sheet family covers them, and an unmapped document exists
for the missing year. Those three together are what the ranking adds
up; a gap with none of them is probably an estate that published
nothing, and saying so is as useful as finding one that did.
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

YEAR_IN = re.compile(r'(?<!\d)((?:1[89]|20)\d\d)(?!\d)')


def family(fn):
    """The filename with its numbers out: one estate's sheet, any year."""
    s = os.path.splitext(str(fn or ''))[0].lower()
    s = re.sub(r'(?:19|20)\d\d', '####', s)
    s = re.sub(r'\d+', '#', s)
    return re.sub(r'[\s_]+', '-', s).strip('-') or '?'


def years_in(s):
    """Every four-digit year a string spells, as ints."""
    return set(int(y) for y in YEAR_IN.findall(str(s or ''))
               if 1800 < int(y) < 2100)


def load_manifest():
    p = ROOT + 'data/sources.json'
    man = json.load(io.open(p, encoding='utf-8'))
    return man.get('sheets', [])


def load_records():
    """Every record, and every document any of its fields came from."""
    recs = {}
    for name, nkey in (('fiches.js', 2), ('cuvees.js', 3)):
        p = ROOT + 'data/' + name
        if not os.path.exists(p):
            continue
        pat = re.compile(r"^'([a-z0-9-]+)\|" +
                         (r"([a-z0-9-]+)\|" if nkey == 3 else '') +
                         r"(\d{4})':\{(.*)\},$")
        for line in io.open(p, encoding='utf-8'):
            m = pat.match(line.rstrip())
            if not m:
                continue
            key = '|'.join(m.group(i + 1) for i in range(nkey))
            body = m.group(nkey + 1)
            src = re.search(r"src:'([^']*)'", body)
            recs[key] = {
                'estate': m.group(1),
                'year': int(m.group(nkey)),
                'cites': set([src.group(1)] if src else []),
                'fields': set(re.findall(r'(?:^|\{|,)([a-z][a-z0-9]*):',
                                         body)),
            }
    # Per-field provenance: the real archive-to-dataset edges.
    for name in ('field-src.js', 'cuvee-src.js'):
        p = ROOT + 'data/' + name
        if not os.path.exists(p):
            continue
        for line in io.open(p, encoding='utf-8'):
            m = re.match(r"^'([^']+)':\{(.*)\},$", line.rstrip())
            if not m or m.group(1) not in recs:
                continue
            for f, v in re.findall(r"([a-z]+):'([^']*)'", m.group(2)):
                recs[m.group(1)]['cites'].add(v)
    return recs


def on_disk():
    seen = {}
    d = ROOT + 'sources'
    if not os.path.isdir(d):
        return seen
    for root, dirs, files in os.walk(d):
        for f in files:
            seen.setdefault(f, os.path.join(root, f))
    return seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estate')
    ap.add_argument('--gaps', action='store_true')
    ap.add_argument('--orphans', type=int, default=0)
    ap.add_argument('--limit', type=int, default=20)
    a = ap.parse_args()

    sheets = load_manifest()
    recs = load_records()
    disk = on_disk()

    if a.estate:
        sheets = [s for s in sheets if s.get('estate') == a.estate]
        recs = dict((k, v) for k, v in recs.items()
                    if v['estate'] == a.estate)

    # ---------------------------------------------- the archive side
    cited = collections.defaultdict(set)      # filename -> record keys
    for k, r in recs.items():
        for fn in r['cites']:
            if fn:
                cited[fn].add(k)

    by_hash = collections.defaultdict(list)
    orphans, year_conflict, estate_conflict, absent_file = [], [], [], []
    est_years = collections.defaultdict(set)   # estate -> years with a doc
    fam_years = collections.defaultdict(set)   # (estate, family) -> years
    doc_for = collections.defaultdict(list)    # (estate, year) -> files

    for s in sheets:
        fn, eid = s.get('file'), s.get('estate')
        if not fn:
            continue
        if s.get('sha1'):
            by_hash[s['sha1']].append(s)
        here = cited.get(fn) or set()
        myr = s.get('year')
        try:
            myr = int(myr) if myr else None
        except Exception:
            myr = None
        if eid and myr:
            est_years[eid].add(myr)
            fam_years[(eid, family(fn))].add(myr)
            doc_for[(eid, myr)].append(fn)
        if fn not in disk:
            absent_file.append((eid, fn))
        if not here:
            orphans.append((eid, myr, fn, s.get('role') or '?',
                            s.get('wine') or ''))
            continue
        # Cited - but by a record for which year, and whose?
        fy = years_in(fn) | years_in(s.get('url'))
        for k in here:
            r = recs[k]
            if fy and r['year'] not in fy and myr and myr not in fy:
                year_conflict.append((k, fn, sorted(fy), r['year']))
            if eid and r['estate'] != eid:
                estate_conflict.append((k, fn, eid, r['estate']))

    # --------------------------------------------- the dataset side
    unsupported, thin = [], []
    man_files = set(s.get('file') for s in sheets if s.get('file'))
    for k, r in sorted(recs.items()):
        real = set(f for f in r['cites'] if f)
        if not real:
            unsupported.append((k, 'cites no document at all'))
            continue
        if not (real & man_files):
            unsupported.append((k, 'cites %d document(s), none in the '
                                'manifest' % len(real)))
        elif not (real & set(disk)):
            unsupported.append((k, 'cites %d document(s), none on disk'
                                % len(real)))

    dups = [(h, v) for h, v in by_hash.items() if len(v) > 1]
    dup_cross = [(h, v) for h, v in dups
                 if len(set((x.get('estate'), x.get('wine'),
                             x.get('year')) for x in v)) > 1]

    # -------------------------------------------------------- report
    print('=' * 72)
    print('RECONCILIATION%s' % (' - ' + a.estate if a.estate else ''))
    print('=' * 72)
    print()
    print('SOURCE ARTIFACTS')
    print('-' * 24)
    print('   %-34s %d' % ('in the manifest', len(sheets)))
    print('   %-34s %d' % ('present on disk',
                           sum(1 for s in sheets
                               if s.get('file') in disk)))
    print('   %-34s %d' % ('cited by at least one record',
                           len(sheets) - len(orphans)))
    print('   %-34s %d' % ('cited by nothing (ORPHAN)', len(orphans)))
    print('   %-34s %d' % ('named but not on disk', len(absent_file)))
    print('   %-34s %d  (%d across different wines)'
          % ('identical bytes, filed twice', len(dups), len(dup_cross)))
    print()
    print('DATASET RECORDS')
    print('-' * 24)
    print('   %-34s %d' % ('total', len(recs)))
    print('   %-34s %d' % ('supported by a manifest document',
                           len(recs) - len(unsupported)))
    print('   %-34s %d' % ('weakly or not supported', len(unsupported)))
    print()
    print('IDENTITY CONFLICTS')
    print('-' * 24)
    print('   %-34s %d' % ('document year vs record year',
                           len(year_conflict)))
    print('   %-34s %d' % ('document estate vs record estate',
                           len(estate_conflict)))

    # ------------------------------------------------- ranked gaps
    gaps = []
    for eid, years in est_years.items():
        have = set(r['year'] for r in recs.values()
                   if r['estate'] == eid)
        if not have:
            continue
        lo, hi = min(have), max(have)
        for y in sorted(years):
            if y in have or not (lo <= y <= hi):
                continue
            score, why = 0, []
            if (y - 1) in have and (y + 1) in have:
                score += 3
                why.append('%d and %d are on record' % (y - 1, y + 1))
            elif (y - 1) in have or (y + 1) in have:
                score += 1
                why.append('a neighbouring vintage is on record')
            fams = [f for (e, f), ys in fam_years.items()
                    if e == eid and y in ys
                    and len(ys & have) >= 2]
            if fams:
                score += 3
                why.append('the same sheet family covers %d other '
                           'vintage(s) that ARE on record'
                           % len(fam_years[(eid, fams[0])] & have))
            files = doc_for.get((eid, y)) or []
            un = [f for f in files if f not in cited]
            if un:
                score += 4
                why.append('%d document(s) for %d that nothing cites: %s'
                           % (len(un), y, ', '.join(un[:2])))
            gaps.append((score, eid, y, why, files))
    gaps.sort(key=lambda g: (-g[0], g[1], g[2]))

    print()
    print('GAPS - a document is filed for the year and no record exists')
    print('-' * 24)
    print('   %-34s %d' % ('total', len(gaps)))
    for band, lo, hi in (('HIGH   (evidence in the archive)', 7, 99),
                         ('MEDIUM (neighbours and a family)', 3, 6),
                         ('LOW    (little to go on)', 0, 2)):
        n = sum(1 for g in gaps if lo <= g[0] <= hi)
        print('   %-34s %d' % (band, n))

    if a.gaps or a.estate:
        print()
        print('=' * 72)
        print('RANKED GAPS')
        print('=' * 72)
        for score, eid, y, why, files in gaps[:a.limit if not a.estate
                                              else 60]:
            print()
            print('   %s %s   priority %s'
                  % (eid, y, 'HIGH' if score >= 7
                     else 'MEDIUM' if score >= 3 else 'LOW'))
            for w in why:
                print('      - ' + w)
            if not why:
                print('      - nothing beside it; probably no fiche '
                      'published')

    if a.orphans:
        print()
        print('=' * 72)
        print('ORPHANS - downloaded, cited by no record')
        print('=' * 72)
        byest = collections.Counter(o[0] for o in orphans)
        for eid, n in byest.most_common(a.orphans):
            print('   %-30s %d' % (eid or '(no estate)', n))

    if a.estate:
        if orphans:
            print()
            print('ORPHANS at this estate:')
            for eid, yr, fn, role, wine in orphans[:40]:
                print('   %-56s %s %s' % (fn[:56], yr or '----',
                                          (wine or role)[:18]))
        if unsupported:
            print()
            print('RECORDS WITH WEAK SUPPORT:')
            for k, why in unsupported[:20]:
                print('   %-28s %s' % (k, why))

    if year_conflict:
        print()
        print('=' * 72)
        print('YEAR CONFLICTS - the document spells a year the record '
              'does not')
        print('=' * 72)
        for k, fn, fy, ry in year_conflict[:a.limit]:
            print('   %-26s record %s   document says %s'
                  % (k, ry, ','.join(str(x) for x in fy)))
            print('      %s' % fn[:66])
        if len(year_conflict) > a.limit:
            print('   ... and %d more' % (len(year_conflict) - a.limit))

        # A systematic offset is worth more than any single case.
        off = collections.Counter()
        for k, fn, fy, ry in year_conflict:
            for y in fy:
                off[y - ry] += 1
        print()
        print('   the offsets, which is where a systematic bug would '
              'show:')
        for d, n in off.most_common(6):
            print('      document year minus record year = %+d   %d case(s)'
                  % (d, n))

    print()
    print('Nothing was written. This pass reads metadata only - the '
          'manifest, the\nprovenance files and the filenames - so it '
          'can run after every merge.')


if __name__ == '__main__':
    main()
