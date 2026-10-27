"""Phase M3.6F: Cuvée Mongravey's vintages from its held technical sheets (tools/m36f-vintages.py, read by
tools/mig_m5_vintages.py and tools/mig_m7_observations.py).

    python tools/test-m36f.py

Read-only. Six vintages of wn_00640 - each titled by a held technical sheet whose latest evidence answer names
the wine - and their class-A values (months, new-oak share), each value an observation per stating sheet
quoting its line, one reconciliation, a SOURCED canonical value. Nothing else: no 1999 vintage, no blend or
yield from the vineyard section, no production field, no alias, wn_00158 and every earlier row as they were,
v1-v7 of the evidence store byte for byte.
"""
import collections
import hashlib
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_cache as CC  # noqa: E402
import historical_m2_scope as H  # noqa: E402
import migration_lib as L  # noqa: E402
import m35_rubric as RB  # noqa: E402

BEFORE = '345f892'               # M3.6E: the state M3.6F is applied to
MANIFEST = L.ROOT + 'data/audit/m3.6f-cuvee-vintages.jsonl'
ACTOR = 'tools/m36f-vintages.py'
WINE, GRAND_VIN = 'wn_00640', 'wn_00158'
YEARS = ['2015', '2016', '2018', '2019', '2020', '2022']
CHECKS = []


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode('utf-8')


def manifest(record=None):
    return [r for r in L.jsonl_lines(MANIFEST) if record is None or r['record'] == record]


def prov():
    return {p['id']: p for p in L.read_table('cross/provenance.jsonl')}


def m36f(rel):
    p = prov()
    return [r for r in L.read_table(rel) if (p.get(r.get('provenance')) or {}).get('actor') == ACTOR]


@check
def t01_six_vintages_of_the_cuvee():
    got = sorted(v['label'] for v in L.read_table('identity/vintages.jsonl') if v['wine'] == WINE)
    assert got == YEARS == sorted(r['label'] for r in manifest('vintage') if r['applied']), got
    wv = json.load(open(L.MODEL + 'derived/wine-vintages.json', encoding='utf-8'))
    assert sorted(wv[WINE]) == YEARS


@check
def t02_each_vintage_rests_on_its_own_titled_technical_sheets():
    docs = {d['artifact']: d for d in manifest('document')}
    arts = {a['id']: a for a in L.read_table('identity/artifacts.jsonl')}
    for v in manifest('vintage'):
        assert v['documents'], v
        for a in v['documents']:
            d = docs[a]
            assert d['used'] and d['kind'] == 'TECHNICAL_SHEET' and str(d['vintage']) == v['label'], d
            assert d['title_line'] == 'Cuvée de Mongravey %s' % v['label'], d['title_line']
            assert d['sha256'] == arts[a]['sha256']
            text = json.load(open(L.ROOT + 'sources/discovery/extracted/%s.json' % d['sha256'], encoding='utf-8'))
            assert text['pages'][0].strip().splitlines()[0].strip() == d['title_line']
    # the sheets that create nothing: the press-review sheet and the undated one
    assert sorted((d['artifact'], d['used']) for d in docs.values() if not d['used']) == \
        [('ar_002548', False), ('ar_010393', False)]


@check
def t03_no_1999_vintage_and_no_other_year():
    assert not [v for v in L.read_table('identity/vintages.jsonl') if v['wine'] == WINE and v['label'] not in YEARS]
    assert [r['vintage'] for r in manifest('not_created')] == ['vt:%s:1999' % WINE]
    first = [r for r in L.jsonl_lines(L.ROOT + H.M36D_MANIFEST) if r.get('fact') == 'first_vintage']
    assert first[0]['applied'] is False and first[0]['value']['kind'] == 'FIRST_VINTAGE_STATED'


@check
def t04_the_values_are_class_a_and_read_exactly():
    vals = {(v['subject'], v['field']): v for v in L.read_table('canonical/values.jsonl') if v['subject'].startswith('vt:%s:' % WINE)}
    want = {('vt:%s:%s' % (WINE, y), 'oak'): 100 for y in YEARS}
    want.update({('vt:%s:%s' % (WINE, y), 'months'): '18' for y in YEARS if y != '2015'})
    assert {k: v['value'] for k, v in vals.items()} == want, sorted(vals)
    assert all(v['status'] == 'SOURCED' for v in vals.values())
    # 2015 says only "24 months maturing depending on vintages": kept verbatim, not the vintage's figure
    m15 = [r for r in manifest('value') if r['vintage'].endswith(':2015') and r['field'] == 'months'][0]
    assert not m15['applied'] and m15['status'] == 'QUALIFIED_ONLY' and \
        [q['quote'] for q in m15['qualified']] == ['24 months maturing depending on vintages']


