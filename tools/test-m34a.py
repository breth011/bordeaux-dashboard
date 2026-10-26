"""M3.4A: the accepted evidence mapping audit (audit and dry run only).

    python tools/test-m34a.py

Read-only. Holds data/audit/m3.4a-mapping-proposals.jsonl and its report to the rules of
tools/m34a-mapping-audit.py: every candidate decided exactly once, every document real and its hash
its own, every proposal resting on the document's own text and on an accepted decision's evidence
link, the refusals found in review staying refused, open decisions untouched, nothing changed, and
the output reproducible byte for byte.
"""

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import migration_lib as L  # noqa: E402

BEFORE = '357f44c'               # M3.3: the state before M3.4A
OUT = L.ROOT + 'data/audit/m3.4a-mapping-proposals.jsonl'
REPORT = L.ROOT + 'docs/PHASE-M3.4A-MAPPING-AUDIT.md'
CHECKS = []

spec = importlib.util.spec_from_file_location('m34a', L.ROOT + 'tools/m34a-mapping-audit.py')
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
A, P = M.A, M.P
ROWS = [json.loads(l) for l in open(OUT, encoding='utf-8')]
BUILT = M.build()                 # one fresh build per run, shared by the checks


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode()


def key(r):
    return (r['estate'], r['wine'], r['vintage'], r['artifact'])


@check
def every_candidate_appears_exactly_once():
    ev, _ = P.item_evidence(P.states())
    want = {(e, w, y, x['locator']) for (e, w, y), xs in ev.items() for x in xs
            if x['family'] == 'EXISTING_ACCEPTED_DOCUMENT'}
    got = [key(r) for r in ROWS]
    assert len(got) == len(set(got)), 'a candidate appears twice'
    assert set(got) == want, ('lost', sorted(want - set(got))[:3], 'extra', sorted(set(got) - want)[:3])
    assert len(ROWS) == 517 and len({(r['wine'], r['vintage']) for r in ROWS}) == 182   # verified, not assumed
    assert ROWS == sorted(ROWS, key=key)


@check
def every_disposition_is_one_of_eleven_with_a_reason():
    for r in ROWS:
        assert r['disposition'] in M.DISPOSITIONS, key(r)
        assert r['reason'] and r['reason'].strip(), key(r)
        assert ('proposal' in r) == (r['disposition'] == 'SAFE_TO_MAP'), key(r)          # only SAFE rows propose


@check
def artifacts_exist_and_their_hashes_match():
    arts = A.by_id('identity/artifacts.jsonl')
    checked = 0
    for r in ROWS:
        a = arts.get(r['artifact'])
        assert a and a['sha256'] == r['sha256'] and a['bytes_available'], key(r)
        for pl in A.placements_of(r['artifact']):
            q = L.ROOT + 'sources/' + pl['locator']['value']
            if pl['locator']['kind'] == 'LOCAL_PATH' and os.path.exists(q):
                assert hashlib.sha256(open(q, 'rb').read()).hexdigest() == r['sha256'], (key(r), q)
                checked += 1
    assert checked >= len({r['artifact'] for r in ROWS}) * 0.9, checked       # nearly every document re-hashed


@check
def estate_wine_and_vintage_exist():
    estates = A.by_id('identity/estates.jsonl')
    wines = A.by_id('identity/wines.jsonl')
    vintages = {'vt:%s:%s' % (v['wine'], v['label']) for v in A.table('identity/vintages.jsonl')}
    ew = {(x['estate'], x['wine']) for x in A.table('state/estate-wine.jsonl')}
    for r in ROWS:
        assert r['estate'] in estates and r['wine'] in wines, key(r)
        assert (r['estate'], r['wine']) in ew, key(r)
        assert r['vintage_id'] == 'vt:%s:%d' % (r['wine'], r['vintage']) and r['vintage_id'] in vintages, key(r)


@check
def safe_rows_carry_evidence_and_rest_on_the_document_text():
    links = {e['row_key'] for e in A.table('observation/evidence-links.jsonl') if e['evidence_version'] == 5}
    safe = [r for r in ROWS if r['disposition'] == 'SAFE_TO_MAP']
    assert safe
    for r in safe:
        p = r['proposal']
        assert r['evidence_refs'] and set(r['evidence_refs']) <= links, key(r)
        assert p['evidence_refs'] == r['evidence_refs'] and p['basis'] == r['basis'] == r['reason'], key(r)
        assert (p['artifact'], p['wine'], p['vintage'], p['sha256']) == (r['artifact'], r['wine'], r['vintage_id'], r['sha256'])
        assert p['action'] == 'LINK_ARTIFACT_TO_VINTAGE' and p['confidence'] == 'HIGH' and p['role'] in ('GRAND_VIN', 'NAMED_WINE')
        # one estate, one wine, one vintage claimed; the year in the document's own opening, not its name
        assert len({(c[0], c[1]) for c in r['accepted_claims']}) == 1 and {c[2] for c in r['accepted_claims']} == {r['vintage']}
        text, _ = M.document_text(r['artifact'])
        assert re.search(r'(?<!\d)%d(?!\d)' % r['vintage'], text[:M.OPENING]), key(r)
        # the wine named in the text: never the estate alone
        assert A.fold(r['wine_name']) in text or M.GRAND_VIN.search(text[:M.OPENING]) or \
            all(t in text for t in M.distinct_name(r['wine_name'], r['estate_name'])), key(r)


