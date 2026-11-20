"""Blockers 2-4 of the controlled integration: the REVIEWED_LISTING attribution method, the listing branch of the
acceptance path (apply-vintage-creation-manifest.check_review and its attribution) and the C6 branch of the value
runner (apply-value-manifest.py).

    python tools/test-recording-branches.py

Read-only. The listing branch is exercised on a real Desmirail sheet (ar_010990, Chateau Desmirail 2005) with a
reviewed row built from identity_rules' own listing record, and the C6 branch on a real Grand Mayne sheet's C6 read;
each is then broken one condition at a time. The text branch and the explicit-statement path are compared with the
runners as they were before (65463b7): every M3.9 reviewed row gets the same verdict, and an explicit value row the
same model rows.
"""
import copy
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import warnings

warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import identity_rules as IR  # noqa: E402
import migration_lib as L  # noqa: E402
import model_schema as S  # noqa: E402
import recording_policy as P  # noqa: E402
import yield_layout as Y  # noqa: E402

BEFORE = '65463b7'               # the runners before the branches
FINGERPRINTED = ('tools/m34a-mapping-audit.py', 'tools/sheetreader.py', 'tools/web_evidence.py', 'tools/m35_rubric.py',
                 'tools/read-fiches.py', 'tools/model_schema.py')
SHA = 'dadce6f4cae85ca00f6a8a62bbfa442a9283b1bf2e8d1c3825772f09a6f21b01'      # FT-DM 2005, Chateau Desmirail
ART, EST, WINE, YEAR = 'ar_010990', 'es_00254', 'wn_00254', 2005
KEY = '["guard", "x", 10]'       # an evidence decision key, as the attribution names it (not resolved here)
CHECKS = []
_C = {}


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode('utf-8')


def load(name, rel, rev=None):
    """A runner as it is now, or as it was at `rev` (written to a temporary file, never into the repository)."""
    path = L.ROOT + rel
    if rev:
        d = tempfile.mkdtemp(prefix='bdx-branches-')
        path = os.path.join(d, os.path.basename(rel))
        open(path, 'w', encoding='utf-8', newline='\n').write(git('show', '%s:%s' % (rev, rel)))
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def mods():
    if not _C:
        _C['V'] = load('v1_now', 'tools/apply-vintage-creation-manifest.py')
        _C['V0'] = load('v1_before', 'tools/apply-vintage-creation-manifest.py', BEFORE)
        _C['VR'] = _C['V'].VR
        _C['VR0'] = load('vr_before', 'tools/apply-value-manifest.py', BEFORE)
    return _C


def listing_row():
    """The reviewed row the listing branch reads: identity_rules' listing record for the real sheet, the headings
    of the review's pages, the year as the sheet states it."""
    if 'row' not in _C:
        li = IR.listing({'id': ART, 'sha256': SHA}, WINE)
        assert li['status'] == P.LISTING_IDENTITY, li
        ents = P.reviewed_entries()
        by = {r['entry']: r for r in ents.values()}
        heads = {x['entry']: [p['heading'] for p in by[x['entry']]['pages'] if p['names_the_wine']][0]
                 for x in li['provenance']['listing']}
        _C['row'] = {
            'sha256': SHA, 'disposition': 'SAFE_TO_MAP', 'category': 'ACCEPTED_EXACT_ESTATE_WINE_VINTAGE',
            'estate': EST, 'wine': WINE, 'vintage': YEAR, 'identity_source': 'R4',
            'vintage_evidence': 'statement "millesime 2005" in the opening',
            'claims': [{'wine': WINE, 'disposition': 'SAFE_TO_MAP', 'claim_year_dated': False,
                        'reader': {'decision': 'ACCEPTED', 'code': 'ACCEPTED', 'why': ''},
                        'evidence_of_document': {'kind': 'DOCUMENT', 'rule': 'R4', 'basis': 'the reviewed listing',
                                                 'listing': li, 'headings': heads}}]}
    return copy.deepcopy(_C['row'])


def refused(rv, part, sha=SHA, wine=WINE):
    V = mods()['V']
    try:
        V.check_review(rv, sha, EST, wine, YEAR)
    except V.Invalid as x:
        assert part in str(x), (part, str(x))
        return
    raise AssertionError('accepted: %s' % part)


