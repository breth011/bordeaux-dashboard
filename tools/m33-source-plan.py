"""M3.3: the highest-yield source acquisition plan (audit only).

    python tools/m33-source-plan.py             write data/audit/m3.3-source-acquisition-plan.jsonl
    python tools/m33-source-plan.py --check     recompute and compare, byte for byte
    python tools/m33-source-plan.py --report    write docs/PHASE-M3.3-HIGHEST-YIELD-SOURCES.md (also --check)

Nothing is fetched, crawled, OCR'd or written to the model. For every unresolved new-data gap of
the M3.1 register, the items it is missing are listed (a vintage with no document, a figure with
no source, an unsourced statement), and for each item the best evidence that some source holds it
is looked up in what the project already has, in this order:

  A1 EXISTING_ACCEPTED_DOCUMENT   the evidence store accepted a document for exactly this wine and
                                  vintage, but the model does not link it to the vintage
  A2 EXISTING_FETCHED_DOCUMENT    the crawl fetched a document of the estate headed with that year
  B  DISCOVERED_NOT_ACQUIRED      the crawl saw a first-party URL naming that year and never fetched
                                  it (budget, queue, size)
  B' DISCOVERED_OFFSITE_REDIRECT  a first-party link that redirected off the site
  X  BLOCKED_BY_POLICY            robots.txt, an AI-agent refusal, a challenge or a login: never acquired
  Y  DISCOVERED_DEAD_LINK         the URL answered an error
  D  SOURCE_DISCOVERY_REQUIRED    nothing known: the source must first be found

Each source candidate is scored by the documented, deterministic formula in score(). The score
ranks; it establishes nothing.
"""
import collections
import glob
import json
import os
import re
import sys
from urllib.parse import unquote, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_gap_analysis as A  # noqa: E402
import migration_lib as L  # noqa: E402

OUT = L.ROOT + 'data/audit/m3.3-source-acquisition-plan.jsonl'
REPORT = L.ROOT + 'docs/PHASE-M3.3-HIGHEST-YIELD-SOURCES.md'
REGISTER = L.ROOT + 'data/audit/data-gap-register.jsonl'
STATE = L.ROOT + 'sources/discovery/state/'

UNFETCHED = ('SKIPPED_BUDGET', 'QUEUED', 'TOO_LARGE')
BLOCKED = ('ROBOTS_DISALLOW', 'ROBOTS_DISALLOW_REDIRECT', 'BLOCKED_CHALLENGE', 'AUTH_REQUIRED')
DEAD = ('HTTP_ERROR', 'TLS_FAILURE', 'TIMEOUT', 'NETWORK_FAILURE', 'TOO_MANY_REDIRECTS')
DOC_WORD = re.compile(r'fiche|ft[-_ ]|technique|technical|factsheet|fact-sheet|sheet|millesime|vintage|cuvee|degustation|tasting')
STOP = {'chateau', 'domaine', 'grand', 'cuvee', 'blanc', 'rouge', 'second', 'vin', 'clos', 'cru', 'les', 'des', 'saint'}
EFFORT_MID = {'XS': 0.25, 'S': 0.75, 'M': 2.5, 'L': 10, 'XL': 20, 'UNKNOWN': 20}
POINTS = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
RANKED = {'EXISTING_ACCEPTED_DOCUMENT', 'EXISTING_FETCHED_DOCUMENT', 'EXISTING_OFFICIAL_SOURCE',
          'DISCOVERED_NOT_ACQUIRED', 'DISCOVERED_OFFSITE_REDIRECT'}
CATEGORY = {'EXISTING_ACCEPTED_DOCUMENT': 'A', 'EXISTING_FETCHED_DOCUMENT': 'A', 'EXISTING_OFFICIAL_SOURCE': 'A',
            'DISCOVERED_NOT_ACQUIRED': 'B', 'DISCOVERED_OFFSITE_REDIRECT': 'B', 'DISCOVERED_DEAD_LINK': 'B',
            'FIRST_PARTY_TARGETED': 'C', 'OFFICIAL_SOURCE_SUSPECTED': 'C', 'SOURCE_DISCOVERY_REQUIRED': 'D',
            'BLOCKED_BY_POLICY': 'E', 'CANNOT_ESTABLISH': 'E'}
