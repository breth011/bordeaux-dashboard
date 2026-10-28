"""M3.11: the value-application runner - already-approved canonical values, applied from a reviewed manifest.

    python tools/apply-value-manifest.py                 validate (the default; read-only)
    python tools/apply-value-manifest.py --validate      validate the manifest against the model and the evidence
    python tools/apply-value-manifest.py --plan          the deterministic application plan (read-only)
    python tools/apply-value-manifest.py --apply         validate -> plan -> verify -> write; all or nothing
    python tools/apply-value-manifest.py --check         the model holds every manifest row as its plan says
    python tools/apply-value-manifest.py --check-all     --check, and the migration, indexes and app rebuild
  options:
    --manifest <file>          default data/audit/value-application-manifest.jsonl
    --expected-scope <file>    the exact set of (vintage, field) allowed: a JSON {"expected": [...]}, or a JSONL
                               whose 'scope' record holds 'expected' (M3.10C's manifest is one); each entry
                               {"vintage": "vt:<wine>:<year>", "field": ...}
    --timings                  each stage's wall time, on stderr
  BDX_MODEL_DIR points it at another model directory: the isolated copy the golden test applies to.

The manifest is an application authorization, not evidence. One row is one canonical field of one vintage: its
value, already approved, and the artifacts whose accepted evidence states it, with each artifact's own quote and
locus (copied into provenance verbatim; nothing here reads a document or parses a statement). Rows sharing estate,
wine, vintage and observation_group are one packet, validated and planned as a unit.

Representation (M3.6F's and M3.10C's, unchanged): each artifact of a row one Observation, with its own DOCUMENT
provenance quoting it and naming its evidence decision; one Reconciliation per row, ONLY_CANDIDATE (one artifact)
or UNANIMOUS (several, which state the one fact), with a DERIVATION provenance - the application provenance, naming
the manifest row, its artifacts, observations and evidence version; one canonical value, SOURCED.

Evidence (all of it read from the model and the store, never from a file name, URL or domain): each artifact
exists; an ACCEPTED attribution ties it to the row's exact estate, wine and vintage; that attribution's provenance
names an evidence decision of the row's evidence_version; that decision is ACCEPTED, is still the latest for its
context, and read the artifact's own bytes (sha256).

Against the model each row is APPLY (no canonical value), NOOP_EXISTING_IDENTICAL (the same value, held from
these artifacts' observations) or CONFLICT (anything else: a different value, the same value from other sources,
an orphan observation). Any invalid row or CONFLICT stops the run before anything is written. Never latest-wins,
never an overwrite, never a duplicate. Identities are never created.

The migration applies the same plan (mig_m7_observations.value_application), so the model rebuilds byte for
byte; --apply writes the planned rows directly, without a rebuild.
"""
import collections
import hashlib
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_cache as CC  # noqa: E402
import migration_lib as L  # noqa: E402
import model_schema as S  # noqa: E402

ACTOR = 'tools/apply-value-manifest.py'
RUNNER = 'apply-value-manifest/1'
STREAM = 'value-application'
MANIFEST = 'data/audit/value-application-manifest.jsonl'
STAT = 'value-application manifest values'
OBSERVED = '2026-10-25'          # as M3.6F's and M3.10C's observations (mig_m7_observations.CRAWLED)
REQUIRED = ('manifest_id', 'estate_id', 'wine_id', 'vintage', 'field', 'value', 'artifact_ids', 'evidence_version',
            'observation_group', 'application_class', 'source_basis', 'source_locations')
OPTIONAL = ('unit', 'raw_statement', 'notes')          # audit only: never parsed
CLASSES = {'SOURCED'}
BASES = {'explicit_document_statement'}
TABLES = ('canonical/values.jsonl', 'cross/provenance.jsonl', 'observation/observations.jsonl',
          'reconciliation/reconciliations.jsonl')
ACTIONS = ('APPLY', 'NOOP_EXISTING_IDENTICAL', 'CONFLICT')
VARIETIES = {'CA', 'CF', 'CM', 'CS', 'MA', 'ME', 'MU', 'PV', 'SB', 'SE', 'SEM', 'SG'}   # the model's blend codes


