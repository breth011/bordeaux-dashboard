# -*- coding: utf-8 -*-
"""Why the reader accepted or refused each document, kept.

    python tools/evidence.py --estate lynch-bages      one estate
    python tools/evidence.py --write                   the whole archive
    python tools/evidence.py --pins                    migrate REFUSED
    python tools/evidence.py --show lynch-bages        read it back

Writes to the evidence store, data/evidence/, through
tools/evidence_store.py, and nothing else.
sources.json, fiches.js, cuvees.js, field-src.js and cuvee-src.js are
never opened for writing.

                            WHY THIS EXISTS

read-fiches.py counts the reader's refusals and prints them:

    why[how['refused']] += 1

and that is where the information ends. The count goes to the terminal
and the reason dies with the process. So a document the guards have
refused every year for a decade is indistinguishable from a document
nobody ever looked at, and "why is Lynch-Bages missing 1990?" has to
be re-investigated from nothing every time.

It is answerable in one line - the 1990 document's own filename says
1989, so the reader refused it - and that answer was computed and
thrown away on every run since the document was downloaded.

                      A DECISION, NOT A VERDICT

A refusal is what one version of one rule concluded from one document
on one day. It is not a fact about the document. So each decision
carries the version that made it, and a later version appends a new
decision beside the old one rather than replacing it. The file is
append-only: nothing in it is ever rewritten.

That is what makes "can this be re-evaluated under a newer rule?"
answerable - and the question matters, because this week three of the
reader's rules changed and two of them were wrong in their first
draft.

                           REASON CODES

The codes below are not invented. Every one is mapped from a verdict
string the guard chain actually returns, and `raw` keeps that string
verbatim so nothing is lost in the normalisation. If the reader grows
a new verdict, UNMAPPED_VERDICT appears in the file and says so rather
than being quietly folded into OTHER.

                           IDEMPOTENCE

Keyed on (artifact, estate, wine, decider version). Running twice with
the same version adds nothing; running after a version bump appends
one new decision per artifact and leaves every earlier one in place.
"""
import argparse
import collections
import datetime
import hashlib
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr

DECIDER_VERSION = 1
# The store, one file per decider version, since Phase 2.4. The old
# single file is in git history at a36b35c; evidence_store.py says
# why it moved.
import evidence_store as ST

# Each entry maps a verdict the guard chain really returns to a code.
# The order matters only where one string contains another.
CODES = (
    (re.compile(r'(?i)^nothing states this vintage'), 'NO_VINTAGE_STATED'),
    (re.compile(r'(?i)^the document declares the \d+ vintage'),
     'WRONG_VINTAGE'),
    (re.compile(r'(?i)^the filename calls this the \d+ vintage'),
     'WRONG_VINTAGE'),
    (re.compile(r'(?i)^the filename says it is press'), 'PRESS_DOCUMENT'),
    (re.compile(r'(?i)^a press dossier'), 'PRESS_DOCUMENT'),
    (re.compile(r'(?i)^the filename names another ch'), 'WRONG_ESTATE'),
    (re.compile(r'(?i)^the sheet names a sibling property'),
     'WRONG_ESTATE'),
    # Second-wine mode's own verdicts (Phase 2.3, decider v3). It now
    # asks a document to BE the second wine's, so it can say why not.
    (re.compile(r'(?i)^the estate records no second wine'),
     'NO_SECOND_WINE'),
    (re.compile(r'(?i)as well as the second wine'), 'AMBIGUOUS_WINE'),
    (re.compile(r'(?i)^the filename names the grand vin, not'),
     'IS_GRAND_VIN'),
    (re.compile(r'(?i)^the (filename|document) names another of the '
                r'estate'), 'WRONG_WINE'),
    (re.compile(r'(?i)^nothing identifies this as'), 'NOT_IDENTIFIED'),
    (re.compile(r'(?i)^the name spells another of the estate'),
     'WRONG_WINE'),
    (re.compile(r'(?i)^the filename abbreviates another'), 'WRONG_WINE'),
    (re.compile(r'(?i)^the sheet names another of the'), 'WRONG_WINE'),
    (re.compile(r'(?i)^the document calls itself the second wine'),
     'WRONG_WINE'),
    (re.compile(r'(?i)^the filename says another colour'),
     'WRONG_COLOUR'),
    # sells_another_wine returns its own sentence, which names a
    # merchant listing rather than an estate's sheet.
    (re.compile(r'(?i)(sells|merchant|shop|boutique|listing)'),
     'TRADE_LISTING'),
    (re.compile(r'(?i)^a guard could not read it'), 'GUARD_ERROR'),
    (re.compile(r'(?i)^unreadable$'), 'INVALID_DOCUMENT'),
    (re.compile(r'(?i)^the sheet states none of these fields'),
     'NO_FIELDS_FOUND'),
)


