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
    ('siaurac', '2021'):
        'the April frost destroyed the Merlot: "ASSEMBLAGE : 51% '
        'Cabernet-franc, 38% Malbec, 10% Merlot, 1% Cabernet Sauvignon"',
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

# The records pinned in read-sheets.py, read from there rather than
# listed again here. A pin means the estate's own sheet is wrong and the
# record holds the corrected reading, with the sentence from the sheet
# and the reason written beside it - Haut-Brion's 2016, 2017, 2018 and
# 2019 all have the two Cabernets transposed in the typesetting. Those
# are corrections, not contradictions, and a gate that reports them
# forever is a gate people learn to skip. Two copies of the same list
# would drift, so there is one.
PINNED_OK = set()
try:
    _rs = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'read-sheets.py'), encoding='utf-8').read()
    _in = re.search(r'^PINNED\s*=\s*\{(.*?)^\}', _rs, re.S | re.M)
    if _in:
        for _k in re.findall(r"'([a-z0-9-]+)\|(\d{4})'\s*:", _in.group(1)):
            PINNED_OK.add(_k)
except Exception:
    pass

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
#
# A proposal is only worth contradicting a record with if the sheet
# behind it is still filed as that estate's grand vin. This is the same
# condition merge-proposals.py applies before it adds anything, and for
# the same reason: the manifest is the record of what each sheet is for,
# and reports/proposed.json is a snapshot taken before the last
# refiling.
#
# It mattered three times at once. Domaine de Chevalier 2022 was being
# contradicted by two Chateau Poumey sheets, Lynch-Moussas 2019 by
# Chateau Batailley's, and both pairs were refiled as 'skip' the moment
# they were read - but the gate went on quoting them, because the
# snapshot predates the correction. A gate that reports settled
# questions trains people to ignore it.
NOT_GRAND = ('skip', 'second', 'other', 'page', 'group report')
if os.path.exists(prop):
    said = collections.defaultdict(set)
    for r in json.load(io.open(prop, encoding='utf-8')):
        sh = sheets.get(r['src']) or {}
        if sh.get('role') in NOT_GRAND:
            continue
        if sh.get('estate') and sh['estate'] != r['estate']:
            continue
        said[(r['estate'], str(r['year']))].add(
            tuple(sorted((k, float(v)) for k, v in r['blend'].items())))
    checked = 0
    for (eid, yr), got in sorted(blends.items()):
        if (eid, yr) not in said:
            continue
        # A record pinned because its own sheet is wrong is not a
        # contradiction; it is a correction, with the reason written
        # down in read-sheets.py.
        if (eid, yr) in PINNED_OK:
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

# A vintage out of line with the estate's own other vintages.
#
# The lead check above needs a declared usual blend, and only 139
# estates have one - so for the three hundred-odd that do not, nothing
# was watching. This asks the same question of the estate's own
# records: where every other vintage leads on one variety and this one
# leads on another by a wide margin, something is wrong with one of
# them.
#
# It matters most for a vintage being added, because the gate that
# compares a record against its sheet cannot help there: a new record
# comes from its sheet by definition.
byestate = collections.defaultdict(dict)
for (eid, yr), got in blends.items():
    byestate[eid][yr] = got
for eid, yrs in sorted(byestate.items()):
    if len(yrs) < 4:
        continue
    leads = collections.Counter(lead(v) for v in yrs.values())
    top, n = leads.most_common(1)[0]
    if n < len(yrs) - 1:
        continue        # the estate genuinely varies; nothing to compare
    for yr, got in sorted(yrs.items()):
        if lead(got) == top or (eid, yr) in LEAD_OK:
            continue
        others = [v[top] for y, v in yrs.items() if y != yr and top in v]
        if not others:
            continue
        usual_top = sum(others) / len(others)
        if usual_top >= 55 and got.get(top, 0) + 12 < got[lead(got)]:
            note('a vintage leading on a variety none of the estate’s '
                 'others lead on',
                 '%s %s  %s %g%% where its other vintages average %s %g%%'
                 % (eid, yr, lead(got), got[lead(got)], top, usual_top))

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

