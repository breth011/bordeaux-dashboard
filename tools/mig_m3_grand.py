"""Phase 4 M3: explicit grand-vin Wines, only where supported.

A grand-vin Wine is minted for an estate when the legacy data says such a
wine exists:
  - a classification lists the estate (a classification's unit is the cru,
    the wine sold under the estate's name: data/scope's role basis);
  - the estate has a full record (its cat, blend and appellation describe
    the wine the estate is judged on: sources.json roles.grand); or
  - a legacy 'estate|vintage' record exists for it (fiches, field-src,
    fiches-url, ratings, cellar, BDX_SCORES, BDX_NOT_PRODUCED); or
  - the manifest attributes a sheet to it with role 'grand'.
An estate with none of these (an editorial compact-list name and nothing
else) gets no Wine: the app's defaults for it (cat red, the list's
appellation) are page behaviour, reproduced as such in M8, not facts.

Type: from the full record's cat (red RED, white WHITE_DRY, sweet
WHITE_SWEET); UNKNOWN for a compact-list estate, whose cat the app
assumes. Name: the estate's own, as the dataset shows it (the contract's
mapping), provenance LEGACY_UNSOURCED. Rank: FIRST within the estate's
range, claimant DATASET, legacy_term 'grand'.

Classification: a scheme and the dataset's edition per classification of
classifications.js that is not editorial; the body is the one the Phase
3.0 authoritative sources name, verbatim. Membership is on the Wine, not
the Estate. Editorial collections stay estate-level (M2).
"""
import collections
import json

import migration_lib as L
import model_schema as S
import mig_m2_identity as M2

ACTOR = 'tools/migrate.py M3'
TYPE = {'red': 'RED', 'white': 'WHITE_DRY', 'sweet': 'WHITE_SWEET'}
SYSTEM = {'1855': '1855-medoc', 'sauternes': '1855-sauternes', 'graves': 'graves',
          'stem': 'stem-2022', 'bourgeois': 'cb-2025', 'artisan': 'ca-2022'}
VINTAGE_STRUCTURES = ['BDX_FICHES', 'BDX_FIELD_SRC', 'BDX_FICHE_URL', 'BDX_RATINGS', 'BDX_CELLAR',
                      'BDX_SCORES']


def current():
    return {'valid_from': S.bound('UNKNOWN'), 'valid_to': S.bound('OPEN')}


def support(view):
    """{legacy estate id: [reasons]} for every estate with a supported grand vin."""
    sup = collections.defaultdict(list)
    classes = {c['id']: c for c in L.g('BDX_CLASSIFICATIONS')}
    for e in view['estates']:
        if not classes[e['cls']].get('editorial'):
            sup[e['id']].append('classification:' + e['cls'])
        if e.get('cross'):
            sup[e['id']].append('classification:' + e['cross'])
        if not e['sparse']:
            sup[e['id']].append('full record')
    for name in VINTAGE_STRUCTURES:
        for k in L.g(name):
            sup[k.split('|')[0]].append(name)
    for k in L.g('BDX_NOT_PRODUCED'):
        sup[k].append('BDX_NOT_PRODUCED')
    # The manifest says a sheet is the grand vin of the estate.
    for r in L.sources_rows()['sheets']:
        if r['estate'] and r['role'] == 'grand':
            sup[r['estate']].append('sources.json role grand')
    return {k: sorted(set(v)) for k, v in sup.items()}


def run(m):
    view = L.canonical_view()
    by_id = {e['id']: e for e in view['estates']}
    files = {r['id']: (f, r) for f, r in L.estate_files()}
    sup = support(view)
    unsupported = sorted(i for i in by_id if i not in sup)
    m.grand = {}

    p_name = m.prov('LEGACY_UNSOURCED', 'data/sources.json',
                    quote="roles.grand: 'the grand vin, the wine the estate is judged on'; the dataset "
                          "shows it under the estate's name")
    p_rule = m.prov('DERIVATION', ACTOR, quote='one grand-vin Wine per estate whose legacy data '
                    'supports one (classification listing, full record, or an estate|vintage record)')
    for lid in sorted(sup):
        if lid not in m.estate:
            continue                      # unresolved legacy ids (M2) get no wine
        e = by_id[lid]
        eid = m.estate[lid]
        wid = m.mint('Wine', 'grand-vin', lid)
        m.grand[lid] = wid
        typ = TYPE[files[lid][1]['cat']] if lid in files else 'UNKNOWN'
        m.add('identity/wines.jsonl', {'id': wid, 'name_status': 'KNOWN', 'type': typ})
        M2.idmap(m, 'grand-vin', lid, wid, m.prov('DERIVATION', ACTOR, quote='supported by: ' +
                                                  ', '.join(sup[lid])))
        m.add('identity/names.jsonl', {
            'id': S.hid('NameRecord', wid, e['name'], 'CURRENT'), 'subject': wid, 'name': e['name'],
            'kind': 'CURRENT', 'validity': current(), 'provenance': p_name})
        rel = S.hid('EstateWineRelationship', eid, wid, 'PRODUCED_BY')
        m.add('state/estate-wine.jsonl', {
            'id': rel, 'estate': eid, 'wine': wid, 'status': 'ESTABLISHED', 'kind': 'PRODUCED_BY',
            'validity': current(), 'provenance': p_rule})
        m.add('state/rank-assertions.jsonl', {
            'id': S.hid('RankAssertion', rel, 'FIRST', 'ESTATE_RANGE', 'DATASET', 'grand'),
            'relationship': rel, 'tier': 'FIRST', 'scope': 'ESTATE_RANGE', 'claimant': 'DATASET',
            'legacy_term': 'grand', 'validity': current(), 'provenance': p_name})
    m.grand_rel = {lid: S.hid('EstateWineRelationship', m.estate[lid], w, 'PRODUCED_BY')
                   for lid, w in m.grand.items()}
    m.stat('M3', 'grand-vin wines minted', len(m.grand))
    m.stat('M3', 'estates with no supported grand vin', unsupported)
    m.stat('M3', 'grand-vin types', dict(sorted(collections.Counter(
        r['type'] for r in m.rows('identity/wines.jsonl')).items())))

    classification(m, by_id, files)
    appellations(m, by_id, files)


