"""The integration review: the reviewed rows the acceptance path reads for the adopted identity rules, and the three
manifests built from them.

    python tools/integration-review.py              write data/audit/integration-review.jsonl and
                                                    docs/PHASE-INTEGRATION-REVIEW.md
    python tools/integration-review.py --check      recompute both and compare, byte for byte
    python tools/integration-review.py --manifests  write the evidence-acceptance, vintage-creation and
                                                    value-application manifests from the committed review

An audit in M3.9's review format (tools/m39-evidence-review.py): what each document establishes, by the existing
reader, with the identity decided by the adopted rules (tools/identity_rules.py) beside M3.4A's decide. Nothing in
the model, the evidence store or the gap register changes; the manifests are authorizations the three runners
validate and apply, never evidence themselves.

THE DOCUMENTS are the integration dry run's ACCEPTABLE_TO_NEXT_STAGE claims (data/audit/integration-dryrun.jsonl),
grouped by document and vintage. Each is put to every wine the model lists for its estate, as M3.9 does, and a row
is SAFE_TO_MAP only when exactly the claimed wine is: the document's evidence holds (the adopted rules on decide),
the reader raises no objection, R1's gate passes. A document the rules leave unsettled is reviewed and refused; the
dry run's count is not assumed.

THE IDENTITY SOURCE is M34A where decide accepts the text as the rules leave it (R1, R1b, R2, R3 rewrite or mask
it; their trace is kept as identity_rules; R1's gate applies), R4 where the reviewed listing names the wine: a
separate identity method with its own gate, recording_policy.check_listing_review (the listing record and the
pages' headings are kept). For R4, decide's verdict on the text R4 annotated is a veto only (text_check), never the
identity, and R1's gate is not asked.

THE VINTAGE is the document's own: M3.8's statement or wine-and-year form (the P1 review's vintage_basis), else, by
the user's decision of 2026-11-18, the title block R2 reads ('title block ...') or the estate's short name beside the
year that R1b reads ('short name and year ...'). Never the filename or the listing.

THE FIGURES are the dry run's candidate fields only: the reader's value, confirmed by statement verification v2
(tools/statement_check.py), quoted as the held lines that state it; or, for a yield the reader does not read, the
C6 layout read (tools/yield_layout.py) as recording_policy.c6_observation records it.
"""
import collections
import importlib.util
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import identity_rules as IR  # noqa: E402
import migration_lib as L  # noqa: E402
import recording_policy as RP  # noqa: E402
import statement_check as S2  # noqa: E402
import yield_layout as Y  # noqa: E402


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, L.ROOT + rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


P1 = _load('p1_integration_review', 'tools/m312-p1-review.py')       # the M3.9 reader over the discovery store
R, X, V, RB = P1.R, P1.X, P1.V, P1.RB

VERSION = 'integration-review/1'
AUDIT = 'data/audit/integration-review.jsonl'
OUT = L.ROOT + AUDIT
DOC = L.ROOT + 'docs/PHASE-INTEGRATION-REVIEW.md'
PREFIX = 'ir'
DRYRUN = L.ROOT + 'data/audit/integration-dryrun.jsonl'
MANIFESTS = {'acceptance': 'data/audit/evidence-acceptance-manifest.jsonl',
             'vintage': 'data/audit/vintage-creation-manifest.jsonl',
             'value': 'data/audit/value-application-manifest.jsonl'}
CATEGORY = R.CATEGORY
DISP = {'ESTATE_VINTAGE_ONLY': 'ESTATE_ONLY', 'ALREADY_MAPPED': 'ALREADY_SUPPORTED', 'NOT_FOUND': 'EVIDENCE_INSUFFICIENT',
        IR.HELD: 'REVIEW_REQUIRED', IR.REFUSED: 'NOT_RELEVANT'}
SEP = re.compile(r'[ \t]*\n[ \t\n]*')       # R.joined's line separator, on the folded text


class Stop(Exception):
    pass


def candidates():
    """The dry run's acceptable claims, {(sha, estate, wine, vintage): {field: dry-run claim}}."""
    out = collections.defaultdict(dict)
    for r in L.jsonl_lines(DRYRUN):
        if r['record'] == 'claim' and r['final']['disposition'] == 'ACCEPTABLE_TO_NEXT_STAGE':
            c = r['claim']
            out[(c['sha256'], c['estate_id'], c['wine_id'], c['vintage'])][c['field']] = r
    return out


