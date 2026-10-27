"""M3.5: held-document review - the Bernaleau pilot first, then the wider held population.

    python tools/m35-review.py             review; write data/audit/m3.5-held-document-review.jsonl
    python tools/m35-review.py --check     recompute and compare, byte for byte
    python tools/m35-review.py --check-all recompute once; compare the output and the report, byte for byte
    python tools/m35-review.py --report    write docs/PHASE-M3.5-HELD-DOCUMENT-REVIEW.md (also --check)

The question for every candidate: what exact estate / wine / vintage relationship does the held
document itself establish? The rubric is tools/m35_rubric.py (title identity, exact names, producer
lines, dated years, scope, colour, open decisions); a document with no title is judged by M3.4A's
rules unchanged. Populations, measured on the model as it stands now:

  BERNALEAU_PILOT   every accepted claim on a held document whose accepted decisions name both
                    Château de Braude and Château Mongravey (the group's shared media library)
  WIDER_ACCEPTED    M3.3's EXISTING_ACCEPTED_DOCUMENT items: an accepted held document for a vintage
                    with no document, on any other document
  WIDER_FETCHED     M3.3's EXISTING_FETCHED_DOCUMENT items: a fetched estate document for a vintage
                    with no document, never put to the evidence store

The pilot runs first; if any pilot document falls outside the rubric (no title, or an outcome the
rubric does not name), the review stops before the wider population. A candidate is eligible for an
attribution only when SAFE (or a shared sheet supporting both estates), an ACCEPTED decision on these
exact bytes names exactly that estate, wine and vintage, and the preflight holds. The migration
(tools/mig_m6_provenance.held_document_attributions) reads the eligible rows and nothing else.
A WRONG_EXISTING_ATTRIBUTION row records a correction proposal; no decision is changed. No figure is
read into the model; no clock, no network, no OCR.
"""
import collections
import hashlib
import importlib.util
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_gap_analysis as A  # noqa: E402
import migration_lib as L  # noqa: E402
import model_schema as S  # noqa: E402
import mig_m6_provenance as M6  # noqa: E402
import m35_rubric as RB  # noqa: E402

OUT = L.ROOT + 'data/audit/m3.5-held-document-review.jsonl'
REPORT = L.ROOT + 'docs/PHASE-M3.5-HELD-DOCUMENT-REVIEW.md'
PILOT_ESTATES = ('es_00073', 'es_00158')          # Château de Braude, Château Mongravey (identity/names.jsonl)
ROLE = {'grand': 'FIRST', 'second': 'SECOND'}
ELIGIBLE = ('SAFE_TO_ATTRIBUTE', 'BOTH_ESTATES_SUPPORTED')
FROM_M34A = {'SAFE_TO_MAP': 'SAFE_TO_ATTRIBUTE', 'ESTATE_VINTAGE_ONLY': 'WINE_AMBIGUOUS', 'CONFLICT': 'CONFLICT_REMAINS',
             'IDENTITY_BLOCKED': 'WINE_AMBIGUOUS', 'ALREADY_MAPPED': 'ALREADY_SUPPORTED', 'NOT_FOUND': 'EVIDENCE_INSUFFICIENT'}
DISPOSITIONS = ['SAFE_TO_ATTRIBUTE', 'ALREADY_SUPPORTED', 'BOTH_ESTATES_SUPPORTED', 'CONFLICT_REMAINS', 'WINE_AMBIGUOUS',
                'VINTAGE_AMBIGUOUS', 'MULTI_WINE_AMBIGUOUS', 'COLOUR_AMBIGUOUS', 'ESTATE_AMBIGUOUS', 'EVIDENCE_INSUFFICIENT',
                'WRONG_EXISTING_ATTRIBUTION', 'NOT_RELEVANT']
