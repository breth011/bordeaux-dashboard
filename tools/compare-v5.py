# -*- coding: utf-8 -*-
"""v4 against v5: what the Phase 2.9 grand-vin reader changed, checked
against what its dry run predicted.

    python tools/compare-v5.py
    python tools/compare-v5.py --write    data/v4-v5-comparison.json

Reads the evidence store, data/phase29-grand-dryrun.json (Phase 2.9's
prediction) and data/provenance-audit.jsonl. Writes nothing else, and
no evidence.

v4 and v5 share their provenance machinery and their decision universe,
and differ in one thing: the reader (c12eb3102b45 -> 7e8cfed1c24e).
Phase 2.9 re-judged every v4 grand-vin and second-wine decision with the
new reader on the same files and predicted exactly which verdicts would
change. This checks v5 against that prediction context by context.
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

OUT = ROOT + 'data/v4-v5-comparison.json'
UNRESOLVED = ('NOT_IDENTIFIED', 'AMBIGUOUS_WINE')
MISSING_V = (2008, 2009, 2010, 2015, 2016)


def kind(code):
    if code == 'ACCEPTED':
        return 'ACCEPTED'
    if code in UNRESOLVED:
        return 'UNRESOLVED'
    if code == 'GUARD_HAS_NO_CUVEE_MODE':
        return 'NOT_EVALUATED'
    return 'REFUSED'


def ckey(d):
    return EV.row_key(d)[:-1]


def pkey(d):
    """The key Phase 2.9's dry run used."""
    c = d.get('ctx') or {}
    return (c.get('folder'), d['artifact'],
            c.get('estate') or c.get('target_estate'),
            c.get('target_role'), c.get('target_vintage'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    out = {}

    v4 = dict((ckey(d), d) for d in ST.iter_rows([4]))
    v5rows = list(ST.iter_rows([5]))
    v5 = dict((ckey(d), d) for d in v5rows)
    fails = list(ST.iter_failures(5))
    fails4 = list(ST.iter_failures(4))

    # ------------------------------------------------------------- run
    roles = collections.Counter(d['ctx'].get('target_role') for d in v5rows)
    withv = sum(1 for d in v5rows if d['ctx'].get('target_vintage'))
    att = sum(1 for d in v5rows if d['ctx'].get('estate'))
    readers = collections.Counter(d.get('reader') for d in v5rows)
    gits = collections.Counter((d['git']['commit'], d['git']['dirty'])
                               for d in v5rows)
    run = {'decisions': len(v5rows), 'distinct_identities': len(v5),
           'by_role': dict(roles), 'with_vintage': withv,
           'without_vintage': len(v5rows) - withv,
           'attributed': att, 'unattributed': len(v5rows) - att,
           'readers': dict(readers),
           'git': ['%s dirty=%s: %d' % (c, dt, n)
                   for (c, dt), n in gits.items()],
           'failures': dict(collections.Counter(f['code'] for f in fails)),
           'failures_v4': dict(collections.Counter(f['code']
                                                   for f in fails4))}
    out['run'] = run
    print('V5 RUN')
    for k, v in run.items():
        print('   %-20s %s' % (k, v))

    # -------------------------------------------------- reconciliation
    both = set(v4) & set(v5)
    only4, only5 = set(v4) - set(v5), set(v5) - set(v4)
    cls = collections.Counter()
    changes = []
    prov_only = 0
    for k in both:
        a4, a5 = v4[k], v5[k]
        if a4['code'] == a5['code']:
            if (a4.get('raw') or '') != (a5.get('raw') or ''):
                cls['REASON_ONLY'] += 1
            else:
                cls['UNCHANGED'] += 1
            if a4['read'] != a5['read']:
                prov_only += 1
            continue
        k4, k5 = kind(a4['code']), kind(a5['code'])
        name = ('%s_TO_%s' % (k4, k5) if k4 != k5
                else '%s_TO_DIFFERENT_%s' % (k4, k5))
        cls[name] += 1
        changes.append({'key': list(pkey(a5)), 'v4': a4['code'],
                        'v5': a5['code'], 'class': name,
                        'v4_why': (a4.get('raw') or '')[:160],
                        'v5_why': (a5.get('raw') or '')[:160]})
    out['reconciliation'] = {
        'same_questions': len(both), 'only_v4': len(only4),
        'only_v5': len(only5), 'classes': dict(cls),
        'same_verdict_different_read': prov_only}
    print('\nV4 -> V5, SAME QUESTIONS: %d (v4 only %d, v5 only %d)'
          % (len(both), len(only4), len(only5)))
    for k, n in cls.most_common():
        print('   %-36s %6d' % (k, n))
    print('   same verdict, different file or hash read: %d' % prov_only)

    # -------------------------------------------- against the prediction
    pred = json.load(io.open(ROOT + 'data/phase29-grand-dryrun.json',
                             encoding='utf-8'))
    predicted = set((r['folder'], r['artifact'], r['estate'], r['role'],
                     r['vintage']) for r in pred['v4_changed'])
    predicted_new = dict(((r['folder'], r['artifact'], r['estate'],
                           r['role'], r['vintage']), r['new'])
                         for r in pred['v4_changed'])
    observed = set(tuple(c['key']) for c in changes)
    obs_new = dict((tuple(c['key']), c['v5']) for c in changes)
    agree = [k for k in observed & predicted if obs_new[k] == predicted_new[k]]
    out['prediction'] = {
        'predicted': len(predicted), 'observed': len(observed),
        'both_same_verdict': len(agree),
        'observed_not_predicted': sorted(map(list, observed - predicted)),
        'predicted_not_observed': sorted(map(list, predicted - observed))}
    print('\nAGAINST THE PHASE 2.9 DRY RUN')
    print('   predicted %d, observed %d, identical %d, unpredicted %d, '
          'missed %d' % (len(predicted), len(observed), len(agree),
                         len(observed - predicted), len(predicted - observed)))

    # -------------------------------------------------------- per role
    for role in ('grand', 'second', 'other'):
        rr = [k for k in both if v5[k]['ctx'].get('target_role') == role]
        acc4 = sum(1 for k in v4 if v4[k]['ctx'].get('target_role') == role
                   and v4[k]['code'] == 'ACCEPTED')
        acc5 = sum(1 for k in v5 if v5[k]['ctx'].get('target_role') == role
                   and v5[k]['code'] == 'ACCEPTED')
        ch = [c for c in changes if c['key'][3] == role]
        tr = collections.Counter(c['class'] for c in ch)
        out['role_' + role] = {'same_questions': len(rr), 'accepted_v4': acc4,
                               'accepted_v5': acc5, 'changes': dict(tr)}
        print('\n%s: same questions %d, accepted v4 %d -> v5 %d, changed %d %s'
              % (role.upper(), len(rr), acc4, acc5, len(ch), dict(tr)))
    other = [d for d in v5rows if d['ctx'].get('target_role') == 'other']
    out['other_cuvees'] = {
        'contexts': len(other),
        'not_evaluated': sum(1 for d in other
                             if d['code'] == 'GUARD_HAS_NO_CUVEE_MODE'),
        'evaluated': sum(1 for d in other
                         if d['code'] != 'GUARD_HAS_NO_CUVEE_MODE')}
    print('   other cuvees: %s' % out['other_cuvees'])
    wd = [c for c in changes if c['key'][3] == 'grand'
          and c['v4'] == 'ACCEPTED']
    out['grand_withdrawals'] = wd
    by = collections.Counter((c['key'][2], c['v5_why'].split(': ', 1)[-1][:40])
                             for c in wd)
    print('   grand-vin withdrawals by estate / wine named:')
    for k, n in by.most_common():
        print('      %-30s %-40s %3d' % (k[0][:30], k[1], n))

    # ------------------------------------------------------------ Echo
    DG = importlib.util.spec_from_file_location(
        'dg', ROOT + 'tools/diagnose-second-mode.py')
    dg = importlib.util.module_from_spec(DG)
    DG.loader.exec_module(dg)
    E = sr.estates(ROOT)
    e = E['lynch-bages']
    docs = collections.defaultdict(list)
    for d in v5rows:
        c = d['ctx']
        if c.get('estate') == 'lynch-bages' and c.get('target_role') == 'second':
            docs[(d['artifact'], c.get('folder'))].append(d)
    lab, acc = collections.Counter(), collections.Counter()
    for (fn, fo), ds in docs.items():
        lb = dg.population(fn, e)
        lab[lb] += 1
        acc[lb] += any(x['code'] == 'ACCEPTED' for x in ds)
    echo_ctx = [x for (fn, fo), ds in docs.items()
                if dg.population(fn, e) == 'second' for x in ds]
    years = {}
    for y in MISSING_V:
        years[y] = sorted(set(x['artifact'] for x in echo_ctx
                              if x['ctx'].get('target_vintage') == y
                              and x['code'] == 'ACCEPTED'))
    out['echo'] = {'documents': dict(lab), 'accepted_documents': dict(acc),
                   'echo_contexts': dict(collections.Counter(
                       x['code'] for x in echo_ctx)),
                   'missing_vintages': years}
    print('\nECHO %s' % out['echo'])

    # ------------------------------------------------------- conflicts
    def conflicts(rows):
        accd = collections.defaultdict(set)
        for d in rows:
            if d['code'] != 'ACCEPTED':
                continue
            c = d['ctx']
            accd[(c.get('folder'), d['artifact'])].add(
                (c.get('estate') or c.get('target_estate'),
                 c.get('target_role'), c.get('target_wine'),
                 c.get('target_vintage')))
        res = {}
        for doc, ts in accd.items():
            rel = []
            byv = collections.defaultdict(set)
            for est, role, wine, yr in ts:
                byv[(est, yr)].add(role)
            if any({'grand', 'second'} <= r for r in byv.values()):
                rel.append('GRAND_AND_SECOND')
            if any({'grand', 'other'} <= r for r in byv.values()):
                rel.append('GRAND_AND_OTHER')
            byw = collections.defaultdict(set)
            for est, role, wine, yr in ts:
                if yr:
                    byw[(est, wine)].add(yr)
            if any(len(y) > 1 for y in byw.values()):
                rel.append('SEVERAL_VINTAGES')
            if len(set(t[0] for t in ts)) > 1:
                rel.append('SEVERAL_ESTATES')
            if rel:
                res[doc] = rel
        return res
    c4 = conflicts(ST.iter_rows([4]))
    c5 = conflicts(v5rows)
    rel5 = collections.Counter(r for rs in c5.values() for r in rs)
    rel4 = collections.Counter(r for rs in c4.values() for r in rs)
    tertre = sorted(doc for doc, rs in c4.items()
                    if 'GRAND_AND_SECOND' in rs and doc[0] == 'du-tertre')
    out['conflicts'] = {
        'v4_documents': len(c4), 'v5_documents': len(c5),
        'v4_relations': dict(rel4), 'v5_relations': dict(rel5),
        'tertre_v4': [d[1] for d in tertre],
        'tertre_in_v5_grand_and_second': [d[1] for d in tertre
                                          if 'GRAND_AND_SECOND'
                                          in c5.get(d, [])],
        'new_in_v5': sorted(map(list, set(c5) - set(c4))),
        'gone_in_v5': len(set(c4) - set(c5))}
    print('\nCONFLICTS v4 %d -> v5 %d; v4 %s; v5 %s' % (
        len(c4), len(c5), dict(rel4), dict(rel5)))
    print('   du Tertre GRAND_AND_SECOND: v4 %d, still in v5 %d'
          % (len(tertre), len(out['conflicts']['tertre_in_v5_grand_and_second'])))
    print('   new in v5: %d, gone: %d' % (len(out['conflicts']['new_in_v5']),
                                          out['conflicts']['gone_in_v5']))

    # ------------------------------------------------------ edge cases
    def verdicts(pred_fn):
        return sorted(set((d['artifact'], d['ctx'].get('target_vintage'),
                           v4.get(ckey(d), {}).get('code'), d['code'])
                          for d in v5rows
                          if d['ctx'].get('target_role') == 'grand'
                          and pred_fn(d)))
    edges = {
        'guiraud_G': verdicts(lambda d: d['ctx'].get('estate') == 'guiraud'
                              and d['artifact'].upper().startswith('G')),
        'smith_HDS_PHL': verdicts(lambda d: d['ctx'].get('estate')
                                  == 'smith-haut-lafitte'
                                  and ('HDS' in d['artifact']
                                       or 'PHL' in d['artifact'])),
        'fieuzal_2022': verdicts(lambda d: d['ctx'].get('estate')
                                 == 'de-fieuzal'
                                 and d['artifact'].startswith(
                                     'de-fieuzal-2022')),
        'chevalier_2014': verdicts(lambda d: d['ctx'].get('estate')
                                   == 'domaine-de-chevalier'
                                   and d['artifact'].startswith(
                                       'Domaine-de-Chevalier-2014-FT')),
        'terrasses': verdicts(lambda d: 'TERRASSES-DE-SAINT-CHRISTOPHE'
                              in d['artifact']),
        'malle_weddings': verdicts(lambda d: d['ctx'].get('estate')
                                   == 'de-malle'
                                   and 'MARIAGES' in d['artifact'].upper()),
    }
    out['edge_cases'] = edges
    print('\nEDGE CASES (artifact, vintage, v4, v5)')
    for k, v in edges.items():
        print('   %s:' % k)
        for x in v:
            print('      %-62s %s %s -> %s' % (x[0][:62], x[1], x[2], x[3]))

    # ------------------------------------------------------ provenance
    audit = []
    p = ROOT + 'data/provenance-audit.jsonl'
    with io.open(p, encoding='utf-8') as f:
        f.readline()
        audit = [json.loads(l) for l in f]
    wrong = dict(((r['folder'], r['artifact']), r) for r in audit
                 if r['bytes_differ'])
    moved = set((r['folder'], r['artifact']) for r in audit
                if r['class'].startswith('old read another'))
    on_wrong = [d for d in v5rows
                if (d['ctx'].get('folder'), d['artifact']) in wrong]
    ok = sum(1 for d in on_wrong if d['read']['sha256'] ==
             wrong[(d['ctx'].get('folder'), d['artifact'])]['actual_sha256'])
    out['provenance'] = {
        'wrong_folder_rows': len(moved), 'wrong_bytes_rows': len(wrong),
        'v5_decisions_on_wrong_bytes_files': len(on_wrong),
        'v5_hash_equals_audit': ok,
        'v5_decisions_on_wrong_folder_files': sum(
            1 for d in v5rows
            if (d['ctx'].get('folder'), d['artifact']) in moved),
        'failures_v5': run['failures'], 'failures_v4': run['failures_v4']}
    print('\nPROVENANCE %s' % out['provenance'])

    if a.write:
        with io.open(OUT, 'w', encoding='utf-8', newline='') as f:
            f.write(json.dumps(out, ensure_ascii=False, sort_keys=True,
                               indent=1) + '\n')
        print('\nwritten to data/v4-v5-comparison.json')


if __name__ == '__main__':
    main()
