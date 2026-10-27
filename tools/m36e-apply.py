"""M3.6E: correct the historical Cuvée Mongravey evidence decisions - append-only.

    python tools/m36e-apply.py --apply     preflight; the 38 superseding v7 decisions and the manifest
    python tools/m36e-apply.py --check     recompute what is written and compare (see VERIFYING)

THE ALLOW-LIST is M3.6C's committed audit (data/audit/m3.6c-cuvee-mongravey-identity.jsonl) and nothing
else: its 38 WRONG_WINE_HISTORICAL_ACCEPTANCE decisions, the v5 acceptances of Cuvée de Mongravey sheets as
a grand vin. They ask two estates' questions, because the sheets sit in a shared group library:

  21 ask "is this Château Mongravey (es_00158)?"   - their latest answer is still the v5 acceptance
                                                     (20 that M3.6B flagged and retained, 1 it never saw)
  17 ask "is this Château de Braude (es_00073)?"   - M3.6B already refused them in v6, recording the
                                                     document as "a wine the model does not list"

A count, a latest answer or a disposition that differs stops the run.

THE READING is the existing one: each document is judged again by tools/m35_rubric.judge() exactly as
M3.6B judged it, and must still be WRONG_EXISTING_ATTRIBUTION with a title. That title names the wine:
it must fold (m35_rubric.fold) to a name M3.6D recorded for wn_00640 - "Cuvée de Mongravey" is its
SOURCE_RENDERING. A title that is any other name, that names "Mongravey Cuvée Margaux" (unresolved, not
an alias), or that is missing leaves the decision UNRESOLVED and unwritten; nothing is inferred from the
word "Mongravey". The vintage is the title's own; a title without one is recorded as stating none.

THE REPRESENTATION is M3.6B's (tools/m36b-apply.py): one v7 REFUSED row (kind correction, code WRONG_WINE)
asking exactly the question of the decision it supersedes - the same artifact and context, so its row key
differs only in `v` - and latest_by_context() reads it. `supersedes` names that decision (v5 or v6);
`document_is` names wn_00640 and the title; `replacement` says why there is none: the model holds no
vintage of wn_00640 yet, and vintage population is a later, evidence-gated phase. v1-v6 stay byte for byte.
Decider version 7: the same rules as v6 (tools/m35_rubric.py, tools/web_evidence.py), so the same reader
fingerprint.

The model is not changed: it reads evidence links from v4-v5 only (mig_m6_provenance.evidence_links), and
no attribution, vintage, figure, name, rank or estate follows from a refusal. wn_00158 and wn_00640 stand
as they are; "1st Vintage: 1999" stays FIRST_VINTAGE_STATED in M3.6D's manifest and creates nothing.

VERIFYING. A v7 row carries the git state it was written in. --check, run later from another commit,
recomputes every row and the manifest and compares all of it except that git stamp, which must name a
commit in HEAD's history.
"""
import collections
import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evidence_store as ST  # noqa: E402
import migration_lib as L  # noqa: E402
import provenance as PV  # noqa: E402
import m35_rubric as RB  # noqa: E402
import mig_m6_provenance as M6  # noqa: E402

VERSION = 7
ACTOR = 'tools/m36e-apply.py'
M36C = 'data/audit/m3.6c-cuvee-mongravey-identity.jsonl'
M36D = 'data/audit/m3.6d-cuvee-mongravey.jsonl'
MANIFEST = L.ROOT + 'data/audit/m3.6e-cuvee-historical-corrections.jsonl'
DECIDER_FILES = ('tools/m35_rubric.py', 'tools/web_evidence.py')
WINE, ESTATE, GRAND_VIN = 'wn_00640', 'es_00158', 'wn_00158'
UNRESOLVED_NAME = 'Mongravey Cuvée Margaux'
EXPECT = {'decisions': 38, 'latest v5 ACCEPTED': 21, 'latest v6 REFUSED': 17}
NOTE = ('the document is Cuvée Mongravey (wn_00640), %s; the model holds no vintage of that wine yet: '
        'vintage population is a later, evidence-gated phase')

_x = importlib.util.spec_from_file_location('m36a', L.ROOT + 'tools/m36a-rerun.py')
X = importlib.util.module_from_spec(_x)
_x.loader.exec_module(X)
V = X.V


class Stop(Exception):
    pass


def decider_fingerprint():
    h = hashlib.sha1()
    for f in DECIDER_FILES:
        h.update(open(L.ROOT + f, 'rb').read())
    return h.hexdigest()[:12]


