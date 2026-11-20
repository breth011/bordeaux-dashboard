"""Integration dry-run: identity, the figure reader, statement verification v2 and the C6 layout yield, at one boundary.

    python tools/integration-dryrun.py           write data/audit/integration-dryrun.jsonl and docs/PHASE-INTEGRATION-DRYRUN.md
    python tools/integration-dryrun.py --check   recompute both and compare, byte for byte
    python tools/integration-dryrun.py --timing  also print where the time goes (never written to the outputs)

A dry run, not an application: nothing in the model, the evidence store, the discovery store, the gap register or the
app changes, no evidence is accepted and no manifest is written. Nothing in production calls this file; the contract
it exercises is docs/INTEGRATION-CONTRACT.md.

For every claim (document x wine x vintage x field) the layers run in a fixed order and each keeps its own result:

    precondition  the P1 review's own gates: the model holds no value, the source is first-party, the bytes are held
    identity      M3.4A as production runs it (the P1 review's reader, unchanged), and again with the candidate rules
                  (tools/identity_rules_candidate.py); the candidate governs, the rule audit's review hold applies
    reader        sheetreader's figure for the field (identity-independent; DIAGNOSTIC where the identity is unsettled)
    statement     tools/statement_check.py: verify() after the identity, check() kept as a diagnostic only
    c6            tools/yield_layout.py: yld only, identity settled, the reader read no yield; never otherwise
    final         ACCEPTABLE_TO_NEXT_STAGE | REFUSED | CONFLICT | REVIEW_REQUIRED, with one reason code

THE CORPUS is the M3.12 P1 review (all 187 rows, data/audit/m3.12-p1-review.jsonl) and EXTRA: the multi-estate
brochure and the C6 negative documents the P1 review does not hold as rows. The audited sets are tagged from their
committed definitions: the identity refusal audit's READER_DEFECT rows (79), the figure audit's rows and positive and
negative controls (tools/test-statement-check.py) and the C6 sheets and negatives (tools/test-yield-layout.py).
"""
import ast
import collections
import contextlib
import glob
import importlib.util
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import identity_rules_candidate as IRC  # noqa: E402
import integration_application as IA  # noqa: E402
import migration_lib as L  # noqa: E402
import statement_check as S2  # noqa: E402
import yield_layout as Y  # noqa: E402

VERSION = 'integration-dryrun/1'
OUT = L.ROOT + 'data/audit/integration-dryrun.jsonl'
DOC = L.ROOT + 'docs/PHASE-INTEGRATION-DRYRUN.md'
REFUSAL_AUDIT = L.ROOT + 'data/audit/m3.12-identity-refusal-audit.jsonl'
FINAL = ('ACCEPTABLE_TO_NEXT_STAGE', 'REFUSED', 'CONFLICT', 'REVIEW_REQUIRED')
IDENTITY = ('IDENTITY_SETTLED', 'IDENTITY_REFUSED', 'IDENTITY_CONFLICTED', 'IDENTITY_REVIEW_REQUIRED')
CONFLICTING = ('MULTI_WINE_AMBIGUOUS', 'CONFLICT', 'IDENTITY_BLOCKED', 'COLOUR_AMBIGUOUS', 'ROLE_AMBIGUOUS')
BROCHURE = '05af0950a3f5001362f993dfe88c9a551ca903778bd45c91879c372177ef2cd3'  # La Gurgue / Durfort-Vivens / HBL
EXTRA = [   # (sha256, estate, wine, vintage, field, tag): claims outside the P1 rows, each named for a boundary
    (BROCHURE, 'es_00263', 'wn_00263', 2025, 'blend', 'MULTI_ESTATE_BROCHURE'),
    (BROCHURE, 'es_00277', 'wn_00277', 2025, 'blend', 'MULTI_ESTATE_BROCHURE'),
    ('5c6adcf35966ed0f4e4c7e8a76df1ab7a86d4fda7e64ebe9d9e7c64196763dad', 'es_00053', 'wn_00053', 2021, 'yld', 'C6_NEGATIVE'),
    ('987f8307609048a9186b1e743da82cd5384db7b47ca86a90a5ed8406ee54e9f3', 'es_00322', 'wn_00322', 2021, 'yld', 'C6_NEGATIVE'),
    ('2e9f05687822df9ba30443e28d53bbddaffbd7978031c27e61f0aedaa966fafa', 'es_00322', 'wn_00547', 2021, 'yld', 'C6_NEGATIVE'),
    ('e7b9f9c1ea0fbb27f2a6d20f87041590ca2219a31341496ac4da75a0c42d5951', 'es_00387', 'wn_00572', 2016, 'yld', 'C6_NEGATIVE'),
    ('650113bd6f953ffb3f2b281192cc6192a08d186f9c99a3e05c1718abd5188f3e', 'es_00224', 'wn_00224', 2024, 'yld', 'C6_NEGATIVE'),
]
BOUNDARY = {   # P1 review ids of the named boundary cases
    'ISSAN_2012': ('gs_7d6ebe9220f6', 'gs_59c7bc4f8cbd', 'gs_8ef443db52d6', 'gs_b462e5fe8a11', 'gs_041a01ed2df9',
                   'gs_37bbd1f16986'),
    'KIRWAN_2019': ('gs_eaefc0184f76', 'gs_269c6fdca3d8'),
    'CHAPELLE_1998': ('gs_ac9e56dfd0d4',),
    'PALOUMEY_2022': ('gs_29eb6d397c97',),
    'TAILLAN_2025': ('gs_b759e729fea7',),
}
TIME = collections.Counter()


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, L.ROOT + rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def literal(rel, name):
    """A module-level constant of a committed file, read without running the file."""
    for node in ast.parse(open(L.ROOT + rel, encoding='utf-8').read()).body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError((rel, name))


