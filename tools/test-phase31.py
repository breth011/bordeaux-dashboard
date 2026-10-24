# -*- coding: utf-8 -*-
"""Phase 3.1: the structural audit's invariants.

    python tools/test-phase31.py

Read-only. Three kinds of check:

  scope       what this phase changed, and that nothing canonical,
              historical or proposed moved;
  findings    the audit's measured facts, read from the code and data AS
              AUDITED (commit e100b25, via `git show`), so they stay true
              after Phase 3.2 changes the code;
  boundaries  the separations the audit found sound, checked on the live
              tree, because they must keep holding.

The full existing suite is run separately (docs §19 lists the results);
it takes too long to nest here.
"""
import importlib.util
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

BASE = 'e100b25'
DOC = 'docs/PHASE-3.1-STRUCTURAL-AND-DOMAIN-AUDIT.md'
REPORT = 'data/audit/phase31-structure.json'
OWN = {DOC, REPORT, 'tools/audit-structure.py', 'tools/test-phase31.py',
       # its first three checks rescoped to Phase 3.0's own commits
       'tools/test-phase30.py'}
CANON = ('data/fiches.js', 'data/field-src.js', 'data/cuvee-src.js', 'data/chateaux.js',
         'data/cuvees.js', 'data/sources.json', 'data/proposals.jsonl',
         'data/attribution-candidates.jsonl')
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
                                   stderr=subprocess.DEVNULL).decode('utf-8')


def at_base(path):
    return git(['show', '%s:%s' % (BASE, path)])


log = [l.split(' ', 1) for l in git(['log', '--format=%H %s', BASE + '..HEAD']).splitlines()]
mine = [h for h, s in log if s.startswith('Phase 3.1')]
later = [h for h, s in log if not s.startswith('Phase 3.1')]
# A later phase's uncommitted files count as later too: the reproduction
# checks below describe the tree as Phase 3.1 left it, and a new tool in
# the working tree is not part of that (Phase 3.2 found this).
later += sorted(set(l[3:] for l in git(['status', '--porcelain=v1',
                                         '--untracked-files=all']).splitlines()) - OWN)
changed = set()
for h in mine:
    changed |= set(git(['diff-tree', '--no-commit-id', '--name-only', '-r', h]).split())
if not mine:
    changed |= set(l[3:] for l in git(['status', '--porcelain=v1',
                                        '--untracked-files=all']).splitlines())

# ---------------------------------------------------------------- scope
says('the audit started from e100b25, the Phase 3.0 commit',
     git(['log', '-1', '--format=%s', BASE]).startswith('Phase 3.0')
     and subprocess.call(['git', 'merge-base', '--is-ancestor', BASE, 'HEAD'], cwd=ROOT) == 0)
says('Phase 3.1 changed only its audit files', changed <= OWN,
     ', '.join(sorted(changed - OWN))[:40])
says('...no canonical file, manifest or proposal', not (changed & set(CANON)))
says('...no app code and no data the page loads (no implementation)',
     not any(f.startswith(('assets/', 'index.html', 'service-worker.js'))
             or re.match(r'data/[^/]+\.js$', f) for f in changed))
says('...nothing in data/evidence/, and the store verifies at 177,127, no v6',
     not any(f.startswith('data/evidence/') for f in changed)
     and ST.verify() == [] and sum(1 for _ in ST.iter_rows()) == 177127
     and ST.versions() == [1, 2, 3, 4, 5]
     and not any(re.match(r'(decisions|provenance-failures)-v6', f)
                 for f in os.listdir(ROOT + 'data/evidence')))
says('the reader is still 7e8cfed1c24e', EV.reader_fingerprint() == '7e8cfed1c24e')
says('the Phase 3.0 universe and its comparisons are untouched',
     not any(f.startswith(('data/scope/', 'tools/build-universe.py',
                           'tools/compare-universe.py')) for f in changed))
