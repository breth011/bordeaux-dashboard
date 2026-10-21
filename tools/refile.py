# -*- coding: utf-8 -*-
"""Which estate does each sheet's filename name? REPORT ONLY for now.

    python tools/refile.py              what it finds
    python tools/refile.py --apply      refuses; see below

An owner keeps all its properties in one library, and the crawl files
them all under whichever estate led it there. 144 sheets sit under Tour
Saint-Christophe and only 40 are its own; the rest are Vignobles K's
other properties - Chateau La Patache and its Badine, Enclos
Tourmaline, Enclos de Viaud, Chateau Le Rey in three cuvees, Chateau
Haut-Brisson - and, importantly, Chateau Bellefont-Belcier, which this
dashboard does hold and which was therefore missing sheets it had all
along.

So the filename is read against every name the dashboard knows: each
estate's, and each of their other wines'. The longest match wins,
which is the only way past the names that contain each other -
Maucaillou contains Caillou, Les Carmes Haut-Brion contains Haut-Brion,
Madame de Beaucaillou contains Caillou, and LA_TOUR_DE_MONS contains
Latour, which once filed 57% Merlot at a 90%-Cabernet estate.

Three outcomes, and the manifest already has a word for each:
  a different estate this dashboard holds   move it there
  another of some estate's wines            role second or other
  a property this dashboard does not hold   estate null, another property

--apply is disabled. I turned it on once, moved 218 sheets, and the
audit went from 4 complaints to 79 - and two of those were a grand
vin's own sheet relabelled as its second wine's:
Canon-la-Gaffeliere-2014-FT-FR-36.pdf marked Cote Mignon-La Gaffeliere,
and 2024-Fiche-technique-Grand-Puy-Lacoste marked Lacoste-Borie. That
is precisely the error this pipeline exists to prevent, so the move was
reverted and the switch taken off until the name resolution is worth
trusting with it.

What it finds is still worth reading, because much of it is real:

  61 sheets of BriO de Cantenac Brown, 20 of Lagrave-Martillac, 16 of
  Echo de Lynch-Bages, 12 of La Croix Ducru-Beaucaillou, 12 of Prelude
  a Grand-Puy-Ducasse, 9 of Charmes de Kirwan, 7 of Pastourelle de
  Clerc Milon, 6 of La Dame de Montrose - all filed as their estate's
  grand vin.

  36 sheets belonging to nobody that are Chateau Bellefont-Belcier's,
  and 104 of the 144 under Tour Saint-Christophe that are Vignobles K's
  other properties - La Patache and its Badine, Enclos Tourmaline,
  Enclos de Viaud, Le Rey in three cuvees, Haut-Brisson.

And what it gets wrong says what still needs doing: it offered to move
La Mondotte's sheets to Troplong Mondot on the strength of "Mondot",
and to strip Pichon Baron and d'Issan of theirs as properties this
dashboard does not hold, which they are not.
"""
import io, json, os, re, sys, argparse, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
ap.add_argument('--estate', action='append', default=[],
                help='only sheets currently filed under these')
a = ap.parse_args()

E = sr.estates(ROOT)

# Every name the dashboard knows, longest first so the longest wins.
# A name has to be distinctive enough to be worth matching: "Olivier"
# is, "Le Dauphin" is not.
index = []
for eid, e in E.items():
    nm = e.get('name')
    if nm:
        index.append((nm, eid, None))
    for c in e.get('cuvees') or ():
        index.append((c, eid, c))
index = [(nm, eid, cuvee) for nm, eid, cuvee in index
         if len(sr.packed(nm)) >= 6]
index.sort(key=lambda r: -len(sr.packed(r[0])))


def forms(nm):
    """The ways a filename may write a name.

    Three, and all three are needed. Keeping only the shortest made
    LA-TOUR-CARNET resolve to Château Latour, because the prefix "la
    tour" matched Latour's bare form before "la tour carnet" could be
    tried - the substring trap arriving through the back door. Keeping
    only the longest made Château La Mission Haut-Brion unmatchable by
    a file called la-mission-haut-brion, and reported as a property the
    dashboard does not hold.
    """
    whole = nm or ''
    house = re.sub(r'(?i)^(château|chateau|clos|domaine|vieux\s+'
                   r'château)\s+', '', whole)
    noart = re.sub(r"(?i)^(d'|de\s+|du\s+|des\s+|la\s+|le\s+|les\s+|l')",
                   '', house)
    out = []
    for f in (whole, house, noart):
        if f and f not in out:
            out.append(f)
    return out


def bare(nm):
    return forms(nm)[-1]


# (packed form, name, estate, cuvee), longest form first.
packed_index = []
for nm, eid, cuvee in index:
    for form in forms(nm):
        if len(sr.packed(form)) >= 6:
            packed_index.append((sr.packed(form), nm, eid, cuvee))
packed_index = sorted(set(packed_index), key=lambda r: -len(r[0]))

# Packed name -> (name, estate, cuvee), for exact lookup.
# Longest form first, so that "la tour carnet" is looked up before
# anything can match "la tour".
exact = {}
for nm, eid, cuvee in index:
    for form in forms(nm):
        exact.setdefault(sr.packed(form), (nm, eid, cuvee))