# Items that would bear on an open identity decision: a document there is evidence for the decision,
# never a reason to make it (D2: Echo before 2008; La Parde: Haut-Bailly II before 2018).
DECISION_ITEMS = {('wn_00547', 2008): 'D2', ('wn_00522', 2018): 'LAPARDE_IDENTITY'}


# -- inputs ----------------------------------------------------------------------------------------

LATER = ('M3.4B', 'M3.5')         # phases after this plan: what they resolved was unresolved when it was made


def resolved_before(r):
    """A gap the register records as resolved by the phases before this plan (M3.2), not by later ones."""
    res = r.get('resolution') or {}
    earlier = sum(b['items'] for b in res.get('by', []) if b['phase'] not in LATER)
    return bool(res) and earlier >= res['affected_before']


def new_data_gaps():
    return [r for r in L.jsonl_lines(REGISTER) if r['requires_new_data'] and r['priority'] != 'DEFERRED'
            and not resolved_before(r)]


def names():
    return {n['subject']: n['name'] for n in A.table('identity/names.jsonl') if n['kind'] == 'CURRENT'}


def tokens(name):
    return sorted({t for t in re.findall(r'[a-z]{4,}', A.fold(name or '')) if t not in STOP})


def states():
    """domain -> {estates (model ids), seen {url: status}, robots}."""
    u2e = A.universe_to_estate()
    out = {}
    for p in sorted(glob.glob(STATE + '*.json')):
        d = json.load(open(p, encoding='utf-8'))
        out[d['domain']] = {'estates': sorted({u2e[u] for u in d['estates'] if u2e.get(u)}), 'seen': d['seen'],
                            'robots': {'delay': (d.get('robots') or {}).get('delay'),
                                       'ai_refused': bool((d.get('robots') or {}).get('ai_refused'))},
                            'stopped': d.get('stopped')}
    return out


def documentless():
    """estate -> [(wine, year)] exactly as the register derives VINTAGE_NO_DOCUMENT."""
    vdocs = A.vintage_documents()
    ew = collections.defaultdict(set)
    for r in A.table('state/estate-wine.jsonl'):
        ew[r['estate']].add(r['wine'])
    out = collections.defaultdict(list)
    for v in A.table('identity/vintages.jsonl'):
        if not vdocs.get('vt:%s:%s' % (v['wine'], v['label'])):
            for e, ws in sorted(ew.items()):
                if v['wine'] in ws:
                    out[e].append((v['wine'], int(v['label'])))
    return {e: sorted(v) for e, v in sorted(out.items())}


def year_in(path, y):
    return re.search(r'(?<!\d)%d(?!\d)' % y, path) is not None


# -- evidence per item ------------------------------------------------------------------------------