def locate(raw, words, value=None):
    """(quote, locus) of the statement `words` (folded, as statement_check reads it): the held lines that hold it, as
    held, and their page and line numbers (non-blank lines, 1-based), or (None, None)."""
    # folding is not length-preserving (decomposed accents), so the text is folded line by line: a held line is
    # one segment of the joined text, which must be exactly the text statement_check read
    held = [l for l in raw.split('\n') if RB.fold(l).strip(' \t\n')]
    segs = [RB.fold(l).strip(' \t\n') for l in held]
    joined = ' / '.join(segs)
    edges = re.sub(r'(?:[ \t\n]*/)?[ \t\n]*$', '', re.sub(r'^[ \t\n]*(?:/[ \t\n]*)?', '', R.joined(raw)))
    if joined != edges:              # R.joined writes a blank first or last line as a separator at the edge
        raise Stop('the held lines do not rebuild the text statement_check reads')
    words = re.sub(r'^(?:[ \t]*/[ \t]*)+|(?:[ \t]*/[ \t]*)+$', '', words)   # a statement may end on a line break
    at = joined.find(words)
    if at < 0 or not words:
        return None, None
    starts, o = [], 0
    for s in segs:
        starts.append(o)
        o += len(s) + 3
    hit = [i for i, st in enumerate(starts) if st <= at + len(words) - 1 and st + len(segs[i]) >= at]
    first, last = hit[0], hit[-1]
    if value is not None:        # the statement's window runs on past it: end the quote at the value's last number
        nums = collections.Counter(float(x) for x in (value.values() if isinstance(value, dict) else [value]))

        def holds(i, k):       # every number of the value, as often as it occurs (a 50/50 blend states 50 twice)
            got = collections.Counter(float(m.replace(',', '.')) for l in held[i:k + 1]
                                      for m in re.findall(r'\d+(?:[.,]\d+)?', l))
            return all(got[n] >= c for n, c in nums.items())
        while last > first and holds(first, last - 1):
            last -= 1
    return ' / '.join(held[i].strip(' \t') for i in range(first, last + 1)), (first, last)


