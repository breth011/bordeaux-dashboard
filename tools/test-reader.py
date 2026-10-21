# -*- coding: utf-8 -*-
"""Every sheet I have had to reason about, and what it should say.

    python tools/test-reader.py

I had been re-checking these by hand after each change to the reader,
which is how a fix for one of them quietly broke another: making the
name matching boundary-aware fixed "parde" inside "marque par des" and
broke "lionsdebatailley2014", and I only noticed because a count jumped.
So they are written down.

These read the documents in sources/, which is not committed - this repo
is served by GitHub Pages and none of that material is ours to
republish. So on a fresh clone every case prints MISSING, which is
correct and not a failure: run tools/harvest.py first and the archive
comes back.

Each case names the document, what the reader should get from it, and -
in the comment - why that document is hard. A new case belongs here as
soon as a document surprises me.
"""
import glob, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr

E = sr.estates(ROOT)

# (estate, filename, expected blend or None, note)
BLEND = [
    # The labelled window beats the plantings.
    ('malartic-lagraviere',
     'Fiche_Technique_Chateau_MALARTIC_LAGRAVIERE_PEL_RO_2021_Francais.pdf',
     'CF1,CS67,ME32', 'BLEND 67% at the top, Grape varieties 56% below'),
    ('batailley', 'web-batailley2021_fr.pdf', 'CF2,CS76,ME20,PV2',
     'ENCEPAGEMENT 70/25/3/2 first, ASSEMBLAGE 2021 76/20/2/2 after'),
    # A sheet carrying two wines' blends.
    ('haut-bailly', 'fiche-technique-millesime-2021-fr.pdf',
     'CF3,CS65,ME22,PV10', 'Chateau Haut-Bailly then Haut-Bailly II'),
    ('haut-bailly', 'technical-sheet-vintage-2022-en.pdf',
     'CF2,CS56,ME37,PV5', 'the column reading mis-joins this one'),
    ('branaire-ducru', 'Ch.-Branaire-Ducru-2019-FT-FREN.pdf',
     'CF4,CS56,ME35,PV5', 'Duluc 52.5/44/2.5/1 sits in the same library'),
    # The data block beats the tasting prose.
    ('la-conseillante', 'Tech-sheet-la-Conseillante-2020.pdf', 'CF13,ME87',
     'Blend: 87/13 in the block, "blend of 80% Merlot" in the note'),
    ('dauzac', 'FT_CH-DAUZAC-2010.pdf', 'CS65,ME35',
     'Assemblage : 65/35, and "Assemblage de 66 %" in the prose'),
    ('issan', 'CHATEAU_ISSAN_2009.pdf', 'CS60,ME40',
     'Assemblage 60/40, and "blend of 62%" in the prose'),
    # Compound variety names.
    ('la-mission-haut-brion', 'Mission-Haut-Brion-2014-FT-GB.pdf',
     'CF1,CS45,ME54', 'Merlot Noir: 54% - without the suffix this read 99'),
    ('rieussec', 'Chateau-Rieussec-2018.pdf', 'SB25,SEM75',
     'Varietals : Semillon 75%, Sauvignon 25% - bare Sauvignon, white'),
    ('lafite', 'Chateau-Lafite-Rothschild-1991.pdf', 'CS36,ME64',
     'Varietals, and a genuine Merlot-led Lafite'),
    # The flat reading against the column reading. Each of these was
    # read wrong while the column reading came first, and the record
    # was right - which is how the preference came to be measured
    # rather than assumed.
    ('bourgeois-chateau-lacour-jacquet', 'Fiche-technique-LJ-2014.pdf',
     'CF2,CS55,ME40,PV3',
     'Assemblage 55/40/3/2 then Encepagement 50/45/3/2; read column by '
     'column the label acquires the encepagement'),
    ('stem-chateau-badette', 'Chateau-Badette-2015-FR.pdf', 'CF5,ME95',
     'a bare "Assemblage" heading; only the prose carries the figures, '
     'and the column reorder lends it a 90/7/3 block'),
    # The encepagement and the assemblage on one sheet.
    ('stem-chateau-villemaurine', 'fiche_technique_Villemaurine_2010.pdf',
     'CF5,ME95',
     'ENCEPAGEMENT : 80% Merlot 20% Cabernet-Franc, then ASSEMBLAGE : '
     '95% Merlot 5% Cabernet-Franc'),
    ('stem-chateau-ripeau', 'FICHE-TECHNIQUE-RIPEAU-2015-A4.pdf', 'CF10,ME90',
     'Encepagement 65/30/5, then "LE MILLESIME 2015 - Assemblage : '
     '90 % Merlot 10 % Cabernet Franc"'),
    ('stem-chateau-laroque', 'FT_NUMERIQUE_LAROQUE_2018.pdf', 'CF3,ME97',
     'a table, with the figures reached through harvest dates: "3% '
     'CABERNET FRANC ET 97% MERLOT DE SELECTION MASSALE"'),
    # Ambiguity refused.
    ('giscours', 'Giscours-Carnet-Primeurs-2025-FR.pdf', None,
     'two blends under identical headings, neither named'),
    ('giscours', 'FT-Chateau-Giscours-2025.pdf', 'CF5,CS64,ME31',
     'the estate own sheet for the same vintage'),
    ('de-carles', 'Fiche-technique-CDC-2018.pdf', 'ME100',
     "L'ASSEMBLAGE 100 % merlot, which is right for Fronsac"),
]

