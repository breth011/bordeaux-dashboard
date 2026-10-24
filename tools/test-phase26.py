# -*- coding: utf-8 -*-
"""Phase 2.6: "a second wine" is a role, "this second wine" is an
identity, and the reader now tells them apart.

    python tools/test-phase26.py

Three kinds of check. Unit checks on names and phrases, which need
nothing. Fixture pages, written to a temporary directory, for the
document-level rules. And the real documents of the Phase 2.4 cases,
where sources/ is present (MISSING otherwise).
"""
import glob
import importlib.util
import inspect
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr
import evidence as EV

fails = []
checks = 0


def says(name, ok, shown=''):
    global checks
    checks += 1
    if not ok:
        fails.append(name)
    print('%-4s %-62s %s' % ('ok' if ok else 'FAIL', name[:62], shown))


def code(v):
    return 'ACCEPTED' if v is None else EV.code_for(v.get('why'))[0]


# ================================================================ names
print('NAMES BUILT ON THE ESTATE\'S NAME')
cases = [
    ('Barsac LES MURETS DE CAILLOU 2023', 'Château Caillou',
     ['Les Erables de Caillou'], ('unlisted', 'LES MURETS DE CAILLOU')),
    ('Echo de Lynch-Bages 2008', 'Château Lynch-Bages',
     ['Echo de Lynch-Bages', 'Blanc de Lynch-Bages'],
     ('listed', 'Echo de Lynch-Bages')),
    ('Blanc de Lynch-Bages 2019', 'Château Lynch-Bages',
     ['Echo de Lynch-Bages', 'Blanc de Lynch-Bages'],
     ('listed', 'Blanc de Lynch-Bages')),
    ('Grand Vin de Château Latour', 'Château Latour',
     ['Les Forts de Latour'], ('estate', None)),
    ('Les Forts de Latour 2016', 'Château Latour',
     ['Les Forts de Latour'], ('listed', 'Les Forts de Latour')),
    ('lacroix-martillac-rouge-2019', 'Château Latour-Martillac',
     ['Lagrave-Martillac'], ('unlisted', 'lacroix-martillac')),
    ('lagrave-martillac-blanc-2020', 'Château Latour-Martillac',
     ['Lagrave-Martillac'], ('listed', 'Lagrave-Martillac')),
    ('FT-PEDESCLAUX-2025_FR', 'Château Pédesclaux',
     ['Fleur de Pédesclaux'], ('estate', None)),
    ('Second vin du Château Belgrave', 'Château Belgrave',
     ['Diane de Belgrave'], ('estate', None)),
    ('Le Petit Mouton de Mouton Rothschild', 'Château Mouton Rothschild',
     ['Le Petit Mouton de Mouton Rothschild'],
     ('listed', 'Le Petit Mouton de Mouton Rothschild')),
]
for text, grand, wines, want in cases:
    # A filename or an address is read as one (no spaces, all one
    # case); a title as prose.
    prose = ' ' in text
    names = [n for n, _ in sr.wine_shaped_names(text, grand, prose=prose)]
    got = [sr.classify_name(n, grand, wines) for n in names]
    if want[0] == 'estate':
        # The estate talking about itself names no wine at all.
        ok = all(k in ('estate', 'generic') for k, _ in got)
        label = 'no wine'
    else:
        ok = want in got
        label = want[0]
    says('%s -> %s' % (text[:34], label), ok, str(got)[:44])
says('"Baron Philippe de Rothschild" is not a Mouton wine',
     sr.wine_shaped_names('Baron Philippe de Rothschild SA',
                          'Château Mouton Rothschild') == [])
says('a name does not run across "et"',
     not any(' et ' in n for n, _ in sr.wine_shaped_names(
         'Château Haut-Bages Libéral et Lynch-Bages', 'Château Lynch-Bages')))
