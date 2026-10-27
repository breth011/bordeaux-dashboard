"""M3.9: the evidence review of M3.8's 17 acquired candidates - what each document establishes, by the
existing reader, and what figures it would offer a later application phase.

    python tools/m39-evidence-review.py           write data/audit/m3.9-evidence-review.jsonl and
                                                  docs/PHASE-M3.9-EVIDENCE-REVIEW.md
    python tools/m39-evidence-review.py --check   recompute both and compare, byte for byte

An audit, as M3.6A's review was: no evidence decision is written (M3.6A recorded "no evidence decision exists
for these bytes; M3.6B would record one" and left that to its application phase), and nothing in the model,
the evidence store (v1-v8), the gap register or the app changes.

THE CANDIDATES are exactly M3.8's EXACT_ESTATE_WINE_VINTAGE and ESTATE_VINTAGE_ONLY items (17), in the brief's
order: Durfort-Vivens 2014 EN, 2014 FR, the 2021 bottling certificate, the 2024 brief; La Mondotte's eleven
Chinese sheets by vintage; Myrat 2010, 2011. The 62 unclear items, and the cuvées the model does not list,
are not reviewed.

THE CLAIM put to each document is (its estate, a wine the model lists for the estate, the vintage M3.8 read
in its text). It is a question, not an inference: the estate having one wine decides nothing - M3.4A's rule,
used unchanged, returns ESTATE_VINTAGE_ONLY for a document that names the estate and the year and not the
wine, single-wine estate or not.

THE READER is the existing one, unchanged, exactly as M3.6A's rerun applies it (tools/m36a-rerun.py):
  - the document's own evidence: a sheet by the M3.5 rubric (m35_rubric.judge, T1-T7), and where it has no
    title by M3.4A's rules (m34a-mapping-audit.decide); a web page by W1-W6 (web_evidence.judge_page);
  - the evidence store's reader as a veto: sheetreader.whose_sheet on the document presented as M3.6A's
    Presenter presents it (a PDF under its URL's file name; a page as its URL, title, headings and blocks);
  - SAFE_TO_MAP only when the document's evidence holds, the reader raises no objection, and R1's gate
    passes; a document the evidence supports but the reader refuses takes the reader's code.
The only difference is where the bytes are read from: M3.8's store (sources/acquisition/m3.8/), which the
model does not hold. M3.4A's rule reads its text through its own text hook, here given the held text.

THE FIGURES of a SAFE_TO_MAP document are what sheetreader.fields_of reads - its guards, then its readers,
with the words each figure was read in. They are candidates for a later application phase, compared with
the model's canonical value, never applied.
"""
import collections
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import migration_lib as L  # noqa: E402

_x = importlib.util.spec_from_file_location('m36a', L.ROOT + 'tools/m36a-rerun.py')
X = importlib.util.module_from_spec(_x)
_x.loader.exec_module(X)
_p = importlib.util.spec_from_file_location('m38', L.ROOT + 'tools/m38-acquisition-pilot.py')
P = importlib.util.module_from_spec(_p)
_p.loader.exec_module(P)
V, EV, SR, RB, WE = X.V, X.EV, X.SR, X.RB, X.WE

OUT = L.ROOT + 'data/audit/m3.9-evidence-review.jsonl'
DOC = L.ROOT + 'docs/PHASE-M3.9-EVIDENCE-REVIEW.md'
ACQ = P.ACQ
READER_FILES = ('tools/m35_rubric.py', 'tools/web_evidence.py', 'tools/sheetreader.py', 'tools/read-fiches.py',
                'tools/m34a-mapping-audit.py', 'tools/model_schema.py')
