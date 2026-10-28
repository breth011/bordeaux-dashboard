"""Generic evidence acceptance: an evidence decision recorded against a registered artifact, from a reviewed manifest.

    python tools/apply-evidence-acceptance-manifest.py               validate (the default; read-only)
    python tools/apply-evidence-acceptance-manifest.py --validate    validate the manifest against the model, the
                                                                     review audits, the held bytes and the store
    python tools/apply-evidence-acceptance-manifest.py --plan        the deterministic plan (read-only)
    python tools/apply-evidence-acceptance-manifest.py --apply       validate -> plan -> verify -> append; all or nothing
    python tools/apply-evidence-acceptance-manifest.py --check       the store holds every manifest row, and nothing else
                                                                     in the versions the mechanism writes
  options: --manifest <file> (default data/audit/evidence-acceptance-manifest.jsonl); --timings
  BDX_EVIDENCE_DIR points it at another evidence store (an isolated copy); BDX_MODEL_DIR at another model.

docs/PHASE-GENERIC-EVIDENCE-REGISTRATION.md is the contract. It is M3.10B's acceptance made reusable: the same
decision, in the same representation (M3.6B's, for a sheet), with no phase, estate or document count written into it.

A ROW (eam_NNNNNN) asks that the store record that the artifact's own bytes are evidence for exactly this estate's
grand vin and this vintage. It holds references only: the artifact (a model artifact, registered or crawled), the
held file that is its bytes, and the reviewed reader row ({audit, row}) that says what those bytes establish. This
runner reads no document and judges nothing: the verdict is the reviewed row's, checked as V1 checks it
(apply-vintage-creation-manifest.check_review, unchanged) - SAFE_TO_MAP, the document's own text naming exactly
this wine beside this year, the reader accepting it. --apply first runs the review audit's own --check, so a row is
accepted only while the existing reader still judges the document as the audit recorded.

THE DECISION is the store's ACCEPTED `guard` row (as v1-v5's and M3.10B's acceptances): its `read` the held bytes,
its `folder` the store and the digest (`acquisition:<sha256>`, as M3.10B's; `discovery:<sha256>`, as M3.6B's), its
evidence the reviewed row's rule and basis and the reader's verdict, its `reader` the decider fingerprint the row
names - which must be the current one (tools/m35_rubric.py, tools/web_evidence.py) when it is appended.

VERSIONS. The store's rule stands: new decisions append, old ones stay byte for byte, and the latest version of a
question (its row key without `v`) is its answer. v1-v9 were written by their phases and are closed
(CLOSED_THROUGH); a row names a later version - the store's newest, or the next one. Each row is APPEND (the
question is new, or this version supersedes an earlier answer), NOOP (the store holds exactly this decision) or
CONFLICT (the store holds another decision under the same key); a row asking a version older than the question's
latest answer is REJECT (stale), as is every invalid row. Any REJECT or CONFLICT stops the batch before anything is
written. Recording a decision creates no attribution, vintage or value: V1's vintage-creation manifest and M3.11's
value-application manifest consume it by its row key.
"""
import collections
import gzip
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import migration_lib as L  # noqa: E402
import evidence_store as ST  # noqa: E402
import mig_m6_provenance as M6  # noqa: E402

if os.environ.get('BDX_EVIDENCE_DIR'):            # an isolated copy of the store; the store's code is unchanged
    ST.DIR = os.path.abspath(os.environ['BDX_EVIDENCE_DIR']).replace('\\', '/').rstrip('/') + '/'
    ST.INDEX = ST.DIR + 'index.json'

ACTOR = 'tools/apply-evidence-acceptance-manifest.py'
RUNNER = 'apply-evidence-acceptance-manifest/1'
MANIFEST = 'data/audit/evidence-acceptance-manifest.jsonl'
REQUIRED = ('acceptance_id', 'artifact_id', 'estate_id', 'wine_id', 'vintage', 'decision', 'evidence_version',
            'reader', 'review', 'read', 'document_name')
