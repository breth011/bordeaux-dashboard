"""Phase M3.6D: the canonical Cuvée Mongravey wine (tools/m36d-cuvee.py, read by tools/mig_m4_wines.py).

    python tools/test-m36d.py

Read-only. One Wine, its three supported names and not the unresolved fourth, PRODUCED_BY Château
Mongravey with its stated first vintage as the relationship's start on the VINTAGE axis, a PLOT_SELECTION
descriptor and no rank, type RED - every fact on a provenance naming the held document and its words.
No vintage, figure, attribution or evidence decision is created, the grand vin is untouched, and the
38 historical acceptances M3.6C named are exactly as they were.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_cache as CC  # noqa: E402
import migration_lib as L  # noqa: E402

BEFORE = '27a05d6'               # the state M3.6D is applied to
MANIFEST = L.ROOT + 'data/audit/m3.6d-cuvee-mongravey.jsonl'
M36C = L.ROOT + 'data/audit/m3.6c-cuvee-mongravey-identity.jsonl'
ACTOR = 'tools/m36d-cuvee.py'
ESTATE, GRAND_VIN, KEY = 'es_00158', 'wn_00158', 'bourgeois-chateau-mongravey|cuvee-mongravey'
NAMES = {'Cuvée Mongravey': 'CURRENT', 'Cuvée de Mongravey': 'SOURCE_RENDERING',
         'Mongravey Cuvée Spéciale': 'MARKET_ALIAS'}
UNRESOLVED = 'Mongravey Cuvée Margaux'
# the model tables M3.6D adds rows to; every other one is byte-identical to BEFORE
M36D_TABLES = {'cross/provenance.jsonl', 'identity/identity-map.jsonl', 'identity/names.jsonl',
               'identity/wines.jsonl', 'state/estate-wine.jsonl', 'state/wine-descriptors.jsonl',
               'manifest.json', 'derived/estate-wines.json'}
CHECKS = []


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode('utf-8')


def table(rel):
    return L.read_table(rel)


def before(rel):
    try:
        return [json.loads(x) for x in git('show', '%s:data/model/%s' % (BEFORE, rel)).splitlines() if x.strip()]
    except subprocess.CalledProcessError:
        return []


def added(rel):
    old = {json.dumps(r, sort_keys=True) for r in before(rel)}
    return [r for r in table(rel) if json.dumps(r, sort_keys=True) not in old]


PROV = {p['id']: p for p in table('cross/provenance.jsonl')}
SLUG = [r for r in table('identity/identity-map.jsonl') if r['namespace'] == 'wine-by-slug' and r['legacy_key'] == KEY]
WINE = SLUG[0]['stable_id'] if len(SLUG) == 1 else None


def rel_of(wid):
    return [r for r in table('state/estate-wine.jsonl') if r['wine'] == wid]


@check
def t01_exactly_one_cuvee_mongravey_wine():
    assert WINE, ('one wine-by-slug key for the Cuvée', SLUG)
    cur = [n for n in table('identity/names.jsonl') if n['name'] == 'Cuvée Mongravey' and n['kind'] == 'CURRENT']
    assert [n['subject'] for n in cur] == [WINE]
    assert [w['id'] for w in added('identity/wines.jsonl')] == [WINE]            # the only wine M3.6D adds
    # no other wine bears any of its names
    assert {n['subject'] for n in table('identity/names.jsonl') if n['name'] in NAMES} == {WINE}


@check
def t02_produced_by_chateau_mongravey():
    (r,) = rel_of(WINE)
    assert (r['estate'], r['kind'], r['status']) == (ESTATE, 'PRODUCED_BY', 'ESTABLISHED')
    est = {e['id'] for e in table('identity/estates.jsonl')}
    assert ESTATE in est and len(added('identity/estates.jsonl')) == 0      # no estate was created


@check
def t03_its_role_is_a_plot_selection_with_no_rank():
    # the contract's OTHER_CUVEE: no RankAssertion, and what the wine is as a WineDescriptor
    (r,) = rel_of(WINE)
    assert not [a for a in table('state/rank-assertions.jsonl') if a['relationship'] == r['id']]
    (d,) = [d for d in table('state/wine-descriptors.jsonl') if d['wine'] == WINE]
    assert (d['kind'], d['source_term']) == ('PLOT_SELECTION', 'cuvée spéciale')
    assert 'best plots' in PROV[d['provenance']]['quote']
    for rel in ('state/rank-assertions.jsonl', 'state/rank-absences.jsonl'):
        assert table(rel) == before(rel), rel                              # no rank was added or changed
    assert 'OTHER_CUVEE' not in open(L.MODEL + 'state/wine-descriptors.jsonl', encoding='utf-8').read()


@check
def t04_its_colour_is_red_on_its_documents():
    (w,) = [w for w in table('identity/wines.jsonl') if w['id'] == WINE]
    assert w['type'] == 'RED'
    p = PROV[SLUG[0]['provenance']]                                        # the provenance it is minted with
    assert p['kind'] == 'DERIVATION' and p['actor'] == ACTOR and 'RED' in p['quote']
    quotes = {PROV[x]['quote'] for x in p['derived_from']}
    assert quotes == {'Grape Varieties: 30% Merlot, 70% Cabernet Sauvignon', 'Brilliant ruby color'}


@check
def t05_the_three_supported_names():
    got = {n['name']: n['kind'] for n in table('identity/names.jsonl') if n['subject'] == WINE}
    assert got == NAMES, got
    disp = [r for r in table('identity/identity-map.jsonl') if r['namespace'] == 'wine-by-display-name'
            and r['legacy_key'] == 'bourgeois-chateau-mongravey|Cuvée Mongravey']
    assert [r['stable_id'] for r in disp] == [WINE]


@check
def t06_the_unresolved_name_is_not_recorded():
    for rel in ('identity/names.jsonl', 'identity/identity-map.jsonl'):
        assert UNRESOLVED not in open(L.MODEL + rel, encoding='utf-8').read(), rel
    un = [r for r in L.jsonl_lines(MANIFEST) if r['record'] == 'unresolved_name']
    assert [(r['value']['name'], r['applied']) for r in un] == [(UNRESOLVED, False)]


@check
def t07_the_first_vintage_is_stated_and_waits_for_the_historical_gate():
    # recorded as the sheet states it, FIRST_VINTAGE_STATED 1999, and not applied: a dated statement is a
    # historical claim, and Historical M3's gate admits none (E3 rests on a misattributed v5 acceptance)
    (m,) = [x for x in L.jsonl_lines(MANIFEST) if x['fact'] == 'first_vintage']
    assert m['value'] == {'kind': 'FIRST_VINTAGE_STATED', 'vintage': 1999} and m['quote'] == '1st Vintage: 1999'
    assert m['applied'] is False and 'E3' in m['why'] and 'E7' in m['why']
    (r,) = rel_of(WINE)
    assert r['validity'] == {'valid_from': {'kind': 'UNKNOWN'}, 'valid_to': {'kind': 'OPEN'}}   # like every other
    claim = {'claimed_validity', 'claimed_window', 'statement_mode'}
    assert not [o['id'] for o in table('observation/observations.jsonl') if claim & set(o)]
    assert not [p for p in PROV.values() if p.get('actor') == ACTOR and '1999' in (p.get('quote') or '')]
    text = open(MANIFEST, encoding='utf-8').read() + open(L.MODEL + 'cross/provenance.jsonl', encoding='utf-8').read()
    assert 'EARLIEST_DOCUMENTED' not in text


@check
def t08_no_vintage_was_created():
    # M3.6D made none; the vintages M3.6F later read from the wine's own sheets are set aside, exactly
    m36f = L.ROOT + 'data/audit/m3.6f-cuvee-vintages.jsonl'
    later = {r['label'] for r in L.jsonl_lines(m36f) if r['record'] == 'vintage' and r['applied']} \
        if os.path.exists(m36f) else set()
    assert {v['label'] for v in table('identity/vintages.jsonl') if v.get('wine') == WINE} == later
    assert [v for v in table('identity/vintages.jsonl') if v.get('wine') != WINE] == before('identity/vintages.jsonl')
    prov = {p['id']: p for p in table('cross/provenance.jsonl')}
    for rel in ('state/vintage-statements.jsonl', 'document/attributions.jsonl', 'observation/observations.jsonl',
                'canonical/values.jsonl'):
        assert all((prov.get(r.get('provenance')) or {}).get('actor') == 'tools/m36f-vintages.py'
                   for r in table(rel) if WINE in json.dumps(r)), rel
    wv = json.load(open(L.MODEL + 'derived/wine-vintages.json', encoding='utf-8'))
    assert set(wv.get(WINE, [])) == later


@check
def t09_the_grand_vin_is_unchanged():
    for rel in ('identity/wines.jsonl', 'identity/names.jsonl', 'identity/identity-map.jsonl',
                'state/estate-wine.jsonl', 'state/classification-memberships.jsonl',
                'state/appellation-memberships.jsonl', 'identity/estates.jsonl'):
        now = [r for r in table(rel) if GRAND_VIN in json.dumps(r) or ESTATE in json.dumps(r)
               and WINE not in json.dumps(r)]
        old = [r for r in before(rel) if GRAND_VIN in json.dumps(r) or ESTATE in json.dumps(r)]
        assert now == old, rel


@check
def t10_the_38_historical_acceptances_are_untouched():
    dec = [r for r in L.jsonl_lines(M36C) if r['record'] == 'decision']
    assert len(dec) == 38
    keys = {r['id'] for r in dec}
    links = [e for e in table('observation/evidence-links.jsonl') if e['row_key'] in keys]
    old = [e for e in before('observation/evidence-links.jsonl') if e['row_key'] in keys]
    assert links == old and len(links) == 38 and not [e for e in links if e.get('wine') == WINE]
    assert not git('diff', '--stat', BEFORE, '--', 'data/audit/m3.6b-historical-flags.jsonl',
                   'data/audit/m3.6b-correction-application.jsonl', M36C[len(L.ROOT):]).strip()


@check
def t11_no_evidence_decision_was_rewritten():
    import historical_m2_scope as H                 # M3.6E's v7, a later correction, set aside: v1-v6 as they were
    H.evidence_unchanged_but_m36e(BEFORE)


@check
def t12_every_new_fact_has_its_provenance():
    rows = {(rel, json.dumps(r, sort_keys=True)) for rel in M36D_TABLES if rel.endswith('.jsonl')
            for r in added(rel) if rel != 'cross/provenance.jsonl'}
    assert rows
    for rel, s in rows:
        r = json.loads(s)
        if rel == 'identity/wines.jsonl':
            # a Wine row has no provenance field (the contract): it is on the key it is minted with (t04)
            assert r['id'] == WINE and PROV[SLUG[0]['provenance']]['actor'] == ACTOR
            continue
        p = PROV[r['provenance']]
        if rel == 'identity/identity-map.jsonl' and r['namespace'] == 'wine-by-display-name':
            continue                         # the display-name rule every wine shares (M4), not a fact
        if __import__('historical_m2_scope').is_m310a_row(rel, r, PROV):
            continue                         # M3.10A's registered artifacts' keys, a later phase

        assert p['actor'] == ACTOR and p['code_state']['stream'] == 'M3.6D', (rel, r)
        if p['kind'] == 'DOCUMENT':
            assert p['artifact'] and p['quote'], (rel, r)
    facts = [x for x in L.jsonl_lines(MANIFEST) if x['applied']]
    docs = [p for p in PROV.values() if p.get('actor') == ACTOR and p['kind'] == 'DOCUMENT']
    assert sorted((p['artifact'], p['quote']) for p in docs) == sorted((x['artifact'], x['quote']) for x in facts)


@check
def t13_only_m36d_changed_the_model_and_nothing_else_moved():
    import historical_m2_scope as H                 # M3.6F's vintages and values, a later phase: additions, set aside
    changed = set(git('diff', '--name-only', BEFORE, '--', 'data/model').split())
    assert {c[len('data/model/'):] for c in changed} <= M36D_TABLES | set(H.M36F_FILES) | set(H.M310A_FILES) | set(H.M310B_FILES), sorted(changed)
    H.unchanged_but_m310a(BEFORE, *('data/model/' + f for f in ('identity/artifacts.jsonl', 'document/placements.jsonl', 'document/locators.jsonl')))   # M3.10A, a later phase
    H.unchanged_but_m36d(BEFORE, *('data/model/' + f for f in H.M36F_FILES))
    for rel in M36D_TABLES - {'manifest.json', 'derived/estate-wines.json'}:
        old = {json.dumps(r, sort_keys=True) for r in before(rel)}
        new = {json.dumps(r, sort_keys=True) for r in table(rel)}
        assert old <= new, (rel, 'a row changed or was removed')
    __import__('historical_m2_scope').register_changes_are_m34b_only(BEFORE)   # M3.10B's resolution, a later linking phase
    assert not git('diff', '--stat', BEFORE, '--', 'data/app', 'data/sources.json', ':(glob)data/*.js',
                   'index.html', 'assets').strip()
    ew = json.load(open(L.MODEL + 'derived/estate-wines.json', encoding='utf-8'))
    assert ew[ESTATE] == sorted([GRAND_VIN, WINE])


@check
def t14_deterministic():
    for cmd in ([sys.executable, L.ROOT + 'tools/m36d-cuvee.py', '--check'],
                [sys.executable, L.ROOT + 'tools/migrate.py', '--check'],
                [sys.executable, L.ROOT + 'tools/build-indexes.py', '--check'],
                [sys.executable, L.ROOT + 'tools/build-app-data.py', '--check']):
        out = CC.run(cmd)
        assert out.returncode == 0, (cmd[1], out.stdout[-300:] + out.stderr[-300:])


def main():
    fails = 0
    for f in CHECKS:
        try:
            f()
            print('ok   %s' % f.__name__)
        except Exception as ex:
            fails += 1
            print('FAIL %s: %s' % (f.__name__, str(ex)[:400]))
    print('%d check(s), %s' % (len(CHECKS), 'all pass' if not fails else '%d FAIL' % fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