if os.path.isdir(ROOT + 'sources/scope') and not later:
    r = subprocess.run([sys.executable, '-I', ROOT + 'tools/build-universe.py', '--check'],
                       cwd=ROOT, capture_output=True)
    says('...and a rebuild still reproduces it', r.returncode == 0)
Es = sr.estates(ROOT)
S = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))['sheets']
says('the Phase 2 proposals are unapplied: Terrasses, Echo (50 as Blanc), Murets',
     Es['stem-chateau-tour-saint-christophe']['second'] is None
     and sum(1 for r in S if r['estate'] == 'lynch-bages' and 'echo' in r['file'].lower()
             and r['wine'] == 'Blanc de Lynch-Bages') == 50
     and Es['caillou']['second'] == 'Les Erables de Caillou'
     and not any('murets' in str(w).lower() for w in Es['caillou']['cuvees']))

# -------------------------------------------------------------- document
t = io.open(ROOT + DOC, encoding='utf-8').read() if os.path.exists(ROOT + DOC) else ''
secs = [int(s) for s in re.findall(r'^## (\d+)\. ', t, re.M)]
says('the audit document has its 19 sections', secs == list(range(1, 20)), str(len(secs)))
CONCEPTS = ('Estate', 'Wine', 'WineEstateRelationship', 'WineRole', 'Vintage', 'Document',
            'Source', 'Observation', 'CanonicalValue', 'Provenance', 'Reconciliation',
            'Quality/Anomaly', 'ClassificationMembership', 'Appellation',
            'HistoricalIdentity')
model = t.split('## 16.', 1)[-1].split('## 17.', 1)[0]
says('every conceptual entity is named in the proposed model',
     all(re.search(r'\b%s\b' % re.escape(c), model) for c in CONCEPTS),
     ', '.join(c for c in CONCEPTS if not re.search(r'\b%s\b' % re.escape(c), model)))
says('the partial wine universe is recorded as not a structural blocker',
     'The incomplete authoritative wine universe is a domain-data limitation carried '
     'forward from Phase 3.0. It is not treated as a structural blocker for this audit.'
     in ' '.join(t.split()))
ids = re.findall(r'^\| ([SLRBM]\d+) \|', t, re.M)
says('40 findings, each in exactly one class (8 S, 12 L, 12 R, 3 B, 5 M)',
     len(ids) == len(set(ids)) == 40
     and [sum(1 for i in ids if i[0] == k) for k in 'SLRBM'] == [8, 12, 12, 3, 5])
says('the document states the gate',
     t.rstrip().endswith('**SAFE — STRUCTURAL AUDIT COMPLETE**')
     or t.rstrip().endswith('**BLOCKED — STRUCTURAL AUDIT INCOMPLETE**'))

# ------------------------------------------------- the report, as audited
R = json.load(io.open(ROOT + REPORT, encoding='utf-8'))
if not later:
    r = subprocess.run([sys.executable, '-I', ROOT + 'tools/audit-structure.py', '--check'],
                       cwd=ROOT, capture_output=True)
    says('the dependency report is reproduced from the tree', r.returncode == 0,
         r.stdout.decode().strip()[:30])
T = {x['tool']: x for x in R['tools']}
M = R['measures']
says('report: 308 edges, one 13-tool cycle through the manifest',
     len(R['edges']) == 308 and [len(c) for c in R['tool_cycles']] == [13]
     and 'tools/read-fiches.py' in R['tool_cycles'][0])
says('R6: the only unflagged store writers are promote-urls and read-sheets',
     sorted(k for k, x in T.items() if x['ungated_store_writes']
            and not k.startswith('tools/test-'))
     == ['tools/promote-urls.py', 'tools/read-sheets.py'])
says('R4: basename first-match in 11 tools, including two canonical writers',
     sum(1 for k, x in T.items() if x['basename_first_match']) == 11
     and T['tools/read-fiches.py']['basename_first_match']
     and T['tools/read-plantings.py']['basename_first_match'])