@check
def t05_every_value_has_its_observations_and_reconciliation():
    p = prov()
    obs = {o['id']: o for o in m36f('observation/observations.jsonl')}
    rec = {r['id']: r for r in L.read_table('reconciliation/reconciliations.jsonl')}
    n = 0
    for v in m36f('canonical/values.jsonl'):
        r = rec[v['reconciliation']]
        assert r['resolver'] == ACTOR and r['selected'] in r['candidates'] and r['subject'] == v['subject']
        assert (r['rule'], r['status']) in (('ONLY_CANDIDATE', 'SINGLE'), ('UNANIMOUS', 'AGREED'))
        assert len(r['candidates']) == (1 if r['rule'] == 'ONLY_CANDIDATE' else 2)
        d = p[r['provenance']]
        assert d['kind'] == 'DERIVATION' and d['actor'] == ACTOR
        for oid in r['candidates']:
            o = obs[oid]
            assert o['subject'] == v['subject'] and o['field'] == v['field'] and o['value'] == v['value']
            pd = p[o['provenance']]
            assert pd['kind'] == 'DOCUMENT' and pd['artifact'] == o['artifact'] and pd['quote'] == o['raw_value']
            assert o['provenance'] in d['derived_from'] and pd['code_state']['stream'] == 'M3.6F'
            n += 1
        assert v['provenance'] in d['derived_from']
    assert n == len(obs) == 21 and len(m36f('canonical/values.jsonl')) == 11


@check
def t06_each_quote_is_a_line_of_its_held_sheet():
    arts = {a['id']: a for a in L.read_table('identity/artifacts.jsonl')}
    exact = re.compile(r'^(18 months maturing|18 mois d.élevage\.|100% new oak|100% bois neuf\.)$')
    for o in m36f('observation/observations.jsonl'):
        text = json.load(open(L.ROOT + 'sources/discovery/extracted/%s.json' % arts[o['artifact']]['sha256'], encoding='utf-8'))
        lines = [l.strip() for l in '\n'.join(p for p in text['pages'] if isinstance(p, str)).splitlines()]
        assert o['raw_value'] in lines and exact.match(o['raw_value']), (o['artifact'], o['raw_value'])


@check
def t07_no_unsupported_value():
    # nothing for the fields the manifest withholds; no field but months and oak on the wine's vintages
    fields = {(o['subject'], o['field']) for o in L.read_table('observation/observations.jsonl') if o['subject'].startswith('vt:%s:' % WINE)}
    assert {f for _, f in fields} == {'months', 'oak'}
    held = collections.Counter((r['field'], r['status']) for r in manifest('withheld'))
    assert held == {(f, s): 6 for f, s in (('yld', 'SCOPE_NOT_ESTABLISHED'), ('blend', 'SCOPE_NOT_ESTABLISHED'),
                                           ('production', 'CLASS_B_NO_FIELD'), ('window', 'CLASS_B'),
                                           ('alc', 'NOT_STATED'), ('ph', 'NOT_STATED'), ('ta', 'NOT_STATED'),
                                           ('sug', 'NOT_STATED'), ('harvest', 'NOT_STATED'), ('pick', 'NOT_STATED'))}, held
    # the vineyard section's grape varieties are not the wine's blend
    assert not [v for v in L.read_table('canonical/values.jsonl') if v['subject'].startswith('vt:%s:' % WINE) and v['field'] == 'blend']


@check
def t08_the_wines_names_and_estate_are_as_they_were():
    for rel in ('identity/wines.jsonl', 'identity/names.jsonl', 'state/estate-wine.jsonl',
                'state/wine-descriptors.jsonl', 'state/rank-assertions.jsonl'):
        assert not git('diff', '--stat', BEFORE, '--', 'data/model/' + rel).strip(), rel
    H.unchanged_but_m310a(BEFORE, 'data/model/identity/identity-map.jsonl')   # M3.10A's artifact keys aside
    margaux = RB.fold('Mongravey Cuvée Margaux')
    assert not [n for n in L.read_table('identity/names.jsonl') if RB.fold(n['name']) == margaux]
    assert not [v for v in L.read_table('identity/vintages.jsonl') if v['wine'] == GRAND_VIN and
                v not in [json.loads(x) for x in git('show', BEFORE + ':data/model/identity/vintages.jsonl').splitlines()]]


@check
def t09_only_m36f_changed_the_model():
    H.unchanged_but_m36d(BEFORE, 'data/model', ':(exclude)data/model/manifest.json')
    H.model_changes_are_m2_only(BEFORE)
    changed = set(git('diff', '--name-only', BEFORE, '--', 'data/model').split())
    # M3.10A's registrations, a later phase, set aside (unchanged_but_m36d verified they hold only its rows)
    assert changed <= {'data/model/' + f for f in H.M36F_FILES + H.M310A_FILES + ('cross/provenance.jsonl', 'manifest.json')}, changed
    assert not git('diff', '--stat', BEFORE, '--', 'data/app', ':(glob)data/*.js', 'data/sources.json',
                   'data/audit/data-gap-register.jsonl', 'assets', 'index.html').strip()


@check
def t10_evidence_v1_to_v7_byte_for_byte():
    # M3.6H's v8, a later correction, verified and set aside: v1-v7 and their index entries as they were
    H.evidence_unchanged_but_m36h(BEFORE)
    assert not git('diff', '--stat', BEFORE, '--', *['data/evidence/decisions-v%d.jsonl' % v for v in range(1, 8)]).strip()
    assert not git('status', '--porcelain', '--', *['data/evidence/decisions-v%d.jsonl' % v for v in range(1, 8)]).strip()


@check
def t11_deterministic():
    for cmd in ([sys.executable, L.ROOT + 'tools/m36f-vintages.py', '--check'],
                [sys.executable, L.ROOT + 'tools/migrate.py', '--check'],
                [sys.executable, L.ROOT + 'tools/build-indexes.py', '--check'],
                [sys.executable, L.ROOT + 'tools/build-app-data.py', '--check']):
        out = CC.run(cmd, cwd=L.ROOT)
        assert out.returncode == 0, (cmd[1], (out.stdout + out.stderr)[-400:])


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
