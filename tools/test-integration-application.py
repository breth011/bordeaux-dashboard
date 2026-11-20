"""The integration application (tools/integration_application.py): the repository is in exactly one of two states.

    python tools/test-integration-application.py

Read-only. PRE_APPLY: none of the application exists - evidence v9, 5,292 / 13,004 / 12,211, manifests 0 / 0 / 9 / 0,
no row of it in the model, no record of it in the gap register. POST_APPLY: exactly the reviewed application - v10
with its 34 decisions, 34 attributions (17 REVIEWED_LISTING, 17 DOCUMENT_TEXT) on 51 provenance rows, 51 values,
observations and reconciliations on 102, no vintage created, 5,292 / 13,055 / 12,245 - with the C6 and R4 records as
the recording policy fixes them, and the gap register's record of what it resolved. Anything in between fails.
"""
import collections
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_cache as CC  # noqa: E402
import integration_application as IA  # noqa: E402
import migration_lib as L  # noqa: E402

CHECKS = []
PHASE = IA.phase()


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode('utf-8')


def prov():
    return {p['id']: p for p in L.read_table('cross/provenance.jsonl')}


@check
def s01_exactly_one_state_and_its_figures():
    assert IA.verify() == PHASE
    want = IA.PRE_APPLY if PHASE == 'PRE_APPLY' else IA.POST_APPLY
    assert IA.counts() == want


@check
def s02_a_half_applied_state_is_neither():
    """The detector, on stubbed inputs: every partial combination of manifests, store and stats is refused."""
    import evidence_store as ST
    keep = (IA.manifest_rows, ST.versions, IA._stats, IA.evidence_rows)
    full = {k: [dict(zip([IA.ID_FIELD[k]], [i])) for i in IA.IDS[k]] for k in IA.MANIFESTS}
    stats = {'M6': 34, 'M7': 51}
    cases = [
        ('manifests written, nothing applied', full, False, {'M6': None, 'M7': None}),
        ('evidence applied, nothing else', {k: [] for k in IA.MANIFESTS}, True, {'M6': None, 'M7': None}),
        ('values not applied', full, True, {'M6': 34, 'M7': None}),
        ('a manifest short of a row', dict(full, value=full['value'][:-1]), True, stats),
        ('rows not the reviewed ones', full, True, stats),          # their digest differs (ids only)
    ]
    try:
        for name, rows, has, st in cases:
            IA.manifest_rows = lambda kind, rows=rows: rows[kind]
            ST.versions = lambda has=has: list(range(1, 11 if has else 10))
            IA._stats = lambda st=st: st
            IA.evidence_rows = lambda: []
            try:
                IA.phase()
            except AssertionError as x:
                assert 'neither unapplied nor applied' in str(x), (name, str(x))
                continue
            raise AssertionError('accepted: %s' % name)
    finally:
        IA.manifest_rows, ST.versions, IA._stats, IA.evidence_rows = keep


@check
def s03_the_rows_are_exactly_those_added_since_the_start():
    for rel in IA.IA_TABLES:
        mine = set(IA.row_ids(rel))
        if PHASE == 'PRE_APPLY':
            assert not mine, rel
            continue
        old = {IA.row_key(rel, json.loads(x)) for x in git('show', '%s:data/model/%s' % (IA.PRE_APPLY_COMMIT, rel)).splitlines()}
        new = {IA.row_key(rel, r) for r in L.read_table(rel)}
        assert old <= new and mine == new - old, rel
    assert git('diff', '--name-only', IA.PRE_APPLY_COMMIT, '--', 'data/model/identity').strip() == ''


