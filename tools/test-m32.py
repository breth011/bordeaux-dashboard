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
    added = {(r['target']['subject'], r['target']['field']): r for r in a if r['disposition'] == 'APPLY_VALUE'}
    for c in L.read_table('canonical/values.jsonl'):
        if (c['subject'], c['field']) in added:
            # M3.2D: the value as the sheet states it, in the model's own unit; the raw text kept
            r = added[(c['subject'], c['field'])]
            assert c['value'] == r['proposed']['value'] and (c['subject'], c['field']) not in old
            continue
        o = old[(c['subject'], c['field'])]
        assert c['value'] == o['value'], (c['subject'], c['field'])
    for o in L.read_table('observation/observations.jsonl'):
        if H.is_m32d_observation(o):
            assert o.get('raw_value') and o.get('unit') == {'alc': '%', 'ph': None, 'yld': 'hl/ha', 'blend': '%'}[o['field']]
    obs_old = {json.loads(l)['id']: json.loads(l) for l in git('show', BEFORE + ':data/model/observation/observations.jsonl').splitlines()}
    for o in L.read_table('observation/observations.jsonl'):
        if H.is_m32d_observation(o):
            continue                                  # checked above: added, not changed
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
    assert seen == len(applied) and seen > 0, (seen, len(applied))


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
    eligible = {'A': 'MODEL_MATCHES', 'B': 'EXACT_FIRST_PARTY', 'C': 'MODEL_MATCHES', 'D': 'MODEL_MISSING',
                'E': None}                                     # E: OCR text is never applied
    for r in audit():
        if r['classification'] != eligible[r['stream']]:
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
    recs = L.read_table('reconciliation/reconciliations.jsonl')
    assert {r['rule'] for r in recs if not H.is_m32d_reconciliation(r)} == {'LEGACY_NEVER_OVERWRITE'}
    # M3.2D chose no winner: one sheet, or several that agree; never newest-wins or source priority (D5)
    assert {r['rule'] for r in recs if H.is_m32d_reconciliation(r)} <= {'ONLY_CANDIDATE', 'UNANIMOUS'}
    assert not [r for r in recs if 'dispositions' in r]
    idm = [r for r in L.read_table('identity/identity-map.jsonl') if r['legacy_key'] == 'haut-bailly|La Parde de Haut-Bailly']
    assert idm and all(r['status'] == 'AMBIGUOUS' for r in idm)


@check
def gap_ids_are_stable_and_the_register_keeps_its_history():
    reg = {r['gap_id']: r for r in L.jsonl_lines(L.ROOT + 'data/audit/data-gap-register.jsonl')}
    family = {'A': 'FIG_UNSOURCED|', 'B': 'FIG_FILE_ONLY|URL_IN_DISCOVERY', 'C': 'FIG_UNSOURCED|3b_TEXT_NOT_STORED|',
              'D': 'FILLABLE|', 'E': 'OCR|'}
    for r in audit():
        assert r['gap_id'] in reg, r['key']
        assert reg[r['gap_id']]['gap_key'].startswith(family[r['stream']]), r['key']
    m31 = {json.loads(l)['gap_id']: json.loads(l) for l in git('show', '6880c16:data/audit/data-gap-register.jsonl').splitlines()}
    assert set(m31) <= set(reg), 'a gap was dropped from the register'
    # a resolved gap keeps its id, tier and original count, and names what resolved it
    commits = json.load(open(L.ROOT + 'data/audit/m32-resolutions.json', encoding='utf-8'))
    recovered = 0
    for gid, r in reg.items():
        if 'resolution' not in r:
            continue
        o = m31[gid]
        assert (r['priority'], r['affected_count'], r['gap_key']) == (o['priority'], o['affected_count'], o['gap_key']), gid
        res = r['resolution']
        assert res['affected_before'] == r['affected_count'] and res['affected_after'] == r['affected_count'] - res['recovered']
        assert res['status'] == ('RESOLVED' if res['affected_after'] == 0 else 'PARTIALLY_RESOLVED')
        for b in res['by']:
            assert b['commit'] == commits[b['phase']]['commit'], gid
        recovered += res['recovered']
    # the register counts the streams whose applying commit is recorded
    assert recovered == sum(1 for r in audit() if r['disposition'].startswith('APPLY')
                            and 'M3.2' + r['stream'] in commits), recovered


@check
def figure_sources_change_is_exactly_the_recovered_figures():
    assert H.figure_sources_change_is_m32_only()


# -- M3.2C: held sheets without stored text --------------------------------------------------------

