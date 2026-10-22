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
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estate', action='append', default=[])
    ap.add_argument('--year', type=int)
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--redo', action='store_true',
                    help='take back what this reader wrote, then re-read')
    ap.add_argument('--prose', action='store_true',
                    help='also merge taste and note, which have no gate')
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()

    E = sr.estates(ROOT)
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

    recs = {}
    for line in io.open(ROOT + 'data/fiches.js', encoding='utf-8'):
        m = re.match(r"^'([a-z0-9-]+)\|(\d{4})':\{(.*)\},$", line.rstrip())
        if m:
            recs[(m.group(1), m.group(2))] = m.group(3)

    todo = []
    for s in man['sheets']:
        # 'page' as well as 'grand' and 'combined'. A page's role is
        # 'page' because nobody has judged which wine it is for, and
        # the guards judge it now; the roles that are a judgement -
        # skip, second, other, group report - are still respected.
        if s.get('role') not in ('grand', 'combined', 'page'):
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
            todo.append((eid, str(yr), s['file'], p))
    if a.limit:
        todo = todo[:a.limit]
    print('%d documents to read' % len(todo))

    found, why = [], collections.Counter()
    for eid, yr, f, p in todo:
        e = E.get(eid) or {}
        # The guards and the reading are both sheetreader's now. It
        # returns {'refused': why} instead of fields when a sheet is a
        # dossier, another of the estate's wines, the other colour or a
        # sibling property's.
        got, how = sr.fields_of(
            p, grand=e.get('name'), others=list(e.get('cuvees') or ()),
            second=e.get('second'), cat=e.get('cat'), filename=f,
            year=yr)
        if 'refused' in how:
            why[how['refused']] += 1
            continue
        if not got:
            why['the sheet states none of these fields'] += 1
            continue
        body = recs.get((eid, yr), '')
        held = set(re.findall(r'(?:^|,)([a-z]+[a-z0-9]*)[:\{]', body))
        found.append({'estate': eid, 'year': yr, 'src': f,
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
    for r in sorted(found, key=lambda x: (x['estate'], x['year'])):
        if not r['new']:
            continue
        o.write('%s|%s  %s\n' % (r['estate'], r['year'], r['src'][:58]))
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
        body = recs.get((r['estate'], str(r['year']))) or ''
        return bool(head and head in body)
    if boiler:
        print('%d unlabelled page openings repeat across an estate’s '
              'vintages, so they are the site’s description of the '
              'wine and not a vintage’s:' % len(boiler))
        for eid, f, head in sorted(boiler)[:8]:
            print('   %-30s %-6s %d vintages: %s'
                  % (eid[:30], f, len(TEMPLATE[(eid, f, head)]),
                     head[:60]))

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
               'wy', 'blend')
    PROSE = ('taste', 'note', 'window', 'decant', 'food')
    fields = NUMERIC + (PROSE if a.prose else ())

    def render(f, v):
        if f == 'pick':
            return 'pick:{%s}' % ','.join(
                "%s:'%s'" % kv for kv in sorted(v.items()))
        if f == 'temp':
            return 'temp:[%s]' % ','.join('%g' % x for x in v)
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
    for r in sorted(found, key=lambda x: (x['estate'], x['year'], x['src'])):
        key = (r['estate'], r['year'])
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

    lines = io.open(ROOT + 'data/fiches.js', encoding='utf-8').read().split(
        '\n')
    prov = {}
    pf = ROOT + 'data/field-src.js'
    if os.path.exists(pf):
        for line in io.open(pf, encoding='utf-8'):
            m = re.match(r"^'([a-z0-9-]+\|\d{4})':\{(.*)\},$", line.rstrip())
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
    in_scope = set('%s|%s' % (eid, yr) for eid, yr, f, p in todo)
    undone = collections.Counter()
    if a.redo:
        for i, line in enumerate(lines):
            m = re.match(r"^'([a-z0-9-]+\|\d{4})':\{(.*)\},$", line)
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

    wrote = collections.Counter()
    refused = collections.Counter()
    for i, line in enumerate(lines):
        m = re.match(r"^'([a-z0-9-]+)\|(\d{4})':\{(.*)\},$", line)
        if not m:
            continue
        key = (m.group(1), m.group(2))
        if key not in best:
            continue
        body = m.group(3)
        held = set(re.findall(r'(?:^|,)([a-z]+[a-z0-9]*)[:\{]', body))
        add, pk = [], '%s|%s' % key
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
        m = re.match(r"^'([a-z0-9-]+)\|(\d{4})':\{", line)
        if m:
            seen.add((m.group(1), m.group(2)))
    fresh = sorted(k for k in best if k not in seen)
    made = []
    for key in fresh:
        pk = '%s|%s' % key
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

    io.open(ROOT + 'data/fiches.js', 'w', encoding='utf-8',
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
            '==================== */\n'
            'window.BDX_FIELD_SRC = {\n')
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
    print('\n%d field values written into data/fiches.js:'
          % sum(wrote.values()))
    for f, n in wrote.most_common():
        print('   %-8s %5d' % (f, n))
    print('provenance for %d records in data/field-src.js' % len(prov))
    print('\nnow run: python tools/check-data.py  and  check-language.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())