PILOT_OK = {'SAFE_TO_ATTRIBUTE', 'ALREADY_SUPPORTED', 'BOTH_ESTATES_SUPPORTED', 'WRONG_EXISTING_ATTRIBUTION', 'VINTAGE_AMBIGUOUS'}
FIELDS = ('alc', 'blend', 'ph', 'yld', 'oak', 'months')

_s = importlib.util.spec_from_file_location('m34a', L.ROOT + 'tools/m34a-mapping-audit.py')
M34A = importlib.util.module_from_spec(_s)
_s.loader.exec_module(M34A)
P = M34A.P


def doc_type(text, media):
    t = RB.fold(text or '')[:3000]
    if re.search(r'add to cart|ajouter au panier|\bprice\b|\bprix\b|€|quantity|quantite', t):
        return 'SHOP_PAGE'
    if re.search(r'revue de presse|\bpts\b|/100|/20\b|\bpoints\b', t) and not re.search(r'assemblage|blend|c[eé]page', t):
        return 'PRESS'
    if media == 'application/pdf' and re.search(r'assemblage|blend|c[eé]page|alcool|alcohol|\bph\b|rendement|yield', t):
        return 'TECHNICAL_SHEET'
    if media == 'application/pdf':
        return 'OTHER_PDF'
    return 'WEB_PAGE'


class Ctx:
    def __init__(self):
        self.nm = P.names()
        W = A.by_id('identity/wines.jsonl')
        self.wines_raw = W
        self.wines = {w: (self.nm.get(w, ''), W[w].get('type')) for w in W}
        self.ew = collections.defaultdict(list)
        for r in A.table('state/estate-wine.jsonl'):
            self.ew[r['estate']].append(r['wine'])
        self.blocked = M34A.open_decision_wines(self.nm)
        self.vd = A.vintage_documents((A.M35_ACTOR, A.M36B_ACTOR, A.M310B_ACTOR))     # now, as before this phase's own links and later ones
        self.vintages = {'vt:%s:%s' % (v['wine'], v['label']) for v in A.table('identity/vintages.jsonl')}
        self.arts = A.by_id('identity/artifacts.jsonl')
        self.s2a = A.sha_to_artifact()
        self.pv = A.by_id('cross/provenance.jsonl')
        self.raw, self.links = M34A.accepted_claims()
        self.decs = {M6.row_key(d): d for d in L.jsonl_lines(L.ROOT + 'data/evidence/decisions-v5.jsonl')}
        self.ln = {e['row_key']: e for e in A.table('observation/evidence-links.jsonl') if e['evidence_version'] == 5}
        self.by_art = collections.defaultdict(list)
        for rk, e in self.ln.items():
            if e.get('artifact'):
                self.by_art[e['artifact']].append(rk)
        self.gaps = {g['gap_key']: g['gap_id'] for g in L.jsonl_lines(L.ROOT + 'data/audit/data-gap-register.jsonl')}
        self.legacy = A.legacy_attr_by_artifact()
        self.canon = collections.defaultdict(set)
        for c in A.table('canonical/values.jsonl'):
            self.canon[c['subject']].add(c['field'])
        self.text = {}

    def doc(self, aid):
        if aid not in self.text:
            self.text[aid] = M34A.document_text(aid)[0]
        return self.text[aid]

    def decisions_for(self, aid, e, w, y):
        """(accepted row keys, other row keys) of the v5 decisions on this artifact for this estate+wine+vintage."""
        acc, oth = [], []
        for rk in sorted(self.by_art.get(aid, [])):
            ln, d = self.ln[rk], self.decs.get(rk)
            if not d or ln.get('estate') != e or ln.get('wine') != w:
                continue
            c = d.get('ctx') or {}
            if (c.get('target_vintage') or c.get('vintage')) != y:
                continue
            (acc if d['decision'] == 'ACCEPTED' else oth).append(rk)
        return acc, oth

    def manifest_prov(self, aid):
        return sorted({x['provenance'] for x in self.legacy.get(aid, [])
                       if (self.pv.get(x['provenance']) or {}).get('kind') == 'LEGACY_MANIFEST'})


