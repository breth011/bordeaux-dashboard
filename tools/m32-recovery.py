"""M3.2: existing-data recovery - the candidate audit and what the model may take from it.

    python tools/m32-recovery.py             write data/audit/m32-recovery-candidates.jsonl
    python tools/m32-recovery.py --check     recompute and compare, byte for byte
    python tools/m32-recovery.py --dry-run   the counts and the eligible changes; writes nothing

One row per candidate, per stream, each with its target (the figure: record, field, model
subject), the current value, what is proposed, the source (exact artifact, file name, the
addresses known for those bytes, whether other estates share it), the evidence (locus and the
passage), the classification (m32_recovery.classify), a disposition and the reason.

    A  own-sheet figures: the 1,247 figures with no field source whose value M3.1 found printed in
       the record's own held sheet. Eligible (APPLY_PROVENANCE) only when the field, labelled,
       states exactly the model's value (MODEL_MATCHES). The value is never changed; the figure
       gains the sheet as its own source. Anything else goes to review.

The migration (tools/mig_m6_provenance.value_prov) reads the APPLY_* rows and nothing else. No
clock, no network; the raw sources and the evidence store are only read.
"""
import collections
import re
import importlib.util
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_gap_analysis as A  # noqa: E402
import m32_recovery as R  # noqa: E402
import migration_lib as L  # noqa: E402

OUT = L.ROOT + 'data/audit/m32-recovery-candidates.jsonl'
REGISTER = L.ROOT + 'data/audit/data-gap-register.jsonl'
_spec = importlib.util.spec_from_file_location('xdd', L.ROOT + 'tools/extract-document-dates.py')
X = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(X)


def segments(aid):
    """[(locus, text)] of a held artifact: its discovery extraction, else its own text lines."""
    a = A.by_id('identity/artifacts.jsonl').get(aid) or {}
    sha = a.get('sha256')
    p = A.EXTRACTED + str(sha) + '.json'
    if sha and os.path.exists(p):
        d = json.load(open(p, encoding='utf-8'))
        if d.get('status') == 'EXTRACTED':
            return X.segments_of(d), 'extracted'
    for pl in A.placements_of(aid):
        q = L.ROOT + 'sources/' + pl['locator']['value']
        if pl['locator']['kind'] == 'LOCAL_PATH' and q.endswith('.txt') and os.path.exists(q):
            text = open(q, 'rb').read().decode('utf-8', 'replace')
            return [('l:%d' % i, t) for i, t in enumerate(text.split('\n')) if t.strip()], 'raw_text'
    return None, None


def source_of(aid, basename):
    """The exact source of a figure: the artifact, its file name, the addresses those exact bytes
    were fetched from (the model's URL placements), and the estates that share it."""
    urls = sorted({pl['locator']['value'] for pl in A.placements_of(aid) if pl['locator']['kind'] == 'URL'})
    estates = sorted({a['estate'] for a in A.legacy_attr_by_artifact().get(aid, []) if a.get('estate')})
    a = A.by_id('identity/artifacts.jsonl')[aid]
    return {'artifact': aid, 'sha256': a.get('sha256'), 'filename': basename, 'media_type': a.get('media_type'),
            'urls': urls, 'url_is_exact_artifact': bool(urls), 'type': 'WEB' if urls else 'ON_FILE',
            'estates': estates, 'shared': len(estates) > 1}


def gap_ids():
    return {r['gap_key']: r['gap_id'] for r in L.jsonl_lines(REGISTER)}


def stream_a():
    gaps = gap_ids()
    out = []
    for f in A.unsourced_figures():
        if f['group'] != '1_LOCAL_IDENTIFIABLE':
            continue
        segs, how = segments(f['document'])
        c = R.classify(f['field'], f['value'], segs or [])
        est = A.estate_of_record(f['record'])
        eligible = c['classification'] == 'MODEL_MATCHES'
        row = {'stream': 'A', 'key': 'A|%s|%s|%s' % (f['file'], f['record'], f['field']),
               'gap_id': gaps.get('FIG_UNSOURCED|1_LOCAL_IDENTIFIABLE|%s' % est),
               'target': {'record_file': f['file'], 'record': f['record'], 'field': f['field'], 'subject': f['subject']},
               'current_value': f['value'], 'current_provenance': f['provenance']['id'],
               'proposed': {'provenance': 'DOCUMENT', 'value': 'unchanged'} if eligible else None,
               'source': source_of(f['document'], f.get('basename')),
               'evidence': {'locus': c.get('locus'), 'quote': c.get('quote'), 'text': how, 'labelled_hits': c['hits'],
                            'found': c.get('found')},
               'classification': c['classification'],
               'disposition': 'APPLY_PROVENANCE' if eligible else 'REVIEW',
               'confidence': 'HIGH' if eligible else 'LOW',
               'reason': REASON[c['classification']]}
        out.append(row)
    return out


