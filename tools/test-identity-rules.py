"""The adopted identity rules (tools/identity_rules.py), beside M3.4A's decide.

    python tools/test-identity-rules.py

Read-only. On the integration dry run's corpus, every decide call is answered by the adopted rules exactly as by the
candidate rules, except the changes the two decisions name (R2 narrowed to the title block; R4 only on approved
listing entries); the dry run's 57 candidates become 51. On a synthetic module: decide is never replaced, the text
seam is always restored, R2 reads only a title block, G1 still withdraws, and a listed claim is never SAFE_TO_MAP.
Nothing in production imports the module.
"""
import collections
import importlib.util
import json
import os
import re
import subprocess
import sys
import warnings

warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import identity_rules as IR  # noqa: E402
import identity_rules_candidate as I  # noqa: E402
import migration_lib as L  # noqa: E402

BEFORE = '37cf151'               # the last commit before the adopted rules
DRYRUN = L.ROOT + 'data/audit/integration-dryrun.jsonl'
FINGERPRINTED = ('tools/m34a-mapping-audit.py', 'tools/sheetreader.py', 'tools/web_evidence.py', 'tools/m35_rubric.py',
                 'tools/read-fiches.py', 'tools/model_schema.py')
# (sha12, wine, vintage) -> why the adopted rules answer otherwise than the candidate's, and the candidate's answer
CHANGED = {
    ('1c74d87a4ddc', 'wn_00534', 1998): ('Chapelle 1998: bare R2 not adopted; its listing entry REQUIRES_REVIEW', 'SAFE_TO_MAP'),
    ('ff3f74b8517d', 'wn_00167', 2022): ('Paloumey 2022: single-line R2 not adopted', 'SAFE_TO_MAP'),
    ('87b0089b0f12', 'wn_00283', 2004): ('Issan 2004: the chateau page REQUIRES_REVIEW', 'SAFE_TO_MAP'),
    ('f6d4b98d6d3f', 'wn_00283', 2010): ('Issan 2010: the chateau page REQUIRES_REVIEW', 'SAFE_TO_MAP'),
    ('80d9fedb054a', 'wn_00219', 2014): ('Caillou 2014: refused by G1 before, now unsettled without single-line R2',
                                         'WINE_AMBIGUOUS'),
}
ISSAN_LOST = {'gs_eccc4afd2daf', 'gs_dd04f3148961', 'gs_e0dab80ce8cc', 'gs_c655425d035f', 'gs_08395b0b4a39',
              'gs_ad0c9ecec15c'}     # DECISION-RECORDING-POLICY.md: the six that lose R4
CHECKS = []
_CORPUS = []


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode('utf-8')


def corpus():
    """Every decide call the P1 reader makes over the dry run's claims and their siblings, answered three ways:
    (key, candidate result, adopted record). The recorder below is the test's own; identify never patches."""
    if _CORPUS:
        return _CORPUS[0]
    spec = importlib.util.spec_from_file_location('p1_ir_t', L.ROOT + 'tools/m312-p1-review.py')
    p1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(p1)
    m = p1.V.M34A
    claims = sorted({(r['claim']['sha256'], r['claim']['estate_id'], r['claim']['wine_id'], r['claim']['vintage'])
                     for r in L.jsonl_lines(DRYRUN) if r['record'] == 'claim'})
    rd, calls, orig = p1.Reader(), {}, m.decide

    def recorder(*args):
        calls[(IR.doc_key(args[1])[:12], args[4], args[5])] = (args, m.document_text)   # text_hook's text
        return orig(*args)
    m.decide = recorder
    try:
        for sha, e, w, y in claims:
            for x in [w] + sorted(set(rd.cx.ew[e]) - {w}):
                rd.claim(sha, e, x, y)
    finally:
        m.decide = orig
    rd.close()
    s, held_text, out = I.series(), m.document_text, []
    try:
        for k, (args, hook) in sorted(calls.items()):
            a = args[1]
            m.document_text = hook
            text, how = hook(a['id']) if a and a.get('id') and a.get('bytes_available') else (None, None)
            cand = I.evaluate(m, orig, I.RULES, text, how, s.mapping(s.urls(a)), args)['result'] if text else orig(*args)
            rec = IR.identify(m, args)
            assert m.decide is orig and m.document_text is hook, k
            out.append((k, cand, rec))
    finally:
        m.document_text = held_text
    _CORPUS.append(out)
    return out


