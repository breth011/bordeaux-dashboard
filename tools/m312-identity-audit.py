"""M3.12: an audit of the P1 batch's identity refusals - is the reader right to refuse, or is it misreading?

    python tools/m312-identity-audit.py            write data/audit/m3.12-identity-refusal-audit.jsonl and the report
    python tools/m312-identity-audit.py --check    both are current

The P1 review (tools/m312-p1-review.py) refused 112 datapoints on the reader's identity gate: ESTATE_ONLY (the document
names the estate, not the wine) and VINTAGE_AMBIGUOUS (it does not settle the year). They come from 82 (document,
wine, vintage) claims on 80 documents. Each claim was read - its opening, the lines naming the year, the estate's other
wines and its file series - and given one class below by hand (CLASSIFIED). The tool holds that reading, checks it
against the held text (every quote must occur in the document as held, NFC and spacing aside), and writes it out.

A review, not an application: no reader rule, evidence decision, model row or app file is changed. The reader, its
fingerprint and the review are M3.9's and M3.12's, unchanged. A reader change that this audit argues for is its own
phase: tools/sheetreader.py and tools/read-fiches.py are fingerprinted into every evidence decision.
"""
import collections
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import migration_lib as L  # noqa: E402

REVIEW = L.ROOT + 'data/audit/m3.12-p1-review.jsonl'
OUT = L.ROOT + 'data/audit/m3.12-identity-refusal-audit.jsonl'
DOC = L.ROOT + 'docs/PHASE-M3.12-IDENTITY-REFUSAL-AUDIT.md'
EXTRACTED = L.ROOT + 'sources/discovery/extracted/'
REFUSALS = ('ESTATE_ONLY', 'VINTAGE_AMBIGUOUS')

# class: (verdict, what the class means)
CLASSES = collections.OrderedDict([
    ('GRAND_VIN_NAMED_AS_ESTATE', ('READER_DEFECT', 'the text names "Château X" with the year; X is the estate and '
                                   'its grand vin, and the reader takes the name as the estate\'s only')),
    ('HEADING_EXTRACTED_LATE', ('READER_DEFECT', 'the wine and the year are stated (a heading or a titled line), but '
                                'after the opening the reader checks: the PDF\'s layout puts the heading last, or estate '
                                'boilerplate comes first')),
    ('NON_VINTAGE_YEARS_COUNTED', ('READER_DEFECT', 'the opening\'s other years are not vintages of the document - a '
                                   'comparison, a planting or certification date, a drinking window, the previous '
                                   'autumn\'s weather - and the reader counts them as a multi-vintage document')),
    ('FILENAME_SERIES_ONLY', ('READER_DEFECT', 'the text never names the wine; the estate publishes one file series '
                              'per wine (Desmirail\'s FT-DM, FT-IDM, FT-IRIS-POURPRE; Issan\'s CHATEAU_, BLASON_, '
                              'MOULIN_ISSAN), and the series names it')),
    ('WEB_PAGE_VINTAGE_SELECTOR', ('NEEDS_STRUCTURE', 'a web page whose title names the wine and the year, carrying a '
                                   'selector of the other years: the year is the page\'s only if the held structure '
                                   'shows which panel the figures belong to')),
    ('LEAD_WRONG_WINE', ('CORRECT_REFUSAL', 'the document is another wine\'s: the P1 lead was wrong')),
    ('LEAD_WRONG_VINTAGE', ('CORRECT_REFUSAL', 'the document is another year\'s, or its year is genuinely unclear')),
    ('ESTATE_WIDE_DOCUMENT', ('CORRECT_REFUSAL', 'a document about the estate\'s whole range or campaign, not one wine')),
    ('YEAR_NOT_IN_TEXT', ('CORRECT_REFUSAL', 'the text states no year at all; only the file name does')),
    ('COLOUR_NOT_IN_MODEL', ('MODEL_GAP', 'the estate makes a red and a white under one name and the model holds one '
                             'wine: no reader can say which colour the model\'s wine is')),
])

