"""Phase M3.6G: the targeted acquisition for Cuvée Mongravey's open fields (tools/m36g-acquisition.py).

    python tools/test-m36g.py

Read-only. Every gap M3.6F left open has its row; every candidate quotes a line of a held document and is
rejected for a stated reason that is not only the identity gate; nothing from a vineyard section or a shop
page's template becomes the wine's; the four conflicting "24 mois d'élevage" figures are recorded and the
applied "18" stands; the fetched bytes are the lost bytes of artifacts the model already records; the model,
the evidence store (v1-v7) and the app are as M3.6F left them.
"""
import hashlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_cache as CC  # noqa: E402
import migration_lib as L  # noqa: E402

BEFORE = 'ddbe7db'               # M3.6F: the state M3.6G is audited against
AUDIT = L.ROOT + 'data/audit/m3.6g-cuvee-acquisition.jsonl'
M36F = L.ROOT + 'data/audit/m3.6f-cuvee-vintages.jsonl'
ACQ = L.ROOT + 'sources/acquisition/m3.6g/'
WINE = 'wn_00640'
SUBSTANTIVE = {'VINEYARD_SECTION', 'TEMPLATE', 'CONTRADICTED', 'QUALIFIED', 'QUALIFIED_IN_OTHER_LANGUAGE',
               'EARLIER_REVISION', 'NOT_A_VALUE'}
CHECKS = []


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode('utf-8')


def audit(record=None):
    return [r for r in L.jsonl_lines(AUDIT) if record is None or r['record'] == record]


def held(sha):
    for p in (L.ROOT + 'sources/discovery/extracted/%s.json' % sha, ACQ + 'extracted/%s.json' % sha):
        if os.path.exists(p):
            return json.load(open(p, encoding='utf-8'))
    raise AssertionError('no held text for %s' % sha)


@check
def t01_every_open_gap_of_m36f_has_its_row():
    want = set()
    for r in L.jsonl_lines(M36F):
        if r['record'] == 'withheld' and r['field'] not in ('production', 'window'):
            want.add((r['vintage'], r['field']))
        if r['record'] == 'value' and not r['applied']:
            want.add((r['vintage'], r['field']))
    got = {(g['vintage'], g['field']) for g in audit('gap')}
    assert got == want and len(got) == 49, sorted(want ^ got)


@check
def t02_nothing_was_accepted_and_every_gap_stays_open():
    assert not [c for c in audit('candidate') if c['decision'] in ('ACCEPTED', 'TO_RECONCILE')]
    assert all(g['status'] == 'UNRESOLVED' and g['accepted'] == 0 and g['acquisition'] for g in audit('gap'))
    [s] = audit('summary')
    assert (s['accepted'], s['resolved'], s['model_changes'], s['gaps']) == (0, 0, 0, 49), s


@check
def t03_every_candidate_quotes_a_line_of_a_held_document():
    docs = {}
    for d in audit('document'):
        docs[d['artifact'] or d['urls'][0]] = d
    for c in audit('candidate'):
        d = docs[c['source']]
        assert str(d['vintage']) == c['vintage'][-4:] and d['kind'] in ('TECHNICAL_SHEET', 'SHOP_PAGE'), c
        t = held(d['sha256'])
        if t.get('media') == 'html':
            line = t['blocks'][int(c['locus'][1:])]['text'].strip()
        else:
            p, l = c['locus'].split(':')
            line = t['pages'][int(p[1:]) - 1].splitlines()[int(l[1:]) - 1].strip()
        assert line == c['quote'], (c['source'], c['locus'], line, c['quote'])


