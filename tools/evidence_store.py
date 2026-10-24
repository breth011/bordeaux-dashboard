# -*- coding: utf-8 -*-
"""Where the evidence decisions live, and the only code that touches them.

    python tools/evidence_store.py              summary of the store
    python tools/evidence_store.py --verify     check every part's hash

                              THE LAYOUT

    data/evidence/index.json             what is stored, and its hashes
    data/evidence/decisions-v1.jsonl     decider version 1
    data/evidence/decisions-v2.jsonl     decider version 2
    data/evidence/decisions-v3.jsonl     decider version 3
    data/evidence/decisions-v4.jsonl     ...and so on, one per version

Until Phase 2.4 every version shared one file,
data/evidence-decisions.jsonl. It reached 64 MB at v3. Git stored it
well (all three revisions pack to 2.4 MB), but GitHub refuses any
single file over 100 MB. Each pass adds about 29 MB, so the file
would have gone over at v5. Splitting by version keeps the
append-only log and fixes that:

  - a version's file only ever grows, and only while that version's
    reader is the one writing it;
  - v1, v2 and v3 were moved line for line, unchanged.
    tools/migrate-evidence-store.py proves it, and the index keeps the
    old file's hash, so the proof can be repeated;
  - a version that outgrows PART_LIMIT continues in
    decisions-vN.part2.jsonl, so no file reaches GitHub's 50 MB
    warning.

                              THE RULES

append() is the only writer, and it refuses:

  - a row whose `v` is not the version being appended to;
  - a row whose `reader` fingerprint differs from the one that version
    was opened with. A version is one reader. When the reader changes,
    that is a new decider version, never more rows under the old one;
  - from v4 on, a row without established provenance (Phase 2.5,
    tools/provenance.py):
      read.path     the file actually read, under sources/
      read.sha256   SHA-256 of the bytes the reader was given
      git.commit    the full HEAD sha
      git.dirty     whether the working tree differed from it
      git.status_hash   which uncommitted state, when dirty
    and a v4 row carrying the v1-v3 fields `observed` or `commit`,
    whose meanings were the manifest's hash and HEAD at run time.
    Those meanings stay with v1-v3; a v4 row must not be read as
    having them. v1-v3 lack all of this, and Phase 2.4 found why it
    matters: rows named a document while the bytes read came from a
    same-named file in another folder. They also recorded the
    manifest's hash instead of computing one, and named a commit made
    before the code that decided;
  - a provenance failure (`kind: provenance_failure`). That is "we
    could not establish which document was read", not a verdict, and
    it goes to append_failures() and its own file,
    provenance-failures-vN.jsonl, which iter_rows() never reads.

It also drops a row whose identity (evidence.row_key) is already
stored, or that appears twice in one batch. v1-v3 hold 1,228 such
duplicates. They are kept as written, and no more can be added.
"""
import hashlib
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
DIR = ROOT + 'data/evidence/'
INDEX = DIR + 'index.json'
# Below GitHub's 50 MB warning, with room for one batch to overshoot it.
PART_LIMIT = 40 * 1000 * 1000
# From this version on, a row must say what it read and from which code.
PROVENANCE_FROM = 4


def _load_index():
    if not os.path.exists(INDEX):
        return {'versions': {}}
    with io.open(INDEX, encoding='utf-8') as f:
        return json.load(f)


def _save_index(ix):
    with io.open(INDEX, 'w', encoding='utf-8', newline='') as f:
        f.write(json.dumps(ix, ensure_ascii=False, indent=1,
                           sort_keys=True) + '\n')


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def versions():
    """The decider versions stored, in order."""
    return sorted(int(v) for v in _load_index().get('versions', {}))


def parts(v):
    """The files holding version v, in order."""
    meta = _load_index().get('versions', {}).get(str(v)) or {}
    return [DIR + p['file'] for p in meta.get('parts', [])]


def iter_lines(v):
    """Version v's lines exactly as stored, as bytes without the newline."""
    for p in parts(v):
        with open(p, 'rb') as f:
            for line in f:
                yield line.rstrip(b'\n')


def iter_rows(only=None):
    """Every decision, oldest version first, in the order written.

    `only` limits it to some versions: iter_rows([3]).
    """
    for v in versions():
        if only is not None and v not in only:
            continue
        for line in iter_lines(v):
            if line.strip():
                yield json.loads(line.decode('utf-8'))