REASON = {
    'MODEL_MATCHES': 'the field, labelled, states exactly the model value in the record\'s own sheet',
    'MODEL_CONFLICT': 'the field, labelled, states another value: reconciliation, not correction',
    'DUPLICATE_VALUE': 'the sheet states the field with the model value and another value: which applies is not settled',
    'AMBIGUOUS': 'the value is printed, but not with its field\'s label: not evidence of this field',
    'NOT_FOUND': 'no labelled statement of the field in the held text',
    'FIELD_NOT_CHECKABLE': 'the field or value has no deterministic reading (a range, a date, an unknown grape code)',
}


def _host(u):
    from urllib.parse import urlparse
    h = urlparse(u).netloc.lower()
    return h[4:] if h.startswith('www.') else h


def estate_domains():
    """Model estate -> the hosts of its own site (websites.js via targets.json, and the crawl's domain)."""
    t = json.load(open(L.ROOT + 'data/discovery/targets.json', encoding='utf-8'))
    cov = {c['estate']: c for c in json.load(open(L.ROOT + 'data/discovery/coverage.json', encoding='utf-8'))}
    u2e = A.universe_to_estate()
    out = {}
    for e in t['estates']:
        es = u2e.get(e['universe_id'])
        hosts = set()
        if e.get('site'):
            hosts.add(_host(e['site']))
        if cov.get(e['universe_id'], {}).get('domain'):
            hosts.add(_host('https://' + cov[e['universe_id']]['domain']))
        if es:
            out.setdefault(es, set()).update(hosts)
    return out


def discovered():
    """sha256 -> [location rows] and basename -> {sha256} over the discovery store."""
    by_sha, by_name = {}, {}
    import glob
    for p in sorted(glob.glob(L.ROOT + 'data/discovery/locations/*.jsonl')):
        for r in L.jsonl_lines(p):
            u = r.get('final_url') or r.get('url')
            if not r.get('sha256') or not u:
                continue
            by_sha.setdefault(r['sha256'], []).append(r)
            by_name.setdefault(os.path.basename(u.split('?')[0]).lower(), set()).add(r['sha256'])
    return by_sha, by_name


def stream_b():
    """The 71 figures whose own sheet is held with no address, while the crawl fetched the very same
    bytes (same sha256) from a URL. Eligible (APPLY_PLACEMENT) when such a URL is on the estate's own
    site: the address belongs to the exact artifact. A third-party host goes to review; a file of the
    same name with other bytes is another version, recorded, never attached."""
    gaps = gap_ids()
    domains = estate_domains()
    by_sha, by_name = discovered()
    out = []
    for f in A.file_only_figures():
        if not f['url_known']:
            continue
        aid = f['document']
        a = A.by_id('identity/artifacts.jsonl')[aid]
        locs = sorted(by_sha.get(a['sha256'], []), key=lambda r: (r.get('final_url') or r['url'], r['at']))
        estates = sorted({x['estate'] for x in A.legacy_attr_by_artifact().get(aid, []) if x.get('estate')})
        own = set().union(*[domains.get(e, set()) for e in estates]) if estates else set()
        first = [r for r in locs if any(_host(r.get('final_url') or r['url']) == h or
                                        _host(r.get('final_url') or r['url']).endswith('.' + h) for h in own)]
        basename = f['provenance']['legacy_reference']['basename']
        versions = sorted(by_name.get(basename.lower(), set()) - {a['sha256']})
        if first:
            cls, disp = 'EXACT_FIRST_PARTY', 'APPLY_PLACEMENT'
        elif locs:
            cls, disp = 'EXACT_THIRD_PARTY', 'REVIEW'
        else:
            cls, disp = 'AMBIGUOUS_SOURCE', 'REVIEW'
        urls = sorted({r.get('final_url') or r['url'] for r in first})
        out.append({'stream': 'B', 'key': 'B|%s|%s|%s' % (f['file'], f['record'], f['field']),
                    'gap_id': gaps.get('FIG_FILE_ONLY|URL_IN_DISCOVERY'),
                    'target': {'record_file': f['file'], 'record': f['record'], 'field': f['field'], 'subject': f['subject']},
                    'current_value': f['value'], 'current_provenance': f['provenance']['id'],
                    'proposed': {'placements': urls, 'value': 'unchanged'} if disp.startswith('APPLY') else None,
                    'source': {'artifact': aid, 'sha256': a['sha256'], 'filename': basename, 'estates': estates,
                               'estate_hosts': sorted(own), 'urls_same_bytes': sorted({r.get('final_url') or r['url'] for r in locs}),
                               'urls_first_party': urls, 'other_versions': len(versions),
                               'fetched': [{'url': r.get('final_url') or r['url'], 'at': r['at'],
                                            'via': r.get('discovered_via')} for r in first]},
                    'evidence': {'correspondence': 'identical bytes (sha256)' if locs else 'none'},
                    'classification': cls, 'disposition': disp,
                    'confidence': 'HIGH' if disp.startswith('APPLY') else 'LOW',
                    'reason': {'EXACT_FIRST_PARTY': 'the estate\'s own site served exactly these bytes',
                               'EXACT_THIRD_PARTY': 'the same bytes, but from a host that is not the estate\'s site',
                               'AMBIGUOUS_SOURCE': 'no address carries exactly these bytes'}[cls]})
    return out


