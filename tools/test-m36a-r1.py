"""M3.6A-R1: the web-page evidence rules (tools/web_evidence.py) - the controlled reader rule update.

    python tools/test-m36a-r1.py

Read-only. The five false-positive classes the blocked M3.6A audit found in fetched web pages, each
on the real page that showed it, rejected; a genuine wine page accepted; the separator, region and
page-type rules on pages built for the purpose; every M3.5 rule still holding on web pages; the
verdicts identical run after run; and nothing else changed - not the data, not the reader
(sheetreader.whose_sheet), not the M3.5 rubric.
"""

import collections
import hashlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_gap_analysis as A  # noqa: E402
import migration_lib as L  # noqa: E402
import web_evidence as WE  # noqa: E402

BEFORE = '7cb0d02'               # M3.5 (register recorded): the state before R1
CHECKS = []
NM = {n['subject']: n['name'] for n in A.table('identity/names.jsonl') if n['kind'] == 'CURRENT'}
W = A.by_id('identity/wines.jsonl')
WINES = {w: (NM.get(w, ''), W[w].get('type')) for w in W}
EW = collections.defaultdict(list)
for _r in A.table('state/estate-wine.jsonl'):
    EW[_r['estate']].append(_r['wine'])
ESTATES = sorted(v for k, v in NM.items() if k.startswith('es_'))
BLOCKED = {}
for _w, _n in NM.items():
    if _w.startswith('wn_') and any(x in A.fold(_n) for x in ('lions de batailley', 'hauts de lynch-moussas', 'haut-bailly ii')):
        BLOCKED[_w] = 'OPEN'
VERDICTS = []

# the real pages (sources/discovery/extracted/<sha256>.json), as the blocked audit met them
POITEVIN_INSULA = '1e5d75f7d0bcbd024aa0527e518025e38cc4e173f4521d77c5280eadafb03e35'   # chateau-poitevin.com/produit/insula-2018/
BELAIR_2019 = '69a327c1b33944a411a4dcccc816eebe57148f9600dcc07f3d0836c4c5d49cc3'       # belairmonange.com/fr/news/le-millesime-2019
BELAIR_ARCHIVE = '7b85e1fbc0f72b25de7ca6ea38f2eb519f45064f4ad87f6565d14dddf94b2f5f'    # belairmonange.com/news?page=2
CORBIN_93 = '203ce1a5582cee41cda4ba2931d04f0da90e431f20197c3ac5d48bf8110a9354'         # chateau-corbin.com/corbin-2016-93/
CORBIN_LIST = '5b60dbb546c90b53adaff08d5482c64c7a3aa1fdc6bb47f71059489cea86444f'       # chateau-corbin.com/actualites/page/6/
COUHINS_BLOG = '1e7d07ae15c5dce8210cd5feafeba0ba162e5c3effe0e92ded9c5752cf0f2f4b'      # chateau-couhins.fr/fr/blog/...biodiversity...
FILHOT_RANGE = '2ed532512d97c134c68767862a23c17ffb2499d2de2d30ec18fd9049cfef2d1b'      # filhot.com/les-vins/
FIGEAC_GREETING = 'e29b7d77c02cadd7468d9dbe25a5361383863179f098cd1c4e7ef03dfa393e4a'   # chateau-figeac.com/en/article/1014/
CL_ROUGE = '280a6d14fbf86fa9aaa881373e9209a3b5be783c9060f850a19745a6873f7331'          # couhins-lurton: visuel bouteille ... rouge 2019
CL_BLANC = '238200a45f307a63a9106c2e7449f6622d6322f6643b245cd3dcb856ed30d9ce'          # couhins-lurton: bouteille ... blanc 2019
PALOUMEY_2022 = '6712325195516058bc32c23ae0d1a9bfafea4df426a805a9e849b334dffc23e6'     # chateaupaloumey.com/nos-vins/chateau-paloumey-2022-2/
PALOUMEY_2016 = '44124493674b2bde1b8b60ff2cbc38df14df930a89c18e7d9a959b209c24047f'     # chateaupaloumey.com/en/buy-our-wines/chateau-paloumey-2016/


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode('utf-8')


def real(sha, estate, wine, year):
    ext = WE.load(sha, L.ROOT)
    assert ext, 'the held extraction of %s is missing' % sha
    j = WE.judge_page(ext, {'estate': estate, 'wine': wine, 'vintage': year}, WINES, EW, BLOCKED, ESTATES)
    VERDICTS.append((sha, estate, wine, year, j))
    return j


# a page built for the purpose: a fictitious estate, so no real name is hard-coded
T_EST, T_WINE, T_SECOND = 'es_test', 'wn_test', 'wn_test2'
T_WINES = dict(WINES, **{T_WINE: ('Château Testé', 'RED'), T_SECOND: ('La Réserve de Testé', 'RED')})
T_EW = dict(EW, **{T_EST: [T_WINE, T_SECOND]})


