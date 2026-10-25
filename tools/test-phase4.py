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
