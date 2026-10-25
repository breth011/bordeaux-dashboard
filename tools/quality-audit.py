"""Phase 4 M10: a data-quality audit of the normalized model.

    python tools/quality-audit.py         write data/model/checks/quality-audit.json
    python tools/quality-audit.py --check compare with the committed report

Reads the model only. Fourteen detectors, one per kind the Phase 4 brief
names; each hit is a finding with a PROPOSED action. Nothing is fixed:
the model, the legacy files and the proposals files are not written.
"""
import collections
import json
import os
import re
import sys
import unicodedata

import migration_lib as L
import model_reader as R

OUT = L.MODEL + 'checks/quality-audit.json'


def norm(s):
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').casefold().replace('’', "'")
    s = re.sub(r'\b(chateau|ch|domaine|clos)\b', ' ', s)
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def audit():
    M = R.Model()
    rows = M.rows
    names = collections.defaultdict(list)
    for n in rows('identity/names.jsonl'):
        names[n['subject']].append(n['name'])
    est = {e['id'] for e in rows('identity/estates.jsonl')}
    wines = {w['id']: w for w in rows('identity/wines.jsonl')}
    rels = rows('state/estate-wine.jsonl')
    rel = {r['id']: r for r in rels}
    prov = {p['id']: p for p in rows('cross/provenance.jsonl')}
    im = collections.defaultdict(dict)
    for r in rows('identity/identity-map.jsonl'):
        im[r['namespace']][r['legacy_key']] = r
    out = collections.OrderedDict()

    def hit(kind, target, detail, action):
        out.setdefault(kind, []).append({'target': target, 'detail': detail,
                                         'proposed_action': action, 'status': 'PROPOSED'})

    # 1 duplicate estates: two estates whose names agree once 'Château' and typography go
    by = collections.defaultdict(list)
    for e in est:
        for n in names[e]:
            by[norm(n)].append(e)
    for k, es in sorted(by.items()):
        if len(set(es)) > 1:
            hit('duplicate estates', sorted(set(es)), 'names agree as %r: %s' % (
                k, '; '.join(sorted({n for e in es for n in names[e]}))),
                'review whether these are one estate (IdentityTransition) or distinct (DISTINCT_FROM)')
    # 2 duplicate wines: one estate, two wines of one normalized name
    wines_of = collections.defaultdict(list)
    for r in rels:
        wines_of[r['estate']].append(r['wine'])
    for e, ws in sorted(wines_of.items()):
        byn = collections.defaultdict(set)
        for w in ws:
            for n in names[w]:
                byn[norm(n)].add(w)
        for k, s in sorted(byn.items()):
            if len(s) > 1:
                hit('duplicate wines', sorted(s), 'one estate, wines named alike (%r)' % k,
                    'review: one wine, or wines distinguished by type')
    # 3 duplicate wine aliases: a display name resolving to several or no wines
    for k, r in sorted(im['wine-by-display-name'].items()):
        if not r.get('stable_id'):
            hit('duplicate wine aliases', k, '%d candidate wines' % len(r.get('candidates', [])),
                'decide which wine the name denotes, or record it as unresolved')
    # 4 impossible estate/wine relationships
    prod = collections.defaultdict(set)
    for r in rels:
        if r['kind'] == 'PRODUCED_BY':
            prod[r['wine']].add(r['estate'])
    for w in sorted(wines):
        if len(prod[w]) != 1:
            hit('impossible estate/wine relationships', w, 'produced by %d estates' % len(prod[w]),
                'review the relationship')
    # 5 conflicting temporal intervals
    for t in ('state/estate-wine.jsonl', 'state/rank-assertions.jsonl', 'state/classification-memberships.jsonl',
              'state/classification-editions.jsonl', 'state/appellation-memberships.jsonl'):
        for r in rows(t):
            v = r['validity']
            a, b = v['valid_from'].get('value'), v['valid_to'].get('value')
            if a and b and str(a) > str(b):
                hit('conflicting temporal intervals', r['id'], '%s after %s' % (a, b), 'correct the bounds')
    # 6 overlapping mutually exclusive rank claims (one tier, one estate range, several wines)
    held = collections.defaultdict(set)
    for r in rows('state/rank-assertions.jsonl'):
        if r['tier'] in ('FIRST', 'SECOND', 'THIRD') and r['scope'] == 'ESTATE_RANGE':
            held[(rel[r['relationship']]['estate'], r['tier'])].add(rel[r['relationship']]['wine'])
    absent = {(r['estate'], r['tier']) for r in rows('state/rank-absences.jsonl')}
    for (e, tier), ws in sorted(held.items()):
        if len(ws) > 1:
            hit('overlapping mutually exclusive rank claims', e, '%d wines claimed %s within the estate '
                'range: %s' % (len(ws), tier, '; '.join(sorted(names[w][0] for w in ws if names[w]))),
                'decide whether the claims are scoped by wine type (TYPE_RANGE) or one is historical')
        if (e, tier) in absent:
            hit('overlapping mutually exclusive rank claims', e, '%s claimed and declared absent' % tier,
                'decide which claim holds, and when')
    # 7 classification contradictions: one wine, one scheme, two ranks; and Phase 3.0's list differences
    ed = {r['id']: r for r in rows('state/classification-editions.jsonl')}
    bys = collections.defaultdict(set)
    for r in rows('state/classification-memberships.jsonl'):
        bys[(r['wine'], ed[r['edition']]['scheme'])].add(r.get('rank'))
    for (w, s), rk in sorted(bys.items()):
        if len(rk) > 1:
            hit('classification contradictions', w, 'ranks %s in one scheme' % sorted(rk), 'review')
    for d in L.jsonl_lines(L.ROOT + 'data/scope/canonical-discrepancies.jsonl'):
        hit('classification contradictions', d.get('canonical') or d.get('universe'),
            'Phase 3.0 %s: %s' % (d['category'], d.get('detail', '')),
            'reconcile the dataset edition against the authoritative list (I21)')
    # 8 appellation contradictions: one wine, several appellations
    app = {a['id']: a['name'] for a in rows('state/appellations.jsonl')}
    bya = collections.defaultdict(set)
    for r in rows('state/appellation-memberships.jsonl'):
        bya[r['wine']].add(app[r['appellation']])
    for w, a in sorted(bya.items()):
        if len(a) > 1:
            hit('appellation contradictions', w, 'appellations %s' % sorted(a), 'review')
    # 9 orphan documents: legacy artifacts no attribution names
    attributed = {a['artifact'] for a in rows('document/attributions.jsonl') if a.get('estate')}
    legacy_arts = {a['id'] for a in rows('identity/artifacts.jsonl') if 'sha1' in a}
    for a in sorted(legacy_arts - attributed):
        hit('orphan documents', a, 'a manifest artifact no attribution assigns to an estate',
            'attribute it, or record it as UNATTRIBUTED once examined (I17)')
    # 10 orphan observations: an observation whose subject has no relationship to an estate
    vint_wines = {w for r in rels for w in [r['wine']]}
    for o in rows('observation/observations.jsonl'):
        s = o['subject']
        if s.startswith('vt:') and s[3:].rsplit(':', 1)[0] not in vint_wines:
            hit('orphan observations', o['id'], 'its vintage belongs to a wine no estate produces', 'review')
    # 11 provenance-less canonical values (none may exist) and the unsourced ones
    for c in rows('canonical/values.jsonl'):
        if c.get('provenance') not in prov:
            hit('provenance-less canonical values', [c['subject'], c['field']], 'no provenance', 'trace it')
    unsourced = sum(1 for c in rows('canonical/values.jsonl') if c['status'] == 'LEGACY_UNSOURCED')
    # 12 unresolved legacy references
    for r in rows('document/legacy-references.jsonl'):
        if r['resolution'] != 'ACTIVE':
            hit('unresolved legacy references', [r['origin'], r['record_key'], r.get('field'), r['basename']],
                '%d candidate placements' % len(r['candidates']),
                'choose the document by review, never by first match (I22)')
    for ns, kv in sorted(im.items()):
        for k, r in sorted(kv.items()):
            if r['status'] == 'AMBIGUOUS' and ns != 'wine-by-display-name':
                hit('unresolved legacy references', [ns, k], 'identity map AMBIGUOUS, %d candidates' % len(
                    r.get('candidates', [])), 'decide, or keep as unresolved')
    # 13 duplicate document identities
    s1 = collections.Counter(a['sha1'] for a in rows('identity/artifacts.jsonl') if 'sha1' in a)
    s2 = collections.Counter(a['sha256'] for a in rows('identity/artifacts.jsonl') if 'sha256' in a)
    for d, n in list(s1.items()) + list(s2.items()):
        if n > 1:
            hit('duplicate document identities', d, '%d artifacts share a digest' % n, 'merge them')
    for f in rows('cross/findings.jsonl'):
        if f['kind'] == 'IDENTITY_UNCERTAIN' and f['detail'].startswith('the bytes read at'):
            hit('duplicate document identities', f['target'], f['detail'],
                'hash the manifest version still on disk to join or separate them')
    # 14 invalid source relationships
    srcs = {s['id']: s for s in rows('identity/sources.jsonl')}
    links = collections.defaultdict(set)
    for r in rows('state/source-estate.jsonl'):
        if r['estate'] not in est or r['source'] not in srcs:
            hit('invalid source relationships', r['id'], 'dangling', 'remove')
        links[r['source']].add(r['estate'])
    for s, es in sorted(links.items()):
        if len(es) > 1:
            hit('invalid source relationships', s, '%s: one site listed as the official site of %d '
                'estates' % (srcs[s]['name'], len(es)), 'classify it (GROUP_SITE, NEGOCIANT_SITE) by review')
    return out, unsourced