def item_evidence(st):
    """For every documentless (estate, wine, year): the evidence each kind of source offers."""
    nm = names()
    nodoc = documentless()
    vdocs = A.vintage_documents()
    accepted = collections.defaultdict(set)                     # (wine, year) -> artifacts
    for d in A.decisions():
        if d['decision'] == 'ACCEPTED' and d['wine'] and d['vintage'] and d['sha256']:
            aid = A.sha_to_artifact().get(d['sha256'])
            if aid:
                accepted[(d['wine'], int(d['vintage']))].add(aid)
    dart = {}
    for a in L.jsonl_lines(L.ROOT + 'data/discovery/artifacts.jsonl'):
        dart[a['sha256']] = a
    fetched = collections.defaultdict(list)                     # (estate, year) -> [(sha, title, url)]
    vc = A.vintage_candidates()
    for sha, a in dart.items():
        m = A.artifact_mapping(sha)
        if m['estate'] not in ('EXACT', 'DETERMINISTIC'):
            continue
        c = vc.get(sha) or {}
        for y in set(c.get('heading_years') or []) | set(c.get('title_years') or []):
            for e in m['estates']:
                fetched[(e, int(y))].append((sha, a.get('title') or '', a.get('first_url') or ''))
    dom_of = collections.defaultdict(list)
    for dmn, s in st.items():
        for e in s['estates']:
            dom_of[e].append(dmn)
    # a URL any crawl was refused (robots, AI rule, challenge, login) is refused, whatever another crawl recorded
    refused = {u for s in st.values() for u, status in s['seen'].items() if status in BLOCKED}
    out = {}
    for e, items in nodoc.items():
        for wine, y in items:
            toks = tokens(nm.get(wine))
            ev = []
            for aid in sorted(accepted.get((wine, y), set()) - set(vdocs.get('vt:%s:%d' % (wine, y), []))):
                ev.append({'family': 'EXISTING_ACCEPTED_DOCUMENT', 'confidence': 'HIGH', 'locator': aid,
                           'domain': None})
            for sha, title, url in sorted(fetched.get((e, y), [])):
                hay = A.fold(title + ' ' + unquote(url))
                conf = 'MEDIUM' if any(t in hay for t in toks) else 'LOW'
                ev.append({'family': 'EXISTING_FETCHED_DOCUMENT', 'confidence': conf,
                           'locator': A.sha_to_artifact().get(sha) or 'discovery:' + sha[:16],
                           'domain': urlparse(url).netloc.lower() or None})
            for dmn in sorted(dom_of.get(e, [])):
                for u, status in sorted(st[dmn]['seen'].items()):
                    path = A.fold(unquote(urlparse(u).path))
                    if not year_in(path, y):
                        continue
                    tok = any(t in path for t in toks)
                    doc = path.endswith('.pdf') or bool(DOC_WORD.search(path))
                    conf = 'HIGH' if tok and doc else 'MEDIUM' if tok or doc else 'LOW'
                    fam = ('BLOCKED_BY_POLICY' if u in refused else
                           'DISCOVERED_NOT_ACQUIRED' if status in UNFETCHED else
                           'DISCOVERED_OFFSITE_REDIRECT' if status == 'OFFSITE_REDIRECT' else
                           'BLOCKED_BY_POLICY' if status in BLOCKED or (st[dmn]['robots']['ai_refused'] and status != 'RETRIEVED') else
                           'DISCOVERED_DEAD_LINK' if status in DEAD else None)
                    if fam:
                        ev.append({'family': fam, 'confidence': conf if fam != 'DISCOVERED_OFFSITE_REDIRECT' else
                                   {'HIGH': 'MEDIUM', 'MEDIUM': 'LOW', 'LOW': 'LOW'}[conf],
                                   'locator': u, 'domain': dmn, 'status': status})
            out[(e, wine, y)] = ev
    return out, dom_of


# -- candidates -------------------------------------------------------------------------------------

def effort_by_count(n, kind):
    if kind == 'fetch':             # polite fetches (robots delay 1.5 s) and per-document review
        return 'XS' if n <= 5 else 'S' if n <= 25 else 'M' if n <= 120 else 'L' if n <= 500 else 'XL'
    return 'XS' if n <= 10 else 'S' if n <= 60 else 'M' if n <= 300 else 'L'      # mapping held documents


def score(c):
    """The documented yield score: item points plus source bonuses, over the effort midpoint.
    Items, not register rows, are counted: a register row is an estate's whole set of document-less
    vintages, so one row can be resolved item by item. (The brief's model, applied to items.)"""
    pts = sum(POINTS[k] * c['items_by_confidence'].get(k, 0) for k in POINTS)
    b = 0
    b += 3 if c['party'] == 'FIRST_PARTY' else 0
    b += 3 if c['already_discovered'] else 0
    b += 4 if c['already_stored'] else 0
    b += 3 if c['potential_vintage_count'] >= 3 else 0
    b += 2 if c['potential_wine_count'] >= 2 else 0
    b += 2 if c['exact_document_provenance'] else 0
    b -= 2 if c['requires_ocr'] else 0
    b -= 3 if c['requires_new_scraping'] == 'BROAD' else 0
    b -= 4 if c['party'] == 'THIRD_PARTY' else 0
    eff = c['acquisition_effort'] if c['acquisition_effort'] != 'NONE' else c['extraction_effort']
    return round((pts + b) / EFFORT_MID[eff], 3), pts, b