def _num(lo, hi):
    return lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and lo <= v <= hi


def _day(s):
    m = re.fullmatch(r'(\d\d)-(\d\d)', s)
    return bool(m) and 1 <= int(m.group(1)) <= 12 and 1 <= int(m.group(2)) <= 31


def _blend(v):
    return (isinstance(v, dict) and bool(v) and set(v) <= VARIETIES
            and all(_num(0, 100)(x) and x > 0 for x in v.values()) and abs(sum(v.values()) - 100) < 1e-9)


def _pick(v):
    if not (isinstance(v, dict) and v and set(v) <= VARIETIES | {'ALL'} and ('ALL' not in v or len(v) == 1)):
        return False
    for x in v.values():
        parts = x.split('|') if isinstance(x, str) else []
        if len(parts) != 2 or not any(parts) or not all(_day(p) for p in parts if p):
            return False
    return True


# The fields the runner applies, each in the model's existing representation and unit (M3.2D's, M3.6F's). The
# other class-A fields (harvest, sug, ta) are not supported yet: their units are not settled in the model.
FIELDS = {
    'alc': ('%', _num(5, 20)),
    'blend': ('%', _blend),
    'months': (None, lambda v: isinstance(v, str) and bool(re.fullmatch(r'\d{1,2}(-\d{1,2})?', v))),
    'oak': ('%', _num(0, 100)),
    'pick': (None, _pick),
    'ph': (None, _num(2.5, 4.5)),
    'yld': ('hl/ha', _num(1, 150)),
}


class Invalid(Exception):
    pass


class Conflict(Exception):
    pass


def same(a, b):
    return L.dumps(a) == L.dumps(b)


def vref(wine, vintage):
    return S.vref(wine, str(vintage))


def load_manifest(path):
    return L.jsonl_lines(path) if os.path.exists(path) else []


def load_scope(path):
    """{(vintage ref, field)} from an expected-scope file."""
    text = open(path, encoding='utf-8').read()
    try:
        doc = json.loads(text)
        entries = doc['expected']
    except ValueError:
        [doc] = [r for r in (json.loads(x) for x in text.splitlines() if x.strip()) if r.get('record') == 'scope']
        entries = doc['expected']
    return {(e['vintage'], e['field']) for e in entries}


def _migrate():
    import migrate
    return migrate


# ---------------------------------------------------------------- the model and the evidence, read once

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
            att = collections.defaultdict(list)
            for a in self.table('document/attributions.jsonl'):
                if a.get('artifact') and a.get('status') == 'ACCEPTED':
                    att[a['artifact']].append(a)
            obs = collections.defaultdict(list)
            for o in self.table('observation/observations.jsonl'):
                obs[(o['subject'], o['field'])].append(o)
            self._ix = {
                'estates': {r['id'] for r in self.table('identity/estates.jsonl')},
                'wines': {r['id'] for r in self.table('identity/wines.jsonl')},
                'estate_wine': {(r['estate'], r['wine']) for r in self.table('state/estate-wine.jsonl')
                                if r.get('status') == 'ESTABLISHED'},
                'vintages': {(r['wine'], r['label']) for r in self.table('identity/vintages.jsonl')},
                'artifacts': {r['id']: r for r in self.table('identity/artifacts.jsonl')},
                'attributions': att,
                'prov': {p['id']: p for p in self.table('cross/provenance.jsonl')},
                'values': {(v['subject'], v['field']): v for v in self.table('canonical/values.jsonl')},
                'observations': obs,
                'keys': {rel: {L.dumps(_key(rel, r)): r for r in self.table(rel)} for rel in TABLES},
            }
        return self._ix


def _key(rel, row):
    k = S.LAYOUT[rel][1]
    return tuple(row.get(x) for x in k) if isinstance(k, tuple) else row[k]