# The prose that the first draft of this phase read as wine names, on
# real Phase 2.6 dry-run titles: none is a wine.
for text, grand in (('la fois à Branaire-Ducru', 'Château Branaire-Ducru'),
                    ('fille unique du fondateur de Branaire-Ducru',
                     'Château Branaire-Ducru'),
                    ('Découvrez Giscours', 'Château Giscours'),
                    ('Station météo de Gruaud Larose',
                     'Château Gruaud Larose'),
                    ('terroir de Graves à Fieuzal', 'Château de Fieuzal'),
                    ('Château Bahans Haut-Brion', 'Château Haut-Brion')):
    says('prose is not a wine name: "%s"' % text[:34],
         sr.wine_shaped_names(text, grand) == [],
         str(sr.wine_shaped_names(text, grand))[:30])
# A listed wine with something in front of it is still that wine.
for text, grand, wines, want in (
        ('France Castelnau de Suduiraut', 'Château Suduiraut',
         ['Castelnau de Suduiraut'], 'Castelnau de Suduiraut'),
        ('OLIVIER BERNARD ESPRIT DE CHEVALIER', 'Domaine de Chevalier',
         ['Esprit de Chevalier'], 'Esprit de Chevalier'),
        ('FT_LABASTIDE-DAUZAC-2013', 'Château Dauzac',
         ['La Bastide Dauzac'], 'La Bastide Dauzac')):
    got = [sr.classify_name(n, grand, wines)
           for n, _ in sr.wine_shaped_names(text, grand, prose=False)]
    says('"%s" is the listed %s' % (text[:24], want),
         ('listed', want) in got, str(got)[:34])
says('"Grand Vin" in front of the estate is furniture, not a wine',
     sr.classify_name('Grand Vin de Lynch-Bages', 'Château Lynch-Bages',
                      ['Echo de Lynch-Bages'])[0] in ('estate', 'generic'))

# ============================================================ fixtures
tmp = tempfile.mkdtemp(prefix='p26-')


def page(name, url, body):
    # A crawled page as the crawler writes it: the URL, the browser-tab
    # <title> (which the reader skips), then the page.
    p = os.path.join(tmp, name)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(url + '\n' + 'Exemple - tab title\n' + body + '\n')
    return p


GRAND, SECOND = 'Château Exemple', 'Les Ailes d’Exemple'
OTHERS = ['Les Ailes d’Exemple', 'Exemple Blanc']


def ask(p, second=SECOND, others=OTHERS, as_second=True):
    sr._TEXT.clear()
    return sr.whose_sheet(p, os.path.basename(p), GRAND, others, second,
                          'red', is_second=as_second)


