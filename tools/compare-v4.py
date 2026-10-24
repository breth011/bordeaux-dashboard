# -*- coding: utf-8 -*-
"""v3 against v4: what the corrected reader and the corrected provenance
changed - and which of the two changed it.

    python tools/compare-v4.py
    python tools/compare-v4.py --write    data/v3-v4-comparison.jsonl

Reads the evidence store, data/phase26-impact.jsonl (Phase 2.6's dry
run) and data/provenance-audit.jsonl (Phase 2.5's). Writes nothing else,
and no evidence.

v4 differs from v3 in two ways at once: a new reader (Phase 2.6) and
files found by their own folder and hashed (Phase 2.5). Phase 2.6's dry
run ran the OLD reader on the RIGHT bytes, so for each context it gives
the answer with only the provenance corrected. Hence, per context:

    v3  -> base    the provenance effect (old reader, wrong -> right file)
    base -> v4     the reader effect     (same file, old -> new reader)

The dry run kept every context where either differed, so a context
absent from it had v3 == base == v4.
"""
import argparse
import collections
import importlib.util
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr
import evidence as EV
import evidence_store as ST

OUT = ROOT + 'data/v3-v4-comparison.jsonl'
UNRESOLVED = ('NOT_IDENTIFIED', 'AMBIGUOUS_WINE')
MISSING_V = (2008, 2009, 2010, 2015, 2016)


def ctx_key(d):
    return EV.row_key(d)[:-1]


def jl(path):
    out = []
    if not os.path.exists(path):
        return out
    with io.open(path, encoding='utf-8') as f:
        for i, line in enumerate(f):
            d = json.loads(line)
            if i == 0 and '_' in d:
                continue
            out.append(d)
    return out


def kind(code):
    if code == 'ACCEPTED':
        return 'ACCEPTED'
    if code in UNRESOLVED:
        return 'UNRESOLVED'
    if code == 'GUARD_HAS_NO_CUVEE_MODE':
        return 'NOT_EVALUATED'
    return 'REFUSED'


