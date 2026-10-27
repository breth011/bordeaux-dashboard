"""Phase M3.11: the value-application runner (tools/apply-value-manifest.py; the migration's value_application).

    python tools/test-value-application-manifest.py

Read-only for the repository: every application runs on an isolated copy of the model at 128263f (the state
before M3.10C), through BDX_MODEL_DIR. The production manifest holds M3.10C's nine values; in production each is
NOOP_EXISTING_IDENTICAL and the model does not move. The golden reference is M3.10C (88f8c8d): the runner applied
to the copy must give its nine values, twelve observations, nine reconciliations and twenty-one provenance rows,
differing only in the runner's own metadata, and a migration rebuild must give the copy byte for byte.
"""
import copy
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import migration_lib as L  # noqa: E402

BEFORE = '128263f'               # M3.10B and its gap-register record: the state M3.10C applied to
GOLDEN = '88f8c8d'               # M3.10C
TOOL = L.ROOT + 'tools/apply-value-manifest.py'
M310C = L.ROOT + 'data/audit/m3.10c-value-application.jsonl'
TABLES = ('canonical/values.jsonl', 'cross/provenance.jsonl', 'observation/observations.jsonl',
          'reconciliation/reconciliations.jsonl')
# the fields the runner's metadata alone makes differ from M3.10C's (ids are hashes of the runner's tag and actor)
METADATA = {'observation.extraction', 'observation.id', 'observation.provenance', 'provenance.DERIVATION.actor',
            'provenance.DERIVATION.code_state', 'provenance.DERIVATION.id', 'provenance.DOCUMENT.actor',
            'provenance.DOCUMENT.code_state', 'provenance.DOCUMENT.id', 'reconciliation.id',
            'reconciliation.provenance', 'reconciliation.reason', 'reconciliation.resolver', 'value.provenance',
            'value.reconciliation'}
CHECKS = []
TMP = []
BASE = []


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT)


def _runner():
    import importlib.util
    spec = importlib.util.spec_from_file_location('apply_value_manifest', TOOL)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


R = _runner()
PROD = L.jsonl_lines(L.ROOT + R.MANIFEST)
VIEW = R.View()
EV = R.Evidence({9})
SCOPE = R.load_scope(M310C)


def errors(rows, scope=None, ev=None):
    return R.validate_manifest(rows, VIEW, ev or EV, scope)[0]


def row(mid):
    return copy.deepcopy(next(r for r in PROD if r['manifest_id'] == mid))


def _base():
    """The model at 128263f, once, in a temporary directory."""
    if not BASE:
        d = tempfile.mkdtemp(prefix='m311-base-')
        for f in git('ls-tree', '-r', '--name-only', BEFORE, 'data/model').decode().split():
            p = os.path.join(d, f[len('data/model/'):])
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'wb').write(git('show', '%s:%s' % (BEFORE, f)))
        TMP.append(d)
        BASE.append(d)
    return BASE[0]


def isolated():
    d = tempfile.mkdtemp(prefix='m311-')
    shutil.rmtree(d)
    shutil.copytree(_base(), d)
    TMP.append(d)
    return d


def snapshot(d):
    out = {}
    for base, _, names in os.walk(d):
        for n in names:
            p = os.path.join(base, n)
            out[os.path.relpath(p, d).replace('\\', '/')] = open(p, 'rb').read()
    return out


def run(*args, model=None, manifest=None):
    env = dict(os.environ)
    env.pop('BDX_MODEL_DIR', None)
    if model:
        env['BDX_MODEL_DIR'] = model
    a = list(args)
    if manifest is not None:
        p = tempfile.mktemp(prefix='m311-manifest-', suffix='.jsonl')
        open(p, 'w', encoding='utf-8', newline='\n').write(''.join(L.dumps(r) + '\n' for r in manifest))
        TMP.append(p)
        a += ['--manifest', p]
    return subprocess.run([sys.executable, TOOL] + a, cwd=L.ROOT, env=env, capture_output=True, text=True)


# ---------------------------------------------------------------- validation

