"""M3.4B: the audited existing-evidence mappings, applied.

    python tools/test-m34b.py

Read-only. Holds the model to M3.4B's one intended change - the M3.4A SAFE_TO_MAP documents linked
to their audited estate + wine + vintage, as Attributions with their own DOCUMENT provenance - and
to nothing else: no decision, artifact, provenance, value, figure, open decision or app file changed;
the M3.4A audit unchanged; the model, its indexes, the manifest and the app data reproducible.
"""

import hashlib
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

BEFORE = '8b1c25b'               # M3.4A: the state before M3.4B
AUDIT = L.ROOT + 'data/audit/m3.4a-mapping-proposals.jsonl'
MANIFEST = L.ROOT + 'data/audit/m3.4b-mapping-application.jsonl'
REPORT = L.ROOT + 'docs/PHASE-M3.4B-MAPPING-APPLICATION.md'
CHECKS = []

spec = importlib.util.spec_from_file_location('m34b', L.ROOT + 'tools/m34b-apply.py')
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
SAFE = [r for r in L.jsonl_lines(AUDIT) if r['disposition'] == 'SAFE_TO_MAP']
ROWS = L.jsonl_lines(MANIFEST)
PROV = A.by_id('cross/provenance.jsonl')
ATT = A.table('document/attributions.jsonl')
MINE = [a for a in ATT if (PROV.get(a['provenance']) or {}).get('actor') == B.M6.MAPPINGS_ACTOR]


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode('utf-8')


def run(*args):
    out = subprocess.run([sys.executable] + [L.ROOT + args[0]] + list(args[1:]), capture_output=True, text=True)
    assert out.returncode == 0, (args, out.stdout[-400:] + out.stderr[-400:])
    return out.stdout


def key(r):
    return (r['estate'], r['wine'], r['vintage_id'], r['artifact'])


def at_before(rel):
    return git('show', '%s:%s' % (BEFORE, rel))


@check
def every_allow_list_entry_is_applied():
    # the allow-list is the audit's, verified against its own report, never assumed
    counts = (len(SAFE), len({r['vintage_id'] for r in SAFE}), len({r['wine'] for r in SAFE}))
    assert counts == B.recorded_counts() == (39, 26, 14), counts
    applied = {key(r) for r in ROWS if r['result'] == 'APPLIED'}
    assert {key(r) for r in SAFE} == applied, 'a SAFE row not applied'
    model = {(a['estate'], a['wine'], a['vintage'], a['artifact']) for a in MINE}
    assert applied <= model


@check
def no_allow_list_entry_is_missing():
    assert len(ROWS) == len(SAFE) == len({key(r) for r in ROWS})
    assert all(r['result'] == 'APPLIED' and not r['failures'] for r in ROWS), [r['artifact'] for r in ROWS if r['failures']]
    assert len(MINE) == len(SAFE) and len({a['id'] for a in MINE}) == len(MINE)


@check
def no_extra_mapping_exists():
    old = {json.loads(x)['id'] for x in at_before('data/model/document/attributions.jsonl').splitlines()}
    added = [a for a in ATT if a['id'] not in old]
    assert sorted(a['id'] for a in added) == sorted(a['id'] for a in MINE), 'an attribution beyond M3.4B'
    assert {a['id'] for a in ATT if a['method'] != 'LEGACY_UNKNOWN' or a['status'] != 'LEGACY'} == {a['id'] for a in MINE}
    assert all(H.is_m34b_attribution(a, PROV) for a in MINE)
    old_vd = json.loads(at_before('data/model/derived/vintage-documents.json'))
    new_vd = json.load(open(L.MODEL + 'derived/vintage-documents.json', encoding='utf-8'))
    gained = {(k, x) for k in new_vd for x in set(new_vd[k]) - set(old_vd.get(k, []))}
    assert gained == {(a['vintage'], a['artifact']) for a in MINE}, 'a vintage gained a document beyond M3.4B'
    assert all(set(old_vd[k]) <= set(new_vd.get(k, [])) for k in old_vd), 'a link was removed'
    assert len({k for k, _ in gained}) == 26 and not any(k in old_vd for k, _ in gained)


@check
def every_mapping_points_to_the_expected_artifact():
    audit = {key(r): r for r in SAFE}
    att = {a['id']: a for a in MINE}
    for r in ROWS:
        a = att[r['attribution']]
        assert (a['artifact'], a['estate'], a['wine'], a['vintage']) == (r['artifact'], r['estate'], r['wine'], r['vintage_id'])
        s = audit[key(r)]
        assert (s['artifact'], s['sha256']) == (r['artifact'], r['sha256'])
        assert PROV[a['provenance']]['artifact'] == r['artifact']