# ---- blocker 2 -------------------------------------------------------------------------------------------------

@check
def b2_reviewed_listing_is_an_attribution_method():
    base = json.load(open(L.ROOT + 'docs/phase34-model.json', encoding='utf-8'))
    assert 'REVIEWED_LISTING' not in base['enums']['AttributionMethod']['values']        # the protected contract
    assert 'REVIEWED_LISTING' in S.ENUMS['AttributionMethod']
    row = {'id': 'at_x', 'artifact': ART, 'estate': EST, 'wine': WINE, 'vintage': 'vt:%s:%d' % (WINE, YEAR),
           'role': 'FIRST', 'method': 'REVIEWED_LISTING', 'status': 'ACCEPTED', 'provenance': 'pv_x'}
    assert not S.check_row('Attribution', row), S.check_row('Attribution', row)
    assert S.check_row('Attribution', dict(row, method='LISTING')), 'an unknown method passed'


# ---- blocker 3: the listing branch -----------------------------------------------------------------------------

@check
def b3_a_signed_off_listing_settles_the_identity():
    mods()['V'].check_review(listing_row(), SHA, EST, WINE, YEAR)


@check
def b3_each_listing_condition_refuses():
    rv = listing_row()
    rv['claims'][0]['evidence_of_document']['rule'] = 'M34A'
    refused(rv, 'needs a DOCUMENT claim by rule R4')
    rv = listing_row()
    rv['claims'][0]['evidence_of_document']['listing']['provenance']['filename_used_as_identity_evidence'] = True
    refused(rv, 'the filename was used')
    rv = listing_row()
    rv['claims'][0]['evidence_of_document']['listing']['provenance']['sha256'] = '0' * 64
    refused(rv, 'for other bytes')
    rv = listing_row()
    rv['claims'][0]['evidence_of_document']['headings'] = {k: 'Initial de Desmirail' for k in
                                                           rv['claims'][0]['evidence_of_document']['headings']}
    refused(rv, 'is not the review\'s')
    rv = listing_row()
    rv['vintage_evidence'] = 'filename FT-DM-2005'
    refused(rv, 'the vintage is not stated in the document')
    rv = listing_row()
    rv['claims'][0]['claim_year_dated'] = True
    refused(rv, 'dated line')
    other = listing_row()
    for k in ('wine',):
        other[k] = 'wn_00499'
    other['claims'][0]['wine'] = 'wn_00499'
    refused(other, 'the listing identity is LISTING_IDENTITY for wn_00254', wine='wn_00499')


@check
def b3_the_review_is_read_again_and_the_sign_off_holds():
    real, signed = P.reviewed_entries, P.SIGNOFF
    rv = listing_row()
    eid = rv['claims'][0]['evidence_of_document']['listing']['provenance']['listing'][0]['entry']
    try:
        for change, part in ((('disposition', 'REQUIRES_REVIEW'), 'not APPROVED_R4'),
                             (('version', 'r4-listing-review/2'), 'not APPROVED_R4'),
                             (('effect', 'VETO_ONLY'), 'can only veto'),
                             (('wine', 'wn_00499'), 'is the page of wn_00499')):
            ents = copy.deepcopy(real())
            [k] = [k for k, r in ents.items() if r['entry'] == eid]
            ents[k][change[0]] = change[1]
            P.reviewed_entries = lambda path=None, e=ents: e
            refused(listing_row(), part)
        P.reviewed_entries = real
        P.SIGNOFF = dict(signed, entries=signed['entries'] - {eid})
        refused(listing_row(), 'approved but not signed off')
    finally:
        P.reviewed_entries, P.SIGNOFF = real, signed


