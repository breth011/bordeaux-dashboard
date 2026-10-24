# -*- coding: utf-8 -*-
"""Move data/evidence-decisions.jsonl into data/evidence/, line for line.

    python tools/migrate-evidence-store.py --sample 400 --to DIR   prototype
    python tools/migrate-evidence-store.py --write                 the real one
    python tools/migrate-evidence-store.py --check                 re-prove it

The source is the file as git stores it at a commit (a36b35c by
default), not the working copy. The working copy is not the same
bytes: with core.autocrlf on, the 54,325 lines that were there at
checkout came back with CRLF, while the 41,259 v3 lines appended since
have LF. The committed blob is LF throughout. Its hash is the one
worth recording.

Nothing is parsed and re-serialised. Each line's bytes go to the file
for its version, so a row is the same row in the new store, byte for
byte. The proof:

  1. header + v1 + v2 + v3, concatenated, equals the source exactly -
     same bytes, same sha256. The source holds the versions as three
     contiguous blocks in that order, so this is also a proof of
     order;
  2. rows per version, and the sha1 of every line, unchanged;
  3. every decision identity (evidence.row_key), and how often it
     occurs, unchanged - including the 1,228 historical duplicates,
     which are kept.

--write refuses to run if any check fails or if data/evidence/
already holds a version.
"""
import argparse
import collections
import hashlib
import io
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evidence as EV

SRC = 'data/evidence-decisions.jsonl'


def source_bytes(commit):
    return subprocess.check_output(['git', 'show', '%s:%s' % (commit, SRC)],
                                   cwd=ROOT)


def split(raw):
    """(header lines, {version: [line bytes]}, order of versions seen)."""
    header, by, order = [], collections.OrderedDict(), []
    for line in raw.split(b'\n')[:-1] if raw.endswith(b'\n') \
            else raw.split(b'\n'):
        d = json.loads(line.decode('utf-8'))
        if '_' in d and 'decider_version' in d:
            header.append(line)
            continue
        v = d['v']
        by.setdefault(v, []).append(line)
        if not order or order[-1] != v:
            order.append(v)
    return header, by, order


def prove(raw, header, by, order, files):
    """files: {version: bytes as written}. Returns a list of failures."""
    bad = []
    if order != sorted(set(order)):
        bad.append('versions are not contiguous blocks in order: %s'
                   % order)
    joined = b''.join(h + b'\n' for h in header) + b''.join(
        files[v] for v in sorted(files))
    if joined != raw:
        bad.append('header + versions does not reproduce the source')
    if hashlib.sha256(joined).hexdigest() != \
            hashlib.sha256(raw).hexdigest():
        bad.append('sha256 differs')
    for v, lines in by.items():
        got = files[v].split(b'\n')[:-1]
        if len(got) != len(lines):
            bad.append('v%s: %d rows written, %d in the source'
                       % (v, len(got), len(lines)))
        if [hashlib.sha1(x).digest() for x in got] != \
                [hashlib.sha1(x).digest() for x in lines]:
            bad.append('v%s: a line changed or moved' % v)
        k_src = collections.Counter(EV.row_key(json.loads(x.decode('utf-8')))
                                    for x in lines)
        k_new = collections.Counter(EV.row_key(json.loads(x.decode('utf-8')))
                                    for x in got)
        if k_src != k_new:
            bad.append('v%s: decision identities differ' % v)
    return bad


