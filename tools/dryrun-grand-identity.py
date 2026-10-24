# -*- coding: utf-8 -*-
"""Phase 2.9: what the grand-vin identity rule (_grand_mark) changes -
measured in memory, never written as evidence.

    python tools/dryrun-grand-identity.py --universe
    python tools/dryrun-grand-identity.py --v4            (about 10 min)
    python tools/dryrun-grand-identity.py --summary       (from the cache)
    python tools/dryrun-grand-identity.py --write         data/phase29-grand-dryrun.json

The OLD reader is tools/sheetreader.py as committed at --base (5778417),
loaded from git into a temporary module; the NEW reader is the working
tree's. Nothing is appended to data/evidence/.

  --universe  every one of the 195 other wines: its old and new
              grand-vin mark, the grand-vin check's name tests on file
              names written for it (old and new reader), and whether the
              new mark collides with the grand vin's own name or with
              another of the estate's wines.
  --v4        every v4 grand-vin decision and every v4 second-wine
              decision, re-judged by the NEW reader on the exact file v4
              read (read.path) and compared with the recorded v4 verdict,
              which is the OLD reader's (fingerprint c12eb3102b45, the
              same reader as --base). Each changed verdict is re-judged
              by the OLD module too, to prove the change is the rule's
              and not the harness's.
"""
import argparse
import collections
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as NEW
import evidence as EV
import evidence_store as ST

CACHE = ROOT + 'reports/phase29-v4-cache.json'
OUT = ROOT + 'data/phase29-grand-dryrun.json'


