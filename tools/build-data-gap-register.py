"""M3.1: the resolution-first data-gap register.

    python tools/build-data-gap-register.py             write data/audit/data-gap-register.jsonl
    python tools/build-data-gap-register.py --check     recompute and compare, byte for byte
    python tools/build-data-gap-register.py --summary   the tier and category counts, nothing written

Audit only. Every row is a gap measured from the committed state by tools/data_gap_analysis.py,
classified by one primary category and one state (MISSING, UNMAPPED, CONFLICTING, UNRESOLVED),
given the one method that would resolve it, an effort bucket for Claude Code to carry it out, a
confidence, a cascading benefit and its dependencies; the tier (R1-R5, or DEFERRED for what is
not a gap) follows from those by the rules in tier(). Nothing is fixed, fetched or OCR'd.
"""
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_gap_analysis as A  # noqa: E402
import migration_lib as L  # noqa: E402

OUT = L.ROOT + 'data/audit/data-gap-register.jsonl'

CATEGORIES = ['MAPPING_GAP', 'SOURCE_GAP', 'EVIDENCE_GAP', 'CONFLICT', 'DISCOVERY_GAP', 'EXTRACTION_GAP',
              'IDENTITY_GAP', 'TEMPORAL_GAP', 'COVERAGE_GAP', 'UNAVAILABLE', 'NOT_A_GAP']
STATES = ['MISSING', 'UNMAPPED', 'CONFLICTING', 'UNRESOLVED', 'NONE']
METHODS = ['DETERMINISTIC_MAPPING', 'EXISTING_EVIDENCE_REVIEW', 'DUPLICATE_COLLAPSE', 'PROVENANCE_REPAIR', 'OCR',
           'TARGETED_LOCAL_SEARCH', 'TARGETED_FIRST_PARTY_SCRAPE', 'MANUAL_DECISION', 'MODEL_MAPPING',
           'NEW_SOURCE_REQUIRED', 'NO_ACTION', 'UNKNOWN']
EFFORTS = ['XS', 'S', 'M', 'L', 'XL', 'UNKNOWN']
LEVELS = ['HIGH', 'MEDIUM', 'LOW', 'NONE']
DEPENDENCIES = ['D2', 'D5', 'LAPARDE_IDENTITY', 'MANUAL_REVIEW', 'OCR', 'SOURCE_DISCOVERY', 'PARENT_MAPPING',
                'IDENTITY_MAPPING', 'EXTERNAL_SOURCE', 'D1', 'NONE']
BLOCKING_DEPS = {'D1', 'D2', 'D5', 'LAPARDE_IDENTITY'}
TIERS = ['R1', 'R2', 'R3', 'R4', 'R5', 'DEFERRED']
NEW_DATA_METHODS = {'TARGETED_FIRST_PARTY_SCRAPE', 'NEW_SOURCE_REQUIRED'}


# -- the rules -------------------------------------------------------------------------------------

def effort(method, n):
    """The bucket for Claude Code to carry out the resolution (not to discover it), by method and size."""
    if method in ('DETERMINISTIC_MAPPING', 'PROVENANCE_REPAIR', 'DUPLICATE_COLLAPSE', 'MODEL_MAPPING'):
        return 'XS' if n <= 30 else 'S' if n <= 300 else 'M' if n <= 3000 else 'L'
    if method == 'EXISTING_EVIDENCE_REVIEW':
        return 'XS' if n <= 5 else 'S' if n <= 40 else 'M' if n <= 300 else 'L' if n <= 2000 else 'XL'
    if method == 'TARGETED_LOCAL_SEARCH':
        return 'S' if n <= 20 else 'M' if n <= 200 else 'L'
    if method == 'OCR':
        return 'S' if n <= 3 else 'M' if n <= 30 else 'L'
    if method == 'TARGETED_FIRST_PARTY_SCRAPE':
        return 'S' if n <= 10 else 'M' if n <= 60 else 'L'
    if method == 'NO_ACTION':
        return 'XS'
    return 'UNKNOWN'                                   # MANUAL_DECISION, NEW_SOURCE_REQUIRED, UNKNOWN


def cascade(n, scale=(20, 5, 1)):
    """How many other gaps disappear when this one is fixed."""
    return 'HIGH' if n >= scale[0] else 'MEDIUM' if n >= scale[1] else 'LOW' if n >= scale[2] else 'NONE'


def tier(r):
    deps = set(r['dependencies']) - {'NONE'}
    if r['category'] == 'NOT_A_GAP' or r['proposed_resolution'] == 'NO_ACTION':
        return 'DEFERRED'
    if (deps & BLOCKING_DEPS or r['proposed_resolution'] in ('MANUAL_DECISION', 'UNKNOWN')
            or r['effort'] in ('XL', 'UNKNOWN') or r['category'] == 'UNAVAILABLE'):
        return 'R5'
    if r['proposed_resolution'] in NEW_DATA_METHODS or deps & {'SOURCE_DISCOVERY', 'EXTERNAL_SOURCE'}:
        return 'R4'
    if r['proposed_resolution'] == 'OCR' or 'OCR' in deps or r['effort'] in ('L',):
        return 'R3'
    if (r['effort'] in ('XS', 'S') and r['effort_confidence'] in ('HIGH', 'MEDIUM') and not deps
            and r['evidence_available']):
        return 'R1'
    if r['effort'] == 'M' and r['proposed_resolution'] in ('TARGETED_LOCAL_SEARCH',):
        return 'R3'
    return 'R2'


ORDER = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2, 'NONE': 3}
CAT_ORDER = {'MAPPING_GAP': 0, 'EVIDENCE_GAP': 1, 'EXTRACTION_GAP': 2, 'IDENTITY_GAP': 3, 'CONFLICT': 4}


def rank_key(r):
    """Within a tier: confidence, cascading benefit, effort, provenance/mapping first, then the id."""
    return (TIERS.index(r['priority']), ORDER[r['effort_confidence']], ORDER[r['cascading_benefit']],
            EFFORTS.index(r['effort']), CAT_ORDER.get(r['category'], 9), r['gap_id'])


def gap(key, **kw):
    row = {'gap_key': key, 'secondary_categories': [], 'dependencies': ['NONE'], 'representative_examples': [],
           'source_artifacts': [], 'notes': '', 'evidence_available': True}
    row.update(kw)
    row['gap_id'] = 'gap_' + L.stable_hash('DataGap', key)
    if 'effort' not in row:
        row['effort'] = effort(row['proposed_resolution'], row['affected_count'])
    row['dependencies'] = sorted(set(row['dependencies'])) or ['NONE']
    if len(row['dependencies']) > 1 and 'NONE' in row['dependencies']:
        row['dependencies'].remove('NONE')
    row['priority'] = tier(row)
    block = sorted(set(row['dependencies']) & BLOCKING_DEPS)
    if row['proposed_resolution'] == 'MANUAL_DECISION':
        block.append('MANUAL_DECISION')
    if row['effort'] in ('UNKNOWN', 'XL'):
        block.append(row['effort'] + '_EFFORT')
    if row['category'] == 'UNAVAILABLE' and row['priority'] == 'R5':
        block.append('UNAVAILABLE')
    row['blocking'] = sorted(set(block))
    row['requires_new_data'] = row['proposed_resolution'] in NEW_DATA_METHODS
    if row['effort'] == 'UNKNOWN':
        row['unknown_reason'] = UNKNOWN_WHY[row['proposed_resolution']]
    return row


UNKNOWN_WHY = {
    'MANUAL_DECISION': 'a decision, not work: it waits on whoever holds the decision; once taken, applying it is XS-S',
    'NEW_SOURCE_REQUIRED': 'no source is known yet; the effort depends on what discovery finds',
    'UNKNOWN': 'no resolution path exists without new attribution evidence for these documents',
}


def by_estate(rows, key=lambda r: A.estate_of_record(r['record'])):
    out = collections.defaultdict(list)
    for r in rows:
        out[key(r)].append(r)
    return dict(sorted(out.items()))


# -- the rows --------------------------------------------------------------------------------------

