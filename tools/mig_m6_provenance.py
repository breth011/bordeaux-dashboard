"""Phase 4 M6: sources, attributions, evidence links and value provenance.

Sources: one per host data/websites.js lists (ESTATE_SITE when one estate
lists it, UNKNOWN when several do: a group or a merchant, not decided
here), linked to each listing estate by a SourceEstateRelationship, never
by identity (I15); one per discovery domain (UNKNOWN; its estates are
Phase 3.0 universe ids, which no stage maps); bordoverview.com, the
aggregator behind ratings.js; the Wine Advocate, the critic BDX_SCORES
names.

The manifest: one Attribution LEGACY per row (I14: many per artifact).
role grand/second/other -> FIRST/SECOND/UNKNOWN; a null wine stays null
except under role 'grand', which names the grand vin itself (R1); method
LEGACY_UNKNOWN for every row, the row's own words kept (D6: the legacy how
table is not decided). skip, page, group report, combined and unknown are
ArtifactAssessments. The row's other fields (how, note, colour, a year
with no wine) are kept on the attribution's provenance.

Evidence: one EvidenceLink per v4 and v5 decision (row key exactly as
tools/evidence.py builds it), to the artifact it hashed, the estate and
the wine it was asked about where those resolve; v1-v3 stay interpretable
through the identity map, unlinked to bytes they never hashed.

Value provenance (value_prov): a value's provenance is the field's, never
the record's (I13):
  field-src names the field, one artifact     LEGACY_FIELD_SOURCE
  field-src names the field, not one artifact LEGACY_AMBIGUOUS_SOURCE
  only the record has a src                   LEGACY_RECORD_SOURCE
  neither                                     LEGACY_UNSOURCED
"""
import collections
import glob
from urllib.parse import urlparse

import migration_lib as L
import model_schema as S
import mig_m2_identity as M2

ACTOR = 'tools/migrate.py M6'
ROLE = {'grand': 'FIRST', 'second': 'SECOND', 'other': 'UNKNOWN'}
DOCTYPE = {'skip': 'OTHER', 'page': 'WEB_PAGE', 'group report': 'GROUP_REPORT',
           'combined': 'MULTI_WINE_SHEET', 'unknown': 'UNKNOWN'}


def host(u):
    return urlparse(u).netloc.lower().removeprefix('www.')


def current():
    return {'valid_from': S.bound('UNKNOWN'), 'valid_to': S.bound('OPEN')}


def source(m, key, kind, name, base_urls):
    sid = m.mint('Source', 'source', key)
    row = {'id': sid, 'kind': kind, 'name': name}
    if base_urls:
        row['base_urls'] = sorted(set(base_urls))
    m.add('identity/sources.jsonl', row, replace=True)
    return sid


def sources(m):
    p_rule = m.prov('DERIVATION', ACTOR, quote='one Source per host, never an estate identity')
    sites = L.g('BDX_SITES')
    by_host = collections.defaultdict(list)
    for lid, (u, tag) in sorted(sites.items()):
        by_host[host(u)].append((lid, u, tag))
    import json
    targets = json.load(open(L.ROOT + 'data/discovery/targets.json', encoding='utf-8'))['estates']
    disc = collections.defaultdict(list)
    for t in targets:
        if t.get('site'):
            disc[host(t['site'])].append(t['site'])
    keys = sorted(set(by_host) | set(disc))
    m.source_of_host = {}
    for h in keys:
        listed = by_host.get(h, [])
        kind = 'ESTATE_SITE' if len({x[0] for x in listed}) == 1 else 'UNKNOWN'
        sid = source(m, 'host:' + h, kind, h, [x[1] for x in listed] + disc.get(h, []))
        M2.idmap(m, 'source', 'host:' + h, sid, p_rule)
        m.source_of_host[h] = sid
        for lid, u, tag in listed:
            p = m.prov('LEGACY_UNSOURCED', 'data/websites.js', quote='tag %s' % tag,
                       code_state={'url': u, 'tag': tag})
            m.add('state/source-estate.jsonl', {
                'id': S.hid('SourceEstateRelationship', sid, m.estate[lid], 'OFFICIAL_SITE'),
                'source': sid, 'estate': m.estate[lid], 'kind': 'OFFICIAL_SITE',
                'validity': current(), 'provenance': p})
    m.src_bordoverview = source(m, 'aggregator:bordoverview.com', 'AGGREGATOR', 'bordoverview.com',
                                ['https://bordoverview.com/'])
    M2.idmap(m, 'source', 'aggregator:bordoverview.com', m.src_bordoverview, p_rule)
    m.src_critic = {}
    for name in sorted({v['src'] for v in L.g('BDX_SCORES').values()} - {'Multiple critics'}):
        sid = source(m, 'critic:' + name, 'CRITIC', name, [])
        M2.idmap(m, 'source', 'critic:' + name, sid, p_rule)
        m.src_critic[name] = sid
    m.stat('M6', 'sources (hosts, of which shared by estates)', [
        len(keys), sum(1 for h in by_host if len({x[0] for x in by_host[h]}) > 1)])


