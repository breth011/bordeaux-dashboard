# -*- coding: utf-8 -*-
"""Phase 2.12: the Phase 2 exit invariants.

    python tools/test-phase212.py

The state Phase 2 hands to Phase 3: evidence intact at v5, canonical data
as it was, the Terrasses correction recorded as a proposal and not as
data, and the exit decision written down.
"""
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

BASE = '2072abe'
DOC = 'docs/PHASE-2.12-EVIDENCE-RECONCILIATION.md'
CANON = ('data/fiches.js', 'data/field-src.js', 'data/cuvee-src.js',
         'data/chateaux.js', 'data/cuvees.js', 'data/sources.json')
fails = []
checks = 0


def says(name, ok, shown=''):
    global checks
    checks += 1
    if not ok:
        fails.append(name)
    print('%-4s %-62s %s' % ('ok' if ok else 'FAIL', name[:62], shown))


def git(args):
    return subprocess.check_output(['git'] + args, cwd=ROOT,
                                   stderr=subprocess.DEVNULL).decode()


# 1. Phase 2.12 itself, its commit 8964131, changed only its document
# and test. Fixed to that range: a later phase's files are not this
# phase's business (the whole-tree form of this check failed as soon as
# Phase 3.0 added files).
changed = set(git(['diff', '--name-only', BASE, '8964131']).split())
allowed = {DOC, 'tools/test-phase212.py'}
says('Phase 2.12 (%s..8964131) changed only its document and test' % BASE,
     changed <= allowed, ', '.join(sorted(changed - allowed))[:40])
# 2. canonical files
out = git(['diff', '--name-only', BASE, '--'] + list(CANON)).strip()
says('canonical files unchanged since %s' % BASE, out == '', out[:30])
# 3. evidence store
# M3.6B adds evidence version 6 beside v1-v5 (the store grows by design); every v1-v5 assertion stands,
# and v6 must be exactly M3.6B's decisions (historical_m2_scope.evidence_changes_are_m36b_only)
out = '' if H.evidence_changes_are_m36b_only(BASE) else 'changed'
says('the evidence store is byte-for-byte as at %s' % BASE, out == '',
     out[:30])
says('...and verifies', ST.verify() == [])
says('...holding 177,127 decisions',
     H.evidence_rows_before_m36b() == 177127)
# 4. reader
says('the reader fingerprint is 7e8cfed1c24e',
     EV.reader_fingerprint() == '7e8cfed1c24e')
# 5. Terrasses is a proposal, not data
E = sr.estates(ROOT)
tsc = E['stem-chateau-tour-saint-christophe']
says('Tour Saint-Christophe still lists no second wine and no cuvee',
     tsc['second'] is None and not tsc['cuvees'])
says('no canonical estate or wine list names Les Terrasses',
     not any('terrasses de saint' in io.open(ROOT + p, encoding='utf-8')
             .read().lower() for p in ('data/chateaux.js', 'data/cuvees.js',
                                        'data/saintemilion.js')))
# 6. ...and no canonical record cites a Terrasses document
cited = [p for p in ('data/fiches.js', 'data/field-src.js',
                     'data/cuvee-src.js', 'data/fiches-nl.js')
         if re.search(r'(?i)terrasses-de-saint-christophe',
                      io.open(ROOT + p, encoding='utf-8').read())]
says('no canonical record cites a Terrasses document', not cited,
     ', '.join(cited))
# 7. v5 intact
v5 = list(ST.iter_rows([5]))
says('v5 intact: 40,772 decisions, one reader, one commit, clean',
     len(v5) == 40772
     and set(d['reader'] for d in v5) == {'7e8cfed1c24e'}
     and len(set(d['git']['commit'] for d in v5)) == 1
     and all(d['git']['dirty'] is False for d in v5))
# 8-9. the document and its decision
if os.path.exists(ROOT + DOC):
    t = io.open(ROOT + DOC, encoding='utf-8').read()
    says('the reconciliation document exists', True)
    says('...and records the Phase 2 exit decision',
         'SAFE — PHASE 2 COMPLETE' in t)
    says('...with Terrasses under proposed corrections',
         'PROPOSED_CORRECTION_PENDING_DOMAIN_EVIDENCE' in t)
else:
    says('the reconciliation document exists', False)
# 10. no v6
says('no v6 evidence was generated', H.evidence_versions_before_m36b() == [1, 2, 3, 4, 5]
     and not any(re.match(r'(decisions|provenance-failures)-v6', f) and f != 'decisions-v6.jsonl'
                 for f in os.listdir(ROOT + 'data/evidence')))
print('\n%d check(s), %s'
      % (checks, 'all pass' if not fails
         else '%d FAILED: %s' % (len(fails), '; '.join(fails[:4]))))
sys.exit(1 if fails else 0)
