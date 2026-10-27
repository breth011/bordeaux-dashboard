"""Phase V1: new-vintage creation (tools/apply-vintage-creation-manifest.py; mig_m5_vintages.vintage_creation and
mig_m6_provenance.vintage_creation_attributions; the V1 exception in historical_m2_scope).

    python tools/test-vintage-creation-manifest.py

Read-only for the repository. The production manifest is empty and must stay so; every application runs on an
isolated copy of the model (BDX_MODEL_DIR) or in memory. The real case is Château Durfort-Vivens 2024 (wn_00263,
ar_037071, M3.9's review row m3.9:4, its v9 decision): taken out of a copy, the runner must put back exactly its
shell and an existence attribution equal to M3.10B's but for the runner's metadata, after which the value runner
(M3.11, unchanged) plans M3.10C's five 2024 values. Negative cases alter the review row or the evidence decision in
memory only. A synthetic vintage (Durfort-Vivens 2025, a fabricated decision and review, in a subprocess and an
isolated copy only) exercises the migration hooks, rebuild determinism, the historical-scope exception and the gap
register's set-aside (U2).
"""
import copy
import datetime
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import migration_lib as L  # noqa: E402

TOOL = L.ROOT + 'tools/apply-vintage-creation-manifest.py'
VALUE_TOOL = L.ROOT + 'tools/apply-value-manifest.py'
REVIEW = 'data/audit/m3.9-evidence-review.jsonl'
ESTATE, WINE, ART, VT = 'es_00263', 'wn_00263', 'ar_037071', 'vt:wn_00263:2024'
M310B_ATTRIBUTION = 'at_118b7dcaeeb1'
VINTAGE_SCOPED = ('canonical/values.jsonl', 'observation/observations.jsonl', 'reconciliation/reconciliations.jsonl')
CHECKS, TMP, BASE = [], [], []


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT)


