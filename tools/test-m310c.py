"""Phase M3.10C: Château Durfort-Vivens' nine values from the four documents M3.10B accepted
(tools/m310c-values.py; the migration's m310c_values).

    python tools/test-m310c.py

Read-only. A closed world: exactly the nine (vintage, field) values, no tenth, each from its accepted
document's own statement with field-level provenance; the 2014 English and French sheets one fact per field
(one reconciliation, UNANIMOUS, one canonical value; an observation per sheet, as M3.6F's and M3.2D's); the
2024 new oak 70, never 30. Evidence (v1-v9), attributions, identities, other vintages, other fields, the
earlier audits and the app are as M3.10B left them: the app projects the legacy files' records, and none
holds these nine.
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

BEFORE = '128263f'               # M3.10B and its gap-register record: the state M3.10C applies to
MANIFEST = L.ROOT + H.M310C_MANIFEST
WINE = 'wn_00263'
EXPECT = {
    ('vt:wn_00263:2014', 'blend'): {'CS': 90, 'ME': 10}, ('vt:wn_00263:2014', 'oak'): 50,
    ('vt:wn_00263:2014', 'months'): '18', ('vt:wn_00263:2021', 'alc'): 13.5,
    ('vt:wn_00263:2024', 'blend'): {'CS': 94.5, 'ME': 5, 'CF': 0.5}, ('vt:wn_00263:2024', 'pick'): {'ALL': '09-23|10-08'},
    ('vt:wn_00263:2024', 'yld'): 37, ('vt:wn_00263:2024', 'oak'): 70, ('vt:wn_00263:2024', 'months'): '18',
}
ARTIFACTS = {'ar_037069', 'ar_037068', 'ar_037070', 'ar_037071'}
READER = ('tools/m35_rubric.py', 'tools/web_evidence.py', 'tools/sheetreader.py', 'tools/read-fiches.py',
          'tools/m34a-mapping-audit.py', 'tools/model_schema.py', 'tools/evidence.py')
CHECKS = []


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode('utf-8')


def added(rel):
    old = set(git('show', '%s:data/model/%s' % (BEFORE, rel)).splitlines())
    return [json.loads(x) for x in open(L.MODEL + rel, encoding='utf-8').read().splitlines() if x not in old]


@check
def t01_exactly_the_nine_values_no_tenth():
    vals = added('canonical/values.jsonl')
    assert {(v['subject'], v['field']): v['value'] for v in vals} == EXPECT and len(vals) == 9
    assert all(v['status'] == 'SOURCED' for v in vals)
    assert {(r['vintage'], r['field']): r['value'] for r in L.jsonl_lines(MANIFEST) if r['record'] == 'value'} == EXPECT


@check
def t02_per_vintage_fields():
    by = {}
    for (vt, f) in EXPECT:
        by.setdefault(vt[-4:], set()).add(f)
    got = {}
    for v in added('canonical/values.jsonl'):
        got.setdefault(v['subject'][-4:], set()).add(v['field'])
    assert got == by == {'2014': {'blend', 'oak', 'months'}, '2021': {'alc'}, '2024': {'blend', 'pick', 'yld', 'oak', 'months'}}


@check
def t03_the_2014_pair_is_one_fact_per_field():
    obs = added('observation/observations.jsonl')
    rec = {(r['subject'], r['field']): r for r in added('reconciliation/reconciliations.jsonl')}
    vals = {(v['subject'], v['field']): v for v in added('canonical/values.jsonl')}
    for f in ('blend', 'oak', 'months'):
        k = ('vt:wn_00263:2014', f)
        os_ = [o for o in obs if (o['subject'], o['field']) == k]
        assert sorted(o['artifact'] for o in os_) == ['ar_037068', 'ar_037069'], (f, os_)
        assert len({json.dumps(o['value'], sort_keys=True) for o in os_}) == 1, ('the sheets disagree', f)
        r = rec[k]
        assert (r['rule'], r['status']) == ('UNANIMOUS', 'AGREED') and sorted(r['candidates']) == sorted(o['id'] for o in os_)
        assert vals[k]['reconciliation'] == r['id']
    assert len([v for v in vals if v[0] == 'vt:wn_00263:2014']) == 3, 'one canonical value per 2014 field'
    for k in EXPECT:
        if not k[0].endswith('2014'):
            assert rec[k]['rule'] == 'ONLY_CANDIDATE' and len(rec[k]['candidates']) == 1, k
    assert len(obs) == 12 and len(rec) == 9


@check
def t04_the_2024_oak_is_70_never_30():
    vals = {(v['subject'], v['field']): v['value'] for v in L.read_table('canonical/values.jsonl')}
    assert vals[('vt:wn_00263:2024', 'oak')] == 70
    assert not [o for o in added('observation/observations.jsonl') if o['field'] == 'oak' and o['value'] == 30]
    assert not [v for v in added('canonical/values.jsonl') if v['value'] == 30]
    [w] = [r for r in L.jsonl_lines(MANIFEST) if r['record'] == 'withheld' and r['status'] == 'REJECTED_READER_MISREAD']
    assert w['candidate'] == 30 and w['vintage'] == 'vt:wn_00263:2024'


@check
def t05_every_value_has_field_level_provenance():
    prov = {p['id']: p for p in L.read_table('cross/provenance.jsonl')}
    decs = {r['evidence_decision'] for r in L.jsonl_lines(L.ROOT + H.M310B_MANIFEST) if r['record'] == 'decision'}
    for v in added('canonical/values.jsonl'):
        p = prov[v['provenance']]
        assert p['kind'] == 'DOCUMENT' and p['actor'] == H.M310C_ACTOR and p['artifact'] in ARTIFACTS and p['quote']
        cs = p['code_state']
        assert (cs['stream'], cs['vintage'], cs['field']) == ('M3.10C', v['subject'], v['field'])
        assert cs['evidence_decision'] in decs and cs['evidence_version'] == 9 and cs['locus']
    for o in added('observation/observations.jsonl'):
        p = prov[o['provenance']]
        assert p['artifact'] == o['artifact'] and p['quote'] == o['raw_value'] and o['confidence'] == 'EXPLICIT_LABELLED'
    for r in added('reconciliation/reconciliations.jsonl'):
        assert prov[r['provenance']]['kind'] == 'DERIVATION'
    # every quote is the document's own lines
    reg = {r['artifact']: r for r in L.jsonl_lines(L.ROOT + H.M310A_MANIFEST) if r['record'] == 'result'}
    shas = {r['artifact']: g['sha256'] for g in L.jsonl_lines(L.ROOT + H.M310A_MANIFEST) if g['record'] == 'registration'
            for r in reg.values() if r['candidate'] == g['candidate']}
    for o in added('observation/observations.jsonl'):
        x = json.load(open(L.ROOT + 'sources/acquisition/m3.8/extracted/%s.json' % shas[o['artifact']], encoding='utf-8'))
        page, a, b = o['locus'][1:].replace('l', '').split(':')[0], *o['locus'].split(':')[1].replace('l', '').split('-')
        lines = x['pages'][int(page) - 1].splitlines()[int(a) - 1:int(b)]
        assert o['raw_value'] == ' / '.join(l.strip() for l in lines if l.strip()), o['id']


@check
def t06_evidence_attributions_and_identities_unchanged():
    paths = ['data/evidence', 'data/model/document/attributions.jsonl', 'data/model/identity',
             'data/model/state', 'data/model/derived', 'data/model/document']
    assert not git('diff', '--stat', BEFORE, '--', *paths).strip()
    assert ST.versions()[-1] == 9 and ST.verify() == []


@check
def t07_no_unrelated_vintage_or_field_changed():
    changed = {f[len('data/model/'):] for f in git('diff', '--name-only', BEFORE, '--', 'data/model').split()}
    assert changed == set(H.M310C_FILES), sorted(changed)
    for rel in ('canonical/values.jsonl', 'observation/observations.jsonl', 'reconciliation/reconciliations.jsonl'):
        old = set(git('show', '%s:data/model/%s' % (BEFORE, rel)).splitlines())
        new = set(open(L.MODEL + rel, encoding='utf-8').read().splitlines())
        assert old <= new, (rel, 'a row changed or was removed')
    assert {(v['subject'], v['field']) for v in added('canonical/values.jsonl')} == set(EXPECT)
    assert {(o['subject'], o['field']) for o in added('observation/observations.jsonl')} == set(EXPECT)
    H.unchanged_but_m310a('995276d', 'data/model')


@check
def t08_the_app_is_unchanged_and_why():
    # the app projects the legacy files' records (model_reader: observations by legacy file and record), overlaying
    # the canonical value; none of the nine (vintage, field) has such a record, so none is shown and nothing moves
    assert not git('diff', '--stat', BEFORE, '--', 'data/app', ':(glob)data/*.js', 'assets', 'index.html').strip()
    legacy = {(o['subject'], o['field']) for o in L.read_table('observation/observations.jsonl')
              if (o.get('extraction') or {}).get('file', '').startswith('data/')
              and (o.get('extraction') or {}).get('file', '').endswith('.js')}          # the legacy data files
    assert not legacy & set(EXPECT), sorted(legacy & set(EXPECT))


@check
def t09_audits_reader_discovery_and_register_unchanged():
    paths = ('data/audit/m3.8-acquisition-pilot.jsonl', 'data/audit/m3.9-evidence-review.jsonl',
             'data/audit/m3.10a-external-artifact-registration.jsonl', 'data/audit/m3.10b-evidence-decisions.jsonl',
             'data/audit/data-gap-register.jsonl', 'docs/DATA-GAP-REGISTER.md', 'data/discovery', *READER)
    assert not git('diff', '--stat', BEFORE, '--', *paths).strip()
    assert not git('ls-files', '--', 'sources/acquisition').strip()


@check
def t10_the_audit_is_the_application_set():
    rows = L.jsonl_lines(MANIFEST)
    [scope] = [r for r in rows if r['record'] == 'scope']
    assert {(e['vintage'], e['field']) for e in scope['expected']} == set(EXPECT)
    st = {r['status'] for r in rows if r['record'] == 'withheld'}
    assert st == {'REJECTED_READER_MISREAD', 'REJECTED_VINEYARD_SECTION', 'WITHHELD_CLASS_B', 'WITHHELD_NOT_STATED',
                  'WITHHELD_NOT_IN_INPUT'}, st


@check
def t11_the_earlier_guards_set_m310c_aside():
    H.model_changes_are_m2_only('345f892')
    H.unchanged_but_m36d('1a58c92', 'data/model', ':(exclude)data/model/manifest.json')


@check
def t12_deterministic():
    for cmd in (['m310c-values.py', '--check'], ['migrate.py', '--check'], ['build-indexes.py', '--check'],
                ['build-app-data.py', '--check'], ['build-data-gap-register.py', '--check-all']):
        out = CC.run([sys.executable, L.ROOT + 'tools/' + cmd[0]] + cmd[1:], cwd=L.ROOT)
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