class Review:
    def __init__(self):
        self.rd = P1.Reader()
        self.cx = self.rd.cx
        self.ents = RP.reviewed_entries()
        names = collections.defaultdict(list)
        for n in L.read_table('identity/names.jsonl'):
            if n['kind'] == 'CURRENT':
                names[n['subject']].append(n['name'])
        self.names = names
        self.disc = {a['sha256']: a for a in L.jsonl_lines(L.ROOT + 'data/discovery/artifacts.jsonl')}

    def close(self):
        self.rd.close()

    def evidence(self, sha, folded, e, w, y):
        """The document's own evidence for (e, w, y), as M3.9's judge gives it, with the adopted rules on decide."""
        cx = self.cx
        j = RB.judge(folded, {'estate': e, 'wine': w, 'vintage': y}, cx.wines, cx.ew, cx.blocked)
        if j is not None:
            d = j['disposition']
            m = ('IDENTITY_BLOCKED' if d == 'WINE_AMBIGUOUS' and 'open identity decision' in j['basis'] else
                 'NOT_RELEVANT' if d == 'WRONG_EXISTING_ATTRIBUTION' else 'SAFE_TO_MAP' if d == 'SAFE_TO_ATTRIBUTE' else d)
            return {'kind': 'DOCUMENT', 'disposition': m, 'basis': j['basis'], 'rule': 'T', 'title': j['title']}, None
        mrow = {'vintage_id': 'vt:%s:%d' % (w, y), 'evidence_refs': ['(the document text; no decision)']}
        a = {'id': 'm3.8:%s' % sha[:12], 'bytes_available': True, 'sha256': sha}
        with R.text_hook(folded):
            rec = IR.identify(V.M34A, (mrow, a, [], e, w, y, cx.nm, cx.ew, cx.wines_raw, cx.blocked, cx.vd))
        disp, reason, basis, facts = rec['result']
        r4 = any(t[0] == 'R4' for t in rec['trace'])
        ev = {'kind': 'DOCUMENT', 'disposition': DISP.get(disp, disp), 'basis': basis or reason,
              'rule': 'R4' if r4 else 'M34A', 'title': None, 'grand_vin_rule': bool((facts or {}).get('grand_vin')),
              'identity_rules': {'version': IR.VERSION, 'settled_by': rec['settled_by'],
                                 'trace': [list(t) for t in rec['trace']], 'notes': rec['notes']}}
        if r4:
            # the identity is the listing's: decide's verdict on the text R4 annotated is kept as a veto only
            li = rec['listing']
            ev['basis'] = ('the reviewed listing files the document under %s (%s), entries approved in the independent '
                           'review and signed off' % (cx.nm.get(w), ', '.join(x['entry'] for x in li['provenance']['listing'])))
            ev['text_check'] = {'role': 'veto only, not the identity: decide on the text R4 annotated with the '
                                        'listing\'s wine', 'disposition': DISP.get(disp, disp), 'basis': basis or reason}
            ev['listing'] = li
            by = {r['entry']: r for r in self.ents.values()}
            ev['headings'] = {x['entry']: [p['heading'] for p in by[x['entry']]['pages'] if p['names_the_wine']][0]
                              for x in rec['listing']['provenance']['listing']}
        return ev, rec

    def claim(self, sha, raw, folded, media, e, w, y):
        """One wine's claim, as the P1 review's Reader.claim builds it."""
        ev, rec = self.evidence(sha, folded, e, w, y)
        rd = R.reader(self.rd.pres, self.rd.est.get(e), sha, media, self.cx.nm.get(w, ''), y)
        dated = y in RB.dated_years(raw) and not re.search(
            r'(?<!\d)%d(?!\d)' % y, '\n'.join(l for l in folded.split('\n') if not RB.DATED_YEAR.search(l)))
        claim = {'wine': w, 'wine_name': self.cx.nm.get(w), 'wine_type': (self.cx.wines.get(w) or (None, None))[1],
                 'evidence_of_document': ev, 'reader': {'decision': rd[0], 'code': rd[1], 'why': rd[2]},
                 'claim_year_dated': bool(dated)}
        if ev['disposition'] == 'SAFE_TO_MAP' and rd[0] == 'ACCEPTED':
            disp, why = 'SAFE_TO_MAP', ev['basis']
        elif ev['disposition'] == 'SAFE_TO_MAP':
            disp = X.READER_TO_DISP.get(rd[1], 'EVIDENCE_INSUFFICIENT')
            why = 'the document\'s evidence holds (%s), but the reader refuses it (%s: %s)' % (ev['basis'], rd[1], rd[2])
        else:
            disp, why = ev['disposition'], ev['basis']
        gate = None
        if disp == 'SAFE_TO_MAP' and ev.get('rule') == 'R4':
            # a listing identity has its own gate (the user's decision of 2026-11-19): R1's gate asks whether a text
            # rule decided it, which a listing identity never claims
            claim['identity_gate'] = 'REVIEWED_LISTING'
            why_l = RP.check_listing_review(claim, sha, e, w, self.ents)
            gate = (['listing gate: %s' % why_l] if why_l else []) + (
                ['the year stands only in a dated line'] if dated else [])
        elif disp == 'SAFE_TO_MAP':
            claim['identity_gate'] = 'R1 (%s)' % ev.get('rule')
            gate = X.r1_gate({'wine': w, 'wine_name': self.cx.nm.get(w), 'vintage': y, 'evidence_of_document': ev,
                              'reader': claim['reader'], 'claim_year_dated': bool(dated)})
            if gate:
                disp, why = 'EVIDENCE_INSUFFICIENT', 'R1 gate: %s' % '; '.join(gate)
        claim.update(disposition=disp, basis=why, r1_gate=gate)
        return claim, rec

    def vintage_evidence(self, raw, folded, w, y, rec):
        vb = P1.vintage_basis(raw, folded, self.names.get(w, []), y)
        if vb:
            return vb
        # the title block R2 reads (two to four short lines: the wine's name, a classification, the year), wherever
        # it stands - R2 moves it only when it falls outside the opening - and only when no block names another year
        hs = IR.I.headings(folded, self.cx.nm.get(w, ''), False)
        mine = [h for h in hs if h[0] == y and h[1] == 'NAMED_BLOCK']
        if mine and not [h for h in hs if h[0] != y]:
            return 'title block "%s" (line %d of %d)' % (mine[0][2], mine[0][3], folded.count('\n') + 1)
        for t in (rec or {}).get('trace') or []:
            if t[0] == 'R1b':
                return 'short name and year "%s"' % t[1]
        return None

    def figure(self, sha, raw, media, e, w, y, f, art, lang):
        """The candidate figure for field f: the reader's value confirmed by its statement, or the C6 layout read."""
        got, how, j = self.rd.figures(sha, e, y)
        value = got.get(f)
        sv, words = S2.stated(f, j)
        if value is not None:
            verdict, _, _ = S2.verify('SAFE_TO_MAP', f, value, j)
            quote, lines = locate(raw, words, value) if words else (None, None)
            return {'field': f, 'source': 'READER', 'value': value, 'unit': R.UNITS.get(f), 'reader_words': how.get(f),
                    'statement_check': verdict, 'stated_value': sv, 'statement': words, 'quote': quote,
                    'locus': 'extracted text, non-blank lines %d-%d' % (lines[0] + 1, lines[1] + 1) if lines else None,
                    'lang': lang,
                    'recordable': verdict == 'CONFIRMED' and quote is not None}
        if f != 'yld' or media != 'application/pdf':
            return {'field': f, 'source': None, 'value': None, 'recordable': False,
                    'reason': 'the reader reads no %s' % f}
        others = [self.cx.nm.get(s, s) for s in sorted(set(self.cx.ew[e]) - {w})]
        c6 = Y.read_yield(self.rd.pres.blob(sha), 'SAFE_TO_MAP', None, y, self.cx.nm.get(w, ''), others)
        o = RP.c6_observation(c6, 'IDENTITY_SETTLED', None, 'vt:%s:%d' % (w, y), art, lang)
        if o['status'] != 'RECORDABLE':
            return {'field': f, 'source': 'C6_LAYOUT', 'value': None, 'recordable': False, 'reason': o['reason']}
        agree = sv is None or float(sv) == float(o['observation']['value'])
        return {'field': f, 'source': 'C6_LAYOUT', 'value': o['observation']['value'], 'unit': o['observation']['unit'],
                'stated_value': sv, 'statement': words, 'quote': o['provenance']['quote'],
                'locus': o['observation']['locus'], 'lang': lang,
                'c6': {'raw_value': o['observation']['raw_value'], 'evidence': o['provenance']['code_state']},
                'statement_check': 'AGREES' if agree else 'LAYERS_DISAGREE', 'recordable': agree}