def load(path, name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


V = load(TOOL, 'apply_vintage_creation_manifest_t')
R11 = load(VALUE_TOOL, 'apply_value_manifest_t')
PROV = {p['id']: p for p in L.read_table('cross/provenance.jsonl')}
KEY = PROV[[a for a in L.read_table('document/attributions.jsonl') if a['id'] == M310B_ATTRIBUTION][0]['provenance']][
    'code_state']['evidence_decisions'][0]
EV = R11.Evidence({9})
VIEW = V.View()


def row(**kw):
    r = {'manifest_id': 'vcm_000001', 'estate_id': ESTATE, 'wine_id': WINE, 'vintage': 2024, 'artifact_ids': [ART],
         'evidence_version': 9, 'evidence_decisions': {ART: KEY},
         'review': {ART: {'audit': REVIEW, 'row': 'm3.9:4'}}, 'creation_class': 'EXPLICIT_DOCUMENT_TEXT'}
    r.update(kw)
    return r


class FixedReviews(V.Reviews):
    """The review audits, with some rows replaced or added (in memory only)."""

    def __init__(self, extra):
        super().__init__()
        self.extra = extra

    def get(self, audit, r):
        return copy.deepcopy(self.extra[(audit, r)]) if (audit, r) in self.extra else super().get(audit, r)


def review_with(**kw):
    rv = copy.deepcopy(V.Reviews().get(REVIEW, 'm3.9:4'))
    rv.update(kw)
    return FixedReviews({(REVIEW, 'm3.9:4'): rv})


def evidence_with(change=None, later=None):
    ev = copy.copy(EV)
    ev.by_key, ev.latest = dict(EV.by_key), dict(EV.latest)
    ctx = L.dumps(json.loads(KEY)[:-1])
    if change:
        ev.by_key[KEY] = ev.latest[ctx] = dict(EV.by_key[KEY], **change)
    if later:
        import mig_m6_provenance as M6
        d = dict(EV.by_key[KEY], **later)
        ev.by_key[M6.row_key(d)] = ev.latest[ctx] = d
    return ev


def errors(rows, view=None, ev=None, reviews=None):
    return V.validate_manifest(rows, view or VIEW, ev or EV, reviews)[0]


def m310b_rows():
    """Durfort-Vivens' three vintages as creation rows, from M3.10B's accepted decisions (artifact, review row,
    evidence decision): all held in production (NOOP)."""
    by = {}
    for d in L.jsonl_lines(L.ROOT + 'data/audit/m3.10b-evidence-decisions.jsonl'):
        if d['record'] == 'decision':
            by.setdefault(d['vintage'], []).append(d)
    out = []
    for n, (y, ds) in enumerate(sorted(by.items()), 1):
        out.append(row(manifest_id='vcm_%06d' % n, vintage=y, artifact_ids=sorted(d['artifact'] for d in ds),
                       evidence_decisions={d['artifact']: d['evidence_decision'] for d in ds},
                       review={d['artifact']: {'audit': REVIEW, 'row': d['candidate']} for d in ds}))
    return out


def gone(rel, rows, attribution_only=False):
    """`rows` of `rel` with Durfort-Vivens 2024 taken out: its vintage, its attributions and its values (or, with
    attribution_only, M3.10B's attribution alone)."""
    if attribution_only:
        return [a for a in rows if a.get('id') != M310B_ATTRIBUTION] if rel == 'document/attributions.jsonl' else rows
    if rel == 'identity/vintages.jsonl':
        return [v for v in rows if (v['wine'], v['label']) != (WINE, '2024')]
    if rel == 'document/attributions.jsonl':
        return [a for a in rows if a.get('vintage') != VT]
    if rel in VINTAGE_SCOPED:
        return [x for x in rows if x.get('subject') != VT]
    return rows


def gone_view(attribution_only=False):
    return V.View(lambda rel: gone(rel, L.read_table(rel), attribution_only))


def isolated(attribution_only=None):
    """A copy of the committed model (HEAD) in a temporary directory; with attribution_only False or True,
    Durfort-Vivens 2024 taken out of it as gone() does."""
    if not BASE:
        d = tempfile.mkdtemp(prefix='v1-base-')
        for f in git('ls-tree', '-r', '--name-only', 'HEAD', 'data/model').decode().split():
            p = os.path.join(d, f[len('data/model/'):])
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'wb').write(git('show', 'HEAD:' + f))
        TMP.append(d)
        BASE.append(d)
    d = tempfile.mkdtemp(prefix='v1-')
    shutil.rmtree(d)
    shutil.copytree(BASE[0], d)
    TMP.append(d)
    if attribution_only is not None:
        for rel in ('identity/vintages.jsonl', 'document/attributions.jsonl') + VINTAGE_SCOPED:
            p = os.path.join(d, rel)
            rows = gone(rel, L.jsonl_lines(p), attribution_only)
            open(p, 'w', encoding='utf-8', newline='\n').write(''.join(L.dumps(x) + '\n' for x in rows))
    return d


def snapshot(d):
    out = {}
    for base, _, names in os.walk(d):
        for n in names:
            out[os.path.relpath(os.path.join(base, n), d).replace('\\', '/')] = open(os.path.join(base, n), 'rb').read()
    return out


def run(*args, model=None, manifest=None, tool=TOOL):
    env = dict(os.environ)
    env.pop('BDX_MODEL_DIR', None)
    if model:
        env['BDX_MODEL_DIR'] = model
    a = list(args)
    if manifest is not None:
        p = tempfile.mktemp(prefix='v1-manifest-', suffix='.jsonl')
        open(p, 'w', encoding='utf-8', newline='\n').write(''.join(L.dumps(r) + '\n' for r in manifest))
        TMP.append(p)
        a += ['--manifest', p]
    return subprocess.run([sys.executable, tool] + a, cwd=L.ROOT, env=env, capture_output=True, text=True)


def added(d, before, rel):
    old = set(before[rel].decode('utf-8').splitlines())
    return [json.loads(x) for x in open(os.path.join(d, rel), encoding='utf-8').read().splitlines() if x not in old]


# ---------------------------------------------------------------- plan and application

@check
def c01_valid_creation_plan():
    view = gone_view()
    e, res = V.validate_manifest([row()], view, EV)
    assert e == [], e
    plan = V.plan_manifest([row()], res, view)
    [it] = plan['rows']
    assert (it['action'], it['reason']) == ('CREATE', 'no vintage %s' % VT), it
    assert plan['adds'] == {'cross/provenance.jsonl': 1, 'document/attributions.jsonl': 1, 'identity/vintages.jsonl': 1}
    V.verify_plan(plan)


