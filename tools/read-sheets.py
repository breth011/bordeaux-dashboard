# -*- coding: utf-8 -*-
"""Read the sheets nothing has read yet, and propose what they say.

    python tools/read-sheets.py                 propose, write the report
    python tools/read-sheets.py --year 2026     only that vintage
    python tools/read-sheets.py --apply         write them into fiches.js

It proposes; it does not merge until told to. The report goes to
reports/proposed.txt and is meant to be read, because every error this
pipeline has made was plausible on the face of it and obvious in the
document.

What it refuses, before any blend is taken:

  a press dossier      one document per property, not per vintage.
  a second wine        the sheet that says so about itself.
  a wine that is not   the sheet names a property this dashboard does
  in the dashboard     not hold, so it goes nowhere.

and then what it proposes has to pass the gates in tools/check-data.py,
which is run again at the end over everything rather than over the
batch - because the batch check is what let Chateau Margaux sit at 87%
Merlot for a month.
"""
import io, json, os, re, sys, argparse, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr

# Records the reader must not overwrite, because the estate's own sheet
# is wrong and the record holds the corrected reading. Each entry needs
# the sentence from the sheet and the reason it cannot be right.
#
# La Mission Haut-Brion 2024 reads, on the estate's own English sheet:
# "Blend Cabernet Franc: 51%; Merlot: 46.5% Cabernet Sauvignon: 2.5%".
# La Mission is a Cabernet Sauvignon estate - around half the blend
# every year, with Cabernet Franc a few per cent - so the two Cabernets
# have been swapped in the typesetting. The figures are right and the
# labels are not.
PINNED = {
    'la-mission-haut-brion|2024':
        'the sheet gives Cabernet Franc 51% and Cabernet Sauvignon 2.5%, '
        'which is the two Cabernets swapped: La Mission is roughly half '
        'Cabernet Sauvignon and a few per cent Franc',
}

ap = argparse.ArgumentParser()
ap.add_argument('--year', type=int)
ap.add_argument('--estate', action='append', default=[])
ap.add_argument('--apply', action='store_true')
ap.add_argument('--limit', type=int, default=0)
a = ap.parse_args()

man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))
have, held = set(), {}
for line in io.open(ROOT + 'data/fiches.js', encoding='utf-8'):
    m = re.match(r"^'([a-z0-9-]+\|\d{4})':\{(.*)\},$", line.rstrip())
    if not m:
        continue
    have.add(m.group(1))
    b = re.search(r'blend:\{([^}]*)\}', m.group(2))
    if b:
        held[m.group(1)] = dict((k, float(v)) for k, v in
                                re.findall(r'(\w+):([\d.]+)', b.group(1)))

known, grand, second = set(), {}, {}
for f in ('chateaux.js', 'crubourgeois.js', 'cruartisan.js', 'graves.js',
          'sauternes.js', 'saintemilion.js', 'pomerol.js', 'rightbank.js',
          'libournais.js'):
    q = ROOT + 'data/' + f
    if not os.path.exists(q):
        continue
    txt = io.open(q, encoding='utf-8').read()
    known |= set(re.findall(r"id:'([a-z0-9-]+)'", txt))
    # Each estate's own block, so the name and the second wine stay together.
    for blk in re.finditer(r"\{id:'([a-z0-9-]+)'(.{0,900}?)\}(?=,\s*$|,\s*\{)",
                           txt, re.S | re.M):
        eid, body = blk.group(1), blk.group(2)
        nm = re.search(r"name:'([^']+)'", body)
        sc = re.search(r"second:'([^']+)'", body)
        if nm:
            grand.setdefault(eid, nm.group(1))
        if sc:
            second.setdefault(eid, sc.group(1))

# Every other wine the estate makes, so a sheet for one of them is not
# read as the grand vin's. D de Dauzac is a white Bordeaux; the Giscours
# Carnet Primeurs carries La Sirene's blend beside Giscours' own.
others = collections.defaultdict(list)
cv = ROOT + 'data/cuvees.js'
if os.path.exists(cv):
    txt = io.open(cv, encoding='utf-8').read()
    for m in re.finditer(r"^'([a-z0-9-]+)':\[(.*)\],?$", txt, re.M):
        for nm in re.findall(r"name:'([^']+)'", m.group(2)):
            others[m.group(1)].append(nm)
