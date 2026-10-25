# -*- coding: utf-8 -*-
"""Phase 2.9: the grand-vin check tells each wine from the grand vin, and
nothing else the reader does has moved.

    python tools/test-phase29.py

Name-level checks need nothing. The document checks need sources/ and
print MISSING without it.
"""
import glob
import hashlib
import importlib.util
import inspect
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr

fails = []
checks = 0


def says(name, ok, shown=''):
    global checks
    checks += 1
    if not ok:
        fails.append(name)
    print('%-4s %-62s %s' % ('ok' if ok else 'FAIL', name[:62], shown))


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


AG = load(ROOT + 'tools/audit-grand-marks.py', 'audit_grand')
src = subprocess.check_output(['git', 'show', '5778417:tools/sheetreader.py'],
                              cwd=ROOT)
tmp = tempfile.mkdtemp(prefix='p29-')
with open(os.path.join(tmp, 'sheetreader_base.py'), 'wb') as f:
    f.write(src)
OLD = load(os.path.join(tmp, 'sheetreader_base.py'), 'sheetreader_base')

WATCH = ['data/sources.json', 'data/fiches.js', 'data/cuvees.js',
         'data/field-src.js', 'data/cuvee-src.js', 'data/chateaux.js']
WATCH += ['data/evidence/' + f for f in sorted(os.listdir(
    ROOT + 'data/evidence'))]


def digest():
    return dict((p, hashlib.sha256(open(ROOT + p, 'rb').read()).hexdigest())
                for p in WATCH)


before = digest()
E = sr.estates(ROOT)


def others_of(e):
    ws = list(dict.fromkeys([w for w in (e.get('cuvees') or ()) if w]
                            + ([e['second']] if e.get('second') else [])))
    return [w for w in ws if w != e['name']]


def caught_by_name(eid, wine):
    """Every written form of the wine's name refused by the grand-vin
    check's name tests (whose_sheet names_only + the filename mark)."""
    e = E[eid]
    others = others_of(e)
    for fn in AG.forms(wine):
        v = sr.whose_sheet(None, fn, e['name'], e.get('cuvees') or (),
                           e.get('second'), e.get('cat'), names_only=True)
        if v:
            continue
        hit = False
        for o in [e.get('second')] + others:
            mk = o and sr.mark_of(o, e['name'], against_grand=True)
            if mk and sr.says_in_name(fn, mk):
                hit = True
                break
        if not hit:
            return False, fn
    return True, ''


# =============================================== the known case, exactly
print('LES HAUTS DU TERTRE')
g = E['du-tertre']['name']
says('old grand-vin mark: "les du tertre"',
     sr.mark_of('Les Hauts du Tertre', g) == 'les du tertre')
says('new grand-vin mark: "hauts du tertre"',
     sr.mark_of('Les Hauts du Tertre', g, against_grand=True)
     == 'hauts du tertre')
ok, fn = caught_by_name('du-tertre', 'Les Hauts du Tertre')
says('every written form of it is now refused as the grand vin', ok, fn)
says('the default mark (blend_of, check-data) is unchanged',
     sr.mark_of('Les Hauts du Tertre', g)
     == OLD.mark_of('Les Hauts du Tertre', g))

# ======================== the 12 previously uncaught, and the two G wines
print()
print('THE WINES THAT SLIPPED EVERY GRAND-VIN NAME TEST (PHASE 2.8 D1 + F)')
for eid, wine in (
        ('stem-chateau-bellefont-belcier', 'Les Tours de Belcier'),
        ('smith-haut-lafitte', 'Le Petit Haut Lafitte'),
        ('du-tertre', 'Les Hauts du Tertre'),
        ('stem-chateau-laroque', 'Les Tours de Laroque'),
        ('ducru-beaucaillou', 'La Croix de Beaucaillou'),
        ('smith-haut-lafitte', 'Les Hauts de Smith'),
        ('bourgeois-chateau-beaumont', 'Les Tours de Beaumont'),
        ('de-malle', 'Les Fleurs de Malle'),
        ('lynch-moussas', 'Les Hauts de Lynch-Moussas'),
        ('pontet-canet', 'Les Hauts de Pontet-Canet'),
        ('smith-haut-lafitte', 'Le Petit Haut Lafitte Blanc'),
        ('smith-haut-lafitte', 'Les Hauts de Smith Blanc'),
        ('guiraud', 'Le G de Château Guiraud'),
        ('guiraud', 'Le G de Château Guiraud Blanc')):
    if wine not in others_of(E[eid]):
        print('MISSING  %s / %s not listed' % (eid, wine))
        continue
    ok, fn = caught_by_name(eid, wine)
    says('%s: caught by name' % wine, ok, fn or
         sr.mark_of(wine, E[eid]['name'], against_grand=True))