KINDS = ['duplicate estates', 'duplicate wines', 'duplicate wine aliases',
         'impossible estate/wine relationships', 'conflicting temporal intervals',
         'overlapping mutually exclusive rank claims', 'classification contradictions',
         'appellation contradictions', 'orphan documents', 'orphan observations',
         'provenance-less canonical values', 'unresolved legacy references',
         'duplicate document identities', 'invalid source relationships']


def build():
    hits, unsourced = audit()
    return {'_': 'Phase 4 M10: the data-quality audit of the model (tools/quality-audit.py). '
                 'Every entry is a proposal; nothing was fixed.',
            'summary': {k: len(hits.get(k, [])) for k in KINDS},
            'canonical_values_marked_legacy_unsourced': unsourced,
            'proposals': {k: hits.get(k, []) for k in KINDS}}


def main():
    r = build()
    if '--check' in sys.argv:
        saved = json.load(open(OUT, encoding='utf-8'))
        ok = saved['summary'] == r['summary']
        L.out('quality audit %s' % ('current' if ok else 'stale'))
        sys.exit(0 if ok else 1)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8', newline='\n').write(json.dumps(r, ensure_ascii=False, indent=1) + '\n')
    for k, v in r['summary'].items():
        L.out('%6d  %s' % (v, k))


if __name__ == '__main__':
    main()