@check
def t01_the_corpus_changes_only_as_decided():
    rows = corpus()
    assert len(rows) > 250, len(rows)
    diff = {k: (c[0], r['result'][0]) for k, c, r in rows if c[0] != r['result'][0]}
    assert set(diff) == set(CHANGED), sorted(set(diff) ^ set(CHANGED))
    for k, (was, now) in diff.items():
        assert was == CHANGED[k][1] and now != IR.SAFE, (k, was, now)
    safe = [r for _, _, r in rows if r['result'][0] == IR.SAFE]
    assert len(safe) == 46 and all(r['settled_by'] in ('PRODUCTION', 'ADOPTED_RULES') for r in safe), len(safe)


@check
def t02_r4_runs_only_on_approved_desmirail_entries():
    rows = corpus()
    r4 = [(k, x) for k, _, r in rows for x in r['trace'] if x[0] in ('R4', 'R4_VETO')]
    assert r4
    for k, x in r4:
        assert x[1] == 'REVIEWED_LISTING' and x[-1] == IR.ENTRY_SIGNOFF, x
        if x[0] == 'R4':
            assert all(e.startswith('desmirail.com/') for e in x[3]), x
            assert all(IR.entries()[(e.split('/', 1)[0], '/' + e.split('/', 1)[1])]['disposition'] == 'APPROVED_R4'
                       for e in x[3]), x
    for k in [('87b0089b0f12', 'wn_00283', 2004), ('f6d4b98d6d3f', 'wn_00283', 2010)]:
        rec = [r for kk, _, r in rows if kk == k][0]
        assert rec['listing']['code'] == 'LISTING_ENTRY_NOT_APPROVED', rec['listing']
        assert not any(x[0].startswith('R4') for x in rec['trace'])


@check
def t03_the_dry_runs_57_candidates_become_51():
    now = {k: r['result'][0] for k, _, r in corpus()}
    cand = [r for r in L.jsonl_lines(DRYRUN) if r['record'] == 'claim'
            and r['final']['disposition'] == 'ACCEPTABLE_TO_NEXT_STAGE']
    assert len(cand) == 57, len(cand)
    lost = {r['claim_id'] for r in cand
            if now.get((r['claim']['sha256'][:12], r['claim']['wine_id'], r['claim']['vintage'])) != IR.SAFE}
    assert lost == ISSAN_LOST, sorted(lost ^ ISSAN_LOST)
    assert len(cand) - len(lost) == 51


# ---- a synthetic M3.4A module: decide reads the opening through document_text, as the real one does ----------

class Fake:
    OPENING = 600
    OTHER_WINE = re.compile(r'second wine|second vin')

    def __init__(self, text, raise_on_rewrite=False):
        self.text, self.raise_on_rewrite, self.seen = text, raise_on_rewrite, []

    def document_text(self, aid):
        return (self.text, 'synthetic')

    def distinct_name(self, wname, ename):
        return None

    def decide(self, row, a, claims, e, w, y, nm, ew, wines, blocked, vdocs):
        t, _ = self.document_text(a['id'])
        self.seen.append(t)
        if self.raise_on_rewrite and t != self.text:
            raise RuntimeError('decide failed on the rewritten text')
        op = t[:self.OPENING]
        if not re.search(r'(?<!\d)%d(?!\d)' % y, op):
            return ('VINTAGE_AMBIGUOUS', 'the opening does not state %d' % y, None, {})
        if 'chateau test' in op:
            return ('SAFE_TO_MAP', 'named', None, {'grand_vin': True})
        return ('ESTATE_VINTAGE_ONLY', 'the estate only', None, {})


FILLER = ('x ' * 80 + '\n') * 5         # long lines: past the 600-character opening, never a heading
NM = {'es_t': 'Château Test', 'wn_t': 'Château Test', 'wn_s': 'Le Second de Test'}
EW = {'es_t': ['wn_t', 'wn_s']}


def run(text, y=2015, sha=None, **kw):
    f = Fake(text, **kw)
    a = {'id': 'm3.8:' + (sha or '0123456789ab'), 'bytes_available': True}
    d = f.decide
    rec = IR.identify(f, ({}, a, [], 'es_t', 'wn_t', y, NM, EW, {}, set(), {}))
    assert f.decide == d and f.document_text.__func__ is Fake.document_text
    return rec