@check
def b3_the_text_branch_is_not_loosened():
    m = mods()
    rv = listing_row()
    for src in ('R1', 'R1b', 'R2', 'R3', 'REVIEWED_LISTING', None):
        x = dict(rv, identity_source=src)
        refused(x, 'not established by the document\'s own text')
    x = listing_row()
    x['identity_source'] = 'M34A'          # a text identity resting on a claim the listing rule made
    refused(x, 'not established by the document\'s own text')
    # every M3.9 reviewed row: the same verdict, word for word, as the runner before the branch
    n = 0
    for r in L.jsonl_lines(L.ROOT + 'data/audit/m3.9-evidence-review.jsonl'):
        if r.get('record') != 'review':
            continue
        out = []
        for V in (m['V0'], m['V']):
            try:
                V.check_review(r, r.get('sha256'), r.get('estate'), r.get('wine'), r.get('vintage'))
                out.append('ok')
            except V.Invalid as e:
                out.append(str(e))
        assert out[0] == out[1], (r.get('n'), out)
        n += 1
    assert n >= 10, n


@check
def b3_the_listing_attribution_is_recorded_as_the_policy_says():
    V = mods()['V']
    view = V.View()
    rv = listing_row()
    src = V.listing_source(view, rv, EST)
    hosts = [s for s in view.table('identity/sources.jsonl') if s['id'] == src][0]['base_urls']
    assert any('desmirail.com' in b for b in hosts), hosts
    vt = 'vt:%s:%d' % (WINE, YEAR)
    r = {'manifest_id': 'vcm_999999', 'estate_id': EST, 'wine_id': WINE, 'vintage': YEAR, 'evidence_version': 10,
         'artifact_ids': [ART]}
    res = {'vintage': vt, 'evidence': {ART: KEY}, 'source': {ART: src},
           'review': {ART: dict(rv, _ref={'audit': 'data/audit/x.jsonl', 'row': 'x:1'})}}
    m = V._migrate().Model()
    V.add_attribution(m, r, res, ART, {'artifacts': {ART: {'sha256': SHA}}})
    [att] = m.tables['document/attributions.jsonl'].values()
    provs = {p['id']: p for p in m.tables['cross/provenance.jsonl'].values()}
    assert att['method'] == 'REVIEWED_LISTING' and att['status'] == 'ACCEPTED', att
    pub, = [p for p in provs.values() if p['kind'] == 'ESTATE_PUBLICATION']
    doc, = [p for p in provs.values() if p['kind'] == 'DOCUMENT']
    assert att['provenance'] == pub['id'] and pub['derived_from'] == [doc['id']] and pub['source'] == src
    assert pub['quote'] in rv['claims'][0]['evidence_of_document']['headings'].values(), pub['quote']
    cs = pub['code_state']
    assert cs['evidence_decisions'] == [KEY] and cs['identity_source'] == 'R4'
    assert cs['listing']['filename_used_as_identity_evidence'] is False and cs['listing']['sha256'] == SHA
    assert cs['signoff'] == {'by': 'user', 'date': '2026-11-18', 'review_version': 'r4-listing-review/1'}
    assert doc['artifact'] == ART and doc['quote'] == rv['vintage_evidence']
    for p in provs.values():
        assert not S.check_row('Provenance', p), S.check_row('Provenance', p)
    assert not S.check_row('Attribution', att), S.check_row('Attribution', att)
    ix = {'attributions': {ART: [att]}, 'prov': provs}
    assert V.exact(ix, ART, EST, WINE, vt, KEY, 'REVIEWED_LISTING')
    assert not V.exact(ix, ART, EST, WINE, vt, KEY)                 # never counted as a text attribution
    # the value runner's evidence chain reads the decision from it as from a text attribution
    try:
        V.VR.evidence_of(ART, EST, WINE, vt, YEAR, 10, dict(ix, artifacts={ART: {'sha256': SHA}}),
                         type('E', (), {'by_key': {}, 'latest': {}})())
    except V.VR.Invalid as x:
        assert 'is not in the store' in str(x), str(x)        # it found the key; the stub store does not hold it
    # the plan check counts two provenance rows for a listing attribution
    it = {'manifest_id': 'vcm_999999', 'vintage_ref': vt, 'action': 'ATTRIBUTION_ONLY', 'reason': '',
          'adds': {'cross/provenance.jsonl': list(provs.values()), 'document/attributions.jsonl': [att]}}
    V.verify_plan({'rows': [it], 'adds': {}})
    it['adds']['cross/provenance.jsonl'] = [pub]
    try:
        V.verify_plan({'rows': [it], 'adds': {}})
        raise RuntimeError('one provenance row passed')
    except AssertionError:
        pass


