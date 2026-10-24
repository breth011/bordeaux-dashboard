# -*- coding: utf-8 -*-
"""File an estate's documents under the wine the guards say they are.

    python tools/refile-wine.py --estate margaux
    python tools/refile-wine.py --estate margaux --apply
    python tools/refile-wine.py --estate margaux --wine "Pavillon Rouge"

A wine's pages sit in the manifest filed `page` or `unknown`, which
means nobody has judged which wine they are for. The cuvee reader
takes rows filed `second` or `other` with a wine named on them, so
those pages are offered to no reader at all: Margaux has 48 Pavillon
Rouge pages and 56 Pavillon Blanc pages and not one record for either
wine.

whose_sheet already knows. Asked at full depth it answers "the sheet
names another of the estate's wines: Pavillon Blanc du Chateau
Margaux", with the role and the wine in the verdict. The manifest
role is documented as a cache of what the guards said, so this writes
that cache.

WHY THIS IS NOT tools/refile.py

refile.py reads the filename against every name the dashboard knows
and moves the sheet to the longest match. Its --apply is switched off,
and its docstring says why: turned on once it moved 218 sheets and
took the audit from 4 complaints to 79, two of them a grand vin's own
sheet relabelled as its second wine's.

This differs in three ways that matter:

  it asks the guard chain, not a filename. The verdict comes from
  whose_sheet, which opens the document and has thirteen tests in a
  fixed order, and it is the same verdict that would refuse the
  document if a reader were pointed at it.

  it will not invent a wine. A verdict naming a wine that is not in
  BDX_CUVEE_WINES is reported and skipped, because a wine in that list
  is shown in the drawer as the estate's and belongs there by a
  reviewed edit.

  it never touches a row already judged. Only `page` and `unknown` are
  candidates - the roles that mean nobody has looked. A row filed
  grand, second, other or skip is somebody's decision and is left.

A document the guards cannot place stays where it is, which is the
behaviour that makes this safe to run estate by estate.
"""
import io, json, os, re, shutil, sys, argparse, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
MAN = ROOT + 'data/sources.json'


def listed_wines(eid):
    """The estate's wines as cuvees.js has them, which is the authority."""
    p = ROOT + 'data/cuvees.js'
    if not os.path.exists(p):
        return []
    body = io.open(p, encoding='utf-8').read()
    body = body.split('window.BDX_CUVEE_WINES', 1)[-1].split(
        'window.BDX_CUVEES', 1)[0]
    m = re.search(r"(?m)^'" + re.escape(eid) + r"':\[(.*)\],$", body)
    if not m:
        return []
    out = []
    for w in re.finditer(r"\{slug:'((?:[^'\\]|\\.)*)',name:'"
                         r"((?:[^'\\]|\\.)*)',role:'([a-z]*)',"
                         r"colour:'([a-z]*)'\}", m.group(1)):
        out.append({'slug': w.group(1),
                    'name': w.group(2).replace("\\'", "'"),
                    'role': w.group(3), 'colour': w.group(4)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estate', action='append', default=[], required=True)
    ap.add_argument('--wine', action='append', default=[],
                    help='only these wines, matched loosely; '
                         'default is every wine the list holds')
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()

    man = json.load(io.open(MAN, encoding='utf-8'))
    E = sr.estates(ROOT)

    where = {}
    for root, dirs, files in os.walk(ROOT + 'sources'):
        for f in files:
            where.setdefault(f, os.path.join(root, f))

    total, skipped = [], collections.Counter()
    for eid in a.estate:
        e = E.get(eid) or {}
        wines = listed_wines(eid)
        by_packed = dict((sr.packed(w['name']), w) for w in wines)
        want = [sr.packed(x) for x in a.wine]

        print('=' * 70)
        print('%s - %s' % (eid, e.get('name')))
        print('=' * 70)
        if not wines:
            print('no wine listed in cuvees.js; nothing can be filed '
                  'until one is')
            continue
        for w in wines:
            print('   listed: %-38s %-7s %s'
                  % (w['name'][:38], w['role'], w['colour']))

        rows = [s for s in man['sheets']
                if s.get('estate') == eid
                and s.get('role') in ('page', 'unknown')]
        print('\n%d row(s) filed page or unknown' % len(rows))

        change, why = [], collections.Counter()
        for s in rows:
            p = where.get(s['file'])
            if not p:
                why['the document is not on disk'] += 1
                continue
            try:
                v = sr.whose_sheet(p, s['file'], e.get('name'),
                                   list(e.get('cuvees') or ()),
                                   e.get('second'), e.get('cat'),
                                   s.get('year'))
            except Exception as ex:
                why['a guard could not read it: %s' % str(ex)[:30]] += 1
                continue
            if not v:
                why["still the estate's own"] += 1
                continue
            why[v['why'][:54]] += 1
            if v.get('role') not in ('second', 'other') or not v.get('wine'):
                continue
            hit = by_packed.get(sr.packed(v['wine']))
            if not hit:
                skipped['%s: %s' % (eid, v['wine'][:40])] += 1
                continue
            if want and sr.packed(hit['name']) not in want \
                    and not any(x in sr.packed(hit['name']) for x in want):
                continue
            if not s.get('year'):
                why['no vintage on the row, so no record to make'] += 1
                continue
            change.append((s, hit))

        print('\nwhat the guards said:')
        for k, n in why.most_common():
            print('   %-56s %d' % (k, n))

        byw = collections.Counter(h['name'] for s, h in change)
        print('\n%d row(s) to file:' % len(change))
        for nm, n in byw.most_common():
            yrs = sorted(set(s.get('year') for s, h in change
                             if h['name'] == nm))
            print('   %-38s %3d  %s-%s'
                  % (nm[:38], n, yrs[0], yrs[-1]))
        total += change

    if skipped:
        print('\nverdicts naming a wine the list does not hold, skipped:')
        for k, n in skipped.most_common():
            print('   %-58s %d' % (k, n))
        print('   add it to BDX_CUVEE_WINES first if it is really '
              'the estate’s')

    if not a.apply:
        print('\nnothing written; pass --apply to file %d row(s)'
              % len(total))
        return 0
    if not total:
        print('\nnothing to file')
        return 0
    shutil.copy(MAN, MAN + '.bak')
    for s, h in total:
        s['role'] = h['role']
        s['wine'] = h['name']
        s['colour'] = h['colour']
    io.open(MAN, 'w', encoding='utf-8', newline='').write(
        json.dumps(man, ensure_ascii=False, indent=1))
    print('\n%d row(s) filed; sources.json.bak holds the previous file'
          % len(total))
    print('now run: python tools/read-fiches.py --cuvees --estate <id> '
          '--prose --apply')
    print('then:    python tools/audit-sources.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())
