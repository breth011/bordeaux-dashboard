"""Phase 4: the reversible migration into the normalized model.

    python tools/migrate.py --until M5     build stages M1..M5 into data/model/
    python tools/migrate.py --check        rebuild from scratch in memory and
                                           compare with data/model/ byte for byte
    python tools/migrate.py --revert M5    drop what M5 and later stages added

Additive: no stage reads or writes anything outside data/model/ except to
read the legacy files, the evidence store, the discovery data and the
document-date audit (data/history/document-dates.jsonl), which are never
written (tools/phase4-baseline.py --check). Each stage is a function
over one in-memory model; the runner validates every row against the
Phase 3.4 contract (tools/model_schema.py), refuses dangling references,
and writes each table sorted by its key. Reverting a stage is rebuilding up
to the stage before it: nothing outside data/model/ was ever changed.
"""
import collections
import importlib
import json
import os
import shutil
import sys

import migration_lib as L
import model_schema as S

STAGES = ['M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7']
MODULES = {'M2': 'mig_m2_identity', 'M3': 'mig_m3_grand', 'M4': 'mig_m4_wines',
           'M5': 'mig_m5_vintages', 'M6': 'mig_m6_provenance', 'M7': 'mig_m7_observations',
           'M13': 'mig_m13_indexes'}
MANIFEST = 'manifest.json'
# The identity-map namespaces whose stable ids are minted (and so must be
# reused on a rebuild); every other namespace maps onto one of these.
MINT_NS = {'estate', 'grand-vin', 'wine-by-slug', 'second-by-name', 'graves-white',
           'artifact-by-sha1', 'artifact-by-sha256', 'source', 'party'}


class Model:
    """Every table in memory, keyed by the table's key, plus the minting
    registry carried over from the previous build."""

    def __init__(self, registry=None):
        self.tables = collections.defaultdict(dict)
        self.registry = registry or {}        # (namespace, legacy_key) -> minted id
        self.counters = collections.Counter()
        for (ns, k), i in self.registry.items():
            p, n = i.split('_', 1)
            if n.isdigit():
                self.counters[p] = max(self.counters[p], int(n))
        self.stats = collections.OrderedDict()

    def key(self, relpath, row):
        k = S.LAYOUT[relpath][1]
        return tuple(row.get(x) for x in k) if isinstance(k, tuple) else row[k]

    def add(self, relpath, row, replace=False):
        k = self.key(relpath, row)
        t = self.tables[relpath]
        if k in t and t[k] != row and not replace:
            raise SystemExit('%s: two different rows for %r:\n %s\n %s' % (
                relpath, k, L.dumps(t[k]), L.dumps(row)))
        t[k] = row
        return row

    def get(self, relpath, k):
        return self.tables[relpath].get(k)

    def rows(self, relpath):
        return list(self.tables[relpath].values())

    def mint(self, entity, namespace, legacy_key):
        """The minted id for a legacy key: the one already issued, or the
        next in sequence. Callers mint in a sorted order."""
        rk = (namespace, legacy_key)
        if rk not in self.registry:
            p = S.MINTED[entity][0]
            self.counters[p] += 1
            self.registry[rk] = S.mint(entity, self.counters[p])
        return self.registry[rk]

    def prov(self, kind, actor, **kw):
        """A Provenance record, deduplicated by content."""
        row = {'kind': kind, 'actor': actor}
        row.update({k: v for k, v in kw.items() if v is not None})
        row['id'] = S.hid('Provenance', L.dumps({k: v for k, v in row.items() if k != 'id'}))
        self.add('cross/provenance.jsonl', row)
        return row['id']

    def finding(self, target, kind, detail, detected_by, prov):
        row = {'id': S.hid('QualityFinding', target, kind, detail), 'target': target,
               'kind': kind, 'status': 'OPEN', 'detail': detail,
               'detected_by': detected_by, 'provenance': prov}
        self.add('cross/findings.jsonl', row)
        return row['id']

    def stat(self, stage, name, value):
        self.stats.setdefault(stage, collections.OrderedDict())[name] = value


def load_registry():
    """Minted ids from the committed identity map (namespace, legacy_key)."""
    reg = {}
    for r in L.read_table('identity/identity-map.jsonl'):
        if r.get('stable_id') and r['namespace'] in MINT_NS:
            reg[(r['namespace'], r['legacy_key'])] = r['stable_id']
    return reg


def all_ids(m):
    ids = set()
    for rel, t in m.tables.items():
        for row in t.values():
            if 'id' in row:
                ids.add(row['id'])
    for (w, lab) in m.tables['identity/vintages.jsonl']:
        ids.add(S.vref(w, lab))
    return ids