def page(h1, blocks=(), title=None, before=(), meta=None, canonical=None):
    bl = [{'tag': t, 'text': x, 'path': ''} for t, x in before]
    bl.append({'tag': 'h1', 'text': h1, 'path': h1})
    bl += [{'tag': t, 'text': x, 'path': '%s > %s' % (h1, x) if t.startswith('h') else h1} for t, x in blocks]
    heads = [{'level': 1, 'text': h1}] + [{'level': int(t[1]), 'text': x} for t, x in blocks if t.startswith('h')]
    return {'status': 'EXTRACTED', 'media': 'html', 'title': title or h1, 'headings': heads, 'blocks': bl,
            'meta': meta or {}, 'canonical': canonical, 'jsonld': []}


def made(ext, year=2019, wine=T_WINE):
    j = WE.judge_page(ext, {'estate': T_EST, 'wine': wine, 'vintage': year}, T_WINES, T_EW, BLOCKED,
                      ESTATES + ['Château Testé'])
    VERDICTS.append(('made', ext['headings'][0]['text'], wine, year, j))
    return j


SHEET = [('h2', 'Fiche technique'), ('p', 'Assemblage : 70% Merlot, 30% Cabernet Sauvignon. Alcool 14%.')]


# -- the five classes the blocked audit found, on their real pages ---------------------------------

@check
def r01_poitevin_related_product_contamination():
    j = real(POITEVIN_INSULA, 'es_00177', 'wn_00177', 2021)
    assert j['disposition'] != 'SAFE_TO_MAP' and j['identity']['name'] == 'insula', j
    assert any('Poitevin Blanc 2021' in x for x in j['excluded_region_match']), j['excluded_region_match']


@check
def r02_belair_monange_site_name_and_estate_wide_vintage():
    j = real(BELAIR_2019, 'es_00038', 'wn_00038', 2019)
    assert (j['page_type'], j['disposition']) == ('ESTATE_PAGE', 'ESTATE_ONLY'), j
    ext = WE.load(BELAIR_2019, L.ROOT)
    assert 'Bélair-Monange' in ext['title'] and 'Bélair-Monange' not in j['identity']['heading']   # the tab title is never read
    j = real(BELAIR_ARCHIVE, 'es_00038', 'wn_00038', 2020)
    assert j['page_type'] == 'ARCHIVE_PAGE' and j['disposition'] == 'NOT_RELEVANT', j


@check
def r03_corbin_news_archive_and_listing():
    j = real(CORBIN_93, 'es_00398', 'wn_00386', 2016)
    assert j['page_type'] == 'NEWS_ARTICLE' and j['disposition'] != 'SAFE_TO_MAP', j
    j = real(CORBIN_LIST, 'es_00398', 'wn_00386', 2016)
    assert j['page_type'] in ('ARCHIVE_PAGE', 'LISTING_PAGE') and j['disposition'] == 'NOT_RELEVANT', j


@check
def r04_couhins_sidebar_recent_articles():
    j = real(COUHINS_BLOG, 'es_00240', 'wn_00240', 2025)
    assert j['disposition'] != 'SAFE_TO_MAP' and j['page_type'] != 'WINE_DOCUMENT', j
    assert any('Couhins Blanc 2025' in x for x in j['excluded_region_match']), j['excluded_region_match']


@check
def r05_filhot_multi_wine_range_page():
    j = real(FILHOT_RANGE, 'es_00267', 'wn_00267', 2020)
    assert (j['page_type'], j['disposition']) == ('RANGE_PAGE', 'MULTI_WINE_AMBIGUOUS'), j


@check
def r06_figeac_greeting_page():
    j = real(FIGEAC_GREETING, 'es_00266', 'wn_00266', 2024)
    assert (j['page_type'], j['disposition']) == ('GREETING_EVENT_PAGE', 'NOT_RELEVANT'), j


@check
def r07_couhins_lurton_bottle_image_colour():
    j = real(CL_ROUGE, 'es_00241', 'wn_00241', 2019)         # the red bottle; the model's wine is the white
    assert j['identity']['asset'] and j['disposition'] == 'COLOUR_AMBIGUOUS', j
    j = real(CL_BLANC, 'es_00241', 'wn_00241', 2019)         # full name, vintage and colour: it may stand
    assert j['identity']['asset'] and j['identity']['colour'] == 'WHITE' and j['disposition'] == 'SAFE_TO_MAP', j
    # an asset page naming no colour, of a wine whose colour the model does not hold, with a colour in the heading
    assert made(page('Visuel bouteille Château Testé blanc 2019')) ['disposition'] == 'COLOUR_AMBIGUOUS'