def attributions(m):
    sheets = L.sources_rows()['sheets']
    im = {(r['namespace'], r['legacy_key']): r for r in m.rows('identity/identity-map.jsonl')}

    def wine_of(r):
        lid = r['estate']
        if not lid or lid not in m.estate:
            return None
        if r.get('slug') and (lid, r['slug']) in m.cuvee:
            return m.cuvee[(lid, r['slug'])]
        if r.get('wine'):
            x = im.get(('wine-by-display-name', '%s|%s' % (lid, r['wine'])))
            return x.get('stable_id') if x else None
        if r['role'] == 'grand':
            return m.grand.get(lid)
        return None
    out = collections.Counter()
    for i, r in enumerate(sheets):
        aid = m.art[('sha1', r['sha1'])]
        keep = {k: r[k] for k in ('how', 'colour', 'year', 'wine', 'slug', 'estateName', 'role', 'url')
                if r.get(k) is not None}
        keep['row'] = i
        if r['sha1'] in m.size_conflicts:
            keep['bytes'] = r['bytes']
        loc = {'kind': 'LOCAL_PATH', 'value': M2.sources_path(r)}
        p = m.prov('LEGACY_MANIFEST', 'data/sources.json', artifact=aid, quote=r.get('note'),
                   locator=loc, code_state=keep)
        if r['role'] not in ROLE and r['estate']:
            # What kind of document it is is an assessment; which estate it
            # concerns is still an attribution, with no rank claimed.
            row = {'id': S.hid('Attribution', aid, i), 'artifact': aid, 'method': 'LEGACY_UNKNOWN',
                   'status': 'LEGACY', 'provenance': p}
            if r['estate'] in m.estate:
                row['estate'] = m.estate[r['estate']]
            m.add('document/attributions.jsonl', row)
            out['attribution with no rank (%s)' % r['role']] += 1
        if r['role'] in ROLE:
            row = {'id': S.hid('Attribution', aid, i), 'artifact': aid, 'role': ROLE[r['role']],
                   'method': 'LEGACY_UNKNOWN', 'status': 'LEGACY', 'provenance': p}
            if r['estate'] and r['estate'] in m.estate:
                row['estate'] = m.estate[r['estate']]
            w = wine_of(r)
            if w:
                row['wine'] = w
                if r.get('year'):
                    m.add('identity/vintages.jsonl', {'wine': w, 'label': str(r['year'])})
                    row['vintage'] = S.vref(w, r['year'])
            elif r.get('wine') or r.get('slug'):
                out['wine named, not resolved'] += 1
            m.add('document/attributions.jsonl', row)
            out['attribution ' + r['role']] += 1
        else:
            m.add('document/assessments.jsonl', {
                'id': S.hid('ArtifactAssessment', aid, i), 'artifact': aid,
                'document_type': DOCTYPE[r['role']], 'status': 'LEGACY', 'provenance': p})
            out['assessment ' + r['role']] += 1
    m.stat('M6', 'manifest rows', dict(sorted(out.items())))