def candidate(fam, key, items, ev_by_item, gaps_by_item, nm, **kw):
    """One source candidate over its items: [(estate, wine, year, confidence, locators)]."""
    conf = collections.Counter(i[3] for i in items)
    locs = sorted({l for i in items for l in i[4]})
    blocked = []
    for _, w, y, _, _ in items:
        for (dw, dy), dec in DECISION_ITEMS.items():
            if w == dw and y < dy:
                blocked.append(dec)
    gaps = sorted({gaps_by_item[(e, w, y)] for e, w, y, _, _ in items})
    c = {'source_candidate_id': 'src_' + L.stable_hash('M33Source', fam, key), 'source_key': key, 'source_family': fam,
         'category': CATEGORY[fam], 'estates': sorted({e for e, _, _, _, _ in items}),
         'estate_names': sorted({nm.get(e, e) for e, _, _, _, _ in items}),
         'wines': sorted({w for _, w, _, _, _ in items}), 'wine_names': sorted({nm.get(w, w) for _, w, _, _, _ in items}),
         'vintages': sorted({y for _, _, y, _, _ in items}),
         'gap_ids': gaps, 'potential_gap_count': len(gaps),
         'high_confidence_gap_count': len({gaps_by_item[(e, w, y)] for e, w, y, cf, _ in items if cf == 'HIGH'}),
         'potential_item_count': len(items), 'items_by_confidence': dict(sorted(conf.items())),
         'potential_estate_count': len({e for e, _, _, _, _ in items}),
         'potential_wine_count': len({w for _, w, _, _, _ in items}),
         'potential_vintage_count': len({y for _, _, y, _, _ in items}),
         'locators': locs, 'locator_count': len(locs),
         'expected_fields': ['vintage document (technical sheet or vintage page): alc, blend, oak, months, yield, pH as stated'],
         'open_decisions': sorted(set(blocked))}
    c.update(kw)
    return c


