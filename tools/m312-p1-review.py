"""M3.12 P1 batch review: the sweep's P1 datapoints put through the existing reader, as one deterministic batch.

    python tools/m312-p1-review.py           write data/audit/m3.12-p1-review.jsonl and docs/PHASE-M3.12-P1-REVIEW.md
    python tools/m312-p1-review.py --check   recompute both and compare, byte for byte

A review, not an application: no evidence decision is written and nothing in the model, the evidence store, the
discovery store or the app changes. Each recommended decision is the reader's and the checks', for a later batch
acceptance (tools/apply-evidence-acceptance-manifest.py) and application (tools/apply-value-manifest.py) to act on.

THE INPUT is every P1 row of data/audit/public-gap-sweep.jsonl (M3.12): a missing datapoint of an existing vintage
with a held first-party document. THE READER is M3.9's, unchanged (tools/m39-evidence-review.py: judge, reader, the
R1 gate, figures and the statement check), run on the discovery store's held bytes through M3.6A's presenter. For each
document it is asked about the target wine and every other wine of the estate (a sibling it also accepts is a
competing identity). The field evidence is the fiche reader's own figure for the field, checked against the
document's statement; the vintage basis uses M3.8's vintage-statement patterns and its wine-and-year form with the
target wine's names.

DECISIONS: ACCEPT (identity SAFE_TO_MAP, no competing wine, the reader's figure CONFIRMED by the statement),
REJECT_WRONG_WINE (a sibling, not the target, is the document's wine), REJECT_NOT_FIRST_PARTY, READER_REFUSED (the
reader or its gates refuse it; the reason kept), CONFLICT (several wines or estates), DUPLICATE_EXISTING_EVIDENCE (the
model holds the value, or the document is already linked to the vintage for it), INSUFFICIENT_FIELD_EVIDENCE (the
document is the wine's, the field is not read or not confirmed - a reader-capability gap is recorded separately when
the field is stated but not read), NOT_ACTUALLY_A_VINTAGE_DOCUMENT. `acceptance_path` says whether the generic
acceptance runner, unchanged, could record it (a document, not a web page; identity from the text; a stated vintage).
"""
import collections
import importlib.util
import json
import os
import re
import sys
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import migration_lib as L  # noqa: E402

SWEEP = L.ROOT + 'data/audit/public-gap-sweep.jsonl'
OUT = L.ROOT + 'data/audit/m3.12-p1-review.jsonl'
DOC = L.ROOT + 'docs/PHASE-M3.12-P1-REVIEW.md'
EXTRACTED = L.ROOT + 'sources/discovery/extracted/'
DECISIONS = ('ACCEPT', 'REJECT_WRONG_WINE', 'REJECT_WRONG_VINTAGE', 'REJECT_NOT_FIRST_PARTY', 'READER_REFUSED', 'CONFLICT',
             'DUPLICATE_EXISTING_EVIDENCE', 'INSUFFICIENT_FIELD_EVIDENCE', 'NOT_ACTUALLY_A_VINTAGE_DOCUMENT')
SPECIAL = (('es_00450', 2022), ('es_00067', 2022), ('es_00275', 2026))   # the sweep's first-party missing-vintage leads
TEXT_RULES = {'M34A', 'T'}


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, L.ROOT + rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


R = _load('m39_p1', 'tools/m39-evidence-review.py')           # the M3.9 reader, unchanged
X, V, RB, P, WE = R.X, R.V, R.RB, R.P, R.WE


def text_of(sha):
    """(raw text, extraction, media) of a held discovery document."""
    p = EXTRACTED + sha + '.json'
    if not os.path.exists(p):
        return None, None, None
    x = json.load(open(p, encoding='utf-8'))
    if x.get('media') == 'pdf':
        t = '\n'.join(s for s in x.get('pages') or [] if isinstance(s, str))
        return (t if t.strip() and x.get('ocr') != 'NEEDED_NO_ENGINE' else None), x, 'application/pdf'
    t = '\n'.join([x.get('title') or ''] + [h.get('text') or '' for h in x.get('headings') or []] +
                  [b.get('text') or '' for b in x.get('blocks') or []])
    return (t if t.strip() else None), x, 'text/html'


