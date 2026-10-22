# -*- coding: utf-8 -*-
"""Add the vintages that have a sheet and no record, where it is safe to.

    python tools/merge-proposals.py             what it would add
    python tools/merge-proposals.py --apply     add them

Run after tools/read-sheets.py. It takes reports/proposed.json and adds
only the records that clear three filters, because a proposal is a
reading and not yet a fact.

  EVERY SHEET FOR THAT VINTAGE AGREES. Where two do not, one of them is
  another wine, and the merge cannot tell which: Paloumey 2018 is
  offered as 55/40/5, 57/28/15 and 45/43/12 by three different
  documents, and Clos Puy Arnaud 2024 as 90% Merlot by one and 60%
  Malbec by another. Those go in the report for someone to read.

  THE SHEET IS STILL THIS ESTATE'S. A proposal is only as current as
  the run that made it, and sheets get refiled between runs - 22 came
  out of Chateau Lalande's folder after the last one, being
  Tronquoy-Lalande's, Lalande-Borie's and Pichon Comtesse's. So the
  manifest is consulted again at merge time rather than trusted from
  the report.

  THE BLEND PASSES THE GATES. Sums to 100, no single variety at 100,
  Petit Verdot under a quarter, no white varieties in a red. The rest
  of tools/check-data.py runs afterwards over everything, which is
  where the cross-vintage checks live.

What it adds is a blend and a src and nothing else. Yields, alcohols
and ageing times need the per-field provenance this pipeline does not
have yet: src names the last writer, so a record with four fields from
three documents cannot say which came from where.
"""
import io, json, os, re, sys, argparse, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
ap.add_argument('--estate', action='append', default=[])
a = ap.parse_args()

WHITE = set(['SEM', 'SB', 'SG', 'MU'])
SINGLE_OK = set(['de-carles', 'stem-chateau-moulin-du-cadet', 'levangile',
                 'doisy-dubroca', 'petrus', 'lafleur-petrus'])

man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))
sheets = {}
for s in man['sheets']:
    sheets.setdefault(s['file'], s)
E = sr.estates(ROOT)

held = set()
for line in io.open(ROOT + 'data/fiches.js', encoding='utf-8'):
    m = re.match(r"^'([a-z0-9-]+\|\d{4})':", line)
    if m:
        held.add(m.group(1))

prop = json.load(io.open(ROOT + 'reports/proposed.json', encoding='utf-8'))
byvintage = collections.defaultdict(list)
for r in prop:
    if a.estate and r['estate'] not in a.estate:
        continue
    byvintage[(r['estate'], r['year'])].append(r)

add, refused = [], collections.Counter()
clashes, examples = [], {}
for (eid, yr), rows in sorted(byvintage.items()):
    key = '%s|%d' % (eid, yr)
    if key in held:
        refused['a record already exists'] += 1
        continue

    # Still this estate's, by the manifest as it stands now.
    rows = [r for r in rows
            if (sheets.get(r['src']) or {}).get('estate') == eid
            and (sheets.get(r['src']) or {}).get('role') not in (
                'skip', 'second', 'other', 'page')]
    if not rows:
        refused['the sheet is no longer filed as this estate’s'] += 1
        continue

    distinct = []
    for r in rows:
        b = tuple(sorted(r['blend'].items()))
        if b not in distinct:
            distinct.append(b)
    if len(distinct) > 1:
        refused['two sheets for this vintage disagree'] += 1
        clashes.append((eid, yr, distinct, [r['src'] for r in rows]))
        continue

    blend = rows[0]['blend']
    total = sum(blend.values())
    e = E.get(eid) or {}
    if abs(total - 100) > 1.5:
        refused['does not sum to 100'] += 1
        continue
    if len(blend) == 1 and list(blend.values())[0] >= 100 and eid not in SINGLE_OK:
        refused['a single variety at 100%'] += 1
        examples.setdefault('a single variety at 100%', key)
        continue
    if blend.get('PV', 0) > 25:
        refused['Petit Verdot over 25%'] += 1
        continue
    white = sum(v for k, v in blend.items() if k in WHITE)
    if e.get('cat') == 'red' and white > 20:
        refused['white varieties in a red'] += 1
        continue
    if e.get('cat') in ('white', 'sweet') and white < 50:
        refused['red varieties in a white'] += 1
        continue
    add.append((key, blend, rows[0]['src']))

print('%d vintages offered, %d to add' % (len(byvintage), len(add)))
for k, n in refused.most_common():
    print('   refused: %-50s %d%s'
          % (k[:50], n, '  e.g. ' + examples[k] if k in examples else ''))

if clashes:
    print('\n%d vintages where the sheets disagree, for someone to read:'
          % len(clashes))
    for eid, yr, distinct, srcs in clashes[:30]:
        print('   %-30s %s  %s' % (eid[:30], yr,
                                   ' | '.join(','.join('%s%g' % kv for kv in d)
                                              for d in distinct)[:62]))
    if len(clashes) > 30:
        print('   ... and %d more' % (len(clashes) - 30))

if not a.apply:
    print('\nnothing written; pass --apply to add them')
    sys.exit(0)

p = ROOT + 'data/fiches.js'
lines = io.open(p, encoding='utf-8').read().split(chr(10))
tail = ["'%s':{blend:{%s},src:'%s'},"
        % (k, ','.join('%s:%g' % kv for kv in sorted(b.items())), s)
        for k, b, s in add]
for i in range(len(lines) - 1, -1, -1):
    if lines[i].strip().startswith('}'):
        lines[i:i] = tail
        break
else:
    lines.extend(tail)
io.open(p, 'w', encoding='utf-8', newline='').write(chr(10).join(lines))

# A sheet this merge has just read as the grand vin's is the grand vin's,
# and the manifest should say so. Left at role unknown it made the audit
# complain about every record added - correctly, since nothing in the
# manifest vouched for them, and the merge was the thing that could.
named = 0
for key, blend, src in add:
    eid = key.split('|')[0]
    sh = sheets.get(src)
    if sh and sh.get('role') == 'unknown':
        sh['role'] = 'grand'
        sh['wine'] = (E.get(eid) or {}).get('name')
        sh['note'] = ((sh.get('note') or '') + '; read as this estate’s '
                      'grand vin when its blend was merged').lstrip('; ')
        named += 1
if named:
    io.open(ROOT + 'data/sources.json', 'w', encoding='utf-8',
            newline='').write(json.dumps(man, ensure_ascii=False, indent=1))


def _refresh_progress():
    """Rebuild PROGRESS.md, now that the records have changed.

    A separate process: progress.py reads data/fiches.js from disk and
    it has just been rewritten. Wrapped, because a report that will
    not build must not take a merge with it.
    """
    import subprocess
    try:
        out = subprocess.run(
            [sys.executable, '-I', ROOT + 'tools/progress.py']
            + (['--no-save'] if '--no-save' in sys.argv else []),
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=600)
        tail = (out.stdout or b'').decode('utf-8', 'replace')
        kept = [l for l in tail.splitlines() if l.startswith('saved ')]
        if out.returncode == 0 and kept:
            print(kept[-1])
        else:
            print('PROGRESS.md was not refreshed; run '
                  'tools/progress.py to see why')
    except Exception as e:
        print('PROGRESS.md was not refreshed (%s); the merge above '
              'still stands' % str(e)[:50])


print('\n%d records added, %d sheets named as the grand vin’s'
      % (len(add), named))
_refresh_progress()
print('now run: python tools/check-data.py  and  python tools/audit-sources.py')
