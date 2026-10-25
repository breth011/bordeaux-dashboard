"""Historical model M3: explicit, already-reviewed historical claims only.

    python tools/test-historical-m3.py

Read-only. M3's candidate audit (tools/extract-historical-m3.py ->
data/audit/historical-m3-candidates.jsonl) applies the eight-gate eligibility rule
(tools/historical_m3.py) to every historical statement earlier research exposed and to the
model's own history-like rows. None is eligible, so the model is unchanged. These checks hold the
gate to its rules on candidates built here, prove that an accepted fact would be representable
in the M1 schema and read correctly by the evaluator (tools/historical_evaluator.py) - on rows
built in memory, never in data/model/ - and hold the real audit and model to what M3 found.
"""
import builtins
import datetime
import hashlib
import json
import os
import random
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import historical_evaluator as E  # noqa: E402
import historical_m3 as H  # noqa: E402
import migration_lib as L  # noqa: E402
import model_schema as S  # noqa: E402

BEFORE = '253e16f'               # M2: the model before M3
AUDIT = L.ROOT + 'data/audit/historical-m3-candidates.jsonl'
CHECKS = []


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode()


def audit():
    return {r['key']: r for r in (json.loads(l) for l in open(AUDIT, encoding='utf-8'))}


# -- facts built here ------------------------------------------------------------------------------

GOOD = {'artifact_present': True, 'passage_found': True, 'provenance_kind': 'DOCUMENT', 'evidence': 'ACCEPTED',
        'statement_mode': 'EXPLICIT', 'subject_status': 'RESOLVED', 'temporal': 'STATED', 'value': 'x'}


def facts(**kw):
    f = dict(GOOD)
    f.update(kw)
    return f


V = lambda y: S.bound('EXACT', y, 'VINTAGE', 'VINTAGE', 'q')
Y = lambda y: S.bound('EXACT', y, 'CALENDAR', 'YEAR', 'q')
T = lambda axis, v: {'axis': axis, 'value': v}


def claim(subject, field, value, validity, artifact='ar_900001', locus='p:1'):
    return {'artifact': artifact, 'quote': 'quoted words', 'locus': locus, 'lang': 'fr', 'subject': subject,
            'field': field, 'value': value, 'claimed_validity': validity}


def build(*facts_rows):
    """Merge rows_for() outputs into one table set, validate every row, return Tables."""
    rows = {}
    for fr in facts_rows:
        for rel, rs in fr.items():
            rows.setdefault(rel, []).extend(rs)
    prov = {p['id']: p for p in rows.get('cross/provenance.jsonl', [])}
    for rel, rs in rows.items():
        entity = S.LAYOUT[rel][0]
        for r in rs:
            errs = S.check_row(entity, r, provenance=prov)
            assert not errs, (rel, r.get('id'), errs)
    return E.Tables(rows), rows


def not_made(wine, year, n=1):
    v = {'valid_from': V(year), 'valid_to': V(year)}
    return H.rows_for([claim('vt:%s:%d' % (wine, year), 'vintage.not_produced', True, v, artifact='ar_90000%d' % i)
                       for i in range(n)],
                      {'entity': 'VintageStatement', 'vintage': 'vt:%s:%d' % (wine, year), 'kind': 'NOT_PRODUCED'},
                      '2026-10-25')


def name(wine, nm, kind, validity, decision=None, claims=1, values=None):
    vals = values or [nm] * claims
    return H.rows_for([claim(wine, 'name', v, validity, artifact='ar_91000%d' % i) for i, v in enumerate(vals)],
                      {'entity': 'NameRecord', 'subject': wine, 'name': nm, 'kind': kind, 'validity': validity},
                      '2026-10-25', decision=decision)


# -- the 22 cases of the brief ---------------------------------------------------------------------