def local_pdf(aid):
    for pl in sorted(A.placements_of(aid), key=lambda p: p['locator']['value']):
        q = L.ROOT + 'sources/' + pl['locator']['value']
        if pl['locator']['kind'] == 'LOCAL_PATH' and q.lower().endswith('.pdf') and os.path.exists(q):
            return q
    return None


_PDF = {}


def pdf_text(path):
    """(flat text, column text, reader) as tools/sheetreader.py reads the sheet; never OCR."""
    if path not in _PDF:
        import sheetreader as SR
        import pymupdf
        try:
            _PDF[path] = (SR.flat(path), SR.by_columns(path, pages=99), 'pymupdf %s' % pymupdf.VersionBind)
        except Exception as ex:                       # a file pymupdf cannot open
            _PDF[path] = (None, None, 'unreadable: %s' % type(ex).__name__)
    return _PDF[path]


def stream_c():
    """The 411 figures whose record's own held sheet is a PDF with no stored text. The sheet is read
    as the sheet reader reads it - flat, then by columns - and the figure checked with stream A's
    rules. Only the passage that states the figure is kept. Image-only sheets are recorded for OCR
    (M3.2E), never guessed."""
    gaps = gap_ids()
    out = []
    for f in A.unsourced_figures():
        if f['group'] != '3b_TEXT_NOT_STORED':
            continue
        aid = f['document']
        path = local_pdf(aid)
        flat, cols, reader = pdf_text(path) if path else (None, None, 'not held as a local PDF')
        if flat is None:
            doc = 'CORRUPT_OR_UNREADABLE'
            c = {'classification': 'NOT_FOUND', 'hits': 0}
        elif len((flat or '').strip()) < 80 and len((cols or '').strip()) < 80:
            doc = 'IMAGE_ONLY'
            c = {'classification': 'NOT_FOUND', 'hits': 0}
        else:
            c = R.classify(f['field'], f['value'], [('pdf:flat', flat)])
            doc = 'TEXT_EXTRACTABLE'
            if c['classification'] in ('NOT_FOUND', 'AMBIGUOUS'):
                c2 = R.classify(f['field'], f['value'], [('pdf:columns', cols)])
                if c2['classification'] == 'MODEL_MATCHES':
                    c, doc = c2, 'LAYOUT_EXTRACTABLE'
            if c['classification'] == 'NOT_FOUND':
                doc = 'IRRELEVANT_AFTER_REVIEW'
        eligible = c['classification'] == 'MODEL_MATCHES'
        est = A.estate_of_record(f['record'])
        out.append({'stream': 'C', 'key': 'C|%s|%s|%s' % (f['file'], f['record'], f['field']),
                    'gap_id': gaps.get('FIG_UNSOURCED|3b_TEXT_NOT_STORED|%s' % est),
                    'target': {'record_file': f['file'], 'record': f['record'], 'field': f['field'], 'subject': f['subject']},
                    'current_value': f['value'], 'current_provenance': f['provenance']['id'],
                    'proposed': {'provenance': 'DOCUMENT', 'value': 'unchanged'} if eligible else None,
                    'source': source_of(aid, f.get('basename')),
                    'evidence': {'locus': c.get('locus'), 'quote': c.get('quote'), 'text': reader,
                                 'document_class': doc, 'labelled_hits': c['hits'], 'found': c.get('found')},
                    'classification': c['classification'],
                    'disposition': 'APPLY_PROVENANCE' if eligible else ('OCR_CANDIDATE' if doc == 'IMAGE_ONLY' else 'REVIEW'),
                    'confidence': 'HIGH' if eligible else 'LOW',
                    'reason': REASON[c['classification']] if doc not in ('IMAGE_ONLY', 'CORRUPT_OR_UNREADABLE')
                    else {'IMAGE_ONLY': 'the PDF holds no text layer: only OCR could read it (M3.2E)',
                          'CORRUPT_OR_UNREADABLE': 'the held file cannot be opened'}[doc]})
    return out


