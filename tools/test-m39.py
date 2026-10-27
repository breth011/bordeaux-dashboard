"""Phase M3.9: the evidence review of M3.8's 17 acquired candidates (tools/m39-evidence-review.py).

    python tools/test-m39.py

Read-only. The review recomputes byte for byte; it reviews exactly M3.8's 17 candidates and nothing of the 62
unclear items or the unlisted cuvées; no identity rests on a URL, file name or domain; a single-wine estate's
document is not made its wine; every candidate figure is confirmed by the document's own sentence; the reader
files and the evidence store (v1-v8) are unchanged, no decision written; the model and app are as M3.8 left them.
"""
import collections
import importlib.util
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_cache as CC  # noqa: E402
import migration_lib as L  # noqa: E402

BEFORE = '5bcca5f'               # M3.8: the state M3.9 reviews
_s = importlib.util.spec_from_file_location('m39', L.ROOT + 'tools/m39-evidence-review.py')
M = importlib.util.module_from_spec(_s)
_s.loader.exec_module(M)
CHECKS = []


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode('utf-8')


def audit(record=None):
    return [r for r in L.jsonl_lines(M.OUT) if record is None or r['record'] == record]


@check
def t01_deterministic():
    out = CC.run([sys.executable, L.ROOT + 'tools/m39-evidence-review.py', '--check'], cwd=L.ROOT)
    assert out.returncode == 0, (out.stdout + out.stderr)[-400:]


@check
def t02_exactly_the_17_candidates_in_order():
    rv = audit('review')
    m38 = {r['n']: r for r in L.jsonl_lines(M.P.OUT) if r['record'] == 'item'}
    want = {n for n, r in m38.items() if r['classification'] in ('EXACT_ESTATE_WINE_VINTAGE', 'ESTATE_VINTAGE_ONLY')}
    assert len(rv) == 17 and {r['m38_item'] for r in rv} == want
    names = [r['url'].split('/')[-1] for r in rv[:4]]
    assert names == list(M.ORDER), names
    assert [r['estate'] for r in rv] == ['es_00263'] * 4 + ['es_00293'] * 11 + ['es_00253'] * 2
    assert [r['vintage'] for r in rv[4:15]] == [2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2015]


@check
def t03_no_expansion_to_the_unclear_items_or_the_unlisted_cuvees():
    unclear = {r['url'] for r in L.jsonl_lines(M.P.OUT) if r['record'] == 'item'
               and r['classification'] == 'ESTATE_DOCUMENT_IDENTITY_UNCLEAR'}
    assert len(unclear) == 62 and not unclear & {r['url'] for r in audit('review')}
    model_wines = {w['id'] for w in L.read_table('identity/wines.jsonl')}
    for r in audit('review'):
        assert all(c['wine'] in model_wines for c in r['claims'])
        assert r['wine'] in (None, 'wn_00263'), r['n']
    for name in ('nature de durfort', 'relais de durfort', 'haut medoc de haut bages'):
        assert not [r for r in audit('review') if name in json.dumps(r['claims']).lower()], name


@check
def t04_identity_never_from_url_filename_or_domain():
    for r in audit('review'):
        src = r['identity_source']
        assert src in ('T', 'M34A', 'h1', 'none'), (r['n'], src)
        for c in r['claims']:
            b = (c['evidence_of_document']['basis'] or '').lower()
            assert 'http' not in b and '.pdf' not in b and '.com' not in b, (r['n'], b)
    # La Mondotte: the estate has one wine, and its documents do not name it: no attribution
    mondotte = [r for r in audit('review') if r['estate'] == 'es_00293']
    assert len(mondotte) == 11 and all(r['category'] == 'ESTATE_VINTAGE_ONLY' and r['wine'] is None for r in mondotte)
    assert all(not r['claims'][0]['evidence_of_document'].get('grand_vin_rule') for r in mondotte)
    # Myrat's print views: no main heading, no identity (W1)
    myrat = [r for r in audit('review') if r['estate'] == 'es_00253']
    assert [r['disposition'] for r in myrat] == ['EVIDENCE_INSUFFICIENT'] * 2
    assert all(r['claims'][0]['evidence_of_document']['page']['identity_source'] == 'none' for r in myrat)


@check
def t05_accepted_documents_and_their_figures():
    acc = [r for r in audit('review') if r['category'] == 'ACCEPTED_EXACT_ESTATE_WINE_VINTAGE']
    assert len(acc) == 4 and all(r['disposition'] == 'SAFE_TO_MAP' and r['wine'] == 'wn_00263' for r in acc)
    assert all(c['reader']['decision'] == 'ACCEPTED' and not c['r1_gate'] for r in acc for c in r['claims'])
    raw = {r['sha256']: M.joined(M.P.text_of(r['sha256'])[0]) for r in acc}
    for r in acc:
        for f in r.get('figures') or []:
            v, s, words = M.check(f['field'], f['value'], raw[r['sha256']])
            assert v == f['statement_check'], (r['n'], f['field'])
            if f['suitable_for_later_canonicalization']:
                assert v == 'CONFIRMED' and f['existing'] in (None, f['value'])
            if words:
                assert words in raw[r['sha256']], (r['n'], f['field'])
    oak = [f for r in acc for f in r.get('figures') or [] if f['statement_check'] == 'CONTRADICTED_BY_STATEMENT']
    assert len(oak) == 1 and oak[0]['field'] == 'oak' and oak[0]['value'] == 30.0 and oak[0]['stated_value'] == 70.0
    assert not [r for r in audit('review') if r['category'] != 'ACCEPTED_EXACT_ESTATE_WINE_VINTAGE' and r.get('figures')]
    rel = {(r['n'], o['review']): o['relation'] for r in acc for o in r.get('related') or []}
    assert rel == {(1, 2): 'LANGUAGE_VARIANT_SAME_STATEMENTS', (2, 1): 'LANGUAGE_VARIANT_SAME_STATEMENTS'}, rel


@check
def t06_the_reader_and_the_evidence_store_unchanged():
    assert not git('diff', '--stat', BEFORE, '--', *M.READER_FILES, 'tools/evidence.py', 'tools/evidence_store.py',
                   'tools/m35-review.py', 'tools/m36a-rerun.py').strip()
    [scope] = audit('scope')
    assert scope['reader_fingerprint'] == M.EV.reader_fingerprint()
    import evidence_store as ST
    assert ST.versions() == [1, 2, 3, 4, 5, 6, 7, 8] and ST.verify() == []
    [s] = audit('summary')
    assert s['evidence_decisions_written'] == 0 and s['model_changes'] == 0


@check
def t07_no_model_or_app_mutation():
    paths = ('data/model', 'data/evidence', 'data/app', 'data/sources.json', 'data/websites.js', ':(glob)data/*.js',
             'assets', 'index.html', 'data/audit/data-gap-register.jsonl', 'data/discovery',
             'data/audit/m3.7-source-confirmation.jsonl', 'data/audit/m3.8-acquisition-pilot.jsonl')
    assert not git('diff', '--stat', BEFORE, '--', *paths).strip()
    assert not git('status', '--porcelain', '--', *paths).strip()


@check
def t08_stable_output():
    kinds = [r['record'] for r in audit()]
    assert kinds == ['scope'] + ['review'] * 17 + ['summary']
    assert [r['n'] for r in audit('review')] == list(range(1, 18))
    c = collections.Counter(r['category'] for r in audit('review'))
    assert c == {'ACCEPTED_EXACT_ESTATE_WINE_VINTAGE': 4, 'ESTATE_VINTAGE_ONLY': 11, 'REJECTED_INSUFFICIENT_EVIDENCE': 2}


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
