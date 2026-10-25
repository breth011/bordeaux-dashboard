"""M3.1: the resolution-first data-gap register.

    python tools/test-data-gap-register.py

Read-only. Rebuilds the register (tools/build-data-gap-register.py, from
tools/data_gap_analysis.py) in memory and holds it to its rules: deterministic and
reproducible, one primary category and state per gap, a bucketed effort with a confidence,
tiers that follow from the fields, R1 free of blockers, R4 needing new data, every UNKNOWN
explained; the 2,149-figure, harvested-observation and OCR analyses reproducible from the store;
the report generated from the rows; and no model, evidence, canonical, provenance or app data
touched.
"""
import collections
import importlib.util
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_gap_analysis as A  # noqa: E402
import migration_lib as L  # noqa: E402

BEFORE = 'f911873'               # M3: the state before M3.1
M31 = '6880c16'                  # the M3.1 commit
REGISTER = L.ROOT + 'data/audit/data-gap-register.jsonl'
CHECKS = []

spec = importlib.util.spec_from_file_location('build_register', L.ROOT + 'tools/build-data-gap-register.py')
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
ROWS = B.build()


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode()


def body(rows):
    return ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n' for r in rows).encode('utf-8')


def fam(r):
    return r['gap_key'].split('|')[0]


@check
def t01_output_is_deterministic():
    assert body(ROWS) == body(B.build()), 'two builds in one process differ'
    assert open(REGISTER, 'rb').read() == body(ROWS), 'the committed register is not a fresh build'
    out = subprocess.run([sys.executable, L.ROOT + 'tools/build-data-gap-register.py', '--check'], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr


@check
def t02_gap_ids_are_stable():
    for r in ROWS:
        assert r['gap_id'] == 'gap_' + L.stable_hash('DataGap', r['gap_key']), r['gap_key']
        assert re.match(r'^gap_[0-9a-f]{12}$', r['gap_id']), r['gap_id']


@check
def t03_no_duplicate_gap_ids():
    c = collections.Counter(r['gap_id'] for r in ROWS)
    assert max(c.values()) == 1 and len(c) == len(ROWS) == 580, (len(ROWS), c.most_common(1))


@check
def t04_exactly_one_primary_category_and_one_state():
    for r in ROWS:
        assert isinstance(r['category'], str) and r['category'] in B.CATEGORIES, r['gap_key']
        assert r['category'] not in r['secondary_categories'], r['gap_key']
        assert all(s in B.CATEGORIES for s in r['secondary_categories']), r['gap_key']
        assert r['state'] in B.STATES, r['gap_key']
        assert (r['state'] == 'NONE') == (r['category'] == 'NOT_A_GAP'), r['gap_key']
    assert 'OTHER' not in {r['category'] for r in ROWS}
    # the four states the brief requires all occur, and are told apart
    assert {r['state'] for r in ROWS} >= {'MISSING', 'UNMAPPED', 'CONFLICTING', 'UNRESOLVED'}


@check
def t05_every_gap_has_an_effort_bucket_and_one_method():
    for r in ROWS:
        assert r['effort'] in B.EFFORTS, r['gap_key']
        assert r['proposed_resolution'] in B.METHODS, r['gap_key']
        assert r['effort'] == r.get('effort') and isinstance(r['affected_count'], int) and r['affected_count'] >= 0


@check
def t06_every_estimate_has_a_confidence_and_a_cascade():
    for r in ROWS:
        assert r['effort_confidence'] in ('HIGH', 'MEDIUM', 'LOW'), r['gap_key']
        assert r['cascading_benefit'] in B.LEVELS, r['gap_key']
        assert r['dependencies'] and all(d in B.DEPENDENCIES for d in r['dependencies']), r['gap_key']


@check
def t07_every_r1_gap_has_no_unresolved_blocker():
    r1 = [r for r in ROWS if r['priority'] == 'R1']
    assert r1
    for r in r1:
        assert r['dependencies'] == ['NONE'] and not r['blocking'], r['gap_key']
        assert r['effort'] in ('XS', 'S') and r['effort_confidence'] in ('HIGH', 'MEDIUM'), r['gap_key']
        assert r['evidence_available'] and not r['requires_new_data'], r['gap_key']


@check
def t08_every_r4_gap_requires_new_source_or_research():
    r4 = [r for r in ROWS if r['priority'] == 'R4']
    assert r4
    for r in r4:
        assert r['requires_new_data'] or set(r['dependencies']) & {'SOURCE_DISCOVERY', 'EXTERNAL_SOURCE'}, r['gap_key']
    # and nothing that needs new data is ranked as resolvable from what is held
    for r in ROWS:
        if r['requires_new_data']:
            assert r['priority'] in ('R4', 'R5'), r['gap_key']


@check
def t09_every_r5_unknown_estimate_is_explained():
    for r in ROWS:
        if r['effort'] == 'UNKNOWN':
            assert r['priority'] == 'R5' and r.get('unknown_reason'), r['gap_key']
        if r['priority'] == 'R5':
            assert r['blocking'], r['gap_key']
    blocked = {d for r in ROWS for d in r['dependencies'] if d in B.BLOCKING_DEPS}
    for r in ROWS:
        if set(r['dependencies']) & B.BLOCKING_DEPS:
            assert r['priority'] == 'R5', r['gap_key']
    assert {'D1', 'D2', 'D5', 'LAPARDE_IDENTITY'} <= blocked


@check
def t10_affected_counts_are_reproducible():
    u = A.unsourced_figures()
    assert sum(r['affected_count'] for r in ROWS if fam(r) == 'FIG_UNSOURCED') == len(u) == 2149
    assert sum(r['affected_count'] for r in ROWS if fam(r) == 'FIG_AMBIGUOUS') == len(A.ambiguous_figures()) == 96
    assert sum(r['affected_count'] for r in ROWS if fam(r) == 'FIG_FILE_ONLY') == len(A.file_only_figures()) == 304
    assert sum(r['affected_count'] for r in ROWS if fam(r) == 'CORPUS') == 163582
    vnd = sum(r['affected_count'] for r in ROWS if fam(r) == 'VINTAGE_NO_DOCUMENT')
    assert vnd == A.vintage_document_counts()['none'], vnd
    assert sum(r['affected_count'] for r in ROWS if fam(r) == 'FILLABLE') == len(A.fillable_slots())


@check
def t11_the_2149_analysis_is_reproducible():
    states = collections.Counter(f['state'] for f in A.figures())
    assert dict(states) == {'LINKED': 2142, 'FILE_ONLY': 304, 'AMBIGUOUS': 96, 'NONE': 2149}, states
    g = collections.Counter(r['group'] for r in A.unsourced_figures())
    assert sum(g.values()) == 2149 and g['4_NOT_HELD'] == 36 and not g.get('5_UNAVAILABLE') and not g.get('6_UNKNOWN'), g
    # identifiable means the exact value is printed in the record's own held sheet
    for r in [r for r in A.unsourced_figures() if r['group'] == '1_LOCAL_IDENTIFIABLE'][::97]:
        assert A.value_printed(r['field'], r['value'], A.document_text(r['document'])), (r['record'], r['field'])
    # a bare number is not enough: an alcohol needs its unit
    assert not A.value_printed('alc', 13, 'vendanges le 13 septembre')
    assert A.value_printed('alc', 13.5, 'alcool : 13,5 % vol')


@check
def t12_the_harvested_observation_analysis_is_reproducible():
    om = A.observation_mapping()
    n = sum(1 for p in sorted(os.listdir(L.ROOT + 'data/discovery/observations'))
            for _ in open(L.ROOT + 'data/discovery/observations/' + p, encoding='utf-8'))
    assert om['total'] == n == 163582 == sum(om['buckets'].values()), (om['total'], n)
    assert om['exact']['estate_wine_vintage'] == om['buckets']['ESTATE_WINE_VINTAGE']
    assert om['exact']['estate'] >= om['exact']['estate_wine_vintage']
    # a shared sheet is not a conflict
    assert om['buckets']['AMBIGUOUS_SHARED_DOCUMENT'] > om['buckets']['CONFLICTING']
    # a crawl attribution is never promoted to an exact estate
    assert A.artifact_mapping('0' * 64)['estate'] == 'UNMAPPABLE'


@check
def t13_the_ocr_backlog_is_reproducible():
    ocr = A.ocr_backlog()
    assert len(ocr) == sum(1 for a in A.table('identity/artifacts.jsonl') if a.get('extraction_status') == 'NEEDS_OCR') == 374
    useful = [o for o in ocr if o['benefit'] != 'NONE']
    rows = [r for r in ROWS if fam(r) == 'OCR' and r['category'] != 'NOT_A_GAP']
    assert len(rows) == len(useful), (len(rows), len(useful))
    for o in useful:
        assert o['gaps']['record_sheet_of'] or o['gaps']['only_document_of_vintages'], o['artifact']
    deferred = [r for r in ROWS if r['gap_key'] == 'OCR|NO_IDENTIFIED_GAP'][0]
    assert deferred['affected_count'] == len(ocr) - len(useful) and deferred['priority'] == 'DEFERRED'


@check
def t14_scraping_candidates_trace_to_actual_gaps():
    scrape = [r for r in ROWS if r['proposed_resolution'] == 'TARGETED_FIRST_PARTY_SCRAPE']
    assert scrape
    allowed = {'VINTAGE_NO_DOCUMENT', 'FIG_UNSOURCED', 'FIG_FILE_ONLY', 'HIST'}
    for r in scrape:
        # MISSING (no document held) or UNRESOLVED (held evidence that only a first-party source can settle)
        assert fam(r) in allowed and r['affected_count'] >= 1 and r['state'] in ('MISSING', 'UNRESOLVED'), r['gap_key']
        assert r['state'] == 'MISSING' or not r['evidence_available'], r['gap_key']
        assert r['priority'] == 'R4', r['gap_key']
    for r in ROWS:
        if fam(r) == 'SITE':
            assert r['priority'] == 'DEFERRED', r['gap_key']     # a site with no dependent gap is not a target
    # a blocked site is never a scrape target (robots.txt is respected)
    blocked = {c.get('model_estate') for c in A.discovery_coverage()['coverage'] if c['status'] == 'BLOCKED_BY_POLICY'}
    assert not [r for r in scrape if r['entity_id'] in blocked]


@check
def t15_report_totals_match_the_register():
    out = subprocess.run([sys.executable, L.ROOT + 'tools/build-data-gap-register.py', '--report', '--check'],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
    text = open(L.ROOT + 'docs/DATA-GAP-REGISTER.md', encoding='utf-8').read()
    t = collections.Counter(r['priority'] for r in ROWS)
    for tier in ('R1', 'R2', 'R3', 'R4', 'R5', 'DEFERRED'):
        m = re.search(r'^\| %s \| (\d+) \|' % tier, text, re.M)
        assert m and int(m.group(1)) == t[tier], (tier, m and m.group(1), t[tier])
    assert '**%d gaps**' % len(ROWS) in text
    live = [r for r in ROWS if r['priority'] != 'DEFERRED']
    no_new = sum(1 for r in live if not r['requires_new_data'])
    assert '**%s live gaps' % '{:,}'.format(no_new) in text
    for heading in ('Resolution-first dashboard', 'Top 25 fastest resolvable gaps', 'Top 10 cascading opportunities',
                    'Targeted scraping backlog', 'OCR backlog', 'Blocked decisions', 'Deliberately deferred',
                    'Which gaps can be resolved without acquiring any new data?', 'Which gaps genuinely require new data?',
                    'Mapping before scraping'):
        assert '## ' + heading in text, heading


@check
def t16_no_model_evidence_canonical_or_app_mutation():
    assert not git('diff', '--stat', BEFORE, '--', 'data/evidence', 'data/history',
                   'data/discovery', 'data/review', 'data/scope', ':(glob)data/*.js', 'data/sources.json',
                   'data/audit/historical-m3-candidates.jsonl', 'assets', 'index.html').strip()
    # after M3.1: M3.2 changes the model and figure-sources.js in named ways only
    import historical_m2_scope
    historical_m2_scope.model_changes_are_m2_only(BEFORE)
    assert not historical_m2_scope.app_files_changed_beyond_m32(git('diff', '--name-only', BEFORE, '--', 'data/app').split())
    b0 = json.load(open(L.MODEL + 'baseline.json', encoding='utf-8'))['groups']
    for g in b0:
        assert L.group_hashes(g)['digest'] == b0[g]['digest'], g
    # the M3.1 commit itself touched only M3.1's files (later commits are their own phases)
    changed = set(git('show', '--name-only', '--format=', M31).split())
    allowed = {'data/audit/data-gap-register.jsonl', 'docs/DATA-GAP-REGISTER.md', 'tools/build-data-gap-register.py',
               'tools/data_gap_analysis.py', 'tools/test-data-gap-register.py', '.gitattributes'}
    assert changed == allowed, sorted(changed ^ allowed)


# -- found in the audit ----------------------------------------------------------------------------

@check
def deferred_only_for_what_is_not_a_gap_or_needs_no_action():
    for r in ROWS:
        if r['priority'] == 'DEFERRED':
            assert r['category'] == 'NOT_A_GAP' or r['proposed_resolution'] == 'NO_ACTION', r['gap_key']


@check
def ranks_follow_the_resolution_first_order():
    assert [r['rank'] for r in ROWS] == list(range(1, len(ROWS) + 1))
    assert [B.TIERS.index(r['priority']) for r in ROWS] == sorted(B.TIERS.index(r['priority']) for r in ROWS)
    assert ROWS == sorted(ROWS, key=B.rank_key)


@check
def decisions_stay_decisions():
    by = {r['gap_key']: r for r in ROWS}
    assert by['HIST|ECHO_D2']['dependencies'] == ['D2'] and by['HIST|ECHO_D2']['priority'] == 'R5'
    assert by['HIST|LAPARDE']['dependencies'] == ['LAPARDE_IDENTITY'] and by['HIST|LAPARDE']['priority'] == 'R5'
    assert by['IDENTITY_NOT_CONTENT']['state'] == 'UNRESOLVED'       # document identity is not content approval
    for r in ROWS:
        if r['gap_key'].startswith('FINDING|CONFLICT|') and 'second wine' in r['description']:
            assert r['dependencies'] == ['D5'] and r['priority'] == 'R5', r['gap_key']


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
