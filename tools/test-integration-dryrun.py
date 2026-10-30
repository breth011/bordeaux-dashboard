"""The integration dry-run (tools/integration-dryrun.py): one boundary for identity, reader, statement v2 and C6.

    python tools/test-integration-dryrun.py

Read-only. The combinations the contract (docs/INTEGRATION-CONTRACT.md) names are exercised through the dry-run's
own evaluate(), on real claims where the corpus holds one and on stubbed layers where it does not: the layers' results
are given, the orchestration and its precedence are what is tested. The committed report is recomputed and compared,
and nothing in production imports the modules or changes.
"""
import contextlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import types
import warnings

warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import identity_rules_candidate as IRC  # noqa: E402
import migration_lib as L  # noqa: E402
import statement_check as S2  # noqa: E402

BEFORE = 'b5b5fe1'               # C6, isolated: the state this phase starts from
_s = importlib.util.spec_from_file_location('dryrun_t', L.ROOT + 'tools/integration-dryrun.py')
D = importlib.util.module_from_spec(_s)
_s.loader.exec_module(D)
CHECKS = []
FINGERPRINTED = ('tools/m34a-mapping-audit.py', 'tools/sheetreader.py', 'tools/web_evidence.py', 'tools/m35_rubric.py',
                 'tools/read-fiches.py', 'tools/model_schema.py')
DRYRUN_FILES = ('integration-dryrun.py', 'test-integration-dryrun.py')
GM_2004 = D.GRAND_MAYNE[2004]                       # (sha, 38.0): a real Grand Mayne sheet for the stubbed claims
_ROWS = []
_BYTES = {}


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode('utf-8')


def rows():
    if not _ROWS:
        _ROWS.extend(D.build_claims())
    return _ROWS


def by_id(cid):
    return next(r for r in rows() if r['claim_id'] == cid)


def gm_bytes():
    if 'gm' not in _BYTES:
        p = D.P1.X.Presenter()
        try:
            _BYTES['gm'] = p.blob(GM_2004[0])
        finally:
            p.close()
    return _BYTES['gm']


class Stub:
    """Layers with given results: identity status, the reader's figure, the joined text and the PDF bytes. The
    claim is Grand Mayne 2004's, so that the real sheet's bytes fit it."""

    def __init__(self, status, value=None, j='', blob=None, field='alc', disposition=None, hold=None):
        self.status, self.value, self.j, self.blob, self.field = status, value, j, blob, field
        self.disposition = disposition or ('SAFE_TO_MAP' if status == 'IDENTITY_SETTLED' else 'VINTAGE_AMBIGUOUS')
        self.hold = hold
        self.c6_calls = 0
        stub = self

        def blob_of(sha):
            stub.c6_calls += 1
            return stub.blob
        self.prod = types.SimpleNamespace(
            figures=lambda sha, e, y: (({self.field: self.value} if self.value is not None else {}), {}, self.j),
            pres=types.SimpleNamespace(blob=blob_of),
            cx=types.SimpleNamespace(nm={'wn_t': 'Château Grand Mayne', 'wn_s': 'Filia de Grand Mayne'}))

    def both(self, sha, e, w, y, ew):
        ident = {'status': self.status, 'disposition': self.disposition, 'reason': 'stubbed: %s' % self.disposition,
                 'rule': 'M34A', 'kind': 'DOCUMENT', 'rules': ['R3'], 'trace': [], 'notes': []}
        return {'status': self.status, 'settled_by': 'CANDIDATE_RULES' if self.status == 'IDENTITY_SETTLED' else None,
                'review_hold': self.hold, 'regimes_disagree': False, 'production': dict(ident), 'candidate': ident}


@contextlib.contextmanager
def held_text(raw='chateau grand mayne 2004'):
    old = D.P1.text_of
    D.P1.text_of = lambda sha: (raw, None, 'application/pdf')
    try:
        yield
    finally:
        D.P1.text_of = old


