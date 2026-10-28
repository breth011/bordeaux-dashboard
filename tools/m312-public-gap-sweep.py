"""M3.12: the Bordeaux-wide public missing-data sweep - every missing vintage datapoint, and what public evidence
the repository already holds for it. An audit: nothing in the model, the evidence store, the discovery store or the
app changes.

    python tools/m312-public-gap-sweep.py           write data/audit/public-gap-sweep.jsonl and
                                                    docs/PHASE-M3.12-PUBLIC-GAP-SWEEP.md
    python tools/m312-public-gap-sweep.py --check   recompute both and compare, byte for byte

THE SURFACE is every vintage the model holds, of every wine, crossed with the seven vintage fields the value runner
can apply (tools/apply-value-manifest.py FIELDS: alc, blend, months, oak, pick, ph, yld), less the datapoints the
model has a canonical value for. A missing vintage is never inferred from an absent year: one enters only where a
held public document of the estate states a single year the model does not hold.

THE PUBLIC WEB is what the project's discovery crawl fetched from the estates' own sites (data/discovery, robots
respected, per-domain profiles), the earlier acquisition and review audits, and the model's documents and evidence.
Nothing is fetched here: a new crawl writes data/discovery, which the model is built from, and is its own phase.
Domains the crawl did not reach are reported as not searched, never as empty.

EACH DATAPOINT gets one missingness status (never collapsed):
  NOT_PRODUCED      the model states the vintage was not produced
  NOT_EXTRACTED     a document mapped exactly to the vintage carries the field (data present, unconnected)
  EXTRACTION_FAILED the vintage's documents are held but unreadable (OCR needed, extraction failed)
  NOT_PUBLISHED     the vintage's readable documents carry no label for the field
  SOURCE_MISSING    no document of the vintage is in the model
  NOT_FOUND         ... and the estate's reached first-party site holds none either
  UNKNOWN           not established (the field cannot be checked in the held text, or the site was not reached)
and one discovery class: KNOWN_ARTIFACT_WITH_MISSING_FIELDS, KNOWN_DOCUMENT_NOT_LINKED, KNOWN_URL_NOT_ACQUIRED,
KNOWN_FIRST_PARTY_DOMAIN_NOT_SEARCHED, BLOCKED_PUBLIC_ROUTE, CONFLICT_REQUIRES_REVIEW, NO_PUBLIC_EVIDENCE (and, for a
fresh crawl only, NEW_PUBLIC_DOCUMENT / NEW_PUBLIC_FIELD_EVIDENCE: none here). Candidates are leads: a file name or a
heading year is not identity (docs/PHASE-M3.4A, the reader decides), so every row's review_status is NOT_REVIEWED.
Tiers: A an estate's own or confirmed estate-controlled domain; B none (the rules admit no external source for these
fields); C any other host.
"""
import collections
import glob
import hashlib
import importlib.util
import json
import os
import re
import sys
from urllib.parse import unquote, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import migration_lib as L  # noqa: E402
import data_gap_analysis as A  # noqa: E402

OUT = L.ROOT + 'data/audit/public-gap-sweep.jsonl'
DOC = L.ROOT + 'docs/PHASE-M3.12-PUBLIC-GAP-SWEEP.md'
VINTAGE_FIELD = 'vintage'
FIRST_YEAR, LAST_YEAR = 1950, 2027
CONFIRMED = {'CONFIRMED_FIRST_PARTY', 'CONFIRMED_ESTATE_CONTROLLED'}
PRIORITY = {1: 'known first-party document carries or may carry it', 2: 'first-party, predictable route (read, OCR, '
            'link or retry a known document or URL)', 3: 'first-party page carries it', 4: 'authoritative external',
            5: 'third-party lead to confirm first-party', 6: 'no plausible public source'}


