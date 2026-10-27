"""M3.6B: apply M3.6A's eight safe mappings and its evidence corrections - controlled mutation.

    python tools/m36b-apply.py --mappings      stage 1: preflight; the 8 mappings' v6 decisions and manifest
    python tools/m36b-apply.py --corrections   stage 2: preflight; the 199 superseding v6 decisions, the
                                               20 historical flags, and the correction manifest
    python tools/m36b-apply.py --check         recompute what is written and compare (see VERIFYING)
    python tools/m36b-apply.py --report        write docs/PHASE-M3.6B-APPLICATION.md (also --check)

THE ALLOW-LISTS are M3.6A's committed fresh audit (35f8df8) and nothing else, verified before anything
is written: its 8 SAFE_TO_MAP candidates; its 199 SUPERSEDE_WITH_CORRECTED_DECISION decisions (62 whose
correct target is already accepted on the same bytes, 137 whose document is a wine the model does not
list); its 20 RETAIN_AS_HISTORICAL_ACCEPTANCE_BUT_FLAG decisions (Cuvée de Mongravey). A count or an id
that differs stops the run.

THE REPRESENTATION is the evidence store's own: one file per decider version, append-only, and
evidence_store.latest_by_context() reading, for each question, the answer of the highest version that
asked it. M3.6B is decider version 6. Its reader fingerprint is the fingerprint of the rules that
decide (tools/m35_rubric.py and tools/web_evidence.py), not whose_sheet's.

  a mapping     a v6 ACCEPTED row (kind web_page_review) for the page's estate, wine and vintage, its
                read.path the held bytes under sources/discovery/, its evidence the page's main heading
                and vintage source. The model gains one Attribution per mapping through the migration
                (tools/mig_m6_provenance.m36b_mappings), as M3.4B's did.
  a correction  a v6 REFUSED row asking exactly the question the v5 row asked (the same artifact and
                context: its row_key differs only in `v`), so latest_by_context() now reads the
                correction - and the v5 row stays in decisions-v5.jsonl byte for byte. The one relation
                added is explicit: `supersedes` names the v5 row (row_key and version); `code` is the
                M3.6A category (WRONG_ESTATE, WRONG_WINE); `replacement` names the accepted decision for
                the document's own wine and vintage where one exists, and the model attribution that
                carries it; `document_is` keeps what the document is even when the model has no such wine.
  a flag        an audit record (data/audit/m3.6b-historical-flags.jsonl), not a decision: the historical
                acceptance stays as the latest answer, flagged for review. The model's findings could hold
                it, but a new finding changes the register's identity-gap counts, which M3.6B must not.

VERIFYING. A v6 row carries the git state it was written in (evidence_store: a v4+ row must). Run
twice from the same state, the rows are byte-identical; --check, run later from another commit,
recomputes every row and compares all of it except that git stamp, which it requires to name a commit
in HEAD's history.

No figure, name, rank, classification or canonical value changes; nothing is fetched or OCR'd.
"""
import collections
import copy
import gzip
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_gap_analysis as A  # noqa: E402
import evidence_store as ST  # noqa: E402
import migration_lib as L  # noqa: E402
import model_schema as S  # noqa: E402
import provenance as PV  # noqa: E402
import m35_rubric as RB  # noqa: E402
import web_evidence as WE  # noqa: E402
import mig_m6_provenance as M6  # noqa: E402

VERSION = 6
ACTOR = 'tools/m36b-apply.py'
M36A_PROPOSALS = 'data/audit/m3.6a-rerun-held-document-proposals.jsonl'
M36A_CORRECTIONS = 'data/audit/m3.6a-rerun-evidence-corrections.jsonl'
MAPPINGS = L.ROOT + 'data/audit/m3.6b-mapping-application.jsonl'
CORRECTIONS = L.ROOT + 'data/audit/m3.6b-correction-application.jsonl'
FLAGS = L.ROOT + 'data/audit/m3.6b-historical-flags.jsonl'
REPORT = L.ROOT + 'docs/PHASE-M3.6B-APPLICATION.md'
DECIDER_FILES = ('tools/m35_rubric.py', 'tools/web_evidence.py')
EXPECT = {'mappings': 8, 'supersessions': 199, 'with_replacement': 62, 'without_replacement': 137, 'flags': 20}
FLAG_REASON = ('historical acceptance retained; attribution requires review because the document concerns '
               'Cuvée de Mongravey and the current model has no corresponding canonical wine')

