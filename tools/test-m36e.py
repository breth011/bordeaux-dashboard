"""Phase M3.6E: the historical Cuvée Mongravey evidence decisions corrected (tools/m36e-apply.py).

    python tools/test-m36e.py

Read-only. Each of the 38 acceptances M3.6C named - a Cuvée de Mongravey sheet accepted as a grand vin - has
one superseding v7 answer: REFUSED, WRONG_WINE, the same question, the document named as Cuvée Mongravey
(wn_00640) by the title the existing rubric reads, which is a name M3.6D recorded. v1-v6 are byte for byte
as they were; the model, the app data and the manifest-driven files are untouched; no vintage is created,
"Mongravey Cuvée Margaux" stays unrecorded, and wn_00158 and wn_00640 are as M3.6D left them.
"""
import collections
import hashlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_cache as CC  # noqa: E402
import evidence as EV  # noqa: E402
import evidence_store as ST  # noqa: E402
import historical_m2_scope as H  # noqa: E402
import migration_lib as L  # noqa: E402
import mig_m6_provenance as M6  # noqa: E402
import m35_rubric as RB  # noqa: E402

BEFORE = '1a58c92'               # M3.6D: the state M3.6E is applied to
M36C = L.ROOT + 'data/audit/m3.6c-cuvee-mongravey-identity.jsonl'
M36D = L.ROOT + 'data/audit/m3.6d-cuvee-mongravey.jsonl'
MANIFEST = L.ROOT + H.M36E_MANIFEST
WINE, GRAND_VIN, ESTATE = 'wn_00640', 'wn_00158', 'es_00158'
CHECKS = []


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode('utf-8')


def manifest():
    return L.jsonl_lines(MANIFEST)


def m36c_decisions():
    return [r for r in L.jsonl_lines(M36C) if r['record'] == 'decision']


def v7():
    return {M6.row_key(d): d for d in H.m36e_evidence_rows()}


def stored(v):
    return {M6.row_key(d): d for d in ST.iter_rows([v])}


@check
def t01_all_38_are_accounted_for():
    m = manifest()
    assert len(m) == 38 and sorted(r['decision'] for r in m) == sorted(r['id'] for r in m36c_decisions())
    assert all(r['result'] in ('APPLIED', 'UNRESOLVED') for r in m)


@check
def t02_they_ask_two_estates_questions():
    # 21 ask for Château Mongravey and were still the v5 acceptance; 17 ask for Château de Braude (the shared
    # group library) and M3.6B had already refused them in v6
    c = collections.Counter((r['asked']['estate'], r['asked']['wine'], r['superseding']['v'], r['superseding']['decision'])
                            for r in manifest())
    assert c == {('bourgeois-chateau-mongravey', 'Château Mongravey', 5, 'ACCEPTED'): 21,
                 ('bourgeois-chateau-de-braude', 'Château de Braude', 6, 'REFUSED'): 17}, c
    assert collections.Counter(r['m36b'] for r in manifest() if r['superseding']['v'] == 5) == \
        {'FLAGGED_RETAINED': 20, 'NOT_IN_M36B': 1}


@check
def t03_every_one_is_cuvee_mongravey_by_its_title():
    names = {RB.fold(n['name']): n for n in L.read_table('identity/names.jsonl') if n['subject'] == WINE}
    for r in manifest():
        assert r['outcome'] == 'CUVEE_MONGRAVEY' and r['wine'] == WINE and not r['failures'], r['decision'][:60]
        n = names[RB.fold(r['document_title'][0])]                  # a recorded name, matched whole
        assert n['name'] == 'Cuvée de Mongravey' and n['kind'] == r['name_kind'] == 'SOURCE_RENDERING', r
        assert r['vintage_stated'] == r['document_title'][1] and r['vintage_created'] is False
    # the title states the vintage; one undated sheet (two questions) states none
    assert sorted(r['artifact'] for r in manifest() if r['vintage_stated'] is None) == ['ar_002548', 'ar_002548']


@check
def t04_each_v7_answer_supersedes_exactly_its_question():
    rows, m = v7(), {r['superseded_by']: r for r in manifest()}
    assert set(rows) == set(m) and len(rows) == 38
    old = {**stored(5), **stored(6)}
    import importlib.util
    spec = importlib.util.spec_from_file_location('m36e', L.ROOT + 'tools/m36e-apply.py')
    X = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(X)
    for k, d in rows.items():
        s = m[k]['superseding']
        prev = old[s['row_key']]
        assert json.loads(k)[:-1] == json.loads(s['row_key'])[:-1] and d['v'] == 7 and prev['v'] == s['v']
        assert (d['decision'], d['code'], d['kind']) == ('REFUSED', 'WRONG_WINE', 'correction')
        assert d['supersedes'] == {'row_key': s['row_key'], 'v': prev['v'], 'decision': prev['decision'], 'code': prev.get('code')}
        assert d['document_is'] == {'title': m[k]['document_title'], 'model_wines': [WINE], 'unlisted': False}
        assert d['points_at'] == {'role': None, 'wine': WINE} and d['replacement']['decision'] is None
        assert d['replacement']['attribution'] is None and 'no vintage of that wine' in d['replacement']['note']
        assert d['read'] == prev['read'] and d['reader'] == X.decider_fingerprint() and not ST.provenance_problem(d)
        assert hashlib.sha256(open(L.ROOT + 'sources/' + d['read']['path'], 'rb').read()).hexdigest() == d['read']['sha256']