P1 = _load('p1_dryrun', 'tools/m312-p1-review.py')        # the P1 review: its reader, unchanged
R, V, RB = P1.R, P1.V, P1.RB
AUDITED = literal('tools/test-statement-check.py', 'AUDITED')
NEGATIVE = literal('tools/test-statement-check.py', 'NEGATIVE')
GRAND_MAYNE = literal('tools/test-yield-layout.py', 'GRAND_MAYNE')
C6_NEGATIVES = literal('tools/test-yield-layout.py', 'REAL_NEGATIVES')


@contextlib.contextmanager
def timed(k):
    t0 = time.perf_counter()
    try:
        yield
    finally:
        TIME[k] += time.perf_counter() - t0


def tags_of(rid, sha, wine, field, refusal):
    t = []
    if rid in refusal and refusal[rid]['verdict'] == 'READER_DEFECT':
        t.append('REFUSAL_AUDIT_79')
    if rid in AUDITED:
        f, v1, v2 = AUDITED[rid]
        if v1 == 'CONFIRMED':
            t.append('POSITIVE_CONTROL')
        else:
            t.append('FIGURE_AUDIT_59')
        if v1 != v2:
            t.append({'alc': 'C1_DEGRE', 'ph': 'C4_PH'}.get(f) or
                     ('C2_BLEND_DIRECTION' if v1 == 'CONTRADICTED_BY_STATEMENT' else 'C3_BLEND_HEADING'))
    if rid in NEGATIVE:
        t.append('NEGATIVE_CONTROL')
    if field == 'yld' and sha in {s for s, _ in GRAND_MAYNE.values()}:
        t.append('GRAND_MAYNE_C6')
    if field == 'yld' and sha in C6_NEGATIVES:
        t.append('C6_NEGATIVE')
    if 'clarte' in RB.fold(wine or ''):
        t.append('LA_CLARTE')
    t += [k for k, ids in BOUNDARY.items() if rid in ids]
    return t


class Layers:
    """The readers of one run: production identity, candidate identity, the figures and the bytes, all cached."""

    def __init__(self):
        with timed('setup'):
            self.prod = P1.Reader()
            self.cand = P1.Reader()
            self.trace = {}
            IRC.series()

    def close(self):
        self.prod.close()
        self.cand.close()

    def identity(self, rd, sha, e, w, y, ew):
        target = rd.claim(sha, e, w, y)
        sib = {s: rd.claim(sha, e, s, y) for s in sorted(ew[e] - {w})}
        safe_sib = sorted(s for s, c in sib.items() if c['disposition'] == 'SAFE_TO_MAP')
        d, why = target['disposition'], target['basis']
        nm = rd.cx.nm
        if d == 'SAFE_TO_MAP' and safe_sib:
            st, reason = 'IDENTITY_CONFLICTED', 'accepted for %s and for %s' % (nm.get(w), ', '.join(nm.get(s, s) for s in safe_sib))
        elif d == 'SAFE_TO_MAP':
            st, reason = 'IDENTITY_SETTLED', why
        elif safe_sib:
            st, reason = 'IDENTITY_REFUSED', 'the document is %s\'s (%s: %s)' % (', '.join(nm.get(s, s) for s in safe_sib), d, why)
        elif d in CONFLICTING:
            st, reason = 'IDENTITY_CONFLICTED', '%s: %s' % (d, why)
        else:
            st, reason = 'IDENTITY_REFUSED', '%s: %s' % (d, why)
        return {'status': st, 'disposition': d, 'reason': reason, 'rule': target['rule'], 'kind': target['kind'],
                'reader_veto': list(target['reader']), 'r1_gate': target['gate'], 'doc_type': target.get('doc_type'),
                'siblings': {s: c['disposition'] for s, c in sib.items()}}

    def both(self, sha, e, w, y, ew):
        with timed('identity_production'):
            prod = self.identity(self.prod, sha, e, w, y, ew)
        with timed('identity_candidate'):
            with IRC.applied(V.M34A) as log:
                cand = self.identity(self.cand, sha, e, w, y, ew)
            self.trace.update(log)
        tr = self.trace.get((sha[:12], w, y)) or {}
        steps = tr.get('trace') or []
        cand['rules'] = sorted({s[0] for s in steps if s[0] in ('R1', 'R1b', 'R2', 'R3', 'R4', 'R4_VETO', 'G1')})
        cand['trace'] = steps
        cand['notes'] = tr.get('notes') or []
        cand['file_series'] = tr.get('series')
        status, settled_by, held = cand['status'], None, None
        if prod['status'] == 'IDENTITY_SETTLED' and status == 'IDENTITY_SETTLED':
            settled_by = 'PRODUCTION'
        elif status == 'IDENTITY_SETTLED':
            held = IRC.held_for_review(sha, w, y)
            if held:
                status = 'IDENTITY_REVIEW_REQUIRED'
            else:
                settled_by = 'CANDIDATE_RULES'
        return {'status': status, 'settled_by': settled_by, 'review_hold': held,
                'regimes_disagree': prod['status'] != cand['status'], 'production': prod, 'candidate': cand,
                'rules_version': IRC.VERSION}


def c6_summary(res):
    out = {k: res.get(k) for k in ('status', 'failed_guard', 'reason', 'value', 'unit', 'unit_basis', 'field_basis',
                                    'arithmetic', 'guards', 'version') if k in res}
    if res.get('status') == 'READ':
        lines = res['evidence']['lines']
        out['literal'] = {'french_label': lines[0]['text'], 'english_label': lines[1]['text'],
                          'french_line': lines[2]['text'], 'english_line': lines[3]['text'], 'page': res['evidence']['page']}
        out['evidence'] = res['evidence']
    return out


