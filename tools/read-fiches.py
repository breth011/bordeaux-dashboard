# -*- coding: utf-8 -*-
"""Everything a fiche states, not just its blend.

    python tools/read-fiches.py                    every estate
    python tools/read-fiches.py --estate latour    one
    python tools/read-fiches.py --year 2026        one vintage
    python tools/read-fiches.py --apply            fill blanks in fiches.js

Writes reports/fiches-read.txt and reports/fiches-read.json, and with
--apply fills blank fields in data/fiches.js and records where each one
came from in data/field-src.js.


WHY THIS EXISTS

read-sheets.py proposes a blend and nothing else. Every other figure in
fiches.js was typed in by hand, which is why the dashboard looks the way
it does: blend on 78% of records, barrel months on 48%, yield 35%, new
oak 27%, alcohol 25%, pH 11%, harvest dates 7%.

Sampling 158 sheets of vintages that already have a record, and asking
of each field "does the sheet state it, and does the record hold it",
gives the size of what is being left on the floor:

    taste      59 of 158 sheets state it and the record has none
    note       48
    harvest    46
    alc        45
    oak        30
    months     29
    blend      17
    yld, press  9
    window      6
    ph, temp    5
    food        3

Projected across the 1,806 vintages that have both a sheet and a
record, about 3,500 field values. Another 156 vintages have a sheet and
no record at all.

So: one reader, every field, one pass per sheet.


WHAT IT WILL NOT DO

It never overwrites. A field already on the record stays, and a sheet
that disagrees is reported instead - because the "record only" column of
that same sample was not empty (25 blends, 18 new-oak figures, 15
yields), and those were entered from somewhere this tool cannot see.

It refuses rather than guesses. Every number is gated on a range a
Bordeaux fiche can actually state, and a figure outside it is thrown
away rather than stored:

    alc      10 - 17 % vol        ph       2.8 - 4.2
    yld      5 - 70 hl/ha         months   6 - 36
    oak      0 - 100 %            temp     12 - 22 C
    harvest  August to November   blend    sums to 100 +/- 1.5

That asymmetry matters more than it looks. A wrong number trips a gate.
Wrong prose trips nothing - it simply reads plausibly, which is how a
German wine review, a prize-draw rulebook and a barcode all got into
this dataset's descriptions. So prose is proposed and never merged by
--apply; the report is for reading.

It reuses every attribution guard in sheetreader.py rather than
inventing its own. confirms_estate, names_another_wine, wrong_colour,
is_second_wine, is_dossier. The sample that sized this work matched
Chateau L'Enclos in Pomerol against a sheet for Quinault l'Enclos, a
Saint-Emilion - the same names-containing-names trap that has cost this
project a dozen wrong blends, and it does not go away because the field
changed.

And it records where each field came from. src names the last writer,
which was tolerable while one tool wrote one field; with a reader
filling thousands, "which sheet gave me this alcohol" has to have an
answer. data/field-src.js is that answer.
"""
import io, json, os, re, sys, argparse, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr

# The rules for reading a fiche - the gates, the patterns and the
# stop-list - live in sheetreader.py with every other reading rule in
# this repository, and are called from here. They were written in this
# file first, which split the rules across two places: the guards in the
# library and the patterns in the tool. One library, so that a pattern
# that is wrong is wrong in one place.