def figure_rows():
    rows = []
    u = A.unsourced_figures()
    G = collections.defaultdict(list)
    for r in u:
        G[r['group']].append(r)
    spec = {
        '1_LOCAL_IDENTIFIABLE': dict(category='MAPPING_GAP', secondary=['EVIDENCE_GAP'], state='UNMAPPED',
                                     method='PROVENANCE_REPAIR', conf='HIGH', deps=['NONE'],
                                     what='figures with no field source whose exact value is printed in the record\'s own held sheet',
                                     status='record sheet held; value found in its text'),
        '3_RELATIONSHIP_UNCLEAR': dict(category='EVIDENCE_GAP', secondary=['MAPPING_GAP'], state='UNRESOLVED',
                                       method='EXISTING_EVIDENCE_REVIEW', conf='MEDIUM', deps=['MANUAL_REVIEW'],
                                       what='figures with no field source; the record\'s held sheet does not print the value as such (or the field is a date)',
                                       status='record sheet held with text; value not found verbatim'),
        '3b_TEXT_NOT_STORED': dict(category='EXTRACTION_GAP', secondary=['MAPPING_GAP'], state='UNMAPPED',
                                   method='DETERMINISTIC_MAPPING', conf='MEDIUM', deps=['NONE'],
                                   what='figures with no field source; the record\'s held PDF has no stored text to check against',
                                   status='record sheet held; text read by the sheet reader at run time, not stored'),
        '2_MULTIPLE_CANDIDATES': dict(category='MAPPING_GAP', secondary=['EVIDENCE_GAP'], state='UNRESOLVED',
                                      method='EXISTING_EVIDENCE_REVIEW', conf='MEDIUM', deps=['MANUAL_REVIEW'],
                                      what='figures with no field source; the record\'s sheet name matches several held documents',
                                      status='several candidate documents held'),
        '4_NOT_HELD': dict(category='SOURCE_GAP', secondary=['EVIDENCE_GAP'], state='MISSING',
                           method='TARGETED_FIRST_PARTY_SCRAPE', conf='LOW', deps=['SOURCE_DISCOVERY'],
                           what='figures with no field source; the record names a sheet the store does not hold',
                           status='named, not held'),
    }
    for group, members in sorted(G.items()):
        s = spec[group]
        for est, rs in by_estate(members).items():
            recs = sorted({r['record'] for r in rs})
            docs = sorted({r['document'] for r in rs if r.get('document')} |
                          {d for r in rs for d in r.get('documents') or []})
            rows.append(gap('FIG_UNSOURCED|%s|%s' % (group, est), category=s['category'],
                            secondary_categories=s['secondary'], entity_type='Estate', entity_id=est,
                            description='%s: %d %s' % (est, len(rs), s['what']), state=s['state'],
                            affected_count=len(rs), evidence_status=s['status'],
                            evidence_available=group != '4_NOT_HELD',
                            proposed_resolution=s['method'], effort_confidence=s['conf'],
                            cascading_benefit=cascade(len(rs)), dependencies=s['deps'],
                            representative_examples=['%s %s' % (r['record'], r['field']) for r in rs[:3]],
                            source_artifacts=docs[:5],
                            notes='%d record(s); fields %s; group %s of the 2,149' % (
                                len(recs), dict(sorted(collections.Counter(r['field'] for r in rs).items())), group)))
    for r in A.ambiguous_figures():
        r['sub'] = ('ONE_PRINTS' if r['printed_in'] == 1 else 'SEVERAL_PRINT' if r['printed_in'] > 1
                    else 'NONE_PRINTS' if r['checkable'] else 'NO_TEXT')
    amb = collections.defaultdict(list)
    for r in A.ambiguous_figures():
        amb[r['sub']].append(r)
    aspec = {'ONE_PRINTS': ('DETERMINISTIC_MAPPING', 'HIGH', ['NONE'], 'exactly one candidate prints the value'),
             'SEVERAL_PRINT': ('EXISTING_EVIDENCE_REVIEW', 'MEDIUM', ['MANUAL_REVIEW'], 'every candidate prints it (language or revision versions): which to cite is a choice'),
             'NONE_PRINTS': ('EXISTING_EVIDENCE_REVIEW', 'MEDIUM', ['MANUAL_REVIEW'], 'no candidate prints it verbatim'),
             'NO_TEXT': ('DETERMINISTIC_MAPPING', 'MEDIUM', ['NONE'], 'no candidate has stored text to check')}
    for sub, members in sorted(amb.items()):
        m, conf, deps, how = aspec[sub]
        rows.append(gap('FIG_AMBIGUOUS|%s' % sub, category='MAPPING_GAP', secondary_categories=['EVIDENCE_GAP'],
                        entity_type='Figure', entity_id='source-unclear:%s' % sub.lower(),
                        description='%d "source unclear" figures: the field\'s own source name matches several documents; %s' % (len(members), how),
                        state='UNRESOLVED', affected_count=len(members), evidence_status='candidates held',
                        proposed_resolution=m, effort_confidence=conf, cascading_benefit=cascade(len(members)),
                        dependencies=deps, representative_examples=['%s %s (%s)' % (r['record'], r['field'], r['basename']) for r in members[:3]],
                        source_artifacts=sorted({d for r in members for d in r['documents']})[:5],
                        notes='of the 96 "source unclear" figures'))
    fo = collections.defaultdict(list)
    for r in A.file_only_figures():
        fo[r['url_known']].append(r)
    if fo[True]:
        rows.append(gap('FIG_FILE_ONLY|URL_IN_DISCOVERY', category='MAPPING_GAP', secondary_categories=['DISCOVERY_GAP'],
                        entity_type='Figure', entity_id='file-only:url-known', state='UNMAPPED',
                        description='%d figures cite their own held sheet with no address; the discovery store fetched the same bytes from a URL' % len(fo[True]),
                        affected_count=len(fo[True]), evidence_status='same sha256 fetched online',
                        proposed_resolution='DETERMINISTIC_MAPPING', effort_confidence='HIGH',
                        cascading_benefit=cascade(len(fo[True])), source_artifacts=sorted({r['document'] for r in fo[True]})[:5],
                        representative_examples=['%s %s' % (r['record'], r['field']) for r in fo[True][:3]],
                        notes='attach the discovered URL as a placement of the same artifact'))
    if fo[False]:
        rows.append(gap('FIG_FILE_ONLY|NO_URL', category='DISCOVERY_GAP', secondary_categories=['SOURCE_GAP'],
                        entity_type='Figure', entity_id='file-only:no-url', state='MISSING',
                        description='%d figures cite their own held sheet; no address for those bytes is known anywhere' % len(fo[False]),
                        affected_count=len(fo[False]), evidence_status='document held, address unknown',
                        proposed_resolution='TARGETED_FIRST_PARTY_SCRAPE', effort_confidence='LOW',
                        cascading_benefit='LOW', dependencies=['SOURCE_DISCOVERY'],
                        source_artifacts=sorted({r['document'] for r in fo[False]})[:5],
                        representative_examples=['%s %s' % (r['record'], r['field']) for r in fo[False][:3]],
                        notes='the figure is sourced (the file is held and named); only a public address is missing'))
    return rows


def corpus_rows():
    rows = []
    om = A.observation_mapping()
    b = om['buckets']
    # The unit of work is the document (run the existing evidence guard once per artifact), not the
    # observation: effort is computed on artifacts, the affected count stays in observations.
    spec = [
        ('ESTATE_DETERMINISTIC_CANDIDATE', 'EVIDENCE_GAP', 'UNMAPPED', 'DETERMINISTIC_MAPPING', 'LOW', 'MEDIUM',
         ['NONE'], 'one strong crawl candidate resolving to one model estate; never put to the evidence store'),
        ('ESTATE_ONLY', 'MAPPING_GAP', 'UNMAPPED', 'EXISTING_EVIDENCE_REVIEW', 'LOW', 'LOW', ['MANUAL_REVIEW'],
         'estate exact, wine and vintage not established'),
        ('ESTATE_VINTAGE', 'MAPPING_GAP', 'UNMAPPED', 'EXISTING_EVIDENCE_REVIEW', 'MEDIUM', 'LOW', ['MANUAL_REVIEW'],
         'estate and vintage exact, wine not established'),
        ('ESTATE_WINE', 'MAPPING_GAP', 'UNMAPPED', 'EXISTING_EVIDENCE_REVIEW', 'MEDIUM', 'LOW', ['MANUAL_REVIEW'],
         'estate and wine exact, vintage not established'),
        ('AMBIGUOUS', 'IDENTITY_GAP', 'UNRESOLVED', 'EXISTING_EVIDENCE_REVIEW', 'LOW', 'LOW', ['MANUAL_REVIEW'],
         'several crawl candidates (group and merchant sites)'),
        ('AMBIGUOUS_SHARED_DOCUMENT', 'NOT_A_GAP', 'NONE', 'NO_ACTION', 'HIGH', 'NONE', ['NONE'],
         'one document attributed to several estates by the record itself (a shared sheet)'),
        ('CONFLICTING', 'CONFLICT', 'CONFLICTING', 'EXISTING_EVIDENCE_REVIEW', 'MEDIUM', 'LOW', ['MANUAL_REVIEW'],
         'the record\'s estate and the crawl\'s single strong candidate differ'),
        ('UNMAPPABLE', 'MAPPING_GAP', 'MISSING', 'UNKNOWN', 'LOW', 'NONE', ['NONE'],
         'no estate evidence at all'),
        ('ESTATE_WINE_VINTAGE', 'NOT_A_GAP', 'NONE', 'NO_ACTION', 'HIGH', 'NONE', ['NONE'],
         'estate, wine and vintage all exact (the fillable figures are a separate gap)'),
    ]
    for bucket, cat, state, method, conf, casc, deps, how in spec:
        n = b.get(bucket, 0)
        members = sorted(A.artifact_mapping(s)['artifact'] or s[:16] for s in A.observation_counts() if _bucket_of(s) == bucket)
        arts = members[:5]
        rows.append(gap('CORPUS|%s' % bucket, category=cat, entity_type='Observation', entity_id='corpus:%s' % bucket.lower(),
                        description='%d harvested observations on %d documents: %s' % (n, len(members), how),
                        state=state, affected_count=n, effort=effort(method, len(members)),
                        evidence_status='discovery CANDIDATES_ONLY', proposed_resolution=method,
                        effort_confidence=conf, cascading_benefit=casc, dependencies=deps, source_artifacts=arts,
                        evidence_available=method != 'UNKNOWN',
                        notes='of %d observations on %d artifacts (data/discovery/observations)' % (om['total'], om['artifacts'])))
    fs = A.fillable_slots()
    per = collections.defaultdict(list)
    wine_estate = {r['wine']: r['estate'] for r in A.table('state/estate-wine.jsonl')}
    for k, shas in fs.items():
        vt, field = k.split('|')
        per[wine_estate.get(vt.split(':')[1], '?')].append((vt, field, shas))
    for est, items in sorted(per.items()):
        rows.append(gap('FILLABLE|%s' % est, category='MAPPING_GAP', secondary_categories=['EVIDENCE_GAP'],
                        entity_type='Estate', entity_id=est, state='UNMAPPED',
                        description='%s: %d vintage figure(s) the model lacks, stated in an exactly mapped harvested sheet' % (est, len(items)),
                        affected_count=len(items), evidence_status='accepted sheet (estate, wine, vintage exact); observation label and value shape match',
                        proposed_resolution='EXISTING_EVIDENCE_REVIEW', effort_confidence='MEDIUM',
                        cascading_benefit=cascade(len(items), (10, 3, 1)), dependencies=['MANUAL_REVIEW'],
                        representative_examples=['%s %s' % (vt, f) for vt, f, _ in items[:3]],
                        source_artifacts=sorted({A.sha_to_artifact().get(s, s[:16]) for _, _, ss in items for s in ss})[:5],
                        notes='a figure is filled only after reading the passage: crawled label lines carry neighbouring years and cells'))
    return rows


