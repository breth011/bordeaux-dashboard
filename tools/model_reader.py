"""Phase 4: the new reader. Reads the normalized model (data/model/) and
projects it back into the shapes the legacy files have, so the two can be
compared (M8) and read side by side (M9).

    import model_reader as R
    R.project()          {legacy file: {GLOBAL: value}}
    R.discovery_observations()   the harvested observations, in the
                                 Observation shape, read in place

The projection uses, for each legacy value, what the model treats as its
record: the CanonicalValue for taxonomy class A fields, the Observation
otherwise, identity and state tables for structure (ids, names, ranks,
classification, locations), the identity map for legacy keys, and the
provenance records that keep unresolved and empty records verbatim. It
never reads a legacy data file.
"""
import collections
import glob
import json

import migration_lib as L
import model_schema as S

TYPE_BACK = {'RED': 'red', 'WHITE_DRY': 'white', 'WHITE_SWEET': 'sweet', 'ROSE': 'rose'}
LIST_FILES = {'saintemilion.js': 'stem', 'pomerol.js': 'pomerol', 'crubourgeois.js': 'bourgeois',
              'cruartisan.js': 'artisan'}
FIELD_META = {'ttl', 'ntl', 'dtl', 'ftl', 'wtl', 'sugl', 'tau'}


class Model:
    def __init__(self, root=None):
        self.root = root or L.MODEL
        self.t = {}

    def rows(self, rel):
        if rel not in self.t:
            p = self.root + rel
            self.t[rel] = L.jsonl_lines(p) if glob.glob(p) else []
        return self.t[rel]


