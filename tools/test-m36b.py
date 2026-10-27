"""M3.6B: M3.6A's safe mappings and evidence corrections, applied.

    python tools/test-m36b.py

Read-only. Holds the model and the evidence store to M3.6B's allow-lists and nothing else: the eight
web-page mappings, each with its v6 ACCEPTED decision and its attribution; the historical v1-v5
decisions untouched; no canonical value, figure, identity or open decision changed; and everything
recomputable from the committed inputs.
"""

import hashlib
import importlib.util
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_gap_analysis as A  # noqa: E402
import evidence_store as ST  # noqa: E402
import historical_m2_scope as H  # noqa: E402
import check_cache as CC  # noqa: E402
import migration_lib as L  # noqa: E402
import mig_m6_provenance as M6  # noqa: E402

BEFORE = '35f8df8'               # M3.6A's fresh audit: the state before M3.6B
CHECKS = []

spec = importlib.util.spec_from_file_location('m36b', L.ROOT + 'tools/m36b-apply.py')
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
MAPS, SUP, FLAGS = B.allow_lists()
MANIFEST = L.jsonl_lines(B.MAPPINGS)
PROV = A.by_id('cross/provenance.jsonl')
ATT = A.table('document/attributions.jsonl')
MINE = [a for a in ATT if (PROV.get(a['provenance']) or {}).get('actor') == B.ACTOR]
V6 = {M6.row_key(d): d for d in H.m36b_evidence_rows()}


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode('utf-8')


def run(*args):
    out = CC.run([sys.executable] + [L.ROOT + args[0]] + list(args[1:]))
    assert out.returncode == 0, (args, out.stdout[-400:] + out.stderr[-400:])
    return out.stdout


# -- the eight mappings -----------------------------------------------------------------------------

@check
def exactly_the_eight_allow_listed_mappings_are_applied():
    assert len(MAPS) == 8 and len(MANIFEST) == 8
    assert sorted(r['candidate'] for r in MANIFEST) == sorted(r['candidate'] for r in MAPS)
    assert all(r['result'] == 'APPLIED' and not r['failures'] for r in MANIFEST)
    assert sorted(a['id'] for a in MINE) == sorted(r['attribution'] for r in MANIFEST)
    assert all(H.is_m36b_attribution(a, PROV) for a in MINE)


@check
def every_identity_is_exactly_the_audited_one():
    audit = {r['candidate']: r for r in MAPS}
    att = {a['id']: a for a in MINE}
    for r in MANIFEST:
        a, m = att[r['attribution']], audit[r['candidate']]
        assert (a['artifact'], a['estate'], a['wine'], a['vintage']) == (m['artifact'], m['estate'], m['wine'], m['vintage_id'])
        assert (r['page_type'], r['identity_source']) == ('WINE_DOCUMENT', 'h1')
    got = sorted((r['wine_name'], r['vintage']) for r in MANIFEST)
    assert got == sorted([('Château Paloumey', 2022)] * 2 + [('Château Couhins-Lurton', 2019)] * 3
                         + [('Château Corbin', 2018)] * 3), got


@check
def no_extra_mapping_exists():
    old = {json.loads(x)['id'] for x in git('show', '%s:data/model/document/attributions.jsonl' % BEFORE).splitlines()}
    added = sorted(a['id'] for a in ATT if a['id'] not in old)
    assert added == sorted(a['id'] for a in MINE), 'an attribution beyond M3.6B'
    H.model_changes_are_m2_only(BEFORE)
    old_vd = json.loads(git('show', '%s:data/model/derived/vintage-documents.json' % BEFORE))
    new_vd = json.load(open(L.MODEL + 'derived/vintage-documents.json', encoding='utf-8'))
    gained = {(k, x) for k in new_vd for x in set(new_vd[k]) - set(old_vd.get(k, []))}
    assert gained == {(a['vintage'], a['artifact']) for a in MINE}


@check
def paloumey_carousel_is_not_attributed():
    pal = [r for r in MANIFEST if r['wine_name'] == 'Château Paloumey']
    assert len(pal) == 2 and all(any('autres mill' in x or 'other vintages' in x.lower() for x in r['excluded_matches_set_aside'])
                                 or r['excluded_matches_set_aside'] for r in pal)
    assert {a['vintage'] for a in MINE if a['wine'] == 'wn_00167'} == {'vt:wn_00167:2022'}     # not 2013, 2016, 2018, 2019


