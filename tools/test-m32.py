"""M3.2: existing-data recovery.

    python tools/test-m32.py

Read-only. The recovery audit (tools/m32-recovery.py -> data/audit/m32-recovery-candidates.jsonl)
proposes; the migration applies only its APPLY_* rows. These checks hold the rules
(tools/m32_recovery.py) to what counts as a figure stated in its own document, on text built here;
hold the audit and the model to each other; and hold everything else to what it was: values,
evidence, raw sources, open decisions.
"""
import hashlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import historical_m2_scope as H  # noqa: E402
import m32_recovery as R  # noqa: E402
import migration_lib as L  # noqa: E402

BEFORE = 'eb3772e'               # the state before M3.2
AUDIT = L.ROOT + 'data/audit/m32-recovery-candidates.jsonl'
CHECKS = []


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode()


def audit():
    return [json.loads(l) for l in open(AUDIT, encoding='utf-8')]


def seg(*texts):
    return [('p:%d' % (i + 1), t) for i, t in enumerate(texts)]


def cls(field, value, *texts):
    return R.classify(field, value, seg(*texts))['classification']


# -- the rules, on text built here ---------------------------------------------------------------

@check
def own_sheet_labelled_value_matches():
    assert cls('alc', 13.5, 'Degré alcoolique : 13,5 % vol.') == 'MODEL_MATCHES'
    assert cls('alc', 13.1, 'Alcohol: 13,1° Total acidity: 3,5') == 'MODEL_MATCHES'
    assert cls('ph', 3.81, 'TAV 13,43 AT 3,6 pH 3,81') == 'MODEL_MATCHES'
    assert cls('yld', 50, 'Rendement : 50hl/ha') == 'MODEL_MATCHES'
    assert cls('oak', 65, 'Elevage 100% en barriques (dont 65% neuves) pendant 15 mois') == 'MODEL_MATCHES'
    assert cls('months', 12, 'Elevage : 12 mois en fûts de chêne') == 'MODEL_MATCHES'
    assert cls('blend', {'ME': 70, 'CS': 27, 'PV': 3}, 'Assemblage : 70% Merlot, 27% Cabernet Sauvignon, 3% Petit Verdot') == 'MODEL_MATCHES'


@check
def model_conflict_is_classified_and_never_a_match():
    assert cls('yld', 28.8, 'Rendement 28,5 hl/ha Assemblage') == 'MODEL_CONFLICT'
    assert cls('yld', 40, 'strict selection resulted in a final yield of 30 hl/ha') == 'MODEL_CONFLICT'
    assert cls('alc', 14, 'Alcool : 13,5 % vol.') == 'MODEL_CONFLICT'


@check
def duplicate_values_are_refused():
    # two wines on one sheet, each with its yield
    assert cls('yld', 25, 'Yield: 25 hl/ha Yield: 28 hl/ha') == 'DUPLICATE_VALUE'


@check
def ambiguous_mapping_is_refused():
    # a bound of a general range is not the vintage's figure
    assert cls('oak', 80, 'Élevage : 15 mois en barriques (50-80 % neuves suivant millésime)') == 'AMBIGUOUS'
    assert cls('months', 18, 'aged in barrels for between 16 to 18 months') != 'MODEL_MATCHES'
    # a number without its field's label is not that field
    assert cls('alc', 13, '13 %') == 'AMBIGUOUS'
    assert cls('ph', 3.5, 'the yield was 3,5 tonnes') != 'MODEL_MATCHES'


@check
def semantic_field_mapping_is_exact():
    # "14 % Cabernet Franc" is a blend share, not an alcohol; "100% Alcohol" is not 100 % vol
    assert cls('alc', 14, 'Assemblage 86 % Merlot 14 % Cabernet Franc') != 'MODEL_MATCHES'
    assert cls('alc', 12.5, 'New barrels 100% Alcohol 12,5% Bottling') == 'MODEL_MATCHES'
    # the planting mix is not the vintage's assemblage (D1 stays open)
    assert cls('blend', {'CS': 57, 'ME': 31, 'CF': 12},
               'GRAPE VARIETIES: Cabernet Sauvignon 57% Merlot 31% Cabernet Franc 12% BLENDING see below') != 'MODEL_MATCHES'
    assert cls('blend', {'ME': 70, 'CF': 30}, 'Superﬁcie 7 hectares Assemblage 70 % Merlot, 30% Cabernet franc') == 'MODEL_MATCHES'
    # fields with no deterministic reading are not guessed
    assert cls('pick', {'ALL': '09-20|'}, 'Vendanges le 20 septembre') == 'FIELD_NOT_CHECKABLE'


