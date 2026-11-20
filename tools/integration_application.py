"""The integration application, named exactly: the first controlled application of the three manifests that
tools/integration-review.py writes from data/audit/integration-review.jsonl.

The application is three runs of the generic runners, in order:

    tools/apply-evidence-acceptance-manifest.py --apply   evidence v10: the 34 decisions eam_000001-eam_000034
    tools/apply-vintage-creation-manifest.py --apply      34 attributions (17 REVIEWED_LISTING, 17 DOCUMENT_TEXT)
                                                          on 51 provenance rows, vcm_000001-vcm_000033, no vintage
    tools/apply-value-manifest.py --apply                 51 values, observations and reconciliations on 102
                                                          provenance rows, vam_000010-vam_000060 (36 statements,
                                                          15 C6 yields); vam_000001-vam_000009 are M3.10C's, held

Then the gap register records what it resolved (tools/build-data-gap-register.py, its resolutions file).

The repository is in exactly one of two states, and phase() says which:

    PRE_APPLY    none of the three manifests holds a row named below, the store has no v10, the model manifest
                 has neither runner's stat
    POST_APPLY   each manifest holds exactly the rows named below (their bytes pinned by DIGEST), the store's
                 v10 is exactly the 34 decisions those rows name, and the model manifest carries both stats

Anything else - a manifest written but not applied, a stage applied without the next, a row edited after the
fact - is neither, and phase() fails. The pre-apply guards run in PRE_APPLY unchanged; the post-apply checks
run in POST_APPLY; no check accepts "either".

A model row is the application's (is_row) only on its own provenance: one of the two runners, its stream, its
manifest file, one of the manifest ids below and evidence version 10. A row a later run of the same runners
adds carries another manifest id and is not set aside by anything here.
"""
import functools
import hashlib
import json
import os

import migration_lib as L

NAME = 'the integration application'
PHASE = 'INTEGRATION'                    # its key in data/audit/m32-resolutions.json and the gap register
REVIEW = 'data/audit/integration-review.jsonl'
MANIFESTS = {'acceptance': 'data/audit/evidence-acceptance-manifest.jsonl',
             'vintage': 'data/audit/vintage-creation-manifest.jsonl',
             'value': 'data/audit/value-application-manifest.jsonl'}
ID_FIELD = {'acceptance': 'acceptance_id', 'vintage': 'manifest_id', 'value': 'manifest_id'}
IDS = {'acceptance': tuple('eam_%06d' % i for i in range(1, 35)),
       'vintage': tuple('vcm_%06d' % i for i in range(1, 34)),
       'value': tuple('vam_%06d' % i for i in range(10, 61))}
# sha256 of the application's rows of each manifest, as the runners read them (one compact JSON line each)
DIGEST = {'acceptance': '0a39e4dc45dc94743a1f483eacbd95055914a674d8a3bc2bd81086ae9168b0c7',
          'vintage': 'a9cd541c15be1dd051bc251f568eed6e29e6d65e5c4098b9520c1c7ee7f02009',
          'value': '3a70466fbcbf70a2b338945cb9c65451240480eee64039778585d35048f835bb'}
EVIDENCE_VERSION = 10
PRE_APPLY_COMMIT = '8c9233b'               # the reviewed state the application starts from (model, store, manifests)
READER = '6f68a0af15d3'                    # the decider fingerprint v6-v9 record, and v10 with them
ACTORS = {'tools/apply-vintage-creation-manifest.py': ('vintage-creation', 'vintage'),
          'tools/apply-value-manifest.py': ('value-application', 'value')}
STATS = {'M6': 'vintage-creation manifest attributions', 'M7': 'value-application manifest values'}
FILES = ('document/attributions.jsonl', 'cross/provenance.jsonl', 'observation/observations.jsonl',
         'reconciliation/reconciliations.jsonl', 'canonical/values.jsonl', 'derived/vintage-documents.json',
         'manifest.json')

# the two states, exactly
PRE_APPLY = {'evidence': 9, 'vintages': 5292, 'values': 13004, 'attributions': 12211,
             'manifests': {'acceptance': 0, 'vintage': 0, 'value': 9, 'artifact': 0}}
POST_APPLY = {'evidence': 10, 'vintages': 5292, 'values': 13055, 'attributions': 12245,
              'manifests': {'acceptance': 34, 'vintage': 33, 'value': 60, 'artifact': 0}}
ADDED = {'evidence decisions': 34, 'identity/vintages.jsonl': 0, 'document/attributions.jsonl': 34,
         'cross/provenance.jsonl': 153, 'observation/observations.jsonl': 51,
         'reconciliation/reconciliations.jsonl': 51, 'canonical/values.jsonl': 51}