def wine_names():
    """wn_00640's recorded names, folded, verified against M3.6D's manifest (fail closed)."""
    wines = [w for w in L.read_table('identity/wines.jsonl') if w['id'] == WINE]
    names = [n for n in L.read_table('identity/names.jsonl') if n.get('subject') == WINE]
    applied = {r['value']['name'] for r in L.jsonl_lines(L.ROOT + M36D)
               if r.get('fact') == 'name' and r.get('applied')}
    if len(wines) != 1 or wines[0].get('type') != 'RED':
        raise Stop('wn_00640 is not the one red wine M3.6D created')
    if {n['name'] for n in names} != applied or len(applied) != 3:
        raise Stop('wn_00640\'s names are not the three M3.6D applied: %s' % sorted(n['name'] for n in names))
    if any(RB.fold(n['name']) == RB.fold(UNRESOLVED_NAME) for n in names):
        raise Stop('"%s" is recorded as a name of wn_00640' % UNRESOLVED_NAME)
    return {RB.fold(n['name']): n for n in names}


def latest_before():
    """evidence_store.latest_by_context() over the versions before this one: the answers M3.6E corrects."""
    import evidence as EV
    out = {}
    for d in ST.iter_rows([v for v in ST.versions() if v < VERSION]):
        k = EV.row_key(d)[:-1]
        if k not in out or (d.get('v') or 0) >= (out[k].get('v') or 0):
            out[k] = d
    return out


def allow_list():
    rows = [r for r in L.jsonl_lines(L.ROOT + M36C) if r['record'] == 'decision']
    latest = latest_before()
    out, got = [], collections.Counter(decisions=len(rows))
    for r in rows:
        if r['disposition'] != 'WRONG_WINE_HISTORICAL_ACCEPTANCE':
            raise Stop('an M3.6C decision outside WRONG_WINE_HISTORICAL_ACCEPTANCE: %s' % r['id'][:60])
        cur = latest.get(tuple(json.loads(r['id'])[:-1]))
        if not cur:
            raise Stop('no decision answers %s' % r['id'][:60])
        got['latest v%s %s' % (cur['v'], cur['decision'])] += 1
        out.append((r, cur))
    if dict(got) != EXPECT or len({r['id'] for r, _ in out}) != 38:
        raise Stop('the allow-list differs from M3.6C: %s, expected %s' % (dict(got), EXPECT))
    return out


class Ctx:
    def __init__(self):
        self.cx = V.Ctx()
        self.names = wine_names()
        self.fp = decider_fingerprint()
        self.git = PV.git_state(L.ROOT)


def read(k, r, cur):
    """The document judged again by the existing rubric; its wine and vintage, or why there are none."""
    cx = k.cx
    ln = cx.ln.get(r['id']) or {}
    text = cx.doc(r['artifact'])
    j = RB.judge(text, {'estate': ln.get('estate'), 'wine': ln.get('wine'), 'vintage': r['claimed']['vintage']},
                 cx.wines, cx.ew, cx.blocked) if text else None
    fail = []
    rel = (cur.get('read') or {}).get('path')
    if not rel or not os.path.exists(L.ROOT + 'sources/' + rel) or \
            hashlib.sha256(open(L.ROOT + 'sources/' + rel, 'rb').read()).hexdigest() != r['sha256'] or \
            cur['read'].get('sha256') != r['sha256']:
        fail.append('artifact: the file the decision read no longer hashes to it')
    if not j or j['disposition'] != 'WRONG_EXISTING_ATTRIBUTION' or not j.get('title') or not j['title'][0]:
        return None, None, fail + ['evidence: the document does not judge WRONG_EXISTING_ATTRIBUTION with a title']
    tname, tyear = j['title']
    if RB.fold(UNRESOLVED_NAME) in RB.fold(tname):
        return j, None, fail + ['identity: the title is the unresolved "%s"' % UNRESOLVED_NAME]
    name = k.names.get(RB.fold(tname))
    if not name:
        return j, None, fail + ['identity: the title "%s" is not a recorded name of %s' % (tname, WINE)]
    return j, name, fail