OPTIONAL = ('notes',)
DECISIONS = {'ACCEPTED'}
CLOSED_THROUGH = 9          # v1-v5 the reader's passes, v6 M3.6B, v7 M3.6E, v8 M3.6H, v9 M3.10B
# The held stores a decision's bytes may be read from, as `<store>:<sha256>` folders: M3.8's acquisition store
# (M3.10B) and the discovery store (M3.6B). Neither occurs in v1-v5, so their questions are read from v6 on.
FOLDER_STORES = ('acquisition', 'discovery')
FOLDERS_FROM = 6
# The review audits' own checks: each recomputes its rows with the existing reader and compares them.
REVIEW_CHECKS = {'data/audit/m3.9-evidence-review.jsonl': ['tools/m39-evidence-review.py', '--check']}
DECIDER_FILES = ('tools/m35_rubric.py', 'tools/web_evidence.py')
ACTIONS = ('APPEND', 'NOOP', 'CONFLICT')


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, L.ROOT + rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


V = _load('apply_vintage_creation_manifest_ea', 'tools/apply-vintage-creation-manifest.py')   # V1, unchanged


def decider_fingerprint():
    """The decider's fingerprint, as M3.6B-M3.10B recorded it (tools/m36e-apply.py decider_fingerprint)."""
    h = hashlib.sha1()
    for f in DECIDER_FILES:
        h.update(open(L.ROOT + f, 'rb').read())
    return h.hexdigest()[:12]


def load_manifest(path):
    return L.jsonl_lines(path) if os.path.exists(path) else []


class Invalid(Exception):
    pass


class Conflict(Exception):
    pass


class Store:
    """The store's decisions of the versions a `<store>:<sha256>` question can occur in, by row key, and the latest
    answer to each question - read once."""

    def __init__(self):
        self.versions = ST.versions()
        self.readers = {int(v): m.get('readers', []) for v, m in ST._load_index().get('versions', {}).items()}
        self.by_key, self.latest = {}, {}
        for d in ST.iter_rows([v for v in self.versions if v >= FOLDERS_FROM]):
            k = M6.row_key(d)
            self.by_key[k] = d
            q = L.dumps(json.loads(k)[:-1])
            if q not in self.latest or (d.get('v') or 0) >= (self.latest[q].get('v') or 0):
                self.latest[q] = d


def held(path):
    """The bytes of a held file under sources/ (a .gz is the bytes it compresses, as M3.6B reads it)."""
    p = L.ROOT + 'sources/' + path
    if '..' in path.split('/') or not os.path.isfile(p):
        raise Invalid('the held file sources/%s is missing' % path)
    b = open(p, 'rb').read()
    return gzip.decompress(b) if path.endswith('.gz') else b


# ---------------------------------------------------------------- validate

def identity(r, ix):
    """The estate and its grand vin, as V1 requires them: (estate slug, the wine's one current name)."""
    e, w = r['estate_id'], r['wine_id']
    if e not in ix['estates']:
        raise Invalid('estate %s does not exist' % e)
    if w not in ix['wines']:
        raise Invalid('wine %s does not exist' % w)
    if (e, w) not in ix['estate_wine']:
        raise Invalid('wine %s does not belong to estate %s' % (w, e))
    if ix['grand'].get(w) is None or ix['grand'][w] != ix['estate_slug'].get(e):
        raise Invalid('wine %s is not the grand vin of estate %s (the decision asks the grand-vin question)' % (w, e))
    if w in ix['ambiguous']:
        raise Invalid('wine %s is a candidate of an ambiguous identity' % w)
    if e in ix['open_estates']:
        raise Invalid('estate %s has an open identity finding' % e)
    if w in ix['transitions'] or ix['wines'][w].get('name_status') != 'KNOWN' or len(ix['names'][w]) != 1:
        raise Invalid('wine %s has no single, settled current name' % w)
    return ix['estate_slug'][e], ix['names'][w][0]


