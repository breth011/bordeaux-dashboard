# -*- coding: utf-8 -*-
"""Every gate a blend has to pass, over the whole dataset.

    python tools/check-data.py


These are the tests that have caught real errors, and each one is here
because it caught something:

  sums to 100           a blend that does not add up was misread.
  no single variety     "100% Merlot" is usually the extractor finding
                        one figure and no others. Three estates really
                        do make one - they are listed by name, so a
                        fourth has to be argued for.
  Petit Verdot <= 25%   a seasoning variety at 30% is a column read
                        across the wrong row.
  no white in a red     over 20% of white varieties in a left-bank red
                        is the estate's dry white, filed on its grand
                        vin.
  leads on the same     an estate whose usual blend is 60%+ of one
  variety               variety does not hand the lead to another by
                        twelve points without saying so. Where it
                        genuinely does - Lafite 1991, "exceptional with
                        a majority of Merlot" - the exception is listed
                        here by name and by reason.
  the usual blend       and the reverse test: if every vintage on
  agrees                record contradicts an estate's usual blend,
                        the usual blend is what is wrong. This is how
                        La Tour Carnet was found set to 60% Cabernet at
                        a 62%-Merlot estate, which quietly made every
                        correct vintage look like a departure.
  not standing text     one figure repeated under every vintage of an
                        estate, where the source is a single document
                        covering all of them, is the estate's usual
                        practice and not any year's.

Run it after every merge. An exception belongs in this file, with the
sentence from the estate's own sheet that justifies it, so that the
check stays loud and the list of things it is allowed to ignore stays
short and readable.
"""
import io, json, os, re, sys, glob, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
WHITE = set(['SEM', 'SB', 'SG', 'MU'])

# Estates that really do bottle one variety, each checked against the
# words on its own sheet.
SINGLE_OK = {
    'de-carles': "L’ASSEMBLAGE 100 % merlot",
    'stem-chateau-moulin-du-cadet': "Merlot : 100 %",
    'levangile': "Varietals : Merlot 100%",
    'doisy-dubroca': "the estate is planted to Sémillon alone",
    'petrus': "Merlot alone, but for the years that carry Cabernet Franc",
    'lafleur-petrus': "Merlot-dominant, and 100% in some vintages",
}
# Vintages where the estate itself says the lead changed hands.
LEAD_OK = {
    ('lafite', '1991'):
        "The blend for this vintage was exceptional with a majority of "
        "Merlot. Varietals : Merlot 64%, Cabernet sauvignon 36%",
    ('desmirail', '2016'):
        "ASSEMBLAGE Cabernet Sauvignon : 40% Merlot : 55% Petit Verdot : 5%",
    ('la-tour-carnet', '2017'):
        "2017 BLEND 60% Merlot 37% Cabernet Sauvignon 3% Cabernet Franc",
    ('haut-brion', '1998'): "the estate’s own pages give a Merlot lead",
    ('haut-brion', '1999'): "the estate’s own pages give a Merlot lead",
    ('haut-brion', '2004'): "the estate’s own pages give a Merlot lead",
    ('haut-brion', '2012'): "the estate’s own pages give a Merlot lead",
    ('haut-brion', '2025'): "the estate’s own pages give a Merlot lead",
}


# Records whose source names another wine because the document covers
# both, or because the record cites several documents of which the
# estate's own is one.
#
# A named list rather than a rule. I tried a rule - strip the other
# wine's name from the filename and ask whether the estate is still
# named - and it skipped Le Marquis de Calon-Segur, whose name contains
# the estate's, while flagging Lacoste-Borie, whose name shares a word
# with it. Each attempt to fix one broke the other, which is the sign
# of a rule shaped wrong, so these are listed with their reasons.
TWO_WINES = {
    ('grand-puy-lacoste', '2024'):
        '2024-Fiche-technique-Grand-Puy-Lacoste-et-Lacoste-Borie.pdf is '
        'one sheet for both wines',
    ('giscours', '2024'):
        'four sources, of which CH.-GISCOURS-2024-FR-1.pdf is the grand '
        'vin’s own',
    ('giscours', '2025'):
        'six sources, of which FT-Chateau-Giscours-2025.pdf is the grand '
        'vin’s own',
}


def nums(s):
    return dict((k, float(v)) for k, v in re.findall(r'(\w+):([\d.]+)', s))


def lead(d):
    return max(d.items(), key=lambda kv: kv[1])[0] if d else None