# ------------------------------------------------------------------
# A vintage blend that is exactly the estate's planting.
#
# The commonest defect in this dataset is the vineyard's encepagement
# recorded as the wine's assemblage - Prieure-Lichine on ten vintages,
# Batailley on three, Jean Faure on eight, Clos de l'Oratoire, Dalem.
# The figures are indistinguishable from a blend: the same grapes, the
# same percentages, the same sum. For a long time the only test was
# repetition - a figure that never moves across a decade is the
# planting - and that test is a proxy which fails. It rejected Pichon
# Baron 2012, whose sheet says "ASSEMBLAGE Cabernet sauvignon 80%,
# Merlot 20%" in as many words, because the estate blended to the same
# proportions in 2014 and 2023 as well.
#
# data/plantings.js now records what each vineyard is planted with,
# read off the estate's own sheets under a label that means the
# vineyard, so the test is a comparison against a fact. A record whose
# blend equals the planting exactly is suspect - but only where the
# estate's other vintages disagree with it, because an estate that has
# only ever published one figure gives nothing to contradict.
#
# Bellegrave shows why it has to be exact. Its sheet carries both lines:
# "Blend : 60% Cabernet Sauvignon, 40% Merlot" for the vintage and
# "Encepagement : 65% / 33% / 2%" for the vineyard. 60/40 matches no
# planting, so nothing is said about it.
#
# And HOW each one is known, because that decides what a match means.
# plantings.js holds two different things under one key: 43 entries read
# off the estate's own sheets under a vineyard label, and 50 copied from
# chateaux.js's `blend`, which is the estate's typical ASSEMBLAGE. A
# vintage equal to the first is a wine that matches its vineyard. A
# vintage equal to the second is a wine that matches the estate's usual
# wine, which is not news. They are counted apart below.
PLANTINGS = {}
PLANT_HOW = {}
_p = os.path.join(ROOT, 'data', 'plantings.js')
if os.path.exists(_p):
    for _line in io.open(_p, encoding='utf-8'):
        _m = re.match(r"^'([a-z0-9-]+)':\{blend:\{([^}]*)\}(.*)",
                      _line.rstrip())
        if _m:
            PLANTINGS[_m.group(1)] = tuple(sorted(
                (k, float(v)) for k, v in
                re.findall(r"([A-Z]+):([\d.]+)", _m.group(2))))
            _h = re.search(r"how:'([a-z]+)'", _m.group(3))
            PLANT_HOW[_m.group(1)] = _h.group(1) if _h else '?'

#
# Reported, NOT failed. The first version of this counted as a defect
# and flagged 35, among them La Conseillante's 2002, 2010, 2015, 2016
# and 2024 at CF20,ME80 and Pontet-Canet's eight at 65/30/4/1 - the two
# estates this file's own notes name as the reason the repetition test
# was abandoned, because each genuinely blends to those proportions and
# each matches its own sheets exactly. An estate planted 80/20 that
# blends 80/20 has done nothing wrong.
#
# So it prints and does not fail. A guard that cries wolf is worse than
# no guard, because the next person stops reading it - and what is left
# is still useful: a short list, worth a glance after a merge, of the
# records where a planting and a blend coincide.
plant_hits = []
if PLANTINGS:
    byest = collections.defaultdict(dict)
    for eid, yr, body in recs:
        b = re.search(r'blend:\{([^}]*)\}', body)
        if b:
            byest[eid][yr] = tuple(sorted(
                (k, float(v)) for k, v in
                re.findall(r"'?([A-Z]+)'?:([\d.]+)", b.group(1))))
    for eid, years in sorted(byest.items()):
        planted = PLANTINGS.get(eid)
        if not planted:
            continue
        same = sorted(y for y, b in years.items() if b == planted)
        other = [b for y, b in years.items() if b != planted]
        if not same or not other:
            continue
        plant_hits.append((eid, same, planted,
                           PLANT_HOW.get(eid, '?')))