@check
def c02_c03_c04_creation_application_is_the_shell_and_its_exact_attribution_with_no_value():
    d = isolated(attribution_only=False)
    before = snapshot(d)
    out = run('--apply', model=d, manifest=[row()])
    assert out.returncode == 0 and 'applied: 1 CREATE, 0 ATTRIBUTION_ONLY; 0 NOOP' in out.stdout, out.stdout + out.stderr
    after = snapshot(d)
    changed = sorted(k for k in after if after[k] != before.get(k))
    assert changed == ['cross/provenance.jsonl', 'document/attributions.jsonl', 'identity/vintages.jsonl',
                       'manifest.json'], changed
    # the indexes were rebuilt: the copy's (taken from HEAD, which holds 2024) come out the same, and are current
    for rel in ('derived/vintage-documents.json', 'derived/wine-vintages.json'):
        assert after[rel] == git('show', 'HEAD:data/model/' + rel), rel
    assert run('--check', model=d, manifest=[row()], tool=L.ROOT + 'tools/build-indexes.py').returncode == 0
    assert added(d, before, 'identity/vintages.jsonl') == [{'label': '2024', 'wine': WINE}]
    [a] = added(d, before, 'document/attributions.jsonl')
    [p] = added(d, before, 'cross/provenance.jsonl')
    # the exact existence attribution: M3.10B's at_118b7dcaeeb1, field for field but its id and provenance
    ref = [x for x in L.read_table('document/attributions.jsonl') if x['id'] == M310B_ATTRIBUTION][0]
    assert {k: v for k, v in a.items() if k not in ('id', 'provenance')} == \
        {k: v for k, v in ref.items() if k not in ('id', 'provenance')}, (a, ref)
    assert a['provenance'] == p['id'] and (p['kind'], p['artifact'], p['actor']) == ('DOCUMENT', ART, V.ACTOR)
    rp = PROV[ref['provenance']]
    assert p['quote'] == V.Reviews().get(REVIEW, 'm3.9:4')['reason'] and rp['quote'] in p['quote'], (p['quote'], rp['quote'])
    cs = p['code_state']
    assert (cs['evidence_decisions'], cs['evidence_version'], cs['candidate'], cs['review'], cs['sha256']) == \
        ([KEY], 9, 'm3.9:4', REVIEW, rp['code_state']['sha256'])
    assert (cs['identity_source'], cs['vintage_source']) == (rp['code_state']['identity_source'],
                                                             rp['code_state']['vintage_source'])
    # zero values: nothing on the vintage but its attribution; identities, statements and values byte for byte
    for rel in VINTAGE_SCOPED + ('identity/estates.jsonl', 'identity/wines.jsonl', 'identity/names.jsonl',
                                 'identity/identity-map.jsonl', 'identity/transitions.jsonl',
                                 'state/vintage-statements.jsonl', 'state/estate-wine.jsonl'):
        assert after[rel] == before[rel], rel
    assert not [x for rel in VINTAGE_SCOPED for x in L.jsonl_lines(os.path.join(d, rel)) if x.get('subject') == VT]
    m = json.loads(after['manifest.json'])
    assert m['stats']['M5'][V.VINTAGE_STAT] == [VT] and m['stats']['M6'][V.ATTRIBUTION_STAT] == 1
    assert list(m['stats']['M5'])[-1] == V.VINTAGE_STAT and list(m['stats']['M6'])[-1] == V.ATTRIBUTION_STAT
    assert not re.search(r'20\d\d-\d\d-\d\d', L.dumps([a, p])), 'a date in the created rows'
    assert run('--check', model=d, manifest=[row()]).returncode == 0


# ---------------------------------------------------------------- identity and scope

@check
def c05_c06_c07_unknown_estate_unknown_wine_wrong_estate():
    assert any('estate es_99999 does not exist' in x for x in errors([row(estate_id='es_99999')]))
    assert any('wine wn_99999 does not exist' in x for x in errors([row(wine_id='wn_99999')]))
    other = sorted(VIEW.index()['grand'])[0]
    assert other != WINE
    assert any('does not belong to estate %s' % ESTATE in x for x in errors([row(wine_id=other)]))