@check
def t04_r2_reads_only_a_title_block():
    block = run(FILLER + 'chateau test\ngrand cru classe\n2015\n')
    assert block['result'][0] == IR.SAFE and block['settled_by'] == 'ADOPTED_RULES', block['result']
    assert [x[:2] for x in block['trace']] == [('R2', 'NAMED_BLOCK')]
    single = run(FILLER + 'chateau test 2015\n')
    assert single['result'][0] != IR.SAFE and 'single-line heading is not adopted' in single['notes'][0], single['notes']
    bare = run(FILLER + 'millesime 2015\n')
    assert bare['result'][0] != IR.SAFE, bare['result']
    rival = run(FILLER + 'chateau test\n2015\n' + FILLER + 'chateau test\n2014\n')
    assert rival['result'][0] != IR.SAFE and 'competing headings' in rival['notes'][0], rival['notes']


@check
def t05_g1_still_withdraws_a_rule_made_grand_vin():
    rec = run(FILLER + 'chateau test\n2015\n' + FILLER + 'the second wine is aged in tank\n')
    assert rec['result'][0] == 'WINE_AMBIGUOUS' and rec['trace'][-1] == ('G1', 'second wine'), rec['trace']
    assert rec['result'][3]['identity_rules_version'] == IR.VERSION


@check
def t06_a_listed_claim_is_never_safe():
    assert set(IR.CLAIM_DECISIONS) == set(I.REVIEW_HOLD)               # the same five claims, now decided
    assert collections.Counter(d for d, _ in IR.CLAIM_DECISIONS.values()) == {IR.HOLD: 2, IR.REFUSE: 3}
    brane = 'a9dd99ecfc891e24' + '7' * 48
    assert IR.claim_decision(brane, 'wn_00215', 2023)[0] == IR.REFUSE
    assert IR.claim_decision(brane[:12], 'wn_00215', 2023)[0] == IR.REFUSE        # an m3.8 id holds 12 characters
    assert IR.claim_decision(brane, 'wn_00215', 2022) is None and IR.claim_decision(brane[:11], 'wn_00215', 2023) is None
    assert IR.claim_decision('a9dd99ecfc891e25' + '0' * 48, 'wn_00215', 2023) is None
    refused = IR.identify(Fake('chateau test 2023\n'), ({}, {'id': 'm3.8:' + brane[:12], 'bytes_available': True}, [],
                                                       'es_t', 'wn_00215', 2023, dict(NM, wn_00215='Château Test'),
                                                       {'es_t': ['wn_00215', 'wn_s']}, {}, set(), {}))
    assert refused['base'][0] == IR.SAFE and refused['result'][0] == IR.REFUSED and refused['settled_by'] is None
    assert refused['trace'][-1] == ('CLAIM_LIST', IR.REFUSE, 'a9dd99ecfc891e24')


@check
def t07_the_text_seam_is_restored_when_decide_fails():
    f = Fake(FILLER + 'chateau test\n2015\n', raise_on_rewrite=True)
    try:
        IR.identify(f, ({}, {'id': 'm3.8:0123456789ab', 'bytes_available': True}, [], 'es_t', 'wn_t', 2015, NM, EW,
                        {}, set(), {}))
        raise AssertionError('decide\'s failure was swallowed')
    except RuntimeError:
        pass
    assert f.document_text.__func__ is Fake.document_text and f.document_text('x') == (f.text, 'synthetic')


@check
def t08_nothing_in_production_changes():
    assert not git('diff', '--name-only', BEFORE, '--', *FINGERPRINTED)
    assert not git('status', '--porcelain', '--', 'data', 'sources')
    own = ('identity_rules.py', 'test-identity-rules.py', 'test-recording-branches.py', 'integration-review.py', 'test-integration-review.py')
    users = [p for p in sorted(os.listdir(L.ROOT + 'tools')) if p.endswith('.py') and p not in own
             and re.search(r'(?m)^\s*(?:import|from)\s+identity_rules\b(?!_)|'
                           r'spec_from_file_location\([^)]*identity_rules\.py',     # a use, not a guard naming it
                           open(L.ROOT + 'tools/' + p, encoding='utf-8').read())]
    assert not users, users
    src = open(L.ROOT + 'tools/identity_rules.py', encoding='utf-8').read()
    assert not re.search(r'mod\.decide\s*=|\.decide\s*=(?!=)', src)          # decide is called, never assigned


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