def code_for(why):
    if not why:
        return 'OTHER', ''
    for rx, code in CODES:
        if rx.search(why):
            return code, why
    return 'UNMAPPED_VERDICT', why


def reader_fingerprint():
    """The reader's own bytes, so a rule change is visible."""
    h = hashlib.sha1()
    for name in ('sheetreader.py', 'read-fiches.py'):
        p = os.path.join(ROOT, 'tools', name)
        if os.path.exists(p):
            h.update(io.open(p, 'rb').read())
    return h.hexdigest()[:12]


def commit():
    try:
        return subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT,
            stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def row_key(d):
    """What makes one decision one decision.

    Every part of this is here because leaving it out produced
    duplicates, and the idempotence test found each one:

      artifact               the obvious part
      folder                 a basename occurs in more than one
                             folder 888 times
      estate, wine           the manifest's claim
      field                  a record can hold a pin on two fields
      vintage                the manifest's year
      target_wine            WHICH of the estate's wines the reader
      target_vintage         was asked about, and for which year.
                             Phase 2 asked neither, so its rows carry
                             None and never collide with Phase 2.1's.
      target_role            AS WHAT it was asked. 102 estates list
                             their second wine among their cuvees as
                             well, so one wine is evaluated twice: as
                             the second (a real verdict, via
                             is_second) and as a named cuvee
                             (GUARD_HAS_NO_CUVEE_MODE). Without the
                             role in the key those two collided, and
                             8,181 of the colliding pairs disagreed -
                             so the collision was hiding a verdict,
                             not de-duplicating one.
      v                      the decider version

    One function, used by the reader and the writer, because the three
    previous versions of this key were two copies of a tuple and one of
    them was always behind.
    """
    c = d.get('ctx', {}) or {}
    return (d.get('artifact'), c.get('folder'), c.get('estate'),
            c.get('wine'), c.get('field'), c.get('vintage'),
            c.get('target_estate'), c.get('target_wine'),
            c.get('target_role'), c.get('target_vintage'), d.get('v'))


def existing_keys():
    """What is already recorded, so a re-run adds nothing."""
    return ST.existing_keys()