# ======================================== weakened, and must stay caught
print()
print('ALREADY CAUGHT, STILL CAUGHT (PHASE 2.8 D2 AND OTHERS)')
for eid, wine, mark in (
        ('lynch-bages', 'Blanc de Lynch-Bages', 'blanc de lynch'),
        ('mouton', 'Le Petit Mouton de Mouton Rothschild', 'petit mouton'),
        ('dauzac', 'D de Dauzac Blanc', 'd de dauzac'),
        ('yquem', 'Y d’Yquem', 'y d yquem'),
        ('lynch-bages', 'Echo de Lynch-Bages', 'echo'),
        ('clinet', 'Fleur de Clinet', 'fleur de clinet')):
    e = E[eid]
    w = next((x for x in others_of(e) if sr.wset(x) == sr.wset(wine)), None)
    if not w:
        print('MISSING  %s / %s' % (eid, wine))
        continue
    mk = sr.mark_of(w, e['name'], against_grand=True)
    ok, fn = caught_by_name(eid, w)
    says('%s: mark %r, caught' % (wine[:30], mark), mk == mark and ok,
         '%r %s' % (mk, fn))

# ======================================================= collisions
print()
print('COLLISIONS THE NAME CANNOT SETTLE')
for eid, wine in (('durfort-vivens', 'Vivens'),
                  ('rauzan-segla', 'Ségla'),
                  ('troplong-mondot', 'Mondot')):
    says('%s: still no mark - an identity-model limit, not invented away'
         % wine, sr.mark_of(wine, E[eid]['name'], against_grand=True)
         is None)
says('Margaux du Chateau Margaux: mark unchanged',
     sr.mark_of('Margaux du Château Margaux', 'Château Margaux',
                against_grand=True)
     == OLD.mark_of('Margaux du Château Margaux', 'Château Margaux'))

# ============================================== grand-vin protection
print()
print('GRAND-VIN PROTECTION')
bad = []
for eid, e in E.items():
    for o in others_of(e):
        mk = sr.mark_of(o, e['name'], against_grand=True)
        if mk and sr.says(e['name'], mk):
            bad.append('%s: %r' % (o, mk))
says('no new mark is carried by its grand vin\'s own name (195 wines)',
     not bad, '; '.join(bad)[:40])
same, same_sib, n = 0, 0, 0
for eid, e in E.items():
    os_ = others_of(e)
    for o in os_:
        n += 1
        same += sr.mark_of(o, e['name']) == OLD.mark_of(o, e['name'])
        sib = [x for x in os_ if x != o]
        same_sib += (sr.mark_of(o, e['name'], siblings=sib)
                     == OLD.mark_of(o, e['name'], siblings=sib))
says('without against_grand every mark is the old one (blend_of etc.)',
     same == n, '%d/%d' % (same, n))
says('with siblings (second-wine mode) every mark is the old one',
     same_sib == n, '%d/%d' % (same_sib, n))
for fn_name in ('is_second_wine', 'blend_of', 'second_wine_verdict',
                'named_wines', 'whose_sheet', '_mark_of', 'wine_identity'):
    says('%s is byte-for-byte unchanged' % fn_name,
         inspect.getsource(getattr(OLD, fn_name))
         == inspect.getsource(getattr(sr, fn_name)))
# The CODE of the rule - docstring and comments aside, where examples
# are named on purpose - mentions no estate and no wine.
import ast
fns = [n for n in ast.parse(inspect.getsource(sr)).body
       if isinstance(n, ast.FunctionDef)
       and n.name in ('_grand_mark', '_own_tokens')]
