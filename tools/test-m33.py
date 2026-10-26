"""M3.3: the highest-yield source acquisition plan (audit only).

    python tools/test-m33.py

Read-only. Holds data/audit/m3.3-source-acquisition-plan.jsonl and its report to the rules of
tools/m33-source-plan.py: every unresolved new-data gap accounted for, every candidate pointing at
real gaps and at URLs the crawl actually saw, scores and order recomputable, policy and open
decisions respected, existing data kept apart from acquisition, and nothing else changed.
"""

import glob
import importlib.util
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_cache as CC  # noqa: E402
import migration_lib as L  # noqa: E402

BEFORE = 'd7fb120'               # M3.2E: the state before M3.3
PLAN = L.ROOT + 'data/audit/m3.3-source-acquisition-plan.jsonl'
CHECKS = []

spec = importlib.util.spec_from_file_location('m33', L.ROOT + 'tools/m33-source-plan.py')
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)
ROWS = [json.loads(l) for l in open(PLAN, encoding='utf-8')]
BUILT = P.build()                 # one fresh build per run, shared by the checks


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode()


def register():
    return [json.loads(l) for l in open(L.ROOT + 'data/audit/data-gap-register.jsonl', encoding='utf-8')]


@check
def every_unresolved_new_data_gap_is_accounted_for():
    gaps = {g['gap_id']: g for g in P.new_data_gaps()}
    assert len(gaps) == 133, len(gaps)                                   # verified, not assumed
    covered = {g for c in ROWS for g in c['gap_ids']}
    assert set(gaps) <= covered, sorted(set(gaps) - covered)[:5]
    # every document-less vintage has a best source (or is recorded as needing discovery)
    _, _, best = BUILT
    nodoc = P.documentless()
    assert len(best) == sum(len(v) for v in nodoc.values()) == sum(
        g['affected_count'] for g in gaps.values() if g['gap_key'].startswith('VINTAGE_NO_DOCUMENT|'))


@check
def no_gap_is_duplicated_or_lost():
    reg = register()
    ids = [r['gap_id'] for r in reg]
    assert len(ids) == len(set(ids)), 'a duplicated gap id'
    m31 = {json.loads(l)['gap_id'] for l in git('show', '6880c16:data/audit/data-gap-register.jsonl').splitlines()}
    assert m31 <= set(ids), 'a gap disappeared from the register'


@check
def every_candidate_references_valid_new_data_gaps():
    valid = {g['gap_id'] for g in P.new_data_gaps()}
    for c in ROWS:
        assert c['gap_ids'] and set(c['gap_ids']) <= valid, c['source_candidate_id']
        assert c['potential_gap_count'] == len(c['gap_ids'])


@check
def no_url_is_invented():
    seen = set()
    for p in glob.glob(L.ROOT + 'sources/discovery/state/*.json'):
        seen.update(json.load(open(p, encoding='utf-8'))['seen'])
    for c in ROWS:
        for loc in c['locators']:
            if loc.startswith('http'):
                assert loc in seen, (c['source_candidate_id'], loc)          # every URL was seen by the crawl
            else:
                assert loc.startswith(('ar_', 'discovery:')), loc            # or a held artifact
        if c['url_status'] == 'suspected':
            assert not [l for l in c['locators'] if l.startswith('http')], c['source_candidate_id']


