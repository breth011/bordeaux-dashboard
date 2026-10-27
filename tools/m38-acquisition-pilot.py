"""M3.8: the confirmed-source acquisition pilot's audit - what each fetched URL turned out to be.

    python tools/m38-acquisition-pilot.py           write data/audit/m3.8-acquisition-pilot.jsonl and
                                                    docs/PHASE-M3.8-ACQUISITION-PILOT.md
    python tools/m38-acquisition-pilot.py --check   recompute both and compare, byte for byte

Reads what tools/m38-acquire.py fetched (sources/acquisition/m3.8/, outside Git) and the repository; writes
nothing else. Acquisition is not attribution: no model, evidence, provenance, gap-register or app change.

DOCUMENT IDENTITY comes from the document's own text, never from its URL, filename, folder or the page that
linked it, and never from a publication date:

    estate     the text names the estate (ESTATE_TEXT, on the folded text)
    wine       the document's title (tools/m35_rubric.title, the reader's T1 rule) is the name of a wine the
               model lists for that estate - never the estate's name standing alone in the body
    vintage    the title's year, or a "millésime / vintage YYYY" statement (m35_rubric.VINTAGE_HEAD)
    other      a title naming anything else (another estate, an unlisted cuvée) is recorded as
               other_identity, not attributed

THE CLASSIFICATION, first match:

    robots refused the URL, or M3.3's recorded block stands      BLOCKED_BY_ROBOTS
    HTTP 404 / 410                                                NOT_FOUND
    any other failure (HTTP error, too large, network)            FETCH_FAILED
    already held, or the bytes equal an artifact already held     DUPLICATE_ARTIFACT
    an artifact already held has the same document name and
    other bytes                                                   REVISION_OF_EXISTING_ARTIFACT
    estate, wine and vintage all explicit                         EXACT_ESTATE_WINE_VINTAGE
    estate and vintage explicit                                   ESTATE_VINTAGE_ONLY
    no vintage stated anywhere in the text                        NON_VINTAGE_DOCUMENT
    otherwise (no text without OCR, no estate named, ...)         ESTATE_DOCUMENT_IDENTITY_UNCLEAR

A revision keeps its identity fields: both editions stay visible, neither overwrites the other.
"""
import collections
import importlib.util
import json
import os
import posixpath
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import discover_extract as X  # noqa: E402
import migration_lib as L  # noqa: E402
import m35_rubric as RB  # noqa: E402

_a = importlib.util.spec_from_file_location('m38a', L.ROOT + 'tools/m38-acquire.py')
A = importlib.util.module_from_spec(_a)
_a.loader.exec_module(A)

OUT = L.ROOT + 'data/audit/m3.8-acquisition-pilot.jsonl'
DOC = L.ROOT + 'docs/PHASE-M3.8-ACQUISITION-PILOT.md'
ACQ = A.ACQ
CLASSES = ('EXACT_ESTATE_WINE_VINTAGE', 'ESTATE_VINTAGE_ONLY', 'ESTATE_DOCUMENT_IDENTITY_UNCLEAR',
           'NON_VINTAGE_DOCUMENT', 'DUPLICATE_ARTIFACT', 'REVISION_OF_EXISTING_ARTIFACT', 'BLOCKED_BY_ROBOTS',
           'FETCH_FAILED', 'NOT_FOUND')
# the estate named in the document's own words; a web address (durfort-vivens.com) is not a naming
ESTATE_TEXT = {'es_00293': r'\bla mondotte\b', 'es_00263': r'\bdurfort[- ]vivens\b(?!\.(?:com|fr))',
               'es_00283': r"\bd['’ ]?issan\b", 'es_00253': r'\bmyrat\b', 'es_00277': r'\bhaut[- ]bages[- ]liberal\b'}
ESTATE_RAW = {'es_00293': '拉梦多'}                     # names in scripts that folding drops (zh)
VINTAGE_FOLDED = (RB.VINTAGE_HEAD, re.compile(r'\b((?:19|20)\d\d)\s+(?:vintage|millesime)\b'),
                  re.compile(r'\bjahrgang\s+((?:19|20)\d\d)\b'))