class Evidence:
    """The store's decisions of the versions a manifest names and every later one (a later version can supersede),
    keyed as attributions name them (mig_m6_provenance.row_key)."""

    def __init__(self, versions):
        import evidence_store as ST
        import mig_m6_provenance as M6
        self.versions = set(ST.versions())
        self.by_key, self.latest = {}, {}
        named = [v for v in versions if isinstance(v, int) and v in self.versions]
        if not named:
            return
        for d in ST.iter_rows([v for v in sorted(self.versions) if v >= min(named)]):
            k = M6.row_key(d)
            self.by_key[k] = d
            ctx = L.dumps(json.loads(k)[:-1])
            if ctx not in self.latest or (d.get('v') or 0) >= (self.latest[ctx].get('v') or 0):
                self.latest[ctx] = d


def evidence_of(art, estate, wine, vt, year, version, ix, ev):
    """The evidence decision key establishing `art` as this exact wine's vintage at `version`, or Invalid."""
    a = ix['artifacts'].get(art)
    if a is None:
        raise Invalid('artifact %s does not exist' % art)
    atts = [x for x in ix['attributions'].get(art, []) if (x.get('estate'), x.get('wine'), x.get('vintage')) == (estate, wine, vt)]
    if not atts:
        raise Invalid('artifact %s has no accepted attribution to %s of %s (%s)' % (art, vt, wine, estate))
    keys = sorted({k for x in atts for k in ((ix['prov'].get(x['provenance']) or {}).get('code_state') or {}).get(
        'evidence_decisions') or []})
    if not keys:
        raise Invalid('artifact %s: its attribution names no evidence decision' % art)
    at = [k for k in keys if json.loads(k)[-1] == version]
    if not at:
        raise Invalid('artifact %s: no evidence decision at version %s (its decisions: v%s)' % (
            art, version, ', v'.join(str(json.loads(k)[-1]) for k in keys)))
    why = []
    for k in at:
        d = ev.by_key.get(k)
        if d is None:
            why.append('decision %s is not in the store' % k)
        elif d.get('decision') != 'ACCEPTED':
            why.append('decision is %s, not ACCEPTED' % d.get('decision'))
        elif ev.latest.get(L.dumps(json.loads(k)[:-1])) is not d:
            why.append('decision superseded by version %s' % ev.latest[L.dumps(json.loads(k)[:-1])].get('v'))
        elif (d.get('read') or {}).get('sha256') not in (None, a.get('sha256')):
            why.append('decision read other bytes than artifact %s' % art)
        elif (d.get('ctx') or {}).get('target_vintage') not in (None, year):
            why.append('decision is for vintage %s' % d['ctx']['target_vintage'])
        else:
            return k
    raise Invalid('artifact %s: %s' % (art, '; '.join(why)))


# ---------------------------------------------------------------- validate

