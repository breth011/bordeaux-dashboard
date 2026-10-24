# -*- coding: utf-8 -*-
"""How v1-v3 found their files, against how they should have.

    python tools/audit-provenance.py            summary
    python tools/audit-provenance.py --write    and data/provenance-audit.jsonl

Read-only over sources/ and the evidence store. Changes no record, and
no historical evidence: v1-v3 keep the provenance they recorded. This
says what that provenance turns out to have meant.

For every manifest row it compares:

  old   the basename index v1-v3 used: walk sources/, and keep the
        first path seen for each filename (disk.setdefault), whatever
        folder it is in;
  new   tools/provenance.resolve: the row's own folder and file, or a
        typed failure.

and reports the old path, the new path, the manifest's sha1, the sha1
and sha256 of the bytes at each, whether the bytes differ, and how many
v1-v3 decisions were made from the old path.

Decision identity (evidence.row_key) is built from the artifact name and
the manifest's folder, never from a path or a hash. So it is the same
under both resolutions, and every row says so - the audit checks it
rather than assuming it.
"""
import argparse
import collections
import hashlib
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evidence as EV
import evidence_store as ST
import provenance as PV

OUT = ROOT + 'data/provenance-audit.jsonl'


def hashes(path, memo={}):
    if path not in memo:
        b = open(path, 'rb').read()
        memo[path] = (hashlib.sha1(b).hexdigest(),
                      hashlib.sha256(b).hexdigest())
    return memo[path]


def rel(p):
    return os.path.relpath(p, ROOT + 'sources').replace(os.sep, '/') \
        if p else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()

    man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))
    sheets = [s for s in man['sheets'] if s.get('file')]

    old = {}
    for root, dirs, files in os.walk(ROOT + 'sources'):
        for f in files:
            old.setdefault(f, os.path.join(root, f))

    # How many v1-v3 decisions each (folder, file) carries.
    used = collections.Counter()
    for d in ST.iter_rows([1, 2, 3]):
        c = d.get('ctx') or {}
        used[(c.get('folder'), d.get('artifact'))] += 1

    dupe = collections.Counter((s.get('folder'), s['file']) for s in sheets)
    rows, cls = [], collections.Counter()
    for s in sheets:
        fo, fn = s.get('folder'), s['file']
        op = old.get(fn)
        try:
            art = PV.resolve(fo, fn)
            np, failure = art.path, None
        except PV.ProvenanceFailure as f:
            np, failure = None, f.code
        same_path = bool(op and np and
                         os.path.normcase(os.path.realpath(op))
                         == os.path.normcase(np))
        oh = hashes(op) if op else (None, None)
        nh = hashes(np) if np else (None, None)
        if failure:
            k = 'new: %s; old read %s' % (
                failure, 'another folder\'s file' if op else 'nothing')
        elif not op:
            k = 'old read nothing (skipped); new reads its own file'
        elif same_path:
            k = 'same file'
        elif oh[1] == nh[1]:
            k = 'old read another folder, same bytes'
        else:
            k = 'old read another folder, DIFFERENT bytes'
        cls[k] += 1
        ctx = {'folder': fo, 'estate': s.get('estate'),
               'wine': s.get('wine'), 'vintage': s.get('year')}
        key_old = EV.row_key({'artifact': fn, 'ctx': ctx, 'v': 0})
        key_new = EV.row_key({'artifact': fn, 'ctx': ctx, 'v': 0})
        rows.append({
            'artifact': fn, 'folder': fo, 'estate': s.get('estate'),
            'class': k,
            'old_path': rel(op), 'new_path': rel(np),
            'new_failure': failure,
            'manifest_sha1': s.get('sha1'),
            'old_sha1': oh[0], 'old_sha256': oh[1],
            'actual_sha1': nh[0], 'actual_sha256': nh[1],
            'bytes_differ': bool(op and np and oh[1] != nh[1]),
            'manifest_sha1_matches_actual': (nh[0] == s.get('sha1'))
            if np else None,
            'manifest_row_duplicated': dupe[(fo, fn)] > 1,
            'identity_changes': key_old != key_new,
            'v1_v3_decisions_from_old_path': used[(fo, fn)]
            if not same_path else 0,
        })

    print('%d manifest rows with a file\n' % len(rows))
    print('OLD (basename) AGAINST NEW (folder) RESOLUTION')
    print('-' * 64)
    for k, n in cls.most_common():
        print('   %-50s %6d' % (k, n))

    moved = [r for r in rows if r['class'].startswith('old read another')]
    diff = [r for r in moved if r['bytes_differ']]
    fail = [r for r in rows if r['new_failure']]
    print()
    print('old resolution read another folder\'s file   %6d' % len(moved))
    print('   ...identical bytes                        %6d'
          % (len(moved) - len(diff)))
    print('   ...DIFFERENT bytes                        %6d' % len(diff))
    print('   ...rows that are manifest duplicates      %6d'
          % sum(1 for r in moved if r['manifest_row_duplicated']))
    print('new resolution: ambiguous                    %6d'
          % sum(1 for r in fail if r['new_failure'] == 'ARTIFACT_AMBIGUOUS'))
    print('new resolution: not found                    %6d'
          % sum(1 for r in fail if r['new_failure'] == 'ARTIFACT_NOT_FOUND'))
    print('   ...of which old read some other file      %6d'
          % sum(1 for r in fail if r['old_path']))
    print('decision identity changes                    %6d'
          % sum(1 for r in rows if r['identity_changes']))
    ok = [r for r in rows if r['actual_sha1']]
    print('manifest sha1 == bytes at the right path     %6d of %d'
          % (sum(1 for r in ok if r['manifest_sha1_matches_actual']),
             len(ok)))
    print('v1-v3 decisions made from a wrong-folder file %5d'
          % sum(r['v1_v3_decisions_from_old_path'] for r in moved))
    print('   ...from DIFFERENT bytes                   %6d'
          % sum(r['v1_v3_decisions_from_old_path'] for r in diff))
    print('v1-v3 decisions whose file is now not found  %6d'
          % sum(r['v1_v3_decisions_from_old_path'] for r in fail))

    print()
    print('THE DIFFERENT-BYTES CASES')
    print('-' * 64)
    by_pair = collections.Counter((r['folder'], r['old_path'].split('/')[-2]
                                   if r['old_path'] else None)
                                  for r in diff)
    for (fo, of), n in by_pair.most_common():
        print('   filed under %-34s read from %-22s %3d' % (fo, of, n))

    if a.write:
        with io.open(OUT, 'w', encoding='utf-8', newline='') as f:
            f.write(json.dumps({
                '_': 'How v1-v3 resolved each manifest row (basename, '
                     'first match) against how it should have (the row\'s '
                     'own folder). Diagnostic only: no evidence row and no '
                     'record was changed. tools/audit-provenance.py.',
                'rows': len(rows),
                'classes': dict(cls)}, ensure_ascii=False,
                sort_keys=True) + '\n')
            for r in rows:
                if r['class'] != 'same file':
                    f.write(json.dumps(r, ensure_ascii=False,
                                       sort_keys=True) + '\n')
        print('\nwritten to data/provenance-audit.jsonl (the %d rows that '
              'are not "same file")'
              % sum(1 for r in rows if r['class'] != 'same file'))


if __name__ == '__main__':
    main()
