"""Phase 5 C3: hard-link byte-identical files in the raw store (sources/).

    python tools/link-duplicates.py            measure only: what could be linked
    python tools/link-duplicates.py --apply    link, journal every change
    python tools/link-duplicates.py --revert   undo every journalled link

The raw store is gitignored and local. Every path keeps existing and keeps
returning exactly the same bytes; only the number of physical copies
changes. Two kinds of duplicate are linked:

  - one legacy file at several paths (sources/fiches|pages), and
  - a legacy file whose bytes are also a raw (not gzipped) blob in the
    content-addressed discovery store; the blob is kept as the file.

Identity is established here, by hashing every candidate (sha256), never
taken from the manifest. A file already linked to its keeper is skipped.
Each link is made under a temporary name next to the target and moved
over it with os.replace, then checked to be the keeper's file. The journal
(sources/.link-journal.jsonl, local) lists every path changed;
--revert gives each path its own copy again.

Writers into sources/ remove a file before writing it (add-sheet.py,
harvest.py, crawl-pages.py) or replace it (discover.py), so a write to one
name can never change a linked twin.
"""
import collections
import hashlib
import json
import os
import shutil
import sys
import time

import migration_lib as L
import mig_m2_identity as M2
import raw_store

SRC = L.ROOT + 'sources/'
JOURNAL = SRC + '.link-journal.jsonl'


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def same_file(a, b):
    sa, sb = os.stat(a), os.stat(b)
    return sa.st_ino == sb.st_ino and sa.st_dev == sb.st_dev and sa.st_ino != 0


def candidates():
    """{sha256: [paths]}: every legacy file that may share its bytes, with the
    raw blob of the same bytes first where one exists."""
    sheets = L.sources_rows()['sheets']
    by_sha1 = collections.defaultdict(set)
    for r in sheets:
        p = SRC + M2.sources_path(r)
        if os.path.isfile(p):
            by_sha1[r['sha1']].add(p)
    joined = {a['sha1']: a['sha256'] for a in L.jsonl_lines(L.MODEL + 'identity/artifacts.jsonl')
              if 'sha1' in a and 'sha256' in a}
    paths = set()
    for s1, ps in by_sha1.items():
        if len(ps) > 1 or (s1 in joined and raw_store.blob_path(joined[s1])):
            paths |= ps
    groups = collections.defaultdict(list)
    t = time.perf_counter()
    for p in sorted(paths):
        groups[sha256(p)].append(p)
    hash_s = time.perf_counter() - t
    out = {}
    gz_only = 0
    for h, ps in groups.items():
        blob = '%sdiscovery/blobs/%s/%s' % (SRC, h[:2], h)
        if os.path.isfile(blob):
            ps = [blob] + ps
        elif os.path.isfile(blob + '.gz'):
            gz_only += sum(os.path.getsize(p) for p in ps)
        if len(ps) > 1:
            out[h] = ps
    return out, hash_s, len(paths), gz_only


def plan():
    groups, hash_s, hashed, gz_only = candidates()
    links, saved, already = [], 0, 0
    for h, ps in sorted(groups.items()):
        keeper = ps[0]
        for p in ps[1:]:
            if same_file(keeper, p):
                already += 1
                continue
            links.append((h, keeper, p))
            saved += os.path.getsize(p)
    return {'groups': len(groups), 'files_hashed': hashed, 'hash_seconds': round(hash_s, 1),
            'links': len(links), 'bytes_freed': saved, 'already_linked': already,
            'not_linkable_gzipped_blob_bytes': gz_only}, links


def apply(links):
    free0 = shutil.disk_usage(SRC).free
    done = 0
    with open(JOURNAL, 'a', encoding='utf-8', newline='\n') as j:
        for h, keeper, p in links:
            if sha256(keeper) != h:
                raise SystemExit('keeper changed: %s' % keeper)
            tmp = p + '.link-tmp'
            if os.path.exists(tmp):
                os.remove(tmp)
            os.link(keeper, tmp)
            os.replace(tmp, p)
            if not same_file(keeper, p):
                raise SystemExit('not linked: %s' % p)
            j.write(json.dumps({'path': L.rel(p), 'keeper': L.rel(keeper), 'sha256': h,
                                'at': time.strftime('%Y-%m-%dT%H:%M:%S')}) + '\n')
            done += 1
    return done, free0, shutil.disk_usage(SRC).free


def revert():
    if not os.path.exists(JOURNAL):
        return 0
    n = 0
    for e in reversed(L.jsonl_lines(JOURNAL)):
        p, keeper = L.ROOT + e['path'], L.ROOT + e['keeper']
        if os.path.exists(p) and same_file(p, keeper):
            tmp = p + '.unlink-tmp'
            shutil.copyfile(keeper, tmp)
            os.replace(tmp, p)
            n += 1
    os.replace(JOURNAL, JOURNAL + '.reverted-%s' % time.strftime('%Y%m%d%H%M%S'))
    return n


def main():
    if '--revert' in sys.argv:
        L.out('separated %d linked path(s)' % revert())
        return
    summary, links = plan()
    L.out(json.dumps(summary))
    if '--apply' in sys.argv:
        done, f0, f1 = apply(links)
        L.out('linked %d path(s); free disk %d MB -> %d MB' % (done, f0 // 2**20, f1 // 2**20))


if __name__ == '__main__':
    main()