@check
def c01_explicit_historical_claim_accepted():
    g = H.gate(facts())
    assert (g['category'], g['rule'], g['status']) == (H.ACCEPTED, 'ONLY_CANDIDATE', 'SINGLE'), g
    m, rows = build(name('wn_09001', 'Ancien Nom', 'FORMER', {'valid_from': V(1990), 'valid_to': V(2007)}))
    r = rows['reconciliation/reconciliations.jsonl'][0]
    assert r['rule'] == 'ONLY_CANDIDATE' and r['status'] == 'SINGLE' and r['selected'] == r['candidates'][0]
    o = rows['observation/observations.jsonl'][0]
    assert o['statement_mode'] == 'EXPLICIT' and o['claimed_validity']['valid_from']['value'] == 1990
    assert E.evaluate(m, 'wn_09001', 'name', T('VINTAGE', 2000))['status'] == E.ESTABLISHED


@check
def c02_implied_claim_rejected():
    assert H.gate(facts(statement_mode='IMPLIED'))['category'] == 'EXCLUDED_IMPLIED'
    assert H.gate(facts(temporal='FRAMING'))['category'] == 'EXCLUDED_IMPLIED'
    a = audit()
    assert 'E6_temporal' in a['laparde-rename-2018']['failed']        # "2018" is the sheet's own heading
    assert 'E4_explicit' in a['terrasses-second-2016-2019']['failed']  # the period is the sheets on file


@check
def c03_unsupported_claim_rejected():
    assert H.gate(facts(artifact_present=False))['category'] == 'REJECTED_NO_PROVENANCE'
    assert H.gate(facts(passage_found=False))['category'] == 'REJECTED_NO_PROVENANCE'
    assert H.gate(facts(provenance_kind='LEGACY_UNSOURCED'))['category'] == 'REJECTED_NO_PROVENANCE'
    assert H.gate(facts(evidence='NOT_REVIEWED'))['category'] == 'REJECTED_NOT_REVIEWED'
    legacy = [r for k, r in audit().items() if k.startswith(('legacy-owner', 'legacy-history'))]
    assert legacy and all(r['category'] == 'REJECTED_NO_PROVENANCE' for r in legacy)


@check
def c04_current_fact_not_converted_into_history():
    m = E.Tables.load()
    for subject in ('wn_00547', 'wn_00522', 'es_00398'):
        for p, r in E.state_at(m, subject, T('VINTAGE', 1995)).items():
            assert r['status'] == E.UNDETERMINED, (subject, p, r)
    a = audit()
    assert a['corbin-no-second-2025-en']['category'] == 'EXCLUDED_CURRENT_STATEMENT'
    dataset = [r for k, r in a.items() if k.startswith('dataset-no-')]
    assert len(dataset) == 34 and all(r['category'] == 'EXCLUDED_CURRENT_STATEMENT' for r in dataset)


@check
def c05_document_date_does_not_become_event_date():
    a = audit()
    dated = [r for r in a.values() if r.get('document_date')]
    assert dated, 'expected a candidate on a dated document (Pontoise Cabarrus, M2 2023-01-02)'
    for r in dated:
        for v in (r.get('claimed') or {}).values():
            for bound in v.values():
                assert str(bound.get('value', ''))[:4] != r['document_date'][:4], (r['key'], bound)
    assert H.gate(facts(temporal='FRAMING'))['category'] != H.ACCEPTED


@check
def c06_missing_sheet_does_not_become_not_made():
    m = E.Tables.load()
    r = E.evaluate(m, 'wn_00386', 'produced', T('VINTAGE', 1950))     # Corbin 1950: no sheet, no statement
    assert r['status'] == E.UNDETERMINED and not r['records'], r
    assert audit()['batailley-no-second-before-2014']['category'] == 'EXCLUDED_ABSENCE'


@check
def c07_explicit_not_made_claim_accepted():
    m, rows = build(not_made('wn_09002', 1991))
    assert rows['state/vintage-statements.jsonl'][0]['kind'] == 'NOT_PRODUCED'
    assert E.evaluate(m, 'wn_09002', 'produced', T('VINTAGE', 1991))['status'] == E.NOT_ESTABLISHED
    for y in (1990, 1992):                                             # scoped to its vintage (S26, H19)
        assert E.evaluate(m, 'wn_09002', 'produced', T('VINTAGE', y))['status'] == E.UNDETERMINED