def row_key(d):
    """tools/evidence.py row_key, as text."""
    c = d.get('ctx', {}) or {}
    return L.dumps([d.get('artifact'), c.get('folder'), c.get('estate'), c.get('wine'), c.get('field'),
                    c.get('vintage'), c.get('target_estate'), c.get('target_wine'),
                    c.get('target_role'), c.get('target_vintage'), d.get('v')])


def evidence_links(m):
    im = {(r['namespace'], r['legacy_key']): r for r in m.rows('identity/identity-map.jsonl')}
    n = collections.Counter()
    for v in (4, 5):
        for d in L.jsonl_lines(L.ROOT + 'data/evidence/decisions-v%d.jsonl' % v):
            c = d.get('ctx') or {}
            row = {'row_key': row_key(d), 'evidence_version': v}
            rd = d.get('read') or {}
            if rd.get('sha256'):
                row['artifact'] = m.art[('sha256', rd['sha256'])]
            lid = c.get('target_estate') or c.get('estate')
            if lid in m.estate:
                row['estate'] = m.estate[lid]
            if c.get('target_wine') and c.get('estate'):
                x = im.get(('wine-by-display-name', '%s|%s' % (c['estate'], c['target_wine'])))
                if x and x.get('stable_id'):
                    row['wine'] = x['stable_id']
            m.add('observation/evidence-links.jsonl', row)
            n['v%d' % v] += 1
            n['with artifact'] += 'artifact' in row
            n['with wine'] += 'wine' in row
    m.stat('M6', 'evidence links', dict(sorted(n.items())))


def value_prov(m, origin_src, key, field, record_file, record):
    """The provenance of one legacy value (I13): the field's, or the record's
    named as only the record's, or none."""
    ref = m.get('document/legacy-references.jsonl', (origin_src, key, field, None)) \
        if False else None
    refs = m.refs_by_field.get((origin_src, key, field))
    if refs is not None:
        r = refs
        lref = {'origin': r['origin'], 'record_key': r['record_key'], 'field': r['field'],
                'basename': r['basename']}
        if r['resolution'] == 'ACTIVE':
            art = m.pl_artifact[r['candidates'][0]]
            return m.prov('LEGACY_FIELD_SOURCE', 'data/' + origin_src, artifact=art,
                          legacy_reference=lref), 'LEGACY_FIELD_SOURCE'
        return m.prov('LEGACY_AMBIGUOUS_SOURCE', 'data/' + origin_src,
                      legacy_reference=lref), 'LEGACY_AMBIGUOUS_SOURCE'
    if record.get('src'):
        return m.prov('LEGACY_RECORD_SOURCE', 'data/' + record_file, quote=record['src'],
                      code_state={'record': key}), 'LEGACY_RECORD_SOURCE_ONLY'
    return m.prov('LEGACY_UNSOURCED', 'data/' + record_file), 'LEGACY_UNSOURCED'


def prepare_value_prov(m):
    m.refs_by_field = {}
    for r in m.rows('document/legacy-references.jsonl'):
        if r['origin'] in ('field-src.js', 'cuvee-src.js') and r.get('field'):
            m.refs_by_field[(r['origin'], r['record_key'], r['field'])] = r
    m.pl_artifact = {r['id']: r.get('artifact') for r in m.rows('document/placements.jsonl')}


def documentation(m):
    """The manifest's own vocabularies (note, roles, how), kept with the migration."""
    d = L.sources_rows()
    m.prov('LEGACY_MANIFEST', 'data/sources.json',
           code_state={'documentation': {k: d[k] for k in ('note', 'roles', 'how')}})


def run(m):
    documentation(m)
    sources(m)
    attributions(m)
    evidence_links(m)
    prepare_value_prov(m)