def _vr():
    spec = importlib.util.spec_from_file_location('apply_value_manifest_m312', L.ROOT + 'tools/apply-value-manifest.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


FIELDS = tuple(sorted(_vr().FIELDS))
LABEL_FIELDS = {f for f, _ in A.LABEL_FIELD}


def current_model():
    """data_gap_analysis reads the model as the M3.1 audits did; the sweep reads it as it stands now."""
    A._later_identity = lambda: (set(), set())
    A.LATER_ACTORS = ()


def host(u):
    h = urlparse(u or '').netloc.lower()
    return h[4:] if h.startswith('www.') else h


def template(u):
    """A URL's route shape, host left out so that estates can share it: its directories with years and other digit
    runs generalised, and the file reduced to its extension."""
    path = unquote(urlparse(u or '').path).lower()
    d, _, name = path.rpartition('/')
    d = re.sub(r'\d+', '{N}', re.sub(r'(?<!\d)(?:19|20)\d\d(?!\d)', '{YYYY}', d))
    ext = name.rsplit('.', 1)[1] if '.' in name else '(page)'
    return '%s/*.%s' % (d, ext) if ext != '(page)' else '%s/<page>' % d


def sid(*parts):
    return 'gs_' + hashlib.sha1('|'.join(str(p) for p in parts).encode('utf-8')).hexdigest()[:12]


class World:
    """Everything read once."""

    def __init__(self):
        current_model()
        T = L.read_table
        self.names = {}
        for n in T('identity/names.jsonl'):
            if n['kind'] == 'CURRENT':
                self.names.setdefault(n['subject'], n['name'])
        self.wine_estate = collections.defaultdict(set)
        self.estate_wines = collections.defaultdict(set)
        for r in T('state/estate-wine.jsonl'):
            self.wine_estate[r['wine']].add(r['estate'])
            self.estate_wines[r['estate']].add(r['wine'])
        self.vintages = sorted({(v['wine'], v['label']) for v in T('identity/vintages.jsonl')})
        self.vset = {'vt:%s:%s' % k for k in self.vintages}
        self.not_produced = {r['vintage'] for r in T('state/vintage-statements.jsonl') if r['kind'] == 'NOT_PRODUCED'}
        self.values = collections.defaultdict(dict)
        for c in T('canonical/values.jsonl'):
            if c['subject'].startswith('vt:'):
                self.values[c['subject']][c['field']] = c['status']
        self.artifacts = {a['id']: a for a in T('identity/artifacts.jsonl')}
        # the legacy fiche pipeline's own documents (sources.json rows): already read for every vintage field
        self.legacy_read = {p['artifact'] for p in T('document/placements.jsonl')
                            if p.get('artifact') and 'legacy_manifest_row' in p}
        self.sha_art = {a['sha256']: a['id'] for a in self.artifacts.values() if a.get('sha256')}
        self.vdocs = A.vintage_documents(())
        self.fillable = {}
        for k, shas in A.fillable_slots().items():
            vt, f = k.rsplit('|', 1)
            self.fillable[(vt, f)] = shas
        self.obs = A.observation_counts()
        self.disc = {a['sha256']: a for a in L.jsonl_lines(L.ROOT + 'data/discovery/artifacts.jsonl')}
        self.labels = self._labels()
        self._domains()
        self._crawl_urls()
        self._candidates()
        self._refused()

    def _labels(self):
        """sha256 -> the label fields its harvested observations carry (any value)."""
        out = collections.defaultdict(set)
        for p in sorted(glob.glob(L.ROOT + 'data/discovery/observations/*.jsonl')):
            for line in open(p, encoding='utf-8'):
                i = line.find(A.ART_KEY) + len(A.ART_KEY)
                sha = line[i:i + 64]
                lab = A.fold(json.loads(line).get('label') or '').strip()
                for f, rx in A.LABEL_FIELD:
                    if rx.match(lab):
                        out[sha].add(f)
        return out

    def _domains(self):
        """Per estate: its first-party domains (the crawl's targets and M3.7's confirmed relationships) and the
        crawl's outcome for them; per domain: robots and document patterns from the crawl's profiles."""
        u2e = A.universe_to_estate()
        self.estate_domains = collections.defaultdict(set)
        self.estate_cov = collections.defaultdict(set)
        for c in json.load(open(L.ROOT + 'data/discovery/coverage.json', encoding='utf-8')):
            e = u2e.get(c['estate'])
            if not e:
                continue
            self.estate_cov[e].add(c['status'])
            if c.get('domain'):
                self.estate_domains[e].add(c['domain'][4:] if c['domain'].startswith('www.') else c['domain'])
        m37 = L.jsonl_lines(L.ROOT + 'data/audit/m3.7-source-confirmation.jsonl')
        src_host = {r['source']: r.get('canonical_host') for r in m37 if r['record'] == 'source'}
        for r in m37:
            if r['record'] == 'relationship' and r['status'] in CONFIRMED and src_host.get(r['source']):
                self.estate_domains[r['estate']].add(src_host[r['source']].lower().replace('www.', '', 1))
        prof = json.load(open(L.ROOT + 'data/discovery/profiles.json', encoding='utf-8'))
        # a group domain - the crawl's profile says it serves several target estates, M3.7 records the source as
        # shared, or several estates claim it - is first-party for the group, not proof of the estate
        owners = collections.Counter(d for ds in self.estate_domains.values() for d in ds)
        self.shared = {d.replace('www.', '', 1) for d, p in prof.items()
                       if ((p.get('serves_several_target_estates') or {}).get('value') is True)}
        self.shared |= {str(r.get('canonical_host') or '').lower().replace('www.', '', 1) for r in m37
                        if r['record'] == 'source' and r.get('shared') is True}
        self.shared |= {d for d, n in owners.items() if n > 1}

    def _crawl_urls(self):
        """Per (estate, year): first-party URLs the crawl saw but did not hold - refused by robots, or failed."""
        dom_estates = collections.defaultdict(set)
        for e, ds in self.estate_domains.items():
            for d in ds:
                dom_estates[d].add(e)
        self.blocked = collections.defaultdict(set)
        self.failed = collections.defaultdict(set)
        for p in sorted(glob.glob(L.ROOT + 'data/discovery/locations/*.jsonl')):
            for d in L.jsonl_lines(p):
                kind, u = d.get('kind'), d.get('url') or ''
                if kind not in ('ROBOTS_DISALLOW', 'HTTP_ERROR') or not u.lower().endswith('.pdf'):
                    continue
                ys = {int(y) for y in re.findall(r'(?<!\d)((?:19|20)\d\d)(?!\d)', unquote(urlparse(u).path))}
                es = dom_estates.get(host(u), set())
                if len(ys) != 1 or len(es) != 1:
                    continue
                key = (next(iter(es)), next(iter(ys)))
                (self.blocked if kind == 'ROBOTS_DISALLOW' else self.failed)[key].add(u)

    def tier(self, url, estate):
        """A: the estate's own domain; A-shared: a group domain the estate is on (the estate to confirm); C: other."""
        h = host(url)
        if h not in self.estate_domains.get(estate, set()):
            return 'C'
        return 'A-shared' if h in self.shared else 'A'

    def _candidates(self):
        """Held public documents (PDFs and pages) whose recorded mapping names one estate and one year, and whose
        harvested text carries at least one vintage-field label (a heading year alone is a blog post, a price list or
        a greeting as often as a sheet); by (estate, year). Wine identity stays with the reader."""
        self.cands = collections.defaultdict(list)
        for sha, a in self.disc.items():
            if a.get('media') not in ('pdf', 'html') or a.get('status') != 'EXTRACTED' or not self.labels.get(sha):
                continue
            if urlparse(a.get('first_url') or '').path in ('', '/'):
                continue                                     # a site's home page is not a vintage document
            m = A.artifact_mapping(sha)
            if m['estate'] not in ('EXACT', 'DETERMINISTIC', 'CONFLICTING', 'SHARED') or not m['estates']:
                continue
            if m['vintage'] == 'EXACT':
                years = m['vintages']
            elif m['vintage'] == 'HEADING':
                vc = A.vintage_candidates().get(sha) or {}
                years = sorted(set(vc.get('heading_years') or []) | set(vc.get('title_years') or []))
            else:
                continue
            if len(years) != 1:
                continue
            y = int(years[0])
            for e in m['estates']:
                self.cands[(e, y)].append({'sha': sha, 'artifact': self.sha_art.get(sha), 'url': a.get('first_url'),
                                           'media': a['media'], 'estate_mapping': m['estate'],
                                           'wine_mapping': m['wine'], 'wines': m['wines'],
                                           'vintage_mapping': m['vintage'], 'tier': self.tier(a.get('first_url'), e),
                                           'fields': sorted(self.labels.get(sha, ()))})

    def _refused(self):
        """(estate slug, wine name, year) refused by a later correction (v6-v8): acceptances M3.5 found wrong."""
        import evidence_store as ST
        self.refused = set()
        for d in ST.iter_rows([v for v in ST.versions() if 6 <= v <= 8]):
            c = d.get('ctx') or {}
            if d.get('decision') == 'REFUSED' and c.get('target_vintage'):
                self.refused.add((c.get('estate'), c.get('target_wine'), int(c['target_vintage'])))
        slug = {r['stable_id']: r['legacy_key'] for r in L.read_table('identity/identity-map.jsonl')
                if r['namespace'] == 'estate' and r['status'] == 'ACTIVE' and r.get('stable_id')}
        self.conflicted = set()
        for w, lab in self.vintages:
            if not lab.isdigit():
                continue
            for e in self.wine_estate.get(w, ()):
                if (slug.get(e), self.names.get(w), int(lab)) in self.refused:
                    self.conflicted.add('vt:%s:%s' % (w, lab))


def linked_state(w, vt, f):
    """(status, class, artifacts) from the documents the model links to the vintage."""
    docs = [w.artifacts[a] for a in w.vdocs.get(vt, []) if a in w.artifacts]
    if not docs:
        return None
    readable = [a for a in docs if a.get('extraction_status') == 'EXTRACTED']
    ids = sorted(a['id'] for a in docs)
    if not readable:
        return 'EXTRACTION_FAILED', 'KNOWN_ARTIFACT_WITH_MISSING_FIELDS', ids
    in_corpus = [a for a in readable if a.get('sha256') in w.obs]
    if f in LABEL_FIELDS and in_corpus and len(in_corpus) == len(readable):
        if not any(f in w.labels.get(a['sha256'], ()) for a in in_corpus):
            return 'NOT_PUBLISHED', 'NO_PUBLIC_EVIDENCE', ids
    if all(a['id'] in w.legacy_read for a in readable):
        return 'UNKNOWN', 'KNOWN_ARTIFACT_READ', ids        # the fiche reader read them and took no value
    return 'UNKNOWN', 'KNOWN_ARTIFACT_WITH_MISSING_FIELDS', ids


def classify(w, e, wine, y, vt, f):
    """One missing datapoint: its status, class, priority, candidates and reason."""
    domains = sorted(w.estate_domains.get(e, ()))
    cov = sorted(w.estate_cov.get(e, ()))
    row = {'search_domains': domains, 'crawl_outcome': cov}
    if vt in w.not_produced:
        return dict(row, gap_status='NOT_PRODUCED', decision='NO_PUBLIC_EVIDENCE', priority=6, candidates=[],
                    reason='the model states the vintage was not produced', search_strategy='none (not a gap)')
    if vt in w.conflicted:
        return dict(row, gap_status='UNKNOWN', decision='CONFLICT_REQUIRES_REVIEW', priority=6, candidates=[],
                    reason='the vintage stands on acceptances a later correction refused (M3.5, M3.6B/E)',
                    search_strategy='review the vintage before any value')
    if (vt, f) in w.fillable:
        shas = w.fillable[(vt, f)]
        cs = [{'artifact': w.sha_art.get(s), 'url': (w.disc.get(s) or {}).get('first_url'),
               'tier': w.tier((w.disc.get(s) or {}).get('first_url'), e), 'claim': 'carries a %s observation of the '
               'field\'s shape; mapped exactly to this vintage' % f} for s in shas]
        tiers = {c['tier'] for c in cs}
        media = {(w.disc.get(s) or {}).get('media') for s in shas}
        prio = (1 if 'pdf' in media else 3) if 'A' in tiers else 2 if 'A-shared' in tiers else 5
        return dict(row, gap_status='NOT_EXTRACTED', decision='KNOWN_ARTIFACT_WITH_MISSING_FIELDS',
                    priority=prio, candidates=cs,
                    reason='a held document mapped exactly to the vintage carries the field',
                    search_strategy='repository: harvested observations of exactly mapped documents')
    linked = linked_state(w, vt, f)
    linked_ids = set(linked[2]) if linked else set()
    # a document the record already maps to another wine of the estate is that wine's lead, not this one's
    others = [c for c in w.cands.get((e, y), []) if c['artifact'] not in linked_ids
              and not (c['wine_mapping'] == 'EXACT' and wine not in c['wines'])]
    if others and (not linked or linked[0] in ('NOT_PUBLISHED', 'UNKNOWN')):
        conflict = [c for c in others if c['estate_mapping'] in ('CONFLICTING', 'SHARED')]
        good = [c for c in others if c not in conflict]
        cs = [{'artifact': c['artifact'], 'url': c['url'], 'tier': c['tier'],
               'claim': '%s of the estate headed %d (%s); %s; wine %s' % (
                   c['media'].upper(), y, c['vintage_mapping'], 'carries a %s label' % f if f in c['fields'] else
                   'carries %s labels, not %s' % ('/'.join(c['fields']), f) if f in LABEL_FIELDS else
                   'carries %s labels; %s not checkable' % ('/'.join(c['fields']), f), c['wine_mapping'])}
              for c in sorted(good or conflict, key=lambda c: (c['tier'], f not in c['fields'], c['url'] or ''))[:3]]
        if not good:
            return dict(row, gap_status=linked[0] if linked else 'SOURCE_MISSING', decision='CONFLICT_REQUIRES_REVIEW',
                        priority=6, candidates=cs, reason='a held document of that year names this and another estate',
                        search_strategy='repository: held crawl documents by estate and heading year')
        if f in LABEL_FIELDS and not any(f in c['fields'] for c in good):
            return dict(row, gap_status='NOT_PUBLISHED', decision='NO_PUBLIC_EVIDENCE', priority=6, candidates=cs,
                        search_strategy='repository: held crawl documents by estate and heading year',
                        reason='the held documents of that year carry other vintage fields, not this one')
        tierA = [c for c in good if c['tier'] == 'A']
        carries = [c for c in tierA if f in c['fields']]
        prio = 1 if carries else 2 if tierA or any(c['tier'] == 'A-shared' for c in good) else 5
        return dict(row, gap_status=linked[0] if linked else 'SOURCE_MISSING', decision='KNOWN_DOCUMENT_NOT_LINKED',
                    priority=prio, candidates=cs, search_strategy='repository: held crawl documents by estate and '
                    'heading year', reason='a held public document of the estate is headed with the year; not linked '
                    'to the vintage%s' % ('; it carries the field\'s label' if carries else ''))
    if linked:
        status, cls, ids = linked
        read = cls == 'KNOWN_ARTIFACT_READ'
        return dict(row, gap_status=status, decision='KNOWN_ARTIFACT_WITH_MISSING_FIELDS' if read else cls,
                    priority=6 if read or cls == 'NO_PUBLIC_EVIDENCE' else 2,
                    candidates=[{'artifact': a, 'url': None, 'tier': 'A'} for a in ids[:3]],
                    search_strategy='repository: the vintage\'s linked documents',
                    reason='the vintage\'s documents were read by the fiche reader, which took no value for the field'
                    if read else {'EXTRACTION_FAILED': 'the vintage\'s documents are held but unreadable (OCR or extraction)',
                                  'NOT_PUBLISHED': 'the vintage\'s readable documents carry no label for the field',
                                  'UNKNOWN': 'a linked document never read for values; the field is not checkable in its '
                                             'harvested text'}[status])
    if w.blocked.get((e, y)):
        return dict(row, gap_status='SOURCE_MISSING', decision='BLOCKED_PUBLIC_ROUTE', priority=6,
                    candidates=[{'artifact': None, 'url': u, 'tier': 'A', 'claim': 'first-party PDF whose address names '
                                 'the year; robots.txt disallows it'} for u in sorted(w.blocked[(e, y)])[:3]],
                    search_strategy='repository: crawl location logs', reason='the first-party route is disallowed by robots.txt')
    if w.failed.get((e, y)):
        return dict(row, gap_status='SOURCE_MISSING', decision='KNOWN_URL_NOT_ACQUIRED', priority=2,
                    candidates=[{'artifact': None, 'url': u, 'tier': 'A', 'claim': 'first-party PDF whose address names '
                                 'the year; the fetch failed'} for u in sorted(w.failed[(e, y)])[:3]],
                    search_strategy='repository: crawl location logs', reason='a first-party URL of that year failed to fetch')
    if not domains:
        return dict(row, gap_status='SOURCE_MISSING', decision='NO_PUBLIC_EVIDENCE', priority=6, candidates=[],
                    search_strategy='none: no first-party domain is known', reason='no first-party domain is known for the estate')
    if cov and set(cov) <= {'REACHED'}:
        return dict(row, gap_status='NOT_FOUND', decision='NO_PUBLIC_EVIDENCE', priority=6, candidates=[],
                    search_strategy='repository: the crawl of the estate\'s reached site',
                    reason='the estate\'s first-party site was crawled; it holds no document of that year')
    if 'BLOCKED_BY_POLICY' in cov:
        return dict(row, gap_status='UNKNOWN', decision='BLOCKED_PUBLIC_ROUTE', priority=6, candidates=[],
                    search_strategy='none: the site refuses crawling', reason='the first-party site was not crawled (policy)')
    return dict(row, gap_status='UNKNOWN', decision='KNOWN_FIRST_PARTY_DOMAIN_NOT_SEARCHED', priority=2, candidates=[],
                search_strategy='proposed: a crawl of the domain', reason='the first-party domain was not fully reached '
                '(%s)' % ', '.join(cov or ['no crawl record']))


def build():
    w = World()
    rows = []
    for wine, lab in w.vintages:
        if not lab.isdigit():
            continue
        y, vt = int(lab), 'vt:%s:%s' % (wine, lab)
        estates = sorted(w.wine_estate.get(wine, ())) or [None]
        e = estates[0]
        for f in FIELDS:
            if f in w.values.get(vt, {}):
                continue
            c = classify(w, e, wine, y, vt, f)
            best = c['candidates'][0] if c['candidates'] else {}
            rows.append({'record': 'gap', 'sweep_id': sid(wine, lab, f), 'estate_id': e, 'estate': w.names.get(e),
                         'wine_id': wine, 'wine': w.names.get(wine), 'vintage': y, 'field': f,
                         'existing_provenance': sorted(set(w.values.get(vt, {}).values())) or ['NONE'],
                         'known_artifacts': sorted(w.vdocs.get(vt, []))[:5], 'gap_status': c['gap_status'],
                         'search_domains': c['search_domains'], 'crawl_outcome': c['crawl_outcome'],
                         'search_strategy': c['search_strategy'], 'candidate_url': best.get('url'),
                         'candidate_source_tier': best.get('tier'), 'candidate_artifact': best.get('artifact'),
                         'candidate_claim': best.get('claim'),
                         'candidates': c['candidates'] if c['priority'] <= 5 else c['candidates'][:1], 'reader_status': 'NOT_RUN',
                         'review_status': 'NOT_REVIEWED', 'decision': c['decision'], 'priority': c['priority'],
                         'reason': c['reason']})
    # missing vintages: a held public document of one estate states one year no wine of that estate holds
    held = {(wn, int(lab)) for wn, lab in w.vintages if lab.isdigit()}
    for (e, y), cs in sorted(w.cands.items()):
        if not FIRST_YEAR <= y <= LAST_YEAR or any((wn, y) in held for wn in w.estate_wines.get(e, ())):
            continue
        cs = sorted(cs, key=lambda c: (c['tier'], c['url'] or ''))
        # P2 only on the estate's own domain with the document's wine one of the estate's: otherwise an unlisted
        # cuvée's or another estate's sheet could pass for a missing grand-vin vintage
        tierA = [c for c in cs if c['tier'] == 'A' and c['estate_mapping'] in ('EXACT', 'DETERMINISTIC')
                 and c['wine_mapping'] == 'EXACT' and set(c['wines']) <= w.estate_wines.get(e, set())]
        best = (tierA or cs)[0]
        rows.append({'record': 'missing_vintage', 'sweep_id': sid(e, y, VINTAGE_FIELD), 'estate_id': e,
                     'estate': w.names.get(e), 'wine_id': None, 'wine': None, 'vintage': y, 'field': VINTAGE_FIELD,
                     'existing_provenance': ['NONE'], 'known_artifacts': [], 'gap_status': 'SOURCE_MISSING',
                     'search_domains': sorted(w.estate_domains.get(e, ())), 'crawl_outcome': sorted(w.estate_cov.get(e, ())),
                     'search_strategy': 'repository: held crawl documents by estate and heading year',
                     'candidate_url': best['url'], 'candidate_source_tier': best['tier'], 'candidate_artifact': best['artifact'],
                     'candidate_claim': '%s of the estate headed %d (%s); wine %s %s' % (
                         best['media'].upper(), y, best['vintage_mapping'], best['wine_mapping'], best['wines']),
                     'candidates': [{'artifact': c['artifact'], 'url': c['url'], 'tier': c['tier']} for c in cs[:5]],
                     'reader_status': 'NOT_RUN', 'review_status': 'NOT_REVIEWED',
                     'decision': 'CONFLICT_REQUIRES_REVIEW' if not tierA and any(
                         c['estate_mapping'] in ('CONFLICTING', 'SHARED') for c in cs) else 'KNOWN_DOCUMENT_NOT_LINKED',
                     'priority': 2 if tierA else 5,
                     'reason': 'existence lead only: the wine is the reader\'s to establish, and a vintage is created only '
                               'through V1 on an accepted decision'})
    rows.sort(key=lambda r: (r['record'], r['estate_id'] or '', r['wine_id'] or '', r['vintage'], r['field']))
    return w, rows


def body(rows):
    return ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                   for r in rows).encode('utf-8')


