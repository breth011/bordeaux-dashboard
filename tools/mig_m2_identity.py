"""Phase 4 M2: identity mapping.

Estates: one minted Estate per canonical estate id (470), the identity map
holding every legacy estate id any file uses; the 298 name-derived ids are
mapped as they are, never recomputed, and their list entries are mapped
too. A legacy id that names no estate stays unresolved (status AMBIGUOUS,
no stable id, no candidates) with a finding; its records are kept verbatim
by later stages.

Documents: one Artifact per digest. A manifest sha1 and a sha256 are one
artifact only when it is proven they hash the same bytes:
  - the discovery harvest computed both over the bytes it fetched; or
  - the contract's evidence-path rule: the manifest records one version at
    that path and every read there (v4, v5) hashed the same sha256.
Otherwise they stay separate artifacts. A document acquired outside the
crawl and registered by M3.10A's audited manifest is minted by its sha256
in the same way (external_registrations). One Placement per (locator,
artifact); a path with several manifest versions keeps every version
(BYTES_UNAVAILABLE: which one is on disk is not recorded), and the bytes
the reader hashed there get their own PRESENT placement. The 123
provenance failures are placements with no artifact (MISSING,
NAME_MISMATCH); the manifest's claimed digest stays on their provenance.

Filenames: one LegacyDocumentReference per basename a legacy file cites,
with every LOCAL_PATH placement of that basename as candidates: ACTIVE
when they hold one artifact, AMBIGUOUS otherwise (no candidate at all is
AMBIGUOUS with none: unresolved). Never by first match.
"""
import collections
import glob
import json
import os

import migration_lib as L
import model_schema as S

ACTOR = 'tools/migrate.py M2'
EDITORIAL = None


def legacy_prov(m, f):
    return m.prov('LEGACY_UNSOURCED', 'data/' + f)


def rule_prov(m, rule):
    return m.prov('DERIVATION', ACTOR, quote=rule)


def idmap(m, ns, key, stable, prov, status='ACTIVE', candidates=None):
    row = {'namespace': ns, 'legacy_key': key, 'status': status, 'provenance': prov}
    if stable:
        row['stable_id'] = stable
    if candidates is not None:
        row['candidates'] = candidates
    m.add('identity/identity-map.jsonl', row)


def current():
    return {'valid_from': S.bound('UNKNOWN'), 'valid_to': S.bound('OPEN')}


