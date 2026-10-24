# -*- coding: utf-8 -*-
"""Where the evidence contradicts itself: one document accepted as more
than one thing. Both sides kept, nothing resolved.

    python tools/conflicts-v4.py
    python tools/conflicts-v4.py --write   data/v4-identity-conflicts.jsonl

Reads the evidence store only.

Why this and not data/field-conflicts.jsonl: the field-conflict model in
conflicts.py is fed by read-fiches.py, and read-fiches.py calls
conflicts.note() only after its dry run has returned - so it records a
conflict only under --apply, which writes data/fiches.js. Its own
comment says otherwise. Phase 2.7 may not write canonical data, so the
field model could not be run; this measures the conflicts the evidence
itself can show.

A conflict is one document (folder + file) ACCEPTED for more than one
target, by relation:

  GRAND_AND_SECOND   accepted as the grand vin and as the second wine
                     of the same vintage
  SEVERAL_VINTAGES   accepted for more than one vintage of one wine
  SEVERAL_ESTATES    accepted for more than one estate

Each is kept with every accepted target listed - no first-writer-wins.
The same measure on v3, and the Phase 2.5 audit of which documents v3
read from another folder, say which v4 conflicts are new and whether a
new one is due to the corrected provenance alone.
"""
import argparse
import collections
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evidence_store as ST

OUT = ROOT + 'data/v4-identity-conflicts.jsonl'


def conflicts(v):
    acc = collections.defaultdict(set)
    for d in ST.iter_rows([v]):
        if d.get('code') != 'ACCEPTED':
            continue
        c = d.get('ctx') or {}
        acc[(c.get('folder'), d['artifact'])].add(
            (c.get('estate') or c.get('target_estate'),
             c.get('target_role'), c.get('target_wine'),
             c.get('target_vintage')))
    out = {}
    for doc, ts in acc.items():
        rel = []
        by_v = collections.defaultdict(set)
        for est, role, wine, yr in ts:
            by_v[(est, yr)].add(role)
        if any({'grand', 'second'} <= r for r in by_v.values()):
            rel.append('GRAND_AND_SECOND')
        by_w = collections.defaultdict(set)
        for est, role, wine, yr in ts:
            if yr:
                by_w[(est, wine)].add(yr)
        if any(len(y) > 1 for y in by_w.values()):
            rel.append('SEVERAL_VINTAGES')
        if len(set(t[0] for t in ts)) > 1:
            rel.append('SEVERAL_ESTATES')
        if rel:
            out[doc] = (rel, sorted(ts, key=lambda t: tuple(
                str(x) for x in t)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    c4, c3 = conflicts(4), conflicts(3)
    audit = set()
    p = ROOT + 'data/provenance-audit.jsonl'
    if os.path.exists(p):
        with io.open(p, encoding='utf-8') as f:
            f.readline()
            for line in f:
                r = json.loads(line)
                if r['class'].startswith('old read another'):
                    audit.add((r['folder'], r['artifact']))

    print('documents accepted for more than one target: v3 %d, v4 %d'
          % (len(c3), len(c4)))
    rel = collections.Counter(r for rs, _ in c4.values() for r in rs)
    print('\nv4 BY RELATION')
    for k, n in rel.most_common():
        print('   %-18s %5d  (v3 %d)' % (k, n, sum(
            1 for rs, _ in c3.values() if k in rs)))
    est = collections.Counter(t[0] for _, ts in c4.values()
                              for t in set((x[0],) for x in ts))
    print('\nv4 BY ESTATE (top 12)')
    for k, n in est.most_common(12):
        print('   %-34s %4d' % (k, n))
    wine = collections.Counter(x[2] for _, ts in c4.values()
                               for x in set((t[0], t[1], t[2]) for t in ts))
    print('\nv4 BY WINE (top 10)')
    for k, n in wine.most_common(10):
        print('   %-40s %4d' % (str(k)[:40], n))
    vint = collections.Counter(t[3] for _, ts in c4.values() for t in ts
                               if t[3])
    dec = collections.Counter('%ds' % (y // 10 * 10) for y in vint
                              for _ in range(vint[y]))
    print('\nv4 BY DECADE OF THE VINTAGES INVOLVED')
    for k, n in sorted(dec.items()):
        print('   %-8s %5d' % (k, n))

    new = set(c4) - set(c3)
    gone = set(c3) - set(c4)
    newp = [d for d in new if d in audit]
    print('\nNEW IN v4: %d documents (%d of them on a document v3 read '
          'from another folder)' % (len(new), len(newp)))
    print('GONE IN v4: %d documents' % len(gone))
    changed = [d for d in set(c4) & set(c3) if c4[d][0] != c3[d][0]]
    print('relation changed v3 -> v4: %d' % len(changed))
    for d in sorted(new)[:15]:
        print('   new  %-30s %-46s %s' % (d[0][:30], d[1][:46], c4[d][0]))
    for d in sorted(gone)[:15]:
        print('   gone %-30s %-46s %s' % (d[0][:30], d[1][:46], c3[d][0]))

    if a.write:
        with io.open(OUT, 'w', encoding='utf-8', newline='') as f:
            f.write(json.dumps({
                '_': 'Documents the v4 evidence accepts for more than one '
                     'target, every target kept. Not resolved, not '
                     'canonical. tools/conflicts-v4.py.',
                'v4': len(c4), 'v3': len(c3), 'relations': dict(rel),
                'new_in_v4': len(new), 'gone_in_v4': len(gone),
                'new_on_wrong_folder_documents': len(newp)},
                ensure_ascii=False, sort_keys=True) + '\n')
            for d in sorted(c4):
                rs, ts = c4[d]
                f.write(json.dumps({
                    'folder': d[0], 'artifact': d[1], 'relations': rs,
                    'accepted_for': [{'estate': t[0], 'role': t[1],
                                      'wine': t[2], 'vintage': t[3]}
                                     for t in ts],
                    'new_in_v4': d in new,
                    'v3_read_another_folder': d in audit},
                    ensure_ascii=False, sort_keys=True) + '\n')
        print('\nwritten to data/v4-identity-conflicts.jsonl (%d)' % len(c4))


if __name__ == '__main__':
    main()