ATTRIBUTION_METHODS = {'REVIEWED_LISTING': 17, 'DOCUMENT_TEXT': 17}
PROVENANCE = {('vintage-creation', 'DOCUMENT'): 34, ('vintage-creation', 'ESTATE_PUBLICATION'): 17,
              ('value-application', 'DOCUMENT'): 51, ('value-application', 'DERIVATION'): 51}
OBSERVATIONS = {'EXPLICIT_LABELLED': 36, 'UNIT_FROM_LAYOUT': 15}

_IDSET = {k: frozenset(v) for k, v in IDS.items()}


def _digest(rows):
    return hashlib.sha256(''.join(L.dumps(r) + '\n' for r in rows).encode('utf-8')).hexdigest()


def manifest_rows(kind):
    """The application's rows of one manifest, in file order (none in PRE_APPLY)."""
    path = L.ROOT + MANIFESTS[kind]
    rows = L.jsonl_lines(path) if os.path.exists(path) else []
    return [r for r in rows if r.get(ID_FIELD[kind]) in _IDSET[kind]]


def reads_repository_model():
    """True when L.MODEL is the repository's own model (not a copy named by BDX_MODEL_DIR)."""
    return os.path.abspath(L.MODEL) == os.path.abspath(L.ROOT + 'data/model')


def _stats():
    # the repository's own committed model, whatever BDX_MODEL_DIR names: the phase is the repository's
    m = json.load(open(L.ROOT + 'data/model/manifest.json', encoding='utf-8'))
    s = m.get('stats') or {}
    return {st: (s.get(st) or {}).get(name) for st, name in STATS.items()}


def phase():
    """'PRE_APPLY' or 'POST_APPLY', each exactly as the module docstring says; anything else fails."""
    import evidence_store as ST
    rows = {k: manifest_rows(k) for k in MANIFESTS}
    has_version = EVIDENCE_VERSION in ST.versions()
    stats = _stats()
    if not any(rows.values()) and not has_version and not any(stats.values()):
        return 'PRE_APPLY'
    problems = []
    for k, rs in rows.items():
        ids = tuple(r[ID_FIELD[k]] for r in rs)
        if ids != IDS[k]:
            problems.append('%s manifest holds %d of the %d application rows' % (k, len(ids), len(IDS[k])))
        elif _digest(rs) != DIGEST[k]:
            problems.append('%s manifest: the application rows are not the reviewed ones' % k)
    if not has_version:
        problems.append('the store has no v%d' % EVIDENCE_VERSION)
    if stats != {'M6': ADDED['document/attributions.jsonl'], 'M7': ADDED['canonical/values.jsonl']}:
        problems.append('the model manifest stats are %s' % stats)
    assert not problems, '%s is neither unapplied nor applied: %s' % (NAME, '; '.join(problems))
    evidence_rows()
    return 'POST_APPLY'


def evidence_keys():
    """The decision keys the application's vintage rows name: the 34 its acceptance rows appended."""
    out = set()
    for r in manifest_rows('vintage'):
        out |= set(r['evidence_decisions'].values())
    return out


def evidence_rows():
    """v10, verified to be exactly the application's decisions: the 34 keys its manifest names and no other, each an
    ACCEPTED guard row by the decider fingerprint v6-v9 record. [] when there is no v10."""
    import evidence_store as ST
    import mig_m6_provenance as M6
    if EVIDENCE_VERSION not in ST.versions():
        return []
    rows = list(ST.iter_rows([EVIDENCE_VERSION]))
    keys = [M6.row_key(d) for d in rows]
    assert len(keys) == len(set(keys)) == ADDED['evidence decisions'] and set(keys) == evidence_keys(), \
        'v%d is not exactly %s\'s decisions' % (EVIDENCE_VERSION, NAME)
    assert all(d.get('kind') == 'guard' and d.get('decision') == 'ACCEPTED' and d.get('reader') == READER
               for d in rows), 'a v%d row of another kind' % EVIDENCE_VERSION
    return rows


def is_provenance(p):
    """A provenance row the application wrote: its runner, stream, manifest and one of its manifest ids (unique, and
    their rows pinned by DIGEST); a row that names an evidence version names v10. (The vintage stage's DOCUMENT rows
    under a listing attribution name none.)"""
    s = ACTORS.get(p.get('actor'))
    cs = p.get('code_state') or {}
    return bool(s) and cs.get('stream') == s[0] and cs.get('manifest') == MANIFESTS[s[1]] \
        and cs.get('manifest_id') in _IDSET[s[1]] and cs.get('evidence_version', EVIDENCE_VERSION) == EVIDENCE_VERSION