@check
def m32c_reads_the_held_pdf_and_keeps_only_the_passage():
    c = [r for r in audit() if r['stream'] == 'C']
    assert len(c) == 411, len(c)
    classes = {r['evidence']['document_class'] for r in c}
    assert classes <= {'TEXT_EXTRACTABLE', 'LAYOUT_EXTRACTABLE', 'IMAGE_ONLY', 'CORRUPT_OR_UNREADABLE',
                       'IRRELEVANT_AFTER_REVIEW'}, classes
    for r in c:
        if r['disposition'] == 'APPLY_PROVENANCE':
            assert r['evidence']['text'].startswith('pymupdf '), r['key']        # the sheet reader's reading
            assert r['evidence']['locus'] in ('pdf:flat', 'pdf:columns') and len(r['evidence']['quote']) <= 200
            assert r['source']['filename'] and r['source']['filename'].lower().endswith('.pdf'), r['key']
        if r['evidence']['document_class'] == 'IMAGE_ONLY':
            assert r['disposition'] == 'OCR_CANDIDATE', r['key']                  # never guessed, never skipped
    # a compilation of vintages is refused for a blend, whichever section matches
    import m32_recovery as RR
    compilation = 'Assemblage 2013 : 80% Merlot, 15% Cabernet Franc, 5% Petit Verdot. Assemblage 2014 : 82% Merlot, 12% Cabernet Franc, 6% Petit Verdot'
    assert RR.classify('blend', {'ME': 80, 'CF': 15, 'PV': 5}, [('p:1', compilation)])['classification'] == 'DUPLICATE_VALUE'
    # a share is read with its own grape, never both neighbours
    assert RR._read_run(': cabernet sauvignon 49% merlot 38% cabernet franc 7% petit verdot 6%') == {'CS': 49, 'ME': 38, 'CF': 7, 'PV': 6}
    assert RR._read_run(': 98% merlot et 2% cabernet franc') == {'ME': 98, 'CF': 2}


# -- M3.2D: harvested observations ----------------------------------------------------------------