@check
def c08_vintage_axis_claim_remains_vintage_axis():
    v = {'valid_from': V(2008), 'valid_to': S.bound('OPEN')}
    m, rows = build(name('wn_09003', 'Nouveau Nom', 'CURRENT', v))
    assert rows['identity/names.jsonl'][0]['validity']['valid_from']['axis'] == 'VINTAGE'
    assert E.evaluate(m, 'wn_09003', 'name', T('VINTAGE', 2010))['status'] == E.ESTABLISHED
    assert E.evaluate(m, 'wn_09003', 'name', T('CALENDAR', '2010'))['status'] == E.UNDETERMINED


@check
def c09_calendar_axis_claim_remains_calendar_axis():
    v = {'valid_from': Y('1881'), 'valid_to': Y('1959')}
    rows = H.rows_for([claim('es_09004', 'owner', 'pt_09004', v)],
                      {'entity': 'Ownership', 'estate': 'es_09004', 'party': 'pt_09004', 'role': 'OWNER', 'validity': v},
                      '2026-10-25')
    m, rows = build(rows)
    assert rows['state/ownership.jsonl'][0]['validity']['valid_to']['axis'] == 'CALENDAR'
    assert E.evaluate(m, 'es_09004', 'owner', T('CALENDAR', '1900'))['status'] == E.ESTABLISHED
    assert E.evaluate(m, 'es_09004', 'owner', T('CALENDAR', '1960'), value='pt_09004')['status'] == E.NOT_ESTABLISHED
    assert E.evaluate(m, 'es_09004', 'owner', T('VINTAGE', 1900))['status'] == E.UNDETERMINED


@check
def c10_unknown_event_date_remains_unknown():
    v = {'valid_from': S.bound('UNKNOWN'), 'valid_to': V(2007)}
    m, rows = build(name('wn_09005', 'Ancien', 'FORMER', v))
    assert rows['identity/names.jsonl'][0]['validity']['valid_from'] == {'kind': 'UNKNOWN'}
    assert E.holds(v, T('VINTAGE', 1990)) == E.UNDET
    assert E.evaluate(m, 'wn_09005', 'name', T('VINTAGE', 1990))['status'] == E.UNDETERMINED
    assert E.evaluate(m, 'wn_09005', 'name', T('VINTAGE', 2009), value='Ancien')['status'] == E.NOT_ESTABLISHED


@check
def c11_open_ended_period_remains_open():
    v = {'valid_from': V(2004), 'valid_to': S.bound('OPEN')}
    m, rows = build(name('wn_09006', 'Depuis 2004', 'CURRENT', v))
    assert rows['identity/names.jsonl'][0]['validity']['valid_to'] == {'kind': 'OPEN'}
    assert E.evaluate(m, 'wn_09006', 'name', T('VINTAGE', 2030))['status'] == E.ESTABLISHED
    assert E.evaluate(m, 'wn_09006', 'name', T('VINTAGE', 2003), value='Depuis 2004')['status'] == E.NOT_ESTABLISHED


@check
def c12_ambiguous_identity_remains_unresolved():
    a = audit()
    for k in ('laparde-rename-2018', 'laparde-born-1967'):
        assert a[k]['category'] == 'BLOCKED_IDENTITY_DECISION' and a[k]['subject_status'] == 'AMBIGUOUS', a[k]
    idm = [r for r in L.read_table('identity/identity-map.jsonl') if r['legacy_key'] == 'haut-bailly|La Parde de Haut-Bailly']
    assert idm and all(r['status'] == 'AMBIGUOUS' for r in idm)
    m = E.Tables({'identity/transitions.jsonl': [
        {'id': 'it_x', 'kind': 'RELATED_UNSPECIFIED', 'from': 'wn_1', 'to': 'wn_2', 'certainty': 'UNRESOLVED',
         'provenance': 'pv_x', 'occurred': {'earliest': V(2018), 'latest': V(2018)}}]})
    c = E.changes(m, 'wn_1', T('VINTAGE', 2017), T('VINTAGE', 2018))
    assert not c['changes'] and c['unresolved'] == [{'transition': 'it_x', 'kind': 'RELATED_UNSPECIFIED'}]


