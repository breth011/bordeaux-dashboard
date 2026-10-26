"""M3.6A rerun: the fresh fetched-document reader audit and evidence-correction audit (audit only).

    python tools/test-m36a-rerun.py

Read-only. Holds data/audit/m3.6a-rerun-held-document-proposals.jsonl, its correction audit and its
report to their rules: every candidate and every wrong accepted claim judged exactly once, every
artifact's bytes its own, every web page judged by its structure, every SAFE_TO_MAP inside the R1
gate, the R1 regressions holding on the real pages, no historical decision touched, nothing mapped
or corrected, no network or OCR, and the outputs reproducible byte for byte.
"""

import gzip
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_gap_analysis as A  # noqa: E402
import check_cache as CC  # noqa: E402
import migration_lib as L  # noqa: E402

BEFORE = '0564fcb'               # the controlled web-page rule update: the state this audit read
PROPS = L.ROOT + 'data/audit/m3.6a-rerun-held-document-proposals.jsonl'
CORR = L.ROOT + 'data/audit/m3.6a-rerun-evidence-corrections.jsonl'
REPORT = L.ROOT + 'docs/PHASE-M3.6A-RERUN.md'
CHECKS = []

spec = importlib.util.spec_from_file_location('m36a', L.ROOT + 'tools/m36a-rerun.py')
X = importlib.util.module_from_spec(spec)
spec.loader.exec_module(X)
ROWS = L.jsonl_lines(PROPS)
CORRS = L.jsonl_lines(CORR)
BUILT = X.build()                 # one fresh build per run, shared by the checks


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode('utf-8')


def by_url(tail, vintage=None):
    return [r for r in ROWS if (r['first_url'] or '').endswith(tail) and (vintage is None or r['vintage'] == vintage)]


@check
def every_candidate_has_exactly_one_disposition():
    props, _, _, base = BUILT
    keys = [r['candidate'] for r in ROWS]
    assert len(keys) == len(set(keys)), 'a duplicated candidate'
    assert keys == [r['candidate'] for r in props], 'the candidates differ from a fresh population'
    assert all(r['disposition'] in X.DISPOSITIONS and r['basis'] for r in ROWS)
    assert len(ROWS) == 1046 and len({r['artifact'] for r in ROWS}) == 698        # verified, not assumed
    assert base['items_before_documenting'] - base['removed_documented_since'] == len(ROWS)
    for r in ROWS:
        if r['disposition'] == 'SAFE_TO_MAP':
            pe = r['positive_evidence']
            assert pe and pe['identity'] and pe['vintage_source'] and pe['basis'], r['candidate']


@check
def every_wrong_claim_has_exactly_one_correction_record():
    review = L.jsonl_lines(L.ROOT + 'data/audit/m3.5-held-document-review.jsonl')
    want = sorted(d for r in review if r.get('correction_proposal') for d in r['correction_proposal']['decisions'])
    got = [c['decision'] for c in CORRS]
    assert len(got) == len(set(got)), 'a duplicated evidence decision'
    assert sorted(got) == want and len(got) == 219                               # verified, not assumed
    for c in CORRS:
        assert c['category'] in X.CATEGORIES and c['proposed_action'] in X.ACTIONS and c['reason'], c['decision']
        assert c['proposed_action'] != 'WITHDRAW_ACCEPTANCE' or not c['mismatch_evidence'], c['decision']


@check
def artifact_ids_and_hashes_are_their_own():
    arts = A.by_id('identity/artifacts.jsonl')
    per = {}
    for r in ROWS:
        assert arts[r['artifact']]['sha256'] == r['sha256'], r['artifact']
        assert per.setdefault(r['artifact'], r['sha256']) == r['sha256'], 'one artifact, two hashes'
    blobs = L.ROOT + 'sources/discovery/blobs/'
    for aid, sha in sorted(per.items()):
        p = blobs + sha[:2] + '/' + sha
        b = open(p, 'rb').read() if os.path.exists(p) else gzip.decompress(open(p + '.gz', 'rb').read())
        assert hashlib.sha256(b).hexdigest() == sha, aid
    for c in CORRS:
        assert arts[c['artifact']]['sha256'] == c['sha256'], c['decision']