def vintage_basis(raw, folded, names, y):
    """M3.8's vintage basis for year y: a vintage statement (its patterns, unchanged), else the wine's name beside
    the year; None when the document states neither."""
    for rx in P.VINTAGE_FOLDED:
        for m in rx.finditer(folded):
            if int(m.group(1)) == y:
                return 'statement "%s"' % m.group(0)
    for rx in P.VINTAGE_RAW:
        for m in rx.finditer(raw):
            if int(m.group(1)) == y:
                return 'statement "%s"' % m.group(0)
    norm = RB.norm_name(raw)
    for n in names:
        m = re.search(r'\b(%s) (%d)\b' % (re.escape(RB.norm_name(n)), y), norm)
        if m:
            return 'wine and year "%s"' % m.group(0)
    return None


class Reader:
    """The M3.9 reader over the discovery store, one claim at a time, every result cached."""

    def __init__(self):
        self.cx = V.Ctx()
        self.est = X.legacy_estates()
        self.pres = X.Presenter()
        self.cache = {}

    def close(self):
        self.pres.close()

    def claim(self, sha, e, w, y):
        k = (sha, e, w, y)
        if k in self.cache:
            return self.cache[k]
        raw, ext, media = text_of(sha)
        if raw is None:
            out = {'disposition': 'EVIDENCE_INSUFFICIENT', 'basis': 'the document holds no readable text',
                   'kind': None, 'rule': None, 'reader': ('NOT_EVALUATED', 'NO_TEXT', ''), 'gate': None, 'media': media}
            self.cache[k] = out
            return out
        folded = RB.fold(raw)
        page = WE.load(sha, L.ROOT) if media == 'text/html' else None
        if media == 'text/html' and not page:
            ev = {'kind': 'WEB_PAGE', 'disposition': 'EVIDENCE_INSUFFICIENT', 'basis': 'no structured extraction is held'}
        else:
            ev = R.judge(self.cx, {'sha256': sha, 'n': 0}, page, folded, e, w, y)
        rd = R.reader(self.pres, self.est.get(e), sha, media, self.cx.nm.get(w, ''), y)
        dated = ev.get('kind') == 'DOCUMENT' and y in RB.dated_years(raw) and not re.search(
            r'(?<!\d)%d(?!\d)' % y, '\n'.join(l for l in folded.split('\n') if not RB.DATED_YEAR.search(l)))
        if ev['disposition'] == 'SAFE_TO_MAP' and rd[0] == 'ACCEPTED':
            disp, why = 'SAFE_TO_MAP', ev['basis']
        elif ev['disposition'] == 'SAFE_TO_MAP':
            disp = X.READER_TO_DISP.get(rd[1], 'EVIDENCE_INSUFFICIENT')
            why = 'the document\'s evidence holds (%s), but the reader refuses it (%s: %s)' % (ev['basis'], rd[1], rd[2])
        else:
            disp, why = ev['disposition'], ev['basis']
        gate = None
        if disp == 'SAFE_TO_MAP':
            gate = X.r1_gate({'wine': w, 'wine_name': self.cx.nm.get(w), 'vintage': y, 'evidence_of_document': ev,
                              'reader': {'decision': rd[0], 'code': rd[1], 'why': rd[2]}, 'claim_year_dated': bool(dated)})
            if gate:
                disp, why = 'EVIDENCE_INSUFFICIENT', 'R1 gate: %s' % '; '.join(gate)
        out = {'disposition': disp, 'basis': why, 'kind': ev.get('kind'), 'rule': ev.get('rule') or
               ((ev.get('page') or {}).get('identity_source')), 'reader': rd, 'gate': gate, 'media': media,
               'doc_type': V.doc_type(folded, media)}
        self.cache[k] = out
        return out

    def figures(self, sha, e, y):
        k = ('fig', sha, e, y)
        if k not in self.cache:
            raw, _, _ = text_of(sha)
            got, how = R.figures(self.pres, self.est.get(e), sha, '', y)
            j = R.joined(raw or '')
            self.cache[k] = (got, how, j)
        return self.cache[k]


