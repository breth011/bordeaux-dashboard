# -*- coding: utf-8 -*-
"""Phase 2.10: the v5 evidence is what it says it is, and v1-v4 are
untouched.

    python tools/test-phase210.py
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


v5 = list(ST.iter_rows([5]))
v4n = sum(1 for _ in ST.iter_rows([4]))
says('v5 exists', len(v5) > 0, '%d rows' % len(v5))
says('every v5 row is version 5', all(d.get('v') == 5 for d in v5))
fps = collections.Counter(d.get('reader') for d in v5)
says('one reader for all of v5: the Phase 2.9 reader 7e8cfed1c24e',
     list(fps) == ['7e8cfed1c24e'], ', '.join(fps))
commits = collections.Counter(d['git']['commit'] for d in v5)
says('one full commit for all of v5', len(commits) == 1
     and all(re.match(r'^[0-9a-f]{40}$', c) for c in commits),
     ', '.join(c[:12] for c in commits))
try:
    c = list(commits)[0]
    h = hashlib.sha1()
    for name in ('sheetreader.py', 'read-fiches.py'):
        h.update(git(['show', '%s:tools/%s' % (c, name)]))
    says('...whose code is that reader', h.hexdigest()[:12] == list(fps)[0])
    says('...and whose runner writes version 5',
         'DECIDER_VERSION = 5' in git(['show', '%s:tools/evidence-wines.py'
                                       % c]).decode('utf-8'))
except Exception as ex:
    says('...whose code is that reader', False, str(ex)[:40])
says('v5 ran clean: no dirty row',
     all(d['git']['dirty'] is False and d['git']['status_hash'] is None
         for d in v5))
says('every v5 row carries a SHA-256 of what it read',
     all(re.match(r'^[0-9a-f]{64}$', d['read']['sha256']) for d in v5))
says('no v5 row carries the v1-v3 fields observed/commit',
     not any('observed' in d or 'commit' in d for d in v5))
if os.path.isdir(ROOT + 'sources/fiches'):
    random.seed(5)
    bad = []
    for d in random.sample(v5, min(300, len(v5))):
        p = os.path.join(ROOT, 'sources', *d['read']['path'].split('/'))
        if hashlib.sha256(open(p, 'rb').read()).hexdigest() \
                != d['read']['sha256']:
            bad.append(d['read']['path'])
    says('re-hashing 300 v5 files gives the recorded bytes', not bad,
         '; '.join(bad)[:40])
else:
    print('MISSING  sources/ (re-hash check)')
keys = collections.Counter(EV.row_key(d) for d in v5)
says('every v5 decision identity is unique',
     all(n == 1 for n in keys.values()))
f5 = list(ST.iter_failures(5))
f4 = list(ST.iter_failures(4))
says('v5 provenance failures carry no verdict',
     all('decision' not in f and f['code'] in PV.FAILURES for f in f5),
     '%d' % len(f5))
says('...and are the same artifacts as v4\'s',
     sorted((f['artifact'], f['ctx'].get('folder'), f['code']) for f in f5)
     == sorted((f['artifact'], f['ctx'].get('folder'), f['code'])
               for f in f4))
ix = json.load(io.open(ST.INDEX, encoding='utf-8'))
says('the index agrees with the rows and verify() is clean',
     ix['versions']['5']['rows'] == len(v5) and ST.verify() == [])
try:
    old = json.loads(git(['show', '6e4effb:data/evidence/index.json']))
    same = all(old['versions'][v]['parts'] == ix['versions'][v]['parts']
               for v in ('1', '2', '3', '4'))
    same_f = old['versions']['4'].get('failures') == \
        ix['versions']['4'].get('failures')
except Exception:
    same = same_f = False
says('v1-v4 decision files identical to 6e4effb (hash, rows, bytes)', same)
says('v4 failure file identical to 6e4effb', same_f)
out = git(['diff', '--name-only', '6e4effb', '--',
           'data/evidence/decisions-v1.jsonl',
           'data/evidence/decisions-v2.jsonl',
           'data/evidence/decisions-v3.jsonl',
           'data/evidence/decisions-v4.jsonl',
           'data/evidence/provenance-failures-v4.jsonl']).decode().strip()
says('...and git agrees, byte for byte', out == '', out[:30])

# The reconciliation, as compare-v5.py wrote it
p = ROOT + 'data/v4-v5-comparison.json'
if os.path.exists(p):
    cmp_ = json.load(io.open(p, encoding='utf-8'))
    r = cmp_['reconciliation']
    says('every same question is classified exactly once',
         sum(r['classes'].values()) == r['same_questions'])
    says('v4 and v5 ask the same questions (none dropped, none new)',
         r['only_v4'] == 0 and r['only_v5'] == 0,
         '%d / %d' % (r['only_v4'], r['only_v5']))
    pr = cmp_['prediction']
    says('the verdicts that changed are exactly the ones Phase 2.9 '
         'predicted', pr['observed'] == pr['predicted'] ==
         pr['both_same_verdict'] and not pr['observed_not_predicted']
         and not pr['predicted_not_observed'],
         '%d/%d' % (pr['both_same_verdict'], pr['predicted']))
    says('second-wine verdicts: none changed',
         not cmp_['role_second']['changes'])
    says('grand vin: no refused -> accepted',
         not any(k.startswith('REFUSED_TO_ACCEPTED')
                 or k.startswith('UNRESOLVED_TO_ACCEPTED')
                 for k in cmp_['role_grand']['changes']))
else:
    print('MISSING  data/v4-v5-comparison.json')

PROTECTED = ('data/sources.json', 'data/fiches.js', 'data/cuvees.js',
             'data/field-src.js', 'data/cuvee-src.js', 'data/chateaux.js')
out = git(['diff', '--name-only', '6e4effb', '--'] + list(PROTECTED)) \
    .decode().strip()
says('canonical files unchanged since 6e4effb', out == '',
     'clean' if not out else out[:30])
print('\n%d check(s), %s'
      % (checks, 'all pass' if not fails
         else '%d FAILED: %s' % (len(fails), '; '.join(fails[:4]))))
sys.exit(1 if fails else 0)
