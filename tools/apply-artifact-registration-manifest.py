"""Generic artifact registration: externally acquired documents as model artifacts, from a reviewed manifest.

    python tools/apply-artifact-registration-manifest.py               validate (the default; read-only)
    python tools/apply-artifact-registration-manifest.py --validate    validate the manifest against its acquisition
                                                                       records, the held bytes and the model
    python tools/apply-artifact-registration-manifest.py --plan        the deterministic plan (read-only)
    python tools/apply-artifact-registration-manifest.py --apply       validate -> plan -> verify -> write; all or nothing
    python tools/apply-artifact-registration-manifest.py --check       the model holds every manifest row as its plan says
    python tools/apply-artifact-registration-manifest.py --check-all   --check, and the migration, indexes and app rebuild
  options: --manifest <file> (default data/audit/artifact-registration-manifest.jsonl); --timings
  BDX_MODEL_DIR points it at another model directory (an isolated copy).

docs/PHASE-GENERIC-EVIDENCE-REGISTRATION.md is the contract. It is M3.10A's registration made reusable: the same
input shape, the same minting, the same placement - with no phase, estate or document count written into it.

A ROW (arm_NNNNNN) registers one location of one document: the bytes' sha256, size and media type, the file that
holds them (under sources/), and where and when they were fetched - each fact checked against the acquisition record
the row names ({audit, row}: an `item` row of an acquisition audit listed in ACQUISITION_AUDITS), never written from
anything else. The origin is EXTERNAL_ACQUISITION: acquired outside the discovery crawl, whose manifest stays its
generator's; no crawl fact is written. A source relationship is recorded only where the acquisition record already
attributes the fetch to one (M3.7's confirmed relationships). Registration decides no identity: a row names no
estate, wine or vintage, and no evidence decision, attribution or value follows from it.

AN ESTATE-SUPPLIED ROW (the second mode) registers a file the estate itself sent, never fetched: its acquisition
record is an `item` of data/audit/estate-supplied-acquisitions.jsonl (tools/record-estate-supplied-acquisition.py,
which hashes the held file itself). The mode is the audit's, not the row's: a supplied row must not carry url,
final_url, http_status or fetched_at, an HTTP row must not carry received_at, original_filename or supply_channel,
and each record's retrieval (SUPPLIED or OK) and the row's origin (ESTATE_SUPPLIED or EXTERNAL_ACQUISITION) must
be its mode's. The supplier must be the first party: the row's source relationship a confirmed M3.7 one
(CONFIRMED_FIRST_PARTY or CONFIRMED_ESTATE_CONTROLLED) of the supplier estate, its source in the model, and the
sender's domain that source's own host. The file is held at sources/acquisition/supplied/<sha256>/<original
filename> and placed there (a LOCAL_PATH locator, on the source, observed the day it was received, DOCUMENT
provenance stating the supply).

Each valid row is CREATE (its bytes are not a model artifact: one is minted by sha256, then the placement), REUSE
(the bytes are an artifact already, from the crawl or an earlier registration: its URL placement only - never a
second artifact because the URL differs), NOOP (the artifact and this URL placement are held) or CONFLICT (the
artifact's recorded size or media type contradicts the row, or two rows give one sha256 different sizes or media
types); an invalid row is REJECT. Any REJECT or CONFLICT stops the batch before anything is written.

The migration applies the manifest: mig_m2_identity mints the CREATE rows' artifacts by sha256 after every other
input's digests (after M3.10A's), so no existing id moves when the model is built from scratch, and
mig_m6_provenance.artifact_registration_placements places each row at its URL in M3.10A's shape. --apply runs that
migration on the current model and writes it only if exactly the plan's rows were added; an empty manifest adds
nothing and records nothing.
"""
import collections
import datetime
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

ACTOR = 'tools/apply-artifact-registration-manifest.py'
RUNNER = 'apply-artifact-registration-manifest/1'
STREAM = 'artifact-registration'
MANIFEST = 'data/audit/artifact-registration-manifest.jsonl'
PATH = [L.ROOT + MANIFEST]                     # the manifest the migration's hooks read (--manifest replaces it)
ARTIFACT_STAT = 'artifact-registration manifest artifacts'    # M2: artifacts minted from the manifest
PLACEMENT_STAT = 'artifact-registration manifest placements'  # M6: URL placements added from it
COMMON = ('registration_id', 'sha256', 'bytes', 'media_type', 'held_path', 'retrieval_method', 'acquired_by', 'origin',
          'acquisition')
