"""Phase 4 M11: can the model hold the three pending Phase 2 proposals as
they stand, without a schema change? Architecture only: nothing is applied.

    python tools/proposal-compat.py         write data/model/checks/proposal-compatibility.json
    python tools/proposal-compat.py --check exit 1 if a proposal does not fit

Each proposal (docs/phase34-model.json proposals) is written as the rows
it would add, referring to the model's real estates, wines and artifacts;
every row is validated against the contract (tools/model_schema.py) with
the model's ids as the reference set. The rows go only into the report.
Wines a proposal would mint carry the placeholder ids wn_P...; nothing is
minted. Undecided questions stay undecided in the rows themselves: Echo's
predecessor is a transition of certainty UNRESOLVED (D2); Terrasses has
no rank from 2020 on, only UNKNOWN.
"""
import json
import os
import sys

import migration_lib as L
import model_schema as S

OUT = L.MODEL + 'checks/proposal-compatibility.json'
ACTOR = 'tools/proposal-compat.py (proposal, not applied)'


def vb(kind, year=None, basis=None):
    return S.bound(kind, str(year), 'VINTAGE', 'VINTAGE', basis) if year else S.bound(kind)


def build():
    T = L.read_table
    im = {(r['namespace'], r['legacy_key']): r for r in T('identity/identity-map.jsonl')}
    ids = {r['id'] for t in S.LAYOUT for r in T(t) if 'id' in r}
    prov = {p['id']: p for p in T('cross/provenance.jsonl')}
    atts = T('document/attributions.jsonl')

    def estate(lid):
        return im[('estate', lid)]['stable_id']

    def artifact_named(lid, needle):
        e = estate(lid)
        for a in atts:
            p = prov[a['provenance']]
            if a.get('estate') == e and needle in p['locator']['value'].lower():
                return a['artifact']

    out = {}

    def proposal(name, rows):
        new = {r['id'] for _, r in rows if 'id' in r}
        refs = ids | new
        errs = []
        for ent, r in rows:
            errs += ['%s: %s' % (ent, e) for e in S.check_row(ent, r, refs)]
        out[name] = {'rows': [{'entity': e, 'row': r} for e, r in rows], 'contract_violations': errs,
                     'representable': not errs, 'applied': False}

    def doc(art, quote):
        r = {'id': S.hid('Provenance', 'proposal', art, quote), 'kind': 'DOCUMENT', 'actor': ACTOR,
             'quote': quote}
        if art:
            r['artifact'] = art
        return r

    # Echo de Lynch-Bages: the wine exists; the proposal adds the producer's claim and its time.
    lb = estate('lynch-bages')
    echo = im[('wine-by-slug', 'lynch-bages|echo-de-lynch-bages')]['stable_id']
    rel = S.hid('EstateWineRelationship', lb, echo, 'PRODUCED_BY')
    art = artifact_named('lynch-bages', 'echo')
    p = doc(art, '2nd vin du Chateau Lynch-Bages')
    pred = 'wn_P0001'
    rows = [('Provenance', p),
            ('RankAssertion', {'id': S.hid('RankAssertion', 'proposal', rel, 'PRODUCER'), 'relationship': rel,
                               'tier': 'SECOND', 'scope': 'ESTATE_RANGE', 'claimant': 'PRODUCER',
                               'source_term': '2nd vin', 'validity': {'valid_from': vb('EXACT', 2008, p['id']),
                                                                      'valid_to': S.bound('OPEN')},
                               'provenance': p['id']}),
            ('Observation', {'id': S.hid('Observation', 'proposal', rel), 'subject': rel, 'field': 'rank_statement',
                             'value': '2nd vin du Chateau Lynch-Bages', 'raw_label': None, 'artifact': art,
                             'extraction': {'method': 'PROPOSAL'}, 'confidence': 'PROPOSED',
                             'observed_at': '2026-10-25', 'provenance': p['id'],
                             'subject_status': 'PROPOSED'}),
            ('Wine', {'id': pred, 'name_status': 'KNOWN', 'type': 'RED'}),
            ('NameRecord', {'id': S.hid('NameRecord', 'proposal', pred), 'subject': pred,
                            'name': 'Haut-Bages Averous', 'kind': 'CURRENT',
                            'validity': {'valid_from': S.bound('UNKNOWN'), 'valid_to': vb('NO_LATER_THAN', 2008, p['id'])},
                            'provenance': p['id']}),
            ('IdentityTransition', {'id': S.hid('IdentityTransition', 'proposal', pred, echo), 'kind': 'SUCCEEDED_BY',
                                    'from': pred, 'to': echo, 'at': vb('EXACT', 2008, p['id']),
                                    'certainty': 'UNRESOLVED', 'source_term': "change d'identité pour devenir",
                                    'provenance': p['id']})]
    rows[2][1].pop('raw_label')
    if not art:
        rows[2][1].pop('artifact')
    proposal('Echo de Lynch-Bages', rows)

    # Les Murets de Caillou, blanc: its own Wine, apart from the rouge and the estate's other wines.
    ca = estate('caillou')
    blanc, rouge = 'wn_P0002', 'wn_P0003'
    p = doc(artifact_named('caillou', 'murets'), 'Second Vin blanc sec')
    rows = [('Provenance', p)]
    for w, t in ((blanc, 'WHITE_DRY'), (rouge, 'RED')):
        rows += [('Wine', {'id': w, 'name_status': 'KNOWN', 'type': t}),
                 ('NameRecord', {'id': S.hid('NameRecord', 'proposal', w), 'subject': w, 'name': 'Les Murets de Caillou',
                                 'kind': 'CURRENT', 'validity': {'valid_from': vb('NO_LATER_THAN', 2023, p['id']),
                                                                 'valid_to': S.bound('OPEN')}, 'provenance': p['id']}),
                 ('EstateWineRelationship', {'id': S.hid('EstateWineRelationship', 'proposal', ca, w), 'estate': ca,
                                             'wine': w, 'status': 'ESTABLISHED', 'kind': 'PRODUCED_BY',
                                             'validity': {'valid_from': vb('NO_LATER_THAN', 2023, p['id']),
                                                          'valid_to': S.bound('OPEN')}, 'provenance': p['id']})]
    rows.append(('RankAssertion', {'id': S.hid('RankAssertion', 'proposal', blanc),
                                   'relationship': S.hid('EstateWineRelationship', 'proposal', ca, blanc),
                                   'tier': 'SECOND', 'scope': 'TYPE_RANGE', 'scope_type': 'WHITE_DRY',
                                   'claimant': 'PRODUCER', 'source_term': 'Second Vin blanc sec',
                                   'validity': {'valid_from': vb('NO_LATER_THAN', 2023, p['id']),
                                                'valid_to': S.bound('OPEN')}, 'provenance': p['id']}))
    proposal('Les Murets de Caillou (blanc)', rows)

    # Les Terrasses de Saint Christophe: SECOND 2016-2019, UNKNOWN from 2020.
    tsc = estate('stem-chateau-tour-saint-christophe')
    ter = 'wn_P0004'
    p1 = doc(None, 'second label of Chateau Tour Saint Christophe')
    p2 = doc(None, "made from some of the younger vines planted on the terrasses of the estate")
    p3 = doc(None, "creee et orchestree par l'equipe des Vignobles K")
    rows = [('Provenance', p1), ('Provenance', p2), ('Provenance', p3),
            ('Wine', {'id': ter, 'name_status': 'KNOWN', 'type': 'RED'}),
            ('NameRecord', {'id': S.hid('NameRecord', 'proposal', ter), 'subject': ter,
                            'name': 'Les Terrasses de Saint Christophe', 'kind': 'CURRENT',
                            'validity': {'valid_from': vb('NO_LATER_THAN', 2016, p1['id']), 'valid_to': S.bound('OPEN')},
                            'provenance': p1['id']})]
    for kind, p in (('FROM_ESTATE_VINEYARD', p2), ('MADE_BY_GROUP_TEAM', p3)):
        rows.append(('EstateWineRelationship', {
            'id': S.hid('EstateWineRelationship', 'proposal', tsc, ter, kind), 'estate': tsc, 'wine': ter,
            'status': 'ESTABLISHED', 'kind': kind,
            'validity': {'valid_from': vb('NO_LATER_THAN', 2016, p['id']), 'valid_to': S.bound('OPEN')},
            'provenance': p['id']}))
    r1 = S.hid('EstateWineRelationship', 'proposal', tsc, ter, 'FROM_ESTATE_VINEYARD')
    rows += [('RankAssertion', {'id': S.hid('RankAssertion', 'proposal', ter, '2016'), 'relationship': r1,
                                'tier': 'SECOND', 'scope': 'ESTATE_RANGE', 'claimant': 'PRODUCER',
                                'source_term': 'second label',
                                'validity': {'valid_from': vb('EXACT', 2016, p1['id']),
                                             'valid_to': vb('EXACT', 2019, p1['id'])}, 'provenance': p1['id']}),
             ('RankAssertion', {'id': S.hid('RankAssertion', 'proposal', ter, '2020'), 'relationship': r1,
                                'tier': 'UNKNOWN', 'scope': 'ESTATE_RANGE', 'claimant': 'PRODUCER',
                                'validity': {'valid_from': vb('EXACT', 2020, p1['id']),
                                             'valid_to': vb('NO_EARLIER_THAN', 2023, p1['id'])},
                                'provenance': p1['id']})]
    proposal('Les Terrasses de Saint Christophe', rows)
    return {'_': 'Phase 4 M11: the three pending proposals written as the rows they would add, '
                 'validated against the contract and the model. Not applied (tools/proposal-compat.py).',
            'schema_changes_needed': sum(len(v['contract_violations']) for v in out.values()),
            'proposals': out}


def main():
    r = build()
    for k, v in r['proposals'].items():
        L.out('%-40s %s (%d rows)' % (k, 'REPRESENTABLE' if v['representable'] else 'DOES NOT FIT',
                                      len(v['rows'])))
        for e in v['contract_violations']:
            L.out('   ' + e)
    if '--check' not in sys.argv:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        open(OUT, 'w', encoding='utf-8', newline='\n').write(json.dumps(r, ensure_ascii=False, indent=1) + '\n')
    sys.exit(1 if r['schema_changes_needed'] else 0)


if __name__ == '__main__':
    main()