def names_of(view):
    """{artifact: {basename of each of its locators}}: the names a decision may give the document."""
    out = collections.defaultdict(set)
    for p in view.table('document/placements.jsonl'):
        if p.get('artifact'):
            out[p['artifact']].add(p['locator']['value'].rstrip('/').rsplit('/', 1)[-1])
    return out


def decision_of(r, slug, wine_name, sha, n, rv, git=None):
    """The store row the manifest row asks for (M3.10B's representation), with `git` the state it is written in."""
    y = r['vintage']
    [c] = [c for c in rv['claims'] if c.get('disposition') == 'SAFE_TO_MAP']
    ev = c['evidence_of_document']
    read = {'path': r['read']['path'], 'sha256': sha, 'bytes': n}
    if r['read'].get('extraction'):
        read['extraction'] = r['read']['extraction']
    return {'artifact': r['document_name'], 'kind': 'guard',
            'ctx': {'estate': slug, 'folder': '%s:%s' % (r['read']['path'].split('/', 1)[0], sha), 'wine': None,
                    'vintage': y, 'target_wine': wine_name, 'target_role': 'grand', 'target_vintage': y,
                    'evaluated_as': '%s, vintage %d' % (wine_name, y)},
            'decision': r['decision'], 'code': r['decision'], 'raw': '',
            'evidence': ['%s rule: %s' % (ev['rule'], ev['basis']),
                         'whose_sheet with year=%d, is_second=False: %s' % (y, c['reader']['decision']),
                         'reviewed reader row %s (%s): %s; artifact %s; evidence acceptance %s' % (
                             r['review']['row'], r['review']['audit'], rv['disposition'], r['artifact_id'],
                             r['acceptance_id'])],
            'points_at': {'role': None, 'wine': None},
            'read': read, 'git': git, 'reader': r['reader'], 'v': r['evidence_version'], 're_evaluable': True}