def validate_manifest(rows, view, ev=None, scope=None):
    """Every problem with the manifest, read-only: ([error], {manifest_id: resolved}). `resolved` holds a row's
    vintage ref and each artifact's evidence decision key."""
    errors, resolved = [], {}
    ix = view.index()
    ev = ev or Evidence({r.get('evidence_version') for r in rows})
    ids = collections.Counter(r.get('manifest_id') for r in rows)
    groups = collections.defaultdict(set)
    facts = collections.defaultdict(list)
    for n, r in enumerate(rows, 1):
        mid = r.get('manifest_id') if isinstance(r.get('manifest_id'), str) else 'row %d' % n

        def bad(msg):
            errors.append('%s: %s' % (mid, msg))
        missing = [k for k in REQUIRED if k not in r]
        extra = sorted(set(r) - set(REQUIRED) - set(OPTIONAL))
        if missing or extra:
            bad('missing %s; unknown %s' % (missing, extra))
            continue
        if not re.fullmatch(r'vam_\d{6}', str(r['manifest_id'])):
            bad('manifest_id is not vam_NNNNNN')
        if ids[r['manifest_id']] > 1:
            bad('manifest_id used %d times' % ids[r['manifest_id']])
        if r['application_class'] not in CLASSES:
            bad('application_class %r is not one of %s' % (r['application_class'], sorted(CLASSES)))
        if r['source_basis'] not in BASES:
            bad('source_basis %r is not one of %s' % (r['source_basis'], sorted(BASES)))
        e, w, y, f = r['estate_id'], r['wine_id'], r['vintage'], r['field']
        ok = True
        if e not in ix['estates']:
            bad('estate %s does not exist' % e)
            ok = False
        if w not in ix['wines']:
            bad('wine %s does not exist' % w)
            ok = False
        elif ok and (e, w) not in ix['estate_wine']:
            bad('wine %s does not belong to estate %s' % (w, e))
            ok = False
        if not isinstance(y, int) or isinstance(y, bool):
            bad('vintage %r is not a year' % (y,))
            ok = False
        elif w in ix['wines'] and (w, str(y)) not in ix['vintages']:
            bad('vintage %s of %s does not exist' % (y, w))
            ok = False
        if f not in FIELDS:
            bad('field %r is not a field the runner applies (%s)' % (f, ', '.join(sorted(FIELDS))))
            ok = False
        else:
            unit, valid = FIELDS[f]
            if not valid(r['value']):
                bad('value %s is not a valid %s' % (L.dumps(r['value']), f))
            if 'unit' in r and r['unit'] != unit:
                bad('unit %r: the model holds %s in %r' % (r['unit'], f, unit))
        g = r['observation_group']
        if not isinstance(g, str) or not g.strip():
            bad('observation_group is empty')
            ok = False
        arts = r['artifact_ids']
        if not (isinstance(arts, list) and arts and all(isinstance(a, str) for a in arts) and len(set(arts)) == len(arts)):
            bad('artifact_ids must be a non-empty list of distinct artifact ids')
            ok = False
        locs = r['source_locations']
        if ok and not (isinstance(locs, list) and sorted(l.get('artifact') for l in locs if isinstance(l, dict)) == sorted(arts)
                       and all(isinstance(l.get('quote'), str) and l['quote'].strip() and isinstance(l.get('locus'), str)
                               and isinstance(l.get('lang'), str) and set(l) == {'artifact', 'quote', 'locus', 'lang'}
                               for l in locs)):
            bad('source_locations must hold one {artifact, locus, quote, lang} per artifact')
            ok = False
        v = r['evidence_version']
        if not isinstance(v, int) or v not in ev.versions:
            bad('evidence_version %r is not a version of the store' % (v,))
            ok = False
        if not ok:
            continue
        vt = vref(w, y)
        groups[(g, e, w)].add(vt)
        facts[(vt, f)].append((g, r['manifest_id']))
        keys = {}
        for a in sorted(arts):
            try:
                keys[a] = evidence_of(a, e, w, vt, y, v, ix, ev)
            except Invalid as x:
                bad(str(x))
        if len(keys) == len(arts):
            resolved[r['manifest_id']] = {'vintage': vt, 'evidence': keys}
    for (g, e, w), vts in sorted(groups.items()):
        if len(vts) > 1:
            errors.append('observation group %s spans vintages %s' % (g, sorted(vts)))
    for (vt, f), where in sorted(facts.items()):
        if len(where) > 1:
            same_group = len({g for g, _ in where}) == 1
            errors.append('%s %s: %s rows %s' % (vt, f, 'duplicate field in packet' if same_group else 'one fact in several',
                                                 sorted(m for _, m in where)))
    if scope is not None:
        got = set(facts)
        for vt, f in sorted(scope - got):
            errors.append('expected scope: %s %s is missing' % (vt, f))
        for vt, f in sorted(got - scope):
            errors.append('expected scope: %s %s is not expected' % (vt, f))
    return errors, resolved


# ---------------------------------------------------------------- plan

