"""M3.1: the analyses behind the data-gap register. Read-only, deterministic, no clock, no network.

Each function recomputes one part of the chain Estate -> Wine -> Vintage -> Document -> Figure
-> Source -> Evidence from the committed state (data/model, data/evidence, data/discovery,
data/audit, the held extraction text) and returns plain data. tools/build-data-gap-register.py
turns the results into register rows; tools/test-data-gap-register.py recomputes them.

Nothing here changes a file, and nothing here resolves a gap: where a check reads a document
(is a figure's value printed in its record's sheet), it only measures whether the existing
evidence is likely to settle the question.
"""
import collections
import glob
import json
import os
import re
import unicodedata

import migration_lib as L

EXTRACTED = L.ROOT + 'sources/discovery/extracted/'
T = L.read_table
_cache = {}


def cached(name, f):
    if name not in _cache:
        _cache[name] = f()
    return _cache[name]


def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')


def table(rel):
    return cached('t:' + rel, lambda: T(rel))


def by_id(rel):
    return cached('i:' + rel, lambda: {r['id']: r for r in table(rel)})


def text_of(sha):
    """The held extracted text of an artifact (folded), or None when none is held."""
    def load():
        if not sha:
            return None
        p = EXTRACTED + sha + '.json'
        if not os.path.exists(p):
            return None
        d = json.load(open(p, encoding='utf-8'))
        if d.get('status') != 'EXTRACTED':
            return None
        parts = [d.get('title') or '']
        parts += [h.get('text') or '' for h in d.get('headings') or []]
        parts += [b.get('text') or '' for b in d.get('blocks') or []]
        parts += [p for p in d.get('pages') or [] if isinstance(p, str)]
        if isinstance(d.get('text'), str):
            parts.append(d['text'])
        return fold('\n'.join(parts))
    return cached('x:' + str(sha), load)


def raw_text(artifact):
    """Text for a plain-text artifact held under sources/ (no extraction record)."""
    for pl in placements_of(artifact['id']):
        if pl['locator']['kind'] == 'LOCAL_PATH':
            p = L.ROOT + 'sources/' + pl['locator']['value']
            if p.endswith('.txt') and os.path.exists(p):
                return fold(open(p, 'rb').read().decode('utf-8', 'replace'))
    return None


def placements_of(aid):
    idx = cached('pl_by_art', lambda: _group(table('document/placements.jsonl'), 'artifact'))
    return idx.get(aid, [])


def _group(rows, key):
    out = collections.defaultdict(list)
    for r in rows:
        if r.get(key):
            out[r[key]].append(r)
    return out


def document_text(aid):
    a = by_id('identity/artifacts.jsonl').get(aid)
    if not a:
        return None
    return text_of(a.get('sha256')) or raw_text(a)


# -- figure -> source -----------------------------------------------------------------------------

FIGURE_FILES = ('data/fiches.js', 'data/cuvees.js')