def classification(m, by_id, files):
    uni = json.load(open(L.ROOT + 'data/scope/authoritative-universe.json', encoding='utf-8'))
    systems = {s['id']: s for s in uni['systems']}
    srcs = {s['id']: s for s in uni['sources']}
    m.editions = {}
    for c in L.g('BDX_CLASSIFICATIONS'):
        if c.get('editorial'):
            continue
        sy = systems[SYSTEM[c['id']]]
        pid = m.mint('Party', 'party', sy['body'])
        M2.idmap(m, 'party', sy['body'], pid, m.prov(
            'AUTHORITATIVE_SOURCE', 'data/scope/authoritative-universe.json',
            quote='the body its systems name, verbatim'))
        m.add('identity/parties.jsonl', {'id': pid, 'kind': 'INSTITUTION', 'name': sy['body']})
        sid = S.hid('ClassificationScheme', c['id'])
        m.add('state/classification-schemes.jsonl', {'id': sid, 'name': c['name'], 'body': pid})
        p_c = m.prov('LEGACY_UNSOURCED', 'data/classifications.js')
        vf = S.bound('EXACT', str(c['year']), 'CALENDAR', 'YEAR', p_c) if c.get('year') \
            else S.bound('UNKNOWN')
        ed = S.hid('ClassificationEdition', c['id'], 'dataset')
        m.add('state/classification-editions.jsonl', {
            'id': ed, 'scheme': sid, 'label': '%s (as data/classifications.js holds it)' % c['name'],
            'validity': {'valid_from': vf, 'valid_to': S.bound('OPEN')},
            'ranks': [t['label'] for t in c['tiers']], 'status': 'IN_FORCE', 'provenance': p_c})
        m.editions[c['id']] = (ed, {t['growth']: t['label'] for t in c['tiers']})

    def member(cls, lid, growth, f, appellation_listed=None):
        ed, tiers = m.editions[cls]
        wid = m.grand[lid]
        row = {'id': S.hid('ClassificationMembership', ed, wid), 'edition': ed, 'wine': wid,
               'rank': tiers[growth], 'rank_status': 'KNOWN', 'validity': current(),
               'provenance': m.prov('LEGACY_UNSOURCED', 'data/' + f)}
        if appellation_listed:
            row['appellation_listed'] = appellation_listed
        m.add('state/classification-memberships.jsonl', row)

    n = collections.Counter()
    for lid, (f, r) in sorted(files.items()):
        cls = r.get('cls') or ('sauternes' if r.get('cat') == 'sweet' else '1855')
        if cls in m.editions:
            member(cls, lid, r['growth'], f)
            n[cls] += 1
    for name, lid in M2.sparse_ids('stem', L.g('BDX_STEM_GCC'), by_id):
        member('stem', lid, 3, 'saintemilion.js')
        n['stem'] += 1
    for tier, g in (('exceptionnel', 1), ('superieur', 2), ('bourgeois', 3)):
        rows = L.g('BDX_CRU_BOURGEOIS')[tier]
        for (name, lid), row in zip(M2.sparse_ids('bourgeois', [x[0] for x in rows], by_id), rows):
            member('bourgeois', lid, g, 'crubourgeois.js', row[1])
            n['bourgeois'] += 1
    rows = L.g('BDX_CRU_ARTISAN')['current']
    for (name, lid), row in zip(M2.sparse_ids('artisan', [x[0] for x in rows], by_id), rows):
        member('artisan', lid, 1, 'cruartisan.js', row[1])
        n['artisan'] += 1
    for lid in L.g('BDX_GRAVES_CROSSLIST'):
        member('graves', lid, 1, 'graves.js')
        n['graves (cross-list)'] += 1
    m.stat('M3', 'classification memberships (grand vins)', dict(sorted(n.items())))


def appellations(m, by_id, files):
    def appellation(name):
        aid = S.hid('Appellation', name)
        m.add('state/appellations.jsonl', {'id': aid, 'name': name, 'validity': current(),
                                           'provenance': m.prov('DERIVATION', ACTOR,
                                                                quote='an appellation name the legacy '
                                                                      'files use, verbatim')})
        return aid

    def member(lid, name, f):
        wid = m.grand[lid]
        aid = appellation(name)
        m.add('state/appellation-memberships.jsonl', {
            'id': S.hid('AppellationMembership', wid, aid), 'wine': wid, 'appellation': aid,
            'validity': current(), 'provenance': m.prov('LEGACY_UNSOURCED', 'data/' + f)})
    for lid, (f, r) in sorted(files.items()):
        if r.get('appellation'):
            member(lid, r['appellation'], f)
    for tier in ('exceptionnel', 'superieur', 'bourgeois'):
        rows = L.g('BDX_CRU_BOURGEOIS')[tier]
        for (name, lid), row in zip(M2.sparse_ids('bourgeois', [x[0] for x in rows], by_id), rows):
            member(lid, row[1], 'crubourgeois.js')
    rows = L.g('BDX_CRU_ARTISAN')['current']
    for (name, lid), row in zip(M2.sparse_ids('artisan', [x[0] for x in rows], by_id), rows):
        member(lid, row[1], 'cruartisan.js')
    m.stat('M3', 'appellation memberships', len(m.rows('state/appellation-memberships.jsonl')))
