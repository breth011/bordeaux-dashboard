"""The integration review (tools/integration-review.py) and the manifests it builds.

    python tools/test-integration-review.py

Read-only. The committed review is reproduced; every safe row passes the acceptance path's own check_review (the
text branch or the listing branch) and every refused one fails it; every quote is the held text; the figures are
the dry run's; the vintage-creation manifest validates against the decisions the acceptance runner would append.
Nothing is applied: no manifest row is committed, the store and the model are as they were.
"""
import collections
import importlib.util
import json
import os
import re
import subprocess
import sys
import warnings

warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import migration_lib as L  # noqa: E402


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, L.ROOT + rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


IRV = _load('integration_review_t', 'tools/integration-review.py')
V1 = _load('v1_ir_t', 'tools/apply-vintage-creation-manifest.py')
CHECKS = []
_C = {}


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode('utf-8')


def rows():
    if 'rows' not in _C:
        _C['rows'] = [r for r in L.jsonl_lines(IRV.OUT) if r.get('record') == 'review']
    return _C['rows']


@check
def t01_reproduces_the_committed_review():
    built = IRV.build()
    assert IRV.body(built) == open(IRV.OUT, 'rb').read()
    assert IRV.report(built) == open(IRV.DOC, 'rb').read()


@check
def t02_the_documents_and_their_identities():
    rs = rows()
    c = collections.Counter((r['disposition'], r['identity_source']) for r in rs)
    assert c == {('SAFE_TO_MAP', 'R4'): 17, ('SAFE_TO_MAP', 'M34A'): 17, ('ESTATE_ONLY', 'M34A'): 2}, c
    refused = {(r['wine'] or r['claims'][0]['wine'], r['vintage']) for r in rs if r['disposition'] != 'SAFE_TO_MAP'}
    assert {y for _, y in refused} == {2004, 2010} and all(r['estate'] == 'es_00283' for r in rs
                                                          if r['disposition'] != 'SAFE_TO_MAP')
    for r in rs:
        if r['identity_source'] == 'R4':
            assert r['wine'] == 'wn_00254', r['n']                 # the listing names Chateau Desmirail only
            [c] = [c for c in r['claims'] if c['disposition'] == 'SAFE_TO_MAP']
            assert c['r1_gate_rule'].startswith('M34A') and c['evidence_of_document']['listing']['status'] == 'LISTING_IDENTITY'


@check
def t03_the_acceptance_path_reads_them_as_reviewed():
    for r in rows():
        w = r['wine'] or r['claims'][0]['wine']
        try:
            V1.check_review(r, r['sha256'], r['estate'], r['wine'] or 'wn_00283', r['vintage'])
            ok = True
        except V1.Invalid as x:
            ok, why = False, str(x)
        assert ok == (r['disposition'] == 'SAFE_TO_MAP'), (r['n'], w, None if ok else why)


@check
def t04_the_vintage_is_the_documents_own():
    forms = collections.Counter()
    for r in rows():
        if r['disposition'] != 'SAFE_TO_MAP':
            continue
        ve = r['vintage_evidence']
        assert ve.startswith(V1.TEXT_VINTAGE) and str(r['vintage']) in ve, (r['n'], ve)
        form = ve.split(' "')[0]
        forms[form] += 1
        if form == 'title block':
            assert r['estate'] == 'es_00414', r['n']          # Grand Mayne's title blocks only
        if form == 'short name and year':
            assert (r['estate'], r['vintage']) == ('es_00283', 2008), r['n']
    assert forms == {'statement': 19, 'title block': 13, 'short name and year': 1, 'wine and year': 1}, forms


@check
def t05_the_figures_are_the_dry_runs_and_quoted_as_held():
    dry = {r['claim_id']: r for r in L.jsonl_lines(IRV.DRYRUN) if r['record'] == 'claim'}
    n = 0
    for r in rows():
        raw, _, _ = IRV.P1.text_of(r['sha256'])
        lines = [l.strip(' \t') for l in raw.split('\n')]
        for f in r.get('figures') or []:
            [d] = [dry[c] for c in r['dry_run_claims'] if dry[c]['claim']['field'] == f['field']]
            assert f['recordable'] and L.dumps(f['value']) == L.dumps(d['final']['value']), (r['n'], f['field'])
            assert f['source'] == d['final']['value_source'], (r['n'], f['field'])
            parts = f['quote'].split(' | ' if f['source'] == 'C6_LAYOUT' else ' / ')
            assert all(p in lines for p in parts), (r['n'], f['field'], f['quote'])     # whole held lines, as held
            assert 'hl/ha' not in f['quote'] or f['source'] == 'READER'
            n += 1
    assert n == 51, n


@check
def t06_the_manifests_build_and_validate():
    acc, vin, val = IRV.manifests()
    assert (len(acc), len(vin), len(val)) == (34, 33, 51), (len(acc), len(vin), len(val))
    assert collections.Counter(v['source_basis'] for v in val) == {'explicit_document_statement': 36,
                                                                  'layout_derived_unit': 15}
    assert {a['evidence_version'] for a in acc} == {v['evidence_version'] for v in vin} == {10}
    # V1 against the decisions the acceptance runner would append (a stub store holding exactly those)
    EA = _load('ea_ir_t', 'tools/apply-evidence-acceptance-manifest.py')
    view = EA.V.View()
    errs, resolved = EA.validate_manifest(acc, view, EA.Store(), read_bytes=False)
    assert not errs, errs
    by_key = {x['key']: dict(x['decision'], v=10) for x in resolved.values()}
    ev = type('Ev', (), {'versions': {10}, 'by_key': by_key,
                         'latest': {L.dumps(json.loads(k)[:-1]): d for k, d in by_key.items()}})()
    errs, res = V1.validate_manifest(vin, V1.View(), ev=ev)
    assert not errs and len(res) == 33, errs
    plan = V1.plan_manifest(vin, res, V1.View())
    assert plan['actions'] == {'CREATE': 0, 'ATTRIBUTION_ONLY': 33, 'NOOP': 0, 'CONFLICT': 0}, plan['actions']
    assert plan['adds'] == {'cross/provenance.jsonl': 51, 'document/attributions.jsonl': 34}, plan['adds']
    V1.verify_plan(plan)
    # the class must say what the identities are
    swap = [dict(v, creation_class='EXPLICIT_DOCUMENT_TEXT' if v['creation_class'] == 'REVIEWED_LISTING'
                 else 'REVIEWED_LISTING') for v in vin]
    errs, res = V1.validate_manifest(swap, V1.View(), ev=ev)
    assert {e.split(':')[0] for e in errs} == {v['manifest_id'] for v in vin} and not res, errs[:3]


@check
def t07_nothing_is_applied():
    assert not git('status', '--porcelain', '--', 'data', 'sources')
    for k in ('acceptance', 'vintage'):
        assert not L.jsonl_lines(L.ROOT + IRV.MANIFESTS[k]), k               # no manifest row is committed
    assert all(r['source_basis'] == 'explicit_document_statement' and r['manifest_id'] <= 'vam_000009'
               for r in L.jsonl_lines(L.ROOT + IRV.MANIFESTS['value']))
    import evidence_store as ST
    assert ST.versions()[-1] == 9


def main():
    fails = 0
    for f in CHECKS:
        try:
            f()
            print('ok   %s' % f.__name__)
        except Exception as e:
            fails += 1
            print('FAIL %s: %r' % (f.__name__, e))
    print('%d check(s), %s' % (len(CHECKS), 'all pass' if not fails else '%d FAIL' % fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
