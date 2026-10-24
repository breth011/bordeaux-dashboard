# -*- coding: utf-8 -*-
"""Rewrite the census as one artifact per line, and trim it.

    python tools/census-compact.py

census.py --write emits a single 18 MB JSON array, which is the wrong
shape for this repository twice over: it cannot be diffed, so a change
in one artifact's classification shows as a rewrite of the whole file,
and 18 MB of it enters git history on every run.

data/artifact-census.jsonl is the same information as JSON Lines - one
artifact per line, sorted - which is how fiches.js and cuvees.js are
stored and for the same reason: a defect becomes a diff.

The header line carries the analyzer version, the date and the commit,
so a line's classification can always be attributed to the version
that made it.

Trimmed: the evidence strings are kept but capped, and fields that are
UNKNOWN or empty are dropped rather than stored as nulls.
"""
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
SRC = ROOT + 'data/artifact-census.json'
OUT = ROOT + 'data/artifact-census.jsonl'

d = json.load(io.open(SRC, encoding='utf-8'))
rows = d.pop('artifacts')

head = dict(d)
head['_'] = ('An analysis, not a source of truth. One artifact per '
             'line. Manifest identity, observed identity and the '
             'conclusion are separate on purpose and nothing here has '
             'been written back into sources.json or the records.')
head['rows'] = len(rows)

with io.open(OUT, 'w', encoding='utf-8', newline='') as f:
    f.write(json.dumps(head, ensure_ascii=False, sort_keys=True) + '\n')
    for r in sorted(rows, key=lambda x: (x['manifest'].get('estate') or '',
                                         x['path'])):
        o = {
            'id': r['artifact_id'],
            'path': r['path'],
            'm': dict((k, v) for k, v in r['manifest'].items() if v),
            'o': {
                'estate': r['observed']['estate'],
                'wine': r['observed']['wine'],
                'vintage': r['observed']['vintage'],
                'type': r['observed']['document_type'],
                'data': r['observed']['data_signals'],
            },
            'conf': dict((k[0] + k.split('_')[0][1:3], v) for k, v in (
                ('estate_confidence', r['identity']['estate_confidence']),
                ('wine_confidence', r['identity']['wine_confidence']),
                ('vintage_confidence',
                 r['identity']['vintage_confidence']))),
            'status': r['reconciliation']['status'],
            'why': [w[:120] for w in r['reconciliation']['reasons']][:3],
            'ev': [e[:100] for e in r['identity']['evidence']][:4],
            'v': r['analysis']['analyzer_version'],
        }
        if r['url']:
            o['url'] = r['url']
        if r['duplicate']['group_id']:
            o['dup'] = {'g': r['duplicate']['group_id'][:12],
                        'n': r['duplicate']['members']}
        if r['reconciliation']['candidate_records']:
            o['recs'] = r['reconciliation']['candidate_records'][:4]
        f.write(json.dumps(o, ensure_ascii=False, sort_keys=True) + '\n')

print('%d line(s) written to data/artifact-census.jsonl' % len(rows))
print('%.1f MB -> %.1f MB'
      % (os.path.getsize(SRC) / 1e6, os.path.getsize(OUT) / 1e6))