def validate(m):
    ids = all_ids(m)
    errs = []
    for rel, t in sorted(m.tables.items()):
        entity = S.LAYOUT[rel][0]
        for row in t.values():
            for e in S.check_row(entity, row, ids):
                errs.append('%s: %s' % (rel, e))
    return errs


def run(until, registry=None):
    m = Model(registry)
    for st in STAGES[:STAGES.index(until) + 1]:
        if st == 'M1':
            continue                    # M1 is the layout itself (model_schema.py)
        mod = importlib.import_module(MODULES[st])
        mod.run(m)
    errs = validate(m)
    if errs:
        raise SystemExit('%d contract violation(s):\n  %s' % (len(errs), '\n  '.join(errs[:40])))
    return m


def snapshots(stages, registry=None):
    """One build, rendered at each stage named in `stages` ({stage: {relpath: bytes}}).
    The stages are additive, so the model after Mk rendered at Mk is what a
    separate build --until Mk renders (Phase 5 C2: one build serves the
    determinism and rollback checks)."""
    m = Model(registry)
    out = {}
    last = max(STAGES.index(s) for s in stages)
    for st in STAGES[:last + 1]:
        if st != 'M1':
            importlib.import_module(MODULES[st]).run(m)
        if st in stages:
            errs = validate(m)
            if errs:
                raise SystemExit('%d contract violation(s) at %s' % (len(errs), st))
            out[st] = render(m, st)
    return out


def render(m, until):
    """{relpath: bytes} for every table the stages reached, plus the manifest."""
    reached = set(STAGES[:STAGES.index(until) + 1])
    files = {}
    for rel, (entity, key, stage) in sorted(S.LAYOUT.items()):
        if stage not in reached:
            continue
        rows = sorted(m.tables[rel].values(), key=lambda r: L.dumps(m.key(rel, r)))
        files[rel] = ''.join(L.dumps(r) + '\n' for r in rows).encode('utf-8')
    import hashlib
    man = {
        '_': 'The normalized model (Phase 4). Built by tools/migrate.py; do not edit by hand. '
             'Layout and id rules: tools/model_schema.py; storage decision D3 there.',
        'stage': until,
        'contract': 'docs/phase34-model.json',
        'files': {rel: {'entity': S.LAYOUT[rel][0], 'rows': len(m.tables[rel]),
                        'sha256': hashlib.sha256(b).hexdigest()} for rel, b in files.items()},
        'views': S.VIEWS,
        'stats': m.stats,
    }
    files[MANIFEST] = (json.dumps(man, ensure_ascii=False, indent=1) + '\n').encode('utf-8')
    return files


def write(files):
    keep = {'baseline.json'}
    for rel, b in files.items():
        p = L.MODEL + rel
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p + '.tmp', 'wb') as f:
            f.write(b)
        os.replace(p + '.tmp', p)
    # A table no stage reached any more (after --revert) is removed.
    for rel in S.LAYOUT:
        if rel not in files and os.path.exists(L.MODEL + rel):
            os.remove(L.MODEL + rel)
    for d in sorted({os.path.dirname(L.MODEL + r) for r in S.LAYOUT}):
        if os.path.isdir(d) and not os.listdir(d):
            os.rmdir(d)
    return keep


def current_stage():
    p = L.MODEL + MANIFEST
    return json.load(open(p, encoding='utf-8'))['stage'] if os.path.exists(p) else None


def main():
    a = sys.argv[1:]
    if '--check' in a:
        until = current_stage()
        if not until:
            sys.exit('no model built')
        bad = []
        for label, reg in (('from scratch', None), ('with the registry', load_registry())):
            files = render(run(until, reg), until)
            for rel, b in files.items():
                p = L.MODEL + rel
                if not os.path.exists(p) or open(p, 'rb').read() != b:
                    bad.append('%s differs (%s)' % (rel, label))
        L.out('\n'.join(bad) if bad else 'model at %s rebuilds byte for byte' % until)
        sys.exit(1 if bad else 0)
    if '--revert' in a:
        st = a[a.index('--revert') + 1]
        prev = STAGES[STAGES.index(st) - 1]
        files = render(run(prev, load_registry()), prev)
        write(files)
        L.out('reverted to %s' % prev)
        return
    until = a[a.index('--until') + 1] if '--until' in a else STAGES[-1]
    m = run(until, load_registry())
    files = render(m, until)
    write(files)
    for rel, info in json.loads(files[MANIFEST])['files'].items():
        L.out('%-42s %7d' % (rel, info['rows']))
    for st, kv in m.stats.items():
        for k, v in kv.items():
            L.out('%s %s: %s' % (st, k, v))


if __name__ == '__main__':
    main()
