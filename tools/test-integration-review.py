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
import integration_application as IA  # noqa: E402
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
            ev = c['evidence_of_document']
            # a separate identity method: its own gate, a listing basis, decide's verdict a veto only - never M34A
            assert c['identity_gate'] == 'REVIEWED_LISTING' and 'r1_gate_rule' not in c and ev['rule'] == 'R4'
            assert ev['basis'].startswith('the reviewed listing files the document under') and 'M34A' not in ev['basis']
            assert ev['text_check']['role'].startswith('veto only') and ev['listing']['status'] == 'LISTING_IDENTITY'
        elif r['disposition'] == 'SAFE_TO_MAP':
            [c] = [c for c in r['claims'] if c['disposition'] == 'SAFE_TO_MAP']
            assert c['identity_gate'] == 'R1 (M34A)' and 'listing' not in c['evidence_of_document'], r['n']


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
        [c] = [c for c in r['claims'] if c['disposition'] == 'SAFE_TO_MAP']
        assert (ve.startswith(V1.TEXT_VINTAGE) or V1.adopted_vintage(ve, c['evidence_of_document'])) \
            and str(r['vintage']) in ve, (r['n'], ve)
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
    # V1 against the decisions the acceptance runner would append (a stub store holding exactly those), on the model
    # the manifests were reviewed for: before the integration application (BEFORE_VIEW)
    EA = _load('ea_ir_t', 'tools/apply-evidence-acceptance-manifest.py')
    view = BEFORE_VIEW(EA.V)
    errs, resolved = EA.validate_manifest(acc, view, EA.Store(), read_bytes=False)
    assert not errs, errs
    by_key = {x['key']: dict(x['decision'], v=10) for x in resolved.values()}
    ev = type('Ev', (), {'versions': {10}, 'by_key': by_key,
                         'latest': {L.dumps(json.loads(k)[:-1]): d for k, d in by_key.items()}})()
    errs, res = V1.validate_manifest(vin, BEFORE_VIEW(V1), ev=ev)
    assert not errs and len(res) == 33, errs
    plan = V1.plan_manifest(vin, res, BEFORE_VIEW(V1))
    assert plan['actions'] == {'CREATE': 0, 'ATTRIBUTION_ONLY': 33, 'NOOP': 0, 'CONFLICT': 0}, plan['actions']
    assert plan['adds'] == {'cross/provenance.jsonl': 51, 'document/attributions.jsonl': 34}, plan['adds']
    V1.verify_plan(plan)
    # the class must say what the identities are
    swap = [dict(v, creation_class='EXPLICIT_DOCUMENT_TEXT' if v['creation_class'] == 'REVIEWED_LISTING'
                 else 'REVIEWED_LISTING') for v in vin]
    errs, res = V1.validate_manifest(swap, BEFORE_VIEW(V1), ev=ev)
    assert {e.split(':')[0] for e in errs} == {v['manifest_id'] for v in vin} and not res, errs[:3]
    if IA.phase() == 'POST_APPLY':
        # the committed manifests are these, and the live model holds every row: nothing left to apply
        for k, rows in (('acceptance', acc), ('vintage', vin), ('value', val)):
            assert IA.manifest_rows(k) == rows, k
        errs, res = V1.validate_manifest(vin, V1.View())      # the store's own v10 (the runner's default)
        assert not errs, errs[:3]
        assert V1.plan_manifest(vin, res, V1.View())['actions'] == {'CREATE': 0, 'ATTRIBUTION_ONLY': 0, 'NOOP': 33,
                                                                    'CONFLICT': 0}


def refused(rv, part, sha=None):
    try:
        V1.check_review(rv, sha or rv['sha256'], rv['estate'], rv['wine'], rv['vintage'])
    except V1.Invalid as x:
        assert part in str(x), (part, str(x))
        return
    raise AssertionError('accepted: %s' % part)


@check
def t08_the_adopted_vintage_forms_are_scoped():
    import copy
    by = {(r['estate'], r['vintage'], r['disposition']): r for r in rows()}
    gm = by[('es_00414', 1988, 'SAFE_TO_MAP')]                    # a title block
    issan = by[('es_00283', 2008, 'SAFE_TO_MAP')]                 # the short name beside the year
    for r in (gm, issan):
        V1.check_review(r, r['sha256'], r['estate'], r['wine'], r['vintage'])
        bare = copy.deepcopy(r)                                   # the same row as if no adopted rule decided it
        for c in bare['claims']:
            c['evidence_of_document'].pop('identity_rules', None)
        refused(bare, 'the vintage is not stated in the document')
    no_r1b = copy.deepcopy(issan)                                 # the short name, where R1b did not read it
    for c in no_r1b['claims']:
        tr = (c['evidence_of_document'].get('identity_rules') or {}).get('trace') or []
        tr[:] = [t for t in tr if t[0] != 'R1b']
    refused(no_r1b, 'the vintage is not stated in the document')
    # an M3.9 row given an adopted form is refused: the forms do not redefine M3.9's vintage recognition
    m39 = [r for r in L.jsonl_lines(L.ROOT + 'data/audit/m3.9-evidence-review.jsonl') if r.get('record') == 'review'
           and r.get('disposition') == 'SAFE_TO_MAP']
    assert m39
    for r in m39:
        x = dict(r, vintage_evidence='title block "%s %d" (line 1 of 2)' % (r['estate_name'], r['vintage']))
        refused(x, 'the vintage is not stated in the document')