for eid, nm in second.items():
    if nm not in others[eid]:
        others[eid].append(nm)

# A role this tool set on an earlier run is never un-set by a later one,
# so a role set by a rule that was later found wrong stays wrong. Those
# sheets are re-read and reported rather than silently flipped back: the
# manifest is the record, and something that writes it both ways without
# saying so is not a record.
recheck = []
todo = []
for s in man['sheets']:
    if s.get('role') in ('second', 'other') and s.get('estate'):
        recheck.append(s)
    if s.get('role') in ('skip', 'second', 'other', 'page'):
        continue
    if not s.get('estate') or s['estate'] not in known:
        continue
    if a.estate and s['estate'] not in a.estate:
        continue
    if a.year and s.get('year') != a.year:
        continue
    if not s.get('year'):
        continue
    folder = s['folder']
    path = os.path.join(ROOT, 'sources',
                        folder if folder.startswith('pages')
                        else 'fiches/' + folder, s['file'])
    if not (os.path.exists(path) and path.lower().endswith('.pdf')):
        continue
    todo.append((s, path))
if a.limit:
    todo = todo[:a.limit]
print('%d sheets to read' % len(todo))

out, why = [], collections.Counter()
for s, path in todo:
    key = '%s|%d' % (s['estate'], s['year'])
    if sr.is_dossier(path):
        why['a press dossier, not a vintage’s sheet'] += 1
        s['role'] = 'skip'
        continue
    if sr.is_second_wine(path):
        why['the document calls itself the second wine'] += 1
        s['role'] = 'second'
        continue
    g = grand.get(s['estate'], '')
    whose = sr.confirms_estate(path, s['file'], g,
                               others.get(s['estate'], []))
    if whose == 'other':
        why['the sheet names a sibling property, not this estate'] += 1
        s['role'], s['how'] = 'unknown', 'another property'
        continue
    if whose == 'folder':
        # Camensac and Desmirail print their name in a logo, so no
        # extraction finds it. The folder is the only evidence there is,
        # and the manifest says so rather than pretending otherwise.
        s['how'] = s.get('how') or 'from the folder, which serves one estate'
        why['named nowhere in the document; the folder is the only evidence'] += 1
    named = None
    for nm in others.get(s['estate'], []):
        if sr.names_another_wine(path, s['file'], g, nm):
            named = nm
            break
    if named:
        why['the sheet names another of the estate’s wines'] += 1
        s['role'] = 'second' if named == second.get(s['estate']) else 'other'
        s['wine'] = named
        continue
    if key in PINNED:
        why['pinned: the sheet is wrong and the record is right'] += 1
        continue
    b = sr.blend_of(path, g, others.get(s['estate'], []))
    if not b:
        why['no blend in a window the sheet labels'] += 1
        continue
    if abs(sum(b.values()) - 100) > 1.5:
        why['a blend that does not sum to 100'] += 1
        continue
    out.append({'key': key, 'estate': s['estate'], 'year': s['year'],
                'blend': b, 'src': s['file'],
                'new': key not in have,
                'held': held.get(key)})

io.open(ROOT + 'data/sources.json', 'w', encoding='utf-8', newline='').write(
    json.dumps(man, ensure_ascii=False, indent=1))

# Does anything still hold the role it was given?
conflict = []
for s in recheck:
    g = grand.get(s['estate'], '')
    if not g:
        continue
    folder = s['folder']
    path = os.path.join(ROOT, 'sources',
                        folder if folder.startswith('pages')
                        else 'fiches/' + folder, s['file'])
    if not (os.path.exists(path) and path.lower().endswith('.pdf')):
        continue
    still = None
    for nm in others.get(s['estate'], []):
        if sr.names_another_wine(path, s['file'], g, nm):
            still = nm
            break
    if not still and not sr.is_second_wine(path):
        conflict.append((s['estate'], s.get('year'), s['file'],
                         s.get('role'), s.get('wine')))

