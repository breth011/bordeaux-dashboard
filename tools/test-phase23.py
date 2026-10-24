# -*- coding: utf-8 -*-
"""Phase 2.3: a reader that can tell the Echo from the grand vin and the Blanc.

    python tools/test-phase23.py

Two defects fixed together - a second-wine mode that only meant "not
refused for naming the second wine", and marks that threw away "blanc"
- and these are the cases that prove the fix is general and has not
weakened anything to get there.

Mostly needs no archive: the identity layer is tested on the estates'
real wine names. The document-level matrix needs sources/ and says
MISSING on a fresh clone.
"""
import glob
import io
import json
import os
import re
import subprocess
import sys

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
    print('%-4s %-58s %s' % ('ok' if ok else 'FAIL', name[:58], shown))


E = sr.estates(ROOT)


def doc(eid, name):
    for where in ('fiches', 'pages'):
        hit = glob.glob(os.path.join(ROOT, 'sources', where, eid, name))
        if hit:
            return hit[0]
    return None


def verdict(eid, path, year, second_mode):
    e = E[eid]
    return sr.whose_sheet(path, os.path.basename(path), e['name'],
                          e['cuvees'], e['second'], e['cat'], year=year,
                          is_second=second_mode)


# ================================================ the Lynch-Bages matrix
print('Lynch-Bages: three wines, each asked as each')
print('-' * 72)
LB = [('Echo-de-Lynch-Bages-2008-EN.pdf', 2008, 'Echo'),
      ('Chateau-Lynch-Bages-2008-EN.pdf', 2008, 'grand vin'),
      ('Blanc-de-Lynch-Bages-2018-ENG.pdf', 2018, 'Blanc')]
# (document, asked as second?, expected)
MATRIX = [
    ('Echo', True, 'ACCEPT'),
    ('grand vin', True, 'REFUSE'),
    ('Blanc', True, 'REFUSE'),
    ('Echo', False, 'REFUSE'),
    ('Blanc', False, 'REFUSE'),
    ('grand vin', False, 'ACCEPT'),
]
paths = dict((who, (doc('lynch-bages', fn), yr)) for fn, yr, who in LB)
for who, as_second, want in MATRIX:
    p, yr = paths[who]
    asked = 'Echo' if as_second else 'grand vin'
    if not p:
        print('MISSING  %s sheet' % who)
        continue
    v = verdict('lynch-bages', p, yr, as_second)
    got = 'ACCEPT' if v is None else 'REFUSE'
    says('%s sheet asked as %s -> %s' % (who, asked, want), got == want,
         (v or {}).get('why', 'accepted')[:40])

# ======================= every distinct pair the old marks confused
print()
print('Distinct wines whose old marks collided - now told apart')
print('-' * 72)
# (estate, wine A, wine B): both real names from the estates' own lists.
PAIRS = [
    ('lynch-bages', 'Blanc de Lynch-Bages', 'Echo de Lynch-Bages'),
    ('margaux', 'Pavillon Blanc du Château Margaux',
     'Pavillon Rouge du Château Margaux'),
    ('cos-destournel', 'Pagodes de Cos Blanc', 'Pagodes de Cos'),
    ('guiraud', 'Petit Guiraud Blanc', 'Petit Guiraud'),
    ('olivier', "Le Dauphin d'Olivier Blanc", "Le Dauphin d'Olivier"),
    ('pichon-baron', 'Les Griffons de Pichon Baron Blanc',
     'Les Griffons de Pichon Baron'),
    ('haut-bages-liberal', 'La Chapelle de Haut-Bages Libéral',
     'La Chapelle de Bages'),
    ('bourgeois-chateau-dillon', 'La Comtesse Noire',
     'Secret de la Comtesse'),
    ('leoville-poyferre', 'Moulin Riche', 'Pavillon de Poyferré'),
]
for eid, a, b in PAIRS:
    e = E.get(eid)
    if not e or a not in e['cuvees'] or b not in e['cuvees']:
        print('MISSING  %s: %r / %r not both in its wine list' % (eid, a, b))
        continue
    wines = e['cuvees']
    na = sr.named_wines(a, e['name'], wines)
    nb = sr.named_wines(b, e['name'], wines)
    # Each name, read as text, is found to be that wine - and not the
    # other. Spelling variants of the same wine may come along with it.
    ok_a = a in na and b not in na
    ok_b = b in nb and a not in nb
    says('%s: %s' % (eid, a), ok_a, repr(na)[:40])
    says('%s: %s' % (eid, b), ok_b, repr(nb)[:40])

