"""Generic artifact registration and evidence acceptance (tools/apply-artifact-registration-manifest.py,
tools/apply-evidence-acceptance-manifest.py; mig_m2_identity.artifact_registrar and
mig_m6_provenance.artifact_registration_placements).

    python tools/test-generic-evidence-registration.py

Read-only for the repository. Both production manifests are empty and must stay so; every registration runs on an
isolated copy of the model (BDX_MODEL_DIR) or in memory, every acceptance on an isolated copy of the evidence store
(v1-v5 linked, never written; v6 on copied). The material is real: M3.8's acquisition records and held bytes (89
documents the model does not hold, 19 it does, one PDF fetched from three URLs) and M3.9's review rows. The golden
cases are M3.10A's four registrations and M3.10B's four decisions, replayed through the generic mechanisms with the
historical inputs set aside in the copy only: the same artifacts, locators and decisions, M3.10A/B themselves
untouched. Negative cases alter an acquisition record, a review row or the store in memory or in a copy only.
"""
import contextlib
import copy
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import migration_lib as L  # noqa: E402

REG_TOOL = L.ROOT + 'tools/apply-artifact-registration-manifest.py'
ACC_TOOL = L.ROOT + 'tools/apply-evidence-acceptance-manifest.py'
M38 = 'data/audit/m3.8-acquisition-pilot.jsonl'
M39 = 'data/audit/m3.9-evidence-review.jsonl'
ESTATE, WINE, SECOND = 'es_00263', 'wn_00263', 'wn_00612'
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


RA = load(REG_TOOL, 'apply_artifact_registration_manifest_t')
EA = load(ACC_TOOL, 'apply_evidence_acceptance_manifest_t')
V, R11 = EA.V, EA.V.VR
import evidence_store as ST  # noqa: E402
PROD_STORE = (ST.DIR, ST.INDEX)
FP = EA.decider_fingerprint()
ITEMS = {r['n']: r for r in L.jsonl_lines(L.ROOT + M38) if r['record'] == 'item'}
M310A = [r for r in L.jsonl_lines(L.ROOT + 'data/audit/m3.10a-external-artifact-registration.jsonl')
         if r['record'] == 'registration']
M310B = {r['artifact']: r for r in L.jsonl_lines(L.ROOT + 'data/audit/m3.10b-evidence-decisions.jsonl')}
RVIEW = RA.View()
AVIEW = V.View()


# ---------------------------------------------------------------- registration rows, acquisitions, model copies

def reg(i, n, **kw):
    """A registration row for M3.8's item n, every fact the record's."""
    it = ITEMS[n]
    conf = RA.ACQUISITION_AUDITS[M38]
    r = {'registration_id': 'arm_%06d' % i, 'sha256': it['sha256'], 'bytes': it['bytes'],
         'media_type': it['content_type'], 'held_path': conf['held'] + it['sha256'], 'url': it['url'],
         'final_url': it['final_url'], 'http_status': it['status'], 'fetched_at': it['at'],
         'retrieval_method': conf['retrieval_method'], 'acquired_by': conf['acquired_by'], 'origin': RA.ORIGIN,
         'acquisition': {'audit': M38, 'row': 'm3.8:%d' % n}}
    if it.get('attributed_to'):
        r['source_relationship'] = it['attributed_to']
        r['source'] = it['attributed_to'].split(':')[1]
    r.update(kw)
    return r


class FixedAcquisitions(RA.Acquisitions):
    """The acquisition audits, with some records replaced (in memory only)."""

    def __init__(self, extra):
        super().__init__()
        self.extra = extra

    def get(self, audit, row):
        return copy.deepcopy(self.extra[(audit, row)]) if (audit, row) in self.extra else super().get(audit, row)


def r_errors(rows, acq=None, read_bytes=True):
    return RA.validate_manifest(rows, RVIEW, acq, None, read_bytes)[0]


def r_plan(rows, acq=None, read_bytes=True):
    e, ok = RA.validate_manifest(rows, RVIEW, acq, None, read_bytes)
    assert e == [], e
    return RA.plan_manifest(ok, RVIEW)


def unheld():
    """M3.8's retrieved, held items whose bytes the model does not hold, by item number."""
    have = set(RVIEW.index()['by_sha'])
    return sorted(n for n, it in ITEMS.items() if it['retrieval'] == 'OK' and it['sha256'] not in have
                  and os.path.exists(L.ROOT + 'sources/acquisition/m3.8/blobs/' + it['sha256']))


def isolated():
    """A copy of the committed model (HEAD) in a temporary directory."""
    if not BASE:
        d = tempfile.mkdtemp(prefix='gen-base-')
        for f in git('ls-tree', '-r', '--name-only', 'HEAD', 'data/model').decode().split():
            p = os.path.join(d, f[len('data/model/'):])
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'wb').write(git('show', 'HEAD:' + f))
        TMP.append(d)
        BASE.append(d)
    d = tempfile.mkdtemp(prefix='gen-')
    shutil.rmtree(d)
    shutil.copytree(BASE[0], d)
    TMP.append(d)
    return d


def snapshot(d):
    out = {}
    for base, _, names in os.walk(d):
        for n in names:
            out[os.path.relpath(os.path.join(base, n), d).replace('\\', '/')] = open(os.path.join(base, n), 'rb').read()
    return out


def manifest_file(rows):
    p = tempfile.mktemp(prefix='gen-manifest-', suffix='.jsonl')
    open(p, 'w', encoding='utf-8', newline='\n').write(''.join(L.dumps(r) + '\n' for r in rows))
    TMP.append(p)
    return p


