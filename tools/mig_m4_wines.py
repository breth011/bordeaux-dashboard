"""Phase 4 M4: the wines that are not the grand vin.

cuvees.js BDX_CUVEE_WINES: one Wine per (estate, slug); type from colour;
the name verbatim; PRODUCED_BY; a RankAssertion claimed by the DATASET:
'second' -> SECOND, 'other' -> UNKNOWN with legacy_term 'other' (B1:
'other' meant both 'another cuvee' and 'not known', so it never becomes a
rank). An estate listing two 'second' wines (a red and a white) gets an
AMBIGUOUS_SEMANTICS finding: 'second' did not say within which range.

The estate files' `second` field, mechanically and without judgement:
  '—'                        RankAbsence SECOND (no second wine)
  the name of a listed wine  that wine; also when the two differ only in
                             letter case, apostrophe form or hyphen/space
  text in parentheses        not a plain name ('Y d'Yquem (a dry white, not
                             a second wine)'): no wine, no rank, a finding
  another name, where the    AMBIGUOUS, the listed wines as candidates: a
  estate lists wines         rename, a succession or another wine; not
                             decided here (La Parde / Haut-Bailly II)
  a name two estates claim   AMBIGUOUS (La Reserve de Leoville-Barton)
  any other name             a minted Wine, SECOND claimed by the DATASET
Every string stays in the identity map (namespace 'second-by-name'), so
the field is reconstructable whatever became of it.

Graves 'red and white': the white Wine is the listed white wine when the
estate lists exactly one; with several, the membership waits (AMBIGUOUS,
candidates); with none, a white Wine is minted with name_status UNKNOWN
(D8: the names found in Phase 3.4 are not applied).
"""
import collections
import glob
import re
import unicodedata

import migration_lib as L
import model_schema as S
import mig_m2_identity as M2

ACTOR = 'tools/migrate.py M4'
TYPE = {'red': 'RED', 'white': 'WHITE_DRY', 'sweet': 'WHITE_SWEET', 'rose': 'ROSE'}


def current():
    return {'valid_from': S.bound('UNKNOWN'), 'valid_to': S.bound('OPEN')}


def typo(s):
    """Typography only: letter case, apostrophe form, hyphen versus space."""
    s = unicodedata.normalize('NFC', s).casefold().replace('’', "'").replace('‘', "'")
    return re.sub(r'[\s-]+', ' ', s).strip()


def relate(m, eid, wid, prov):
    rel = S.hid('EstateWineRelationship', eid, wid, 'PRODUCED_BY')
    m.add('state/estate-wine.jsonl', {'id': rel, 'estate': eid, 'wine': wid, 'status': 'ESTABLISHED',
                                      'kind': 'PRODUCED_BY', 'validity': current(), 'provenance': prov})
    return rel


def rank(m, rel, tier, legacy_term, prov):
    m.add('state/rank-assertions.jsonl', {
        'id': S.hid('RankAssertion', rel, tier, 'ESTATE_RANGE', 'DATASET', legacy_term, prov),
        'relationship': rel, 'tier': tier, 'scope': 'ESTATE_RANGE', 'claimant': 'DATASET',
        'legacy_term': legacy_term, 'validity': current(), 'provenance': prov})


def cuvee_wines(m):
    p_c = m.prov('LEGACY_UNSOURCED', 'data/cuvees.js')
    p_rule = m.prov('DERIVATION', ACTOR, quote='one Wine per (estate, slug) of BDX_CUVEE_WINES')
    m.cuvee = {}                       # (legacy estate id, slug) -> wine id
    m.cuvee_rel = {}
    wines = L.g('BDX_CUVEE_WINES')
    for lid in sorted(wines):
        eid = m.estate[lid]
        for w in sorted(wines[lid], key=lambda x: x['slug']):
            wid = m.mint('Wine', 'wine-by-slug', '%s|%s' % (lid, w['slug']))
            m.cuvee[(lid, w['slug'])] = wid
            m.add('identity/wines.jsonl', {'id': wid, 'name_status': 'KNOWN',
                                           'type': TYPE.get(w.get('colour'), 'UNKNOWN')})
            M2.idmap(m, 'wine-by-slug', '%s|%s' % (lid, w['slug']), wid, p_rule)
            m.add('identity/names.jsonl', {
                'id': S.hid('NameRecord', wid, w['name'], 'CURRENT'), 'subject': wid, 'name': w['name'],
                'kind': 'CURRENT', 'validity': current(), 'provenance': p_c})
            rel = relate(m, eid, wid, p_c)
            m.cuvee_rel[(lid, w['slug'])] = rel
            if w['role'] == 'second':
                rank(m, rel, 'SECOND', 'second', p_c)
            elif w['role'] == 'other':
                rank(m, rel, 'UNKNOWN', 'other', p_c)
            else:
                raise SystemExit('unknown legacy role %r' % w['role'])
        seconds = [w for w in wines[lid] if w['role'] == 'second']
        if len(seconds) > 1:
            m.finding(m.estate[lid], 'AMBIGUOUS_SEMANTICS',
                      "cuvees.js lists %d 'second' wines (%s): the legacy role does not say within "
                      "which range (estate, or wine type) each is second" % (
                          len(seconds), ', '.join('%s %s' % (w['name'], w.get('colour')) for w in seconds)),
                      ACTOR, p_c)
    m.stat('M4', 'cuvee wines', len(m.cuvee))