@check
def s04_c6_records_say_the_unit_is_derived():
    p = prov()
    obs = [o for o in L.read_table('observation/observations.jsonl')
           if IA.is_row('observation/observations.jsonl', o, p) and o['confidence'] == 'UNIT_FROM_LAYOUT']
    assert len(obs) == (15 if PHASE == 'POST_APPLY' else 0)
    vals = {(v['subject'], v['field']): v for v in L.read_table('canonical/values.jsonl')}
    for o in obs:
        assert o['field'] == 'yld' and o['unit'] == 'hl/ha' and isinstance(o['raw_value'], list) and len(o['raw_value']) == 2
        assert o['raw_value'][0].endswith('hl') and o['raw_value'][1].endswith('ha'), o['raw_value']
        assert o['extraction']['method'] == 'yield-layout/1'
        d = p[o['provenance']]
        cs = d['code_state']
        flat = json.dumps(cs)
        assert d['quote'] == ' | '.join(o['raw_value']) and 'hl/ha' not in d['quote'] and 'hl/ha' not in json.dumps(o['raw_value'])
        assert '"unit_derived": true' in flat and '"source_prints_hl_per_ha": false' in flat, o['id']
        assert vals[(o['subject'], 'yld')]['derivation'] == 'UNIT_FROM_LAYOUT'


@check
def s05_r4_records_are_reviewed_listings_never_m34a():
    p = prov()
    att = [a for a in L.read_table('document/attributions.jsonl') if IA.is_row('document/attributions.jsonl', a, p)]
    listing = [a for a in att if a['method'] == 'REVIEWED_LISTING']
    assert len(listing) == (17 if PHASE == 'POST_APPLY' else 0)
    for a in listing:
        d = p[a['provenance']]
        assert d['kind'] == 'ESTATE_PUBLICATION' and d.get('source') and 'M34A' not in json.dumps(d), a['id']
        for x in d.get('derived_from') or []:
            assert 'M34A' not in json.dumps(p[x]), (a['id'], x)
    if PHASE == 'POST_APPLY':
        review = [r for r in L.jsonl_lines(L.ROOT + IA.REVIEW) if r.get('record') == 'review']
        r4 = [c for r in review for c in r['claims'] if c.get('identity_gate') == 'REVIEWED_LISTING']
        assert r4 and all(c['evidence_of_document']['text_check']['role'].startswith('veto only') for c in r4)


@check
def s06_the_gap_register_records_what_it_resolved():
    res = json.load(open(L.ROOT + IA.RESOLUTIONS, encoding='utf-8'))
    reg = L.jsonl_lines(L.ROOT + 'data/audit/data-gap-register.jsonl')
    by = [(g['gap_id'], b) for g in reg for b in (g.get('resolution') or {}).get('by', []) if b['phase'] == IA.PHASE]
    if PHASE == 'PRE_APPLY':
        assert IA.PHASE not in res and not by
        return
    assert res.get(IA.PHASE) == IA.resolution_entry(), res.get(IA.PHASE)
    assert len(by) == 4 and sum(b['items'] for _, b in by) == 32 and {b['commit'] for _, b in by} == {IA.applying_commit()}
    # a full test run's shared result when another suite has passed it in this state (tools/check_cache.py)
    out = CC.run([sys.executable, L.ROOT + 'tools/build-data-gap-register.py', '--check-all'], cwd=L.ROOT)
    assert out.returncode == 0 and out.stdout.count('is current') == 2, out.stdout + out.stderr


@check
def s07_the_quality_audit_is_current():
    out = subprocess.run([sys.executable, L.ROOT + 'tools/quality-audit.py', '--check'], cwd=L.ROOT,
                         capture_output=True, text=True)
    assert out.returncode == 0 and 'quality audit current' in out.stdout, out.stdout + out.stderr
    q = json.load(open(L.MODEL + 'checks/quality-audit.json', encoding='utf-8'))
    assert q['summary']['orphan documents'] == {'PRE_APPLY': 723, 'POST_APPLY': 722}[PHASE]


def main():
    fails = 0
    for f in CHECKS:
        try:
            f()
            print('ok   %s' % f.__name__)
        except Exception as ex:
            fails += 1
            print('FAIL %s: %s' % (f.__name__, (str(ex) or repr(ex))[:400]))
    print('%d check(s), %s' % (len(CHECKS), '%d FAIL' % fails if fails else 'all pass'))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
