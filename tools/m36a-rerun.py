"""M3.6A, run again from scratch after the controlled web-page rule update (0564fcb) - audit only.

    python tools/m36a-rerun.py             write data/audit/m3.6a-rerun-held-document-proposals.jsonl and
                                           data/audit/m3.6a-rerun-evidence-corrections.jsonl
    python tools/m36a-rerun.py --check     recompute both and compare, byte for byte
    python tools/m36a-rerun.py --check-all recompute once; compare the output and the report, byte for byte
    python tools/m36a-rerun.py --report    write docs/PHASE-M3.6A-RERUN.md (also --check)

PART 1 - the fetched estate documents, recalculated on the model as it stands: M3.3's
EXISTING_FETCHED_DOCUMENT items for a vintage with no document. Each candidate (document, estate,
wine, vintage) is judged by the evidence of its own kind:

  a web page   tools/web_evidence.judge_page on the page's stored structure (its headings and blocks):
               page type, main-heading identity, content region, excluded regions, vintage source,
               ambiguity reason. Never its flattened text, tab title, URL, file, folder or domain.
  a PDF        tools/m35_rubric.py, and a document with no title by M3.4A's rules - as proven in M3.5.

The v5 reader (tools/sheetreader.whose_sheet, unmodified, called as tools/evidence-wines.py calls it,
on the held bytes presented as it reads files, in a temporary directory never named in any output)
is a veto, never a basis: SAFE_TO_MAP needs the document's own evidence AND no objection from the
reader. A reader acceptance the evidence rejects is recorded as a reader false positive with its
class. Every SAFE_TO_MAP is then held to the R1 gate: a WINE_DOCUMENT whose main heading is the
model wine's exact name, its vintage from the heading or a labelled field, nothing from an excluded
region - any other acceptance is a new false-positive class, and the audit stops.

PART 2 - the accepted claims M3.5 found wrong (its correction proposals), each examined again on the
document's own words. Nothing is corrected: the decision store is only read.

No clock, no network, no OCR; the model, the evidence store and the app are only read.
"""
import collections
import functools
import gzip
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_gap_analysis as A  # noqa: E402
import migration_lib as L  # noqa: E402
import m35_rubric as RB  # noqa: E402
import web_evidence as WE  # noqa: E402

# norm_name is pure, and the rubric and the page rules ask it of the same names millions of times: remembered
# here, from outside their files, whose bytes are fingerprinted and stay as they are
RB.norm_name = functools.lru_cache(maxsize=1 << 17)(RB.norm_name)

PROPOSALS =L.ROOT + 'data/audit/m3.6a-rerun-held-document-proposals.jsonl'
CORRECTIONS = L.ROOT + 'data/audit/m3.6a-rerun-evidence-corrections.jsonl'
REPORT = L.ROOT + 'docs/PHASE-M3.6A-RERUN.md'
BLOCKED_RUN = L.ROOT + 'data/audit/m3.6a-blocked-run-summary.json'
BLOBS = L.ROOT + 'sources/discovery/blobs/'
FIELDS = ('alc', 'blend', 'ph', 'yld', 'oak', 'months')
DISPOSITIONS = ['SAFE_TO_MAP', 'ALREADY_SUPPORTED', 'ESTATE_ONLY', 'WINE_AMBIGUOUS', 'VINTAGE_AMBIGUOUS',
                'MULTI_WINE_AMBIGUOUS', 'COLOUR_AMBIGUOUS', 'ROLE_AMBIGUOUS', 'EVIDENCE_INSUFFICIENT',
                'IDENTITY_BLOCKED', 'CONFLICT', 'NOT_RELEVANT']
CATEGORIES = ['WRONG_ESTATE', 'WRONG_WINE', 'WRONG_VINTAGE', 'WRONG_COLOUR', 'ESTATE_ONLY_NOT_WINE',
              'MULTI_WINE_UNRESOLVED', 'PRODUCER_LINE_FALSE_POSITIVE', 'TITLE_FALSE_POSITIVE', 'DATE_FALSE_POSITIVE',
              'IDENTITY_BLOCKED', 'CONFLICT', 'OTHER_REVIEW_REQUIRED']
ACTIONS = ['RETAIN_AS_HISTORICAL_ACCEPTANCE_BUT_FLAG', 'SUPERSEDE_WITH_CORRECTED_DECISION', 'WITHDRAW_ACCEPTANCE',
           'LEAVE_CONFLICT_OPEN', 'REVIEW_REQUIRED']