@check
def c01_the_nine_row_m310c_manifest_validates():
    assert len(PROD) == 9 and [r['manifest_id'] for r in PROD] == ['vam_%06d' % n for n in range(1, 10)]
    assert errors(PROD, SCOPE) == []
    m310c = {(r['vintage'], r['field']): r for r in L.jsonl_lines(M310C) if r['record'] == 'value'}
    for r in PROD:          # each row is M3.10C's: value, artifacts, quotes, loci, languages
        x = m310c[('vt:%s:%d' % (r['wine_id'], r['vintage']), r['field'])]
        assert L.dumps(r['value']) == L.dumps(x['value']) and r['evidence_version'] == 9
        assert sorted((l['artifact'], l['locus'], l['quote'], l['lang']) for l in r['source_locations']) == \
            sorted((o['artifact'], o['locus'], o['quote'], o['lang']) for o in x['observations'])
    out = run('--validate')
    assert out.returncode == 0 and '9 manifest row(s) in 3 packet(s) valid' in out.stdout, out.stdout + out.stderr


@check
def c02_duplicate_manifest_id():
    r = row('vam_000004')
    r['field'], r['value'] = 'oak', 50
    r2 = row('vam_000001')
    r2['manifest_id'] = 'vam_000004'
    e = errors([row('vam_000004'), r2])
    assert any('manifest_id used 2 times' in x for x in e), e


@check
def c03_unknown_estate():
    r = row('vam_000007')
    r['estate_id'] = 'es_99999'
    assert any('estate es_99999 does not exist' in x for x in errors([r])), errors([r])


@check
def c04_unknown_wine():
    r = row('vam_000007')
    r['wine_id'] = 'wn_99999'
    assert any('wine wn_99999 does not exist' in x for x in errors([r])), errors([r])


@check
def c05_wine_of_another_estate():
    other = sorted(e['id'] for e in VIEW.table('identity/estates.jsonl') if e['id'] != 'es_00263')[0]
    r = row('vam_000007')
    r['estate_id'] = other
    assert any('does not belong to estate %s' % other in x for x in errors([r])), errors([r])


@check
def c06_unknown_vintage():
    r = row('vam_000007')
    r['vintage'] = 1850
    assert any('vintage 1850 of wn_00263 does not exist' in x for x in errors([r])), errors([r])
    r['vintage'] = '2024'
    assert any('is not a year' in x for x in errors([r])), errors([r])


@check
def c07_unknown_field():
    for f in ('colour', 'harvest', 'vineyard_area_ha'):
        r = row('vam_000007')
        r['field'] = f
        assert any('is not a field the runner applies' in x for x in errors([r])), (f, errors([r]))


@check
def c08_invalid_value_type():
    for field, bad in (('oak', '70'), ('oak', 170), ('oak', True), ('blend', {'CS': 94.5, 'ME': 5}),
                       ('blend', {'XX': 100}), ('months', 18), ('pick', {'ALL': '13-40|10-08'}),
                       ('pick', {'ALL': '|'}), ('yld', None), ('alc', 'thirteen')):
        r = row({'oak': 'vam_000007', 'blend': 'vam_000005', 'months': 'vam_000006', 'pick': 'vam_000008',
                 'yld': 'vam_000009', 'alc': 'vam_000004'}[field])
        r['value'] = bad
        assert any('is not a valid %s' % field in x for x in errors([r])), (field, bad, errors([r]))
    r = row('vam_000007')
    r['unit'] = 'percent'
    assert any("unit 'percent'" in x for x in errors([r])), errors([r])
    r = row('vam_000007')
    r['application_class'] = 'DERIVED'
    r['source_basis'] = 'calculated'
    e = errors([r])
    assert any('application_class' in x for x in e) and any('source_basis' in x for x in e), e


@check
def c09_missing_evidence():
    r = row('vam_000007')
    r['artifact_ids'] = ['ar_999999']
    r['source_locations'][0]['artifact'] = 'ar_999999'
    assert any('artifact ar_999999 does not exist' in x for x in errors([r])), errors([r])
    # an artifact the model holds, with no accepted attribution to this vintage (a legacy one at most)
    legacy = sorted(a['id'] for a in VIEW.table('identity/artifacts.jsonl')
                    if a['id'] not in VIEW.index()['attributions'])[0]
    r['artifact_ids'] = [legacy]
    r['source_locations'][0]['artifact'] = legacy
    assert any('has no accepted attribution' in x for x in errors([r])), errors([r])
    r = row('vam_000007')
    r['source_locations'] = []
    assert any('source_locations' in x for x in errors([r])), errors([r])


