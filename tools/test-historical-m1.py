"""Historical model M1: the model can carry history; it has been told none.

    python tools/test-historical-m1.py

Read-only. M1 adds the structures M0 proposed (docs/PHASE-M0-HISTORICAL-
SCHEMA.md), as docs/schema/historical-m1-contract.json merged by
tools/model_schema.py: Observation.claimed_validity, claimed_window and
statement_mode; the TimeWindow type; IdentityTransition.occurred (with `at`
now optional) and the kind RELATED_UNSPECIFIED; Reconciliation.dispositions;
and the checks that go with them. These checks exercise each structure on
rows built here, in memory - never in data/model/ - and hold the model itself
to what it was: every row valid unchanged, nothing populated, no current fact
made historical.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import migration_lib as L  # noqa: E402
import model_schema as S  # noqa: E402

BEFORE = 'c0a4b4b'               # M0: the model before M1
CHECKS = []


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode()


def b(kind, value=None, axis=None, precision=None):
    return S.bound(kind, value, axis, precision, 'pv_basis' if value is not None else None)


def obs(**extra):
    row = {'id': 'ob_test', 'subject': 'wn_00001', 'field': 'name', 'extraction': {'method': 'TEST'},
           'confidence': 'TEST', 'observed_at': '2026-10-25', 'provenance': 'pv_test', 'artifact': 'ar_000001',
           'subject_status': 'ESTABLISHED'}
    row.update(extra)
    return row


def transition(**extra):
    row = {'id': 'it_test', 'kind': 'RENAMED', 'from': 'wn_00001', 'to': 'wn_00001',
           'certainty': 'PROBABLE', 'provenance': 'pv_test'}
    row.update(extra)
    return row


def rec(**extra):
    row = {'id': 'rc_test', 'subject': 'nm_test', 'field': 'valid_from', 'candidates': ['ob_a', 'ob_b'],
           'rule': 'MANUAL_DECISION', 'status': 'RESOLVED', 'reason': 'test', 'resolver': 'test',
           'decided_at': '2026-10-25', 'provenance': 'pv_test'}
    row.update(extra)
    return row


def valid(entity, row):
    errs = S.check_row(entity, row)
    assert not errs, errs


def invalid(entity, row, words):
    errs = S.check_row(entity, row)
    assert errs and any(words in e for e in errs), (words, errs)


VINTAGE_2008 = b('EXACT', '2008', 'VINTAGE', 'VINTAGE')
POINT_2008 = {'earliest': VINTAGE_2008, 'latest': VINTAGE_2008}


# ---------------------------------------------------------------- claims (cases 1-10)

@check
def c01_observation_without_historical_fields():
    valid('Observation', obs())


@check
def c02_explicit_claimed_validity():
    valid('Observation', obs(claimed_validity={'valid_from': VINTAGE_2008, 'valid_to': b('OPEN')},
                             statement_mode='EXPLICIT'))


@check
def c03_implied_claimed_validity():
    valid('Observation', obs(claimed_validity={'valid_from': b('NO_LATER_THAN', '2008', 'CALENDAR', 'YEAR'),
                                               'valid_to': b('OPEN')}, statement_mode='IMPLIED'))


@check
def c04_claimed_event_window_needs_a_mode_and_a_source():
    valid('Observation', obs(field='transition.RENAMED', claimed_window=POINT_2008, statement_mode='EXPLICIT'))
    invalid('Observation', obs(claimed_window=POINT_2008), 'needs a statement_mode')
    invalid('Observation', obs(statement_mode='EXPLICIT'), 'statement_mode without a temporal claim')
    invalid('Observation', obs(claimed_window=POINT_2008, statement_mode='STATED'), 'StatementMode')
    invalid('Observation', obs(claimed_window=POINT_2008, statement_mode='EXPLICIT',
                               claimed_validity={'valid_from': b('UNKNOWN'), 'valid_to': b('OPEN')}), 'not both')
    no_artifact = obs(claimed_window=POINT_2008, statement_mode='EXPLICIT')
    no_artifact.pop('artifact')
    invalid('Observation', no_artifact, 'no artifact and no quote')
    assert not S.check_row('Observation', no_artifact, provenance={'pv_test': {'quote': 'from the 2008 vintage'}})


@check
def c05_calendar_window():
    valid('Observation', obs(claimed_window={'earliest': b('NO_EARLIER_THAN', '2005', 'CALENDAR', 'YEAR'),
                                             'latest': b('NO_LATER_THAN', '2008-06', 'CALENDAR', 'MONTH')},
                             statement_mode='EXPLICIT'))
    invalid('Observation', obs(claimed_window={'earliest': b('EXACT', '2008', 'CALENDAR', 'DAY'),
                                               'latest': b('EXACT', '2008', 'CALENDAR', 'YEAR')},
                               statement_mode='EXPLICIT'), 'does not match precision')


@check
def c06_vintage_window_and_no_axis_conversion():
    valid('Observation', obs(claimed_window=POINT_2008, statement_mode='EXPLICIT'))
    invalid('Observation', obs(claimed_window={'earliest': b('EXACT', '2007', 'CALENDAR', 'YEAR'),
                                               'latest': VINTAGE_2008}, statement_mode='EXPLICIT'), 'two axes')
    invalid('Observation', obs(claimed_window={'earliest': b('EXACT', '2008-05', 'VINTAGE', 'MONTH'),
                                               'latest': VINTAGE_2008}, statement_mode='EXPLICIT'), 'VINTAGE bound')


@check
def c07_open_and_unknown_lower_bound():
    # A state's start is UNKNOWN, never OPEN; an event's earliest may be UNKNOWN.
    valid('Observation', obs(claimed_validity={'valid_from': b('UNKNOWN'), 'valid_to': VINTAGE_2008},
                             statement_mode='EXPLICIT'))
    invalid('Observation', obs(claimed_validity={'valid_from': b('OPEN'), 'valid_to': VINTAGE_2008},
                               statement_mode='EXPLICIT'), 'OPEN only as valid_to')
    valid('Observation', obs(claimed_window={'earliest': b('UNKNOWN'), 'latest': VINTAGE_2008},
                             statement_mode='EXPLICIT'))


@check
def c08_open_upper_bound_only_for_a_state():
    valid('Observation', obs(claimed_validity={'valid_from': VINTAGE_2008, 'valid_to': b('OPEN')},
                             statement_mode='EXPLICIT'))
    invalid('Observation', obs(claimed_window={'earliest': VINTAGE_2008, 'latest': b('OPEN')},
                               statement_mode='EXPLICIT'), 'OPEN in a window')


@check
def c09_unknown_date():
    valid('Observation', obs(claimed_window={'earliest': b('UNKNOWN'), 'latest': b('UNKNOWN')},
                             statement_mode='IMPLIED'))
    invalid('Observation', obs(claimed_window={'earliest': {'kind': 'UNKNOWN', 'value': '2008'},
                                               'latest': b('UNKNOWN')}, statement_mode='IMPLIED'), 'with a value')


@check
def c10_reversed_bounds_rejected():
    invalid('Observation', obs(claimed_validity={'valid_from': b('EXACT', '2010', 'VINTAGE', 'VINTAGE'),
                                                 'valid_to': b('NO_LATER_THAN', '2007', 'VINTAGE', 'VINTAGE')},
                               statement_mode='EXPLICIT'), 'after upper bound')
    invalid('Observation', obs(claimed_window={'earliest': b('NO_EARLIER_THAN', '2009', 'CALENDAR', 'YEAR'),
                                               'latest': b('NO_LATER_THAN', '2008', 'CALENDAR', 'YEAR')},
                               statement_mode='EXPLICIT'), 'after upper bound')
    # same year at different precisions is not reversed
    valid('Observation', obs(claimed_window={'earliest': b('NO_EARLIER_THAN', '2008', 'CALENDAR', 'YEAR'),
                                             'latest': b('NO_LATER_THAN', '2008-03-01', 'CALENDAR', 'DAY')},
                             statement_mode='EXPLICIT'))


# ---------------------------------------------------------------- transitions (cases 11-15)

@check
def c11_transition_with_at():
    valid('IdentityTransition', transition(at=VINTAGE_2008))


@check
def c12_transition_with_occurred():
    valid('IdentityTransition', transition(occurred=POINT_2008))


@check
def c13_transition_with_neither_fails():
    invalid('IdentityTransition', transition(), 'exactly one of at and occurred')


@check
def c14_transition_with_both_fails():
    invalid('IdentityTransition', transition(at=VINTAGE_2008, occurred=POINT_2008), 'exactly one of at and occurred')


@check
def c15_related_unspecified_and_identity_rules():
    valid('IdentityTransition', transition(kind='RELATED_UNSPECIFIED', to='wn_00002', certainty='UNRESOLVED',
                                           occurred={'earliest': b('UNKNOWN'), 'latest': b('UNKNOWN')}))
    invalid('IdentityTransition', transition(kind='RELATED_UNSPECIFIED', to='wn_00002', certainty='CONFIRMED',
                                             occurred=POINT_2008), 'establishes nothing')
    invalid('IdentityTransition', transition(kind='POSSIBLY_SAME', to='wn_00002', certainty='PROBABLE',
                                             occurred=POINT_2008), 'establishes nothing')
    # rename is not succession, and succession is not rename
    invalid('IdentityTransition', transition(to='wn_00002', occurred=POINT_2008), 'RENAMED relates one subject')
    valid('IdentityTransition', transition(kind='SUCCEEDED_BY', to='wn_00002', occurred=POINT_2008))
    invalid('IdentityTransition', transition(kind='SUCCEEDED_BY', occurred=POINT_2008), 'SUCCEEDED_BY relates two')
    invalid('IdentityTransition', transition(kind='SUCCEEDED_BY', to='es_00001', occurred=POINT_2008), 'SUCCEEDED_BY')
    # the existing kinds are all still accepted
    for k in ('MERGED_INTO', 'SPLIT_FROM', 'DISTINCT_FROM'):
        valid('IdentityTransition', transition(kind=k, to='wn_00002', occurred=POINT_2008))


# ---------------------------------------------------------------- reconciliations (cases 16-19)

@check
def c16_each_disposition():
    valid('Reconciliation', rec(selected='ob_a', dispositions={'ob_a': {'disposition': 'SELECTED'},
                                                              'ob_b': {'disposition': 'CONSISTENT'}}))
    valid('Reconciliation', rec(selected='ob_a', dispositions={'ob_a': {'disposition': 'SELECTED'},
                                                              'ob_b': {'disposition': 'CONTRADICTS'}}))
    valid('Reconciliation', rec(selected='ob_a', dispositions={'ob_a': {'disposition': 'SELECTED'},
                                                              'ob_b': {'disposition': 'REJECTED',
                                                                       'reason': 'the later revision says 2008'}}))
    valid('Reconciliation', rec(status='CONFLICT_OPEN', dispositions={'ob_a': {'disposition': 'CONTRADICTS'},
                                                                      'ob_b': {'disposition': 'NOT_ASSESSED'}}))
    invalid('Reconciliation', rec(dispositions={'ob_a': {'disposition': 'WINNER'}}), 'disposition')
    invalid('Reconciliation', rec(selected='ob_a', dispositions={'ob_a': {'disposition': 'SELECTED'},
                                                                'ob_b': {'disposition': 'SELECTED'}}), 'differ')
    invalid('Reconciliation', rec(selected='ob_a', status='CONFLICT_OPEN'), 'a selection while CONFLICT_OPEN')
    invalid('Reconciliation', rec(selected='ob_b', rule='MOST_RECENT_DOCUMENT'), 'before D5')
    invalid('Reconciliation', rec(selected='ob_b', rule='SOURCE_PRIORITY', field='occurred'), 'before D5')


@check
def c17_rejected_without_reason_fails():
    invalid('Reconciliation', rec(dispositions={'ob_b': {'disposition': 'REJECTED'}}), 'REJECTED without a reason')


@check
def c18_disposition_for_a_non_candidate_fails():
    invalid('Reconciliation', rec(dispositions={'ob_z': {'disposition': 'CONSISTENT'}}), 'non-candidates')


@check
def c19_one_observation_different_dispositions_in_different_reconciliations():
    # The disposition belongs to the candidate within one reconciliation, not to the observation.
    valid('Reconciliation', rec(id='rc_one', subject='nm_x', field='valid_from', selected='ob_a',
                                dispositions={'ob_a': {'disposition': 'SELECTED'}}))
    valid('Reconciliation', rec(id='rc_two', subject='it_x', field='occurred', status='CONFLICT_OPEN',
                                dispositions={'ob_a': {'disposition': 'CONTRADICTS'}}))
    assert 'dispositions' not in S.ENTITIES['Observation']['fields'], 'a disposition stored on the observation'


# ---------------------------------------------------------------- the model itself (case 20 and more)

def all_rows():
    for rel, (entity, _, _) in sorted(S.LAYOUT.items()):
        if rel.endswith('.jsonl') and entity in S.ENTITIES:
            for row in L.read_table(rel):
                yield rel, entity, row


@check
def c20_every_legacy_row_valid_with_historical_fields_absent():
    n, bad = 0, []
    for rel, entity, row in all_rows():
        n += 1
        errs = S.check_row(entity, row)
        if errs:
            bad.append((rel, row.get('id'), errs[:1]))
    # 333022 rows at M1; M2 adds one ArtifactDate and one DOCUMENT provenance per accepted date
    m2 = 2 * len(L.read_table('document/artifact-dates.jsonl'))
    # M3.2 adds: A one DOCUMENT provenance per recovered figure; B per recovered address a placement,
    # its locator and its provenance (it changes other rows, adds no others)
    import historical_m2_scope
    prov = L.read_table('cross/provenance.jsonl')
    m32 = sum(1 for p in prov if p.get('actor') == historical_m2_scope.M32_ACTOR)
    m32 += 2 * sum(1 for p in prov if (p.get('code_state') or {}).get('stream') == 'M3.2B')
    # D: the recovered values, their observations and their reconciliations
    m32 += sum(1 for o in L.read_table('observation/observations.jsonl') if historical_m2_scope.is_m32d_observation(o))
    m32 += 2 * sum(1 for r in L.read_table('reconciliation/reconciliations.jsonl') if historical_m2_scope.is_m32d_reconciliation(r))
    # M3.4B adds one Attribution and its DOCUMENT provenance per applied mapping
    m34b = 2 * len(historical_m2_scope.m34b_applied())
    # M3.5 likewise, one Attribution and its provenance per eligible review row
    m34b += 2 * len(historical_m2_scope.m35_applied())
    # M3.6B likewise, one Attribution and its provenance per applied web-page mapping
    m34b += 2 * len(historical_m2_scope.m36b_applied())
    # M3.10B likewise, one Attribution and its provenance per accepted external document
    m34b += 2 * len(historical_m2_scope.m310b_applied())
    # M3.6D: one wine, its names, identity keys, relationship, descriptor and their provenance
    m36d = sum(len(historical_m2_scope.m36d_rows(r)) for r in historical_m2_scope.CUVEE_FILES + ('cross/provenance.jsonl',)
               if r.endswith('.jsonl'))
    # M3.10A: per registered document an artifact, its sha256 key, a placement, its locator and its provenance
    p = {x['id']: x for x in prov}
    m310a = sum(1 for r in historical_m2_scope.M310A_FILES if r.endswith('.jsonl')
                for x in L.read_table(r) if historical_m2_scope.is_m310a_row(r, x, p))
    assert n == 333022 + m2 + m32 + m34b + m36d + m310a and not bad, (n, m2, m32, m34b, m36d, m310a, bad[:3])


@check
def nothing_populated():
    fields = {'claimed_validity', 'claimed_window', 'statement_mode', 'occurred', 'dispositions'}
    found = [(rel, row.get('id')) for rel, _, row in all_rows() if fields & set(row)]
    assert not found, found[:3]
    assert not L.read_table('identity/transitions.jsonl'), 'an identity transition was written'
    # M2 writes document dates (STATED_IN_TEXT only); M1 itself wrote none, and nothing else dates a document
    assert all(r['kind'] == 'STATED_IN_TEXT' for r in L.read_table('document/artifact-dates.jsonl')), 'a document date not from M2'
    import historical_m2_scope
    m36d = historical_m2_scope.m36d_rows('identity/names.jsonl')
    assert not [n for n in L.read_table('identity/names.jsonl') if n['kind'] != 'CURRENT' and n not in m36d], 'a former name'
    # M3.6D's two variants of its wine's name: neither former nor dated
    assert all(n['kind'] in ('CURRENT', 'SOURCE_RENDERING', 'MARKET_ALIAS') and n['validity'] == {'valid_from': {'kind': 'UNKNOWN'}, 'valid_to': {'kind': 'OPEN'}}
               for n in m36d), 'a former or dated M3.6D name'


@check
def the_extension_makes_no_current_fact_historical():
    # Every state record and name is still "current, start unknown": the new structures
    # exist, and none of them dates or ends anything.
    rels = ('identity/names.jsonl', 'state/estate-wine.jsonl', 'state/rank-assertions.jsonl',
            'state/rank-absences.jsonl', 'state/classification-memberships.jsonl',
            'state/appellation-memberships.jsonl', 'state/estate-locations.jsonl', 'state/source-estate.jsonl')
    n = 0
    for rel in rels:
        for r in L.read_table(rel):
            n += 1
            assert r['validity']['valid_from'] == {'kind': 'UNKNOWN'} and r['validity']['valid_to'] == {'kind': 'OPEN'}, (rel, r['id'])
    import historical_m2_scope                    # M3.6D's names and relationship, as current as the rest
    assert n == 3917 + sum(len(historical_m2_scope.m36d_rows(rel)) for rel in rels
                           if rel in historical_m2_scope.CUVEE_FILES), n


@check
def model_generated_data_and_protected_groups_unchanged():
    import historical_m2_scope                    # M3.2: figure-sources.js by exactly the recovered figures
    assert not historical_m2_scope.app_files_changed_beyond_m32(
        git('diff', '--name-only', BEFORE, '--', 'data/app').split()), 'generated data changed'
    import historical_m2_scope                    # M2's document dates: three files, additions only
    historical_m2_scope.model_changes_are_m2_only(BEFORE)
    b0 = json.load(open(L.MODEL + 'baseline.json', encoding='utf-8'))['groups']
    for g in b0:
        # M3.6B's evidence version 6 named and set aside; v1-v5 and every other group byte for byte
        assert __import__('historical_m2_scope').protected_group(g)['digest'] == b0[g]['digest'], g
    # the reconciliations' candidate lists are exactly as they were
    old = [json.loads(l) for l in git('show', BEFORE + ':data/model/reconciliation/reconciliations.jsonl').splitlines() if l.strip()]
    # M3.2D adds its own reconciliations (named); every one there before keeps its candidates
    # ... and M3.6F its Cuvée Mongravey ones (named)
    now = [r for r in L.read_table('reconciliation/reconciliations.jsonl')
           if not historical_m2_scope.is_m32d_reconciliation(r) and not historical_m2_scope.is_m36f_reconciliation(r)]
    assert [r['candidates'] for r in old] == [r['candidates'] for r in now] and len(now) == 12959


@check
def the_phase34_contract_is_untouched_and_extended_by_merge():
    assert not git('diff', '--stat', BEFORE, '--', 'docs/phase34-model.json', 'docs/phase34-fixtures.json').strip()
    base = json.load(open(L.ROOT + 'docs/phase34-model.json', encoding='utf-8'))
    assert 'RELATED_UNSPECIFIED' not in base['enums']['TransitionKind']['values']
    assert 'RELATED_UNSPECIFIED' in S.ENUMS['TransitionKind'] and S.ENUMS['StatementMode'] == {'EXPLICIT', 'IMPLIED'}
    assert S.ENUMS['CandidateDisposition'] == {'SELECTED', 'CONSISTENT', 'CONTRADICTS', 'REJECTED', 'NOT_ASSESSED'}
    assert S.ENTITIES['IdentityTransition']['fields']['at']['required'] is False
    for ent, f in (('Observation', 'claimed_validity'), ('Observation', 'claimed_window'),
                   ('Observation', 'statement_mode'), ('IdentityTransition', 'occurred'),
                   ('Reconciliation', 'dispositions')):
        assert S.ENTITIES[ent]['fields'][f]['required'] is False, (ent, f)
    # the evaluator is not part of M1
    assert 'EvaluationStatus' not in S.ENUMS and 'Holds' not in S.ENUMS
    assert not hasattr(S, 'state_at') and not hasattr(S, 'evaluate')


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