_x = importlib.util.spec_from_file_location('m36a', L.ROOT + 'tools/m36a-rerun.py')
X = importlib.util.module_from_spec(_x)
_x.loader.exec_module(X)
V, EV = X.V, X.EV


def decider_fingerprint():
    """v6's reader: the rules that decide, so a change to them is a new decider version."""
    h = hashlib.sha1()
    for f in DECIDER_FILES:
        h.update(open(L.ROOT + f, 'rb').read())
    return h.hexdigest()[:12]


class Stop(Exception):
    pass


def allow_lists():
    """The three allow-lists from M3.6A's committed outputs, verified (fail closed)."""
    props = L.jsonl_lines(L.ROOT + M36A_PROPOSALS)
    corr = L.jsonl_lines(L.ROOT + M36A_CORRECTIONS)
    maps = [r for r in props if r['disposition'] == 'SAFE_TO_MAP']
    sup = [c for c in corr if c['proposed_action'] == 'SUPERSEDE_WITH_CORRECTED_DECISION']
    flags = [c for c in corr if c['proposed_action'] == 'RETAIN_AS_HISTORICAL_ACCEPTANCE_BUT_FLAG']
    got = {'mappings': len(maps), 'supersessions': len(sup), 'flags': len(flags),
           'with_replacement': sum(1 for c in sup if c['replacement']['established']),
           'without_replacement': sum(1 for c in sup if not c['replacement']['established'])}
    if got != EXPECT:
        raise Stop('the allow-lists differ from M3.6A: %s, expected %s' % (got, EXPECT))
    if len({r['candidate'] for r in maps}) != 8 or len({c['decision'] for c in sup + flags}) != 219:
        raise Stop('duplicated ids in the allow-lists')
    if {c['proposed_action'] for c in corr} - {'SUPERSEDE_WITH_CORRECTED_DECISION', 'RETAIN_AS_HISTORICAL_ACCEPTANCE_BUT_FLAG'}:
        raise Stop('an M3.6A correction action outside the two this phase applies')
    if any('cuvee de mongravey' not in (c['document_is']['title'][0] or '') for c in flags):
        raise Stop('a flag that is not a Cuvée de Mongravey document')
    return maps, sup, flags


def git_state():
    return PV.git_state(L.ROOT)


def blob_path(sha):
    for rel in ('discovery/blobs/%s/%s' % (sha[:2], sha), 'discovery/blobs/%s/%s.gz' % (sha[:2], sha)):
        if os.path.exists(L.ROOT + 'sources/' + rel):
            return rel
    return None


def held_bytes(rel):
    b = open(L.ROOT + 'sources/' + rel, 'rb').read()
    return gzip.decompress(b) if rel.endswith('.gz') else b


class Ctx:
    def __init__(self):
        self.cx = V.Ctx()
        self.before = A.vintage_documents((A.M36B_ACTOR, A.M310B_ACTOR))          # the model as M3.6A read it
        self.cx.vd = self.before
        self.estates = X.legacy_estates()
        self.gv = {}
        for r in A.table('identity/identity-map.jsonl'):
            if r['namespace'] == 'grand-vin' and r.get('stable_id'):
                self.gv[r['stable_id']] = r['legacy_key']
        self.findings = [f for f in A.table('cross/findings.jsonl') if f['status'] == 'OPEN']
        self.fp = decider_fingerprint()
        self.git = git_state()


# -- stage 1: the eight mappings ----------------------------------------------------------------