_BUCKET = {}


def _bucket_of(sha):
    if sha not in _BUCKET:
        m = A.artifact_mapping(sha)
        e, w, v = m['estate'] == 'EXACT', m['wine'] == 'EXACT', m['vintage'] == 'EXACT'
        _BUCKET[sha] = ('CONFLICTING' if m['estate'] == 'CONFLICTING' else
                        'AMBIGUOUS_SHARED_DOCUMENT' if m['estate'] == 'SHARED' else
                        'ESTATE_WINE_VINTAGE' if e and w and v else 'ESTATE_WINE' if e and w else
                        'ESTATE_VINTAGE' if e and v else 'ESTATE_ONLY' if e else
                        'ESTATE_DETERMINISTIC_CANDIDATE' if m['estate'] == 'DETERMINISTIC' else
                        'AMBIGUOUS' if m['estate'] == 'AMBIGUOUS' else
                        'WINE_ONLY' if w else 'VINTAGE_ONLY' if v else 'UNMAPPABLE')
    return _BUCKET[sha]


def ocr_rows():
    rows = []
    useful = [o for o in A.ocr_backlog() if o['benefit'] != 'NONE']
    for o in useful:
        g = o['gaps']
        n = g['unsourced_figures_on_those_records'] + len(g['only_document_of_vintages'])
        rows.append(gap('OCR|%s' % o['artifact'], category='EXTRACTION_GAP', secondary_categories=['EVIDENCE_GAP'],
                        entity_type='Artifact', entity_id=o['artifact'], state='UNMAPPED',
                        description='image-only %s: %s' % ((o['names'] or ['?'])[0], '; '.join(filter(None, [
                            'the only document of %s' % ', '.join(g['only_document_of_vintages']) if g['only_document_of_vintages'] else '',
                            'the record sheet of %s, %d figure(s) unsourced there' % (', '.join(g['record_sheet_of']),
                                                                                     g['unsourced_figures_on_those_records'])
                            if g['record_sheet_of'] else '']))),
                        affected_count=max(n, 1), evidence_status='bytes held, NEEDS_OCR',
                        proposed_resolution='OCR', effort_confidence='MEDIUM', cascading_benefit=o['benefit'],
                        dependencies=['OCR'], source_artifacts=[o['artifact']],
                        representative_examples=(g['record_sheet_of'] + g['only_document_of_vintages'])[:3],
                        notes='estates %s; vintages %s' % (o['estates'], o['vintages'])))
    rest = [o for o in A.ocr_backlog() if o['benefit'] == 'NONE']
    rows.append(gap('OCR|NO_IDENTIFIED_GAP', category='NOT_A_GAP', entity_type='Artifact', entity_id='ocr:no-gap',
                    description='%d image-only documents that are no record\'s sheet and the only document of no vintage' % len(rest),
                    state='NONE', affected_count=len(rest), evidence_status='bytes held, NEEDS_OCR',
                    proposed_resolution='NO_ACTION', effort_confidence='HIGH', cascading_benefit='NONE',
                    source_artifacts=[o['artifact'] for o in rest[:5]],
                    notes='OCR them only when a gap names them (M3.1: which OCR is worth doing, not OCR everything)'))
    return rows


def source_rows():
    rows = []
    dc = A.discovery_coverage()
    vdocs = A.vintage_documents()
    ew = collections.defaultdict(set)
    for r in A.table('state/estate-wine.jsonl'):
        ew[r['estate']].add(r['wine'])
    nodoc = collections.Counter()
    for v in A.table('identity/vintages.jsonl'):
        if not vdocs.get('vt:%s:%s' % (v['wine'], v['label'])):
            for e, ws in ew.items():
                if v['wine'] in ws:
                    nodoc[e] += 1
    status_of = {}
    for c in dc['coverage']:
        if c.get('model_estate'):
            status_of[c['model_estate']] = c
    names = {n['subject']: n['name'] for n in A.table('identity/names.jsonl') if n['kind'] == 'CURRENT'}
    for e, n in sorted(nodoc.items()):
        c = status_of.get(e)
        st = c['status'] if c else 'NOT_IN_UNIVERSE'
        if st in ('REACHED', 'PARTIAL', 'UNREACHABLE'):
            # PARTIAL stopped on budget: a targeted pass is likely to find more. REACHED exhausted its
            # frontier: only unlinked files (WordPress media, sitemaps) or another source remain.
            kw = dict(category='COVERAGE_GAP', secondary_categories=['DISCOVERY_GAP'], state='MISSING',
                      proposed_resolution='TARGETED_FIRST_PARTY_SCRAPE',
                      effort_confidence='MEDIUM' if st == 'PARTIAL' else 'LOW', dependencies=['SOURCE_DISCOVERY'])
        elif st == 'BLOCKED_BY_POLICY':
            kw = dict(category='UNAVAILABLE', secondary_categories=['COVERAGE_GAP'], state='MISSING',
                      proposed_resolution='NEW_SOURCE_REQUIRED', effort_confidence='LOW', dependencies=['EXTERNAL_SOURCE'])
        else:
            kw = dict(category='SOURCE_GAP', secondary_categories=['COVERAGE_GAP'], state='MISSING',
                      proposed_resolution='NEW_SOURCE_REQUIRED', effort_confidence='LOW', dependencies=['SOURCE_DISCOVERY'])
        rows.append(gap('VINTAGE_NO_DOCUMENT|%s' % e, entity_type='Estate', entity_id=e, affected_count=n,
                        description='%s (%s): %d vintage(s) in the model with no document at all (site %s)' % (
                            names.get(e, e), e, n, st),
                        evidence_status='no document held for these vintages', evidence_available=False,
                        cascading_benefit=cascade(n, (15, 5, 1)),
                        representative_examples=[c['domain']] if c and c.get('domain') else [],
                        notes='vintages present (ratings, lists) but no sheet; local search found none: the unincorporated '
                              'crawl PDFs fill no document-less vintage', **kw))
    for c in dc['coverage']:
        if c['status'] in ('UNREACHABLE', 'BLOCKED_BY_POLICY', 'PARTIAL', 'NO_KNOWN_SITE'):
            e = c.get('model_estate') or c['estate']
            n = nodoc.get(c.get('model_estate'), 0)
            if n:
                continue        # the estate's VINTAGE_NO_DOCUMENT row carries this site status: one gap, one row
            if c['status'] == 'BLOCKED_BY_POLICY':
                kw = dict(category='UNAVAILABLE', proposed_resolution='NO_ACTION' if not n else 'NEW_SOURCE_REQUIRED',
                          dependencies=['EXTERNAL_SOURCE'], effort_confidence='HIGH',
                          notes='robots.txt disallows us; respected. Another source (a merchant, the negociant) only')
            elif c['status'] == 'NO_KNOWN_SITE':
                kw = dict(category='SOURCE_GAP', proposed_resolution='NEW_SOURCE_REQUIRED', dependencies=['SOURCE_DISCOVERY'],
                          effort_confidence='MEDIUM', notes='no official site known (websites.js); finding one is the first step')
            else:
                kw = dict(category='DISCOVERY_GAP', proposed_resolution='TARGETED_FIRST_PARTY_SCRAPE',
                          dependencies=['SOURCE_DISCOVERY'], effort_confidence='LOW' if c['status'] == 'UNREACHABLE' else 'MEDIUM',
                          notes='crawl stopped: %s' % c.get('stopped'))
            # no identified data gap depends on this site: recorded, deliberately deferred
            kw.update(proposed_resolution='NO_ACTION')
            rows.append(gap('SITE|%s|%s' % (c['status'], c['estate']), secondary_categories=['COVERAGE_GAP'],
                            entity_type='Estate', entity_id=e, state='MISSING', affected_count=1,
                            description='%s (%s): site %s; no identified data gap depends on it' % (
                                c['name'], c.get('domain') or 'no site', c['status']),
                            evidence_status='crawl %s' % c['status'], evidence_available=False,
                            cascading_benefit='NONE', representative_examples=[c.get('domain') or c['name']], **kw))
    for e, v in A.unincorporated_documents().items():
        rows.append(gap('UNINCORPORATED|%s' % e, category='EVIDENCE_GAP', secondary_categories=['MAPPING_GAP'],
                        entity_type='Estate', entity_id=e, state='UNMAPPED',
                        description='%s: %d harvested PDF(s) with one strong estate candidate, never put to the evidence store' % (e, v['documents']),
                        affected_count=v['documents'], evidence_status='held, crawl attribution only',
                        proposed_resolution='EXISTING_EVIDENCE_REVIEW', effort_confidence='MEDIUM',
                        cascading_benefit='LOW' if not v['fills_documentless_vintage'] else 'MEDIUM',
                        dependencies=['MANUAL_REVIEW'], source_artifacts=v['examples'],
                        notes='%d carry one heading year; %d would be the first document of a model vintage' % (
                            v['heading_year'], v['fills_documentless_vintage'])))
    return rows