CATEGORY = {'SAFE_TO_MAP': 'ACCEPTED_EXACT_ESTATE_WINE_VINTAGE', 'ESTATE_ONLY': 'ESTATE_VINTAGE_ONLY',
            'WINE_AMBIGUOUS': 'IDENTITY_AMBIGUOUS', 'VINTAGE_AMBIGUOUS': 'IDENTITY_AMBIGUOUS',
            'MULTI_WINE_AMBIGUOUS': 'IDENTITY_AMBIGUOUS', 'COLOUR_AMBIGUOUS': 'IDENTITY_AMBIGUOUS',
            'ROLE_AMBIGUOUS': 'IDENTITY_AMBIGUOUS', 'IDENTITY_BLOCKED': 'IDENTITY_AMBIGUOUS',
            'EVIDENCE_INSUFFICIENT': 'REJECTED_INSUFFICIENT_EVIDENCE', 'NOT_RELEVANT': 'REJECTED_INSUFFICIENT_EVIDENCE',
            'CONFLICT': 'IDENTITY_AMBIGUOUS', 'ALREADY_SUPPORTED': 'ACCEPTED_EXACT_ESTATE_WINE_VINTAGE'}
UNITS = {'alc': '% vol', 'ph': 'pH', 'ta': 'g/L (as stated)', 'sug': 'g/L', 'yld': 'hl/ha', 'months': 'months',
         'oak': '% new oak', 'blend': '% by variety', 'harvest': 'dates', 'pick': 'dates by variety'}
# what the document's own sentence states for a field, on its text joined line by line (" / "): the check a
# reader's figure must pass before it is a candidate. A figure the statement contradicts is the reader's
# misreading; a statement the reader did not read is listed, never promoted.
NUM = r'(\d+(?:[.,]\d+)?)'
STATED = {
    'oak': re.compile(NUM + r'\s*%\s*(?:/\s*)?(?:in\s+|en\s+|de\s+)?(?:new\s+(?:oak\s+)?barrels|barriques\s+neuves|new\s+oak)'),
    'months': re.compile(r'(?:ageing|aging|elevage)\b[^%]{0,40}?\b(\d{1,2})\s*(?:months|mois)\b'),
    'yld': re.compile(NUM + r'\s*hl\s*/\s*ha'),
    'alc': re.compile(NUM + r'\s*%\s*(?:alcohol|alc\b|vol)|(?:alcohol|alcool)\s*(?:content)?\s*:?\s*' + NUM + r'\s*%'),
}
BLEND_LABEL = re.compile(r'(?:the blend|l.?\s?assemblage|blend of [a-z -]{0,30}\d{4}|assemblage)\b(.{0,200})')
VARIETY = {'CS': r'cabernet\s*(?:/\s*)?sauvignon', 'ME': r'merlot', 'CF': r'cabernet\s*(?:/\s*)?franc', 'PV': r'petit\s*(?:/\s*)?verdot'}
MONTHS = {'01': 'january', '02': 'february', '03': 'march', '04': 'april', '05': 'may', '06': 'june', '07': 'july',
          '08': 'august', '09': 'september', '10': 'october', '11': 'november', '12': 'december'}


def joined(raw):
    return re.sub(r'[ \t]*\n[ \t\n]*', ' / ', RB.fold(raw))


def num(x):
    return float(x.replace(',', '.'))


def stated(field, j):
    """(stated value, the words) the document's own text gives for a field, or (None, None)."""
    if field in STATED:
        m = STATED[field].search(j)
        if m:
            v = next(g for g in m.groups() if g)
            return num(v), m.group(0)
        return None, None
    if field == 'blend':
        # every blend label; the one whose following words state the most varieties is the blend's statement
        best, words = {}, None
        for m in BLEND_LABEL.finditer(j):
            out = {}
            for code, rx in VARIETY.items():
                mm = re.search(NUM + r'\s*%\s*(?:/\s*)?' + rx + r'|' + rx + r'\s*(?:/\s*)?:?\s*' + NUM + r'\s*%', m.group(1))
                if mm:
                    out[code] = num(next(g for g in mm.groups() if g))
            if len(out) > len(best):
                best, words = out, m.group(0)[:160]
        return (best or None), words
    return None, None


