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
# Keyed by estate and file, not by file alone. 888 filenames exist in
# more than one folder, because an owner publishes one document under
# each of its properties: Lafite, L'Evangile, Duhart-Milon and Rieussec
# all hold 2025__2025-the-lucky-hand.txt. Keyed by name, the first copy
# won and this audit accused all four records of reading Duhart-Milon's
# sheet.
sheets = {}
by_name = {}
for s in man['sheets']:
    sheets.setdefault((s.get('estate'), s['file']), s)
    by_name.setdefault(s['file'], s)
print('%d sheets in the manifest' % len(by_name))

OWNED = ('blend', 'harvest', 'yld', 'alc', 'ph', 'months', 'oak', 'temp',
         'food', 'press', 'taste', 'decant', 'window', 'wy')
GRANDISH = ('grand', 'skip', 'page', 'combined')

txt = io.open(ROOT + 'data/fiches.js', encoding='utf-8').read()
bad = collections.defaultdict(list)
checked = 0
pages = 0
for m in re.finditer(r"^'([a-z0-9-]+)\|(\d{4})':\{(.*)\},$", txt, re.M):
    eid, yr, body = m.group(1), m.group(2), m.group(3)
    sm = re.search(r"src:'([^']*)'", body)
    if not sm:
        continue
    checked += 1
    has = [f for f in OWNED if re.search(r'(?:^|,)' + f + r"[:']", body)]
    # src can name several sheets, comma-separated, where a record was
    # read from more than one - Giscours 2025 cites six. Testing the
    # joined string as a single filename reported four records as having
    # no sheet on disk when every sheet they named was there, and hid
    # whatever those sheets were for. A filename could itself contain a
    # comma, so an src that is a sheet in its own right is left whole.
    ref = sm.group(1)
    refs = ([ref] if ref in sheets
            else [r.strip() for r in ref.split(',') if r.strip()])
    for ref in refs:
        # A source can be a page rather than a file. Latour publishes no
        # technical sheets at all - its archive is seventy-five vintages
        # of prose on one page - so those records cite the page they came
        # from. That is a source, not a missing file.
        if '/' in ref and not ref.lower().endswith('.pdf'):
            pages += 1
            continue
        # This estate's copy if it has one, and only then anyone's.
        s = sheets.get((eid, ref)) or by_name.get(ref)
        if not s:
            bad['the sheet is not on disk'].append((eid, yr, ref, has))
            continue
        if s['estate'] and s['estate'] != eid:
            bad['the sheet belongs to another estate'].append(
                (eid, yr, '%s -> %s' % (ref[:40], s['estate']), has))
        elif s['role'] not in GRANDISH and has:
            bad["the sheet is this estate's %s" % s['role']].append(
                (eid, yr, '%s (%s)' % (ref[:40], s.get('wine') or '?'), has))

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
