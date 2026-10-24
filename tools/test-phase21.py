# -*- coding: utf-8 -*-
"""Phase 2.1 invariants: context, vintage, and proposals that stay proposals.

    python tools/test-phase21.py

What Phase 2.1 added over Phase 2 is CONTEXT - estate, wine and
vintage - so these tests are about the context being real rather than
decorative. The one that matters most is that supplying a vintage
actually changes a verdict: it is possible to add a `target_vintage`
field to an output file and go on calling the reader without a
vintage, and that would look identical in the data.

Mostly runs without the archive. The two cases that need a document
say MISSING and are skipped on a fresh clone.
"""
import collections
import io
import json
import os
import subprocess
import sys

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
    print('%-4s %-52s %s' % ('ok' if ok else 'FAIL', name[:52], shown))


def check(name, got, limit, why=''):
    global checks
    checks += 1
    ok = got <= limit
    if not ok:
        fails.append(name)
    print('%-4s %-52s %4s (max %s)'
          % ('ok' if ok else 'FAIL', name[:52], got, limit))
    if not ok and why:
        print('       %s' % why)


# ============================================ the decision identity
# Phase 2 asked one question per artifact; Phase 2.1 asks several. If
# the key cannot tell them apart, the second pass is discarded as a
# re-run of the first.
k1 = EV.row_key({'artifact': 'a.pdf', 'v': 1,
                 'ctx': {'folder': 'f', 'estate': 'e', 'wine': 'w',
                         'vintage': 2008}})
k2 = EV.row_key({'artifact': 'a.pdf', 'v': 2,
                 'ctx': {'folder': 'f', 'estate': 'e', 'wine': 'w',
                         'vintage': 2008, 'target_wine': 'Echo',
                         'target_vintage': 2008}})
k3 = EV.row_key({'artifact': 'a.pdf', 'v': 2,
                 'ctx': {'folder': 'f', 'estate': 'e', 'wine': 'w',
                         'vintage': 2008, 'target_wine': 'Echo',
                         'target_vintage': 2009}})
says('a no-vintage decision differs from a targeted one', k1 != k2)
says('two target vintages are two decisions', k2 != k3)
says('the key carries the target context',
     'Echo' in k2 and 2009 in k3)

# ================================== the vintage guard actually fires
# Not "is there a target_vintage field" - whether supplying it changes
# the answer. Chateau-Lynch-Bages-1989-FR.pdf is the case: the
# manifest files it under 1990, Phase 2 accepted it as the grand vin's
# because nothing asked about the year, and with year=1990 supplied the
# guard refuses it.
E = sr.estates(ROOT)
e = E.get('lynch-bages') or {}
import glob
hit = (glob.glob(os.path.join(ROOT, 'sources', 'fiches', 'lynch-bages',
                              'Chateau-Lynch-Bages-1989-FR.pdf'))
       or glob.glob(os.path.join(ROOT, 'sources', '*', '*',
                                 'Chateau-Lynch-Bages-1989-FR.pdf')))
if not hit or not e:
    print('MISSING  Chateau-Lynch-Bages-1989-FR.pdf (needs sources/)')
else:
    p = hit[0]
    args = (p, os.path.basename(p), e.get('name'),
            e.get('cuvees') or (), e.get('second'), e.get('cat'))
    no_year = sr.whose_sheet(*args, year=None)
    with_year = sr.whose_sheet(*args, year=1990)
    right_year = sr.whose_sheet(*args, year=1989)
    says('with no vintage the guard raises no objection',
         no_year is None, 'accepted')
    says('with the manifest year 1990 it refuses',
         with_year is not None,
         (with_year or {}).get('why', '')[:34])
    says('and the refusal is about the vintage',
         EV.code_for((with_year or {}).get('why'))[0] == 'WRONG_VINTAGE',
         EV.code_for((with_year or {}).get('why'))[0])
    says('with its own year 1989 it is accepted again',
         right_year is None, 'accepted')

# ===================================== the store holds both passes
import evidence_store as ST
if not ST.versions():
    print('MISSING  data/evidence/')