@check
def t04_no_vineyard_or_template_statement_becomes_the_wines():
    for c in audit('candidate'):
        assert set(c['codes']) & SUBSTANTIVE, ('rejected by the gate alone', c)
        if c['field'] in ('blend', 'yld') and c['kind'] == 'TECHNICAL_SHEET':
            assert 'VINEYARD_SECTION' in c['codes'], c
        if c['kind'] == 'SHOP_PAGE':
            assert {'TEMPLATE', 'CONTRADICTED'} <= set(c['codes']), c
    # the shop pages' characteristics: one block per language on every target vintage's page (2010's pages,
    # outside the target, swap their languages and lay the text out otherwise)
    blocks = {}
    for d in audit('document'):
        if d['kind'] == 'SHOP_PAGE' and d['vintage'] in (2015, 2016, 2018, 2019, 2020, 2022):
            t = held(d['sha256'])
            text = [b['text'].strip() for b in t['blocks']]
            i = next(i for i, x in enumerate(text) if x in ('Caractéristiques', 'Characteristics'))
            blocks.setdefault(d['lang'], set()).add(tuple(text[i + 1:i + 6]))
    assert sorted(blocks) == ['en', 'fr'] and all(len(b) == 1 for b in blocks.values()), blocks


@check
def t05_the_conflicts_are_recorded_and_the_applied_value_stands():
    conf = [c for c in audit('candidate') if c.get('conflict')]
    assert sorted(c['vintage'][-4:] for c in conf) == ['2016', '2018', '2019', '2020'], conf
    for c in conf:
        assert c['field'] == 'months' and c['quote'].startswith('24 mois') and c['existing']['value'] == '18'
        assert c['decision'] == 'NOT_ENTERED' and 'EARLIER_REVISION' in c['codes'], c
    vals = {(v['subject'], v['field']): v['value'] for v in L.read_table('canonical/values.jsonl')
            if str(v['subject']).startswith('vt:%s:' % WINE)}
    assert {k: v for k, v in vals.items() if k[1] == 'months'} == \
        {('vt:%s:%s' % (WINE, y), 'months'): '18' for y in ('2016', '2018', '2019', '2020', '2022')}, vals
    assert not git('diff', '--stat', BEFORE, '--', M36F[len(L.ROOT):]).strip()


@check
def t06_the_fetched_bytes_are_known_artifacts_bytes():
    arts = {(a.get('sha1'), a.get('bytes')): a for a in L.read_table('identity/artifacts.jsonl')}
    fetched = audit('fetched')
    assert len(fetched) == 5 and all(f['url'].startswith('https://vignobles-bernaleau.com/wp-content/uploads/2023/09/')
                                     for f in fetched)
    for f in fetched:
        data = open(ACQ + 'blobs/%s.pdf' % f['sha256'], 'rb').read()
        assert hashlib.sha256(data).hexdigest() == f['sha256'] and len(data) == f['bytes']
        a = arts.get((hashlib.sha1(data).hexdigest(), len(data)))
        assert a and a.get('sha256') in (None, f['sha256']), ('a new document', f['url'])
    assert sorted(p['route'] for p in audit('probe')) == [1, 1, 2, 2, 2, 4]


@check
def t07_the_uncorrected_acceptance_is_reported_not_corrected():
    [f] = audit('finding')
    assert f['artifact'] == 'ar_010314' and f['asked'] == 'Château Mongravey, vintage 2015', f
    links = [l for l in L.read_table('observation/evidence-links.jsonl') if l['artifact'] == 'ar_010314']
    assert sorted(l['evidence_version'] for l in links) == [4, 4, 5, 5] and {l['wine'] for l in links} == {'wn_00158'}
    assert not [o for o in L.read_table('observation/observations.jsonl') if 'ar_010314' in json.dumps(o)]


@check
def t08_model_evidence_and_app_unchanged_since_m36f():
    paths = ('data/model', 'data/evidence', 'data/app', 'data/sources.json', ':(glob)data/*.js', 'assets', 'index.html')
    assert not git('diff', '--stat', BEFORE, '--', *paths).strip()
    assert not git('status', '--porcelain', '--', *paths).strip()


@check
def t09_deterministic():
    out = CC.run([sys.executable, L.ROOT + 'tools/m36g-acquisition.py', '--check'], cwd=L.ROOT)
    assert out.returncode == 0, (out.stdout + out.stderr)[-400:]


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