def identity_rows():
    rows = []
    for r in sorted(A.identity_ambiguities(), key=lambda r: (r['namespace'], r['legacy_key'])):
        laparde = 'La Parde' in r['legacy_key']
        rows.append(gap('IDMAP|%s|%s' % (r['namespace'], r['legacy_key']), category='IDENTITY_GAP',
                        entity_type='IdentityMapEntry', entity_id='%s|%s' % (r['namespace'], r['legacy_key']),
                        state='UNRESOLVED',
                        description='identity map %s "%s" is AMBIGUOUS between %d candidate(s)' % (
                            r['namespace'], r['legacy_key'], len(r.get('candidates') or [])),
                        affected_count=1, evidence_status='candidates recorded',
                        proposed_resolution='MANUAL_DECISION' if laparde else 'EXISTING_EVIDENCE_REVIEW',
                        effort_confidence='LOW' if laparde else 'MEDIUM', cascading_benefit='LOW',
                        dependencies=['LAPARDE_IDENTITY'] if laparde else ['MANUAL_REVIEW'],
                        representative_examples=(r.get('candidates') or [])[:3],
                        notes='Phase 6.2/6.3: "needs a decision", as D2' if laparde else ''))
    for k, ids in A.duplicate_estate_names().items():
        rows.append(gap('DUPNAME|%s' % k, category='IDENTITY_GAP', entity_type='Estate', entity_id=','.join(ids),
                        state='UNRESOLVED', description='two model estates share the current name "%s"' % k,
                        affected_count=len(ids), evidence_status='names and appellations held',
                        proposed_resolution='EXISTING_EVIDENCE_REVIEW', effort_confidence='HIGH',
                        cascading_benefit='LOW', dependencies=['MANUAL_REVIEW'], representative_examples=ids,
                        notes='likely two different estates of one name in different appellations; confirm, do not merge'))
    for (est, wine), v in A.unlisted_wines().items():
        rows.append(gap('UNLISTED|%s|%s' % (est, wine), category='IDENTITY_GAP', secondary_categories=['MAPPING_GAP'],
                        entity_type='Wine', entity_id='%s|%s' % (est, wine), state='MISSING',
                        description='%s: "%s" has accepted-looking sheets (%d decision(s), vintages %s) but is no model wine' % (
                            est, wine, v['decisions'], v['vintages'][:6]),
                        affected_count=v['decisions'], evidence_status='refused UNLISTED_WINE: the guard cannot assign it',
                        proposed_resolution='MODEL_MAPPING', effort_confidence='MEDIUM',
                        cascading_benefit=cascade(v['decisions'], (10, 3, 1)), dependencies=['MANUAL_REVIEW'],
                        representative_examples=v['examples'],
                        notes='adding a wine is an editorial decision; once listed, the evidence store accepts the sheets'))
    by_kind = collections.defaultdict(list)
    for f in A.findings():
        by_kind[f['kind']].append(f)
    fspec = {
        'AMBIGUOUS_SEMANTICS': ('CONFLICT', 'UNRESOLVED', 'MANUAL_DECISION', ['D1'], 'LOW',
                                'the estate-level blend means plantings or usual assemblage (D1)'),
        'SOURCE_FAILURE': ('UNAVAILABLE', 'MISSING', 'NO_ACTION', ['NONE'], 'HIGH',
                           'a manifest row whose file is not held or not found'),
        'IDENTITY_UNCERTAIN': ('IDENTITY_GAP', 'UNRESOLVED', 'EXISTING_EVIDENCE_REVIEW', ['MANUAL_REVIEW'], 'MEDIUM',
                               'a legacy name not resolved to one model id'),
        'ORPHAN_PROVENANCE': ('MAPPING_GAP', 'UNMAPPED', 'DETERMINISTIC_MAPPING', ['NONE'], 'HIGH',
                              'cuvee-src names sources for a record cuvees.js does not hold'),
        'MISSING': ('EVIDENCE_GAP', 'MISSING', 'TARGETED_LOCAL_SEARCH', ['NONE'], 'MEDIUM',
                    'a fiche record holds a source but no value'),
    }
    for kind, fs in sorted(by_kind.items()):
        if kind == 'CONFLICT':
            for f in fs:
                second = 'second wine' in f['detail']
                rows.append(gap('FINDING|CONFLICT|%s' % f['id'], category='CONFLICT', entity_type='QualityFinding',
                                entity_id=f['id'], state='CONFLICTING', description=f['detail'][:160], affected_count=1,
                                evidence_status='two legacy statements disagree',
                                proposed_resolution='MANUAL_DECISION' if second else 'EXISTING_EVIDENCE_REVIEW',
                                effort_confidence='LOW' if second else 'HIGH', cascading_benefit='LOW',
                                dependencies=['D5'] if second else ['MANUAL_REVIEW'],
                                representative_examples=[f['target']],
                                notes='contemporaneous dataset conflict (6.2); no winner before D5' if second else
                                      'two byte counts for one sha1 in the manifest: the held bytes decide'))
            continue
        cat, state, method, deps, conf, how = fspec[kind]
        rows.append(gap('FINDING|%s' % kind, category=cat, entity_type='QualityFinding', entity_id='findings:%s' % kind.lower(),
                        state=state, description='%d open %s findings: %s' % (len(fs), kind, how), affected_count=len(fs),
                        evidence_status='recorded by the migration', proposed_resolution=method, effort_confidence=conf,
                        cascading_benefit=cascade(len(fs), (50, 10, 1)) if kind != 'SOURCE_FAILURE' else 'NONE',
                        dependencies=deps, representative_examples=[f['detail'][:90] for f in fs[:2]],
                        notes='cross/findings.jsonl'))
    return rows