GM = 'ChateauGrandMayne%d.pdf'
CL = 'COUHINS-LURTON %s %d'
DM = 'FT-DM-%d-FR.pdf'
DM_NOTE = ('the series FT-DM is the grand vin\'s: the site also publishes FT-IDM (Initial de Desmirail), '
           'FT-IRIS-POURPRE-DE-DESMIRAIL and FICHE-TECHNIQUE-INITIAL')
GM_NOTE = 'the heading "CHATEAU GRAND MAYNE grand cru classé %d" is the last text the PDF yields'
CL_NOTE = 'the %s; the model holds one Couhins-Lurton wine'

# (file name, wine, vintage): (class, quote, note) - the reading, by hand
CLASSIFIED = {
    ('Fiche-Technique-Biston-2021-v2.pdf', 'wn_00053', 2021): ('GRAND_VIN_NAMED_AS_ESTATE', 'Château Biston', 'Millésime 2021 heads the sheet'),
    ('Fiche_Technique_BB_2023_ok.pdf', 'wn_00053', 2023): ('GRAND_VIN_NAMED_AS_ESTATE', 'Château Biston-Brillette', 'Millésime 2023 heads the sheet'),
    ('CS_RIveDroite_Mill2025.pdf', 'wn_00220', 2025): ('LEAD_WRONG_WINE', 'Château Le Prieuré 2025', 'a Rive Droite sheet: the group\'s Saint-Émilion estate, not Calon-Ségur'),
    ('CalonSe%CC%81gur_FicheTechnique_FR_2018.pdf', 'wn_00220', 2018): ('GRAND_VIN_NAMED_AS_ESTATE', 'Château Calon Ségur 2018', ''),
    ('2009_Ch-CouhinsLurton_blanc-pdf.pdf', 'wn_00241', 2009): ('COLOUR_NOT_IN_MODEL', CL % ('BLANC', 2009), CL_NOTE % 'blanc'),
    ('chateau-darmailhac-1992', 'wn_00247', 1992): ('GRAND_VIN_NAMED_AS_ESTATE', "CHÂTEAU d'ARMAILHAC 1992", 'a web page'),
    ('CHATEAU_ISSAN_2008.pdf', 'wn_00283', 2008): ('GRAND_VIN_NAMED_AS_ESTATE', 'Issan 2008', ''),
    ('CHATEAU_ISSAN_2012.pdf', 'wn_00283', 2012): ('GRAND_VIN_NAMED_AS_ESTATE', 'The 2012 Issan', 'the critic sets it against "the second wine"'),
    ('CHATEAU_ISSAN_2010.pdf', 'wn_00283', 2010): ('FILENAME_SERIES_ONLY', 'moated castle', 'the text names Issan only in its address; the site publishes CHATEAU_ISSAN (26), BLASON_ISSAN (11) and MOULIN_ISSAN (21)'),
    ('dossier-primeurs-lp2024-fr-web.pdf', 'wn_00318', 2024): ('ESTATE_WIDE_DOCUMENT', 'PRIMEURS 2024', 'the estate\'s primeurs dossier'),
    ('Chateau-Croix-Cardinale-2024-Technical-Sheet.pdf', 'wn_00395', 2024): ('LEAD_WRONG_WINE', '14,000 bottles', 'Château Croix Cardinale, 5 ha: not Fleur Cardinale and not in the model'),
    ('ChateauGrandMayne1955.pdf', 'wn_00402', 1955): ('GRAND_VIN_NAMED_AS_ESTATE', 'CHATEAU GRAND MAYNE grand cru classé 1955', ''),
    ('Chateau-Grand-Mayne-2009.pdf', 'wn_00402', 2009): ('GRAND_VIN_NAMED_AS_ESTATE', 'CHATEAU GRAND MAYNE grand cru classé 2009', ''),
    ('Chateau-Grand-Mayne-2008.pdf', 'wn_00402', 2008): ('GRAND_VIN_NAMED_AS_ESTATE', 'CHATEAU GRAND MAYNE grand cru classé 2008', ''),
    ('presentation-A3-Jean-Faure-FR_compressed.pdf', 'wn_00405', 2025): ('GRAND_VIN_NAMED_AS_ESTATE', '2025 - Millésime Surya', 'a vintage presentation; the estate holds one wine'),
    ('Carnet-millesime-2022-EN.pdf', 'wn_00422', 2022): ('GRAND_VIN_NAMED_AS_ESTATE', 'Discover and taste our 2022 vintage', ''),
    ('YF-fr_compressed.pdf', 'wn_00438', 2016): ('LEAD_WRONG_VINTAGE', 'Vinous April 2016', 'press of April 2016 is a primeurs note on 2015: the year is unclear'),
    ('chateau-beaumont', 'wn_00044', 2025): ('WEB_PAGE_VINTAGE_SELECTOR', 'Select a vintage to view its details', ''),
    ('Fiche-Technique-Biston-2020.pdf', 'wn_00053', 2020): ('YEAR_NOT_IN_TEXT', 'Château Biston', ''),
    ('Fiche-Technique-Biston-2019-1.pdf', 'wn_00053', 2019): ('YEAR_NOT_IN_TEXT', 'Château Biston', ''),
    ('fiche-technique-chateau-du-taillan-2025.pdf', 'wn_00089', 2025): ('NON_VINTAGE_YEARS_COUNTED', 'la plus jeune de 2016', 'and "certifiée HVE en Juillet 2018"; Millésime 2025 heads it'),
    ('FT-Chateau-Paloumey-2022-fr-1.pdf', 'wn_00167', 2022): ('HEADING_EXTRACTED_LATE', 'Château Paloumey 2022', ''),
    ('Fiche-technique-FR-CHATEAU-CAILLOU-2014-AOC-Barsac.pdf', 'wn_00219', 2014): ('HEADING_EXTRACTED_LATE', 'CHATEAU CAILLOU 2014', 'after the estate\'s presentation'),
    ('CouhinsLurton_R2019_FR.pdf', 'wn_00241', 2019): ('COLOUR_NOT_IN_MODEL', CL % ('ROUGE', 2019), CL_NOTE % 'rouge'),
    ('2015-R-Ch-Couhins-Lurton.pdf', 'wn_00241', 2015): ('COLOUR_NOT_IN_MODEL', CL % ('ROUGE', 2015), CL_NOTE % 'rouge'),
    ('2011-R-Ch-Couhins-Lurton.pdf', 'wn_00241', 2011): ('COLOUR_NOT_IN_MODEL', CL % ('ROUGE', 2011), CL_NOTE % 'rouge'),
    ('CouhinsLurton_R2018_FR.pdf', 'wn_00241', 2018): ('COLOUR_NOT_IN_MODEL', CL % ('ROUGE', 2018), CL_NOTE % 'rouge'),
    ('2013-R-Ch-Couhins-Lurton.pdf', 'wn_00241', 2013): ('COLOUR_NOT_IN_MODEL', CL % ('ROUGE', 2013), CL_NOTE % 'rouge'),
    ('2014-R-Ch-Couhins-Lurton.pdf', 'wn_00241', 2014): ('COLOUR_NOT_IN_MODEL', CL % ('ROUGE', 2014), CL_NOTE % 'rouge'),
    ('2016_Ch-CouhinsLurton_blanc-pdf.pdf', 'wn_00241', 2016): ('COLOUR_NOT_IN_MODEL', CL % ('BLANC', 2016), CL_NOTE % 'blanc'),
    ('2012_Ch-CouhinsLurton_blanc-pdf.pdf', 'wn_00241', 2012): ('COLOUR_NOT_IN_MODEL', CL % ('BLANC', 2012), CL_NOTE % 'blanc'),
    ('2008-R-Ch-Couhins-Lurton.pdf', 'wn_00241', 2008): ('COLOUR_NOT_IN_MODEL', CL % ('ROUGE', 2008), CL_NOTE % 'rouge'),
    ('2010-R-Ch-Couhins-Lurton.pdf', 'wn_00241', 2010): ('COLOUR_NOT_IN_MODEL', CL % ('ROUGE', 2010), CL_NOTE % 'rouge'),
    ('CouhinsLurton_R2017_FR.pdf', 'wn_00241', 2017): ('COLOUR_NOT_IN_MODEL', CL % ('ROUGE', 2017), CL_NOTE % 'rouge'),
    ('2007-R-Ch-Couhins-Lurton.pdf', 'wn_00241', 2007): ('COLOUR_NOT_IN_MODEL', CL % ('ROUGE', 2007), CL_NOTE % 'rouge'),
    ('2006-R-Ch-Couhins-Lurton.pdf', 'wn_00241', 2006): ('COLOUR_NOT_IN_MODEL', CL % ('ROUGE', 2006), CL_NOTE % 'rouge'),
    (DM % 2009, 'wn_00254', 2009): ('NON_VINTAGE_YEARS_COUNTED', 'Après le 2005', 'comparisons with 2005 and 2000; ' + DM_NOTE),
    ('Primeurs2022_DOMAINE_de_CHEVALIER_ROUGE_FR.pdf', 'wn_00503', 2022): ('LEAD_WRONG_WINE', 'Rouge Primeur 2022', 'the red grand vin\'s primeurs sheet, not the Blanc'),
    ('Primeurs2022_DOMAINE_de_CHEVALIER_ROUGE_FR.pdf', 'wn_00504', 2022): ('LEAD_WRONG_WINE', 'Rouge Primeur 2022', 'the red grand vin\'s primeurs sheet, not L\'Esprit'),
    ('Primeurs2022_DOMAINE_de_CHEVALIER_ROUGE_FR.pdf', 'wn_00505', 2022): ('LEAD_WRONG_WINE', 'Rouge Primeur 2022', 'the red grand vin\'s primeurs sheet, not the Rosé'),
    ('Primeurs-2022_Chateau-Figeac_-FR.pdf', 'wn_00266', 2022): ('NON_VINTAGE_YEARS_COUNTED', '(2015/2018/2019/2020)', 'the opening\'s first sentence is "le Château-Figeac 2022"'),
    ('g-de-chateau-guiraud-2023_en.pdf', 'wn_00519', 2023): ('LEAD_WRONG_WINE', 'G de Château GUIRAUD', 'the dry white G, not Petit Guiraud'),
    ('Fiche-technique_ClarteHB_2017_FR1.pdf', 'wn_00525', 2017): ('HEADING_EXTRACTED_LATE', 'Millésime 2017', 'the file series ClarteHB names the wine'),
    ('Fiche-technique_ChateauHBB_2007_EN1.pdf', 'wn_00525', 2007): ('LEAD_WRONG_WINE', 'Sauvignon Blanc: 55%', 'ChateauHBB is Château Haut-Brion Blanc, not La Clarté'),
    ('Fiche-technique_ClarteHB_2016_FR1.pdf', 'wn_00525', 2016): ('HEADING_EXTRACTED_LATE', 'La Clarté de Haut-Brion 2016', ''),
    ('CHATEAU_ISSAN_2004.pdf', 'wn_00283', 2004): ('NON_VINTAGE_YEARS_COUNTED', 'A boire à partir de 2012', 'a drinking window and a 2007 review date'),
    ('2019-FR-FICHE-TECH-Chateau-Kirwan.pdf', 'wn_00530', 2019): ('LEAD_WRONG_WINE', 'Le château Kirwan 2019', 'the grand vin\'s sheet, not Les Charmes de Kirwan'),
    ('Moulin-2016.pdf', 'wn_00533', 2016): ('NON_VINTAGE_YEARS_COUNTED', 'Après un automne 2015', 'the previous autumn\'s weather; the text names "le Moulin"'),
    ('Fiche-technique_ChapelleMissionHB_1998_FR.pdf', 'wn_00534', 1998): ('HEADING_EXTRACTED_LATE', 'Millésime 1998', 'the file series ChapelleMissionHB names the wine'),
    ('Fiche-technique_MissionHBB_2009_FR.pdf', 'wn_00535', 2009): ('LEAD_WRONG_WINE', 'Château La Mission Haut-Brion Blanc', 'MissionHBB is La Mission Haut-Brion Blanc, not La Clarté'),
    ('moulin-riche-2020-fiche-caisse-frgb.pdf', 'wn_00543', 2017): ('LEAD_WRONG_VINTAGE', '2020 résonnera longtemps', 'the 2020 sheet; 2017 is the HVE certification year'),
    ('chateau-sigalas-rabaud-2017', 'wn_00374', 2017): ('WEB_PAGE_VINTAGE_SELECTOR', 'Le Château Sigalas Rabaud 2017', 'the title states it; the page lists the estate\'s other wines'),
    ('chateau-suduiraut', 'wn_00448', 2023): ('WEB_PAGE_VINTAGE_SELECTOR', 'Château Suduiraut 2023 2023 2022 2021', ''),
}
for y in (2017, 2022, 2007, 2023, 2015, 2008, 2012, 2013, 2018, 2006, 2010, 2005, 2011, 2019, 2014):
    CLASSIFIED[(DM % y, 'wn_00254', y)] = ('FILENAME_SERIES_ONLY', 'MILLESIME %d' % y, DM_NOTE)
