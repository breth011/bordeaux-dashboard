# -*- coding: utf-8 -*-
"""Phase 2.8: the grand-vin audit measures what it says, the same way
twice, and touches nothing.

    python tools/test-phase28.py

Tests the AUDIT (tools/audit-grand-marks.py), not a reader change: the
reader is unchanged in Phase 2.8.
"""
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr

spec = importlib.util.spec_from_file_location(
    'audit_grand', ROOT + 'tools/audit-grand-marks.py')
AG = importlib.util.module_from_spec(spec)
spec.loader.exec_module(AG)

fails = []
checks = 0


def says(name, ok, shown=''):
    global checks
    checks += 1
    if not ok:
        fails.append(name)
    print('%-4s %-60s %s' % ('ok' if ok else 'FAIL', name[:60], shown))


WATCH = ['data/sources.json', 'data/fiches.js', 'data/cuvees.js',
         'data/field-src.js', 'data/cuvee-src.js', 'data/chateaux.js']
WATCH += ['data/evidence/' + f for f in sorted(os.listdir(
    ROOT + 'data/evidence'))]


def digest():
    out = {}
    for p in WATCH:
        with open(ROOT + p, 'rb') as f:
            out[p] = hashlib.sha256(f.read()).hexdigest()
    return out


before = digest()
E1, rows1, al1 = AG.audit()
E2, rows2, al2 = AG.audit()
after = digest()

others = 0
for e in E1.values():
    if not e.get('name'):
        continue
    ws = list(dict.fromkeys([w for w in (e.get('cuvees') or ()) if w]
                            + ([e['second']] if e.get('second') else [])))
    others += len([w for w in ws if w != e['name']])
says('every estate of the reader\'s universe is audited',
     len(E1) == len(sr.estates(ROOT)), '%d estates' % len(E1))
cls = AG.collections_of()
unk = [e for e in E1 if AG.collection(e, cls) == 'unknown']
says('every estate is placed in a collection', not unk,
     '%d unknown' % len(unk))
says('every listed wine other than the grand vin is considered',
     len(rows1) == others, '%d wines' % len(rows1))
says('the audit is deterministic: two runs, identical rows',
     json.dumps(rows1, sort_keys=True) == json.dumps(rows2, sort_keys=True)
     and al1 == al2)
says('every row has one of the categories A B C D1 D2 F',
     all(r['category'] in ('A', 'B', 'C', 'D1', 'D2', 'F') for r in rows1))
mis = [r['wine'] for r in rows1
       if AG.explain_mark(r['wine'], r['grand'])[1]
       != sr.mark_of(r['wine'], r['grand'])]
says('the step-by-step explanation agrees with mark_of() for every wine',
     not mis, ', '.join(mis)[:40])

dt = [r for r in rows1 if r['estate'] == 'du-tertre'
      and r['wine'] == 'Les Hauts du Tertre']
says('Les Hauts du Tertre is audited', len(dt) == 1)
if dt:
    r = dt[0]
    says('...its mark is "les du tertre"',
         r['identity']['mark'] == 'les du tertre',
         repr(r['identity']['mark']))
    says('..."hauts" is the token lost, to COMMON',
         r['identity']['own'] == ['hauts']
         and r['identity']['own_common'] == ['hauts'])
    says('...it is a common-word-loss collision the name check misses (D1)',
         r['category'] == 'D1')
    steps, mk = AG.explain_mark('Les Hauts du Tertre', 'Château du Tertre')
    says('...and the trace shows where "hauts" goes',
         any(w == 'Hauts' and 'COMMON' in res for _, w, res in steps)
         and mk == 'les du tertre')

# A real-world shape the audit must keep finding, not one it was tuned to:
# the other known members of the class.
cats = dict(((r['estate'], r['wine']), r['category']) for r in rows1)
says('Les Tours de Belcier is D1 too',
     cats.get(('stem-chateau-bellefont-belcier', 'Les Tours de Belcier'))
     == 'D1')
says('a Blanc that a colour word still catches is D2, not D1',
     cats.get(('lynch-bages', 'Blanc de Lynch-Bages')) == 'D2')
says('a wine with a distinctive word is A (Echo de Lynch-Bages)',
     cats.get(('lynch-bages', 'Echo de Lynch-Bages')) == 'A')

says('running the audit changed no canonical file and no evidence file',
     before == after)
try:
    out = subprocess.check_output(
        ['git', 'diff', '--name-only', 'HEAD', '--'] + WATCH, cwd=ROOT,
        stderr=subprocess.DEVNULL).decode().strip()
except Exception:
    out = None
if out is None:
    print('MISSING  git unavailable')
else:
    says('canonical files, chateaux.js and the evidence store match HEAD',
         out == '', 'clean' if not out else out.replace('\n', ' ')[:30])

# The committed inventory is what the tool writes now.
p = ROOT + 'data/phase28-grand-audit.jsonl'
if os.path.exists(p):
    with io.open(p, encoding='utf-8') as f:
        f.readline()
        stored = [json.loads(l) for l in f]
    says('data/phase28-grand-audit.jsonl matches a fresh run',
         json.dumps(stored, sort_keys=True)
         == json.dumps(rows1, sort_keys=True))
else:
    print('MISSING  data/phase28-grand-audit.jsonl')

print('\n%d check(s), %s'
      % (checks, 'all pass' if not fails
         else '%d FAILED: %s' % (len(fails), '; '.join(fails[:4]))))
sys.exit(1 if fails else 0)