def pct(n, d):
    return '%5.1f%%' % (100.0 * n / d) if d else '   -  '


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()

    v3, v4 = {}, {}
    n3 = n4 = 0
    for d in ST.iter_rows([3]):
        v3[ctx_key(d)] = d
        n3 += 1
    for d in ST.iter_rows([4]):
        v4[ctx_key(d)] = d
        n4 += 1
    fails = list(ST.iter_failures(4))
    both = set(v3) & set(v4)
    only3 = set(v3) - set(v4)
    only4 = set(v4) - set(v3)

    print('THE RUN')
    print('-' * 70)
    print('   v3 rows %d (%d contexts), v4 rows %d (%d contexts)'
          % (n3, len(v3), n4, len(v4)))
    print('   v4 duplicate identities: %d' % (n4 - len(v4)))
    print('   v4 provenance failures: %d  %s' % (len(fails), dict(
        collections.Counter(f['code'] for f in fails))))
    roles = collections.Counter((d.get('ctx') or {}).get('target_role')
                                for d in v4.values())
    print('   v4 by target role: %s' % dict(roles))
    withv = sum(1 for d in v4.values()
                if (d.get('ctx') or {}).get('target_vintage'))
    print('   v4 with a target vintage %d, without %d'
          % (withv, len(v4) - withv))
    att = sum(1 for d in v4.values() if (d.get('ctx') or {}).get('estate'))
    print('   v4 contexts on attributed artifacts %d, unattributed %d'
          % (att, len(v4) - att))
    readers = collections.Counter(d.get('reader') for d in v4.values())
    gits = collections.Counter(((d.get('git') or {}).get('commit'),
                                (d.get('git') or {}).get('dirty'))
                               for d in v4.values())
    print('   v4 readers %s' % dict(readers))
    print('   v4 git %s' % dict(gits))

    print('\nPOPULATION')
    print('-' * 70)
    print('   same context in v3 and v4   %6d' % len(both))
    print('   in v3 only (no longer asked) %5d' % len(only3))
    print('   in v4 only (newly asked)     %5d' % len(only4))
    why3 = collections.Counter()
    fail_art = set((f['artifact'], (f.get('ctx') or {}).get('folder'))
                   for f in fails)
    for k in only3:
        d = v3[k]
        art = (d['artifact'], (d.get('ctx') or {}).get('folder'))
        why3['its artifact is now a provenance failure'
             if art in fail_art else 'other'] += 1
    for k, n in why3.most_common():
        print('      v3-only: %-44s %5d' % (k, n))

    # The dry run: old reader on the right bytes.
    base = {}
    for r in jl(ROOT + 'data/phase26-impact.jsonl'):
        if r['unattributed']:
            k = (r['artifact'], r['folder'], None, r['estate'], r['role'],
                 r['target_vintage'])
        else:
            k = (r['artifact'], r['folder'], r['estate'], None, r['role'],
                 r['target_vintage'])
        base[k] = r['base']

    def bkey(d):
        c = d.get('ctx') or {}
        return (d['artifact'], c.get('folder'), c.get('estate'),
                c.get('target_estate'), c.get('target_role'),
                c.get('target_vintage'))

    rows = []
    cls = collections.Counter()
    trans = collections.Counter()
    cause = collections.Counter()
    for k in both:
        a3, a4 = v3[k], v4[k]
        c3, c4 = a3.get('code'), a4.get('code')
        if c3 == c4:
            if (a3.get('raw') or '') != (a4.get('raw') or ''):
                cls['reason-only change'] += 1
            else:
                cls['unchanged verdict'] += 1
            continue
        cls['changed verdict'] += 1
        t = '%s -> %s' % (kind(c3), kind(c4))
        if kind(c3) == kind(c4):
            t = '%s -> different %s' % (kind(c3), kind(c4).lower())
        trans[t] += 1
        b = base.get(bkey(a4))
        if b is None:
            why = 'unexplained (not in the dry run)'
        elif b == c3 and b != c4:
            why = 'reader'
        elif b == c4 and b != c3:
            why = 'provenance'
        elif b != c3 and b != c4:
            why = 'both'
        else:
            why = 'unexplained'
        cause[why] += 1
        rows.append({'ctx': a4.get('ctx'), 'artifact': a4['artifact'],
                     'v3': c3, 'v4': c4, 'base': b, 'cause': why,
                     'v4_why': (a4.get('raw') or '')[:160],
                     'v3_why': (a3.get('raw') or '')[:160],
                     'read': a4.get('read')})
    print('\nSAME CONTEXT, v3 -> v4')
    print('-' * 70)
    for k, n in cls.most_common():
        print('   %-34s %6d  %s' % (k, n, pct(n, len(both))))
    print('   changed, by transition:')
    for k, n in trans.most_common():
        print('      %-40s %5d' % (k, n))
    print('   changed, by cause:')
    for k, n in cause.most_common():
        print('      %-40s %5d' % (k, n))

    # ------------------------------------------------- grand vin
    g = [r for r in rows if r['ctx'].get('target_role') == 'grand']
    print('\nGRAND VIN')
    print('-' * 70)
    gb = sum(1 for k in both if v4[k]['ctx'].get('target_role') == 'grand')
    print('   %d contexts in both, %d changed' % (gb, len(g)))
    for k, n in collections.Counter(r['cause'] for r in g).most_common():
        print('      cause %-20s %5d' % (k, n))
    for r in [x for x in g if x['cause'] != 'provenance'][:10]:
        print('      NOT PROVENANCE: %s %s %s -> %s'
              % (r['artifact'][:50], r['ctx'].get('target_vintage'),
                 r['v3'], r['v4']))

    # ------------------------------------------------- second wine
    sec3 = [k for k in v3 if v3[k]['ctx'].get('target_role') == 'second']
    sec4 = [k for k in v4 if v4[k]['ctx'].get('target_role') == 'second']
    sb = [k for k in both if v4[k]['ctx'].get('target_role') == 'second']
    acc3 = sum(1 for k in sec3 if v3[k]['code'] == 'ACCEPTED')
    acc4 = sum(1 for k in sec4 if v4[k]['code'] == 'ACCEPTED')
    s = [r for r in rows if r['ctx'].get('target_role') == 'second']
    wd = [r for r in s if r['v3'] == 'ACCEPTED']
    ad = [r for r in s if r['v4'] == 'ACCEPTED']
    print('\nSECOND WINE')
    print('-' * 70)
    print('   contexts v3 %d, v4 %d, in both %d'
          % (len(sec3), len(sec4), len(sb)))
    print('   accepted v3 %d, v4 %d' % (acc3, acc4))
    print('   withdrawn %d, added %d, refusal->other refusal %d'
          % (len(wd), len(ad), sum(1 for r in s if r['v3'] != 'ACCEPTED'
                                   and r['v4'] != 'ACCEPTED')))
    print('   unchanged refusals %d' % sum(
        1 for k in sb if v3[k]['code'] == v4[k]['code'] != 'ACCEPTED'))
    print('   v4 unresolved %d, v4 UNLISTED_WINE %d' % (
        sum(1 for k in sec4 if v4[k]['code'] in UNRESOLVED),
        sum(1 for k in sec4 if v4[k]['code'] == 'UNLISTED_WINE')))
    print('   WITHDRAWN:')
    for r in sorted(wd, key=lambda x: (x['ctx'].get('estate')
                                       or x['ctx'].get('target_estate'),
                                       x['artifact'])):
        c = r['ctx']
        print('      %-18s %-26s %s %s' % (
            (c.get('estate') or c.get('target_estate'))[:18],
            (c.get('target_wine') or '')[:26], c.get('target_vintage'),
            r['artifact'][:60]))
        print('         v3 %s | v4 %s: %s  [cause: %s]'
              % (r['v3'], r['v4'], r['v4_why'][:80], r['cause']))
    print('   ADDED, by estate: %s' % dict(collections.Counter(
        (r['ctx'].get('estate') or r['ctx'].get('target_estate'))
        for r in ad)))
    print('   added, by cause: %s' % dict(collections.Counter(
        r['cause'] for r in ad)))

    # ------------------------------------------------------- Echo
    DG = importlib.util.spec_from_file_location(
        'dg', ROOT + 'tools/diagnose-second-mode.py')
    dg = importlib.util.module_from_spec(DG)
    DG.loader.exec_module(dg)
    E = sr.estates(ROOT)
    e = E['lynch-bages']
    docs = collections.defaultdict(list)
    for d in v4.values():
        c = d.get('ctx') or {}
        if c.get('estate') == 'lynch-bages' and c.get('target_role') == 'second':
            docs[(d['artifact'], c.get('folder'))].append(d)
    lab = collections.Counter()
    acc = collections.Counter()
    for (fn, fo), ds in docs.items():
        lb = dg.population(fn, e)
        lab[lb] += 1
        if any(x['code'] == 'ACCEPTED' for x in ds):
            acc[lb] += 1
    print('\nECHO (v4 evidence, Lynch-Bages documents asked as the Echo)')
    print('-' * 70)
    for lb in ('second', 'grand vin', 'other cuvee'):
        print('   %-12s documents %4d, accepted for some vintage %4d'
              % (lb, lab[lb], acc[lb]))
    echo_ctx = [x for (fn, fo), ds in docs.items()
                if dg.population(fn, e) == 'second' for x in ds]
    print('   Echo contexts %d: %s' % (len(echo_ctx), dict(
        collections.Counter(x['code'] for x in echo_ctx))))
    for y in MISSING_V:
        h = [x for x in echo_ctx if x['ctx'].get('target_vintage') == y]
        ok = [x for x in h if x['code'] == 'ACCEPTED']
        print('   %d: %d context(s), %d accepted: %s' % (
            y, len(h), len(ok), ', '.join(sorted(set(
                x['artifact'] for x in ok)))[:70]))

    # ------------------------------------------------- provenance
    audit = jl(ROOT + 'data/provenance-audit.jsonl')
    wrong = [r for r in audit if r['bytes_differ']]
    same = [r for r in audit if r['class'] == 'old read another folder, '
                                              'same bytes']
    keyset = set((r['artifact'], r['folder']) for r in wrong)
    pv = [(k, v3.get(k), v4[k]) for k in v4
          if (v4[k]['artifact'], v4[k]['ctx'].get('folder')) in keyset]
    ch = [x for x in pv if x[1] and x[1]['code'] != x[2]['code']]
    print('\nPROVENANCE')
    print('-' * 70)
    print('   wrong-folder rows (Phase 2.5 audit): %d, of which different '
          'bytes %d' % (len(wrong) + len(same), len(wrong)))
    print('   v4 contexts on the different-bytes artifacts: %d; their '
          'verdict changed from v3: %d' % (len(pv), len(ch)))
    ok = sum(1 for _, _, d4 in pv
             if d4['read']['sha256'] == next(
                 r['actual_sha256'] for r in wrong
                 if r['artifact'] == d4['artifact']
                 and r['folder'] == d4['ctx'].get('folder')))
    print('   ...v4 read.sha256 equals the audit\'s actual hash: %d of %d'
          % (ok, len(pv)))
    for k, d3, d4 in ch[:12]:
        r = next(r for r in wrong if r['artifact'] == d4['artifact']
                 and r['folder'] == d4['ctx'].get('folder'))
        print('      %s | %s %s: %s -> %s' % (
            d4['artifact'][:40], d4['ctx'].get('target_role'),
            d4['ctx'].get('target_vintage'), d3['code'], d4['code']))
        print('         old %s %s / v4 %s %s' % (
            r['old_path'][:40], r['old_sha256'][:10],
            d4['read']['path'][:40], d4['read']['sha256'][:10]))
    print('   failures by code: %s' % dict(collections.Counter(
        f['code'] for f in fails)))

    if a.write:
        with io.open(OUT, 'w', encoding='utf-8', newline='') as f:
            f.write(json.dumps({
                '_': 'v3 against v4, per context, with the cause of each '
                     'change: reader, provenance or both. Analysis only, '
                     'not evidence. tools/compare-v4.py.',
                'classes': dict(cls), 'transitions': dict(trans),
                'causes': dict(cause)}, ensure_ascii=False,
                sort_keys=True) + '\n')
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False, sort_keys=True)
                        + '\n')
        print('\nwritten to data/v3-v4-comparison.jsonl (%d changed '
              'contexts)' % len(rows))


if __name__ == '__main__':
    main()