CLASSIFIED[('FT-DM-2023-EN.pdf', 'wn_00254', 2023)] = ('FILENAME_SERIES_ONLY', 'VINTAGE 2023', DM_NOTE)
for y in (1990, 2003, 2002, 2000, 2005, 2001, 2007, 2004, 1988, 1998, 2006, 1989):
    CLASSIFIED[(GM % y, 'wn_00402', y)] = ('HEADING_EXTRACTED_LATE', 'grand cru classé %d' % y, GM_NOTE % y)
CLASSIFIED[(GM % 1995, 'wn_00402', 1995)] = ('NON_VINTAGE_YEARS_COUNTED', 'April 1998', 'review dates (March 2004, April 1998)')


def norm(s):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', s or '')).strip().lower()


def held(sha):
    p = EXTRACTED + sha + '.json'
    x = json.load(open(p, encoding='utf-8'))
    if x.get('media') == 'pdf':
        return '\n'.join(s for s in x.get('pages') or [] if isinstance(s, str))
    return '\n'.join([x.get('title') or ''] + [h.get('text') or '' for h in x.get('headings') or []] +
                     [b.get('text') or '' for b in x.get('blocks') or []])


def name_of(url):
    return url.rstrip('/').rsplit('/', 1)[1]


def build():
    rows = [r for r in L.jsonl_lines(REVIEW) if r['record'] == 'review' and r['decision'] == 'READER_REFUSED'
            and r['reader_status'] in REFUSALS]
    claims = collections.OrderedDict()
    for r in sorted(rows, key=lambda r: (r['estate_id'], r['wine_id'], r['vintage'], r['sha256'], r['field'])):
        claims.setdefault((name_of(r['url']), r['wine_id'], r['vintage']), []).append(r)
    missing = sorted(set(claims) - set(CLASSIFIED))
    extra = sorted(set(CLASSIFIED) - set(claims))
    assert not missing and not extra, ('unclassified', missing, 'classified but not refused', extra)
    out = []
    for key, rs in claims.items():
        r = rs[0]
        klass, quote, note = CLASSIFIED[key]
        t = norm(held(r['sha256']))
        at = t.find(norm(quote))
        assert at >= 0, ('the quote is not in the held text', key, quote)
        out.append({'record': 'claim', 'estate_id': r['estate_id'], 'estate': r['estate'], 'wine_id': r['wine_id'],
                    'wine': r['wine'], 'vintage': r['vintage'], 'fields': sorted(x['field'] for x in rs),
                    'review_ids': sorted(x['review_id'] for x in rs), 'artifact': r['artifact'], 'sha256': r['sha256'],
                    'url': r['url'], 'reader_status': r['reader_status'], 'reader_reason': r['reason'],
                    'class': klass, 'verdict': CLASSES[klass][0], 'quote': quote,
                    'quote_at': round(at / max(len(t), 1), 2), 'note': note})
    return out