def figures():
    """Every canonical figure on a record that links a sheet (Phase 6.1's population), with its
    source state: LINKED, FILE_ONLY, AMBIGUOUS or NONE."""
    def build():
        pv = by_id('cross/provenance.jsonl')
        obs = table('observation/observations.jsonl')
        rec_of = {o['subject']: o['extraction']['record'] for o in obs if o['extraction']['file'] in FIGURE_FILES}
        file_of = {o['subject']: o['extraction']['file'] for o in obs if o['extraction']['file'] in FIGURE_FILES}
        linked = {o['subject'] for o in obs if o['field'] == 'document_url'}
        urls = collections.defaultdict(set)
        recovered_url = collections.defaultdict(set)
        for pl in table('document/placements.jsonl'):
            if pl['locator']['kind'] == 'URL' and pl.get('artifact'):
                if (pv[pl['provenance']].get('code_state') or {}).get('stream') == 'M3.2B':
                    recovered_url[pl['artifact']].add(pl['locator']['value'])   # measured as before M3.2
                else:
                    urls[pl['artifact']].add(pl['locator']['value'])
        out = []
        for c in table('canonical/values.jsonl'):
            s = c['subject']
            if s not in linked or s not in rec_of:
                continue
            p = pv[c['provenance']]
            recovered = None
            if (p.get('code_state') or {}).get('stream') == 'M3.2D':
                continue          # a value M3.2D added to the model: no legacy figure, not this population
            if p['kind'] == 'DOCUMENT' and str((p.get('code_state') or {}).get('stream', '')).startswith('M3.2'):
                # recovered by M3.2: measured as it stood before (M3.1 stays reproducible), flagged
                recovered = {'stream': p['code_state']['stream'], 'provenance': p['id']}
                p = pv[p['derived_from'][0]]
            if p['kind'] == 'LEGACY_FIELD_SOURCE':
                state = 'LINKED' if urls[p.get('artifact')] else 'FILE_ONLY'
                if state == 'FILE_ONLY' and recovered_url[p.get('artifact')]:
                    recovered = {'stream': 'M3.2B', 'urls': sorted(recovered_url[p['artifact']])}
            elif p['kind'] == 'LEGACY_AMBIGUOUS_SOURCE':
                state = 'AMBIGUOUS'
            else:
                state = 'NONE'
            out.append({'subject': s, 'record': rec_of[s], 'file': file_of[s], 'field': c['field'],
                        'value': c['value'], 'state': state, 'provenance': p, 'recovered': recovered})
        return sorted(out, key=lambda f: (f['record'], f['field'], f['subject']))
    return cached('figures', build)


def record_refs():
    """(origin file, record key) -> the record-level legacy reference (the sheet the record names)."""
    def build():
        out = {}
        for r in table('document/legacy-references.jsonl'):
            if r['origin'] in ('fiches.js', 'cuvees.js') and not r.get('field'):
                out[('data/' + r['origin'], r['record_key'])] = r
        return out
    return cached('record_refs', build)


def _num_forms(x):
    s = ('%g' % float(x))
    forms = {s, s.replace('.', ',')}
    return forms


def value_printed(field, value, text):
    """True if the figure's exact value is printed in the text, False if not, None if the field is
    not checkable this way (dates and free text). Conservative: a number must stand as a token."""
    if text is None:
        return None
    def tok(n, after=''):
        return any(re.search(r'(?<![\d.,])%s(?![\d])%s' % (re.escape(f), after), text) for f in _num_forms(n))
    try:
        if field == 'alc':
            return tok(value, r'\s*(?:%|°|vol)')        # "13" alone also matches "13 septembre"
        if field == 'yld':
            return tok(value, r'\s*(?:hl|hecto)')
        if field == 'ph':
            return tok(value)
        if field == 'oak':
            return tok(value, r'\s*%')
        if field == 'months':
            return tok(value, r'\s*(?:mois|months?|maanden)')
        if field == 'blend' and isinstance(value, dict) and value:
            return all(tok(v, r'\s*%') for v in value.values())
    except (TypeError, ValueError):
        return None
    return None