@check
def c08_ambiguous_wine_and_open_estate_identity():
    def plus(rel, extra):
        return V.View(lambda r: L.read_table(r) + (extra if r == rel else []))
    amb = plus('identity/identity-map.jsonl', [{'namespace': 'wine-by-display-name', 'legacy_key': 'x|y',
                                                 'status': 'AMBIGUOUS', 'candidates': [WINE], 'provenance': 'pv_x'}])
    assert any('candidate of an ambiguous identity' in x for x in errors([row()], amb))
    fnd = plus('cross/findings.jsonl', [{'id': 'qf_x', 'target': ESTATE, 'kind': 'IDENTITY_UNCERTAIN', 'status': 'OPEN',
                                         'detail': 'x', 'detected_by': 'x', 'provenance': 'pv_x'}])
    assert any('open identity finding' in x for x in errors([row()], fnd))
    renamed = plus('identity/names.jsonl', [{'id': 'nm_x', 'kind': 'CURRENT', 'name': 'Durfort', 'subject': WINE,
                                             'provenance': 'pv_x'}])
    assert any('no single, settled current name' in x for x in errors([row()], renamed))


@check
def c09_c10_second_wine_and_cuvee_rejected():
    ix = VIEW.index()
    im = VIEW.table('identity/identity-map.jsonl')
    ew = {r['wine']: r['estate'] for r in VIEW.table('state/estate-wine.jsonl')}
    for ns in ('second-by-name', 'wine-by-slug'):
        w = sorted(r['stable_id'] for r in im if r['namespace'] == ns and r['status'] == 'ACTIVE' and r.get('stable_id')
                   and r['stable_id'] not in ix['grand'])[0]
        e = errors([row(wine_id=w, estate_id=ew[w])])
        assert any('is not the grand vin of estate' in x for x in e), (ns, w, e)


@check
def c11_c12_c13_c14_vintage_values():
    for y in ('2024', 2024.0, True, None, 'NV'):
        assert any('is not a year' in x for x in errors([row(vintage=y)])), y
    assert any('vintage 1949 is outside 1950-' in x for x in errors([row(vintage=1949)]))
    nxt = datetime.date.today().year + 1
    assert V.last_year() == nxt
    assert any('vintage %d is outside 1950-%d' % (nxt + 1, nxt) in x for x in errors([row(vintage=nxt + 1)]))
    # the bounds themselves pass the range rule (they fail later, on this 2024 evidence)
    for y in (1950, nxt):
        assert not any('outside' in x for x in errors([row(vintage=y)])), y


# ---------------------------------------------------------------- evidence

@check
def c15_c16_c17_filename_url_and_date_years_rejected():
    # no reviewed reader row: an ACCEPTED store decision alone (a filename guard's) is not enough
    e = errors([row(review={ART: {'audit': 'data/audit/m3.4a-mapping-proposals.jsonl', 'row': 'x'}})])
    assert any('no reviewed reader row' in x for x in e), e
    e = errors([row(review={ART: {'audit': REVIEW, 'row': 'm3.9:999'}})])
    assert any('no reviewed reader row' in x for x in e), e
    rv = V.Reviews().get(REVIEW, 'm3.9:4')
    filename = review_with(identity_source='FILENAME', claims=[dict(rv['claims'][0], evidence_of_document={
        'kind': 'DOCUMENT', 'rule': 'FILENAME', 'disposition': 'SAFE_TO_MAP'})])
    assert any('not established by the document\'s own text' in x for x in errors([row()], reviews=filename))
    url = review_with(vintage_evidence='url "commercialandtechnicalargumentationdv2024.pdf"')
    assert any('the vintage is not stated in the document' in x for x in errors([row()], reviews=url))
    dated = review_with(claims=[dict(rv['claims'][0], claim_year_dated=True)])
    assert any('dated line' in x for x in errors([row()], reviews=dated))