HTTP_ONLY = ('url', 'final_url', 'http_status', 'fetched_at')
SUPPLIED_ONLY = ('received_at', 'original_filename', 'supply_channel')
REQUIRED = COMMON[:5] + HTTP_ONLY + COMMON[5:]            # HTTP mode, as before
OPTIONAL = ('source', 'source_relationship', 'notes')
ORIGIN = 'EXTERNAL_ACQUISITION'
SUPPLIED = 'ESTATE_SUPPLIED'
# A row's mode is its acquisition audit's, never its own fields': HTTP (a fetch, M3.8's records) or ESTATE_SUPPLIED
# (a file the estate itself sent, recorded by tools/record-estate-supplied-acquisition.py). Each mode's fields are
# required in it and forbidden in the other; a supplied row must name its source and relationship.
MODES = {
    'HTTP': {'origin': ORIGIN, 'retrieval': 'OK', 'required': REQUIRED, 'optional': OPTIONAL,
             'forbidden': SUPPLIED_ONLY},
    SUPPLIED: {'origin': SUPPLIED, 'retrieval': 'SUPPLIED', 'required': COMMON + SUPPLIED_ONLY + ('source', 'source_relationship'),
               'optional': ('notes',), 'forbidden': HTTP_ONLY},
}
SUPPLY_CHANNELS = {'EMAIL_ATTACHMENT'}       # a link the estate sends is a fetch: an HTTP acquisition, not a supply
SUPPLIER_STATUSES = {'CONFIRMED_FIRST_PARTY', 'CONFIRMED_ESTATE_CONTROLLED'}
SUPPLIED_AUDIT = 'data/audit/estate-supplied-acquisitions.jsonl'
# The acquisition audits whose `item` rows a registration may rest on, each with its mode and what it establishes
# about how its documents were acquired and held. Another audit is added here, by name, when a later acquisition
# produces one. `file` (tests only) reads the audit from elsewhere.
ACQUISITION_AUDITS = {
    'data/audit/m3.8-acquisition-pilot.jsonl': {
        'mode': 'HTTP', 'prefix': 'm3.8', 'acquired_by': 'M3.8', 'held': 'sources/acquisition/m3.8/blobs/',
        'retrieval_method': 'confirmed-source acquisition (tools/m38-acquire.py, the discovery fetch discover/1.0)'},
    SUPPLIED_AUDIT: {
        'mode': SUPPLIED, 'prefix': 'sup', 'acquired_by': 'the estate (supplied)', 'held': 'sources/acquisition/supplied/',
        'retrieval_method': 'supplied by the estate (%s)'},
}
HELD_ROOT = [L.ROOT]                        # where held_path resolves (tests point it at a temporary copy)
RELATIONSHIPS = 'data/audit/m3.7-source-confirmation.jsonl'
MAGIC = {'application/pdf': b'%PDF-'}
TABLES = ('identity/artifacts.jsonl', 'identity/identity-map.jsonl', 'document/locators.jsonl',
          'document/placements.jsonl', 'cross/provenance.jsonl')
ACTIONS = ('CREATE', 'REUSE', 'NOOP', 'CONFLICT')


def media_types():
    import mig_m2_identity as M2
    return set(M2.MEDIA.values())


def load_manifest(path):
    return L.jsonl_lines(path) if os.path.exists(path) else []


class Invalid(Exception):
    pass


class Conflict(Exception):
    pass


class Acquisitions:
    """The acquisition records (`item` rows) of the allowed audits, by (audit, row id), each audit read once."""

    def __init__(self):
        self._rows = {}

    def get(self, audit, row):
        if audit not in ACQUISITION_AUDITS:
            return None
        if audit not in self._rows:
            conf = ACQUISITION_AUDITS[audit]
            path = conf.get('file') or L.ROOT + audit
            rows = L.jsonl_lines(path) if os.path.exists(path) else []
            self._rows[audit] = {'%s:%d' % (conf['prefix'], r['n']): r for r in rows
                                 if r.get('record') == 'item' and isinstance(r.get('n'), int)}
        return self._rows[audit].get(row)


class Relationships:
    """M3.7's confirmed source relationships, by id, and each source's host."""

    def __init__(self):
        self._rows = self._hosts = None

    def _load(self):
        if self._rows is None:
            rows = L.jsonl_lines(L.ROOT + RELATIONSHIPS)
            self._rows = {r['id']: r for r in rows
                          if r.get('record') == 'relationship' and str(r.get('status', '')).startswith('CONFIRMED_')}
            self._hosts = {r['source']: r.get('canonical_host') for r in rows if r.get('record') == 'source'}

    def get(self, rid):
        self._load()
        return self._rows.get(rid)

    def host(self, source):
        self._load()
        return self._hosts.get(source)