def unsourced_figures():
    """The figures shown without a source (state NONE), each placed in one of the brief's six groups:

    1 LOCAL_IDENTIFIABLE   the record names one held document whose text prints the exact value
    2 MULTIPLE_CANDIDATES  the record's name matches several documents
    3 RELATIONSHIP_UNCLEAR one held document with text, but the value is not printed as such (or the
                           field cannot be checked by value: dates, harvest text)
    3b NO_TEXT_HELD        one held document, no extracted text (OCR or unsupported format)
    4 NOT_HELD             the record names a document the model does not hold
    5 UNAVAILABLE          the named document is known to be unobtainable
    6 UNKNOWN              the record names no document"""
    def build():
        refs = record_refs()
        arts = by_id('identity/artifacts.jsonl')
        pls = by_id('document/placements.jsonl')
        out = []
        for f in figures():
            if f['state'] != 'NONE':
                continue
            ref = refs.get((f['file'], f['record']))
            row = dict(f, document=None, candidates=0)
            if not ref:
                row['group'] = '6_UNKNOWN'
            else:
                cands = sorted({pls[c]['artifact'] for c in ref.get('candidates') or [] if c in pls and pls[c].get('artifact')})
                row['candidates'] = len(cands)
                row['basename'] = ref.get('basename')
                if not cands:
                    row['group'] = '4_NOT_HELD'
                elif ref['resolution'] == 'AMBIGUOUS' or len(cands) > 1:
                    shas = {arts[a].get('sha256') or arts[a].get('sha1') for a in cands if a in arts}
                    row['group'] = '2_MULTIPLE_CANDIDATES'
                    row['same_bytes'] = len(shas) == 1
                    row['documents'] = cands
                elif not arts.get(cands[0], {}).get('bytes_available'):
                    row['group'] = '4_NOT_HELD'
                else:
                    row['document'] = cands[0]
                    hit = value_printed(f['field'], f['value'], document_text(cands[0]))
                    if document_text(cands[0]) is None:
                        # held, and the sheet reader reads it, but no text is stored to check
                        row['group'] = '3b_TEXT_NOT_STORED'
                        row['extraction_status'] = arts[cands[0]].get('extraction_status')
                    elif hit:
                        row['group'] = '1_LOCAL_IDENTIFIABLE'
                    else:
                        row['group'] = '3_RELATIONSHIP_UNCLEAR'
                        row['checked'] = hit is not None
            out.append(row)
        return out
    return cached('unsourced', build)


def ambiguous_figures():
    """The 'source unclear' figures: the field's own source name matches several documents.
    same_bytes: every candidate is the same file (a duplicate placement, collapsible)."""
    def build():
        refs = {}
        for r in table('document/legacy-references.jsonl'):
            if r.get('field'):
                refs[(r['origin'], r['record_key'], r['field'])] = r
        arts = by_id('identity/artifacts.jsonl')
        pls = by_id('document/placements.jsonl')
        out = []
        for f in figures():
            if f['state'] != 'AMBIGUOUS':
                continue
            lr = f['provenance'].get('legacy_reference') or {}
            ref = refs.get((lr.get('origin'), lr.get('record_key'), lr.get('field')))
            cands = sorted({pls[c]['artifact'] for c in (ref or {}).get('candidates') or [] if c in pls and pls[c].get('artifact')})
            shas = sorted({arts[a].get('sha256') or arts[a].get('sha1') for a in cands if a in arts})
            texts = [document_text(a) for a in cands]
            printed = [bool(value_printed(f['field'], f['value'], t)) for t in texts]
            out.append(dict(f, basename=lr.get('basename'), documents=cands, same_bytes=len(shas) == 1,
                            printed_in=sum(printed), checkable=any(t is not None for t in texts)))
        return out
    return cached('ambiguous', build)


def file_only_figures():
    """Figures whose own sheet is held but carries no address: can a URL be found for the same
    bytes in the discovery store (fetched online, same sha256)?"""
    def build():
        fetched = discovery_urls()
        out = []
        for f in figures():
            if f['state'] != 'FILE_ONLY':
                continue
            a = by_id('identity/artifacts.jsonl').get(f['provenance'].get('artifact'), {})
            out.append(dict(f, document=a.get('id'), url_known=bool(fetched.get(a.get('sha256')))))
        return out
    return cached('file_only', build)


def discovery_urls():
    def build():
        out = collections.defaultdict(set)
        for p in sorted(glob.glob(L.ROOT + 'data/discovery/locations/*.jsonl')):
            for r in L.jsonl_lines(p):
                if r.get('sha256') and (r.get('final_url') or r.get('url')):
                    out[r['sha256']].add(r.get('final_url') or r.get('url'))
        return out
    return cached('discovery_urls', build)


def estate_of_record(record):
    return record.split('|')[0]