# ---------------------------------------------------------------------
# THE APPELLATION THE SHEET STATES, against the one the estate is
# recorded in. The strongest evidence there is for the defect that
# keeps coming back - one owner's whole range in one folder - and the
# reason it is a report rather than a guard is written beside apps_in
# in sheetreader: it refuses thirty good sheets to catch four bad ones.
#
# What it caught on its first run, and what is now marked in the
# manifest: Barton & Guestier's MARGAUX, BORDEAUX BLANC, Cremant de
# Bordeaux and Cremant de Bourgogne, all in Chateau Magnol's folder,
# which had given Magnol seven of its nine records - the three months
# in the 2011 record came from a sparkling Chardonnay.
app_hits = []
if known:
    _where = {}
    for _root, _dirs, _files in os.walk(ROOT + 'sources'):
        for _f in _files:
            _where.setdefault(_f, os.path.join(_root, _f))
else:
    _where = {}
for s in sheets.values():
    if s.get('role') not in ('grand', 'combined'):
        continue
    eid, yr = s.get('estate'), s.get('year')
    if not (eid and yr):
        continue
    e = (known or {}).get(eid) or {}
    mine = _sr.app_canon(e.get('app'))
    if not mine:
        continue
    p = _sr.path_of(ROOT, s, _where)
    if not (p and p.lower().endswith('.pdf')):
        continue
    try:
        text = ' '.join(_sr.flat(p).split())
    except Exception:
        continue
    named = _sr.apps_in(text[:2500])
    if not named or mine in named:
        continue
    others = [a for a in named if a not in _sr.APP_GENERIC]
    if len(set(others)) != 1 or _sr.APP_RX[mine].search(text):
        continue
    app_hits.append((eid, str(yr), e.get('app'), others[0], s['file']))

print('%d records, %d with a blend, %d sheets in the manifest'
      % (len(recs), len(blends), len(sheets)))

if app_hits:
    print('\n%d sheets state an appellation the estate is not recorded '
          'in.\nEither the sheet is another property\u2019s or the '
          'appellation on record is wrong, and\nwhich it is wants a '
          'person, not a rule:' % len(app_hits))
    for eid, yr, mine, said, f in sorted(app_hits)[:18]:
        print('   %-30s %s  on record %-16s sheet says %-18s %s'
              % (eid[:30], yr, (mine or '?')[:16], said[:18], f[:34]))
    if len(app_hits) > 18:
        print('   ... and %d more' % (len(app_hits) - 18))

_read_hits = [h for h in plant_hits if h[3] == 'read']
_decl_hits = [h for h in plant_hits if h[3] != 'read']


def _plant_lines(hits):
    for eid, same, planted, _how in hits[:18]:
        print('   %-34s %-22s %s'
              % (eid[:34],
                 ','.join('%s%g' % kv for kv in planted)[:22],
                 ','.join(same)[:30]))
    if len(hits) > 18:
        print('   ... and %d more' % (len(hits) - 18))


if _read_hits:
    print('\n%d estates have a vintage whose blend is exactly what the '
          'vineyard is planted with,\nread off the estate\'s own sheets '
          'under a vineyard label. Some of these are right -\nan estate '
          'planted 80/20 may well blend 80/20 - so this is a list to '
          'glance at,\nnot a complaint:' % len(_read_hits))
    _plant_lines(_read_hits)

if _decl_hits:
    print('\n%d estates have a vintage whose blend equals the typical '
          'assemblage declared\nfor them in chateaux.js. That is the '
          'expected kind of coincidence and is listed\nonly so it is not '
          'mistaken for the kind above: a wine matching its estate\'s '
          'usual\nwine is not news. Pontet-Canet prints its assemblage '
          'under "Grape varieties"\nand moves it every year - 17 figures '
          'across 145 sheets - so its eight at\n65/30/4/1 are the '
          'commonest one, not a planting:' % len(_decl_hits))
    _plant_lines(_decl_hits)

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