for fn_node in fns:
    if (fn_node.body and isinstance(fn_node.body[0], ast.Expr)
            and isinstance(getattr(fn_node.body[0], 'value', None),
                           ast.Constant)):
        fn_node.body = fn_node.body[1:]
code = ' '.join(ast.unparse(n) for n in fns).lower()
names = set()
for e in E.values():
    names |= sr.wset(e['name'])
    for o in others_of(e):
        names |= sr.wset(o)
names -= sr.COMMON | sr.ARTICLES | sr.HOUSE_WORDS
hit = sorted(w for w in names if len(w) >= 4
             and __import__('re').search(r'(?<![a-z])%s(?![a-z])' % w, code))
says('the rule\'s code names no estate and no wine', len(fns) == 2
     and not hit, ', '.join(hit)[:40])


def real(eid, name, as_second=False):
    p = glob.glob(ROOT + 'sources/fiches/%s/%s' % (eid, name))
    if not p:
        return 'MISSING'
    e = E[eid]
    sr._TEXT.clear()
    v = sr.whose_sheet(p[0], name, e['name'], e['cuvees'], e['second'],
                       e['cat'], is_second=as_second)
    return 'ACCEPTED' if v is None else 'REFUSED'


print()
print('ON REAL DOCUMENTS')
for label, args, want in (
        ('Les Hauts du Tertre 2017 as the grand vin',
         ('du-tertre', 'Hauts-du-Tertre-2017-FT-FR.pdf'), 'REFUSED'),
        ('Les Hauts du Tertre 2017 as the second wine (unchanged)',
         ('du-tertre', 'Hauts-du-Tertre-2017-FT-FR.pdf', True), 'ACCEPTED'),
        ('Les Tours de Belcier 2015 as the grand vin',
         ('stem-chateau-bellefont-belcier',
          'FICHE-TECHNIQUE-LES-TOURS-DE-BELCIER-2015.pdf'), 'REFUSED'),
        ('G de Guiraud 2025 as the grand vin',
         ('guiraud', 'G-DE-GUIRAUD-2025-EN.pdf'), 'REFUSED'),
        ('Chateau Lynch-Bages 2008 as the grand vin (kept)',
         ('lynch-bages', 'Chateau-Lynch-Bages-2008-EN.pdf'), 'ACCEPTED')):
    got = real(*args)
    if got == 'MISSING':
        print('MISSING  %s (needs sources/)' % label)
        continue
    says(label, got == want, got)

# ================================================ determinism, safety
m1 = [(o, sr.mark_of(o, e['name'], against_grand=True))
      for e in E.values() for o in others_of(e)]
m2 = [(o, sr.mark_of(o, e['name'], against_grand=True))
      for e in E.values() for o in others_of(e)]
says('the rule is deterministic', m1 == m2, '%d marks' % len(m1))
says('nothing canonical and no evidence was touched by these tests',
     digest() == before)
# Against HEAD: canonical files and every COMMITTED evidence file. The
# store grows by design (a new version plus its index entry), so the
# whole directory is not the invariant.
committed = subprocess.check_output(
    ['git', 'ls-files', 'data/evidence/'], cwd=ROOT,
    stderr=subprocess.DEVNULL).decode().split()
out = subprocess.check_output(
    ['git', 'diff', '--name-only', 'HEAD', '--']
    + [p for p in WATCH if not p.startswith('data/evidence/')]
    + [p for p in committed if p.endswith('.jsonl')], cwd=ROOT,
    stderr=subprocess.DEVNULL).decode().strip()
says('canonical files and every committed evidence file match HEAD',
     out == '', 'clean' if not out else out.replace('\n', ' ')[:30])
# The copy of the old reader was needed until the last inspect.getsource above.
import shutil
shutil.rmtree(tmp, ignore_errors=True)

print('\n%d check(s), %s'
      % (checks, 'all pass' if not fails
         else '%d FAILED: %s' % (len(fails), '; '.join(fails[:4]))))
sys.exit(1 if fails else 0)