# ---- blocker 4: the C6 branch ----------------------------------------------------------------------------------

def c6_location():
    if 'c6' not in _C:
        yt = load('yield_layout_t2', 'tools/test-yield-layout.py')
        sha, want = yt.GRAND_MAYNE[2004]
        res = Y.read_yield(yt.held(sha), 'SAFE_TO_MAP', None, 2004, yt.WINE, yt.OTHERS)
        o = P.c6_observation(res, 'IDENTITY_SETTLED', None, 'vt:wn_00402:2004', 'ar_c6')
        _C['c6'] = (want, {'artifact': 'ar_c6', 'quote': o['provenance']['quote'], 'locus': o['observation']['locus'],
                           'lang': 'fr', 'c6': {'raw_value': o['observation']['raw_value'],
                                                'evidence': o['provenance']['code_state']}})
    want, loc = _C['c6']
    return want, copy.deepcopy(loc)


@check
def b4_a_c6_read_is_a_valid_location():
    VR = mods()['VR']
    want, loc = c6_location()
    assert want == 38 and VR.c6_location(loc, want) is None, VR.c6_location(loc, want)
    assert loc['quote'] == '38hl | 38ha'


@check
def b4_each_c6_condition_refuses():
    VR = mods()['VR']
    want, base = c6_location()
    cases = [
        (lambda l: l['c6'].update(raw_value=['38hl', '37ha']), 'do not both state'),
        (lambda l: l['c6'].update(raw_value=['38hl']), 'the two printed lines'),
        (lambda l: l['c6'].update(raw_value=['38 hl/ha', '38ha']), 'not a "NNhl" line'),
        (lambda l: l.update(quote='38 hl/ha'), 'the two lines as printed'),
        (lambda l: l['c6']['evidence'].update(unit_derived=False), 'mark the unit derived'),
        (lambda l: l['c6']['evidence'].update(source_prints_hl_per_ha=True), 'mark the unit derived'),
        (lambda l: l['c6']['evidence'].pop('arithmetic'), 'guards and arithmetic'),
        (lambda l: l['c6']['evidence']['french_line'].update(text='39hl'), 'lines are not the raw value'),
        (lambda l: l.update(locus=l['locus'] + ' (harvested yield)'), 'never called a harvested yield'),
    ]
    for change, part in cases:
        loc = copy.deepcopy(base)
        change(loc)
        why = VR.c6_location(loc, want)
        assert why and part in why, (part, why)
    assert 'do not both state' in VR.c6_location(base, 37)


def value_row(basis, loc, field='yld', value=38):
    return {'manifest_id': 'vam_999999', 'estate_id': 'es_00414', 'wine_id': 'wn_00402', 'vintage': 2004,
            'field': field, 'value': value, 'artifact_ids': [loc['artifact']], 'evidence_version': 10,
            'observation_group': 'g', 'application_class': 'SOURCED', 'source_basis': basis,
            'source_locations': [loc]}


@check
def b4_the_c6_value_is_recorded_as_the_policy_says():
    VR = mods()['VR']
    want, loc = c6_location()
    m = VR._migrate().Model()
    vt = 'vt:wn_00402:2004'
    VR.materialize(m, value_row(VR.C6_BASIS, loc), {'vintage': vt, 'evidence': {'ar_c6': KEY}})
    [o] = m.tables['observation/observations.jsonl'].values()
    [cv] = m.tables['canonical/values.jsonl'].values()
    provs = {p['id']: p for p in m.tables['cross/provenance.jsonl'].values()}
    assert o['raw_value'] == ['38hl', '38ha'] and o['value'] == 38 and o['unit'] == 'hl/ha', o
    assert o['confidence'] == 'UNIT_FROM_LAYOUT' and o['extraction']['method'] == Y.VERSION, o
    assert cv['derivation'] == 'UNIT_FROM_LAYOUT' and cv['status'] == 'SOURCED', cv
    pv = provs[o['provenance']]
    assert pv['kind'] == 'DOCUMENT' and pv['quote'] == '38hl | 38ha' and 'hl/ha' not in pv['quote']
    cs = pv['code_state']
    assert cs['unit_derived'] is True and cs['source_prints_hl_per_ha'] is False and cs['evidence_decision'] == KEY
    assert cs['french_line']['text'] == '38hl' and cs['english_line']['text'] == '38ha'
    assert 'harvest' not in L.dumps([o, cv, list(provs.values())]).lower()
    for ent, rows in (('Observation', [o]), ('CanonicalValue', [cv]), ('Provenance', provs.values())):
        for x in rows:
            assert not S.check_row(ent, x), (ent, S.check_row(ent, x))