@check
def r08_genuine_positive_web_page():
    j = real(PALOUMEY_2022, 'es_00167', 'wn_00167', 2022)
    assert (j['page_type'], j['disposition'], j['vintage_source']) == ('WINE_DOCUMENT', 'SAFE_TO_MAP', 'main heading'), j
    assert any('autres mill' in x for x in j['excluded_region_match'])        # its "other vintages" carousel set aside
    j = real(PALOUMEY_2016, 'es_00167', 'wn_00167', 2022)                      # the same wine's 2016 page
    assert j['disposition'] == 'NOT_RELEVANT' and j['identity']['year'] == 2016, j


# -- separators, regions and page types, on pages built for the purpose -----------------------------

@check
def r09_separators_mark_the_site_name():
    for sep in (' | ', ' – ', ' — '):
        j = made(page('Le millésime 2019' + sep + 'Château Testé'))
        assert j['identity']['site_suffix'] == 'chateau teste' and j['disposition'] == 'ESTATE_ONLY', (sep, j)
        j = made(page('Château Testé 2019' + sep + 'Château Testé', SHEET))
        assert j['identity']['site_suffix'] == 'chateau teste' and j['disposition'] == 'SAFE_TO_MAP', (sep, j)
    # a separator whose trailing part is not a site's name stays in the heading
    j = made(page('Château Testé 2019 | Cuvée spéciale', SHEET))
    assert j['identity']['site_suffix'] is None and j['disposition'] != 'SAFE_TO_MAP', j


@check
def r10_navigation_and_recommendation_regions_establish_nothing():
    nav = [('li', 'Château Testé 2019'), ('div', 'Menu')]
    j = made(page('Nos actualités', [('p', 'Bienvenue.')], before=nav))
    assert j['disposition'] != 'SAFE_TO_MAP'
    j = made(page('Une journée au chai', [('h2', 'Vous aimerez aussi'), ('h3', 'Château Testé 2019'),
                                          ('p', 'Commander')]))
    assert j['disposition'] != 'SAFE_TO_MAP' and any('2019' in x for x in j['excluded_region_match'])
    # the wine's own page keeps its identity whatever its carousel shows
    j = made(page('Château Testé 2019', SHEET + [('h2', 'Nos autres millésimes'), ('h3', 'Château Testé 2016'),
                                                 ('h3', 'Château Testé 2017'), ('h3', 'La Réserve de Testé 2019')]))
    assert j['disposition'] == 'SAFE_TO_MAP', j


# -- the M3.5 rules, still holding on web pages ----------------------------------------------------

@check
def r11_m35_rules_hold_on_web_pages():
    assert made(page('Le climat', [('p', 'Château Testé 2019 : un millésime solaire.')]))['disposition'] != 'SAFE_TO_MAP'   # heading, not title
    j = made(page('Château Testé', SHEET + [('p', 'Portes ouvertes le 16 mai 2019.')]))
    assert j['disposition'] == 'VINTAGE_AMBIGUOUS', j                                   # a date in prose is no vintage
    j = made(page('Château Testé', SHEET + [('p', 'Millésime : 2019')]))
    assert j['disposition'] == 'SAFE_TO_MAP' and j['vintage_source'].startswith('labelled'), j
    j = made(page('Château Testé', SHEET + [('p', 'Millésime'), ('p', '2019')]))
    assert j['disposition'] != 'SAFE_TO_MAP' or j['vintage_source'].startswith('labelled'), j
    j = made(page('Château Testé', SHEET + [('p', 'Après un été difficile, le millésime 2019 fut sauvé en septembre.')]))
    assert j['disposition'] == 'VINTAGE_AMBIGUOUS', j                                   # a sentence is no labelled field
    j = made(page('Château Testé 2019', SHEET + [('p', 'Notre second vin, La Réserve de Testé, ...')]))
    assert j['disposition'] == 'MULTI_WINE_AMBIGUOUS', j                                 # another wine of the estate
    j = made(page('Château Testé 2019', SHEET + [('h2', 'Millésime 2017'), ('h2', 'Millésime 2018')]))
    assert j['disposition'] == 'VINTAGE_AMBIGUOUS', j                                    # several vintages
    j = made(page('Château Testé 2019', [('p', 'Assemblage : 100% Sauvignon blanc.')]))
    assert j['disposition'] == 'COLOUR_AMBIGUOUS', j                                     # a white blend, a red wine
    j = made(page('Château Testé 2019', SHEET), wine=T_WINE, year=2020)
    assert j['disposition'] == 'NOT_RELEVANT', j                                         # wrong vintage
    j = made(page('La Réserve de Testé 2019', SHEET))
    assert j['disposition'] == 'NOT_RELEVANT', j                                         # wrong wine
    j = made(page('La Réserve de Testé 2019', SHEET), wine=T_SECOND)
    assert j['disposition'] == 'SAFE_TO_MAP', j                                          # the second wine's own page
    # never the URL, the tab title, a file or folder: a page whose heading names no wine
    j = made(page('Bienvenue', [('p', 'Bonjour.')], title='Château Testé 2019', canonical='https://x/chateau-teste-2019/'))
    assert j['disposition'] != 'SAFE_TO_MAP'
    assert set(WE.judge_page.__code__.co_varnames) & {'url', 'path', 'filename', 'folder'} == set()
    # an open identity decision is never attributed
    lions = next((w for w in WINES if w in BLOCKED), None)
    if lions:
        e = next(e for e, ws in EW.items() if lions in ws)
        j = WE.judge_page(page(WINES[lions][0] + ' 2019', SHEET), {'estate': e, 'wine': lions, 'vintage': 2019},
                          WINES, EW, BLOCKED, ESTATES)
        assert j['disposition'] == 'IDENTITY_BLOCKED', j