# the false-positive classes already named: M3.5's (its report, section 4) and R1's (tools/web_evidence.py)
KNOWN_CLASSES = {
    'T1_HEADING_AS_TITLE': 'section heading mistaken for title',
    'T3_PRODUCER_LINE': 'producer line mistaken for wine identity',
    'T4_DATE_AS_VINTAGE': 'date inside the document mistaken for vintage',
    'T4_PRESS_YEAR': 'press-guide year mistaken for vintage',
    'ESTATE_ONLY': 'exact estate name insufficient to establish the grand vin',
    'T5_MULTI_WINE': 'multiple wines in one document',
    'T2_SIMILAR_NAME': 'wrong wine with a similar name, or another wine or vintage\'s own page',
    'ROLE_SECOND': 'second or third wine mistaken for the grand vin',
    'T6_COLOUR': 'colour ambiguity',
    'MULTI_VINTAGE': 'multiple vintages in one document',
    'R1_SITE_NAME': 'site or estate name in the tab title or a heading separator (an estate-wide page)',
    'R1_EXCLUDED_REGION': 'sidebar, related product, recommendation or list region',
    'R1_ARCHIVE_LISTING': 'archive, listing or pagination page',
    'R1_GREETING_EVENT': 'greeting or event page',
    'R1_RANGE': 'multi-wine range page',
    'R1_NEWS': 'news article whose heading is not the wine\'s exact name',
    'R1_NO_IDENTITY': 'page whose main heading establishes no wine',
    'IDENTITY_BLOCKED': 'open identity decision',
}

_s = importlib.util.spec_from_file_location('m35', L.ROOT + 'tools/m35-review.py')
V = importlib.util.module_from_spec(_s)
_s.loader.exec_module(V)
M34A, P = V.M34A, V.P
_e = importlib.util.spec_from_file_location('ev', L.ROOT + 'tools/evidence.py')
EV = importlib.util.module_from_spec(_e)
_e.loader.exec_module(EV)
import sheetreader as SR  # noqa: E402


def sha12(rel):
    return hashlib.sha256(open(L.ROOT + rel, 'rb').read()).hexdigest()[:12]


def fingerprints():
    readers = collections.Counter(d.get('reader') for d in L.jsonl_lines(L.ROOT + 'data/evidence/decisions-v5.jsonl'))
    return {'reader': EV.reader_fingerprint(), 'reader_of_v5_decisions': sorted(readers), 'decider_version_v5': 5,
            'web_rules': sha12('tools/web_evidence.py'), 'rubric': sha12('tools/m35_rubric.py'),
            'm34a_rules': sha12('tools/m34a-mapping-audit.py'), 'model_contract': sha12('tools/model_schema.py'),
            'model_contract_file': json.load(open(L.MODEL + 'manifest.json', encoding='utf-8')).get('contract'),
            'evidence_schema': 'decisions-v5 (row_key as tools/evidence.py)'}


# -- the reader, as a veto: the held bytes presented as it reads files -----------------------------