def evidence_rows():
    rows = []
    unc = collections.defaultdict(list)
    for c in A.unsourced_canonical():
        unc[c['field']].append(c)
    for field, cs in sorted(unc.items()):
        rows.append(gap('UNSOURCED_CANONICAL|%s' % field, category='EVIDENCE_GAP', secondary_categories=['SOURCE_GAP'],
                        entity_type='CanonicalValue', entity_id='field:%s' % field, state='MISSING',
                        description='%d canonical %s value(s) with no source at all (LEGACY_UNSOURCED)' % (len(cs), field),
                        affected_count=len(cs), evidence_status='none recorded', evidence_available=False,
                        proposed_resolution='TARGETED_LOCAL_SEARCH', effort_confidence='LOW',
                        cascading_benefit='LOW', representative_examples=sorted({c['subject'] for c in cs})[:3],
                        notes='search the estate\'s held documents for the value before any new retrieval'))
    pv = A.by_id('cross/provenance.jsonl')
    obs = collections.Counter(o['field'] for o in A.table('observation/observations.jsonl')
                              if pv[o['provenance']]['kind'] == 'LEGACY_UNSOURCED')
    for field, n in sorted(obs.items()):
        if field in ('owner', 'history'):
            continue                                     # the historical rows below
        rows.append(gap('UNSOURCED_OBSERVATION|%s' % field, category='NOT_A_GAP', entity_type='Observation',
                        entity_id='field:%s' % field, state='NONE',
                        description='%d legacy %s observation(s) are editorial, LEGACY_UNSOURCED' % (n, field),
                        affected_count=n, evidence_status='editorial text', proposed_resolution='NO_ACTION',
                        effort_confidence='HIGH', cascading_benefit='NONE',
                        notes='the dashboard\'s own prose; it claims no source and needs none to be shown as such'))
    acc = sum(1 for d in A.decisions() if d['decision'] == 'ACCEPTED')
    rows.append(gap('IDENTITY_NOT_CONTENT', category='EVIDENCE_GAP', entity_type='EvidenceDecision',
                    entity_id='decisions-v5:accepted', state='UNRESOLVED',
                    description='%d accepted evidence decisions establish whose sheet a document is, never that its content (a figure, a history statement) is right' % acc,
                    affected_count=acc, evidence_status='attribution reviewed; content not reviewed',
                    proposed_resolution='EXISTING_EVIDENCE_REVIEW', effort_confidence='LOW', cascading_benefit='HIGH',
                    dependencies=['MANUAL_REVIEW'],
                    notes='established by M3: document-identity approval is not content approval. A content review '
                          'is a new kind of decision; it gates every historical claim'))
    rows.append(gap('ACCEPTED_UNAVAILABLE', category='NOT_A_GAP', entity_type='EvidenceDecision', entity_id='decisions-v5:unavailable',
                    state='NONE', description='%d accepted decisions whose bytes are not held' % len(A.unavailable_accepted()),
                    affected_count=len(A.unavailable_accepted()), evidence_status='checked',
                    proposed_resolution='NO_ACTION', effort_confidence='HIGH', cascading_benefit='NONE',
                    notes='every accepted document is held (sha256 proven)'))
    nov = [d for d in A.decisions() if d['decision'] == 'ACCEPTED' and not d['vintage']]
    rows.append(gap('ACCEPTED_NO_VINTAGE', category='TEMPORAL_GAP', secondary_categories=['MAPPING_GAP'],
                    entity_type='EvidenceDecision', entity_id='decisions-v5:accepted-no-vintage', state='UNRESOLVED',
                    description='%d accepted documents state no vintage (estate or wine pages, multi-vintage sheets)' % len(nov),
                    affected_count=len(nov), evidence_status='attribution accepted, vintage unstated',
                    proposed_resolution='EXISTING_EVIDENCE_REVIEW', effort_confidence='LOW', cascading_benefit='LOW',
                    dependencies=['MANUAL_REVIEW'], representative_examples=[d['artifact_name'] for d in nov[:3]],
                    notes='most are not vintage documents at all; a vintage is never read from the file name or URL alone'))
    vc = A.vintage_document_counts()
    rows.append(gap('VINTAGE_SEVERAL_DOCUMENTS', category='MAPPING_GAP', secondary_categories=['EVIDENCE_GAP'],
                    entity_type='Vintage', entity_id='vintages:several-documents', state='UNMAPPED',
                    description='%d vintages have several documents; their language-version and revision relations are not recorded (0 ArtifactRelations)' % vc.get('several', 0),
                    affected_count=vc.get('several', 0), evidence_status='documents held',
                    proposed_resolution='DETERMINISTIC_MAPPING', effort_confidence='MEDIUM', cascading_benefit='MEDIUM',
                    notes='file names pair FR/EN and -v2 versions; a relation is a document fact, not a choice of winner (D5)'))
    return rows


def historical_rows():
    rows = []
    c = {r['key']: r for r in A.m3_candidates()}
    def keys(prefix):
        return sorted(k for k in c if k.startswith(prefix))
    echo = keys('echo-') + keys('averous-')
    rows.append(gap('HIST|ECHO_D2', category='IDENTITY_GAP', secondary_categories=['TEMPORAL_GAP'], entity_type='Wine',
                    entity_id='wn_00547', state='UNRESOLVED',
                    description='Echo de Lynch-Bages: rename or succession from Haut-Bages Averous (D2); %d M3 candidates wait on it' % len(echo),
                    affected_count=len(echo), evidence_status='three sources word a change of name from the 2008 vintage; none reviewed',
                    proposed_resolution='MANUAL_DECISION', effort_confidence='LOW', cascading_benefit='MEDIUM',
                    dependencies=['D2'], representative_examples=echo[:3],
                    source_artifacts=sorted({c[k]['artifact'] for k in echo if c[k].get('artifact')})))
    lp = keys('laparde-')
    rows.append(gap('HIST|LAPARDE', category='IDENTITY_GAP', secondary_categories=['TEMPORAL_GAP'], entity_type='Wine',
                    entity_id='haut-bailly|La Parde de Haut-Bailly', state='UNRESOLVED',
                    description='La Parde de Haut-Bailly -> Haut-Bailly II: the identity decision (6.2) gates %d M3 candidates' % len(lp),
                    affected_count=len(lp), evidence_status='accepted 2018 sheet states the rename',
                    proposed_resolution='MANUAL_DECISION', effort_confidence='LOW', cascading_benefit='LOW',
                    dependencies=['LAPARDE_IDENTITY'], representative_examples=lp, source_artifacts=['ar_002853']))
    nm = [r for k, r in c.items() if k.startswith('legacy-not-made:')]
    per = collections.defaultdict(list)
    for r in nm:
        per[r['subject']].append(r['key'].rsplit(':', 1)[1])
    for w, ys in sorted(per.items()):
        rows.append(gap('HIST|NOT_MADE|%s' % w, category='EVIDENCE_GAP', secondary_categories=['SOURCE_GAP'],
                        entity_type='Wine', entity_id=w, state='MISSING',
                        description='%s: %d legacy not-produced vintage(s) with no source (%s)' % (w, len(ys), ', '.join(sorted(ys))),
                        affected_count=len(ys), evidence_status='LEGACY_UNSOURCED; no accepted sheet of the estate states them',
                        evidence_available=False, proposed_resolution='TARGETED_FIRST_PARTY_SCRAPE', effort_confidence='LOW',
                        cascading_benefit='LOW', dependencies=['SOURCE_DISCOVERY'],
                        notes='M3: the fixed-phrase search of the estate\'s accepted sheets found nothing; the estate site is the source to look for'))
    oh = [r for k, r in c.items() if k.startswith(('legacy-owner', 'legacy-history'))]
    rows.append(gap('HIST|OWNER_HISTORY_TEXT', category='EVIDENCE_GAP', secondary_categories=['SOURCE_GAP'],
                    entity_type='Observation', entity_id='legacy owner/history', state='MISSING',
                    description='%d legacy owner/history texts state dated history ("since 2016", "bought in 1986") with no source' % len(oh),
                    affected_count=len(oh), evidence_status='LEGACY_UNSOURCED editorial text', evidence_available=False,
                    proposed_resolution='TARGETED_LOCAL_SEARCH', effort_confidence='LOW', cascading_benefit='LOW',
                    dependencies=['MANUAL_REVIEW'], representative_examples=sorted(r['subject'] for r in oh)[:3],
                    notes='the estates\' own history pages are held but never reviewed; some texts say "sources disagree"'))
    nr = [r for r in c.values() if r['category'] == 'REJECTED_NOT_REVIEWED']
    rows.append(gap('HIST|UNREVIEWED_PAGES', category='EVIDENCE_GAP', entity_type='Artifact', entity_id='history pages',
                    state='UNRESOLVED',
                    description='%d explicit dated statements on held, never-reviewed estate pages (Coutet Opalie 2010; Pontoise Cabarrus 1881-1959, Crus Bourgeois 2018)' % len(nr),
                    affected_count=len(nr), evidence_status='held and quoted; evidence store never reviewed web pages',
                    proposed_resolution='EXISTING_EVIDENCE_REVIEW', effort_confidence='MEDIUM', cascading_benefit='LOW',
                    dependencies=['MANUAL_REVIEW'], representative_examples=sorted(r['key'] for r in nr),
                    source_artifacts=sorted({r['artifact'] for r in nr})))
    rows.append(gap('HIST|CORBIN_CURRENT_NO_SECOND', category='MAPPING_GAP', entity_type='Estate', entity_id='es_00398',
                    state='UNMAPPED', description='Corbin: accepted 2025 sheets (EN, FR) say "No second wine"; the model holds nothing about a second wine',
                    affected_count=2, evidence_status='accepted, explicit, current (not history)',
                    proposed_resolution='MODEL_MAPPING', effort_confidence='HIGH', cascading_benefit='LOW',
                    dependencies=['MANUAL_REVIEW'], source_artifacts=['ar_002680', 'ar_010117'],
                    notes='a current RankAbsence claimed by the producer; never a history fact'))
    rows.append(gap('HIST|CORBIN_2022', category='EVIDENCE_GAP', entity_type='Estate', entity_id='es_00398',
                    state='UNRESOLVED', description='Corbin 2022 "no second wine was produced this year": only in a press compilation the evidence store refused',
                    affected_count=1, evidence_status='REFUSED (PRESS_DOCUMENT); "this year" is deictic',
                    evidence_available=False, proposed_resolution='TARGETED_FIRST_PARTY_SCRAPE', effort_confidence='LOW',
                    cascading_benefit='LOW', dependencies=['SOURCE_DISCOVERY'], source_artifacts=['ar_009394']))
    rows.append(gap('HIST|TERRASSES', category='IDENTITY_GAP', entity_type='Wine', entity_id='Les Terrasses de Saint Christophe',
                    state='MISSING', description='Les Terrasses de Saint Christophe is stated as Tour Saint Christophe\'s second label but is no model wine (2.11)',
                    affected_count=1, evidence_status='accepted sheet states it (undated)',
                    proposed_resolution='MANUAL_DECISION', effort_confidence='LOW', cascading_benefit='LOW',
                    dependencies=['MANUAL_REVIEW'], source_artifacts=['ar_007920'],
                    notes='Phase 2.11/2.12: whether to list it is an editorial decision'))
    rows.append(gap('HIST|CB_EDITION', category='COVERAGE_GAP', secondary_categories=['TEMPORAL_GAP'],
                    entity_type='ClassificationEdition', entity_id='Crus Bourgeois 2020', state='MISSING',
                    description='earlier classification editions (Crus Bourgeois 2020, Saint-Émilion 2012/2006) are not recorded; dated memberships have nothing to attach to',
                    affected_count=1, evidence_status='one unreviewed estate page describes the 2020 edition',
                    evidence_available=False, proposed_resolution='NEW_SOURCE_REQUIRED', effort_confidence='LOW',
                    cascading_benefit='MEDIUM', dependencies=['EXTERNAL_SOURCE'],
                    notes='the classification bodies\' own lists are the source (Phase 3.0 universe sources)'))
    rows.append(gap('HIST|CURRENT_NOT_HISTORY', category='NOT_A_GAP', entity_type='Observation', entity_id='current statements',
                    state='NONE', description='%d current statements tempt a historical reading (34 dataset "no second wine", Corbin 2025, Desmirail\'s two names, Opalie\'s label) - none is history' % (
                        sum(1 for r in c.values() if r['category'] in ('EXCLUDED_CURRENT_STATEMENT', 'EXCLUDED_NOT_HISTORICAL', 'EXCLUDED_NOT_IDENTITY'))),
                    affected_count=sum(1 for r in c.values() if r['category'] in ('EXCLUDED_CURRENT_STATEMENT', 'EXCLUDED_NOT_HISTORICAL', 'EXCLUDED_NOT_IDENTITY')),
                    evidence_status='M3 audit', proposed_resolution='NO_ACTION', effort_confidence='HIGH', cascading_benefit='NONE',
                    notes='M3: a current fact is not converted into history'))
    rows.append(gap('HIST|BATAILLEY_BEFORE_2014', category='NOT_A_GAP', entity_type='Estate', entity_id='es_00035', state='NONE',
                    description='"Batailley had no second wine before 2014" is read from missing records - not a gap, an inference refused (H2)',
                    affected_count=1, evidence_status='absence of records', proposed_resolution='NO_ACTION',
                    effort_confidence='HIGH', cascading_benefit='NONE',
                    notes='the contemporaneous conflict itself is the FINDING|CONFLICT row'))
    return rows