def run(tool, *args, model=None, store=None, manifest=None):
    env = dict(os.environ)
    env.pop('BDX_MODEL_DIR', None)
    env.pop('BDX_EVIDENCE_DIR', None)
    if model:
        env['BDX_MODEL_DIR'] = model
    if store:
        env['BDX_EVIDENCE_DIR'] = store
    a = list(args) + (['--manifest', manifest_file(manifest)] if manifest is not None else [])
    return subprocess.run([sys.executable, tool] + a, cwd=L.ROOT, env=env, capture_output=True, text=True)


def table(d, rel):
    return [json.loads(x) for x in open(os.path.join(d, rel), encoding='utf-8').read().splitlines()]


# ---------------------------------------------------------------- acceptance rows, reviews, store copies

def acc(i=1, art='ar_037071', v=10, **kw):
    """An acceptance row for one of M3.10A's artifacts, asking what M3.10B asked of it, at version v."""
    m = M310B[art]
    r = {'acceptance_id': 'eam_%06d' % i, 'artifact_id': art, 'estate_id': ESTATE, 'wine_id': WINE,
         'vintage': m['vintage'], 'decision': 'ACCEPTED', 'evidence_version': v, 'reader': FP,
         'review': {'audit': M39, 'row': m['candidate']},
         'read': {'path': 'acquisition/m3.8/blobs/' + m['sha256'],
                  'extraction': 'acquisition/m3.8/extracted/%s.json' % m['sha256']},
         'document_name': m['url'].rsplit('/', 1)[1]}
    r.update(kw)
    return r


class FixedReviews(V.Reviews):
    """The review audits, with some rows replaced or added (in memory only)."""

    def __init__(self, extra):
        super().__init__()
        self.extra = extra

    def get(self, audit, r):
        return copy.deepcopy(self.extra[(audit, r)]) if (audit, r) in self.extra else super().get(audit, r)


def review_with(row='m3.9:4', **kw):
    rv = copy.deepcopy(V.Reviews().get(M39, row))
    rv.update(kw)
    return FixedReviews({(M39, row): rv})


class PatchedView(V.View):
    def __init__(self, **patch):
        super().__init__()
        self.patch = patch

    def index(self):
        ix = dict(super().index())
        for k, f in self.patch.items():
            ix[k] = f(ix[k])
        return ix


def store_copy(drop=()):
    """An isolated evidence store: the index (without the versions in `drop`), v1-v5 and the failure files linked
    (never written: the mechanism's versions start after v9), v6 on copied."""
    d = tempfile.mkdtemp(prefix='gen-store-')
    TMP.append(d)
    ix = json.load(open(PROD_STORE[1], encoding='utf-8'))
    for v in drop:
        ix['versions'].pop(str(v))
    for v, meta in ix['versions'].items():
        files = [p['file'] for p in meta['parts']] + ([meta['failures']['file']] if meta.get('failures') else [])
        for f in files:
            if int(v) <= 5:
                try:
                    os.link(PROD_STORE[0] + f, os.path.join(d, f))
                    continue
                except OSError:
                    pass
            shutil.copyfile(PROD_STORE[0] + f, os.path.join(d, f))
    open(os.path.join(d, 'index.json'), 'w', encoding='utf-8', newline='').write(
        json.dumps(ix, ensure_ascii=False, indent=1, sort_keys=True) + '\n')
    return d


@contextlib.contextmanager
def store(d, closed=None):
    """The store module (and the runners) pointed at copy d; `closed` replaces CLOSED_THROUGH."""
    was = EA.CLOSED_THROUGH
    ST.DIR, ST.INDEX = d.replace('\\', '/') + '/', d.replace('\\', '/') + '/index.json'
    if closed is not None:
        EA.CLOSED_THROUGH = closed
    try:
        yield
    finally:
        ST.DIR, ST.INDEX = PROD_STORE
        EA.CLOSED_THROUGH = was


def a_validate(rows, reviews=None, view=None):
    return EA.validate_manifest(rows, view or AVIEW, EA.Store(), reviews)


def a_errors(rows, reviews=None, view=None):
    return a_validate(rows, reviews, view)[0]


def a_plan(rows, reviews=None):
    st = EA.Store()
    e, res = EA.validate_manifest(rows, AVIEW, st, reviews)
    assert e == [], e
    return EA.plan_manifest(rows, res, st)


def accept(rows):
    """Plan and append, in the store currently in use; the plan."""
    e, plan = a_plan(rows)
    assert e == [], e
    EA.verify_plan(plan)
    EA.apply_plan(plan)
    return plan


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


# ---------------------------------------------------------------- registration

@check
def g01_new_artifact_is_minted_by_sha256_and_placed():
    """CREATE on an isolated copy: one artifact per digest after every existing id, its identity key, its URL
    placement in M3.10A's shape; no evidence, attribution or value; the rows then NOOP."""
    n = unheld()[0]
    rows = [reg(1, n)]
    plan = r_plan(rows)
    assert plan['actions'] == {'CREATE': 1, 'REUSE': 0, 'NOOP': 0, 'CONFLICT': 0} and plan['artifacts'] == [rows[0]['sha256']]
    d = isolated()
    before = snapshot(d)
    out = run(REG_TOOL, '--apply', model=d, manifest=rows)
    assert out.returncode == 0 and 'applied: 1 CREATE' in out.stdout, out.stdout + out.stderr
    after = snapshot(d)
    changed = sorted(rel for rel in after if before.get(rel) != after[rel])
    assert set(changed) - {rel for rel in changed if rel.startswith('derived/')} == set(RA.TABLES) | {'manifest.json'}, changed
    last = max(int(a['id'].split('_')[1]) for a in table(BASE[0], 'identity/artifacts.jsonl'))
    [art] = [a for a in table(d, 'identity/artifacts.jsonl') if a.get('sha256') == rows[0]['sha256']]
    assert art == {'id': 'ar_%06d' % (last + 1), 'sha256': rows[0]['sha256'], 'bytes': rows[0]['bytes'],
                   'bytes_available': True, 'media_type': rows[0]['media_type'], 'extraction_status': 'PENDING'}, art
    [im] = [r for r in table(d, 'identity/identity-map.jsonl') if r['legacy_key'] == rows[0]['sha256']]
    assert (im['namespace'], im['stable_id'], im['status']) == ('artifact-by-sha256', art['id'], 'ACTIVE')
    [pl] = [p for p in table(d, 'document/placements.jsonl') if p.get('artifact') == art['id']]
    assert pl['locator'] == {'kind': 'URL', 'value': rows[0]['url']} and pl['status'] == 'PRESENT'
    assert pl['observed']['valid_from']['value'] == rows[0]['fetched_at'][:10] and pl['retrieval_method'] == rows[0]['retrieval_method']
    for rel in ('document/attributions.jsonl', 'canonical/values.jsonl', 'observation/observations.jsonl',
                'identity/vintages.jsonl', 'identity/wines.jsonl', 'identity/estates.jsonl'):
        assert before[rel] == after[rel], rel
    out = run(REG_TOOL, '--plan', model=d, manifest=rows)
    assert '0 CREATE, 0 REUSE, 1 NOOP, 0 CONFLICT' in out.stdout, out.stdout + out.stderr
    out = run(REG_TOOL, '--apply', model=d, manifest=rows)
    assert out.returncode == 0 and 'nothing to apply' in out.stdout and snapshot(d) == after
    out = run(REG_TOOL, '--check', model=d, manifest=rows)
    assert out.returncode == 0 and '1 row(s) held' in out.stdout, out.stdout + out.stderr


