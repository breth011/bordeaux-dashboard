# -*- coding: utf-8 -*-
"""Ask the guards again about documents they have already judged.

    python tools/recheck-sources.py             both reports
    python tools/recheck-sources.py --apply     correct manifest roles

Every guard in sheetreader.py was added because of one document, and
each one is a decision about hundreds. The manifest records the
decision - role `skip`, `other`, `second` - and fiches.js records what
was read before it. Neither is revisited when a guard changes, so a
guard change leaves two kinds of debris behind it:

  a record standing on a document now refused. The merge can add a
  field and overwrite one, but it cannot withdraw one: when --redo
  re-reads a document the guards have since rejected, the provenance
  is cleared and the value stays. Giscours 2021 kept the 2020 blend
  that way, with an empty provenance row beside it.

  a document refused by a guard that has since been narrowed. Marquis
  de Terme's nine vintages sat at role `skip` because their filenames
  say `Revue-de-Presse` as well as `Fiche-technique`; when the press
  guard learnt to read the first half of that name, nothing went back
  and asked it about them again.

The first list is for reading: a value to withdraw is a judgement
about a wine and this tool will not make it.

The second asks what the change to the guards actually did, which it
can only do by having something to compare against - so the filename
guards are run twice, once from sheetreader.py as git holds it and
once from the working copy, and the verdicts are diffed. The manifest
does not record which guard refused which document, and most refusals
come from guards that open the file rather than read the name, so
asking the filename guards alone about a document already filed `skip`
proves nothing about why it was filed that way. The diff has an exact
answer where that question has none.

A document the change has un-refused should be filed as accepted, and
a role is the manifest's own bookkeeping, so --apply writes those and
only those. It never refuses anything currently accepted - that would
hide data rather than find it - and it never touches fiches.js.

Only the filename guards are asked, of both versions. They are the
cheap ones, they are where guards keep being added, and asking them of
all 12,393 documents twice costs nothing.
"""
import argparse
import collections
import io
import json
import os
import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr

MANIFEST = ROOT + 'data/sources.json'
# A role the guards put a document into. Everything else - grand,
# combined, page - is a document already in use.
REFUSED = ('skip', 'other', 'second', 'unknown')
# Bookkeeping, not something a sheet states.
NOT_A_FIELD = frozenset(('src', 'via', 'url', 'xsrc', 'ttl', 'ntl',
                         'wtl', 'dtl', 'ftl'))
ROW = re.compile(r"(?m)^'([a-z0-9-]+)\|(\d{4})':\{(.*)\},$")