@check
def c13_echo_d2_remains_unresolved():
    a = audit()
    echo = [r for k, r in a.items() if k.startswith(('echo-', 'averous-'))]
    assert len(echo) == 5 and all(r['category'] == 'BLOCKED_D2' and 'E7_decisions' in r['failed'] for r in echo)
    assert not L.read_table('identity/transitions.jsonl')
    assert [n['kind'] for n in L.read_table('identity/names.jsonl') if n['subject'] == 'wn_00547'] == ['CURRENT']
    assert E.evaluate(E.Tables.load(), 'wn_00547', 'name', T('VINTAGE', 2007))['status'] == E.UNDETERMINED


@check
def c14_conflicting_claims_remain_contested():
    g = H.gate(facts(value='A'), eligible_peers=[{'key': 'other', 'value': 'B'}])
    assert g['category'] == 'CONFLICT_OPEN' and not g.get('rule'), g
    v = {'valid_from': V(1990), 'valid_to': V(2007)}
    m, rows = build(name('wn_09007', 'Nom A', 'FORMER', v, values=['Nom A', 'Nom B']))
    r = rows['reconciliation/reconciliations.jsonl'][0]
    assert r['status'] == 'CONFLICT_OPEN' and 'selected' not in r
    assert E.evaluate(m, 'wn_09007', 'name', T('VINTAGE', 2000))['status'] == E.CONTESTED


@check
def c15_unanimous_claims_establish_a_fact():
    g = H.gate(facts(value='A'), eligible_peers=[{'key': 'fr', 'value': 'A'}])
    assert (g['category'], g['rule'], g['status']) == (H.ACCEPTED, 'UNANIMOUS', 'AGREED'), g
    m, rows = build(not_made('wn_09008', 1992, n=2))
    r = rows['reconciliation/reconciliations.jsonl'][0]
    assert r['rule'] == 'UNANIMOUS' and r['status'] == 'AGREED' and len(r['candidates']) == 2
    assert sorted(d['disposition'] for d in r['dispositions'].values()) == ['CONSISTENT', 'SELECTED']
    assert E.evaluate(m, 'wn_09008', 'produced', T('VINTAGE', 1992))['status'] == E.NOT_ESTABLISHED


@check
def c16_existing_manual_decision_establishes_a_fact():
    g = H.gate(facts(manual_decision={'resolver': 'a reviewer'}))
    assert (g['category'], g['rule'], g['status']) == (H.ACCEPTED, 'MANUAL_DECISION', 'RESOLVED'), g
    v = {'valid_from': V(1967), 'valid_to': V(2017)}
    m, rows = build(name('wn_09009', 'Ancien', 'FORMER', v, decision={'resolver': 'a reviewer', 'reason': 'recorded decision'}))
    assert rows['reconciliation/reconciliations.jsonl'][0]['rule'] == 'MANUAL_DECISION'
    assert E.evaluate(m, 'wn_09009', 'name', T('VINTAGE', 2000))['status'] == E.ESTABLISHED


@check
def c17_rejected_evidence_cannot_create_history():
    assert H.gate(facts(evidence='REFUSED'))['category'] == 'REJECTED_EVIDENCE_REFUSED'
    r = audit()['corbin-2022-no-second']
    assert r['category'] == 'REJECTED_EVIDENCE_REFUSED' and r['evidence']['verdict'] == 'REFUSED'
    assert any(d[1] == 'PRESS_DOCUMENT' for d in r['evidence']['decisions']), r['evidence']