@check
def units_are_preserved():
    # recovery attaches a source; the value and its unit are the model's, untouched
    a = audit()
    old = {(json.loads(l)['subject'], json.loads(l)['field']): json.loads(l)
           for l in git('show', BEFORE + ':data/model/canonical/values.jsonl').splitlines()}
    for c in L.read_table('canonical/values.jsonl'):
        o = old[(c['subject'], c['field'])]
        assert c['value'] == o['value'], (c['subject'], c['field'])
    obs_old = {json.loads(l)['id']: json.loads(l) for l in git('show', BEFORE + ':data/model/observation/observations.jsonl').splitlines()}
    for o in L.read_table('observation/observations.jsonl'):
        p = obs_old[o['id']]
        assert (o['value'], o.get('unit'), o.get('qualifier')) == (p['value'], p.get('unit'), p.get('qualifier')), o['id']
    assert a


# -- the audit and the model -----------------------------------------------------------------------

@check
def candidate_generation_is_deterministic():
    out = subprocess.run([sys.executable, L.ROOT + 'tools/m32-recovery.py', '--check'], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr


@check
def application_is_deterministic():
    out = subprocess.run([sys.executable, L.ROOT + 'tools/migrate.py', '--check'], capture_output=True, text=True)
    assert out.returncode == 0 and 'byte for byte' in out.stdout, out.stdout + out.stderr
    out = subprocess.run([sys.executable, L.ROOT + 'tools/build-app-data.py', '--check'], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr


@check
def exact_artifact_provenance():
    prov = {p['id']: p for p in L.read_table('cross/provenance.jsonl')}
    arts = {a['id']: a for a in L.read_table('identity/artifacts.jsonl')}
    applied = {r['id']: r for r in audit() if r['disposition'] == 'APPLY_PROVENANCE'}
    seen = 0
    for p in prov.values():
        if not H.is_m32_source(p):
            continue
        r = applied[p['code_state']['candidate']]
        assert p['artifact'] == r['source']['artifact'] and arts[p['artifact']]['bytes_available'], p['id']
        assert arts[p['artifact']]['sha256'] == r['source']['sha256']
        assert p['quote'] == r['evidence']['quote'] and p['code_state']['locus'] == r['evidence']['locus']
        assert p['code_state']['basename'] == r['source']['filename']
        seen += 1
    assert seen == len(applied) == 716, (seen, len(applied))


@check
def own_sheet_recovery_uses_the_records_own_sheet_and_mapping():
    refs = {(('data/' + r['origin']), r['record_key']): r for r in L.read_table('document/legacy-references.jsonl')
            if r['origin'] in ('fiches.js', 'cuvees.js') and not r.get('field')}
    pls = {p['id']: p for p in L.read_table('document/placements.jsonl')}
    vint = {'vt:%s:%s' % (v['wine'], v['label']) for v in L.read_table('identity/vintages.jsonl')}
    for r in audit():
        if r['stream'] != 'A' or r['disposition'] != 'APPLY_PROVENANCE':
            continue
        t = r['target']
        ref = refs[(t['record_file'], t['record'])]
        held = {pls[c]['artifact'] for c in ref['candidates'] if c in pls}
        assert held == {r['source']['artifact']}, t                    # exactly the record's one sheet
        assert t['subject'] in vint and t['subject'].endswith(':' + t['record'].rsplit('|', 1)[1]), t
        assert r['classification'] == 'MODEL_MATCHES' and r['evidence']['quote'], t


@check
def provenance_history_is_preserved():
    prov = {p['id']: p for p in L.read_table('cross/provenance.jsonl')}
    old_ids = {json.loads(l)['id'] for l in git('show', BEFORE + ':data/model/cross/provenance.jsonl').splitlines()}
    assert old_ids <= set(prov), 'a provenance row was removed'
    for p in prov.values():
        if H.is_m32_source(p):
            assert p['derived_from'][0] in old_ids and prov[p['derived_from'][0]]['kind'] == 'LEGACY_RECORD_SOURCE'
    H.model_changes_are_m2_only(BEFORE)


@check
def model_missing_and_conflicts_are_never_applied():
    for r in audit():
        if r['classification'] != 'MODEL_MATCHES':
            assert not r['disposition'].startswith('APPLY'), r['key']
            assert r['proposed'] is None, r['key']
    # a conflict stays with its legacy value and its record source
    cv = {(c['subject'], c['field']): c for c in L.read_table('canonical/values.jsonl')}
    for r in audit():
        if r['classification'] == 'MODEL_CONFLICT':
            c = cv[(r['target']['subject'], r['target']['field'])]
            assert c['status'] == 'LEGACY_RECORD_SOURCE_ONLY' and c['value'] == r['current_value'], r['key']


@check
def no_raw_source_or_evidence_mutation():
    assert not git('diff', '--stat', BEFORE, '--', 'data/evidence', 'data/discovery', ':(glob)data/*.js',
                   'data/sources.json', 'data/scope', 'data/review').strip()
    b0 = json.load(open(L.MODEL + 'baseline.json', encoding='utf-8'))['groups']
    for g in b0:
        assert L.group_hashes(g)['digest'] == b0[g]['digest'], g
    # the held bytes behind every applied source are still exactly what the model proved
    arts = {a['id']: a for a in L.read_table('identity/artifacts.jsonl')}
    pls = {}
    for p in L.read_table('document/placements.jsonl'):
        if p.get('artifact') and p['locator']['kind'] == 'LOCAL_PATH':
            pls.setdefault(p['artifact'], p['locator']['value'])
    for r in [r for r in audit() if r['disposition'] == 'APPLY_PROVENANCE'][::25]:
        aid = r['source']['artifact']
        path = L.ROOT + 'sources/' + pls[aid]
        if os.path.exists(path):
            assert hashlib.sha256(open(path, 'rb').read()).hexdigest() == arts[aid]['sha256'], aid


@check
def open_decisions_stay_open():
    assert not L.read_table('identity/transitions.jsonl'), 'D2: a transition was written'
    f = L.read_table('cross/findings.jsonl')
    assert sum(1 for x in f if x['kind'] == 'AMBIGUOUS_SEMANTICS' and x['status'] == 'OPEN') == 179, 'D1'
    assert sum(1 for x in f if x['kind'] == 'CONFLICT' and x['status'] == 'OPEN') == 7, 'D5'
    rules = {r['rule'] for r in L.read_table('reconciliation/reconciliations.jsonl')}
    assert rules == {'LEGACY_NEVER_OVERWRITE'}, rules                 # no new winner rule
    idm = [r for r in L.read_table('identity/identity-map.jsonl') if r['legacy_key'] == 'haut-bailly|La Parde de Haut-Bailly']
    assert idm and all(r['status'] == 'AMBIGUOUS' for r in idm)


@check
def gap_ids_are_stable_and_the_register_keeps_its_history():
    reg = {r['gap_id']: r for r in L.jsonl_lines(L.ROOT + 'data/audit/data-gap-register.jsonl')}
    for r in audit():
        assert r['gap_id'] in reg, r['key']
        assert reg[r['gap_id']]['gap_key'].startswith('FIG_UNSOURCED|'), r['key']
    old = {json.loads(l)['gap_id'] for l in git('show', '6880c16:data/audit/data-gap-register.jsonl').splitlines()}
    assert old <= set(reg), 'a gap was dropped from the register'


@check
def figure_sources_change_is_exactly_the_recovered_figures():
    assert H.figure_sources_change_is_m32_only()


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