def mode_of(r):
    """The row's mode: its acquisition audit's, or None when the reference names no listed audit."""
    ref = r.get('acquisition')
    if isinstance(ref, dict) and set(ref) == {'audit', 'row'} and ref['audit'] in ACQUISITION_AUDITS:
        return ACQUISITION_AUDITS[ref['audit']]['mode']
    return None


def locator_of(r):
    """(kind, value) of the row's placement: the URL it was fetched from, or the held file a supplied row names."""
    if mode_of(r) == SUPPLIED:
        return 'LOCAL_PATH', r['held_path'][len('sources/'):]
    return 'URL', r['url']


UNSAFE = re.compile(r'[\x00-\x1f\x7f/\\<>:"|?*]')


def safe_segment(name):
    """A received file's original name, usable as exactly one path segment on every platform, kept as received."""
    return isinstance(name, str) and 0 < len(name) <= 200 and name not in ('.', '..') and not UNSAFE.search(name) \
        and name == name.strip() and not name.endswith('.')


def _host(h):
    h = str(h or '').strip().lower()
    return h[4:] if h.startswith('www.') else h


# ---------------------------------------------------------------- validate

def check_supplied(r, it, conf, rels):
    """An estate-supplied row: every fact the supplied record's, and the supplier the first party of the source it
    names - a confirmed M3.7 relationship of that estate, the sender's domain the source's own host."""
    if it.get('retrieval') != 'SUPPLIED' or it.get('origin') != SUPPLIED:
        raise Invalid('the acquisition record is not an estate-supplied one (retrieval %r, origin %r)' % (
            it.get('retrieval'), it.get('origin')))
    sup = it.get('supplier') if isinstance(it.get('supplier'), dict) else {}
    stated = {'sha256': it.get('sha256'), 'bytes': it.get('bytes'), 'media_type': it.get('content_type'),
              'held_path': it.get('held_path'), 'received_at': it.get('received_at'),
              'original_filename': it.get('original_filename'), 'supply_channel': it.get('supply_channel'),
              'source': sup.get('source'), 'source_relationship': sup.get('relationship'),
              'acquired_by': conf['acquired_by'], 'retrieval_method': conf['retrieval_method'] % it.get('supply_channel')}
    differ = sorted(k for k, v in stated.items() if r[k] != v)
    if differ:
        raise Invalid('not what the acquisition record establishes: %s' % ', '.join(
            '%s %r (the record: %r)' % (k, r[k], stated[k]) for k in differ))
    if r['held_path'] != conf['held'] + '%s/%s' % (r['sha256'], r['original_filename']):
        raise Invalid('held_path must be %s<sha256>/<original_filename>' % conf['held'])
    rc = it.get('receipt')
    if not (isinstance(rc, dict) and set(rc) == {'held', 'sha256'} and re.fullmatch(r'[0-9a-f]{64}', str(rc['sha256']))
            and str(rc['held']).startswith(conf['held'] + r['sha256'] + '/')) or not str(it.get('statement') or '').strip():
        raise Invalid('the supplied record lacks its hashed receipt or its supplied statement')
    x = rels.get(r['source_relationship'])
    if x is None or x.get('status') not in SUPPLIER_STATUSES:
        raise Invalid('%s is not a confirmed first-party or estate-controlled relationship (M3.7)' % r['source_relationship'])
    if x.get('source') != r['source']:
        raise Invalid('%s is a relationship of source %s, not %s' % (r['source_relationship'], x.get('source'), r['source']))
    if x.get('estate') != sup.get('estate'):
        raise Invalid('the supplier estate %r is not %s\'s estate %s' % (sup.get('estate'), r['source_relationship'],
                                                                         x.get('estate')))
    host = rels.host(r['source'])
    if not host or _host(it.get('sender_domain')) != _host(host):
        raise Invalid('the sender domain %r is not the host of source %s (%r)' % (it.get('sender_domain'), r['source'], host))


