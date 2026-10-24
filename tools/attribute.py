# -*- coding: utf-8 -*-
"""The artifacts the manifest gives no estate, and what they look like.

    python tools/attribute.py                 the report
    python tools/attribute.py --write         data/attribution-candidates.jsonl
    python tools/attribute.py --estate doisy-daene

Writes one file and never the manifest. A candidate here is a
proposal with its evidence attached; promoting one is a later phase's
decision and this tool has no code that could.

                             WHY THEY MATTER

908 artifacts carry no `estate` in data/sources.json. Every reader
iterates sheets by estate - read-fiches, read-plantings, read-sheets
all do - so these are offered to nothing. A perfect fiche technique
with a blend, an alcohol and a tasting note is invisible if this one
field is empty.

904 of the 908 sit in a folder named after an estate, and 786 carry
wine data. That makes the folder the obvious answer, and the obvious
answer is exactly what has to be handled carefully: the folder is
where the CRAWLER put the file, and Phase 1 found two cases where the
crawler was wrong about that - the whole de Braude/Mongravey pattern
is one website's PDFs landing in one estate's folder, and a Figeac
page sitting in Haut-Bailly's.

So the folder is evidence, not truth, and it is recorded as evidence
beside the document's own words rather than instead of them.

                               THE STATES

  HIGH_CONFIDENCE   the document itself names the folder's estate, it
                    carries wine data, and a vintage is known. Two
                    independent signals agree.

  CANDIDATE         the folder names an estate, the document carries
                    wine data, and the document does not name any
                    estate - usually because the fiche prints a logo
                    rather than a name. One signal, uncontradicted.

  CONFLICT          the document names an estate and it is NOT the
                    folder's. The most interesting group and the one
                    that must not be bulk-assigned.

  REJECTED          not a data document: press, event, catalogue,
                    price list, or nothing wine-shaped in it at all.

  UNRESOLVED        no folder estate, unreadable, or no evidence
                    either way.

Nothing is ever promoted to CONFIRMED by this tool. That state exists
in the file so a person can set it.
"""
import argparse
import collections
import datetime
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr

TOOL_VERSION = 1
CENSUS = ROOT + 'data/artifact-census.jsonl'
OUT = ROOT + 'data/attribution-candidates.jsonl'

NOT_DATA = ('PRESS_DOSSIER', 'EVENT_DOCUMENT', 'NEWS_ARTICLE', 'CATALOG',
            'PRICE_LIST', 'MARKETING_DOCUMENT', 'PRODUCER_PROFILE')