@check
def g02_existing_content_is_reused_never_duplicated():
    """Bytes the crawl already holds: REUSE - the existing artifact gains the URL placement, no artifact is minted,
    and the existing artifact row is unchanged."""
    have = RVIEW.index()['by_sha']
    placed = RVIEW.index()['placed']
    n = sorted(k for k, it in ITEMS.items() if it['retrieval'] == 'OK' and it['sha256'] in have
               and it['url'] not in placed.get(have[it['sha256']], ()))[0]
    rows = [reg(1, n)]
    plan = r_plan(rows)
    assert plan['actions']['REUSE'] == 1 and plan['artifacts'] == [] and plan['placements'] == 1, plan
    d = isolated()
    out = run(REG_TOOL, '--apply', model=d, manifest=rows)
    assert out.returncode == 0 and 'applied: 0 CREATE, 1 REUSE' in out.stdout, out.stdout + out.stderr
    aid = have[rows[0]['sha256']]
    assert table(d, 'identity/artifacts.jsonl') == table(BASE[0], 'identity/artifacts.jsonl')
    assert table(d, 'identity/identity-map.jsonl') == table(BASE[0], 'identity/identity-map.jsonl')
    assert [p['locator']['value'] for p in table(d, 'document/placements.jsonl')
            if p.get('artifact') == aid and p['id'] == RA.placement_id(rows[0], aid)] == [rows[0]['url']]


@check
def g03_one_artifact_many_locations_and_the_same_location_twice():
    """A URL already placed (M3.10A's) is NOOP; one PDF fetched from three URLs is one artifact with three
    placements; the same bytes at the same URL twice is REJECT."""
    rows = [reg(i, r['m38_item']) for i, r in enumerate(M310A, 1)]
    plan = r_plan(rows)
    assert plan['actions'] == {'CREATE': 0, 'REUSE': 0, 'NOOP': 4, 'CONFLICT': 0}, plan['actions']
    shas = {}
    for n, it in ITEMS.items():
        if it['retrieval'] == 'OK':
            shas.setdefault(it['sha256'], set()).add(n)
    many = sorted(ns for s, ns in shas.items() if len({ITEMS[n]['url'] for n in ns}) == 3)[0]
    rows = [reg(i, n) for i, n in enumerate(sorted(many), 1)]
    plan = r_plan(rows)
    assert plan['actions']['CREATE'] == 3 and len(plan['artifacts']) == 1 and plan['placements'] == 3, plan
    d = isolated()
    out = run(REG_TOOL, '--apply', model=d, manifest=rows)
    assert out.returncode == 0, out.stdout + out.stderr
    [art] = [a['id'] for a in table(d, 'identity/artifacts.jsonl') if a.get('sha256') == rows[0]['sha256']]
    assert sorted(p['locator']['value'] for p in table(d, 'document/placements.jsonl') if p.get('artifact') == art) == \
        sorted(r['url'] for r in rows)
    e = r_errors([reg(1, sorted(many)[0]), reg(2, sorted(many)[0])])
    assert len(e) == 2 and all('registered 2 times' in x for x in e), e


@check
def g04_contradictory_immutable_metadata_is_a_conflict():
    """The model's artifact records another size or media type; or two rows give one sha256 two sizes: CONFLICT,
    refused before anything is written (by the runner and by the migration's hook)."""
    have = RVIEW.index()['by_sha']
    n = sorted(k for k, it in ITEMS.items() if it['retrieval'] == 'OK' and it['sha256'] in have
               and RVIEW.index()['artifacts'][have[it['sha256']]].get('bytes'))[0]
    it = dict(ITEMS[n], bytes=ITEMS[n]['bytes'] + 1)
    acq = FixedAcquisitions({(M38, 'm3.8:%d' % n): it})
    plan = r_plan([reg(1, n, bytes=it['bytes'])], acq, read_bytes=False)
    assert plan['actions']['CONFLICT'] == 1 and 'records bytes' in plan['rows'][0]['reason'], plan
    try:
        RA.verify_plan(plan)
        raise AssertionError('a conflict was not refused')
    except RA.Conflict:
        pass
    [a, b] = sorted(unheld())[:2]
    twin = dict(ITEMS[b], sha256=ITEMS[a]['sha256'], bytes=ITEMS[a]['bytes'] + 1)
    acq = FixedAcquisitions({(M38, 'm3.8:%d' % b): twin})
    rows = [reg(1, a), reg(2, b, sha256=twin['sha256'], bytes=twin['bytes'], held_path=reg(1, a)['held_path'])]
    plan = r_plan(rows, acq, read_bytes=False)
    assert plan['actions']['CONFLICT'] == 2, plan['actions']
    d = isolated()
    before = snapshot(d)
    out = run(REG_TOOL, '--apply', model=d, manifest=[reg(1, n, bytes=it['bytes'])])
    assert out.returncode != 0 and 'nothing was written' in (out.stdout + out.stderr) and snapshot(d) == before


