# -*- coding: utf-8 -*-
"""Check every record against the wine its sheet is actually for.

    python tools/audit-sources.py


This is the audit the manifest exists to make possible. For each record
in fiches.js, which holds grand vins and nothing else, ask data/
sources.json what the sheet named in src belongs to, and complain when
the answer is not this estate's grand vin.

Three kinds of complaint:
  wrong wine    the sheet is this estate's second wine or another cuvee
  wrong estate  the sheet belongs to a different estate entirely
  unknown       the sheet is not on disk, so nothing can be checked

A season note is exempt from the first: one weather falls on one
vineyard, so an estate's cuvees share a season and a note that crossed
from one to another is still true. Everything else is one wine's.
"""
import io, json, re, sys, collections

import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep

man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))
sheets = {}
for s in man['sheets']:
    sheets.setdefault(s['file'], s)
print('%d sheets in the manifest' % len(sheets))

OWNED = ('blend', 'harvest', 'yld', 'alc', 'ph', 'months', 'oak', 'temp',
         'food', 'press', 'taste', 'decant', 'window', 'wy')
GRANDISH = ('grand', 'skip', 'page', 'combined')

txt = io.open(ROOT + 'data/fiches.js', encoding='utf-8').read()
bad = collections.defaultdict(list)
checked = 0
for m in re.finditer(r"^'([a-z0-9-]+)\|(\d{4})':\{(.*)\},$", txt, re.M):
    eid, yr, body = m.group(1), m.group(2), m.group(3)
    sm = re.search(r"src:'([^']*)'", body)
    if not sm:
        continue
    checked += 1
    s = sheets.get(sm.group(1))
    has = [f for f in OWNED if re.search(r'(?:^|,)' + f + r"[:']", body)]
    if not s:
        bad['the sheet is not on disk'].append((eid, yr, sm.group(1), has))
        continue
    if s['estate'] and s['estate'] != eid:
        bad['the sheet belongs to another estate'].append(
            (eid, yr, '%s -> %s' % (sm.group(1)[:40], s['estate']), has))
    elif s['role'] not in GRANDISH and has:
        bad["the sheet is this estate's %s" % s['role']].append(
            (eid, yr, '%s (%s)' % (sm.group(1)[:40], s.get('wine') or '?'), has))

print('%d records name a sheet\n' % checked)
tot = 0
for why in sorted(bad):
    rows = bad[why]
    tot += len(rows)
    print('%-42s %d' % (why, len(rows)))
print('%-42s %d' % ('-- total needing attention', tot))

o = io.open(os.path.join(ROOT, 'reports', 'audit-sources.txt'), 'w', encoding='utf-8', newline='')
for why in sorted(bad):
    o.write('\n===== %s: %d\n' % (why, len(bad[why])))
    for eid, yr, what, has in sorted(bad[why]):
        o.write('  %-24s %s  %-52s fields=%s\n'
                % (eid, yr, what, ','.join(has) or '-'))
o.close()
print('\ndetail in reports/audit-sources.txt')