@check
def c18_c19_multi_vintage_and_multi_wine_rejected():
    rv = V.Reviews().get(REVIEW, 'm3.9:4')
    for disp, cat in (('VINTAGE_AMBIGUOUS', 'IDENTITY_AMBIGUOUS'), ('MULTI_WINE_AMBIGUOUS', 'IDENTITY_AMBIGUOUS'),
                      ('ESTATE_ONLY', 'ESTATE_VINTAGE_ONLY')):
        e = errors([row()], reviews=review_with(disposition=disp, category=cat))
        assert any('did not map it to one wine and vintage' in x for x in e), (disp, e)
    two = review_with(claims=[rv['claims'][0], dict(rv['claims'][0], wine='wn_00264')])
    assert any('maps 2 wine(s)' in x for x in errors([row()], reviews=two))
    other = review_with(wine='wn_00264')
    assert any('the reviewed row is for' in x for x in errors([row()], reviews=other))


@check
def c20_c21_c22_rejected_superseded_and_wrong_version():
    for change in ({'decision': 'REJECTED', 'code': 'REJECTED'}, {'decision': 'WRONG_WINE'}):
        assert any('not ACCEPTED' in x for x in errors([row()], ev=evidence_with(change=change))), change
    e = errors([row()], ev=evidence_with(later={'v': 10, 'decision': 'WRONG_WINE'}))
    assert any('superseded by version 10' in x for x in e), e
    e = V.validate_manifest([row(evidence_version=8)], VIEW, R11.Evidence({8}))[0]
    assert any('of version 9, not 8' in x for x in e), e
    assert any('is not a version of the store' in x for x in errors([row(evidence_version=99)]))
    assert any('not in the store' in x for x in errors([row(evidence_decisions={ART: KEY.replace('2024,9', '2023,9')})]))
    assert any('read other bytes' in x for x in errors([row()], ev=evidence_with(change={'read': {'sha256': '0' * 64}})))
    assert any('evidence decision is for' in x for x in errors([row()], ev=evidence_with(
        change={'ctx': dict(EV.by_key[KEY]['ctx'], target_role='second')})))


# ---------------------------------------------------------------- existing state

@check
def c23_existing_vintage_and_attribution_is_noop():
    rows = m310b_rows()
    e, res = V.validate_manifest(rows, VIEW, EV)
    assert e == [], e
    plan = V.plan_manifest(rows, res, VIEW)
    assert [(i['vintage_ref'], i['action'], i['adds']) for i in plan['rows']] == [
        ('vt:wn_00263:%d' % y, 'NOOP', {}) for y in (2014, 2021, 2024)], plan['rows']
    out = run('--apply', manifest=rows)
    assert out.returncode == 0 and 'nothing to apply: 3 row(s), all held (NOOP)' in out.stdout, out.stdout + out.stderr
    assert not git('status', '--porcelain', '--', 'data/model', 'data/app').strip()


@check
def c24_existing_vintage_without_its_attribution_is_attribution_only():
    view = gone_view(attribution_only=True)
    e, res = V.validate_manifest([row()], view, EV)
    plan = V.plan_manifest([row()], res, view)
    [it] = plan['rows']
    assert it['action'] == 'ATTRIBUTION_ONLY' and set(it['adds']) == {'cross/provenance.jsonl',
                                                                      'document/attributions.jsonl'}, it
    d = isolated(attribution_only=True)
    before = snapshot(d)
    out = run('--apply', model=d, manifest=[row()])
    assert out.returncode == 0 and 'applied: 0 CREATE, 1 ATTRIBUTION_ONLY' in out.stdout, out.stdout + out.stderr
    after = snapshot(d)
    assert after['identity/vintages.jsonl'] == before['identity/vintages.jsonl']
    assert all(after[rel] == before[rel] for rel in VINTAGE_SCOPED)
    assert len(added(d, before, 'document/attributions.jsonl')) == 1
    m = json.loads(after['manifest.json'])
    assert V.VINTAGE_STAT not in m['stats']['M5'] and m['stats']['M6'][V.ATTRIBUTION_STAT] == 1
    assert run('--apply', model=d, manifest=[row()]).stdout.startswith('nothing to apply')


