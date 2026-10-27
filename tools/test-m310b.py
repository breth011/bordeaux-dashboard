"""Phase M3.10B: the four Durfort-Vivens documents M3.10A registered, accepted as evidence (v9) and attributed
to their exact wine and vintage (tools/m310b-accept.py; the migration's m310b_attributions).

    python tools/test-m310b.py

Read-only. Exactly M3.10A's four artifacts are decided - each one of M3.9's SAFE_TO_MAP documents, each for
Château Durfort-Vivens and the vintage its text states (2014, 2014, 2021, 2024) - as v9 ACCEPTED rows appended
beside v1-v8; each is attributed once in the model. Acceptance is not value application: no observation,
reconciliation or canonical value is added, the 2014 English and French sheets stay two artifacts of one claim,
and the 2024 oak is in no canonical value. The reader, discovery, the M3.8/M3.9/M3.10A audits and the app are
as they were; the decisions, manifest and report recompute.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_cache as CC  # noqa: E402
import evidence_store as ST  # noqa: E402
import historical_m2_scope as H  # noqa: E402
import migration_lib as L  # noqa: E402
import mig_m6_provenance as M6  # noqa: E402

BEFORE = '995276d'               # M3.10A: the state M3.10B decides on
MANIFEST = L.ROOT + H.M310B_MANIFEST
ARTIFACTS = {'ar_037069', 'ar_037068', 'ar_037070', 'ar_037071'}
WINE, ESTATE = 'wn_00263', 'es_00263'
READER = ('tools/m35_rubric.py', 'tools/web_evidence.py', 'tools/sheetreader.py', 'tools/read-fiches.py',
          'tools/m34a-mapping-audit.py', 'tools/model_schema.py', 'tools/evidence.py')
CHECKS = []


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode('utf-8')


def decisions():
    return [r for r in L.jsonl_lines(MANIFEST) if r['record'] == 'decision']


@check
def t01_exactly_m310as_four_artifacts_and_m39s_verdicts():
    ms = decisions()
    reg = {r['candidate']: r for r in L.jsonl_lines(L.ROOT + H.M310A_MANIFEST) if r['record'] == 'result'}
    m39 = {'m3.9:%d' % r['n']: r for r in L.jsonl_lines(L.ROOT + 'data/audit/m3.9-evidence-review.jsonl')
           if r['record'] == 'review'}
    assert len(ms) == 4 and {m['artifact'] for m in ms} == ARTIFACTS == {r['artifact'] for r in reg.values()}
    for m in ms:
        assert reg[m['candidate']]['artifact'] == m['artifact'] and m39[m['candidate']]['disposition'] == 'SAFE_TO_MAP'
        assert (m['estate'], m['wine']) == (ESTATE, WINE) == (m39[m['candidate']]['estate'], m39[m['candidate']]['wine'])
    assert sorted(m['vintage'] for m in ms) == [2014, 2014, 2021, 2024]


@check
def t02_v9_is_exactly_the_four_acceptances():
    rows = H.m310b_evidence_rows()
    assert ST.versions()[-1] == H.M310B_EVIDENCE_VERSION == 9 and len(rows) == 4
    by = {M6.row_key(d): d for d in rows}
    for m in decisions():
        d = by[m['evidence_decision']]
        assert (d['kind'], d['decision'], d['code'], d['v']) == ('guard', 'ACCEPTED', 'ACCEPTED', 9)
        assert d['ctx']['target_wine'] == 'Château Durfort-Vivens' and d['ctx']['target_role'] == 'grand'
        assert d['ctx']['target_vintage'] == m['vintage'] and d['read']['sha256'] == m['sha256']
        assert d['reader'] == m['decider'] and any(m['candidate'] in e for e in d['evidence'])
        assert not any(k in json.dumps(d['evidence']).lower() for k in ('http', '.pdf', 'gc-lurton', 'folder'))


@check
def t03_v1_to_v8_byte_for_byte_and_append_only():
    H.evidence_unchanged_but_m310b(BEFORE)
    old = ['data/evidence/decisions-v%d.jsonl' % v for v in range(1, 9)]
    assert not git('diff', '--stat', BEFORE, '--', *old).strip() and ST.verify() == []
    names = {os.path.basename(m['url']) for m in decisions()}
    assert not [d for d in ST.iter_rows(list(range(1, 9))) if d.get('artifact') in names]


@check
def t04_four_attributions_and_nothing_else():
    prov = {p['id']: p for p in L.read_table('cross/provenance.jsonl')}
    att = [a for a in L.read_table('document/attributions.jsonl') if a['artifact'] in ARTIFACTS]
    assert len(att) == 4 and all(H.is_m310b_attribution(a, prov) for a in att)
    for a in att:
        [m] = [m for m in decisions() if m['attribution'] == a['id']]
        assert (a['estate'], a['wine'], a['vintage'], a['role'], a['method'], a['status']) == \
            (ESTATE, WINE, m['vintage_id'], 'FIRST', 'DOCUMENT_TEXT', 'ACCEPTED')
        assert prov[a['provenance']]['code_state']['evidence_decisions'] == [m['evidence_decision']]
    vd = json.load(open(L.MODEL + 'derived/vintage-documents.json', encoding='utf-8'))
    for m in decisions():
        assert m['artifact'] in vd[m['vintage_id']]


@check
def t05_no_new_wine_estate_value_observation_or_reconciliation():
    changed = {f[len('data/model/'):] for f in git('diff', '--name-only', BEFORE, '--', 'data/model').split()}
    mine = {'document/attributions.jsonl', 'cross/provenance.jsonl', 'derived/vintage-documents.json', 'manifest.json'}
    # M3.10C's values, observations and reconciliations, a later phase, set aside (their rows: t06, t07)
    assert {f for f in changed if f in mine or f not in H.M310C_FILES} == mine, sorted(changed)
    old = set(git('show', '%s:data/model/document/attributions.jsonl' % BEFORE).splitlines())
    new = set(open(L.MODEL + 'document/attributions.jsonl', encoding='utf-8').read().splitlines())
    assert old <= new and {json.loads(x)['artifact'] for x in new - old} == ARTIFACTS and len(new - old) == 4


@check
def t06_the_2014_pair_is_two_artifacts_of_one_claim():
    pair = [m for m in decisions() if m['vintage'] == 2014]
    assert len(pair) == 2 and len({m['artifact'] for m in pair}) == 2 and len({m['vintage_id'] for m in pair}) == 1
    assert {m['same_claim_as'][0] for m in pair} == {m['artifact'] for m in pair}
    vt = pair[0]['vintage_id']
    # no observation or reconciliation added for the pair (the vintage's legacy rating observation stands);
    # M3.10C's, a later phase, set aside
    prov = {p['id']: p for p in L.read_table('cross/provenance.jsonl')}
    for rel in ('observation/observations.jsonl', 'reconciliation/reconciliations.jsonl'):
        old = [x for x in git('show', '%s:data/model/%s' % (BEFORE, rel)).splitlines() if json.loads(x)['subject'] == vt]
        new = [json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
               for r in L.read_table(rel) if r['subject'] == vt and not H.is_m310c_row(rel, r, prov)]
        assert [json.loads(x) for x in old] == [json.loads(x) for x in new], rel
    assert not [r for r in L.read_table('reconciliation/reconciliations.jsonl') if r['subject'] == vt
                and not H.is_m310c_row('reconciliation/reconciliations.jsonl', r, prov)]


@check
def t07_no_value_and_no_2024_oak():
    prov = {p['id']: p for p in L.read_table('cross/provenance.jsonl')}
    vals = [v for v in L.read_table('canonical/values.jsonl')        # M3.10C's, a later phase, set aside
            if v['subject'] in {m['vintage_id'] for m in decisions()}
            and not H.is_m310c_row('canonical/values.jsonl', v, prov)]
    assert not vals, vals[:2]
    for m in decisions():
        assert m['stages']['value_applied'].startswith('NONE'), m['candidate']


@check
def t08_audits_discovery_reader_and_app_unchanged():
    __import__('historical_m2_scope').register_changes_are_m34b_only(BEFORE)   # M3.10B's resolution, a later linking phase
    paths = ('data/audit/m3.8-acquisition-pilot.jsonl', 'data/audit/m3.9-evidence-review.jsonl',
             'data/audit/m3.10a-external-artifact-registration.jsonl', 'data/discovery', 'data/app',
             'data/websites.js', 'assets', 'index.html',
             'tools/discover.py', 'tools/discover_extract.py', *READER)
    assert not git('diff', '--stat', BEFORE, '--', *paths).strip()
    assert not git('status', '--porcelain', '--', *paths).strip()
    assert not git('ls-files', '--', 'sources/acquisition').strip()


@check
def t09_the_earlier_guards_set_m310b_aside():
    H.model_changes_are_m2_only('345f892')
    H.unchanged_but_m310a(BEFORE, 'data/model')
    H.evidence_unchanged_but_m36e('1a58c92')


@check
def t10_decisions_manifest_and_report_recompute():
    out = CC.run([sys.executable, L.ROOT + 'tools/m310b-accept.py', '--check'], cwd=L.ROOT)
    assert out.returncode == 0, (out.stdout + out.stderr)[-400:]


@check
def t11_the_model_rebuilds_from_scratch_and_with_its_registry():
    out = CC.run([sys.executable, L.ROOT + 'tools/migrate.py', '--check'], cwd=L.ROOT)
    assert out.returncode == 0, (out.stdout + out.stderr)[-400:]


@check
def t12_the_generated_views_are_current():
    for cmd in ('build-indexes.py', 'build-app-data.py', 'build-data-gap-register.py'):
        out = CC.run([sys.executable, L.ROOT + 'tools/' + cmd, '--check'], cwd=L.ROOT)
        assert out.returncode == 0, (cmd, (out.stdout + out.stderr)[-300:])


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
