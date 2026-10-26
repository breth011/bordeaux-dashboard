"""M3.5: the held-document review and the Bernaleau pilot.

    python tools/test-m35.py

Read-only. Holds the rubric (tools/m35_rubric.py) to its regression cases - each the real rule on a
document's own words - and the review (data/audit/m3.5-held-document-review.jsonl) to its
invariants: every candidate once, the pilot deterministic, M3.4A's false positives still refused,
only eligible rows attributed and each exactly so, no decision, refusal, figure or open question
changed, and the output reproducible byte for byte.
"""

import collections
import importlib.util
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_gap_analysis as A  # noqa: E402
import historical_m2_scope as H  # noqa: E402
import migration_lib as L  # noqa: E402
import m35_rubric as RB  # noqa: E402

BEFORE = 'e1d9ae0'               # M3.4B (register recorded): the state before M3.5
OUT = L.ROOT + 'data/audit/m3.5-held-document-review.jsonl'
REPORT = L.ROOT + 'docs/PHASE-M3.5-HELD-DOCUMENT-REVIEW.md'
CHECKS = []

spec = importlib.util.spec_from_file_location('m35', L.ROOT + 'tools/m35-review.py')
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)
ROWS = L.jsonl_lines(OUT)
CX = V.Ctx()
BRAUDE, MONGRAVEY = 'wn_00073', 'wn_00158'
FOOTER = 'vignobles bernaleau -  sarl mongravey - 33460 arsac - france\ntel: +33 (0)5 56 58 84 51 - email: k.bernaleau@mongravey.fr'


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode('utf-8')


def judge(text, estate, wine, year):
    return RB.judge(text, {'estate': estate, 'wine': wine, 'vintage': year}, CX.wines, CX.ew, CX.blocked)


def rows_for(pred):
    return [r for r in ROWS if pred(r)]


def files(r):
    return ' '.join(r['files'])


def wine_named(name):
    return next(w for w, (n, _) in CX.wines.items() if n == name)


# -- the twelve regression cases --------------------------------------------------------------------

@check
def r01_document_explicitly_naming_braude():
    j = judge('\nchateau de braude 2020 \nhaut-medoc cru bourgeois\n' + FOOTER, 'es_00073', BRAUDE, 2020)
    assert j['disposition'] == 'SAFE_TO_ATTRIBUTE', j
    r = rows_for(lambda r: 'FT-Ch-de-Braude-2020.pdf' in files(r) and r['wine'] == BRAUDE and r['vintage'] == 2020)
    assert r and all(x['eligible'] and x['pilot_outcome'] == 'BRAUDE_ONLY' for x in r)


@check
def r02_document_explicitly_naming_mongravey():
    j = judge('\nchateau mongravey 2021\nmargaux cru bourgeois superieur\n' + FOOTER, 'es_00158', MONGRAVEY, 2021)
    assert j['disposition'] == 'SAFE_TO_ATTRIBUTE', j
    # the same sheet claimed for Braude: the producer line naming Mongravey is not why; the title is
    j = judge('\nchateau mongravey 2021\nmargaux\n' + FOOTER, 'es_00073', BRAUDE, 2021)
    assert j['disposition'] == 'WRONG_EXISTING_ATTRIBUTION', j
    assert {r['pilot_outcome'] for r in rows_for(lambda r: 'FT-Ch-Mongravey-2021' in files(r))} == {'MONGRAVEY_ONLY'}


@check
def r03_document_legitimately_supporting_both():
    text = 'tarifs primeurs 2020\nchateau de braude 2020 - haut-medoc\nchateau mongravey 2020 - margaux\n' + FOOTER
    claims = [{'wine': BRAUDE, 'vintage': 2020}, {'wine': MONGRAVEY, 'vintage': 2020}]
    assert RB.shared(text, claims, CX.wines) == sorted([BRAUDE, MONGRAVEY])
    assert RB.title(text) is None                                  # no single-wine title: T5 decides, not T1
    # named only in the producer line, the second wine is no support
    assert RB.shared('chateau de braude 2020\n' + FOOTER, claims, CX.wines) == []
    # the pilot found none: each Bernaleau document is one wine's
    assert not rows_for(lambda r: r['disposition'] == 'BOTH_ESTATES_SUPPORTED')