def review():
    sweep = L.jsonl_lines(SWEEP)
    p1 = [r for r in sweep if r['record'] == 'gap' and r['priority'] == 1]
    special = [r for r in sweep if r['record'] == 'missing_vintage' and (r['estate_id'], r['vintage']) in SPECIAL]
    names = collections.defaultdict(list)
    for n in L.read_table('identity/names.jsonl'):
        if n['kind'] == 'CURRENT':
            names[n['subject']].append(n['name'])
    ew = collections.defaultdict(set)
    for r in L.read_table('state/estate-wine.jsonl'):
        if r.get('status') == 'ESTABLISHED':
            ew[r['estate']].add(r['wine'])
    values = {(c['subject'], c['field']): c['value'] for c in L.read_table('canonical/values.jsonl')}
    linked = {(a['artifact'], a.get('vintage')) for a in L.read_table('document/attributions.jsonl') if a.get('vintage')}
    arts = {a['id']: a for a in L.read_table('identity/artifacts.jsonl')}
    disc = {a['sha256']: a for a in L.jsonl_lines(L.ROOT + 'data/discovery/artifacts.jsonl')}
    by_art = collections.defaultdict(set)                  # artifact -> the wines it is a P1 candidate for
    for r in p1:
        by_art[r['candidate_artifact']].add(r['wine_id'])
    rd = Reader()
    rows = []
    try:
        for r in sorted(p1, key=lambda r: (r['estate_id'], r['wine_id'], r['vintage'], r['field'])):
            e, w, y, f, aid = r['estate_id'], r['wine_id'], r['vintage'], r['field'], r['candidate_artifact']
            sha = (arts.get(aid) or {}).get('sha256')
            vt = 'vt:%s:%d' % (w, y)
            claim = r['candidate_claim'] or ''
            wine_established = 'wine EXACT' in claim or r['gap_status'] == 'NOT_EXTRACTED'
            target = rd.claim(sha, e, w, y)
            siblings = {s: rd.claim(sha, e, s, y) for s in sorted(ew[e] - {w})}
            safe_sib = sorted(s for s, c in siblings.items() if c['disposition'] == 'SAFE_TO_MAP')
            raw, _, media = text_of(sha)
            basis = vintage_basis(raw or '', RB.fold(raw or ''), names.get(w, []), y) if raw else None
            competing = sorted(names.get(s, [s])[0] for s in safe_sib)
            klass = 'P1-C' if (len(by_art[aid]) > 1 or safe_sib or 'AMBIGUOUS' in claim) else \
                'P1-A' if wine_established else 'P1-B'
            fig = {'reader_value': None, 'statement_check': None, 'stated_value': None, 'statement': None}
            capability = None
            if (vt, f) in values:
                decision, reason = 'DUPLICATE_EXISTING_EVIDENCE', 'the model now holds %s for %s' % (f, vt)
            elif r['candidate_source_tier'] != 'A':
                decision, reason = 'REJECT_NOT_FIRST_PARTY', 'the document is not on the estate\'s own domain'
            elif target['disposition'] == 'SAFE_TO_MAP' and safe_sib:
                decision, reason = 'CONFLICT', 'the reader accepts it for %s and for %s' % (
                    names[w][0], ', '.join(competing))
            elif target['disposition'] == 'SAFE_TO_MAP':
                if (aid, vt) in linked and r['gap_status'] != 'NOT_EXTRACTED':
                    decision, reason = 'DUPLICATE_EXISTING_EVIDENCE', 'the document is already linked to %s' % vt
                elif media != 'application/pdf':
                    decision = 'INSUFFICIENT_FIELD_EVIDENCE'
                    reason = 'the page is the wine\'s; the fiche reader does not read a web page\'s figures'
                    capability = 'WEB_PAGE_FIGURES_NOT_READ'
                else:
                    got, how, j = rd.figures(sha, e, y)
                    sv, words = R.stated(f, j)
                    fig['stated_value'], fig['statement'] = sv, words
                    if f in got:
                        verdict, sv2, words2 = R.check(f, got[f], j)
                        fig.update(reader_value=got[f], statement_check=verdict, reader_words=how.get(f))
                        if verdict == 'CONFIRMED':
                            decision, reason = 'ACCEPT', 'the reader reads %s and the document\'s statement confirms it' % f
                        elif verdict == 'CONTRADICTED_BY_STATEMENT':
                            decision, reason = 'INSUFFICIENT_FIELD_EVIDENCE', 'the reader\'s %s is contradicted by the ' \
                                'document\'s statement (%s)' % (f, words2)
                        else:
                            decision, reason = 'INSUFFICIENT_FIELD_EVIDENCE', 'the reader reads %s, but the statement ' \
                                'check does not find it as stated' % f
                    else:
                        decision = 'INSUFFICIENT_FIELD_EVIDENCE'
                        refused = (how.get('refused') or {}) if isinstance(how.get('refused'), dict) else {}
                        if sv is not None:
                            reason = 'the document states %s (%s); the reader does not read it%s' % (
                                f, words, ' (%s)' % refused.get(f) if refused.get(f) else '')
                            capability = 'STATED_NOT_READ'
                        else:
                            reason = 'the reader reads no %s in the document%s; the crawl\'s harvest labels one' % (
                                f, ' (refused: %s)' % refused.get(f) if refused.get(f) else '')
                            capability = 'HARVESTED_NOT_READ'      # the sweep's P1 rule: the harvest carries the label
            else:
                d, why = target['disposition'], target['basis']
                titled = re.search(r'the title is "[^"]*" \((wn_\d+)\)', why or '')
                if any(siblings[s]['disposition'] == 'SAFE_TO_MAP' for s in siblings):
                    decision = 'REJECT_WRONG_WINE'
                    reason = 'the document is %s\'s, not %s\'s (%s)' % (', '.join(competing), names[w][0], why)
                elif titled and titled.group(1) != w:
                    decision, reason = 'REJECT_WRONG_WINE', '%s: %s' % (d, why)
                elif re.search(r'news article|press|a shop listing', why or '', re.I):
                    decision, reason = 'NOT_ACTUALLY_A_VINTAGE_DOCUMENT', '%s: %s' % (d, why)
                elif d in ('MULTI_WINE_AMBIGUOUS', 'CONFLICT', 'IDENTITY_BLOCKED', 'COLOUR_AMBIGUOUS', 'ROLE_AMBIGUOUS'):
                    decision, reason = 'CONFLICT', '%s: %s' % (d, why)
                elif d == 'NOT_RELEVANT' and target.get('doc_type') not in ('TECHNICAL_SHEET',):
                    decision, reason = 'NOT_ACTUALLY_A_VINTAGE_DOCUMENT', '%s (%s): %s' % (d, target.get('doc_type'), why)
                else:
                    decision, reason = 'READER_REFUSED', '%s: %s' % (d, why)
            path = None
            if decision == 'ACCEPT':
                blockers = []
                if target['kind'] != 'DOCUMENT':
                    blockers.append('a web page (the acceptance runner records documents)')
                if target['rule'] not in TEXT_RULES:
                    blockers.append('identity not from a text rule (%s)' % target['rule'])
                if not basis:
                    blockers.append('no stated vintage (M3.8\'s statement or wine-and-year form)')
                path = 'READY' if not blockers else 'BLOCKED: ' + '; '.join(blockers)
            url = (disc.get(sha) or {}).get('first_url') or r['candidate_url']
            rows.append({
                'record': 'review', 'review_id': r['sweep_id'], 'review_class': klass,
                'estate_id': e, 'estate': r['estate'], 'wine_id': w, 'wine': r['wine'], 'vintage': y, 'field': f,
                'artifact': aid, 'sha256': sha, 'url': url, 'domain': urlparse(url or '').netloc.lower(),
                'first_party': r['candidate_source_tier'], 'gap_status': r['gap_status'],
                'existing_provenance': r['existing_provenance'], 'existing_value': values.get((vt, f)),
                'wine_identity': {'established_by_record': wine_established, 'sweep_claim': claim,
                                  'reader': target['disposition'], 'basis': target['basis'], 'rule': target['rule'],
                                  'reader_veto': list(target['reader']), 'r1_gate': target['gate']},
                'competing_identity': {'siblings': {s: siblings[s]['disposition'] for s in siblings},
                                       'accepted_for': competing, 'also_p1_for': sorted(by_art[aid] - {w})},
                'vintage_evidence': basis, 'document_type': target.get('doc_type'), 'media': target['media'],
                'field_evidence': fig, 'reader_status': target['disposition'], 'capability_gap': capability,
                'decision': decision, 'reason': reason, 'acceptance_path': path})
        specials = []
        for s in sorted(special, key=lambda s: (s['estate_id'], s['vintage'])):
            e, y = s['estate_id'], s['vintage']
            sha = (arts.get(s['candidate_artifact']) or {}).get('sha256')
            res = {w: rd.claim(sha, e, w, y)['disposition'] for w in sorted(ew[e])} if sha else {}
            specials.append({'record': 'new_vintage_lead', 'estate_id': e, 'estate': s['estate'], 'vintage': y,
                             'artifact': s['candidate_artifact'], 'url': s['candidate_url'], 'reader': res,
                             'workflow': 'acquisition -> review -> evidence acceptance -> V1 existence attribution and '
                                         'vintage creation -> M3.11 values; not part of this batch'})
    finally:
        rd.close()
    return rows, specials