def load_old(base):
    src = subprocess.check_output(['git', 'show', '%s:tools/sheetreader.py'
                                   % base], cwd=ROOT)
    d = tempfile.mkdtemp(prefix='sr29-')
    p = os.path.join(d, 'sheetreader_base.py')
    with open(p, 'wb') as f:
        f.write(src)
    spec = importlib.util.spec_from_file_location('sheetreader_base', p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def load_audit():
    spec = importlib.util.spec_from_file_location(
        'audit_grand', ROOT + 'tools/audit-grand-marks.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def probe(sr, fn, e, others, new):
    v = sr.whose_sheet(None, fn, e['name'], e.get('cuvees') or (),
                       e.get('second'), e.get('cat'), names_only=True)
    if v:
        return v.get('why')
    for o in [e.get('second')] + list(others):
        if not o:
            continue
        mk = (sr.mark_of(o, e['name'], against_grand=True) if new
              else sr.mark_of(o, e['name']))
        if mk and sr.says_in_name(fn, mk):
            return 'names_another_wine (filename): %s' % o
    return None


def universe(OLD, AG):
    E = NEW.estates(ROOT)
    _, rows28, _ = AG.audit()
    out = []
    for r in rows28:
        e = E[r['estate']]
        o, g = r['wine'], r['grand']
        others = list(dict.fromkeys(
            [w for w in (e.get('cuvees') or ()) if w]
            + ([e['second']] if e.get('second') else [])))
        others = [w for w in others if w != g]
        old_mk, new_mk = NEW.mark_of(o, g), NEW.mark_of(o, g, against_grand=True)
        forms = AG.forms(o)
        op = dict((fn, probe(OLD, fn, e, others, False)) for fn in forms)
        np_ = dict((fn, probe(NEW, fn, e, others, True)) for fn in forms)
        o_pass = [f for f, v in op.items() if not v]
        n_pass = [f for f, v in np_.items() if not v]
        # New collisions: the new mark found in the grand vin's own name,
        # or in another of the estate's wines' names.
        hits_grand = bool(new_mk) and NEW.says(g, new_mk)
        hits_sib = sorted(s for s in others if s != o and new_mk
                          and NEW.says(s, new_mk)
                          and NEW.wset(s) != NEW.wset(o))
        old_hits_sib = sorted(s for s in others if s != o and old_mk
                              and NEW.says(s, old_mk)
                              and NEW.wset(s) != NEW.wset(o))
        # Ambiguity for the GRAND-VIN check means a mark the grand vin's
        # own name carries: that would refuse grand-vin sheets. A mark
        # another of the estate's wines also carries ("hauts de smith"
        # inside "Les Hauts de Smith Blanc") is refused either way in
        # grand-vin mode; it changes only which wine a refusal names,
        # and is reported apart as sibling_overlap.
        if not r['identity']['own']:
            cls = 'EXACT_CANONICAL_COLLISION'
        elif hits_grand:
            cls = 'CREATES_AMBIGUITY'
        elif o_pass and not n_pass:
            cls = 'PREVENTS_FALSE_COLLISION'
        elif n_pass:
            cls = 'REQUIRES_INSPECTION'
        elif new_mk != old_mk:
            cls = 'STRENGTHENS_DISTINCTION'
        else:
            cls = 'CHANGES_NOTHING'
        out.append({
            'estate': r['estate'], 'grand': g, 'wine': o,
            'phase28_category': r['category'],
            'old_mark': old_mk, 'new_mark': new_mk,
            'old_probe_passes': o_pass, 'new_probe_passes': n_pass,
            'new_mark_in_grand_name': hits_grand,
            'new_mark_in_siblings': hits_sib,
            'old_mark_in_siblings': old_hits_sib,
            'sibling_overlap': sorted(set(hits_sib) - set(old_hits_sib)),
            'own_tokens': r['identity']['own'],
            'class': cls,
            'v4_grand_decision_ids': r['v4']['grand_decision_ids'],
        })
    return out


def v4_pass(OLD):
    E = NEW.estates(ROOT)
    rows = [d for d in ST.iter_rows([4])
            if (d.get('ctx') or {}).get('target_role') in ('grand', 'second')]
    res = []
    for n, d in enumerate(rows, 1):
        if n % 1000 == 0:
            sys.stderr.write('  %d of %d\n' % (n, len(rows)))
            sys.stderr.flush()
        c = d['ctx']
        eid = c.get('estate') or c.get('target_estate')
        e = E.get(eid) or {}
        p = os.path.join(ROOT, 'sources', *d['read']['path'].split('/'))
        sec = c.get('target_role') == 'second'
        try:
            v = NEW.whose_sheet(p, d['artifact'], e.get('name'),
                                e.get('cuvees') or (), e.get('second'),
                                e.get('cat'), year=c.get('target_vintage'),
                                is_second=sec)
        except Exception as ex:
            v = {'why': 'a guard could not read it: %s' % type(ex).__name__}
        new = 'ACCEPTED' if not v else EV.code_for(v.get('why'))[0]
        row = {'folder': c.get('folder'), 'artifact': d['artifact'],
               'estate': eid, 'role': c.get('target_role'),
               'vintage': c.get('target_vintage'),
               'v4': d.get('code'), 'new': new,
               'new_why': '' if not v else (v.get('why') or '')[:160]}
        if new != d.get('code'):
            try:
                ov = OLD.whose_sheet(p, d['artifact'], e.get('name'),
                                     e.get('cuvees') or (), e.get('second'),
                                     e.get('cat'),
                                     year=c.get('target_vintage'),
                                     is_second=sec)
            except Exception as ex:
                ov = {'why': 'a guard could not read it: %s'
                             % type(ex).__name__}
            row['old_reproduces_v4'] = (
                ('ACCEPTED' if not ov else EV.code_for(ov.get('why'))[0])
                == d.get('code'))
        res.append(row)
    return res


def summarise(uni, v4rows):
    out = {}
    if uni:
        cls = collections.Counter(u['class'] for u in uni)
        print('UNIVERSE: %d wines' % len(uni))
        for k, n in sorted(cls.items()):
            print('   %-28s %4d' % (k, n))
        out['universe_classes'] = dict(cls)
    if v4rows:
        for role in ('grand', 'second'):
            rr = [r for r in v4rows if r['role'] == role]
            tr = collections.Counter(
                ('ACC' if r['v4'] == 'ACCEPTED' else 'REF',
                 'ACC' if r['new'] == 'ACCEPTED' else 'REF') for r in rr)
            ch = [r for r in rr if r['v4'] != r['new']]
            print('\nV4 %s: %d decisions, %d changed verdicts' % (
                role, len(rr), len(ch)))
            for k in (('ACC', 'ACC'), ('ACC', 'REF'), ('REF', 'ACC'),
                      ('REF', 'REF')):
                print('   %s -> %s  %6d' % (k[0], k[1], tr.get(k, 0)))
            print('   changed verdicts the OLD module reproduces as v4: '
                  '%d of %d' % (sum(1 for r in ch if r.get(
                      'old_reproduces_v4')), len(ch)))
            out['v4_%s' % role] = {
                'decisions': len(rr), 'changed': len(ch),
                'transitions': dict(('%s->%s' % k, n)
                                    for k, n in tr.items())}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='5778417')
    ap.add_argument('--universe', action='store_true')
    ap.add_argument('--v4', action='store_true')
    ap.add_argument('--summary', action='store_true')
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    OLD = load_old(a.base)
    AG = load_audit()
    cache = {}
    if os.path.exists(CACHE):
        cache = json.load(io.open(CACHE, encoding='utf-8'))
    if a.universe or a.write:
        cache['universe'] = universe(OLD, AG)
    if a.v4:
        cache['v4'] = v4_pass(OLD)
    os.makedirs(ROOT + 'reports', exist_ok=True)
    with io.open(CACHE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False)
    s = summarise(cache.get('universe'), cache.get('v4'))
    if a.write:
        doc = {'_': 'Phase 2.9 dry run of the grand-vin identity rule. '
                    'Analysis only: not evidence, not canonical. '
                    'tools/dryrun-grand-identity.py.',
               'base': a.base,
               'reader_new': EV.reader_fingerprint(),
               'summary': s,
               'universe': cache.get('universe'),
               'v4_changed': [r for r in cache.get('v4', [])
                              if r['v4'] != r['new']]}
        with io.open(OUT, 'w', encoding='utf-8', newline='') as f:
            f.write(json.dumps(doc, ensure_ascii=False, sort_keys=True,
                               indent=1) + '\n')
        print('\nwritten to data/phase29-grand-dryrun.json')


if __name__ == '__main__':
    main()