def commit():
    try:
        return subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT,
            stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--estate')
    ap.add_argument('--limit', type=int, default=16)
    a = ap.parse_args()

    if not os.path.exists(CENSUS):
        print('run tools/census.py --write && tools/census-compact.py '
              'first')
        return 2

    E = sr.estates(ROOT)
    # "Classified" is not one list. The four classifications this
    # dashboard holds are defined in four files, and reading only
    # chateaux.js - the 61 of the 1855 Medoc - called Doisy-Daene
    # unclassified, which it is not: it is a Barsac second growth of
    # the same 1855 list, and it owns 287 of the 908.
    CLASSIFIED_FILES = {
        'chateaux.js': '1855 Medoc & Graves',
        'sauternes.js': '1855 Sauternes & Barsac',
        'graves.js': 'Crus Classes de Graves',
        'saintemilion.js': 'Saint-Emilion grands crus classes',
    }
    classified, collection = set(), {}
    for fn in sorted(os.listdir(ROOT + 'data')):
        if not fn.endswith('.js'):
            continue
        src = io.open(ROOT + 'data/' + fn, encoding='utf-8').read()
        if 'BDX_CHATEAUX' not in src:
            continue
        for i in re.findall(r"id:'([a-z0-9-]+)'", src):
            collection.setdefault(i, fn)
            if fn in CLASSIFIED_FILES:
                classified.add(i)

    rows = []
    with io.open(CENSUS, encoding='utf-8') as f:
        f.readline()
        for line in f:
            d = json.loads(line)
            if d['m'].get('estate'):
                continue
            rows.append(d)

    out = []
    for d in rows:
        folder = d['path'].split('/')[0]
        # pages/<estate>/... puts the estate one level down.
        parts = d['path'].split('/')
        if parts[0] in ('pages', 'fiches', '_raw') and len(parts) > 2:
            folder = parts[1]
        fold_est = folder if folder in E else None
        obs = [e for e in d['o']['estate'] if e != 'UNKNOWN']
        kind = d['o']['type']
        data = d['o']['data']
        vintage = d['o']['vintage']

        ev = ['folder names %s' % (fold_est or 'nothing we know')]
        ev += d.get('ev', [])[:3]

        if kind in NOT_DATA and not data:
            state, why = 'REJECTED', '%s with no wine data' % kind
        elif not data and kind in ('IMAGE_ONLY', 'UNREADABLE'):
            state, why = 'UNRESOLVED', kind.lower().replace('_', ' ')
        elif not fold_est:
            state, why = 'UNRESOLVED', 'no estate in the folder either'
        elif obs and fold_est not in obs:
            state, why = ('CONFLICT',
                          'the document names %s, the folder says %s'
                          % (','.join(obs), fold_est))
        elif obs and fold_est in obs:
            if data and vintage != 'UNKNOWN':
                state, why = ('HIGH_CONFIDENCE',
                              'the document names the folder\'s estate, '
                              'carries %s, and states %s'
                              % (','.join(data[:3]), vintage))
            else:
                state, why = ('CANDIDATE',
                              'the document names the folder\'s estate '
                              'but %s'
                              % ('states no vintage' if data
                                 else 'carries no wine data'))
        elif data:
            state, why = ('CANDIDATE',
                          'the folder names %s and the document carries '
                          '%s, but names no estate itself'
                          % (fold_est, ','.join(data[:3])))
        else:
            state, why = 'REJECTED', 'no wine data and no estate named'

        out.append({
            'artifact': d['path'],
            'id': d['id'],
            'manifest': {'estate': None, 'wine': d['m'].get('wine'),
                         'vintage': d['m'].get('vintage'),
                         'role': d['m'].get('role')},
            'evidence': {
                'folder_estate': fold_est,
                'document_estate': obs or ['UNKNOWN'],
                'document_wine': d['o']['wine'],
                'document_vintage': vintage,
                'document_type': kind,
                'data_signals': data,
                'vintage_confidence': d['conf'].get('vin'),
                'notes': ev,
            },
            'proposed': {
                'estate': fold_est if state in ('HIGH_CONFIDENCE',
                                                'CANDIDATE') else None,
                # Never the estate's main wine by default: an estate is
                # not one wine, and guessing the grand vin is how a
                # second wine's sheet becomes the first wine's data.
                'wine': None,
                'vintage': vintage if vintage != 'UNKNOWN' else None,
            },
            'state': state,
            'why': why,
            'classified_estate': bool(fold_est and fold_est in classified),
            'v': TOOL_VERSION,
            'at': datetime.date.today().isoformat(),
            'commit': commit(),
        })

    byst = collections.Counter(r['state'] for r in out)
    print('%d artifact(s) with no estate in the manifest\n' % len(out))
    print('%-20s %6s  %s' % ('STATE', 'n', 'of which at a classified '
                             'estate'))
    print('-' * 62)
    for k, c in byst.most_common():
        cl = sum(1 for r in out
                 if r['state'] == k and r['classified_estate'])
        print('   %-18s %6d  %d' % (k, c, cl))

    print()
    print('BY FOLDER, top 12')
    print('-' * 62)
    byf = collections.Counter(r['evidence']['folder_estate'] or '(none)'
                              for r in out)
    for k, c in byf.most_common(12):
        print('   %-34s %4d  %s'
              % (k[:34], c,
                 CLASSIFIED_FILES.get(collection.get(k), '')
                 or ('not in BDX_CHATEAUX' if k not in collection
                     else collection.get(k, ''))))

    print()
    print('DOCUMENT KIND')
    print('-' * 62)
    for k, c in collections.Counter(
            r['evidence']['document_type'] for r in out).most_common(8):
        print('   %-26s %4d' % (k, c))

    if a.estate:
        print()
        print('=' * 62)
        print(a.estate)
        print('=' * 62)
        for r in out:
            if r['evidence']['folder_estate'] != a.estate:
                continue
            print('   %-46s %s' % (r['artifact'].split('/')[-1][:46],
                                   r['state']))
            print('      %s' % r['why'][:70])
    else:
        print()
        print('CONFLICT cases - the document disagrees with its folder')
        print('-' * 62)
        n = 0
        for r in out:
            if r['state'] != 'CONFLICT':
                continue
            n += 1
            if n <= a.limit:
                print('   %-44s' % r['artifact'].split('/')[-1][:44])
                print('      %s' % r['why'][:70])
        if n > a.limit:
            print('   ... and %d more' % (n - a.limit))

    if a.write:
        with io.open(OUT, 'w', encoding='utf-8', newline='') as f:
            f.write(json.dumps({
                '_': 'Proposals, not corrections. The manifest is '
                     'unchanged and nothing here has been promoted. '
                     'folder_estate is evidence about where the '
                     'crawler put the file, not about whose wine it '
                     'is.',
                'tool_version': TOOL_VERSION,
                'rows': len(out),
                'states': dict(byst),
            }, ensure_ascii=False, sort_keys=True) + '\n')
            for r in sorted(out, key=lambda x: x['artifact']):
                f.write(json.dumps(r, ensure_ascii=False,
                                   sort_keys=True) + '\n')
        print('\nwritten to data/attribution-candidates.jsonl (%d)'
              % len(out))
    else:
        print('\nnothing written; pass --write')


if __name__ == '__main__':
    sys.exit(main() or 0)