@check
def r04_mentioning_both_but_supporting_neither():
    text = '\nchateau galland 2014\nmoulis\n' + FOOTER + '\nvoisin de chateau de braude'
    for e, w in (('es_00073', BRAUDE), ('es_00158', MONGRAVEY)):
        assert judge(text, e, w, 2014)['disposition'] == 'WRONG_EXISTING_ATTRIBUTION'
    # a shared word is no match (T2)
    assert judge('\nchateau braude fellonneau 2019\nhaut-medoc\n' + FOOTER, 'es_00073', BRAUDE, 2019)['disposition'] \
        == 'WRONG_EXISTING_ATTRIBUTION'
    outcome = {r['artifact']: r['pilot_outcome'] for r in rows_for(lambda r: r['population'] == 'BERNALEAU_PILOT')}
    for r in rows_for(lambda r: r['population'] == 'BERNALEAU_PILOT' and (r['title'] or [''])[0] in
                      ('chateau galland', 'chateau braude fellonneau', 'cuvee de mongravey')):
        assert outcome[r['artifact']] == 'NEITHER' and not r['eligible'], r['artifact']


@check
def r05_filename_only_vintage():
    # the year is only in the file name: the text gives none, and the rubric never reads a file name
    j = judge('\nchateau de braude \nhaut-medoc\n' + FOOTER, 'es_00073', BRAUDE, 2020)
    assert j['disposition'] == 'VINTAGE_AMBIGUOUS', j
    assert 'path' not in RB.judge.__code__.co_varnames and 'filename' not in RB.judge.__code__.co_varnames
    for r in rows_for(lambda r: r['title'] and r['title'][1] is None and r['population'] != 'WIDER_FETCHED'):
        assert not r['eligible'], r['artifact']


@check
def r06_press_article_date_mistaken_for_vintage():
    text = '\nchateau de braude 2016\nhaut-medoc\n' + FOOTER + '\njames suckling - dec 2018\n93 pts'
    assert 2018 in RB.dated_years(text)
    assert judge(text, 'es_00073', BRAUDE, 2018)['disposition'] == 'WRONG_EXISTING_ATTRIBUTION'
    assert {2017} <= RB.dated_years('guide hubert des vins 2017') and {2019} <= RB.dated_years('le 16 mai 2019')
    dated = rows_for(lambda r: r['claim_year_dated'] and r['population'] != 'WIDER_FETCHED')
    assert dated and not any(r['eligible'] for r in dated)
    assert any('Ch-Galland-2014.pdf' in files(r) and r['vintage'] == 2017 for r in dated)


@check
def r07_multi_wine_document():
    hb, cl = wine_named('Château Haut-Brion'), wine_named('Le Clarence de Haut-Brion')
    text = '\nchateau haut-brion 2010\npessac-leognan\nle second vin, le clarence de haut-brion 2010, ...'
    j = judge(text, 'es_00281', hb, 2010)
    assert j['disposition'] in ('MULTI_WINE_AMBIGUOUS', 'WINE_AMBIGUOUS'), j
    assert cl in CX.ew['es_00281']


@check
def r08_estate_only_vintage_page():
    # an estate page headed by a vintage, never naming the wine: no title, M3.4A's rule, not the grand vin
    text = 'https://www.chateau-latour.com/en/a-time-for-sharing/vintages#1991 vintages 1991 the weather in 1991 ...'
    assert RB.title(text) is None
    latour = rows_for(lambda r: r['estate_name'] == 'Château Latour' and r['population'] == 'WIDER_ACCEPTED')
    assert latour and not any(r['eligible'] for r in latour)
    assert any(r['disposition'] == 'WINE_AMBIGUOUS' and 'not the wine' in r['basis'] for r in latour)


@check
def r09_shop_or_magnum_page():
    text = 'https://en.chantegrive.com/product-page/magnum-de-chantegrive-rouge-2020-cb --> magnum de chantegrive rouge - 2020 cb\nadd to cart €38.00'
    assert V.doc_type(text, 'text/plain') == 'SHOP_PAGE'
    assert RB.title(text) is None                          # a page whose first line is its address has no title
    assert not any(r['eligible'] and r['document_type'] == 'SHOP_PAGE' for r in ROWS)


