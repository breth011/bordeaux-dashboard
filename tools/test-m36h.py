"""Phase M3.6H: the one Cuvée Mongravey acceptance M3.6E did not see, corrected as v8 (tools/m36h-apply.py).

    python tools/test-m36h.py

Read-only. v1-v7 are byte for byte; v8 is one appended REFUSED correction superseding the v5 acceptance of
ar_010314 (FT-Cuvee-Mongravey-2015.pdf) as Château Mongravey 2015, naming wn_00640; the sheet's latest
answer now names wn_00640 and no Cuvée sheet is still accepted as a grand vin; the reader and rubric are
those of v7; the model, its evidence links and the app are as M3.6G left them; the outputs recompute.
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_cache as CC  # noqa: E402
import evidence as EV  # noqa: E402
import evidence_store as ST  # noqa: E402
import historical_m2_scope as H  # noqa: E402
import migration_lib as L  # noqa: E402
import mig_m6_provenance as M6  # noqa: E402

BEFORE = 'be7527d'               # M3.6G: the state M3.6H is applied to
MANIFEST = L.ROOT + H.M36H_MANIFEST
ART, SHA = 'ar_010314', 'a4bbe67402d9e1356348b4338eda82527090ad4165c62241da0e09d52adb1f8a'
WINE, GRAND_VIN = 'wn_00640', 'wn_00158'
SHEET = re.compile(r'cuvee.?(de.?)?mongravey|mongravey.?cuvee', re.I)
CHECKS = []


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode('utf-8')


def manifest(record=None):
    return [r for r in L.jsonl_lines(MANIFEST) if record is None or r['record'] == record]


@check
def t01_v1_to_v7_are_byte_for_byte():
    H.evidence_unchanged_but_m36h(BEFORE)
    old = ['data/evidence/decisions-v%d.jsonl' % v for v in range(1, 8)]
    assert not git('diff', '--stat', BEFORE, '--', *old).strip() and not git('status', '--porcelain', '--', *old).strip()
    assert ST.verify() == [] and ST.versions() == [1, 2, 3, 4, 5, 6, 7, 8]


@check
def t02_v8_is_one_appended_correction():
    [d] = H.m36h_evidence_rows()
    [m] = manifest('correction')
    old = json.loads(m['decision'])
    assert old[-1] == 5 and json.loads(M6.row_key(d)) == old[:-1] + [8] == json.loads(m['superseded_by'])
    sup = [x for x in ST.iter_rows([5]) if M6.row_key(x) == m['decision']]
    assert len(sup) == 1 and sup[0]['decision'] == 'ACCEPTED' and sup[0]['ctx']['evaluated_as'] == 'Château Mongravey, vintage 2015'
    assert d['supersedes'] == {'row_key': m['decision'], 'v': 5, 'decision': 'ACCEPTED', 'code': 'ACCEPTED'}
    assert (d['kind'], d['decision'], d['code']) == ('correction', 'REFUSED', 'WRONG_WINE')
    assert d['document_is'] == {'title': ['cuvee de mongravey', 2015], 'model_wines': [WINE], 'unlisted': False}
    assert d['points_at'] == {'role': None, 'wine': WINE} and d['ctx'] == sup[0]['ctx'] and d['ctx']['vintage'] == 2015
    assert d['replacement']['decision'] is None and d['replacement']['attribution'] is None
    assert d['read'] == sup[0]['read'] and d['read']['sha256'] == SHA
    assert {x['reader'] for x in ST.iter_rows([7])} == {d['reader']}, 'not v7\'s reader and rubric'
    assert not git('diff', '--stat', BEFORE, '--', 'tools/m35_rubric.py', 'tools/web_evidence.py', 'tools/sheetreader.py',
                   'tools/read-fiches.py', 'tools/m34a-mapping-audit.py', 'tools/model_schema.py', 'tools/evidence.py').strip()


@check
def t03_the_sheet_now_resolves_to_the_cuvee():
    latest = {}
    for d in ST.latest_by_context().values():
        if (d.get('read') or {}).get('sha256') == SHA:
            latest[d['ctx']['target_vintage']] = d
    assert sorted(latest) == [1999, 2015], sorted(latest)
    assert latest[2015]['v'] == 8 and latest[2015]['document_is']['model_wines'] == [WINE]
    assert (latest[1999]['v'], latest[1999]['decision'], latest[1999]['code']) == (5, 'REFUSED', 'WRONG_VINTAGE')
    [u] = manifest('unchanged')
    assert u['decision'] == M6.row_key(latest[1999]) and u['latest'] == {'v': 5, 'decision': 'REFUSED', 'code': 'WRONG_VINTAGE'}
    # the track closed: no Cuvée sheet's latest answer accepts it as any wine
    left = [M6.row_key(d)[:90] for d in ST.latest_by_context().values()
            if d['decision'] == 'ACCEPTED' and SHEET.search(os.path.basename((d.get('read') or {}).get('path') or ''))]
    assert not left, left


@check
def t04_nothing_attributed_and_the_model_unchanged():
    [m] = manifest('correction')
    assert (m['result'], m['outcome'], m['wine'], m['attributed'], m['vintage_created']) == \
        ('APPLIED', 'CUVEE_MONGRAVEY', WINE, False, False) and m['vintage_stated'] == 2015 and not m['failures']
    assert m['linked_to'] == {'estate': 'es_00158', 'wine': GRAND_VIN}
    paths = ('data/model', 'data/app', 'data/sources.json', ':(glob)data/*.js', 'assets', 'index.html')
    assert not git('diff', '--stat', BEFORE, '--', *paths).strip() and not git('status', '--porcelain', '--', *paths).strip()
    # the model reads v4-v5 links only: the grand vin's links are as they were, and no observation uses the sheet
    links = [x for x in L.read_table('observation/evidence-links.jsonl') if x['artifact'] == ART]
    assert sorted(x['evidence_version'] for x in links) == [4, 4, 5, 5] and {x['wine'] for x in links} == {GRAND_VIN}
    assert not [o for o in L.read_table('observation/observations.jsonl') if ART in json.dumps(o)]


@check
def t05_the_other_audits_are_as_they_were():
    for f in ('data/audit/m3.6c-cuvee-mongravey-identity.jsonl', 'data/audit/m3.6d-cuvee-mongravey.jsonl',
              'data/audit/m3.6e-cuvee-historical-corrections.jsonl', 'data/audit/m3.6f-cuvee-vintages.jsonl',
              'data/audit/m3.6g-cuvee-acquisition.jsonl'):
        assert not git('diff', '--stat', BEFORE, '--', f).strip(), f
    [f] = [r for r in L.jsonl_lines(L.ROOT + 'data/audit/m3.6g-cuvee-acquisition.jsonl') if r['record'] == 'finding']
    assert f['artifact'] == ART and json.loads(manifest('correction')[0]['decision'])[-2] == 2015


@check
def t06_deterministic():
    for tool in ('m36h-apply.py', 'm36e-apply.py', 'm36g-acquisition.py'):
        out = CC.run([sys.executable, L.ROOT + 'tools/' + tool, '--check'], cwd=L.ROOT)
        assert out.returncode == 0, (tool, (out.stdout + out.stderr)[-400:])


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