rep = ['%d sheets read, %d propose a blend, %d of them for a vintage with no '
       'record yet' % (len(todo), len(out), sum(1 for r in out if r['new'])),
       '']
for k, n in why.most_common():
    rep.append('   %-52s %d' % (k[:52], n))
if conflict:
    rep.append('')
    rep.append('%d sheets are filed as another wine but no longer read as one '
               '- a role from an earlier run, to correct in the manifest:'
               % len(conflict))
    for e, y, f, role, wine in sorted(conflict):
        rep.append('   %-26s %s  role=%-7s wine=%-24s %s'
                   % (e[:26], y, role, str(wine)[:24], f[:40]))

# The disagreements first, because they are the whole point. A reading
# that contradicts the record means one of the two was taken off the
# wrong wine - Branaire-Ducru 2019 held Duluc's 52.5/44/2.5/1 where the
# grand vin's sheet says 56/35/4/5.
clash = [r for r in out if r['held'] and not
         (len(r['held']) == len(r['blend']) and
          all(abs(r['held'].get(k, -1) - v) < 0.6
              for k, v in r['blend'].items()))]
rep.append('')
rep.append('%d readings contradict the record they would overwrite:'
           % len(clash))
for r in sorted(clash, key=lambda r: r['key']):
    rep.append('   %-30s record %-28s sheet %-28s %s'
               % (r['key'],
                  ','.join('%s%g' % kv for kv in sorted(r['held'].items())),
                  ','.join('%s%g' % kv for kv in sorted(r['blend'].items())),
                  r['src'][:44]))
rep.append('')
for r in sorted(out, key=lambda r: r['key']):
    rep.append('%-34s %-30s %s %s'
               % (r['key'], ','.join('%s%g' % kv
                                     for kv in sorted(r['blend'].items())),
                  'NEW  ' if r['new'] else 'exists',
                  r['src'][:46]))
if not os.path.isdir(ROOT + 'reports'):
    os.makedirs(ROOT + 'reports')
io.open(ROOT + 'reports/proposed.txt', 'w', encoding='utf-8',
        newline='').write('\n'.join(rep))
json.dump(out, io.open(ROOT + 'reports/proposed.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\n'.join(rep[:24]))
print('\nfull report in reports/proposed.txt')

if not a.apply:
    print('nothing written to fiches.js; pass --apply to merge')
    sys.exit(0)

p = ROOT + 'data/fiches.js'
lines = io.open(p, encoding='utf-8').read().split(chr(10))
bykey = dict((r['key'], r) for r in out)
added, updated = 0, 0
for i, line in enumerate(lines):
    m = re.match(r"^'([a-z0-9-]+\|\d{4})':\{(.*)\},$", line)
    if not m or m.group(1) not in bykey:
        continue
    r = bykey.pop(m.group(1))
    bl = 'blend:{%s}' % ','.join('%s:%g' % kv
                                 for kv in sorted(r['blend'].items()))
    body = m.group(2)
    body = (re.sub(r'blend:\{[^}]*\}', bl, body) if 'blend:{' in body
            else bl + ',' + body)
    lines[i] = "'%s':{%s}," % (m.group(1), body)
    updated += 1
tail = []
for key, r in sorted(bykey.items()):
    bl = ','.join('%s:%g' % kv for kv in sorted(r['blend'].items()))
    tail.append("'%s':{blend:{%s},src:'%s'}," % (key, bl, r['src']))
    added += 1
# Keep the new ones together, before the file's closing brace.
for i in range(len(lines) - 1, -1, -1):
    if lines[i].strip().startswith('}'):
        lines[i:i] = tail
        break
else:
    lines.extend(tail)
io.open(p, 'w', encoding='utf-8', newline='').write(chr(10).join(lines))
print('%d records updated, %d added' % (updated, added))
print('now run: python tools/check-data.py  and  python tools/audit-sources.py')