def check_acquisition(r, acq, rels):
    """Every fact the row states is the acquisition record's; the source relationship only where it attributes one."""
    ref = r['acquisition']
    if not (isinstance(ref, dict) and set(ref) == {'audit', 'row'}):
        raise Invalid('acquisition must be an {audit, row} reference')
    conf = ACQUISITION_AUDITS.get(ref['audit'])
    it = acq.get(ref['audit'], ref['row'])
    if conf is None or it is None:
        raise Invalid('no acquisition record (the audit is not one of %s, or the row is not in it)'
                      % sorted(ACQUISITION_AUDITS))
    if conf['mode'] == SUPPLIED:
        return check_supplied(r, it, conf, rels)
    if it.get('retrieval') != 'OK':
        raise Invalid('the acquisition did not retrieve it (%s)' % it.get('retrieval'))
    stated = {'url': it.get('url'), 'final_url': it.get('final_url'), 'http_status': it.get('status'),
              'fetched_at': it.get('at'), 'sha256': it.get('sha256'), 'bytes': it.get('bytes'),
              'media_type': it.get('content_type'), 'acquired_by': conf['acquired_by'],
              'retrieval_method': conf['retrieval_method'], 'held_path': conf['held'] + str(it.get('sha256'))}
    differ = sorted(k for k, v in stated.items() if r[k] != v)
    if differ:
        raise Invalid('not what the acquisition record establishes: %s' % ', '.join(
            '%s %r (the record: %r)' % (k, r[k], stated[k]) for k in differ))
    rel, src = r.get('source_relationship'), r.get('source')
    if rel is None and src is None:
        return
    if rel is None or src is None:
        raise Invalid('source and source_relationship go together')
    if rel != it.get('attributed_to'):
        raise Invalid('the acquisition record attributes the fetch to %r, not %r' % (it.get('attributed_to'), rel))
    x = rels.get(rel)
    if x is None or x.get('source') != src:
        raise Invalid('%s is not a confirmed relationship of source %s' % (rel, src))


def structural(rows, acq=None, rels=None):
    """What the manifest says, checked without the model or the held bytes: ([error], [valid row]). The
    migration's hooks run this; the runner adds the bytes and the model."""
    acq, rels = acq or Acquisitions(), rels or Relationships()
    errors, ok = [], []
    ids = collections.Counter(r.get('registration_id') for r in rows)
    media = media_types()
    shaped = []
    for n, r in enumerate(rows, 1):
        rid = r.get('registration_id') if isinstance(r.get('registration_id'), str) else 'row %d' % n

        def bad(msg, rid=rid):
            errors.append('%s: %s' % (rid, msg))
        # the mode is the acquisition audit's; a reference to no listed audit is judged by HTTP's fields and refused
        # by check_acquisition
        mode = mode_of(r) or 'HTTP'
        spec = MODES[mode]
        forbidden = sorted(k for k in spec['forbidden'] if k in r)
        if forbidden:
            bad('%s in a %s acquisition: forbidden (the other mode\'s fields)' % (forbidden, mode))
            continue
        missing = [k for k in spec['required'] if k not in r]
        extra = sorted(set(r) - set(spec['required']) - set(spec['optional']))
        if missing or extra:
            bad('missing %s; unknown %s (a registration names no estate, wine or vintage)' % (missing, extra))
            continue
        shaped.append((rid, r, mode, bad))
    places = collections.Counter((r['sha256'], locator_of(r)) for _, r, _, _ in shaped)
    for rid, r, mode, bad in shaped:
        spec = MODES[mode]
        before = len(errors)
        if not re.fullmatch(r'arm_\d{6}', str(r['registration_id'])):
            bad('registration_id is not arm_NNNNNN')
        if ids[r['registration_id']] > 1:
            bad('registration_id used %d times' % ids[r['registration_id']])
        if not re.fullmatch(r'[0-9a-f]{64}', str(r['sha256'])):
            bad('sha256 is not a SHA-256')
        if not isinstance(r['bytes'], int) or isinstance(r['bytes'], bool) or r['bytes'] <= 0:
            bad('bytes %r is not a size' % (r['bytes'],))
        if r['media_type'] not in media:
            bad('media type %r is not one the model records' % (r['media_type'],))
        if r['origin'] != spec['origin']:
            bad('origin %r: only %s is registered from a %s acquisition audit (the crawl\'s documents are its '
                'manifest\'s)' % (r['origin'], spec['origin'], mode))
        if mode == 'HTTP' and not str(r['url']).startswith(('http://', 'https://')):
            bad('url is not a URL')
        if mode == SUPPLIED:
            if not safe_segment(r['original_filename']):
                bad('original_filename %r is not one safe path segment' % (r['original_filename'],))
            if r['supply_channel'] not in SUPPLY_CHANNELS:
                bad('supply_channel %r is not one of %s' % (r['supply_channel'], sorted(SUPPLY_CHANNELS)))
            try:
                datetime.date.fromisoformat(str(r['received_at']))
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(r['received_at'])):
                    raise ValueError
            except ValueError:
                bad('received_at %r is not a date (YYYY-MM-DD)' % (r['received_at'],))
        if places[(r['sha256'], locator_of(r))] > 1:
            bad('the same bytes at the same %s are registered %d times' % (
                'URL' if mode == 'HTTP' else 'held path', places[(r['sha256'], locator_of(r))]))
        if len(errors) == before:
            try:
                check_acquisition(r, acq, rels)
            except Invalid as x:
                bad(str(x))
        if len(errors) == before:
            ok.append(r)
    return errors, ok