def estates(m):
    view = L.canonical_view()
    by_id = {e['id']: e for e in view['estates']}
    files = {r['id']: f for f, r in L.estate_files()}
    p_rule = rule_prov(m, 'one Estate per canonical estate id; the legacy id is mapped, never renamed')
    for lid in sorted(by_id):
        eid = m.mint('Estate', 'estate', lid)
        m.add('identity/estates.jsonl', {'id': eid, 'name_status': 'KNOWN'})
        idmap(m, 'estate', lid, eid, p_rule)
    m.estate = {lid: m.registry[('estate', lid)] for lid in by_id}

    # Names, verbatim, from the file that holds the estate.
    for lid, e in sorted(by_id.items()):
        f = files.get(lid) or {'stem': 'saintemilion.js', 'pomerol': 'pomerol.js',
                               'bourgeois': 'crubourgeois.js', 'artisan': 'cruartisan.js'}[e['cls']]
        eid = m.estate[lid]
        m.add('identity/names.jsonl', {
            'id': S.hid('NameRecord', eid, e['name'], 'CURRENT'), 'subject': eid,
            'name': e['name'], 'kind': 'CURRENT', 'validity': current(),
            'provenance': legacy_prov(m, f)})

    # The compact lists: the list entry itself is a legacy key too (R12).
    p_list = rule_prov(m, "a compact-list entry; its legacy id is cls + '-' + slug(name) as app.js "
                          "builds it, mapped here as it stands")
    def entry(key, lid):
        idmap(m, 'estate-list-entry', key, m.estate[lid], p_list)
    for name, (lid) in sparse_ids('stem', L.g('BDX_STEM_GCC'), by_id):
        entry('BDX_STEM_GCC|' + name, lid)
    for name, lid in sparse_ids('pomerol', L.g('BDX_POMEROL_OTHER'), by_id):
        entry('BDX_POMEROL_OTHER|' + name, lid)
    for tier in ('exceptionnel', 'superieur', 'bourgeois'):
        for name, lid in sparse_ids('bourgeois', [r[0] for r in L.g('BDX_CRU_BOURGEOIS')[tier]], by_id):
            entry('BDX_CRU_BOURGEOIS.%s|%s' % (tier, name), lid)
    for name, lid in sparse_ids('artisan', [r[0] for r in L.g('BDX_CRU_ARTISAN')['current']], by_id):
        entry('BDX_CRU_ARTISAN.current|' + name, lid)

    # Every other legacy estate id in use: resolved, or unresolved with a finding.
    used = legacy_estate_uses()
    m.unresolved_estates = {}
    for lid in sorted(used):
        if lid in m.estate:
            continue
        p = m.prov('DERIVATION', ACTOR, quote='legacy estate id %r used by %s; no canonical estate has '
                   'this id and nothing in the data says which estate or wine it is' % (
                       lid, ', '.join('%s (%d)' % kv for kv in sorted(used[lid].items()))))
        idmap(m, 'estate', lid, None, p, status='AMBIGUOUS', candidates=[])
        m.finding(p, 'IDENTITY_UNCERTAIN', 'legacy estate id %r resolves to no estate' % lid, ACTOR, p)
        m.unresolved_estates[lid] = dict(used[lid])
    m.stat('M2', 'legacy estate ids', len(set(used) | set(m.estate)))
    m.stat('M2', 'estates minted', len(m.estate))
    m.stat('M2', 'name-derived ids mapped', sum(1 for e in by_id.values() if e['sparse']))
    m.stat('M2', 'unresolved legacy estate ids', sorted(m.unresolved_estates))
    return by_id


def sparse_ids(cls, names, by_id):
    import re
    import unicodedata
    out = []
    for n in names:
        s = unicodedata.normalize('NFD', n)
        s = ''.join(ch for ch in s if not ('̀' <= ch <= 'ͯ')).lower()
        s = re.sub(r'^-|-$', '', re.sub(r'[^a-z0-9]+', '-', s))
        lid = cls + '-' + s
        assert lid in by_id, lid
        out.append((n, lid))
    return out


def legacy_estate_uses():
    used = collections.defaultdict(collections.Counter)
    for name in ['BDX_FICHES', 'BDX_FIELD_SRC', 'BDX_FICHE_URL', 'BDX_RATINGS', 'BDX_CELLAR',
                 'BDX_SCORES', 'BDX_CUVEES', 'BDX_CUVEE_SRC', 'BDX_CUVEE_URL', 'BDX_FICHES_NL']:
        for k in L.g(name):
            used[k.split('|')[0]][name] += 1
    for name in ['BDX_CUVEE_WINES', 'BDX_NOT_PRODUCED', 'BDX_COORDS', 'BDX_SITES', 'BDX_PLANTINGS',
                 'BDX_TERROIR']:
        for k in L.g(name):
            used[k][name] += 1
    for i in L.g('BDX_GRAVES_CROSSLIST'):
        used[i]['BDX_GRAVES_CROSSLIST'] += 1
    for r in L.sources_rows()['sheets']:
        if r['estate']:
            used[r['estate']]['sources.json'] += 1
    for name in L.evidence_files('*.jsonl'):
        for d in L.evidence(name):
            c = d.get('ctx') or {}
            for f in ('estate', 'target_estate'):
                if c.get(f):
                    used[c[f]]['evidence ctx.' + f] += 1
    return used