def migrate(raw, to, commit, label):
    header, by, order = split(raw)
    files = dict((v, b''.join(x + b'\n' for x in lines))
                 for v, lines in by.items())
    bad = prove(raw, header, by, order, files)
    print('%s: %d bytes, %d header line(s), versions %s'
          % (label, len(raw), len(header), order))
    for v in sorted(by):
        print('   v%s  %7d rows  %11d bytes' % (v, len(by[v]),
                                               len(files[v])))
    if bad:
        print('NOT LOSSLESS:\n   ' + '\n   '.join(bad))
        return False
    print('   lossless: concatenation, line hashes and identities match')
    if not to:
        return True
    if not os.path.isdir(to):
        os.makedirs(to)
    if any(n.startswith('decisions-v') for n in os.listdir(to)):
        print('refused: %s already holds a version' % to)
        return False
    ix = {'_': 'The evidence decisions, one file per decider version. '
               'Append-only: tools/evidence_store.py is the only writer. '
               'An analysis, not a source of truth.',
          'migrated_from': {
              'path': SRC, 'commit': commit,
              'bytes': len(raw),
              'sha256': hashlib.sha256(raw).hexdigest(),
              'lines': raw.count(b'\n'),
              'header': [h.decode('utf-8') for h in header],
              'how': 'tools/migrate-evidence-store.py: lines moved '
                     'verbatim; header + v1 + v2 + v3 reproduces the '
                     'source byte for byte'},
          'versions': {}}
    for v in sorted(by):
        name = 'decisions-v%d.jsonl' % v
        with open(os.path.join(to, name), 'wb') as f:
            f.write(files[v])
        rows = [json.loads(x.decode('utf-8')) for x in by[v]]
        ix['versions'][str(v)] = {
            'parts': [{'file': name, 'rows': len(by[v]),
                       'bytes': len(files[v]),
                       'sha256': hashlib.sha256(files[v]).hexdigest()}],
            'rows': len(by[v]),
            'readers': sorted(set(r.get('reader') for r in rows)),
            'commits': sorted(set(r.get('commit') for r in rows)),
        }
    with io.open(os.path.join(to, 'index.json'), 'w', encoding='utf-8',
                 newline='') as f:
        f.write(json.dumps(ix, ensure_ascii=False, indent=1,
                           sort_keys=True) + '\n')
    print('   written to %s' % to)
    return True


def sample(raw, n):
    """The first n lines of each version, every duplicated identity, the
    header - a small file with each awkward case in it, still in
    version order."""
    header, by, _ = split(raw)
    out = list(header)
    for v in sorted(by):
        lines = by[v]
        keys = collections.Counter(EV.row_key(json.loads(x.decode('utf-8')))
                                   for x in lines)
        dup = [x for x in lines
               if keys[EV.row_key(json.loads(x.decode('utf-8')))] > 1][:n]
        take = lines[:n]
        seen = set(take)
        out += take + [x for x in dup if x not in seen]
    return b''.join(x + b'\n' for x in out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--commit', default='a36b35c')
    ap.add_argument('--sample', type=int, default=0)
    ap.add_argument('--to')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    raw = source_bytes(a.commit)

    if a.sample:
        s = sample(raw, a.sample)
        ok = migrate(s, a.to, a.commit, 'sample')
        if ok and a.to:
            # Read it back through the store's own code, pointed at the
            # prototype directory.
            import evidence_store as ST
            ST.DIR = os.path.join(a.to, '')
            ST.INDEX = ST.DIR + 'index.json'
            back = b''.join(
                json.dumps(d, ensure_ascii=False, sort_keys=True)
                .encode('utf-8') + b'\n' for d in ST.iter_rows())
            body = b''.join(x + b'\n' for x in s.split(b'\n')[1:-1])
            print('   read back through evidence_store: %s'
                  % ('identical' if back == body else 'DIFFERENT'))
            print('   verify(): %s' % (ST.verify() or 'sound'))
            ok = ok and back == body and not ST.verify()
        sys.exit(0 if ok else 1)

    if a.check:
        import evidence_store as ST
        ix = json.load(io.open(ST.INDEX, encoding='utf-8'))
        mf = ix['migrated_from']
        raw = source_bytes(mf['commit'])
        header = b''.join(h.encode('utf-8') + b'\n' for h in mf['header'])
        body = b''
        for v in ('1', '2', '3'):
            for p in ST.parts(int(v)):
                body += open(p, 'rb').read()
        ok = (header + body == raw
              and hashlib.sha256(header + body).hexdigest() == mf['sha256'])
        print('header + v1 + v2 + v3 against %s:%s - %s'
              % (mf['commit'], SRC, 'identical' if ok else 'DIFFERENT'))
        bad = ST.verify()
        print('parts against index: %s' % (bad or 'sound'))
        sys.exit(0 if ok and not bad else 1)

    ok = migrate(raw, ROOT + 'data/evidence' if a.write else None,
                 a.commit, '%s:%s' % (a.commit, SRC))
    if not a.write:
        print('\nnothing written; pass --write')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