class Presenter:
    def __init__(self):
        self.dir = tempfile.mkdtemp(prefix='m36a-')
        self.disc = {a['sha256']: a for a in L.jsonl_lines(L.ROOT + 'data/discovery/artifacts.jsonl')}

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def blob(self, sha):
        for p in (BLOBS + sha[:2] + '/' + sha, BLOBS + sha[:2] + '/' + sha + '.gz'):
            if os.path.exists(p):
                b = open(p, 'rb').read()
                return gzip.decompress(b) if p.endswith('.gz') else b
        return None

    def present(self, sha, media):
        d = self.disc.get(sha) or {}
        url = d.get('first_url') or ''
        base = os.path.basename(urlparse(url).path.rstrip('/')) or 'index'
        sub = os.path.join(self.dir, sha[:16])
        os.makedirs(sub, exist_ok=True)
        if media == 'application/pdf':
            b = self.blob(sha)
            if not b or hashlib.sha256(b).hexdigest() != sha:
                return None, 'the held bytes are missing or do not hash to the artifact'
            fn = base if base.lower().endswith('.pdf') else base + '.pdf'
            p = os.path.join(sub, fn)
            open(p, 'wb').write(b)
            return p, fn
        ex = L.ROOT + 'sources/discovery/extracted/' + sha + '.json'
        if not os.path.exists(ex):
            return None, 'no extraction held for the page'
        x = json.load(open(ex, encoding='utf-8'))
        lines = [url, x.get('title') or '']
        lines += [h.get('text') or '' for h in x.get('headings') or []]
        lines += [b.get('text') or '' for b in x.get('blocks') or []]
        fn = base + '.txt'
        p = os.path.join(sub, fn)
        io.open(p, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
        return p, fn


def legacy_estates():
    E = SR.estates(L.ROOT)
    out = {}
    for r in A.table('identity/identity-map.jsonl'):
        if r['namespace'] == 'estate' and r.get('stable_id') and r['legacy_key'] in E:
            out.setdefault(r['stable_id'], (r['legacy_key'], E[r['legacy_key']]))
    return out


def reader_verdict(pres, est, sha, media, wname, y):
    if not est:
        return 'NOT_EVALUATED', 'NO_ESTATE_FOR_READER', 'the reader has no record for the estate'
    _, e = est
    role = {e.get('name'): 'grand', e.get('second'): 'second'}.get(wname)
    if role is None:
        return 'NOT_EVALUATED', 'GUARD_HAS_NO_CUVEE_MODE', 'the reader has no mode for %s' % wname
    path, fn = pres.present(sha, media)
    if not path:
        return 'NOT_EVALUATED', 'NOT_PRESENTABLE', fn
    try:
        v = SR.whose_sheet(path, fn, e.get('name'), e.get('cuvees') or (), e.get('second'), e.get('cat'),
                           year=y, is_second=(role == 'second'))
    except Exception as ex:
        v = {'why': 'a guard could not read it: %s' % type(ex).__name__}
    if v:
        code, why = EV.code_for(v.get('why'))
        return 'REFUSED', code, why
    return 'ACCEPTED', 'ACCEPTED', ''


READER_TO_DISP = {'WRONG_VINTAGE': 'VINTAGE_AMBIGUOUS', 'SECOND_WINE': 'ROLE_AMBIGUOUS', 'OTHER_WINE': 'WINE_AMBIGUOUS',
                  'WRONG_COLOUR': 'COLOUR_AMBIGUOUS', 'PRESS': 'NOT_RELEVANT', 'DOSSIER': 'NOT_RELEVANT',
                  'OTHER_CHATEAU': 'NOT_RELEVANT'}


# -- the document's own evidence --------------------------------------------------------------------

class Judge:
    def __init__(self, cx):
        self.cx = cx
        self.estate_names = sorted(v for k, v in cx.nm.items() if k.startswith('es_'))

    def web(self, sha, e, w, y):
        ext = WE.load(sha, L.ROOT)
        if not ext:
            return {'kind': 'WEB_PAGE', 'disposition': 'EVIDENCE_INSUFFICIENT', 'basis': 'no structured extraction is held for the page',
                    'page': None}
        j = WE.judge_page(ext, {'estate': e, 'wine': w, 'vintage': y}, self.cx.wines, self.cx.ew, self.cx.blocked,
                          self.estate_names)
        return {'kind': 'WEB_PAGE', 'disposition': j['disposition'], 'basis': j['basis'],
                'page': {k: j[k] for k in ('page_type', 'page_type_basis', 'identity_source', 'identity', 'identity_region',
                                           'vintage_source', 'excluded_region_match', 'ambiguity_reason')}}

    def document(self, aid, e, w, y):
        cx = self.cx
        text = cx.doc(aid)
        if not text:
            return {'kind': 'DOCUMENT', 'disposition': 'EVIDENCE_INSUFFICIENT', 'basis': 'the document holds no readable text',
                    'rule': 'M34A', 'title': None}
        j = RB.judge(text, {'estate': e, 'wine': w, 'vintage': y}, cx.wines, cx.ew, cx.blocked)
        if j is not None:
            d = j['disposition']
            m = ('IDENTITY_BLOCKED' if d == 'WINE_AMBIGUOUS' and 'open identity decision' in j['basis'] else
                 'NOT_RELEVANT' if d == 'WRONG_EXISTING_ATTRIBUTION' else 'SAFE_TO_MAP' if d == 'SAFE_TO_ATTRIBUTE' else d)
            return {'kind': 'DOCUMENT', 'disposition': m, 'basis': j['basis'], 'rule': 'T', 'title': j['title']}
        a = cx.arts.get(aid) or {}
        mrow = {'vintage_id': 'vt:%s:%d' % (w, y), 'evidence_refs': ['(the document text; no decision)']}
        disp, reason, basis, _ = M34A.decide(mrow, a, [], e, w, y, cx.nm, cx.ew, cx.wines_raw, cx.blocked, cx.vd)
        m = {'ESTATE_VINTAGE_ONLY': 'ESTATE_ONLY', 'ALREADY_MAPPED': 'ALREADY_SUPPORTED',
             'NOT_FOUND': 'EVIDENCE_INSUFFICIENT'}.get(disp, disp)
        return {'kind': 'DOCUMENT', 'disposition': m, 'basis': basis or reason, 'rule': 'M34A', 'title': None}


def fp_class(ev, dated):
    """The class of a reader acceptance the document's evidence rejects."""
    d, b = ev['disposition'], ev['basis'] or ''
    page = ev.get('page') or {}
    pt = page.get('page_type')
    if d == 'IDENTITY_BLOCKED':
        return 'IDENTITY_BLOCKED'
    if pt == 'ESTATE_PAGE':
        return 'R1_SITE_NAME' if (page.get('identity') or {}).get('site_suffix') else 'ESTATE_ONLY'
    if pt in ('ARCHIVE_PAGE', 'LISTING_PAGE'):
        return 'R1_ARCHIVE_LISTING'
    if pt == 'GREETING_EVENT_PAGE':
        return 'R1_GREETING_EVENT'
    if pt == 'RANGE_PAGE':
        return 'R1_RANGE'
    if pt == 'NEWS_ARTICLE':
        return 'R1_NEWS'
    if pt == 'OTHER_WEB_PAGE':
        return 'R1_EXCLUDED_REGION' if page.get('excluded_region_match') else 'R1_NO_IDENTITY'
    if dated:
        return 'T4_PRESS_YEAR' if re.search(r'guide|revue|pts|points', b) else 'T4_DATE_AS_VINTAGE'
    if d == 'ESTATE_ONLY' or 'not the wine' in b:
        return 'ESTATE_ONLY'
    if d == 'MULTI_WINE_AMBIGUOUS':
        return 'T5_MULTI_WINE'
    if d == 'COLOUR_AMBIGUOUS':
        return 'T6_COLOUR'
    if d == 'ROLE_AMBIGUOUS' or 'second' in b or 'autre vin' in b or 'other wine' in b:
        return 'ROLE_SECOND'
    if d == 'VINTAGE_AMBIGUOUS':
        return 'T4_DATE_AS_VINTAGE' if 'calendar date' in b or 'date' in b else 'MULTI_VINTAGE'
    if d == 'NOT_RELEVANT':
        return 'T2_SIMILAR_NAME'
    if d == 'WINE_AMBIGUOUS':
        return 'ESTATE_ONLY'
    if d == 'EVIDENCE_INSUFFICIENT':
        return 'R1_NO_IDENTITY' if pt else 'ESTATE_ONLY'
    return 'UNCLASSIFIED'


def r1_gate(row):
    """[] when a SAFE_TO_MAP rests only on evidence R1 allows; otherwise what it rests on instead."""
    ev = row['evidence_of_document']
    bad = []
    if ev['kind'] == 'WEB_PAGE':
        page = ev['page'] or {}
        ident = page.get('identity') or {}
        if page.get('page_type') != 'WINE_DOCUMENT':
            bad.append('not a wine document (%s)' % page.get('page_type'))
        if page.get('identity_source') != 'h1':
            bad.append('identity not from the visible main heading')
        if RB.norm_name(row['wine_name']) != ident.get('name'):
            bad.append('the main heading is not the wine\'s exact name')
        if page.get('vintage_source') not in ('main heading', 'labelled field in the content'):
            bad.append('vintage not from the heading or a labelled field')
        if ident.get('year') not in (None, row['vintage']):
            bad.append('the heading states another year')
    else:
        if ev.get('rule') not in ('T', 'M34A'):
            bad.append('no rule decided it')
    if row['claim_year_dated']:
        bad.append('the year stands only in a dated line')
    return bad


def population(cx):
    ev, _ = P.item_evidence(P.states())
    vd = A.vintage_documents((A.M36B_ACTOR, A.M310B_ACTOR))      # the model as this audit read it: before M3.6B's own links and later ones
    every, out, removed = set(), set(), set()
    for (e, w, y), xs in ev.items():
        for x in xs:
            if x['family'] != 'EXISTING_FETCHED_DOCUMENT':
                continue
            every.add((x['locator'], e, w, y))
            (removed if vd.get('vt:%s:%d' % (w, y)) else out).add((x['locator'], e, w, y))
    return sorted(out), vd, {'items_before_documenting': len(every), 'removed_documented_since': len(removed),
                             'removed_vintages': len({(w, y) for _, _, w, y in removed})}


def proposals(cx):
    items, vd, base = population(cx)
    judge = Judge(cx)
    pres = Presenter()
    est = legacy_estates()
    rows = []
    try:
        for aid, e, w, y in items:
            a = cx.arts.get(aid) or {}
            sha, media = a.get('sha256'), a.get('media_type')
            text = cx.doc(aid)
            vt = 'vt:%s:%d' % (w, y)
            ev = judge.web(sha, e, w, y) if media == 'text/html' else judge.document(aid, e, w, y)
            rd, rcode, rwhy = reader_verdict(pres, est.get(e), sha, media, cx.nm.get(w, ''), y)
            dated = bool(text) and y in RB.dated_years(text) and not re.search(
                r'(?<!\d)%d(?!\d)' % y, '\n'.join(l for l in RB.fold(text).split('\n') if not RB.DATED_YEAR.search(l)))
            row = {'candidate': '%s|%s|%s|%d' % (aid, e, w, y), 'artifact': aid, 'sha256': sha, 'media_type': media,
                   'first_url': (pres.disc.get(sha) or {}).get('first_url'),
                   'estate': e, 'estate_name': cx.nm.get(e, e), 'wine': w, 'wine_name': cx.nm.get(w, w), 'vintage': y,
                   'vintage_id': vt, 'gap_id': cx.gaps.get('VINTAGE_NO_DOCUMENT|%s' % e),
                   'document_type': V.doc_type(text, media) if text else 'NO_TEXT',
                   'evidence_of_document': ev, 'reader': {'decision': rd, 'code': rcode, 'why': rwhy},
                   'claim_year_dated': bool(dated) if ev['kind'] == 'DOCUMENT' else False,
                   'reader_false_positive': None, 'positive_evidence': None, 'r1_gate': None}
            if ev['disposition'] == 'SAFE_TO_MAP' and rd == 'ACCEPTED':
                disp, why = 'SAFE_TO_MAP', ev['basis']
            elif ev['disposition'] == 'SAFE_TO_MAP':
                disp = READER_TO_DISP.get(rcode, 'EVIDENCE_INSUFFICIENT')
                why = 'the document\'s evidence holds (%s), but the reader refuses it (%s: %s)' % (ev['basis'], rcode, rwhy)
            else:
                disp, why = ev['disposition'], ev['basis']
                if rd == 'ACCEPTED':
                    c = fp_class(ev, dated)
                    row['reader_false_positive'] = {'class': c, 'known': c in KNOWN_CLASSES,
                                                    'rule': KNOWN_CLASSES.get(c, 'not a named class')}
            if disp == 'SAFE_TO_MAP' and aid in vd.get(vt, []):
                disp, why = 'ALREADY_SUPPORTED', 'the model already links this document to the vintage'
            row.update(disposition=disp, basis=why)
            if disp == 'SAFE_TO_MAP':
                row['r1_gate'] = r1_gate(row)
                page = ev.get('page') or {}
                row['positive_evidence'] = {
                    'identity': (page.get('identity') or {}).get('heading') if page else (ev.get('title') or [None])[0],
                    'identity_source': page.get('identity_source') if page else ev.get('rule'),
                    'vintage_source': page.get('vintage_source') if page else 'title or opening',
                    'basis': ev['basis'], 'excluded_matches_set_aside': page.get('excluded_region_match') if page else [],
                    'reader': 'whose_sheet raised no objection (reader %s)' % EV.reader_fingerprint(),
                    'needs_decision': 'no evidence decision exists for these bytes; M3.6B would record one'}
                row['extraction_opportunity'] = sorted(set(FIELDS) - cx.canon.get(vt, set()))
            rows.append(row)
    finally:
        pres.close()
    rows.sort(key=lambda r: (r['estate'], r['wine'], r['vintage'], r['artifact']))
    return rows, base


# -- part 2: the accepted claims M3.5 found wrong ----------------------------------------------------

def corrections(cx):
    review = L.jsonl_lines(L.ROOT + 'data/audit/m3.5-held-document-review.jsonl')
    flagged = [(r, d) for r in review if r.get('correction_proposal') for d in r['correction_proposal']['decisions']]
    by_name = collections.defaultdict(set)
    for wid, (n, _) in cx.wines.items():
        by_name[RB.norm_name(n)].add(wid)
    wine_estate = collections.defaultdict(set)
    for e, ws in cx.ew.items():
        for w in ws:
            wine_estate[w].add(e)
    out = []
    for r, rk in flagged:
        d, ln = cx.decs[rk], cx.ln[rk]
        aid, e, w, y = r['artifact'], r['estate'], r['wine'], r['vintage']
        text = cx.doc(aid)
        j = RB.judge(text, {'estate': e, 'wine': w, 'vintage': y}, cx.wines, cx.ew, cx.blocked) if text else None
        tname, tyear = (j['title'] if j else (None, None))
        twines = sorted(by_name.get(tname or '', set()))
        if j is None or j['disposition'] != 'WRONG_EXISTING_ATTRIBUTION':
            cat, actual = 'OTHER_REVIEW_REQUIRED', None
        elif twines and w not in twines:
            other_estates = sorted(set().union(*(wine_estate[t] for t in twines)))
            cat = 'WRONG_ESTATE' if e not in other_estates else 'WRONG_WINE'
            actual = {'estate': other_estates, 'wine': twines, 'vintage': tyear}
        elif not twines:
            cat = 'WRONG_ESTATE' if (tname or '').startswith('chateau ') else 'WRONG_WINE'
            actual = {'estate': None, 'wine': None, 'vintage': tyear, 'unlisted_title': tname}
        elif r['claim_year_dated']:
            cat, actual = 'DATE_FALSE_POSITIVE', {'estate': [e], 'wine': [w], 'vintage': tyear}
        else:
            cat, actual = 'WRONG_VINTAGE', {'estate': [e], 'wine': [w], 'vintage': tyear}
        repl = None
        if actual and actual.get('wine') and actual.get('vintage'):
            for k in sorted(cx.by_art.get(aid, [])):
                dd, ll = cx.decs.get(k), cx.ln[k]
                if dd and dd['decision'] == 'ACCEPTED' and ll.get('wine') in actual['wine'] and \
                        ((dd.get('ctx') or {}).get('target_vintage') or (dd.get('ctx') or {}).get('vintage')) == actual['vintage']:
                    repl = k
                    break
        accepted_on_doc = {cx.ln[k].get('estate') for k in cx.by_art.get(aid, [])
                           if cx.decs.get(k) and cx.decs[k]['decision'] == 'ACCEPTED'} - {None}
        systematic = []
        if len(accepted_on_doc) >= 2:
            systematic.append('SHARED_GROUP_LIBRARY: the document is accepted for %d estates' % len(accepted_on_doc))
        if r['claim_year_dated']:
            systematic.append('PRESS_OR_EVENT_DATE: the claimed year stands only in a dated line')
        elif tyear and tyear != y and re.search(r'(?<!\d)%d(?!\d)' % y, text or ''):
            systematic.append('YEAR_IN_BODY: the claimed year is printed in the document, not as its vintage')
        own = RB.norm_name(cx.nm.get(e, ''))
        producer_lines = RB.norm_name('\n'.join(l for l in (text or '').split('\n') if RB.PRODUCER.search(RB.fold(l))))
        producer_only = bool(own) and own.split()[-1] in producer_lines and own.split()[-1] not in RB.norm_name(RB.body(text or ''))
        if cat == 'OTHER_REVIEW_REQUIRED':
            action = 'REVIEW_REQUIRED'
        elif cat == 'WRONG_WINE' and actual and actual.get('unlisted_title') and own and own.split()[-1] in (tname or ''):
            # the estate's own name on a wine the model does not list (Cuvée de Mongravey): the estate may be
            # right, the wine is not this one, and no wine exists in the model to supersede with
            action = 'RETAIN_AS_HISTORICAL_ACCEPTANCE_BUT_FLAG'
        else:
            action = 'SUPERSEDE_WITH_CORRECTED_DECISION'
        out.append({
            'decision': rk, 'artifact': aid, 'sha256': r['sha256'], 'files': r['files'],
            'original': {'decision': d['decision'], 'code': d['code'], 'estate': ln.get('estate'), 'wine': ln.get('wine'),
                         'vintage': (d.get('ctx') or {}).get('target_vintage') or (d.get('ctx') or {}).get('vintage'),
                         'target_role': (d.get('ctx') or {}).get('target_role'), 'reader': d.get('reader'),
                         'evidence': d.get('evidence')},
            'estate_name': cx.nm.get(e, e), 'wine_name': cx.nm.get(w, w),
            'document_is': {'title': [tname, tyear], 'model_wines': twines},
            'actual': actual, 'category': cat,
            'reason': j['basis'] if j else 'the document has no title line to judge by',
            'mismatch_evidence': 'the document\'s first line reads "%s%s"' % (tname, ' %d' % tyear if tyear else '') if tname else None,
            'claimed_name_only_in_producer_line': producer_only,
            'replacement': {'established': bool(repl), 'decision': repl,
                            'note': ('the document\'s own target is accepted on these bytes' if repl else
                                     'no correct replacement is established in the model' if not (actual and actual.get('wine')) else
                                     'the document\'s own target has no accepted decision on these bytes')},
            'systematic': systematic, 'proposed_action': action})
    out.sort(key=lambda x: (x['artifact'], x['decision']))
    return out


def build():
    cx = V.Ctx()
    cx.vd = A.vintage_documents((A.M36B_ACTOR, A.M310B_ACTOR))      # the model as this audit read it: before M3.6B's own links and later ones
    props, base = proposals(cx)
    return props, corrections(cx), fingerprints(), base


def body(rows):
    return ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                   for r in rows).encode('utf-8')