def is_row(rel, r, prov):
    """A model row the application added: a provenance row it wrote, or an attribution, observation, reconciliation
    or canonical value on one. It creates no vintage."""
    if rel == 'cross/provenance.jsonl':
        return is_provenance(r)
    if rel in ('document/attributions.jsonl', 'observation/observations.jsonl',
               'reconciliation/reconciliations.jsonl', 'canonical/values.jsonl'):
        return is_provenance(prov.get(r.get('provenance')) or {})
    return False


def row_key(rel, r):
    """A model row's identity: its id, or (subject, field) for a canonical value."""
    return (r['subject'], r['field']) if rel == 'canonical/values.jsonl' else r['id']


@functools.lru_cache(maxsize=None)
def _rows_cached(rel, key):
    prov = {p['id']: p for p in L.read_table('cross/provenance.jsonl')}
    return tuple(row_key(rel, r) for r in L.read_table(rel) if is_row(rel, r, prov))


def row_ids(rel):
    """The keys (row_key) of the application's rows in one model table (read once per state of the model files)."""
    st = [os.stat(L.MODEL + f) for f in (rel, 'cross/provenance.jsonl')]
    return _rows_cached(rel, tuple((s.st_size, s.st_mtime_ns) for s in st))


def links(prov):
    """{(vintage ref, artifact)} the application's attributions link."""
    return {(a['vintage'], a['artifact']) for a in L.read_table('document/attributions.jsonl')
            if is_row('document/attributions.jsonl', a, prov)}


# -- the two states, verified exactly ------------------------------------------------------------------------------

def counts():
    """The model and store figures each state fixes."""
    import evidence_store as ST
    man = {k: len(L.jsonl_lines(L.ROOT + p)) if os.path.exists(L.ROOT + p) else 0 for k, p in MANIFESTS.items()}
    p = L.ROOT + 'data/audit/artifact-registration-manifest.jsonl'
    man['artifact'] = len(L.jsonl_lines(p)) if os.path.exists(p) else 0
    return {'evidence': max(ST.versions()), 'vintages': len(L.read_table('identity/vintages.jsonl')),
            'values': len(L.read_table('canonical/values.jsonl')),
            'attributions': len(L.read_table('document/attributions.jsonl')), 'manifests': man}


def verify():
    """The current state, checked against its exact figures: PRE_APPLY's, or POST_APPLY's with every added row by
    kind. Returns the phase; an assertion error names the first figure that differs."""
    import collections
    ph = phase()
    want = PRE_APPLY if ph == 'PRE_APPLY' else POST_APPLY
    got = counts()
    assert got == want, '%s: %s, not %s' % (ph, got, want)
    if ph == 'PRE_APPLY':
        assert not any(row_ids(rel) for rel in IA_TABLES), 'an application row in the pre-apply model'
        return ph
    added = {rel: len(row_ids(rel)) for rel in IA_TABLES}
    added['evidence decisions'] = len(evidence_rows())
    added['identity/vintages.jsonl'] = 0
    assert added == ADDED, added
    prov = {p['id']: p for p in L.read_table('cross/provenance.jsonl')}
    att = [a for a in L.read_table('document/attributions.jsonl') if is_row('document/attributions.jsonl', a, prov)]
    assert dict(collections.Counter(a['method'] for a in att)) == ATTRIBUTION_METHODS
    pk = collections.Counter(((p.get('code_state') or {}).get('stream'), p['kind']) for p in prov.values() if is_provenance(p))
    assert dict(pk) == PROVENANCE, dict(pk)
    obs = [o for o in L.read_table('observation/observations.jsonl') if is_row('observation/observations.jsonl', o, prov)]
    assert dict(collections.Counter(o['confidence'] for o in obs)) == OBSERVATIONS
    return ph


IA_TABLES = ('document/attributions.jsonl', 'cross/provenance.jsonl', 'observation/observations.jsonl',
             'reconciliation/reconciliations.jsonl', 'canonical/values.jsonl')


# -- the gap register's record of the application -----------------------------------------------------------------

RESOLUTIONS = 'data/audit/m32-resolutions.json'
WHAT = ('vintage figures the model lacked, stated in accepted documents the integration review read (36 statements, '
        '15 C6 layout-derived yields; value-application manifest vam_000010-vam_000060), and document-less vintages '
        'its attributions now document (vintage-creation manifest vcm_000001-vcm_000033, all ATTRIBUTION_ONLY; '
        'evidence version 10)')


def applying_commit():
    """The commit that applied the application: the one that added its evidence version's decision file."""
    import subprocess
    out = subprocess.run(['git', 'log', '--diff-filter=A', '--format=%H', '--',
                          'data/evidence/decisions-v%d.jsonl' % EVIDENCE_VERSION],
                         cwd=L.ROOT, capture_output=True, encoding='utf-8', check=True).stdout.split()
    assert len(out) == 1, 'v%d was added by %d commits' % (EVIDENCE_VERSION, len(out))
    return out[0][:7]