# -- the evidence store, joined to model ids --------------------------------------------------------

def decisions():
    """The latest (v5) decisions with read bytes: [{sha256, decision, code, estate, wine, vintage}],
    model ids resolved exactly as tools/mig_m6_provenance.evidence_links does."""
    def build():
        im = {(r['namespace'], r['legacy_key']): r for r in table('identity/identity-map.jsonl')}
        est = {k[1]: r['stable_id'] for k, r in im.items() if k[0] == 'estate' and r.get('stable_id')}
        out = []
        for d in L.jsonl_lines(L.ROOT + 'data/evidence/decisions-v5.jsonl'):
            rd = d.get('read') or {}
            c = d.get('ctx') or {}
            lid = c.get('target_estate') or c.get('estate')
            w = None
            if c.get('target_wine') and c.get('estate'):
                x = im.get(('wine-by-display-name', '%s|%s' % (c['estate'], c['target_wine'])))
                w = x.get('stable_id') if x else None
            out.append({'sha256': rd.get('sha256'), 'decision': d['decision'], 'code': d['code'],
                        'estate_slug': lid, 'estate': est.get(lid), 'wine_name': c.get('target_wine'),
                        'wine': w, 'vintage': c.get('target_vintage') or c.get('vintage'),
                        'artifact_name': d.get('artifact')})
        return out
    return cached('decisions', build)


def accepted_by_sha():
    def build():
        out = collections.defaultdict(list)
        for d in decisions():
            if d['decision'] == 'ACCEPTED' and d['sha256']:
                out[d['sha256']].append(d)
        return out
    return cached('accepted_by_sha', build)


def legacy_attr_by_artifact():
    return cached('attr_by_art', lambda: _group(table('document/attributions.jsonl'), 'artifact'))


def sha_to_artifact():
    return cached('sha2art', lambda: {a['sha256']: a['id'] for a in table('identity/artifacts.jsonl') if a.get('sha256')})


def universe_to_estate():
    """Phase 3.0 universe id -> model estate id, through targets.json canonical ids and the identity
    map's estate namespace. None where it does not resolve to exactly one."""
    def build():
        im = {r['legacy_key']: r for r in table('identity/identity-map.jsonl') if r['namespace'] == 'estate'}
        t = json.load(open(L.ROOT + 'data/discovery/targets.json', encoding='utf-8'))
        out = {}
        for e in t['estates']:
            ids = {im[c]['stable_id'] for c in e.get('canonical_ids') or [] if c in im and im[c].get('stable_id')}
            out[e['universe_id']] = sorted(ids)[0] if len(ids) == 1 else None
        return out
    return cached('u2e', build)


# -- the harvested observation corpus ---------------------------------------------------------------

ART_KEY = '"artifact": "'


def observation_counts():
    """sha256 -> number of discovery observations (163,582 in all)."""
    def build():
        n = collections.Counter()
        for p in sorted(glob.glob(L.ROOT + 'data/discovery/observations/*.jsonl')):
            for line in open(p, encoding='utf-8'):
                i = line.find(ART_KEY) + len(ART_KEY)
                n[line[i:i + 64]] += 1
        return n
    return cached('obs_counts', build)


def vintage_candidates():
    return cached('vcands', lambda: {r['artifact']: r for r in L.jsonl_lines(L.ROOT + 'data/discovery/vintage-candidates.jsonl')})


def discovery_attribution():
    return cached('dattr', lambda: {r['artifact']: r for r in L.jsonl_lines(L.ROOT + 'data/discovery/attribution.jsonl')})