UNIT = {'alc': '%', 'ph': None, 'yld': 'hl/ha', 'blend': '%'}
YIELD_UNIT = re.compile(r'h[l]\s*/\s*ha|hectolitres?\s+(?:par|per)\s+hectare|hl\s*par\s*ha')


def parse_value(field, raw):
    """(value, unit) in the model's own form, or (None, reason). Never a conversion: the model holds
    alcohol in % vol, yield in hl/ha, pH bare, a blend as grape-code shares."""
    t = R.fold(raw or '')
    if field == 'blend':
        run = R._read_run(t)
        if len(run) < 1 or not 97 <= sum(run.values()) <= 101:
            return None, 'blend shares do not make a whole'
        return {k: (int(v) if float(v).is_integer() else v) for k, v in sorted(run.items())}, '%'
    m = R.VALUE_NUM[field].search(t)
    if not m:
        return None, 'no value of the field\'s shape'
    if field == 'yld' and not YIELD_UNIT.search(t):
        return None, 'UNIT_UNCERTAIN: a yield must be stated per hectare (hl/ha)'
    v = float(m.group(1).replace(',', '.'))
    return (int(v) if v.is_integer() else v), UNIT[field]


def exact_slots():
    """sha256 -> vintage id, for harvested documents mapped exactly to estate, wine and vintage."""
    out = {}
    for sha in A.observation_counts():
        m = A.artifact_mapping(sha)
        if m['estate'] == 'EXACT' and m['wine'] == 'EXACT' and m['vintage'] == 'EXACT':
            out[sha] = 'vt:%s:%d' % (m['wines'][0], m['vintages'][0])
    return out


def harvest_figures():
    """Every figure observation on an exactly mapped document, with its parsed value and how it
    stands against the model: [{sha, vt, field, obs, label, raw, value, unit, state}]."""
    import glob
    slots = exact_slots()
    vint = {'vt:%s:%s' % (v['wine'], v['label']) for v in A.table('identity/vintages.jsonl')}
    pv = A.by_id('cross/provenance.jsonl')
    # the model as it stood before M3.2D: its own recovered values do not count as already held
    canon = {(c['subject'], c['field']): c['value'] for c in A.table('canonical/values.jsonl')
             if (pv[c['provenance']].get('code_state') or {}).get('stream') != 'M3.2D'}
    out = []
    for p in sorted(glob.glob(L.ROOT + 'data/discovery/observations/*.jsonl')):
        for line in open(p, encoding='utf-8'):
            i = line.find(A.ART_KEY) + len(A.ART_KEY)
            sha = line[i:i + 64]
            if sha not in slots:
                continue
            o = json.loads(line)
            lab = R.fold(o.get('label') or '').strip()
            vt = slots[sha]
            field = next((f for f, rx in A.LABEL_FIELD if rx.match(lab)), None)
            if not field:
                continue
            if any(y != vt.rsplit(':', 1)[1] for y in re.findall(r'(?<!\d)(?:19|20)\d\d(?!\d)', lab)):
                state = 'OTHER_YEAR_LABEL'
                value, unit = None, None
            elif not A.VALUE_SHAPE[field].search(R.fold(o.get('value') or '')):
                state, value, unit = 'FIELD_MAPPING_AMBIGUOUS', None, None
            else:
                value, unit = parse_value(field, o.get('value'))
                if value is None:
                    state = 'UNIT_UNCERTAIN' if str(unit).startswith('UNIT') else 'FIELD_MAPPING_AMBIGUOUS'
                elif vt not in vint:
                    state = 'NO_MODEL_VINTAGE'
                elif (vt, field) not in canon:
                    state = 'MODEL_MISSING'
                elif _same(canon[(vt, field)], value):
                    state = 'MODEL_MATCHES'
                else:
                    state = 'MODEL_CONFLICT'
            out.append({'sha': sha, 'vt': vt, 'field': field, 'obs': o['id'], 'label': o.get('label'),
                        'raw': (o.get('value') or '')[:120], 'value': value, 'unit': unit, 'state': state,
                        'lang': o.get('lang'), 'locus': o.get('locus')})
    return out