def existing_keys(only=None):
    import evidence as EV
    return set(EV.row_key(d) for d in iter_rows(only))


def latest_by_context():
    """For each question asked (row_key without the version), the decision
    of the highest version that asked it. Earlier answers stay in the
    store; this is a reading of it, not a replacement."""
    import evidence as EV
    out = {}
    for d in iter_rows():
        k = EV.row_key(d)[:-1]
        if k not in out or (d.get('v') or 0) >= (out[k].get('v') or 0):
            out[k] = d
    return out


class RefusedAppend(Exception):
    pass


def append(rows, v):
    """Append decisions of version v. Returns how many were written."""
    import evidence as EV
    v = int(v)
    ix = _load_index()
    meta = ix['versions'].setdefault(str(v), {'parts': [], 'readers': [],
                                              'commits': []})
    for r in rows:
        if r.get('v') != v:
            raise RefusedAppend('a row of version %r appended to v%d'
                                % (r.get('v'), v))
    readers = set(r.get('reader') for r in rows)
    if meta['readers'] and not readers <= set(meta['readers']):
        raise RefusedAppend(
            'v%d was written by reader %s; these rows come from %s. A '
            'changed reader is a new decider version.'
            % (v, ', '.join(meta['readers']),
               ', '.join(sorted(str(x) for x in readers))))
    for r in rows:
        if r.get('kind') == 'provenance_failure' \
                or r.get('code') in FAILURE_CODES:
            raise RefusedAppend('a provenance failure is not a decision: '
                                '%s' % r.get('artifact'))
    if v >= PROVENANCE_FROM:
        for r in rows:
            why = provenance_problem(r)
            if why:
                raise RefusedAppend('v%d: %s: %s'
                                    % (v, why, r.get('artifact')))

    seen = existing_keys([v])
    fresh = []
    for r in rows:
        k = EV.row_key(r)
        if k in seen:
            continue
        seen.add(k)
        fresh.append(r)
    if not fresh:
        return 0

    if not os.path.isdir(DIR):
        os.makedirs(DIR)
    lines = [json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n'
             for r in fresh]
    i = 0
    while i < len(lines):
        if not meta['parts']:
            meta['parts'].append({'file': 'decisions-v%d.jsonl' % v})
        cur = meta['parts'][-1]
        path = DIR + cur['file']
        size = os.path.getsize(path) if os.path.exists(path) else 0
        if size >= PART_LIMIT:
            meta['parts'].append({'file': 'decisions-v%d.part%d.jsonl'
                                          % (v, len(meta['parts']) + 1)})
            continue
        with io.open(path, 'a', encoding='utf-8', newline='') as f:
            while i < len(lines) and size < PART_LIMIT:
                f.write(lines[i])
                size += len(lines[i].encode('utf-8'))
                i += 1
    for p in meta['parts']:
        path = DIR + p['file']
        p['bytes'] = os.path.getsize(path)
        p['sha256'] = sha256_of(path)
        with open(path, 'rb') as f:
            p['rows'] = sum(1 for _ in f)
    meta['readers'] = sorted(set(meta['readers']) | readers)
    meta['commits'] = sorted(set(meta['commits'])
                             | set(r.get('commit') or (r.get('git') or {})
                                   .get('commit') for r in fresh))
    meta['rows'] = sum(p['rows'] for p in meta['parts'])
    _save_index(ix)
    return len(fresh)


def provenance_problem(r):
    """Why a v4+ row's provenance is not acceptable, or None."""
    import re
    if 'observed' in r or 'commit' in r or 'tree_clean' in r:
        return 'carries a v1-v3 provenance field (observed/commit)'
    rd, g = r.get('read') or {}, r.get('git') or {}
    if not rd.get('path'):
        return 'no read.path'
    if not re.match(r'^[0-9a-f]{64}$', str(rd.get('sha256'))):
        return 'read.sha256 is not a SHA-256'
    if not re.match(r'^[0-9a-f]{40}$', str(g.get('commit'))):
        return 'git.commit is not a full sha'
    if not isinstance(g.get('dirty'), bool):
        return 'git.dirty missing'
    if g['dirty'] and not re.match(r'^[0-9a-f]{64}$',
                                   str(g.get('status_hash'))):
        return 'a dirty run without git.status_hash'
    if not g['dirty'] and g.get('status_hash') is not None:
        return 'a clean run with a status_hash'
    if not r.get('reader'):
        return 'no reader fingerprint'
    return None


