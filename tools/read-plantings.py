# -*- coding: utf-8 -*-
"""What is planted in each vineyard, read off the sheets and recorded.

    python tools/read-plantings.py                 every estate
    python tools/read-plantings.py --estate dalem  one
    python tools/read-plantings.py --dry-run       print, write nothing

Writes data/plantings.js.


WHY THIS EXISTS

The single defect this dataset has suffered most is the vineyard's
encepagement recorded as the wine's assemblage. Prieure-Lichine had it
on ten vintages, Batailley on three, and this week Clos Fourtet on
five, Castera on ten and Jean Faure on eight. The figures look exactly
like a blend, because they are percentages of the same grapes adding to
a hundred, and the only thing separating them is what the sheet calls
them and whether the number moves from one year to the next.

Until now the test was repetition: a figure that never changes across a
decade is the planting. That is a proxy, and it fails. It rejected
Pichon Baron 2012, whose sheet says "ASSEMBLAGE Cabernet sauvignon 80%,
Merlot 20%" in as many words, simply because the estate blended to the
same proportions in 2014 and 2023.

Recording the planting turns the proxy into a comparison. If we know
Clos Fourtet is planted 90% Merlot, 7% Cabernet Sauvignon, 3% Cabernet
Franc, then a sheet offering exactly 90/7/3 as the 2018 assemblage is
making a claim we can check, and five sheets offering it for five
different years are not five assemblages. Pichon Baron's 80/20 matches
no planting we hold - chateaux.js has it at 70/28/2 - so nothing is
held against it.

The plantings are also worth having for their own sake. The dashboard
can say what a property grows as against what it bottled in a given
year, which is the more interesting number in a vintage where one
variety failed.


WHERE THE FIGURES COME FROM

Two places, and the file records which:

  declared   the blend already carried in data/chateaux.js, which has
             held one for the 1855 and Graves estates all along and
             which nothing read until now - sheetreader.estates() threw
             it away. 170 estates have one.
  read       a percentage block on the estate's own sheets under a
             label that means the vineyard rather than the wine:
             encepagement, cepages, grape varieties, surface en
             production, varieties planted. The figure taken is the one
             appearing on the most of that estate's sheets, and the
             sheet that gave it is named, because a planting read off
             one document is worth less than one read off nine.

A sheet that labels the figure as the wine - assemblage, blend,
composition du vin - is not read here at all. That is the assemblage,
and tools/read-sheets.py has it.

The count matters more than it looks. A planting seen on one sheet may
be that sheet's mistake; one seen on nine sheets across nine vintages
is the vineyard. Only figures seen at least twice, or declared in
chateaux.js, are written.
"""
import io, json, os, re, sys, argparse, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr

# Labels that mean the vineyard. Deliberately not "blend" or
# "assemblage": those mean the wine, and belong to read-sheets.py.
VINE = re.compile(r'(?i)\b(enc[eé]pagement(?:\s+du\s+vignoble)?|'
                  r'grape\s+varieties|varieties\s+planted|'
                  r'surface\s+en\s+production|surface\s+du\s+vignoble|'
                  r'area\s+under\s+vines?|r[eé]partition\s+du\s+vignoble)\b')
# "Cepages" on its own means either, and sheetreader counts it as a wine
# label because that is what it usually is. Reading it as a planting
# unconditionally gave Lafite a planting of CS91/ME9, which is its 2015
# assemblage. So it is accepted only when a fact about the vines stands
# just after the figures - Jean Faure writes "Cepages : 50% de Cabernet
# Franc, 45% de Merlot, 5% de Malbec Age des vignes : 45 ans", and
# Croix de Reverdi puts its under Surface, Rendements and Age du
# vignoble. That is a description of a property, not of a year.
# The group is not decoration: block() returns m.group(1) as the
# label it read under, and VINE has one. Without it every planting
# accepted through this route raised IndexError on the last line,
# and the caller's `except Exception: continue` dropped the sheet
# without counting it - so the figures were found, checked, and
# silently thrown away.
MAYBE = re.compile(r'(?i)\b(c[eé]pages?)\b')
VINEFACT = re.compile(r'(?i)\b([aâ]ge\s+(?:moyen\s+)?(?:du\s+vignoble|'
                      r'des\s+vignes)|densit[eé]|surface|superficie|'
                      r'rendements?|vines?\s+age|average\s+age|'
                      r'plantation)\b')
WINE = re.compile(r'(?i)\b(assemblage|blend|composition\s+du\s+vin|'
                  r'varietals?)\b')
