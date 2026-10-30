"""The recording policy (tools/recording_policy.py) and the R4 listing review (tools/r4-listing-review.py).

    python tools/test-recording-policy.py

Read-only. The adversarial cases of the policy decision (docs/DECISION-RECORDING-POLICY.md): six for an R4 identity,
on synthetic listings and on the real reviewed one, and eight for a C6 yield, on real and built Grand Mayne pages.
Nothing in production imports either module, and the committed review is reproduced.
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import warnings

warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import identity_rules_candidate as I  # noqa: E402
import migration_lib as L  # noqa: E402
import recording_policy as P  # noqa: E402
import yield_layout as Y  # noqa: E402


def _load(name, rel):
    s = importlib.util.spec_from_file_location(name, L.ROOT + rel)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


BEFORE = '5589f7c'               # the identity-rule decision: the state this phase starts from
RV = _load('r4_review_t', 'tools/r4-listing-review.py')
YT = _load('yield_layout_t', 'tools/test-yield-layout.py')       # its held bytes and built pages, nothing else
CHECKS = []
FINGERPRINTED = ('tools/m34a-mapping-audit.py', 'tools/sheetreader.py', 'tools/web_evidence.py', 'tools/m35_rubric.py',
                 'tools/read-fiches.py', 'tools/model_schema.py')
H = 'estate.example'
SYN = {(H, '/wines/grand/'): {'entry': H + '/wines/grand/', 'host': H, 'path_prefix': '/wines/grand/', 'wine': 'wn_g',
                              'estate': 'es_x', 'disposition': 'APPROVED_R4', 'version': 't'},
       (H, '/wines/second/'): {'entry': H + '/wines/second/', 'host': H, 'path_prefix': '/wines/second/', 'wine': 'wn_s',
                               'estate': 'es_x', 'disposition': 'APPROVED_R4', 'version': 't'},
       (H, '/wines/unsure/'): {'entry': H + '/wines/unsure/', 'host': H, 'path_prefix': '/wines/unsure/', 'wine': 'wn_g',
                               'estate': 'es_x', 'disposition': 'REQUIRES_REVIEW', 'version': 't'}}
G, SEC, UNS = 'https://%s/wines/grand/' % H, 'https://%s/wines/second/' % H, 'https://%s/wines/unsure/' % H
_REAL = {}


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode('utf-8')


def doc(name):
    return ['https://%s/files/%s' % (H, name)]


def real():
    if not _REAL:
        _REAL['entries'] = P.reviewed_entries()
        _REAL['series'] = I.series()
    return _REAL['entries'], _REAL['series']


def held_urls(fragment):
    s = real()[1]
    return sorted(u for us in s.urls_of_sha.values() for u in us if fragment in u)


# ---- R4 ---------------------------------------------------------------------------------------------------

@check
def r1_one_wine_page_lists_the_document():
    r = P.listing_identity('wn_g', doc('SHEET-2010.pdf'), {(H, 'sheet-2010.pdf'): {'wn_g': {G}}}, SYN)
    assert r['status'] == P.LISTING_IDENTITY and r['wine'] == 'wn_g' and r['attribution_method'] == 'REVIEWED_LISTING', r
    pv = r['provenance']
    assert pv['rule'] == 'R4' and pv['identity_basis'] == 'LISTING_IDENTITY' and not pv['filename_used_as_identity_evidence']
    assert pv['listing'][0]['review']['disposition'] == 'APPROVED_R4' and pv['listing'][0]['pages'] == [G]
    entries, s = real()                         # Desmirail 2005 FT-DM: the estate's Chateau Desmirail pages - real
    urls = held_urls('FT-DM-2005-FR.pdf')
    r = P.listing_identity('wn_00254', urls, s.linked, entries)
    assert urls and r['status'] == P.LISTING_IDENTITY and {l['review']['disposition'] for l in r['provenance']['listing']} == {'APPROVED_R4'}, r


@check
def r2_two_wine_pages_list_the_same_document():
    r = P.listing_identity('wn_g', doc('a.pdf'), {(H, 'a.pdf'): {'wn_g': {G}, 'wn_s': {SEC}}}, SYN)
    assert r['status'] == 'REFUSED' and r['code'] == 'SHARED_LISTING', r
    entries, s = real()                         # Issan 2016: the Chateau and the Blason pages both link it - real
    r = P.listing_identity('wn_00283', held_urls('CHATEAU_ISSAN_2016.pdf'), s.linked, entries)
    assert r['status'] == 'REFUSED' and r['code'] == 'SHARED_LISTING', r


@check
def r3_target_named_by_the_filename_but_listed_under_a_sibling():
    r = P.listing_identity('wn_g', doc('GRAND-VIN-2010.pdf'), {(H, 'grand-vin-2010.pdf'): {'wn_s': {SEC}}}, SYN)
    assert r['status'] == 'REFUSED' and r['code'] == 'LISTED_UNDER_OTHER_WINE' and r['listed_wine'] == 'wn_s', r
    entries, s = real()                         # a Rose de Desmirail sheet claimed for the grand vin - real
    r = P.listing_identity('wn_00254', held_urls('FT-ROSE-2021'), s.linked, entries)
    assert r['status'] == 'REFUSED' and r['code'] == 'LISTED_UNDER_OTHER_WINE', r


@check
def r4_a_wine_prefix_in_the_filename_and_no_reviewed_listing():
    r = P.listing_identity('wn_g', doc('FT-GRAND-2099.pdf'), {}, SYN)
    assert r['status'] == 'REFUSED' and r['code'] == 'NO_REVIEWED_LISTING', r
    entries, s = real()
    r = P.listing_identity('wn_00254', ['https://www.desmirail.com/wp-content/uploads/FT-DM-2099-FR.pdf'], s.linked, entries)
    assert r['status'] == 'REFUSED' and r['code'] == 'NO_REVIEWED_LISTING', r


@check
def r5_the_listing_names_the_wine_the_text_does_not():
    # listing_identity reads no text at all: the listing's relationship is the evidence, recorded as LISTING_IDENTITY
    r = P.listing_identity('wn_g', doc('untitled.pdf'), {(H, 'untitled.pdf'): {'wn_g': {G}}}, SYN)
    assert r['status'] == P.LISTING_IDENTITY and r['provenance']['identity_basis'] != P.TEXT_IDENTITY
    assert 'text' not in P.listing_identity.__code__.co_varnames


@check
def r6_an_ambiguous_listing():
    r = P.listing_identity('wn_g', doc('b.pdf'), {(H, 'b.pdf'): {'wn_g': {UNS}}}, SYN)
    assert r['status'] == 'REFUSED' and r['code'] == 'LISTING_ENTRY_NOT_APPROVED', r
    r = P.listing_identity('wn_g', doc('c.pdf'), {(H, 'c.pdf'): {'wn_g': {G, 'https://%s/news/' % H}}}, SYN)
    assert r['status'] == 'REFUSED' and r['code'] == 'LISTING_ENTRY_NOT_APPROVED', r      # a page outside every entry
    entries, s = real()                         # Issan 2004: only the Chateau pages, whose entry requires review - real
    r = P.listing_identity('wn_00283', held_urls('CHATEAU_ISSAN_2004.pdf'), s.linked, entries)
    assert r['status'] == 'REFUSED' and r['code'] == 'LISTING_ENTRY_NOT_APPROVED', r


@check
def r7_the_review_itself():
    rows, eff = RV.build()
    committed = L.jsonl_lines(RV.OUT)
    assert json.loads(RV.body(rows, eff).decode('utf-8').splitlines()[0]) == committed[0]
    assert RV.body(rows, eff) == open(RV.OUT, 'rb').read()
    assert len(rows) == 31 and [(r['host'], r['path_prefix'], r['wine']) for r in rows] == list(I.FILE_SERIES_PAGES)
    by = {r['disposition'] for r in rows}
    assert by <= set(RV.DISPOSITIONS)
    for r in rows:
        if r['disposition'] == 'APPROVED_R4':
            c = r['checklist']
            assert c['estate_controlled'] and c['page_names_the_wine'] and c['estate_covered'] and not c['shared_documents']
    assert all(r['effect'] == 'VETO_ONLY' for r in rows if r['wine'].startswith('UNLISTED:') and r['disposition'] == 'APPROVED_R4')


# ---- C6 ---------------------------------------------------------------------------------------------------

def c6(b, vintage=2010, reader=None):
    return Y.read_yield(b, 'SAFE_TO_MAP', reader, vintage, YT.WINE, YT.OTHERS)


@check
def c1_aligned_hl_and_ha_derive_hl_per_ha():
    sha, want = YT.GRAND_MAYNE[2004]
    r = P.c6_observation(c6(YT.held(sha), 2004), 'IDENTITY_SETTLED', None, 'vt:wn_00402:2004', 'ar_test')
    o, pv = r['observation'], r['provenance']
    assert r['status'] == 'RECORDABLE' and o['value'] == want and o['unit'] == 'hl/ha', r
    assert o['raw_value'] == ['38hl', '38ha'] and o['confidence'] == 'UNIT_FROM_LAYOUT', o
    assert pv['code_state']['unit_derived'] and not pv['code_state']['source_prints_hl_per_ha']
    assert pv['code_state']['unit_basis'].startswith('LAYOUT_DERIVED') and pv['code_state']['c6'] == Y.VERSION
    assert pv['code_state']['french_line']['text'] == '38hl' and pv['code_state']['english_line']['text'] == '38ha'
    assert 'hl/ha' not in pv['quote'] and r['canonical']['derivation'] == 'UNIT_FROM_LAYOUT'
    assert 'harvest' not in json.dumps(r).lower()


@check
def c2_to_c5_the_layout_does_not_hold():
    for name, rows in (('37hl + 38ha', YT.variant(cell=[('37hl', 9), ('38ha', 7)])),
                       ('37hl only', YT.variant(cell=[('37hl', 9)])),
                       ('37ha only', YT.variant(cell=[('37ha', 7)])),
                       ('a competing yield row', YT.variant(extra_rows=[('MAXIMUM', 'MAXIMUM YIELD', [('55 hl/ha', 9)])]))):
        res = c6(YT.built(rows))
        r = P.c6_observation(res, 'IDENTITY_SETTLED', None, 'vt:wn_t:2010', 'ar_t')
        assert res['status'] == 'REFUSED' and r['status'] == 'REFUSED' and r['code'] == 'C6_NOT_READ', (name, res, r)


@check
def c6_identity_unsettled_records_nothing():
    res = c6(YT.built(YT.variant()))
    assert res['status'] == 'READ'
    for st in ('IDENTITY_REFUSED', 'IDENTITY_CONFLICTED', 'IDENTITY_REVIEW_REQUIRED'):
        r = P.c6_observation(res, st, None, 'vt:wn_t:2010', 'ar_t')
        assert r['status'] == 'REFUSED' and r['code'] == 'IDENTITY_NOT_SETTLED', r


@check
def c7_the_reader_found_a_yield():
    res = c6(YT.built(YT.variant()), reader=37.0)
    assert res['status'] == 'NOT_RUN' and res['failed_guard'] == 2
    r = P.c6_observation(res, 'IDENTITY_SETTLED', 37.0, 'vt:wn_t:2010', 'ar_t')
    assert r['status'] == 'REFUSED' and r['code'] == 'READER_PATH' and P.value_path(37.0, res) == 'READER'


@check
def c8_a_source_that_prints_hl_per_ha_is_the_reader_path():
    res = c6(YT.built(YT.variant(cell=[('37 hl/ha', 9)])))
    assert res['status'] == 'REFUSED'                           # never C6's: not its layout
    assert P.value_path(37.0, res) == 'READER' and P.value_path(None, res) is None
    res = c6(YT.built(YT.variant()))
    assert P.value_path(None, res) == 'C6_LAYOUT'


@check
def z1_nothing_in_production_changes():
    assert not git('diff', '--name-only', BEFORE, '--', *FINGERPRINTED)
    assert not git('status', '--porcelain', '--', 'data', 'sources', ':!data/audit/r4-listing-review.jsonl')
    own = ('recording_policy.py', 'test-recording-policy.py', 'r4-listing-review.py')
    users = [p for p in sorted(os.listdir(L.ROOT + 'tools')) if p.endswith('.py') and p not in own
             and re.search(r'(?m)^\s*(?:import|from)\s+recording_policy\b|'
                           r'spec_from_file_location\([^)]*r4-listing-review\.py', open(L.ROOT + 'tools/' + p, encoding='utf-8').read())]
    assert not users, users


def main():
    fails = 0
    for f in CHECKS:
        try:
            f()
            print('ok   %s' % f.__name__)
        except Exception as e:
            fails += 1
            print('FAIL %s: %r' % (f.__name__, e))
    print('%d check(s), %s' % (len(CHECKS), 'all pass' if not fails else '%d FAIL' % fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