def validate_manifest(rows, view, store, reviews=None, last=None, read_bytes=True):
    """Every problem with the manifest, read-only: ([error], {acceptance_id: the decision it asks for})."""
    errors, resolved = [], {}
    ix = view.index()
    reviews = reviews or V.Reviews()
    last = last or V.last_year()
    names = names_of(view)
    ids = collections.Counter(r.get('acceptance_id') for r in rows)
    newest = store.versions[-1] if store.versions else 0
    keys = collections.defaultdict(list)
    for n, r in enumerate(rows, 1):
        aid = r.get('acceptance_id') if isinstance(r.get('acceptance_id'), str) else 'row %d' % n

        def bad(msg):
            errors.append('%s: %s' % (aid, msg))
        missing = [k for k in REQUIRED if k not in r]
        extra = sorted(set(r) - set(REQUIRED) - set(OPTIONAL))
        if missing or extra:
            bad('missing %s; unknown %s' % (missing, extra))
            continue
        before = len(errors)
        if not re.fullmatch(r'eam_\d{6}', str(r['acceptance_id'])):
            bad('acceptance_id is not eam_NNNNNN')
        if ids[r['acceptance_id']] > 1:
            bad('acceptance_id used %d times' % ids[r['acceptance_id']])
        if r['decision'] not in DECISIONS:
            bad('decision %r: this mechanism records %s' % (r['decision'], sorted(DECISIONS)))
        if not re.fullmatch(r'[0-9a-f]{12}', str(r['reader'])):
            bad('reader %r is not a decider fingerprint' % (r['reader'],))
        v, y = r['evidence_version'], r['vintage']
        if not isinstance(v, int) or isinstance(v, bool) or v <= CLOSED_THROUGH:
            bad('evidence_version %r: v1-v%d are closed (written by their phases)' % (v, CLOSED_THROUGH))
        elif v not in store.versions and v != newest + 1:
            bad('evidence_version %d is neither the store\'s newest (v%d) nor the next' % (v, newest))
        elif v in store.versions and store.readers.get(v) != [r['reader']]:
            bad('v%d was written by reader %s, not %s: a changed reader is a new version' % (
                v, store.readers.get(v), r['reader']))
        if not isinstance(y, int) or isinstance(y, bool) or not V.FIRST_YEAR <= y <= last:
            bad('vintage %r is not a year in %d-%d' % (y, V.FIRST_YEAR, last))
        rd, rev = r['read'], r['review']
        if not (isinstance(rd, dict) and set(rd) <= {'path', 'extraction'} and isinstance(rd.get('path'), str)
                and rd['path'].split('/', 1)[0] in FOLDER_STORES):
            bad('read must be {path[, extraction]} under one of the held stores %s' % (FOLDER_STORES,))
        if not (isinstance(rev, dict) and set(rev) == {'audit', 'row'}):
            bad('review must be an {audit, row} reference')
        if len(errors) > before:
            continue
        try:
            slug, wine_name = identity(r, ix)
            art = ix['artifacts'].get(r['artifact_id'])
            if art is None:
                raise Invalid('artifact %s does not exist' % r['artifact_id'])
            if not art.get('bytes_available') or not art.get('sha256'):
                raise Invalid('artifact %s: its bytes are not held' % r['artifact_id'])
            sha = art['sha256']
            if r['document_name'] not in names[r['artifact_id']]:
                raise Invalid('artifact %s is not placed under the name %r (its names: %s)' % (
                    r['artifact_id'], r['document_name'], sorted(names[r['artifact_id']])))
            size = art.get('bytes')
            if read_bytes:
                b = held(rd['path'])
                if hashlib.sha256(b).hexdigest() != sha:
                    raise Invalid('sources/%s is not the bytes of artifact %s' % (rd['path'], r['artifact_id']))
                size = len(b)
                if rd.get('extraction'):
                    held(rd['extraction'])
            if size is None or (art.get('bytes') is not None and art['bytes'] != size):
                raise Invalid('the size of artifact %s is not established' % r['artifact_id'])
            if rev['audit'] not in REVIEW_CHECKS:
                raise Invalid('review audit %s has no recorded check (%s)' % (rev['audit'], sorted(REVIEW_CHECKS)))
            rv = reviews.get(rev['audit'], rev['row'])
            try:
                V.check_review(rv, sha, r['estate_id'], r['wine_id'], y)
            except V.Invalid as x:
                raise Invalid('review %s: %s' % (rev['row'], x))
            [c] = [c for c in rv['claims'] if c.get('disposition') == 'SAFE_TO_MAP']
            if (c.get('evidence_of_document') or {}).get('kind') != 'DOCUMENT':
                raise Invalid('review %s is of a web page: the guard representation is a document\'s' % rev['row'])
            d = decision_of(r, slug, wine_name, sha, size, rv)
            k = M6.row_key(d)
            keys[k].append(r['acceptance_id'])
            resolved[r['acceptance_id']] = {'decision': d, 'key': k}
        except Invalid as x:
            bad(str(x))
    for k, where in sorted(keys.items()):
        if len(where) > 1:
            errors.append('%s: ask the same question at the same version %s' % (sorted(where), k))
    return errors, resolved


# ---------------------------------------------------------------- plan

def same(a, b):
    """One decision, but for the git state it was written in."""
    return {k: x for k, x in a.items() if k != 'git'} == {k: x for k, x in b.items() if k != 'git'}


def classify(r, res, store, current):
    """(action, reason) for one valid row against the store; REJECT raised as Invalid."""
    d, k = res['decision'], res['key']
    held_d = store.by_key.get(k)
    if held_d is not None:
        if same(held_d, d):
            return 'NOOP', 'the store holds this decision (v%d)' % d['v']
        diff = sorted(x for x in set(d) | set(held_d) if x != 'git' and d.get(x) != held_d.get(x))
        return 'CONFLICT', 'v%d holds another decision for this question (%s)' % (d['v'], ', '.join(diff))
    q = L.dumps(json.loads(k)[:-1])
    lat = store.latest.get(q)
    if lat is not None and (lat.get('v') or 0) > d['v']:
        raise Invalid('stale: the question is answered at v%d (%s), later than v%d' % (lat['v'], lat.get('decision'), d['v']))
    if r['reader'] != current:
        raise Invalid('the decider is now %s, not %s: an appended decision records the decider that decides' % (
            current, r['reader']))
    if lat is not None:
        return 'APPEND', 'supersedes v%d (%s)' % (lat['v'], lat.get('decision'))
    return 'APPEND', 'a new question'