@check
def c25_contradictions_are_conflicts():
    def plus(rel, extra):
        return V.View(lambda r: gone(r, L.read_table(r)) + (extra if r == rel else []))
    np_ = plus('state/vintage-statements.jsonl', [{'id': 'vs_x', 'vintage': VT, 'kind': 'NOT_PRODUCED',
                                                   'provenance': 'pv_x'}])
    elsewhere = plus('document/attributions.jsonl', [{'id': 'at_x', 'artifact': ART, 'estate': ESTATE, 'wine': WINE,
                                                      'vintage': 'vt:wn_00263:2014', 'status': 'ACCEPTED',
                                                      'method': 'DOCUMENT_TEXT', 'role': 'FIRST', 'provenance': 'pv_x'}])
    for view, why in ((np_, 'NOT_PRODUCED'), (elsewhere, 'ACCEPTED-attributed to')):
        e, res = V.validate_manifest([row()], view, EV)
        plan = V.plan_manifest([row()], res, view)
        [it] = plan['rows']
        assert it['action'] == 'CONFLICT' and why in it['reason'] and not it['adds'], it
        try:
            V.verify_plan(plan)
            raise AssertionError('a conflict passed verification')
        except V.Conflict:
            pass


@check
def c26_no_partial_mutation():
    d = isolated(attribution_only=False)
    before = snapshot(d)
    out = run('--apply', model=d, manifest=[row(), row(manifest_id='vcm_000002', estate_id='es_99999', vintage=2023)])
    assert out.returncode != 0 and 'nothing was written' in out.stderr, out.stdout + out.stderr
    assert snapshot(d) == before, 'the valid row was written'


@check
def c27_deterministic_plan():
    d = isolated(attribution_only=False)
    rows = m310b_rows()
    a, b = run('--plan', model=d, manifest=rows), run('--plan', model=d, manifest=rows)
    assert a.returncode == 0 and a.stdout == b.stdout and 'CREATE (no vintage %s)' % VT in a.stdout, a.stdout + a.stderr
    assert '3 manifest row(s): 1 CREATE, 0 ATTRIBUTION_ONLY, 2 NOOP, 0 CONFLICT' in a.stdout, a.stdout
    assert '1 vintage(s), 1 existence attribution(s), 1 provenance row(s)' in a.stdout
    shuffled = list(rows)
    random.Random(7).shuffle(shuffled)
    assert shuffled != rows and run('--plan', model=d, manifest=shuffled).stdout == a.stdout
    p1 = V.plan_manifest([row()], V.validate_manifest([row()], gone_view(), EV)[1], gone_view())
    p2 = V.plan_manifest([row()], V.validate_manifest([row()], gone_view(), EV)[1], gone_view())
    assert L.dumps(p1) == L.dumps(p2)