@check
def r10_wrong_existing_attribution():
    wrong = rows_for(lambda r: r['disposition'] == 'WRONG_EXISTING_ATTRIBUTION')
    assert wrong and all(r['correction_proposal']['proposed'] == 'REVIEW_FOR_REFUSAL' and not r['eligible'] for r in wrong)
    ex = rows_for(lambda r: 'FT-Ch-Mongravey-2016.pdf' in files(r) and r['wine'] == BRAUDE and r['vintage'] == 1981)
    assert ex and ex[0]['disposition'] == 'WRONG_EXISTING_ATTRIBUTION'
    # the decision itself stands: the evidence store is untouched, its acceptance not converted or deleted
    assert not git('diff', '--stat', BEFORE, '--', 'data/evidence').strip()
    for rk in ex[0]['evidence_decisions']:
        assert CX.decs[rk]['decision'] == 'ACCEPTED'


@check
def r11_unresolved_conflict():
    con = rows_for(lambda r: r['disposition'] == 'CONFLICT_REMAINS')
    assert con and not any(r['eligible'] for r in con)
    assert {r['estate_name'] for r in con} >= {'Château Poitevin', 'Château Doisy-Daëne'}


@check
def r12_open_identity_case():
    for name in ('Les Hauts de Lynch-Moussas', 'Lions de Batailley', 'Echo de Lynch-Bages', 'Haut-Bailly II'):
        w = wine_named(name)
        e = next(e for e, ws in CX.ew.items() if w in ws)
        j = judge('\n%s 2019\npauillac\n' % RB.norm_name(name), e, w, 2019)
        assert j is None or j['disposition'] == 'WINE_AMBIGUOUS', (name, j)
    assert not any(r['eligible'] and r['wine'] in CX.blocked for r in ROWS)


# -- M3.4A's false positives stay refused ---------------------------------------------------------

@check
def m34a_false_positives_remain_rejected():
    hb = wine_named('Château Haut-Brion')
    assert judge('\nle climat\nthe growing season ...', 'es_00281', hb, 2009) is None   # a heading, not a title
    assert not M34A_GRAND_VIN('il crea le grand vin sec de doisy daene')
    for pat in ('PDF_CLOS_FLORIDENE', 'SILT-20', 'Fiche-technique-Mondot', 'Commentaires-Clos-Puy-Arnaud'):
        rs = rows_for(lambda r: pat in files(r) and r['population'] != 'WIDER_FETCHED')
        assert rs and not any(r['eligible'] for r in rs), pat
    # an event date: Lynch-Moussas 2019 has its document since M3.4B, so these pages are no longer
    # candidates; judged again through the review, they are still refused
    m34a = [r for r in L.jsonl_lines(L.ROOT + 'data/audit/m3.4a-mapping-proposals.jsonl') if 'de-la-fleur' in files(r)]
    assert len(m34a) == 2
    for r in m34a:
        x = V.review_one(CX, 'WIDER_ACCEPTED', r['artifact'], r['estate'], r['wine'], r['vintage'])
        assert x['disposition'] == 'VINTAGE_AMBIGUOUS' and 'calendar date' in x['basis'], x['basis']


def M34A_GRAND_VIN(s):
    return V.M34A.GRAND_VIN.search(s)


# -- the review's invariants -----------------------------------------------------------------------

@check
def every_candidate_appears_once_and_the_pilot_ran_first():
    keys = [(r['population'], r['artifact'], r['estate'], r['wine'], r['vintage']) for r in ROWS]
    assert len(keys) == len(set(keys))
    assert all(r['disposition'] in V.DISPOSITIONS and r['basis'] for r in ROWS)
    pilot = rows_for(lambda r: r['population'] == 'BERNALEAU_PILOT')
    assert len({r['artifact'] for r in pilot}) == 74 and all(r['rule'] == 'T' for r in pilot)   # verified, not assumed
    assert {r['pilot_outcome'] for r in pilot} <= {'BRAUDE_ONLY', 'MONGRAVEY_ONLY', 'NEITHER'}
    assert set(V.pilot_claims(CX)) == {(r['artifact'], r['estate'], r['wine'], r['vintage']) for r in pilot}
    assert all(r['disposition'] == 'EVIDENCE_INSUFFICIENT' and not r['eligible'] for r in rows_for(
        lambda r: r['population'] == 'WIDER_FETCHED'))                    # no decision, no attribution (O1)