@check
def couhins_lurton_colour_is_preserved():
    cl = [r for r in MANIFEST if r['wine_name'] == 'Château Couhins-Lurton']
    assert len(cl) == 3 and {r['colour'] for r in cl} == {'WHITE'}
    assert A.by_id('identity/wines.jsonl')['wn_00241']['type'] == 'WHITE_DRY'
    assert H.unchanged_but_m36d(BEFORE, 'data/model/identity')   # no wine created or retyped (M3.6D's, later, aside)


@check
def corbin_guide_date_is_not_the_vintage():
    co = [r for r in MANIFEST if r['wine_name'] == 'Château Corbin']
    assert len(co) == 3 and {r['vintage'] for r in co} == {2018}
    assert all(r['vintage_source'] == 'main heading' and '2018' in r['identity'] for r in co)
    # the three press-dossier PDFs the reader refused are not mapped
    assert not [r for r in MANIFEST if 'RP-CORBIN' in (r['first_url'] or '')]


@check
def every_mapping_has_its_v6_decision_and_provenance():
    for r in MANIFEST:
        d = V6[r['evidence_decision']]
        assert (d['decision'], d['kind'], d['v']) == ('ACCEPTED', 'web_page_review', 6)
        assert d['read']['sha256'] == r['sha256'] and ST.provenance_problem(d) is None
        assert d['reader'] == B.decider_fingerprint() and d['ctx']['target_vintage'] == r['vintage']
        a = next(x for x in MINE if x['id'] == r['attribution'])
        p = PROV[a['provenance']]
        assert p['kind'] == 'DOCUMENT' and p['artifact'] == r['artifact']
        assert p['code_state']['evidence_decisions'] == [r['evidence_decision']]
        # the held bytes are the artifact's
        blob = L.ROOT + 'sources/' + d['read']['path']
        assert os.path.exists(blob) and hashlib.sha256(B.held_bytes(d['read']['path'])).hexdigest() == r['sha256']


# -- the 199 corrections ----------------------------------------------------------------------------

CORR = L.jsonl_lines(B.CORRECTIONS)
FLAGROWS = L.jsonl_lines(B.FLAGS)


def v5_rows():
    return {M6.row_key(d): d for d in L.jsonl_lines(L.ROOT + 'data/evidence/decisions-v5.jsonl')}


@check
def exactly_199_superseding_decisions_each_asking_its_v5_question():
    assert len(CORR) == 199 and all(r['result'] == 'APPLIED' and not r['failures'] for r in CORR)
    assert sorted(r['decision'] for r in CORR) == sorted(c['decision'] for c in SUP)
    rows = [d for d in V6.values() if d['kind'] == 'correction']
    assert len(rows) == 199 and sorted(M6.row_key(d) for d in rows) == sorted(r['superseded_by'] for r in CORR)
    audit = {c['decision']: c for c in SUP}
    for r in CORR:
        d = V6[r['superseded_by']]
        assert d['decision'] == 'REFUSED' and d['code'] == audit[r['decision']]['category'] == r['category']
        assert d['supersedes'] == {'row_key': r['decision'], 'v': 5, 'decision': 'ACCEPTED', 'code': 'ACCEPTED'}
        assert json.loads(r['superseded_by'])[:-1] == json.loads(r['decision'])[:-1]      # the same question
        assert d['read']['sha256'] == r['sha256'] and ST.provenance_problem(d) is None
    assert not [d for d in V6.values() if d['kind'] == 'correction' and d['decision'] == 'ACCEPTED']


@check
def the_corrections_are_the_latest_answers_and_the_originals_stand():
    import evidence as EV
    latest = H.latest_before_m36e()                  # as M3.6B left it: M3.6E's v7, a later correction, set aside
    v5 = v5_rows()
    for r in CORR:
        old = v5[r['decision']]
        assert old['decision'] == 'ACCEPTED' and old['read']['sha256'] == r['sha256']        # historical row unchanged
        assert latest[EV.row_key(old)[:-1]] == V6[r['superseded_by']]                         # read through v6
    for f in FLAGROWS:                                                                        # a flag supersedes nothing
        assert latest[EV.row_key(v5[f['decision']])[:-1]] == v5[f['decision']]
    assert not git('diff', '--stat', BEFORE, '--', 'data/evidence/decisions-v1.jsonl', 'data/evidence/decisions-v2.jsonl',
                   'data/evidence/decisions-v3.jsonl', 'data/evidence/decisions-v4.jsonl',
                   'data/evidence/decisions-v5.jsonl').strip()


