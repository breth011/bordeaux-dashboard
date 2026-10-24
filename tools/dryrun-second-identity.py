# -*- coding: utf-8 -*-
"""What Phase 2.6's second-wine identity model would change - measured,
not written.

    python tools/dryrun-second-identity.py [--base 4370382] [--limit N]
    python tools/dryrun-second-identity.py --write   data/phase26-impact.jsonl

Writes nothing to the evidence store, and never v4. --write puts this
analysis in data/phase26-impact.jsonl, which is not evidence and not
canonical.

Two readers are run on the same bytes: the reader as committed at
--base (loaded from git into a temporary module) and the reader in the
working tree. The files are found through tools/provenance.py - each
row's own folder - so the comparison is the reader change alone, not
the reader change plus Phase 2.5's path fix. The same contexts as the
evidence passes are asked: every manifest sheet with an estate, each
of its years, as the grand vin and as the second wine; and every sheet
without one, under its folder's estate.

The stored v3 decision for each context is reported beside the two, so
"what would v4 say that v3 said differently" can be read off as well.
"""
import argparse
import collections
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as NEW
import evidence as EV
import evidence_store as ST
import provenance as PV

OUT = ROOT + 'data/phase26-impact.jsonl'
# Raw results, local: reports/ is not committed.
CACHE = ROOT + 'reports/phase26-dryrun-cache.json'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def verdict(sr, p, fn, e, yr, second):
    try:
        v = sr.whose_sheet(p, fn, e.get('name'), e.get('cuvees') or (),
                           e.get('second'), e.get('cat'), year=yr,
                           is_second=second)
    except Exception as ex:
        v = {'why': 'a guard could not read it: %s' % type(ex).__name__}
    if not v:
        return 'ACCEPTED', ''
    return EV.code_for(v.get('why'))[0], v.get('why') or ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='4370382')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--summary', action='store_true',
                    help='re-summarise the last run from its cache')
    a = ap.parse_args()
    if a.summary:
        c = json.load(io.open(CACHE, encoding='utf-8'))
        tally = collections.Counter(dict(
            (tuple(k) if isinstance(k, list) else k, n)
            for k, n in c['tally']))
        summarise(c['changed'], c['added'], c['rows'], tally, a.base,
                  a.write)
        return

    tmp = tempfile.mkdtemp(prefix='sr-base-')
    src = subprocess.check_output(['git', 'show', '%s:tools/sheetreader.py'
                                   % a.base], cwd=ROOT)
    with open(os.path.join(tmp, 'sheetreader_base.py'), 'wb') as f:
        f.write(src)
    OLD = load(os.path.join(tmp, 'sheetreader_base.py'), 'sheetreader_base')
    EW = load(ROOT + 'tools/evidence-wines.py', 'evidence_wines')
    RC = load(ROOT + 'tools/recharacterize.py', 'recharacterize')

    # Which functions differ between the two readers at all. Anything the
    # grand-vin guard or the blend reader calls, and that is not listed
    # here, cannot have changed behaviour.
    import inspect
    changed, added = [], []
    for name, obj in vars(NEW).items():
        if inspect.isfunction(obj) and obj.__module__ == NEW.__name__:
            old = getattr(OLD, name, None)
            if old is None:
                added.append(name)
            elif inspect.getsource(old) != inspect.getsource(obj):
                changed.append(name)
    print('functions changed: %s' % ', '.join(sorted(changed)))
    print('functions added:   %s\n' % ', '.join(sorted(added)))

    E = NEW.estates(ROOT)
    man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))
    sheets = [s for s in man['sheets'] if s.get('file')]
    if a.limit:
        sheets = sheets[:a.limit]

    v3 = {}
    for d in ST.iter_rows([3]):
        c = d.get('ctx') or {}
        if c.get('target_role') in ('grand', 'second'):
            v3[(d['artifact'], c.get('folder'), c.get('estate'),
                c.get('target_estate'), c.get('target_role'),
                c.get('target_vintage'))] = d.get('code')

    rows, tally = [], collections.Counter()
    seen = set()
    for n, s in enumerate(sheets, 1):
        if n % 500 == 0:
            sys.stderr.write('  %d of %d\n' % (n, len(sheets)))
            sys.stderr.flush()
        key = (s.get('folder'), s['file'], s.get('estate'))
        if key in seen:
            continue                      # a manifest duplicate
        seen.add(key)
        eid = s.get('estate')
        unattributed = not eid
        if unattributed:
            eid = RC.folder_estate((s.get('folder') or '') + '/' + s['file'],
                                   E) or RC.folder_estate(s.get('folder'), E)
        e = E.get(eid) if eid else None
        if not e:
            continue
        try:
            art = PV.resolve(s.get('folder'), s['file'])
        except PV.ProvenanceFailure:
            tally['(provenance failure, not asked)'] += 1
            continue
        try:
            text = NEW.flat(art.path)
        except Exception:
            text = ''
        if unattributed:
            years = []
            for y in RC.YEAR_DECLARED.findall(text or ''):
                if int(y) not in years:
                    years.append(int(y))
            for y in RC.YEAR_IN.findall(s['file']):
                if 1800 < int(y) < 2100 and int(y) not in years:
                    years.append(int(y))
            years = years[:3] or [None]
        else:
            years = EW.candidate_years(s, text)
        for role in ('grand', 'second'):
            if role == 'second' and not e.get('second'):
                continue
            for yr in years:
                o, ow = verdict(OLD, art.path, s['file'], e, yr,
                                role == 'second')
                nw_, nww = verdict(NEW, art.path, s['file'], e, yr,
                                   role == 'second')
                k3 = (s['file'], s.get('folder'),
                      None if unattributed else eid,
                      eid if unattributed else None, role, yr)
                stored = v3.get(k3)
                tally[(role, o, nw_)] += 1
                if o != nw_ or (stored and stored != nw_):
                    rows.append({
                        'artifact': s['file'], 'folder': s.get('folder'),
                        'estate': eid, 'unattributed': unattributed,
                        'role': role, 'target_vintage': yr,
                        'target_wine': e.get('second') if role == 'second'
                        else e.get('name'),
                        'base': o, 'new': nw_, 'new_why': nww[:160],
                        'v3_stored': stored, 'read': art.rel,
                    })

    # Kept before anything is summarised, so a fault in the summary
    # cannot cost the run: --summary re-reads this instead of reading
    # thirteen thousand documents twice again.
    with io.open(CACHE, 'w', encoding='utf-8', newline='') as f:
        json.dump({'changed': changed, 'added': added, 'rows': rows,
                   'tally': [[list(k) if isinstance(k, tuple) else k, n]
                             for k, n in tally.items()]}, f,
                  ensure_ascii=False)
    summarise(changed, added, rows, tally, a.base, a.write)


