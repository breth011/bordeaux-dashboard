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

WHY_HB = (
    'the sheet has the two Cabernets transposed. Proven for Haut-Brion '
    '2016: Fiche-technique_ChateauHBR_2016_EN.pdf reads "Cabernet '
    'Sauvignon: 6,5% Cabernet Franc: 37,5%" where the estate’s own '
    'FR sheet, its GB sheet and its own vintage page all read "Cabernet '
    'Franc : 6,5 % Cabernet Sauvignon : 37,5 %". The other three have no '
    'second source on disk, and are inferred from the same pattern at '
    'the same two estates, where Cabernet Franc is a few per cent of the '
    'planting and never forty')

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
WHY_BLOCK_OVER_PROSE = (
    'the sheet states its blend twice and the two disagree. Its data '
    'block gives one figure and the tasting paragraph below it gives '
    'another, and a data block beats prose - the same rule that settles '
    'La Conseillante 2020, Dauzac 2010 and d’Issan 2009. The flat '
    'reading finds the paragraph first, so the proposal is the prose and '
    'the record holds the block')

PINNED = {
    'stem-chateau-badette|2015': WHY_BLOCK_OVER_PROSE +
        ': the block reads "Assemblage Merlot : 90 % Cabernet franc : '
        '7 % Petit Verdot : 3 %" and the paragraph "Assemblage de 95 % '
        'Merlot et 5 % Cabernet Franc"',
    'stem-chateau-badette|2019': WHY_BLOCK_OVER_PROSE +
        ': the block reads "Merlot : 80 % Cabernet franc : 15 % Petit '
        'Verdot : 5 %" and the paragraph "Assemblage de 85 % Merlot, '
        '10 % Cabernet Franc et 5 % Petit Verdot"',
    'bourgeois-chateau-paloumey|2022':
        'the flat reading takes the planting. The sheet prints '
        '"Encépagement ... Cabernet Sauvignon 50% Merlot 44% / Cabernet '
        'Franc 3% Petit Verdot 3%" above "Assemblage Cabernet Sauvignon '
        ': 53 % Merlot : 44 % Cabernet franc : 1 % Petit Verdot : 2 %", '
        'and only the column reading reaches the second',
    'stem-chateau-de-pressac|2016':
        'the sheet is one document for every vintage from 2012 to 2024, '
        'each with its own ASSEMBLAGE FINAL, and both readings '
        'interleave the years - which is why one of them proposed 87% '
        'Malbec and the other 85% Cabernet Franc for the same wine. '
        '2016’s own line reads "Merlot : 90% Malbec : 10% Le millésime '
        '2016 fait partie de ces millésimes exceptionnels". The sheet is '
        'filed as a group report',
    'haut-brion|2016': WHY_HB,
    'haut-brion|2017': WHY_HB,
    'haut-brion|2018': WHY_HB,
    'haut-brion|2019': WHY_HB,
    'la-mission-haut-brion|2024': WHY_HB,
    'giscours|2021':
        'the sheet states no assemblage. Its "65 % Cabernet Sauvignon - '
        '32 % Merlot - 3% Petit Verdot" follows "95 ha en production" and '
        'is the planted area, and the English edition prints no label '
        'beside it at all - the labels are in one column of the table and '
        'the values in another',
    'ferriere|2019':
        'the sheet says "Assemblage 70 % cabernet sauvignon, 25 % merlot, '
        '5 % petit verdot", which is the record, and only the column '
        'reading finds it: read flat, the heading is followed by "Elevage '
        'Second vin Claire VILLARS LURTON"',
    'montrose|2019':
        'the record sums to 100 with 1% Petit Verdot where the sheet’s '
        'prose reaches only 99 without it',
    'stem-chateau-jean-faure|2021':
        'the only source is a carnet de notes, whose prose gives 67% '
        'Cabernet Franc and 33% Merlot; the record gives 60/7/33 with the '
        'Malbec this estate does grow, and neither is better evidence '
        'than the other',
    'stem-chateau-destieux|2020':
        'the sheet says "assemblage de 70% de merlots ... et de 30% de '
        'Cabernets Franc et Sauvignon" - the two Cabernets lumped, so no '
        'split exists to read',
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

# One loader, in sheetreader, rather than each tool parsing data/*.js its
# own way. The version that lived here used a regex for a whole estate
# block that matched almost none of them, and another that broke on the
# escaped apostrophe in 'Chateau Lalande d\'Auvion' - which silently
# dropped every estate after it in the list.
E = sr.estates(ROOT)
known = set(E)
grand = dict((k, v['name'] or '') for k, v in E.items())
second = dict((k, v['second']) for k, v in E.items() if v['second'])
cat = dict((k, v['cat']) for k, v in E.items())
# Every other wine the estate makes, so a sheet for one of them is not
# read as the grand vin's. D de Dauzac is a white Bordeaux; the Giscours
# Carnet Primeurs carries La Sirene's blend beside Giscours' own.
others = dict((k, v['cuvees']) for k, v in E.items())

# A role this tool set on an earlier run is never un-set by a later one,
# so a role set by a rule that was later found wrong stays wrong. Those
# sheets are re-read and reported rather than silently flipped back: the
# manifest is the record, and something that writes it both ways without
# saying so is not a record.
recheck = []
twoways = []
todo = []
for s in man['sheets']:
    if (s.get('role') in ('second', 'other') and s.get('estate')
            and not sr.role_is_reasoned(s)):
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
    if sr.role_is_reasoned(s):
        why['a role already decided, with the reason recorded'] += 1
        continue
    press = sr.is_press_name(s['file'])
    if press:
        why['the filename says it is press'] += 1
        s['role'], s['how'] = 'skip', 'the filename says ' + press
        continue
    if sr.is_dossier(path):
        why['a press dossier, not a vintage’s sheet'] += 1
        s['role'] = 'skip'
        continue
    if sr.is_second_wine(path):
        why['the document calls itself the second wine'] += 1
        s['role'] = 'second'
        continue
    g = grand.get(s['estate'], '')
    spells = sr.names_other_chateau(s['file'], g,
                                    others.get(s['estate'], []),
                                    second.get(s['estate']))
    if spells:
        why['the filename names another château'] += 1
        s['role'], s['how'] = 'other', 'the filename says ' + spells
        s['wine'] = spells
        continue
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
    b, alt = sr.blend_of(path, g, others.get(s['estate'], []), both=True)
    if b and alt and b != alt:
        # The two readings of the page disagree, so which is right
        # depends on a layout no rule here can judge. The flat reading
        # is proposed, because it is right more often, and the
        # disagreement is listed so that someone can look.
        twoways.append((s['estate'], s.get('year'), s['file'], b, alt))
    if not b:
        why['no blend in a window the sheet labels'] += 1
        continue
    bad = sr.wrong_colour(s['file'], b, cat.get(s['estate']))
    if bad:
        why['a different wine of this estate: ' + bad] += 1
        s['role'] = 'other'
        continue
    if abs(sum(b.values()) - 100) > 1.5:
        why['a blend that does not sum to 100'] += 1
        continue
    out.append({'key': key, 'estate': s['estate'], 'year': s['year'],
                'blend': b, 'src': s['file'],
                'new': key not in have,
                'held': held.get(key)})

# Write back by re-reading first, and changing only the sheets this run
# decided something about.
#
# A full pass takes the better part of an hour, and writing the copy
# loaded at the start of it threw away everything written meanwhile:
# 132 sheets refiled out of five owner-group libraries and nine
# Cailleteau Bergeron cuvees named, all silently reverted by a run that
# had been reading PDFs since before any of it happened. The work looked
# done and was not, which is the worst way to lose it.
touched = {}
for s in man['sheets']:
    touched[(s['folder'], s['file'])] = s

fresh = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))
restored = 0
for s in fresh['sheets']:
    mine = touched.get((s['folder'], s['file']))
    if mine is None:
        continue
    for key in ('role', 'wine', 'how', 'note'):
        if mine.get(key) != s.get(key) and mine.get(key) is not None:
            s[key] = mine[key]
            restored += 1