@check
def c10_rejected_or_superseded_evidence():
    import mig_m6_provenance as M6
    [k] = [k for k, d in EV.by_key.items() if (d.get('read') or {}).get('sha256') ==
           VIEW.index()['artifacts']['ar_037071']['sha256']]
    ctx = L.dumps(json.loads(k)[:-1])
    for change in ({'decision': 'REJECTED', 'code': 'REJECTED'}, {'decision': 'WRONG_WINE'}):
        ev = copy.copy(EV)
        ev.by_key, ev.latest = dict(EV.by_key), dict(EV.latest)
        d = dict(EV.by_key[k], **change)
        ev.by_key[k] = ev.latest[ctx] = d
        e = errors([row('vam_000007')], ev=ev)
        assert any('not ACCEPTED' in x for x in e), e
    ev = copy.copy(EV)
    ev.by_key, ev.latest = dict(EV.by_key), dict(EV.latest)
    later = dict(EV.by_key[k], v=10, decision='WRONG_WINE')
    ev.by_key[M6.row_key(later)] = ev.latest[ctx] = later
    e = errors([row('vam_000007')], ev=ev)
    assert any('superseded by version 10' in x for x in e), e


@check
def c11_wrong_evidence_version():
    r = row('vam_000007')
    r['evidence_version'] = 8
    e = R.validate_manifest([r], VIEW, R.Evidence({8}))[0]
    assert any('no evidence decision at version 8' in x for x in e), e
    r['evidence_version'] = 99
    assert any('is not a version of the store' in x for x in errors([r])), errors([r])


@check
def c12_artifact_of_another_vintage():
    r = row('vam_000007')               # 2024 oak, citing the 2014 English sheet
    r['artifact_ids'] = ['ar_037069']
    r['source_locations'][0]['artifact'] = 'ar_037069'
    e = errors([r])
    assert any('ar_037069 has no accepted attribution to vt:wn_00263:2024' in x for x in e), e


@check
def c13_duplicate_field_in_packet():
    r = row('vam_000007')
    r['manifest_id'] = 'vam_000010'
    e = errors(PROD + [r])
    assert any('duplicate field in packet' in x for x in e), e
    r['observation_group'] = 'another-group'
    e = errors(PROD + [r])
    assert any('one fact in several' in x for x in e), e
    r = row('vam_000004')                # a group spanning two vintages
    r['observation_group'] = 'durfort-vivens-2024'
    e = errors([row('vam_000007'), r])
    assert any('spans vintages' in x for x in e), e


@check
def c14_missing_expected_field():
    e = errors([r for r in PROD if r['manifest_id'] != 'vam_000003'], SCOPE)
    assert e == ['expected scope: vt:wn_00263:2014 oak is missing'], e
    out = run('--plan', '--expected-scope', M310C, manifest=PROD[:-1])
    assert out.returncode != 0 and 'vt:wn_00263:2024 yld is missing' in out.stderr, out.stderr


@check
def c15_unexpected_field():
    r = row('vam_000004')
    r.update(manifest_id='vam_000010', vintage=2014, field='yld', value=40, unit='hl/ha',
             observation_group='durfort-vivens-2014', artifact_ids=['ar_037069'])
    r['source_locations'] = [dict(row('vam_000001')['source_locations'][1])]
    assert r['source_locations'][0]['artifact'] == 'ar_037069'
    assert errors([r]) == [], errors([r])          # a valid row in itself ...
    e = errors(PROD + [r], SCOPE)
    assert e == ['expected scope: vt:wn_00263:2014 yld is not expected'], e     # ... outside the scope


# ---------------------------------------------------------------- application

@check
def c16_idempotent_second_application():
    d = isolated()
    out = run('--apply', '--expected-scope', M310C, model=d)
    assert out.returncode == 0 and 'applied 9 row(s); 0 held already' in out.stdout, out.stdout + out.stderr
    after = snapshot(d)
    out = run('--apply', model=d)
    assert out.returncode == 0 and 'nothing to apply: 9 row(s) held already' in out.stdout, out.stdout + out.stderr
    assert snapshot(d) == after, 'a second application changed the model'
    assert run('--check', model=d).returncode == 0
    out = run('--plan', model=d)
    assert out.stdout.count('NOOP_EXISTING_IDENTICAL (held') == 9