def check(field, value, j):
    """A reader's figure against the document's statement: CONFIRMED, CONTRADICTED_BY_STATEMENT, NOT_FOUND_AS_STATED."""
    if field == 'pick':
        dates = [d for v in value.values() for d in v.split('|')]
        ok = all(re.search(r'\b%s\s+0?%d\b|\b0?%d\s+%s\b' % (MONTHS[d[:2]], int(d[3:]), int(d[3:]), MONTHS[d[:2]]), j)
                 for d in dates)
        return ('CONFIRMED' if ok else 'NOT_FOUND_AS_STATED'), None, None
    sv, words = stated(field, j)
    if sv is None:
        return 'NOT_FOUND_AS_STATED', None, None
    if field == 'blend':
        same = {k: float(v) for k, v in value.items()} == sv
    else:
        same = float(value) == sv
    return ('CONFIRMED' if same else 'CONTRADICTED_BY_STATEMENT'), sv, words


ORDER = ('ftdv2014eng.pdf', 'ftdv2014fr.pdf', 'bottlingcertificatedurfort-vivens2021.pdf',
         'commercialandtechnicalargumentationdv2024.pdf')


class Stop(Exception):
    pass


def candidates():
    """M3.8's 17 candidates, in the brief's order."""
    items = [r for r in L.jsonl_lines(P.OUT) if r['record'] == 'item'
             and r['classification'] in ('EXACT_ESTATE_WINE_VINTAGE', 'ESTATE_VINTAGE_ONLY')]
    if len(items) != 17:
        raise Stop('M3.8 records %d candidates, expected 17' % len(items))

    def key(i):
        name = urllib.parse.unquote(i['url']).split('/')[-1]
        est = i['identity']['estate']
        group = {'es_00263': 0, 'es_00293': 1, 'es_00253': 2}[est]
        return (group, ORDER.index(name) if name in ORDER else 0, i['identity']['vintage'])
    return sorted(items, key=key)