VINTAGE_RAW = (re.compile(r'年份\s*((?:19|20)\d\d)'),)
GENRES = (('certificate', r'\bcertificate?\b|\battestation\b'),
          ('analysis', r'bulletin d.analyse|rapport d.analyse|analysis report|certificat de purete|analyse'),
          ('ingredients list', r'ingredient'), ('flowchart', r'flowchart|flow chart|logigramme'),
          ('food pairing guide', r'recipe|recette|accords mets'),
          ('commercial argument', r'argumentation|argumentaire'),
          ('product code sheet', r'\bgencod|\bcode ean\b|\bean 13\b'))
NON_VINTAGE_GENRES = ('certificate', 'ingredients list', 'flowchart')
WINE_LIKE = re.compile(r"^(?:chateau|clos|domaine|cuvee|la|le|les|l)\s+\S+(?:\s+\S+){0,5}$")   # a name, not a sentence


class Stop(Exception):
    pass


def text_of(sha):
    p = ACQ + 'extracted/%s.json' % sha
    if not sha or not os.path.exists(p):
        return None, None
    x = json.load(open(p, encoding='utf-8'))
    if x.get('media') == 'pdf':
        t = '\n'.join(x.get('pages') or [])
        return (t if t.strip() and x.get('ocr') != 'NEEDED_NO_ENGINE' else None), x
    t = '\n'.join([x.get('title') or ''] + [b.get('text') or '' for b in x.get('blocks') or []])
    return (t if t.strip() else None), x


def docname(u):
    return posixpath.basename(urllib.parse.unquote(urllib.parse.urlsplit(u).path)).lower()


class Held:
    """What the repository held before M3.8: by sha256, by (sha1, bytes), and by document name."""

    def __init__(self):
        self.sha, self.name = {}, collections.defaultdict(set)
        for l in open(L.ROOT + 'data/discovery/artifacts.jsonl', encoding='utf-8'):
            a = json.loads(l)
            self.sha.setdefault(a['sha256'], 'discovery:%s' % a['sha256'][:12])
            self.name[docname(a['first_url'])].add((a['sha256'], 'discovery:%s' % a['sha256'][:12]))
        self.sha1 = {}
        arts = L.read_table('identity/artifacts.jsonl')
        for a in arts:
            if a.get('sha256'):
                self.sha.setdefault(a['sha256'], a['id'])
            if a.get('sha1'):
                self.sha1[(a['sha1'], a.get('bytes'))] = a['id']
        by_id = {a['id']: a for a in arts}
        for p in L.read_table('document/placements.jsonl'):
            if not p.get('artifact'):          # a legacy placement whose file is missing: no bytes to compare
                continue
            loc = p.get('locator') or {}
            v = loc.get('value') or ''
            n = docname(v) if loc.get('kind') == 'URL' else posixpath.basename(v).lower()
            a = by_id.get(p['artifact']) or {}
            self.name[n].add((a.get('sha256') or a.get('sha1'), p['artifact']))

    def duplicate(self, sha, sha1, size):
        return self.sha.get(sha) or self.sha1.get((sha1, size))

    def earlier(self, url, sha, sha1):
        """Held artifacts with this document file's name and other bytes (a page's name is not a file's)."""
        n = docname(url)
        if not re.search(r'\.(?:pdf|docx?|xlsx?)$', n):
            return []
        return sorted({ident for s, ident in self.name.get(n, set()) if s not in (sha, sha1)})

    def renderings(self, url, sha):
        """Held pages of the same name (a print view of a page the crawl held): related, not revisions."""
        n = docname(url)
        if re.search(r'\.(?:pdf|docx?|xlsx?|png|jpe?g)$', n):
            return []
        return sorted({ident for s, ident in self.name.get(n, set()) if s != sha})


def wines_of(estates):
    names = collections.defaultdict(list)
    for n in L.read_table('identity/names.jsonl'):
        names[n['subject']].append(n['name'])
    out = collections.defaultdict(dict)
    for r in L.read_table('state/estate-wine.jsonl'):
        if r['estate'] in estates:
            for nm in names.get(r['wine'], []):
                out[r['estate']][RB.norm_name(nm)] = r['wine']
    return out