try:
    print()
    print('PHRASES')
    p_this = page('a.txt', 'https://exemple.fr/vins/note',
                  'SECOND VIN DU CHATEAU EXEMPLE 2020. Robe grenat.')
    p_both = page('b.txt', 'https://exemple.fr/vins/carte',
                  'CARTOGRAPHIE DU PREMIER ET SECOND VIN 2020. Parcelles.')
    p_both_en = page('c.txt', 'https://exemple.fr/en/map',
                     'Map of the first and second wines 2020.')
    p_label = page('d.txt', 'https://exemple.fr/fr/chateau',
                   'Second vin : Les Ailes d’Exemple. Superficie 40 ha.')
    p_none = page('e.txt', 'https://exemple.fr/fr/chateau',
                  'Château Exemple 2020. Robe grenat, nez de cassis.')
    says('"Second vin du Château X" -> this',
         sr.second_wine_claim(p_this) == 'this')
    says('"premier et second vin" -> both (the "et" now read right)',
         sr.second_wine_claim(p_both) == 'both')
    says('"first and second wines" -> both',
         sr.second_wine_claim(p_both_en) == 'both')
    says('"Second vin : <name>" is a label, not a claim',
         sr.second_wine_claim(p_label) is None)
    says('no phrase -> None', sr.second_wine_claim(p_none) is None)
    says('is_second_wine keeps its generic answers (this / both)',
         sr.is_second_wine(p_this) is True
         and sr.is_second_wine(p_both) is True, 'unchanged contract')

    print()
    print('DOCUMENTS')
    v = ask(p_this)
    says('generic "second vin du Château X", one second wine -> ACCEPT',
         v is None, code(v))
    v = ask(p_this, as_second=False)
    says('...and the same document as the grand vin -> REFUSE',
         v is not None, code(v))
    p_gen = page('f.txt', 'https://exemple.fr/en/page',
                 'News from the estate. Produced in small quantities, '
                 'this second wine is a gateway to La Chapelle d’Exemple.')
    v = ask(p_gen)
    says('generic "this second wine" naming an unlisted wine -> REFUSE',
         code(v) == 'UNLISTED_WINE', code(v))
    p_mur = page('g.txt', 'https://exemple.fr/fr/fiche',
                 'LES MURETS D’EXEMPLE 2023 Second Vin blanc sec du '
                 'Château Exemple.')
    v = ask(p_mur)
    says('"Les Murets d\'Exemple ... second vin", asked as the listed '
         'second -> REFUSE', code(v) == 'UNLISTED_WINE', code(v))
    v = ask(p_mur, second='Les Murets d’Exemple',
            others=OTHERS + ['Les Murets d’Exemple'])
    says('...asked as Les Murets itself (were it listed) -> ACCEPT',
         v is None, code(v))
    says('...and the reader names it without adding it anywhere',
         sr.wine_identity(p_mur, os.path.basename(p_mur), GRAND,
                          OTHERS)['title_unlisted']
         == ['LES MURETS D’EXEMPLE'])
    v = ask(p_both)
    says('"premier et second vin" alone -> not accepted as the second',
         v is not None, code(v))
    p_url = page('h.txt', 'https://exemple.fr/vins/les-ailes-d-exemple-2020',
                 'LA REVE D’EXEMPLE 2020. Robe grenat.')
    v = ask(p_url)
    says('URL names the second wine, title names another wine -> REFUSE',
         code(v) == 'UNLISTED_WINE', code(v))
    p_two = page('i.txt', 'https://exemple.fr/vins/'
                          'les-ailes-d-exemple-2020/la-reve-d-exemple-2019',
                 'Image 2019-min.')
    v = ask(p_two)
    says('URL names the second wine AND another wine -> AMBIGUOUS',
         code(v) == 'AMBIGUOUS_WINE', code(v))
    p_ok = page('j.txt', 'https://exemple.fr/vins/les-ailes-d-exemple-2020',
                'LES AILES D’EXEMPLE 2020. Robe grenat.')
    v = ask(p_ok)
    says('URL and title both name the second wine -> ACCEPT',
         v is None, code(v))
    p_gv = page('k.txt', 'https://exemple.fr/vins/chateau-exemple-2020',
                'CHÂTEAU EXEMPLE 2020. Robe grenat.')
    v = ask(p_gv)
    says('grand-vin document as the second -> REFUSE', v is not None,
         code(v))
    p_bl = page('l.txt', 'https://exemple.fr/vins/exemple-blanc-2020',
                'EXEMPLE BLANC 2020. Robe or pâle.')
    v = ask(p_bl)
    says('Blanc document as the second -> REFUSE', v is not None, code(v))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ===================================================== shared contracts
print()
print('THE GENERIC CONTRACT, AND ITS OTHER CALLERS')
try:
    src = subprocess.check_output(
        ['git', 'show', '4370382:tools/sheetreader.py'], cwd=ROOT,
        stderr=subprocess.DEVNULL)
except Exception:
    src = None
if src is None:
    print('MISSING  git object 4370382:tools/sheetreader.py')