# The tenth estate of the Phase 2.2 table is Yquem, whose collision was
# Y d'Yquem against a note-carrying spelling of itself: one wine, so the
# right answer is that the two read as the same wine, not as two.
ey = E.get('yquem')
if ey:
    ys = [w for w in ey['cuvees'] if w.startswith('Y d')]
    says("yquem: the two spellings of Y d'Yquem are one wine",
         len(ys) == 2 and sr.wset(ys[0]) == sr.wset(ys[1]), repr(ys)[:40])

# ======================= the protections "blanc" was in COMMON for
print()
print('What COMMON was protecting still holds')
print('-' * 72)
e = E['lynch-bages']
m = sr.mark_of('Blanc de Lynch-Bages', e['name'],
               siblings=[x for x in e['cuvees'] if x != 'Blanc de Lynch-Bages'])
says("Blanc de Lynch-Bages marks with 'blanc' in it", 'blanc' in m, repr(m))
says("...and that mark is not inside the Echo's name",
     not sr.says('Echo de Lynch-Bages', m))
says("...and does not match a Sauvignon Blanc in prose",
     not sr.says('85% Sauvignon Blanc, 15% Semillon, fresh on the palate',
                 m))
# A colour word is never a mark on its own.
for eid in ('margaux', 'cos-destournel', 'guiraud', 'olivier',
            'pichon-baron', 'lynch-bages'):
    ee = E.get(eid) or {}
    for w in ee.get('cuvees') or ():
        mk = sr.mark_of(w, ee['name'],
                        siblings=[x for x in ee['cuvees'] if x != w])
        if mk and sr.packed(mk) in sr.COMMON:
            says('%s: %s marks as a bare common word' % (eid, w), False,
                 repr(mk))
says('no refined mark is a bare colour or common word', True)
# The case the old fallback was right about.
d = E.get('dauzac') or {}
if 'D de Dauzac Blanc' in (d.get('cuvees') or ()):
    m = sr.mark_of('D de Dauzac Blanc', d['name'])
    says("D de Dauzac Blanc still marks as 'd de dauzac' (no siblings)",
         m == 'd de dauzac', repr(m))
    says('...which its filename FT_D_DE_DAUZAC_2022_FR.pdf carries',
         sr.says('FT_D_DE_DAUZAC_2022_FR.pdf', m))
# With no siblings given, mark_of is exactly what it was.
says('mark_of without siblings is unchanged',
     sr.mark_of('Blanc de Lynch-Bages', e['name']) == 'de lynch bages')

# ======================= one wine written twice is still one wine
print()
print('A wine spelled two ways is not two wines')
print('-' * 72)
for eid, a, b in (('issan', "Blason d'Issan", 'Blason d’Issan'),
                  ('kirwan', 'Charmes de Kirwan', 'Les Charmes de Kirwan'),
                  ('cantenac-brown', 'BRIO de Cantenac Brown',
                   'BriO de Cantenac Brown')):
    says('%s: %r and %r have the same identifying words' % (eid, a, b),
         sr.wset(a) == sr.wset(b), repr(sorted(sr.wset(a))))

# ======================= Margaux, at document level
print()
print('Margaux: Pavillon Rouge is the second wine, Pavillon Blanc is not')
print('-' * 72)
pr = (glob.glob(os.path.join(ROOT, 'sources', 'pages', 'margaux',
                             '*pavillon-rouge*2018*')) or [None])[0]