def held_bytes(r):
    """The held file is the row's bytes: its sha256, size and media type."""
    p = HELD_ROOT[0] + r['held_path']
    if not r['held_path'].startswith('sources/') or '..' in r['held_path'].split('/') or not os.path.isfile(p):
        raise Invalid('the held file %s is missing' % r['held_path'])
    b = open(p, 'rb').read()
    if hashlib.sha256(b).hexdigest() != r['sha256'] or len(b) != r['bytes']:
        raise Invalid('the held file %s does not hash to the row' % r['held_path'])
    if r['media_type'] in MAGIC and not b.startswith(MAGIC[r['media_type']]):
        raise Invalid('the held file is not %s' % r['media_type'])


class View:
    """The model's artifacts, digests and placements, each read once: from a migration's in-memory model, or from
    the model directory."""

    def __init__(self, rows=None):
        self._rows = rows or L.read_table
        self._ix = None

    def index(self):
        if self._ix is None:
            by_sha = {r['legacy_key']: r['stable_id'] for r in self._rows('identity/identity-map.jsonl')
                      if r['namespace'] == 'artifact-by-sha256' and r.get('stable_id') and r['status'] == 'ACTIVE'}
            placed = collections.defaultdict(set)
            for p in self._rows('document/placements.jsonl'):
                if p.get('artifact'):
                    placed[p['artifact']].add((p['locator']['kind'], p['locator']['value']))
            self._ix = {'by_sha': by_sha, 'placed': placed,
                        'artifacts': {a['id']: a for a in self._rows('identity/artifacts.jsonl')},
                        'sources': {s['id'] for s in self._rows('identity/sources.jsonl')}}
        return self._ix


def validate_manifest(rows, view, acq=None, rels=None, read_bytes=True):
    """Every problem with the manifest, read-only: ([error], [valid row])."""
    errors, ok = structural(rows, acq, rels)
    ix = view.index()
    out = []
    for r in ok:
        try:
            if r.get('source') is not None and r['source'] not in ix['sources']:
                raise Invalid('source %s is not in the model' % r['source'])
            if read_bytes:
                held_bytes(r)
            out.append(r)
        except Invalid as x:
            errors.append('%s: %s' % (r['registration_id'], x))
    return errors, out


# ---------------------------------------------------------------- plan

def classify(r, ix, batch):
    """(action, reason, artifact id or None) for one valid row against the model and the rest of the batch."""
    others = {(x['bytes'], x['media_type']) for x in batch[r['sha256']]}
    if len(others) > 1:
        return 'CONFLICT', 'the manifest gives these bytes sizes and media types %s' % sorted(others), None
    aid = ix['by_sha'].get(r['sha256'])
    if aid is None:
        return 'CREATE', 'no artifact has these bytes', None
    a = ix['artifacts'].get(aid) or {}
    differ = [k for k in ('bytes', 'media_type') if a.get(k) is not None and a[k] != r[k]]
    if differ:
        return 'CONFLICT', 'artifact %s records %s' % (aid, ', '.join('%s %r' % (k, a[k]) for k in differ)), aid
    loc = locator_of(r)
    where = 'URL' if loc[0] == 'URL' else 'held path'
    if loc in ix['placed'].get(aid, ()):
        return 'NOOP', 'artifact %s is held at this %s' % (aid, where), aid
    return 'REUSE', 'artifact %s holds these bytes; this %s is a new placement of it' % (aid, where), aid


