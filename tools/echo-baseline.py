# -*- coding: utf-8 -*-
"""The Lynch-Bages / Echo baseline, before anything is changed.

    python tools/echo-baseline.py            report
    python tools/echo-baseline.py --write    data/echo-baseline.jsonl

Reads only. Writes one analysis file, never a canonical one.

Phase 2.2 item 3: a machine-readable record of exactly where things
stand for the 50 Echo cases, taken from the reader's real behaviour and
the evidence store rather than from filenames - so that whatever is
changed later can be shown to have changed it.

Three verdicts per sheet, each evaluating it as the SECOND wine:

  current   whose_sheet(..., is_second=True), as the code is today
  naive     the same with the second wine dropped from the competing
            set - the obvious fix, which is wrong (see
            tools/diagnose-second-mode.py)
  grand     the same sheet evaluated as the GRAND VIN, which is what
            the 50 were refused as when the manifest routed them to the
            Blanc
"""
import argparse
import datetime
import io
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr

OUT = ROOT + 'data/echo-baseline.jsonl'
EID = 'lynch-bages'
MISSING = (2008, 2009, 2010, 2015, 2016)


def commit():
    try:
        return subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT,
            stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def why(v):
    return 'ACCEPTED' if v is None else (v.get('why') or '')[:96]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()

    E = sr.estates(ROOT)
    e = E[EID]
    others = [c for c in e['cuvees'] if c != e['second']]

    ident = {}
    with io.open(ROOT + 'data/wine-identity.jsonl', encoding='utf-8') as f:
        f.readline()
        for line in f:
            d = json.loads(line)
            if d['state'] == 'MANIFEST_METADATA_WRONG':
                ident[d['artifact']] = d

    # The structures, as they are.
    cuv_src = io.open(ROOT + 'data/cuvees.js', encoding='utf-8').read()
    cuv_line = [l for l in cuv_src.split('\n')
                if l.startswith("'%s':[" % EID)]
    echo_records = sorted(
        int(l.split('|')[2].split("'")[0])
        for l in cuv_src.split('\n')
        if l.startswith("'%s|echo-de-lynch-bages|" % EID))

    man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))
    disk = {}
    for root, dirs, files in os.walk(ROOT + 'sources'):
        for f in files:
            disk.setdefault(f, os.path.join(root, f))

    rows = []
    for s in man['sheets']:
        if s.get('estate') != EID or s.get('file') not in ident:
            continue
        fn, p = s['file'], disk.get(s['file'])
        yr = int(s['year']) if s.get('year') else None
        d = ident[fn]
        if p:
            cur = sr.whose_sheet(p, fn, e['name'], e['cuvees'],
                                 e['second'], e['cat'], year=yr,
                                 is_second=True)
            nai = sr.whose_sheet(p, fn, e['name'], others, None,
                                 e['cat'], year=yr, is_second=True)
            grd = sr.whose_sheet(p, fn, e['name'], e['cuvees'],
                                 e['second'], e['cat'], year=yr)
        else:
            cur = nai = grd = {'why': 'not on disk'}
        rows.append({
            'artifact': fn,
            'folder': s.get('folder'),
            'sha1': s.get('sha1'),
            'manifest': {'estate': s.get('estate'),
                         'wine': s.get('wine'),
                         'vintage': s.get('year'),
                         'role': s.get('role')},
            'document_wine': {
                'from_filename': d['observed']['wine_from_filename'],
                'from_text': d['observed']['wine_from_text'],
                'also_names_the_estate':
                    d['observed'].get('also_names_the_estate'),
            },
            'reader': {
                'as_second_current': why(cur),
                'as_second_naive': why(nai),
                'as_grand_vin': why(grd),
            },
            'year_is_missing_from_records': yr in MISSING and
                                            yr not in echo_records,
        })

    head = {
        '_': 'Lynch-Bages / Echo, before any Phase 2.2 change. An '
             'analysis, not a source of truth.',
        'taken_at': datetime.datetime.now().isoformat(timespec='seconds'),
        'commit': commit(),
        'structure': {
            'chateaux.js second': e['second'],
            'cuvees.js BDX_CUVEE_WINES line':
                cuv_line[0][:300] if cuv_line else None,
            'echo listed in BDX_CUVEE_WINES': cuv_src.count(
                "name:'Echo de Lynch-Bages'"),
            'sr.estates() cuvees': e['cuvees'],
            'sr.estates() merges second into cuvees':
                e['second'] in e['cuvees'],
            'mark_of(Blanc de Lynch-Bages)':
                sr.mark_of('Blanc de Lynch-Bages', e['name']),
            'that mark inside the Echo\'s own name':
                sr.says('Echo de Lynch-Bages',
                        sr.mark_of('Blanc de Lynch-Bages', e['name'])),
        },
        'echo_records_on_file': echo_records,
        'missing_vintages': [y for y in MISSING if y not in echo_records],
        'cases': len(rows),
    }

    import collections
    print('Lynch-Bages / Echo baseline - %d MANIFEST_METADATA_WRONG '
          'case(s)\n' % len(rows))
    for k, v in head['structure'].items():
        print('   %-42s %s' % (k[:42], str(v)[:70]))
    print()
    print('   Echo records on file   %s' % head['echo_records_on_file'])
    print('   missing vintages       %s' % head['missing_vintages'])
    print()
    for col in ('as_second_current', 'as_second_naive', 'as_grand_vin'):
        c = collections.Counter(r['reader'][col][:64] for r in rows)
        print('   %s' % col)
        for k, n in c.most_common(4):
            print('      %3d  %s' % (n, k))
    print()
    print('   cases whose year is a missing Echo vintage: %d'
          % sum(1 for r in rows if r['year_is_missing_from_records']))

    if a.write:
        with io.open(OUT, 'w', encoding='utf-8', newline='') as f:
            f.write(json.dumps(head, ensure_ascii=False,
                               sort_keys=True) + '\n')
            for r in sorted(rows, key=lambda x: x['artifact']):
                f.write(json.dumps(r, ensure_ascii=False,
                                   sort_keys=True) + '\n')
        print('\nwritten to data/echo-baseline.jsonl')


if __name__ == '__main__':
    main()