def _same(a, b):
    if isinstance(a, dict) or isinstance(b, dict):
        return isinstance(a, dict) and isinstance(b, dict) and set(a) == set(b) and \
            all(abs(float(a[k]) - float(b[k])) < 1e-9 for k in a)
    try:
        return abs(float(a) - float(b)) < 1e-9
    except (TypeError, ValueError):
        return False


RED_GRAPES, WHITE_GRAPES = {'CS', 'CF', 'ME', 'PV', 'MA', 'CR'}, {'SB', 'SG', 'SE', 'MU'}
APPROX = re.compile(r'environ|approx\w*|about|around|circa|\bca\.|~|±|potentiel\w*|potential|provisoire|provisional'
                    r'|estim\w*|attendu|expected|pr[ée]vu')


def colour_ok(field, value, wine):
    """A blend must agree with the wine's colour in the model; an unknown colour admits none."""
    if field != 'blend':
        return True, None
    t = (wine or {}).get('type')
    if t in ('RED', 'ROSE'):
        ok = set(value) <= RED_GRAPES
    elif t in ('WHITE_DRY', 'WHITE_SWEET'):
        ok = set(value) <= WHITE_GRAPES
    else:
        return False, 'WINE_COLOUR_UNKNOWN: the model does not hold the wine\'s colour'
    return ok, None if ok else 'WRONG_COLOUR: %s grapes for a %s wine' % (sorted(value), t)


def approximate(field, value, quote):
    """True when the stated value is qualified as approximate, potential or provisional."""
    if field == 'blend' or not quote:
        return False
    q = R.fold(quote)
    for m in re.finditer(R._alt(value), q):
        if APPROX.search(q[max(0, m.start() - 40):m.start()]):
            return True
    return False


def stream_d():
    """The harvested figures the model lacks, on exactly mapped documents (estate, wine and vintage
    all from an accepted decision). A value is eligible (APPLY_VALUE) only when the document itself,
    read with stream A's rules, states it labelled, once, with its unit - and every exactly mapped
    document of that vintage that states the field agrees. Different values: no winner."""
    gaps = gap_ids()
    figs = harvest_figures()
    by_slot = collections.defaultdict(list)
    for f in figs:
        if f['state'] == 'MODEL_MISSING':
            by_slot[(f['vt'], f['field'])].append(f)
    sha2aid = A.sha_to_artifact()
    wine_estate = {r['wine']: r['estate'] for r in A.table('state/estate-wine.jsonl')}
    out = []
    for (vt, field), fs in sorted(by_slot.items()):
        checks = []
        for f in sorted(fs, key=lambda f: (f['sha'], f['obs'])):
            aid = sha2aid.get(f['sha'])
            segs, how = segments(aid)
            if segs is None and local_pdf(aid):
                flat, _, how = pdf_text(local_pdf(aid))
                segs = [('pdf:flat', flat)] if flat else None
            c = R.classify(field, f['value'], segs or [])
            checks.append((f, aid, c, how))
        clear = [(f, aid, c, how) for f, aid, c, how in checks if c['classification'] == 'MODEL_MATCHES']
        values = [f['value'] for f, _, _, _ in clear]
        distinct = []
        for v in values:
            if not any(_same(v, d) for d in distinct):
                distinct.append(v)
        wine = A.by_id('identity/wines.jsonl').get(vt.split(':')[1])
        colour = colour_ok(field, distinct[0], wine) if len(distinct) == 1 else (True, None)
        approx = any(approximate(field, f['value'], c.get('quote')) for f, _, c, _ in clear)
        if clear and len(distinct) == 1 and len(clear) == len(checks) and not colour[0]:
            cls, disp = 'FIELD_MAPPING_AMBIGUOUS', 'REVIEW'
        elif clear and len(distinct) == 1 and len(clear) == len(checks) and approx:
            cls, disp = 'APPROXIMATE_VALUE', 'REVIEW'
        elif clear and len(distinct) == 1 and len(clear) == len(checks):
            cls, disp = 'MODEL_MISSING', 'APPLY_VALUE'
        elif len(distinct) > 1:
            cls, disp = 'CONFLICT_BETWEEN_SHEETS', 'REVIEW'
        elif clear:
            cls, disp = 'AMBIGUOUS', 'REVIEW'            # one sheet states it, another does not as such
        else:
            worst = sorted({c['classification'] for _, _, c, _ in checks})
            cls, disp = ('DUPLICATE_VALUE' if 'DUPLICATE_VALUE' in worst else 'AMBIGUOUS'), 'REVIEW'
        f0, aid0, c0, how0 = (clear or checks)[0]
        est = wine_estate.get(vt.split(':')[1])
        out.append({'stream': 'D', 'key': 'D|%s|%s' % (vt, field), 'gap_id': gaps.get('FILLABLE|%s' % est),
                    'target': {'subject': vt, 'field': field, 'estate': est},
                    'current_value': None,
                    'proposed': {'value': distinct[0], 'unit': f0['unit'],
                                 'rule': 'UNANIMOUS' if len(clear) > 1 else 'ONLY_CANDIDATE'} if disp == 'APPLY_VALUE' else None,
                    'source': {'artifacts': sorted({aid for _, aid, _, _ in checks if aid}),
                               'observations': [{'id': f['obs'], 'artifact': aid, 'label': f['label'], 'raw': f['raw'],
                                                 'value': f['value'], 'unit': f['unit'], 'lang': f['lang'],
                                                 'classification': c['classification'], 'locus': c.get('locus'),
                                                 'quote': c.get('quote'), 'text': how}
                                                for f, aid, c, how in checks]},
                    'evidence': {'locus': c0.get('locus'), 'quote': c0.get('quote'), 'documents': len(checks),
                                 'clear': len(clear)},
                    'classification': cls, 'disposition': disp,
                    'confidence': 'HIGH' if disp == 'APPLY_VALUE' else 'LOW',
                    'colour': colour[1],
                    'reason': {'MODEL_MISSING': 'the model lacks it; the exactly mapped sheet states it labelled, once, with its unit',
                               'FIELD_MAPPING_AMBIGUOUS': colour[1] or 'the field mapping is not established',
                               'APPROXIMATE_VALUE': 'the sheet states it as approximate, potential or provisional: an exact figure would claim more',
                               'CONFLICT_BETWEEN_SHEETS': 'the vintage\'s sheets state different values: no winner (D5)',
                               'AMBIGUOUS': 'not every sheet states it as that field',
                               'DUPLICATE_VALUE': 'the sheet states the field with more than one value'}[cls]})
    return out