def artifact_mapping(sha):
    """How one harvested artifact maps to estate, wine and vintage, using only what is recorded:

    estate  EXACT (an accepted evidence decision or a legacy attribution names one estate),
            CONFLICTING (they name several, or the crawl's single strong candidate is another),
            DETERMINISTIC (no exact estate; one strong crawl candidate resolving to one estate),
            AMBIGUOUS (several crawl candidates), UNMAPPABLE
    wine    EXACT (one wine), AMBIGUOUS (several), ABSENT
    vintage EXACT (one, from a decision or attribution), HEADING (one year in the title or
            headings), AMBIGUOUS (several), URL_ONLY (a year only in the address or file name), ABSENT"""
    aid = sha_to_artifact().get(sha)
    es, wn, vt = set(), set(), set()
    for d in accepted_by_sha().get(sha, []):
        if d['estate']:
            es.add(d['estate'])
        if d['wine']:
            wn.add(d['wine'])
        if d['vintage']:
            vt.add(int(d['vintage']))
    for a in legacy_attr_by_artifact().get(aid, []):
        if a.get('estate'):
            es.add(a['estate'])
        if a.get('wine'):
            wn.add(a['wine'])
        if a.get('vintage'):
            y = str(a['vintage']).rsplit(':', 1)[-1]          # a vintage reference vt:<wine>:<year>
            if y.isdigit():
                vt.add(int(y))
    at = discovery_attribution().get(sha) or {}
    cands = at.get('candidates') or []
    strong = [c for c in cands if any(e.get('weight') == 'STRONG' for e in c.get('evidence') or [])]
    u2e = universe_to_estate()
    single = u2e.get(strong[0]['estate']) if len(strong) == 1 and not at.get('multi_estate') else None
    if len(es) == 1:
        estate = 'CONFLICTING' if single and single not in es else 'EXACT'
    elif len(es) > 1:
        estate = 'SHARED'          # the record's own attribution names several estates (6.4: a shared sheet)
    elif single:
        estate = 'DETERMINISTIC'
    elif len(cands) > 1 or at.get('multi_estate'):
        estate = 'AMBIGUOUS'
    else:
        estate = 'UNMAPPABLE'
    wine = 'EXACT' if len(wn) == 1 else 'AMBIGUOUS' if wn else 'ABSENT'
    if len(vt) == 1:
        vintage = 'EXACT'
    elif len(vt) > 1:
        vintage = 'AMBIGUOUS'
    else:
        vc = vintage_candidates().get(sha) or {}
        hy = set(vc.get('heading_years') or []) | set(vc.get('title_years') or [])
        vintage = ('HEADING' if len(hy) == 1 else 'AMBIGUOUS' if hy else
                   'URL_ONLY' if vc.get('url_years') else 'ABSENT')
    return {'estate': estate, 'wine': wine, 'vintage': vintage, 'artifact': aid,
            'estates': sorted(es | ({single} if single else set())), 'wines': sorted(wn), 'vintages': sorted(vt)}


def observation_mapping():
    """The 163,582 observations, counted by how their artifact maps. Summary buckets follow the brief."""
    def build():
        cube = collections.Counter()
        buckets = collections.Counter()
        per_estate = collections.defaultdict(collections.Counter)
        for sha, n in sorted(observation_counts().items()):
            m = artifact_mapping(sha)
            cube[(m['estate'], m['wine'], m['vintage'])] += n
            e, w, v = m['estate'] == 'EXACT', m['wine'] == 'EXACT', m['vintage'] == 'EXACT'
            if m['estate'] == 'CONFLICTING':
                b = 'CONFLICTING'
            elif m['estate'] == 'SHARED':
                b = 'AMBIGUOUS_SHARED_DOCUMENT'
            elif e and w and v:
                b = 'ESTATE_WINE_VINTAGE'
            elif e and w:
                b = 'ESTATE_WINE'
            elif e and v:
                b = 'ESTATE_VINTAGE'
            elif e:
                b = 'ESTATE_ONLY'
            elif m['estate'] == 'DETERMINISTIC':
                b = 'ESTATE_DETERMINISTIC_CANDIDATE'
            elif m['estate'] == 'AMBIGUOUS':
                b = 'AMBIGUOUS'
            elif w:
                b = 'WINE_ONLY'
            elif v:
                b = 'VINTAGE_ONLY'
            else:
                b = 'UNMAPPABLE'
            buckets[b] += n
            if m['estates'] and b in ('ESTATE_DETERMINISTIC_CANDIDATE', 'ESTATE_ONLY', 'ESTATE_VINTAGE', 'ESTATE_WINE'):
                per_estate[m['estates'][0]][b] += n
        return {'total': sum(observation_counts().values()), 'artifacts': len(observation_counts()),
                'buckets': dict(sorted(buckets.items())),
                'cube': {'|'.join(k): v for k, v in sorted(cube.items())},
                'exact': {'estate': sum(v for k, v in cube.items() if k[0] == 'EXACT'),
                          'wine': sum(v for k, v in cube.items() if k[1] == 'EXACT'),
                          'vintage': sum(v for k, v in cube.items() if k[2] == 'EXACT'),
                          'estate_wine_vintage': buckets['ESTATE_WINE_VINTAGE']},
                'per_estate': {k: dict(v) for k, v in sorted(per_estate.items())}}
    return cached('obs_mapping', build)