def load():
    usual, names = {}, {}
    for f in sorted(glob.glob(ROOT + 'data/*.js')):
        if os.path.basename(f) in ('fiches.js', 'fiches-nl.js', 'cuvees.js'):
            continue
        s = io.open(f, encoding='utf-8').read()
        for m in re.finditer(r"id:'([a-z0-9-]+)'(.{0,900}?)blend:\{([^}]*)\}",
                             s, re.S):
            d = nums(m.group(3))
            if d:
                usual.setdefault(m.group(1), d)
        for m in re.finditer(r"id:'([a-z0-9-]+)',\s*name:'([^']+)'", s):
            names.setdefault(m.group(1), m.group(2))
    recs = []
    for line in io.open(ROOT + 'data/fiches.js', encoding='utf-8'):
        m = re.match(r"^'([a-z0-9-]+)\|(\d{4})':\{(.*)\},$", line.rstrip())
        if m:
            recs.append((m.group(1), m.group(2), m.group(3)))
    return usual, names, recs


usual, names, recs = load()
man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))
sheets = {}
for s in man['sheets']:
    sheets.setdefault(s['file'], s)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import sheetreader as _sr
    known = _sr.estates(ROOT)
except Exception:
    known = None

fail = collections.OrderedDict()


def note(kind, msg):
    fail.setdefault(kind, []).append(msg)


blends, bymonths = {}, collections.defaultdict(dict)
for eid, yr, body in recs:
    b = re.search(r'blend:\{([^}]*)\}', body)
    src = re.search(r"src:'([^']*)'", body)
    mo = re.search(r"months:'([^']*)'", body)
    if mo:
        bymonths[eid][yr] = (mo.group(1), src.group(1) if src else '')
    if not b:
        continue
    got = nums(b.group(1))
    blends[(eid, yr)] = got
    where = ' <- ' + (src.group(1)[:50] if src else 'no src')

    if abs(sum(got.values()) - 100) > 1.5:
        note('a blend that does not sum to 100 ±1.5',
             '%s %s  %g%%%s' % (eid, yr, sum(got.values()), where))
    if len(got) == 1 and list(got.values())[0] >= 100 and eid not in SINGLE_OK:
        note('a single variety at 100%, with no exception recorded',
             '%s %s  %s%s' % (eid, yr, list(got)[0], where))
    if got.get('PV', 0) > 25:
        note('Petit Verdot over 25%',
             '%s %s  PV %g%%%s' % (eid, yr, got['PV'], where))
    u = usual.get(eid)
    if u:
        if lead(u) not in WHITE:
            w = sum(v for k, v in got.items() if k in WHITE)
            if w > 20:
                note('white varieties over 20% in a red',
                     '%s %s  %g%%%s' % (eid, yr, w, where))
        lu, lg = lead(u), lead(got)
        if (lu and lg and lu != lg and u[lu] >= 58
                and got.get(lu, 0) + 12 < got[lg]
                and (eid, yr) not in LEAD_OK):
            note('the lead handed to another variety, unexplained',
                 '%s %s  usually %s %g%%, here %s %g%%%s'
                 % (eid, yr, lu, u[lu], lg, got[lg], where))

# A blend that appears in none of the estate's own sheets for that
# vintage.
#
# I first wrote this as "one blend repeated under four or more
# vintages", reasoning that an estate varies its blend with the weather.
# It flagged 22 estates and nearly all of them were right: La
# Conseillante really did land on 20% Cabernet Franc in five separate
# years, and Pontet-Canet on 65/30/4/1 in eight, and their records match
# their own sheets exactly. Repetition is not the defect.
#
# The defect is a figure with no sheet behind it. Prieuré-Lichine held
# 50/45/5 across ten vintages and not one of its sheets says that: each
# gives "ENCÉPAGEMENT VIGNOBLE : Cabernet Sauvignon : 50% Merlot : 45%
# Petit Verdot : 5%", which is the vineyard and the same every year, and
# then "ASSEMBLAGE GRAND VIN MILLÉSIME 2013 : Cabernet Sauvignon : 70%
# ...", which is the wine. Batailley and Clos Floridène were the same
# shape. Comparing the record against the sheet catches all of them and
# accuses none of the innocent.
#
# This needs what the sheets say, which means reports/proposed.json from
# tools/read-sheets.py. Without it the check is skipped and says so,
# rather than passing quietly.
prop = ROOT + 'reports/proposed.json'
if os.path.exists(prop):
    said = collections.defaultdict(set)
    for r in json.load(io.open(prop, encoding='utf-8')):
        said[(r['estate'], str(r['year']))].add(
            tuple(sorted((k, float(v)) for k, v in r['blend'].items())))
    checked = 0
    for (eid, yr), got in sorted(blends.items()):
        if (eid, yr) not in said:
            continue
        checked += 1
        if tuple(sorted(got.items())) not in said[(eid, yr)]:
            note('a blend that appears in none of the estate’s own '
                 'sheets for that vintage',
                 '%s %s  record %s  sheets %s'
                 % (eid, yr, ','.join('%s%g' % kv
                                      for kv in sorted(got.items())),
                    ' | '.join(','.join('%s%g' % kv for kv in s)
                               for s in sorted(said[(eid, yr)]))[:70]))
    print('%d records compared against a sheet for the same vintage'
          % checked)