# Fields the reader must not write, with the reason. A deleted field
# leaves no mark, so without this the next --redo writes it back: both
# of these were removed and both came straight back.
#
# This is read-sheets' PINNED, for prose.
REFUSED = {
    ('lynch-bages|2017', 'taste'):
        'not this wine: the note is the estate\'s white - "le '
        'Blanc de Lynch-Bages 2017 presente un nez '
        'particulierement expressif ... des aromes complexes de '
        'peche, de fruits blancs" - and this record is the red '
        'grand vin. It names the wine in its own second line and '
        'nothing caught it: the filename does not say white, and '
        'wrong_colour guards the assemblage, not the prose',
    # Found by translating: the first seven short advice fields held
    # three that are not advice. See the commit.
    ('belgrave|2022', 'food'):
        'not a food pairing: the window opens on the label itself - '
        '"FOOD AND WINE MATCHING" - and what follows it is the '
        'vinification, "100 % Merlot Vinification traditionnelle en '
        'cuves inox thermoregulees". The sheet prints its headings in '
        'one column and its answers in another, and flattened they '
        'meet in the wrong order',
    ('prieure-lichine|2006', 'window'):
        'not a drinking window: a tasting note that happens to begin '
        'on a year - "2025. This wine boasts a beautiful carmine red '
        'colour. The nose is fine and elegant, on a floral and fruity '
        'frame". The year is the end of the window printed above it, '
        'and the sentence after it is the note',
    ('la-tour-carnet|2011', 'food'):
        'the pairing is real - Joel Robuchon\'s turkey with truffle '
        'and chestnut confit - but it runs on into the letterhead, '
        '"Bernard Magrez Grands Vignobles - E-Mail: bernardmagrez", '
        'and the stop-list has nothing between the dish and the '
        'address',
    ('dauzac|2003', 'window'):
        'not a drinking window, or not only: "Palate: very well '
        'balanced, velvety tannins, an elegant wine to drink from now '
        'and for five to six years" is a tasting note with the window '
        'in its last clause, and the field should hold the clause or '
        'nothing',
    ('batailley|2010', 'taste'):
        'not a tasting note: Batailley\'s sheet sets the estate\'s history in a column beside it and the flat reading weaves the two together - "Il doit son nom a la derniere Robe grenat-pourpre. Nez riche et Bataille en Medoc de la guerre de cent ans expressif, fruite avec des notes (1337-1453)". Every word is whole and only the order is wrong, so no rule about spacing or capitals sees it, and it cannot be trimmed into a sentence',
    ('batailley|2016', 'taste'):
        'not a tasting note: Batailley\'s sheet sets the estate\'s history in a column beside it and the flat reading weaves the two together - "Il doit son nom a la derniere Robe grenat-pourpre. Nez riche et Bataille en Medoc de la guerre de cent ans expressif, fruite avec des notes (1337-1453)". Every word is whole and only the order is wrong, so no rule about spacing or capitals sees it, and it cannot be trimmed into a sentence',
    ('batailley|2018', 'taste'):
        'not a tasting note: Batailley\'s sheet sets the estate\'s history in a column beside it and the flat reading weaves the two together - "Il doit son nom a la derniere Robe grenat-pourpre. Nez riche et Bataille en Medoc de la guerre de cent ans expressif, fruite avec des notes (1337-1453)". Every word is whole and only the order is wrong, so no rule about spacing or capitals sees it, and it cannot be trimmed into a sentence',
    ('ducru-beaucaillou|2018', 'note'):
        'not a season note: the sheet prints the estate’s motto - '
        '"Nihil sine sole, nihil sine labore", rien sans le soleil, rien '
        'sans le travail - and then a paragraph on how the pump-overs '
        'were reduced as the density fell, which is how the wine was '
        'made and not what the year did',
    ('stem-chateau-peby-faugeres|2022', 'note'):
        'not a season note: a press release about the bottle engraved '
        'for the estate’s twenty-fifth harvest, naming Silvio Denz, '
        'Corinne Guisez and Michel Rolland, with the weather nowhere in '
        'it',
    ('bourgeois-chateau-dillon|2018', 'months'):
        'not this wine: the source is a shop page '
        'for Les Haldes de Luchey, which is Luchey-Halde\'s, and white',
    ('bourgeois-chateau-dillon|2024', 'alc'):
        'not this wine: the source is a shop '
        'page for a case of six bottles of Leonie',
    ('bourgeois-chateau-dillon|2024', 'months'):
        'not this wine: the source is a shop '
        'page for a case of six bottles of Leonie',
    ('bourgeois-chateau-paveil-de-luze|2024', 'alc'):
        'not this wine: the source is the shop\'s page for Paveil '
        'de Luze blanc',
    ('bourgeois-chateau-paveil-de-luze|2024', 'months'):
        'not this wine: the source is the shop\'s page for Paveil '
        'de Luze blanc',
    ('bourgeois-chateau-paveil-de-luze|2024', 'yld'):
        'not this wine: the source is the shop\'s page for Paveil '
        'de Luze blanc',
    ('chantegrive|2019', 'months'):
        'not this wine: the source is the product page for '
        'Les Oiseaux\' Panache',
    ('clos-haut-peyraguey|2021', 'months'):
        'not this wine: the source is a shop page for '
        'Chateau Les Grands Chenes, red, and this is a Sauternes',
    ('giscours|2021', 'blend'):
        'not this wine: 2020\'s blend, from a page Giscours '
        'published in August 2021 about the 2020 wine, and its filename '
        'says so - millesime-2020-du-chateau-giscours. The manifest filed '
        'it under the day it went up, which is how a vintage came to be '
        'read off a publication date',
    ('batailley|2019', 'window'):
        'not a drinking window: a sentence of the tasting note that ends on '
        'the words keeping potential, which the label reads as a heading',
    ('bourgeois-chateau-moulin-de-canhaut|2018', 'food'):
        'not a food pairing: marketing copy for another wine, INSULA '
        '“Amphora”, on antioxidants, with the c dropped out of concentrated '
        'by whatever extracted it',
    ('branaire-ducru|2011', 'window'):
        'not a drinking window: the tasting note\'s verdict on the vintage, '
        'ending on keeping potential',
    ('dauzac|2008', 'window'):
        'not a drinking window: the nose, from the tasting note - '
        'liquorice, camphor, grill smoke and spice',
    ('figeac|2021', 'window'):
        'not a drinking window: a remark that the young vintages drink '
        'well, which names no year and no span',
    ('guiraud|2022', 'window'):
        'not a drinking window: the tasting note\'s finish, ending on '
        'keeping potential',
    ('margaux|2022', 'food'):
        'not a food pairing: the page\'s share button and its invitation to '
        'visit - “Vous pouvez partager cette page Vous souhaitez nous '
        'rendre visite ?”',
    ('montrose|2017', 'window'):
        'not a drinking window: the tasting note\'s verdict, ending on '
        'keeping potential',
    ('olivier|2019', 'window'):
        'not a drinking window: a sentence about glutathione, ending on '
        'keeping potential',
    ('margaux|2023', 'note'):
        'not a season note: a news item about bottling - \u201cThe bottling '
        'of the 2023 vintage of Ch\u00e2teau Margaux marks a key step in the '
        'production cycle of our fine wines\u201d - with the weather nowhere '
        'in it',
    ('stem-chateau-jean-faure|2010', 'blend'):
        'not the estate’s figure: read off lvod-carnet-notes-jean-faure-2010.pdf, '
        'a merchant’s tasting notebook, which gives CF54 MA6 ME40 where the '
        'estate’s own fiche technique for 2010 gives CF50 MA5 ME45. Both are '
        'filed grand and the notebook was read first. The estate’s figure is '
        'still not being read, which is a separate complaint',
}

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estate', action='append', default=[])
    ap.add_argument('--year', type=int)
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--redo', action='store_true',
                    help='take back what this reader wrote, then re-read')
    ap.add_argument('--prose', action='store_true',
                    help='also merge taste and note, which have no gate')
    ap.add_argument('--cuvees', action='store_true',
                    help="read the estate's other wines - the "
                         'second wine, the dry white, the odd '
                         'cuvee - into data/cuvees.js')
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()

    E = sr.estates(ROOT)
    # ---------------------------------------------------- which wine
    #
    # The grand vin lives in fiches.js keyed estate|year; the
    # estate's other wines live in cuvees.js keyed estate|slug|year.
    # Between those two facts everything is the same work - the same
    # guards, the same gates, the same pins, the same refusal to
    # overwrite - so it is the same reader with the file and the key
    # as parameters rather than a second copy to fall behind.
    DATA = 'data/cuvees.js' if a.cuvees else 'data/fiches.js'
    SRCF = 'data/cuvee-src.js' if a.cuvees else 'data/field-src.js'
    # Provenance is kept apart because check-language.py checks
    # field-src.js key for key against fiches.js, and a three-part
    # key in it would read as a record that does not exist.
    KEY = (r"[a-z0-9-]+\|[a-z0-9-]+\|\d{4}" if a.cuvees
           else r"[a-z0-9-]+\|\d{4}")
    ROW = re.compile(r"^'(" + KEY + r")':\{(.*)\},$")
    HEAD = re.compile(r"^'(" + KEY + r")':\{")

    def estate_of(k):
        return k.split('|')[0]

    man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))

    # A basename is not a path. The same document is published under
    # several of an owner's properties - 2018__millesime-2018.txt is in
    # Figeac's folder and Haut-Bailly's, LR-Rapport-2023-planche.pdf in
    # four - and keying on the name alone read whichever copy os.walk
    # reached first, so Haut-Bailly's season note was proposed for La
    # Tour Figeac and Lascombes. The manifest says which folder each
    # row is in; read-sheets has always used it.
    where = {}
    for root, dirs, files in os.walk(ROOT + 'sources'):
        for f in files:
            where.setdefault(f, os.path.join(root, f))

    def resolve(s):
        """The document this manifest row is for."""
        folder = s.get('folder') or ''
        if folder:
            p = os.path.join(ROOT, 'sources',
                             folder if folder.startswith('pages')
                             else 'fiches/' + folder, s['file'])
            if os.path.exists(p):
                return p
        return where.get(s['file'])

    # Keyed by the record's own key as a string, which is the one
    # thing both shapes have in common.
    recs = {}
    for line in io.open(ROOT + DATA, encoding='utf-8'):
        m = ROW.match(line.rstrip())
        if m:
            recs[m.group(1)] = m.group(2)

    # ------------------------------------- the estate's other wines
    #
    # BDX_CUVEE_WINES is the authority on a cuvee's slug, because the
    # app looks a record up as ch.id|slug|year and takes the slug from
    # that list. Those slugs are not one rule's output - "Les Charmes
    # de Magnol" is charmes-de-magnol where "Les Brulieres de
    # Beychevelle" is les-brulieres-de-beychevelle, and 33 of the 116
    # listed cannot be derived from the name at all - so nothing here
    # recomputes one. A listed wine keeps the slug it has; a wine the
    # manifest names and the list does not is appended with sr.slug's,
    # and the app reads it back from the same list.
    WINES = {}
    CUV = ROOT + 'data/cuvees.js'
    if a.cuvees:
        wbody = io.open(CUV, encoding='utf-8').read().split(
            'window.BDX_CUVEE_WINES', 1)[1].split('window.BDX_CUVEES', 1)[0]
        for m in re.finditer(r"^'([a-z0-9-]+)':\[(.*)\],?$", wbody, re.M):
            for w in re.finditer(
                    r"\{slug:'((?:[^'\\]|\\.)*)',name:'((?:[^'\\]|\\.)*)'"
                    r",role:'([a-z]*)',colour:'([a-z]*)'\}", m.group(2)):
                WINES.setdefault(m.group(1), []).append(
                    {'slug': w.group(1),
                     'name': w.group(2).replace("\\'", "'"),
                     'role': w.group(3), 'colour': w.group(4)})

    UNLISTED = collections.Counter()

    def wine_of(eid, name):
        """The list's entry for this wine, or None.

        Matched on sheetreader's packed() form, so an accent or a
        case difference between the manifest's name and the list's
        is still one wine, and not two keys with a wine's vintages
        split between them.

        Nothing is minted. A wine the manifest names and the list
        does not is counted for the report: of the 85 the first run
        found, half were sibling properties cross-filed under each
        other, Barton & Guestier brand sheets under Magnol, or
        filename debris - mongravey under de Braude, braude under
        Mongravey, 'cci octobre2013', 'langlet bd'. A wine in that
        list is shown in the drawer as the estate's, so it goes in
        by a reviewed edit to cuvees.js and not by a reader.
        """
        want = sr.packed(name)
        for w in WINES.get(eid, ()):
            if sr.packed(w['name']) == want:
                return w
        UNLISTED[(eid, name)] += 1
        return None

    # Blanc, white, Rose: the wine's own name, which is the only
    # witness that was right about all three of Blanc de
    # Lynch-Bages (list white, row red), Rose de Chevalier (list
    # red, row rose) and Cos d'Estournel Blanc (list white, row
    # red). Asked before the list, the row and the estate.
    SAYS_WHITE = re.compile(r'(?i)\b(?:blancs?|white|bianco)\b')
    SAYS_ROSE = re.compile(u'(?i)\\b(?:ros[e\u00e9]s?|rosado)\\b')

    def cuvee_cat(name, w, s, eid):
        if SAYS_ROSE.search(name):
            return 'rose'
        if SAYS_WHITE.search(name):
            return 'white'
        return ((w or {}).get('colour') or s.get('colour')
                or (E.get(eid) or {}).get('cat'))

    todo = []
    if a.cuvees:
        # The rows the grand-vin reader skips, and has always
        # skipped: the ones a guard filed as another of the
        # estate's wines. 2,286 of them name which wine, because
        # the guard that refused them said so, and that name is
        # the attribution - it is in the row because it was read
        # in the document.
        for s in man['sheets']:
            if s.get('role') not in ('second', 'other'):
                continue
            eid, yr = s.get('estate'), s.get('year')
            nm = s.get('wine')
            if not eid or not yr or not nm:
                continue
            if a.estate and eid not in a.estate:
                continue
            if a.year and int(yr) != a.year:
                continue
            p = resolve(s)
            if not p or not (p.lower().endswith('.pdf')
                             or sr.is_page(p)):
                continue
            w = wine_of(eid, nm)
            if not w:
                continue
            sl = w['slug']
            # Every other wine of the estate, and not the estate
            # itself: a cuvee sheet carries the chateau's
            # letterhead, and listing the chateau as a rival wine
            # refuses all of them.
            rivals = [w['name'] for w in WINES.get(eid, ())
                      if w['slug'] != sl]
            aim = {'grand': nm, 'others': rivals, 'second': None,
                   'cat': cuvee_cat(nm, w, s, eid),
                   'is_second': s.get('role') == 'second'}
            todo.append(('%s|%s|%s' % (eid, sl, yr), str(yr),
                         s['file'], p, aim))
        man = {'sheets': []}
    for s in man['sheets']:
        # 'page' as well as 'grand' and 'combined'. A page's role is
        # 'page' because nobody has judged which wine it is for, and
        # the guards judge it now; the roles that are a judgement -
        # skip, second, other, group report - are still respected.
        # `unknown` is harvest.py's default - nobody has looked -
        # and read-sheets.py has always read those, which is why
        # Cantenac-Brown's blends are complete and its alcohol,
        # yield and picking dates are not: 72 of its own fiches sit
        # at that default and this reader never opened one. The
        # manifest role is a cache of what the guards said, not a
        # gate; whose_sheet runs on every document here anyway, and
        # refuses BriO and Alto by name as it always did.
        if s.get('role') not in ('grand', 'combined', 'page',
                                 'unknown'):
            continue
        eid, yr = s.get('estate'), s.get('year')
        if not eid or not yr:
            continue
        if a.estate and eid not in a.estate:
            continue
        if a.year and int(yr) != a.year:
            continue
        p = resolve(s)
        # A crawled page is text, not PDF, and sheetreader reads both.
        if p and (p.lower().endswith('.pdf') or sr.is_page(p)):
            e = E.get(eid) or {}
            todo.append(('%s|%s' % (eid, yr), str(yr), s['file'], p,
                         {'grand': e.get('name'),
                          'others': list(e.get('cuvees') or ()),
                          'second': e.get('second'),
                          'cat': e.get('cat')}))
    if a.limit:
        todo = todo[:a.limit]
    print('%d documents to read' % len(todo))

    found, why = [], collections.Counter()
    for key, yr, f, p, aim in todo:
        eid = estate_of(key)
        # The guards and the reading are both sheetreader's now. It
        # returns {'refused': why} instead of fields when a sheet is a
        # dossier, another of the estate's wines, the other colour or a
        # sibling property's.
        got, how = sr.fields_of(p, filename=f, year=yr, **aim)
        if 'refused' in how:
            why[how['refused']] += 1
            continue
        if not got:
            why['the sheet states none of these fields'] += 1
            continue
        body = recs.get(key, '')
        held = set(re.findall(r'(?:^|,)([a-z]+[a-z0-9]*)[:\{]', body))
        found.append({'key': key, 'estate': eid, 'year': yr, 'src': f,
                      'got': got, 'how': how,
                      'new': sorted(set(got) - held),
                      'held': sorted(set(got) & held),
                      'record': bool(body)})

    o = io.open(ROOT + 'reports/fiches-read.txt', 'w', encoding='utf-8',
                newline='')
    gain = collections.Counter()
    for r in found:
        for f in r['new']:
            gain[f] += 1
    o.write('%d sheets read, %d state something\n\n' % (len(todo), len(found)))
    o.write('fields a sheet states that the record does not hold:\n')
    for f, n in gain.most_common():
        o.write('   %-8s %5d\n' % (f, n))
    o.write('\nrefused:\n')
    for k, n in why.most_common():
        o.write('   %-52s %d\n' % (str(k)[:52], n))
    o.write('\n')
    for r in sorted(found, key=lambda x: x['key']):
        if not r['new']:
            continue
        o.write('%s  %s\n' % (r['key'], r['src'][:58]))
        for f in r['new']:
            v = r['got'][f]
            v = v if not isinstance(v, str) else v[:96]
            o.write('    + %-8s %s\n' % (f, v))
            o.write('      %-8s said: %s\n' % ('', r['how'].get(f, '')))
    o.close()

    json.dump(found, io.open(ROOT + 'reports/fiches-read.json', 'w',
                             encoding='utf-8'), ensure_ascii=False,
              indent=1)
    print('%d sheets state something; %d field values the records lack'
          % (len(found), sum(gain.values())))
    for f, n in gain.most_common():
        print('   %-8s %5d' % (f, n))
    print('\nrefused:')
    for k, n in why.most_common(8):
        print('   %-52s %d' % (str(k)[:52], n))
    # An unlabelled page opening that is word for word the same on
    # several of an estate's vintages is the site's standing
    # description of the wine. Beychevelle's is on nineteen pages, from
    # 2000 to 2025. Only candidates that had no label are judged this
    # way: a labelled note may repeat, and Coutet's does.
    TEMPLATE = collections.defaultdict(set)
    for r in found:
        for f in ('taste', 'note'):
            if f in r['got'] and not (r.get('how') or {}).get(f):
                TEMPLATE[(r['estate'], f, r['got'][f][:120])].add(
                    str(r['year']))
    boiler = set(k for k, v in TEMPLATE.items() if len(v) > 1)

    # And an unlabelled opening that is the season note, which is what
    # Haut-Bailly's vintage articles are: their first paragraph is the
    # year's story, and the record holds it as the note already.
    def SAME_AS_NOTE(r):
        t = (r.get('got') or {}).get('taste')
        if not t or (r.get('how') or {}).get('taste'):
            return False
        head = t[:80]
        if head and head in ((r.get('got') or {}).get('note') or ''):
            return True
        # And against the note the record already holds. r['record'] is
        # a flag, not the record - recs holds the line itself, keyed by
        # the estate and the year as strings.
        #
        # The note, and not the whole line: the line holds the tasting
        # note too, so this matched a candidate against itself. Once
        # written, a tasting note was refused on the next run as a
        # duplicate of the season note. Nothing showed while the field
        # was held - it would have been skipped anyway - but --redo
        # takes the field back and then refuses it, and Margaux lost
        # 21 tasting notes that way.
        body = recs.get(r['key']) or ''
        held = re.search(r"(?:^|,)note:'((?:[^'\\]|\\.)*)'", body)
        return bool(head and held and head in held.group(1))
    if boiler:
        print('%d unlabelled page openings repeat across an estate’s '
              'vintages, so they are the site’s description of the '
              'wine and not a vintage’s:' % len(boiler))
        for eid, f, head in sorted(boiler)[:8]:
            print('   %-30s %-6s %d vintages: %s'
                  % (eid[:30], f, len(TEMPLATE[(eid, f, head)]),
                     head[:60]))

    if UNLISTED:
        u = io.open(ROOT + 'reports/cuvee-wines-unlisted.txt', 'w',
                    encoding='utf-8', newline='')
        u.write('Wines the manifest names that BDX_CUVEE_WINES does '
                'not hold.\n\nTheir documents were not read. A wine '
                'in that list is shown in the\ndrawer as one of the '
                'estate\u2019s wines, so it goes in by a reviewed '
                'edit to\ndata/cuvees.js and not by a reader - '
                'because half of these are sibling\nproperties '
                'cross-filed under each other, brand sheets, or '
                'filename\ndebris.\n\n')
        for (eid, nm), n in sorted(UNLISTED.items(),
                                   key=lambda kv: (-kv[1], kv[0])):
            u.write('%-32s %-40s %3d document(s)\n'
                    % (eid[:32], nm[:40], n))
        u.close()
        print('%d wine(s) the list does not hold, on %d document(s)'
              ' - reports/cuvee-wines-unlisted.txt'
              % (len(UNLISTED), sum(UNLISTED.values())))
    print('\nreport in reports/fiches-read.txt')
    if not a.apply:
        print('nothing written to fiches.js; read the report, then --apply')
        return 0

    # ------------------------------------------------------------ apply
    #
    # Numbers only unless --prose is given. Every number has passed a
    # gate - a range a Bordeaux fiche can state - and a figure outside
    # it was thrown away rather than stored. Prose has no gate; it reads
    # plausibly whatever it says, which is how a German wine review, a
    # phenology table and a description of a park all got as far as they
    # did. So prose is opt-in and the report is there to be read first.
    NUMERIC = ('alc', 'ph', 'yld', 'months', 'oak', 'temp', 'pick',
               'wy', 'blend', 'sug', 'ta')
    PROSE = ('taste', 'note', 'window', 'decant', 'food')
    fields = NUMERIC + (PROSE if a.prose else ())

    def render(f, v):
        if f == 'pick':
            return 'pick:{%s}' % ','.join(
                "%s:'%s'" % kv for kv in sorted(v.items()))
        if f == 'temp':
            return 'temp:[%s]' % ','.join('%g' % x for x in v)
        if f == 'sug':
            # Residual sugar in g/l, and whether the sheet said "less
            # than". Not a Sauternes field: Pedesclaux's Pauillac
            # states "< 2 g/l" and that is a reading, not a miss.
            return 'sug:%g%s' % (v[0], ',sugl:1' if v[1] else '')
        if f == 'ta':
            # Total acidity, with the scale the sheet named. Bordeaux
            # quotes two - 3.7 g/l H2SO4 is about 5.7 g/l tartaric -
            # and 208 of 229 sheets name neither, which is recorded as
            # '?' rather than guessed. Nothing is converted.
            return "ta:%g,tau:'%s'" % (v[0], v[1])
        if f == 'wy':
            return 'wy:[%d,%d]' % (v[0], v[1])
        if f == 'blend':
            # Sorted by variety, as read-sheets writes it.
            return 'blend:{%s}' % ','.join('%s:%g' % kv
                                           for kv in sorted(v.items()))
        if f == 'months':
            return "months:'%s'" % v
        if f in PROSE:
            return "%s:'%s'" % (f, str(v).replace('\\', '\\\\')
                                .replace("'", "\\'"))
        return '%s:%g' % (f, v)

    # one proposal per record: the first sheet that offers each field,
    # so provenance is a filename and not a guess
    # Built from everything the sheet states, not from the fields the
    # record was missing when it was read. Those two differ once --redo
    # is in play: the "new" list is computed before the taking-back, so
    # a field just taken back is not in it and would never be written
    # again. Whether to write is decided at write time, against the line
    # as it then stands.
    best = {}
    for r in sorted(found, key=lambda x: (x['key'], x['src'])):
        key = r['key']
        for f in r['got']:
            if f not in fields:
                continue
            if (f in ('taste', 'note')
                    and not (r.get('how') or {}).get(f)
                    and (r['estate'], f,
                         r['got'][f][:120]) in boiler):
                continue
            if f == 'taste' and SAME_AS_NOTE(r):
                continue
            best.setdefault(key, {}).setdefault(f, (r['got'][f], r['src']))

    lines = io.open(ROOT + DATA, encoding='utf-8').read().split('\n')
    prov = {}
    pf = ROOT + SRCF
    if os.path.exists(pf):
        for line in io.open(pf, encoding='utf-8'):
            m = ROW.match(line.rstrip())
            if m:
                prov[m.group(1)] = dict(
                    re.findall(r"([a-z]+[a-z0-9]*):'([^']*)'", m.group(2)))

    # --redo: take back what this reader wrote, so a corrected rule can
    # write it again. --apply never overwrites, which is right - a field
    # entered from somewhere this tool cannot see must not be replaced
    # by a guess. But it also means a reader bug is permanent, and there
    # was one: Coutet prints "DATES DE VENDANGES" with no colon, the
    # stop-list wanted a colon, and six season notes swallowed the whole
    # technical block down to "MISE EN BOUTEILLES Juin 2013".
    #
    # This is only safe because data/field-src.js says, field by field,
    # which ones came from the reader. Nothing else is touched.
    # Scoped to the records this run actually read, and not to every
    # record provenance knows about. Run as --estate coutet --redo the
    # unscoped version took back 1,842 fields across all 468 estates and
    # then wrote back only Coutet's, because the read was scoped and the
    # taking-back was not. A repair that is wider than the thing being
    # repaired is not a repair.
    in_scope = set(t[0] for t in todo)
    undone = collections.Counter()
    if a.redo:
        for i, line in enumerate(lines):
            m = ROW.match(line)
            if not m or m.group(1) not in prov:
                continue
            if m.group(1) not in in_scope:
                continue
            key, body = m.group(1), m.group(2)
            # A field the reader wrote and a translator then rewrote is
            # still, to field-src, the reader's - so a --redo took back
            # La Tour Blanche's eighteen tasting notes and Coutet's
            # season notes and read the French in again, and French in
            # an English field went from 146 to 186 in one run. The
            # records already say which fields were translated: ttl for
            # taste, ntl for note, wtl, dtl, ftl for the rest. Those are
            # not the reader's to take back.
            TRANSLATED = {'taste': 'ttl', 'note': 'ntl', 'window': 'wtl',
                          'decant': 'dtl', 'food': 'ftl'}
            for f in sorted(prov[key]):
                if f not in fields:
                    continue
                flag = TRANSLATED.get(f)
                if flag and re.search(r'(?:^|,)' + flag + r':1\b', body):
                    continue
                v = re.search(r'(?:^|,)' + f + r"(?::'(?:[^'\\]|\\.)*'"
                              r"|:\{[^}]*\}|:[\d.]+|:\[[^\]]*\])", body)
                if v:
                    body = (body[:v.start()] + body[v.end():]).lstrip(',')
                    undone[f] += 1
                    prov[key].pop(f, None) if isinstance(
                        prov[key], dict) else prov[key].discard(f)
            if body != m.group(2):
                lines[i] = "'%s':{%s}," % (key, body)
        print('%d field values taken back for re-reading' % sum(
            undone.values()))

    # THE PIN LIST, WHICH IS A DECISION AND NOT A NOTE. --redo takes
    # back what field-src.js credits the reader with, and field-src is
    # rewritten whole each run: once a guard refuses a document, the
    # provenance row empties and nothing can reach the value any more.
    # So the pins are applied from the pins, and nothing else.
    gone = collections.Counter()
    TL_FLAG = {'taste': 'ttl', 'note': 'ntl', 'window': 'wtl',
               'decant': 'dtl', 'food': 'ftl'}
    for i, line in enumerate(lines):
        m = ROW.match(line)
        if not m:
            continue
        pk, body = m.group(1), m.group(2)
        if a.estate and estate_of(pk) not in a.estate:
            continue
        for f in sorted(set(f for k, f in REFUSED if k == pk)):
            v = re.search(r"(?:^|,)" + f + r"(?::'(?:[^'\\]|\\.)*'"
                          r"|:\{[^}]*\}|:[\d.]+|:\[[^\]]*\])", body)
            if not v:
                continue
            body = (body[:v.start()] + body[v.end():]).lstrip(',')
            gone[f] += 1
            # A translation of a value that was never this wine's is
            # not work worth keeping, so the flag goes with it.
            flag = TL_FLAG.get(f)
            if flag:
                fm = re.search(r"(?:^|,)" + flag + r":1\b", body)
                if fm:
                    body = (body[:fm.start()]
                            + body[fm.end():]).lstrip(',')
            prov.get(pk, {}).pop(f, None)
        if body != m.group(2):
            lines[i] = "'%s':{%s}," % (pk, body)
    if gone:
        print('%d field value(s) withdrawn, pinned absent: %s'
              % (sum(gone.values()),
                 ', '.join('%s %d' % kv for kv in
                           sorted(gone.most_common()))))


    wrote = collections.Counter()
    refused = collections.Counter()
    for i, line in enumerate(lines):
        m = ROW.match(line)
        if not m:
            continue
        key = m.group(1)
        if key not in best:
            continue
        body = m.group(2)
        held = set(re.findall(r'(?:^|,)([a-z]+[a-z0-9]*)[:\{]', body))
        add, pk = [], key
        for f, (v, src) in sorted(best[key].items()):
            if f in held:          # never overwrite
                continue
            if (pk, f) in REFUSED:
                refused[f] += 1
                continue
            add.append(render(f, v))
            prov.setdefault(pk, {})[f] = src
            wrote[f] += 1
        if not add:
            continue
        lines[i] = "'%s':{%s,%s}," % (pk, body, ','.join(add))

    # NEW RECORDS. A vintage with a sheet and no record was read and
    # dropped: 106 of them, holding 224 values. The record is created
    # from what the sheet states, with src naming the sheet that gave
    # the most of it - the same provenance any other record carries.
    seen = set()
    for line in lines:
        m = HEAD.match(line)
        if m:
            seen.add(m.group(1))
    fresh = sorted(k for k in best if k not in seen)
    made = []
    for key in fresh:
        pk = key
        who = collections.Counter(s for v, s in best[key].values())
        add = [render(f, v) for f, (v, s) in sorted(best[key].items())
               if (pk, f) not in REFUSED]
        if not add:
            continue
        add.append("src:'%s'" % who.most_common(1)[0][0])
        made.append("'%s':{%s}," % (pk, ','.join(add)))
        for f, (v, s) in best[key].items():
            prov.setdefault(pk, {})[f] = s
            wrote[f] += 1
    if made:
        at = max(i for i, l in enumerate(lines) if l.strip() == '};')
        lines[at:at] = made

    io.open(ROOT + DATA, 'w', encoding='utf-8',
            newline='').write('\n'.join(lines))

    o = io.open(pf, 'w', encoding='utf-8', newline='')
    o.write('/* =====================================================' +
            '====================\n'
            '   Bordeaux Dashboard — which sheet each field came from\n'
            '   ------------------------------------------------------'
            '-------------------\n'
            '   Built by tools/read-fiches.py. Do not edit by hand.\n'
            '\n'
            '   src on a record names the last writer, which was enough\n'
            '   while one tool wrote one field. With a reader filling\n'
            '   thousands, "which sheet gave me this alcohol" has to\n'
            '   have an answer, and this is it: one filename per field,\n'
            '   per vintage. A field absent here was entered by hand or\n'
            '   predates the reader.\n'
            '   ======================================================'
            '==================== */\n' +
            ('window.BDX_CUVEE_SRC = {\n' if a.cuvees
             else 'window.BDX_FIELD_SRC = {\n'))
    for k in sorted(prov):
        o.write("'%s':{%s},\n" % (k, ','.join(
            "%s:'%s'" % (f, prov[k][f].replace("'", "\\'"))
            for f in sorted(prov[k]))))
    o.write('};\n')
    o.close()

    if refused:
        print('\n%d field values the pin list refuses: %s'
              % (sum(refused.values()), dict(refused)))
    if made:
        print('\n%d records created for vintages that had none'
              % len(made))
    print('\n%d field values written into %s:'
          % (sum(wrote.values()), DATA))
    for f, n in wrote.most_common():
        print('   %-8s %5d' % (f, n))
    print('provenance for %d records in %s' % (len(prov), SRCF))
    _refresh_progress()
    print('\nnow run: python tools/check-data.py  and  check-language.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())
