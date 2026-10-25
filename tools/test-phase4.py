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

_tables = {}


def T(rel):
    # The model's files do not change during a run; read each once.
    if rel not in _tables:
        _tables[rel] = L.read_table(rel)
    return _tables[rel]


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
         and x['detail'] == "legacy estate id 'saint-julien' resolves to no estate"]
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


# ---------------------------------------------------------------- M3

_imaps = {}


def imap(ns):
    if ns not in _imaps:
        _imaps[ns] = {r['legacy_key']: r for r in T('identity/identity-map.jsonl')
                      if r['namespace'] == ns}
    return _imaps[ns]


@check
def m3_grand_vins_only_where_supported():
    import mig_m3_grand as M3
    sup = M3.support(L.canonical_view())
    gv = imap('grand-vin')
    est = imap('estate')
    for lid, r in est.items():
        if not r.get('stable_id'):
            assert lid not in gv
        elif lid in sup:
            assert lid in gv and gv[lid]['stable_id'].startswith('wn_'), lid
        else:
            assert lid not in gv, 'a grand vin with no support: %s' % lid
    unsupported = sorted(set(est) - set(sup) - {'saint-julien'})
    assert len(unsupported) == 12 and all(i.startswith('pomerol-') for i in unsupported), unsupported


@check
def m3_every_estate_vintage_key_has_a_grand_vin_or_is_unresolved():
    gv = imap('grand-vin')
    est = imap('estate')
    for name in ('BDX_FICHES', 'BDX_FIELD_SRC', 'BDX_FICHE_URL', 'BDX_RATINGS', 'BDX_CELLAR',
                 'BDX_SCORES'):
        for k in L.g(name):
            lid = k.split('|')[0]
            assert lid in gv or not est[lid].get('stable_id'), (name, k)


@check
def m3_classification_on_wines_editorial_on_estates():
    mem = T('state/classification-memberships.jsonl')
    assert all(r['wine'].startswith('wn_') for r in mem)
    eds = {r['id']: r for r in T('state/classification-editions.jsonl')}
    grand = {r['stable_id'] for r in imap('grand-vin').values()}
    n = collections.Counter(eds[r['edition']]['label'].split(' (as ')[0] for r in mem
                            if r['wine'] in grand)
    whites = {r['stable_id'] for r in imap('graves-white').values() if r.get('stable_id')}
    assert {r['wine'] for r in mem if r['wine'] not in grand} == whites and len(whites) == 6
    want = {'Classification of 1855': 61, 'Sauternes & Barsac 1855': 27, 'Saint-Émilion 2022': 85,
            'Crus Classés de Graves': 16, 'Crus Bourgeois du Médoc 2025': 170,
            'Crus Artisans du Médoc': 34}
    assert dict(n) == want, dict(n)
    editorial = {c['id'] for c in L.g('BDX_CLASSIFICATIONS') if c.get('editorial')}
    assert {r['collection'] for r in T('state/editorial-memberships.jsonl')} <= editorial
    assert not any(r['label'].startswith(tuple(c['name'] for c in L.g('BDX_CLASSIFICATIONS')
                                                if c.get('editorial'))) for r in eds.values())
    bodies = {r['name'] for r in T('identity/parties.jsonl')}
    uni = json.load(open(L.ROOT + 'data/scope/authoritative-universe.json', encoding='utf-8'))
    assert bodies == {s['body'] for s in uni['systems']}, 'a body not named by the sources'


@check
def m3_wine_type_never_promoted_from_unknown():
    files = {r['id']: r for _, r in L.estate_files()}
    gv = imap('grand-vin')
    wines = {r['id']: r for r in T('identity/wines.jsonl')}
    TY = {'red': 'RED', 'white': 'WHITE_DRY', 'sweet': 'WHITE_SWEET'}
    for lid, r in gv.items():
        t = wines[r['stable_id']]['type']
        assert t == (TY[files[lid]['cat']] if lid in files else 'UNKNOWN'), (lid, t)


@check
def m3_grand_vin_rank_is_a_dataset_claim():
    rels = {r['id']: r for r in T('state/estate-wine.jsonl')}
    gv = {r['stable_id'] for r in imap('grand-vin').values()}
    ra = [r for r in T('state/rank-assertions.jsonl') if rels[r['relationship']]['wine'] in gv]
    assert len(ra) == len(gv)
    assert all(r['tier'] == 'FIRST' and r['scope'] == 'ESTATE_RANGE' and r['claimant'] == 'DATASET'
               and r['legacy_term'] == 'grand' for r in ra)