def estate_state(m, by_id):
    """Editorial collections and locations: estate-level state."""
    classes = {c['id']: c for c in L.g('BDX_CLASSIFICATIONS')}
    for f, r in L.estate_files():
        eid = m.estate[r['id']]
        cls = r.get('cls') or ('sauternes' if r.get('cat') == 'sweet' else '1855')
        if classes[cls].get('editorial'):
            m.add('state/editorial-memberships.jsonl', {
                'id': S.hid('EditorialCollectionMembership', eid, cls), 'estate': eid,
                'collection': cls, 'tier': str(r['growth']), 'provenance': legacy_prov(m, f)})
        if any(r.get(k) is not None for k in ('commune', 'lat', 'lng')):
            row = {'id': S.hid('EstateLocation', eid, f), 'estate': eid, 'method': 'data/' + f,
                   'validity': current(), 'provenance': legacy_prov(m, f)}
            for k in ('commune', 'lat', 'lng'):
                if r.get(k) is not None:
                    row[k] = r[k]
            m.add('state/estate-locations.jsonl', row)
    p_other = m.prov('LEGACY_UNSOURCED', 'data/pomerol.js',
                     quote="BDX_POMEROL_OTHER: the 'Other notable estates' tier (growth 3) of the "
                           "editorial Pomerol collection")
    for n, lid in sparse_ids('pomerol', L.g('BDX_POMEROL_OTHER'), by_id):
        eid = m.estate[lid]
        m.add('state/editorial-memberships.jsonl', {
            'id': S.hid('EditorialCollectionMembership', eid, 'pomerol'), 'estate': eid,
            'collection': 'pomerol', 'tier': '3', 'provenance': p_other})
    for lid, c in sorted(L.g('BDX_COORDS').items()):
        eid = m.estate[lid]
        row = {'id': S.hid('EstateLocation', eid, 'coords.js'), 'estate': eid, 'lat': c[0],
               'lng': c[1], 'validity': current(), 'provenance': legacy_prov(m, 'coords.js')}
        if len(c) > 2:                  # a two-element entry names no method; none is invented
            row['method'] = c[2]
        m.add('state/estate-locations.jsonl', row)


MEDIA = {'.pdf': 'application/pdf', '.txt': 'text/plain', '.html': 'text/html', '.htm': 'text/html',
         '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.doc': 'application/msword',
         '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
         '.xls': 'application/vnd.ms-excel', '.webp': 'image/webp'}
DISC_STATUS = {'EXTRACTED': 'EXTRACTED', 'STORED_NOT_EXTRACTED': 'STORED_ONLY',
               'UNSUPPORTED': 'UNSUPPORTED', 'EXTRACTION_FAILED': 'FAILED'}


EXTERNAL = 'data/audit/m3.10a-external-artifact-registration.jsonl'


def external_registrations():
    """M3.10A: documents acquired outside the discovery crawl, registered by an audited manifest - the fourth
    input beside data/sources.json, the discovery manifest and the reader's hashed paths. Its `registration`
    rows only: sha256 -> row (bytes, media type). Minted by sha256 exactly as every other input's digests."""
    if not os.path.exists(L.ROOT + EXTERNAL):
        return {}
    return {r['sha256']: r for r in L.jsonl_lines(L.ROOT + EXTERNAL) if r['record'] == 'registration'}


def sources_path(r):
    """The manifest row's path relative to sources/, as the reader records it."""
    return r['folder'] + '/' + r['file'] if r['folder'].startswith('pages/') \
        else 'fiches/' + r['folder'] + '/' + r['file']