def pilot_claims(cx):
    """Every accepted claim (artifact, estate, wine, vintage) on a document accepted for both pilot estates."""
    per = collections.defaultdict(set)
    acc = [d for d in A.decisions() if d['decision'] == 'ACCEPTED' and d['sha256'] and d['wine'] and d['vintage']]
    for d in acc:
        per[d['sha256']].add(d['estate'])
    shas = {s for s, es in per.items() if set(PILOT_ESTATES) <= es and cx.s2a.get(s)}
    return sorted({(cx.s2a[d['sha256']], d['estate'], d['wine'], int(d['vintage'])) for d in acc if d['sha256'] in shas})


def wider_items(cx, pilot_docs):
    ev, _ = P.item_evidence(P.states())
    out = collections.defaultdict(set)
    for (e, w, y), xs in ev.items():
        if cx.vd.get('vt:%s:%d' % (w, y)):
            continue                                   # documented now (incl. M3.4B)
        for x in xs:
            if x['family'] == 'EXISTING_ACCEPTED_DOCUMENT' and x['locator'] not in pilot_docs:
                out['WIDER_ACCEPTED'].add((x['locator'], e, w, y))
            elif x['family'] == 'EXISTING_FETCHED_DOCUMENT':
                out['WIDER_FETCHED'].add((x['locator'], e, w, y))
    return {k: sorted(v) for k, v in out.items()}


def review_one(cx, pop, aid, e, w, y):
    vt = 'vt:%s:%d' % (w, y)
    a = cx.arts.get(aid) or {}
    text = cx.doc(aid)
    acc, oth = cx.decisions_for(aid, e, w, y)
    row = {'population': pop, 'artifact': aid, 'sha256': a.get('sha256'), 'media_type': a.get('media_type'),
           'files': sorted({os.path.basename(p['locator']['value']) for p in A.placements_of(aid)})[:4],
           'estate': e, 'estate_name': cx.nm.get(e, e), 'wine': w, 'wine_name': cx.nm.get(w, w), 'vintage': y,
           'vintage_id': vt, 'gap_id': cx.gaps.get('VINTAGE_NO_DOCUMENT|%s' % e) if not cx.vd.get(vt) else None,
           'document_type': doc_type(text, a.get('media_type')) if text else 'NO_TEXT',
           'evidence_decisions': acc, 'other_decisions': oth, 'manifest_provenance': cx.manifest_prov(aid),
           'title': None, 'rule': None}
    # T4: the claimed year stands in the document only as a date (a press or event line), never as a vintage
    undated = '\n'.join(l for l in RB.fold(text or '').split('\n') if not RB.DATED_YEAR.search(l))
    row['claim_year_dated'] = bool(text) and y in RB.dated_years(text) and not re.search(r'(?<!\d)%d(?!\d)' % y, undated)
    if pop == 'WIDER_FETCHED':
        j = RB.judge(text, {'estate': e, 'wine': w, 'vintage': y}, cx.wines, cx.ew, cx.blocked) if text else None
        if j:
            row['title'] = j['title']
        row.update(disposition='EVIDENCE_INSUFFICIENT', rule='O1',
                   basis='no accepted evidence decision: the document was fetched but never put to the evidence store'
                   + ('; its first line reads "%s"' % ' '.join(str(x) for x in j['title'] if x) if j else ''))
        return row
    if not text:
        row.update(disposition='EVIDENCE_INSUFFICIENT', rule='M34A', basis='the document holds no readable text')
        return row
    j = RB.judge(text, {'estate': e, 'wine': w, 'vintage': y}, cx.wines, cx.ew, cx.blocked)
    if j is not None:
        row.update(title=j['title'], rule='T', disposition=j['disposition'], basis=j['basis'])
    else:
        # no title: M3.4A's rules, unchanged, on the model as it stands now
        claims = cx.raw.get(a.get('sha256'), [])
        mrow = {'vintage_id': vt, 'evidence_refs': sorted(set(cx.links.get((aid, e, w), [])))}
        disp, reason, basis, _ = M34A.decide(mrow, a, claims, e, w, y, cx.nm, cx.ew, cx.wines_raw, cx.blocked, cx.vd)
        row.update(rule='M34A', disposition=FROM_M34A.get(disp, disp), basis=basis or reason)
    if row['disposition'] == 'SAFE_TO_ATTRIBUTE' and aid in cx.vd.get(vt, []):
        row.update(disposition='ALREADY_SUPPORTED', basis='the model already links this document to %s %d' % (cx.nm.get(w), y))
    return row