def pins():
    """The REFUSED list in read-fiches.py, read without importing it.

    It is a hand-written quality memory - (record, field) with a
    reason - and the point here is to carry it into the store WITHOUT
    removing it from the Python, so the two can be compared before
    either is trusted alone.
    """
    p = ROOT + 'tools/read-fiches.py'
    src = io.open(p, encoding='utf-8').read()
    m = re.search(r'^REFUSED = \{(.*?)^\}', src, re.S | re.M)
    if not m:
        return []
    out = []
    body = m.group(1)
    for mm in re.finditer(
            r"\('([^']+)',\s*\n?\s*'([a-z]+)'\):\s*\n?((?:\s*'(?:[^'\\]"
            r"|\\.)*'\n?)+)", body):
        txt = ''.join(re.findall(r"'((?:[^'\\]|\\.)*)'", mm.group(3)))
        out.append((mm.group(1), mm.group(2), txt.replace("\\'", "'")))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estate')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--pins', action='store_true')
    ap.add_argument('--show')
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()

    if a.show:
        if not ST.versions():
            print('no decisions recorded yet')
            return
        n = 0
        for v in ST.versions():
            for line in ST.iter_lines(v):
                line = line.decode('utf-8')
                if a.show not in line:
                    continue
                d = json.loads(line)
                if d.get('ctx', {}).get('estate') != a.show:
                    continue
                n += 1
                if n > 25:
                    continue
                print('%-50s %-20s %s'
                      % (d['artifact'][:50], d['code'],
                         (d.get('raw') or '')[:40]))
        print('\n%d decision(s) for %s' % (n, a.show))
        return

    fp, cm = reader_fingerprint(), commit()
    rows = []

    if a.pins:
        for key, field, why in pins():
            rows.append({
                'artifact': 'PIN:%s' % key,
                'kind': 'pin',
                'ctx': {'estate': key.split('|')[0], 'wine': None,
                        'vintage': key.split('|')[-1], 'field': field},
                'decision': 'REFUSED',
                'code': 'PINNED_BY_HAND',
                'raw': why,
                'evidence': ['hand-written in read-fiches.py REFUSED'],
                'v': DECIDER_VERSION, 'reader': fp, 'commit': cm,
                'at': datetime.date.today().isoformat(),
                're_evaluable': False,
            })
        print('%d pin(s) read from read-fiches.py REFUSED' % len(rows))

    if not a.pins or a.write:
        E = sr.estates(ROOT)
        man = json.load(io.open(ROOT + 'data/sources.json',
                                encoding='utf-8'))
        sheets = man.get('sheets', [])
        if a.estate:
            sheets = [s for s in sheets if s.get('estate') == a.estate]
        if a.limit:
            sheets = sheets[:a.limit]
        # Found from its own folder and name: tools/provenance.py.
        import provenance as PV
        run = PV.Run(DECIDER_VERSION)

        counts = collections.Counter()
        n = 0
        for s in sheets:
            fn, eid = s.get('file'), s.get('estate')
            if not fn or not eid:
                # No estate means no reader ever evaluates it, which is
                # itself a decision worth recording.
                if fn:
                    counts['NO_ESTATE_IN_MANIFEST'] += 1
                    rows.append({
                        'artifact': fn, 'kind': 'guard',
                        'ctx': {'estate': None, 'wine': None,
                                'vintage': s.get('year'),
                                'folder': s.get('folder')},
                        'decision': 'NOT_EVALUATED',
                        'code': 'NO_ESTATE_IN_MANIFEST',
                        'raw': 'the manifest gives this artifact no '
                               'estate, and every reader iterates by '
                               'estate',
                        'evidence': ['folder: %s' % (s.get('folder')
                                                     or '?')],
                        'v': DECIDER_VERSION, 'reader': fp,
                        'commit': cm,
                        'at': datetime.date.today().isoformat(),
                        're_evaluable': True,
                    })
                continue
            e = E.get(eid) or {}
            art = run.resolve(s, {'estate': eid, 'wine': s.get('wine'),
                                  'vintage': s.get('year'),
                                  'folder': s.get('folder')})
            p = art.path if art else None
            n += 1
            if n % 500 == 0:
                sys.stderr.write('  %d of %d\n' % (n, len(sheets)))
                sys.stderr.flush()
            if not p:
                counts['NOT_ON_DISK'] += 1
                rows.append({
                    'artifact': fn, 'kind': 'guard',
                    'ctx': {'estate': eid, 'wine': s.get('wine'),
                            'vintage': s.get('year'),
                            'folder': s.get('folder')},
                    'decision': 'NOT_EVALUATED', 'code': 'NOT_ON_DISK',
                    'raw': 'named in the manifest, absent from disk',
                    'evidence': [], 'v': DECIDER_VERSION, 'reader': fp,
                    'commit': cm,
                    'at': datetime.date.today().isoformat(),
                    're_evaluable': True,
                })
                continue
            try:
                verdict = sr.whose_sheet(
                    p, fn, e.get('name'), e.get('cuvees') or (),
                    e.get('second'), e.get('cat'))
            except Exception as ex:
                verdict = {'why': 'a guard could not read it: %s'
                                  % type(ex).__name__,
                           'role': None, 'wine': None}
            if verdict:
                code, raw = code_for(verdict.get('why'))
                counts[code] += 1
                rows.append({
                    'artifact': fn, 'kind': 'guard',
                    'ctx': {'estate': eid, 'wine': s.get('wine'),
                            'vintage': s.get('year'),
                            'folder': s.get('folder'),
                            'evaluated_as': 'grand vin'},
                    'decision': 'REFUSED', 'code': code, 'raw': raw,
                    'points_at': {'role': verdict.get('role'),
                                  'wine': verdict.get('wine')},
                    'evidence': ['whose_sheet verdict'],
                    'v': DECIDER_VERSION, 'reader': fp, 'commit': cm,
                    'at': datetime.date.today().isoformat(),
                    're_evaluable': True,
                })
            else:
                counts['ACCEPTED'] += 1
                rows.append({
                    'artifact': fn, 'kind': 'guard',
                    'ctx': {'estate': eid, 'wine': s.get('wine'),
                            'vintage': s.get('year'),
                            'folder': s.get('folder'),
                            'evaluated_as': 'grand vin'},
                    'decision': 'ACCEPTED', 'code': 'ACCEPTED',
                    'raw': '', 'evidence': ['whose_sheet raised no '
                                            'objection'],
                    'v': DECIDER_VERSION, 'reader': fp, 'commit': cm,
                    'at': datetime.date.today().isoformat(),
                    're_evaluable': True,
                })

        print('%d artifact(s) evaluated, decider version %d, reader %s'
              % (n, DECIDER_VERSION, fp))
        print()
        print('%-30s %s' % ('DECISION', 'n'))
        print('-' * 44)
        for k, c in counts.most_common():
            print('   %-28s %5d' % (k, c))

    if a.write:
        n = ST.append(rows, DECIDER_VERSION)
        print('\n%d decision(s) appended to data/evidence/ at v%d'
              % (n, DECIDER_VERSION))
        if n != len(rows):
            print('%d already recorded at version %d and left alone'
                  % (len(rows) - n, DECIDER_VERSION))
    else:
        print('\nnothing written; pass --write')


if __name__ == '__main__':
    main()