def harvest_summary():
    """The stream D quantification over every exactly mapped figure observation."""
    figs = harvest_figures()
    return {'exact_documents': len(exact_slots()),
            'figure_observations': len(figs),
            'by_state': dict(sorted(collections.Counter(f['state'] for f in figs).items())),
            'by_field_state': {'%s|%s' % k: v for k, v in sorted(collections.Counter((f['field'], f['state']) for f in figs).items())}}


def build():
    rows = stream_a() + stream_b() + stream_c() + stream_d()
    for r in rows:
        r['id'] = 'm32_' + L.stable_hash('M32Candidate', r['key'])
        r['extractor'] = R.VERSION
    rows.sort(key=lambda r: (r['stream'], r['key']))
    return rows


def eligible():
    """(record file, record key, field) -> the row, for the APPLY_* rows of the committed audit."""
    if not os.path.exists(OUT):
        return {}
    out = {}
    for r in L.jsonl_lines(OUT):
        if r['disposition'].startswith('APPLY'):
            t = r['target']
            out[(t['record_file'], t['record'], t['field'])] = r
    return out


def main():
    rows = build()
    body = ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n' for r in rows).encode('utf-8')
    if '--check' in sys.argv:
        same = os.path.exists(OUT) and open(OUT, 'rb').read() == body
        print('data/audit/m32-recovery-candidates.jsonl ' + ('is current' if same else 'differs from a fresh run'))
        sys.exit(0 if same else 1)
    for s in sorted({r['stream'] for r in rows}):
        rs = [r for r in rows if r['stream'] == s]
        print('stream %s: %d candidates; %s; eligible %d' % (
            s, len(rs), dict(collections.Counter(r['classification'] for r in rs).most_common()),
            sum(1 for r in rs if r['disposition'].startswith('APPLY'))))
    if '--dry-run' in sys.argv:
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT + '.tmp', 'wb') as f:
        f.write(body)
    os.replace(OUT + '.tmp', OUT)
    print('wrote', os.path.relpath(OUT, L.ROOT))


if __name__ == '__main__':
    main()