def second_field(m):
    wines = L.g('BDX_CUVEE_WINES')
    files = [(f, r) for f, r in L.estate_files() if 'second' in r]
    named = collections.Counter(r['second'] for f, r in files if r['second'] != '—')
    out = collections.Counter()
    for f, r in sorted(files, key=lambda x: x[1]['id']):
        lid, s = r['id'], r['second']
        eid = m.estate[lid]
        p = m.prov('LEGACY_UNSOURCED', 'data/' + f)
        key = '%s|%s' % (lid, s)
        listed = sorted(wines.get(lid, []), key=lambda w: w['slug'])
        if s == '—':
            m.add('state/rank-absences.jsonl', {
                'id': S.hid('RankAbsence', eid, 'SECOND', 'ESTATE_RANGE', 'DATASET', p), 'estate': eid,
                'tier': 'SECOND', 'scope': 'ESTATE_RANGE', 'claimant': 'DATASET', 'validity': current(),
                'provenance': p})
            M2.idmap(m, 'second-by-name', key, None, p, status='RETIRED')
            out['dash: RankAbsence'] += 1
            sec = [w for w in listed if w['role'] == 'second']
            if sec:
                m.finding(eid, 'CONFLICT', "data/%s says the estate has no second wine ('—'); cuvees.js "
                          "lists %s as its second" % (f, ', '.join(w['name'] for w in sec)), ACTOR, p)
                out['dash contradicted by cuvees.js'] += 1
            continue
        exact = [w for w in listed if w['name'] == s]
        typed = [w for w in listed if typo(w['name']) == typo(s)]
        hit = exact or typed
        if len(hit) == 1:
            wid = m.cuvee[(lid, hit[0]['slug'])]
            M2.idmap(m, 'second-by-name', key, wid, p)
            rank(m, m.cuvee_rel[(lid, hit[0]['slug'])], 'SECOND', 'second', p)
            out['a listed wine (exact)' if exact else 'a listed wine (typography)'] += 1
            if hit[0]['role'] == 'other':
                out['...listed as other in cuvees.js'] += 1
            continue
        cands = [m.cuvee[(lid, w['slug'])] for w in listed]
        if '(' in s:
            M2.idmap(m, 'second-by-name', key, None, p, status='AMBIGUOUS',
                     candidates=[m.cuvee[(lid, w['slug'])] for w in listed
                                 if typo(w['name']) == typo(s.split('(')[0])])
            m.finding(eid, 'AMBIGUOUS_SEMANTICS', 'data/%s second is not a plain name: %r; no wine and '
                      'no rank taken from it' % (f, s), ACTOR, p)
            out['commentary in parentheses'] += 1
        elif listed:
            sec = [m.cuvee[(lid, w['slug'])] for w in listed if w['role'] == 'second']
            M2.idmap(m, 'second-by-name', key, None, p, status='AMBIGUOUS', candidates=sec or cands)
            m.finding(eid, 'IDENTITY_UNCERTAIN', 'data/%s names %r as the second wine; cuvees.js lists '
                      '%s; whether it is one of them (renamed, succeeded) or another wine is not decided '
                      'here' % (f, s, ', '.join('%s (%s)' % (w['name'], w['role']) for w in listed)),
                      ACTOR, p)
            out['another name than the listed wines'] += 1
        elif named[s] > 1:
            M2.idmap(m, 'second-by-name', key, None, p, status='AMBIGUOUS', candidates=[])
            m.finding(eid, 'IDENTITY_UNCERTAIN', '%r is named as the second wine of %d estates' % (
                s, named[s]), ACTOR, p)
            out['claimed by several estates'] += 1
        else:
            wid = m.mint('Wine', 'second-by-name', key)
            m.add('identity/wines.jsonl', {'id': wid, 'name_status': 'KNOWN', 'type': 'UNKNOWN'})
            M2.idmap(m, 'second-by-name', key, wid, p)
            m.add('identity/names.jsonl', {
                'id': S.hid('NameRecord', wid, s, 'CURRENT'), 'subject': wid, 'name': s,
                'kind': 'CURRENT', 'validity': current(), 'provenance': p})
            rank(m, relate(m, eid, wid, p), 'SECOND', 'second', p)
            out['minted (the estate lists no wines)'] += 1
    m.stat('M4', 'estate-file second field', dict(sorted(out.items())))