@check
def t09_a_reviewed_listing_never_creates_a_vintage():
    import copy
    import mig_m6_provenance as M6
    acc, vin, _ = IRV.manifests()
    EA = _load('ea_ir_t9', 'tools/apply-evidence-acceptance-manifest.py')
    view = BEFORE_VIEW(V1)                  # the model the manifests were reviewed for
    errs, resolved = EA.validate_manifest(acc, BEFORE_VIEW(EA.V), EA.Store(), read_bytes=False)
    assert not errs, errs
    held = {(v['wine'], v['label']) for v in view.table('identity/vintages.jsonl')}
    listing = [v for v in vin if v['creation_class'] == 'REVIEWED_LISTING' and len(v['artifact_ids']) == 1][0]
    w = listing['wine_id']
    y = next(y for y in range(1990, 2000) if (w, str(y)) not in held)        # a year the model holds no vintage for
    [a] = listing['artifact_ids']
    ref = listing['review'][a]
    [d0] = [x['decision'] for x in resolved.values() if x['decision']['ctx']['target_vintage'] == listing['vintage']
            and 'discovery:' in x['decision']['ctx']['folder'] and x['key'] == listing['evidence_decisions'][a]]
    d = copy.deepcopy(d0)
    d['ctx'].update(vintage=y, target_vintage=y, evaluated_as=d['ctx']['evaluated_as'].replace(str(listing['vintage']), str(y)))
    key = M6.row_key(d)
    ev = type('Ev', (), {'versions': {10}, 'by_key': {key: d}, 'latest': {L.dumps(json.loads(key)[:-1]): d}})()
    rv = copy.deepcopy(V1.Reviews().get(ref['audit'], ref['row']))
    rv['vintage'], rv['vintage_evidence'] = y, 'statement "millesime %d"' % y
    reviews = type('Rv', (), {'get': lambda self, audit, row: rv if (audit, row) == (ref['audit'], ref['row']) else None})()
    absent = dict(listing, vintage=y, evidence_decisions={a: key})
    errs, res = V1.validate_manifest([absent], view, ev=ev, reviews=reviews)
    assert errs == ['%s: vt:%s:%d does not exist, and a reviewed listing alone never creates a vintage'
                    % (listing['manifest_id'], w, y)] and not res, errs
    # the same listing row for the vintage the model holds is an attribution, nothing more
    ev2 = type('Ev', (), {'versions': {10}, 'by_key': {listing['evidence_decisions'][a]: d0},
                          'latest': {L.dumps(json.loads(listing['evidence_decisions'][a])[:-1]): d0}})()
    errs, res = V1.validate_manifest([listing], view, ev=ev2)
    assert not errs, errs
    plan = V1.plan_manifest([listing], res, view)
    assert plan['actions']['ATTRIBUTION_ONLY'] == 1 and plan['actions']['CREATE'] == 0, plan['actions']


def BEFORE_VIEW(runner):
    """A runner's View of the model as it stood before the integration application (the live model before it)."""
    return runner.View() if IA.phase() == 'PRE_APPLY' else runner.View(IA.read_before)


@check
def t07_nothing_is_applied():
    assert not git('status', '--porcelain', '--', 'data', 'sources')
    if IA.phase() == 'POST_APPLY':
        # applied, exactly: the three manifests are the reviewed rows, every figure of both states exact
        assert IA.verify() == 'POST_APPLY'
        for k in ('acceptance', 'vintage'):
            assert L.jsonl_lines(L.ROOT + IRV.MANIFESTS[k]) == IA.manifest_rows(k), k
        rows = L.jsonl_lines(L.ROOT + IRV.MANIFESTS['value'])
        assert rows[9:] == IA.manifest_rows('value') and all(
            r['source_basis'] == 'explicit_document_statement' and r['manifest_id'] <= 'vam_000009' for r in rows[:9])
        import evidence_store as ST
        assert ST.versions() == list(range(1, 11))
        return
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