def build():
    st = states()
    nm = names()
    gaps = new_data_gaps()
    ev, dom_of = item_evidence(st)
    gaps_by_item = {}
    for g in gaps:
        if g['gap_key'].startswith('VINTAGE_NO_DOCUMENT|'):
            e = g['gap_key'].split('|')[1]
            for (ee, w, y) in ev:
                if ee == e:
                    gaps_by_item[(ee, w, y)] = g['gap_id']
    groups = collections.defaultdict(list)                       # (family, key) -> items
    best = {}
    for (e, w, y), evs in sorted(ev.items()):
        order = ['EXISTING_ACCEPTED_DOCUMENT', 'EXISTING_FETCHED_DOCUMENT', 'DISCOVERED_NOT_ACQUIRED',
                 'DISCOVERED_OFFSITE_REDIRECT', 'BLOCKED_BY_POLICY', 'DISCOVERED_DEAD_LINK']
        by_fam = collections.defaultdict(list)
        for x in evs:
            by_fam[x['family']].append(x)
        for fam, xs in by_fam.items():
            top = max(xs, key=lambda x: POINTS[x['confidence']])['confidence']
            key = ('estate:' + e) if fam == 'EXISTING_ACCEPTED_DOCUMENT' else \
                  ('domain:' + (xs[0]['domain'] or 'unknown')) if fam != 'EXISTING_FETCHED_DOCUMENT' else ('estate:' + e)
            # only the item's best-evidence locators: a batch fetches those, not every page naming the year
            groups[(fam, key)].append((e, w, y, top, sorted({x['locator'] for x in xs if x['confidence'] == top})))
        fams = [f for f in order if f in by_fam]
        best[(e, w, y)] = fams[0] if fams else 'SOURCE_DISCOVERY_REQUIRED'
    # items with no evidence at all: the source must first be found
    cov = {c.get('model_estate'): c for c in A.discovery_coverage()['coverage'] if c.get('model_estate')}
    for (e, w, y), fam in sorted(best.items()):
        if fam == 'SOURCE_DISCOVERY_REQUIRED':
            site = (cov.get(e) or {}).get('status', 'NOT_IN_UNIVERSE')
            groups[('SOURCE_DISCOVERY_REQUIRED', 'estate:%s|%s' % (e, site))].append((e, w, y, 'LOW', []))
    rows = []
    for (fam, key), items in sorted(groups.items()):
        doms = sorted({d for (e, _, _, _, _) in items for d in dom_of.get(e, [])})
        dom = key.split(':', 1)[1] if key.startswith('domain:') else None
        stored = fam in ('EXISTING_ACCEPTED_DOCUMENT', 'EXISTING_FETCHED_DOCUMENT')
        discovered = fam not in ('SOURCE_DISCOVERY_REQUIRED',)
        n_loc = len({l for i in items for l in i[4]})
        if fam in ('EXISTING_ACCEPTED_DOCUMENT', 'EXISTING_FETCHED_DOCUMENT'):
            acq, ext, scrape = 'NONE', effort_by_count(len(items), 'map'), 'NONE'
        elif fam in ('DISCOVERED_NOT_ACQUIRED', 'DISCOVERED_OFFSITE_REDIRECT'):
            acq, ext, scrape = effort_by_count(n_loc, 'fetch'), effort_by_count(len(items), 'map'), 'TARGETED'
        else:
            acq, ext, scrape = 'UNKNOWN', 'UNKNOWN', ('BROAD' if fam == 'SOURCE_DISCOVERY_REQUIRED' else 'NONE')
        robots = st[dom]['robots'] if dom in st else None
        best_here = sum(1 for (e, w, y, _, _) in items if best.get((e, w, y)) == fam)
        c = candidate(fam, key, items, ev, gaps_by_item, nm,
                      items_where_best_source=best_here,
                      domain=dom, domains=doms,
                      party='FIRST_PARTY' if fam != 'SOURCE_DISCOVERY_REQUIRED' else 'UNKNOWN',
                      already_discovered=discovered, already_stored=stored,
                      exact_document_provenance=fam in ('EXISTING_ACCEPTED_DOCUMENT', 'DISCOVERED_NOT_ACQUIRED'),
                      requires_ocr=False, requires_new_scraping=scrape,
                      acquisition_effort=acq, extraction_effort=ext,
                      robots=robots,
                      url_status='suspected' if fam == 'SOURCE_DISCOVERY_REQUIRED' else 'seen by the crawl' if
                      fam.startswith('DISCOVERED') or fam == 'BLOCKED_BY_POLICY' else 'held')
        finish(c)
        rows.append(c)
    rows += other_candidates(st, nm)
    rows.sort(key=lambda c: (-c['yield_score'], -c['high_confidence_gap_count'], list(EFFORT_MID).index(
        c['acquisition_effort'] if c['acquisition_effort'] in EFFORT_MID else 'UNKNOWN'), c['source_candidate_id']))
    for i, c in enumerate(rows, 1):
        c['rank'] = i
    return rows, gaps, best


def finish(c):
    fam = c['source_family']
    c['provenance_quality'] = {'EXISTING_ACCEPTED_DOCUMENT': 'EXACT_DOCUMENT_ACCEPTED',
                               'EXISTING_FETCHED_DOCUMENT': 'EXACT_DOCUMENT_UNREVIEWED',
                               'EXISTING_OFFICIAL_SOURCE': 'OFFICIAL_DOCUMENT',
                               'DISCOVERED_NOT_ACQUIRED': 'EXACT_URL_FIRST_PARTY',
                               'DISCOVERED_OFFSITE_REDIRECT': 'FIRST_PARTY_LINK_OFFSITE_TARGET',
                               'FIRST_PARTY_TARGETED': 'FIRST_PARTY_SUSPECTED',
                               'OFFICIAL_SOURCE_SUSPECTED': 'OFFICIAL_SUSPECTED',
                               'SOURCE_DISCOVERY_REQUIRED': 'UNKNOWN'}.get(fam, 'NONE')
    c['cascading_benefit'] = 'HIGH' if c['potential_item_count'] >= 10 else 'MEDIUM' if c['potential_item_count'] >= 3 else 'LOW'
    if fam in RANKED and not c['open_decisions']:
        c['yield_score'], c['item_points'], c['bonus_points'] = score(c)
        c['status'] = 'RANKED'
    else:
        c['yield_score'], c['item_points'], c['bonus_points'] = 0.0, 0, 0
        c['status'] = ('BLOCKED_BY_EDITORIAL_OR_IDENTITY_DECISION' if c['open_decisions'] else
                       'BLOCKED_BY_POLICY' if fam == 'BLOCKED_BY_POLICY' else
                       'UNAVAILABLE_AT_KNOWN_URL' if fam == 'DISCOVERED_DEAD_LINK' else
                       'DEFERRED_DISCOVERY_REQUIRED' if fam == 'SOURCE_DISCOVERY_REQUIRED' else
                       'CANNOT_ESTABLISH' if fam == 'CANNOT_ESTABLISH' else 'DEFERRED')
    c['why'] = WHY[fam]
    c['acquire'] = ('acquire' if c['status'] == 'RANKED' and c['category'] == 'B' else
                    'map from the existing corpus (no acquisition)' if c['status'] == 'RANKED' and c['category'] == 'A' else
                    'do not acquire: ' + c['status'].lower().replace('_', ' '))