def recovery_tool():
    import importlib.util
    spec = importlib.util.spec_from_file_location('m32tool', L.ROOT + 'tools/m32-recovery.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@check
def m32d_adds_only_clear_values_with_their_units_and_meaning():
    M = recovery_tool()
    # units: kept, never converted; a yield must be per hectare
    assert M.parse_value('alc', '13,5 % vol.') == (13.5, '%')
    assert M.parse_value('yld', '35 hl/ha') == (35, 'hl/ha')
    assert M.parse_value('yld', 'Rendement 38.5 hl')[0] is None              # UNIT_UNCERTAIN
    assert M.parse_value('blend', 'Merlot 77% / Cabernet Sauvignon 23%') == ({'CS': 23, 'ME': 77}, '%')
    assert M.parse_value('blend', 'Merlot 70%')[0] is None                    # not a whole blend
    # approximate, potential, provisional figures are not exact ones
    assert M.approximate('alc', 13.5, 'Degré : Environ 13,5 ° Production')
    assert M.approximate('alc', 14.5, 'Degré approximatif : 14.5°')
    assert not M.approximate('alc', 13.5, 'TAUX ALCOOL : 13.5 % VOL')
    # a blend must agree with the wine's colour; an unknown colour admits none
    assert not M.colour_ok('blend', {'ME': 77, 'CS': 23}, {'type': 'WHITE_DRY'})[0]
    assert M.colour_ok('blend', {'SE': 100}, {'type': 'WHITE_SWEET'})[0]
    assert not M.colour_ok('blend', {'ME': 100}, {'type': 'UNKNOWN'})[0]
    # the audit: every added value from exactly mapped sheets, all stating it, labelled, agreeing
    for r in audit():
        if r['stream'] != 'D':
            continue
        if r['disposition'] == 'APPLY_VALUE':
            obs = r['source']['observations']
            assert obs and all(o['classification'] == 'MODEL_MATCHES' and o['quote'] for o in obs), r['key']
            assert r['proposed']['rule'] == ('UNANIMOUS' if len(obs) > 1 else 'ONLY_CANDIDATE'), r['key']
        else:
            assert r['proposed'] is None, r['key']
    cls = {r['classification'] for r in audit() if r['stream'] == 'D'}
    assert {'CONFLICT_BETWEEN_SHEETS', 'APPROXIMATE_VALUE', 'FIELD_MAPPING_AMBIGUOUS'} <= cls, cls


@check
def m32d_values_stay_out_of_the_legacy_projection():
    # the app's files reconstruct the legacy ones; a model-only value is not slipped into them
    out = subprocess.run([sys.executable, L.ROOT + 'tools/build-app-data.py', '--check'], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout
    assert not git('diff', '--stat', '75a120d', '--', 'data/app').strip(), 'the app data changed in M3.2D'


# -- M3.2E: OCR ----------------------------------------------------------------------------------

@check
def m32e_ocr_candidates_are_never_silently_skipped():
    import data_gap_analysis as A
    e = [r for r in audit() if r['stream'] == 'E']
    backlog = {o['artifact'] for o in A.ocr_backlog() if o['benefit'] != 'NONE'}
    assert {r['source']['artifact'] for r in e} == backlog and len(e) == 17     # every candidate accounted for
    unsourced = {f['record'] for f in A.unsourced_figures() if not f.get('recovered')}
    for r in e:
        assert r['disposition'] in ('NONE', 'OCR_CANDIDATE', 'OCR_REVIEW'), r['key']   # nothing applied from OCR
        if r['classification'] == 'NO_LONGER_A_GAP':
            assert not set(r['target']['record_sheet_of']) & unsourced, r['key']
        if r['disposition'] == 'OCR_REVIEW':
            ev = r['evidence']
            assert ev['engine'].startswith('rapidocr_onnxruntime') and ev['dpi'] == 200 and ev['text_sha256'], r['key']
            p = L.ROOT + 'sources/discovery/ocr/' + r['source']['sha256'] + '.json'
            if os.path.exists(p):                                                 # held locally, never in git
                d = json.load(open(p, encoding='utf-8'))
                text = '\n'.join(l['text'] for pg in d['pages'] for l in pg)
                assert hashlib.sha256(text.encode('utf-8')).hexdigest() == ev['text_sha256'], r['key']
    assert not git('ls-files', 'sources').strip(), 'OCR text or sources committed'
    # a bound in OCR text is flagged, not read as a figure
    M = recovery_tool()
    assert M.approximate('yld', 32, 'Les rendements, inférieurs à 32 hl/ha')


# -- M3.2B: online addresses -----------------------------------------------------------------------

@check
def m32b_places_only_first_party_addresses_of_exactly_these_bytes():
    import glob
    prov = {p['id']: p for p in L.read_table('cross/provenance.jsonl')}
    arts = {a['id']: a for a in L.read_table('identity/artifacts.jsonl')}
    fetched = {}
    for p in sorted(glob.glob(L.ROOT + 'data/discovery/locations/*.jsonl')):
        for r in L.jsonl_lines(p):
            u = r.get('final_url') or r.get('url')
            if r.get('sha256') and u:
                fetched.setdefault(u, set()).add(r['sha256'])
    rows = {r['id']: r for r in audit() if r['stream'] == 'B'}
    new = [pl for pl in L.read_table('document/placements.jsonl')
           if (prov[pl['provenance']].get('code_state') or {}).get('stream') == 'M3.2B']
    assert len(new) == len({(f['url'], r['source']['artifact']) for r in rows.values()
                            if r['disposition'] == 'APPLY_PLACEMENT' for f in r['source']['fetched']}) == 48
    for pl in new:
        p = prov[pl['provenance']]
        r = rows[p['code_state']['candidate']]
        u = pl['locator']['value']
        assert pl['locator']['kind'] == 'URL' and pl['artifact'] == r['source']['artifact'] == p['artifact']
        assert arts[pl['artifact']]['sha256'] in fetched[u], u                 # identical bytes at that address
        assert u in r['source']['urls_first_party']
        host = u.split('/')[2].lower()
        host = host[4:] if host.startswith('www.') else host
        assert any(host == h or host.endswith('.' + h) for h in r['source']['estate_hosts']), u
        assert pl['observed']['valid_from']['value'] == p['code_state']['fetched_at'][:10]


@check
def m32b_figures_gain_the_address_and_keep_their_file():
    gen = H.unpack_figure_sources(open(L.ROOT + 'data/app/figure-sources.js', encoding='utf-8').read())
    placed = H.m32b_urls()
    for r in audit():
        if r['stream'] == 'B' and r['disposition'] == 'APPLY_PLACEMENT':
            s = gen[r['target']['record']][r['target']['field']]
            assert s['n'] == r['source']['filename'] and s.get('u') in placed, r['key']
        if r['stream'] == 'B':
            assert r['source']['other_versions'] == 0 or r['disposition'] != 'APPLY_PLACEMENT' or \
                r['source']['urls_first_party'], r['key']                          # a version is never attached


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