def documents(m):
    sheets = L.sources_rows()['sheets']
    path_rows = collections.defaultdict(list)            # path -> [(row index, row)]
    for i, r in enumerate(sheets):
        path_rows[sources_path(r)].append((i, r))
    versions = {p: sorted({r['sha1'] for _, r in rows}) for p, rows in path_rows.items()}
    sizes = collections.defaultdict(set)
    for r in sheets:
        sizes[r['sha1']].add(r['bytes'])
    # One sha1, several byte counts: the manifest contradicts itself; the
    # artifact takes no count and each row keeps its own (M6).
    sha1_bytes = {s1: (next(iter(b)) if len(b) == 1 else None) for s1, b in sizes.items()}
    m.size_conflicts = {s1: sorted(b) for s1, b in sizes.items() if len(b) > 1}

    # What the reader hashed (v4, v5) and what failed.
    reads = collections.defaultdict(set)                   # path -> {sha256}
    read_bytes = {}
    failures = {}
    for v in (4, 5):
        for d in L.evidence('decisions-v%d.jsonl' % v):
            rd = d.get('read')
            if rd and rd.get('sha256'):
                p = rd['path'].replace('\\', '/')
                reads[p].add(rd['sha256'])
                read_bytes[rd['sha256']] = rd.get('bytes')
        for d in L.evidence('provenance-failures-v%d.jsonl' % v):
            folder = d['ctx']['folder']
            p = sources_path({'folder': folder, 'file': d['artifact']})
            failures[(p, d['manifest_sha1'])] = d['code']

    # Proven pairs: the harvest hashed the same bytes both ways.
    disc_pair = {}
    disc_loc = collections.defaultdict(list)
    for p in sorted(glob.glob(L.ROOT + 'data/discovery/locations/*.jsonl')):
        for d in L.jsonl_lines(p):
            if d.get('sha1') and d.get('sha256'):
                disc_pair[d['sha1']] = d['sha256']
    disc = {}
    for d in L.jsonl_lines(L.ROOT + 'data/discovery/artifacts.jsonl'):
        disc[d['sha256']] = d
    ext = external_registrations()

    # Joins. sha256 -> sha1 must be one-to-one or the join is refused.
    join = {}
    basis = {}
    for s1, s256 in disc_pair.items():
        join[s1] = s256
        basis[s1] = 'discovery'
    for p, vs in versions.items():
        if len(vs) == 1 and len(reads.get(p, ())) == 1:
            s1, s256 = vs[0], next(iter(reads[p]))
            if s1 in join and join[s1] != s256:
                basis[s1] = 'conflict'
            elif s1 not in join:
                join[s1] = s256
                basis[s1] = 'evidence'
    back = collections.defaultdict(set)
    for s1, s256 in join.items():
        back[s256].add(s1)
    refused = {s1 for s1, b in basis.items() if b == 'conflict'} | \
              {s1 for s256, s1s in back.items() if len(s1s) > 1 for s1 in s1s}
    for s1 in refused:
        join.pop(s1, None)
    m.stat('M2', 'digest joins (discovery-proven, evidence-path rule, refused)', [
        sum(1 for s1 in join if basis[s1] == 'discovery' and s1 in sha1_bytes),
        sum(1 for s1 in join if basis[s1] == 'evidence'), len(refused)])

    # Mint: manifest sha1 first, then every sha256 not joined to one, each sorted.
    art = {}                                                # ('sha1'|'sha256', digest) -> id
    p_mint = rule_prov(m, 'one Artifact per digest; a sha1 and a sha256 are one artifact only when '
                          'proven to hash the same bytes')
    joined256 = {s256: s1 for s1, s256 in join.items() if s1 in sha1_bytes}
    for s1 in sorted(sha1_bytes):
        aid = m.mint('Artifact', 'artifact-by-sha1', s1)
        art[('sha1', s1)] = aid
        idmap(m, 'artifact-by-sha1', s1, aid, p_mint)
        if s1 in join and join[s1] in joined256:
            s256 = join[s1]
            art[('sha256', s256)] = aid
            idmap(m, 'artifact-by-sha256', s256, aid, m.prov(
                'DERIVATION', ACTOR, quote={'discovery': 'the harvest computed sha1 and sha256 over the '
                                            'same fetched bytes',
                                            'evidence': 'the manifest records one version at the path and '
                                            'every v4/v5 read there hashed this sha256'}[basis[s1]]))
    # the external registrations last, so that no earlier digest's id moves when the model is built from scratch
    all256 = sorted(set(disc) | {h for hs in reads.values() for h in hs})
    all256 += sorted(set(ext) - set(all256))
    for s256 in all256:
        if ('sha256', s256) in art:
            continue
        aid = m.mint('Artifact', 'artifact-by-sha256', s256)
        art[('sha256', s256)] = aid
        idmap(m, 'artifact-by-sha256', s256, aid, p_mint)

    read_any = {h for hs in reads.values() for h in hs}
    first_path = {}                                         # sha1 -> the first path, in versions order, holding it
    for pp, vs in versions.items():
        for s1 in vs:
            first_path.setdefault(s1, pp)
    rows = {}
    for (kind, dg), aid in art.items():
        r = rows.setdefault(aid, {'id': aid})
        r[kind] = dg
    for aid, r in rows.items():
        d = disc.get(r.get('sha256'))
        if 'sha1' in r and r['sha1'] in sha1_bytes:
            if sha1_bytes[r['sha1']] is not None:
                r['bytes'] = sha1_bytes[r['sha1']]
            else:
                m.finding(aid, 'CONFLICT', 'the manifest gives %s bytes for this one sha1' % ' and '.join(
                    map(str, m.size_conflicts[r['sha1']])), ACTOR, p_mint)
        elif d:
            r['bytes'] = d['bytes']
        elif read_bytes.get(r.get('sha256')) is not None:
            r['bytes'] = read_bytes[r['sha256']]
        elif r.get('sha256') in ext:
            r['bytes'] = ext[r['sha256']]['bytes']
        r['bytes_available'] = bool(r.get('sha256'))
        if d:
            r['media_type'] = (d.get('content_types') or [None])[0]
            st = DISC_STATUS[d['status']]
            if d.get('ocr') == 'NEEDED_NO_ENGINE':
                st = 'NEEDS_OCR'
            r['extraction_status'] = st
        else:
            r['extraction_status'] = 'EXTRACTED' if r.get('sha256') in read_any else 'PENDING'
            if r.get('sha256') in ext:
                r['media_type'] = ext[r['sha256']]['media_type']
        if 'media_type' not in r:
            p = first_path.get(r.get('sha1'), '')
            r['media_type'] = MEDIA.get(os.path.splitext(p)[1].lower())
            if r['media_type'] is None:
                del r['media_type']
        m.add('identity/artifacts.jsonl', r)
    m.art = art
    m.stat('M2', 'artifacts (manifest sha1, sha256 only)', [
        len(sha1_bytes), sum(1 for r in rows.values() if 'sha1' not in r)])

    # Placements.
    p_man = m.prov('LEGACY_MANIFEST', 'data/sources.json')
    pl_by_path = collections.defaultdict(list)
    def place(kind, value, aid, status, prov, row=None, claimed=None):
        loc = {'kind': kind, 'value': value}
        m.add('document/locators.jsonl', loc)
        pid = S.hid('Placement', kind, value, aid or '', claimed or '')
        pr = {'id': pid, 'locator': loc, 'status': status, 'observed': S.UNKNOWN_VALIDITY,
              'provenance': prov}
        if aid:
            pr['artifact'] = aid
        if row is not None:
            pr['legacy_manifest_row'] = row
        m.add('document/placements.jsonl', pr)
        if kind == 'LOCAL_PATH':
            pl_by_path[value.rsplit('/', 1)[-1]].append(pid)
        return pid
    statuses = collections.Counter()
    for p, rws in sorted(path_rows.items()):
        multi = len(versions[p]) > 1
        read_arts = {art[('sha256', h)] for h in reads.get(p, ())}
        for s1 in versions[p]:
            first = min(i for i, r in rws if r['sha1'] == s1)
            code = failures.get((p, s1))
            aid = art[('sha1', s1)]
            if code:
                st = 'MISSING' if code == 'ARTIFACT_NOT_FOUND' else 'NAME_MISMATCH'
                prov = m.prov('LEGACY_MANIFEST', 'data/sources.json', artifact=aid,
                              quote='the manifest claims these bytes at this path; v4/v5 found %s' % code)
                pid = place('LOCAL_PATH', p, None, st, prov, first, claimed=s1)
                m.finding(pid, 'SOURCE_FAILURE', '%s: %s' % (code, p), ACTOR, prov)
            else:
                # Several versions: only the one proven to be the bytes read is PRESENT.
                st = 'PRESENT' if (not multi or aid in read_arts) else 'BYTES_UNAVAILABLE'
                place('LOCAL_PATH', p, aid, st, p_man, first)
            statuses[st] += 1
        version_arts = {art[('sha1', s1)] for s1 in versions[p]}
        for s256 in sorted(reads.get(p, ())):
            aid = art[('sha256', s256)]
            if aid in version_arts:
                continue
            prov = m.prov('EVIDENCE_DECISION', 'tools/provenance.py', artifact=aid,
                          quote='hashed immediately before the reader read it (v4/v5)')
            place('LOCAL_PATH', p, aid, 'PRESENT', prov)
            statuses['PRESENT (read, not joined)'] += 1
            m.finding(aid, 'IDENTITY_UNCERTAIN',
                      'the bytes read at %s are not proven to be any version the manifest records there '
                      '(%s)' % (p, ', '.join(v[:12] for v in versions[p])), ACTOR, prov)
    urls = collections.defaultdict(set)
    for i, r in enumerate(sheets):
        if r.get('url'):
            urls[(r['url'], r['sha1'])].add(i)
    for (u, s1), idx in sorted(urls.items()):
        place('URL', u, art[('sha1', s1)], 'PRESENT', p_man, min(idx))
        statuses['URL'] += 1
    m.stat('M2', 'placements by status', dict(sorted(statuses.items())))
    m.placements_by_basename = pl_by_path
    return sheets


