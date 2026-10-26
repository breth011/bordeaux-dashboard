"""Historical model M2: document dates, only where the document dates itself.

    python tools/test-historical-m2.py

Read-only. M2 decides each held document's own date (tools/document_dates.py,
run by tools/extract-document-dates.py into the audit
data/history/document-dates.jsonl) and writes only the accepted ones into the
model, as ArtifactDate STATED_IN_TEXT rows (tools/mig_m6_provenance.py). The
first checks exercise the rules on text built here; the rest hold the model
to them: every date stated in the document's own words, calendar axis, a
DOCUMENT provenance quoting those words, and nothing else historical written.
"""
import collections
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import document_dates as D  # noqa: E402
import historical_m2_scope as H  # noqa: E402
import migration_lib as L  # noqa: E402
import model_schema as S  # noqa: E402

BEFORE = '3b1d543'               # M1: the model before M2
AUDIT = L.ROOT + 'data/history/document-dates.jsonl'
CHECKS = []


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode()


def decide(*texts, clues=None, anchored=None, latest='2026-12-31'):
    """decide() over segments b:0, b:1, ... (all anchored unless told otherwise)."""
    seg = [('b:%d' % i, t) for i, t in enumerate(texts)]
    return D.decide(seg, clues or {}, latest=latest,
                    anchored=anchored if anchored is not None else {l for l, _ in seg})


def audit():
    return [json.loads(l) for l in open(AUDIT, encoding='utf-8')]


def model_dates():
    return L.read_table('document/artifact-dates.jsonl')


# -- the rules, on text built here ---------------------------------------------------------------

@check
def c01_explicit_date_accepted():
    d = decide('Publié le 04/10/2012 à 06h00 Par Julien Lestage')
    assert d['category'] == D.ACCEPTED and d['value'] == '2012-10-04' and d['label'] == 'PUBLISHED', d
    d = decide('Posted on 3 June 2019')
    assert d['category'] == D.ACCEPTED and d['value'] == '2019-06-03', d


@check
def c02_year_precision():
    d = decide('Mise à jour : 2019')
    assert (d['category'], d['value'], d['precision']) == (D.ACCEPTED, '2019', 'YEAR'), d


@check
def c03_month_and_day_precision():
    d = decide('Dernière mise à jour : juin 2026')
    assert (d['value'], d['precision']) == ('2026-06', 'MONTH'), d
    d = decide('Issue Date 20th May 2021')
    assert (d['value'], d['precision']) == ('2021-05-20', 'DAY'), d
    d = decide('Dernière mise à jour : 14 oct. 2023')
    assert (d['value'], d['precision']) == ('2023-10-14', 'DAY'), d


@check
def c04_several_dates_stay_unresolved():
    d = decide('Publié le 02/01/2023', 'Mis à jour le 05/03/2024')
    assert d['category'] == 'AMBIGUOUS' and 'value' not in d and len(d['candidates']) == 2, d
    # an English label does not fix day and month order
    d = decide('Published 03/04/2020')
    assert d['category'] == 'AMBIGUOUS' and 'value' not in d, d
    # a first date and a labelled update: the revision is not taken for the document's date
    d = decide('Apr 13, 2021', '1 min read', 'Updated: Oct 14, 2023')
    assert d['category'] == 'AMBIGUOUS' and 'value' not in d, d


@check
def c05_filename_only_rejected():
    d = decide('Château Exemple, fiche technique', clues={'filename_year': True})
    assert d['category'] == 'REJECTED_FILENAME_ONLY' and 'value' not in d, d


@check
def c06_url_only_rejected():
    d = decide('Château Exemple', clues={'url_year': True, 'retrieved': True})
    assert d['category'] == 'REJECTED_URL_ONLY' and 'value' not in d, d


@check
def c07_retrieval_and_metadata_rejected():
    d = decide('Château Exemple', clues={'retrieved': True, 'http_last_modified': True})
    assert d['category'] == 'REJECTED_RETRIEVAL_DATE' and 'value' not in d, d
    d = decide('Château Exemple', clues={'metadata_date': True, 'retrieved': True})
    assert d['category'] == 'REJECTED_METADATA_ONLY' and 'value' not in d, d
    # a stated date after the document was first retrieved cannot be its own
    d = decide('Publié le 12/06/2026', latest='2026-05-01')
    assert d['category'] == 'REJECTED_IMPLAUSIBLE' and 'value' not in d, d


@check
def c08_vintage_rejected():
    for t in ('Millésime 2015 - Pessac-Léognan', '2018 vintage technical sheet', 'Published 2015 vintage notes'):
        d = decide(t)
        assert d['category'] == 'REJECTED_VINTAGE_ONLY' and 'value' not in d, (t, d)


@check
def c09_referenced_dates_not_promoted():
    cases = [
        # a date of something the text names, not of the text
        ['Le classement des crus bourgeois est publié le 20/02/2020 et laisse apparaître 179 crus'],
        ['Le Château en majesté, par Isabelle Spaak, publié le 22/10/2021'],
        ['Top 100 Wine Spectator publié le 22/11/2022 - 95'],
        ['Cette politique de confidentialité a été mise à jour le 12/03/2024'],
        ['This Cookie Policy was last updated on March 4, 2024'],
        # dates of events: planted, founded, classified
        ['Le vignoble fut planté en 1950 et le château fondé en 1850, classé en 1855'],
    ]
    for texts in cases:
        d = decide(*texts)
        assert d['category'] != D.ACCEPTED and 'value' not in d, (texts, d)
    # a labelled date away from the page's own heading belongs to the page furniture
    d = decide('Château Exemple', 'Accueil', 'Dernière mise à jour : 5 octobre 2026', anchored={'b:0'})
    assert d['category'] == 'REJECTED_ELSEWHERE_ON_PAGE' and 'value' not in d, d


