# -*- coding: utf-8 -*-
"""Phase 3.2: the normalization architecture, checked.

    python tools/test-phase32.py

Read-only. Four kinds of check:

  scope      Phase 3.1 is the input; nothing canonical, historical or
             proposed moved; no migration ran (no data file, no schema);
  design     the model resolves the three blockers and the brief's
             requirements: UNKNOWN role, temporal validity, observations
             that keep losers, ids apart from names, artifacts apart from
             paths, a decomposed manifest, a staged reversible migration,
             and no dependence on a complete wine universe;
  coverage   every field of every current structure, read at a842bb7, has
             a row in the current -> target mapping;
  fixtures   every worked example obeys the model's own rules, and every
             manifest row and hash it cites is the repository's.
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

BASE = 'a842bb7'
ARCH = 'docs/PHASE-3.2-NORMALIZATION-ARCHITECTURE.md'
DM = 'docs/PHASE-3.2-DATA-MODEL.md'
MODEL = 'docs/phase32-model.json'
FIX = 'docs/phase32-fixtures.json'
OWN = {ARCH, DM, MODEL, FIX, 'tools/test-phase32.py',
       # its reproduction checks skipped while a later phase's files exist
       'tools/test-phase31.py'}
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
mine = [h for h, s in log if s.startswith('Phase 3.2')]
changed = set()
for h in mine:
    changed |= set(git(['diff-tree', '--no-commit-id', '--name-only', '-r', h]).split())
if not mine:
    changed |= set(l[3:] for l in git(['status', '--porcelain=v1',
                                        '--untracked-files=all']).splitlines())

# ================================================================ scope
says('Phase 3.1 (a842bb7) is the declared input',
     git(['log', '-1', '--format=%s', BASE]).startswith('Phase 3.1')
     and subprocess.call(['git', 'merge-base', '--is-ancestor', BASE, 'HEAD'], cwd=ROOT) == 0
     and BASE in io.open(ROOT + ARCH, encoding='utf-8').read())
says('Phase 3.2 changed only its design documents and test', changed <= OWN,
     ', '.join(sorted(changed - OWN))[:40])
says('no migration ran: no data file, schema or app file changed',
     not any(f.startswith(('data/', 'assets/', 'index.html', 'service-worker.js'))
             or f.endswith(('.sql', '.db', '.sqlite')) for f in changed))
says('...canonical files, manifest and proposals unchanged', not (changed & set(CANON)))
says('...the evidence store verifies at 177,127 decisions, v1-v5, no v6',
     ST.verify() == [] and sum(1 for _ in ST.iter_rows()) == 177127
     and ST.versions() == [1, 2, 3, 4, 5]
     and not any(re.match(r'(decisions|provenance-failures)-v6', f)
                 for f in os.listdir(ROOT + 'data/evidence')))
says('the reader is still 7e8cfed1c24e', EV.reader_fingerprint() == '7e8cfed1c24e')
Es = sr.estates(ROOT)
S = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))['sheets']
says('no Phase 2 proposal applied: Terrasses, Echo (50 as Blanc), Murets',
     Es['stem-chateau-tour-saint-christophe']['second'] is None
     and sum(1 for r in S if r['estate'] == 'lynch-bages' and 'echo' in r['file'].lower()
             and r['wine'] == 'Blanc de Lynch-Bages') == 50
     and Es['caillou']['second'] == 'Les Erables de Caillou'
     and not any('murets' in str(w).lower() for w in Es['caillou']['cuvees']))
# The design files must not feed a page or any tool that writes data. A
# design generator that revises them into a later design document - Phase
# 3.4's build-phase34-model.py, whose output is under docs/ - is allowed:
# the whole-repository form of this check failed as soon as one existed.
page = io.open(ROOT + 'index.html', encoding='utf-8').read()
readers = [f for f in os.listdir(ROOT + 'tools') if f.endswith('.py') and f != 'test-phase32.py'
           and not f.startswith('test-')
           and re.search(r'phase32-(fixtures|model)', io.open(ROOT + 'tools/' + f, encoding='utf-8').read())]
writes_data = [f for f in readers
               if not re.search(r"^OUT = ROOT \+ 'docs/", io.open(ROOT + 'tools/' + f, encoding='utf-8').read(), re.M)]
says('the fixtures and model feed no page and no tool that writes data',
     'phase32-' not in page and not writes_data, ', '.join(writes_data))

# =============================================================== design
M = json.load(io.open(ROOT + MODEL, encoding='utf-8'))
F = json.load(io.open(ROOT + FIX, encoding='utf-8'))
E, EN = M['entities'], M['enums']
says('six layers plus cross-cutting, in order',
     [l['id'] for l in M['layers']] == ['IDENTITY', 'STATE', 'DOCUMENT', 'OBSERVATION',
                                        'RECONCILIATION', 'CANONICAL', 'CROSS_CUTTING'])
says('every entity named in a layer is defined, and vice versa',
     {e for l in M['layers'] for e in l['holds']} - {'Validity', 'TemporalBound'} == set(E))


def type_ok(t):
    base = t.split(':', 1)
    if base[0] == 'enum':
        return base[1] in EN
    if base[0] in ('ref', 'list') and len(base) > 1:
        targets = base[1].replace('ref:', '').split('|')
        return all(x in E or x in ('*', 'ref', 'text', 'Provenance', 'Placement', 'Observation')
                   for x in targets)
    return base[0] in ('id', 'text', 'bool', 'number', 'any', 'date', 'object', 'Validity',
                       'TemporalBound', 'list:text', 'list:ref', 'ref')


bad = [(n, f, d['type']) for n, e in E.items() for f, d in e['fields'].items() if not type_ok(d['type'])]
says('every field type is an enum, a value type or a defined entity', not bad, str(bad[:2]))
# B1
says('B1: WineRole holds UNKNOWN; the brief\'s six values are all representable',
     'UNKNOWN' in EN['WineRole']['values']
     and {'GRAND_VIN', 'SECOND_WINE', 'OTHER_CUVEE'} <= set(EN['WineRole']['values'])
     and {'DRY_WHITE', 'SWEET_WINE'} <= set(EN['WineRange']['values']))
says('B1: role sits on the relationship, apart from membership',
     E['RoleAssignment']['fields']['relationship']['type'] == 'ref:EstateWineRelationship'
     and 'role' not in E['EstateWineRelationship']['fields']
     and 'role' not in E['Wine']['fields'])
# B2
TEMPORAL = ('EstateWineRelationship', 'RoleAssignment', 'ClassificationMembership',
            'AppellationMembership', 'Appellation', 'NameRecord', 'Ownership', 'RoleAbsence',
            'ClassificationEdition', 'EstateLocation')
says('B2: every time-dependent entity requires a validity',
     all(E[n]['fields'].get('validity', {}).get('required') for n in TEMPORAL)
     and E['IdentityTransition']['fields']['at']['type'] == 'TemporalBound')
says('B2: bounds distinguish unknown, open, not applicable, exact, approximate',
     {'UNKNOWN', 'OPEN', 'NOT_APPLICABLE', 'EXACT', 'APPROXIMATE'} <= set(EN['BoundKind']['values'])
     and {'CALENDAR', 'VINTAGE'} == set(EN['BoundAxis']['values'])
     and 'basis is required whenever a value is given: no date without a source'
     in M['value_types']['TemporalBound']['rules'])
# B3
OBS = ('subject', 'field', 'raw_value', 'value', 'artifact', 'source', 'extraction',
       'confidence', 'observed_at', 'provenance')
REC = ('candidates', 'selected', 'rule', 'status', 'reason', 'resolver', 'decided_at')
says('B3: observations hold subject, field, raw and normalised value, document, method',
     all(f in E['Observation']['fields'] for f in OBS))
says('B3: reconciliations list every candidate; canonical values point at one',
     all(f in E['Reconciliation']['fields'] for f in REC)
     and E['Reconciliation']['fields']['candidates']['required']
     and E['CanonicalValue']['fields']['reconciliation']['required'])
says('B3: no first-writer-wins rule for new decisions (only LEGACY_-named)',
     all(r.startswith('LEGACY_') or 'FIRST' not in r for r in EN['ReconciliationRule']['values'])
     and 'MANUAL_UNSOURCED' in EN['CanonicalStatus']['values']
     and 'LEGACY_UNSOURCED' in EN['CanonicalStatus']['values'])
says('ids are minted and apart from names (no name field on Estate or Wine)',
     'name' not in E['Estate']['fields'] and 'name' not in E['Wine']['fields']
     and 'minted' in E['Estate']['identity'] and 'minted' in E['Wine']['identity']
     and E['IdentityMap']['identity'] == '(namespace, legacy_key)')
says('artifact identity is bytes; paths and URLs are placements',
     {'sha256', 'sha1'} <= set(E['Artifact']['fields'])
     and not any(f in E['Artifact']['fields'] for f in ('path', 'file', 'url', 'folder'))
     and E['Placement']['fields']['locator']['type'] == 'ref:Locator'
     and not E['Placement']['fields']['artifact']['required'])
dec = M['manifest_decomposition']['into']
says('the manifest decomposes into inventory, location, type, attribution, '
     'evidence and accepted relationship',
     {'Artifact', 'Locator+Placement', 'ArtifactAssessment', 'Attribution', 'EvidenceLink',
      'EstateWineRelationship+RoleAssignment'} == set(dec))
mig = M['migrations']
says('ten migration stages M0-M9, each with a reverse and a gate of defined invariants',
     [m['id'] for m in mig] == ['M%d' % i for i in range(10)]
     and all(m['reverse'] and m['gate'] and all(g in M['invariants'] for g in m['gate'])
             for m in mig))
says('stages before M8 are additive: they modify nothing that exists',
     all(m['modifies_existing'] is False for m in mig[:8]))
says('the twenty required invariants are defined (plus I21, I22)',
     ['I%d' % i for i in range(1, 23)] == list(M['invariants']))
says('a partial wine universe blocks nothing (I20, and absence is UNKNOWN)',
     'complete wine universe' in M['invariants']['I20']
     and 'absence of any RoleAssignment or RoleAbsence is UNKNOWN' in E['RoleAbsence']['note'])

# ============================================================== coverage
def chunk_fields(text, start):
    """Top-level field names of the records in a JS data file, a record
    being everything from one `start` match to the next, whether it sits
    on one line or several."""
    text = re.sub(r'/\*.*?\*/', ' ', text, flags=re.S)
    text = re.sub(r"'(?:[^'\\]|\\.)*'", "''", text)
    out = set()
    for chunk in re.split(start, text)[1:]:
        flat = chunk
        # Nested blend/press/pick objects and lists, replaced by a token
        # with no brace in it, so the record's own closing brace is the
        # first one left.
        for _ in range(3):
            flat = re.sub(r"\{[^{}]*\}", ' NESTED ', flat)
            flat = re.sub(r"\[[^\[\]]*\]", ' NESTED ', flat)
        out |= set(re.findall(r"(?:^|[,{\s])([a-z]+):", flat.split('}', 1)[0]))
    return out


def line_fields(text):
    return chunk_fields(text, r"(?m)^''\s*:\s*\{")


est = ''
for f in ('chateaux.js', 'sauternes.js', 'saintemilion.js', 'pomerol.js', 'graves.js',
          'libournais.js', 'batch2.js', 'batch3.js', 'batch4.js'):
    est += at_base('data/' + f)
estate_fields = chunk_fields(est, r"\{id:") | {'id'}
cv = at_base('data/cuvees.js')
STRUCT = {
    'estate files': estate_fields,
    'fiches.js': line_fields(at_base('data/fiches.js').split('BDX_FICHES', 1)[1]),
    'cuvees.js BDX_CUVEES': line_fields(cv.split('window.BDX_CUVEES', 1)[1]),
    'cuvees.js BDX_CUVEE_WINES': set(re.findall(r"[{,]([a-z]+):", cv.split('BDX_CUVEE_WINES', 1)[1]
                                                .split('window.BDX_CUVEES', 1)[0])),
    'sources.json': {k for s in json.loads(at_base('data/sources.json'))['sheets'] for k in s},
    'cellar.js': line_fields(at_base('data/cellar.js')),
    'terroir.js': line_fields(at_base('data/terroir.js')),
    'plantings.js': line_fields(at_base('data/plantings.js')),
    'overrides.js BDX_SCORES': line_fields(at_base('data/overrides.js').split('BDX_NOT_PRODUCED')[0]),
}
missing = []
for struct, fields in STRUCT.items():
    rows = [r for r in M['mapping'] if r['current'] == struct]
    text = ' '.join(r['field'] for r in rows)
    for f in sorted(fields):
        if not re.search(r'(?<![a-z])%s(?![a-z])' % re.escape(f), text):
            missing.append('%s.%s' % (struct, f))
says('every field of every current structure at a842bb7 has a mapping row',
     not missing and all(STRUCT.values()), ', '.join(missing[:4]) or
     '%d fields' % sum(len(v) for v in STRUCT.values()))
needed = ('field-src.js', 'cuvee-src.js', 'fiches-url.js', 'cuvee-url.js', 'ratings.js',
          'coords.js', 'websites.js', 'classifications.js', 'crubourgeois.js', 'cruartisan.js',
          'data/field-conflicts.jsonl', 'data/evidence/', 'overrides.js BDX_NOT_PRODUCED',
          'data/scope/')
have = {r['current'] for r in M['mapping']}
says('...and every keyed structure, the evidence, proposals and scope are mapped',
     all(any(n in h for h in have) for n in needed),
     ', '.join(n for n in needed if not any(n in h for h in have)))
says('every mapping row names a target, a rule and a risk',
     all(r.get('target') and r.get('rule') and r.get('risk') for r in M['mapping']))

# ============================================================ documents
arch = io.open(ROOT + ARCH, encoding='utf-8').read()
secs = [int(s) for s in re.findall(r'^## (\d+)\. ', arch, re.M)]
says('the architecture document has its 21 sections', secs == list(range(1, 22)), str(len(secs)))
says('...addresses B1, B2 and B3, and states the gate',
     all(b in arch for b in ('**B1**', '**B2**', '**B3**'))
     and arch.rstrip().endswith('**SAFE — NORMALIZATION ARCHITECTURE COMPLETE**'))
dm = io.open(ROOT + DM, encoding='utf-8').read()
gaps = []
for n, e in E.items():
    m = re.search(r'^### %s\n(.*?)(?=^### |\Z)' % re.escape(n), dm, re.M | re.S)
    if not m:
        gaps.append(n)
        continue
    for f in e['fields']:
        if not re.search(r'^\| %s \|' % re.escape(f), m.group(1), re.M):
            gaps.append('%s.%s' % (n, f))
says('the data-model document defines every entity and every field', not gaps,
     ', '.join(gaps[:4]))

# ============================================================== fixtures
recs = [r for c in F['cases'] for r in c['records']]
ids = {r['id']: r for r in recs if 'id' in r}
problems = []
for r in recs:
    ent = r['entity']
    if ent not in E:
        problems.append('unknown entity ' + ent)
        continue
    fields = E[ent]['fields']
    for k in r:
        if k != 'entity' and k not in fields:
            problems.append('%s.%s not in model' % (ent, k))
    for k, d in fields.items():
        if d.get('required') and k not in r:
            problems.append('%s %s lacks %s' % (ent, r.get('id', ''), k))
        if k in r and d['type'].startswith('enum:') and r[k] is not None:
            if r[k] not in EN[d['type'][5:]]['values']:
                problems.append('%s.%s=%s' % (ent, k, r[k]))
says('every fixture record fits its entity: known fields, required fields, valid enums',
     not problems, '; '.join(problems[:3]))
FORMAT = {'DAY': r'^\d{4}-\d{2}-\d{2}$', 'MONTH': r'^\d{4}-\d{2}$', 'YEAR': r'^\d{4}$',
          'DECADE': r'^\d{4}s$'}


def bound_problems(b, where, end):
    out = []
    k = b['kind']
    if k not in EN['BoundKind']['values'] or b.get('axis') not in EN['BoundAxis']['values']:
        return [where + ' bad kind/axis']
    valued = k in ('EXACT', 'APPROXIMATE', 'NO_LATER_THAN', 'NO_EARLIER_THAN')
    if valued != ('value' in b):
        out.append(where + ' value presence')
    if valued and not b.get('basis'):
        out.append(where + ' a date without a basis')
    if k == 'OPEN' and not end:
        out.append(where + ' OPEN as a start')
    if valued:
        if b['axis'] == 'VINTAGE':
            if not (isinstance(b['value'], int) and b.get('precision') == 'VINTAGE'):
                out.append(where + ' vintage bound')
        elif not re.match(FORMAT.get(b.get('precision'), r'^$'), str(b['value'])):
            out.append(where + ' precision/value mismatch')
    return out


tp = []
for r in recs:
    for key in ('validity', 'observed'):
        if key in r:
            tp += bound_problems(r[key]['valid_from'], '%s.%s.from' % (r.get('id'), key), False)
            tp += bound_problems(r[key]['valid_to'], '%s.%s.to' % (r.get('id'), key), True)
            if not r[key].get('as_of'):
                tp.append('%s no as_of' % r.get('id'))
    if 'at' in r and isinstance(r['at'], dict):
        tp += bound_problems(r['at'], '%s.at' % r.get('id'), False)
says('every bound obeys the temporal rules (no date without a basis)', not tp, '; '.join(tp[:3]))
ID_RE = re.compile(r'^[a-z]{2,3}_\d{3}$')
unres = []
for r in recs:
    for k, v in r.items():
        for x in (v if isinstance(v, list) else [v]):
            if isinstance(x, str) and ID_RE.match(x) and x not in ids:
                unres.append(x)
says('every fixture reference resolves; ids carry no names',
     not unres and all(ID_RE.match(i) for i in ids), ', '.join(sorted(set(unres))[:4]))


def of(entity, **kw):
    return [r for r in recs if r['entity'] == entity and all(r.get(k) == v for k, v in kw.items())]


rel1 = ids.get('rel_001', {})
says('C1/C2: established relationships whose role is UNKNOWN (Terrasses, both Murets)',
     rel1.get('status') == 'ESTABLISHED'
     and any(r['relationship'] == 'rel_001' for r in of('RoleAssignment', role='UNKNOWN'))
     and all(any(r['relationship'] == x for r in of('RoleAssignment', role='UNKNOWN'))
             for x in ('rel_002', 'rel_003')))
says('C1/C2: the corpus role wording stays an observation, DEFERRED, not applied',
     all(ids[x]['status'] == 'DEFERRED' and ids[x]['selected'] is None for x in ('rec_001', 'rec_002')))
rec3 = ids['rec_003']
vals = {ids[c]['value'] for c in rec3['candidates']}
cvs = of('CanonicalValue')
says('C6: both disagreeing observations kept; the canonical value points at the reconciliation',
     len(rec3['candidates']) == 3 and vals == {80, 50}
     and any(c['reconciliation'] == 'rec_003' and c['status'] == 'LEGACY_RECORD_SOURCE_ONLY'
             for c in cvs))
says('C3: Echo from vintage 2008 and Averous to no later than 2007, on the VINTAGE axis',
     ids['rel_006']['validity']['valid_from'] == {'kind': 'EXACT', 'axis': 'VINTAGE', 'value': 2008,
                                                  'precision': 'VINTAGE', 'basis': 'prv_020'}
     and ids['rel_007']['validity']['valid_to']['kind'] == 'NO_LATER_THAN'
     and ids['rel_007']['validity']['valid_from']['kind'] == 'UNKNOWN'
     and ids['itr_001']['certainty'] == 'UNRESOLVED')
says('C4: Mouton\'s membership splits at 1973-06 (MONTH); its earlier rank is UNKNOWN',
     ids['cme_001']['rank_status'] == 'UNKNOWN'
     and ids['cme_001']['validity']['valid_to']['value'] == '1973-06'
     and ids['cme_002']['validity']['valid_from']['precision'] == 'MONTH')
loc = {}
for p in of('Placement'):
    loc.setdefault(p['locator']['value'], set()).add(p['artifact'])
art_loc = {}
for p in of('Placement'):
    art_loc.setdefault(p['artifact'], set()).add(p['locator']['value'])
says('C7: one path holds two artifacts; one artifact sits at two paths',
     any(len(v - {None}) >= 2 for v in loc.values())
     and any(k and len(v) >= 2 for k, v in art_loc.items()))
amb = [r for r in of('LegacyDocumentReference') if r['resolution'] == 'AMBIGUOUS']
says('C7: an ambiguous legacy filename resolves to candidates, not to one',
     amb and all(len({ids[c]['artifact'] for c in r['candidates']}) >= 2 for r in amb))
says('C7: the unreadable (no artifact) and the unattributed are records',
     of('Placement', status='MISSING', artifact=None) and of('Placement', status='NAME_MISMATCH')
     and of('Attribution', status='UNATTRIBUTED'))
says('C8: legacy ids and evidence rows resolve through IdentityMap; sameness stays UNRESOLVED',
     of('IdentityMap', legacy_key='bourgeois-chateau-castera', status='ACTIVE')
     and of('EvidenceLink', estate='est_011')
     and of('IdentityTransition', kind='POSSIBLY_SAME', certainty='UNRESOLVED')
     and of('RoleAbsence'))

# fixture facts against the repository
SA = json.loads(at_base('data/sources.json'))['sheets']
wrong = []
for p in of('Placement'):
    row = p.get('legacy_manifest_row')
    if row is None or p['locator']['kind'] != 'LOCAL_PATH':
        continue
    s = SA[row]
    path = (s['folder'] if s['folder'].startswith('pages') else 'fiches/' + s['folder']) + '/' + s['file']
    a = ids.get(p['artifact']) if p['artifact'] else None
    if path != p['locator']['value'] or (a and a.get('sha1') and a['sha1'] != s['sha1']):
        wrong.append(str(row))
says('every manifest row a fixture cites has that path and those bytes', not wrong,
     ', '.join(wrong[:4]))
v5 = {}
for d in ST.iter_rows([5]):
    if d.get('read'):
        v5.setdefault(d['read']['sha256'], d['manifest_sha1'])
shas = [a for a in of('Artifact') if a.get('sha256')]
says('every sha256 a fixture cites was hashed by v5, against the same sha1',
     all(a['sha256'] in v5 and (not a.get('sha1') or v5[a['sha256']] == a['sha1']) for a in shas),
     '%d artifacts' % len(shas))

print('\n%d check(s), %s'
      % (checks, 'all pass' if not fails
         else '%d FAILED: %s' % (len(fails), '; '.join(fails[:4]))))
sys.exit(1 if fails else 0)