def legacy_references(m):
    """Every basename a legacy file cites, with its candidate placements."""
    refs = []
    for origin, name in (('field-src.js', 'BDX_FIELD_SRC'), ('cuvee-src.js', 'BDX_CUVEE_SRC')):
        for k, fields in L.g(name).items():
            for fld, b in fields.items():
                refs.append((origin, k, fld, b))
    for origin, name in (('fiches.js', 'BDX_FICHES'), ('cuvees.js', 'BDX_CUVEES'),
                         ('cellar.js', 'BDX_CELLAR'), ('terroir.js', 'BDX_TERROIR'),
                         ('plantings.js', 'BDX_PLANTINGS')):
        for k, rec in L.g(name).items():
            if rec.get('src'):
                # A record src may list several files ('a.pdf, b.pdf'); no manifest
                # filename contains ', ', so each listed name is its own reference.
                for b in rec['src'].split(', '):
                    refs.append((origin, k, None, b))
    pls = {r['id']: r for r in m.rows('document/placements.jsonl')}
    res = collections.Counter()
    for origin, k, fld, b in refs:
        cands = sorted(set(m.placements_by_basename.get(b, [])))
        arts = {pls[c].get('artifact') for c in cands}
        status = 'ACTIVE' if len(arts) == 1 and None not in arts else 'AMBIGUOUS'
        row = {'origin': origin, 'record_key': k, 'basename': b, 'candidates': cands,
               'resolution': status}
        if fld:
            row['field'] = fld
        m.add('document/legacy-references.jsonl', row)
        res[(origin, 'ACTIVE' if status == 'ACTIVE' else
             ('AMBIGUOUS' if cands else 'NO_CANDIDATE'))] += 1
    m.stat('M2', 'legacy filename references', {'%s %s' % k: v for k, v in sorted(res.items())})


def run(m):
    by_id = estates(m)
    estate_state(m, by_id)
    documents(m)
    legacy_references(m)