# Conservative label -> canonical field map for the figures a sheet states as one value.
LABEL_FIELD = [
    ('alc', re.compile(r'^(?:degre(?: d.alcool)?|alcool|alcohol|titre alcoometrique|tav|alc\.?)\b')),
    ('ph', re.compile(r'^ph\b')),
    ('yld', re.compile(r'^(?:rendement|yield)\b')),
    ('blend', re.compile(r'^(?:assemblage|blend)\b')),
]
# A label is not enough: crawled label lines carry table headers, units and neighbouring cells.
# The value must have the shape of the field before it counts.
VALUE_SHAPE = {
    'alc': re.compile(r'(?<![\d.,])1[0-6](?:[.,]\d{1,2})?\s*(?:%|°|vol)'),
    'ph': re.compile(r'(?<![\d.,])[23][.,]\d{1,2}(?![\d])'),
    'yld': re.compile(r'(?<![\d.,])\d{1,2}(?:[.,]\d)?\s*(?:hl|hecto)'),
    'blend': re.compile(r'(?:merlot|cabernet|sauvignon|semillon|petit verdot|malbec|carmenere|muscadelle)'
                        r'[^%]{0,40}\d{1,3}(?:[.,]\d)?\s*%|\d{1,3}(?:[.,]\d)?\s*%[^%]{0,12}'
                        r'(?:merlot|cabernet|sauvignon|semillon|petit verdot|malbec|carmenere|muscadelle)'),
}


def fillable_slots():
    """Vintage figures the model lacks, for which an exactly mapped harvested document (estate,
    wine and vintage all EXACT) carries an observation of that field: data present, unconnected."""
    def build():
        have = collections.defaultdict(set)
        pv = by_id('cross/provenance.jsonl')
        for c in table('canonical/values.jsonl'):
            if (pv[c['provenance']].get('code_state') or {}).get('stream') == 'M3.2D':
                continue          # recovered by M3.2D: measured as it stood before (still a fillable slot)
            if c['subject'].startswith('vt:'):
                have[c['subject']].add(c['field'])
        vintages = {'vt:%s:%s' % (v['wine'], v['label']) for v in table('identity/vintages.jsonl')}
        exact = {}
        for sha in observation_counts():
            m = artifact_mapping(sha)
            if m['estate'] == 'EXACT' and m['wine'] == 'EXACT' and m['vintage'] == 'EXACT':
                exact[sha] = 'vt:%s:%d' % (m['wines'][0], m['vintages'][0])
        slots = collections.defaultdict(set)
        for p in sorted(glob.glob(L.ROOT + 'data/discovery/observations/*.jsonl')):
            for line in open(p, encoding='utf-8'):
                i = line.find(ART_KEY) + len(ART_KEY)
                sha = line[i:i + 64]
                if sha not in exact:
                    continue
                o = json.loads(line)
                lab = fold(o.get('label') or '').strip()
                val = fold(o.get('value') or '')
                vt = exact[sha]
                other_year = [y for y in re.findall(r'(?<!\d)(?:19|20)\d\d(?!\d)', lab) if y != vt.rsplit(':', 1)[1]]
                if other_year:
                    continue                                 # "Rendement 2023" on the 2024 sheet
                for field, rx in LABEL_FIELD:
                    if rx.match(lab) and VALUE_SHAPE[field].search(val):
                        if vt in vintages and field not in have[vt]:
                            slots[(vt, field)].add(sha)
        return {'%s|%s' % k: sorted(v) for k, v in sorted(slots.items())}
    return cached('fillable', build)