def materialize(m, r, res):
    """The model rows of one approved row, added to migrate.Model `m`: observations, their DOCUMENT provenance, one
    reconciliation with its DERIVATION (application) provenance, one canonical value. Returns the value."""
    vt, f, arts = res['vintage'], r['field'], sorted(r['artifact_ids'])
    loc = {l['artifact']: l for l in r['source_locations']}
    unit = FIELDS[f][0]
    oids, provs = [], []
    for a in arts:
        pid = m.prov('DOCUMENT', ACTOR, artifact=a, quote=loc[a]['quote'],
                     code_state={'stream': STREAM, 'runner': RUNNER, 'manifest': MANIFEST,
                                 'manifest_id': r['manifest_id'], 'vintage': vt, 'field': f, 'locus': loc[a]['locus'],
                                 'evidence_decision': res['evidence'][a], 'evidence_version': r['evidence_version']})
        oid = S.hid('Observation', vt, f, STREAM, a)
        row = {'id': oid, 'subject': vt, 'field': f, 'value': r['value'], 'raw_value': loc[a]['quote'],
               'artifact': a, 'locus': loc[a]['locus'],
               'extraction': {'method': RUNNER, 'file': MANIFEST, 'record': '%s|%s' % (r['manifest_id'], a)},
               'confidence': 'EXPLICIT_LABELLED', 'observed_at': OBSERVED, 'provenance': pid,
               'subject_status': 'ESTABLISHED', 'lang': loc[a]['lang']}
        if unit:
            row['unit'] = unit
        m.add('observation/observations.jsonl', row)
        oids.append(oid)
        provs.append(pid)
    rule = 'ONLY_CANDIDATE' if len(oids) == 1 else 'UNANIMOUS'
    rid = S.hid('Reconciliation', vt, f, STREAM)
    m.add('reconciliation/reconciliations.jsonl', {
        'id': rid, 'subject': vt, 'field': f, 'candidates': oids, 'selected': oids[0], 'rule': rule,
        'status': 'SINGLE' if rule == 'ONLY_CANDIDATE' else 'AGREED',
        'reason': 'approved in the value-application manifest (%s); stated in %d accepted document(s); %s' % (
            r['manifest_id'], len(oids), 'the only candidate' if rule == 'ONLY_CANDIDATE' else 'the documents agree'),
        'resolver': ACTOR, 'decided_at': OBSERVED,
        'provenance': m.prov('DERIVATION', ACTOR, derived_from=sorted(provs),
                             code_state={'stream': STREAM, 'runner': RUNNER, 'manifest': MANIFEST,
                                         'manifest_id': r['manifest_id'], 'vintage': vt, 'field': f, 'rule': rule,
                                         'artifacts': arts, 'observations': oids,
                                         'evidence_version': r['evidence_version'],
                                         'application_class': r['application_class'],
                                         'source_basis': r['source_basis']})})
    m.add('canonical/values.jsonl', {'subject': vt, 'field': f, 'value': r['value'], 'status': 'SOURCED',
                                     'reconciliation': rid, 'provenance': provs[0]})


def classify(r, res, ix):
    """(action, reason) for one valid row against the model."""
    vt, f, arts = res['vintage'], r['field'], set(r['artifact_ids'])
    cur = ix['values'].get((vt, f))
    obs = ix['observations'].get((vt, f), [])
    if cur is None:
        orphan = sorted(o['id'] for o in obs if o.get('artifact') in arts)
        if orphan:
            return 'CONFLICT', 'observations %s from these documents exist, but no canonical value' % orphan
        return 'APPLY', 'no canonical value'
    if not same(cur['value'], r['value']):
        return 'CONFLICT', 'the model holds %s' % L.dumps(cur['value'])
    held = {o.get('artifact') for o in obs if same(o['value'], r['value'])}
    if arts <= held:
        return 'NOOP_EXISTING_IDENTICAL', 'held, from these documents'
    return 'CONFLICT', 'the model holds the same value, but not from %s' % sorted(arts - held)