def heading(text):
    """The document's heading: its first lines, a line or two joined ("CHÂTEAU" / "DURFORT-VIVENS"), with a
    trailing year or 'vintage' word set aside. Returns the candidate names, in reading order."""
    lines = [l.strip() for l in text.split('\n') if l.strip()][:3]
    cands = []
    for i in range(len(lines)):
        cands.append(lines[i])
        if i + 1 < len(lines):
            cands.append(lines[i] + ' ' + lines[i + 1])
    out = []
    for c in cands:
        n = RB.norm_name(c)
        n = re.sub(r'(?:\s+(?:19|20)\d\d)?(?:\s+(?:vintage|millesime))?$', '', n).strip()
        if n and n not in out:
            out.append(n)
    return out


def identify(text, eligible, wines):
    """Estate, wine and vintage, each only as the document's own text states it (see the docstring)."""
    f = RB.fold(text)
    named = sorted({e for e, rx in ESTATE_TEXT.items() if re.search(rx, f)} |
                   {e for e, w in ESTATE_RAW.items() if w in text})
    mine = [e for e in named if e in eligible]
    estate = mine[0] if len(mine) == 1 else None
    head = heading(text)
    wine, other = None, None
    if estate:
        wine = next((wines[estate][h] for h in head if h in wines.get(estate, {})), None)
    if not wine:
        # a heading that reads as a wine's name (Château ..., La ..., Le ...) and is none the estate lists
        named_like = [h for h in head if WINE_LIKE.match(h) and not re.search(r' (?:com|fr)$|\d', h)]
        # "LE HAUT-MÉDOC" / "DE HAUT-BAGES LIBÉRAL" is one name: the joined line wins over its first half
        joined = [h for h in named_like if re.search(r' (?:de|du|des|par) ', h)]
        first = (joined or named_like or [None])[0]
        if first and not any(first in w for e in mine for w in wines.get(e, {})):
            other = 'heading "%s"' % first
    if len(mine) > 1:
        other = (other + '; ' if other else '') + 'names several gated estates: %s' % ', '.join(mine)
    years = {}
    for rx in VINTAGE_FOLDED:
        for m in rx.finditer(f):
            years.setdefault(int(m.group(1)), 'statement "%s"' % m.group(0))
    for rx in VINTAGE_RAW:
        for m in rx.finditer(text):
            years.setdefault(int(m.group(1)), 'statement "%s"' % m.group(0))
    if wine:
        wn = [k for k, v in wines[estate].items() if v == wine]
        for m in re.finditer(r'\b(%s) ((?:19|20)\d\d)\b' % '|'.join(re.escape(x) for x in wn), RB.norm_name(text)):
            years.setdefault(int(m.group(2)), 'wine and year "%s"' % m.group(0))
    vint = basis = None
    if len(years) == 1:
        vint, basis = next(iter(years.items()))
    elif len(years) > 1:
        basis = 'conflicting statements: %s' % ', '.join(str(y) for y in sorted(years))
    genre = next((g for g, rx in GENRES if re.search(rx, f[:1500])), 'technical sheet' if (wine or vint) else 'document')
    # a year standing alone on a line is layout, not a statement: kept for the later review, never used here
    bare = sorted({int(l.strip()) for l in text.split('\n') if re.fullmatch(r'\s*(?:19|20)\d\d\s*', l)})
    return {'estates_named': named, 'estate': estate, 'wine': wine, 'vintage': vint, 'vintage_basis': basis,
            'heading': head[:2], 'other_identity': other, 'genre': genre, 'language': X.detect_lang(text),
            'bare_year_lines': bare}


def classify(item, ident, dup, earlier):
    r = item['retrieval']
    if r in ('ROBOTS_DISALLOW', 'NOT_REQUESTED_RECORDED_BLOCK'):
        return 'BLOCKED_BY_ROBOTS'
    if r != 'OK' and r != 'NOT_REQUESTED_ALREADY_HELD':
        return 'NOT_FOUND' if item.get('status') in (404, 410) else 'FETCH_FAILED'
    if r == 'NOT_REQUESTED_ALREADY_HELD' or dup:
        return 'DUPLICATE_ARTIFACT'
    if earlier:
        return 'REVISION_OF_EXISTING_ARTIFACT'
    if ident is None:
        return 'ESTATE_DOCUMENT_IDENTITY_UNCLEAR'
    if ident['estate'] and ident['wine'] and ident['vintage']:
        return 'EXACT_ESTATE_WINE_VINTAGE'
    if ident['estate'] and ident['vintage']:
        return 'ESTATE_VINTAGE_ONLY'
    if not ident['vintage'] and not ident['vintage_basis'] and ident['genre'] in NON_VINTAGE_GENRES:
        return 'NON_VINTAGE_DOCUMENT'
    return 'ESTATE_DOCUMENT_IDENTITY_UNCLEAR'


