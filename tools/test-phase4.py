"""Phase 4: the normalized model, its migration and the dual read.

    python tools/test-phase4.py

Every check reads the files as they are; none writes. The protected groups
(canonical data, phase records, evidence, discovery, scope, review, the
Phase 3.4 contract) are held to data/model/baseline.json, which stage M0
wrote at 91a5b8b.
"""
import collections
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import migration_lib as L  # noqa: E402

CHECKS = []


def check(f):
    CHECKS.append(f)
    return f


def baseline():
    return json.load(open(L.MODEL + 'baseline.json', encoding='utf-8'))


def same_group(name):
    b = baseline()['groups'][name]
    now = L.group_hashes(name)
    changed = sorted(f for f in set(b['files']) | set(now['files'])
                     if b['files'].get(f) != now['files'].get(f))
    assert not changed, '%s changed: %s' % (name, changed[:8])


# ---------------------------------------------------------------- M0

@check
def baseline_recorded_at_start():
    b = baseline()
    assert b['start_commit'] == '91a5b8b'
    assert set(b['groups']) == set(L.GROUPS), sorted(b['groups'])
    assert os.path.exists(L.ROOT + 'docs/PHASE-4-MIGRATION-BASELINE.md')


@check
def canonical_files_unchanged():
    same_group('canonical')


@check
def evidence_unchanged_no_v6():
    same_group('evidence')
    assert not os.path.exists(L.ROOT + 'data/evidence/decisions-v6.jsonl')


@check
def discovery_unchanged():
    same_group('discovery')


@check
def proposals_and_phase_records_unchanged():
    same_group('phase_records')


@check
def scope_review_and_contract_unchanged():
    for g in ('scope', 'review', 'phase34_model'):
        same_group(g)


@check
def phase34_contract_still_reproduced_by_its_generator():
    # test-phase34 skips this once a later commit exists (by its design);
    # Phase 4 builds on the contract, so it keeps the check running.
    import subprocess
    r = subprocess.run([sys.executable, '-I', L.ROOT + 'tools/build-phase34-model.py', '--check'],
                       cwd=L.ROOT, capture_output=True)
    assert r.returncode == 0, r.stdout.decode()[-300:]