def plan_manifest(rows, resolved, store, current=None):
    """The deterministic plan, read-only: rows in (version, key, id) order, each with its action; ([error], plan)."""
    current = current or decider_fingerprint()
    items, counts, errors = [], collections.Counter(), []
    for r in sorted(rows, key=lambda r: (r['evidence_version'], resolved[r['acceptance_id']]['key'], r['acceptance_id'])):
        res = resolved[r['acceptance_id']]
        try:
            action, reason = classify(r, res, store, current)
        except Invalid as x:
            errors.append('%s: %s' % (r['acceptance_id'], x))
            continue
        counts[action] += 1
        items.append({'acceptance_id': r['acceptance_id'], 'artifact': r['artifact_id'], 'estate': r['estate_id'],
                      'wine': r['wine_id'], 'vintage': r['vintage'], 'version': r['evidence_version'], 'key': res['key'],
                      'review': r['review'], 'action': action, 'reason': reason, 'decision': res['decision']})
    return errors, {'rows': items, 'actions': {a: counts[a] for a in ACTIONS}}


def verify_plan(plan):
    conflicts = ['%s %s: %s' % (it['acceptance_id'], it['key'], it['reason'])
                 for it in plan['rows'] if it['action'] == 'CONFLICT']
    if conflicts:
        raise Conflict('%d conflict(s):\n  %s' % (len(conflicts), '\n  '.join(conflicts)))


# ---------------------------------------------------------------- writing (--apply) and checking

def review_audits_current(plan):
    """Each review audit an APPEND rests on passes its own check (the existing reader, recomputed)."""
    audits = sorted({it['review']['audit'] for it in plan['rows'] if it['action'] == 'APPEND'})
    for a in audits:
        out = subprocess.run([sys.executable, L.ROOT + REVIEW_CHECKS[a][0]] + REVIEW_CHECKS[a][1:], cwd=L.ROOT,
                             capture_output=True, text=True)
        if out.returncode:
            raise Conflict('review audit %s is not current: %s' % (a, out.stdout.strip()[-300:]))
    return audits


def apply_plan(plan, git=None):
    """Append the plan's APPEND decisions, each version in turn, through the store's only writer. {version: n}."""
    import provenance as PV
    git = git or PV.git_state(L.ROOT)
    by_v = collections.defaultdict(list)
    for it in plan['rows']:
        if it['action'] == 'APPEND':
            by_v[it['version']].append(dict(it['decision'], git=git))
    out = {}
    for v in sorted(by_v):
        n = ST.append(by_v[v], v)
        if n != len(by_v[v]):
            raise Conflict('v%d took %d of %d decision(s)' % (v, n, len(by_v[v])))
        out[v] = n
    return out


def in_head(commit):
    return subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=L.ROOT,
                          capture_output=True).returncode == 0