@check
def b4_the_explicit_path_is_unchanged():
    m = mods()
    loc = {'artifact': 'ar_x', 'quote': 'Alcool : 13,5 %', 'locus': 'p1', 'lang': 'fr'}
    out = []
    for VR in (m['VR0'], m['VR']):
        mm = VR._migrate().Model()
        VR.materialize(mm, value_row('explicit_document_statement', loc, 'alc', 13.5),
                       {'vintage': 'vt:wn_00402:2004', 'evidence': {'ar_x': KEY}})
        out.append(L.dumps({k: sorted(v.values(), key=L.dumps) for k, v in sorted(mm.tables.items())}))
    assert out[0] == out[1]


@check
def b4_the_manifest_shape_holds_the_c6_branch():
    VR = mods()['VR']
    want, loc = c6_location()
    view = VR.View()
    ev = type('E', (), {'versions': {10}, 'by_key': {}, 'latest': {}})()
    bad_field = value_row(VR.C6_BASIS, loc, 'alc', 13.5)
    bad_c6 = value_row(VR.C6_BASIS, dict(loc, quote='38 hl/ha'))
    no_c6 = value_row(VR.C6_BASIS, {k: v for k, v in loc.items() if k != 'c6'})
    stray = value_row('explicit_document_statement', loc)
    for row, part in ((bad_field, 'recorded for [\'yld\'] only'), (bad_c6, 'the two lines as printed'),
                      (no_c6, '{artifact, locus, quote, lang, c6}'), (stray, '{artifact, locus, quote, lang}')):
        errs, _ = VR.validate_manifest([row], view, ev)
        assert any(part in e for e in errs), (part, errs)
    errs, _ = VR.validate_manifest([value_row(VR.C6_BASIS, loc)], view, ev)
    assert errs == ['vam_999999: artifact ar_c6 does not exist'], errs     # past the shape, stopped at the evidence


@check
def z1_nothing_else_changes():
    assert not git('diff', '--name-only', BEFORE, '--', *FINGERPRINTED)
    assert not git('status', '--porcelain', '--', 'data', 'sources')
    users = [p for p in sorted(os.listdir(L.ROOT + 'tools')) if p.endswith('.py')
             and p not in ('recording_policy.py', 'apply-vintage-creation-manifest.py', 'apply-value-manifest.py',
                          'test-recording-branches.py', 'integration-review.py', 'test-integration-review.py')
             and re.search(r'check_listing_review|C6_BASIS|layout_derived_unit', open(L.ROOT + 'tools/' + p, encoding='utf-8').read())]
    assert not users, users
    import integration_application as IA
    phase = IA.phase()
    for kind, f in (('vintage', 'data/audit/vintage-creation-manifest.jsonl'),
                    ('value', 'data/audit/value-application-manifest.jsonl'),
                    ('acceptance', 'data/audit/evidence-acceptance-manifest.jsonl')):
        txt = open(L.ROOT + f, encoding='utf-8').read() if os.path.exists(L.ROOT + f) else ''
        if phase == 'PRE_APPLY':
            assert 'layout_derived_unit' not in txt and '"R4"' not in txt, f      # no manifest row uses a branch yet
            continue
        # POST_APPLY: the rows that use a branch are the integration application's, and only they
        used = [r for r in L.jsonl_lines(L.ROOT + f) if 'layout_derived_unit' in L.dumps(r) or '"R4"' in L.dumps(r)]
        mine = IA.manifest_rows(kind)
        assert all(r in mine for r in used), f
    if phase == 'POST_APPLY':
        assert sum(r['source_basis'] == 'layout_derived_unit' for r in IA.manifest_rows('value')) == 15


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