def mapping_rows(k, maps):
    cx = k.cx
    out = []
    pres = X.Presenter()
    judge = X.Judge(cx)
    try:
        for r in maps:
            aid, e, w, y, sha = r['artifact'], r['estate'], r['wine'], r['vintage'], r['sha256']
            vt = 'vt:%s:%d' % (w, y)
            fail = []
            a = cx.arts.get(aid) or {}
            rel = blob_path(sha)
            if a.get('sha256') != sha or not rel or hashlib.sha256(held_bytes(rel)).hexdigest() != sha:
                fail.append('artifact: missing, or its held bytes do not hash to it')
            ev = judge.web(sha, e, w, y)
            page = ev.get('page') or {}
            if ev['disposition'] != 'SAFE_TO_MAP' or page.get('page_type') != 'WINE_DOCUMENT' \
                    or page.get('identity_source') != 'h1' or page != r['evidence_of_document']['page']:
                fail.append('evidence: the page no longer judges as M3.6A recorded it')
            rd, code, why = X.reader_verdict(pres, k.estates.get(e), sha, a.get('media_type'), cx.nm.get(w, ''), y)
            if rd != 'ACCEPTED':
                fail.append('reader: %s %s' % (code, why))
            if w not in cx.ew.get(e, []) or vt not in cx.vintages:
                fail.append('identity: the wine is not the estate\'s, or the vintage does not exist')
            if k.before.get(vt):
                fail.append('vintage: it had a document before M3.6B')
            if w in cx.blocked:
                fail.append('open decision: %s' % cx.blocked[w])
            for f in k.findings:
                if f['target'] in (w, vt, aid):
                    fail.append('open finding %s on the target' % f['id'])
            slug = (k.estates.get(e) or (None,))[0]
            role = 'grand' if k.gv.get(w) == slug else None
            if not slug or not role:
                fail.append('role: %s is not the grand vin of a legacy estate record' % cx.nm.get(w))
            url = r['first_url'] or ''
            d = {'artifact': (os.path.basename(url.split('?')[0].rstrip('/')) or 'index'),
                 'kind': 'web_page_review',
                 'ctx': {'estate': slug, 'folder': 'discovery:' + sha, 'wine': None, 'vintage': y,
                         'target_wine': cx.nm.get(w), 'target_role': role, 'target_vintage': y,
                         'evaluated_as': '%s, vintage %d' % (cx.nm.get(w), y)},
                 'decision': 'ACCEPTED', 'code': 'ACCEPTED', 'raw': '',
                 'evidence': ['web_evidence: page type %s; identity from the main heading "%s"; vintage from the %s'
                              % (page.get('page_type'), (page.get('identity') or {}).get('heading'), page.get('vintage_source')),
                              'M3.6A fresh audit (35f8df8) candidate %s: SAFE_TO_MAP; whose_sheet raised no objection' % r['candidate']],
                 'excluded_matches_set_aside': page.get('excluded_region_match') or [],
                 'points_at': {'role': None, 'wine': None},
                 'read': {'path': rel, 'sha256': sha, 'bytes': len(held_bytes(rel)) if rel else None,
                          'extraction': 'discovery/extracted/%s.json' % sha},
                 'git': k.git, 'reader': k.fp, 'v': VERSION, 're_evaluable': True}
            rk = M6.row_key(d)
            out.append({'manifest': {
                'candidate': r['candidate'], 'artifact': aid, 'sha256': sha, 'estate': e, 'estate_name': r['estate_name'],
                'wine': w, 'wine_name': r['wine_name'], 'vintage': y, 'vintage_id': vt, 'gap_id': r['gap_id'],
                'first_url': url, 'page_type': page.get('page_type'), 'identity_source': page.get('identity_source'),
                'identity': (page.get('identity') or {}).get('heading'), 'vintage_source': page.get('vintage_source'),
                'colour': (page.get('identity') or {}).get('colour'),
                'excluded_matches_set_aside': page.get('excluded_region_match') or [],
                'supporting_evidence': r['positive_evidence']['basis'], 'm36a_disposition': r['disposition'],
                'original_attribution': [a2['id'] for a2 in A.legacy_attr_by_artifact().get(aid, [])],
                'evidence_decision': rk, 'attribution': S.hid('Attribution', aid, 'm36b', vt), 'role': 'FIRST',
                'result': 'REJECTED_PREFLIGHT' if fail else 'APPLIED', 'failures': sorted(set(fail))},
                'decision': d})
    finally:
        pres.close()
    out.sort(key=lambda x: (x['manifest']['estate'], x['manifest']['wine'], x['manifest']['vintage'], x['manifest']['artifact']))
    return out


# -- stage 2: the corrections and the flags -------------------------------------------------------