def evaluate(ly, c, ctx):
    """One claim through every layer; each layer's result kept apart, the final disposition from them."""
    sha, e, w, y, f = c['sha256'], c['estate_id'], c['wine_id'], c['vintage'], c['field']
    names, ew, values, linked = ctx['names'], ctx['ew'], ctx['values'], ctx['linked']
    vt = 'vt:%s:%d' % (w, y)
    with timed('text'):
        raw, _, media = P1.text_of(sha) if sha else (None, None, None)
    pre = {'model_value': values.get((vt, f)), 'first_party': c.get('first_party'),
           'already_linked': (c.get('artifact'), vt) in linked and c.get('gap_status') != 'NOT_EXTRACTED',
           'held_text': raw is not None, 'media': media}
    if pre['model_value'] is not None:
        pre.update(status='REFUSED', reason='MODEL_HOLDS_VALUE')
    elif c['source'] != 'P1':
        pre.update(status='NOT_ASSESSED', reason='SOURCE_NOT_ASSESSED')
    elif pre['first_party'] != 'A':
        pre.update(status='REFUSED', reason='NOT_FIRST_PARTY')
    elif raw is None:
        pre.update(status='REFUSED', reason='NO_HELD_TEXT')
    else:
        pre.update(status='PASSED', reason=None)

    ident = ly.both(sha, e, w, y, ew) if raw is not None else {
        'status': 'IDENTITY_REFUSED', 'settled_by': None, 'review_hold': None, 'regimes_disagree': False,
        'production': None, 'candidate': None, 'reason': 'no held text'}
    settled = ident['status'] == 'IDENTITY_SETTLED'
    wname = ly.prod.cx.nm.get(w, '')

    reader = {'status': 'NOT_RUN', 'value': None}
    statement = {'version': S2.VERSION, 'gated': None, 'diagnostic': None, 'stated_value': None, 'statement': None,
                 'v1_reference': None}
    j = None
    if media == 'application/pdf' and raw is not None:
        with timed('reader'):
            got, how, j = ly.prod.figures(sha, e, y)
        value = got.get(f)
        refused = how.get('refused') if isinstance(how.get('refused'), dict) else {}
        reader = {'status': 'VALUE_READ' if value is not None else 'NO_VALUE', 'value': value,
                  'words': how.get(f), 'refused': refused.get(f), 'mode': 'GATED' if settled else 'DIAGNOSTIC'}
        with timed('statement'):
            sv, words = S2.stated(f, j)
            verdict, _, vwords = S2.verify(ident['candidate']['disposition'] if settled else ident['status'], f, value, j)
            statement.update(gated=verdict, stated_value=sv, statement=words,
                             diagnostic=S2.check(f, value, j)[0] if value is not None else None,
                             v1_reference=R.check(f, value, j)[0] if value is not None else None)
    elif raw is not None:
        reader['reason'] = 'a web page: the fiche reader reads PDFs only'

    c6 = {'status': 'NOT_APPLICABLE', 'reason': 'C6 is a fallback for yield only'}
    if f == 'yld':
        if media != 'application/pdf' or raw is None:
            c6 = {'status': 'NOT_ELIGIBLE', 'reason': 'not a held PDF'}
        elif reader['value'] is not None:
            c6 = {'status': 'NOT_RUN', 'reason': 'the reader read a yield (%s); C6 does not run' % reader['value']}
        else:
            others = [ly.prod.cx.nm.get(s, s) for s in sorted(ew[e] - {w})]
            with timed('pdf_bytes'):
                blob = ly.prod.pres.blob(sha)
            if settled:
                with timed('c6'):
                    c6 = c6_summary(Y.read_yield(blob, ident['candidate']['disposition'], None, y, wname, others))
            else:
                with timed('c6'):
                    diag = Y.read_yield(blob, 'SAFE_TO_MAP', None, y, wname, others)
                c6 = {'status': 'NOT_ELIGIBLE', 'reason': 'identity is %s' % ident['status'],
                      'diagnostic_if_identity_were_settled': {k: diag.get(k) for k in ('status', 'failed_guard', 'reason',
                                                                                     'value')}}

    fin = final(c, pre, ident, reader, statement, c6, media, raw, names.get(w, []), y, f)
    return {'record': 'claim', 'claim_id': c['claim_id'], 'source': c['source'], 'tags': c['tags'],
            'claim': {k: c.get(k) for k in ('review_id', 'artifact', 'sha256', 'url', 'estate_id', 'estate', 'wine_id',
                                            'wine', 'vintage', 'field')},
            'audit_refs': c['audit_refs'], 'precondition': pre, 'identity': ident, 'reader': reader,
            'statement': statement, 'c6': c6, 'final': fin, 'version': VERSION}