def build():
    cands = candidates()
    rv = Review()
    rows = []
    try:
        for n, key in enumerate(sorted(cands, key=lambda k: (k[1], k[2], k[3], k[0])), 1):
            sha, e, w, y = key
            fields = cands[key]
            first = fields[sorted(fields)[0]]['claim']
            raw, _, media = P1.text_of(sha)
            folded = RB.fold(raw)
            claims, recs = [], {}
            for x in sorted(set(rv.cx.ew[e])):
                c, rec = rv.claim(sha, raw, folded, media, e, x, y)
                claims.append(c)
                recs[x] = rec
            safe = [c for c in claims if c['disposition'] == 'SAFE_TO_MAP']
            target = next(c for c in claims if c['wine'] == w)
            ok = [c['wine'] for c in safe] == [w]
            disp = 'SAFE_TO_MAP' if ok else ('MULTI_WINE_AMBIGUOUS' if len(safe) > 1 else target['disposition'])
            if disp == 'SAFE_TO_MAP' and not ok:
                disp = 'CONFLICT'
            lang = (rv.disc.get(sha) or {}).get('lang_detected')
            ev = target['evidence_of_document']
            row = {'record': 'review', 'n': n, 'artifact': first['artifact'], 'url': first['url'], 'sha256': sha,
                   'bytes': (rv.disc.get(sha) or {}).get('bytes'), 'media': media, 'language': lang,
                   'document_type': V.doc_type(folded, media), 'estate': e, 'estate_name': rv.cx.nm.get(e),
                   'vintage': y, 'vintage_evidence': rv.vintage_evidence(raw, folded, w, y, recs[w]),
                   'claims': claims, 'disposition': disp, 'category': CATEGORY.get(disp, 'IDENTITY_AMBIGUOUS'),
                   'wine': w if disp == 'SAFE_TO_MAP' else None,
                   'identity_source': ev.get('rule'), 'reason': target['basis'],
                   'dry_run_claims': sorted(r['claim_id'] for r in fields.values()),
                   'not_used': 'URL, file name, folder, domain and crawl membership: never identity (the listing is R4\'s '
                               'reviewed relationship, not a file name)'}
            if disp == 'SAFE_TO_MAP':
                row['figures'] = [rv.figure(sha, raw, media, e, w, y, f, first['artifact'], lang) for f in sorted(fields)]
            rows.append(row)
    finally:
        rv.close()
    return [{'record': 'scope', 'version': VERSION, 'identity_rules': IR.VERSION, 'statement_check': S2.VERSION,
             'c6': Y.VERSION, 'documents': len(rows), 'dry_run_claims': sum(len(v) for v in cands.values()),
             'reader_files': list(R.READER_FILES), 'not_written': 'no evidence decision, attribution or value; the '
             'manifests are written separately (--manifests)'}] + rows + [summary(rows)]