def correction_rows(k, sup, flags):
    cx = k.cx
    v5 = {}
    for d in L.jsonl_lines(L.ROOT + 'data/evidence/decisions-v5.jsonl'):
        v5[M6.row_key(d)] = d
    m35 = {(a['artifact'], a['vintage']): a['id'] for a in A.m35_attributions()}
    out, fl = [], []
    for c in sup + flags:
        rk = c['decision']
        old = v5.get(rk)
        fail = []
        if not old or old['decision'] != 'ACCEPTED' or (old.get('read') or {}).get('sha256') != c['sha256']:
            fail.append('the historical decision is not the accepted one M3.6A audited')
            old = old or {}
        rel = (old.get('read') or {}).get('path')
        if not rel or not os.path.exists(L.ROOT + 'sources/' + rel) or \
                hashlib.sha256(open(L.ROOT + 'sources/' + rel, 'rb').read()).hexdigest() != c['sha256']:
            fail.append('artifact: the file the decision read no longer hashes to it')
        text = cx.doc(c['artifact'])
        j = RB.judge(text, {'estate': cx.ln[rk].get('estate'), 'wine': cx.ln[rk].get('wine'), 'vintage': c['original']['vintage']},
                     cx.wines, cx.ew, cx.blocked) if text else None
        if not j or j['disposition'] != 'WRONG_EXISTING_ATTRIBUTION' or j['title'] != c['document_is']['title']:
            fail.append('evidence: the document no longer judges as M3.6A recorded it')
        if c['proposed_action'] == 'RETAIN_AS_HISTORICAL_ACCEPTANCE_BUT_FLAG':
            fl.append({'decision': rk, 'v': 5, 'artifact': c['artifact'], 'sha256': c['sha256'], 'files': c['files'],
                       'original': c['original'], 'estate_name': c['estate_name'], 'wine_name': c['wine_name'],
                       'document_is': c['document_is'], 'flag': 'RETAIN_AS_HISTORICAL_ACCEPTANCE_BUT_FLAG',
                       'reason': FLAG_REASON, 'replacement': None,
                       'result': 'REJECTED_PREFLIGHT' if fail else 'RECORDED', 'failures': sorted(set(fail))})
            continue
        repl = c['replacement']['decision']
        repl_att = None
        if repl:
            rd = v5.get(repl)
            if not rd or rd['decision'] != 'ACCEPTED' or (rd.get('read') or {}).get('sha256') != c['sha256']:
                fail.append('replacement: the accepted decision for the document\'s own target is not on these bytes')
            else:
                vy = (rd.get('ctx') or {}).get('target_vintage') or (rd.get('ctx') or {}).get('vintage')
                lw = cx.ln[repl].get('wine')
                repl_att = m35.get((c['artifact'], 'vt:%s:%s' % (lw, vy)))
        new = {'artifact': old.get('artifact'), 'kind': 'correction', 'ctx': copy.deepcopy(old.get('ctx')),
               'decision': 'REFUSED', 'code': c['category'], 'raw': c['reason'],
               'evidence': [c['mismatch_evidence'] or '', 'M3.6A fresh audit (35f8df8): %s, %s' % (c['category'], c['proposed_action'])]
               + ['systematic: %s' % s for s in c['systematic']],
               'points_at': {'role': None, 'wine': ((c['actual'] or {}).get('wine') or [None])[0]},
               'supersedes': {'row_key': rk, 'v': 5, 'decision': old.get('decision'), 'code': old.get('code')},
               'replacement': {'decision': repl, 'attribution': repl_att,
                               'note': c['replacement']['note']},
               'document_is': {'title': c['document_is']['title'], 'model_wines': c['document_is']['model_wines'],
                               'unlisted': not c['document_is']['model_wines']},
               'read': {'path': rel, 'sha256': c['sha256'], 'bytes': (old.get('read') or {}).get('bytes')},
               'git': k.git, 'reader': k.fp, 'v': VERSION, 're_evaluable': True}
        nk = M6.row_key(new)
        if json.loads(nk)[:-1] != json.loads(rk)[:-1]:
            fail.append('the superseding decision does not ask the historical decision\'s question')
        out.append({'manifest': {'decision': rk, 'superseded_by': nk, 'artifact': c['artifact'], 'sha256': c['sha256'],
                                 'files': c['files'], 'original': c['original'], 'estate_name': c['estate_name'],
                                 'wine_name': c['wine_name'], 'category': c['category'], 'reason': c['reason'],
                                 'document_is': c['document_is'], 'replacement': {'decision': repl, 'attribution': repl_att},
                                 'proposed_action': c['proposed_action'],
                                 'result': 'REJECTED_PREFLIGHT' if fail else 'APPLIED', 'failures': sorted(set(fail))},
                    'decision': new})
    out.sort(key=lambda x: (x['manifest']['artifact'], x['manifest']['decision']))
    fl.sort(key=lambda x: (x['artifact'], x['decision']))
    return out, fl