def final(c, pre, ident, reader, statement, c6, media, raw, names, y, f):
    def out(disp, code, why, **kw):
        return dict({'disposition': disp, 'reason_code': code, 'reason': why, 'value': None, 'unit': None,
                     'value_source': None, 'recording_path': None}, **kw)
    if pre['status'] == 'REFUSED':
        return out('REFUSED', pre['reason'], {'MODEL_HOLDS_VALUE': 'the model holds a value for the field',
                                               'NOT_FIRST_PARTY': 'the document is not on the estate\'s own domain',
                                               'NO_HELD_TEXT': 'the document holds no readable text'}[pre['reason']])
    if pre['status'] == 'NOT_ASSESSED':
        return out('REFUSED', 'SOURCE_NOT_ASSESSED', 'a claim outside the P1 review: its source admissibility is not '
                   'assessed here, so it cannot proceed whatever its layers say')
    st = ident['status']
    if st == 'IDENTITY_CONFLICTED':
        return out('CONFLICT', 'IDENTITY_CONFLICTED', ident['candidate']['reason'])
    if st == 'IDENTITY_REVIEW_REQUIRED':
        return out('REVIEW_REQUIRED', 'IDENTITY_REVIEW_REQUIRED', 'the candidate rules settle it, the rule audit held '
                   'it for review: %s' % ident['review_hold'])
    if st != 'IDENTITY_SETTLED':
        return out('REFUSED', 'IDENTITY_NOT_SETTLED', ident['candidate']['reason'])
    if pre['already_linked']:
        return out('REFUSED', 'DOCUMENT_ALREADY_LINKED', 'the document is already linked to the vintage')
    if media != 'application/pdf':
        return out('REFUSED', 'WEB_PAGE_FIGURES_NOT_READ', 'the page is the wine\'s; the fiche reader does not read a '
                   'web page\'s figures')
    sv = statement['stated_value']
    if reader['value'] is not None:
        v = statement['gated']
        if v == 'CONFIRMED':
            return out('ACCEPTABLE_TO_NEXT_STAGE', 'READER_CONFIRMED_BY_STATEMENT', 'the reader reads %s and the '
                       'document\'s statement confirms it' % f, value=reader['value'], unit=R.UNITS.get(f),
                       value_source='READER', recording_path=path(c, ident, raw, names, y, []))
        if v == 'CONTRADICTED_BY_STATEMENT':
            return out('CONFLICT', 'READER_CONTRADICTED_BY_STATEMENT', 'the reader reads %s, the statement says %s '
                       '("%s"): neither is chosen' % (reader['value'], sv, statement['statement']))
        return out('REFUSED', 'STATEMENT_NOT_FOUND', 'the reader reads %s, but the statement check does not find it '
                   'as stated' % f)
    if c6.get('status') == 'READ':
        if sv is not None and sv != c6['value']:
            return out('CONFLICT', 'LAYERS_DISAGREE', 'C6 reads %g, the statement says %s ("%s"): neither is chosen' % (
                c6['value'], sv, statement['statement']))
        return out('ACCEPTABLE_TO_NEXT_STAGE', 'C6_LAYOUT_CONFIRMED', 'the reader reads no yield; the C6 layout reads '
                   '%g, its unit derived from the layout' % c6['value'], value=c6['value'], unit=c6['unit'],
                   value_source='C6_LAYOUT', unit_basis=c6['unit_basis'],
                   recording_path=path(c, ident, raw, names, y, ['a C6 layout observation with a derived unit, which no '
                                                                 'production path records']))
    if sv is not None:
        return out('REFUSED', 'STATEMENT_STATED_VALUE_UNRESOLVED', 'the document states %s ("%s") but the reader reads '
                   'none; a statement does not make a value' % (f, statement['statement']))
    if c6.get('status') == 'REFUSED':
        return out('REFUSED', 'C6_GUARD_FAILED', 'the reader reads no yield; C6 refuses at guard %s: %s' % (
            c6['failed_guard'], c6['reason']))
    return out('REFUSED', 'VALUE_NOT_READ', 'the reader reads no %s and the document states none' % f)


def path(c, ident, raw, names, y, extra):
    """Whether the generic acceptance runner, unchanged, could record a candidate - the P1 review's acceptance_path,
    with what the candidate layers add."""
    b = []
    cand = ident['candidate']
    if cand['kind'] != 'DOCUMENT':
        b.append('a web page (the acceptance runner records documents)')
    if cand['rule'] not in P1.TEXT_RULES:
        b.append('identity not from a text rule (%s)' % cand['rule'])
    if ident['settled_by'] == 'CANDIDATE_RULES':
        b.append('identity settled by candidate rules %s, not by production' % '+'.join(cand['rules']))
    if 'R4' in cand['rules']:
        b.append('the wine named by the site\'s file listing (R4), not by the text')
    if not P1.vintage_basis(raw or '', RB.fold(raw or ''), names, y):
        b.append('no stated vintage (M3.8\'s statement or wine-and-year form)')
    b += extra
    return 'READY' if not b else 'BLOCKED: ' + '; '.join(b)