def whose(filename):
    """Whose wine the filename says this is.

    Where the filename says CHATEAU, CLOS or DOMAINE, the words after it
    are the name, and the longest prefix of them that the dashboard
    knows is the wine. Prefixes, not substrings: FT_Chateau_Labegorce_
    Margaux_MAR_RO_2025 names Labegorce, which this dashboard does not
    hold, and matching substrings would have resolved it to Chateau
    Margaux - whose 2025 record it was in fact sitting on.

    Returns (name, estate, cuvee), or (name, None, None) when the
    filename names a property the dashboard does not hold, or None when
    it names nothing and the folder is all there is to go on.
    """
    said = sr.property_in_filename(filename)
    if said:
        words = said.split()
        for n in range(len(words), 0, -1):
            hit = exact.get(sr.packed(' '.join(words[:n])))
            if hit:
                return hit
        return (said, None, None)
    # No house word, so fall back to any name the filename carries,
    # longest first - which is how the names that contain each other
    # are kept apart.
    #
    # The cheap test first. Running the boundary-aware match against
    # every one of a thousand names for every one of nine thousand
    # sheets is twenty million regex searches and does not finish; the
    # packed substring rules out all but a handful, and only those are
    # confirmed properly.
    pf = sr.packed(filename)
    for form, nm, eid, cuvee in packed_index:
        if form in pf and sr.says_in_name(filename, nm):
            return nm, eid, cuvee
    return None


man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))
moves, counts = [], collections.Counter()
for s in man['sheets']:
    if a.estate and s.get('estate') not in a.estate:
        continue
    if sr.role_is_reasoned(s) or s.get('role') == 'skip':
        continue
    hit = whose(s['file'])
    if not hit:
        counts['the filename names no wine the dashboard knows'] += 1
        continue
    nm, eid, cuvee = hit
    if eid is None:
        # The filename names a property, and it is not one this
        # dashboard holds. Whatever estate the crawl guessed, the
        # document says otherwise.
        if s.get('estate') is None:
            counts['already filed as another property'] += 1
            continue
        moves.append((s, None, nm, 'unknown'))
        continue
    if cuvee:
        if s.get('wine') == cuvee and s.get('role') in ('second', 'other'):
            counts['already filed as that wine'] += 1
            continue
        role = ('second' if cuvee == (E[eid].get('second') or '') else 'other')
        moves.append((s, eid, cuvee, role))
    elif eid != s.get('estate'):
        moves.append((s, eid, None, s.get('role')))
    else:
        counts['already filed under that estate'] += 1

# What --apply is allowed to do, and what it only reports.
#
# Two kinds of move are safe. Marking a sheet as another wine of the
# estate it already sits under changes nothing about whose library it
# came from - BriO de Cantenac Brown, Echo de Lynch-Bages, Charmes de
# Kirwan, La Croix Ducru-Beaucaillou. And giving an estate a sheet that
# currently belongs to nobody can only add.
#
# The rest are reported and left alone, because the name matching is
# not good enough yet to be trusted with them. In one dry run it
# offered to move La Mondotte's sheets to Troplong Mondot on the
# strength of "Mondot", and to strip Pichon Baron and d'Issan of
# theirs as properties this dashboard does not hold - which they are
# not. A wrong move here is the error this whole pipeline exists to
# avoid, so until those resolve correctly the tool reports them for
# someone to read.
safe, unsafe = [], []
for mv in moves:
    sheet, eid, cuvee, role = mv
    if cuvee and eid and eid == sheet.get('estate'):
        safe.append(mv)
    elif eid and sheet.get('estate') is None:
        safe.append(mv)
    else:
        unsafe.append(mv)

print('%d sheets to move:' % len(moves))
by = collections.Counter()
for s, eid, cuvee, role in moves:
    by[(s.get('estate'), eid or 'not in the dashboard',
    cuvee or 'the grand vin')] += 1
for (was, now, wine), n in by.most_common(30):
    print('   %-30s -> %-30s %-26s %d'
          % (str(was)[:30], now[:30], wine[:26], n))
if len(by) > 30:
    print('   ... and %d more groupings' % (len(by) - 30))
for k, n in counts.most_common():
    print('   %-56s %d' % (k[:56], n))

print('\n%d of those are safe to apply; %d need reading first'
      % (len(safe), len(unsafe)))
if unsafe:
    print('\nreported, not moved:')
    seen = set()
    for sheet, eid, cuvee, role in unsafe:
        k = (sheet.get('estate'), eid, cuvee)
        if k in seen:
            continue
        seen.add(k)
        print('   %-30s -> %-30s %s'
              % (str(sheet.get('estate'))[:30],
                 str(eid or 'not in the dashboard')[:30], (cuvee or '')[:28]))

if a.apply:
    print('\n--apply is disabled; see the note at the top of this file. '
          'Nothing was written.')
else:
    print('\nnothing written: this tool reports and does not move.')
sys.exit(0)

for s, eid, cuvee, role in safe:
    if eid is None:
        s['estate'], s['estateName'], s['wine'] = None, None, None
        s['role'], s['how'] = 'unknown', 'another property'
        s['note'] = ((s.get('note') or '') + '; the filename names %s, '
                     'which this dashboard does not hold' % cuvee).lstrip('; ')
    elif cuvee:
        s['wine'], s['role'] = cuvee, role
        s['note'] = ((s.get('note') or '') + '; the filename names %s, '
                     'another of the estate’s wines' % cuvee).lstrip('; ')
    else:
        s['estate'] = eid
        s['estateName'] = E[eid].get('name')
        s['wine'] = E[eid].get('name')
        s['note'] = ((s.get('note') or '') + '; moved to the estate its '
                     'filename names').lstrip('; ')
io.open(ROOT + 'data/sources.json', 'w', encoding='utf-8', newline='').write(
    json.dumps(man, ensure_ascii=False, indent=1))
print('\n%d sheets moved, %d left for someone to read'
      % (len(safe), len(unsafe)))
print('now run: python tools/read-sheets.py  then  tools/check-data.py')