def plan_manifest(rows, view):
    """The deterministic plan, read-only: rows in (sha256, locator, id) order, each with its action."""
    ix = view.index()
    batch = collections.defaultdict(list)
    for r in rows:
        batch[r['sha256']].append(r)
    items, counts = [], collections.Counter()
    for r in sorted(rows, key=lambda r: (r['sha256'], locator_of(r)[1], r['registration_id'])):
        action, reason, aid = classify(r, ix, batch)
        counts[action] += 1
        kind, value = locator_of(r)
        items.append({'registration_id': r['registration_id'], 'sha256': r['sha256'], 'url': r.get('url'),
                      'locator': {'kind': kind, 'value': value}, 'mode': mode_of(r),
                      'artifact': aid, 'action': action, 'reason': reason})
    new = sorted({it['sha256'] for it in items if it['action'] == 'CREATE'})
    return {'rows': items, 'actions': {a: counts[a] for a in ACTIONS}, 'artifacts': new,
            'placements': sum(1 for it in items if it['action'] in ('CREATE', 'REUSE'))}


def verify_plan(plan):
    conflicts = ['%s %s: %s' % (it['registration_id'], it['locator']['value'], it['reason'])
                 for it in plan['rows'] if it['action'] == 'CONFLICT']
    if conflicts:
        raise Conflict('%d conflict(s):\n  %s' % (len(conflicts), '\n  '.join(conflicts)))


def prepared(view, acq=None, rels=None, read_bytes=True):
    """(rows, plan) for the manifest against `view`, or SystemExit naming every problem."""
    rows = load_manifest(PATH[0])
    if not rows:
        return rows, None
    errors, ok = validate_manifest(rows, view, acq, rels, read_bytes)
    if errors:
        raise SystemExit('artifact-registration manifest: %d problem(s); nothing was written:\n  %s' % (
            len(errors), '\n  '.join(errors)))
    plan = plan_manifest(ok, view)
    try:
        verify_plan(plan)
    except Conflict as x:
        raise SystemExit('artifact-registration manifest: %s\nnothing was written' % x)
    return ok, plan


# ---------------------------------------------------------------- the migration's hooks

def _hook_rows():
    """The manifest's rows as the migration reads them: checked against their acquisition records (committed),
    not against the held bytes (sources/ is not part of a clone)."""
    rows = load_manifest(PATH[0])
    if not rows:
        return []
    errors, ok = structural(rows)
    if errors:
        raise SystemExit('artifact-registration manifest: %d problem(s):\n  %s' % (len(errors), '\n  '.join(errors)))
    batch = collections.defaultdict(set)
    for r in ok:
        batch[r['sha256']].add((r['bytes'], r['media_type']))
    bad = sorted(s for s, v in batch.items() if len(v) > 1)
    if bad:
        raise SystemExit('artifact-registration manifest: one sha256, several sizes or media types: %s' % bad)
    return ok


def m2_artifacts(m, known):
    """mig_m2_identity.documents: {sha256: row} of the registrations whose bytes no other input holds (`known`: every
    sha256 the migration mints or has joined already) - minted after them, in sha256 order. Recorded as an M2 stat
    only when there is one."""
    new = {}
    for r in _hook_rows():
        if r['sha256'] not in known:
            new.setdefault(r['sha256'], r)
    if new:
        m.stat('M2', ARTIFACT_STAT, len(new))
    return new


def placement_id(r, aid):
    kind, value = locator_of(r)
    return S.hid('Placement', kind, value, aid, 'arm')


def add_supplied_placement(m, r, aid):
    """The held file an estate supplied, as a LOCAL_PATH placement on the source it came from, observed on the day it
    was received; its DOCUMENT provenance states the supply and no fetch."""
    kind, value = locator_of(r)
    pid = m.prov('DOCUMENT', ACTOR, artifact=aid,
                 code_state={'stream': STREAM, 'runner': RUNNER, 'manifest': MANIFEST,
                             'registration_id': r['registration_id'], 'acquisition': r['acquisition'],
                             'origin': r['origin'], 'source_relationship': r['source_relationship'],
                             'supply_channel': r['supply_channel'], 'received_at': r['received_at'],
                             'original_filename': r['original_filename'], 'acquired_by': r['acquired_by'],
                             'correspondence': 'the bytes the estate supplied (sha256)'})
    loc = {'kind': kind, 'value': value}
    m.add('document/locators.jsonl', loc)
    day = S.bound('EXACT', r['received_at'], 'CALENDAR', 'DAY', pid)
    m.add('document/placements.jsonl', {
        'id': placement_id(r, aid), 'locator': loc, 'artifact': aid, 'source': r['source'], 'status': 'PRESENT',
        'retrieval_method': r['retrieval_method'], 'observed': {'valid_from': day, 'valid_to': day}, 'provenance': pid})