def corpus():
    p1 = [r for r in L.jsonl_lines(P1.OUT) if r.get('record') == 'review']
    refusal = {}
    for r in L.jsonl_lines(REFUSAL_AUDIT):
        for rid in r['review_ids']:
            refusal[rid] = r
    held = {(r['sha256'], r['wine_id'], r['vintage'], r['field']) for r in p1}
    names = collections.defaultdict(list)
    for n in L.read_table('identity/names.jsonl'):
        if n['kind'] == 'CURRENT':
            names[n['subject']].append(n['name'])
    disc = {a['sha256']: a for a in L.jsonl_lines(L.ROOT + 'data/discovery/artifacts.jsonl')}
    arts = {a['sha256']: a['id'] for a in L.read_table('identity/artifacts.jsonl') if a.get('sha256')}
    out = []
    for r in p1:
        out.append({'claim_id': r['review_id'], 'source': 'P1', 'review_id': r['review_id'], 'artifact': r['artifact'],
                    'sha256': r['sha256'], 'url': r['url'], 'estate_id': r['estate_id'], 'estate': r['estate'],
                    'wine_id': r['wine_id'], 'wine': r['wine'], 'vintage': r['vintage'], 'field': r['field'],
                    'first_party': r['first_party'], 'gap_status': r['gap_status'],
                    'tags': ['P1'] + tags_of(r['review_id'], r['sha256'], r['wine'], r['field'], refusal),
                    'audit_refs': {'p1_review': {'review_id': r['review_id'], 'decision': r['decision'],
                                                 'reader_status': r['reader_status'], 'reason': r['reason']},
                                   'identity_refusal_audit': ({k: refusal[r['review_id']][k] for k in ('verdict', 'class')}
                                                              if r['review_id'] in refusal else None)},
                    'p1_row': r})
    for sha, e, w, y, f, tag in EXTRA:
        assert (sha, w, y, f) not in held, ('an EXTRA claim the P1 review already holds', sha, w, y, f)
        out.append({'claim_id': 'x:%s:%s:%d:%s' % (sha[:12], w, y, f), 'source': 'EXTRA', 'review_id': None,
                    'artifact': arts.get(sha), 'sha256': sha, 'url': (disc.get(sha) or {}).get('first_url'),
                    'estate_id': e, 'estate': (names.get(e) or [e])[0], 'wine_id': w, 'wine': (names.get(w) or [w])[0],
                    'vintage': y, 'field': f, 'first_party': None, 'gap_status': None,
                    'tags': [tag] + tags_of(None, sha, (names.get(w) or [''])[0], f, refusal),
                    'audit_refs': {'p1_review': None, 'identity_refusal_audit': None}})
    for c in out:
        c['tags'] = sorted(set(c['tags']))
    return sorted(out, key=lambda c: (c['estate_id'], c['wine_id'], c['vintage'], c['field'], c['claim_id'])), names


def build_claims():
    claims, names = corpus()
    ew = collections.defaultdict(set)
    for r in L.read_table('state/estate-wine.jsonl'):
        if r.get('status') == 'ESTABLISHED':
            ew[r['estate']].add(r['wine'])
    # the model as the dry run read it: the integration application's own rows (tools/integration_application.py),
    # which this dry run's review later authorised, set aside - none exist before it is applied
    prov = {p['id']: p for p in L.read_table('cross/provenance.jsonl')}
    ctx = {'names': names, 'ew': ew,
           'values': {(c['subject'], c['field']): c['value'] for c in L.read_table('canonical/values.jsonl')
                      if not IA.is_row('canonical/values.jsonl', c, prov)},
           'linked': {(a['artifact'], a.get('vintage')) for a in L.read_table('document/attributions.jsonl')
                      if a.get('vintage') and not IA.is_row('document/attributions.jsonl', a, prov)}}
    ly = Layers()
    rows = []
    try:
        for c in claims:
            row = evaluate(ly, c, ctx)
            p = c.get('p1_row')
            if p is not None:       # production, as the P1 review committed it, reproduced - or stop
                prod = row['identity']['production']
                assert prod is None or prod['disposition'] == p['reader_status'], (c['claim_id'], prod, p['reader_status'])
                fe = p.get('field_evidence') or {}
                if fe.get('reader_value') is not None:
                    assert fe['reader_value'] == row['reader']['value'], c['claim_id']
                    assert fe['statement_check'] == row['statement']['v1_reference'], c['claim_id']
            rows.append(row)
    finally:
        ly.close()
    return rows


def statement_corpus(rows):
    """Version 1 against version 2 over every held discovery PDF, and the candidates that rest on either."""
    cnt = collections.Counter()
    refused_blend = set()
    for p in sorted(glob.glob(L.ROOT + 'sources/discovery/extracted/*.json')):
        sha = os.path.basename(p)[:-5]
        raw, _, media = P1.text_of(sha)
        if media != 'application/pdf' or not raw:
            continue
        cnt['pdfs'] += 1
        j = R.joined(raw)
        for f in ('alc', 'blend', 'ph'):
            a = R.stated(f, j)[0] if f != 'ph' else None
            b = S2.stated(f, j)[0]
            cnt['%s|%s|%s|%s' % (f, 'v1' if a is not None else '-', 'v2' if b is not None else '-',
                                 'same' if a == b else 'diff')] += 1
            if f == 'blend' and a is not None and b is None:
                refused_blend.add(sha)
    on_refused = sorted(r['claim_id'] for r in rows if r['final']['disposition'] == 'ACCEPTABLE_TO_NEXT_STAGE'
                        and r['claim']['field'] == 'blend' and r['claim']['sha256'] in refused_blend)
    in_corpus = sorted(r['claim_id'] for r in rows if r['claim']['field'] == 'blend' and r['claim']['sha256'] in refused_blend)
    return {'record': 'statement_corpus', 'counts': dict(sorted(cnt.items())),
            'blend_refused_by_v2_documents': len(refused_blend), 'blend_claims_on_them': in_corpus,
            'blend_candidates_on_them': on_refused, 'version': VERSION}


# ---- the expectations: each boundary the phase must show, as a predicate over the rows ----------------------

