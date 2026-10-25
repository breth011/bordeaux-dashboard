"""Phase 4 M8: today's data reconstructed from the normalized model.

    python tools/reconstruct.py           write data/model/checks/reconstruction.json
    python tools/reconstruct.py --check   exit 1 on any unexplained difference

tools/model_reader.py projects the model into the legacy shapes; this
compares the projection with the legacy files as the page reads them
(tools/legacy-dump.js), value by value, and classifies every difference:

  EXPECTED STRUCTURAL DIFFERENCE   the model represents it differently on
                                   purpose (order of presentation, an
                                   empty record, a file outside the
                                   contract's scope)
  TRUE MIGRATION ERROR             anything not explained: a failure
  LEGACY AMBIGUITY                 the legacy value is kept but its meaning
                                   is undecided
  PRE-EXISTING DATA ISSUE          the legacy data is itself defective and
                                   is kept as it is
  UNRESOLVED                       kept verbatim, not attached to the model

Zero unexplained differences are allowed.
"""
import collections
import json
import os
import sys

import migration_lib as L
import model_reader as R

OUT = L.MODEL + 'checks/reconstruction.json'

# Legacy files outside the Phase 3.4 contract: reference and editorial assets
# the page keeps reading as they are (D7).
OUT_OF_SCOPE = {
    'appellations.js': 'appellation outlines for the map', 'geography.js': 'map geometry',
    'water.js': 'map geometry', 'climate.js': 'regional rainfall and yields',
    'notes.js': 'editorial notes on appellations and classifications',
    'notes-nl.js': 'their Dutch translation', 'grapes.js': 'grape reference', 'grapes-nl.js': 'its Dutch',
    'vintages.js': 'regional vintage reports', 'vintages-nl.js': 'their Dutch',
    'rightbank.js': 'regional vintage scores', 'phenology.js': 'regional phenology dates',
}
# classifications.js: the editions and ranks are in the model; the prose,
# the editorial model parameters and the derived counts are page assets.
CLASSIFICATIONS_NOTE = 'classifications.js: editions, tiers and ranks are migrated; blurb, ' \
                       'detail, region, tiers.base and estates (a derived count) are page assets'