WHY = {
    'EXISTING_ACCEPTED_DOCUMENT': 'the evidence store accepted a document for exactly this wine and vintage; the model does not link it - a mapping task, not an acquisition',
    'EXISTING_FETCHED_DOCUMENT': 'the crawl fetched an estate document headed with the vintage; it was never reviewed for this wine - extraction and review, no acquisition',
    'EXISTING_OFFICIAL_SOURCE': 'an official source already held states it',
    'DISCOVERED_NOT_ACQUIRED': 'the estate\'s own site links a document naming the vintage; the crawl skipped it for budget - one targeted fetch per URL, no crawling',
    'DISCOVERED_OFFSITE_REDIRECT': 'a first-party link that redirects off the site (often a CDN): the target must be checked to be the estate\'s file',
    'BLOCKED_BY_POLICY': 'robots.txt, an AI-agent refusal, a challenge or a login stands in the way: respected, never acquired',
    'DISCOVERED_DEAD_LINK': 'the URL answered an error: the document is not available there',
    'FIRST_PARTY_TARGETED': 'a first-party page likely to state it, not yet seen',
    'OFFICIAL_SOURCE_SUSPECTED': 'an official body publishes it; the exact document is not known',
    'SOURCE_DISCOVERY_REQUIRED': 'nothing known holds it: the estate publishes no such document anywhere the crawl looked',
    'CANNOT_ESTABLISH': 'a source that exists but cannot establish the fact needed',
}


# -- the other new-data gaps --------------------------------------------------------------------------