def summary(rows):
    c = collections.Counter(r['disposition'] for r in rows)
    figs = [f for r in rows for f in r.get('figures') or []]
    return {'record': 'summary', 'documents': dict(sorted(c.items())),
            'identity_source': dict(sorted(collections.Counter(r['identity_source'] for r in rows
                                                               if r['disposition'] == 'SAFE_TO_MAP').items())),
            'vintage_evidence': dict(sorted(collections.Counter((r['vintage_evidence'] or 'NONE').split(' ')[0]
                                                                for r in rows if r['disposition'] == 'SAFE_TO_MAP').items())),
            'figures': len(figs), 'recordable': sum(1 for f in figs if f['recordable']),
            'by_source': dict(sorted(collections.Counter(f['source'] for f in figs if f['recordable']).items()))}


def body(rows):
    return ''.join(L.dumps(r) + '\n' for r in rows).encode('utf-8')


def report(rows):
    s = rows[-1]
    out = ['# Integration review', '',
           'Generated by `tools/integration-review.py` (%s); data in `%s`. An audit: nothing in the model or the '
           'evidence store changes.' % (VERSION, AUDIT), '',
           '- Documents: %d (%s).' % (len(rows) - 2, ', '.join('%s %d' % kv for kv in s['documents'].items())),
           '- Identity source of the safe documents: %s.' % ', '.join('%s %d' % kv for kv in s['identity_source'].items()),
           '- Vintage evidence: %s.' % ', '.join('%s %d' % kv for kv in s['vintage_evidence'].items()),
           '- Figures: %d, recordable %d (%s).' % (s['figures'], s['recordable'],
                                                   ', '.join('%s %d' % kv for kv in s['by_source'].items())), '',
           '| row | document | wine | vintage | identity | vintage evidence | figures |', '|---|---|---|---|---|---|---|']
    for r in rows[1:-1]:
        figs = ', '.join('%s %s%s' % (f['field'], L.dumps(f['value']), '' if f['recordable'] else ' (not recordable)')
                         for f in r.get('figures') or [])
        out.append('| %s:%d | %s | %s | %d | %s %s | %s | %s |' % (
            PREFIX, r['n'], (r['url'] or '').rsplit('/', 1)[-1], r['wine'] or '-', r['vintage'], r['disposition'],
            r['identity_source'], (r['vintage_evidence'] or '-').replace('|', '/'), figs or '-'))
    return ('\n'.join(out) + '\n').encode('utf-8')


# ---------------------------------------------------------------- the manifests