@check
def baseline_counts_still_hold():
    import importlib.util
    spec = importlib.util.spec_from_file_location('b', L.ROOT + 'tools/phase4-baseline.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert m.counts() == baseline()['counts']


def slug(s):
    s = unicodedata.normalize('NFD', s)
    s = ''.join(ch for ch in s if not ('̀' <= ch <= 'ͯ')).lower()
    return re.sub(r'^-|-$', '', re.sub(r'[^a-z0-9]+', '-', s))


@check
def frozen_key_shapes():
    for name in ('BDX_FICHES', 'BDX_FIELD_SRC', 'BDX_FICHE_URL', 'BDX_RATINGS', 'BDX_CELLAR',
                 'BDX_SCORES'):
        bad = [k for k in L.g(name) if not re.fullmatch(r'[a-z0-9-]+\|\d{4}', k)]
        assert not bad, (name, bad[:3])
    for name in ('BDX_CUVEES', 'BDX_CUVEE_SRC', 'BDX_CUVEE_URL'):
        bad = [k for k in L.g(name) if not re.fullmatch(r'[a-z0-9-]+\|[a-z0-9-]+\|\d{4}', k)]
        assert not bad, (name, bad[:3])


@check
def frozen_sparse_id_rule():
    ids = set()
    for n in L.g('BDX_STEM_GCC'):
        ids.add('stem-' + slug(n))
    for n in L.g('BDX_POMEROL_OTHER'):
        ids.add('pomerol-' + slug(n))
    for tier in ('exceptionnel', 'superieur', 'bourgeois'):
        for row in L.g('BDX_CRU_BOURGEOIS')[tier]:
            ids.add('bourgeois-' + slug(row[0]))
    for row in L.g('BDX_CRU_ARTISAN')['current']:
        ids.add('artisan-' + slug(row[0]))
    view = {e['id'] for e in L.canonical_view()['estates'] if e['sparse']}
    assert ids == view and len(ids) == 298, (len(ids), len(view))


@check
def frozen_role_vocabulary_and_dash():
    roles = collections.Counter(w['role'] for x in L.g('BDX_CUVEE_WINES').values() for w in x)
    assert set(roles) == {'second', 'other'}, roles
    assert sum(1 for _, r in L.estate_files() if r.get('second') == '—') == 34


# ---------------------------------------------------------------- M1

import model_schema as S  # noqa: E402


@check
def m1_every_contract_entity_has_a_home():
    homed = {e for e, _, _ in S.LAYOUT.values()} | set(S.VIEWS)
    missing = set(S.ENTITIES) - homed
    assert not missing, sorted(missing)
    assert len({p for p, _ in S.MINTED.values()} | set(S.HASHED.values())) == \
        len(S.MINTED) + len(S.HASHED), 'two entities share an id prefix'


@check
def m1_validator_refuses_bad_rows():
    good = {'id': 'es_00001', 'name_status': 'KNOWN'}
    assert not S.check_row('Estate', good)
    assert S.check_row('Estate', dict(good, colour='red')), 'unknown field accepted'
    assert S.check_row('Estate', dict(good, name_status='MAYBE')), 'bad enum accepted'
    assert S.check_row('Estate', {'name_status': 'KNOWN'}), 'missing id accepted'
    rel = {'id': S.hid('EstateWineRelationship', 'x'), 'estate': 'es_00001', 'wine': 'wn_00001',
           'status': 'ESTABLISHED', 'kind': 'PRODUCED_BY', 'provenance': 'pv_1',
           'validity': S.UNKNOWN_VALIDITY}
    assert S.check_row('EstateWineRelationship', rel, {'es_00001', 'wn_00001'}), \
        'dangling provenance accepted'
    assert S.check_row('EstateWineRelationship', dict(rel, wine='es_00001')), \
        'an estate accepted where a wine is required'
    dated = dict(rel, validity={'valid_from': {'kind': 'EXACT', 'value': '2016', 'axis': 'CALENDAR',
                                               'precision': 'YEAR'}, 'valid_to': {'kind': 'OPEN'}})
    assert any('basis' in e for e in S.check_row('EstateWineRelationship', dated)), \
        'a date without a basis accepted'
    opened = dict(rel, validity={'valid_from': {'kind': 'OPEN'}, 'valid_to': {'kind': 'OPEN'}})
    assert S.check_row('EstateWineRelationship', opened), 'OPEN accepted as valid_from'


@check
def m1_storage_is_files_by_responsibility():
    import glob
    assert not [p for p in glob.glob(L.ROOT + '**/*', recursive=True)
                if p.endswith(('.db', '.sqlite', '.sqlite3')) and '/sources/' not in p.replace('\\', '/')]
    files = list(S.LAYOUT)
    assert len(files) == len(set(files))
    by_entity = collections.Counter(e for e, _, _ in S.LAYOUT.values())
    assert max(by_entity.values()) == 1, 'an entity split over two files'
    assert all(f.split('/')[0] in ('identity', 'state', 'document', 'observation',
                                   'reconciliation', 'canonical', 'cross') for f in files)
    attrs = open(L.ROOT + '.gitattributes', encoding='utf-8').read()
    assert 'data/model/** text eol=lf' in attrs


@check
def m1_raw_store_addresses_by_digest():
    import raw_store
    rows = L.sources_rows()['sheets']
    r = next(x for x in rows if x['folder'] == 'artisan-chateau-de-lauga'
             and x['file'] == 'Fiche-technique-LAUGA-ENG.pdf')
    p = raw_store.locate(sha1=r['sha1'], folder=r['folder'], file=r['file'])
    assert p and raw_store.digests(p)[0] == r['sha1']
    assert raw_store.locate(sha1='0' * 40, folder=r['folder'], file=r['file']) is None, \
        'a path returned for bytes it does not hold'
    a = json.loads(open(L.ROOT + 'data/discovery/artifacts.jsonl', encoding='utf-8').readline())
    data = raw_store.read_blob(a['sha256'])
    import hashlib
    assert data is not None and hashlib.sha256(data).hexdigest() == a['sha256']


# ---------------------------------------------------------------- the model, any stage

def T(rel):
    return L.read_table(rel)


def stage_at_least(st):
    import migrate
    cur = migrate.current_stage()
    return cur and migrate.STAGES.index(cur) >= migrate.STAGES.index(st)


@check
def model_rebuilds_byte_for_byte_deterministic():
    import subprocess
    r = subprocess.run([sys.executable, L.ROOT + 'tools/migrate.py', '--check'], cwd=L.ROOT,
                       capture_output=True)
    assert r.returncode == 0, r.stdout.decode()[-600:] + r.stderr.decode()[-600:]


@check
def model_rows_conform_to_contract_no_dangling_refs():
    import migrate
    m = migrate.Model()
    for rel in S.LAYOUT:
        for row in T(rel):
            m.tables[rel][m.key(rel, row)] = row
    errs = migrate.validate(m)
    assert not errs, errs[:5]
    man = json.load(open(L.MODEL + 'manifest.json', encoding='utf-8'))
    for rel, info in man['files'].items():
        assert info['rows'] == len(T(rel)), rel


# ---------------------------------------------------------------- M2

@check
def m2_every_canonical_estate_resolves_to_exactly_one_estate():
    im = [r for r in T('identity/identity-map.jsonl') if r['namespace'] == 'estate']
    by = collections.defaultdict(list)
    for r in im:
        by[r['legacy_key']].append(r)
    view = [e['id'] for e in L.canonical_view()['estates']]
    assert all(len(by[i]) == 1 and by[i][0]['status'] == 'ACTIVE' and by[i][0].get('stable_id')
               for i in view)
    ests = {r['id'] for r in T('identity/estates.jsonl')}
    assert len(ests) == 470 and {by[i][0]['stable_id'] for i in view} == ests


@check
def m2_every_legacy_estate_id_resolved_or_classified_unresolved():
    import mig_m2_identity as M2
    used = set(M2.legacy_estate_uses())
    im = {r['legacy_key']: r for r in T('identity/identity-map.jsonl') if r['namespace'] == 'estate'}
    missing = used - set(im)
    assert not missing, sorted(missing)[:5]
    unresolved = sorted(k for k, r in im.items() if not r.get('stable_id'))
    assert all(im[k]['status'] == 'AMBIGUOUS' and im[k].get('candidates') == [] for k in unresolved)
    assert unresolved == ['saint-julien'], unresolved
    f = [x for x in T('cross/findings.jsonl') if x['kind'] == 'IDENTITY_UNCERTAIN'
         and "'saint-julien'" in x['detail']]
    assert len(f) == 1


@check
def m2_name_derived_ids_mapped_not_recomputed():
    im = {(r['namespace'], r['legacy_key']): r for r in T('identity/identity-map.jsonl')}
    sparse = [e for e in L.canonical_view()['estates'] if e['sparse']]
    assert len(sparse) == 298
    entries = [r for k, r in im.items() if k[0] == 'estate-list-entry']
    assert len(entries) == 298
    for e in sparse:
        assert im[('estate', e['id'])]['stable_id']
    # Ids are opaque: none spells a legacy id or a name.
    for r in T('identity/estates.jsonl'):
        assert re.fullmatch(r'es_\d{5}', r['id'])


@check
def m2_filenames_never_resolve_by_first_match():
    pls = {r['id']: r for r in T('document/placements.jsonl')}
    n = collections.Counter()
    for r in T('document/legacy-references.jsonl'):
        arts = {pls[c].get('artifact') for c in r['candidates']}
        base = {pls[c]['locator']['value'].rsplit('/', 1)[-1] for c in r['candidates']}
        assert base <= {r['basename']}, r
        if r['resolution'] == 'ACTIVE':
            assert len(arts) == 1 and None not in arts, r
        else:
            assert len(arts) != 1 or None in arts, r
        n[r['resolution']] += 1
    assert n['AMBIGUOUS'] > 0 and n['ACTIVE'] > 0


@check
def m2_every_manifest_version_kept_one_placement_per_locator_artifact():
    sheets = L.sources_rows()['sheets']
    import mig_m2_identity as M2
    versions = collections.defaultdict(set)
    for r in sheets:
        versions[M2.sources_path(r)].add(r['sha1'])
    art = {r['legacy_key']: r['stable_id'] for r in T('identity/identity-map.jsonl')
           if r['namespace'] == 'artifact-by-sha1'}
    prov = {r['id']: r for r in T('cross/provenance.jsonl')}
    held = collections.defaultdict(set)
    seen = set()
    for p in T('document/placements.jsonl'):
        if p['locator']['kind'] != 'LOCAL_PATH':
            continue
        a = p.get('artifact') or prov[p['provenance']].get('artifact')
        key = (p['locator']['value'], p.get('artifact'), a)
        assert key not in seen
        seen.add(key)
        held[p['locator']['value']].add(a)
    multi = [pth for pth, v in versions.items() if len(v) > 1]
    assert len(multi) == 204
    for pth, v in versions.items():
        assert {art[s] for s in v} <= held[pth], pth


@check
def m2_provenance_failures_are_placements_without_artifact():
    pl = T('document/placements.jsonl')
    c = collections.Counter(p['status'] for p in pl if p['status'] in ('MISSING', 'NAME_MISMATCH'))
    assert c == {'MISSING': 103, 'NAME_MISMATCH': 20}, c
    assert all('artifact' not in p for p in pl if p['status'] in ('MISSING', 'NAME_MISMATCH'))
    targets = {f['target'] for f in T('cross/findings.jsonl') if f['kind'] == 'SOURCE_FAILURE'}
    assert {p['id'] for p in pl if p['status'] in ('MISSING', 'NAME_MISMATCH')} <= targets


@check
def m2_digest_joins_only_where_proven():
    import glob
    pairs = {}
    for p in glob.glob(L.ROOT + 'data/discovery/locations/*.jsonl'):
        for d in L.jsonl_lines(p):
            if d.get('sha1') and d.get('sha256'):
                pairs[d['sha1']] = d['sha256']
    import mig_m2_identity as M2
    versions = collections.defaultdict(set)
    for r in L.sources_rows()['sheets']:
        versions[M2.sources_path(r)].add(r['sha1'])
    reads = collections.defaultdict(set)
    for v in (4, 5):
        for d in L.jsonl_lines(L.ROOT + 'data/evidence/decisions-v%d.jsonl' % v):
            if (d.get('read') or {}).get('sha256'):
                reads[d['read']['path'].replace('\\', '/')].add(d['read']['sha256'])
    rule = {}
    for pth, vs in versions.items():
        if len(vs) == 1 and len(reads.get(pth, ())) == 1:
            rule[next(iter(vs))] = next(iter(reads[pth]))
    both = [a for a in T('identity/artifacts.jsonl') if 'sha1' in a and 'sha256' in a]
    assert both
    for a in both:
        assert pairs.get(a['sha1']) == a['sha256'] or rule.get(a['sha1']) == a['sha256'], a
    s256 = [a['sha256'] for a in T('identity/artifacts.jsonl') if 'sha256' in a]
    s1 = [a['sha1'] for a in T('identity/artifacts.jsonl') if 'sha1' in a]
    assert len(s256) == len(set(s256)) and len(s1) == len(set(s1)), 'one digest, two artifacts'


def main():
    only = sys.argv[1:]
    fails = 0
    n = 0
    for f in CHECKS:
        if only and f.__name__ not in only:
            continue
        n += 1
        try:
            f()
            print('ok   %s' % f.__name__)
        except Exception as ex:      # a check that cannot run is a failure, not a skip
            fails += 1
            print('FAIL %s: %s' % (f.__name__, str(ex)[:400]))
    print('%d check(s), %s' % (n, 'all pass' if not fails else '%d FAIL' % fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