@check
def g05_deterministic_ids_plan_and_rebuild():
    """The plan is the same for any row order; ids follow sha256 order after every existing id; the migration
    rebuilds what --apply wrote, from scratch and with the registry (in a subprocess)."""
    ns = unheld()[:10]
    rows = [reg(i, n) for i, n in enumerate(ns, 1)]
    p1 = r_plan(rows)
    shuffled = rows[:]
    random.Random(7).shuffle(shuffled)
    assert L.dumps(r_plan(shuffled)) == L.dumps(p1)
    d = isolated()
    out = run(REG_TOOL, '--apply', model=d, manifest=rows)
    assert out.returncode == 0, out.stdout + out.stderr
    last = max(int(a['id'].split('_')[1]) for a in table(BASE[0], 'identity/artifacts.jsonl'))
    by = {a['sha256']: a['id'] for a in table(d, 'identity/artifacts.jsonl') if a.get('sha256')}
    assert [by[s] for s in p1['artifacts']] == ['ar_%06d' % (last + i) for i in range(1, len(p1['artifacts']) + 1)]
    out = subprocess.run([sys.executable, os.path.abspath(__file__), '--rebuild', manifest_file(rows)], cwd=L.ROOT,
                         env=dict(os.environ, BDX_MODEL_DIR=d), capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout.strip().endswith('rebuild: all pass'), (out.stdout + out.stderr)[-1500:]


@check
def g06_the_placement_provenance_names_the_registration():
    n = unheld()[0]
    r = reg(1, n)
    d = isolated()
    assert run(REG_TOOL, '--apply', model=d, manifest=[r]).returncode == 0
    prov = {p['id']: p for p in table(d, 'cross/provenance.jsonl')}
    [pl] = [p for p in table(d, 'document/placements.jsonl') if (prov[p['provenance']].get('actor') == RA.ACTOR)]
    p = prov[pl['provenance']]
    assert p['kind'] == 'DOCUMENT' and p['artifact'] == pl['artifact']
    cs = p['code_state']
    assert cs == {'stream': RA.STREAM, 'runner': RA.RUNNER, 'manifest': RA.MANIFEST, 'registration_id': 'arm_000001',
                  'acquisition': r['acquisition'], 'url': r['url'], 'fetched_at': r['fetched_at'],
                  'http_status': r['http_status'], 'acquired_by': 'M3.8', 'origin': RA.ORIGIN,
                  'correspondence': 'the bytes the acquisition fetched (sha256)'}, cs
    man = json.load(open(os.path.join(d, 'manifest.json'), encoding='utf-8'))
    assert man['stats']['M2'][RA.ARTIFACT_STAT] == 1 and man['stats']['M6'][RA.PLACEMENT_STAT] == 1


@check
def g07_external_acquisition_stays_distinguishable_from_the_crawl():
    """Only EXTERNAL_ACQUISITION is registered; the placement names the acquisition's retrieval, never the crawl's;
    the discovery manifest and its location logs are not written."""
    n = unheld()[0]
    for origin in ('DISCOVERY_CRAWL', None, 'external'):
        e = r_errors([reg(1, n, origin=origin)])
        assert len(e) == 1 and 'only EXTERNAL_ACQUISITION' in e[0], e
    assert reg(1, n)['retrieval_method'] != 'discovery crawl (discover/1.0)'
    assert not git('status', '--porcelain', '--', 'data/discovery').strip()


@check
def g08_no_fact_is_invented():
    """Every stated fact must be the acquisition record's; a relationship only where the record attributes one; no
    identity field; the held bytes must hash to the row. The migration's hook refuses what the runner refuses."""
    n = sorted(k for k in unheld() if ITEMS[k].get('attributed_to'))[0]
    for change in ({'url': ITEMS[n]['url'] + '?x'}, {'fetched_at': '2026-10-28T00:00:00Z'}, {'http_status': 203},
                   {'final_url': 'https://example.org/x.pdf'}, {'acquired_by': 'M3.10A'},
                   {'retrieval_method': 'discovery crawl (discover/1.0)'}, {'media_type': 'text/html'},
                   {'held_path': 'sources/acquisition/m3.8/blobs/x'}):
        e = r_errors([reg(1, n, **change)])
        assert len(e) == 1 and 'not what the acquisition record establishes' in e[0], (change, e)
    e = r_errors([reg(1, n, source_relationship='m37:sr_00001:es_00001', source='sr_00001')])
    assert len(e) == 1 and 'attributes the fetch to' in e[0], e
    bare = sorted(k for k in unheld() if not ITEMS[k].get('attributed_to'))[0]
    e = r_errors([reg(1, bare, source_relationship=reg(1, n)['source_relationship'], source=reg(1, n)['source'])])
    assert len(e) == 1 and 'attributes the fetch to None' in e[0], e
    for extra in ({'estate': ESTATE}, {'wine': WINE}, {'vintage': 2024}):
        e = r_errors([reg(1, n, **extra)])
        assert len(e) == 1 and 'names no estate, wine or vintage' in e[0], e
    e = r_errors([reg(1, n, acquisition={'audit': M38, 'row': 'm3.8:9999'})])
    assert len(e) == 1 and 'no acquisition record' in e[0], e
    other = unheld()[1]
    acq = FixedAcquisitions({(M38, 'm3.8:%d' % n): dict(ITEMS[n], sha256=ITEMS[other]['sha256'])})
    e = RA.validate_manifest([reg(1, n, sha256=ITEMS[other]['sha256'], held_path=reg(1, other)['held_path'])],
                             RVIEW, acq)[0]
    assert len(e) == 1 and 'does not hash to the row' in e[0], e
    RA.PATH[0] = manifest_file([reg(1, n, url=ITEMS[n]['url'] + '?x')])
    try:
        RA._hook_rows()
        raise AssertionError('the hook took an invented fact')
    except SystemExit as x:
        assert 'not what the acquisition record establishes' in str(x)
    finally:
        RA.PATH[0] = L.ROOT + RA.MANIFEST


# ---------------------------------------------------------------- evidence acceptance

@check
def g09_g10_valid_acceptance_records_the_exact_identity():
    """A reviewed row of M3.9 accepted at the next version: APPEND, superseding M3.10B's answer to the same question;
    the decision asks exactly that estate's grand-vin question for that year, on the artifact's own bytes."""
    with store(store_copy()):
        plan = accept([acc()])
        [it] = plan['rows']
        assert (it['action'], it['reason']) == ('APPEND', 'supersedes v9 (ACCEPTED)'), it
        [d] = list(ST.iter_rows([10]))
        m = M310B['ar_037071']
        assert d['ctx'] == {'estate': 'durfort-vivens', 'folder': 'acquisition:' + m['sha256'], 'wine': None,
                            'vintage': 2024, 'target_wine': m['wine_name'], 'target_role': 'grand',
                            'target_vintage': 2024, 'evaluated_as': '%s, vintage 2024' % m['wine_name']}, d['ctx']
        assert d['read'] == {'path': 'acquisition/m3.8/blobs/' + m['sha256'], 'sha256': m['sha256'], 'bytes': 1175573,
                             'extraction': 'acquisition/m3.8/extracted/%s.json' % m['sha256']}
        assert (d['decision'], d['code'], d['kind'], d['reader'], d['v']) == ('ACCEPTED', 'ACCEPTED', 'guard', FP, 10)
        assert d['evidence'][:2] == ['M34A rule: ' + m['supporting_evidence'],
                                     'whose_sheet with year=2024, is_second=False: ACCEPTED']
        assert 'm3.9:4' in d['evidence'][2] and 'eam_000001' in d['evidence'][2] and ST.provenance_problem(d) is None
        assert EA.check(a_plan([acc()])[1], EA.Store()) == []


@check
def g11_g12_g13_wrong_estate_wine_or_vintage():
    e = a_errors([acc(estate_id='es_00277')])
    assert len(e) == 1 and 'does not belong to estate es_00277' in e[0], e
    e = a_errors([acc(wine_id=SECOND)])
    assert len(e) == 1 and 'not the grand vin' in e[0], e
    e = a_errors([acc(vintage=2023)])
    assert len(e) == 1 and 'the reviewed row is for es_00263 wn_00263 2024' in e[0], e
    e = a_errors([acc(), acc(2, art='ar_037069', review={'audit': M39, 'row': 'm3.9:4'})])
    assert any('read other bytes' in x for x in e), e


@check
def g14_ambiguous_or_unsettled_identity():
    for patch, why in (({'ambiguous': lambda s: s | {WINE}}, 'ambiguous identity'),
                       ({'open_estates': lambda s: s | {ESTATE}}, 'open identity finding'),
                       ({'transitions': lambda s: s | {WINE}}, 'settled current name')):
        e = a_errors([acc()], view=PatchedView(**patch))
        assert len(e) == 1 and why in e[0], e
    e = a_errors([acc()], reviews=review_with(claims=V.Reviews().get(M39, 'm3.9:4')['claims'] * 2))
    assert len(e) == 1 and 'maps 2 wine(s)' in e[0], e


@check
def g15_a_rejected_reader_result_is_not_accepted():
    for kw, why in (({'disposition': 'HOLD'}, 'did not map it'), ({'category': 'ESTATE_VINTAGE_ONLY'}, 'did not map it'),
                    ({'identity_source': 'url'}, 'own text'), ({'vintage_evidence': 'file name 2024'}, 'not stated')):
        e = a_errors([acc()], reviews=review_with(**kw))
        assert len(e) == 1 and why in e[0], (kw, e)
    rv = copy.deepcopy(V.Reviews().get(M39, 'm3.9:4'))
    rv['claims'][0]['reader'] = {'code': 'WRONG_WINE', 'decision': 'REFUSED', 'why': 'x'}
    e = a_errors([acc()], reviews=FixedReviews({(M39, 'm3.9:4'): rv}))
    assert len(e) == 1 and 'did not accept' in e[0], e
    e = a_errors([acc(decision='REFUSED')])
    assert len(e) == 1 and "this mechanism records ['ACCEPTED']" in e[0], e


@check
def g16_g17_missing_artifact_and_wrong_bytes():
    e = a_errors([acc(artifact_id='ar_999999')])
    assert len(e) == 1 and 'does not exist' in e[0], e
    other = M310B['ar_037070']['sha256']
    e = a_errors([acc(read={'path': 'acquisition/m3.8/blobs/' + other})])
    assert len(e) == 1 and 'is not the bytes of artifact ar_037071' in e[0], e
    e = a_errors([acc(read={'path': 'acquisition/m3.8/blobs/' + 'f' * 64})])
    assert len(e) == 1 and 'is missing' in e[0], e
    e = a_errors([acc(read={'path': 'fiches/x/y.pdf'})])
    assert len(e) == 1 and 'held stores' in e[0], e
    e = a_errors([acc(document_name='ftdv2014eng.pdf')])
    assert len(e) == 1 and 'not placed under the name' in e[0], e


@check
def g18_wrong_reader_or_audit_reference():
    e = a_errors([acc(review={'audit': M39, 'row': 'm3.9:99'})])
    assert len(e) == 1 and 'no reviewed reader row' in e[0], e
    e = a_errors([acc(review={'audit': 'data/audit/m3.6a-held-document-review.jsonl', 'row': 'x:1'})])
    assert len(e) == 1 and 'has no recorded check' in e[0], e
    e = a_errors([acc(reader='not-a-fingerprint')])
    assert len(e) == 1 and 'decider fingerprint' in e[0], e
    with store(store_copy()):
        e, plan = a_plan([acc(reader='0' * 12)])
        assert len(e) == 1 and 'the decider is now %s' % FP in e[0], e
        accept([acc()])
        e = a_errors([acc(2, art='ar_037070', reader='0' * 12)])
        assert len(e) == 1 and 'a changed reader is a new version' in e[0], e


@check
def g19_stale_and_superseded_decisions():
    """A row asking a version older than its question's latest answer is stale; V1 and M3.11 refuse a superseded
    decision as they did."""
    with store(store_copy()):
        accept([acc(1, art='ar_037070')])                          # v10: the 2021 certificate
        accept([acc(2, v=11)])                                     # v11: the 2024 brief, superseding v9
        e, plan = a_plan([acc(3, v=10)])
        assert len(e) == 1 and 'stale: the question is answered at v11' in e[0], e
        ev = R11.Evidence({9})
        try:
            V.check_decision(M310B['ar_037071']['evidence_decision'], 9, AVIEW.index()['artifacts']['ar_037071'],
                             'durfort-vivens', M310B['ar_037071']['wine_name'], 2024, ev)
            raise AssertionError('V1 took a superseded decision')
        except V.Invalid as x:
            assert 'superseded by version 11' in str(x)


@check
def g20_append_only_versioning():
    """v1-v9 and their index entries byte for byte after appends; a closed version, or one beyond the next, is
    refused; the latest answer is the highest version, the earlier one kept."""
    d = store_copy()
    files = sorted(f for f in os.listdir(d) if f != 'index.json')
    before = {f: sha(os.path.join(d, f)) for f in files}
    ix0 = json.load(open(os.path.join(d, 'index.json'), encoding='utf-8'))['versions']
    with store(d):
        e = a_errors([acc(v=9)])
        assert len(e) == 1 and 'v1-v9 are closed' in e[0], e
        e = a_errors([acc(v=11)])
        assert len(e) == 1 and 'neither the store\'s newest (v9) nor the next' in e[0], e
        accept([acc()])
        accept([acc(2, art='ar_037070', v=10)])                    # the newest version takes more rows
        e = a_errors([acc(3, art='ar_037069', v=12)])
        assert len(e) == 1 and 'neither the store\'s newest (v10)' in e[0], e
        assert {f: sha(os.path.join(d, f)) for f in files} == before
        ix = json.load(open(os.path.join(d, 'index.json'), encoding='utf-8'))['versions']
        assert {k: x for k, x in ix.items() if k != '10'} == ix0 and ix['10']['rows'] == 2
        st = EA.Store()
        k9 = M310B['ar_037071']['evidence_decision']
        assert k9 in st.by_key and st.latest[L.dumps(json.loads(k9)[:-1])]['v'] == 10
        assert ST.verify() == []


@check
def g21_g22_exact_duplicate_is_noop_contradiction_is_conflict():
    d = store_copy()
    with store(d):
        accept([acc()])
        e, plan = a_plan([acc()])
        assert e == [] and plan['actions'] == {'APPEND': 0, 'NOOP': 1, 'CONFLICT': 0}, plan['actions']
        out = run(ACC_TOOL, '--apply', store=d, manifest=[acc()])
        assert out.returncode == 0 and 'nothing to apply' in out.stdout, out.stdout + out.stderr
        e, plan = a_plan([acc(2, art='ar_037070')])
        refused = dict(plan['rows'][0]['decision'], decision='REFUSED', code='WRONG_WINE')
        import provenance as PV
        ST.append([dict(refused, git=PV.git_state(L.ROOT))], 10)
        v10 = sha(os.path.join(d, 'decisions-v10.jsonl'))
        e, plan = a_plan([acc(2, art='ar_037070')])
        assert e == [] and plan['actions']['CONFLICT'] == 1 and 'code, decision' in plan['rows'][0]['reason'], plan
        out = run(ACC_TOOL, '--apply', store=d, manifest=[acc(2, art='ar_037070')])
        assert out.returncode != 0 and 'nothing was written' in out.stdout + out.stderr, out.stdout + out.stderr
        assert sha(os.path.join(d, 'decisions-v10.jsonl')) == v10
        out = run(ACC_TOOL, '--check', store=d, manifest=[acc()])
        assert out.returncode != 0 and 'that no manifest row names' in out.stdout + out.stderr, out.stdout + out.stderr


# ---------------------------------------------------------------- integration

@check
def g23_m310a_golden_artifacts():
    """M3.10A's four registrations as generic rows, built with M3.10A's own input set aside (in a subprocess, in a
    copy): the same artifacts, ids, identity keys and locators; the same placements but for their id and provenance;
    the provenance's facts the same."""
    d = isolated()
    out = subprocess.run([sys.executable, os.path.abspath(__file__), '--golden-registration', d], cwd=L.ROOT,
                         env=dict(os.environ, BDX_MODEL_DIR=d), capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout.strip().endswith('golden registration: all pass'), \
        (out.stdout + out.stderr)[-2000:]


@check
def g24_m310b_golden_decisions():
    """M3.10B's four acceptances replayed on a store without v9: v9 again, the same four row keys, every field the
    same but the git state and the line naming the operation; v1-v8 byte for byte."""
    d = store_copy(drop=(9,))
    rows = [acc(i, art=a, v=9) for i, a in enumerate(sorted(M310B), 1)]
    before = {f: sha(os.path.join(d, f)) for f in os.listdir(d) if f != 'index.json'}
    with store(d, closed=8):
        plan = accept(rows)
        assert plan['actions'] == {'APPEND': 4, 'NOOP': 0, 'CONFLICT': 0}
        got = {EA.M6.row_key(x): x for x in ST.iter_rows([9])}
    want = {EA.M6.row_key(x): x for x in ST.iter_rows([9])}
    assert set(got) == set(want) == {m['evidence_decision'] for m in M310B.values()}
    for k in want:
        a, b = dict(want[k]), dict(got[k])
        assert {x for x in set(a) | set(b) if a.get(x) != b.get(x)} == {'evidence', 'git'}, k
        [m] = [m for m in M310B.values() if m['evidence_decision'] == k]
        assert a['evidence'][:2] == b['evidence'][:2], k
        assert m['candidate'] in a['evidence'][2] and m['candidate'] in b['evidence'][2] and m['artifact'] in b['evidence'][2]
    ix = json.load(open(os.path.join(d, 'index.json'), encoding='utf-8'))['versions']
    prod = json.load(open(PROD_STORE[1], encoding='utf-8'))['versions']
    assert ix['9']['readers'] == prod['9']['readers'] and ix['9']['rows'] == prod['9']['rows'] == 4
    assert {k: x for k, x in ix.items() if k != '9'} == {k: x for k, x in prod.items() if k != '9'}
    assert {f: sha(os.path.join(d, f)) for f in before} == before


@check
def g25_g26_v1_and_m311_consume_a_generic_decision():
    """V1, unchanged, takes a generically recorded decision: the replayed v9 (NOOP, as production), and a v10
    answer (ATTRIBUTION_ONLY: its existence attribution names the new decision); M3.11, unchanged, then takes v10."""
    d9 = store_copy(drop=(9,))
    with store(d9, closed=8):
        accept([acc(i, art=a, v=9) for i, a in enumerate(sorted(M310B), 1)])
        by = {}
        for m in M310B.values():
            by.setdefault(m['vintage'], []).append(m)
        rows = [{'manifest_id': 'vcm_%06d' % n, 'estate_id': ESTATE, 'wine_id': WINE, 'vintage': y,
                 'artifact_ids': sorted(m['artifact'] for m in ms), 'evidence_version': 9,
                 'evidence_decisions': {m['artifact']: m['evidence_decision'] for m in ms},
                 'review': {m['artifact']: {'audit': M39, 'row': m['candidate']} for m in ms},
                 'creation_class': 'EXPLICIT_DOCUMENT_TEXT'} for n, (y, ms) in enumerate(sorted(by.items()), 1)]
        e, res = V.validate_manifest(rows, AVIEW, R11.Evidence({9}))
        assert e == [], e
        assert V.plan_manifest(rows, res, AVIEW)['actions'] == {'CREATE': 0, 'ATTRIBUTION_ONLY': 0, 'NOOP': 3, 'CONFLICT': 0}
    with store(store_copy()):
        plan = accept([acc()])
        key = plan['rows'][0]['key']
        ev = R11.Evidence({10})
        row = {'manifest_id': 'vcm_000001', 'estate_id': ESTATE, 'wine_id': WINE, 'vintage': 2024,
               'artifact_ids': ['ar_037071'], 'evidence_version': 10, 'evidence_decisions': {'ar_037071': key},
               'review': {'ar_037071': {'audit': M39, 'row': 'm3.9:4'}}, 'creation_class': 'EXPLICIT_DOCUMENT_TEXT'}
        import migrate
        m = migrate.Model()
        for rel in ('identity/estates.jsonl', 'identity/wines.jsonl', 'state/estate-wine.jsonl', 'identity/vintages.jsonl',
                    'identity/artifacts.jsonl', 'document/attributions.jsonl', 'cross/provenance.jsonl',
                    'identity/names.jsonl', 'identity/identity-map.jsonl', 'cross/findings.jsonl',
                    'identity/transitions.jsonl', 'state/vintage-statements.jsonl', 'canonical/values.jsonl',
                    'observation/observations.jsonl', 'reconciliation/reconciliations.jsonl'):
            for r in L.read_table(rel):
                m.add(rel, r)
        view = V.View(m.rows)
        e, res = V.validate_manifest([row], view, ev)
        assert e == [], e
        plan = V.plan_manifest([row], res, view)
        assert plan['rows'][0]['action'] == 'ATTRIBUTION_ONLY', plan['rows'][0]
        assert V.apply_plan(m, plan, shells=False) == ([], 1)
        values = [dict(r, evidence_version=10) for r in L.jsonl_lines(L.ROOT + R11.MANIFEST) if r['vintage'] == 2024]
        assert len(values) == 5
        e, res = R11.validate_manifest(values, R11.View(m.rows), ev)
        assert e == [], e
        p = R11.plan_manifest(values, res, R11.View(m.rows))
        assert p['actions'] == {'APPLY': 0, 'NOOP_EXISTING_IDENTICAL': 5, 'CONFLICT': 0}, p['actions']
        old = [r for r in L.jsonl_lines(L.ROOT + R11.MANIFEST) if r['vintage'] == 2024]
        e = R11.validate_manifest(old, R11.View(m.rows), R11.Evidence({9}))[0]
        assert len(e) == 5 and all('superseded by version 10' in x for x in e), e
    assert not git('status', '--porcelain', '--', 'data/model').strip()


@check
def g27_historical_evidence_byte_for_byte():
    assert not git('status', '--porcelain', '--', 'data/evidence').strip()
    assert not git('diff', '--stat', 'HEAD', '--', 'data/evidence').strip()
    assert ST.DIR == PROD_STORE[0] and ST.verify() == [] and ST.versions() == list(range(1, 10))


@check
def g28_no_production_data_changed():
    for p in (RA.MANIFEST, EA.MANIFEST):
        assert os.path.getsize(L.ROOT + p) == 0, p
    out = run(REG_TOOL, '--check-all')
    assert out.returncode == 0 and '0 row(s) held' in out.stdout and 'model at M7 rebuilds byte for byte' in out.stdout \
        and 'data/app is the model, byte for byte' in out.stdout, out.stdout + out.stderr
    out = run(ACC_TOOL, '--check')
    assert out.returncode == 0 and '0 row(s) held by the store' in out.stdout, out.stdout + out.stderr
    assert run(REG_TOOL, '--plan').stdout.startswith('0 manifest row(s)')
    assert run(ACC_TOOL, '--plan').stdout.startswith('0 manifest row(s)')
    m = json.load(open(L.MODEL + 'manifest.json', encoding='utf-8'))
    assert RA.ARTIFACT_STAT not in m['stats'].get('M2', {}) and RA.PLACEMENT_STAT not in m['stats'].get('M6', {})
    assert not git('status', '--porcelain', '--', 'data/model', 'data/app', 'data/evidence', 'data/discovery').strip()
    assert not git('diff', '--stat', 'HEAD', '--', 'data/model', 'data/app', 'data/evidence').strip()


# ---------------------------------------------------------------- the subprocesses

def rebuild(manifest):
    """Run with BDX_MODEL_DIR=d (a copy --apply wrote): the migration fed `manifest`, from scratch and with the
    registry, renders exactly the copy's files."""
    import mig_m2_identity as M2
    import migrate
    M2.artifact_registrar().PATH[0] = manifest
    for reg_ in (None, migrate.load_registry()):
        files = migrate.render(migrate.run('M7', reg_), 'M7')
        for rel, b in files.items():
            assert open(L.MODEL + rel, 'rb').read() == b, ('the rebuild differs from --apply', rel, reg_ is None)
    print('rebuild: all pass')


def golden_registration(d):
    """Run with BDX_MODEL_DIR=d (a copy of the committed model): M3.10A's input set aside, its four documents
    registered through the generic manifest instead."""
    import mig_m2_identity as M2
    import migrate
    assert L.MODEL.rstrip('/') == d.replace('\\', '/').rstrip('/')
    rows = [reg(i, r['m38_item']) for i, r in enumerate(M310A, 1)]
    for r, g in zip(rows, M310A):
        for k in ('sha256', 'bytes', 'media_type', 'url', 'final_url', 'http_status', 'fetched_at', 'retrieval_method',
                  'acquired_by', 'origin', 'source', 'source_relationship'):
            assert r[k] == g[k], (k, r[k], g[k])
        assert r['held_path'] == g['acquisition_path']
    M2.external_registrations = lambda: {}
    M2.artifact_registrar().PATH[0] = manifest_file(rows)
    head = snapshot(d)
    for reg_ in (None, migrate.load_registry()):
        files = migrate.render(migrate.run('M7', reg_), 'M7')
        differ = sorted(rel for rel, b in files.items() if head[rel] != b)
        assert differ == ['cross/provenance.jsonl', 'document/placements.jsonl', 'manifest.json'], differ
        old_pl, new_pl = ({json.dumps(json.loads(x), sort_keys=True) for x in b.decode().splitlines()}
                          for b in (head['document/placements.jsonl'], files['document/placements.jsonl']))
        gone_, made = [json.loads(x) for x in old_pl - new_pl], [json.loads(x) for x in new_pl - old_pl]
        assert len(gone_) == len(made) == 4
        prov_old = {p['id']: p for p in map(json.loads, head['cross/provenance.jsonl'].decode().splitlines())}
        prov_new = {p['id']: p for p in map(json.loads, files['cross/provenance.jsonl'].decode().splitlines())}
        by = {(p['artifact'], p['locator']['value']): p for p in made}
        for p in gone_:
            q = by[(p['artifact'], p['locator']['value'])]
            strip = lambda x: {k: v for k, v in x.items() if k not in ('id', 'provenance', 'observed')}
            assert strip(p) == strip(q), (p, q)
            for side in ('valid_from', 'valid_to'):
                a, b = dict(p['observed'][side]), dict(q['observed'][side])
                assert (a.pop('basis'), b.pop('basis')) == (p['provenance'], q['provenance']) and a == b
            a, b = prov_old[p['provenance']], prov_new[q['provenance']]
            assert (a['kind'], a['artifact']) == (b['kind'], b['artifact']) == ('DOCUMENT', p['artifact'])
            for k in ('url', 'fetched_at', 'http_status', 'acquired_by', 'origin'):
                assert a['code_state'][k] == b['code_state'][k], k
            assert a['actor'] == 'tools/m310a-register.py' and b['actor'] == RA.ACTOR
        assert set(prov_old) - set(prov_new) == {p['provenance'] for p in gone_}
        assert set(prov_new) - set(prov_old) == {q['provenance'] for q in made}
        mo, mn = json.loads(head['manifest.json']), json.loads(files['manifest.json'])
        assert mn['stats']['M6'].pop('M3.10A placements (externally acquired documents)') == 0
        assert mo['stats']['M6'].pop('M3.10A placements (externally acquired documents)') == 4
        assert mn['stats']['M6'].pop(RA.PLACEMENT_STAT) == 4 and mn['stats']['M2'].pop(RA.ARTIFACT_STAT) == 4
        for x in (mo, mn):
            for rel in ('cross/provenance.jsonl', 'document/placements.jsonl'):
                x['files'][rel].pop('sha256')
        assert mo == mn
    print('golden registration: all pass')


def main():
    fails = 0
    try:
        if '--rebuild' in sys.argv:
            return rebuild(sys.argv[sys.argv.index('--rebuild') + 1])
        if '--golden-registration' in sys.argv:
            return golden_registration(sys.argv[sys.argv.index('--golden-registration') + 1])
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