def plan_manifest(rows, resolved, view):
    """The deterministic plan: packets in (estate, wine, vintage, group) order, each row's action and, for APPLY,
    the model rows it adds. Read-only."""
    mig = _migrate()
    ix = view.index()
    by = collections.defaultdict(list)
    for r in rows:
        by[(r['estate_id'], r['wine_id'], r['vintage'], r['observation_group'])].append(r)
    packets, counts = [], collections.Counter()
    for (e, w, y, g) in sorted(by, key=lambda k: (k[0], k[1], k[2], k[3])):
        items = []
        for r in sorted(by[(e, w, y, g)], key=lambda r: (r['field'], r['manifest_id'])):
            res = resolved[r['manifest_id']]
            action, reason = classify(r, res, ix)
            adds = {}
            if action == 'APPLY':
                scratch = mig.Model()
                materialize(scratch, r, res)
                adds = {rel: sorted(scratch.tables[rel].values(), key=lambda x: L.dumps(_key(rel, x)))
                        for rel in sorted(scratch.tables)}
                clash = [(rel, x) for rel, xs in adds.items() for x in xs
                         if L.dumps(_key(rel, x)) in ix['keys'].get(rel, {})
                         and not same(ix['keys'][rel][L.dumps(_key(rel, x))], x)]
                if clash:
                    action, reason = 'CONFLICT', 'a different row already holds %s %s' % (clash[0][0], L.dumps(_key(*clash[0])))
                    adds = {}
            counts[action] += 1
            items.append({'manifest_id': r['manifest_id'], 'field': r['field'], 'value': r['value'],
                          'artifacts': sorted(r['artifact_ids']), 'action': action, 'reason': reason, 'adds': adds})
        packets.append({'group': g, 'estate': e, 'wine': w, 'vintage': y, 'vintage_ref': vref(w, y), 'rows': items})
    added = collections.Counter()
    for p in packets:
        for it in p['rows']:
            for rel, xs in it['adds'].items():
                added[rel] += len(xs)
    return {'packets': packets, 'actions': {a: counts[a] for a in ACTIONS}, 'adds': dict(sorted(added.items())),
            'rows': sum(len(p['rows']) for p in packets)}


def verify_plan(plan):
    """The plan's own guarantees, before anything is written."""
    conflicts = ['%s %s %s: %s' % (p['vintage_ref'], it['field'], it['manifest_id'], it['reason'])
                 for p in plan['packets'] for it in p['rows'] if it['action'] == 'CONFLICT']
    if conflicts:
        raise Conflict('%d conflict(s):\n  %s' % (len(conflicts), '\n  '.join(conflicts)))
    assert set(plan['adds']) <= set(TABLES), 'the plan touches %s' % sorted(set(plan['adds']) - set(TABLES))
    for p in plan['packets']:
        for it in p['rows']:
            if it['action'] == 'APPLY':
                n = len(it['artifacts'])
                got = {rel: len(xs) for rel, xs in it['adds'].items()}
                assert got == {'canonical/values.jsonl': 1, 'cross/provenance.jsonl': n + 1,
                               'observation/observations.jsonl': n, 'reconciliation/reconciliations.jsonl': 1}, \
                    (it['manifest_id'], got)


def apply_plan(m, plan):
    """Add the plan's rows to migrate.Model `m` (its add refuses a different row under a key). The rows applied."""
    n = 0
    for p in plan['packets']:
        for it in p['rows']:
            if it['action'] != 'APPLY':
                continue
            for rel in sorted(it['adds']):
                for x in it['adds'][rel]:
                    m.add(rel, x)
            n += 1
    return n


# ---------------------------------------------------------------- the migration's hook

def migration_hook(m):
    """mig_m7_observations.value_application: the production manifest, planned against the model being built and
    applied the same way; NOOP rows add nothing, and an all-NOOP manifest leaves no trace (no stat)."""
    rows = load_manifest(L.ROOT + MANIFEST)
    if not rows:
        return
    view = View(m.rows)
    errors, resolved = validate_manifest(rows, view)
    if errors:
        raise SystemExit('value-application manifest: %d invalid:\n  %s' % (len(errors), '\n  '.join(errors[:40])))
    plan = plan_manifest(rows, resolved, view)
    try:
        verify_plan(plan)
    except Conflict as x:
        raise SystemExit('value-application manifest: %s' % x)
    n = apply_plan(m, plan)
    if n:
        m.stat('M7', STAT, n)


# ---------------------------------------------------------------- writing (--apply)