else:
    d = tempfile.mkdtemp(prefix='p26b-')
    with open(os.path.join(d, 'sheetreader_base.py'), 'wb') as f:
        f.write(src)
    spec = importlib.util.spec_from_file_location(
        'sheetreader_base', os.path.join(d, 'sheetreader_base.py'))
    OLD = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(OLD)
    changed = sorted(
        n for n, o in vars(sr).items()
        if inspect.isfunction(o) and o.__module__ == sr.__name__
        and hasattr(OLD, n) and inspect.getsource(getattr(OLD, n))
        != inspect.getsource(o))
    # Phase 2.9 changed three more on purpose, for the GRAND-VIN path
    # only: mark_of gained against_grand (default off), names_another_wine
    # passes it when it has no siblings, abbreviates_other_wine gained a
    # comment. What this suite protects is that second-wine mode and the
    # blend reader see exactly the marks they saw - checked below by
    # behaviour, for every wine, instead of by source.
    PHASE29 = {'mark_of', 'names_another_wine', 'abbreviates_other_wine'}
    says('the existing functions changed are second_wine_verdict and '
         'Phase 2.9\'s',
         set(changed) <= {'second_wine_verdict'} | PHASE29,
         ', '.join(changed))
    for fn in ('is_second_wine', 'blend_of', 'whose_sheet', 'named_wines'):
        says('%s is byte-for-byte the Phase 2.5 one' % fn,
             inspect.getsource(getattr(OLD, fn))
             == inspect.getsource(getattr(sr, fn)))
    E0 = sr.estates(ROOT)
    n = same = 0
    for e in E0.values():
        ws = [w for w in dict.fromkeys((e.get('cuvees') or [])
                                       + [e.get('second')]) if w
              and w != e['name']]
        for w in ws:
            sib = [x for x in ws if x != w]
            n += 2
            same += sr.mark_of(w, e['name']) == OLD.mark_of(w, e['name'])
            same += (sr.mark_of(w, e['name'], siblings=sib)
                     == OLD.mark_of(w, e['name'], siblings=sib))
    says('mark_of gives second-wine mode and blend_of the Phase 2.5 marks',
         same == n, '%d/%d' % (same, n))
    shutil.rmtree(d, ignore_errors=True)
callers = []
for f in glob.glob(ROOT + 'tools/*.py'):
    t = open(f, encoding='utf-8').read()
    if 'is_second_wine(' in t:
        callers.append(os.path.basename(f))
says('is_second_wine callers are the known ones',
     sorted(callers) == sorted(['sheetreader.py', 'read-sheets.py',
                                'test-reader.py', 'diagnose-second-mode.py',
                                'trace-second-wine-cases.py',
                                'test-phase26.py']),
     ', '.join(sorted(callers)))

# ========================================================= real documents
print()
print('THE PHASE 2.4 CASES, ON THEIR OWN DOCUMENTS')
E = sr.estates(ROOT)


def real(eid, sub, fn, yr, as_second=True, second=None, extra=()):
    p = os.path.join(ROOT, 'sources', *sub.split('/'), fn)
    if not os.path.exists(p):
        return 'MISSING'
    e = E[eid]
    sr._TEXT.clear()
    v = sr.whose_sheet(p, fn, e['name'], list(e['cuvees']) + list(extra),
                       second or e['second'], e['cat'], year=yr,
                       is_second=as_second)
    return code(v)