# ---------------------------------------------------------------- M4

def ranks_by_wine():
    rels = {r['id']: r for r in T('state/estate-wine.jsonl')}
    out = collections.defaultdict(list)
    for r in T('state/rank-assertions.jsonl'):
        out[rels[r['relationship']]['wine']].append(r)
    return out


@check
def m4_other_never_becomes_a_rank():
    slugmap = imap('wine-by-slug')
    rk = ranks_by_wine()
    p_c = next(p['id'] for p in T('cross/provenance.jsonl') if p.get('actor') == 'data/cuvees.js'
               and p['kind'] == 'LEGACY_UNSOURCED' and 'quote' not in p and 'code_state' not in p)
    n = 0
    for lid, ws in L.g('BDX_CUVEE_WINES').items():
        for w in ws:
            wid = slugmap['%s|%s' % (lid, w['slug'])]['stable_id']
            cuv = [r for r in rk[wid] if r['provenance'] == p_c]
            assert len(cuv) == 1, (lid, w['slug'])
            want = ('SECOND', 'second') if w['role'] == 'second' else ('UNKNOWN', 'other')
            assert (cuv[0]['tier'], cuv[0]['legacy_term']) == want, (lid, w, cuv[0])
            n += 1
    assert n == 135
    for r in T('state/rank-assertions.jsonl'):
        assert r['tier'] in ('FIRST', 'SECOND', 'UNKNOWN'), 'a tier no legacy term supports'
        assert r['legacy_term'] in ('grand', 'second', 'other', 'red and white')


@check
def m4_second_field_kept_whole_dash_is_absence_not_unknown():
    sec = imap('second-by-name')
    files = [r for _, r in L.estate_files() if 'second' in r]
    assert {'%s|%s' % (r['id'], r['second']) for r in files} == set(sec)
    est = {k: r['stable_id'] for k, r in imap('estate').items() if r.get('stable_id')}
    absent = {r['estate'] for r in T('state/rank-absences.jsonl')}
    for r in files:
        k = '%s|%s' % (r['id'], r['second'])
        if r['second'] == '—':
            assert est[r['id']] in absent and sec[k]['status'] == 'RETIRED'
        elif '(' in r['second']:
            assert not sec[k].get('stable_id'), k
    assert len(absent) == 34
    # Yquem's Y is not made a second wine.
    rk = ranks_by_wine()
    y = imap('wine-by-slug')["yquem|" + next(w['slug'] for w in L.g('BDX_CUVEE_WINES')['yquem'])]['stable_id']
    assert {r['tier'] for r in rk[y]} == {'UNKNOWN'}


@check
def m4_no_wine_minted_where_the_estate_lists_wines():
    listed = set(L.g('BDX_CUVEE_WINES'))
    cuvee_ids = {x['stable_id'] for x in imap('wine-by-slug').values()}
    for k, r in imap('second-by-name').items():
        lid = k.split('|')[0]
        minted = r.get('stable_id') and r['stable_id'] not in cuvee_ids
        if minted:
            assert lid not in listed, k
    # undecided renames stay undecided: Haut-Bailly's La Parde is not merged into Haut-Bailly II
    hb = imap('second-by-name')['haut-bailly|La Parde de Haut-Bailly']
    assert hb['status'] == 'AMBIGUOUS' and not hb.get('stable_id') and hb['candidates']


@check
def m4_phase2_proposals_not_applied():
    names = {r['name'] for r in T('identity/names.jsonl')}
    assert not any('murets' in n.lower() for n in names), 'Murets in the model'
    est = imap('estate')['stem-chateau-tour-saint-christophe']['stable_id']
    rels = [r for r in T('state/estate-wine.jsonl') if r['estate'] == est]
    assert len(rels) == 1, 'Terrasses attached to Tour Saint-Christophe'
    assert not T('identity/transitions.jsonl'), 'an identity transition decided (Echo)'
    echo = imap('second-by-name')['lynch-bages|Echo de Lynch-Bages']
    assert echo['stable_id'] == imap('wine-by-slug')['lynch-bages|echo-de-lynch-bages']['stable_id']