def render_tables(view, plan):
    """{relpath: bytes} for the four tables and the manifest with the plan applied, rendered as migrate.render does."""
    mig = _migrate()
    m = mig.Model()
    for rel in TABLES:
        for r in view.table(rel):
            m.add(rel, r)
    n = apply_plan(m, plan)
    man = json.load(open(L.MODEL + mig.MANIFEST, encoding='utf-8'), object_pairs_hook=collections.OrderedDict)
    files = {}
    for rel in TABLES:
        rows = sorted(m.tables[rel].values(), key=lambda r: L.dumps(m.key(rel, r)))
        b = ''.join(L.dumps(r) + '\n' for r in rows).encode('utf-8')
        files[rel] = b
        man['files'][rel]['rows'] = len(rows)
        man['files'][rel]['sha256'] = hashlib.sha256(b).hexdigest()
    m7 = man['stats'].setdefault('M7', collections.OrderedDict())
    m7[STAT] = m7.get(STAT, 0) + n
    files[mig.MANIFEST] = (json.dumps(man, ensure_ascii=False, indent=1) + '\n').encode('utf-8')
    return files


def write_files(files):
    tmp = []
    for rel, b in sorted(files.items()):
        p = L.MODEL + rel
        with open(p + '.tmp', 'wb') as f:
            f.write(b)
        tmp.append(p)
    for p in tmp:
        os.replace(p + '.tmp', p)


# ---------------------------------------------------------------- output

def fmt(field, v):
    unit = FIELDS[field][0] if field in FIELDS else None
    if field == 'blend':
        return ' / '.join('%s %s' % (k, _n(x)) for k, x in sorted(v.items(), key=lambda kv: (-kv[1], kv[0]))) + ' %'
    if field == 'pick':
        return ', '.join('%s %s' % (k, x.replace('|', ' to ')) for k, x in sorted(v.items()))
    if unit == '%':
        return '%s%%' % _n(v)
    return '%s%s' % (_n(v) if not isinstance(v, str) else v, ' ' + unit if unit else '')


def _n(x):
    return ('%g' % x) if isinstance(x, float) else str(x)


def render_plan(plan):
    out = []
    for p in plan['packets']:
        out.append('PACKET: %s  (%s, %s, %s)' % (p['group'], p['estate'], p['wine'], p['vintage']))
        out.append('')
        for it in p['rows']:
            out.append('%s  %s' % (it['field'], it['manifest_id']))
            out.append('  value: %s' % fmt(it['field'], it['value']))
            out.append('  artifacts: %s' % ', '.join(it['artifacts']))
            out.append('  action: %s%s' % (it['action'], '' if it['action'] == 'APPLY' else ' (%s)' % it['reason']))
            out.append('')
    a, adds = plan['actions'], plan['adds']
    out.append('%d packet(s), %d manifest row(s): %d APPLY, %d NOOP_EXISTING_IDENTICAL, %d CONFLICT' % (
        len(plan['packets']), plan['rows'], a['APPLY'], a['NOOP_EXISTING_IDENTICAL'], a['CONFLICT']))
    out.append('%d source observation(s), %d reconciliation(s), %d canonical value(s), %d provenance row(s)' % (
        adds.get('observation/observations.jsonl', 0), adds.get('reconciliation/reconciliations.jsonl', 0),
        adds.get('canonical/values.jsonl', 0), adds.get('cross/provenance.jsonl', 0)))
    out.append('0 new estates, 0 new wines, 0 new vintages')
    return '\n'.join(out) + '\n'


# ---------------------------------------------------------------- main

class Clock:
    def __init__(self):
        self.t, self.marks = time.perf_counter(), []

    def mark(self, name):
        now = time.perf_counter()
        self.marks.append((name, now - self.t))
        self.t = now

    def report(self):
        return '\n'.join('%-26s %7.3f s' % kv for kv in self.marks) + '\n%-26s %7.3f s' % (
            'total', sum(s for _, s in self.marks))