def resolution_entry():
    return {'commit': applying_commit(), 'method': 'EXISTING_EVIDENCE_REVIEW', 'what': WHAT}


def record_resolution():
    """Write the application's entry into the resolutions file (POST_APPLY, committed): the register then records,
    on each gap it reduced, what it resolved and by which commit. Idempotent; a different existing entry fails."""
    assert verify() == 'POST_APPLY', 'the application is not applied'
    path = L.ROOT + RESOLUTIONS
    d = json.load(open(path, encoding='utf-8'))
    entry = resolution_entry()
    if PHASE in d:
        assert d[PHASE] == entry, 'a different %s entry is recorded: %s' % (PHASE, d[PHASE])
        return False
    d[PHASE] = entry
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(d, ensure_ascii=False, indent=1) + '\n')
    return True


def main(argv):
    if '--record-resolution' in argv:
        print('%s: %s entry %s' % (RESOLUTIONS, PHASE, 'written' if record_resolution() else 'already recorded'))
        return 0
    ph = verify()
    print('%s: %s, figures exact' % (NAME, ph))
    if ph == 'POST_APPLY':
        d = json.load(open(L.ROOT + RESOLUTIONS, encoding='utf-8'))
        rec = d.get(PHASE)
        print('  gap register resolution entry: %s' % ('recorded, commit %s' % rec['commit'] if rec else 'NOT YET RECORDED'))
        if '--check' in argv:
            assert rec == resolution_entry(), 'the %s resolution entry is %s, not %s' % (PHASE, rec, resolution_entry())
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv[1:]))


# -- the pre-application state, as a fixture -----------------------------------------------------------------------
# Suites whose synthetic cases are built on the model as it stood before the application (a vintage without this
# value, a store whose next version is v10) read that state here: in PRE_APPLY it is the committed state itself
# (HEAD), in POST_APPLY the commit the application started from. Never a filter by date or by "newer".

def fixture_rev():
    return 'HEAD' if phase() == 'PRE_APPLY' else PRE_APPLY_COMMIT


def _git_bytes(*a):
    import subprocess
    return subprocess.run(['git'] + list(a), cwd=L.ROOT, capture_output=True, check=True).stdout


@functools.lru_cache(maxsize=None)
def _before_text(rel):
    return _git_bytes('show', '%s:data/model/%s' % (PRE_APPLY_COMMIT, rel)).decode('utf-8')


def read_before(rel):
    """A model table as committed at PRE_APPLY_COMMIT (L.read_table's rows, fresh dicts each call)."""
    return [json.loads(x) for x in _before_text(rel).splitlines() if x.strip()]


def applied_values():
    """{(vintage ref, field): value} the application's value rows add, from its pinned manifest rows."""
    return {('vt:%s:%d' % (r['wine_id'], r['vintage']), r['field']): r['value'] for r in manifest_rows('value')}


def without_rows(files):
    """A migration render ({rel: bytes}) with the application's rows taken out of every table, and its stats and
    those rows out of the model manifest (each table's count and sha256 recomputed as migrate.render computes them):
    the render of the same inputs before the application."""
    import hashlib
    rel_p = 'cross/provenance.jsonl'
    prov = {}
    if rel_p in files:
        prov = {r['id']: r for r in (json.loads(x) for x in files[rel_p].decode('utf-8').splitlines() if x.strip())}
    out, gone = {}, {}
    for rel, b in files.items():
        if not rel.endswith('.jsonl'):
            out[rel] = b
            continue
        lines = b.decode('utf-8').splitlines()
        kept = [x for x in lines if not is_row(rel, json.loads(x), prov)]
        gone[rel] = len(lines) - len(kept)
        out[rel] = ''.join(x + '\n' for x in kept).encode('utf-8')
    if 'manifest.json' in out:
        man = json.loads(out['manifest.json'].decode('utf-8'))
        # its stats count its rows among others (a rebuild applies M3.10C's nine through the value runner too): its
        # own counts subtracted, the stat dropped only when nothing else is left in it
        mine = {'M6': ADDED['document/attributions.jsonl'], 'M7': ADDED['canonical/values.jsonl']}
        for st, name in STATS.items():
            stats = (man.get('stats') or {}).get(st, {})
            if name in stats:
                stats[name] -= mine[st]
                if not stats[name]:
                    del stats[name]
        for rel, n in gone.items():
            if n and rel in man['files']:
                man['files'][rel]['rows'] -= n
                man['files'][rel]['sha256'] = hashlib.sha256(out[rel]).hexdigest()
        out['manifest.json'] = (json.dumps(man, ensure_ascii=False, indent=1) + '\n').encode('utf-8')
    return out