# -- OCR --------------------------------------------------------------------------------------------

def ocr_backlog():
    """Every artifact the model marks NEEDS_OCR, with what it is for and which gap it could close."""
    def build():
        arts = by_id('identity/artifacts.jsonl')
        refs_by_art = collections.defaultdict(list)
        pls = by_id('document/placements.jsonl')
        for (_, rk), r in record_refs().items():
            for c in r.get('candidates') or []:
                if c in pls and pls[c].get('artifact'):
                    refs_by_art[pls[c]['artifact']].append(rk)
        unsourced_by_rec = collections.Counter(f['record'] for f in unsourced_figures())
        vdocs = json.load(open(L.MODEL + 'derived/vintage-documents.json', encoding='utf-8'))
        sole = collections.defaultdict(list)
        for vt, ds in vdocs.items():
            if len(ds) == 1:
                sole[ds[0]].append(vt)
        out = []
        for aid, a in sorted(arts.items()):
            if a.get('extraction_status') != 'NEEDS_OCR':
                continue
            m = artifact_mapping(a['sha256']) if a.get('sha256') else {'estates': [], 'wines': [], 'vintages': []}
            recs = sorted(set(refs_by_art.get(aid, [])))
            names = sorted({os.path.basename(pl['locator']['value']) for pl in placements_of(aid)})
            gaps = {'record_sheet_of': recs,
                    'unsourced_figures_on_those_records': sum(unsourced_by_rec[r] for r in recs),
                    'only_document_of_vintages': sorted(sole.get(aid, []))}
            benefit = ('HIGH' if gaps['unsourced_figures_on_those_records'] >= 10 else
                       'MEDIUM' if gaps['unsourced_figures_on_those_records'] or gaps['only_document_of_vintages']
                       else 'LOW' if recs else 'NONE')
            out.append({'artifact': aid, 'names': names[:3], 'estates': m['estates'], 'wines': m['wines'],
                        'vintages': m['vintages'], 'gaps': gaps, 'benefit': benefit})
        return out
    return cached('ocr', build)


# -- discovery and sources --------------------------------------------------------------------------

def discovery_coverage():
    def build():
        cov = json.load(open(L.ROOT + 'data/discovery/coverage.json', encoding='utf-8'))
        t = json.load(open(L.ROOT + 'data/discovery/targets.json', encoding='utf-8'))
        u2e = universe_to_estate()
        no_site = [{'universe_id': e['universe_id'], 'name': e['name'], 'estate': u2e.get(e['universe_id'])}
                   for e in t['estates'] if not e.get('site')]
        return {'coverage': [dict(c, model_estate=u2e.get(c['estate'])) for c in cov], 'no_site': no_site}
    return cached('dcov', build)