@check
def scoring_is_deterministic_and_documented():
    assert P.POINTS == {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
    assert P.EFFORT_MID == {'XS': 0.25, 'S': 0.75, 'M': 2.5, 'L': 10, 'XL': 20, 'UNKNOWN': 20}
    for c in ROWS:
        if c['status'] == 'RANKED':
            assert (c['yield_score'], c['item_points'], c['bonus_points']) == P.score(c), c['source_candidate_id']
        else:
            assert c['yield_score'] == 0.0, c['source_candidate_id']


@check
def effort_classes_are_valid():
    for c in ROWS:
        assert c['acquisition_effort'] in ('NONE', 'XS', 'S', 'M', 'L', 'XL', 'UNKNOWN'), c['source_candidate_id']
        assert c['extraction_effort'] in ('XS', 'S', 'M', 'L', 'XL', 'UNKNOWN'), c['source_candidate_id']
        assert set(c['items_by_confidence']) <= {'HIGH', 'MEDIUM', 'LOW'}


@check
def sorting_is_deterministic():
    order = ['XS', 'S', 'M', 'L', 'XL', 'UNKNOWN']
    key = lambda c: (-c['yield_score'], -c['high_confidence_gap_count'],
                     order.index(c['acquisition_effort'] if c['acquisition_effort'] in order else 'UNKNOWN'),
                     c['source_candidate_id'])
    assert ROWS == sorted(ROWS, key=key)
    assert [c['rank'] for c in ROWS] == list(range(1, len(ROWS) + 1))
    assert len({c['source_candidate_id'] for c in ROWS}) == len(ROWS)


@check
def repeated_generation_is_byte_identical():
    rows1, _, _ = BUILT
    rows2, _, _ = P.build()                   # a second, independent build
    assert P.body(rows1) == P.body(rows2) == open(PLAN, 'rb').read()
    out = CC.run([sys.executable, L.ROOT + 'tools/m33-source-plan.py', '--check-all'])   # the plan and its report
    assert out.returncode == 0, out.stdout + out.stderr
    # no clock, no environment in the output
    text = open(PLAN, encoding='utf-8').read()
    assert L.ROOT not in text and 'Users' not in text and 'T0' not in text


@check
def policy_and_open_decisions_stay_respected():
    for c in ROWS:
        if c['source_family'] == 'BLOCKED_BY_POLICY':
            assert c['status'] == 'BLOCKED_BY_POLICY' and c['yield_score'] == 0
        if c['open_decisions']:
            assert c['status'] == 'BLOCKED_BY_EDITORIAL_OR_IDENTITY_DECISION' and c['yield_score'] == 0
    # a URL the site's robots or an AI-agent rule refuses is never in a ranked candidate
    refused = set()
    for p in glob.glob(L.ROOT + 'sources/discovery/state/*.json'):
        for u, s in json.load(open(p, encoding='utf-8'))['seen'].items():
            if s in P.BLOCKED:
                refused.add(u)
    for c in ROWS:
        if c['status'] == 'RANKED':
            assert not set(c['locators']) & refused, c['source_candidate_id']
    # the decisions themselves are untouched
    assert not L.read_table('identity/transitions.jsonl')
    f = L.read_table('cross/findings.jsonl')
    assert sum(1 for x in f if x['kind'] == 'AMBIGUOUS_SEMANTICS' and x['status'] == 'OPEN') == 179
    assert sum(1 for x in f if x['kind'] == 'CONFLICT' and x['status'] == 'OPEN') == 7


@check
def existing_data_is_kept_apart_from_acquisition():
    for c in ROWS:
        if c['category'] == 'A':
            assert c['acquisition_effort'] == 'NONE' and c['already_stored'] and c['requires_new_scraping'] == 'NONE'
        if c['source_family'] == 'DISCOVERED_NOT_ACQUIRED':
            assert c['acquisition_effort'] != 'NONE' and not c['already_stored'] and c['already_discovered']
        if c['source_family'] == 'SOURCE_DISCOVERY_REQUIRED':
            assert c['status'] != 'RANKED'
    _, _, best = BUILT
    assert best and set(best.values()) <= {'EXISTING_ACCEPTED_DOCUMENT', 'EXISTING_FETCHED_DOCUMENT',
                                           'DISCOVERED_NOT_ACQUIRED', 'DISCOVERED_OFFSITE_REDIRECT',
                                           'BLOCKED_BY_POLICY', 'DISCOVERED_DEAD_LINK', 'SOURCE_DISCOVERY_REQUIRED'}


@check
def no_model_evidence_or_app_data_was_mutated():
    # M3.6B adds evidence version 6 beside v1-v5 (the store grows by design); every v1-v5 assertion stands,
    # and v6 must be exactly M3.6B's decisions (historical_m2_scope.evidence_changes_are_m36b_only)
    import historical_m2_scope
    historical_m2_scope.evidence_changes_are_m36b_only(BEFORE)
    assert not git('diff', '--stat', BEFORE, '--', 'data/app', 'data/discovery',
                   'data/history', 'data/review', 'data/scope', ':(glob)data/*.js', 'data/sources.json',
                   'data/audit/m32-recovery-candidates.jsonl',
                   'assets', 'index.html').strip()
    # the model and the gap register: M3.4B (an audited accepted document linked to its vintage, and the
    # register's record of what that resolved) is the only later change, each named exactly
    import historical_m2_scope as H
    H.model_changes_are_m2_only(BEFORE)
    H.register_changes_are_m34b_only(BEFORE)
    for args in (['--check'], ['--report', '--check']):
        out = CC.run([sys.executable, L.ROOT + 'tools/build-data-gap-register.py'] + args)
        assert out.returncode == 0, out.stdout + out.stderr
    b0 = json.load(open(L.MODEL + 'baseline.json', encoding='utf-8'))['groups']
    for g in b0:
        # M3.6B's evidence version 6 named and set aside; v1-v5 and every other group byte for byte
        assert __import__('historical_m2_scope').protected_group(g)['digest'] == b0[g]['digest'], g


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