def canon(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


def compare(legacy, proj):
    diffs = []

    def add(cat, where, detail):
        diffs.append({'class': cat, 'where': where, 'detail': detail})

    for f in sorted(legacy):
        if f in OUT_OF_SCOPE:
            add('EXPECTED STRUCTURAL DIFFERENCE', f, 'outside the contract: ' + OUT_OF_SCOPE[f])
            continue
        if f == 'classifications.js':
            add('EXPECTED STRUCTURAL DIFFERENCE', f, CLASSIFICATIONS_NOTE)
            continue
        for g, lv in sorted(legacy[f].items()):
            pv = proj.get(f, {}).get(g)
            where = '%s %s' % (f, g)
            if pv is None:
                add('TRUE MIGRATION ERROR', where, 'not projected')
                continue
            if g == 'BDX_CHATEAUX':
                lmap = {r['id']: r for r in lv}
                pmap = {r['id']: r for r in pv}
                if [r['id'] for r in lv] != sorted(lmap):
                    add('EXPECTED STRUCTURAL DIFFERENCE', where, 'records in presentation order; '
                        'the model holds no order')
                lv, pv = lmap, pmap
            elif isinstance(lv, list):
                if sorted(map(canon, lv)) == sorted(map(canon, pv)):
                    if list(map(canon, lv)) != list(map(canon, pv)):
                        add('EXPECTED STRUCTURAL DIFFERENCE', where, 'list in presentation order; '
                            'the model holds no order')
                    continue
                add('TRUE MIGRATION ERROR', where, 'list differs')
                continue
            if g in ('BDX_CRU_BOURGEOIS', 'BDX_CRU_ARTISAN'):
                for tier in sorted(set(lv) | set(pv)):
                    a, b = lv.get(tier, []), pv.get(tier, [])
                    if sorted(map(canon, a)) != sorted(map(canon, b)):
                        add('TRUE MIGRATION ERROR', '%s.%s' % (where, tier), 'list differs')
                    elif list(map(canon, a)) != list(map(canon, b)):
                        add('EXPECTED STRUCTURAL DIFFERENCE', '%s.%s' % (where, tier),
                            'list in presentation order; the model holds no order')
                continue
            if g == 'BDX_CUVEE_WINES':
                lv = {k: sorted(v, key=lambda w: w['slug']) for k, v in lv.items()}
            for k in sorted(set(lv) | set(pv)):
                a, b = lv.get(k), pv.get(k)
                if canon(a) == canon(b):
                    continue
                w = '%s[%r]' % (where, k)
                if g in ('BDX_FIELD_SRC', 'BDX_CUVEE_SRC') and a == {} and b is None:
                    add('EXPECTED STRUCTURAL DIFFERENCE', w, 'an empty provenance record names no '
                        'source; nothing to keep')
                    continue
                if isinstance(a, dict) and isinstance(b, dict):
                    for fld in sorted(set(a) | set(b)):
                        if canon(a.get(fld)) != canon(b.get(fld)):
                            add('TRUE MIGRATION ERROR', '%s.%s' % (w, fld),
                                'legacy %s / model %s' % (canon(a.get(fld))[:80], canon(b.get(fld))[:80]))
                else:
                    add('TRUE MIGRATION ERROR', w, 'legacy %s / model %s' % (canon(a)[:80], canon(b)[:80]))
    for f in proj:
        if f not in legacy and f != 'sources.json':
            add('TRUE MIGRATION ERROR', f, 'projected a file that does not exist')
    return diffs


def manifest_diffs(proj):
    diffs = []
    legacy = L.sources_rows()
    p = proj['sources.json']
    for k in ('note', 'roles', 'how'):
        if canon(legacy[k]) != canon(p[k]):
            diffs.append({'class': 'TRUE MIGRATION ERROR', 'where': 'sources.json ' + k, 'detail': 'differs'})
    if len(legacy['sheets']) != len(p['sheets']):
        diffs.append({'class': 'TRUE MIGRATION ERROR', 'where': 'sources.json sheets',
                      'detail': '%d rows / %d' % (len(legacy['sheets']), len(p['sheets']))})
        return diffs
    for i, (a, b) in enumerate(zip(legacy['sheets'], p['sheets'])):
        for fld in sorted(set(a) | set(b)):
            if canon(a.get(fld)) != canon(b.get(fld)):
                diffs.append({'class': 'TRUE MIGRATION ERROR', 'where': 'sources.json sheets[%d].%s' % (i, fld),
                              'detail': 'legacy %s / model %s' % (canon(a.get(fld))[:80], canon(b.get(fld))[:80])})
    return diffs


def kept_records():
    """What is kept verbatim, classified (these reconstruct, but are not modelled)."""
    out = []
    for p in L.jsonl_lines(L.MODEL + 'cross/provenance.jsonl'):
        cs = p.get('code_state') or {}
        if cs.get('unresolved'):
            out.append({'class': 'UNRESOLVED', 'where': '%s %s[%r]' % (cs['legacy_file'], cs['global'], cs['key']),
                        'detail': cs['unresolved']})
        elif 'empty_record' in cs:
            out.append({'class': 'PRE-EXISTING DATA ISSUE', 'where': '%s %s[%r]' % (
                cs['legacy_file'], cs['global'], cs['key']), 'detail': 'a record holding no value'})
        elif cs.get('orphan_translation'):
            out.append({'class': 'PRE-EXISTING DATA ISSUE', 'where': 'data/fiches-nl.js BDX_FICHES_NL[%r].%s' % (
                cs['key'], cs['field']), 'detail': 'translates a field the English record does not hold'})
    for f in L.jsonl_lines(L.MODEL + 'cross/findings.jsonl'):
        if f['kind'] == 'CONFLICT' and 'bytes for this one sha1' in f['detail']:
            out.append({'class': 'PRE-EXISTING DATA ISSUE', 'where': f['target'], 'detail': f['detail']})
        elif f['kind'] in ('AMBIGUOUS_SEMANTICS', 'IDENTITY_UNCERTAIN', 'CONFLICT') and \
                'kept verbatim' not in f['detail']:
            out.append({'class': 'LEGACY AMBIGUITY', 'where': f['target'], 'detail': f['detail']})
    return out


def build():
    cls = {c['id']: c for c in L.g('BDX_CLASSIFICATIONS')}
    proj = R.project(classifications=cls)
    legacy = {f: g for f, g in L.legacy().items()}
    diffs = compare(legacy, proj) + manifest_diffs(proj)
    kept = kept_records()
    summary = collections.Counter(d['class'] for d in diffs + kept)
    return {'_': 'Phase 4 M8: the legacy data reconstructed from the model and compared value by '
                 'value (tools/reconstruct.py). Differences are what the projection does not reproduce; '
                 'kept are values reproduced from records kept verbatim or with an open question.',
            'summary': dict(sorted(summary.items())),
            'unexplained': sum(1 for d in diffs if d['class'] == 'TRUE MIGRATION ERROR'),
            'differences': diffs, 'kept': kept}


def main():
    r = build()
    if '--check' not in sys.argv:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        open(OUT, 'w', encoding='utf-8', newline='\n').write(json.dumps(r, ensure_ascii=False, indent=1) + '\n')
    L.out(json.dumps(r['summary'], ensure_ascii=False))
    for d in [d for d in r['differences'] if d['class'] == 'TRUE MIGRATION ERROR'][:40]:
        L.out('  %s: %s' % (d['where'], d['detail']))
    L.out('unexplained differences: %d' % r['unexplained'])
    sys.exit(1 if r['unexplained'] else 0)


if __name__ == '__main__':
    main()