pb = (glob.glob(os.path.join(ROOT, 'sources', 'pages', 'margaux',
                             '*pavillon-blanc*2018*')) or [None])[0]
gm = (glob.glob(os.path.join(ROOT, 'sources', 'pages', 'margaux',
                             '*grand-vin*2018*')) or [None])[0]
for label, p, want in (('Pavillon Rouge 2018', pr, 'ACCEPT'),
                       ('Pavillon Blanc 2018', pb, 'REFUSE'),
                       ('the grand vin 2018', gm, 'REFUSE')):
    if not p:
        print('MISSING  %s page' % label)
        continue
    v = verdict('margaux', p, 2018, True)
    says('%s asked as the second wine -> %s' % (label, want),
         ('ACCEPT' if v is None else 'REFUSE') == want,
         (v or {}).get('why', 'accepted')[:36])

# ======================= the group footer is still not evidence
print()
print('A group footer naming a property does not make the sheet its')
print('-' * 72)
gf = doc('stem-chateau-bellefont-belcier',
         'FICHE-PRODUIT-CHATEAU-LA-PATACHE-2019.pdf')
if not gf:
    print('MISSING  FICHE-PRODUIT-CHATEAU-LA-PATACHE-2019.pdf')
else:
    for second_mode in (False, True):
        v = verdict('stem-chateau-bellefont-belcier', gf, 2019,
                    second_mode)
        says('La Patache sheet refused as Bellefont-Belcier\'s %s'
             % ('second wine' if second_mode else 'grand vin'),
             v is not None, (v or {}).get('why', 'ACCEPTED')[:34])

# ======================= the Echo's data, as it must stay
print()
print('The Echo\'s definition is untouched')
print('-' * 72)
cuv = io.open(ROOT + 'data/cuvees.js', encoding='utf-8').read()
line = [l for l in cuv.split('\n') if l.startswith("'lynch-bages':[")]
entries = re.findall(r"\{([^}]*)\}", line[0]) if line else []
echo = [x for x in entries if "name:'Echo de Lynch-Bages'" in x]
says('the Echo is defined exactly once', len(echo) == 1, '%d' % len(echo))
says("...with slug echo-de-lynch-bages, role second, colour red",
     bool(echo) and "slug:'echo-de-lynch-bages'" in echo[0]
     and "role:'second'" in echo[0] and "colour:'red'" in echo[0])
says("chateaux.js still has second: 'Echo de Lynch-Bages'",
     E['lynch-bages']['second'] == 'Echo de Lynch-Bages')
says('the loader still merges the second wine into cuvees',
     E['lynch-bages']['second'] in E['lynch-bages']['cuvees'])
says('the 13 Echo records are untouched',
     len([l for l in cuv.split('\n')
          if l.startswith("'lynch-bages|echo-de-lynch-bages|")]) == 13)
man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))
filed_blanc = sum(1 for s in man['sheets']
                  if s.get('estate') == 'lynch-bages'
                  and (s.get('file') or '').startswith('Echo-de-Lynch')
                  and s.get('wine') == 'Blanc de Lynch-Bages')
says('no manifest correction made: the 50 Echo sheets still say Blanc',
     filed_blanc == 50, '%d' % filed_blanc)

# ======================= canonical safety
PROTECTED = ('data/sources.json', 'data/fiches.js', 'data/cuvees.js',
             'data/field-src.js', 'data/cuvee-src.js')
print()
try:
    out = subprocess.check_output(
        ['git', 'diff', '--name-only', 'HEAD', '--'] + list(PROTECTED),
        cwd=ROOT, stderr=subprocess.DEVNULL).decode().strip()
    says('canonical dataset files unmodified vs HEAD', out == '',
         'clean' if out == '' else out.replace('\n', ' ')[:24])
except Exception:
    print('MISSING  git unavailable')

print('\n%d check(s), %s'
      % (checks, 'all pass' if not fails
         else '%d FAILED: %s' % (len(fails), '; '.join(fails[:4]))))
sys.exit(1 if fails else 0)