def claim(field='alc', source='P1', first_party='A'):
    return {'claim_id': 'stub', 'source': source, 'tags': [], 'review_id': None, 'artifact': 'ar_x', 'sha256': 'f' * 64,
            'url': None, 'estate_id': 'es_t', 'estate': 'Chateau Test', 'wine_id': 'wn_t', 'wine': 'Chateau Test',
            'vintage': 2004, 'field': field, 'first_party': first_party, 'gap_status': 'MISSING', 'audit_refs': {}}


def run(stub, field='alc', values=None, **kw):
    ctx = {'names': {'wn_t': ['Château Grand Mayne']}, 'ew': {'es_t': {'wn_t', 'wn_s'}}, 'values': values or {}, 'linked': set()}
    with held_text():
        return D.evaluate(stub, claim(field, **kw), ctx)


ALC = 'fiche technique / degre alcoolique 13,5 %'
BLEND = 'assemblage / cabernet sauvignon : 51% / merlot : 49%'


@check
def t01_identity_refused_statement_confirmed():
    """A: the statement confirms, the identity is not settled - refused, the confirmation kept as a diagnostic."""
    r = run(Stub('IDENTITY_REFUSED', 13.5, ALC))
    assert r['final']['disposition'] == 'REFUSED' and r['final']['reason_code'] == 'IDENTITY_NOT_SETTLED', r['final']
    assert r['statement']['diagnostic'] == 'CONFIRMED' and r['statement']['gated'] == 'NOT_EVALUATED'
    assert r['reader']['mode'] == 'DIAGNOSTIC' and r['final']['value'] is None
    for cid in ('gs_eaefc0184f76', 'gs_269c6fdca3d8', 'gs_59c7bc4f8cbd', 'gs_8ef443db52d6', 'gs_b462e5fe8a11'):
        x = by_id(cid)                              # Kirwan 2019 pH and yld, Issan 2012 blend, pH, yld: real
        assert x['statement']['diagnostic'] == 'CONFIRMED' and x['statement']['gated'] != 'CONFIRMED', cid
        assert x['final']['disposition'] == 'REFUSED' and x['final']['reason_code'] == 'IDENTITY_NOT_SETTLED', cid


@check
def t02_settled_reader_confirmed():
    """B: settled, the reader's figure, the statement confirms - a candidate, and nothing is written."""
    r = run(Stub('IDENTITY_SETTLED', 13.5, ALC))
    f = r['final']
    assert f['disposition'] == 'ACCEPTABLE_TO_NEXT_STAGE' and f['value'] == 13.5 and f['value_source'] == 'READER', f
    assert r['statement']['gated'] == 'CONFIRMED' and r['c6']['status'] == 'NOT_APPLICABLE'
    x = by_id('gs_289919c0662e')                    # Desmirail 2005 "degre 13 %": real
    assert x['final']['disposition'] == 'ACCEPTABLE_TO_NEXT_STAGE' and x['statement']['v1_reference'] == 'NOT_FOUND_AS_STATED'


@check
def t03_settled_reader_contradicted():
    """C: the statement contradicts the reader - a conflict; neither value is chosen."""
    assert S2.stated('blend', BLEND)[0] == {'CS': 51.0, 'ME': 49.0}
    r = run(Stub('IDENTITY_SETTLED', {'CS': 49.0, 'ME': 51.0}, BLEND, field='blend'), field='blend')
    f = r['final']
    assert f['disposition'] == 'CONFLICT' and f['reason_code'] == 'READER_CONTRADICTED_BY_STATEMENT', f
    assert f['value'] is None and r['reader']['value'] == {'CS': 49.0, 'ME': 51.0}
    assert r['statement']['stated_value'] == {'CS': 51.0, 'ME': 49.0}
    # 50/50 against a 51/49 statement: no symmetric figure hides the direction
    r = run(Stub('IDENTITY_SETTLED', {'CS': 50.0, 'ME': 50.0}, BLEND, field='blend'), field='blend')
    assert r['final']['reason_code'] == 'READER_CONTRADICTED_BY_STATEMENT', r['final']


