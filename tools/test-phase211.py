# -*- coding: utf-8 -*-
"""Phase 2.11: the Terrasses de Saint-Christophe audit, made repeatable.

    python tools/test-phase211.py

Read-only. Identifies the 15 v5 acceptances the audit is about, checks
the document evidence the audit's conclusion rests on (where sources/ is
present), and that nothing canonical or historical moved.
"""
import collections
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr
import evidence as EV
import evidence_store as ST
import historical_m2_scope as H  # noqa: E402

fails = []
checks = 0


def says(name, ok, shown=''):
    global checks
    checks += 1
    if not ok:
        fails.append(name)
    print('%-4s %-62s %s' % ('ok' if ok else 'FAIL', name[:62], shown))


TSC = 'stem-chateau-tour-saint-christophe'


def is_terrasses(fn):
    n = fn.upper()
    return 'TERRASSES' in n and 'CHRISTOPHE' in n


acc = sorted((d for d in ST.iter_rows([5])
              if is_terrasses(d['artifact'])
              and d['ctx'].get('target_estate') == TSC
              and d['ctx'].get('target_role') == 'grand'
              and d['code'] == 'ACCEPTED'), key=lambda d: d['artifact'])
says('the audit\'s 15: v5 grand-vin acceptances of Terrasses sheets at '
     'Tour Saint-Christophe', len(acc) == 15, '%d' % len(acc))
says('...all unattributed in the manifest (folder hypothesis)',
     all(d['ctx'].get('estate') is None for d in acc))
says('...all read from Tour Saint-Christophe\'s own folder',
     all(d['read']['path'].startswith('fiches/%s/' % TSC) for d in acc))
says('...4 PRODUCT-SHEET and 11 FICHE-TECHNIQUE / TECHNICAL-SHEET',
     collections.Counter(d['artifact'].split('-')[0] for d in acc)
     == {'PRODUCT': 4, 'FICHE': 7, 'TECHNICAL': 4})

E = sr.estates(ROOT)
says('canonical data lists no second wine and no cuvee for Tour '
     'Saint-Christophe', E[TSC]['second'] is None and not E[TSC]['cuvees'])

if os.path.isdir(ROOT + 'sources/fiches/' + TSC):
    label = []
    letterhead_only = []
    for d in acc:
        p = os.path.join(ROOT, 'sources', *d['read']['path'].split('/'))
        t = sr.norm(' '.join(sr.flat(p).split()))
        if 'second label of chateau tour saint christophe' in t:
            label.append(d['artifact'])
        if d['artifact'].startswith(('FICHE', 'TECHNICAL')) and \
                len(re.findall(r' tour saint christophe ', t)) == 1 and \
                ' vignobles k ' in t:
            letterhead_only.append(d['artifact'])
    says('the 4 PRODUCT-SHEETs state "second label of Chateau Tour Saint '
         'Christophe"', len(label) == 4
         and all(a.startswith('PRODUCT') for a in label), '%d' % len(label))
    says('the 11 others name Tour Saint-Christophe once - in the group '
         'letterhead - and present a Vignobles K cuvee',
         len(letterhead_only) == 11, '%d' % len(letterhead_only))
    sr._TEXT.clear()
    e = E[TSC]
    p = os.path.join(ROOT, 'sources', *acc[0]['read']['path'].split('/'))
    v = sr.whose_sheet(p, acc[0]['artifact'], e['name'],
                       ['Les Terrasses de Saint Christophe'],
                       'Les Terrasses de Saint Christophe', e['cat'],
                       year=acc[0]['ctx'].get('target_vintage'))
    says('were the second wine listed, the unchanged reader would refuse '
         'the sheet as the grand vin', v is not None,
         (v or {}).get('why', 'accepted')[:30])
else:
    print('MISSING  sources/ (document checks)')

says('the evidence store still holds 177,127 decisions',
     H.evidence_rows_before_m36b() == 177127)
says('the reader is still 7e8cfed1c24e',
     EV.reader_fingerprint() == '7e8cfed1c24e')
committed = subprocess.check_output(['git', 'ls-files', 'data/evidence/'],
                                    cwd=ROOT).decode().split()
out = subprocess.check_output(
    ['git', 'diff', '--name-only', 'HEAD', '--', 'data/fiches.js',
     'data/chateaux.js', 'data/cuvees.js', 'data/sources.json',
     'data/field-src.js', 'data/cuvee-src.js'] + committed,
    cwd=ROOT).decode().strip()
says('canonical files and every committed evidence file match HEAD',
     out == '', 'clean' if not out else out[:30])
print('\n%d check(s), %s'
      % (checks, 'all pass' if not fails
         else '%d FAILED: %s' % (len(fails), '; '.join(fails[:4]))))
sys.exit(1 if fails else 0)