def preflight(cx, r):
    """The fail-closed checks before an attribution may be proposed: [] when it may."""
    fail = []
    a = cx.arts.get(r['artifact']) or {}
    if not a or a.get('sha256') != r['sha256'] or not a.get('bytes_available'):
        fail.append('artifact: missing, or hash or held bytes differ')
    held = [L.ROOT + 'sources/' + p['locator']['value'] for p in A.placements_of(r['artifact'])
            if p['locator']['kind'] == 'LOCAL_PATH' and os.path.exists(L.ROOT + 'sources/' + p['locator']['value'])]
    if not held or any(hashlib.sha256(open(q, 'rb').read()).hexdigest() != r['sha256'] for q in held):
        fail.append('artifact: no held file re-hashes to it')
    if not r['evidence_decisions']:
        fail.append('evidence: no accepted decision for exactly this estate, wine and vintage')
    for rk in r['evidence_decisions']:
        d = cx.decs[rk]
        if d['decision'] != 'ACCEPTED' or (d.get('read') or {}).get('sha256') != r['sha256']:
            fail.append('evidence: decision not accepted on these bytes')
    roles = {(cx.decs[rk].get('ctx') or {}).get('target_role') for rk in r['evidence_decisions']}
    if len(roles) != 1 or roles - set(ROLE):
        fail.append('role: the accepted decisions give %s' % sorted(str(x) for x in roles))
    if not r['manifest_provenance']:
        fail.append('provenance: no manifest provenance for the artifact')
    if r['wine'] not in cx.ew.get(r['estate'], []) or r['vintage_id'] not in cx.vintages:
        fail.append('identity: the wine is not the estate\'s, or the vintage does not exist')
    if r['wine'] in cx.blocked:
        fail.append('open decision: %s' % cx.blocked[r['wine']])
    return fail, (ROLE.get(roles.pop()) if len(roles) == 1 else None)


def pilot_outcomes(rows):
    """Per pilot document: which of the two estates it establishes, from its rows."""
    by = collections.defaultdict(list)
    for r in rows:
        by[r['artifact']].append(r)
    out = {}
    for aid, rs in by.items():
        sup = {r['estate'] for r in rs if r['disposition'] in ('SAFE_TO_ATTRIBUTE', 'ALREADY_SUPPORTED', 'BOTH_ESTATES_SUPPORTED')}
        sup &= set(PILOT_ESTATES)
        if any(r['disposition'] not in PILOT_OK for r in rs):
            out[aid] = 'AMBIGUOUS'
        elif sup == set(PILOT_ESTATES):
            out[aid] = 'BOTH_ESTATES'
        elif sup == {'es_00073'}:
            out[aid] = 'BRAUDE_ONLY'
        elif sup == {'es_00158'}:
            out[aid] = 'MONGRAVEY_ONLY'
        else:
            out[aid] = 'NEITHER'
    return out