def summarise(changed, added, rows, tally, base, write):
    trip = dict((k, n) for k, n in tally.items() if isinstance(k, tuple))
    print('\nCONTEXTS, base reader -> new reader (same bytes)')
    print('-' * 70)
    for role in ('grand', 'second'):
        tot = sum(n for (r, _, _), n in trip.items() if r == role)
        same = sum(n for (r, o, nw_), n in trip.items()
                   if r == role and o == nw_)
        print('   %-7s %6d contexts, %6d unchanged, %5d changed'
              % (role, tot, same, tot - same))
        for (r, o, nw_), n in sorted(trip.items(), key=lambda x: -x[1]):
            if r == role and o != nw_:
                print('      %-22s -> %-22s %5d' % (o, nw_, n))
    if tally.get('(provenance failure, not asked)'):
        print('   artifacts not asked (provenance failure): %d'
              % tally['(provenance failure, not asked)'])

    sec = [r for r in rows if r['role'] == 'second']
    acc_lost = [r for r in sec if r['base'] == 'ACCEPTED'
                and r['new'] != 'ACCEPTED']
    print('\nSECOND-WINE ACCEPTANCES THE NEW READER WITHDRAWS: %d'
          % len(acc_lost))
    for k, n in collections.Counter(r['new'] for r in acc_lost).most_common():
        print('   -> %-22s %5d' % (k, n))
    unl = [r for r in rows if r['new'] == 'UNLISTED_WINE']
    print('...naming a wine no list holds (UNLISTED_WINE): %d contexts, '
          '%d documents, %d estates'
          % (len(unl), len(set((r['folder'], r['artifact']) for r in unl)),
             len(set(r['estate'] for r in unl))))
    names = collections.Counter()
    for r in unl:
        names[(r['estate'], r['new_why'].split(': ', 1)[-1].lower())] += 1
    for (est, nm), n in names.most_common(40):
        print('      %-26s %-40s %3d' % (est[:26], nm[:40], n))
    gained = [r for r in sec if r['base'] != 'ACCEPTED'
              and r['new'] == 'ACCEPTED']
    print('second-wine acceptances the new reader ADDS: %d' % len(gained))
    for r in gained[:10]:
        print('      %s %s %s (was %s)' % (r['estate'], r['artifact'][:50],
                                         r['target_vintage'], r['base']))

    print('\nAGAINST THE STORED v3 (second role)')
    st = collections.Counter()
    for r in sec:
        if r['v3_stored'] == 'ACCEPTED' and r['new'] != 'ACCEPTED':
            st['v3 ACCEPTED -> new refused'] += 1
        elif r['v3_stored'] and r['v3_stored'] != 'ACCEPTED' \
                and r['new'] == 'ACCEPTED':
            st['v3 refused -> new ACCEPTED'] += 1
    for k, n in st.most_common():
        print('   %-36s %5d' % (k, n))

    if write:
        with io.open(OUT, 'w', encoding='utf-8', newline='') as f:
            f.write(json.dumps({
                '_': 'Phase 2.6 dry run: the reader at %s against the '
                     'working tree, on the same bytes. Analysis only: '
                     'not evidence, not v4, not canonical.' % base,
                'functions_changed': sorted(changed),
                'functions_added': sorted(added),
                'tally': dict(('%s|%s|%s' % k if isinstance(k, tuple)
                               else k, n) for k, n in tally.items()),
            }, ensure_ascii=False, sort_keys=True) + '\n')
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False,
                                   sort_keys=True) + '\n')
        print('\nwritten to data/phase26-impact.jsonl (%d rows)' % len(rows))


if __name__ == '__main__':
    main()