@check
def t04_settled_no_reader_yield_c6_reads():
    """D: settled, no reader yield, C6 reads - a candidate with the derived unit and the printed lines."""
    st = Stub('IDENTITY_SETTLED', None, 'fiche', blob=gm_bytes(), field='yld')
    r = run(st, field='yld')
    f, c6 = r['final'], r['c6']
    assert f['disposition'] == 'ACCEPTABLE_TO_NEXT_STAGE' and f['reason_code'] == 'C6_LAYOUT_CONFIRMED', f
    assert f['value'] == GM_2004[1] and f['unit'] == 'hl/ha' and f['value_source'] == 'C6_LAYOUT'
    assert f['unit_basis'].startswith('LAYOUT_DERIVED') and 'neither "hl/ha" nor "per hectare"' in f['unit_basis']
    assert c6['literal']['french_line'] == '38hl' and c6['literal']['english_line'] == '38ha', c6['literal']
    assert 'derived unit' in f['recording_path']
    assert 'harvest' not in json.dumps(r).lower()


@check
def t05_unsettled_c6_would_pass():
    """E: the layout would pass, the identity is not settled - C6 is not eligible; the layout rescues nothing."""
    r = run(Stub('IDENTITY_REFUSED', None, 'fiche', blob=gm_bytes(), field='yld'), field='yld')
    assert r['c6']['status'] == 'NOT_ELIGIBLE' and r['c6']['diagnostic_if_identity_were_settled']['status'] == 'READ'
    assert r['final']['disposition'] == 'REFUSED' and r['final']['reason_code'] == 'IDENTITY_NOT_SETTLED'
    x = by_id('gs_b1e4a29592a5')                    # Grand Mayne 2005: G1 refuses; the layout would read 35 - real
    assert x['identity']['status'] == 'IDENTITY_REFUSED' and 'G1' in x['identity']['candidate']['rules']
    assert x['c6']['status'] == 'NOT_ELIGIBLE' and x['c6']['diagnostic_if_identity_were_settled']['value'] == 35.0
    assert x['final']['disposition'] == 'REFUSED'


@check
def t06_reader_yield_c6_not_run():
    """F: the reader read a yield - C6 does not run (its bytes are never even fetched)."""
    st = Stub('IDENTITY_SETTLED', 38.0, 'fiche', blob=gm_bytes(), field='yld')
    r = run(st, field='yld')
    assert r['c6']['status'] == 'NOT_RUN' and st.c6_calls == 0, r['c6']
    assert r['final']['value_source'] != 'C6_LAYOUT'
    x = by_id('gs_e0dab80ce8cc')                    # Issan 2004 "Rendement 54 hl/ha": the reader's - real
    assert x['c6']['status'] == 'NOT_RUN' and x['final']['value_source'] == 'READER'


@check
def t07_statement_without_reader_value():
    """G: the document states the field, the reader reads none - no value is made from the statement."""
    r = run(Stub('IDENTITY_SETTLED', None, ALC))
    f = r['final']
    assert f['disposition'] == 'REFUSED' and f['reason_code'] == 'STATEMENT_STATED_VALUE_UNRESOLVED', f
    assert f['value'] is None and r['statement']['stated_value'] == 13.5 and r['statement']['gated'] == 'NOT_READ'


@check
def t08_layers_disagree():
    """H: C6 reads one yield, the document's statement another - a conflict; no winner."""
    j = 'fiche / rendement : 40 hl/ha'
    assert S2.stated('yld', j)[0] == 40.0
    r = run(Stub('IDENTITY_SETTLED', None, j, blob=gm_bytes(), field='yld'), field='yld')
    assert r['c6']['status'] == 'READ' and r['c6']['value'] == 38.0
    assert r['final']['disposition'] == 'CONFLICT' and r['final']['reason_code'] == 'LAYERS_DISAGREE', r['final']
    assert r['final']['value'] is None