@check
def c10_calendar_axis():
    rows = model_dates()
    assert rows
    for r in rows:
        v = r['value']
        assert v['axis'] == 'CALENDAR' and v['kind'] == 'EXACT' and v['precision'] in ('DAY', 'MONTH', 'YEAR'), r
        assert not S.check_row('ArtifactDate', r), (r['id'], S.check_row('ArtifactDate', r))


@check
def c11_provenance_present():
    prov = {p['id']: p for p in L.read_table('cross/provenance.jsonl')}
    arts = {a['id'] for a in L.read_table('identity/artifacts.jsonl')}
    for r in model_dates():
        p = prov.get(r['provenance'])
        assert p and r['value']['basis'] == r['provenance'], r
        assert p['kind'] == 'DOCUMENT' and p['actor'] == H.M2_ACTOR and p['artifact'] == r['artifact'], p
        assert p['quote'] and p['code_state']['locus'] and p['code_state']['label'] in ('PUBLISHED', 'UPDATED'), p
        assert p['code_state']['extractor'] == D.VERSION, p
        assert r['artifact'] in arts, r
        assert not S.check_row('ArtifactDate', r, provenance=prov), r['id']


@check
def c12_two_versions_keep_their_own_dates():
    a = decide('Dernière mise à jour : 18/04/2025')
    b = decide('Dernière mise à jour : 02/09/2025')
    assert (a['value'], b['value']) == ('2025-04-18', '2025-09-02'), (a, b)
    # in the model: one date per artifact, each its own document's; no date carried across bytes
    per = collections.Counter(r['artifact'] for r in model_dates())
    assert max(per.values()) == 1, per.most_common(1)
    acc = {r['artifact']: r['value'] for r in audit() if r['category'] == D.ACCEPTED}
    assert {r['artifact']: r['value']['value'] for r in model_dates()} == acc


@check
def c13_missing_date_stays_absent():
    d = decide('Château Exemple', 'Grand vin de Bordeaux')
    assert d['category'] == 'NO_DOCUMENT_DATE' and 'value' not in d, d
    assert D.decide(None, {'retrieved': True})['category'] == 'NO_TEXT_HELD'
    dated = {r['artifact'] for r in model_dates()}
    for r in audit():
        assert (r['artifact'] in dated) == (r['category'] == D.ACCEPTED), r['artifact']
        assert r['category'] in D.CATEGORIES, r['category']
        if r['category'] != D.ACCEPTED:
            assert 'value' not in r, r['artifact']


@check
def c14_no_historical_claims():
    fields = {'claimed_validity', 'claimed_window', 'statement_mode'}
    found = [o['id'] for o in L.read_table('observation/observations.jsonl') if fields & set(o)]
    assert not found, found[:3]
    m36d = H.m36d_rows('identity/names.jsonl')         # M3.6D's two name variants: not former, not dated
    assert all(n['kind'] == 'CURRENT' for n in L.read_table('identity/names.jsonl') if n not in m36d)
    assert all(n['kind'] in ('CURRENT', 'SOURCE_RENDERING', 'MARKET_ALIAS')
               and n['validity'] == {'valid_from': {'kind': 'UNKNOWN'}, 'valid_to': {'kind': 'OPEN'}} for n in m36d)


@check
def c15_no_transitions():
    rows = L.read_table('identity/transitions.jsonl')
    assert not rows, 'an identity transition was written: %s' % rows[0].get('id')


@check
def c16_no_dispositions():
    found = [r['id'] for r in L.read_table('reconciliation/reconciliations.jsonl') if 'dispositions' in r]
    assert not found, found[:3]


# -- the audit and the model as a whole ----------------------------------------------------------

@check
def only_words_on_page_one_or_by_the_heading():
    for r in audit():
        if r['category'] == D.ACCEPTED:
            assert r['locus'] == 'p:1' or r['locus'].startswith(('b:', 'l:')), r
            assert r['label'] in ('PUBLISHED', 'UPDATED') and r['quote'], r
    assert {r['kind'] for r in model_dates()} == {'STATED_IN_TEXT'}


@check
def the_audit_is_reproducible():
    # no clock, no network: the same store gives the same file
    out = subprocess.run([sys.executable, L.ROOT + 'tools/extract-document-dates.py', '--check'],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr


@check
def the_model_changed_only_by_m2_additions():
    changed = H.model_changes_are_m2_only(BEFORE)
    # every M2 file changed; M3.2's named provenance-only changes may be there too
    assert set(H.M2_FILES) <= set(changed) <= H.ALLOWED, changed
    old = [l for l in git('show', BEFORE + ':data/model/document/artifact-dates.jsonl').splitlines() if l.strip()]
    assert not old and len(model_dates()) == sum(1 for r in audit() if r['category'] == D.ACCEPTED)


@check
def generated_data_and_protected_groups_unchanged():
    # M3.2: figure-sources.js by exactly the recovered figures
    assert not H.app_files_changed_beyond_m32(git('diff', '--name-only', BEFORE, '--', 'data/app').split()), \
        'generated app data changed'
    b0 = json.load(open(L.MODEL + 'baseline.json', encoding='utf-8'))['groups']
    for g in b0:
        # M3.6B's evidence version 6 named and set aside; v1-v5 and every other group byte for byte
        assert __import__('historical_m2_scope').protected_group(g)['digest'] == b0[g]['digest'], g


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
