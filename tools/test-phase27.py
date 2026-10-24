# -*- coding: utf-8 -*-
"""Phase 2.7: the v4 evidence is what it says it is.

    python tools/test-phase27.py

Reads the evidence store. Re-hashes a sample of the files v4 says it
read, where sources/ is present. Asks git whether the commit every v4
row names holds the reader that row names.
"""
import collections
import hashlib
import io
import json
import os
import random
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evidence as EV
import evidence_store as ST
import provenance as PV

fails = []
checks = 0


def says(name, ok, shown=''):
    global checks
    checks += 1
    if not ok:
        fails.append(name)
    print('%-4s %-60s %s' % ('ok' if ok else 'FAIL', name[:60], shown))


def git(args):
    return subprocess.check_output(['git'] + args, cwd=ROOT,
                                   stderr=subprocess.DEVNULL)


v4 = list(ST.iter_rows([4]))
says('v4 exists in the store', len(v4) > 0, '%d rows' % len(v4))
says('1. every v4 row is version 4', all(d.get('v') == 4 for d in v4))
fps = collections.Counter(d.get('reader') for d in v4)
says('2. one reader fingerprint for all of v4', len(fps) == 1,
     ', '.join(fps))
says('...the Phase 2.6 reader, c12eb3102b45',
     list(fps) == ['c12eb3102b45'])
shaok = all(re.match(r'^[0-9a-f]{64}$', (d.get('read') or {})
                     .get('sha256', '')) for d in v4)
says('3. every v4 row carries a SHA-256 of what it read', shaok)
if os.path.isdir(ROOT + 'sources/fiches'):
    random.seed(4)
    sample = random.sample(v4, min(300, len(v4)))
    bad = []
    for d in sample:
        p = os.path.join(ROOT, 'sources', *d['read']['path'].split('/'))
        h = hashlib.sha256(open(p, 'rb').read()).hexdigest()
        if h != d['read']['sha256'] or os.path.getsize(p) != \
                d['read']['bytes']:
            bad.append(d['read']['path'])
    says('...and re-hashing 300 of them gives the same bytes',
         not bad, '; '.join(bad)[:40])
else:
    print('MISSING  sources/ (re-hash check)')
commits = collections.Counter((d.get('git') or {}).get('commit')
                              for d in v4)
says('4. one git commit for all of v4, a full sha',
     len(commits) == 1 and all(re.match(r'^[0-9a-f]{40}$', c or '')
                               for c in commits), ', '.join(
                                   c[:12] for c in commits if c))
try:
    c = list(commits)[0]
    h = hashlib.sha1()
    for name in ('sheetreader.py', 'read-fiches.py'):
        h.update(git(['show', '%s:tools/%s' % (c, name)]))
    says('...and that commit holds the reader the rows name',
         h.hexdigest()[:12] == list(fps)[0], h.hexdigest()[:12])
    src = git(['show', '%s:tools/evidence-wines.py' % c]).decode('utf-8')
    says('...and its evidence-wines.py writes version 4',
         'DECIDER_VERSION = 4' in src)
except Exception as ex:
    says('...and that commit holds the reader the rows name', False,
         str(ex)[:40])
says('5. v4 was run from a clean tree (no dirty row)',
     all((d.get('git') or {}).get('dirty') is False
         and (d.get('git') or {}).get('status_hash') is None for d in v4))
says('...and no v4 row carries the v1-v3 fields observed/commit',
     not any('observed' in d or 'commit' in d for d in v4))
fl = list(ST.iter_failures(4))
says('6. provenance failures carry no verdict',
     all('decision' not in f and f.get('kind') == 'provenance_failure'
         and f.get('code') in PV.FAILURES for f in fl),
     '%d failure(s)' % len(fl))
keys = collections.Counter(EV.row_key(d) for d in v4)
says('7. every v4 decision identity is unique',
     all(n == 1 for n in keys.values()),
     '%d duplicates' % sum(n - 1 for n in keys.values()))
ix = json.load(io.open(ST.INDEX, encoding='utf-8'))
says('8. the index agrees with the rows (and verify() is clean)',
     ix['versions']['4']['rows'] == len(v4) and ST.verify() == [])
# 9. v1-v3 exactly as at the commit before v4.
try:
    old = json.loads(git(['show', 'ddf5d19:data/evidence/index.json']))
    same = all(old['versions'][v]['parts'] == ix['versions'][v]['parts']
               for v in ('1', '2', '3'))
except Exception:
    same = False
says('9. v1, v2, v3 parts identical to ddf5d19 (hash, rows, bytes)', same)
PROTECTED = ('data/sources.json', 'data/fiches.js', 'data/cuvees.js',
             'data/field-src.js', 'data/cuvee-src.js')
out = git(['diff', '--name-only', 'ddf5d19', '--'] + list(PROTECTED)) \
    .decode().strip()
says('10. canonical files unchanged since ddf5d19', out == '',
     'clean' if not out else out[:30])
print('\n%d check(s), %s'
      % (checks, 'all pass' if not fails
         else '%d FAILED: %s' % (len(fails), '; '.join(fails[:4]))))
sys.exit(1 if fails else 0)