@check
def c17_existing_identical_in_production():
    out = run('--plan')
    assert out.returncode == 0 and '0 APPLY, 9 NOOP_EXISTING_IDENTICAL, 0 CONFLICT' in out.stdout, out.stdout + out.stderr
    assert '0 source observation(s), 0 reconciliation(s), 0 canonical value(s), 0 provenance row(s)' in out.stdout
    out = run('--apply')
    assert out.returncode == 0 and 'nothing to apply' in out.stdout, out.stdout + out.stderr
    assert not git('status', '--porcelain', '--', 'data/model', 'data/app').strip()
    assert not git('diff', '--stat', GOLDEN, '--', 'data/model', 'data/app').strip()
    assert run('--check').returncode == 0


@check
def c18_existing_conflicting_value():
    r = row('vam_000007')
    r['value'] = 30                      # the reader's misread, which the model holds as 70
    rs, view = [r], R.View()
    e, res = R.validate_manifest(rs, view, EV)
    assert e == []
    plan = R.plan_manifest(rs, res, view)
    [it] = plan['packets'][0]['rows']
    assert (it['action'], it['reason']) == ('CONFLICT', 'the model holds 70'), it
    # --apply refuses a conflicting manifest and writes nothing, beside a row it could apply alone
    d = isolated()
    out = run('--apply', model=d)
    assert out.returncode == 0
    before = snapshot(d)
    bad = [row(m) for m in ('vam_000001', 'vam_000002')]
    bad[0]['value'] = {'CS': 80, 'ME': 20}
    out = run('--apply', model=d, manifest=bad)
    assert out.returncode != 0 and 'CONFLICT' not in out.stdout and 'conflict' in out.stderr, out.stdout + out.stderr
    assert 'the model holds {"CS":90,"ME":10}' in out.stderr and 'nothing was written' in out.stderr
    assert snapshot(d) == before, 'a conflict wrote something'


@check
def c19_multi_artifact_row_is_one_fact():
    d = isolated()
    assert run('--apply', model=d).returncode == 0
    old = {rel: set(git('show', '%s:data/model/%s' % (BEFORE, rel)).decode('utf-8').splitlines()) for rel in TABLES}
    new = {rel: [json.loads(x) for x in open(os.path.join(d, rel), encoding='utf-8').read().splitlines()
                 if x not in old[rel]] for rel in TABLES}
    for f in ('blend', 'oak', 'months'):
        k = ('vt:wn_00263:2014', f)
        obs = [o for o in new['observation/observations.jsonl'] if (o['subject'], o['field']) == k]
        recs = [r for r in new['reconciliation/reconciliations.jsonl'] if (r['subject'], r['field']) == k]
        vals = [v for v in new['canonical/values.jsonl'] if (v['subject'], v['field']) == k]
        assert sorted(o['artifact'] for o in obs) == ['ar_037068', 'ar_037069'], obs
        assert len(recs) == 1 and len(vals) == 1
        assert (recs[0]['rule'], recs[0]['status']) == ('UNANIMOUS', 'AGREED')
        assert recs[0]['candidates'] == [o['id'] for o in sorted(obs, key=lambda o: o['artifact'])]
        assert vals[0]['reconciliation'] == recs[0]['id']
    singles = [r for r in new['reconciliation/reconciliations.jsonl'] if not r['subject'].endswith('2014')]
    assert len(singles) == 6 and all(r['rule'] == 'ONLY_CANDIDATE' and len(r['candidates']) == 1 for r in singles)
    # field-level application provenance: manifest row, artifacts, observations, evidence version, runner version
    prov = {p['id']: p for p in new['cross/provenance.jsonl']}
    for rc in new['reconciliation/reconciliations.jsonl']:
        cs = prov[rc['provenance']]['code_state']
        assert cs['runner'] == R.RUNNER and cs['manifest_id'].startswith('vam_') and cs['observations'] == rc['candidates']
        assert cs['evidence_version'] == 9 and cs['artifacts']
    for o in new['observation/observations.jsonl']:
        p = prov[o['provenance']]
        assert p['kind'] == 'DOCUMENT' and p['artifact'] == o['artifact'] and p['quote'] == o['raw_value']
        assert p['code_state']['evidence_decision'] and p['code_state']['evidence_version'] == 9