@check
def historical_decisions_remain_unchanged():
    # M3.6B adds evidence version 6 beside v1-v5 (the store grows by design); every v1-v5 assertion stands,
    # and v6 must be exactly M3.6B's decisions (historical_m2_scope.evidence_changes_are_m36b_only)
    import historical_m2_scope
    historical_m2_scope.evidence_changes_are_m36b_only(BEFORE)
    decs = {}
    m6 = importlib.util.spec_from_file_location('m6', L.ROOT + 'tools/mig_m6_provenance.py')
    M6 = importlib.util.module_from_spec(m6)
    m6.loader.exec_module(M6)
    for d in L.jsonl_lines(L.ROOT + 'data/evidence/decisions-v5.jsonl'):
        decs[M6.row_key(d)] = d
    for c in CORRS:
        d = decs[c['decision']]
        assert d['decision'] == c['original']['decision'] == 'ACCEPTED' and d['code'] == c['original']['code'], c['decision']
        assert d['read']['sha256'] == c['sha256']


@check
def model_canonical_and_app_unchanged_nothing_mapped_or_corrected():
    # the model: M3.6B's audited web-page mappings are the only later change, named exactly
    import historical_m2_scope
    historical_m2_scope.model_changes_are_m2_only(BEFORE)
    assert not git('diff', '--stat', BEFORE, '--', 'data/app', ':(glob)data/*.js', 'data/sources.json',
                   'data/history', 'data/review', 'data/scope', 'data/discovery', 'assets', 'index.html',
                   'data/audit/m3.5-held-document-review.jsonl', 'data/audit/m3.4b-mapping-application.jsonl').strip()
    # the gap register: changed only by M3.6B's resolution entries, named exactly, and reproducing
    historical_m2_scope.register_changes_are_m34b_only(BEFORE)
    for t, args in (('tools/migrate.py', ['--check']), ('tools/build-app-data.py', ['--check']),
                    ('tools/build-data-gap-register.py', ['--check']),
                    ('tools/build-data-gap-register.py', ['--report', '--check'])):
        out = CC.run([sys.executable, L.ROOT + t] + args)
        assert out.returncode == 0, (t, out.stdout[-200:])
    src = open(L.ROOT + 'tools/mig_m6_provenance.py', encoding='utf-8').read()
    # the migration reads no M3.6A output: M3.6A applied nothing (M3.6B's own manifest is what it reads)
    assert 'm3.6a-rerun-' not in src and 'm3.6a-held-document' not in src, 'the migration reads an M3.6A output'


@check
def no_network_and_no_ocr():
    import ast
    banned = {'urllib.request', 'requests', 'socket', 'http.client', 'httpx', 'aiohttp', 'pytesseract', 'ocrmypdf'}
    for f in ('tools/m36a-rerun.py', 'tools/web_evidence.py', 'tools/m36a_rerun_report.py'):
        tree = ast.parse(open(L.ROOT + f, encoding='utf-8').read())
        mods = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                mods |= {a.name for a in n.names}
            elif isinstance(n, ast.ImportFrom) and n.module:
                mods.add(n.module)
            elif isinstance(n, ast.Attribute) and n.attr in ('urlopen', 'image_to_string'):
                mods.add(n.attr)
        assert not mods & (banned | {'urlopen', 'image_to_string'}), (f, mods & banned)


@check
def web_pages_are_judged_by_their_structure():
    for r in ROWS:
        ev = r['evidence_of_document']
        if r['media_type'] == 'text/html':
            assert ev['kind'] == 'WEB_PAGE', r['candidate']
            assert ev['page'] or ev['disposition'] == 'EVIDENCE_INSUFFICIENT', r['candidate']
        else:
            assert ev['kind'] == 'DOCUMENT' and ev.get('rule') in ('T', 'M34A'), r['candidate']
        if r['disposition'] == 'SAFE_TO_MAP' and ev['kind'] == 'WEB_PAGE':
            p = ev['page']
            assert p['page_type'] == 'WINE_DOCUMENT' and p['identity_source'] == 'h1', r['candidate']
            assert p['vintage_source'] in ('main heading', 'labelled field in the content'), r['candidate']