def body(recs):
    return ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n' for r in recs)


def report(recs):
    dp = lambda rs: sum(len(r['fields']) for r in rs)
    by = collections.defaultdict(list)
    for r in recs:
        by[r['class']].append(r)
    verdicts = collections.OrderedDict((v, [r for r in recs if r['verdict'] == v])
                                       for v in ('READER_DEFECT', 'NEEDS_STRUCTURE', 'CORRECT_REFUSAL', 'MODEL_GAP'))
    o = ['# Phase M3.12 - the P1 identity refusals, read', '',
         'Generated by `python tools/m312-identity-audit.py` (`data/audit/m3.12-identity-refusal-audit.jsonl`); the '
         'classification is a reading by hand, held in the tool, and every quote is checked against the document as '
         'held. **An audit, not a change:** no reader rule, evidence decision, model row or app file is touched.', '',
         '## 1. The question', '',
         'The P1 review refused %d datapoints on the reader\'s identity gate (ESTATE_ONLY %d, VINTAGE_AMBIGUOUS %d), '
         'from %d (document, wine, vintage) claims on %d documents. Is the reader right, or misreading?' % (
             dp(recs), dp([r for r in recs if r['reader_status'] == 'ESTATE_ONLY']),
             dp([r for r in recs if r['reader_status'] == 'VINTAGE_AMBIGUOUS']), len(recs),
             len({r['sha256'] for r in recs})), '',
         '## 2. Verdicts', '', '| verdict | claims | datapoints |', '|---|---:|---:|']
    for v, rs in verdicts.items():
        o.append('| %s | %d | %d |' % (v, len(rs), dp(rs)))
    o += ['', '## 3. Classes', '', '| class | verdict | claims | datapoints | what it is |', '|---|---|---:|---:|---|']
    for k, (v, what) in CLASSES.items():
        o.append('| %s | %s | %d | %d | %s |' % (k, v, len(by[k]), dp(by[k]), what))
    o += ['', '## 4. Every claim', '']
    for k in CLASSES:
        if not by[k]:
            continue
        o += ['### %s' % k, '', '| estate | wine | vintage | fields | document | the text says | note |',
              '|---|---|---|---|---|---|---|']
        for r in sorted(by[k], key=lambda r: (r['estate'], r['wine'], r['vintage'])):
            o.append('| %s | %s | %d | %s | %s | "%s" (at %d%%) | %s |' % (
                r['estate'], r['wine'], r['vintage'], ', '.join(r['fields']), name_of(r['url']),
                r['quote'].replace('|', '/'), round(100 * r['quote_at']), r['note'] or ''))
        o.append('')
    defects = verdicts['READER_DEFECT']
    o += ['## 5. What it means', '',
          '- %d of %d datapoints are refused by reader defects in four shapes; %d are correct refusals (%d of them '
          'leads for the wrong wine), %d wait on a model gap (one wine where the estate makes two colours) and %d on '
          'reading a web page\'s structure.' % (
              dp(defects), dp(recs), dp(verdicts['CORRECT_REFUSAL']), dp(by['LEAD_WRONG_WINE']),
              dp(verdicts['MODEL_GAP']), dp(verdicts['NEEDS_STRUCTURE'])),
          '- Clearing a defect does not by itself make a datapoint accepted: each still goes through the fiche reader\'s '
          'figures and the statement check, which the P1 review never reached for these claims.',
          '- A reader change is its own phase: tools/sheetreader.py and tools/read-fiches.py are fingerprinted into every '
          'evidence decision, so any change is a new decider version, re-run against every held decision.', '']
    return '\n'.join(o)


def main():
    recs = build()
    b, text = body(recs).encode('utf-8'), report(recs).encode('utf-8')
    if '--check' in sys.argv:
        bad = [p for p, x in ((OUT, b), (DOC, text)) if not os.path.exists(p) or open(p, 'rb').read() != x]
        print('M3.12 identity audit ' + ('is current' if not bad else 'differs: %s' % bad))
        sys.exit(1 if bad else 0)
    for p, x in ((OUT, b), (DOC, text)):
        open(p, 'wb').write(x)
    print('%d claims written' % len(recs))


if __name__ == '__main__':
    main()