def build():
    inv = json.load(open(ACQ + 'inventory.json', encoding='utf-8'))
    targets = A.targets()
    if [i['url'] for i in inv['items']] != [u for u, _, _ in targets]:
        raise Stop('the inventory is not exactly the gated targets, in order (run m38-acquire.py --fetch)')
    m37 = {r['id']: r for r in L.jsonl_lines(A.M37) if r['record'] == 'relationship'}
    est_of = {rid: m37[rid]['estate'] for _, rids, _ in targets for rid in rids}
    # an item may be any gated estate's whose confirmed host served it; M3.3's lists are kept as listed_for
    on_host = collections.defaultdict(set)
    for u, rids, _ in targets:
        on_host[A.host(u)] |= set(rids)
    wines = wines_of(set(est_of.values()))
    H = Held()
    rows, first_seen = [], {}
    for n, item in enumerate(inv['items'], 1):
        eligible = sorted(on_host[A.host(item['url'])])
        text, x = text_of(item.get('sha256'))
        ident = identify(text, [est_of[r] for r in eligible], wines) if text else None
        dup = H.duplicate(item.get('sha256'), item.get('sha1'), item.get('bytes')) if item.get('sha256') else \
            (item.get('held') or [None, None])[1]
        if item.get('sha256') and not dup and item['sha256'] in first_seen:
            dup = 'm3.8 item #%d' % first_seen[item['sha256']]      # the same bytes under another known URL
        if item.get('sha256'):
            first_seen.setdefault(item['sha256'], n)
        earlier = H.earlier(item['url'], item.get('sha256'), item.get('sha1')) if item.get('sha256') and not dup else []
        cls = classify(item, ident, dup, earlier)
        attributed = next((r for r in eligible if ident and est_of[r] == ident['estate']), None)
        row = {'record': 'item', 'n': n, 'url': item['url'], 'final_url': item.get('final'),
               'listed_for': item['relationships'], 'eligible_relationships': eligible, 'attributed_to': attributed,
               'target': item['target'], 'retrieval': item['retrieval'], 'status': item.get('status'),
               'error': item.get('error'), 'at': item['at'], 'content_type': item.get('ctype'),
               'sha256': item.get('sha256'), 'bytes': item.get('bytes'), 'classification': cls,
               'duplicate_of': dup or None, 'revision_of': earlier or None,
               'renders_held_page': (H.renderings(item['url'], item.get('sha256')) or None) if item.get('sha256') else None,
               'text': ('NONE' if not item.get('sha256') else 'EXTRACTED' if text else
                        'NEEDS_OCR' if (x or {}).get('ocr') == 'NEEDED_NO_ENGINE' else 'NOT_EXTRACTABLE'),
               'pages': (x or {}).get('page_count'), 'identity': ident,
               'identity_basis': "the document's own text" if ident else None}
        if item['retrieval'] == 'NOT_REQUESTED_RECORDED_BLOCK':
            row['robots_allows_now'] = item['robots_allows_now']
            row['reason'] = 'M3.3 found it blocked by policy; respected, not requested'
        if cls in ('BLOCKED_BY_ROBOTS', 'FETCH_FAILED', 'NOT_FOUND'):
            row['retry'] = {'BLOCKED_BY_ROBOTS': "no: only if the site's policy changes",
                            'NOT_FOUND': 'no: the document is not at this URL',
                            'FETCH_FAILED': 'later, as a decision: %s' % (item.get('retrieval'))}[cls]
            stem = re.sub(r'^.*/docs/[a-z]{2}/', '', urllib.parse.unquote(item['url']))
            alt = [i['url'] for i in inv['items'] if i is not item and i.get('sha256') and
                   urllib.parse.unquote(i['url']).endswith('/' + stem)]
            row['alternative_known_url'] = alt or None
        row['later_review'] = cls in ('EXACT_ESTATE_WINE_VINTAGE', 'ESTATE_VINTAGE_ONLY', 'REVISION_OF_EXISTING_ARTIFACT')
        rows.append(row)
    req = [dict({'record': 'request', 'n': i}, **q) for i, q in enumerate(inv['requests'], 1)]
    c = collections.Counter(r['classification'] for r in rows)
    per = collections.defaultdict(collections.Counter)
    for r in rows:
        for rid in r['listed_for']:
            per[rid]['listed'] += 1
        if r['attributed_to']:
            per[r['attributed_to']][r['classification']] += 1
    rels = [{'record': 'relationship', 'relationship': rid, 'source_name': m37[rid]['source_name'],
             'estate': m37[rid]['estate'], 'estate_name': m37[rid]['estate_name'], 'm37_status': m37[rid]['status'],
             'listed': per[rid]['listed'], 'attributed': sum(per[rid].get(k, 0) for k in CLASSES),
             'by_classification': {k: per[rid].get(k, 0) for k in CLASSES},
             'vintages_identified': sorted({r['identity']['vintage'] for r in rows if r['attributed_to'] == rid
                                            and r['identity']['vintage']})}
            for rid in sorted(per, key=lambda x: [t[1] for t in targets].index(next(t[1] for t in targets if x in t[1])))]
    summary = {'record': 'summary', 'items': len(rows), 'requests': len(req),
               'requested': sum(1 for r in rows if r['retrieval'] not in ('NOT_REQUESTED_ALREADY_HELD',
                                                                            'NOT_REQUESTED_RECORDED_BLOCK')),
               'acquired': sum(1 for r in rows if r['sha256'] and r['retrieval'] == 'OK'),
               'by_classification': {k: c.get(k, 0) for k in CLASSES},
               'later_review': sum(1 for r in rows if r['later_review']), 'model_changes': 0}
    return [{'record': 'scope', 'phase': 'M3.8', 'gate': [list(g) for g in A.GATE], 'excluded_sources': list(A.PROBABLE),
             'classes': list(CLASSES)}] + req + rows + rels + [summary]