@check
def m4_evidence_target_wines_resolve_or_are_classified():
    import glob
    dm = imap('wine-by-display-name')
    used = set()
    for p in glob.glob(L.ROOT + 'data/evidence/decisions-v*.jsonl'):
        for d in L.jsonl_lines(p):
            c = d.get('ctx') or {}
            if c.get('target_wine') and c.get('estate'):
                used.add('%s|%s' % (c['estate'], c['target_wine']))
    assert used <= set(dm), sorted(used - set(dm))[:5]
    sec = imap('second-by-name')
    for k in used:
        if not dm[k].get('stable_id') and k in sec:
            # an undecided second: classified exactly as the second field was
            assert dm[k]['status'] == sec[k]['status'] == 'AMBIGUOUS'
            assert dm[k].get('candidates', []) == sec[k].get('candidates', [])
    unresolved = sorted(k for k in used if not dm[k].get('stable_id') and k not in sec)
    assert unresolved == ['pomerol-chateau-l-enclos|Château L’Enclos'], unresolved


# ---------------------------------------------------------------- M5

def kept_verbatim():
    out = {}
    for p in T('cross/provenance.jsonl'):
        cs = p.get('code_state') or {}
        if cs.get('unresolved'):
            out[(cs['global'], cs['key'])] = json.loads(p['quote'])
    return out


@check
def m5_every_estate_vintage_key_maps_to_one_grand_vin_vintage_or_is_kept():
    ev = imap('estate|vintage')
    gv = imap('grand-vin')
    vint = {(r['wine'], r['label']) for r in T('identity/vintages.jsonl')}
    kept = kept_verbatim()
    import mig_m5_vintages as M5
    for f, name in M5.GRAND:
        for k, v in L.g(name).items():
            lid, year = k.split('|')
            r = ev[k]
            if r.get('stable_id'):
                w, lab = r['stable_id'][3:].rsplit(':', 1)
                assert w == gv[lid]['stable_id'] and lab == year and (w, lab) in vint, k
            else:
                assert kept[(name, k)] == v, k
    assert sum(1 for r in ev.values() if not r.get('stable_id')) == 17


@check
def m5_every_slug_vintage_key_maps_to_its_wine_or_is_kept():
    sv = imap('estate|slug|vintage')
    slugs = imap('wine-by-slug')
    kept = kept_verbatim()
    for name in ('BDX_CUVEES', 'BDX_CUVEE_URL'):
        for k, v in L.g(name).items():
            lid, slug, year = k.split('|')
            r = sv[k]
            if r.get('stable_id'):
                assert r['stable_id'] == S.vref(slugs['%s|%s' % (lid, slug)]['stable_id'], year)
            else:
                assert kept[(name, k)] == v
    orphans = [f for f in T('cross/findings.jsonl') if f['kind'] == 'ORPHAN_PROVENANCE'
               and f['detail'].startswith('cuvee-src.js')]
    assert len(orphans) == 16
    np = T('state/vintage-statements.jsonl')
    assert len(np) == sum(len(x) for x in L.g('BDX_NOT_PRODUCED').values()) == 18


# ---------------------------------------------------------------- M6

@check
def m6_every_manifest_row_is_one_attribution_or_assessment():
    prov = {r['id']: r for r in T('cross/provenance.jsonl')}
    rows = collections.Counter()
    sheets = L.sources_rows()['sheets']
    for t in ('document/attributions.jsonl', 'document/assessments.jsonl'):
        for r in T(t):
            if t.startswith('document/attributions') and 'role' not in r:
                # an estate claim beside an assessment
                i = prov[r['provenance']]['code_state']['row']
                assert sheets[i]['role'] not in ('grand', 'second', 'other') and sheets[i]['estate']
                continue
            rows[prov[r['provenance']]['code_state']['row']] += 1
    assert set(rows) == set(range(len(sheets))) and set(rows.values()) == {1}
    att = T('document/attributions.jsonl')
    assert {r['method'] for r in att} == {'LEGACY_UNKNOWN'}, 'a legacy how text was classified (D6)'
    assert {r['status'] for r in att} == {'LEGACY'}
    by_art = collections.Counter(r['artifact'] for r in att)
    assert max(by_art.values()) > 1, 'attributions are not many per artifact (I14)'