def body(rows):
    return ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                   for r in rows).encode('utf-8')


def write(path, rows):
    open(path, 'wb').write(body(rows))


def apply(rows, what):
    bad = [x['manifest'] for x in rows if x['manifest']['result'] not in ('APPLIED', 'RECORDED')]
    if bad:
        raise Stop('%d %s failed preflight: %s' % (len(bad), what, '; '.join('%s: %s' % (
            b.get('candidate') or b.get('decision', '')[:60], b['failures']) for b in bad[:5])))
    n = ST.append([x['decision'] for x in rows], VERSION)
    return n


def stored_v6():
    return [d for d in ST.iter_rows([VERSION])] if VERSION in ST.versions() else []


_IN_HEAD = {}                                      # commit -> in HEAD's history; asked once per commit


def in_head(commit):
    if commit not in _IN_HEAD:
        _IN_HEAD[commit] = subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'],
                                          cwd=L.ROOT).returncode == 0
    return _IN_HEAD[commit]


def same_but_git(a, b):
    a, b = dict(a), dict(b)
    ga, gb = a.pop('git'), b.pop('git')
    return a == b and ga.get('commit') and in_head(ga['commit'])


def main():
    try:
        maps, sup, flags = allow_lists()
        if '--report' in sys.argv:
            import m36b_report
            text = m36b_report.report(maps, sup, flags)
            if '--check' in sys.argv:
                same = os.path.exists(REPORT) and open(REPORT, encoding='utf-8').read() == text
                print('docs/PHASE-M3.6B-APPLICATION.md ' + ('is current' if same else 'differs from a fresh run'))
                sys.exit(0 if same else 1)
            open(REPORT, 'w', encoding='utf-8', newline='\n').write(text)
            print('wrote docs/PHASE-M3.6B-APPLICATION.md')
            return
        k = Ctx()
        if '--check' in sys.argv:
            stored = {M6.row_key(d): d for d in stored_v6()}
            bad = []
            mrows = mapping_rows(k, maps)
            if os.path.exists(MAPPINGS):
                if body([x['manifest'] for x in mrows]) != open(MAPPINGS, 'rb').read():
                    bad.append('the mapping manifest')
                for x in mrows:
                    s = stored.get(x['manifest']['evidence_decision'])
                    if not s or not same_but_git(x['decision'], s):
                        bad.append('v6 mapping decision %s' % x['manifest']['candidate'])
            if os.path.exists(CORRECTIONS):
                crows, fl = correction_rows(k, sup, flags)
                if body([x['manifest'] for x in crows]) != open(CORRECTIONS, 'rb').read():
                    bad.append('the correction manifest')
                if body(fl) != open(FLAGS, 'rb').read():
                    bad.append('the flags')
                for x in crows:
                    s = stored.get(x['manifest']['superseded_by'])
                    if not s or not same_but_git(x['decision'], s):
                        bad.append('v6 correction %s' % x['manifest']['decision'][:50])
            print('M3.6B ' + ('is current' if not bad else 'differs: %s' % bad[:5]))
            sys.exit(1 if bad else 0)
        if '--mappings' in sys.argv:
            rows = mapping_rows(k, maps)
            n = apply(rows, 'mappings')
            write(MAPPINGS, [x['manifest'] for x in rows])
            print('stage 1: %d mapping decision(s) appended to v%d (reader %s, git %s%s); manifest written'
                  % (n, VERSION, k.fp, k.git['commit'][:12], ' dirty' if k.git['dirty'] else ''))
        if '--corrections' in sys.argv:
            rows, fl = correction_rows(k, sup, flags)
            bad = [f for f in fl if f['result'] != 'RECORDED']
            if bad:
                raise Stop('%d flag(s) failed preflight' % len(bad))
            n = apply(rows, 'corrections')
            write(CORRECTIONS, [x['manifest'] for x in rows])
            write(FLAGS, fl)
            print('stage 2: %d superseding decision(s) appended to v%d; %d flag(s) recorded' % (n, VERSION, len(fl)))
    except Stop as s:
        print('BLOCKED - %s' % s)
        sys.exit(2)


if __name__ == '__main__':
    main()