def main():
    props, corr, fps, base = build()
    gate = [r for r in props if r['disposition'] == 'SAFE_TO_MAP' and r['r1_gate']]
    unknown = [r for r in props if r['reader_false_positive'] and not r['reader_false_positive']['known']]
    if gate or unknown:
        print('BLOCKED - M3.6A READER REQUIRES ANOTHER CONTROLLED RULE UPDATE')
        for r in gate[:20]:
            print('  SAFE breaks R1: %s %s' % (r['candidate'], r['r1_gate']))
        for r in unknown[:20]:
            print('  unnamed false-positive class: %s %s' % (r['candidate'], r['reader_false_positive']))
    if '--report' in sys.argv or '--check-all' in sys.argv:
        import m36a_rerun_report
        text = m36a_rerun_report.report(props, corr, fps, base, json.load(open(BLOCKED_RUN, encoding='utf-8')))
        if '--check' in sys.argv or '--check-all' in sys.argv:
            same = os.path.exists(REPORT) and open(REPORT, encoding='utf-8').read() == text
            print('docs/PHASE-M3.6A-RERUN.md ' + ('is current' if same else 'differs from a fresh run'))
            if not same or '--check-all' not in sys.argv:
                sys.exit(0 if same else 1)
        else:
            open(REPORT, 'w', encoding='utf-8', newline='\n').write(text)
            print('wrote docs/PHASE-M3.6A-RERUN.md')
            return
    outs = ((PROPOSALS, body(props)), (CORRECTIONS, body(corr)))
    if '--check' in sys.argv or '--check-all' in sys.argv:
        bad = [p for p, b in outs if not os.path.exists(p) or open(p, 'rb').read() != b]
        print('M3.6A rerun outputs ' + ('are current' if not bad else 'differ: %s' % bad))
        sys.exit(1 if bad else 0)
    c = collections.Counter(r['disposition'] for r in props)
    fp = [r for r in props if r['reader_false_positive']]
    print('baseline %s' % base)
    print('candidates %d, documents %d, vintages %d; %s' % (len(props), len({r['artifact'] for r in props}),
                                                             len({r['vintage_id'] for r in props}), dict(c.most_common())))
    print('reader: %s; false positives %d, classes %s' % (dict(collections.Counter(r['reader']['decision'] for r in props)),
                                                          len(fp), dict(collections.Counter(r['reader_false_positive']['class'] for r in fp))))
    print('corrections: %d; %s; %s' % (len(corr), dict(collections.Counter(x['category'] for x in corr)),
                                       dict(collections.Counter(x['proposed_action'] for x in corr))))
    for p, b in outs:
        open(p, 'wb').write(b)
    print('wrote both outputs')


if __name__ == '__main__':
    main()