MATRIX = [
    ('Belgrave 2023 as Diane de Belgrave', 'ACCEPTED',
     ('belgrave', 'fiches/belgrave', 'belgrave-2023-fc11b611.pdf', 2023)),
    ('Belgrave 2023 (Diane) as the grand vin', 'REFUSED',
     ('belgrave', 'fiches/belgrave', 'belgrave-2023-fc11b611.pdf', 2023,
      False)),
    ('Lagrave/Lacroix page as Lagrave-Martillac 2020', 'REFUSED',
     ('latour-martillac', 'pages/latour-martillac',
      '2020__agrave-martillac-blanc-2020-lacroix-martillac-rouge-2019-min.txt',
      2020)),
    ('Lagrave/Lacroix page as Lagrave-Martillac 2019', 'REFUSED',
     ('latour-martillac', 'pages/latour-martillac',
      '2020__agrave-martillac-blanc-2020-lacroix-martillac-rouge-2019-min.txt',
      2019)),
    ('Caillou Les Murets as Les Erables', 'UNLISTED_WINE',
     ('caillou', 'fiches/caillou',
      'Fiche-technique-FR-MURETS-BLANCS-2023-AOC-Bordeaux-Blanc.pdf', 2023)),
    ('Caillou Les Murets as Les Murets (were it listed)', 'ACCEPTED',
     ('caillou', 'fiches/caillou',
      'Fiche-technique-FR-MURETS-BLANCS-2023-AOC-Bordeaux-Blanc.pdf', 2023,
      True, 'Les Murets de Caillou', ('Les Murets de Caillou',))),
    ('Pedesclaux both-wines map as Fleur de Pedesclaux', 'REFUSED',
     ('pedesclaux', 'fiches/pedesclaux',
      'FT-PEDESCLAUX-2025_FR_compressed.pdf', 2025)),
    ('La Mission "this second wine" page as Le Clarence', 'REFUSED',
     ('haut-brion', 'pages/la-mission-haut-brion',
      '2019__-mission-haut-brion-la-chapelle-de-la-mission-haut-brion2019.txt',
      2019)),
    ('Lynch-Bages grand-vin sheet as the Echo', 'REFUSED',
     ('lynch-bages', 'fiches/lynch-bages', 'Chateau-Lynch-Bages-2008-EN.pdf',
      2008)),
    ('Echo sheet as the Echo', 'ACCEPTED',
     ('lynch-bages', 'fiches/lynch-bages', 'Echo-de-Lynch-Bages-2008-EN.pdf',
      2008)),
    ('Echo sheet as the grand vin', 'REFUSED',
     ('lynch-bages', 'fiches/lynch-bages', 'Echo-de-Lynch-Bages-2008-EN.pdf',
      2008, False)),
]
blanc = glob.glob(ROOT + 'sources/fiches/lynch-bages/Blanc-de-Lynch-Bages-*')
if blanc:
    fn = os.path.basename(blanc[0])
    MATRIX.append(('Blanc de Lynch-Bages sheet as the Echo', 'REFUSED',
                   ('lynch-bages', 'fiches/lynch-bages', fn, None)))
for label, want, args in MATRIX:
    got = real(*args)
    if got == 'MISSING':
        print('MISSING  %s (needs sources/)' % label)
        continue
    ok = got == want or (want == 'REFUSED' and got != 'ACCEPTED')
    says(label, ok, got)

# ================================================== canonical safety
cu = open(ROOT + 'data/cuvees.js', encoding='utf-8').read()
says('no unlisted wine was added to the canonical lists',
     'Murets' not in cu and 'Lacroix-Martillac' not in cu)
PROTECTED = ('data/sources.json', 'data/fiches.js', 'data/cuvees.js',
             'data/field-src.js', 'data/cuvee-src.js')
try:
    out = subprocess.check_output(
        ['git', 'diff', '--name-only', 'HEAD', '--'] + list(PROTECTED)
        # the historical evidence; a later version is appended beside it
        + ['data/evidence/decisions-v%d.jsonl' % v for v in (1, 2, 3)],
        cwd=ROOT, stderr=subprocess.DEVNULL).decode().strip()
except Exception:
    out = None
print()
if out is None:
    print('MISSING  git unavailable')
else:
    says('canonical files and v1-v3 evidence unmodified vs HEAD',
         out == '', 'clean' if out == '' else out.replace('\n', ' ')[:28])

print('\n%d check(s), %s'
      % (checks, 'all pass' if not fails
         else '%d FAILED: %s' % (len(fails), '; '.join(fails[:4]))))
sys.exit(1 if fails else 0)