def other_rows():
    rows = []
    rows.append(gap('WINES_WITHOUT_ESTATE', category='NOT_A_GAP', entity_type='Wine', entity_id='wines:no-estate', state='NONE',
                    description='%d model wines lack an estate relationship' % len(A.wines_without_estate()),
                    affected_count=len(A.wines_without_estate()), evidence_status='checked', proposed_resolution='NO_ACTION',
                    effort_confidence='HIGH', cascading_benefit='NONE'))
    wrong = sum(1 for d in A.decisions() if d['code'] == 'WRONG_VINTAGE')
    rows.append(gap('WRONG_VINTAGE_REFUSED', category='NOT_A_GAP', entity_type='EvidenceDecision', entity_id='decisions-v5:wrong-vintage',
                    state='NONE', description='%d sheets refused as WRONG_VINTAGE: the guard kept them off the wrong vintage' % wrong,
                    affected_count=wrong, evidence_status='refused', proposed_resolution='NO_ACTION',
                    effort_confidence='HIGH', cascading_benefit='NONE',
                    notes='not an attachment error: no wrong-vintage attachment exists in the model'))
    return rows


RESOLUTIONS = L.ROOT + 'data/audit/m32-resolutions.json'


def resolve(rows):
    """Record, on each gap a recovery stream reduced, what was resolved and by which commit. The gap
    keeps its id, its tier and its original affected count: the register is a historical record."""
    if not os.path.exists(RESOLUTIONS):
        return
    applied = json.load(open(RESOLUTIONS, encoding='utf-8'))
    recovered = collections.Counter()
    for f in A.unsourced_figures():
        if f.get('recovered'):
            stream = f['recovered']['stream']
            recovered[('FIG_UNSOURCED|%s|%s' % (f['group'], A.estate_of_record(f['record'])), stream)] += 1
    for f in A.file_only_figures():
        if f.get('recovered') and f['url_known']:
            recovered[('FIG_FILE_ONLY|URL_IN_DISCOVERY', f['recovered']['stream'])] += 1
    # M3.2D: a fillable slot (M3.1's vintage, field) the model now holds through a recovered value
    pv = A.by_id('cross/provenance.jsonl')
    wine_estate = {r['wine']: r['estate'] for r in A.table('state/estate-wine.jsonl')}
    fillable = set(A.fillable_slots())
    # M3.4B: a document-less vintage (as the register measured it) that an audited accepted document
    # now documents. Only "no document" is resolved: its figures stay with their own gaps.
    before = A.vintage_documents()
    for vt in sorted({a['vintage'] for a in A.m34b_attributions() if not before.get(a['vintage'])}):
        recovered[('VINTAGE_NO_DOCUMENT|%s' % wine_estate.get(vt.split(':')[1], '?'), 'M3.4B')] += 1
    for c in A.table('canonical/values.jsonl'):
        if (pv[c['provenance']].get('code_state') or {}).get('stream') == 'M3.2D' and \
                '%s|%s' % (c['subject'], c['field']) in fillable:
            recovered[('FILLABLE|%s' % wine_estate.get(c['subject'].split(':')[1], '?'), 'M3.2D')] += 1
    for r in rows:
        done = {s: n for (k, s), n in recovered.items() if k == r['gap_key'] and s in applied}
        if not done:
            continue
        n = sum(done.values())
        after = r['affected_count'] - n
        r['resolution'] = {'status': 'RESOLVED' if after == 0 else 'PARTIALLY_RESOLVED',
                           'affected_before': r['affected_count'], 'affected_after': after, 'recovered': n,
                           'by': [{'phase': s, 'commit': applied[s]['commit'], 'method': applied[s]['method'], 'items': k}
                                  for s, k in sorted(done.items())]}


def build():
    rows = figure_rows() + corpus_rows() + ocr_rows() + source_rows() + identity_rows() + evidence_rows() + historical_rows() + other_rows()
    resolve(rows)
    seen = collections.Counter(r['gap_id'] for r in rows)
    assert max(seen.values()) == 1, [k for k, n in seen.items() if n > 1][:3]
    rows.sort(key=rank_key)
    for i, r in enumerate(rows, 1):
        r['rank'] = i
    return rows


REPORT = L.ROOT + 'docs/DATA-GAP-REGISTER.md'


def _dist(rows, field, order):
    c = collections.Counter(r[field] for r in rows)
    return ' · '.join('%s %d' % (k, c[k]) for k in order if c[k]) or '—'


def _batch(rows):
    """The tier's effort as batches: rows sharing a method are one script run, so a tier costs about
    the sum, per method, of the largest bucket in it."""
    per = collections.defaultdict(list)
    for r in rows:
        per[r['proposed_resolution']].append(EFFORTS.index(r['effort']))
    return ', '.join('%s %s' % (m.lower().replace('_', ' '), EFFORTS[max(v)]) for m, v in sorted(per.items()))


def _fmt(n):
    return '{:,}'.format(n)


def _row_line(r):
    return '| %d | %s | %s | %s | %s | %s | %s | %s | %s |' % (
        r['rank'], r['description'].replace('|', '/'), _fmt(r['affected_count']), r['evidence_status'].replace('|', '/'),
        r['proposed_resolution'], r['effort'], r['effort_confidence'], r['cascading_benefit'], ', '.join(r['dependencies']))


HEAD = ('| # | Problem | Affected | Current evidence | Resolution | Effort | Confidence | Cascade | Dependency |\n'
        '|---:|---|---:|---|---|---|---|---|---|')