@check
def the_r1_gate_holds_and_no_new_false_positive_class():
    assert not [r for r in ROWS if r['disposition'] == 'SAFE_TO_MAP' and r['r1_gate']]
    assert not [r for r in ROWS if r['reader_false_positive'] and not r['reader_false_positive']['known']]
    assert all(r['disposition'] != 'SAFE_TO_MAP' or r['reader']['decision'] == 'ACCEPTED' for r in ROWS)   # the reader's veto


@check
def the_r1_regressions_hold():
    out = CC.run([sys.executable, L.ROOT + 'tools/test-m36a-r1.py'])
    assert out.returncode == 0, out.stdout[-400:]
    # on the audit's own rows: the genuine page kept, the five classes and their kin refused
    assert {r['disposition'] for r in by_url('nos-vins/chateau-paloumey-2022-2/', 2022)} == {'SAFE_TO_MAP'}
    p = by_url('nos-vins/chateau-paloumey-2022-2/', 2022)[0]['positive_evidence']
    assert any('autres mill' in x for x in p['excluded_matches_set_aside'])     # its carousel set aside
    assert by_url('buy-our-wines/chateau-paloumey-2016/') and \
        all(r['disposition'] != 'SAFE_TO_MAP' for r in by_url('buy-our-wines/chateau-paloumey-2016/'))
    for tail, ok in (('produit/insula-2018/', None), ('fr/news/le-millesime-2019', 'ESTATE_ONLY'),
                     ('belairmonange.com/news?page=2', 'NOT_RELEVANT'), ('actualites/page/6/', 'NOT_RELEVANT'),
                     ('biodiversity-at-chateau-couhins--b17.html', None), ('filhot.com/les-vins/', 'MULTI_WINE_AMBIGUOUS'),
                     ('article/1014/', 'NOT_RELEVANT'), ('visuel-bouteille-chateau-couhins-lurton-rouge-2019/', 'COLOUR_AMBIGUOUS')):
        rs = by_url(tail)
        assert rs and all(r['disposition'] != 'SAFE_TO_MAP' for r in rs), tail
        if ok:
            assert {r['disposition'] for r in rs} == {ok}, (tail, {r['disposition'] for r in rs})


@check
def cuvee_de_mongravey_is_not_forced_into_the_chateau():
    cuvee = [c for c in CORRS if 'cuvee de mongravey' in (c['document_is']['title'][0] or '')]
    assert cuvee
    for c in cuvee:
        assert not c['replacement']['established'] and not (c['actual'] or {}).get('wine'), c['decision']
        if c['wine_name'] == 'Château Mongravey':
            assert c['proposed_action'] == 'RETAIN_AS_HISTORICAL_ACCEPTANCE_BUT_FLAG', c['decision']
    for c in CORRS:
        if c['replacement']['established']:
            assert c['actual']['wine'] and c['replacement']['decision'] != c['decision']


@check
def outputs_are_deterministic():
    props, corr, _, _ = BUILT
    again = X.build()                       # a second, independent build
    assert X.body(props) == X.body(again[0]) == open(PROPS, 'rb').read()
    assert X.body(corr) == X.body(again[1]) == open(CORR, 'rb').read()
    out = CC.run([sys.executable, '-I', L.ROOT + 'tools/m36a-rerun.py', '--check-all'])   # both outputs and the report
    assert out.returncode == 0, out.stdout[-300:] + out.stderr[-300:]
    text = open(PROPS, encoding='utf-8').read() + open(CORR, encoding='utf-8').read() + open(REPORT, encoding='utf-8').read()
    import tempfile
    assert L.ROOT not in text and 'Users' not in text and tempfile.gettempdir() not in text
    assert not re.search(r'20\d\d-\d\d-\d\dT\d', text)
    # the blocked run's own outputs are not overwritten by this run
    assert PROPS != L.ROOT + 'data/audit/m3.6a-held-document-proposals.jsonl'


@check
def the_report_compares_and_states_the_gate():
    text = open(REPORT, encoding='utf-8').read()
    assert re.findall(r'^## (\d+)\. ', text, re.M) == [str(i) for i in range(1, 13)]
    assert '| SAFE_TO_MAP | 144 | %d |' % sum(1 for r in ROWS if r['disposition'] == 'SAFE_TO_MAP') in text
    assert 'SAFE — M3.6A FRESH AUDIT COMPLETE — READY FOR M3.6B MAPPING/CORRECTION REVIEW' in text


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