@check
def r12_every_verdict_carries_its_structure():
    for v in VERDICTS:
        j = v[-1]
        assert j['page_type'] in WE.PAGE_TYPES and j['basis']
        assert set(j) >= {'page_type', 'identity_source', 'identity_region', 'vintage_source', 'excluded_region_match',
                          'ambiguity_reason', 'disposition'}
        assert j['disposition'] == 'SAFE_TO_MAP' or j['ambiguity_reason'], j


# -- determinism and safety ------------------------------------------------------------------------

@check
def r13_verdicts_are_deterministic():
    first = json.dumps([v[-1] for v in VERDICTS], sort_keys=True, ensure_ascii=False)
    again = []
    for sha, e, w, y, _ in VERDICTS:
        if sha == 'made':
            continue
        again.append(WE.judge_page(WE.load(sha, L.ROOT), {'estate': e, 'wine': w, 'vintage': y}, WINES, EW, BLOCKED, ESTATES))
    real_first = json.dumps([v[-1] for v in VERDICTS if v[0] != 'made'], sort_keys=True, ensure_ascii=False)
    assert real_first == json.dumps(again, sort_keys=True, ensure_ascii=False)
    src = open(L.ROOT + 'tools/web_evidence.py', encoding='utf-8').read()
    assert not any(x in src for x in ('import time', 'import random', 'datetime', 'uuid'))
    print('     verdict digest %s' % hashlib.sha256(first.encode('utf-8')).hexdigest()[:16])


@check
def r14_nothing_else_changed():
    # R1 itself changed no data. Later phases' changes are named exactly: M3.6A's audit outputs (added files
    # only), M3.6B's model rows and its evidence version 6; everything else under data/ is as at BEFORE.
    import historical_m2_scope as H
    later_audit = {'data/audit/m3.6a-rerun-held-document-proposals.jsonl', 'data/audit/m3.6a-rerun-evidence-corrections.jsonl',
                   'data/audit/m3.6a-blocked-run-summary.json', 'data/audit/m3.6b-mapping-application.jsonl',
                   'data/audit/m3.6b-correction-application.jsonl', 'data/audit/m3.6b-historical-flags.jsonl'}
    changed = set(git('diff', '--name-only', BEFORE, '--', 'data').split())
    assert not git('diff', '--name-only', '--diff-filter=M', BEFORE, '--', 'data/audit').strip(), 'an audit output changed'
    assert {f for f in changed if f.startswith('data/audit/')} <= later_audit, 'data changed'
    H.model_changes_are_m2_only(BEFORE)
    H.evidence_changes_are_m36b_only(BEFORE)
    assert not {f for f in changed if not f.startswith(('data/audit/', 'data/model/', 'data/evidence/'))}, 'data changed'
    assert not git('diff', '--stat', BEFORE, '--', 'assets', 'index.html').strip(), 'the app changed'
    assert not git('diff', '--stat', BEFORE, '--', 'tools/sheetreader.py', 'tools/read-fiches.py',
                   'tools/m35_rubric.py', 'tools/evidence.py', 'tools/evidence-wines.py').strip(), 'the reader or rubric changed'
    import importlib.util
    spec = importlib.util.spec_from_file_location('ev', L.ROOT + 'tools/evidence.py')
    ev = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ev)
    assert ev.reader_fingerprint() == '7e8cfed1c24e'          # the v5 decisions' reader, unchanged
    for t in ('tools/migrate.py', 'tools/build-app-data.py'):
        out = subprocess.run([sys.executable, L.ROOT + t, '--check'], capture_output=True, text=True)
        assert out.returncode == 0, (t, out.stdout[-200:])


def main():
    fails = 0
    for f in CHECKS:
        try:
            f()
            print('ok   %s' % f.__name__)
        except Exception as ex:
            fails += 1
            print('FAIL %s: %s' % (f.__name__, str(ex)[:400]))
    print('%d check(s), %s' % (len(CHECKS), 'all pass' if not fails else '%d FAIL' % fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