# The codes tools/provenance.py gives a failure. Kept here as well so the
# store can refuse one without importing the runner's module.
FAILURE_CODES = ('ARTIFACT_NOT_FOUND', 'ARTIFACT_AMBIGUOUS',
                 'ARTIFACT_UNREADABLE', 'ARTIFACT_CHANGED_DURING_READ',
                 'ARTIFACT_OUTSIDE_SOURCES', 'ARTIFACT_NAME_MISMATCH')


def failures_path(v):
    return DIR + 'provenance-failures-v%d.jsonl' % int(v)


def append_failures(rows, v):
    """Record provenance failures of version v, beside its decisions.

    Not decisions: no `decision` field, a FAILURE_CODES code, and a file
    of their own that iter_rows() never reads. A failure that recurs on
    a rerun is not written twice."""
    v = int(v)
    for r in rows:
        if r.get('kind') != 'provenance_failure' \
                or r.get('code') not in FAILURE_CODES \
                or 'decision' in r or r.get('v') != v:
            raise RefusedAppend('not a provenance failure of v%d: %s'
                                % (v, r.get('artifact')))
    have = set()
    for d in iter_failures(v):
        have.add(_failure_key(d))
    fresh = []
    for r in rows:
        k = _failure_key(r)
        if k not in have:
            have.add(k)
            fresh.append(r)
    if not fresh:
        return 0
    if not os.path.isdir(DIR):
        os.makedirs(DIR)
    path = failures_path(v)
    with io.open(path, 'a', encoding='utf-8', newline='') as f:
        for r in fresh:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n')
    ix = _load_index()
    meta = ix['versions'].setdefault(str(v), {'parts': [], 'readers': [],
                                              'commits': []})
    with open(path, 'rb') as f:
        n = sum(1 for _ in f)
    meta['failures'] = {'file': os.path.basename(path), 'rows': n,
                        'bytes': os.path.getsize(path),
                        'sha256': sha256_of(path)}
    _save_index(ix)
    return len(fresh)


def _failure_key(d):
    c = d.get('ctx') or {}
    return (d.get('artifact'), c.get('folder'), d.get('code'),
            json.dumps(c, sort_keys=True, ensure_ascii=False))


def iter_failures(v):
    p = failures_path(v)
    if not os.path.exists(p):
        return
    with io.open(p, encoding='utf-8') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def verify():
    """Every part's bytes and row count against the index. [] when sound."""
    bad = []
    ix = _load_index()
    for v, meta in sorted(ix.get('versions', {}).items(), key=lambda x: int(x[0])):
        fl = meta.get('failures')
        if fl:
            fp = DIR + fl['file']
            if not os.path.exists(fp) or sha256_of(fp) != fl.get('sha256'):
                bad.append('%s does not match its hash' % fl['file'])
        for p in meta.get('parts', []):
            path = DIR + p['file']
            if not os.path.exists(path):
                bad.append('%s is missing' % p['file'])
                continue
            if sha256_of(path) != p.get('sha256'):
                bad.append('%s does not match its hash' % p['file'])
            with open(path, 'rb') as f:
                raw = f.read()
            if b'\r' in raw:
                bad.append('%s has CR line endings' % p['file'])
            if raw.count(b'\n') != p.get('rows'):
                bad.append('%s holds %d rows, the index says %s'
                           % (p['file'], raw.count(b'\n'), p.get('rows')))
    return bad


def main():
    ix = _load_index()
    for v in versions():
        meta = ix['versions'][str(v)]
        print('v%-3d %8d rows  %s  reader %s'
              % (v, meta.get('rows', 0),
                 ', '.join('%s (%.1f MB)' % (p['file'], p['bytes'] / 1e6)
                           for p in meta['parts']),
                 ', '.join(meta.get('readers', []))))
    if '--verify' in sys.argv:
        bad = verify()
        print('\n' + ('verified: every part matches the index' if not bad
                      else '\n'.join(bad)))
        sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