def add_placement(m, r, aid):
    if mode_of(r) == SUPPLIED:
        return add_supplied_placement(m, r, aid)
    pid = m.prov('DOCUMENT', ACTOR, artifact=aid,
                 code_state={'stream': STREAM, 'runner': RUNNER, 'manifest': MANIFEST,
                             'registration_id': r['registration_id'], 'acquisition': r['acquisition'],
                             'url': r['url'], 'fetched_at': r['fetched_at'], 'http_status': r['http_status'],
                             'acquired_by': r['acquired_by'], 'origin': r['origin'],
                             'correspondence': 'the bytes the acquisition fetched (sha256)'})
    loc = {'kind': 'URL', 'value': r['url']}
    m.add('document/locators.jsonl', loc)
    day = S.bound('EXACT', r['fetched_at'][:10], 'CALENDAR', 'DAY', pid)
    row = {'id': placement_id(r, aid), 'locator': loc, 'artifact': aid, 'status': 'PRESENT',
           'retrieval_method': r['retrieval_method'], 'observed': {'valid_from': day, 'valid_to': day},
           'provenance': pid}
    if r.get('source') is not None:
        row['source'] = r['source']
    m.add('document/placements.jsonl', row)


def m6_placements(m):
    """mig_m6_provenance.artifact_registration_placements: each row's placement - its URL, or for a supplied row its
    held file - where the model being built has none of that artifact at that locator (M3.2B's, M3.10A's or an
    earlier row's)."""
    rows = _hook_rows()
    if not rows:
        return
    placed = {(p.get('artifact'), p['locator']['kind'], p['locator']['value']) for p in m.rows('document/placements.jsonl')}
    n = 0
    for r in sorted(rows, key=lambda r: (r['sha256'], locator_of(r)[1], r['registration_id'])):
        aid = m.art[('sha256', r['sha256'])]
        key = (aid,) + locator_of(r)
        if key in placed:
            continue
        placed.add(key)
        add_placement(m, r, aid)
        n += 1
    if n:
        m.stat('M6', PLACEMENT_STAT, n)


# ---------------------------------------------------------------- writing (--apply)

def _migrate():
    import migrate
    return migrate


def rebuilt():
    """{relpath: bytes}: the migration of the current inputs with the manifest, as migrate.py writes it."""
    mig = _migrate()
    sys.modules['apply_artifact_registration_manifest'] = sys.modules[__name__]   # the hooks read this PATH
    return mig.render(mig.run(mig.STAGES[-1], mig.load_registry()), mig.STAGES[-1])


def changes(files, plan):
    """The model files the rebuild changes, verified to be exactly the plan's additions: every changed table one
    of TABLES, every earlier row kept, the artifacts and placements added exactly the plan's. {relpath: bytes}."""
    out = {rel: b for rel, b in files.items()
           if not os.path.exists(L.MODEL + rel) or open(L.MODEL + rel, 'rb').read() != b}
    mig = _migrate()
    stray = sorted(set(out) - set(TABLES) - {mig.MANIFEST})
    if stray:
        raise Conflict('the model is not current with its inputs: the rebuild also changes %s' % stray)
    added = {}
    for rel in TABLES:
        old = set(open(L.MODEL + rel, 'rb').read().splitlines())
        new = set(files[rel].splitlines())
        if old - new:
            raise Conflict('%s: the rebuild removes or alters %d row(s)' % (rel, len(old - new)))
        added[rel] = [json.loads(x) for x in sorted(new - old)]
    shas = sorted(r['legacy_key'] for r in added['identity/identity-map.jsonl'])
    if shas != plan['artifacts'] or len(added['identity/artifacts.jsonl']) != len(shas):
        raise Conflict('the rebuild mints %s, the plan %s' % (shas, plan['artifacts']))
    if len(added['document/placements.jsonl']) != plan['placements']:
        raise Conflict('the rebuild adds %d placement(s), the plan %d' % (len(added['document/placements.jsonl']),
                                                                         plan['placements']))
    old = json.load(open(L.MODEL + mig.MANIFEST, encoding='utf-8'))
    new = json.loads(files[mig.MANIFEST])
    for x in (old, new):
        x.pop('files')
        x['stats'].get('M2', {}).pop(ARTIFACT_STAT, None)
        x['stats'].get('M2', {}).pop('artifacts (manifest sha1, sha256 only)', None)
        x['stats'].get('M6', {}).pop(PLACEMENT_STAT, None)
    if old != new:
        raise Conflict('the rebuild changes the model manifest beyond the registration\'s counts')
    return out