@check
def t09_precedence_and_holds():
    """Preconditions before identity; a conflicted identity and a held one never proceed; C6 is yield only."""
    r = run(Stub('IDENTITY_SETTLED', 13.5, ALC), values={('vt:wn_t:2004', 'alc'): 13.5})
    assert r['final']['reason_code'] == 'MODEL_HOLDS_VALUE'
    assert run(Stub('IDENTITY_SETTLED', 13.5, ALC), first_party='B')['final']['reason_code'] == 'NOT_FIRST_PARTY'
    assert run(Stub('IDENTITY_SETTLED', 13.5, ALC), source='EXTRA')['final']['reason_code'] == 'SOURCE_NOT_ASSESSED'
    r = run(Stub('IDENTITY_CONFLICTED', 13.5, ALC, disposition='MULTI_WINE_AMBIGUOUS'))
    assert r['final']['disposition'] == 'CONFLICT' and r['statement']['gated'] == 'NOT_EVALUATED'
    r = run(Stub('IDENTITY_REVIEW_REQUIRED', 13.5, ALC, disposition='SAFE_TO_MAP', hold='stubbed hold'))
    assert r['final']['disposition'] == 'REVIEW_REQUIRED' and r['statement']['gated'] == 'NOT_EVALUATED'
    st = Stub('IDENTITY_SETTLED', None, 'fiche', blob=gm_bytes(), field='alc')
    r = run(st)
    assert r['c6']['status'] == 'NOT_APPLICABLE' and st.c6_calls == 0
    x = by_id('gs_ac9e56dfd0d4')                    # Chapelle 1998: the rules settle it, the hold stops it - real
    assert x['identity']['candidate']['disposition'] == 'SAFE_TO_MAP' and x['final']['disposition'] == 'REVIEW_REQUIRED'


@check
def t10_candidate_rules_scope():
    """The rules answer only inside applied(); outside it decide is production's again; holds are the audit's five."""
    m = D.V.M34A
    orig = m.decide
    with IRC.applied(m):
        assert m.decide is not orig
    assert m.decide is orig
    assert len(IRC.REVIEW_HOLD) == 5 and IRC.held_for_review('1c74d87a4ddcd665' + '0' * 48, 'wn_00534', 1998)


@check
def t11_every_expectation_holds():
    bad = [e for e in D.expectations(rows()) if not e['ok']]
    assert not bad, bad
    assert all(r['final']['disposition'] in D.FINAL and r['identity']['status'] in D.IDENTITY for r in rows())


@check
def t12_reproduces_the_committed_dry_run():
    committed = [json.loads(x) for x in open(D.OUT, encoding='utf-8')]
    now = [json.loads(x) for x in D.body(rows(), {'record': 'statement_corpus'}).decode('utf-8').splitlines()]
    assert [r for r in committed if r['record'] == 'claim'] == [r for r in now if r['record'] == 'claim']


@check
def t13_nothing_in_production_changes():
    assert not git('diff', '--name-only', BEFORE, '--', *FINGERPRINTED)
    assert not git('status', '--porcelain', '--', 'data', 'sources', ':!data/audit/integration-dryrun.jsonl')
    uses = {   # a module by its import or its file name; the hyphenated dry run can only be loaded by its path
        'statement_check': (r'(?m)^\s*(?:import|from)\s+statement_check\b|statement_check\.py',
                            ('statement_check.py', 'test-statement-check.py')),
        'yield_layout': (r'(?m)^\s*(?:import|from)\s+yield_layout\b|yield_layout\.py',
                         ('yield_layout.py', 'test-yield-layout.py')),
        'identity_rules_candidate': (r'(?m)^\s*(?:import|from)\s+identity_rules_candidate\b|identity_rules_candidate\.py',
                                     ('identity_rules_candidate.py', 'r4-listing-review.py', 'recording_policy.py',
                                      'test-recording-policy.py')),
        'integration-dryrun': (r'spec_from_file_location\([^)]*integration-dryrun\.py', ()),
    }
    for mod, (rx, own) in uses.items():
        users = [p for p in sorted(os.listdir(L.ROOT + 'tools')) if p.endswith('.py') and p not in own + DRYRUN_FILES
                 and re.search(rx, open(L.ROOT + 'tools/' + p, encoding='utf-8').read())]
        assert not users, (mod, users)


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
