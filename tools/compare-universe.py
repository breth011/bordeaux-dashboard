# -*- coding: utf-8 -*-
"""Phase 3.0: the authoritative universe against the canonical data, and,
separately, against the evidence corpus. Read-only on both.

    python -I tools/compare-universe.py

Writes data/scope/canonical-discrepancies.jsonl and
data/scope/corpus-discrepancies.jsonl. Each line is one discrepancy,
recorded and not resolved: nothing here changes the canonical files, the
manifest or the evidence store, and no category is a decision.
"""
import collections
import difflib
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
UNI = ROOT + 'data/scope/authoritative-universe.json'
OUT_C = ROOT + 'data/scope/canonical-discrepancies.jsonl'
OUT_E = ROOT + 'data/scope/corpus-discrepancies.jsonl'

SYSTEM_CLS = {'1855-medoc': '1855', '1855-sauternes': 'sauternes', 'graves': 'graves',
              'stem-2022': 'stem', 'cb-2025': 'bourgeois', 'ca-2022': 'artisan'}
PARTICLES = {'de', 'du', 'des', 'd', 'la', 'le', 'les', 'l'}


def fold(s):
    s = unicodedata.normalize('NFD', s or '')
    return ''.join(c for c in s if not unicodedata.combining(c))


def key(name):
    k = fold(name).lower().replace('’', "'")
    k = re.sub(r'[^a-z0-9]+', ' ', k)
    k = re.sub(r'^chateau ', '', k.strip())
    return ' '.join(k.split())


def bare(name):
    """The key without articles and particles, for spotting variants;
    'St' read as 'Saint'."""
    return ' '.join('saint' if w == 'st' else w
                    for w in key(name).split() if w not in PARTICLES)


def node():
    n = shutil.which('node')
    if n:
        return n
    for p in glob.glob(os.path.expandvars(
            r'%LOCALAPPDATA%\Microsoft\WinGet\Packages\OpenJS.NodeJS*\node-*\node.exe')):
        return p
    sys.exit('node not found: tools/canonical-view.js needs it')


def canonical():
    out = subprocess.check_output([node(), ROOT + 'tools/canonical-view.js'], cwd=ROOT)
    return json.loads(out.decode('utf-8'))