@check
def artifact_hashes_are_unchanged():
    assert not git('diff', '--stat', BEFORE, '--', 'data/model/identity').strip(), 'an identity table changed'
    arts = A.by_id('identity/artifacts.jsonl')
    for r in ROWS:
        assert arts[r['artifact']]['sha256'] == r['sha256'] == PROV[
            next(a['provenance'] for a in MINE if a['id'] == r['attribution'])]['code_state']['sha256']
        held = [L.ROOT + 'sources/' + p['locator']['value'] for p in A.placements_of(r['artifact'])
                if p['locator']['kind'] == 'LOCAL_PATH' and os.path.exists(L.ROOT + 'sources/' + p['locator']['value'])]
        assert held and all(hashlib.sha256(open(q, 'rb').read()).hexdigest() == r['sha256'] for q in held), r['artifact']


@check
def evidence_decision_ids_are_preserved():
    assert not git('diff', '--stat', BEFORE, '--', 'data/evidence', 'data/model/observation/evidence-links.jsonl').strip()
    links = {e['row_key']: e for e in A.table('observation/evidence-links.jsonl') if e['evidence_version'] == 5}
    decs = B.v5_decisions()
    for a in MINE:
        r = next(x for x in ROWS if x['attribution'] == a['id'])
        cs = PROV[a['provenance']]['code_state']
        assert cs['evidence_decisions'] == r['evidence_decisions'] and r['evidence_decisions']
        for rk in r['evidence_decisions']:
            d, ln = decs[rk], links[rk]
            assert d['decision'] == 'ACCEPTED' and d['read']['sha256'] == r['sha256']
            assert (ln['artifact'], ln['estate'], ln['wine']) == (a['artifact'], a['estate'], a['wine'])
            assert (d['ctx'].get('target_vintage') or d['ctx'].get('vintage')) == r['vintage']
        # every decision the audit referenced is accounted for: the mapping's, or another kept beside it
        audit = next(s for s in SAFE if key(s) == key(r))
        assert sorted(r['evidence_decisions'] + [o['decision'] for o in r['other_decisions']]) == sorted(audit['evidence_refs'])
        assert all(o['result'] != 'ACCEPTED' and o['vintage'] != r['vintage'] for o in r['other_decisions'])


@check
def provenance_is_preserved():
    old, new = at_before('data/model/cross/provenance.jsonl').splitlines(), open(
        L.MODEL + 'cross/provenance.jsonl', encoding='utf-8').read().splitlines()
    assert set(old) <= set(new), 'a provenance row changed or was removed'
    added = [json.loads(x) for x in set(new) - set(old)]
    assert sorted(p['id'] for p in added) == sorted(a['provenance'] for a in MINE)
    for a in MINE:
        p = PROV[a['provenance']]
        r = next(x for x in ROWS if x['attribution'] == a['id'])
        assert p['kind'] == 'DOCUMENT' and p['quote'] == r['basis'] and p['derived_from'] == r['manifest_provenance']
        for d in p['derived_from']:
            assert PROV[d]['kind'] == 'LEGACY_MANIFEST' and PROV[d]['artifact'] == a['artifact']
        # the artifact's own manifest attribution is untouched beside the new one
        assert any(x['artifact'] == a['artifact'] and x['provenance'] in p['derived_from'] for x in ATT if x not in MINE)


@check
def estate_wine_vintage_identity_is_exact():
    ew = {(x['estate'], x['wine']) for x in A.table('state/estate-wine.jsonl')}
    vintages = {'vt:%s:%s' % (v['wine'], v['label']) for v in A.table('identity/vintages.jsonl')}
    wines = A.by_id('identity/wines.jsonl')
    audit = {key(r): r for r in SAFE}
    for a in MINE:
        k = (a['estate'], a['wine'], a['vintage'], a['artifact'])
        s = audit[k]
        assert (a['estate'], a['wine']) in ew and a['vintage'] in vintages
        assert a['vintage'] == 'vt:%s:%d' % (s['wine'], s['vintage'])
        assert a['role'] == 'FIRST' and s['proposal']['role'] == 'GRAND_VIN'
        assert s['proposal']['colour'] == (wines.get(a['wine']) or {}).get('type')
    assert len({a['wine'] for a in MINE}) == 14 and len({a['vintage'] for a in MINE}) == 26


