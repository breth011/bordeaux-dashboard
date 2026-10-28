"""V1: new-vintage creation - a grand vin's vintage shell and its existence attributions, from a reviewed manifest.

    python tools/apply-vintage-creation-manifest.py                validate (the default; read-only)
    python tools/apply-vintage-creation-manifest.py --validate     validate the manifest against the model, the review
                                                                   audits and the evidence store
    python tools/apply-vintage-creation-manifest.py --plan         the deterministic plan (read-only)
    python tools/apply-vintage-creation-manifest.py --apply        validate -> plan -> verify -> write; all or nothing
    python tools/apply-vintage-creation-manifest.py --check        the model holds every manifest row as its plan says
    python tools/apply-vintage-creation-manifest.py --check-all    --check, and the migration, indexes and app rebuild
  options: --manifest <file> (default data/audit/vintage-creation-manifest.jsonl); --timings
  BDX_MODEL_DIR points it at another model directory (an isolated copy).

docs/NEW-VINTAGE-CREATION-DESIGN.md is the contract; docs/PHASE-V1-VINTAGE-CREATION.md the implementation. A row
(vcm_NNNNNN) asks that vintage Y of the grand vin W of estate E exist, on the strength of artifacts whose own text
names W beside Y. It holds references only: each artifact's evidence decision (the store's row key) and its
reviewed reader row ({audit, row}); the basis is read from that row, never copied. No value is in it: values go
through the value-application manifest (tools/apply-value-manifest.py) once the vintage exists.

Each valid row is CREATE (no vintage: the shell, then an existence attribution per artifact), ATTRIBUTION_ONLY
(the vintage exists without an exact existence attribution for some artifact: those attributions only), NOOP
(every exact attribution held) or CONFLICT (the model says NOT_PRODUCED, or an artifact is ACCEPTED-attributed to
another vintage or wine); an invalid row is REJECT. Any REJECT or CONFLICT stops the batch before anything is
written. The shell is {wine, label}; the attribution is M3.10B's shape (DOCUMENT_TEXT, ACCEPTED, FIRST) on a
DOCUMENT provenance naming the decision, which is what the value runner's evidence chain reads. Nothing else is
created: no estate, wine, name, identity key, transition, statement, observation or value.

The migration applies the same plan: mig_m5_vintages.vintage_creation adds the shells (recording the vintages it
created as an M5 stat - a vintage row carries no provenance) and mig_m6_provenance.vintage_creation_attributions
the attributions, so a rebuild writes what --apply wrote. An empty manifest adds nothing and records nothing.
"""
import collections
import datetime
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_cache as CC  # noqa: E402
import migration_lib as L  # noqa: E402
import model_schema as S  # noqa: E402

ACTOR = 'tools/apply-vintage-creation-manifest.py'
RUNNER = 'apply-vintage-creation-manifest/1'
STREAM = 'vintage-creation'
MANIFEST = 'data/audit/vintage-creation-manifest.jsonl'
VINTAGE_STAT = 'vintage-creation manifest vintages'           # M5: the vintage refs the mechanism created
ATTRIBUTION_STAT = 'vintage-creation manifest attributions'   # M6: the existence attributions it added
REQUIRED = ('manifest_id', 'estate_id', 'wine_id', 'vintage', 'artifact_ids', 'evidence_version',
            'evidence_decisions', 'review', 'creation_class')
OPTIONAL = ('notes',)
CLASSES = {'EXPLICIT_DOCUMENT_TEXT'}
# The reviewed reader rows a creation may rest on: M3.9's review format (the existing prerequisite path for an
# acquired document), each row the reader's own verdict on the document's text. Another review audit is added
# here, by name, when a later phase produces one.
REVIEW_AUDITS = {'data/audit/m3.9-evidence-review.jsonl': 'm3.9'}
TEXT_RULES = {'M34A', 'T'}                     # a document's own text: M34A (names the wine beside the year), T1-T7
TEXT_PAGE_SOURCES = {'h1'}                     # a web page's own main heading (W1-W6)
TEXT_VINTAGE = ('statement ', 'wine and year ')  # the year as the document states it (M3.8's vintage basis)
OPEN_IDENTITY = {'IDENTITY_UNCERTAIN', 'AMBIGUOUS_SEMANTICS', 'CONFLICT'}
FIRST_YEAR = 1950
TABLES = ('cross/provenance.jsonl', 'document/attributions.jsonl', 'identity/vintages.jsonl')
ACTIONS = ('CREATE', 'ATTRIBUTION_ONLY', 'NOOP', 'CONFLICT')