def compare_canonical(U, C):
    rows = []

    def rec(cat, **kw):
        kw = dict(category=cat, **kw)
        rows.append(kw)

    canon = C['estates']
    by_cls = collections.defaultdict(list)
    for c in canon:
        by_cls[c['cls']].append(c)
        if c.get('cross'):
            by_cls[c['cross']].append(c)
    matched = {}          # canonical id -> [universe estate id]
    match_of = {}         # (universe id, system) -> canonical record
    for e in U['estates']:
        names = [n['name'] for n in e['names']]
        for m in e['memberships']:
            cls = SYSTEM_CLS[m['system']]
            pool = by_cls[cls]
            hit = [c for c in pool if any(key(c['name']) == key(n) for n in names)]
            how = 'exact'
            if not hit:
                hit = [c for c in pool if any(
                    bare(c['name']).replace(' ', '') == bare(n).replace(' ', '')
                    for n in names)]
                how = 'variant'
            if not hit and m['rank'] is not None:
                # One name the other with words added (Pichon-Baron and
                # Pichon-Longueville Baron), at the same rank: a candidate,
                # never asserted.
                hit = [c for c in pool if c['growth'] == m['rank'] and any(
                    set(bare(c['name']).split()) < set(bare(n).split()) or
                    set(bare(n).split()) < set(bare(c['name']).split())
                    for n in names)]
                how = 'contained'
            if not hit:
                best = max(pool, key=lambda c: max(difflib.SequenceMatcher(
                    None, bare(c['name']), bare(n)).ratio() for n in names))
                r = max(difflib.SequenceMatcher(None, bare(best['name']), bare(n)).ratio()
                        for n in names)
                if r >= 0.85:
                    hit, how = [best], 'fuzzy'
            if len(hit) > 1:
                rec('IDENTITY_MAPPING_UNCERTAIN', universe=e['id'], system=m['system'],
                    canonical=[c['id'] for c in hit],
                    detail='more than one canonical estate in the collection carries '
                           'this name')
                continue
            if not hit:
                elsewhere = [c for c in canon if any(key(c['name']) == key(n) for n in names)]
                if elsewhere:
                    rec('CLASSIFICATION_DIFFERENCE', universe=e['id'], system=m['system'],
                        canonical=[c['id'] for c in elsewhere],
                        canonical_cls=[c['cls'] for c in elsewhere],
                        detail='listed by the source in %s; the canonical data holds an '
                               'estate of this name only in another collection, and '
                               'whether it is the same estate is not established'
                               % m['system'])
                else:
                    rec('IN_UNIVERSE_NOT_IN_CANONICAL', universe=e['id'],
                        name=names[0], system=m['system'], rank=m['rank'],
                        appellation=m.get('appellation_listed'), source=m['source'])
                continue
            c = hit[0]
            matched.setdefault(c['id'], []).append(e['id'])
            match_of[(e['id'], m['system'])] = c
            if how in ('fuzzy', 'contained'):
                rec('IDENTITY_MAPPING_UNCERTAIN', universe=e['id'], system=m['system'],
                    canonical=[c['id']], universe_names=names, canonical_name=c['name'],
                    basis='similar names' if how == 'fuzzy' else
                          'one name is the other with words added, at the same rank',
                    detail='a candidate mapping, not asserted to be the same estate')
            elif how == 'variant':
                rec('NAME_VARIANT', universe=e['id'], system=m['system'],
                    canonical=c['id'], universe_names=names, canonical_name=c['name'],
                    detail='the same name once articles and particles are set aside')
            if len(names) > 1 and len(set(key(n) for n in names)) > 1:
                rec('SOURCE_CONFLICT', universe=e['id'], system=m['system'],
                    canonical=c['id'], names=e['names'],
                    detail='the source\'s two renderings spell the name differently')
            if m['rank'] is not None:
                g = c['growth']
                if g != m['rank'] and not (c.get('cross') == SYSTEM_CLS[m['system']]):
                    rec('CLASSIFICATION_DIFFERENCE', universe=e['id'], system=m['system'],
                        canonical=c['id'], universe_rank=m['rank'],
                        universe_rank_term=m['rank_term'], canonical_growth=g,
                        detail='rank differs')
            app = m.get('appellation_listed')
            twice = len([x for x in e['memberships'] if x['system'] == m['system']]) > 1
            if app and c.get('appellation') and not twice and                     fold(app).lower() != fold(c['appellation']).lower():
                rec('APPELLATION_DIFFERENCE', universe=e['id'], system=m['system'],
                    canonical=c['id'], universe_appellation=app,
                    canonical_appellation=c['appellation'])
            if m['system'] == 'graves' and m.get('colours'):
                want = {'rouge': 'red', 'blanc': 'white'}
                cols = [want[x] for x in m['colours']]
                have = c.get('cat')
                if c.get('cross') == 'graves':
                    have = 'red'
                if len(cols) > 1 or (have not in cols):
                    rec('CLASSIFICATION_DIFFERENCE', universe=e['id'], system='graves',
                        canonical=c['id'], universe_classified_colours=cols,
                        canonical_cat=have, colour_source='wp-graves (secondary)',
                        detail='the Graves classification is per colour; the canonical '
                               'record carries one category' if len(cols) > 1 else
                               'classified colour differs from the canonical category')

    # Moutte Blanc: one estate, two classified wines; the canonical list
    # can hold it under only one appellation.
    for e in U['estates']:
        ca = [m for m in e['memberships'] if m['system'] == 'ca-2022']
        if len(ca) > 1:
            c = match_of.get((e['id'], 'ca-2022'))
            have = fold(c['appellation']).lower() if c and c.get('appellation') else None
            for m in ca:
                if fold(m['appellation_listed']).lower() != have:
                    rec('IN_UNIVERSE_NOT_IN_CANONICAL', universe=e['id'],
                        system='ca-2022', canonical=c['id'] if c else None,
                        wine='%s (%s)' % (e['names'][0]['name'], m['appellation_listed']),
                        canonical_appellation=c['appellation'] if c else None,
                        source=m['source'],
                        detail='one estate classified under two appellations, i.e. two '
                               'classified wines; the canonical record holds only one')

    for cls in SYSTEM_CLS.values():
        for c in by_cls[cls]:
            if c['id'] in matched:
                continue
            if c.get('cross') == cls and c['cls'] != cls:
                continue
            temporal = [t for t in U['temporal']
                        if key(c['name']) and key(c['name']) in key(t['subject'])]
            cat = 'TEMPORAL_DIFFERENCE' if temporal else 'IN_CANONICAL_NOT_IN_UNIVERSE'
            rec(cat, canonical=c['id'], name=c['name'], cls=cls, growth=c['growth'],
                appellation=c.get('appellation'),
                temporal=[t['id'] for t in temporal] or None,
                detail=('the source records this as %s' % temporal[0]['change'])
                if temporal else 'not listed by the current source for %s' % cls)

    # The collections' own descriptions, where a source dates them otherwise.
    coll = {c['id']: c for c in C['collections']}
    if coll.get('artisan', {}).get('year') == 2006:
        rec('TEMPORAL_DIFFERENCE', canonical='collection:artisan', canonical_year=2006,
            universe_validity='vintages 2022 to 2026', source='sca-proclamation-b',
            detail='the collection is dated 2006 and described as the 2006 list plus '
                   '2012 additions; its roster is a 2022–2026 site listing, and the '
                   'current classification is the 2022–2026 proclamation')
    cls_js = io.open(ROOT + 'data/classifications.js', encoding='utf-8').read()
    if 'Amended exactly once' in cls_js:
        rec('TEMPORAL_DIFFERENCE', canonical='collection:1855',
            canonical_text='Amended exactly once, in 1973',
            universe=['T1', 'T2'], source='gcc-1855-histoire',
            detail='the Council names two changes: Cantemerle added 16 September 1855, '
                   'Mouton Rothschild promoted June 1973')
    for cid, c in coll.items():
        if c['editorial']:
            rec('UNRESOLVED', canonical='collection:' + cid, name=c['name'],
                detail='an editorial collection with no classification authority: '
                       'outside the authoritative universe, retained as it is')

    # Wines. Only estates whose own pages were read have a wine universe
    # beyond the classified wine; for the rest the canonical other wines are
    # neither confirmed nor contradicted.
    W = collections.defaultdict(list)
    for w in U['wines']:
        W[w['estate']].append(w)
    canon_by_id = {c['id']: c for c in canon}
    read = {e['id'] for e in U['estates'] if e['wine_universe'] == 'ESTATE_SOURCE_READ'}
    for uid in sorted(read):
        cids = [cid for cid, us in matched.items() if uid in us]
        for cid in cids:
            c = canon_by_id[cid]
            uw = {key(re.sub(r'\s*\((blanc|rouge)\)$', '', w['name'])): w for w in W[uid]
                  if w['kind'] == 'ESTATE_WINE'}
            cw = list(c['wines'])
            if c.get('second') and not any(x['name'] == c['second'] for x in cw):
                cw.append({'name': c['second'], 'role': 'second', 'colour': None})
            for x in cw:
                u = uw.get(key(x['name']))
                if not u:
                    rec('IN_CANONICAL_NOT_IN_UNIVERSE', canonical=cid, wine=x['name'],
                        canonical_role=x['role'], detail='the estate\'s page does not '
                                                         'list this wine')
                elif x['role'] != (u['role'] or x['role']) or (x['role'] == 'second'
                                                               and u['role'] is None):
                    rec('ROLE_DIFFERENCE', canonical=cid, wine=x['name'],
                        canonical_role=x['role'], universe_role=u['role'],
                        universe_source_term=u['source_term'], source=u['sources'][0],
                        detail='the canonical role is not stated by the estate\'s own '
                               'page' if u['role'] is None else 'roles differ')
            have = {key(x['name']) for x in cw}
            for k, u in sorted(uw.items()):
                if k not in have:
                    rec('TEMPORAL_DIFFERENCE' if u.get('historical') else
                        'IN_UNIVERSE_NOT_IN_CANONICAL', universe=u['id'], canonical=cid,
                        wine=u['name'], universe_role=u['role'],
                        source_term=u['source_term'], valid=u['valid'],
                        source=u['sources'][0])
    unread = 0
    for cid, us in matched.items():
        if any(u in read for u in us):
            continue
        c = canon_by_id[cid]
        for x in c['wines'] or ([{'name': c['second'], 'role': 'second'}]
                                if c.get('second') else []):
            unread += 1
            rec('UNRESOLVED', canonical=cid, wine=x['name'], canonical_role=x['role'],
                detail='no authoritative source for this estate\'s wines was read; '
                       'neither confirmed nor contradicted')
    return rows, matched