def prepare(args, clock):
    """(rows, view, resolved, plan) or SystemExit with every problem."""
    path = args[args.index('--manifest') + 1] if '--manifest' in args else L.ROOT + MANIFEST
    scope = load_scope(args[args.index('--expected-scope') + 1]) if '--expected-scope' in args else None
    rows = load_manifest(path)
    view = View()
    for rel in ('identity/estates.jsonl', 'identity/wines.jsonl', 'state/estate-wine.jsonl', 'identity/vintages.jsonl',
                'identity/artifacts.jsonl', 'document/attributions.jsonl') + TABLES:
        view.table(rel)
    view.index()
    clock.mark('model loading')
    ev = Evidence({r.get('evidence_version') for r in rows})
    clock.mark('evidence loading')
    errors, resolved = validate_manifest(rows, view, ev, scope)
    clock.mark('manifest validation')
    if errors:
        raise SystemExit('%d problem(s) in %s; nothing was written:\n  %s' % (
            len(errors), os.path.relpath(path, L.ROOT).replace('\\', '/'), '\n  '.join(errors)))
    plan = plan_manifest(rows, resolved, view)
    clock.mark('plan construction')
    return rows, view, resolved, plan


def check(plan):
    """The model holds every row: each is NOOP_EXISTING_IDENTICAL, and the runner's stat counts what it applied."""
    pending = ['%s %s %s' % (p['vintage_ref'], it['field'], it['action']) for p in plan['packets'] for it in p['rows']
               if it['action'] != 'NOOP_EXISTING_IDENTICAL']
    man = json.load(open(L.MODEL + 'manifest.json', encoding='utf-8'))
    mine = sum(1 for v in L.read_table('canonical/values.jsonl')
               if v.get('reconciliation') == S.hid('Reconciliation', v['subject'], v['field'], STREAM))
    stat = man['stats'].get('M7', {}).get(STAT, 0)
    if stat != mine:
        pending.append('the model manifest counts %d runner value(s), the model holds %d' % (stat, mine))
    return pending


def main():
    args = sys.argv[1:]
    clock = Clock()
    mode = next((a for a in ('--apply', '--plan', '--check-all', '--check', '--validate') if a in args), '--validate')
    try:
        rows, view, resolved, plan = prepare(args, clock)
        if mode == '--validate':
            L.out('%d manifest row(s) in %d packet(s) valid' % (plan['rows'], len(plan['packets'])))
        elif mode == '--plan':
            if not plan['actions']['CONFLICT']:
                verify_plan(plan)
            sys.stdout.write(render_plan(plan))
            if plan['actions']['CONFLICT']:
                raise SystemExit('the plan has %d CONFLICT row(s): --apply would refuse it' % plan['actions']['CONFLICT'])
        elif mode == '--apply':
            verify_plan(plan)
            clock.mark('plan verification')
            if not plan['actions']['APPLY']:
                L.out('nothing to apply: %d row(s) held already (NOOP_EXISTING_IDENTICAL)' % plan['rows'])
            else:
                files = render_tables(view, plan)
                clock.mark('application')
                write_files(files)
                env = dict(os.environ)
                subprocess.run([sys.executable, L.ROOT + 'tools/build-indexes.py'], cwd=L.ROOT, env=env, check=True,
                               stdout=subprocess.DEVNULL)
                clock.mark('output generation')
                L.out('applied %d row(s); %d held already' % (plan['actions']['APPLY'], plan['actions']['NOOP_EXISTING_IDENTICAL']))
                for rel, k in plan['adds'].items():
                    L.out('  %-42s +%d' % (rel, k))
                if os.environ.get('BDX_MODEL_DIR'):
                    L.out('  (an isolated model: data/app is not this model\'s and was not checked)')
                else:
                    out = subprocess.run([sys.executable, L.ROOT + 'tools/build-app-data.py', '--check'], cwd=L.ROOT,
                                         capture_output=True, text=True)
                    if out.returncode:
                        raise SystemExit('the app would change: %s - stop, an app change is out of scope' % out.stdout.strip())
                clock.mark('deterministic checking')
        elif mode in ('--check', '--check-all'):
            pending = check(plan)
            clock.mark('deterministic checking')
            if pending:
                raise SystemExit('the model does not hold the manifest:\n  %s' % '\n  '.join(pending))
            L.out('value-application manifest: %d row(s) held by the model' % plan['rows'])
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
