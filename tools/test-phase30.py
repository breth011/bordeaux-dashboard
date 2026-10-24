# -*- coding: utf-8 -*-
"""Phase 3.0: scope and the authoritative universe, checked.

    python tools/test-phase30.py

Read-only. The universe is built from sources, every entry carries one,
the classification systems stay apart, uncertainty is marked rather than
resolved, and nothing canonical or historical moved.
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

BASE = '8964131'
DOC = 'docs/PHASE-3.0-SCOPE-AND-AUTHORITATIVE-UNIVERSE.md'
UNI = 'data/scope/authoritative-universe.json'
CDIS = 'data/scope/canonical-discrepancies.jsonl'
EDIS = 'data/scope/corpus-discrepancies.jsonl'
OWN = {DOC, UNI, CDIS, EDIS, 'tools/build-universe.py', 'tools/compare-universe.py',
       'tools/canonical-view.js', 'tools/test-phase30.py',
       # its first check rescoped to Phase 2.12's own commit range
       'tools/test-phase212.py'}
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


def jsonl(p):
    return [json.loads(l) for l in io.open(ROOT + p, encoding='utf-8') if l.strip()]


# 1-3. what moved since Phase 2 closed
changed = set(git(['diff', '--name-only', BASE]).split()) | set(
    l[3:] for l in git(['status', '--porcelain=v1', '--untracked-files=all']).splitlines())
says('since %s only Phase 3.0\'s own files changed' % BASE, changed <= OWN,
     ', '.join(sorted(changed - OWN))[:40])
out = git(['diff', '--name-only', BASE, '--'] + list(CANON) +
          ['data/proposals.jsonl', 'data/attribution-candidates.jsonl']).strip()
says('canonical files and Phase 2 proposals unchanged', out == '', out[:30])
out = git(['diff', '--name-only', BASE, '--', 'data/evidence/']).strip()
says('the evidence store is as at %s, verifies, 177,127 decisions, no v6' % BASE,
     out == '' and ST.verify() == [] and sum(1 for _ in ST.iter_rows()) == 177127
     and ST.versions() == [1, 2, 3, 4, 5]
     and not any(re.match(r'(decisions|provenance-failures)-v6', f)
                 for f in os.listdir(ROOT + 'data/evidence')))
says('the reader is still 7e8cfed1c24e', EV.reader_fingerprint() == '7e8cfed1c24e')

U = json.load(io.open(ROOT + UNI, encoding='utf-8'))
SRC = {s['id']: s for s in U['sources']}
SYS = {s['id'] for s in U['systems']}
E, W = U['estates'], U['wines']

# 5. the universe is what the sources say, today
if os.path.isdir(ROOT + 'sources/scope'):
    r = subprocess.run([sys.executable, '-I', ROOT + 'tools/build-universe.py', '--check'],
                       cwd=ROOT, capture_output=True)
    says('a rebuild from the retrieved sources reproduces the universe',
         r.returncode == 0, r.stdout.decode().strip()[:30])
else:
    print('MISSING  sources/scope (rebuild check)')

# 6. each system parsed to its own source's total, rank by rank
ranks = collections.defaultdict(collections.Counter)
for e in E:
    for m in e['memberships']:
        ranks[m['system']][m['rank']] += 1
says('memberships match the sources\' totals: 61, 27, 14, 85, 170, 33',
     {k: sum(v.values()) for k, v in ranks.items()} ==
     {'1855-medoc': 61, '1855-sauternes': 27, 'graves': 14, 'stem-2022': 85,
      'cb-2025': 170, 'ca-2022': 33})
says('...and their tiers: 1855 5/14/14/10/18, Sauternes 1/11/15, '
     'Saint-Emilion 2/12/71, Crus Bourgeois 14/36/120',
     ranks['1855-medoc'] == {1: 5, 2: 14, 3: 14, 4: 10, 5: 18}
     and ranks['1855-sauternes'] == {0: 1, 1: 11, 2: 15}
     and ranks['stem-2022'] == {1: 2, 2: 12, 3: 71}
     and ranks['cb-2025'] == {1: 14, 2: 36, 3: 120})

# 7. every entry cites a retrieved source, and every source is registered
cited = [s for e in E for s in e['sources']] + [s for w in W for s in w['sources']] + \
        [m['source'] for e in E for m in e['memberships']]
says('every estate and wine cites a source, and every citation resolves',
     all(e['sources'] for e in E) and all(w['sources'] for w in W)
     and all(s in SRC for s in cited))
says('...and none cites a source that was not retrieved',
     all(SRC[s]['path'] and SRC[s]['sha256'] and SRC[s]['retrieved']
         and 'REFERENCE' not in SRC[s]['role'] for s in set(cited)))
says('every registered source states type, authority, scope, primary, limits',
     all(all(k in s for k in ('type', 'url', 'authority', 'geographic_scope',
                              'temporal_scope', 'primary', 'current', 'limitations',
                              'retrieved')) for s in U['sources']))

# 8. the systems stay apart
hb = [e for e in E if e['id'] == 'u-haut-brion'][0]
hbw = [w for w in W if w['estate'] == 'u-haut-brion' and w['kind'] == 'CLASSIFIED_WINE']
says('each system kept separately; Haut-Brion in two, its red one wine',
     all(m['system'] in SYS for e in E for m in e['memberships'])
     and sorted(m['system'] for m in hb['memberships']) == ['1855-medoc', 'graves']
     and len(hbw) == 1 and hbw[0].get('also_classified', {}).get('system') == 'graves')
says('Graves classified per colour: 20 wines from 14 crus',
     sum(1 for w in W if w['classification'] and w['classification']['system'] == 'graves'
         or w.get('also_classified', {}).get('system') == 'graves') == 20)

# 9. uncertainty is marked, not resolved
un = sorted(e['id'] for e in E if e['identity_status'] == 'UNRESOLVED_IDENTITY')
says('same-name estates in two systems are kept apart and marked',
     un == ['u-bellevue--cb-2025', 'u-bellevue--stem-2022',
            'u-la-commanderie--cb-2025', 'u-la-commanderie--stem-2022'], str(len(un)))
mb = [e for e in E if e['id'] == 'u-moutte-blanc'][0]
says('Moutte Blanc: one estate, two classified wines, with the basis stated',
     len(mb['memberships']) == 2 and mb['identity_basis']
     and len([w for w in W if w['estate'] == 'u-moutte-blanc']) == 2)

# 10. nothing filled in that a source does not give
ew = [w for w in W if w['kind'] == 'ESTATE_WINE']
says('an estate wine has a role only where its source uses the word',
     all((w['role'] is None) or ('second' in w['source_term'].lower()) for w in ew)
     and all(w['estate'] in {'u-lynch-bages', 'u-caillou', 'u-tour-saint-christophe'}
             for w in ew))
says('a classified wine has a colour only from the Graves source',
     all(w['colour'] is None or w['colour_source'] == 'wp-graves'
         for w in W if w['kind'] == 'CLASSIFIED_WINE'))
says('owner set only where a source states it',
     all(e['owner'] is None or e['owner'].get('source') in SRC for e in E)
     and sum(1 for e in E if e['owner']) == 1)

# 11. temporal cases are sourced
says('every temporal case cites a registered source and quotes it',
     len(U['temporal']) >= 9 and all(t['source'] in SRC and t.get('quote')
                                     for t in U['temporal']))

# 12-13. the comparisons: recorded, separate, and stopping at the discrepancy
C = jsonl(CDIS)
X = jsonl(EDIS)
CCAT = {'IN_UNIVERSE_NOT_IN_CANONICAL', 'IN_CANONICAL_NOT_IN_UNIVERSE',
        'IDENTITY_MAPPING_UNCERTAIN', 'ROLE_DIFFERENCE', 'CLASSIFICATION_DIFFERENCE',
        'APPELLATION_DIFFERENCE', 'TEMPORAL_DIFFERENCE', 'NAME_VARIANT',
        'SOURCE_CONFLICT', 'UNRESOLVED'}
says('canonical discrepancies use only the defined categories',
     {d['category'] for d in C} <= CCAT)
says('corpus discrepancies are kept in their own file and categories',
     X and not ({d['category'] for d in X} & CCAT))
want = {('IN_CANONICAL_NOT_IN_UNIVERSE', 'artisan-chateau-lamongeau'),
        ('IN_CANONICAL_NOT_IN_UNIVERSE', 'artisan-chateau-tour-bel-air'),
        ('TEMPORAL_DIFFERENCE', 'laville-haut-brion'),
        ('TEMPORAL_DIFFERENCE', 'la-tour-haut-brion'),
        ('IDENTITY_MAPPING_UNCERTAIN', ('pichon-baron',)),
        ('ROLE_DIFFERENCE', 'caillou')}
have = {(d['category'], tuple(d['canonical']) if isinstance(d.get('canonical'), list)
         else d.get('canonical')) for d in C}
says('the known canonical discrepancies are among those recorded', want <= have,
     ', '.join(str(x[1]) for x in want - have)[:30])
says('the corpus side finds the three Phase 2 findings: 50 Echo as Blanc, '
     '15 Terrasses as grand vin, Murets',
     any(d['category'] == 'CORPUS_ROLE_DIFFERS' and d['sheets'] == 50 for d in X)
     and any(d['category'] == 'CORPUS_DECISION_CONFLICTS_WITH_UNIVERSE'
             and d['decisions'] == 15 for d in X)
     and any(d['category'] == 'CORPUS_WINE_NOT_IN_CANONICAL' for d in X)
     and any(d['category'] == 'CORPUS_UNATTRIBUTED' and d['sheets'] == 908 for d in X))

# 14. the proposals were tested, not applied
Es = sr.estates(ROOT)
S = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))['sheets']
says('no proposal applied: Tour Saint-Christophe lists no second wine, '
     '50 Echo still filed as Blanc, Caillou\'s list unchanged',
     Es['stem-chateau-tour-saint-christophe']['second'] is None
     and sum(1 for r in S if r['estate'] == 'lynch-bages' and 'echo' in r['file'].lower()
             and r['wine'] == 'Blanc de Lynch-Bages') == 50
     and Es['caillou']['second'] == 'Les Erables de Caillou')

# 15. the canonical view the comparison reads agrees with the app's counts
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location('cu', ROOT + 'tools/compare-universe.py')
    cu = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cu)
    CV = cu.canonical()
    n = collections.Counter(e['cls'] for e in CV['estates'])
    coll = {c['id']: c['estates'] for c in CV['collections']}
    says('the canonical view matches classifications.js (Saint-Emilion 14 + 71 '
         'sparse, Graves 15 + Haut-Brion)',
         all(n[k] == v for k, v in coll.items() if k not in ('stem', 'pomerol', 'graves'))
         and n['stem'] == 85 and n['graves'] + 1 == coll['graves'], str(dict(n))[:30])
except Exception as ex:          # node missing is a failure, not a skip
    says('the canonical view matches classifications.js', False, repr(ex)[:30])

# 16. the document
if os.path.exists(ROOT + DOC):
    t = io.open(ROOT + DOC, encoding='utf-8').read()
    secs = re.findall(r'^## (\d+)\. ', t, re.M)
    says('the Phase 3.0 document has its 14 sections',
         [int(s) for s in secs] == list(range(1, 15)), str(len(secs)))
    says('...and states the gate', 'SAFE — SCOPE AND UNIVERSE DEFINED' in t
         or 'BLOCKED — SCOPE OR AUTHORITATIVE UNIVERSE INCOMPLETE' in t)
else:
    says('the Phase 3.0 document exists', False)

print('\n%d check(s), %s'
      % (checks, 'all pass' if not fails
         else '%d FAILED: %s' % (len(fails), '; '.join(fails[:4]))))
sys.exit(1 if fails else 0)