def compare_corpus(U, C, matched):
    """The universe against the manifest (data/sources.json) and the v5
    evidence. Kept apart from the canonical comparison: the corpus is
    what was collected, not what is true."""
    sys.path.insert(0, ROOT + 'tools')
    import evidence_store as ST
    S = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))['sheets']
    rows = []

    def rec(cat, **kw):
        rows.append(dict(category=cat, **kw))

    by_est = collections.defaultdict(list)
    for r in S:
        by_est[r['estate']].append(r)
    u2c = collections.defaultdict(list)
    for cid, us in matched.items():
        for u in us:
            u2c[u].append(cid)
    for e in U['estates']:
        cids = u2c.get(e['id'], [])
        n = sum(len(by_est.get(c, [])) for c in cids)
        if not cids:
            rec('UNIVERSE_ESTATE_NOT_MAPPED', universe=e['id'],
                detail='no canonical estate matched, so no corpus folder can be looked up')
        elif n == 0:
            rec('UNIVERSE_ESTATE_NO_CORPUS', universe=e['id'], canonical=cids,
                detail='no sheet in the manifest is attributed to it')
    inside = set(matched)
    outside = collections.Counter()
    for est, rs in by_est.items():
        if est and est not in inside:
            outside[est] = len(rs)
    for est, n in sorted(outside.items()):
        rec('CORPUS_ESTATE_OUTSIDE_UNIVERSE', canonical=est, sheets=n)
    rec('CORPUS_UNATTRIBUTED', sheets=len(by_est.get(None, [])),
        detail='documents the manifest attributes to no estate; counted, not resolved')

    # The three Phase 2 findings, against the wines the estates publish.
    lb = [r for r in S if r['estate'] == 'lynch-bages' and 'echo' in r['file'].lower()
          and r['wine'] == 'Blanc de Lynch-Bages']
    rec('CORPUS_ROLE_DIFFERS', canonical='lynch-bages', sheets=len(lb),
        manifest_wine='Blanc de Lynch-Bages', manifest_role='other',
        universe_wine='Echo de Lynch-Bages', universe_role='second',
        source='estate-lynch-bages',
        detail='sheets named for Echo are filed as the Blanc; the estate publishes '
               'Echo (red, second vin) and the Blanc (white) as two wines')
    tsc = 'stem-chateau-tour-saint-christophe'
    acc = [d for d in ST.iter_rows([5])
           if 'TERRASSES' in d['artifact'].upper() and 'CHRISTOPHE' in d['artifact'].upper()
           and d['ctx'].get('target_estate') == tsc and d['ctx'].get('target_role') == 'grand'
           and d['code'] == 'ACCEPTED']
    rec('CORPUS_DECISION_CONFLICTS_WITH_UNIVERSE', canonical=tsc, decisions=len(acc),
        evidence_version=5, decided_as='grand vin of Tour Saint Christophe',
        universe_wine='Les Terrasses de Saint Christophe', source='estate-vk-tsc-vins',
        detail='v5 accepts Terrasses sheets as the grand vin; the owner publishes Les '
               'Terrasses as a distinct wine of the estate')
    mur = [r for r in S if r['estate'] == 'caillou' and 'murets' in r['file'].lower()]
    rec('CORPUS_WINE_NOT_IN_CANONICAL', canonical='caillou', sheets=len(mur),
        files=[r['file'] for r in mur], manifest=[(r['wine'], r['role']) for r in mur],
        universe_wine='Les Murets de Caillou', source='estate-caillou-murets-blanc',
        detail='the estate publishes Les Murets de Caillou (blanc and rouge) and gives '
               'it no role')
    return rows


def main():
    U = json.load(io.open(UNI, encoding='utf-8'))
    C = canonical()
    crow, matched = compare_canonical(U, C)
    erow = compare_corpus(U, C, matched)
    for p, rows in ((OUT_C, crow), (OUT_E, erow)):
        with io.open(p, 'w', encoding='utf-8', newline='\n') as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n')
    for name, rows in (('canonical', crow), ('corpus', erow)):
        c = collections.Counter(r['category'] for r in rows)
        print(name, len(rows), dict(sorted(c.items())))


if __name__ == '__main__':
    main()