def graves_white(m):
    wines = L.g('BDX_CUVEE_WINES')
    ed, tiers = m.editions['graves']
    out = collections.Counter()
    for f, r in sorted(L.estate_files(), key=lambda x: x[1]['id']):
        if r.get('wine') != 'red and white':
            continue
        lid = r['id']
        p = m.prov('LEGACY_UNSOURCED', 'data/' + f)
        whites = [w for w in sorted(wines.get(lid, []), key=lambda w: w['slug'])
                  if w.get('colour') == 'white']
        if len(whites) == 1:
            wid = m.cuvee[(lid, whites[0]['slug'])]
            M2.idmap(m, 'graves-white', lid, wid, p)
            out['the one listed white'] += 1
        elif whites:
            M2.idmap(m, 'graves-white', lid, None, p, status='AMBIGUOUS',
                     candidates=[m.cuvee[(lid, w['slug'])] for w in whites])
            m.finding(m.estate[lid], 'IDENTITY_UNCERTAIN', "data/%s classifies the estate 'red and white'; "
                      "cuvees.js lists %d white wines (%s); which is the classified white is not decided "
                      "here (D8)" % (f, len(whites), ', '.join(w['name'] for w in whites)), ACTOR, p)
            out['several listed whites: waits'] += 1
            continue
        else:
            wid = m.mint('Wine', 'graves-white', lid)
            m.add('identity/wines.jsonl', {'id': wid, 'name_status': 'UNKNOWN', 'type': 'WHITE_DRY'})
            M2.idmap(m, 'graves-white', lid, wid, p)
            rel = relate(m, m.estate[lid], wid, p)
            rank(m, rel, 'UNKNOWN', 'red and white', p)
            out['minted, name UNKNOWN (D8)'] += 1
        m.add('state/classification-memberships.jsonl', {
            'id': S.hid('ClassificationMembership', ed, wid), 'edition': ed, 'wine': wid,
            'rank': tiers[r['growth']], 'rank_status': 'KNOWN', 'validity': current(), 'provenance': p})
    m.stat('M4', "Graves 'red and white' white wines", dict(sorted(out.items())))


def display_names(m):
    """(estate, display name) -> wine: what evidence target_wine resolves through."""
    names = collections.defaultdict(set)
    view = {e['id']: e for e in L.canonical_view()['estates']}
    for lid, wid in m.grand.items():
        names[(lid, view[lid]['name'])].add(wid)
    for (lid, slug), wid in m.cuvee.items():
        w = next(x for x in L.g('BDX_CUVEE_WINES')[lid] if x['slug'] == slug)
        names[(lid, w['name'])].add(wid)
    # The estate files' second strings resolve as M4 resolved them.
    second = {}
    for r in m.rows('identity/identity-map.jsonl'):
        if r['namespace'] == 'second-by-name' and r['status'] != 'RETIRED':
            lid, name = r['legacy_key'].split('|', 1)
            second[(lid, name)] = r
    for k, r in second.items():
        if r.get('stable_id'):
            names[k].add(r['stable_id'])
    used = collections.Counter()
    for p in sorted(glob.glob(L.ROOT + 'data/evidence/decisions-v*.jsonl')):
        for d in L.jsonl_lines(p):
            c = d.get('ctx') or {}
            if c.get('target_wine') and c.get('estate'):
                used[(c['estate'], c['target_wine'])] += 1
    p_rule = m.prov('DERIVATION', ACTOR, quote="a wine's display name within its estate, as the "
                    'evidence target_wine and the manifest wine field use it')
    out = collections.Counter()
    for (lid, name) in sorted(set(names) | set(used)):
        key = '%s|%s' % (lid, name)
        ws = sorted(names.get((lid, name), ()))
        if not ws and (lid, name) in second:
            # An ambiguous second: the same candidates, still undecided.
            M2.idmap(m, 'wine-by-display-name', key, None, p_rule, status='AMBIGUOUS',
                     candidates=second[(lid, name)].get('candidates', []))
            out['ambiguous (an undecided second)'] += 1
            continue
        if len(ws) == 1:
            M2.idmap(m, 'wine-by-display-name', key, ws[0], p_rule)
            out['resolved'] += 1
        else:
            M2.idmap(m, 'wine-by-display-name', key, None, p_rule, status='AMBIGUOUS', candidates=ws)
            out['ambiguous' if ws else 'unresolved'] += 1
            if (lid, name) in used:
                out['...used by evidence'] += 1
    m.stat('M4', 'display names', dict(sorted(out.items())))


def run(m):
    cuvee_wines(m)
    second_field(m)
    graves_white(m)
    display_names(m)