def project(model=None, classifications=None):
    M = model or Model()
    out = collections.defaultdict(dict)
    im = collections.defaultdict(dict)                 # namespace -> legacy key -> row
    for r in M.rows('identity/identity-map.jsonl'):
        im[r['namespace']][r['legacy_key']] = r
    est_back = {r['stable_id']: k for k, r in im['estate'].items() if r.get('stable_id')}
    vint_back = {}
    for ns in ('estate|vintage', 'estate|slug|vintage'):
        for k, r in im[ns].items():
            if r.get('stable_id'):
                vint_back.setdefault(r['stable_id'], []).append(k)
    prov = {p['id']: p for p in M.rows('cross/provenance.jsonl')}
    names = collections.defaultdict(list)
    for n in M.rows('identity/names.jsonl'):
        names[n['subject']].append(n)
    wines = {w['id']: w for w in M.rows('identity/wines.jsonl')}
    rels = {r['id']: r for r in M.rows('state/estate-wine.jsonl')}
    grand = {k: r['stable_id'] for k, r in im['grand-vin'].items()}
    obs_by = collections.defaultdict(list)
    for o in M.rows('observation/observations.jsonl'):
        obs_by[(o['extraction']['file'], o['extraction']['record'])].append(o)
    canon = {(c['subject'], c['field']): c for c in M.rows('canonical/values.jsonl')}

    def value(o):
        c = canon.get((o['subject'], o['field']))
        return c['value'] if c else o['value']

    def file_of_estate(eid):
        acts = [prov[n['provenance']]['actor'] for n in names[eid]]
        return [a[5:] for a in acts if a.startswith('data/')][0]

    # ---- classification editions back to the legacy class ids
    classes = classifications or {}
    ed_cls = {S.hid('ClassificationEdition', c, 'dataset'): c for c in classes}
    tiers = {c: {t['label']: t['growth'] for t in v['tiers']} for c, v in classes.items()}
    mem_by_wine = collections.defaultdict(list)
    for r in M.rows('state/classification-memberships.jsonl'):
        mem_by_wine[r['wine']].append(r)
    edit_by_est = {r['estate']: r for r in M.rows('state/editorial-memberships.jsonl')}
    app = {a['id']: a['name'] for a in M.rows('state/appellations.jsonl')}
    app_by_wine = collections.defaultdict(list)
    for r in M.rows('state/appellation-memberships.jsonl'):
        app_by_wine[r['wine']].append((prov[r['provenance']]['actor'], app[r['appellation']]))
    loc = collections.defaultdict(list)
    for r in M.rows('state/estate-locations.jsonl'):
        loc[r['estate']].append(r)

    # ---- estate files and compact lists
    est_files = collections.defaultdict(list)
    lists = collections.defaultdict(list)
    for e in M.rows('identity/estates.jsonl'):
        eid, lid = e['id'], est_back[e['id']]
        f = file_of_estate(eid)
        name = [n['name'] for n in names[eid] if n['kind'] == 'CURRENT'][0]
        wid = grand.get(lid)
        mems = [m for m in mem_by_wine.get(wid, [])]
        if f in LIST_FILES and not any(o for o in obs_by.get(('data/' + f, lid), [])):
            cls = LIST_FILES[f]
            if cls == 'pomerol':
                lists[('pomerol.js', 'BDX_POMEROL_OTHER', None)].append(name)
            else:
                m = [x for x in mems if ed_cls.get(x['edition']) == cls][0]
                g = tiers[cls][m['rank']]
                if cls == 'stem':
                    lists[('saintemilion.js', 'BDX_STEM_GCC', None)].append(name)
                elif cls == 'bourgeois':
                    tier = {1: 'exceptionnel', 2: 'superieur', 3: 'bourgeois'}[g]
                    lists[('crubourgeois.js', 'BDX_CRU_BOURGEOIS', tier)].append(
                        [name, m['appellation_listed']])
                else:
                    lists[('cruartisan.js', 'BDX_CRU_ARTISAN', 'current')].append(
                        [name, m['appellation_listed']])
            continue
        rec = {'id': lid, 'name': name}
        own = [x for x in mems if prov[x['provenance']]['actor'] == 'data/' + f]
        cls = ed_cls[own[0]['edition']] if own else edit_by_est[eid]['collection']
        if cls not in ('1855', 'sauternes'):
            rec['cls'] = cls
        rec['growth'] = tiers[cls][own[0]['rank']] if own else int(edit_by_est[eid]['tier'])
        rec['cat'] = TYPE_BACK[wines[wid]['type']]
        if cls == 'graves':
            rec['wine'] = 'red and white' if lid in im['graves-white'] else rec['cat']
        for actor, a in app_by_wine.get(wid, []):
            if actor == 'data/' + f:
                rec['appellation'] = a
        for r in loc[eid]:
            if r.get('method') == 'data/' + f:
                for k in ('commune', 'lat', 'lng'):
                    if k in r:
                        rec[k] = r[k]
        for o in obs_by.get(('data/' + f, lid), []):
            rec[o['field']] = o['value']
        for k in im['second-by-name']:
            if k.split('|', 1)[0] == lid:
                rec['second'] = k.split('|', 1)[1]
        est_files[f].append(rec)
    for f, recs in est_files.items():
        out[f]['BDX_CHATEAUX'] = sorted(recs, key=lambda r: r['id'])
    for (f, g, sub), v in lists.items():
        if sub:
            out[f].setdefault(g, {})[sub] = sorted(v)
        else:
            out[f][g] = sorted(v)
    cross = [est_back[rels_e] for rels_e in []]
    for wid, ms in mem_by_wine.items():
        eds = {ed_cls.get(m['edition']) for m in ms}
        if {'1855', 'graves'} <= eds:
            cross.append([k for k, v in grand.items() if v == wid][0])
    out['graves.js']['BDX_GRAVES_CROSSLIST'] = sorted(cross)

    # ---- the other wines
    cw = collections.defaultdict(list)
    for k, r in im['wine-by-slug'].items():
        lid, slug = k.split('|')
        wid = r['stable_id']
        if prov[r['provenance']]['actor'] == 'tools/m36d-cuvee.py':
            continue        # M3.6D's Cuvée Mongravey is in no legacy file: it has no cuvees.js shape (no legacy role)
        rel = [x for x in rels.values() if x['wine'] == wid][0]
        ra = [x for x in M.rows('state/rank-assertions.jsonl') if x['relationship'] == rel['id']
              and prov[x['provenance']]['actor'] == 'data/cuvees.js']
        w = {'slug': slug, 'name': [n['name'] for n in names[wid]][0],
             'role': ra[0]['legacy_term']}
        if wines[wid]['type'] in TYPE_BACK:
            w['colour'] = TYPE_BACK[wines[wid]['type']]
        cw[lid].append(w)
    out['cuvees.js']['BDX_CUVEE_WINES'] = {k: sorted(v, key=lambda w: w['slug']) for k, v in cw.items()}

    # ---- the vintage-keyed files
    def records(file, glob_name, fields_from_meta=True):
        res = {}
        for (f, key), os_ in obs_by.items():
            if f != 'data/' + file:
                continue
            rec = {}
            for o in os_:
                ex = o['extraction']
                rec[o['field']] = value(o)
                for k, v in (ex.get('field_meta') or {}).items():
                    rec[k] = v
                for k, v in (ex.get('record_meta') or {}).items():
                    rec[k] = v
            res[key] = rec
        return res
    out['fiches.js']['BDX_FICHES'] = records('fiches.js', 'BDX_FICHES')
    out['cuvees.js']['BDX_CUVEES'] = records('cuvees.js', 'BDX_CUVEES')
    for name, file in (('BDX_FICHE_URL', 'fiches-url.js'), ('BDX_CUVEE_URL', 'cuvee-url.js')):
        out[file][name] = {k: r['document_url'] for k, r in records(file, name).items()}
    out['ratings.js']['BDX_RATINGS'] = {k: r['rating'] for k, r in records('ratings.js', '').items()}
    cel = {}
    for (f, key), os_ in obs_by.items():
        if f == 'data/cellar.js':
            o = os_[0]
            rec = {'v': o['value']}
            for k in ('locus', 'lang'):
                if k in o:
                    rec['label' if k == 'locus' else k] = o[k]
            rec.update(o['extraction'].get('record_meta') or {})
            rec.update(o['extraction'].get('other') or {})
            cel[key] = rec
    out['cellar.js']['BDX_CELLAR'] = cel
    sc = {}
    for (f, key), os_ in obs_by.items():
        if f == 'data/overrides.js':
            rec = {o['field']: o['value'] for o in os_}
            rec['src'] = os_[0]['extraction']['record_meta']['src']
            sc[key] = rec
    out['overrides.js']['BDX_SCORES'] = sc
    np_ = collections.defaultdict(list)
    for r in M.rows('state/vintage-statements.jsonl'):
        wid, lab = r['vintage'][3:].rsplit(':', 1)
        lid = [k for k, v in grand.items() if v == wid][0]
        np_[lid].append(int(lab))
    out['overrides.js']['BDX_NOT_PRODUCED'] = {k: sorted(v) for k, v in np_.items()}
    for name, file, field in (('BDX_PLANTINGS', 'plantings.js', 'blend'), ('BDX_TERROIR', 'terroir.js', 'v')):
        res = {}
        for (f, key), os_ in obs_by.items():
            if f == 'data/' + file:
                o = os_[0]
                rec = {field: o['value']}
                if 'locus' in o:
                    rec['label'] = o['locus']
                if 'lang' in o:
                    rec['lang'] = o['lang']
                rec.update(o['extraction'].get('record_meta') or {})
                rec.update(o['extraction'].get('other') or {})
                res[key] = rec
        out[file][name] = res
    # field provenance files from the legacy references
    for name, file, origin in (('BDX_FIELD_SRC', 'field-src.js', 'field-src.js'),
                               ('BDX_CUVEE_SRC', 'cuvee-src.js', 'cuvee-src.js')):
        res = collections.defaultdict(dict)
        for r in M.rows('document/legacy-references.jsonl'):
            if r['origin'] == origin:
                res[r['record_key']][r['field']] = r['basename']
        out[file][name] = dict(res)
    nl = collections.defaultdict(dict)
    obs_id = {o['id']: o for o in M.rows('observation/observations.jsonl')}
    for t in M.rows('canonical/translations.jsonl'):
        o = obs_id[t['source_observation']]
        nl[o['extraction']['record']][o['field']] = t['text']
    out['fiches-nl.js']['BDX_FICHES_NL'] = dict(nl)
    coords = {}
    for eid, rs in loc.items():
        for r in rs:
            if prov[r['provenance']]['actor'] == 'data/coords.js':
                coords[est_back[eid]] = [r['lat'], r['lng']] + ([r['method']] if 'method' in r else [])
    out['coords.js']['BDX_COORDS'] = coords
    sites = {}
    for r in M.rows('state/source-estate.jsonl'):
        cs = prov[r['provenance']]['code_state']
        sites[est_back[r['estate']]] = [cs['url'], cs['tag']]
    out['websites.js']['BDX_SITES'] = sites

    # ---- records kept verbatim (unresolved, empty, orphan translations)
    for p in prov.values():
        cs = p.get('code_state') or {}
        if cs.get('unresolved'):
            f = cs['legacy_file'][5:]
            out[f].setdefault(cs['global'], {})[cs['key']] = json.loads(p['quote'])
        elif 'empty_record' in cs:
            out[cs['legacy_file'][5:]][cs['global']][cs['key']] = cs['empty_record']
        elif cs.get('orphan_translation'):
            out['fiches-nl.js']['BDX_FICHES_NL'].setdefault(cs['key'], {})[cs['field']] = p['quote']

    # ---- the manifest
    arts = {a['id']: a for a in M.rows('identity/artifacts.jsonl')}
    rows = {}
    est_of_att = {}
    # the manifest's rows only: an attribution whose provenance is not the manifest (M3.4B's audited
    # links) is no row of data/sources.json
    manifest = lambda a: prov[a['provenance']]['kind'] == 'LEGACY_MANIFEST'
    for a in M.rows('document/attributions.jsonl'):
        if not manifest(a):
            continue
        cs = prov[a['provenance']]['code_state']
        est_of_att[cs['row']] = est_back.get(a.get('estate'))
    for t in ('document/attributions.jsonl', 'document/assessments.jsonl'):
        for a in M.rows(t):
            if not manifest(a):
                continue
            p = prov[a['provenance']]
            cs = p['code_state']
            i = cs['row']
            if i in rows:
                continue
            path = p['locator']['value']
            folder, file = path.rsplit('/', 1)
            if folder.startswith('fiches/'):
                folder = folder[7:]
            art = arts[p['artifact']]
            rows[i] = {'file': file, 'folder': folder, 'estate': est_of_att.get(i),
                       'estateName': cs.get('estateName'), 'wine': cs.get('wine'),
                       'role': cs['role'], 'colour': cs.get('colour'), 'year': cs.get('year'),
                       'bytes': cs.get('bytes', art.get('bytes')), 'sha1': art['sha1'], 'url': cs.get('url')}
            for k in ('slug', 'how'):
                if k in cs:
                    rows[i][k] = cs[k]
            if p.get('quote') is not None:
                rows[i]['note'] = p['quote']
    doc = [p['code_state']['documentation'] for p in prov.values()
           if 'documentation' in (p.get('code_state') or {})][0]
    sj = dict(doc)
    sj['sheets'] = [rows[i] for i in sorted(rows)]
    out['sources.json'] = sj
    return {k: dict(v) if not isinstance(v, dict) else v for k, v in out.items()}


def discovery_observations():
    """The harvested observations in the Observation shape, read in place;
    the artifact through the identity map (artifact-by-sha256)."""
    art = {}
    for r in L.jsonl_lines(L.MODEL + 'identity/identity-map.jsonl'):
        if r['namespace'] == 'artifact-by-sha256':
            art[r['legacy_key']] = r['stable_id']
    for p in sorted(glob.glob(L.ROOT + 'data/discovery/observations/*.jsonl')):
        for d in L.jsonl_lines(p):
            yield {'source_record': d, 'artifact': art.get(d.get('artifact') or d.get('sha256')),
                   'subject_status': 'UNRESOLVED'}