def expectations(rows):
    by = collections.defaultdict(list)
    for r in rows:
        for t in r['tags']:
            by[t].append(r)
    fin = lambda r: r['final']['disposition']                         # noqa: E731
    ids = lambda r: r['identity']['status']                           # noqa: E731
    out = []

    def expect(name, rs, ok, observed):
        out.append({'expectation': name, 'claims': len(rs), 'ok': bool(rs) and ok, 'observed': observed})

    def counts(rs, f):
        return dict(sorted(collections.Counter(f(r) for r in rs).items()))
    rescued = [r for r in by['REFUSAL_AUDIT_79'] if ids(r) == 'IDENTITY_SETTLED']
    st79 = collections.Counter(ids(r) for r in by['REFUSAL_AUDIT_79'])
    # the rule audit's own reconciliation of the 79: 64 settled by the rules (two of them held for review), 15 not
    expect('identity: the 79 reader-defect datapoints - the rules settle the audit\'s 64, the other 15 stay refused',
           by['REFUSAL_AUDIT_79'], len(by['REFUSAL_AUDIT_79']) == 79
           and st79['IDENTITY_SETTLED'] + st79['IDENTITY_REVIEW_REQUIRED'] == 64 and st79['IDENTITY_REFUSED'] == 15
           and all(r['identity']['settled_by'] == 'CANDIDATE_RULES' for r in rescued),
           {'status': counts(by['REFUSAL_AUDIT_79'], ids), 'rules': counts(rescued, lambda r: '+'.join(
               r['identity']['candidate']['rules']))})
    neg = [r for r in by['NEGATIVE_CONTROL']]
    expect('identity: the negative controls (Biston-Brillette 2021/2023, Jean Faure 2025, Mangot 2022) are not rescued',
           neg, all(ids(r) == 'IDENTITY_REFUSED' and fin(r) == 'REFUSED' for r in neg), counts(neg, ids))
    lc = by['LA_CLARTE']
    expect('identity: La Clarte is not resolved, whatever its figures', lc,
           all(ids(r) != 'IDENTITY_SETTLED' and fin(r) != 'ACCEPTABLE_TO_NEXT_STAGE' for r in lc), counts(lc, ids))
    ch = by['CHAPELLE_1998']
    expect('identity: Chapelle 1998 is not resolved (the rules settle it; the review hold stops it)', ch,
           all(ids(r) == 'IDENTITY_REVIEW_REQUIRED' and fin(r) == 'REVIEW_REQUIRED' for r in ch),
           {'candidate_disposition': counts(ch, lambda r: r['identity']['candidate']['disposition']), 'status': counts(ch, ids)})
    iss = by['ISSAN_2012']
    expect('identity: Issan 2012 stays unresolved (G1, the second wine named); its statements stay diagnostic', iss,
           all(ids(r) != 'IDENTITY_SETTLED' and fin(r) != 'ACCEPTABLE_TO_NEXT_STAGE' for r in iss),
           {'status': counts(iss, ids), 'g1': sum('G1' in r['identity']['candidate']['rules'] for r in iss),
            'diagnostic_confirmed': sum(r['statement']['diagnostic'] == 'CONFIRMED' for r in iss)})
    kw = by['KIRWAN_2019']
    expect('identity: Kirwan 2019 stays unresolved (the opening states 2018); its statement stays diagnostic', kw,
           all(ids(r) == 'IDENTITY_REFUSED' and fin(r) == 'REFUSED' and r['statement']['gated'] == 'NOT_EVALUATED'
               for r in kw),
           {'status': counts(kw, ids), 'diagnostic': counts(kw, lambda r: r['statement']['diagnostic'])})
    br = by['MULTI_ESTATE_BROCHURE']
    expect('identity: the multi-estate brochure belongs to no one wine', br,
           all(ids(r) != 'IDENTITY_SETTLED' and fin(r) != 'ACCEPTABLE_TO_NEXT_STAGE' for r in br),
           {'status': counts(br, ids), 'diagnostic': counts(br, lambda r: r['statement']['diagnostic'])})
    for tag, n, name in (('C1_DEGRE', 16, '"Degre N %" alcohol'), ('C2_BLEND_DIRECTION', 17, 'blend direction'),
                         ('C3_BLEND_HEADING', 1, 'Desmirail 2023 "BLEND" heading'), ('C4_PH', 3, 'Issan pH')):
        rs = by[tag]
        expect('statement v2: the %d %s cases are confirmed' % (n, name), rs,
               len(rs) == n and all(r['statement']['diagnostic'] == 'CONFIRMED' for r in rs),
               {'diagnostic': counts(rs, lambda r: r['statement']['diagnostic']), 'final': counts(rs, fin)})
    pos = by['POSITIVE_CONTROL']
    expect('statement v2: the five positive controls stay confirmed', pos,
           len(pos) == 5 and all(r['statement']['diagnostic'] == 'CONFIRMED' for r in pos), counts(pos, fin))
    asym = [r for r in rows if r['claim']['field'] == 'blend' and isinstance(r['reader']['value'], dict)
            and len(set(r['reader']['value'].values())) > 1 and r['statement']['diagnostic'] == 'CONFIRMED']
    expect('statement v2: every confirmed asymmetric blend has each grape\'s own figure', asym,
           all(r['reader']['value'] == r['statement']['stated_value'] for r in asym), len(asym))
    tl = by['TAILLAN_2025']
    expect('statement v2: Taillan 2025 (67 + 23 = 90) stays refused', tl,
           all(fin(r) == 'REFUSED' and r['statement']['stated_value'] is None for r in tl), counts(tl, lambda r: r['final']['reason_code']))
    pl = by['PALOUMEY_2022']
    expect('statement v2 / C6: Paloumey 2022 (a label, no figure) stays refused', pl,
           all(fin(r) != 'ACCEPTABLE_TO_NEXT_STAGE' and r['reader']['value'] is None for r in pl),
           counts(pl, lambda r: r['final']['reason_code']))
    gm = by['GRAND_MAYNE_C6']
    ok_gm = [r for r in gm if r['c6']['status'] == 'READ']
    expect('C6: a Grand Mayne sheet is C6-confirmed only with the identity settled and no reader yield', gm,
           all((r['c6']['status'] == 'READ') == (ids(r) == 'IDENTITY_SETTLED' and r['reader']['value'] is None) for r in gm)
           and all(r['final']['value'] == GRAND_MAYNE[r['claim']['vintage']][1] for r in ok_gm),
           {'c6': counts(gm, lambda r: r['c6']['status']), 'identity': counts(gm, ids)})
    expect('C6: every confirmed value keeps its derived-unit mark and the literal hl / ha lines', ok_gm,
           all(r['final']['unit'] == 'hl/ha' and r['final']['unit_basis'].startswith('LAYOUT_DERIVED')
               and r['c6']['literal']['french_line'].lower().endswith('hl') and r['c6']['literal']['english_line'].lower().endswith('ha')
               for r in ok_gm), len(ok_gm))
    sep = [r for r in ok_gm if r['claim']['vintage'] in (2008, 2009)]
    expect('C6: 2008 and 2009 (lines in separate text blocks) are read', sep, len(sep) == 2, len(sep))
    old = [r for r in gm if r['claim']['vintage'] == 1955]
    expect('C6: 1955 is read with its arithmetic UNAVAILABLE, nothing in its place', old,
           all(r['c6']['status'] == 'READ' and r['c6']['arithmetic']['status'] == 'UNAVAILABLE' for r in old),
           [r['c6'].get('arithmetic') for r in old])
    cn = by['C6_NEGATIVE']
    expect('C6: no known negative document is read by C6', cn, all(r['c6']['status'] != 'READ' and not (
        r['c6'].get('diagnostic_if_identity_were_settled') or {}).get('status') == 'READ' for r in cn),
           counts(cn, lambda r: '%s/%s' % (r['c6']['status'], r['c6'].get('failed_guard') or
                                            (r['c6'].get('diagnostic_if_identity_were_settled') or {}).get('failed_guard'))))
    nonyld = [r for r in rows if r['claim']['field'] != 'yld']
    expect('C6: never runs for any field but yield', nonyld, all(r['c6']['status'] == 'NOT_APPLICABLE' for r in nonyld), len(nonyld))
    unsettled = [r for r in rows if ids(r) != 'IDENTITY_SETTLED']
    expect('order: no claim without a settled identity is a candidate, a verified statement or a C6 read', unsettled,
           all(fin(r) != 'ACCEPTABLE_TO_NEXT_STAGE' and r['statement']['gated'] in (None, 'NOT_EVALUATED')
               and r['c6']['status'] != 'READ' for r in unsettled), len(unsettled))
    cands = [r for r in rows if fin(r) == 'ACCEPTABLE_TO_NEXT_STAGE']
    expect('candidates: every one has a settled identity, a source, and one value from one layer', cands,
           all(ids(r) == 'IDENTITY_SETTLED' and r['precondition']['status'] == 'PASSED' and r['final']['value'] is not None
               and (r['final']['value_source'] == 'READER') == (r['reader']['value'] is not None) for r in cands), len(cands))
    return out