# ---------------------------------------------------------------- the report

def table(out, head, rows):
    out.append('| ' + ' | '.join(head) + ' |')
    out.append('|' + '|'.join('---:' if h.startswith(('n', 'N')) or h in ('gaps', 'P1', 'P2', 'P3', 'P5', 'P6', 'vintages')
                              else '---' for h in head) + '|')
    for r in rows:
        out.append('| ' + ' | '.join(str(x).replace('|', '/') for x in r) + ' |')
    out.append('')


def report(w, rows):
    gaps = [r for r in rows if r['record'] == 'gap']
    mv = [r for r in rows if r['record'] == 'missing_vintage']
    C = collections.Counter
    out = []
    a = out.append
    a('# Phase M3.12 — Bordeaux-wide public missing-data sweep\n')
    a('Generated by `python tools/m312-public-gap-sweep.py` (`data/audit/public-gap-sweep.jsonl`); never edited by hand. '
      '**An audit:** nothing in the model, the evidence store, the discovery store, the source profiles or the app '
      'changed. Every candidate is a lead (`review_status` NOT_REVIEWED, `reader_status` NOT_RUN): discovery, not '
      'review, acceptance or application.\n')
    a('## 1. Scope and method\n')
    a('- **Surface:** %d vintages of %d wines (every vintage the model holds) × the %d fields the value runner applies '
      '(%s) = %d datapoints; %d hold a canonical value, **%d are missing**.' % (
          len(w.vintages), len({v[0] for v in w.vintages}), len(FIELDS), ', '.join(FIELDS), len(w.vintages) * len(FIELDS),
          len(w.vintages) * len(FIELDS) - len(gaps), len(gaps)))
    a('- **Missing vintages:** only where a held public document of one estate is headed with one year none of the '
      'estate\'s wines holds (%d leads). An absent year alone is never one.' % len(mv))
    a('- **Public web:** the discovery crawl of 2026-10-25 (robots respected; %d documents held from the estates\' own '
      'sites), the M3.3-M3.11 audits and the model\'s documents and evidence. Nothing was fetched: a new crawl writes '
      '`data/discovery`, which the model is built from, so it is its own phase (§8).' % len(w.disc))
    a('- **Tiers:** A, the estate\'s own domain (or its M3.7-confirmed estate-controlled one); A-shared, a group domain '
      'serving several estates (first-party for the group; which estate a document is stays to confirm - the M3.5 '
      'Bernaleau lesson), never P1; B, none (the rules admit no external source for these fields); C, any other host.')
    a('- **A candidate document** must be held, extracted, not a site\'s home page, mapped by the crawl\'s record to one '
      'estate and one year, and carry at least one vintage-field label in its harvested text. Spot-checked: a '
      'Dubourdieu group-site sheet mapped to Doisy-Daëne was Château Haura\'s, and Lamont group sheets offered as '
      'Château d\'Argan vintages were other wines - why A-shared leads stay below P1 and missing-vintage leads need '
      'the document\'s wine.\n')
    a('## 2. Baseline: the missing datapoints\n')
    a('**%d missing datapoints**, by missingness status:\n' % len(gaps))
    table(out, ['status', 'N'], sorted(C(r['gap_status'] for r in gaps).items(), key=lambda kv: -kv[1]))
    a('By field:\n')
    table(out, ['field', 'N'], sorted(C(r['field'] for r in gaps).items()))
    a('By vintage (decade):\n')
    table(out, ['decade', 'N'], sorted(C('%ds' % (r['vintage'] // 10 * 10) for r in gaps).items()))
    a('The 20 estates with most missing datapoints:\n')
    by_e = C((r['estate'] or r['estate_id'] or '—') for r in gaps)
    table(out, ['estate', 'N'], by_e.most_common(20))
    a('The 20 wines with most missing datapoints:\n')
    table(out, ['wine', 'N'], C('%s (%s)' % (r['wine'], r['wine_id']) for r in gaps).most_common(20))
    a('## 3. Discovery result per datapoint\n')
    table(out, ['class', 'N', 'P1', 'P2', 'P3', 'P5', 'P6'], [
        (k, n) + tuple(sum(1 for r in gaps if r['decision'] == k and r['priority'] == p) for p in (1, 2, 3, 5, 6))
        for k, n in sorted(C(r['decision'] for r in gaps).items(), key=lambda kv: -kv[1])])
    a('Priority: %s.\n' % '; '.join('P%d %s' % kv for kv in PRIORITY.items()))
    a('## 4. Measures\n')
    cand = [r for r in gaps if r['candidate_artifact'] and r['priority'] <= 5]
    p1 = [r for r in gaps if r['priority'] == 1]
    p1_wine = [r for r in p1 if 'wine EXACT' in (r['candidate_claim'] or '') or r['gap_status'] == 'NOT_EXTRACTED']
    res = [r for r in gaps if r['priority'] <= 5]
    res_a = [r for r in gaps if r['priority'] <= 3]
    lines = [
        ('Initial missing datapoints', len(gaps)),
        ('Public evidence candidates found (actionable datapoints with a held candidate document)', len(cand)),
        ('First-party candidates (tier A, the estate\'s own domain)', sum(1 for r in cand if r['candidate_source_tier'] == 'A')),
        ('First-party candidates on a shared group domain (tier A-shared, estate to confirm)',
         sum(1 for r in cand if r['candidate_source_tier'] == 'A-shared')),
        ('Authoritative external candidates (tier B)', 0),
        ('Third-party discovery leads (tier C)', sum(1 for r in cand if r['candidate_source_tier'] == 'C')),
        ('Known documents newly linkable (datapoints)', sum(1 for r in gaps if r['decision'] == 'KNOWN_DOCUMENT_NOT_LINKED')),
        ('Known documents newly linkable (distinct documents)', len({c['artifact'] or c['url'] for r in gaps
                                                                     if r['decision'] == 'KNOWN_DOCUMENT_NOT_LINKED'
                                                                     for c in r['candidates']})),
        ('Existing artifacts with recoverable missing fields (datapoints NOT_EXTRACTED)',
         sum(1 for r in gaps if r['gap_status'] == 'NOT_EXTRACTED')),
        ('Linked documents never read for values (datapoints, P2)',
         sum(1 for r in gaps if r['decision'] == 'KNOWN_ARTIFACT_WITH_MISSING_FIELDS' and r['priority'] == 2)),
        ('Linked legacy fiches already read, field not taken (datapoints, P6)',
         sum(1 for r in gaps if r['decision'] == 'KNOWN_ARTIFACT_WITH_MISSING_FIELDS' and r['priority'] == 6)),
        ('Potential missing vintages with existence evidence (leads)', len(mv)),
        ('... of them on a first-party domain', sum(1 for r in mv if r['priority'] == 2)),
        ('No public evidence (incl. NOT_PRODUCED)', sum(1 for r in gaps if r['decision'] == 'NO_PUBLIC_EVIDENCE')),
        ('Blocked routes', sum(1 for r in gaps if r['decision'] == 'BLOCKED_PUBLIC_ROUTE')),
        ('First-party domains not (fully) searched (datapoints)',
         sum(1 for r in gaps if r['decision'] == 'KNOWN_FIRST_PARTY_DOMAIN_NOT_SEARCHED')),
        ('Known URLs not acquired (datapoints)', sum(1 for r in gaps if r['decision'] == 'KNOWN_URL_NOT_ACQUIRED')),
        ('Conflicts requiring review (datapoints)', sum(1 for r in gaps if r['decision'] == 'CONFLICT_REQUIRES_REVIEW')),
        ('Reader failures (reader not run in this phase)', 0),
        ('**Potentially resolvable gaps (P1-P5)**', len(res)),
        ('**Resolvable first-party gaps (P1-P3)**', len(res_a)),
        ('... of which P1 (a known first-party document carries the field)', len(p1)),
        ('... ... with the document\'s wine already established (the rest: the reader decides which wine)', len(p1_wine)),
    ]
    table(out, ['measure', 'N'], lines)
    a('**Expected reduction, not applied.** At most %d of the %d missing datapoints (%.1f%%) have a first-party route '
      'the repository already holds or knows; P1 alone, %d (%.1f%%), is the realistic first batch. Each still goes through '
      'review, the unchanged reader, acceptance and M3.11; the reader has refused a large share of earlier leads '
      '(Trotte Vieille, d\'Issan, La Lagune\'s template), so these are upper bounds.\n' % (
          len(res_a), len(gaps), 100.0 * len(res_a) / max(len(gaps), 1), sum(1 for r in gaps if r['priority'] == 1),
          100.0 * sum(1 for r in gaps if r['priority'] == 1) / max(len(gaps), 1)))
    a('## 5. Source and domain coverage\n')
    cov = C()
    for r in gaps:
        cov[(r['crawl_outcome'][0] if len(r['crawl_outcome']) == 1 else '+'.join(r['crawl_outcome']) or 'NO_CRAWL_RECORD')] += 1
    table(out, ['crawl outcome for the estate', 'gaps'], sorted(cov.items(), key=lambda kv: -kv[1]))
    dom = collections.defaultdict(C)
    for r in gaps:
        for d in r['search_domains'][:1] or ['(none)']:
            dom[d][r['priority']] += 1
    top = sorted(dom.items(), key=lambda kv: -(kv[1][1] + kv[1][2] + kv[1][3]))[:25]
    a('The 25 first-party domains with most first-party-resolvable datapoints:\n')
    table(out, ['domain', 'P1', 'P2', 'P3', 'P5', 'P6'], [(d, c[1], c[2], c[3], c[5], c[6]) for d, c in top])
    a('## 6. Recurring document patterns\n')
    pat = collections.defaultdict(set)
    for r in gaps:
        if r['decision'] in ('KNOWN_DOCUMENT_NOT_LINKED', 'KNOWN_ARTIFACT_WITH_MISSING_FIELDS'):
            for c in r['candidates']:
                if c.get('url'):
                    pat[template(c['url'])].add(r['estate_id'])
    shared = sorted(((t, len(es)) for t, es in pat.items()), key=lambda kv: (-kv[1], kv[0]))
    a('Candidate URLs reduced to their route shape (host left out; years `{YYYY}`, other digit runs `{N}`, the file '
      'to its extension); %d shapes, %d shared by more than one estate. A persistent source-profile change is proposed '
      'only where a shape recurs (§8).\n' % (len(shared), sum(1 for _, n in shared if n > 1)))
    table(out, ['route shape', 'estates'], shared[:20])
    a('## 7. Ready for the next review / acquisition phase\n')
    ready = collections.defaultdict(list)
    for r in gaps:
        if r['priority'] == 1 and r['candidate_artifact']:
            ready[(r['estate'], r['wine'], r['vintage'], r['candidate_artifact'])].append(r['field'])
    a('%d (wine, vintage, document) packets at P1, %d datapoints. The first 40:\n' % (
        len(ready), sum(len(v) for v in ready.values())))
    table(out, ['estate', 'wine', 'vintage', 'document', 'fields'],
          [(k[0], k[1], k[2], k[3], ', '.join(sorted(v))) for k, v in sorted(ready.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]), kv[0][2]))[:40]])
    a('Missing-vintage leads on a first-party domain (existence only, the reader to judge):\n')
    table(out, ['estate', 'year', 'document'], [(r['estate'], r['vintage'], r['candidate_url'])
                                               for r in mv if r['priority'] == 2][:40])
    a('## 8. Where public evidence appears unavailable, and proposals\n')
    a('- **NO_PUBLIC_EVIDENCE** (%d): the estate\'s reached site holds no document of the year, the held documents do '
      'not state the field, no first-party domain is known, or the vintage was not produced.' %
      sum(1 for r in gaps if r['decision'] == 'NO_PUBLIC_EVIDENCE'))
    a('- **BLOCKED_PUBLIC_ROUTE** (%d): robots.txt disallows the route, or the site refuses crawling; respected.' %
      sum(1 for r in gaps if r['decision'] == 'BLOCKED_PUBLIC_ROUTE'))
    a('- **Proposal A, a targeted crawl** of the %d first-party domains not fully reached (UNREACHABLE, PARTIAL, no crawl '
      'record) with the existing crawler, in its own phase: it writes `data/discovery`. %d datapoints wait on it.' % (
          len({d for r in gaps if r['decision'] == 'KNOWN_FIRST_PARTY_DOMAIN_NOT_SEARCHED' for d in r['search_domains']}),
          sum(1 for r in gaps if r['decision'] == 'KNOWN_FIRST_PARTY_DOMAIN_NOT_SEARCHED')))
    a('- **Proposal B, a retry** of the %d first-party PDF URLs whose fetch failed, by the same crawler.' % len(
        {u for us in w.failed.values() for u in us}))
    a('- **Proposal C, field readers** for months, oak and pick: the held text is checked for alc, blend, ph and yld '
      'labels only (`data_gap_analysis.LABEL_FIELD`), so %d datapoints on held documents stay UNKNOWN. Extending the '
      'harvest labels is a reader-side change and its own phase.' % sum(
          1 for r in gaps if r['gap_status'] == 'UNKNOWN' and r['decision'] == 'KNOWN_ARTIFACT_WITH_MISSING_FIELDS'))
    a('- **Proposal D, the OCR backlog** (EXTRACTION_FAILED, %d datapoints).\n' % sum(
        1 for r in gaps if r['gap_status'] == 'EXTRACTION_FAILED'))
    return ('\n'.join(out) + '\n').encode('utf-8')


def main():
    w, rows = build()
    b, doc = body(rows), report(w, rows)
    if '--check' in sys.argv:
        bad = [p[len(L.ROOT):] for p, x in ((OUT, b), (DOC, doc)) if not os.path.exists(p) or open(p, 'rb').read() != x]
        print('M3.12 outputs ' + ('are current' if not bad else 'differ: %s' % bad))
        sys.exit(1 if bad else 0)
    open(OUT, 'wb').write(b)
    open(DOC, 'wb').write(doc)
    print('%s written (%d rows); %s written' % (OUT[len(L.ROOT):], len(rows), DOC[len(L.ROOT):]))


if __name__ == '__main__':
    main()