# (estate, filename, expected other wine or None, note)
OTHER = [
    ('branaire-ducru', 'DULUC_DE_BRANAIRE_DUCRU_2019_FR_EN.pdf',
     'Duluc de Branaire-Ducru', 'the filename names it'),
    ('branaire-ducru', 'Ch.-Branaire-Ducru-2019-FT-FREN.pdf', None, ''),
    ('de-carles', 'Fiche-technique-HC-2017.pdf',
     'Haut-Carles (prestige cuv\u00e9e)',
     'HAUT-CARLES 2017 is the title; de Carles appears lower, as owner'),
    ('de-carles', 'Fiche-technique-CDC-2018.pdf', None, ''),
    ('figeac', 'CHATEAU-FIGEAC-Datasheet-March-2021.pdf', None,
     '"Second wine: Petit-Figeac" is a fact about the estate'),
    ('pavie-macquin', 'FT-PavieMacquin-19-VFVA.pdf', None,
     '"Second vin /Second wine : Les Chenes de Macquin" likewise'),
    ('haut-bailly', 'fiche-technique-millesime-2022-fr.pdf', None,
     'names both wines, so it is the grand vin sheet too'),
    ('dauzac', 'FT_D_DE_DAUZAC_2022_FR-.pdf', 'D de Dauzac Blanc',
     'D DE DAUZAC is the title'),
    ('batailley', 'lionsdebatailley2014-web_fr.pdf', 'Lions de Batailley',
     'the filename runs the words together'),
    # The other wine's name contains the estate's, so both are in the
    # title and the one named first is the one the sheet is for.
    ('de-fieuzal', '003d410c755fdc615477e63b5647c43599a4cb1f.pdf',
     'L’Abeille de Fieuzal',
     'opens "L’Abeille rouge devoile..." - Fieuzal follows two words '
     'later, so being mentioned does not make it Fieuzal’s'),
    ('de-fieuzal', 'de-fieuzal-2009-1bcbad9f.pdf', None,
     'the grand vin, in the same folder as 57 Abeille sheets'),
]

# (estate, filename, expected answer of confirms_estate, note)
WHOSE = [
    ('malartic-lagraviere', 'diamandes-de-uco-cab-sauv-2020.pdf', 'other',
     'Diamandes de Uco, Mendoza, never mentions Malartic'),
    ('malartic-lagraviere', 'gazin-rocquencourt-red-2021.pdf', 'other',
     'names Malartic 244 characters in, where it credits the owner'),
    ('malartic-lagraviere', 'malartic-lagraviere-red-2021.pdf', 'named', ''),
    ('de-camensac', 'FT-CAM-2025-FR-EN-V2.pdf', 'folder',
     'the chateau is named only in the logo, which is an image'),
    ('batailley', 'batailley2000-web_fr.pdf', 'named',
     'the year runs onto the name; digits do not bound it'),
]