@check
def no_estate_only_document_is_promoted():
    for r in ROWS:
        if r['disposition'] == 'ESTATE_VINTAGE_ONLY':
            assert 'proposal' not in r and not r['basis'], key(r)
    # the refusals found in review stay refused
    def disp(pred):
        return {r['disposition'] for r in ROWS if pred(r)}
    files = lambda r: ' '.join(r['files'])
    assert disp(lambda r: r['estate_name'] == 'Clos Floridène') == {'COLOUR_AMBIGUOUS'}          # white and red sheets, one model wine
    assert disp(lambda r: 'SILT' in files(r)) == {'COLOUR_AMBIGUOUS'}                            # a white Vin de France cuvée
    assert disp(lambda r: 'Fiche-technique-Mondot' in files(r)) == {'MULTI_WINE_AMBIGUOUS'}      # the second wine, Mondot
    assert disp(lambda r: 'fete-de-la-fleur' in files(r)) == {'VINTAGE_AMBIGUOUS'}               # an event date, not a vintage
    assert disp(lambda r: 'Commentaires-Clos-Puy-Arnaud' in files(r)) == {'VINTAGE_AMBIGUOUS'}   # a press digest of eight vintages
    # "grand vin sec" in a history paragraph is not the sweet wine's role
    assert not M.GRAND_VIN.search('il crea le grand vin sec de doisy daene')
    assert not M.GRAND_VIN.search('grand vin de bordeaux') and M.GRAND_VIN.search('the grand vin presents')
    assert all(r['disposition'] != 'SAFE_TO_MAP' or r['proposal']['role'] != 'GRAND_VIN' or 'grand vin' in r['basis']
               or A.fold(r['wine_name']) in r['basis'].lower() or r['wine_name'] in r['basis'] for r in ROWS)


@check
def open_decisions_stay_unresolved():
    blocked = M.open_decision_wines(P.names())
    assert set(blocked.values()) >= {'D2', 'LAPARDE_IDENTITY', 'D5_SECOND_WINE_CONFLICT'}
    for r in ROWS:
        if r['wine'] in blocked:
            assert r['disposition'] == 'IDENTITY_BLOCKED', key(r)
        if r['disposition'] == 'SAFE_TO_MAP':
            sib = {P.names().get(w) for w in blocked}
            text, _ = M.document_text(r['artifact'])
            assert not any(s and A.fold(s) in text for s in sib), key(r)           # no SAFE mapping touches a blocked wine
    assert not L.read_table('identity/transitions.jsonl')
    f = L.read_table('cross/findings.jsonl')
    assert sum(1 for x in f if x['kind'] == 'AMBIGUOUS_SEMANTICS' and x['status'] == 'OPEN') == 179
    assert sum(1 for x in f if x['kind'] == 'CONFLICT' and x['status'] == 'OPEN') == 7


@check
def nothing_was_mutated():
    assert not git('diff', '--stat', BEFORE, '--', 'data/model', 'data/evidence', 'data/app', 'data/discovery',
                   'data/history', 'data/review', 'data/scope', ':(glob)data/*.js', 'data/sources.json',
                   'data/audit/data-gap-register.jsonl', 'data/audit/m32-recovery-candidates.jsonl',
                   'data/audit/m3.3-source-acquisition-plan.jsonl', 'docs/DATA-GAP-REGISTER.md',
                   'assets', 'index.html').strip()
    b0 = json.load(open(L.MODEL + 'baseline.json', encoding='utf-8'))['groups']
    for g in b0:
        assert L.group_hashes(g)['digest'] == b0[g]['digest'], g


@check
def output_is_deterministic():
    again = M.build()                          # a second, independent build
    assert M.body(BUILT) == M.body(again) == open(OUT, 'rb').read()
    for args in (['--check'], ['--report', '--check']):
        out = subprocess.run([sys.executable, L.ROOT + 'tools/m34a-mapping-audit.py'] + args, capture_output=True, text=True)
        assert out.returncode == 0, out.stdout + out.stderr
    text = open(OUT, encoding='utf-8').read() + open(REPORT, encoding='utf-8').read()
    assert L.ROOT not in text and 'Users' not in text                          # no environment in the output


@check
def the_report_has_its_ten_sections_and_gate():
    text = open(REPORT, encoding='utf-8').read()
    heads = re.findall(r'^## (\d+)\. ', text, re.M)
    assert heads == [str(i) for i in range(1, 11)], heads
    assert 'Gate: SAFE — M3.4A EXISTING EVIDENCE MAPPING AUDIT COMPLETE — READY FOR MAPPING REVIEW' in text
    n = sum(1 for r in ROWS if r['disposition'] == 'SAFE_TO_MAP')
    assert '| SAFE_TO_MAP | %d |' % n in text


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