io.open(ROOT + 'data/sources.json', 'w', encoding='utf-8', newline='').write(
    json.dumps(fresh, ensure_ascii=False, indent=1))
if restored:
    print('%d fields written back into the manifest as it now stands'
          % restored)

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
        b = sr.blend_of(path, g, others.get(s['estate'], []))
        if sr.wrong_colour(s['file'], b, cat.get(s['estate'])):
            continue
        conflict.append((s['estate'], s.get('year'), s['file'],
                         s.get('role'), s.get('wine')))

rep = ['%d sheets read, %d propose a blend, %d of them for a vintage with no '
       'record yet' % (len(todo), len(out), sum(1 for r in out if r['new'])),
       '']
for k, n in why.most_common():
    rep.append('   %-52s %d' % (k[:52], n))
if twoways:
    rep.append('')
    rep.append('%d sheets read differently flat and column by column - the '
               'flat reading is proposed, the other is here to check:'
               % len(twoways))
    for e, y, f, b, alt in sorted(twoways)[:40]:
        rep.append('   %-24s %s  flat %-24s cols %-24s %s'
                   % (str(e)[:24], y,
                      ','.join('%s%g' % kv for kv in sorted(b.items())),
                      ','.join('%s%g' % kv for kv in sorted(alt.items())),
                      f[:34]))
    if len(twoways) > 40:
        rep.append('   ... and %d more' % (len(twoways) - 40))

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
# A scoped run writes a scoped report, so that running one estate does
# not quietly replace the report for all of them - which it did once,
# and the full report had taken forty minutes to produce.
scope = ''
if a.estate:
    scope = '-' + '-'.join(sorted(a.estate))[:40]
elif a.year:
    scope = '-%d' % a.year
# A scoped run writes a scoped report, so that reading one estate does
# not quietly replace the report for all of them - which it did once,
# after the full report had taken the better part of an hour to produce.
scope = ''
if a.estate:
    scope = '-' + '-'.join(sorted(a.estate))[:40]
elif a.year:
    scope = '-%d' % a.year
if not os.path.isdir(ROOT + 'reports'):
    os.makedirs(ROOT + 'reports')
io.open(ROOT + 'reports/proposed%s.txt' % scope, 'w', encoding='utf-8',
        newline='').write('\n'.join(rep))
json.dump(out, io.open(ROOT + 'reports/proposed%s.json' % scope, 'w',
                       encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n'.join(rep[:24]))
print('\nfull report in reports/proposed%s.txt' % scope)

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