@check
def c28_deterministic_rebuild_scope_exception_and_gap_register():
    """In a subprocess (its own module state): a synthetic 2025 vintage on fabricated evidence, applied to an
    isolated copy; two migration rebuilds fed the same manifest must equal that copy byte for byte; the
    historical-scope exception and the gap register must set it aside."""
    d = isolated()
    out = subprocess.run([sys.executable, os.path.abspath(__file__), '--synthetic', d], cwd=L.ROOT,
                         env=dict(os.environ, BDX_MODEL_DIR=d), capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout.strip().endswith('synthetic: all pass'), (out.stdout + out.stderr)[-1500:]
    out = subprocess.run([sys.executable, L.ROOT + 'tools/build-data-gap-register.py', '--check-all'], cwd=L.ROOT,
                         env=dict(os.environ, BDX_MODEL_DIR=d), capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout.count('is current') == 2, out.stdout + out.stderr


@check
def c29_m311_needs_the_vintage_and_its_existence_attribution():
    """The value runner (M3.11), unchanged: refuses without the vintage, refuses with the shell alone, and plans
    M3.10C's five 2024 values once V1's existence attribution is there."""
    import migrate
    m = migrate.Model()
    for rel in ('identity/estates.jsonl', 'identity/wines.jsonl', 'state/estate-wine.jsonl', 'identity/vintages.jsonl',
                'identity/artifacts.jsonl', 'document/attributions.jsonl', 'cross/provenance.jsonl',
                'identity/names.jsonl', 'identity/identity-map.jsonl', 'cross/findings.jsonl',
                'state/vintage-statements.jsonl') + VINTAGE_SCOPED:
        for r in gone(rel, L.read_table(rel)):
            m.add(rel, r)
    values = [r for r in L.jsonl_lines(L.ROOT + R11.MANIFEST) if r['vintage'] == 2024]
    assert len(values) == 5

    def value_errors():
        return R11.validate_manifest(values, R11.View(m.rows), EV)[0]
    assert all('vintage 2024 of wn_00263 does not exist' in x for x in value_errors()) and len(value_errors()) == 5
    view = V.View(m.rows)
    plan = V.plan_manifest([row()], V.validate_manifest([row()], view, EV)[1], view)
    assert V.apply_plan(m, plan, attributions=False) == ([VT], 0)                       # the shell
    e = value_errors()
    assert len(e) == 5 and all('has no accepted attribution to %s' % VT in x for x in e), e
    view = V.View(m.rows)
    plan = V.plan_manifest([row()], V.validate_manifest([row()], view, EV)[1], view)
    assert plan['rows'][0]['action'] == 'ATTRIBUTION_ONLY'
    assert V.apply_plan(m, plan, shells=False) == ([], 1)                               # its existence attribution
    view = R11.View(m.rows)
    e, res = R11.validate_manifest(values, view, EV)
    assert e == [], e
    p = R11.plan_manifest(values, res, view)
    assert p['actions'] == {'APPLY': 5, 'NOOP_EXISTING_IDENTICAL': 0, 'CONFLICT': 0}, p['actions']
    assert '70%' in R11.render_plan(p) and not git('status', '--porcelain', '--', 'data/model').strip()


@check
def c30_production_manifest_empty_and_model_unchanged():
    assert os.path.getsize(L.ROOT + V.MANIFEST) == 0
    out = run('--check-all')
    assert out.returncode == 0 and '0 row(s) held' in out.stdout and 'model at M7 rebuilds byte for byte' in out.stdout \
        and 'data/app is the model, byte for byte' in out.stdout, out.stdout + out.stderr
    assert run('--plan').stdout.startswith('0 manifest row(s)')
    m = json.load(open(L.MODEL + 'manifest.json', encoding='utf-8'))
    assert V.VINTAGE_STAT not in m['stats'].get('M5', {}) and V.ATTRIBUTION_STAT not in m['stats'].get('M6', {})
    assert not git('status', '--porcelain', '--', 'data/model', 'data/app', 'data/evidence', 'data/discovery').strip()
    assert not git('diff', '--stat', 'HEAD', '--', 'data/model', 'data/app', 'data/evidence').strip()


# ---------------------------------------------------------------- the synthetic subprocess

def synthetic(d):
    """Run with BDX_MODEL_DIR=d (a copy of the committed model). Fabricated in memory: an ACCEPTED v9 decision and an
    M3.9-style review row stating Château Durfort-Vivens 2025, for an artifact with no attribution."""
    import mig_m6_provenance as M6
    import mig_m5_vintages as M5
    import migrate
    import historical_m2_scope as H
    import data_gap_analysis as A
    assert L.MODEL.rstrip('/') == d.replace('\\', '/').rstrip('/'), (L.MODEL, d)
    att = {a['artifact'] for a in L.read_table('document/attributions.jsonl')}
    art = sorted(a['id'] for a in L.read_table('identity/artifacts.jsonl')
                 if a.get('bytes_available') and a.get('sha256') and a['id'] not in att)[0]
    sha = [a for a in L.read_table('identity/artifacts.jsonl') if a['id'] == art][0]['sha256']
    dec = copy.deepcopy(EV.by_key[KEY])
    dec['ctx'].update(vintage=2025, target_vintage=2025, folder='acquisition:' + sha)
    dec['read'] = dict(dec['read'], sha256=sha)
    key = M6.row_key(dec)
    ev = copy.copy(EV)
    ev.by_key, ev.latest = dict(EV.by_key, **{key: dec}), dict(EV.latest, **{L.dumps(json.loads(key)[:-1]): dec})
    rv = copy.deepcopy(V.Reviews().get(REVIEW, 'm3.9:4'))
    rv.update(vintage=2025, sha256=sha, n=900, reason=rv['reason'].replace('2024', '2025'),
              vintage_evidence='statement "2025 vintage"')
    reviews = FixedReviews({(REVIEW, 'm3.9:900'): rv})
    r = row(vintage=2025, artifact_ids=[art], evidence_decisions={art: key}, review={art: {'audit': REVIEW, 'row': 'm3.9:900'}})
    view = V.View()
    e, res = V.validate_manifest([r], view, ev, reviews)
    assert e == [], e
    plan = V.plan_manifest([r], res, view)
    assert plan['rows'][0]['action'] == 'CREATE', plan['rows'][0]
    V.apply_manifest(view, plan)
    applied = snapshot(d)
    # the migration, fed the same manifest and evidence through the runner instance its hooks share
    W = M5.vintage_creator()
    W.load_manifest = lambda path: [r]
    W.VR.Evidence = lambda versions: ev
    W.Reviews = lambda: reviews
    builds = [migrate.render(migrate.run('M7'), 'M7') for _ in range(2)]
    assert builds[0] == builds[1], 'two rebuilds differ'
    for rel, b in builds[0].items():
        assert applied[rel] == b, ('the rebuild differs from --apply', rel)
    vt = 'vt:%s:2025' % WINE
    # the historical-scope exception: exactly these rows are V1's, and the earlier checks set them aside
    prov = {p['id']: p for p in L.read_table('cross/provenance.jsonl')}
    assert H.v1_created() == {(WINE, '2025')}
    mine = {rel: [x for x in L.read_table(rel) if H.is_v1_row(rel, x, prov)] for rel in
            ('identity/vintages.jsonl', 'document/attributions.jsonl', 'cross/provenance.jsonl')}
    assert {k: len(v) for k, v in mine.items()} == {'identity/vintages.jsonl': 1, 'document/attributions.jsonl': 1,
                                                    'cross/provenance.jsonl': 1}, mine
    assert mine['document/attributions.jsonl'][0]['vintage'] == vt
    assert not [a for a in H.legacy_attributions(L.read_table('document/attributions.jsonl'), prov) if a.get('vintage') == vt]
    head = json.loads(git('show', 'HEAD:data/model/manifest.json'))
    a, b = (H._without_m310a_manifest(x) for x in (head, json.loads(applied['manifest.json'])))
    for x in (a, b):
        x['files'] = {k: v['rows'] for k, v in x['files'].items()}
    assert a == b, 'the model manifest without M3.10A-C and V1 differs'
    real_git = H._git

    def isolated_git(*args):
        if args[:2] == ('diff', '--name-only'):
            out = []
            for rel in sorted(applied):
                try:
                    if git('show', '%s:data/model/%s' % (args[2], rel)) != applied[rel]:
                        out.append('data/model/' + rel)
                except subprocess.CalledProcessError:
                    out.append('data/model/' + rel)
            return '\n'.join(out)
        return real_git(*args)
    H._git = isolated_git
    try:
        changed = H.model_changes_are_m2_only('345f892')     # as test-m310c and the older suites call it
    finally:
        H._git = real_git
    assert {'identity/vintages.jsonl', 'document/attributions.jsonl', 'derived/wine-vintages.json'} <= set(changed)
    assert H.without_v1_vintages(json.loads(applied['derived/wine-vintages.json'])) == \
        json.loads(git('show', 'HEAD:data/model/derived/wine-vintages.json'))
    # U2: the gap analysis reads the model as before V1
    assert vt not in {'vt:%s:%s' % (v['wine'], v['label']) for v in A.table('identity/vintages.jsonl')}
    assert vt not in A.vintage_documents()
    print('synthetic: all pass')


def main():
    if '--synthetic' in sys.argv:
        synthetic(sys.argv[sys.argv.index('--synthetic') + 1])
        return
    fails = 0
    try:
        for f in CHECKS:
            try:
                f()
                print('ok   %s' % f.__name__)
            except Exception as ex:
                fails += 1
                print('FAIL %s: %s' % (f.__name__, (str(ex) or repr(ex))[:600]))
    finally:
        for p in TMP:
            shutil.rmtree(p, ignore_errors=True) if os.path.isdir(p) else os.path.exists(p) and os.remove(p)
    print('%d check(s), %s' % (len(CHECKS), 'all pass' if not fails else '%d FAIL' % fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