@check
def m6_null_wine_never_defaults_to_the_grand_vin():
    prov = {r['id']: r for r in T('cross/provenance.jsonl')}
    sheets = L.sources_rows()['sheets']
    gv = imap('grand-vin')
    grand = {r['stable_id'] for r in gv.values()}
    for a in T('document/attributions.jsonl'):
        r = sheets[prov[a['provenance']]['code_state']['row']]
        if not r.get('wine') and not r.get('slug'):
            if r['role'] == 'grand' and r['estate'] in gv:
                assert a.get('wine') == gv[r['estate']]['stable_id']
            else:
                assert 'wine' not in a, r
        if a.get('wine') in grand:
            assert r['role'] == 'grand' or r.get('wine') or r.get('slug'), r


@check
def m6_sources_never_estate_identity():
    src = {r['id']: r for r in T('identity/sources.jsonl')}
    est = {r['id'] for r in T('identity/estates.jsonl')}
    assert not set(src) & est
    links = collections.defaultdict(set)
    for r in T('state/source-estate.jsonl'):
        links[r['source']].add(r['estate'])
    for sid, es in links.items():
        assert src[sid]['kind'] == ('ESTATE_SITE' if len(es) == 1 else 'UNKNOWN'), src[sid]
    assert len(T('state/source-estate.jsonl')) == len(L.g('BDX_SITES'))


@check
def m6_evidence_links_one_per_v4_v5_row_same_key_as_the_store():
    import evidence
    links = T('observation/evidence-links.jsonl')
    keys = {(r['evidence_version'], r['row_key']) for r in links}
    n = 0
    for v in (4, 5):
        for d in L.jsonl_lines(L.ROOT + 'data/evidence/decisions-v%d.jsonl' % v):
            k = (v, L.dumps(list(evidence.row_key(d))))
            assert k in keys
            n += 1
    assert n == len(links) == len(keys)
    assert not any(r['evidence_version'] < 4 for r in links), 'v1-v3 linked to bytes never hashed'


# ---------------------------------------------------------------- M7

META = {'src', 'url', 'via', 'wy', 'ttl', 'ntl', 'dtl', 'ftl', 'wtl', 'sugl', 'tau'}


@check
def m7_every_legacy_value_is_one_observation():
    obs = collections.Counter((o['extraction']['file'], o['extraction']['record'], o['field'])
                              for o in T('observation/observations.jsonl'))
    assert set(obs.values()) == {1}
    kept = kept_verbatim()
    for file, name in (('data/fiches.js', 'BDX_FICHES'), ('data/cuvees.js', 'BDX_CUVEES')):
        for k, rec in L.g(name).items():
            for f in rec:
                if f in META:
                    continue
                assert (file, k, f) in obs or (name, k) in kept, (name, k, f)
    assert sum(1 for k in obs if k[0] == 'data/fiches.js') == baseline()['counts']['fiche_values']


@check
def m7_record_source_never_promoted_badette_2020_oak():
    v = imap('estate|vintage')['stem-chateau-badette|2020']['stable_id']
    cv = {(c['subject'], c['field']): c for c in T('canonical/values.jsonl')}
    c = cv[(v, 'oak')]
    prov = {p['id']: p for p in T('cross/provenance.jsonl')}
    assert c['value'] == L.g('BDX_FICHES')['stem-chateau-badette|2020']['oak']
    assert c['status'] == 'LEGACY_RECORD_SOURCE_ONLY', c['status']
    assert prov[c['provenance']]['kind'] == 'LEGACY_RECORD_SOURCE'
    assert 'artifact' not in prov[c['provenance']]
    # and in general: an artifact on a value's provenance only through a resolved field source
    for c in cv.values():
        p = prov[c['provenance']]
        if 'artifact' in p:
            assert p['kind'] == 'LEGACY_FIELD_SOURCE' and c['status'] == 'LEGACY_FIELD_SOURCE'
        if p['kind'] == 'LEGACY_AMBIGUOUS_SOURCE':
            assert 'artifact' not in p and c['status'] == 'LEGACY_AMBIGUOUS_SOURCE'


@check
def m7_field_source_artifact_is_the_unique_candidate():
    pls = {p['id']: p for p in T('document/placements.jsonl')}
    refs = {(r['origin'], r['record_key'], r.get('field'), r['basename']): r
            for r in T('document/legacy-references.jsonl')}
    n = 0
    for p in T('cross/provenance.jsonl'):
        if p['kind'] != 'LEGACY_FIELD_SOURCE':
            continue
        lr = p['legacy_reference']
        r = refs[(lr['origin'], lr['record_key'], lr.get('field'), lr['basename'])]
        assert r['resolution'] == 'ACTIVE'
        assert {pls[c].get('artifact') for c in r['candidates']} == {p['artifact']}
        n += 1
    assert n > 0