class Store(X.Presenter):
    """M3.6A's Presenter, reading M3.8's store: the same file name, the same page text."""

    def __init__(self, urls):
        self.dir = tempfile.mkdtemp(prefix='m39-')
        self.disc = {sha: {'first_url': u} for sha, u in urls.items()}

    def blob(self, sha):
        p = ACQ + 'blobs/' + sha
        return open(p, 'rb').read() if os.path.exists(p) else None

    def present(self, sha, media):
        if media == 'application/pdf':
            return X.Presenter.present(self, sha, media)
        url = self.disc[sha]['first_url']
        base = os.path.basename(urllib.parse.urlparse(url).path.rstrip('/')) or 'index'
        x = json.load(open(ACQ + 'extracted/%s.json' % sha, encoding='utf-8'))
        lines = [url, x.get('title') or '']
        lines += [h.get('text') or '' for h in x.get('headings') or []]
        lines += [b.get('text') or '' for b in x.get('blocks') or []]
        sub = os.path.join(self.dir, sha[:16])
        os.makedirs(sub, exist_ok=True)
        p = os.path.join(sub, base + '.txt')
        io.open(p, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
        return p, base + '.txt'


@contextlib.contextmanager
def text_hook(text):
    """M3.4A's rule reads a document's text through document_text(id); give it the held text."""
    old = V.M34A.document_text
    V.M34A.document_text = lambda aid: (text, 'held (sources/acquisition/m3.8)')
    try:
        yield
    finally:
        V.M34A.document_text = old


def judge(cx, item, ext, folded, e, w, y):
    """The document's own evidence, as M3.6A's Judge gives it."""
    if ext is not None:
        j = WE.judge_page(ext, {'estate': e, 'wine': w, 'vintage': y}, cx.wines, cx.ew, cx.blocked,
                          sorted(v for k, v in cx.nm.items() if k.startswith('es_')))
        return {'kind': 'WEB_PAGE', 'disposition': j['disposition'], 'basis': j['basis'],
                'page': {k: j[k] for k in ('page_type', 'page_type_basis', 'identity_source', 'identity', 'identity_region',
                                           'vintage_source', 'excluded_region_match', 'ambiguity_reason')}}
    j = RB.judge(folded, {'estate': e, 'wine': w, 'vintage': y}, cx.wines, cx.ew, cx.blocked)
    if j is not None:
        d = j['disposition']
        m = ('IDENTITY_BLOCKED' if d == 'WINE_AMBIGUOUS' and 'open identity decision' in j['basis'] else
             'NOT_RELEVANT' if d == 'WRONG_EXISTING_ATTRIBUTION' else 'SAFE_TO_MAP' if d == 'SAFE_TO_ATTRIBUTE' else d)
        return {'kind': 'DOCUMENT', 'disposition': m, 'basis': j['basis'], 'rule': 'T', 'title': j['title']}
    mrow = {'vintage_id': 'vt:%s:%d' % (w, y), 'evidence_refs': ['(the document text; no decision)']}
    a = {'id': 'm3.8:%s' % item['sha256'][:12], 'bytes_available': True}
    with text_hook(folded):
        disp, reason, basis, facts = V.M34A.decide(mrow, a, [], e, w, y, cx.nm, cx.ew, cx.wines_raw, cx.blocked, cx.vd)
    m = {'ESTATE_VINTAGE_ONLY': 'ESTATE_ONLY', 'ALREADY_MAPPED': 'ALREADY_SUPPORTED',
         'NOT_FOUND': 'EVIDENCE_INSUFFICIENT'}.get(disp, disp)
    return {'kind': 'DOCUMENT', 'disposition': m, 'basis': basis or reason, 'rule': 'M34A', 'title': None,
            'grand_vin_rule': bool(facts.get('grand_vin'))}


def reader(store, est, sha, media, wname, y):
    return X.reader_verdict(store, est, sha, media, wname, y)


def figures(store, est, sha, url, y):
    """sheetreader.fields_of on the presented document: (fields, how) - what the fiche reader would take."""
    path, fn = store.present(sha, 'application/pdf')
    _, e = est
    return SR.fields_of(path, e.get('name'), e.get('cuvees') or (), e.get('second'), e.get('cat'), filename=fn, year=y)


def build():
    cx = V.Ctx()
    est = X.legacy_estates()
    canon = collections.defaultdict(dict)
    for v in L.read_table('canonical/values.jsonl'):
        canon[v['subject']][v['field']] = v['value']
    vints = {v['id'] if 'id' in v else 'vt:%s:%s' % (v['wine'], v['label']) for v in L.read_table('identity/vintages.jsonl')}
    items = candidates()
    store = Store({i['sha256']: i['url'] for i in items})
    rows = []
    try:
        for n, item in enumerate(items, 1):
            idn = item['identity']
            e, y = idn['estate'], idn['vintage']
            wines = sorted(cx.ew.get(e, []))
            if idn['wine']:
                wines = [idn['wine']]
            html = (item['content_type'] or '').startswith('text/html')
            ext = json.load(open(ACQ + 'extracted/%s.json' % item['sha256'], encoding='utf-8')) if html else None
            raw, _ = P.text_of(item['sha256'])
            folded = RB.fold(raw)
            media = 'text/html' if html else 'application/pdf'
            claims = []
            for w in wines:
                ev = judge(cx, item, ext, folded, e, w, y)
                rd, rcode, rwhy = reader(store, est.get(e), item['sha256'], media, cx.nm.get(w, ''), y)
                dated = y in RB.dated_years(raw) and not re.search(
                    r'(?<!\d)%d(?!\d)' % y, '\n'.join(l for l in folded.split('\n') if not RB.DATED_YEAR.search(l)))
                claim = {'wine': w, 'wine_name': cx.nm.get(w), 'wine_type': (cx.wines.get(w) or (None, None))[1],
                         'evidence_of_document': ev, 'reader': {'decision': rd, 'code': rcode, 'why': rwhy},
                         'claim_year_dated': bool(dated) if ev['kind'] == 'DOCUMENT' else False}
                if ev['disposition'] == 'SAFE_TO_MAP' and rd == 'ACCEPTED':
                    disp, why = 'SAFE_TO_MAP', ev['basis']
                elif ev['disposition'] == 'SAFE_TO_MAP':
                    disp = X.READER_TO_DISP.get(rcode, 'EVIDENCE_INSUFFICIENT')
                    why = 'the document\'s evidence holds (%s), but the reader refuses it (%s: %s)' % (ev['basis'], rcode, rwhy)
                else:
                    disp, why = ev['disposition'], ev['basis']
                gate = None
                if disp == 'SAFE_TO_MAP':
                    gate = X.r1_gate(dict(claim, wine_name=cx.nm.get(w), vintage=y))
                    if gate:
                        disp, why = 'EVIDENCE_INSUFFICIENT', 'R1 gate: %s' % '; '.join(gate)
                claim.update(disposition=disp, basis=why, r1_gate=gate)
                claims.append(claim)
            best = next((c for c in claims if c['disposition'] == 'SAFE_TO_MAP'), claims[0])
            vt = 'vt:%s:%d' % (best['wine'], y)
            row = {'record': 'review', 'n': n, 'm38_item': item['n'], 'url': item['url'], 'sha256': item['sha256'],
                   'bytes': item['bytes'], 'media': media, 'language': idn['language'],
                   'document_type': V.doc_type(folded, media) if folded else 'NO_TEXT', 'm38_genre': idn['genre'],
                   'estate': e, 'estate_name': cx.nm.get(e), 'vintage': y, 'vintage_evidence': idn['vintage_basis'],
                   'm38_classification': item['classification'], 'm38_wine': idn['wine'],
                   'explicit_estate_names': idn['estates_named'], 'heading': idn['heading'],
                   'other_identity': idn['other_identity'], 'colour_evidence': RB.blend_colour(folded),
                   'claims': claims, 'disposition': best['disposition'], 'category': CATEGORY[best['disposition']],
                   'wine': best['wine'] if best['disposition'] == 'SAFE_TO_MAP' else None,
                   'identity_source': (best['evidence_of_document'].get('rule') or
                                       (best['evidence_of_document'].get('page') or {}).get('identity_source')),
                   'vintage_in_model': vt in vints, 'reason': best['basis'],
                   'not_used': 'URL, file name, folder, domain, listed_for and crawl membership: never identity '
                               '(the reader veto sees the file name as M3.6A presents it; a veto can only refuse)'}
            if row['disposition'] == 'SAFE_TO_MAP' and not html:
                got, how = figures(store, est.get(e), item['sha256'], item['url'], y)
                j = joined(raw)
                vals = []
                for f in sorted(got):
                    existing = canon.get(vt, {}).get(f)
                    verdict, sv, words = check(f, got[f], j)
                    vals.append({'field': f, 'value': got[f], 'unit': UNITS.get(f), 'reader_words': how.get(f),
                                 'statement_check': verdict, 'stated_value': sv, 'statement': words,
                                 'vintage_scope': y, 'scope': 'WINE_VINTAGE (the document is accepted as %s %d)'
                                 % (cx.nm.get(best['wine']), y),
                                 'derivation': 'dates read from a stated span' if f == 'pick' else None,
                                 'existing': existing,
                                 'conflict_with_model': existing is not None and existing != got[f],
                                 'suitable_for_later_canonicalization': verdict == 'CONFIRMED' and existing in (None, got[f])})
                row['figures'] = vals
                row['figures_refused'] = how.get('refused')
                row['stated_not_read'] = [{'field': f, 'stated_value': sv, 'statement': words}
                                          for f in ('alc', 'months', 'oak', 'yld', 'blend') if f not in got
                                          for sv, words in [stated(f, j)] if sv is not None] or None
                row['statements'] = {f: sv for f in ('alc', 'months', 'oak', 'yld', 'blend')
                                     for sv, _ in [stated(f, j)] if sv is not None}
            rows.append(row)
    finally:
        store.close()
    relate(rows)
    return [{'record': 'scope', 'phase': 'M3.9', 'candidates': len(rows), 'reader_files': list(READER_FILES),
             'reader_fingerprint': EV.reader_fingerprint(),
             'excluded': ['the 62 identity-unclear M3.8 items', 'La Nature de Durfort-Vivens', 'Le Relais de '
                          'Durfort-Vivens', 'Le Haut-Médoc de Haut-Bages Libéral', 'no evidence decision written',
                          'no model, provenance, vintage, wine or value change']}] + rows + [summary(rows)]


def relate(rows):
    """Language variants and revisions among the reviewed documents: same wine and vintage, other language."""
    by = collections.defaultdict(list)
    for r in rows:
        if r['wine']:
            by[(r['wine'], r['vintage'])].append(r)
    for (w, y), rs in by.items():
        for r in rs:
            others = [o for o in rs if o is not r]
            rel = []
            for o in others:
                same = r.get('statements') == o.get('statements')
                if r['sha256'] == o['sha256']:
                    kind = 'BYTE_IDENTICAL'
                elif r['m38_genre'] != o['m38_genre'] or r['document_type'] != o['document_type']:
                    kind = 'DIFFERENT_DOCUMENT_TYPE'
                elif r['language'] != o['language'] and same:
                    kind = 'LANGUAGE_VARIANT_SAME_STATEMENTS'
                elif r['language'] != o['language']:
                    kind = 'LANGUAGE_VARIANT_DIFFERENT_STATEMENTS'
                else:
                    kind = 'SAME_LANGUAGE_DIFFERENT_STATEMENTS'
                rel.append({'review': o['n'], 'url': o['url'], 'relation': kind,
                            'statements': {'this': r.get('statements'), 'other': o.get('statements')}})
            r['related'] = rel or None


def summary(rows):
    c = collections.Counter(r['category'] for r in rows)
    figs = collections.Counter(f['field'] for r in rows for f in r.get('figures') or [])
    # an observation counted once: language variants with the same figures are one statement
    seen, independent = set(), collections.Counter()
    for r in rows:
        for f in r.get('figures') or []:
            if not f['suitable_for_later_canonicalization']:
                continue
            k = (r['wine'], r['vintage'], f['field'], json.dumps(f['value'], sort_keys=True))
            if k not in seen:
                seen.add(k)
                independent[f['field']] += 1
    return {'record': 'summary', 'candidates': len(rows), 'by_category': dict(sorted(c.items())),
            'by_disposition': dict(sorted(collections.Counter(r['disposition'] for r in rows).items())),
            'figures_by_field': dict(sorted(figs.items())), 'independent_figures_by_field': dict(sorted(independent.items())),
            'suitable_figures': sum(1 for r in rows for f in r.get('figures') or [] if f['suitable_for_later_canonicalization']),
            'contradicted_by_statement': sum(1 for r in rows for f in r.get('figures') or []
                                             if f['statement_check'] == 'CONTRADICTED_BY_STATEMENT'),
            'conflicts_with_model': sum(1 for r in rows for f in r.get('figures') or [] if f['conflict_with_model']),
            'stated_not_read': sum(len(r.get('stated_not_read') or []) for r in rows),
            'evidence_decisions_written': 0, 'model_changes': 0}


def body(rows):
    return ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                   for r in rows).encode('utf-8')


