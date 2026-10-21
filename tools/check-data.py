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

# One blend under several vintages.
#
# An estate varies its blend with the weather; that is what a vintage
# is. The same multi-variety blend to the decimal across four or more
# years is a standing figure that has been copied onto each of them -
# the encépagement, or the blend as of whenever one document was
# written.
#
# Found three times before this was a gate. Clos Floridène had one
# dossier's figures on twenty years, including years in which its red
# did not exist. Batailley held "ENCEPAGEMENT : 70 % Cabernet Sauvignon
# 25 % Merlot 3 % Cabernet Franc 2 % Petit Verdot" under 2019, 2021 and
# 2023, while each of those sheets gives the vintage lower down -
# 74/25/1, 76/20/2/2, 79/19/2. Prieuré-Lichine held 50/45/5 across ten
# vintages and Siaurac 74/19/6/1 across two, both the same way.
#
# A single variety is exempt: Doisy-Dubroca really is Sémillon alone
# every year, and Pétrus Merlot.
byblend = collections.defaultdict(list)
for (eid, yr), got in blends.items():
    if len(got) > 1:
        byblend[(eid, tuple(sorted(got.items())))].append(yr)
for (eid, key), yrs in sorted(byblend.items()):
    if len(yrs) >= 4:
        note('one blend repeated under four or more vintages, which is a '
             'standing figure and not a vintage’s',
             '%s  %s  across %d vintages %s-%s'
             % (eid, ','.join('%s%g' % kv for kv in key), len(yrs),
                min(yrs), max(yrs)))

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

print('%d records, %d with a blend, %d sheets in the manifest'
      % (len(recs), len(blends), len(sheets)))

# Worth knowing, but not a defect: records whose estate the dashboard no
# longer lists. The 2025 Cru Bourgeois revision cut 79 estates from 249,
# and the sheets harvested while they were members are still here. The
# records are sound; there is simply nothing to show them against. Keep
# them against a re-listing or drop them - but know they are there.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import sheetreader as _sr
    known = _sr.estates(ROOT)
except Exception:
    known = None
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