@check
def every_new_attribution_has_explicit_existing_evidence():
    prov = A.by_id('cross/provenance.jsonl')
    mine = A.m35_attributions()
    elig = rows_for(lambda r: r['eligible'])
    assert sorted(a['id'] for a in mine) == sorted(r['attribution'] for r in elig)
    assert all(H.is_m35_attribution(a, prov) for a in mine)
    for r in elig:
        assert r['disposition'] in ('SAFE_TO_ATTRIBUTE', 'BOTH_ESTATES_SUPPORTED') and r['evidence_decisions']
        for rk in r['evidence_decisions']:
            d, ln = CX.decs[rk], CX.ln[rk]
            assert d['decision'] == 'ACCEPTED' and d['read']['sha256'] == r['sha256']
            assert (ln['artifact'], ln['estate'], ln['wine']) == (r['artifact'], r['estate'], r['wine'])
            assert (d['ctx'].get('target_vintage') or d['ctx'].get('vintage')) == r['vintage']
        a = next(x for x in mine if x['id'] == r['attribution'])
        p = prov[a['provenance']]
        assert p['derived_from'] == r['manifest_provenance'] and p['code_state']['evidence_decisions'] == r['evidence_decisions']


@check
def nothing_else_changed():
    changed = set(git('diff', '--name-only', BEFORE, '--', 'data/model').split())
    assert changed <= {'data/model/' + f for f in ('document/attributions.jsonl', 'cross/provenance.jsonl',
                                                    'derived/vintage-documents.json', 'manifest.json')}, sorted(changed)
    H.model_changes_are_m2_only(BEFORE)
    assert not git('diff', '--stat', BEFORE, '--', 'data/evidence', 'data/app', 'data/discovery', ':(glob)data/*.js',
                   'data/sources.json', 'data/history', 'data/review', 'data/scope', 'assets', 'index.html',
                   'data/audit/m3.4a-mapping-proposals.jsonl', 'data/audit/m3.4b-mapping-application.jsonl',
                   'data/audit/m3.3-source-acquisition-plan.jsonl').strip()
    H.register_changes_are_m34b_only(BEFORE)
    # no figure: values, observations and reconciliations byte-identical; D1, D5 and every finding open
    assert not git('diff', '--stat', BEFORE, '--', 'data/model/canonical', 'data/model/observation',
                   'data/model/reconciliation', 'data/model/cross/findings.jsonl', 'data/model/identity').strip()
    f = L.read_table('cross/findings.jsonl')
    assert sum(1 for x in f if x['kind'] == 'AMBIGUOUS_SEMANTICS' and x['status'] == 'OPEN') == 179
    assert sum(1 for x in f if x['kind'] == 'CONFLICT' and x['status'] == 'OPEN') == 7
    assert not L.read_table('identity/transitions.jsonl')


@check
def output_is_deterministic():
    rows, stop = V.build()
    assert not stop and V.body(rows) == open(OUT, 'rb').read()
    for args in (['--check'], ['--report', '--check']):
        out = subprocess.run([sys.executable, L.ROOT + 'tools/m35-review.py'] + args, capture_output=True, text=True)
        assert out.returncode == 0, out.stdout + out.stderr
    for t in ('tools/migrate.py', 'tools/build-indexes.py', 'tools/build-app-data.py'):
        out = subprocess.run([sys.executable, L.ROOT + t, '--check'], capture_output=True, text=True)
        assert out.returncode == 0, (t, out.stdout[-300:])
    text = open(OUT, encoding='utf-8').read()
    assert L.ROOT not in text and 'Users' not in text and not re.search(r'20\d\d-\d\d-\d\dT\d', text)


@check
def the_report_states_the_gate():
    text = open(REPORT, encoding='utf-8').read()
    assert re.findall(r'^## (\d+)\. ', text, re.M) == [str(i) for i in range(1, 11)]
    assert 'SAFE — M3.5 HELD-DOCUMENT REVIEW COMPLETE — READY FOR TARGETED ACQUISITION' in text


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