@check
def c20_deterministic_plan():
    a, b = run('--plan'), run('--plan')
    assert a.returncode == 0 and a.stdout == b.stdout
    shuffled = list(PROD)
    random.Random(311).shuffle(shuffled)
    assert run('--plan', manifest=shuffled).stdout == a.stdout
    d = isolated()
    p1, p2 = run('--plan', model=d), run('--plan', model=d)
    assert p1.stdout == p2.stdout and '9 APPLY, 0 NOOP_EXISTING_IDENTICAL, 0 CONFLICT' in p1.stdout
    assert '12 source observation(s), 9 reconciliation(s), 9 canonical value(s), 21 provenance row(s)' in p1.stdout
    assert '0 new estates, 0 new wines, 0 new vintages' in p1.stdout
    # the 2024 oak: 70%, never 30%
    block = p1.stdout.split('oak  vam_000007')[1].split('\n\n')[0]
    assert 'value: 70%' in block and '30' not in p1.stdout.replace('vam_0000', '')


@check
def c21_no_partial_mutation():
    d = isolated()
    before = snapshot(d)
    rows = [row(m) for m in ('vam_000001', 'vam_000002', 'vam_000003', 'vam_000004', 'vam_000005', 'vam_000006',
                             'vam_000007', 'vam_000008')]
    r = row('vam_000009')
    r['field'] = 'colour'               # row 9 invalid
    out = run('--apply', model=d, manifest=rows + [r])
    assert out.returncode != 0 and 'nothing was written' in out.stderr, out.stdout + out.stderr
    assert snapshot(d) == before, 'rows 1-8 were written'