def report(rows):
    tiers = {t: [r for r in rows if r['priority'] == t] for t in TIERS}
    live = [r for r in rows if r['priority'] != 'DEFERRED']
    u = A.unsourced_figures()
    g = collections.Counter(r['group'] for r in u)
    amb = A.ambiguous_figures()
    fo = A.file_only_figures()
    om = A.observation_mapping()
    ocr = A.ocr_backlog()
    cov = collections.Counter(c['status'] for c in A.discovery_coverage()['coverage'])
    vdc = A.vintage_document_counts()
    no_new = [r for r in live if not r['requires_new_data']]
    new = [r for r in live if r['requires_new_data']]
    unmapped = [r for r in live if r['state'] == 'UNMAPPED']
    fam = lambda r: r['gap_key'].split('|')[0]
    out = []
    w = out.append
    w('# Data-gap register (M3.1)\n')
    w('*Built by `tools/build-data-gap-register.py` from the committed state; do not edit by hand. '
      'The rows are `data/audit/data-gap-register.jsonl`; every number here is computed from them or '
      'from `tools/data_gap_analysis.py`. Audit only: nothing was fixed, fetched or OCR\'d.*\n')
    w('**%s gaps** in the register: %s live, %s deliberately deferred.\n' % (_fmt(len(rows)), _fmt(len(live)), _fmt(len(tiers['DEFERRED']))))
    w('## Resolution-first dashboard\n')
    w('| Tier | Gap count | Estimated effort | Confidence | Cascading benefit |')
    w('|---|---:|---|---|---|')
    for t in TIERS[:5]:
        rs = tiers[t]
        w('| %s | %d | %s | %s | %s |' % (t, len(rs), _dist(rs, 'effort', EFFORTS), _dist(rs, 'effort_confidence', LEVELS),
                                          _dist(rs, 'cascading_benefit', LEVELS)))
    w('| DEFERRED | %d | — | — | — |\n' % len(tiers['DEFERRED']))
    w('**Effort as work.** A tier\'s rows that share a method are one script run, so the tier costs about the '
      'largest bucket per method, not the sum of the rows:\n')
    for t in TIERS[:5]:
        w('- **%s:** %s.' % (t, _batch(tiers[t]) or '—'))
    w('\nThe tiers follow from each row\'s fields by fixed rules (`tier()`): R1 is XS/S, HIGH or MEDIUM '
      'confidence, evidence held, no dependency; R2 is S/M with limited review; R3 processes existing files '
      '(OCR, large deterministic runs); R4 needs new retrieval; R5 is UNKNOWN or XL effort, an unavailable '
      'source, or a decision not yet taken.\n')
    w('## Which gaps can be resolved without acquiring any new data?\n')
    w('**%s live gaps (%s affected items)** need no new data: everything they need is held. They are %s.\n' % (
        _fmt(len(no_new)), _fmt(sum(r['affected_count'] for r in no_new)),
        ', '.join('%s %d' % (t, sum(1 for r in no_new if r['priority'] == t)) for t in TIERS[:5])))
    w('## Which gaps genuinely require new data?\n')
    w('**%s live gaps (%s affected items)**: a document no one holds, a site never or only partly crawled, '
      'or a source that does not exist yet. All of them are R4 or R5. Of these, %d are document-less vintages '
      '(%s vintages), and %d are other historical or figure sources.\n' % (
          _fmt(len(new)), _fmt(sum(r['affected_count'] for r in new)),
          sum(1 for r in new if fam(r) == 'VINTAGE_NO_DOCUMENT'),
          _fmt(sum(r['affected_count'] for r in new if fam(r) == 'VINTAGE_NO_DOCUMENT')),
          sum(1 for r in new if fam(r) != 'VINTAGE_NO_DOCUMENT')))
    w('## Mapping before scraping\n')
    w('Gaps where existing data probably holds the answer and the model does not yet connect it (state UNMAPPED): '
      '**%s gaps, %s affected items.** They outrank every scrape.\n' % (_fmt(len(unmapped)), _fmt(sum(r['affected_count'] for r in unmapped))))
    w('| Kind | Gaps | Affected | Tiers |')
    w('|---|---:|---:|---|')
    kinds = collections.defaultdict(list)
    for r in unmapped:
        kinds[fam(r)].append(r)
    label = {'FIG_UNSOURCED': 'figure → source (the record\'s own sheet)', 'FIG_AMBIGUOUS': 'figure → source (several candidates)',
             'FIG_FILE_ONLY': 'document → address (same bytes fetched online)', 'FILLABLE': 'harvested observation → missing figure',
             'CORPUS': 'harvested observation → estate/wine/vintage', 'UNINCORPORATED': 'harvested PDF → evidence store',
             'VINTAGE_SEVERAL_DOCUMENTS': 'document ↔ document (language versions, revisions)', 'OCR': 'image-only document → text',
             'HIST': 'current statement → current model', 'FINDING': 'orphan provenance → record'}
    for k, rs in sorted(kinds.items(), key=lambda kv: -sum(r['affected_count'] for r in kv[1])):
        w('| %s | %d | %s | %s |' % (label.get(k, k), len(rs), _fmt(sum(r['affected_count'] for r in rs)),
                                    ', '.join('%s %d' % (t, sum(1 for r in rs if r['priority'] == t)) for t in TIERS[:5]
                                              if any(r['priority'] == t for r in rs))))
    w('')
    w('## Top 25 fastest resolvable gaps\n')
    w('By rank: tier, then confidence, cascading benefit, effort, provenance and mapping first.\n')
    w(HEAD)
    for r in [r for r in rows if r['priority'] in ('R1', 'R2')][:25]:
        w(_row_line(r))
    w('\n## Top 10 cascading opportunities\n')
    w('Actionable gaps (R1-R4) with HIGH cascading benefit, by how many items one fix settles.\n')
    w(HEAD)
    for r in sorted([r for r in live if r['cascading_benefit'] == 'HIGH' and r['priority'] in TIERS[:4]],
                    key=lambda r: (-r['affected_count'], r['rank']))[:10]:
        w(_row_line(r))
    big5 = sorted([r for r in live if r['cascading_benefit'] == 'HIGH' and r['priority'] == 'R5'],
                  key=lambda r: (-r['affected_count'], r['rank']))[:2]
    w('\nThe two largest cascades are blocked (R5): %s.' % '; '.join(
        '%s (%s items, %s)' % (r['description'][:90], _fmt(r['affected_count']), ', '.join(r['blocking'])) for r in big5))
    w('\n## The 2,149 figures shown without a source\n')
    w('Recomputed now (Phase 6.1\'s measure, the same population of %s figures): linked %s, own file without an '
      'address %s, "source unclear" %s, **no established source %s**.\n' % (
          _fmt(len(A.figures())), _fmt(sum(1 for f in A.figures() if f['state'] == 'LINKED')),
          _fmt(len(fo)), _fmt(len(amb)), _fmt(len(u))))
    w('| Group | Figures | Looks | What it means |')
    w('|---|---:|---|---|')
    gtxt = [('1_LOCAL_IDENTIFIABLE', '1. local document exists and is identifiable', 'deterministic',
             'the record names one held sheet, and that sheet prints the exact value'),
            ('2_MULTIPLE_CANDIDATES', '2. several local documents are candidates', 'reviewable',
             'the record\'s sheet name matches several held documents'),
            ('3_RELATIONSHIP_UNCLEAR', '3. document held, figure-to-document unclear', 'reviewable',
             'the held sheet has text but does not print the value as such (%d of them are dates)' % sum(
                 1 for r in u if r['group'] == '3_RELATIONSHIP_UNCLEAR' and r['field'] in ('pick', 'harvest'))),
            ('3b_TEXT_NOT_STORED', '3b. document held, its text not stored', 'deterministic',
             'the sheet reader reads the PDF at run time; no stored text to check here (not OCR)'),
            ('4_NOT_HELD', '4. source named, document not held', 'research-dependent',
             'the record names a sheet no placement resolves'),
            ('5_UNAVAILABLE', '5. source genuinely unavailable', 'unavailable', 'none found'),
            ('6_UNKNOWN', '6. completely unknown', '—', 'every record names a sheet')]
    for key, name, looks, means in gtxt:
        w('| %s | %s | %s | %s |' % (name, _fmt(g.get(key, 0)), looks, means))
    w('\nPhase 6.4 counted 1,961 one-document, 152 several or ambiguous, 36 unknown documents. Now: %s one-document '
      '(groups 1, 3, 3b), %s several, %s not held. The value check is conservative: a number must stand as a '
      'token with its unit (alcohol with %%/°, yield with hl, oak with %%, months with mois/months, every blend '
      'share with %%).\n' % (_fmt(g['1_LOCAL_IDENTIFIABLE'] + g['3_RELATIONSHIP_UNCLEAR'] + g['3b_TEXT_NOT_STORED']),
                             _fmt(g['2_MULTIPLE_CANDIDATES']), _fmt(g['4_NOT_HELD'])))
    ac = collections.Counter('one prints it' if r['printed_in'] == 1 else 'several print it' if r['printed_in'] > 1
                             else 'none prints it' if r['checkable'] else 'no stored text' for r in amb)
    w('The %d "source unclear" figures: %s. The %d file-only figures: %d have a discovered URL for the same bytes.\n' % (
        len(amb), ', '.join('%s %d' % kv for kv in sorted(ac.items())), len(fo), sum(1 for r in fo if r['url_known'])))
    w('## The harvested observation corpus\n')
    w('**%s observations** on %s artifacts (`data/discovery/observations`), by how their document maps today, '
      'using only recorded links (accepted evidence decisions, legacy attributions, the crawl\'s attribution):\n' % (
          _fmt(om['total']), _fmt(om['artifacts'])))
    w('| Mapping | Observations |')
    w('|---|---:|')
    names = {'ESTATE_WINE_VINTAGE': 'estate + wine + vintage, all exact', 'ESTATE_WINE': 'estate + wine exact, vintage not',
             'ESTATE_VINTAGE': 'estate + vintage exact, wine not', 'ESTATE_ONLY': 'estate exact only',
             'ESTATE_DETERMINISTIC_CANDIDATE': 'estate deterministic (one strong crawl candidate), unreviewed',
             'AMBIGUOUS': 'ambiguous (several crawl candidates)', 'AMBIGUOUS_SHARED_DOCUMENT': 'one document of several estates (shared sheet)',
             'CONFLICTING': 'conflicting (record and crawl name different estates)', 'UNMAPPABLE': 'unmappable (no estate evidence)',
             'WINE_ONLY': 'wine only', 'VINTAGE_ONLY': 'vintage only'}
    for k, v in sorted(om['buckets'].items(), key=lambda kv: -kv[1]):
        w('| %s | %s |' % (names.get(k, k), _fmt(v)))
    w('\nExactly mappable: to an estate %s, to a wine %s, to a vintage %s, to all three %s. Wine-only and vintage-only '
      'do not occur: a wine or a vintage is only ever known through an estate\'s accepted document.\n' % (
          _fmt(om['exact']['estate']), _fmt(om['exact']['wine']), _fmt(om['exact']['vintage']), _fmt(om['exact']['estate_wine_vintage'])))
    fs = A.fillable_slots()
    w('**Recoverable by mapping alone:** %d vintage figures the model lacks are stated in an exactly mapped sheet '
      '(%s). They are reviewable, not automatic: crawled label lines carry other years ("Rendement 2023" on a 2024 sheet '
      'is excluded) and neighbouring cells, so each is filled only after reading its passage.\n' % (
          len(fs), ', '.join('%s %d' % kv for kv in sorted(collections.Counter(k.split('|')[1] for k in fs).items()))))
    w('## Targeted scraping backlog\n')
    w('Only gaps that need new data, traced to an identified gap; most valuable first.\n')
    w(HEAD)
    for r in sorted([r for r in live if r['proposed_resolution'] == 'TARGETED_FIRST_PARTY_SCRAPE'],
                    key=lambda r: (ORDER[r['cascading_benefit']], -r['affected_count'], r['rank']))[:25]:
        w(_row_line(r))
    sc = [r for r in live if r['proposed_resolution'] == 'TARGETED_FIRST_PARTY_SCRAPE']
    w('\n%d scrape targets in all (%s items). Crawl coverage of the 388 universe estates: %s. Sites blocked by '
      'robots.txt stay blocked; their gaps need another source.\n' % (
          len(sc), _fmt(sum(r['affected_count'] for r in sc)), ', '.join('%s %d' % kv for kv in sorted(cov.items()))))
    w('## OCR backlog\n')
    useful = [o for o in ocr if o['benefit'] != 'NONE']
    w('%d documents are image-only (NEEDS_OCR). **%d** would address an identified gap; the other %d are no record\'s '
      'sheet and the only document of no vintage, so OCR would close nothing today.\n' % (len(ocr), len(useful), len(ocr) - len(useful)))
    w(HEAD)
    for r in sorted([r for r in live if fam(r) == 'OCR'], key=lambda r: r['rank']):
        w(_row_line(r))
    w('\nNo OCR engine is installed (Phase 3.4, P16: "OCR NEEDED_NO_ENGINE"); installing one is part of R3.\n')
    w('## Blocked decisions\n')
    w('These cannot be resolved by work: each waits on a decision.\n')
    w(HEAD)
    for r in sorted([r for r in live if set(r['blocking']) & (BLOCKING_DEPS | {'MANUAL_DECISION'})], key=lambda r: r['rank']):
        w(_row_line(r))
    w('\n- **D2 (Echo).** Rename or succession; five M3 candidates wait. Three sources word it as a change of name '
      'from the 2008 vintage.\n- **La Parde → Haut-Bailly II.** The identity decision Phase 6.2 asked for; the evidence '
      '(the accepted 2018 sheet) is held.\n- **D5.** The conflict policy; the contemporaneous second-wine conflicts '
      '(Batailley, Lynch-Moussas) wait on it.\n- **D1.** What the estate-level blend means (%d AMBIGUOUS_SEMANTICS '
      'findings).\n' % sum(r['affected_count'] for r in rows if r['gap_key'] == 'FINDING|AMBIGUOUS_SEMANTICS'))
    w('## Deliberately deferred\n')
    w('Not worth resolving yet, unavailable, or not a gap at all.\n')
    w('| Kind | Rows | Items | Why |')
    w('|---|---:|---:|---|')
    dfam = collections.defaultdict(list)
    for r in tiers['DEFERRED']:
        dfam[fam(r)].append(r)
    why = {
        'ACCEPTED_UNAVAILABLE': 'checked and clean: every accepted document is held (sha256 proven)',
        'CORPUS': 'observations already exactly mapped (estate, wine, vintage) or on a document several estates share: nothing to connect',
        'FINDING': 'manifest rows naming a file never held; the figures that depend on an unheld sheet are counted in group 4 of the 2,149',
        'HIST': 'current statements and an absence inference: none is history, and M3 refused to treat them as such',
        'OCR': 'image-only documents no gap names: OCR them only when one does',
        'SITE': 'blocked (robots.txt, respected), unreachable, partly crawled or site-less estates on which no identified gap depends',
        'UNSOURCED_OBSERVATION': 'the dashboard\'s own editorial prose; it claims no source',
        'WINES_WITHOUT_ESTATE': 'checked and clean: every model wine has an estate',
        'WRONG_VINTAGE_REFUSED': 'the guard kept these sheets off the wrong vintage; no wrong-vintage attachment exists',
    }
    for k, rs in sorted(dfam.items()):
        w('| %s | %d | %s | %s |' % (k, len(rs), _fmt(sum(r['affected_count'] for r in rs)), why[k]))
    res = [r for r in rows if r.get('resolution')]
    if res:
        w('\n## Resolved since M3.1\n')
        w('Gaps a recovery stream reduced. Each keeps its id, tier and original count; the resolution '
          'records what changed and by which commit (`data/audit/m32-resolutions.json`).\n')
        st = collections.Counter(r['resolution']['status'] for r in res)
        by = collections.defaultdict(lambda: [0, 0])
        for r in res:
            for b in r['resolution']['by']:
                by[(b['phase'], b['commit'], b['method'])][0] += 1
                by[(b['phase'], b['commit'], b['method'])][1] += b['items']
        w('| Phase | Commit | Method | Gaps | Items recovered |')
        w('|---|---|---|---:|---:|')
        for (ph, cm, me), (gaps_n, items_n) in sorted(by.items()):
            w('| %s | `%s` | %s | %d | %s |' % (ph, cm, me, gaps_n, _fmt(items_n)))
        w('\n%d gaps resolved outright, %d partly; %s of their %s affected items recovered, %s remain.\n' % (
            st['RESOLVED'], st['PARTIALLY_RESOLVED'], _fmt(sum(r['resolution']['recovered'] for r in res)),
            _fmt(sum(r['resolution']['affected_before'] for r in res)), _fmt(sum(r['resolution']['affected_after'] for r in res))))
    w('\n## Method and limits\n')
    w('- **State.** MISSING: the information is not held. UNMAPPED: it is held and not connected. CONFLICTING: held '
      'statements disagree. UNRESOLVED: evidence exists and does not settle it. Every row has exactly one primary '
      'category and one state.\n'
      '- **Evidence is never promoted.** A probable mapping stays a candidate; a crawl attribution is never treated '
      'as an accepted decision; accepting a document\'s identity is not approving its content (M3).\n'
      '- **Effort** is for Claude Code to carry out the resolution, by method and size; **confidence** is separate; '
      '**cascade** is how many other gaps one fix settles.\n'
      '- **Limits.** "Value printed" is a conservative token check on stored text; the %s figures whose sheet has no '
      'stored text are not judged. The vintage-document counts use the model\'s derived index (none %s, one %s, '
      'several %s). Nothing was retrieved, so "requires new data" means "not held", not "does not exist".\n' % (
          _fmt(g['3b_TEXT_NOT_STORED']), _fmt(vdc.get('none', 0)), _fmt(vdc.get('one', 0)), _fmt(vdc.get('several', 0))))
    return '\n'.join(out) + '\n'


def main():
    rows = build()
    if '--report' in sys.argv:
        text = report(rows)
        if '--check' in sys.argv:
            same = os.path.exists(REPORT) and open(REPORT, encoding='utf-8').read() == text
            print('docs/DATA-GAP-REGISTER.md ' + ('is current' if same else 'differs from a fresh run'))
            sys.exit(0 if same else 1)
        with open(REPORT, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        print('wrote docs/DATA-GAP-REGISTER.md')
        return
    body = ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n' for r in rows).encode('utf-8')
    if '--check' in sys.argv:
        same = os.path.exists(OUT) and open(OUT, 'rb').read() == body
        print('data/audit/data-gap-register.jsonl ' + ('is current' if same else 'differs from a fresh run'))
        sys.exit(0 if same else 1)
    t = collections.Counter(r['priority'] for r in rows)
    print('%d gaps; tiers %s' % (len(rows), dict(sorted(t.items()))))
    print('categories %s' % dict(collections.Counter(r['category'] for r in rows).most_common()))
    if '--summary' in sys.argv:
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT + '.tmp', 'wb') as f:
        f.write(body)
    os.replace(OUT + '.tmp', OUT)
    print('wrote', os.path.relpath(OUT, L.ROOT))


if __name__ == '__main__':
    main()