def check(plan, store):
    """The store holds every row (each NOOP, written at a commit in HEAD's history), and every decision of the
    versions this mechanism writes is a manifest row's."""
    items = (plan or {'rows': []})['rows']
    pending = ['%s %s %s' % (it['acceptance_id'], it['key'], it['action']) for it in items if it['action'] != 'NOOP']
    written = {it['acceptance_id']: ((store.by_key.get(it['key']) or {}).get('git') or {}).get('commit')
               for it in items if it['action'] == 'NOOP'}
    ok = {c for c in set(written.values()) if c and in_head(c)}      # one git call per commit, not per row
    for aid, c in sorted(written.items()):
        if c not in ok:
            pending.append('%s: written at %s, not in HEAD\'s history' % (aid, c))
    named = {it['key'] for it in items}
    stray = sorted(k for k, d in store.by_key.items() if (d.get('v') or 0) > CLOSED_THROUGH and k not in named)
    if stray:
        pending.append('%d decision(s) in v%d+ that no manifest row names: %s' % (len(stray), CLOSED_THROUGH + 1, stray[:3]))
    unsound = ST.verify()
    if unsound:
        pending.append('the store does not verify: %s' % unsound[:3])
    return pending


# ---------------------------------------------------------------- output and main

def render_plan(plan, n_rows):
    out = []
    for it in (plan or {'rows': []})['rows']:
        out.append('%s  %s %s %d  (v%d)' % (it['acceptance_id'], it['artifact'], it['wine'], it['vintage'], it['version']))
        out.append('  question: %s' % it['key'])
        out.append('  action: %s (%s)' % (it['action'], it['reason']))
        out.append('')
    a = (plan or {}).get('actions') or {k: 0 for k in ACTIONS}
    out.append('%d manifest row(s): %s' % (n_rows, ', '.join('%d %s' % (a[k], k) for k in ACTIONS)))
    out.append('%d decision(s) to append; 0 attributions, 0 vintages, 0 values' % a.get('APPEND', 0))
    return '\n'.join(out) + '\n'


def main():
    args = sys.argv[1:]
    VR = V.VR
    clock = VR.Clock()
    mode = next((a for a in ('--apply', '--plan', '--check', '--validate') if a in args), '--validate')
    path = os.path.abspath(args[args.index('--manifest') + 1]) if '--manifest' in args else L.ROOT + MANIFEST
    try:
        view = V.View()
        view.index()
        view.table('document/placements.jsonl')
        clock.mark('model loading')
        store = Store()
        clock.mark('evidence loading')
        rows = load_manifest(path)
        errors, resolved = validate_manifest(rows, view, store) if rows else ([], {})
        clock.mark('manifest validation')
        if errors:
            raise SystemExit('%d problem(s); nothing was written:\n  %s' % (len(errors), '\n  '.join(errors)))
        errors, plan = plan_manifest(rows, resolved, store) if rows else ([], None)
        clock.mark('plan construction')
        if errors:
            raise SystemExit('%d problem(s); nothing was written:\n  %s' % (len(errors), '\n  '.join(errors)))
        if mode == '--validate':
            L.out('%d manifest row(s) valid' % len(rows))
        elif mode == '--plan':
            sys.stdout.write(render_plan(plan, len(rows)))
            if plan and plan['actions']['CONFLICT']:
                raise SystemExit('the plan has %d CONFLICT row(s): --apply would refuse it' % plan['actions']['CONFLICT'])
        elif mode == '--apply':
            if plan:
                verify_plan(plan)
            if not plan or not plan['actions']['APPEND']:
                L.out('nothing to apply: %d row(s), all held (NOOP)' % len(rows))
                return
            review_audits_current(plan)
            clock.mark('plan verification')
            n = apply_plan(plan)
            clock.mark('evidence-store write')
            L.out('applied: %d APPEND; %d NOOP' % (plan['actions']['APPEND'], plan['actions']['NOOP']))
            for v, k in sorted(n.items()):
                L.out('  v%d  +%d decision(s)' % (v, k))
        elif mode == '--check':
            pending = check(plan, store)
            clock.mark('deterministic checking')
            if pending:
                raise SystemExit('the store does not hold the manifest:\n  %s' % '\n  '.join(pending))
            L.out('evidence-acceptance manifest: %d row(s) held by the store' % len(rows))
    except (Conflict, Invalid) as x:
        raise SystemExit('%s\nnothing was written' % x)
    finally:
        if '--timings' in args:
            sys.stderr.write(clock.report() + '\n')


if __name__ == '__main__':
    main()