@check
def c22_m310c_golden_equivalence():
    d = isolated()
    out = run('--apply', '--expected-scope', M310C, model=d)
    assert out.returncode == 0, out.stderr
    old = {rel: set(git('show', '%s:data/model/%s' % (BEFORE, rel)).decode('utf-8').splitlines()) for rel in TABLES}
    ref = {rel: [json.loads(x) for x in git('show', '%s:data/model/%s' % (GOLDEN, rel)).decode('utf-8').splitlines()
                 if x not in old[rel]] for rel in TABLES}
    got = {rel: [json.loads(x) for x in open(os.path.join(d, rel), encoding='utf-8').read().splitlines()
                 if x not in old[rel]] for rel in TABLES}
    assert {k: len(v) for k, v in ref.items()} == {k: len(v) for k, v in got.items()} == {
        'canonical/values.jsonl': 9, 'cross/provenance.jsonl': 21, 'observation/observations.jsonl': 12,
        'reconciliation/reconciliations.jsonl': 9}
    differ = set()

    def cmp(tag, a, b, skip=()):
        for f in set(a) | set(b):
            if f not in skip and L.dumps(a.get(f)) != L.dumps(b.get(f)):
                differ.add(tag + f)
    key = lambda o: (o['subject'], o['field'], o['artifact'])
    ro = {key(o): o for o in ref['observation/observations.jsonl']}
    go = {key(o): o for o in got['observation/observations.jsonl']}
    assert set(ro) == set(go)
    om = {ro[k]['id']: go[k]['id'] for k in ro}
    pm = {ro[k]['provenance']: go[k]['provenance'] for k in ro}
    rp = {p['id']: p for p in ref['cross/provenance.jsonl']}
    gp = {p['id']: p for p in got['cross/provenance.jsonl']}
    for k in ro:
        cmp('observation.', ro[k], go[k])
        cmp('provenance.DOCUMENT.', rp[ro[k]['provenance']], gp[go[k]['provenance']])
    rr = {(r['subject'], r['field']): r for r in ref['reconciliation/reconciliations.jsonl']}
    gr = {(r['subject'], r['field']): r for r in got['reconciliation/reconciliations.jsonl']}
    assert set(rr) == set(gr)
    for k in rr:
        assert [om[x] for x in rr[k]['candidates']] == gr[k]['candidates'] and om[rr[k]['selected']] == gr[k]['selected']
        cmp('reconciliation.', rr[k], gr[k], skip=('candidates', 'selected'))
        a, b = rp[rr[k]['provenance']], gp[gr[k]['provenance']]
        assert sorted(pm[x] for x in a['derived_from']) == b['derived_from']
        cmp('provenance.DERIVATION.', a, b, skip=('derived_from',))
    rv = {(v['subject'], v['field']): v for v in ref['canonical/values.jsonl']}
    gv = {(v['subject'], v['field']): v for v in got['canonical/values.jsonl']}
    assert set(rv) == set(gv)
    for k in rv:
        assert L.dumps(rv[k]['value']) == L.dumps(gv[k]['value']) and rv[k]['status'] == gv[k]['status'] == 'SOURCED'
        assert pm[rv[k]['provenance']] == gv[k]['provenance']
        cmp('value.', rv[k], gv[k])
    assert differ == METADATA, sorted(differ ^ METADATA)
    # nothing else in the model: identities, attributions, every other table byte for byte; the manifest's counts
    for f in git('ls-tree', '-r', '--name-only', BEFORE, 'data/model').decode().split():
        rel = f[len('data/model/'):]
        if rel not in TABLES and rel != 'manifest.json':
            assert open(os.path.join(d, rel), 'rb').read() == git('show', '%s:%s' % (BEFORE, f)), rel
    m0 = json.loads(git('show', '%s:data/model/manifest.json' % BEFORE))
    m1 = json.load(open(os.path.join(d, 'manifest.json'), encoding='utf-8'))
    assert m1['stats']['M7'].pop(R.STAT) == 9
    for rel in TABLES:
        m1['files'][rel]['rows'] -= {'canonical/values.jsonl': 9, 'cross/provenance.jsonl': 21,
                                     'observation/observations.jsonl': 12, 'reconciliation/reconciliations.jsonl': 9}[rel]
        m1['files'][rel].pop('sha256')
        m0['files'][rel].pop('sha256')
    assert m0 == m1
    # a migration rebuild gives the copy byte for byte (M3.10C's own hook set aside: the copy is before it)
    import migrate
    import mig_m7_observations as M7
    keep = M7.M310C
    M7.M310C = 'data/audit/m3.11-no-such-manifest.jsonl'
    try:
        files = migrate.render(migrate.run('M7'), 'M7')
    finally:
        M7.M310C = keep
    for rel, b in files.items():
        assert open(os.path.join(d, rel), 'rb').read() == b, ('the rebuild differs', rel)
    env = dict(os.environ, BDX_MODEL_DIR=d)
    out = subprocess.run([sys.executable, L.ROOT + 'tools/build-indexes.py', '--check'], cwd=L.ROOT, env=env,
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stdout


@check
def c23_production_is_untouched_and_the_runner_checks():
    assert not git('diff', '--stat', GOLDEN, '--', 'data/model', 'data/app', 'data/evidence', 'data/discovery').strip()
    assert not git('status', '--porcelain', '--', 'data/model', 'data/app', 'data/evidence').strip()
    out = run('--check-all')
    assert out.returncode == 0 and 'model at M7 rebuilds byte for byte' in out.stdout, out.stdout + out.stderr
    reader = ('tools/m35_rubric.py', 'tools/web_evidence.py', 'tools/sheetreader.py', 'tools/read-fiches.py',
              'tools/m34a-mapping-audit.py', 'tools/model_schema.py', 'tools/evidence.py', 'tools/m310c-values.py',
              'data/audit/m3.10c-value-application.jsonl')
    assert not git('diff', '--stat', GOLDEN, '--', *reader).strip()


def main():
    fails = 0
    try:
        for f in CHECKS:
            try:
                f()
                print('ok   %s' % f.__name__)
            except Exception as ex:
                fails += 1
                print('FAIL %s: %s' % (f.__name__, (str(ex) or repr(ex))[:400]))
    finally:
        for p in TMP:
            shutil.rmtree(p, ignore_errors=True) if os.path.isdir(p) else os.path.exists(p) and os.remove(p)
    print('%d check(s), %s' % (len(CHECKS), 'all pass' if not fails else '%d FAIL' % fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
