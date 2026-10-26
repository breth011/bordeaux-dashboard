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
    out = subprocess.run([sys.executable] + [L.ROOT + args[0]] + list(args[1:]), capture_output=True, text=True)
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
    assert not git('diff', '--stat', BEFORE, '--', 'data/model/identity').strip()            # no wine created or retyped


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


# -- safety ---------------------------------------------------------------------------------------

@check
def historical_evidence_and_everything_else_unchanged():
    H.evidence_changes_are_m36b_only(BEFORE)
    assert H.evidence_versions_before_m36b() == [1, 2, 3, 4, 5] and H.evidence_rows_before_m36b() == 177127
    assert not git('diff', '--stat', BEFORE, '--', 'data/model/canonical', 'data/model/observation',
                   'data/model/reconciliation', 'data/model/cross/findings.jsonl', 'data/model/identity',
                   'data/model/state', 'data/app', ':(glob)data/*.js', 'data/sources.json', 'data/discovery',
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
    out = subprocess.run([sys.executable, '-I', L.ROOT + 'tools/m36a-rerun.py', '--check'], capture_output=True, text=True)
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
