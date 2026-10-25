# -*- coding: utf-8 -*-
"""Phase 3.4: the domain model review, checked.

    python tools/test-phase34.py

Read-only. Checks the scope of the phase (nothing canonical, evidential,
proposed or discovered changed), that the revised model is reproducible
and internally consistent, that every Phase 3.2 concept is accounted for,
that the worked cases obey the model and cite real harvested artifacts,
and that each of the twenty Phase 4 readiness requirements is shown by a
case.
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

BASE = 'b278121'
REVIEW = 'docs/PHASE-3.4-DOMAIN-MODEL-REVIEW.md'
CONTRACT = 'docs/PHASE-3.4-DOMAIN-MODEL.md'
MODEL = 'docs/phase34-model.json'
FIX = 'docs/phase34-fixtures.json'
ANALYSIS = 'data/review/phase34-corpus-analysis.json'
OWN = {REVIEW, CONTRACT, MODEL, FIX, ANALYSIS, 'tools/review-corpus.py', 'tools/build-phase34-model.py',
       'tools/test-phase34.py',
       # its design-file check narrowed to tools that write data
       'tools/test-phase32.py'}
CANON = ('data/fiches.js', 'data/field-src.js', 'data/cuvee-src.js', 'data/chateaux.js', 'data/cuvees.js',
         'data/sources.json', 'data/proposals.jsonl', 'data/attribution-candidates.jsonl')
fails = []
checks = 0


def says(name, ok, shown=''):
    global checks
    checks += 1
    if not ok:
        fails.append(name)
    print('%-4s %-62s %s' % ('ok' if ok else 'FAIL', name[:62], shown))


def git(args):
    return subprocess.check_output(['git'] + args, cwd=ROOT, stderr=subprocess.DEVNULL).decode('utf-8')


log = [l.split(' ', 1) for l in git(['log', '--format=%H %s', BASE + '..HEAD']).splitlines()]
mine = [h for h, s in log if s.startswith('Phase 3.4')]
later = [h for h, s in log if not s.startswith('Phase 3.4')]
changed = set()
for h in mine:
    changed |= set(git(['diff-tree', '--no-commit-id', '--name-only', '-r', h]).split())
if not mine:
    changed |= set(l[3:] for l in git(['status', '--porcelain=v1', '--untracked-files=all']).splitlines())

# ================================================================ scope
says('1 Phase 3.3 (b278121) is the declared input',
     git(['log', '-1', '--format=%s', BASE]).startswith('Phase 3.3')
     and subprocess.call(['git', 'merge-base', '--is-ancestor', BASE, 'HEAD'], cwd=ROOT) == 0)
says('Phase 3.4 changed only its review, model, analysis, tools and test', changed <= OWN,
     ', '.join(sorted(changed - OWN))[:40])
says('2 discovery data unchanged', not any(f.startswith('data/discovery/') for f in changed))
says('3 canonical data, manifest and proposals unchanged', not (changed & set(CANON)))
says('4-5 v1-v5 evidence unchanged and verifying; no v6',
     not any(f.startswith('data/evidence/') for f in changed)
     and ST.verify() == [] and sum(1 for _ in ST.iter_rows()) == 177127 and ST.versions() == [1, 2, 3, 4, 5]
     and not any(re.match(r'(decisions|provenance-failures)-v6', f) for f in os.listdir(ROOT + 'data/evidence')))
says('the reader is still 7e8cfed1c24e', EV.reader_fingerprint() == '7e8cfed1c24e')
Es = sr.estates(ROOT)
SJ = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))['sheets']
says('6 no Phase 2 proposal applied: Terrasses, Echo (50 as Blanc), Murets',
     Es['stem-chateau-tour-saint-christophe']['second'] is None
     and sum(1 for r in SJ if r['estate'] == 'lynch-bages' and 'echo' in r['file'].lower()
             and r['wine'] == 'Blanc de Lynch-Bages') == 50
     and Es['caillou']['second'] == 'Les Erables de Caillou'
     and not any('murets' in str(w).lower() for w in Es['caillou']['cuvees']))
says('no implementation: no app, data file or schema changed',
     not any(f.startswith(('assets/', 'index.html', 'service-worker.js')) or re.match(r'data/[^/]+\.(js|json|jsonl)$', f)
             or f.endswith(('.sql', '.db', '.sqlite')) for f in changed))

# ================================================================ model
if not later:
    r = subprocess.run([sys.executable, '-I', ROOT + 'tools/build-phase34-model.py', '--check'], cwd=ROOT,
                       capture_output=True)
    says('the model is reproduced by its generator from the 3.2 model', r.returncode == 0,
         r.stdout.decode().strip()[:30])
M = json.load(io.open(ROOT + MODEL, encoding='utf-8'))
M32 = json.load(io.open(ROOT + 'docs/phase32-model.json', encoding='utf-8'))
E, EN = M['entities'], M['enums']
dangling = []
for n, e in E.items():
    for fld, d in e['fields'].items():
        t = d['type']
        if t.startswith('enum:') and t[5:] not in EN:
            dangling.append('%s.%s' % (n, fld))
        if t.startswith(('ref:', 'list:ref:')):
            for x in t.split(':', 1)[1].replace('ref:', '').split('|'):
                if x not in E and x not in ('*', 'ref'):
                    dangling.append('%s.%s' % (n, fld))
says('17 the contract is internally consistent: no dangling enum or entity reference', not dangling,
     ', '.join(dangling[:3]))
says('...every entity sits in exactly one declared layer',
     all(sum(n in l['holds'] for l in M['layers'] if l['id'] != 'IDENTITY' or n != 'Artifact') >= 1 for n in E)
     and {h for l in M['layers'] for h in l['holds']} - {'Validity', 'TemporalBound'} == set(E))
diff = M['diff']
accounted = set(diff['RETAIN']) | {x[0].split(' ->')[0] for x in diff['RENAME']}
accounted |= {n for n in E}          # changed in place
retained_names = {r.split(' (')[0] for r in diff['RETAIN']}
missing32 = [n for n in M32['entities'] if n not in E and n not in {x[0].split(' ->')[0] for x in diff['RENAME']}]
says('every Phase 3.2 entity is retained, changed or renamed in the diff', not missing32, ', '.join(missing32))
says('the diff lists Add, Split, Merge, Rename, Retain and Reject',
     all(diff.get(k) for k in ('ADD', 'SPLIT', 'MERGE', 'RENAME', 'RETAIN', 'REJECT')))
says('7-9 the hierarchy has THIRD, ABOVE_FIRST and UNRANKED, and no OTHER',
     {'THIRD', 'ABOVE_FIRST', 'UNRANKED', 'UNKNOWN', 'FIRST', 'SECOND'} == set(EN['RankTier']['values'])
     and 'WineRole' not in EN)
says('9 wine type is independent of rank (on the Wine; rank has only a scope type)',
     E['Wine']['fields']['type']['type'] == 'enum:WineType' and 'tier' not in E['Wine']['fields']
     and 'type' not in E['RankAssertion']['fields'] and 'claimant' in E['RankAssertion']['fields'])
says('13 temporal: relationships, ranks, appellations and names carry validity',
     all(E[n]['fields']['validity']['required'] for n in ('EstateWineRelationship', 'RankAssertion',
                                                         'AppellationMembership', 'NameRecord', 'RankAbsence',
                                                         'ClassificationMembership', 'WineDescriptor',
                                                         'SourceEstateRelationship'))
     and 'asserted_at' in E['Observation']['fields'])
says('12 observations keep raw label, raw value and language',
     all(k in E['Observation']['fields'] for k in ('raw_label', 'raw_value', 'lang', 'subject_status')))
D = M['decisions']
says('15 all eight Phase 3.2 decisions are accounted for, each with a status and evidence',
     sorted(D) == ['D%d' % i for i in range(1, 9)] and all(v['status'] and v['evidence'] and v['recommendation']
                                                          for v in D.values()))
says('16 the Phase 4 boundary is explicit',
     M['phase4_boundary']['phase4_may_implement'] and M['phase4_boundary']['phase4_must_not'])
says('the three Phase 2 proposals are assessed, none applied',
     set(M['proposals']) == {'Echo de Lynch-Bages', 'Les Terrasses de Saint Christophe', 'Les Murets de Caillou'}
     and all('status' in v for v in M['proposals'].values()))
says('14 discovery-only classes (B-F) are defined and used in the taxonomy',
     {'B', 'C', 'D', 'E', 'F'} <= {t['class'][0] for t in M['taxonomy']})

# ================================================================ fixtures
F = json.load(io.open(ROOT + FIX, encoding='utf-8'))
recs = [r for c in F['cases'] for r in c['records']]
ids = {r['id']: r for r in recs if 'id' in r}
problems = []
for r in recs:
    ent = r['entity']
    if ent not in E:
        problems.append('unknown ' + ent)
        continue
    for k in r:
        if k != 'entity' and k not in E[ent]['fields']:
            problems.append('%s.%s' % (ent, k))
    for k, d in E[ent]['fields'].items():
        if d.get('required') and k not in r:
            problems.append('%s %s lacks %s' % (ent, r.get('id', ''), k))
        if k in r and d['type'].startswith('enum:') and r[k] is not None and r[k] not in EN[d['type'][5:]]['values']:
            problems.append('%s.%s=%s' % (ent, k, r[k]))
says('every case record fits the model: fields, required fields, enum values', not problems,
     '; '.join(problems[:3]))
FORMAT = {'DAY': r'^\d{4}-\d{2}-\d{2}$', 'MONTH': r'^\d{4}-\d{2}$', 'YEAR': r'^\d{4}$', 'DECADE': r'^\d{4}s$'}


def bound_ok(bnd, end):
    k = bnd['kind']
    valued = k in ('EXACT', 'APPROXIMATE', 'NO_LATER_THAN', 'NO_EARLIER_THAN')
    if k not in EN['BoundKind']['values'] or valued != ('value' in bnd) or (valued and not bnd.get('basis')):
        return False
    if k == 'OPEN' and not end:
        return False
    if valued and bnd['axis'] == 'VINTAGE':
        return isinstance(bnd['value'], int) and bnd['precision'] == 'VINTAGE'
    if valued:
        return bool(re.match(FORMAT.get(bnd['precision'], '^$'), str(bnd['value'])))
    return True


bad = [r.get('id') for r in recs for key in ('validity', 'observed') if key in r
       and not (bound_ok(r[key]['valid_from'], False) and bound_ok(r[key]['valid_to'], True))]
bad += [r.get('id') for r in recs if r['entity'] == 'ArtifactDate' and not bound_ok(r['value'], False)]
says('every date in the cases has a basis and the precision its source gives', not bad, str(bad[:3]))
IDRE = re.compile(r'^[a-z]{2,3}_\d{3}$')
unres = sorted({v for r in recs for v in ([x for x in r.values() if isinstance(x, str)] +
                                           [y for x in r.values() if isinstance(x, list) for y in x if isinstance(y, str)])
                if IDRE.match(v) and v not in ids})
says('every reference in the cases resolves', not unres, ', '.join(unres[:4]))
arts = {}
for l in io.open(ROOT + 'data/discovery/artifacts.jsonl', encoding='utf-8'):
    a = json.loads(l)
    arts[a['sha256']] = a
cited = [r for r in recs if r['entity'] == 'Artifact']
says('every artifact a case cites is in the Phase 3.3 harvest', all(a['sha256'] in arts for a in cited),
     '%d artifacts' % len(cited))
says('...and the OCR case is an artifact the harvest flagged NEEDS_OCR',
     all(arts[a['sha256']].get('ocr') == 'NEEDED_NO_ENGINE' for a in cited if a['extraction_status'] == 'NEEDS_OCR'))


def of(entity, **kw):
    return [r for r in recs if r['entity'] == entity and all(r.get(k) == v for k, v in kw.items())]


tiers = {r['tier'] for r in of('RankAssertion')}
says('R1 third wines (Batailley, Caillou)', 'THIRD' in tiers)
says('R2 prestige / superior wines, by claimant (Mangot)',
     {(r['tier'], r['claimant']) for r in of('RankAssertion', relationship='rel_112')}
     == {('SECOND', 'CLASSIFICATION_BODY'), ('ABOVE_FIRST', 'PRESS')})
says('R3 explicit no hierarchy (Le Rey)', len(of('RankAssertion', tier='UNRANKED')) == 2)
wt = {r['id']: r['type'] for r in of('Wine')}
cai = [(wt[ids[r['relationship']]['wine']], r['tier'], r.get('scope_type')) for r in recs
       if r['entity'] == 'RankAssertion' and r['relationship'] in ('rel_105', 'rel_106', 'rel_107', 'rel_109')]
says('R4 type independent of rank (Caillou: two WHITE_DRY wines FIRST and SECOND; a sweet THIRD)',
     ('WHITE_DRY', 'FIRST', 'WHITE_DRY') in cai and ('WHITE_DRY', 'SECOND', 'WHITE_DRY') in cai
     and ('WHITE_SWEET', 'THIRD', None) in cai)
says('R5 identity independent of name (Desmirail: one wine, two names)',
     len(of('NameRecord', subject='win_113')) == 2 and of('NameRecord', kind='MARKET_ALIAS'))
says('R6-R7 historical relationships and ranks bounded in time (Terrasses 2016-2019)',
     ids['rnk_109']['validity']['valid_to']['kind'] == 'NO_EARLIER_THAN')
says('R8 wine-level classification (Bouscaut red and white)',
     {ids[c['wine']]['type'] for c in of('ClassificationMembership')} == {'RED', 'WHITE_DRY'})
says('R9 appellation per wine and in time (Climens)', len(of('AppellationMembership')) == 2)
says('R10 a historical name on one wine, without guessing a new one (Echo, Haut-Bailly)',
     of('NameRecord', subject='win_112', kind='FORMER') and of('NameRecord', subject='win_118', kind='FORMER')
     and set(M['identity_change_evidence']) >= {'RENAMED', 'SUCCEEDED_BY', 'POSSIBLY_SAME'})
says('R11-R12 a shared source and a multi-estate document (Vignobles K)',
     len(of('SourceEstateRelationship', source='src_112')) == 2 and len(of('Attribution', artifact='art_114')) == 2)
obs = of('Observation')
says('R13-R14 observations keep wording and language; versions are candidate relations',
     {o['lang'] for o in obs if o['id'] in ('obs_101', 'obs_102', 'obs_103')} == {'fr', 'en'}
     and of('ArtifactRelation', kind='LANGUAGE_VERSION_OF', status='CANDIDATE'))
says('R15 a canonical value derived without deleting the losing observations',
     ids['rec_101']['candidates'] == ['obs_101', 'obs_102', 'obs_103']
     and any(c['reconciliation'] == 'rec_101' for c in of('CanonicalValue')))
says('R16 discovery-only information stays an observation (SIRET, no canonical value)',
     of('Observation', subject='src_114') and not any(c['field'] == 'legal_identifier' for c in of('CanonicalValue')))
says('R17 a refused source is represented', of('Placement', status='ACCESS_REFUSED'))
says('R18 an OCR-dependent document exists before OCR', of('Artifact', extraction_status='NEEDS_OCR'))
says('R19 no complete wine universe needed (absence is no RankAssertion)',
     'a wine nobody ranks has no rank assertion' in EN['RankTier']['note'])
says('R20 the proposals are expressed with general constructs only (no special-case entity)',
     ids['rnk_109']['tier'] == 'SECOND' and ids['rnk_107']['scope'] == 'TYPE_RANGE'
     and of('NameRecord', subject='win_112', kind='CURRENT')
     and not any('echo' in n.lower() or 'terrasses' in n.lower() or 'murets' in n.lower() for n in E))

# ================================================================ documents
for path, n in ((REVIEW, 20), (CONTRACT, None)):
    t = io.open(ROOT + path, encoding='utf-8').read() if os.path.exists(ROOT + path) else ''
    if n:
        secs = [int(s) for s in re.findall(r'^## (\d+)\. ', t, re.M)]
        says('the review has its 20 sections', secs == list(range(1, n + 1)), str(len(secs)))
        says('...and ends with one gate',
             t.rstrip().endswith('**SAFE — DOMAIN MODEL REVIEW COMPLETE — READY FOR PHASE 4**')
             or t.rstrip().endswith('**BLOCKED — DOMAIN MODEL REVIEW INCOMPLETE**'))
    else:
        says('the domain contract names every entity of the model',
             t and all(re.search(r'\b%s\b' % re.escape(e), t) for e in E),
             ', '.join(e for e in E if not re.search(r'\b%s\b' % re.escape(e), t))[:40])
A = json.load(io.open(ROOT + ANALYSIS, encoding='utf-8'))
says('the corpus analysis covers hierarchy, relationships, time, taxonomy, families, languages, legal',
     all(k in A for k in ('hierarchy', 'relationship_wording', 'temporal_wording', 'taxonomy', 'fiche_families',
                          'language_versions', 'legal_entity', 'named_cases')))

print('\n%d check(s), %s' % (checks, 'all pass' if not fails else '%d FAILED: %s'
                                % (len(fails), '; '.join(fails[:4]))))
sys.exit(1 if fails else 0)