@check
def c18_provenance_is_mandatory():
    # a record whose basis reaches no reconciliation decides nothing
    v = {'valid_from': S.bound('EXACT', 1990, 'VINTAGE', 'VINTAGE', 'pv_bare'), 'valid_to': S.bound('OPEN')}
    m = E.Tables({'identity/names.jsonl': [{'id': 'nm_x', 'subject': 'wn_1', 'name': 'N', 'kind': 'CURRENT',
                                            'validity': v, 'provenance': 'pv_bare'}],
                  'cross/provenance.jsonl': [{'id': 'pv_bare', 'kind': 'MANUAL', 'actor': 'test'}]})
    r = E.evaluate(m, 'wn_1', 'name', T('VINTAGE', 2000))
    assert r['status'] == E.UNDETERMINED and r['unreconciled'] == ['nm_x'], r
    # a dated bound without a basis is invalid in the schema
    bad = {'kind': 'EXACT', 'value': 1990, 'axis': 'VINTAGE', 'precision': 'VINTAGE'}
    assert S.check_row('NameRecord', {'id': 'nm_y', 'subject': 'wn_1', 'name': 'N', 'kind': 'FORMER',
                                      'validity': {'valid_from': bad, 'valid_to': S.bound('OPEN')}, 'provenance': 'pv_x'})


@check
def c19_evaluator_is_deterministic():
    _, rows = build(name('wn_09010', 'A', 'FORMER', {'valid_from': V(1990), 'valid_to': V(2007)}),
                    name('wn_09010', 'B', 'CURRENT', {'valid_from': V(2008), 'valid_to': S.bound('OPEN')}),
                    not_made('wn_09010', 1991))
    outs = set()
    for seed in range(4):
        shuffled = {rel: random.Random(seed).sample(rs, len(rs)) for rel, rs in rows.items()}
        m = E.Tables(shuffled)
        outs.add(E.dumps([E.state_at(m, 'wn_09010', T('VINTAGE', y)) for y in (1991, 2007, 2008)]
                         + [E.changes(m, 'wn_09010', T('VINTAGE', 2007), T('VINTAGE', 2008))]))
    assert len(outs) == 1


@check
def c20_evaluator_does_not_use_current_time():
    _, rows = build(name('wn_09011', 'A', 'CURRENT', {'valid_from': V(2008), 'valid_to': S.bound('OPEN')}))
    saved = (time.time, time.localtime, datetime.datetime, datetime.date)

    def refuse(*a, **k):
        raise AssertionError('the evaluator read the clock')

    class NoClock(datetime.datetime):
        now = utcnow = today = classmethod(refuse)

    class NoDay(datetime.date):
        today = classmethod(refuse)
    try:
        time.time, time.localtime, datetime.datetime, datetime.date = refuse, refuse, NoClock, NoDay
        m = E.Tables(rows)
        r = E.evaluate(m, 'wn_09011', 'name', T('VINTAGE', 2009))
        E.changes(m, 'wn_09011', T('VINTAGE', 2007), T('VINTAGE', 2009))
    finally:
        time.time, time.localtime, datetime.datetime, datetime.date = saved
    assert r['status'] == E.ESTABLISHED


@check
def c21_snapshots_are_not_stored():
    before = {f: hashlib.sha256(open(f, 'rb').read()).hexdigest()
              for f in sorted(os.path.join(dp, n) for dp, _, ns in os.walk(L.MODEL) for n in ns)}
    m = E.Tables.load()
    opened = []
    real_open = builtins.open

    def watch(f, mode='r', *a, **k):
        if any(c in mode for c in 'wax+'):
            opened.append(f)
        return real_open(f, mode, *a, **k)
    builtins.open = watch
    try:
        for s in ('wn_00547', 'wn_00522', 'wn_00458', 'es_00181'):
            E.state_at(m, s, T('VINTAGE', 2008))
            E.changes(m, s, T('VINTAGE', 2007), T('VINTAGE', 2008))
    finally:
        builtins.open = real_open
    after = {f: hashlib.sha256(open(f, 'rb').read()).hexdigest() for f in before}
    assert not opened and before == after
    assert not [rel for rel in S.LAYOUT if 'snapshot' in rel or 'timeline' in rel or 'event' in rel]