@check
def t05_the_corrections_are_the_latest_answers():
    latest = ST.latest_by_context()
    rows = v7()
    for d in rows.values():
        assert latest[EV.row_key(d)[:-1]] is not None and latest[EV.row_key(d)[:-1]]['v'] == 7
    # no question on these bytes still accepts them as Château Mongravey or Château de Braude
    shas = {d['read']['sha256'] for d in rows.values()}
    left = [d for d in latest.values() if (d.get('read') or {}).get('sha256') in shas and d['decision'] == 'ACCEPTED'
            and (d.get('ctx') or {}).get('target_wine') in ('Château Mongravey', 'Château de Braude')]
    assert not left, [M6.row_key(d)[:80] for d in left]


@check
def t06_v1_to_v6_are_byte_for_byte():
    H.evidence_unchanged_but_m36e(BEFORE)
    assert not git('diff', '--stat', BEFORE, '--', *['data/evidence/decisions-v%d.jsonl' % v for v in range(1, 7)]).strip()
    # M3.6H's v8, a later correction, verified (by evidence_unchanged_but_m36e) and set aside
    assert ST.verify() == [] and [v for v in ST.versions() if v != H.M36H_EVIDENCE_VERSION] == [1, 2, 3, 4, 5, 6, 7]
    assert H.evidence_versions_before_m36b() == [1, 2, 3, 4, 5] and H.evidence_rows_before_m36b() == 177127


@check
def t07_no_model_or_generated_data_changed():
    # M3.6F's vintages, a later phase, set aside: with its rows taken out the model is as at BEFORE
    H.unchanged_but_m36d(BEFORE, 'data/model', ':(exclude)data/model/manifest.json')
    H.model_changes_are_m2_only(BEFORE)
    assert not git('diff', '--stat', BEFORE, '--', 'data/app', ':(glob)data/*.js', 'data/sources.json',
                   'data/audit/data-gap-register.jsonl', 'data/audit/m3.6b-historical-flags.jsonl',
                   'data/audit/m3.6b-correction-application.jsonl', 'data/audit/m3.6c-cuvee-mongravey-identity.jsonl',
                   'data/audit/m3.6d-cuvee-mongravey.jsonl', 'assets', 'index.html').strip()
    # the model reads evidence links from v4-v5 only: a v7 answer cannot reach it
    assert not [l for l in L.read_table('observation/evidence-links.jsonl') if l['evidence_version'] not in (4, 5)]


@check
def t08_both_wines_are_as_m36d_left_them():
    wines = {w['id']: w for w in L.read_table('identity/wines.jsonl')}
    assert wines[WINE]['type'] == 'RED' and GRAND_VIN in wines
    ew = [(r['estate'], r['wine']) for r in L.read_table('state/estate-wine.jsonl') if r['estate'] == ESTATE]
    assert sorted(w for _, w in ew) == [GRAND_VIN, WINE]
    assert sorted(n['name'] for n in L.read_table('identity/names.jsonl') if n['subject'] == WINE) == \
        ['Cuvée Mongravey', 'Cuvée de Mongravey', 'Mongravey Cuvée Spéciale']


@check
def t09_the_margaux_name_stays_unresolved():
    margaux = RB.fold('Mongravey Cuvée Margaux')
    assert not [n for n in L.read_table('identity/names.jsonl') if RB.fold(n['name']) == margaux]
    assert not [r for r in manifest() if margaux in RB.fold(r['document_title'][0])]
    assert [r for r in L.jsonl_lines(M36D) if r.get('record') == 'unresolved_name' and not r.get('applied')]


@check
def t10_no_vintage_was_created():
    # none by M3.6E; M3.6F's, read later from the wine's own sheets, are its manifest's and never 1999
    m36f = L.ROOT + 'data/audit/m3.6f-cuvee-vintages.jsonl'
    later = {r['label'] for r in L.jsonl_lines(m36f) if r['record'] == 'vintage' and r['applied']} \
        if os.path.exists(m36f) else set()
    assert {v['label'] for v in L.read_table('identity/vintages.jsonl') if v['wine'] == WINE} == later
    assert '1999' not in later
    assert all(r['vintage_created'] is False for r in manifest())
    first = [r for r in L.jsonl_lines(M36D) if r.get('fact') == 'first_vintage']
    assert len(first) == 1 and first[0]['applied'] is False and first[0]['value']['kind'] == 'FIRST_VINTAGE_STATED'


@check
def t11_deterministic():
    for cmd in ([sys.executable, L.ROOT + 'tools/m36e-apply.py', '--check'],
                [sys.executable, L.ROOT + 'tools/migrate.py', '--check']):
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