# (estate, filename, expected complaint or None, note)
COLOUR = [
    ('rieussec', 'Chateau-Rieussec-2021.pdf', None,
     'a Sauternes is made of white grapes; treating sweet as red '
     'rejected every Sauternes sheet in the archive'),
    ('coutet', None, None, 'likewise'),
    ('climens', None, None, 'likewise'),
    ('haut-brion', 'Haut-Brion-Blanc-2016-FT-GB-96.pdf',
     'the filename says it is the white', 'a red estate, white sheet'),
    ('olivier', 'Olivier-Blc-2015-FT-FR-139.pdf',
     'the filename says it is the white', 'Blc is the abbreviation'),
    ('domaine-de-chevalier', 'Chevalier-Rose-2019-FT-FR.pdf',
     'the filename says it is the rosé',
     'a rose is made from red grapes, so only the filename betrays it'),
    ('carbonnieux', 'Carbonnieux-Rge-Blc-2018-FT-FR.pdf', None,
     'one sheet for the red and the white; saying both colours is not '
     'saying the wrong one'),
]

SECOND = [
    ('belgrave-2023-fc11b611.pdf', True,
     'SE C O N D VI N D U CH AT EA U BE LG RA V E, chunk-spaced'),
    ('CHATEAU-FIGEAC-Datasheet-March-2021.pdf', False,
     '"Second wine: Petit-Figeac" is a label, 199 characters in'),
]


# ---------------------------------------------------------------------
# The field reader: what a fiche states beyond its blend.
#
# Six documents surprised me in the hour it took to write it, and each
# one is here because the obvious version of the rule got it wrong:
#
#   DEGUSTATIONS is plural, and a pattern ending at DEGUSTATION left the
#   S behind, so every Beychevelle tasting note began "S 2004 Sous sa
#   robe".
#   "le millesime" is not a heading. It is ordinary French - "plus mur
#   que le millesime precedent" - and matching it opened the window in
#   the middle of somebody else's sentence.
#   Under MILLESIME 2018 Beychevelle prints a phenology table:
#   "STADES CEPAGES Merlot Cab. Sauvignon Debourrement 30/03 5/04".
#   Under the same heading in another year it prints a cloud of brand
#   words: "Elegance Fraicheur Finesse Soyeux Fruite Exigence Passion".
#   Under DEGUSTATIONS in 2007 it prints a description of the park:
#   "Prolonge d'un vaste parc qu'anime une piece d'eau".
#   And the 2010 tasting note runs straight on into "La Revue des Vins
#   de France", which is a press citation and has its own field.
#
# (estate, filename, field, what must be true of what comes back)
FIELDS = [
    ('beychevelle', 'Beychevelle-2004-francais.pdf', 'taste',
     'starts with the wine, not with a stray S from DEGUSTATIONS',
     lambda v: v and not v.startswith('S ') and 'robe' in v.lower()),
    ('beychevelle', 'Beychevelle-2007-francais.pdf', 'taste',
     'the park description is refused',
     lambda v: v is None or 'paradis' not in v.lower()),
    ('beychevelle', 'Beychevelle-2010-francais.pdf', 'taste',
     'cut before the press citation',
     lambda v: v is None or 'revue des vins' not in v.lower()),
    ('beychevelle', 'Beychevelle-2018_FR.pdf', 'note',
     'the phenology table is not a season note',
     lambda v: v is None or 'debourrement' not in
     v.lower().replace('é', 'e')),
    ('beychevelle', 'Beychevelle-2003-francais.pdf', 'note',
     'no window opened mid-sentence on "le millesime"',
     lambda v: v is None or not v.startswith('précédent')),
    ('beychevelle', 'Beychevelle-2008-francais.pdf', 'alc',
     'the alcohol is read and gated',
     lambda v: v is not None and 10.0 <= v <= 17.0),
]