def body(rows):
    return ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                   for r in rows).encode('utf-8')


def report(rows, specials):
    C = collections.Counter
    out = []
    a = out.append

    def table(head, data):
        a('| ' + ' | '.join(head) + ' |')
        a('|' + '|'.join('---:' if h in ('N', 'datapoints', 'documents') else '---' for h in head) + '|')
        for r in data:
            a('| ' + ' | '.join(str(x).replace('|', '/').replace('\n', ' ') for x in r) + ' |')
        a('')
    acc = [r for r in rows if r['decision'] == 'ACCEPT']
    ready = [r for r in acc if r['acceptance_path'] == 'READY']
    a('# Phase M3.12 — P1 batch review\n')
    a('Generated by `python tools/m312-p1-review.py` (`data/audit/m3.12-p1-review.jsonl`); never edited by hand. **A '
      'review, not an application:** no evidence decision was written; the model, the evidence store, the discovery '
      'store and the app are unchanged. The reader is M3.9\'s, unchanged.\n')
    a('## 1. The batch\n')
    a('%d P1 datapoints from the M3.12 sweep, on %d documents, %d wines, %d vintages.\n' % (
        len(rows), len({r['artifact'] for r in rows}), len({r['wine_id'] for r in rows}),
        len({(r['wine_id'], r['vintage']) for r in rows})))
    table(['review class', 'N'], sorted(C(r['review_class'] for r in rows).items()))
    a('P1-A: the record already establishes the document\'s wine; P1-B: the wine is for the reader to confirm; P1-C: the '
      'same document is a P1 lead for several wines, a sibling is also accepted, or the record is ambiguous.\n')
    a('## 2. Decisions\n')
    table(['decision', 'N', 'P1-A', 'P1-B', 'P1-C'], [
        (d, n) + tuple(sum(1 for r in rows if r['decision'] == d and r['review_class'] == k) for k in ('P1-A', 'P1-B', 'P1-C'))
        for d, n in sorted(C(r['decision'] for r in rows).items(), key=lambda kv: -kv[1])])
    a('## 3. What is eligible for later application\n')
    table(['measure', 'N'], [
        ('candidates reviewed', len(rows)),
        ('accepted (the reader\'s figure confirmed by the statement)', len(acc)),
        ('... of which the generic acceptance path can record unchanged (READY)', len(ready)),
        ('... of which blocked on the acceptance path', len(acc) - len(ready)),
        ('rejected (wrong wine, wrong vintage, not first-party, not a vintage document)',
         sum(1 for r in rows if r['decision'].startswith('REJECT') or r['decision'] == 'NOT_ACTUALLY_A_VINTAGE_DOCUMENT')),
        ('conflicted', sum(1 for r in rows if r['decision'] == 'CONFLICT')),
        ('reader-refused', sum(1 for r in rows if r['decision'] == 'READER_REFUSED')),
        ('duplicate', sum(1 for r in rows if r['decision'] == 'DUPLICATE_EXISTING_EVIDENCE')),
        ('insufficient field evidence', sum(1 for r in rows if r['decision'] == 'INSUFFICIENT_FIELD_EVIDENCE')),
        ('... of which a reader-capability gap (stated, not read; or a web page)', sum(1 for r in rows if r['capability_gap'])),
        ('**datapoints eligible for later application (ACCEPT and READY)**', len(ready)),
        ('documents involved in those', len({r['artifact'] for r in ready})),
        ('wines / vintages affected', '%d / %d' % (len({r['wine_id'] for r in ready}),
                                                   len({(r['wine_id'], r['vintage']) for r in ready}))),
    ])
    a('No gap is reduced by this review: a value counts only once it is accepted and applied.\n')
    a('## 4. Reader refusals, by reason\n')
    reasons = C(r['reason'].split(':')[0] for r in rows if r['decision'] == 'READER_REFUSED')
    table(['reader outcome', 'N'], reasons.most_common())
    a('## 5. Reader-capability gaps (for proposal C)\n')
    table(['gap', 'field', 'N'], [k + (n,) for k, n in sorted(
        C((r['capability_gap'], r['field']) for r in rows if r['capability_gap']).items())])
    a('## 6. Accepted datapoints\n')
    table(['estate', 'wine', 'vintage', 'field', 'value', 'document', 'acceptance path'],
          [(r['estate'], r['wine'], r['vintage'], r['field'], json.dumps(r['field_evidence']['reader_value'], ensure_ascii=False),
            r['url'].rsplit('/', 1)[-1][:50], r['acceptance_path']) for r in acc])
    a('## 7. New-vintage leads (separate; not in this batch)\n')
    a('Kept out of the field batch: a vintage is created only through V1 on an accepted decision. The reader\'s view of '
      'each, for the estate\'s wines:\n')
    table(['estate', 'year', 'document', 'reader by wine'], [
        (s['estate'], s['vintage'], (s['url'] or '').rsplit('/', 1)[-1], '; '.join('%s %s' % kv for kv in s['reader'].items()))
        for s in specials])
    return ('\n'.join(out) + '\n').encode('utf-8')


def main():
    rows, specials = review()
    b, doc = body(rows + specials), report(rows, specials)
    if '--check' in sys.argv:
        bad = [p[len(L.ROOT):] for p, x in ((OUT, b), (DOC, doc)) if not os.path.exists(p) or open(p, 'rb').read() != x]
        print('M3.12 P1 review ' + ('is current' if not bad else 'differs: %s' % bad))
        sys.exit(1 if bad else 0)
    open(OUT, 'wb').write(b)
    open(DOC, 'wb').write(doc)
    print('%s written (%d review row(s), %d new-vintage lead(s)); %s written' % (
        OUT[len(L.ROOT):], len(rows), len(specials), DOC[len(L.ROOT):]))


if __name__ == '__main__':
    main()