else:
    print('reports/proposed.json is not here, so records were not compared '
          'against their sheets - run tools/read-sheets.py first')

# The usual blend, against the vintages that are supposed to vary round it.
for eid in sorted(set(e for e, y in blends)):
    rows = [v for (e, y), v in blends.items() if e == eid]
    if eid not in usual or len(rows) < 3:
        continue
    leads = collections.Counter(lead(r) for r in rows)
    top, n = leads.most_common(1)[0]
    if top != lead(usual[eid]) and n == len(rows):
        note('an estate whose every vintage contradicts its usual blend',
             '%s  usual %s, all %d vintages lead on %s'
             % (eid, lead(usual[eid]), len(rows), top))

# One figure under every vintage, from one document that covers them all.
for eid, yrs in bymonths.items():
    if len(yrs) < 6:
        continue
    vals = collections.Counter(v for v, s in yrs.values())
    if len(vals) > 1:
        continue
    srcs = set(s for v, s in yrs.values())
    roles = set(sheets.get(s, {}).get('role') for s in srcs)
    # Many estates really do age for 18 months every year, and say so on
    # each vintage's own sheet - Grand-Puy-Lacoste states "16-18 months"
    # on twenty separate sheets. It is only standing text when one
    # document covers every year, or when the document is a dossier
    # rather than a vintage's sheet.
    if roles & set(['skip']) or len(srcs) == 1:
        note('one ageing figure under every vintage, from a source that is '
             'not a vintage’s',
             '%s  months=%s across %d vintages from %d document(s)'
             % (eid, list(vals)[0], len(yrs), len(srcs)))

# A record whose source names another of the estate's wines.
#
# Cheap, and it found eighteen. Château Margaux had five vintages whose
# blend came off Pavillon Rouge's page and one off Château Labégorce's
# sheet; Calon-Ségur six off Le Marquis de Calon-Ségur; Lafon-Rochet two
# off Les Pèlerins; Léoville-Poyferré 2024 off Pavillon de Poyferré;
# Domaine de Chevalier two off its own white.
#
# A season note is exempt, as it is in tools/audit-sources.py: one
# weather falls on one vineyard, so an estate's cuvées share a season
# and a note that crossed from one to another is still true. Everything
# else on a record is one wine's.
if known:
    SEASON_ONLY = set(['note', 'ntl', 'src', 'xsrc', 'url'])
    for eid, yr, body in recs:
        src = re.search(r"src:'([^']*)'", body)
        e = known.get(eid)
        if not (src and e and e.get('name')):
            continue
        fields = set(re.findall(r'([a-z]+):', body)) - SEASON_ONLY
        if not fields:
            continue
        for nm in e.get('cuvees') or ():
            mark = _sr.mark_of(nm, e['name'])
            if not (mark and _sr.says_in_name(src.group(1), mark)):
                continue
            if (eid, yr) in TWO_WINES:
                break
            note('a record whose source names another of the estate’s '
                 'wines',
                 '%s %s  %s  <- %s  fields=%s'
                 % (eid, yr, nm[:28], src.group(1)[:44],
                    ','.join(sorted(fields))[:34]))
            break

print('%d records, %d with a blend, %d sheets in the manifest'
      % (len(recs), len(blends), len(sheets)))

# Worth knowing, but not a defect: records whose estate the dashboard no
# longer lists. The 2025 Cru Bourgeois revision cut 79 estates from 249,
# and the sheets harvested while they were members are still here. The
# records are sound; there is simply nothing to show them against. Keep
# them against a re-listing or drop them - but know they are there.
if known:
    orph = collections.Counter(e for e, y, b in recs if e not in known)
    if orph:
        print('\n%d records belong to %d estates the dashboard no longer '
              'lists:' % (sum(orph.values()), len(orph)))
        for e, n in orph.most_common():
            print('   %-44s %d' % (e[:44], n))
total = 0
for kind, rows in fail.items():
    print('\n%s: %d' % (kind, len(rows)))
    for r in rows[:14]:
        print('   ' + r)
    if len(rows) > 14:
        print('   ... and %d more' % (len(rows) - 14))
    total += len(rows)
print('\n%s' % ('every gate passes' if not total
                else '%d to look at' % total))
sys.exit(1 if total else 0)