@check
def c22_current_state_data_remains_unchanged():
    assert not git('diff', '--stat', BEFORE, '--', 'data/model', 'data/app', 'data/evidence', 'data/history',
                   'assets', 'index.html').strip(), 'model, app, evidence or audit data changed'
    b0 = json.load(open(L.MODEL + 'baseline.json', encoding='utf-8'))['groups']
    for g in b0:
        assert L.group_hashes(g)['digest'] == b0[g]['digest'], g


# -- found in the audit ----------------------------------------------------------------------------

@check
def derived_timeline_answers_both_questions():
    # "What was established about wine X in year Y?" and "What changed between A and B?"
    m, _ = build(name('wn_09012', 'La Parde', 'FORMER', {'valid_from': S.bound('UNKNOWN'), 'valid_to': V(2017)}),
                 name('wn_09012', 'II', 'CURRENT', {'valid_from': V(2018), 'valid_to': S.bound('OPEN')}),
                 not_made('wn_09012', 2017))
    y17 = E.state_at(m, 'wn_09012', T('VINTAGE', 2017))
    assert y17['name']['status'] == E.UNDETERMINED                     # La Parde's start is UNKNOWN
    assert E.evaluate(m, 'wn_09012', 'name', T('VINTAGE', 2017), value='II')['status'] == E.NOT_ESTABLISHED
    assert y17['produced']['status'] == E.NOT_ESTABLISHED
    y18 = E.state_at(m, 'wn_09012', T('VINTAGE', 2018))
    assert y18['name']['status'] == E.ESTABLISHED and y18['name']['values'] == ['II']
    c = E.changes(m, 'wn_09012', T('VINTAGE', 2017), T('VINTAGE', 2018))
    assert [(x['value'], x['before'], x['after']) for x in c['changes']] == [('II', E.NOT_ESTABLISHED, E.ESTABLISHED)]
    assert any(x['value'] == 'La Parde' for x in c['not_established'])  # its end is a boundary, its start unknown


@check
def legacy_not_made_statements_decide_nothing_historically():
    m = E.Tables.load()
    vs = L.read_table('state/vintage-statements.jsonl')
    assert len(vs) == 18
    for v in vs:
        wine, year = v['vintage'].split(':')[1], int(v['vintage'].split(':')[2])
        r = E.evaluate(m, wine, 'produced', T('VINTAGE', year))
        assert r['status'] == E.UNDETERMINED and r['unreconciled'] == [v['id']], r
    a = [r for k, r in audit().items() if k.startswith('legacy-not-made:')]
    assert len(a) == 18 and all(r['category'] == 'REJECTED_NO_PROVENANCE' for r in a)


@check
def the_audit_is_complete_and_nothing_is_eligible():
    a = audit()
    assert len(a) == 97 and len({r['id'] for r in a.values()}) == 97
    for r in a.values():
        assert r['category'] in H.CATEGORIES and r['failed'] and set(r['gates']) == set(H.GATES), r['key']
    assert not [k for k, r in a.items() if r['category'] == H.ACCEPTED]
    research = [r for r in a.values() if r['kind'] == 'RESEARCH']
    assert len(research) == 17
    unfound = sorted(r['key'] for r in research if not r['passage_found'])
    assert unfound == ['batailley-no-second-before-2014', 'echo-rename-mobi'], unfound
    for r in research:
        if r['passage_found']:
            assert r['artifact'] and r['quote'] and len(r['quote']) <= 200, r['key']


@check
def the_audit_is_reproducible():
    out = subprocess.run([sys.executable, L.ROOT + 'tools/extract-historical-m3.py', '--check'],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr


@check
def no_event_entity_and_no_new_concept():
    assert 'Event' not in S.ENTITIES and 'HistoricalEvent' not in S.ENTITIES
    assert not git('diff', '--stat', BEFORE, '--', 'docs/phase34-model.json', 'docs/schema').strip()


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