# ---- the report ---------------------------------------------------------------------------------------------

def table(head, data):
    data = [tuple(row) for row in data]
    num = [bool(data) and all(isinstance(row[i], (int, float)) for row in data) for i in range(len(head))]
    return ['| ' + ' | '.join(head) + ' |', '|' + '|'.join('---:' if n else '---' for n in num) + '|'] + \
        ['| ' + ' | '.join(str(x) for x in row) + ' |' for row in data]


def layer_table(rows):
    C = collections.Counter
    ids = C(r['identity']['status'] for r in rows)
    gated = [r for r in rows if r['statement']['gated'] not in (None, 'NOT_EVALUATED', 'NOT_READ')]
    sg = C(r['statement']['gated'] for r in gated)
    unresolved = sum(r['final']['reason_code'] == 'STATEMENT_STATED_VALUE_UNRESOLVED' for r in rows)
    ran = [r for r in rows if r['c6']['status'] in ('READ', 'REFUSED')]
    c6 = C(r['c6']['status'] for r in ran)
    c6_conflict = sum(r['final']['reason_code'] == 'LAYERS_DISAGREE' for r in rows)
    fin = C(r['final']['disposition'] for r in rows)
    return [
        ('M3.4A identity (candidate rules)', len(rows), ids['IDENTITY_SETTLED'], ids['IDENTITY_REFUSED'],
         ids['IDENTITY_CONFLICTED'], ids['IDENTITY_REVIEW_REQUIRED']),
        ('Statement v2 (gated)', len(gated), sg['CONFIRMED'], sg['NOT_FOUND_AS_STATED'], sg['CONTRADICTED_BY_STATEMENT'],
         unresolved),
        ('C6 yield layout (eligible runs)', len(ran), c6['READ'], c6['REFUSED'], c6_conflict, 0),
        ('Integrated candidates', len(rows), fin['ACCEPTABLE_TO_NEXT_STAGE'], fin['REFUSED'], fin['CONFLICT'],
         fin['REVIEW_REQUIRED']),
    ]