def manifests():
    """The three manifests from the committed review: one acceptance per safe document, one vintage-creation row
    per vintage, one value row per recordable figure. Evidence decision keys are the acceptance runner's own."""
    EA = _load('ea_integration_review', 'tools/apply-evidence-acceptance-manifest.py')
    rows = [r for r in L.jsonl_lines(OUT) if r.get('record') == 'review' and r['disposition'] == 'SAFE_TO_MAP']
    store = EA.Store()
    version = store.versions[-1] + 1
    reader = EA.decider_fingerprint()
    view = EA.V.View()
    names = EA.names_of(view)
    acc = []
    for i, r in enumerate(rows, 1):
        nm = sorted(names[r['artifact']])
        acc.append({'acceptance_id': 'eam_%06d' % i, 'artifact_id': r['artifact'], 'estate_id': r['estate'],
                    'wine_id': r['wine'], 'vintage': r['vintage'], 'decision': 'ACCEPTED', 'evidence_version': version,
                    'reader': reader, 'review': {'audit': AUDIT, 'row': '%s:%d' % (PREFIX, r['n'])},
                    'read': {'path': 'discovery/blobs/%s/%s' % (r['sha256'][:2], r['sha256']),
                             'extraction': 'discovery/extracted/%s.json' % r['sha256']},
                    'document_name': nm[0],
                    'notes': 'integration review %s:%d, identity %s' % (PREFIX, r['n'], r['identity_source'])})
    errs, resolved = EA.validate_manifest(acc, view, store, read_bytes=False)
    if errs:
        raise Stop('the acceptance manifest does not validate:\n  ' + '\n  '.join(errs))
    key = {(a['artifact_id'], a['wine_id'], a['vintage']): resolved[a['acceptance_id']]['key'] for a in acc}
    vin, val = [], []
    by_v = collections.defaultdict(list)
    for r in rows:
        by_v[(r['estate'], r['wine'], r['vintage'])].append(r)
    for i, ((e, w, y), rs) in enumerate(sorted(by_v.items()), 1):
        arts = sorted(r['artifact'] for r in rs)
        listing = any(r['identity_source'] == 'R4' for r in rs)
        vin.append({'manifest_id': 'vcm_%06d' % i, 'estate_id': e, 'wine_id': w, 'vintage': y, 'artifact_ids': arts,
                    'evidence_version': version, 'evidence_decisions': {r['artifact']: key[(r['artifact'], w, y)] for r in rs},
                    'review': {r['artifact']: {'audit': AUDIT, 'row': '%s:%d' % (PREFIX, r['n'])} for r in rs},
                    'creation_class': 'REVIEWED_LISTING' if listing else 'EXPLICIT_DOCUMENT_TEXT',
                    'notes': 'the vintage exists; this row records the existence attribution of each document'})
    facts = collections.defaultdict(list)
    for r in rows:
        for f in r.get('figures') or []:
            if f['recordable']:
                facts[(r['estate'], r['wine'], r['vintage'], f['field'])].append((r, f))
    VR = EA.V.VR
    n = len(L.jsonl_lines(L.ROOT + MANIFESTS['value'])) if os.path.exists(L.ROOT + MANIFESTS['value']) else 0
    for i, ((e, w, y, fld), xs) in enumerate(sorted(facts.items()), n + 1):
        values = {L.dumps(f['value']) for _, f in xs}
        srcs = {f['source'] for _, f in xs}
        if len(values) != 1 or len(srcs) != 1:
            raise Stop('%s %d %s: the documents disagree (%s, %s)' % (w, y, fld, sorted(values), sorted(srcs)))
        c6 = srcs == {'C6_LAYOUT'}
        locs = []
        for r, f in sorted(xs, key=lambda x: x[0]['artifact']):
            loc = {'artifact': r['artifact'], 'quote': f['quote'], 'locus': f['locus'], 'lang': f['lang'] or 'und'}
            if c6:
                loc['c6'] = f['c6']
            locs.append(loc)
        row = {'manifest_id': 'vam_%06d' % i, 'estate_id': e, 'wine_id': w, 'vintage': y, 'field': fld,
               'value': xs[0][1]['value'], 'artifact_ids': sorted(r['artifact'] for r, _ in xs),
               'evidence_version': version, 'observation_group': '%s-%d' % (w, y), 'application_class': 'SOURCED',
               'source_basis': VR.C6_BASIS if c6 else 'explicit_document_statement', 'source_locations': locs,
               'notes': 'integration review %s' % ', '.join('%s:%d' % (PREFIX, r['n']) for r, _ in xs)}
        if VR.FIELDS[fld][0]:
            row['unit'] = VR.FIELDS[fld][0]
        val.append(row)
    return acc, vin, val


def write_manifests():
    acc, vin, val = manifests()
    old = L.jsonl_lines(L.ROOT + MANIFESTS['value']) if os.path.exists(L.ROOT + MANIFESTS['value']) else []
    for k, rows in (('acceptance', acc), ('vintage', vin), ('value', old + val)):
        io.open(L.ROOT + MANIFESTS[k], 'w', encoding='utf-8', newline='\n').write(''.join(L.dumps(r) + '\n' for r in rows))
    print('acceptance %d, vintage %d, value %d (+%d)' % (len(acc), len(vin), len(old) + len(val), len(val)))


def main():
    if '--manifests' in sys.argv:
        write_manifests()
        return
    rows = build()
    b, d = body(rows), report(rows)
    if '--check' in sys.argv:
        ok = open(OUT, 'rb').read() == b and open(DOC, 'rb').read() == d
        print('integration review: %s' % ('reproduced' if ok else 'DIFFERS'))
        sys.exit(0 if ok else 1)
    open(OUT, 'wb').write(b)
    open(DOC, 'wb').write(d)
    print(L.dumps(rows[-1]))


if __name__ == '__main__':
    main()