def last_year():
    """The next calendar year: a vintage a document can state today. Read when a row is validated; a row valid
    then stays valid on every later rebuild, and the year enters no model row."""
    return datetime.date.today().year + 1


def _value_runner():
    spec = importlib.util.spec_from_file_location('apply_value_manifest', L.ROOT + 'tools/apply-value-manifest.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


VR = _value_runner()        # the value runner's evidence loading and clock, reused unchanged


def _migrate():
    import migrate
    return migrate


def load_manifest(path):
    return L.jsonl_lines(path) if os.path.exists(path) else []


def vref(wine, vintage):
    return S.vref(wine, str(vintage))


# ---------------------------------------------------------------- the model, the reviews and the evidence

class View:
    """The model's tables, each read once: from a migration's in-memory model, or from the model directory."""

    def __init__(self, rows=None):
        self._rows = rows or L.read_table
        self._t = {}
        self._ix = None

    def table(self, rel):
        if rel not in self._t:
            self._t[rel] = self._rows(rel)
        return self._t[rel]

    def index(self):
        if self._ix is None:
            im = self.table('identity/identity-map.jsonl')
            att = collections.defaultdict(list)
            for a in self.table('document/attributions.jsonl'):
                if a.get('artifact') and a.get('status') == 'ACCEPTED':
                    att[a['artifact']].append(a)
            names = collections.defaultdict(list)
            for n in self.table('identity/names.jsonl'):
                if n['kind'] == 'CURRENT':
                    names[n['subject']].append(n['name'])
            self._ix = {
                'estates': {r['id'] for r in self.table('identity/estates.jsonl')},
                'wines': {r['id']: r for r in self.table('identity/wines.jsonl')},
                'names': names,
                'estate_slug': {r['stable_id']: r['legacy_key'] for r in im
                                if r['namespace'] == 'estate' and r['status'] == 'ACTIVE' and r.get('stable_id')},
                'grand': {r['stable_id']: r['legacy_key'] for r in im
                          if r['namespace'] == 'grand-vin' and r['status'] == 'ACTIVE' and r.get('stable_id')},
                'ambiguous': {w for r in im if r['status'] == 'AMBIGUOUS' for w in r.get('candidates') or []},
                'estate_wine': {(r['estate'], r['wine']) for r in self.table('state/estate-wine.jsonl')
                                if r.get('status') == 'ESTABLISHED'},
                'open_estates': {f['target'] for f in self.table('cross/findings.jsonl')
                                 if f['status'] == 'OPEN' and f['kind'] in OPEN_IDENTITY},
                'transitions': {x for t in self.table('identity/transitions.jsonl') for x in t.values()
                                if isinstance(x, str)},
                'vintages': {(r['wine'], r['label']) for r in self.table('identity/vintages.jsonl')},
                'not_produced': {r['vintage'] for r in self.table('state/vintage-statements.jsonl')
                                 if r['kind'] == 'NOT_PRODUCED'},
                'artifacts': {r['id']: r for r in self.table('identity/artifacts.jsonl')},
                'attributions': att,
                'prov': {p['id']: p for p in self.table('cross/provenance.jsonl')},
            }
        return self._ix


class Reviews:
    """The reviewed reader rows of the allowed review audits, by (audit, row id), each audit read once."""

    def __init__(self):
        self._rows = {}

    def get(self, audit, row):
        if audit not in REVIEW_AUDITS:
            return None
        if audit not in self._rows:
            prefix = REVIEW_AUDITS[audit]
            self._rows[audit] = {'%s:%d' % (prefix, r['n']): r for r in L.jsonl_lines(L.ROOT + audit)
                                 if r.get('record') == 'review' and isinstance(r.get('n'), int)}
        return self._rows[audit].get(row)


class Invalid(Exception):
    pass


class Conflict(Exception):
    pass


def check_review(rv, sha, estate, wine, year):
    """The reviewed reader row establishes, from the document's own text, this exact estate, grand vin and year."""
    if rv is None:
        raise Invalid('no reviewed reader row (the review audit is not one of %s, or the row is not in it)'
                      % sorted(REVIEW_AUDITS))
    if rv.get('sha256') != sha:
        raise Invalid('the reviewed row read other bytes')
    if (rv.get('disposition'), rv.get('category')) != ('SAFE_TO_MAP', 'ACCEPTED_EXACT_ESTATE_WINE_VINTAGE'):
        raise Invalid('the reader did not map it to one wine and vintage (%s, %s)' % (rv.get('disposition'),
                                                                                     rv.get('category')))
    if (rv.get('estate'), rv.get('wine'), rv.get('vintage')) != (estate, wine, year):
        raise Invalid('the reviewed row is for %s %s %s' % (rv.get('estate'), rv.get('wine'), rv.get('vintage')))
    claims = [c for c in rv.get('claims') or [] if c.get('disposition') == 'SAFE_TO_MAP']
    if [c.get('wine') for c in claims] != [wine]:
        raise Invalid('the reviewed row maps %d wine(s) %s, not exactly %s' % (len(claims), [c.get('wine') for c in claims], wine))
    [c] = claims
    if c.get('claim_year_dated') is not False:
        raise Invalid('the year stands in a dated line (a press or event date), not as the vintage')
    doc = c.get('evidence_of_document') or {}
    text = (doc.get('kind') == 'DOCUMENT' and doc.get('rule') in TEXT_RULES) or \
        (doc.get('kind') == 'WEB_PAGE' and (doc.get('page') or {}).get('identity_source') in TEXT_PAGE_SOURCES)
    if not text or rv.get('identity_source') not in TEXT_RULES | TEXT_PAGE_SOURCES:
        raise Invalid('identity is not established by the document\'s own text (%s)' % rv.get('identity_source'))
    if not str(rv.get('vintage_evidence') or '').startswith(TEXT_VINTAGE):
        raise Invalid('the vintage is not stated in the document (%r)' % rv.get('vintage_evidence'))
    if not (c.get('reader') or {}).get('decision') == 'ACCEPTED':
        raise Invalid('the reader did not accept it')


def check_decision(key, version, art, estate_slug, wine_name, year, ev):
    """The evidence decision is the store's, ACCEPTED at `version`, still the latest for its context, for the
    artifact's own bytes, and for this estate's grand vin and this year."""
    try:
        k = json.loads(key)
    except (TypeError, ValueError):
        raise Invalid('evidence decision %r is not a store row key' % (key,))
    if k[-1] != version:
        raise Invalid('evidence decision is of version %s, not %s' % (k[-1], version))
    d = ev.by_key.get(key)
    if d is None:
        raise Invalid('evidence decision is not in the store')
    if d.get('decision') != 'ACCEPTED':
        raise Invalid('evidence decision is %s, not ACCEPTED' % d.get('decision'))
    latest = ev.latest.get(L.dumps(k[:-1]))
    if latest is not d:
        raise Invalid('evidence decision superseded by version %s (%s)' % (latest.get('v'), latest.get('decision')))
    if (d.get('read') or {}).get('sha256') != art.get('sha256'):
        raise Invalid('evidence decision read other bytes than artifact %s' % art['id'])
    c = d.get('ctx') or {}
    if (c.get('estate'), c.get('target_wine'), c.get('target_role'), c.get('target_vintage')) != \
            (estate_slug, wine_name, 'grand', year):
        raise Invalid('evidence decision is for %s / %s / %s / %s' % (c.get('estate'), c.get('target_wine'),
                                                                     c.get('target_role'), c.get('target_vintage')))


# ---------------------------------------------------------------- validate

def validate_manifest(rows, view, ev=None, reviews=None, last=None):
    """Every problem with the manifest, read-only: ([error], {manifest_id: resolved})."""
    errors, resolved = [], {}
    ix = view.index()
    ev = ev or VR.Evidence({r.get('evidence_version') for r in rows})
    reviews = reviews or Reviews()
    last = last or last_year()
    ids = collections.Counter(r.get('manifest_id') for r in rows)
    claimed = collections.defaultdict(set)
    vintages = collections.defaultdict(list)
    for n, r in enumerate(rows, 1):
        mid = r.get('manifest_id') if isinstance(r.get('manifest_id'), str) else 'row %d' % n

        def bad(msg):
            errors.append('%s: %s' % (mid, msg))
        missing = [k for k in REQUIRED if k not in r]
        extra = sorted(set(r) - set(REQUIRED) - set(OPTIONAL))
        if missing or extra:
            bad('missing %s; unknown %s' % (missing, extra))
            continue
        if not re.fullmatch(r'vcm_\d{6}', str(r['manifest_id'])):
            bad('manifest_id is not vcm_NNNNNN')
        if ids[r['manifest_id']] > 1:
            bad('manifest_id used %d times' % ids[r['manifest_id']])
        if r['creation_class'] not in CLASSES:
            bad('creation_class %r is not one of %s' % (r['creation_class'], sorted(CLASSES)))
        e, w, y, v = r['estate_id'], r['wine_id'], r['vintage'], r['evidence_version']
        ok = True
        if e not in ix['estates']:
            bad('estate %s does not exist' % e)
            ok = False
        if w not in ix['wines']:
            bad('wine %s does not exist' % w)
            ok = False
        if ok:
            if (e, w) not in ix['estate_wine']:
                bad('wine %s does not belong to estate %s' % (w, e))
                ok = False
            elif ix['grand'].get(w) is None or ix['grand'][w] != ix['estate_slug'].get(e):
                bad('wine %s is not the grand vin of estate %s (V1 creates grand-vin vintages only)' % (w, e))
                ok = False
            elif w in ix['ambiguous']:
                bad('wine %s is a candidate of an ambiguous identity' % w)
                ok = False
            elif e in ix['open_estates']:
                bad('estate %s has an open identity finding' % e)
                ok = False
            elif w in ix['transitions'] or ix['wines'][w].get('name_status') != 'KNOWN' or len(ix['names'][w]) != 1:
                bad('wine %s has no single, settled current name' % w)
                ok = False
        if not isinstance(y, int) or isinstance(y, bool):
            bad('vintage %r is not a year' % (y,))
            ok = False
        elif not FIRST_YEAR <= y <= last:
            bad('vintage %d is outside %d-%d' % (y, FIRST_YEAR, last))
            ok = False
        arts, keys, revs = r['artifact_ids'], r['evidence_decisions'], r['review']
        if not (isinstance(arts, list) and arts and all(isinstance(a, str) for a in arts) and len(set(arts)) == len(arts)
                and isinstance(keys, dict) and set(keys) == set(arts) and isinstance(revs, dict) and set(revs) == set(arts)
                and all(isinstance(x, dict) and set(x) == {'audit', 'row'} for x in revs.values())):
            bad('artifact_ids, evidence_decisions and review must name the same distinct artifacts, '
                'each review a {audit, row} reference')
            ok = False
        if not isinstance(v, int) or v not in ev.versions:
            bad('evidence_version %r is not a version of the store' % (v,))
            ok = False
        if not ok:
            continue
        vt = vref(w, y)
        vintages[(w, y)].append(r['manifest_id'])
        rres = {'vintage': vt, 'evidence': {}, 'review': {}}
        for a in sorted(arts):
            claimed[a].add(vt)
            art = ix['artifacts'].get(a)
            try:
                if art is None:
                    raise Invalid('does not exist')
                if not art.get('bytes_available') or not art.get('sha256'):
                    raise Invalid('its bytes are not held')
                rv = reviews.get(revs[a]['audit'], revs[a]['row'])
                check_review(rv, art['sha256'], e, w, y)
                check_decision(keys[a], v, art, ix['estate_slug'][e], ix['names'][w][0], y, ev)
                rres['evidence'][a], rres['review'][a] = keys[a], dict(rv, _ref=revs[a])
            except Invalid as x:
                bad('artifact %s: %s' % (a, x))
        if len(rres['evidence']) == len(arts):
            resolved[r['manifest_id']] = rres
    for (w, y), where in sorted(vintages.items()):
        if len(where) > 1:
            errors.append('%s: requested by %s' % (vref(w, y), sorted(where)))
    for a, vts in sorted(claimed.items()):
        if len(vts) > 1:
            errors.append('artifact %s claimed for %s' % (a, sorted(vts)))
    return errors, resolved


# ---------------------------------------------------------------- plan

def attribution_id(a, vt):
    return S.hid('Attribution', a, 'vcm', vt)


def exact(ix, a, e, w, vt, key):
    """An ACCEPTED attribution of `a` to exactly this estate, wine and vintage whose provenance names `key`."""
    for x in ix['attributions'].get(a, []):
        cs = (ix['prov'].get(x['provenance']) or {}).get('code_state') or {}
        if (x.get('estate'), x.get('wine'), x.get('vintage'), x.get('method')) == (e, w, vt, 'DOCUMENT_TEXT') \
                and key in (cs.get('evidence_decisions') or []):
            return True
    return False


def classify(r, res, ix):
    """(action, reason, artifacts needing an existence attribution) for one valid row against the model."""
    e, w, vt = r['estate_id'], r['wine_id'], res['vintage']
    if vt in ix['not_produced']:
        return 'CONFLICT', 'the model states %s NOT_PRODUCED' % vt, []
    for a in sorted(r['artifact_ids']):
        other = sorted({(x.get('wine'), x.get('vintage')) for x in ix['attributions'].get(a, [])
                        if (x.get('wine'), x.get('vintage')) != (w, vt)}, key=str)
        if other:
            return 'CONFLICT', 'artifact %s is ACCEPTED-attributed to %s' % (a, other), []
    missing = [a for a in sorted(r['artifact_ids']) if not exact(ix, a, e, w, vt, res['evidence'][a])]
    if (w, vt.rsplit(':', 1)[1]) not in ix['vintages']:
        return 'CREATE', 'no vintage %s' % vt, missing
    if missing:
        return 'ATTRIBUTION_ONLY', 'the vintage exists; no existence attribution for %s' % missing, missing
    return 'NOOP', 'the vintage and its existence attributions are held', []


def add_shell(m, r):
    m.add('identity/vintages.jsonl', {'wine': r['wine_id'], 'label': str(r['vintage'])})


def add_attribution(m, r, res, a, ix):
    vt, rv = res['vintage'], res['review'][a]
    pid = m.prov('DOCUMENT', ACTOR, artifact=a, quote=rv['reason'],
                 code_state={'stream': STREAM, 'runner': RUNNER, 'manifest': MANIFEST, 'manifest_id': r['manifest_id'],
                             'review': rv['_ref']['audit'], 'candidate': rv['_ref']['row'],
                             'evidence_decisions': [res['evidence'][a]], 'evidence_version': r['evidence_version'],
                             'identity_source': rv['identity_source'], 'vintage_source': rv['vintage_evidence'],
                             'sha256': ix['artifacts'][a]['sha256']})
    m.add('document/attributions.jsonl', {
        'id': attribution_id(a, vt), 'artifact': a, 'estate': r['estate_id'], 'wine': r['wine_id'], 'vintage': vt,
        'role': 'FIRST', 'method': 'DOCUMENT_TEXT', 'status': 'ACCEPTED', 'provenance': pid})


def plan_manifest(rows, resolved, view):
    """The deterministic plan, read-only: rows in (estate, wine, vintage, id) order, each with its action and,
    for CREATE and ATTRIBUTION_ONLY, the rows it adds."""
    mig = _migrate()
    ix = view.index()
    items, counts, added = [], collections.Counter(), collections.Counter()
    for r in sorted(rows, key=lambda r: (r['estate_id'], r['wine_id'], r['vintage'], r['manifest_id'])):
        res = resolved[r['manifest_id']]
        action, reason, missing = classify(r, res, ix)
        adds = {}
        if action in ('CREATE', 'ATTRIBUTION_ONLY'):
            scratch = mig.Model()
            if action == 'CREATE':
                add_shell(scratch, r)
            for a in missing:
                add_attribution(scratch, r, res, a, ix)
            adds = {rel: sorted(scratch.tables[rel].values(), key=lambda x: L.dumps(scratch.key(rel, x)))
                    for rel in sorted(scratch.tables)}
        counts[action] += 1
        for rel, xs in adds.items():
            added[rel] += len(xs)
        items.append({'manifest_id': r['manifest_id'], 'estate': r['estate_id'], 'wine': r['wine_id'],
                      'vintage': r['vintage'], 'vintage_ref': res['vintage'], 'artifacts': sorted(r['artifact_ids']),
                      'action': action, 'reason': reason, 'adds': adds})
    return {'rows': items, 'actions': {a: counts[a] for a in ACTIONS}, 'adds': dict(sorted(added.items()))}


def verify_plan(plan):
    conflicts = ['%s %s: %s' % (it['manifest_id'], it['vintage_ref'], it['reason'])
                 for it in plan['rows'] if it['action'] == 'CONFLICT']
    if conflicts:
        raise Conflict('%d conflict(s):\n  %s' % (len(conflicts), '\n  '.join(conflicts)))
    assert set(plan['adds']) <= set(TABLES), 'the plan touches %s' % sorted(set(plan['adds']) - set(TABLES))
    for it in plan['rows']:
        got = {rel: len(xs) for rel, xs in it['adds'].items()}
        if it['action'] == 'CREATE':
            n = got.get('document/attributions.jsonl', 0)
            assert got.get('identity/vintages.jsonl') == 1 and got.get('cross/provenance.jsonl') == n, it['manifest_id']
        elif it['action'] == 'ATTRIBUTION_ONLY':
            assert 'identity/vintages.jsonl' not in got and got['cross/provenance.jsonl'] == \
                got['document/attributions.jsonl'] >= 1, it['manifest_id']
        else:
            assert not got, it['manifest_id']


def apply_plan(m, plan, shells=True, attributions=True):
    """Add the plan's rows to migrate.Model `m`: the shells, the attributions, or both. (vintage refs created,
    attributions added)."""
    created, n = [], 0
    for it in plan['rows']:
        for rel in sorted(it['adds']):
            if rel == 'identity/vintages.jsonl' and not shells:
                continue
            if rel in ('document/attributions.jsonl', 'cross/provenance.jsonl') and not attributions:
                continue
            for x in it['adds'][rel]:
                m.add(rel, x)
            if rel == 'identity/vintages.jsonl':
                created.append(it['vintage_ref'])
            if rel == 'document/attributions.jsonl':
                n += len(it['adds'][rel])
    return created, n


def prepared(view, path=None, ev=None, reviews=None, last=None):
    """(rows, plan) for the manifest against `view`, or SystemExit naming every problem."""
    rows = load_manifest(path or L.ROOT + MANIFEST)
    if not rows:
        return rows, None
    errors, resolved = validate_manifest(rows, view, ev, reviews, last)
    if errors:
        raise SystemExit('vintage-creation manifest: %d problem(s); nothing was written:\n  %s' % (
            len(errors), '\n  '.join(errors)))
    plan = plan_manifest(rows, resolved, view)
    try:
        verify_plan(plan)
    except Conflict as x:
        raise SystemExit('vintage-creation manifest: %s\nnothing was written' % x)
    return rows, plan


# ---------------------------------------------------------------- the migration's hooks

def m5_hook(m, **kw):
    """mig_m5_vintages.vintage_creation: the shells of the rows whose vintage the model being built lacks; the
    vintage refs created are recorded as an M5 stat (only when there is one)."""
    _, plan = prepared(View(m.rows), **kw)
    if plan:
        created, _ = apply_plan(m, plan, attributions=False)
        if created:
            m.stat('M5', VINTAGE_STAT, sorted(created))


def m6_hook(m, **kw):
    """mig_m6_provenance.vintage_creation_attributions: each row's missing existence attributions."""
    _, plan = prepared(View(m.rows), **kw)
    if plan:
        _, n = apply_plan(m, plan, shells=False)
        if n:
            m.stat('M6', ATTRIBUTION_STAT, n)


# ---------------------------------------------------------------- writing (--apply)

def render_tables(view, plan):
    """{relpath: bytes} for the three tables and the model manifest with the plan applied, as migrate renders."""
    mig = _migrate()
    m = mig.Model()
    for rel in TABLES:
        for r in view.table(rel):
            m.add(rel, r)
    created, n = apply_plan(m, plan)
    man = json.load(open(L.MODEL + mig.MANIFEST, encoding='utf-8'), object_pairs_hook=collections.OrderedDict)
    files = {}
    for rel in TABLES:
        rows = sorted(m.tables[rel].values(), key=lambda r: L.dumps(m.key(rel, r)))
        b = ''.join(L.dumps(r) + '\n' for r in rows).encode('utf-8')
        files[rel] = b
        man['files'][rel]['rows'] = len(rows)
        man['files'][rel]['sha256'] = hashlib.sha256(b).hexdigest()
    if created:
        m5 = man['stats'].setdefault('M5', collections.OrderedDict())
        m5[VINTAGE_STAT] = sorted(set(m5.get(VINTAGE_STAT, [])) | set(created))
    if n:
        m6 = man['stats'].setdefault('M6', collections.OrderedDict())
        m6[ATTRIBUTION_STAT] = m6.get(ATTRIBUTION_STAT, 0) + n
    files[mig.MANIFEST] = (json.dumps(man, ensure_ascii=False, indent=1) + '\n').encode('utf-8')
    return files


def apply_manifest(view, plan, clock=None):
    """Write the plan: every file computed first, then each replaced; then the indexes rebuilt."""
    files = render_tables(view, plan)
    if clock:
        clock.mark('application')
    VR.write_files(files)
    subprocess.run([sys.executable, L.ROOT + 'tools/build-indexes.py'], cwd=L.ROOT, env=dict(os.environ), check=True,
                   stdout=subprocess.DEVNULL)
    if clock:
        clock.mark('output generation (indexes)')


def check(plan):
    """The model holds every row (each NOOP), and its stats count exactly what the mechanism made."""
    pending = ['%s %s %s' % (it['manifest_id'], it['vintage_ref'], it['action']) for it in (plan or {'rows': []})['rows']
               if it['action'] != 'NOOP']
    man = json.load(open(L.MODEL + 'manifest.json', encoding='utf-8'))
    prov = {p['id']: p for p in L.read_table('cross/provenance.jsonl')}
    mine = sum(1 for a in L.read_table('document/attributions.jsonl')
               if (prov.get(a['provenance']) or {}).get('actor') == ACTOR)
    if man['stats'].get('M6', {}).get(ATTRIBUTION_STAT, 0) != mine:
        pending.append('the model manifest counts %s existence attribution(s), the model holds %d' % (
            man['stats'].get('M6', {}).get(ATTRIBUTION_STAT, 0), mine))
    vts = {'vt:%s:%s' % (v['wine'], v['label']) for v in L.read_table('identity/vintages.jsonl')}
    lost = sorted(set(man['stats'].get('M5', {}).get(VINTAGE_STAT, [])) - vts)
    if lost:
        pending.append('created vintages missing from the model: %s' % lost)
    return pending


# ---------------------------------------------------------------- output and main

def render_plan(plan, n_rows):
    out = []
    for it in (plan or {'rows': []})['rows']:
        out.append('%s  %s  (%s, %s)' % (it['manifest_id'], it['vintage_ref'], it['estate'], it['wine']))
        out.append('  artifacts: %s' % ', '.join(it['artifacts']))
        out.append('  action: %s (%s)' % (it['action'], it['reason']))
        out.append('')
    a = (plan or {}).get('actions') or {k: 0 for k in ACTIONS}
    adds = (plan or {}).get('adds') or {}
    out.append('%d manifest row(s): %s' % (n_rows, ', '.join('%d %s' % (a[k], k) for k in ACTIONS)))
    out.append('%d vintage(s), %d existence attribution(s), %d provenance row(s)' % (
        adds.get('identity/vintages.jsonl', 0), adds.get('document/attributions.jsonl', 0),
        adds.get('cross/provenance.jsonl', 0)))
    out.append('0 estates, 0 wines, 0 names, 0 identity keys, 0 statements, 0 observations, 0 values')
    return '\n'.join(out) + '\n'


def main():
    args = sys.argv[1:]
    clock = VR.Clock()
    mode = next((a for a in ('--apply', '--plan', '--check-all', '--check', '--validate') if a in args), '--validate')
    path = args[args.index('--manifest') + 1] if '--manifest' in args else L.ROOT + MANIFEST
    try:
        view = View()
        for rel in ('identity/estates.jsonl', 'identity/wines.jsonl', 'identity/names.jsonl',
                    'identity/identity-map.jsonl', 'state/estate-wine.jsonl', 'cross/findings.jsonl',
                    'identity/transitions.jsonl', 'state/vintage-statements.jsonl', 'identity/artifacts.jsonl') + TABLES:
            view.table(rel)
        view.index()
        clock.mark('model loading')
        rows = load_manifest(path)
        ev = VR.Evidence({r.get('evidence_version') for r in rows})
        clock.mark('evidence loading')
        errors, resolved = validate_manifest(rows, view, ev) if rows else ([], {})
        clock.mark('manifest validation')
        if errors:
            raise SystemExit('%d problem(s); nothing was written:\n  %s' % (len(errors), '\n  '.join(errors)))
        plan = plan_manifest(rows, resolved, view) if rows else None
        clock.mark('plan construction')
        if mode == '--validate':
            L.out('%d manifest row(s) valid' % len(rows))
        elif mode == '--plan':
            sys.stdout.write(render_plan(plan, len(rows)))
            if plan and plan['actions']['CONFLICT']:
                raise SystemExit('the plan has %d CONFLICT row(s): --apply would refuse it' % plan['actions']['CONFLICT'])
        elif mode == '--apply':
            if plan:
                verify_plan(plan)
            clock.mark('plan verification')
            if not plan or not (plan['actions']['CREATE'] or plan['actions']['ATTRIBUTION_ONLY']):
                L.out('nothing to apply: %d row(s), all held (NOOP)' % len(rows))
            else:
                apply_manifest(view, plan, clock)
                L.out('applied: %d CREATE, %d ATTRIBUTION_ONLY; %d NOOP' % (
                    plan['actions']['CREATE'], plan['actions']['ATTRIBUTION_ONLY'], plan['actions']['NOOP']))
                for rel, k in plan['adds'].items():
                    L.out('  %-42s +%d' % (rel, k))
                if os.environ.get('BDX_MODEL_DIR'):
                    L.out('  (an isolated model: data/app is not this model\'s and was not checked)')
                else:
                    out = subprocess.run([sys.executable, L.ROOT + 'tools/build-app-data.py', '--check'], cwd=L.ROOT,
                                         capture_output=True, text=True)
                    if out.returncode:
                        raise SystemExit('the app would change: %s - an app change is out of scope' % out.stdout.strip())
        elif mode in ('--check', '--check-all'):
            pending = check(plan)
            clock.mark('deterministic checking')
            if pending:
                raise SystemExit('the model does not hold the manifest:\n  %s' % '\n  '.join(pending))
            L.out('vintage-creation manifest: %d row(s) held by the model' % len(rows))
            if mode == '--check-all':
                bad = []
                for cmd in (['migrate.py', '--check'], ['build-indexes.py', '--check'], ['build-app-data.py', '--check']):
                    # a full test run's shared result when another suite has passed it in this state
                    out = CC.run([sys.executable, L.ROOT + 'tools/' + cmd[0]] + cmd[1:], cwd=L.ROOT)
                    L.out('  %s' % (out.stdout.strip().splitlines() or ['?'])[-1])
                    if out.returncode:
                        bad.append(cmd[0])
                clock.mark('rebuild checks')
                if bad:
                    raise SystemExit('not current: %s' % ', '.join(bad))
    except (Conflict, Invalid) as x:
        raise SystemExit('%s\nnothing was written' % x)
    finally:
        if '--timings' in args:
            sys.stderr.write(clock.report() + '\n')


if __name__ == '__main__':
    main()