def build():
    cx = Ctx()
    rows = []
    pilot = [review_one(cx, 'BERNALEAU_PILOT', *k) for k in pilot_claims(cx)]
    # a shared sheet: one document establishing both pilot estates' wines for one vintage (T5)
    by = collections.defaultdict(list)
    for r in pilot:
        by[r['artifact']].append(r)
    for aid, rs in by.items():
        both = RB.shared(cx.doc(aid), [{'wine': r['wine'], 'vintage': r['vintage']} for r in rs], cx.wines)
        for r in rs:
            if r['wine'] in both:
                r.update(disposition='BOTH_ESTATES_SUPPORTED', rule='T5', basis='a shared sheet naming each wine beside %d' % r['vintage'])
    outcome = pilot_outcomes(pilot)
    no_title = sorted({r['artifact'] for r in pilot if r['rule'] != 'T'})
    stop = [a for a, o in outcome.items() if o == 'AMBIGUOUS'] + no_title
    for r in pilot:
        r['pilot_outcome'] = outcome[r['artifact']]
    rows += pilot
    pilot_docs = set(by)
    if not stop:
        for pop, items in sorted(wider_items(cx, pilot_docs).items()):
            rows += [review_one(cx, pop, *k) for k in items]
    for r in rows:
        r.setdefault('pilot_outcome', None)
        fail, role = (preflight(cx, r) if r['disposition'] in ELIGIBLE else ([], None))
        r['eligible'] = r['disposition'] in ELIGIBLE and not fail
        r['unresolved_reason'] = None if r['eligible'] else ('; '.join(fail) if fail else r['basis'])
        if r['eligible']:
            r['role'] = role
            r['attribution'] = S.hid('Attribution', r['artifact'], 'm35', r['vintage_id'])
            r['extraction_opportunity'] = sorted(set(FIELDS) - cx.canon.get(r['vintage_id'], set()))
        if r['disposition'] == 'WRONG_EXISTING_ATTRIBUTION':
            r['correction_proposal'] = {'decisions': r['evidence_decisions'], 'proposed': 'REVIEW_FOR_REFUSAL',
                                        'document_is': r['title'], 'why': r['basis']}
    rows.sort(key=lambda r: (['BERNALEAU_PILOT', 'WIDER_ACCEPTED', 'WIDER_FETCHED'].index(r['population']),
                             r['estate'], r['wine'], r['vintage'], r['artifact']))
    return rows, stop


def body(rows):
    return ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                   for r in rows).encode('utf-8')


def main():
    rows, stop = build()
    if stop:
        print('STOP: the pilot found document(s) outside the rubric: %s' % ', '.join(stop[:10]))
        sys.exit(3)
    if '--report' in sys.argv or '--check-all' in sys.argv:
        import m35_report
        text = m35_report.report(rows)
        if '--check' in sys.argv or '--check-all' in sys.argv:
            same = os.path.exists(REPORT) and open(REPORT, encoding='utf-8').read() == text
            print('docs/PHASE-M3.5-HELD-DOCUMENT-REVIEW.md ' + ('is current' if same else 'differs from a fresh run'))
            if not same or '--check-all' not in sys.argv:
                sys.exit(0 if same else 1)
        else:
            open(REPORT, 'w', encoding='utf-8', newline='\n').write(text)
            print('wrote docs/PHASE-M3.5-HELD-DOCUMENT-REVIEW.md')
            return
    b = body(rows)
    if '--check' in sys.argv or '--check-all' in sys.argv:
        same = os.path.exists(OUT) and open(OUT, 'rb').read() == b
        print('data/audit/m3.5-held-document-review.jsonl ' + ('is current' if same else 'differs from a fresh run'))
        sys.exit(0 if same else 1)
    c = collections.Counter((r['population'], r['disposition']) for r in rows)
    for k in sorted(c):
        print('%-16s %-28s %5d' % (k[0], k[1], c[k]))
    print('eligible: %d (%d vintages)' % (sum(r['eligible'] for r in rows), len({r['vintage_id'] for r in rows if r['eligible']})))
    open(OUT, 'wb').write(b)
    print('wrote data/audit/m3.5-held-document-review.jsonl')


if __name__ == '__main__':
    main()