@check
def no_open_identity_decision_changed():
    assert not git('diff', '--stat', BEFORE, '--', 'data/model/cross/findings.jsonl',
                   'data/model/identity/transitions.jsonl', 'data/model/state').strip()
    assert not L.read_table('identity/transitions.jsonl')
    f = L.read_table('cross/findings.jsonl')
    assert sum(1 for x in f if x['kind'] == 'AMBIGUOUS_SEMANTICS' and x['status'] == 'OPEN') == 179   # D1
    assert sum(1 for x in f if x['kind'] == 'CONFLICT' and x['status'] == 'OPEN') == 7                # D5 and others
    blocked = B.M34A.open_decision_wines(B.M34A.P.names())
    assert set(blocked.values()) >= {'D2', 'LAPARDE_IDENTITY', 'D5_SECOND_WINE_CONFLICT'}
    assert not {a['wine'] for a in MINE} & set(blocked), 'a mapping to a wine an open decision governs'
    targets = {x['target'] for x in f if x['status'] == 'OPEN'}
    assert not targets & ({a['wine'] for a in MINE} | {a['vintage'] for a in MINE} | {a['artifact'] for a in MINE})


@check
def no_figure_or_value_was_added():
    changed = set(git('diff', '--name-only', BEFORE, '--', 'data/model').split())
    assert changed == {'data/model/' + f for f in ('document/attributions.jsonl', 'cross/provenance.jsonl',
                                                    'derived/vintage-documents.json', 'manifest.json')}, sorted(changed)
    assert not git('diff', '--stat', BEFORE, '--', 'data/app', ':(glob)data/*.js', 'data/sources.json', 'data/history',
                   'data/review', 'data/scope', 'data/discovery', 'assets', 'index.html').strip()
    H.model_changes_are_m2_only(BEFORE)
    m0, m1 = json.loads(at_before('data/model/manifest.json')), json.load(open(L.MODEL + 'manifest.json', encoding='utf-8'))
    assert {k: v['rows'] for k, v in m1['files'].items() if m0['files'].get(k) != v} == {
        'cross/provenance.jsonl': m0['files']['cross/provenance.jsonl']['rows'] + 39,
        'document/attributions.jsonl': m0['files']['document/attributions.jsonl']['rows'] + 39}
    assert m1['stats']['M6']['M3.4B audited mappings'] == 39


@check
def repeated_generation_is_deterministic():
    rows, _ = B.build()
    assert B.body(rows) == open(MANIFEST, 'rb').read()
    for args in (('tools/m34b-apply.py', '--check'), ('tools/m34b-apply.py', '--report', '--check'), ('tools/migrate.py', '--check')):
        run(*args)
    text = open(MANIFEST, encoding='utf-8').read()
    assert L.ROOT not in text and 'Users' not in text and not re.search(r'20\d\d-\d\d-\d\dT', text)


@check
def m34a_audit_output_is_unchanged():
    assert not git('diff', '--stat', BEFORE, '--', 'data/audit/m3.4a-mapping-proposals.jsonl',
                   'docs/PHASE-M3.4A-MAPPING-AUDIT.md', 'data/audit/m3.3-source-acquisition-plan.jsonl').strip()
    run('tools/m34a-mapping-audit.py', '--check')
    # the audits measure the model as it stood before M3.4B, exactly
    assert A.vintage_documents() == json.loads(at_before('data/model/derived/vintage-documents.json'))


@check
def model_rebuild_succeeds():
    assert 'rebuilds byte for byte' in run('tools/migrate.py', '--check')
    assert 'rebuild byte for byte' in run('tools/build-indexes.py', '--check')
    assert 'byte for byte' in run('tools/build-app-data.py', '--check')


@check
def generated_data_is_internally_consistent():
    arts, estates, wines = (A.by_id(t) for t in ('identity/artifacts.jsonl', 'identity/estates.jsonl', 'identity/wines.jsonl'))
    vintages = {'vt:%s:%s' % (v['wine'], v['label']) for v in A.table('identity/vintages.jsonl')}
    vd = json.load(open(L.MODEL + 'derived/vintage-documents.json', encoding='utf-8'))
    for a in MINE:
        assert a['artifact'] in arts and a['estate'] in estates and a['wine'] in wines and a['vintage'] in vintages
        assert a['artifact'] in vd[a['vintage']] and a['provenance'] in PROV
    # the legacy manifest is still exactly the manifest: M3.4B's rows are none of its rows
    legacy = H.legacy_attributions(ATT, PROV)
    assert len(legacy) == len(ATT) - len(MINE)
    assert all(PROV[a['provenance']]['kind'] == 'LEGACY_MANIFEST' for a in legacy)


@check
def the_report_states_the_gate():
    text = open(REPORT, encoding='utf-8').read()
    assert 'SAFE — M3.4B AUDITED EVIDENCE MAPPINGS APPLIED — READY FOR HELD-DOCUMENT REVIEW' in text
    assert '| Applied | 39 |' in text and '| Rejected in preflight | 0 |' in text


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