def other_candidates(st, nm):
    """Latour's unheld sheets, the held sheets with no address, the unsourced not-made years, Corbin
    2022, the classification editions: each looked up in the corpus first."""
    gaps = {g['gap_key']: g for g in new_data_gaps()}
    rows = []
    all_seen = {}
    for dmn, s in st.items():
        for u, status in s['seen'].items():
            all_seen.setdefault(os.path.basename(urlparse(u).path).lower(), []).append((u, status, dmn))
    # Latour: the record names sheets the store does not hold
    g = gaps.get('FIG_UNSOURCED|4_NOT_HELD|latour')
    if g:
        figs = [f for f in A.unsourced_figures() if f['group'] == '4_NOT_HELD']
        names_ = sorted({f.get('basename') for f in figs if f.get('basename')})
        found = [(n, all_seen.get(n.lower(), [])) for n in names_]
        seen_any = [(n, x) for n, x in found if x]
        fam = 'DISCOVERED_NOT_ACQUIRED' if any(s in UNFETCHED for _, x in seen_any for _, s, _ in x) else \
              'BLOCKED_BY_POLICY' if any(s in BLOCKED for _, x in seen_any for _, s, _ in x) else 'SOURCE_DISCOVERY_REQUIRED'
        rows.append(other(fam, 'latour-unheld-sheets', g, len(figs), 'LOW' if fam == 'SOURCE_DISCOVERY_REQUIRED' else 'MEDIUM',
                          ['latour'], sorted({u for _, x in seen_any for u, _, _ in x}),
                          note='the record names %d sheet(s) (%s); the crawl saw %d of those names' % (
                              len(names_), ', '.join(names_[:4]), len(seen_any)),
                          fields=['the field sources of 36 figures (picking dates, blends...)'],
                          scrape='NONE' if fam != 'SOURCE_DISCOVERY_REQUIRED' else 'TARGETED'))
    # held sheets with no known address
    g = gaps.get('FIG_FILE_ONLY|NO_URL')
    if g:
        fo = [f for f in A.file_only_figures() if not f['url_known']]
        by_doc = collections.defaultdict(list)
        for f in fo:
            by_doc[f['document']].append(f)
        arts = A.by_id('identity/artifacts.jsonl')
        same_name_unfetched, other_bytes = set(), 0
        for aid, fs in by_doc.items():
            bn = fs[0]['provenance']['legacy_reference']['basename'].lower()
            for u, s, d in all_seen.get(bn, []):
                if s in UNFETCHED:
                    same_name_unfetched.add((aid, u))
                elif s == 'RETRIEVED':
                    other_bytes += 1
        cnt = sum(len(by_doc[a]) for a, _ in same_name_unfetched)
        rows.append(other('DISCOVERED_NOT_ACQUIRED' if same_name_unfetched else 'SOURCE_DISCOVERY_REQUIRED',
                          'held-sheets-address', g, len(fo), 'MEDIUM' if same_name_unfetched else 'LOW',
                          sorted({A.estate_of_record(f['record']) for f in fo}), sorted({u for _, u in same_name_unfetched}),
                          note='%d held sheets with no address; %d have an unfetched URL of the same file name (its bytes '
                               'must be compared); %d of their names were fetched with other bytes (another version, '
                               'which cannot give these bytes an address)' % (len(by_doc), len(same_name_unfetched), other_bytes),
                          fields=['a web address for the held bytes'], items_override=cnt or len(fo),
                          scrape='TARGETED' if same_name_unfetched else 'BROAD'))
    # unsourced not-made years, Corbin 2022: first-party statements, looked for in the fetched text
    for key, words, estates in (('HIST|NOT_MADE|wn_00458', ('pas produit', 'non produit', 'not produced', "pas d'yquem", 'no yquem'), ['yquem']),
                                ('HIST|NOT_MADE|wn_00230', ('pas produit', 'non produit', 'not produced', 'pas de climens'), ['climens']),
                                ('HIST|NOT_MADE|wn_00253', ('pas produit', 'non produit', 'not produced', 'arrach', 'replant'), ['myrat']),
                                ('HIST|CORBIN_2022', ('no second wine', 'pas de second vin', 'second vin'), ['corbin'])):
        g = gaps.get(key)
        if not g:
            continue
        hits = corpus_statements(st, estates, words)
        rows.append(other('EXISTING_FETCHED_DOCUMENT' if hits else 'FIRST_PARTY_TARGETED', key.lower(), g,
                          g['affected_count'], 'MEDIUM' if hits else 'LOW', estates, sorted(hits)[:10],
                          note=('%d fetched first-party document(s) of the estate carry the wording; each must be read '
                                'for the years' % len(hits)) if hits else
                          'no fetched first-party document carries the wording; an estate history or vintage page is the likely source, not yet known',
                          fields=['an explicit first-party statement (not made / no second wine) with its year'],
                          scrape='NONE' if hits else 'TARGETED'))
    g = gaps.get('HIST|CB_EDITION')
    if g:
        rows.append(other('OFFICIAL_SOURCE_SUSPECTED', 'crus-bourgeois-2020-edition', g, 1, 'LOW', [], [],
                          note='held: the 2025 Crus Bourgeois list (acb-cb-2025), the INAO Saint-Emilion 2022 communique '
                               '(which names the 2012 list it replaced), encyclopedia notes on 1953/1959 and 1994-2012. '
                               'Not held: the 2020 Crus Bourgeois list or the 2012/2006 Saint-Emilion lists themselves. The '
                               'publisher (crus-bourgeois.com, the INAO) is known; the document URL is not.',
                          fields=['an earlier classification edition: its members and ranks'], scrape='TARGETED',
                          domain='crus-bourgeois.com (suspected)'))
    return rows