def apply_manifest(plan, clock=None):
    """Write the plan: the migration rebuilt in memory, verified, then each changed file replaced; then the indexes
    rebuilt."""
    files = changes(rebuilt(), plan)
    if clock:
        clock.mark('application (migration)')
    for rel, b in sorted(files.items()):
        with open(L.MODEL + rel + '.tmp', 'wb') as f:
            f.write(b)
    for rel in sorted(files):
        os.replace(L.MODEL + rel + '.tmp', L.MODEL + rel)
    subprocess.run([sys.executable, L.ROOT + 'tools/build-indexes.py'], cwd=L.ROOT, env=dict(os.environ), check=True,
                   stdout=subprocess.DEVNULL)
    if clock:
        clock.mark('output generation (indexes)')
    return files


def check(plan):
    """The model holds every row (each NOOP), and its stats count exactly what the mechanism added."""
    pending = ['%s %s %s' % (it['registration_id'], it['url'], it['action']) for it in (plan or {'rows': []})['rows']
               if it['action'] != 'NOOP']
    man = json.load(open(L.MODEL + 'manifest.json', encoding='utf-8'))
    prov = {p['id']: p for p in L.read_table('cross/provenance.jsonl')}
    mine = sum(1 for p in L.read_table('document/placements.jsonl') if (prov.get(p['provenance']) or {}).get('actor') == ACTOR)
    if man['stats'].get('M6', {}).get(PLACEMENT_STAT, 0) != mine:
        pending.append('the model manifest counts %s placement(s), the model holds %d' % (
            man['stats'].get('M6', {}).get(PLACEMENT_STAT, 0), mine))
    return pending


# ---------------------------------------------------------------- output and main

class Clock:
    def __init__(self):
        self.t, self.marks = time.perf_counter(), []

    def mark(self, name):
        now = time.perf_counter()
        self.marks.append((name, now - self.t))
        self.t = now

    def report(self):
        return '\n'.join('%-28s %7.3f s' % kv for kv in self.marks) + '\n%-28s %7.3f s' % (
            'total', sum(s for _, s in self.marks))


def render_plan(plan, n_rows):
    out = []
    for it in (plan or {'rows': []})['rows']:
        out.append('%s  %s %s' % (it['registration_id'], it['locator']['kind'], it['locator']['value']))
        out.append('  sha256: %s' % it['sha256'])
        out.append('  action: %s (%s)' % (it['action'], it['reason']))
        out.append('')
    a = (plan or {}).get('actions') or {k: 0 for k in ACTIONS}
    out.append('%d manifest row(s): %s' % (n_rows, ', '.join('%d %s' % (a[k], k) for k in ACTIONS)))
    out.append('%d artifact(s) minted, %d placement(s)' % (len((plan or {}).get('artifacts') or []),
                                                          (plan or {}).get('placements') or 0))
    out.append('0 evidence decisions, 0 attributions, 0 estates, 0 wines, 0 vintages, 0 values')
    return '\n'.join(out) + '\n'


def main():
    args = sys.argv[1:]
    clock = Clock()
    mode = next((a for a in ('--apply', '--plan', '--check-all', '--check', '--validate') if a in args), '--validate')
    if '--manifest' in args:
        PATH[0] = os.path.abspath(args[args.index('--manifest') + 1])
    try:
        view = View()
        view.index()
        clock.mark('model loading')
        rows = load_manifest(PATH[0])
        errors, ok = validate_manifest(rows, view) if rows else ([], [])
        clock.mark('manifest validation')
        if errors:
            raise SystemExit('%d problem(s); nothing was written:\n  %s' % (len(errors), '\n  '.join(errors)))
        plan = plan_manifest(ok, view) if rows else None
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
            if not plan or not (plan['actions']['CREATE'] or plan['actions']['REUSE']):
                L.out('nothing to apply: %d row(s), all held (NOOP)' % len(rows))
            else:
                files = apply_manifest(plan, clock)
                L.out('applied: %d CREATE, %d REUSE; %d NOOP' % (
                    plan['actions']['CREATE'], plan['actions']['REUSE'], plan['actions']['NOOP']))
                L.out('  %d artifact(s) minted, %d placement(s); files: %s' % (
                    len(plan['artifacts']), plan['placements'], ', '.join(sorted(files))))
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
            L.out('artifact-registration manifest: %d row(s) held by the model' % len(rows))
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