def committed_reader():
    """sheetreader.py as git holds it, loaded alongside the live one.

    Imported under its own name from a copy, so the working tree is
    not touched and both versions answer in the same process.
    """
    out = subprocess.run(['git', 'show', 'HEAD:tools/sheetreader.py'],
                         cwd=ROOT, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    if out.returncode:
        return None
    tmp = os.path.join(tempfile.mkdtemp(), 'sheetreader_head.py')
    io.open(tmp, 'wb').write(out.stdout)
    spec = importlib.util.spec_from_file_location(
        'sheetreader_head', tmp)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:
        return None
    return mod


def refusal(eid, year, filename, E, S=None):
    """Why the filename guards refuse this document, or None.

    The chain in whose_sheet, less the guards that open the file: this
    runs over every document in the manifest and nothing here needs
    more than the name. `S` picks which sheetreader answers, so the
    committed guards and the working copy's can be compared.
    """
    S = S or sr

    def ask(name, *args):
        """That guard's verdict, or None if this version lacks it."""
        g = getattr(S, name, None)
        return g(*args) if g else None

    e = E.get(eid) or {}
    grand = e.get('name')
    others = list(e.get('cuvees') or ())
    second = e.get('second')
    v = ask('filename_vintage', year, filename, grand) if year else None
    if v:
        return 'the filename calls this the %d vintage' % v
    p = ask('is_press_name', filename)
    if p:
        return 'the filename says it is press: %s' % p
    o = ask('names_other_chateau', filename, grand, others, second)
    if o:
        return 'the filename names another château: %s' % o
    sold = ask('sells_another_wine', filename, grand)
    if sold:
        return sold
    ab = ask('abbreviates_other_wine', filename, grand, others)
    if ab:
        return 'the filename abbreviates another of the estate’s '\
               'wines: %s' % ab
    if ask('wrong_colour', filename, None, e.get('cat')):
        return 'the filename says another colour'
    return None


def fields_in(body):
    """The field names a record body holds at the top level.

    Written out rather than matched, because a record carries prose
    and a regular expression finds `press:` inside a tasting note.
    """
    out = set()
    depth = 0
    i = 0
    while i < len(body):
        c = body[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
        elif c == "'":
            j = i + 1
            while j < len(body):
                if body[j] == '\\':
                    j += 2
                    continue
                if body[j] == "'":
                    break
                j += 1
            i = j + 1
            continue
        elif depth == 0 and (i == 0 or body[i - 1] == ','):
            m = re.match(r'([a-z]+):', body[i:])
            if m:
                out.add(m.group(1))
        i += 1
    return out - NOT_A_FIELD


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true',
                    help='file the documents the guards now accept')
    a = ap.parse_args()

    E = sr.estates(ROOT)
    man = json.load(io.open(MANIFEST, encoding='utf-8'))

    # 1. Records citing a document the guards now refuse.
    t = io.open(ROOT + 'data/fiches.js', encoding='utf-8').read()
    standing = []
    for m in ROW.finditer(t):
        eid, year, body = m.group(1), int(m.group(2)), m.group(3)
        sm = re.search(r"src:'([^']+)'", body)
        if not sm:
            continue
        why = refusal(eid, year, sm.group(1), E)
        if why:
            standing.append((eid, year, why, sm.group(1),
                             sorted(fields_in(body))))

    print('RECORDS CITING A DOCUMENT THE GUARDS NOW REFUSE: %d'
          % len(standing))
    print('   a value here was read before the guard existed and no '
          'merge will take it')
    print('   back; each one is a judgement about a wine, so they are '
          'listed, not changed.')
    print()
    for eid, year, why, f, fields in sorted(standing):
        print('   %-26s %4d  %s' % (eid[:26], year, why))
        print('      %s' % f)
        print('      holds: %s' % (', '.join(fields) or '(nothing)'))
    print()

    # 2. What the change to the guards did, against the committed
    # version of them.
    head = committed_reader()
    if head is None:
        print('WHAT THE GUARD CHANGE DID: sheetreader.py as committed '
              'could not be loaded,')
        print('   so there is nothing to compare against.')
        return
    back, newly = [], []
    for s in man['sheets']:
        eid, f = s.get('estate'), s.get('file') or ''
        if not eid or not f:
            continue
        yr = s.get('year')
        yr = int(yr) if yr else None
        was = refusal(eid, yr, f, E, head)
        now = refusal(eid, yr, f, E)
        if was and not now:
            back.append(s)
        elif now and not was:
            newly.append((s, now))

    print('NOW REFUSED THAT WAS NOT: %d document(s)' % len(newly))
    print('   if any of these is a document a record was read from, '
          'it is in the list above.')
    print()
    for s, why in sorted(newly, key=lambda x: ((x[0].get('estate')
                                                or ''),
                                               str(x[0].get('year')))):
        print('   %-22s %-5s %-8s %s'
              % ((s.get('estate') or '')[:22], s.get('year'),
                 s.get('role'), why[:42]))
        print('      %s' % (s.get('file') or '')[:70])
    print()
    back = [s for s in back if s.get('role') in REFUSED]
    print('NO LONGER REFUSED, AND STILL FILED AS REFUSED: %d'
          % len(back))
    print('   the guard that rejected these has been narrowed; the '
          'role is the manifest’s')
    print('   own bookkeeping, so --apply corrects it.')
    print()
    by = collections.Counter((s.get('estate'), s.get('role'))
                             for s in back)
    for (eid, rl), n in sorted(by.items()):
        print('   %-26s %-8s %3d' % ((eid or '')[:26], rl, n))
    print()
    for s in sorted(back, key=lambda s: ((s.get('estate') or ''),
                                         str(s.get('year')))):
        print('   %-22s %-5s %-8s %s'
              % ((s.get('estate') or '')[:22], s.get('year'),
                 s.get('role'), (s.get('file') or '')[:52]))
    print()

    if not a.apply:
        print('nothing written; pass --apply to correct the %d role(s)'
              % len(back))
        return
    if not back:
        print('no role to correct')
        return

    # The roles the guards can no longer justify become `grand`, which
    # is what a document of this estate's own wine is. A sheet that
    # turns out to carry several wines is for read-sheets.py to find.
    shutil.copy(MANIFEST, MANIFEST + '.bak')
    for s in back:
        s['role'] = 'grand'
    # The same options as harvest.py, refile.py and promote-urls.py.
    # sort_keys here reordered every key of all 12,393 rows, and
    # nineteen roles came out as a diff of 110,756 lines.
    io.open(MANIFEST, 'w', encoding='utf-8', newline='').write(
        json.dumps(man, ensure_ascii=False, indent=1))
    print('%d role(s) corrected to grand; %s holds the previous file'
          % (len(back), os.path.basename(MANIFEST) + '.bak'))
    print()
    print('now run: python tools/audit-sources.py')
    print('then:    python tools/read-fiches.py --estate <each> --redo')


if __name__ == '__main__':
    main()