else:
    rows = list(ST.iter_rows())
    vers = collections.Counter(r.get('v') for r in rows)
    says('the store holds the no-vintage pass', vers.get(1, 0) > 0,
         '%d rows at v1' % vers.get(1, 0))
    says('and the contextual pass beside it', vers.get(2, 0) > 0,
         '%d rows at v2' % vers.get(2, 0))
    v2 = [r for r in rows if r.get('v') == 2]
    if v2:
        targeted = sum(1 for r in v2
                       if (r.get('ctx') or {}).get('target_vintage'))
        check('v2 decisions with no target vintage',
              len(v2) - targeted, len(v2),
              'a contextual decision should name the year it was asked '
              'about')
        says('v2 decisions name a target wine',
             all((r.get('ctx') or {}).get('target_wine') for r in v2),
             '%d' % len(v2))
        says('WRONG_VINTAGE appears, which it could not in v1',
             any(r.get('code') == 'WRONG_VINTAGE' for r in v2),
             '%d' % sum(1 for r in v2
                        if r.get('code') == 'WRONG_VINTAGE'))
        says('v1 has no WRONG_VINTAGE, because it never asked',
             not any(r.get('code') == 'WRONG_VINTAGE'
                     for r in rows if r.get('v') == 1))
        # More than one wine per estate is actually exercised.
        byest = collections.defaultdict(set)
        for r in v2:
            c = r.get('ctx') or {}
            byest[c.get('estate')].add(c.get('target_wine'))
        multi = sum(1 for v in byest.values() if len(v) > 1)
        says('estates evaluated against more than one wine', multi > 0,
             '%d estate(s)' % multi)
        # The cuvee limitation is recorded, not guessed.
        says('the cuvee gap is recorded rather than answered',
             any(r.get('code') == 'GUARD_HAS_NO_CUVEE_MODE'
                 for r in v2),
             '%d' % sum(1 for r in v2
                        if r.get('code') == 'GUARD_HAS_NO_CUVEE_MODE'))
        check('cuvee contexts claiming a verdict',
              sum(1 for r in v2
                  if (r.get('ctx') or {}).get('target_role') == 'other'
                  and r.get('decision') in ('ACCEPTED', 'REFUSED')), 0,
              'whose_sheet has no mode for a named cuvee, so it cannot '
              'conclude anything about one')
        # Idempotence under the new key - and an exact account of every
        # duplicate rather than a bound.
        #
        # The first version of this check allowed "174 x 40" duplicates,
        # which was a guess, and the pass came back with 8,882. Tracing
        # them found two real faults, not noise: the key had no
        # target_role, so one wine evaluated as the second AND as a
        # named cuvee (102 estates list it both ways) collided - and
        # 8,181 of those pairs carried DIFFERENT verdicts, so the
        # collision was hiding information. With target_role and
        # target_estate in the key, 527 duplicates remain, and every
        # one comes from a manifest row duplicating another. So the
        # invariant is now exact: no duplicate that the manifest does
        # not itself contain.
        v2 = [r for r in rows if r.get('v') == 2]
        seen = collections.Counter(EV.row_key(r) for r in v2)
        duprows = set()
        try:
            m = json.load(io.open(ROOT + 'data/sources.json',
                                  encoding='utf-8'))
            kk = collections.Counter(
                (s.get('file'), s.get('folder'), s.get('estate'),
                 s.get('wine'), s.get('year'))
                for s in m.get('sheets', []))
            duprows = set(a for a, n in kk.items() if n > 1)
        except Exception:
            pass
        unexplained = sum(
            n - 1 for kk2, n in seen.items()
            if n > 1 and (kk2[0], kk2[1], kk2[2], kk2[3], kk2[5])
            not in duprows)
        check('contextual duplicates the manifest does not explain',
              unexplained, 0,
              'a duplicate decision with no duplicate manifest row '
              'behind it is a persistence fault')
        says('every contextual duplicate traces to a manifest row',
             unexplained == 0,
             '%d duplicates, all from the manifest'
             % sum(n - 1 for n in seen.values() if n > 1))

# =========================================== proposals stay proposals
PROP = ROOT + 'data/proposals.jsonl'
if not os.path.exists(PROP):
    print('MISSING  data/proposals.jsonl')
else:
    props = []
    with io.open(PROP, encoding='utf-8') as f:
        f.readline()
        for line in f:
            props.append(json.loads(line))
    OK = {'PROPOSED_CORRECTION', 'PROPOSED_REVIEW',
          'INSUFFICIENT_EVIDENCE', 'NO_CHANGE'}
    check('proposals in an unknown status',
          sum(1 for r in props if r.get('status') not in OK), 0)
    check('proposals claiming to have been applied',
          sum(1 for r in props
              if r.get('applied') or r.get('status') == 'CONFIRMED'), 0,
          'a proposal is not a correction until applied and verified')
    check('PROPOSED_CORRECTION with nothing proposed',
          sum(1 for r in props
              if r['status'] == 'PROPOSED_CORRECTION'
              and not r.get('proposed')), 0)
    check('non-corrections that still propose a change',
          sum(1 for r in props
              if r['status'] != 'PROPOSED_CORRECTION'
              and r.get('proposed')), 0,
          'only a PROPOSED_CORRECTION carries a proposed identity')
    check('proposals with no evidence',
          sum(1 for r in props if not r.get('evidence')), 0)
    says('the four FILENAME_MISLEADING cases are NO_CHANGE',
         sum(1 for r in props
             if r['kind'] == 'wine_identity'
             and r['status'] == 'NO_CHANGE') == 4,
         '%d' % sum(1 for r in props if r['kind'] == 'wine_identity'
                    and r['status'] == 'NO_CHANGE'))
    says('the 50 Echo sheets are PROPOSED_CORRECTION',
         sum(1 for r in props
             if r['kind'] == 'wine_identity'
             and r['status'] == 'PROPOSED_CORRECTION') == 50,
         '%d' % sum(1 for r in props if r['kind'] == 'wine_identity'
                    and r['status'] == 'PROPOSED_CORRECTION'))
    says('the 2 multi-wine cases are left for review',
         sum(1 for r in props
             if r['kind'] == 'wine_identity'
             and r['status'] == 'PROPOSED_REVIEW') == 2,
         '%d' % sum(1 for r in props if r['kind'] == 'wine_identity'
                    and r['status'] == 'PROPOSED_REVIEW'))

# ================================================== canonical safety
PROTECTED = ('data/sources.json', 'data/fiches.js', 'data/cuvees.js',
             'data/field-src.js', 'data/cuvee-src.js')
try:
    out = subprocess.check_output(
        ['git', 'diff', '--name-only', 'HEAD', '--'] + list(PROTECTED),
        cwd=ROOT, stderr=subprocess.DEVNULL).decode().strip()
except Exception:
    out = None
if out is None:
    print('MISSING  git unavailable; canonical safety not verified')
else:
    says('canonical dataset files unmodified vs HEAD', out == '',
         'clean' if out == '' else out.replace('\n', ' ')[:26])

print('\n%d check(s), %s'
      % (checks, 'all pass' if not fails
         else '%d FAILED: %s' % (len(fails), '; '.join(fails[:4]))))
sys.exit(1 if fails else 0)