def unincorporated_documents():
    """Harvested PDFs with one strong estate candidate, never put to the evidence store and not in
    the model's attributions: documents held but not connected. Per estate, with how many carry one
    heading year that is a vintage of the estate's wines with no document."""
    def build():
        reviewed = {d['sha256'] for d in decisions() if d['sha256']}
        vdocs = json.load(open(L.MODEL + 'derived/vintage-documents.json', encoding='utf-8'))
        wvint = json.load(open(L.MODEL + 'derived/wine-vintages.json', encoding='utf-8'))
        ew = collections.defaultdict(set)
        for r in table('state/estate-wine.jsonl'):
            ew[r['estate']].add(r['wine'])
        out = {}
        for a in L.jsonl_lines(L.ROOT + 'data/discovery/artifacts.jsonl'):
            if a.get('media') != 'pdf' or a['sha256'] in reviewed:
                continue
            aid = sha_to_artifact().get(a['sha256'])
            if aid and legacy_attr_by_artifact().get(aid):
                continue
            m = artifact_mapping(a['sha256'])
            if m['estate'] != 'DETERMINISTIC':
                continue
            e = m['estates'][0]
            row = out.setdefault(e, {'documents': 0, 'heading_year': 0, 'fills_documentless_vintage': 0, 'examples': []})
            row['documents'] += 1
            vc = vintage_candidates().get(a['sha256']) or {}
            hy = set(vc.get('heading_years') or []) | set(vc.get('title_years') or [])
            if len(hy) == 1:
                row['heading_year'] += 1
                y = str(list(hy)[0])
                if any(y in wvint.get(w, []) and not vdocs.get('vt:%s:%s' % (w, y)) for w in ew[e]):
                    row['fills_documentless_vintage'] += 1
            if len(row['examples']) < 3:
                row['examples'].append(aid or a['sha256'][:16])
        return {k: out[k] for k in sorted(out)}
    return cached('unincorporated', build)


# -- identity, estates, wines, evidence ---------------------------------------------------------------

def identity_ambiguities():
    return [r for r in table('identity/identity-map.jsonl') if r['status'] == 'AMBIGUOUS']


def findings():
    return sorted(table('cross/findings.jsonl'), key=lambda f: f['id'])


def unlisted_wines():
    out = {}
    for d in decisions():
        if d['code'] == 'UNLISTED_WINE':
            k = (d['estate_slug'] or '', d['wine_name'] or '')
            r = out.setdefault(k, {'decisions': 0, 'vintages': set(), 'examples': []})
            r['decisions'] += 1
            if d['vintage']:
                r['vintages'].add(int(d['vintage']))
            if len(r['examples']) < 2:
                r['examples'].append(d['artifact_name'])
    return {k: dict(v, vintages=sorted(v['vintages'])) for k, v in sorted(out.items())}


def duplicate_estate_names():
    names = collections.defaultdict(set)
    for n in table('identity/names.jsonl'):
        if n['subject'].startswith('es_') and n['kind'] == 'CURRENT':
            names[fold(n['name'])].add(n['subject'])
    return {k: sorted(v) for k, v in sorted(names.items()) if len(v) > 1}


def wines_without_estate():
    linked = {r['wine'] for r in table('state/estate-wine.jsonl')}
    return sorted(w['id'] for w in table('identity/wines.jsonl') if w['id'] not in linked)


def vintage_document_counts():
    vdocs = json.load(open(L.MODEL + 'derived/vintage-documents.json', encoding='utf-8'))
    out = collections.Counter()
    for v in table('identity/vintages.jsonl'):
        n = len(vdocs.get('vt:%s:%s' % (v['wine'], v['label']), []))
        out['none' if n == 0 else 'one' if n == 1 else 'several'] += 1
    return dict(sorted(out.items()))


def unsourced_canonical():
    pv = by_id('cross/provenance.jsonl')
    return [c for c in table('canonical/values.jsonl') if pv[c['provenance']]['kind'] == 'LEGACY_UNSOURCED']


def unavailable_accepted():
    arts = by_id('identity/artifacts.jsonl')
    out = []
    for d in decisions():
        if d['decision'] == 'ACCEPTED' and d['sha256']:
            aid = sha_to_artifact().get(d['sha256'])
            if not aid or not arts[aid].get('bytes_available'):
                out.append(d)
    return out


def m3_candidates():
    return list(L.jsonl_lines(L.ROOT + 'data/audit/historical-m3-candidates.jsonl'))