@check
def replacements_are_preserved_and_none_invented():
    v5 = v5_rows()
    m35 = {a['id'] for a in A.m35_attributions()}
    withr = [r for r in CORR if r['replacement']['decision']]
    assert len(withr) == 62 and len(CORR) - len(withr) == 137
    for r in withr:
        d = v5[r['replacement']['decision']]
        assert d['decision'] == 'ACCEPTED' and d['read']['sha256'] == r['sha256'] and r['replacement']['decision'] != r['decision']
        assert r['replacement']['attribution'] is None or r['replacement']['attribution'] in m35
        assert V6[r['superseded_by']]['replacement']['decision'] == r['replacement']['decision']
    for r in CORR:
        if not r['replacement']['decision']:
            assert not r['document_is']['model_wines'] and V6[r['superseded_by']]['document_is']['unlisted']
    assert H.unchanged_but_m36d(BEFORE, 'data/model/identity', 'data/model/state')   # no wine created (M3.6D's aside)


@check
def the_twenty_cuvee_de_mongravey_flags():
    assert len(FLAGROWS) == 20 and sorted(f['decision'] for f in FLAGROWS) == sorted(c['decision'] for c in FLAGS)
    corrected = {r['decision'] for r in CORR}
    for f in FLAGROWS:
        assert f['flag'] == 'RETAIN_AS_HISTORICAL_ACCEPTANCE_BUT_FLAG' and f['reason'] == B.FLAG_REASON
        assert f['replacement'] is None and f['decision'] not in corrected
        assert 'cuvee de mongravey' in f['document_is']['title'][0] and f['wine_name'] == 'Château Mongravey'
    assert not [n for n in A.table('identity/names.jsonl') if 'cuvee de mongravey' in A.fold(n['name'])]


@check
def the_register_records_only_the_mappings():
    H.register_changes_are_m34b_only(BEFORE)
    reg = L.jsonl_lines(L.ROOT + 'data/audit/data-gap-register.jsonl')
    m36b = [g for g in reg if any(b['phase'] == 'M3.6B' for b in (g.get('resolution') or {}).get('by', []))]
    assert sorted(g['entity_id'] for g in m36b) == ['es_00167', 'es_00241', 'es_00398']
    assert all(g['gap_key'].startswith('VINTAGE_NO_DOCUMENT|') for g in m36b)


@check
def the_report_states_the_gate():
    assert 'is current' in run('tools/m36b-apply.py', '--report', '--check')
    text = open(B.REPORT, encoding='utf-8').read()
    assert 'M3.6B corrected evidence history without erasing the historical record.' in text
    assert 'SAFE — M3.6B AUDITED MAPPINGS AND EVIDENCE CORRECTIONS APPLIED' in text


# -- safety ---------------------------------------------------------------------------------------

@check
def historical_evidence_and_everything_else_unchanged():
    H.evidence_changes_are_m36b_only(BEFORE)
    assert H.evidence_versions_before_m36b() == [1, 2, 3, 4, 5] and H.evidence_rows_before_m36b() == 177127
    H.unchanged_but_m36d(BEFORE, 'data/model/identity', 'data/model/state')   # M3.6D's wine, later, aside
    assert not git('diff', '--stat', BEFORE, '--', 'data/model/canonical', 'data/model/observation',
                   'data/model/reconciliation', 'data/model/cross/findings.jsonl',
                   'data/app', ':(glob)data/*.js', 'data/sources.json', 'data/discovery',
                   'data/history', 'data/review', 'data/scope', 'assets', 'index.html').strip()
    f = L.read_table('cross/findings.jsonl')
    assert sum(1 for x in f if x['kind'] == 'AMBIGUOUS_SEMANTICS' and x['status'] == 'OPEN') == 179      # D1
    assert sum(1 for x in f if x['kind'] == 'CONFLICT' and x['status'] == 'OPEN') == 7                 # D5 and others
    assert not L.read_table('identity/transitions.jsonl')
    blocked = B.X.M34A.open_decision_wines(B.X.P.names())
    assert not {a['wine'] for a in MINE} & set(blocked)


@check
def everything_recomputes():
    assert 'is current' in run('tools/m36b-apply.py', '--check')
    assert 'rebuilds byte for byte' in run('tools/migrate.py', '--check')
    assert 'rebuild byte for byte' in run('tools/build-indexes.py', '--check')
    assert 'byte for byte' in run('tools/build-app-data.py', '--check')
    assert 'every part matches' in run('tools/evidence_store.py', '--verify')
    out = CC.run([sys.executable, '-I', L.ROOT + 'tools/m36a-rerun.py', '--check-all'])
    assert out.returncode == 0, out.stdout[-300:]                                  # the audit it applied is unchanged


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