says('R2: every grand-vin record is keyed estate|vintage (2,725)',
     M['records']['fiches_key_parts'] == {'2': 2725})
says('R3: canonical provenance is a basename (364 values cite an ambiguous one)',
     not M['field-src.js']['provenance_carries_folder_or_hash']
     and not M['cuvee-src.js']['provenance_carries_folder_or_hash']
     and M['field-src.js']['field_values_naming_an_ambiguous_document']
     + M['cuvee-src.js']['field_values_naming_an_ambiguous_document'] == 364)
says('R9: document identity is the path (13,032 rows, 12,771 paths, 12,019 sha1)',
     (M['manifest']['rows'], M['manifest']['distinct_folder_file'],
      M['manifest']['distinct_sha1']) == (13032, 12771, 12019))
says('R12: compact estates take their id from their name (app and reader)',
     M['identity']['sparse_ids_from_name_in_app_js']
     and M['identity']['sparse_ids_from_name_in_sheetreader'])

# --------------------------------------------- code facts, at e100b25
rf = at_base('tools/read-fiches.py')
says('R1: read-fiches reads role unknown into the grand-vin record',
     "if s.get('role') not in ('grand', 'combined', 'page',\n                                 'unknown'):"
     in rf and "'%s|%s' % (eid, yr)" in rf)
cv = at_base('data/cuvees.js')
roles = set(re.findall(r",role:'([^']*)'", cv.split('window.BDX_CUVEES', 1)[0]))
says('B1: a wine role is second or other; no unknown role exists', roles == {'second', 'other'},
     str(sorted(roles)))
srb = at_base('tools/sheetreader.py')
says('R11: the reader turns "none" (an em-dash) into None, like unknown',
     "if e['second'] and len(packed(e['second'])) < 3:\n            e['second'] = None" in srb
     and len(re.findall(r"second:'—'", ''.join(at_base('data/' + f) for f in (
         'chateaux.js', 'sauternes.js', 'saintemilion.js', 'pomerol.js', 'graves.js',
         'libournais.js', 'batch2.js', 'batch3.js', 'batch4.js')))) == 34)
says('B3: the losing values have no persistent home at e100b25',
     'data/field-conflicts.jsonl' not in git(['ls-tree', '-r', '--name-only', BASE, 'data/'])
     and 'best.setdefault(key, {}).setdefault(f, (r[\'got\'][f], r[\'src\']))' in rf)
says('R7: merge-proposals writes a manifest role because a blend was merged',
     "sh['role'] = 'grand'" in at_base('tools/merge-proposals.py'))

# -------------------------------------------- boundaries, on the live tree
spec = importlib.util.spec_from_file_location('aus', ROOT + 'tools/audit-structure.py')
aus = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aus)
live = [x for x in aus.build()['tools'] if not x['tool'].startswith('tools/test-')]
store = aus.CANON_FILES | {'sources.json'}
says('S1: no tool that reads evidence writes canonical data or the manifest',
     not [x['tool'] for x in live if x['reads_evidence'] and set(x['writes_data']) & store])
says('S1: evidence_store.py is the only writer of data/evidence/',
     [x['tool'] for x in live if 'evidence/' in x['writes_data']] == ['tools/evidence_store.py'])
says('S2: no canonical or manifest writer reads the proposal files',
     not [x['tool'] for x in live if set(x['writes_data']) & store
          and {'proposals.jsonl', 'attribution-candidates.jsonl'} & set(x['reads_data'])])
index = io.open(ROOT + 'index.html', encoding='utf-8').read()
says('S3: the scope universe is loaded by no page and read by no canonical writer',
     'data/scope' not in index
     and not [x['tool'] for x in live if set(x['writes_data']) & store
              and any(r.startswith('scope/') for r in x['reads_data'])])

print('\n%d check(s), %s'
      % (checks, 'all pass' if not fails
         else '%d FAILED: %s' % (len(fails), '; '.join(fails[:4]))))
sys.exit(1 if fails else 0)