# How far after the label the figures may sit.
REACH = 150


def block(text):
    """The percentages under a vineyard label, if any."""
    flat = ' '.join((text or '').split())
    # Every unambiguous vineyard label first, and only then the
    # ambiguous "cepages". Interleaving them by position let whichever
    # happened to come first on the page decide, so the same estate's
    # sheets answered differently and no figure reached the two
    # sightings needed to be written at all.
    hits = [(m, True) for m in VINE.finditer(flat)] + \
           [(m, False) for m in MAYBE.finditer(flat)]
    for m, certain in hits:
        win = flat[m.end():m.end() + REACH]
        # A wine label inside the window means the window has run on
        # into the assemblage; cut there. Castera's card puts Blend and
        # Aging back to back.
        w = WINE.search(win)
        if w:
            win = win[:w.start()]
        got = sr._from_window(win) if hasattr(sr, '_from_window') else None
        if not (got and abs(sum(got.values()) - 100) <= 1.5 and got):
            continue
        if not certain and not VINEFACT.search(win):
            continue
        return got, m.group(1).lower()
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estate', action='append', default=[])
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    E = sr.estates(ROOT)
    man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))

    # Where every file actually is, once.
    where = {}
    for root, dirs, files in os.walk(ROOT + 'sources'):
        for f in files:
            where.setdefault(f, os.path.join(root, f))

    # The declared ones, which chateaux.js has always had.
    declared = {}
    txt = io.open(ROOT + 'data/chateaux.js', encoding='utf-8').read()
    # One chunk per entry. A non-greedy match up to the next "}," looked
    # tidier and found nothing: the first "}," in an entry is the one
    # closing blend:{...} itself, so the chunk stopped one character
    # before the brace the inner pattern needed. 61 estates carry a
    # blend here and it read none of them.
    for chunk in txt.split("{id:'")[1:]:
        m = re.match(r"([a-z0-9-]+)'", chunk)
        if not m:
            continue
        b = re.search(r'blend:\{([^}]*)\}', chunk[:800])
        if b:
            d = dict((k, float(v)) for k, v in
                     re.findall(r"'?([A-Z]+)'?:\s*([\d.]+)", b.group(1)))
            if d and abs(sum(d.values()) - 100) <= 1.5:
                declared[m.group(1)] = d
    print('%d estates declare a blend in chateaux.js' % len(declared))

    want = set(a.estate) if a.estate else None
    seen = collections.defaultdict(collections.Counter)
    gave = collections.defaultdict(dict)
    read_n = 0
    for s in man['sheets']:
        eid = s.get('estate')
        if not eid or (want and eid not in want):
            continue
        # A second wine and another cuvee each have their own plantings,
        # and they are not this estate's grand vin's. Skipping only
        # 'skip' and 'page' read Giscours' planting off
        # Haut-Medoc-de-Giscours-2013-FT-FR-1055.pdf and made a
        # 60/35/3/2 estate look planted 50/50.
        if s.get('role') in ('skip', 'page', 'second', 'other'):
            continue
        # By folder, not by name: the same document is published
        # under several of an owner's properties, and a basename map
        # returns whichever copy was walked first.
        p = sr.path_of(ROOT, s, where)
        if not p or not p.lower().endswith('.pdf'):
            continue
        # And not off the other colour's sheet. La Tour Carnet came out
        # planted SB72/SEM28 - a Sauvignon and a Semillon - from
        # FT-Chateau-La-Tour-Carnet-blanc-2019-FR.pdf, at an estate
        # whose red is 62% Merlot.
        e = E.get(eid) or {}
        # The whole chain, the same one read-fiches and read-sheets
        # use, so a guard written once applies here too. No year: a
        # planting is the vineyard's and not a vintage's, so a sheet
        # filed under a year nothing states still describes the
        # vineyard it describes.
        try:
            if sr.whose_sheet(p, s['file'], e.get('name'),
                              e.get('cuvees') or (), e.get('second'),
                              e.get('cat')):
                continue
        except Exception:
            pass
        try:
            got, label = block(sr.flat(p))
        except Exception:
            continue
        read_n += 1
        if not got:
            continue
        key = tuple(sorted(got.items()))
        seen[eid][key] += 1
        gave[eid].setdefault(key, (s['file'], label))

    out, why = {}, collections.Counter()
    for eid in sorted(set(seen) | set(declared)):
        if want and eid not in want:
            continue
        row = None
        if seen.get(eid):
            key, n = seen[eid].most_common(1)[0]
            # And it has to agree with itself. The modal figure on
            # two sheets is enough to stop a one-off and not enough
            # to stop a vineyard label that reports the assemblage:
            # at Lynch-Bages the same figures appear under
            # Encepagement on the French sheet and Blending on the
            # English one for the same vintage, and its modal
            # figure holds 2 sightings out of 21.
            #
            # Asked of every document at the nine estates whose
            # blend equals their planting, the two cases separate
            # with nothing in between:
            #
            #   la-conseillante      70 of 70 sightings    100%
            #   marquis-dalesme      16 of 16              100%
            #   clos-haut-peyraguey  22 of 28               79%
            #   moulin-rouge         28 of 38               74%
            #   ----------------------------------------------
            #   haut-bages-liberal    2 of 4                50%
            #   dauzac               16 of 41               39%
            #   la-tour-carnet        5 of 25               20%
            #   lynch-bages           2 of 21               10%
            #
            # A vineyard changes over decades, not vintages.
            total = sum(seen[eid].values())
            share = (100.0 * n / total) if total else 0
            if n >= 2 and share >= 70:
                f, label = gave[eid][key]
                row = {'blend': dict(key), 'how': 'read',
                       'label': label, 'seen': n, 'src': f}
                why['read off %d or more of the estate’s sheets' % 2] += 1
            elif n >= 2:
                why['its own vineyard label disagrees with itself '
                    '(modal figure under 70% of sightings), so it '
                    'is reporting the assemblage'] += 1
            else:
                why['seen on one sheet only, not written'] += 1
        if row is None and eid in declared:
            row = {'blend': declared[eid], 'how': 'declared',
                   'label': 'data/chateaux.js', 'seen': 0, 'src': None}
            why['declared in chateaux.js'] += 1
        if row is None:
            continue
        # Where both exist and disagree, say so - it is worth a look.
        if eid in declared and row['how'] == 'read':
            if dict(row['blend']) != declared[eid]:
                row['declared'] = declared[eid]
                why['read and declared disagree'] += 1
        out[eid] = row

    print('%d sheets read, %d estates with a planting' % (read_n, len(out)))
    for k, n in why.most_common():
        print('   %-54s %d' % (k, n))

    if a.dry_run:
        for eid in sorted(out)[:40]:
            r = out[eid]
            print('   %-40s %-28s %-9s %s'
                  % (eid,
                     ','.join('%s%g' % kv
                              for kv in sorted(r['blend'].items())),
                     r['how'], (r['src'] or r['label'])[:38]))
        return 0

    o = io.open(ROOT + 'data/plantings.js', 'w', encoding='utf-8',
                newline='')
    o.write('/* =====================================================' +
            '====================\n'
            '   Bordeaux Dashboard — what is planted, per estate\n'
            '   ------------------------------------------------------'
            '-------------------\n'
            '   Built by tools/read-plantings.py. Do not edit by hand.\n'
            '\n'
            '   A planting is not an assemblage. This file exists so the\n'
            '   two can be told apart: a sheet offering a vintage blend\n'
            '   identical to the estate’s planting is making a claim\n'
            '   that tools/check-data.py will question.\n'
            '\n'
            '     how:\'read\'      a vineyard-labelled block on this\n'
            '                     estate’s own sheets, seen on `seen` of\n'
            '                     them; `src` names one\n'
            '     how:\'declared\'  carried in data/chateaux.js\n'
            '     declared:       present when the two disagree\n'
            '   ======================================================'
            '==================== */\n'
            'var BDX_PLANTINGS = {\n')
    for eid in sorted(out):
        r = out[eid]
        b = ','.join('%s:%g' % (k, v)
                     for k, v in sorted(r['blend'].items(),
                                        key=lambda kv: -kv[1]))
        bits = ["blend:{%s}" % b, "how:'%s'" % r['how'],
                "label:'%s'" % r['label'].replace("'", "\\'")]
        if r['seen']:
            bits.append('seen:%d' % r['seen'])
        if r['src']:
            bits.append("src:'%s'" % r['src'].replace("'", "\\'"))
        if r.get('declared'):
            bits.append('declared:{%s}' % ','.join(
                '%s:%g' % kv for kv in sorted(r['declared'].items(),
                                              key=lambda kv: -kv[1])))
        o.write("'%s':{%s},\n" % (eid, ','.join(bits)))
    o.write('};\n')
    o.close()
    print('written to data/plantings.js')
    return 0


if __name__ == '__main__':
    sys.exit(main())