def rows(k):
    out = []
    for r, cur in allow_list():
        j, name, fail = read(k, r, cur)
        rk = M6.row_key(cur)
        ctx = cur.get('ctx') or {}
        title = j['title'] if j else None
        vintage = 'its %s vintage' % title[1] if title and title[1] else 'its vintage not stated'
        man = {'decision': r['id'], 'artifact': r['artifact'], 'sha256': r['sha256'],
               'asked': {'estate': ctx.get('estate'), 'wine': ctx.get('target_wine'), 'vintage': ctx.get('target_vintage')},
               'superseding': {'row_key': rk, 'v': cur['v'], 'decision': cur['decision'], 'code': cur.get('code')},
               'm36b': r['m36b'], 'document_title': title,
               'outcome': 'CUVEE_MONGRAVEY' if name and not fail else 'UNRESOLVED',
               'wine': WINE if name and not fail else None, 'name_kind': name['kind'] if name else None,
               'vintage_stated': title[1] if title else None, 'vintage_created': False,
               'failures': sorted(set(fail))}
        if man['outcome'] != 'CUVEE_MONGRAVEY':
            out.append({'manifest': dict(man, superseded_by=None, result='UNRESOLVED'), 'decision': None})
            continue
        new = {'artifact': cur.get('artifact'), 'kind': 'correction', 'ctx': copy.deepcopy(ctx),
               'decision': 'REFUSED', 'code': 'WRONG_WINE',
               'raw': 'the title is "%s", %s of %s (Cuvée Mongravey); not %s' % (
                   tname_of(title), name['kind'], WINE, ctx.get('target_wine')),
               'evidence': ['the document\'s title reads "%s"' % ' '.join(str(x) for x in title if x),
                            'm35_rubric.judge: WRONG_EXISTING_ATTRIBUTION: %s' % j['basis'],
                            'M3.6C identity audit: WRONG_WINE_HISTORICAL_ACCEPTANCE',
                            'M3.6D: "%s" is the %s name of %s' % (name['name'], name['kind'], WINE)],
               'points_at': {'role': None, 'wine': WINE},
               'supersedes': {'row_key': rk, 'v': cur['v'], 'decision': cur['decision'], 'code': cur.get('code')},
               'replacement': {'decision': None, 'attribution': None, 'note': NOTE % vintage},
               'document_is': {'title': title, 'model_wines': [WINE], 'unlisted': False},
               'read': copy.deepcopy(cur['read']), 'git': k.git, 'reader': k.fp, 'v': VERSION, 're_evaluable': True}
        nk = M6.row_key(new)
        if json.loads(nk)[:-1] != json.loads(rk)[:-1]:
            raise Stop('a superseding decision does not ask its decision\'s question: %s' % rk[:60])
        out.append({'manifest': dict(man, superseded_by=nk, result='APPLIED'), 'decision': new})
    out.sort(key=lambda x: (x['manifest']['artifact'], x['manifest']['decision']))
    return out


def tname_of(title):
    return title[0] if title else None


def body(rows):
    return ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                   for r in rows).encode('utf-8')


def stored_v7():
    return list(ST.iter_rows([VERSION])) if VERSION in ST.versions() else []


def in_head(commit):
    return subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=L.ROOT).returncode == 0


def same_but_git(a, b):
    a, b = dict(a), dict(b)
    ga, gb = a.pop('git'), b.pop('git')
    return a == b and ga.get('commit') and in_head(ga['commit'])


def main():
    try:
        k = Ctx()
        if '--check' in sys.argv:
            got = rows(k)
            bad = []
            if body([x['manifest'] for x in got]) != open(MANIFEST, 'rb').read():
                bad.append('the manifest')
            stored = {M6.row_key(d): d for d in stored_v7()}
            want = {x['manifest']['superseded_by']: x['decision'] for x in got if x['decision']}
            if set(stored) != set(want):
                bad.append('v7 is not exactly the manifest\'s decisions')
            bad += ['v7 decision %s' % key[:50] for key in sorted(want)
                    if key in stored and not same_but_git(want[key], stored[key])]
            print('M3.6E ' + ('is current' if not bad else 'differs: %s' % bad[:5]))
            sys.exit(1 if bad else 0)
        if '--apply' in sys.argv:
            if VERSION in ST.versions():
                raise Stop('v%d already exists' % VERSION)
            got = rows(k)
            n = ST.append([x['decision'] for x in got if x['decision']], VERSION)
            open(MANIFEST, 'wb').write(body([x['manifest'] for x in got]))
            c = collections.Counter(x['manifest']['outcome'] for x in got)
            print('%d superseding decision(s) appended to v%d (reader %s, git %s%s); %s; manifest written'
                  % (n, VERSION, k.fp, k.git['commit'][:12], ' dirty' if k.git['dirty'] else '', dict(sorted(c.items()))))
            return
        print(__doc__)
    except Stop as s:
        print('BLOCKED - %s' % s)
        sys.exit(2)


if __name__ == '__main__':
    main()