def find(eid, name):
    hit = glob.glob(os.path.join(ROOT, 'sources/fiches', eid, name))
    return hit[0] if hit else (glob.glob(
        os.path.join(ROOT, 'sources/fiches/*', name)) or [None])[0]


def fmt(b):
    return ','.join('%s%g' % kv for kv in sorted(b.items())) if b else None


fails = 0
for eid, name, want, note in BLEND:
    p = find(eid, name)
    if not p:
        print('MISSING  %s' % name)
        continue
    got = fmt(sr.blend_of(p, E[eid]['name'], E[eid]['cuvees']))
    ok = got == want
    fails += 0 if ok else 1
    print('%-4s blend   %-46s %-22s %s'
          % ('ok' if ok else 'FAIL', name[:46], str(got), '' if ok
             else '!= ' + str(want)))

for eid, name, want, note in OTHER:
    p = find(eid, name)
    if not p:
        print('MISSING  %s' % name)
        continue
    got = None
    for nm in E[eid]['cuvees']:
        if sr.names_another_wine(p, name, E[eid]['name'], nm):
            got = nm
            break
    ok = (got or None) == (want or None)
    fails += 0 if ok else 1
    print('%-4s other   %-46s %-22s %s'
          % ('ok' if ok else 'FAIL', name[:46], str(got)[:22], '' if ok
             else '!= ' + str(want)))

for eid, name, want, note in WHOSE:
    p = find(eid, name)
    if not p:
        print('MISSING  %s' % name)
        continue
    got = sr.confirms_estate(p, name, E[eid]['name'], E[eid]['cuvees'])
    ok = got == want
    fails += 0 if ok else 1
    print('%-4s whose   %-46s %-22s %s'
          % ('ok' if ok else 'FAIL', name[:46], got, '' if ok
             else '!= ' + want))

for eid, name, want, note in COLOUR:
    # No filename given means "any sheet of this estate will do", which
    # is the point for the Sauternes cases.
    p2 = find(eid, name) if name else (glob.glob(
        os.path.join(ROOT, 'sources/fiches', eid, '*.pdf')) or [None])[0]
    if not p2:
        print('MISSING  %s %s' % (eid, name))
        continue
    base = os.path.basename(p2)
    b = sr.blend_of(p2, E[eid]['name'], E[eid]['cuvees'])
    got = sr.wrong_colour(base, b, E[eid]['cat'])
    ok = (got or None) == (want or None)
    fails += 0 if ok else 1
    print('%-4s colour  %-46s %-22s %s'
          % ('ok' if ok else 'FAIL', base[:46], str(got)[:22], '' if ok
             else '!= ' + str(want)))

for name, want, note in SECOND:
    p = find('', name)
    if not p:
        print('MISSING  %s' % name)
        continue
    got = sr.is_second_wine(p)
    ok = got == want
    fails += 0 if ok else 1
    print('%-4s second  %-46s %-22s %s'
          % ('ok' if ok else 'FAIL', name[:46], got, '' if ok
             else '!= ' + str(want)))

for eid, name, field, why, test in FIELDS:
    p = find(eid, name)
    if not p:
        print('MISSING  %s' % name)
        continue
    e = E.get(eid) or {}
    got, how = sr.fields_of(p, grand=e.get('name'),
                            others=list(e.get('cuvees') or ()),
                            second=e.get('second'), cat=e.get('cat'),
                            filename=os.path.basename(p))
    v = got.get(field)
    ok = bool(test(v))
    fails += 0 if ok else 1
    shown = v if not isinstance(v, str) else (v[:34] + '...')
    print('%-4s field   %-40s %-6s %-26s %s'
          % ('ok' if ok else 'FAIL', name[:40], field,
             str(shown)[:26], '' if ok else '<- ' + why))

print('\n%s' % ('all pass' if not fails else '%d FAILED' % fails))
sys.exit(1 if fails else 0)