def body(rows):
    return ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                   for r in rows).encode('utf-8')


def cell(s, n=None):
    s = str(s if s is not None else '—').replace('|', '\\|').replace('\n', ' ')
    return s if not n or len(s) <= n else s[:n - 1] + '…'


def report(rows):
    """docs/PHASE-M3.8-ACQUISITION-PILOT.md, from the audit's records alone."""
    by = collections.defaultdict(list)
    for r in rows:
        by[r['record']].append(r)
    [scope], [sm] = by['scope'], by['summary']
    items = by['item']
    rel_name = {r['relationship']: r['estate_name'] for r in by['relationship']}
    out = []
    w = out.append

    def short(u):
        return cell(urllib.parse.unquote(u).split('/')[-1], 60)

    w('# Phase M3.8 — Confirmed-source acquisition pilot\n')
    w('Generated by `python tools/m38-acquisition-pilot.py` (`data/audit/m3.8-acquisition-pilot.jsonl`) from what '
      '`tools/m38-acquire.py` fetched; never edited by hand. **Acquisition only: no model, evidence, provenance, '
      'reconciliation, gap-register or application data was created or changed.** No value was extracted, no '
      'vintage or wine created, nothing OCR\'d. The fetched bytes are kept outside Git in '
      '`sources/acquisition/m3.8/`, as the M3.6G and M3.7 stores are.\n')
    w('## 1. The gate\n')
    w('M3.7\'s ranking, its first five relationships and nothing else, in this order: %s. The probable sources '
      '(%s) and the 380 unreviewed legacy relationships were never targets; a target off its relationship\'s host '
      'stops the fetch.\n' % (', '.join('%s (`%s`)' % (rel_name.get(next((r['relationship'] for r in by['relationship']
                                                                          if r['estate'] == e), None), e), s)
                                      for s, e in scope['gate']),
                              ', '.join('`%s`' % s for s in scope['excluded_sources'])))
    w('The targets are the URLs M3.7 relied on: each relationship\'s M3.3 candidate locators (%d), plus Myrat\'s fiche '
      'PDFs that M3.3 recorded as blocked by policy, which were not requested. The two G&C Lurton relationships share '
      'one download pool: M3.3 listed a mixed slice of it for each, so every pool URL was fetched once and judged by its '
      'own text against both estates (`eligible_relationships`), M3.3\'s list kept as `listed_for`.\n'
      % sum(1 for i in items if i['target'] == 'TARGET'))
    w('## 2. Outcome\n')
    w('| | Count |')
    w('|---|---:|')
    w('| items | %d |' % sm['items'])
    w('| URLs requested (robots.txt and the delay of `tools/discover.py`) | %d |' % sm['requested'])
    w('| artifacts acquired (bytes stored) | %d |' % sm['acquired'])
    for k in CLASSES:
        w('| `%s` | %d |' % (k, sm['by_classification'][k]))
    w('| for a later evidence review | %d |' % sm['later_review'])
    w('')
    w('| Relationship | Listed by M3.3 | Attributed by text | Exact | Estate + vintage | Unclear | Non-vintage | '
      'Duplicate | Vintages identified |')
    w('|---|---:|---:|---:|---:|---:|---:|---:|---|')
    for r in by['relationship']:
        b = r['by_classification']
        w('| %s (`%s`) | %d | %d | %d | %d | %d | %d | %d | %s |' % (
            r['estate_name'], r['source_name'], r['listed'], r['attributed'], b['EXACT_ESTATE_WINE_VINTAGE'],
            b['ESTATE_VINTAGE_ONLY'], b['ESTATE_DOCUMENT_IDENTITY_UNCLEAR'], b['NON_VINTAGE_DOCUMENT'],
            b['DUPLICATE_ARTIFACT'], ', '.join(str(v) for v in r['vintages_identified']) or '—'))
    w('')
    w('## 3. Identity rules\n')
    w('Identity comes from the document\'s own text: never its URL, filename, folder, the page that linked it, or a '
      'publication date. The estate is named in the text (a web address such as durfort-vivens.com is not a naming); '
      'the wine is a heading that is the name of a wine the model lists for that estate; the vintage is an explicit '
      'statement ("vintage 2014", "2013 vintage", "Jahrgang 2013", "年份2004", or the heading wine\'s name followed by '
      'a year). A year standing alone on a line is layout: it is kept as `bare_year_lines` for the later review and '
      'never used. Conflicting statements leave the vintage open.\n')
    w('## 4. Exact estate + wine + vintage documents\n')
    w('| # | Document | Wine | Vintage | Stated as | Genre |')
    w('|---:|---|---|---:|---|---|')
    for i in items:
        if i['classification'] == 'EXACT_ESTATE_WINE_VINTAGE':
            d = i['identity']
            w('| %d | %s | `%s` | %d | %s | %s |' % (i['n'], short(i['url']), d['wine'], d['vintage'],
                                                  cell(d['vintage_basis'], 60), d['genre']))
    w('')
    w('## 5. Estate + vintage documents (wine not stated in the text)\n')
    w('| # | Document | Estate | Vintage | Stated as | Language |')
    w('|---:|---|---|---:|---|---|')
    for i in items:
        if i['classification'] == 'ESTATE_VINTAGE_ONLY':
            d = i['identity']
            w('| %d | %s | `%s` | %d | %s | %s |' % (i['n'], short(i['url']), d['estate'], d['vintage'],
                                                  cell(d['vintage_basis'], 40), d['language'] or '—'))
    w('\nThe La Mondotte sheets in German and English (22) name neither the estate nor the wine in their text - the '
      'name is not in the extracted text - and state only the vintage ("2013 VINTAGE", "JAHRGANG 2013"): they stay '
      '`ESTATE_DOCUMENT_IDENTITY_UNCLEAR`. Their Chinese editions name the estate ("拉梦多酒庄") and the vintage '
      '("年份2004"), and are the 11 above.\n')
    w('## 6. Documents needing a later review\n')
    w('Estate-identified documents whose vintage, wine or both the text does not state as the rules require, and '
      'documents that name something the model does not list:\n')
    w('| # | Document | Classification | Estate | Wine | Bare year lines | Other identity |')
    w('|---:|---|---|---|---|---|---|')
    for i in items:
        d = i['identity'] or {}
        if i['classification'] in ('ESTATE_DOCUMENT_IDENTITY_UNCLEAR', 'DUPLICATE_ARTIFACT') and \
                (d.get('estate') or d.get('other_identity')):
            w('| %d | %s | `%s` | %s | %s | %s | %s |' % (
                i['n'], short(i['url']), i['classification'], d.get('estate') or '—', d.get('wine') or '—',
                ', '.join(str(y) for y in d.get('bare_year_lines') or []) or '—', cell(d.get('other_identity'))))
    w('\nOther identities are reported, never attributed: other estates on the shared G&C Lurton pool (Château '
      'Ferrière, Château La Gurgue) and cuvées the model does not list (La Nature de Durfort-Vivens, Le Relais de '
      'Durfort-Vivens, Le Haut-Médoc de Haut-Bages Libéral).\n')
    w('## 7. Duplicates, revisions and related renderings\n')
    for i in items:
        if i['classification'] == 'DUPLICATE_ARTIFACT':
            w('- #%d %s: the same bytes are already held (`%s`)%s' % (
                i['n'], short(i['url']), i['duplicate_of'],
                '; not requested' if i['retrieval'] == 'NOT_REQUESTED_ALREADY_HELD' else ''))
    rev = [i for i in items if i['classification'] == 'REVISION_OF_EXISTING_ARTIFACT']
    w('- revisions of a held document (same URL or file name, other bytes): %d' % len(rev))
    for i in items:
        if i.get('renders_held_page'):
            w('- #%d %s: a print view of a page the crawl already held (%s): a related rendering, kept separately, '
              'not a revision' % (i['n'], short(i['url']), ', '.join('`%s`' % x for x in i['renders_held_page'])))
    w('')
    w('## 8. Blocked, failed and missing\n')
    w('| # | URL | Classification | Retrieval | Status | Retry | Alternative known URL |')
    w('|---:|---|---|---|---|---|---|')
    for i in items:
        if i['classification'] in ('BLOCKED_BY_ROBOTS', 'FETCH_FAILED', 'NOT_FOUND'):
            w('| %d | %s | `%s` | %s%s | %s | %s | %s |' % (
                i['n'], short(i['url']), i['classification'], i['retrieval'],
                ' (robots allows it now: %s)' % i['robots_allows_now'] if 'robots_allows_now' in i else '',
                i.get('status') or '—', i['retry'], ', '.join(short(u) for u in i['alternative_known_url'] or []) or '—'))
    w('\nNo blocked URL was requested and none was retried. Myrat\'s fiche PDFs stay blocked as M3.3 recorded; its '
      'print pages, which the gate allowed, were fetched.\n')
    w('## 9. Source contradictions\n')
    w('None with M3.7: every acquired document came from its relationship\'s confirmed host, and no document named a '
      'publisher or owner other than the one M3.7 recorded. The finding is about M3.3\'s locator lists, not the '
      'sources: on a shared pool they mix several estates\' documents, so a list is not an identity.\n')
    w('## 10. No model mutation\n')
    w('`tools/test-m38.py` checks that `data/model`, `data/evidence` (v1-v8), `data/app`, the gap register, '
      '`data/websites.js` and the app files are as M3.7 left them.\n')
    w('## 11. Every item\n')
    w('| # | Document | Listed for | Retrieval | Classification | Estate | Wine | Vintage | Language | Genre |')
    w('|---:|---|---|---|---|---|---|---:|---|---|')
    for i in items:
        d = i['identity'] or {}
        w('| %d | %s | %s | %s | `%s` | %s | %s | %s | %s | %s |' % (
            i['n'], short(i['url']), ', '.join(rel_name[r] for r in i['listed_for']), i['retrieval'],
            i['classification'], d.get('estate') or '—', d.get('wine') or '—', d.get('vintage') or '—',
            d.get('language') or '—', d.get('genre') or '—'))
    return ('\n'.join(out) + '\n').encode('utf-8')


def main():
    try:
        rows = build()
    except (Stop, A.Stop) as s:
        print('BLOCKED - %s' % s)
        sys.exit(2)
    b, doc = body(rows), report(rows)
    if '--check' in sys.argv:
        bad = [p[len(L.ROOT):] for p, x in ((OUT, b), (DOC, doc)) if not os.path.exists(p) or open(p, 'rb').read() != x]
        print('M3.8 outputs ' + ('are current' if not bad else 'differ: %s' % bad))
        sys.exit(1 if bad else 0)
    open(OUT, 'wb').write(b)
    open(DOC, 'wb').write(doc)
    print('%s written (%d records); %s written' % (OUT[len(L.ROOT):], b.count(b'\n'), DOC[len(L.ROOT):]))


if __name__ == '__main__':
    main()