def corpus_statements(st, estates, words):
    """Fetched first-party documents of these estates' domains whose text carries one of the words."""
    rx = re.compile('|'.join(re.escape(w) for w in words))
    doms = {d for d, s in st.items() if any(any(k in e for k in estates) for e in s['estates'] + [d])}
    hits = set()
    for a in L.jsonl_lines(L.ROOT + 'data/discovery/artifacts.jsonl'):
        if not any(dd in (a.get('domains') or []) for dd in doms):
            continue
        t = A.text_of(a['sha256'])
        if t and rx.search(t):
            hits.add(A.sha_to_artifact().get(a['sha256']) or 'discovery:' + a['sha256'][:16])
    return hits


def other(fam, key, gap, items, conf, estates, locators, note, fields, scrape, items_override=None, domain=None):
    n = items_override if items_override is not None else items
    c = {'source_candidate_id': 'src_' + L.stable_hash('M33Source', fam, key), 'source_key': key, 'source_family': fam,
         'category': CATEGORY[fam], 'estates': estates, 'estate_names': estates, 'wines': [], 'wine_names': [],
         'vintages': [], 'gap_ids': [gap['gap_id']], 'potential_gap_count': 1,
         'high_confidence_gap_count': 1 if conf == 'HIGH' else 0, 'potential_item_count': n,
         'items_by_confidence': {conf: n}, 'potential_estate_count': len(estates), 'potential_wine_count': 0,
         'potential_vintage_count': 0, 'locators': locators, 'locator_count': len(locators),
         'expected_fields': fields, 'open_decisions': [], 'domain': domain, 'domains': [],
         'party': 'OFFICIAL' if fam.startswith('OFFICIAL') else 'FIRST_PARTY',
         'already_discovered': fam not in ('SOURCE_DISCOVERY_REQUIRED', 'FIRST_PARTY_TARGETED', 'OFFICIAL_SOURCE_SUSPECTED'),
         'already_stored': fam.startswith('EXISTING'), 'exact_document_provenance': fam == 'DISCOVERED_NOT_ACQUIRED',
         'requires_ocr': False, 'requires_new_scraping': scrape,
         'acquisition_effort': 'NONE' if fam.startswith('EXISTING') else effort_by_count(len(locators), 'fetch')
         if fam == 'DISCOVERED_NOT_ACQUIRED' else 'UNKNOWN',
         'extraction_effort': effort_by_count(n, 'map') if fam.startswith('EXISTING') or fam == 'DISCOVERED_NOT_ACQUIRED' else 'UNKNOWN',
         'robots': None, 'url_status': 'held' if fam.startswith('EXISTING') else 'seen by the crawl' if locators else 'suspected',
         'note': note}
    finish(c)
    return c


# -- output ---------------------------------------------------------------------------------------

def body(rows):
    return ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                   for r in rows).encode('utf-8')


def main():
    rows, gaps, best = build()
    if '--report' in sys.argv:
        import m33_report
        text = m33_report.report(rows, gaps, best)
        if '--check' in sys.argv:
            same = os.path.exists(REPORT) and open(REPORT, encoding='utf-8').read() == text
            print('docs/PHASE-M3.3-HIGHEST-YIELD-SOURCES.md ' + ('is current' if same else 'differs from a fresh run'))
            sys.exit(0 if same else 1)
        open(REPORT, 'w', encoding='utf-8', newline='\n').write(text)
        print('wrote docs/PHASE-M3.3-HIGHEST-YIELD-SOURCES.md')
        return
    b = body(rows)
    if '--check' in sys.argv:
        same = os.path.exists(OUT) and open(OUT, 'rb').read() == b
        print('data/audit/m3.3-source-acquisition-plan.jsonl ' + ('is current' if same else 'differs from a fresh run'))
        sys.exit(0 if same else 1)
    print('%d source candidates; %s' % (len(rows), dict(collections.Counter(r['status'] for r in rows).most_common())))
    print('items by best source: %s' % dict(collections.Counter(best.values()).most_common()))
    with open(OUT + '.tmp', 'wb') as f:
        f.write(b)
    os.replace(OUT + '.tmp', OUT)
    print('wrote', os.path.relpath(OUT, L.ROOT))


if __name__ == '__main__':
    main()