def report(rows, sc, exp):
    C = collections.Counter
    md = ['# Integration dry-run - identity, reader, statement v2, C6', '',
          'Generated by `tools/integration-dryrun.py`; the contract is [INTEGRATION-CONTRACT.md](INTEGRATION-CONTRACT.md). '
          'A dry run: nothing in the model, the evidence store, the discovery store, the gap register or the app changed, '
          'and no evidence was accepted. Every claim, with each layer\'s own result, is in '
          '`data/audit/integration-dryrun.jsonl`.', '', '## Corpus', '']
    tags = C(t for r in rows for t in r['tags'])
    md += table(('set', 'claims'), sorted(tags.items()))
    md += ['', '## Layers', '']
    md += table(('Layer', 'Evaluated', 'Confirmed', 'Refused', 'Conflict', 'New decision needed'), layer_table(rows))
    md += ['', 'Identity: Confirmed is IDENTITY_SETTLED; New decision needed is the rule audit\'s review hold. Statement: '
           'evaluated where the identity is settled and the reader read a value; New decision needed is a statement the '
           'reader did not read. C6: evaluated where eligible (yld, identity settled, no reader yield); Conflict is C6 '
           'against a statement.', '', '## Identity: production against the candidate rules', '']
    md += table(('production', 'candidate rules', 'integration', 'claims'), [k + (v,) for k, v in sorted(C(
        ((r['identity']['production'] or {}).get('status', '-'), (r['identity']['candidate'] or {}).get('status', '-'),
         r['identity']['status']) for r in rows).items())])
    rules = C('+'.join(r['identity']['candidate']['rules']) for r in rows
              if r['identity']['settled_by'] == 'CANDIDATE_RULES')
    md += ['', 'Settled only by the candidate rules, by rule set: ' + ', '.join('%s %d' % kv for kv in sorted(rules.items())) + '.',
           '', '## Final dispositions', '']
    md += table(('disposition', 'reason', 'claims'), [k + (v,) for k, v in sorted(
        C((r['final']['disposition'], r['final']['reason_code']) for r in rows).items())])
    md += ['', '## Candidates', '']
    cands = [r for r in rows if r['final']['disposition'] == 'ACCEPTABLE_TO_NEXT_STAGE']
    md += table(('claim', 'wine', 'vintage', 'field', 'value', 'source', 'identity by', 'recording'), [
        (r['claim_id'], r['claim']['wine'], r['claim']['vintage'], r['claim']['field'],
         json.dumps(r['final']['value'], sort_keys=True) + (' ' + r['final']['unit'] if r['final']['unit'] and r['final']['value_source'] == 'C6_LAYOUT' else ''),
         r['final']['value_source'], r['identity']['settled_by'],
         'READY' if r['final']['recording_path'] == 'READY' else 'BLOCKED') for r in cands])
    blocked = C(b.strip() for r in cands if r['final']['recording_path'] != 'READY'
                for b in r['final']['recording_path'][len('BLOCKED: '):].split(';'))
    md += ['', 'What would still stop a candidate being recorded by the unchanged acceptance runner:', '']
    md += table(('blocker', 'candidates'), sorted(blocked.items()))
    held = [r for r in rows if r['identity']['status'] != 'IDENTITY_SETTLED' and (
        r['statement']['diagnostic'] == 'CONFIRMED' or (r['c6'].get('diagnostic_if_identity_were_settled') or {}).get('status') == 'READ')]
    md += ['', '## Confirmed by a later layer, stopped by the identity', '',
           'The statement or the C6 layout would confirm a value here; the identity is not settled, so the confirmation '
           'stays a diagnostic and the claim does not proceed.', '']
    md += table(('claim', 'wine', 'vintage', 'field', 'diagnostic value', 'identity', 'why'), [
        (r['claim_id'], r['claim']['wine'], r['claim']['vintage'], r['claim']['field'],
         json.dumps(r['reader']['value'] if r['reader']['value'] is not None else
                    r['c6']['diagnostic_if_identity_were_settled']['value'], sort_keys=True),
         r['identity']['status'], r['final']['reason'][:140].replace('|', '/')) for r in held])
    md += ['', '## Expectations', '']
    md += table(('expectation', 'claims', 'holds', 'observed'), [
        (e['expectation'], e['claims'], 'yes' if e['ok'] else '**NO**', json.dumps(e['observed'], ensure_ascii=False,
                                                                               sort_keys=True).replace('|', '/'))
        for e in exp])
    md += ['', '## Statement corpus (every held discovery PDF)', '']
    md += table(('field / v1 / v2 / agreement', 'documents'), [(k.replace('|', ' / '), v) for k, v in sorted(sc['counts'].items())])
    md += ['', 'Documents whose blend version 1 states and version 2 refuses: %d. Blend claims of this corpus on them: %d; '
           'candidates among them: %d.' % (sc['blend_refused_by_v2_documents'], len(sc['blend_claims_on_them']),
                                          len(sc['blend_candidates_on_them'])), '']
    return '\n'.join(md) + '\n'


def body(rows, sc):
    return ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                   for r in rows + [sc]).encode('utf-8')


def build():
    with timed('claims_total'):
        rows = build_claims()
    with timed('statement_corpus'):
        sc = statement_corpus(rows)
    exp = expectations(rows)
    return rows, sc, exp


def main():
    t0 = time.perf_counter()
    rows, sc, exp = build()
    b, md = body(rows, sc), report(rows, sc, exp).encode('utf-8')
    if '--check' in sys.argv:
        same = (open(OUT, 'rb').read() == b, open(DOC, 'rb').read() == md)
        print('jsonl %s, report %s' % tuple('identical' if s else 'DIFFERS' for s in same))
        code = 0 if all(same) else 1
    else:
        with open(OUT, 'wb') as fh:
            fh.write(b)
        with open(DOC, 'wb') as fh:
            fh.write(md)
        print('wrote', len(rows), 'claims')
        code = 0
    for r in layer_table(rows):
        print('  %-36s %4d %4d %4d %4d %4d' % r)
    bad = [e['expectation'] for e in exp if not e['ok']]
    print('expectations: %d, failing %d%s' % (len(exp), len(bad), ''.join('\n  FAIL ' + x for x in bad)))
    if '--timing' in sys.argv:
        TIME['wall'] = time.perf_counter() - t0
        print(json.dumps({k: round(v, 1) for k, v in sorted(TIME.items())}, indent=1))
    sys.exit(code or (1 if bad else 0))


if __name__ == '__main__':
    main()