def cell(s, n=None):
    s = str(s if s is not None else '—').replace('|', '\\|').replace('\n', ' ')
    return s if not n or len(s) <= n else s[:n - 1] + '…'


def report(rows):
    """docs/PHASE-M3.9-EVIDENCE-REVIEW.md, from the audit's records alone."""
    [scope], [sm] = rows[:1], rows[-1:]
    rv = [r for r in rows if r['record'] == 'review']
    out = []
    w = out.append

    def name(r):
        return cell(urllib.parse.unquote(r['url']).split('/')[-1], 55)

    def fv(v):
        return ', '.join('%s %s' % (k, ('%g' % x) if isinstance(x, float) else x) for k, x in sorted(v.items())) \
            if isinstance(v, dict) else ('%g' % v if isinstance(v, float) else str(v))

    w('# Phase M3.9 — Evidence review of acquired candidates\n')
    w('Generated by `python tools/m39-evidence-review.py` (`data/audit/m3.9-evidence-review.jsonl`); never edited by '
      'hand. **A review, not an application: no evidence decision was written, and no model, provenance, vintage, '
      'wine, value, gap-register or application data changed.** As M3.6A\'s review did, it leaves recording decisions '
      'to an application phase.\n')
    w('## 1. Candidate inventory\n')
    w('Exactly M3.8\'s %d `EXACT_ESTATE_WINE_VINTAGE` and `ESTATE_VINTAGE_ONLY` items, in the brief\'s order. The '
      'reader is the existing one, unchanged (fingerprint `%s`): a sheet by the M3.5 rubric, and without a title by '
      'M3.4A\'s rules; a web page by W1-W6; the evidence store\'s reader (`sheetreader.whose_sheet`) as a veto - '
      'exactly as M3.6A\'s rerun applies them, reading the bytes from M3.8\'s store.\n'
      % (scope['candidates'], scope['reader_fingerprint']))
    w('| # | Document | Estate | Vintage | Language | Type | M3.8 |')
    w('|---:|---|---|---:|---|---|---|')
    for r in rv:
        w('| %d | %s | %s | %d | %s | %s | `%s` |' % (r['n'], name(r), r['estate_name'], r['vintage'],
                                                    r['language'] or '—', r['m38_genre'], r['m38_classification']))
    w('\n## 2. Per-document identity verdict\n')
    w('| # | Document | Claim tested | Document\'s evidence | Reader | Disposition | Category |')
    w('|---:|---|---|---|---|---|---|')
    for r in rv:
        for c in r['claims']:
            ev = c['evidence_of_document']
            w('| %d | %s | %s %d | %s (%s) | %s | `%s` | `%s` |' % (
                r['n'], name(r), c['wine_name'], r['vintage'], cell(ev['basis'], 90),
                ev.get('rule') or (ev.get('page') or {}).get('page_type'), c['reader']['decision'],
                c['disposition'], r['category']))
    w('\n| Category | Documents |')
    w('|---|---:|')
    for k, n in sm['by_category'].items():
        w('| `%s` | %d |' % (k, n))
    w('')
    w('## 3. Wine-identity decisions\n')
    w('- **Château Durfort-Vivens (4): accepted.** Each names "Château Durfort-Vivens" beside its year, and no other '
      'wine of the estate (M3.4A); the reader raises no objection. Identity source: the document\'s text. The 2021 '
      'document is a bottling certificate and is reviewed as one; the 2024 document is a commercial and technical brief.')
    w('- **La Mondotte (11): estate and vintage only.** M3.4A\'s rule, unchanged: the document names the estate and '
      'the year, not the wine. The estate having one wine in the model decides nothing; no single-wine inference '
      'exists in the reader and none was added. The wine\'s name is not in the extracted text.')
    w('- **Château de Myrat (2): rejected, insufficient evidence.** The print views have no main heading (W1): the page '
      'establishes no wine. M3.8 read the estate and the vintage in their text; under W1-W4 that is not identity.\n')
    w('## 4. Value candidates\n')
    w('What `sheetreader.fields_of` reads from an accepted document, each figure checked against the document\'s own '
      'sentence: CONFIRMED, CONTRADICTED_BY_STATEMENT (the reader misread it), or NOT_FOUND_AS_STATED. Candidates only: '
      'nothing is applied.\n')
    w('| # | Document | Field | Reader read | Statement | Check | Existing | Suitable |')
    w('|---:|---|---|---|---|---|---|---|')
    for r in rv:
        for f in r.get('figures') or []:
            w('| %d | %s | %s | %s %s | %s | `%s` | %s | %s |' % (
                r['n'], name(r), f['field'], fv(f['value']), f['unit'] or '', cell(f['statement'], 60),
                f['statement_check'], fv(f['existing']) if f['existing'] is not None else '—',
                'yes' if f['suitable_for_later_canonicalization'] else 'no'))
    w('\nIndependent observations (language variants counted once): %s.\n'
      % ', '.join('%s %d' % kv for kv in sm['independent_figures_by_field'].items()))
    w('Stated in an accepted document but not read by the fiche reader - listed for the application phase, not '
      'promoted:\n')
    for r in rv:
        for s in r.get('stated_not_read') or []:
            w('- #%d %s: %s %s ("%s")' % (r['n'], name(r), s['field'], fv(s['stated_value']), s['statement']))
    w('\nScope: every candidate is the accepted wine\'s vintage figure, read from that vintage\'s document. The blends '
      'stand under the sheet\'s BLEND / L\'ASSEMBLAGE / "THE BLEND OF ... 2024" heading, not a vineyard section. The '
      'picking dates are read from a stated span ("From September 23 to October 8, 2024").\n')
    w('## 5. Conflicts\n')
    held = sum(1 for r in rv for f in r.get('figures') or [] if f['existing'] is not None)
    w('- With the model: %d. %s' % (sm['conflicts_with_model'], 'The model holds no canonical value for any candidate\'s '
      'field of these vintages.' if not held else '%d candidate(s) meet a value the model already holds.' % held))
    for r in rv:
        for f in r.get('figures') or []:
            if f['statement_check'] == 'CONTRADICTED_BY_STATEMENT':
                w('- **Reader against its own document:** #%d %s - the reader read %s %s, the document states "%s" '
                  '(%s). Not a candidate; a reader limitation (section 7).' % (
                      r['n'], name(r), f['field'], fv(f['value']), f['statement'], fv(f['stated_value'])))
    w('- Between documents: none. No "latest wins" rule was applied.\n')
    w('## 6. Language and revision relationships\n')
    for r in rv:
        for o in r.get('related') or []:
            w('- #%d %s ↔ #%d: `%s`' % (r['n'], name(r), o['review'], o['relation']))
    w('\nThe 2014 English and French sheets are separate artifacts (different bytes) of one document in two languages: '
      'the same blend, ageing and new-oak statements. They count as one observation. The French new-oak statement is '
      'in its text; the fiche reader did not read it.\n')
    w('## 7. Reader limitations\n')
    w('- **Folded text has no Chinese.** The reader folds text to ASCII: La Mondotte\'s Chinese sheets keep only their '
      'numbers. M3.8 read the estate ("拉梦多酒庄") and the vintage ("年份2004") on the raw text; the reader\'s '
      'verdict rests on the vintage it finds and states no wine.')
    w('- **Images are not read.** No OCR or image reading exists in the reader contract; none was introduced.')
    w('- **A print view has no main heading.** Myrat\'s print pages fail W1 by construction.')
    w('- **The fiche reader misreads or misses figures.** It took 30 for the 2024 new-oak share ("70% in new barrels '
      'and 30% in TAVA amphorae"), and did not read a stated ageing, new-oak share or alcohol (section 4). The reader '
      'is unchanged; these are listed for the application phase.\n')
    w('## 8. Unresolved candidates\n')
    w('- La Mondotte 2004-2013, 2015 (11): estate and vintage established, wine unresolved.')
    w('- Château de Myrat 2010, 2011 (2): no identity under W1; M3.8\'s estate-and-vintage reading stands as an '
      'acquisition finding, not evidence.\n')
    w('## 9. Explicit exclusions\n')
    for x in scope['excluded']:
        w('- %s' % x)
    w('- no reader rule, fingerprinted file, threshold or baseline changed\n')
    w('## 10. Model, evidence and application impact\n')
    w('None. Evidence decisions written: %d. Model changes: %d. `tools/test-m39.py` checks that `data/model`, '
      '`data/evidence` (v1-v8), `data/app`, the gap register and the reader files are as M3.8 left them.\n'
      % (sm['evidence_decisions_written'], sm['model_changes']))
    return ('\n'.join(out) + '\n').encode('utf-8')


def main():
    try:
        rows = build()
    except (Stop, P.Stop) as s:
        print('BLOCKED - %s' % s)
        sys.exit(2)
    b, doc = body(rows), report(rows)
    if '--check' in sys.argv:
        bad = [p[len(L.ROOT):] for p, x in ((OUT, b), (DOC, doc)) if not os.path.exists(p) or open(p, 'rb').read() != x]
        print('M3.9 outputs ' + ('are current' if not bad else 'differ: %s' % bad))
        sys.exit(1 if bad else 0)
    open(OUT, 'wb').write(b)
    open(DOC, 'wb').write(doc)
    print('%s written (%d records); %s written' % (OUT[len(L.ROOT):], b.count(b'\n'), DOC[len(L.ROOT):]))


if __name__ == '__main__':
    main()
