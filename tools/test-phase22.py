# -*- coding: utf-8 -*-
"""Phase 2.2: what must stay true, and the two defects, named.

    python tools/test-phase22.py

Phase 2.2 was planned as "remove the Echo's double listing from the
data". There is no double listing in the data - the Echo appears once
in BDX_CUVEE_WINES, correctly marked role:'second' - and removing it
would delete the wine's definition, which the cuvee reader and the app
both need, while leaving the refusal in place because the loader
re-adds the second wine from chateaux.js.

So the first job of these tests is to make that wrong fix impossible to
apply quietly: they assert the Echo is defined exactly once, as the
second wine, and that the loader's merge - which the grand-vin
evaluation depends on - is still there.

The second job is to state the two real defects, which are in the
reader. They are reported as KNOWN DEFECT lines and do not fail the
suite, because they are the current, documented state and fixing them
needs a decision about reader-wide scope. When either is fixed, its
line flips to "fixed" and the matching assertion below should be
tightened into a real check.

Reads only committed data, plus two documents from sources/ where
present.
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
    print('%-4s %-56s %s' % ('ok' if ok else 'FAIL', name[:56], shown))


def known(name, still_broken, shown=''):
    """A defect that is documented and not yet fixed. Never fails."""
    print('%-4s %-56s %s' % ('KNOWN' if still_broken else 'fixed',
                             name[:56], shown))


E = sr.estates(ROOT)
e = E['lynch-bages']
cuv = io.open(ROOT + 'data/cuvees.js', encoding='utf-8').read()

# ============================== what must stay true about the data
line = [l for l in cuv.split('\n') if l.startswith("'lynch-bages':[")]
says('BDX_CUVEE_WINES has a lynch-bages entry', bool(line))
if line:
    entries = re.findall(r"\{([^}]*)\}", line[0])
    echo = [x for x in entries if "name:'Echo de Lynch-Bages'" in x]
    says('the Echo is defined exactly once', len(echo) == 1,
         '%d' % len(echo))
    says('...as the second wine',
         bool(echo) and "role:'second'" in echo[0])
    says('...and keeps its slug', bool(echo)
         and "slug:'echo-de-lynch-bages'" in echo[0])
    says('the Blanc is still a separate wine',
         any("name:'Blanc de Lynch-Bages'" in x and "role:'other'" in x
             for x in entries))
says('chateaux.js names the Echo as the second wine',
     e.get('second') == 'Echo de Lynch-Bages', repr(e.get('second')))
# The loader puts the second wine into `cuvees` ON PURPOSE: that is how
# a second wine's sheet is refused when the grand vin is evaluated.
says('the loader merges the second wine into cuvees (by design)',
     e['second'] in e['cuvees'])
says('existing Echo records are untouched (13)',
     len([l for l in cuv.split('\n')
          if l.startswith("'lynch-bages|echo-de-lynch-bages|")]) == 13)

# ================================ what must stay true about the reader
def find(name):
    hit = glob.glob(os.path.join(ROOT, 'sources', '*', 'lynch-bages', name))
    return hit[0] if hit else None


p_echo = find('Echo-de-Lynch-Bages-2008-EN.pdf')
p_lb89 = find('Chateau-Lynch-Bages-1989-FR.pdf')
args = (e['name'], e['cuvees'], e['second'], e['cat'])

if not p_echo:
    print('MISSING  Echo-de-Lynch-Bages-2008-EN.pdf (needs sources/)')
else:
    fn = os.path.basename(p_echo)
    # The grand-vin guard must keep refusing the Echo's sheet: if a fix
    # broke this, the Echo's data would start landing on the grand vin.
    gv = sr.whose_sheet(p_echo, fn, *args, year=2008)
    says('an Echo sheet is refused as the GRAND VIN', gv is not None,
         (gv or {}).get('why', '')[:40])

if p_lb89:
    fn = os.path.basename(p_lb89)
    says('1989 sheet: accepted with no vintage',
         sr.whose_sheet(p_lb89, fn, *args) is None)
    v90 = sr.whose_sheet(p_lb89, fn, *args, year=1990)
    says('1989 sheet: refused at 1990', v90 is not None,
         (v90 or {}).get('why', '')[:40])
    says('1989 sheet: accepted at 1989',
         sr.whose_sheet(p_lb89, fn, *args, year=1989) is None)

# ======================================================= the defects
print()
mk = sr.mark_of('Blanc de Lynch-Bages', e['name'])
known("mark_of('Blanc de Lynch-Bages') collides with the Echo's name",
      sr.says('Echo de Lynch-Bages', mk), 'mark=%r' % mk)
known('mark_of drops "blanc" when it is the only distinctive word',
      'blanc' not in (mk or ''), '"blanc" in COMMON')
if p_echo:
    fn = os.path.basename(p_echo)
    v = sr.whose_sheet(p_echo, fn, *args, year=2008, is_second=True)
    known('an Echo sheet is refused AS the Echo (second-wine mode)',
          v is not None, (v or {}).get('why', '')[:44])
p_gv = find('Chateau-Lynch-Bages-2008-EN.pdf')
if p_gv:
    fn = os.path.basename(p_gv)
    v = sr.whose_sheet(p_gv, fn, *args, year=2008, is_second=True)
    known('a GRAND VIN sheet is accepted as the Echo (second mode)',
          v is None,
          'is_second has no positive requirement' if v is None else '')

# ================================================== canonical safety
PROTECTED = ('data/sources.json', 'data/fiches.js', 'data/cuvees.js',
             'data/field-src.js', 'data/cuvee-src.js')
try:
    out = subprocess.check_output(
        ['git', 'diff', '--name-only', 'HEAD', '--'] + list(PROTECTED),
        cwd=ROOT, stderr=subprocess.DEVNULL).decode().strip()
except Exception:
    out = None
print()
if out is None:
    print('MISSING  git unavailable')
else:
    says('canonical dataset files unmodified vs HEAD', out == '',
         'clean' if out == '' else out.replace('\n', ' ')[:28])

print('\n%d check(s), %s'
      % (checks, 'all pass' if not fails
         else '%d FAILED: %s' % (len(fails), '; '.join(fails[:4]))))
sys.exit(1 if fails else 0)