@check
def m7_only_class_a_is_canonical():
    allowed = {'alc', 'blend', 'harvest', 'pick', 'months', 'oak', 'ph', 'sug', 'ta', 'yld',
               'vineyard_area_ha'}
    fields = {c['field'] for c in T('canonical/values.jsonl')}
    assert fields <= allowed, fields - allowed
    for f in ('taste', 'note', 'food', 'press', 'owner', 'rating', 'cellar_note', 'soil'):
        assert f not in fields


@check
def m7_reconciliations_keep_every_candidate_none_deleted():
    obs = {o['id'] for o in T('observation/observations.jsonl')}
    recs = T('reconciliation/reconciliations.jsonl')
    cv = {(c['subject'], c['field']): c for c in T('canonical/values.jsonl')}
    assert len(recs) == len(cv)
    for r in recs:
        assert r['selected'] in r['candidates'] and set(r['candidates']) <= obs
        assert r['rule'] == 'LEGACY_NEVER_OVERWRITE' and r['status'] == 'LEGACY_RETAINED'
        assert cv[(r['subject'], r['field'])]['reconciliation'] == r['id']
    assert {o['extraction']['method'] for o in T('observation/observations.jsonl')} == {'LEGACY'}, \
        'an observation re-extracted or copied from the harvest'


# ---------------------------------------------------------------- M8

_recon = {}


def recon():
    if not _recon:
        import reconstruct
        _recon['r'] = reconstruct.build()
    return _recon['r']


@check
def m8_reconstruction_has_zero_unexplained_differences():
    r = recon()
    assert r['unexplained'] == 0, [d for d in r['differences'] if d['class'] == 'TRUE MIGRATION ERROR'][:5]
    allowed = {'EXPECTED STRUCTURAL DIFFERENCE', 'TRUE MIGRATION ERROR', 'LEGACY AMBIGUITY',
               'PRE-EXISTING DATA ISSUE', 'UNRESOLVED'}
    assert set(r['summary']) <= allowed
    saved = json.load(open(L.MODEL + 'checks/reconstruction.json', encoding='utf-8'))
    assert saved['summary'] == r['summary'], 'the committed reconstruction report is stale'


@check
def m8_every_legacy_global_is_compared_or_classified():
    import reconstruct
    r = recon()
    classified = {d['where'] for d in r['differences'] if d['where'].endswith('.js')}
    for f, g in L.legacy().items():
        if f in reconstruct.OUT_OF_SCOPE or f == 'classifications.js':
            assert f in classified, f
    # everything else is projected
    import model_reader as R
    P = R.project(classifications={c['id']: c for c in L.g('BDX_CLASSIFICATIONS')})
    for f, g in L.legacy().items():
        if f in reconstruct.OUT_OF_SCOPE or f == 'classifications.js':
            continue
        assert set(g) <= set(P.get(f, {})), (f, set(g) - set(P.get(f, {})))


@check
def m8_the_comparison_catches_injected_errors():
    import copy
    import reconstruct
    import model_reader as R
    P = R.project(classifications={c['id']: c for c in L.g('BDX_CLASSIFICATIONS')})
    legacy = L.legacy()
    for mutate in (
            lambda p: p['fiches.js']['BDX_FICHES']['stem-chateau-badette|2020'].__setitem__('oak', 50),
            lambda p: p['cuvees.js']['BDX_CUVEES'].pop(sorted(p['cuvees.js']['BDX_CUVEES'])[0]),
            lambda p: p['chateaux.js']['BDX_CHATEAUX'][0].__setitem__('second', 'Invented'),
            lambda p: p['saintemilion.js']['BDX_STEM_GCC'].pop(),
            lambda p: p['cuvees.js']['BDX_CUVEE_WINES']['lynch-bages'][0].__setitem__('role', 'second')):
        q = copy.deepcopy(P)
        mutate(q)
        errs = [d for d in reconstruct.compare(legacy, q) if d['class'] == 'TRUE MIGRATION ERROR']
        assert errs, 'an injected error went unnoticed'
    q = copy.deepcopy(P)
    q['sources.json']['sheets'][5]['sha1'] = '0' * 40
    assert reconstruct.manifest_diffs(q)


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
