"""Phase M3.7: source confirmation (tools/m37-source-confirmation.py).

    python tools/test-m37.py

Read-only. The audit recomputes byte for byte; its statuses are exactly the eight of the vocabulary and each
reviewed one follows from its elements by the one rule; every quote is a block of a page the repository
holds; every relationship is the model's own, once, in a fixed order; the model, the evidence store (v1-v8),
the earlier audits and the app are as M3.6H left them; the inspection was the narrow one recorded.
"""
import collections
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_cache as CC  # noqa: E402
import migration_lib as L  # noqa: E402

BEFORE = 'f879eda'               # M3.6H: the state M3.7 audits
AUDIT = L.ROOT + 'data/audit/m3.7-source-confirmation.jsonl'
_s = importlib.util.spec_from_file_location('m37', L.ROOT + 'tools/m37-source-confirmation.py')
M = importlib.util.module_from_spec(_s)
_s.loader.exec_module(M)
ORDER = ('scope', 'source', 'inspection', 'relationship', 'finding', 'conflict', 'ranking', 'summary')
CHECKS = []


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode('utf-8')


def audit(record=None):
    return [r for r in L.jsonl_lines(AUDIT) if record is None or r['record'] == record]


@check
def t01_deterministic():
    out = CC.run([sys.executable, L.ROOT + 'tools/m37-source-confirmation.py', '--check'], cwd=L.ROOT)
    assert out.returncode == 0, (out.stdout + out.stderr)[-400:]


@check
def t02_exactly_the_vocabulary():
    assert M.STATUSES == ('CONFIRMED_FIRST_PARTY', 'CONFIRMED_ESTATE_CONTROLLED', 'PROBABLE_FIRST_PARTY', 'THIRD_PARTY',
                          'SHARED_HOST_UNCONFIRMED', 'SOURCE_IDENTITY_UNCLEAR', 'SOURCE_NOT_RELEVANT', 'NOT_REVIEWED')
    [scope] = audit('scope')
    assert tuple(scope['statuses']) == M.STATUSES
    rel = audit('relationship')
    assert all(r['status'] in M.STATUSES for r in rel)
    [s] = audit('summary')
    assert tuple(s['by_status']) == tuple(sorted(M.STATUSES)) and \
        s['by_status'] == {k: sum(1 for r in rel if r['status'] == k) for k in M.STATUSES}, s
    assert s['model_changes'] == 0 and s['reviewed_sources'] == 21 and s['reviewed_relationships'] == 29


@check
def t03_each_status_follows_from_its_elements():
    shared = {s['source']: s['shared'] for s in audit('source')}
    for r in audit('relationship'):
        if r['status'] == 'NOT_REVIEWED':
            assert 'elements' not in r and (r['source_name'], r['estate']) not in M.REVIEW, r['id']
            continue
        assert M.status(r['elements'], shared[r['source']]) == r['status'], r['id']
        assert r['confidence'] == M.CONFIDENCE[r['status']]
        if r['status'] == 'CONFIRMED_FIRST_PARTY':
            assert r['elements']['publisher']['kind'] == 'ESTATE_COMPANY' and r['elements'].get('site'), r['id']
    # nothing confirmed by a name, a URL or a mention alone: a confirmation names a publisher or a stated link
    for r in audit('relationship'):
        if r['status'].startswith('CONFIRMED'):
            assert r['elements'].get('publisher') or r['elements'].get('link'), r['id']


@check
def t04_every_quote_is_a_held_block():
    n = 0
    for r in audit('relationship'):
        for k, e in (r.get('elements') or {}).items():
            if 'quote' not in e:
                continue
            path = (M.ACQ + 'extracted/%s.json' if e['held'] == 'm3.7' else M.DISC + '%s.json') % e['sha256']
            x = json.load(open(path, encoding='utf-8'))
            texts = [(x.get('title') or '').strip()] + [(b.get('text') or '').strip() for b in x.get('blocks') or []]
            assert e['quote'] in texts, (r['id'], k)
            n += 1
    assert n >= 45, n


@check
def t05_every_relationship_is_the_models_own_once():
    model = {r['id']: r for r in L.read_table('state/source-estate.jsonl')}
    rel = audit('relationship')
    assert len(rel) == len(model) == 409
    assert len({r['id'] for r in rel}) == len(rel) and len({(r['source'], r['estate']) for r in rel}) == len(rel)
    assert {r['recorded']['relationship'] for r in rel} == set(model)
    for r in rel:
        m = model[r['recorded']['relationship']]
        assert (m['source'], m['estate'], m['kind']) == (r['source'], r['estate'], r['recorded']['kind'])
    sources = {s['id'] for s in L.read_table('identity/sources.jsonl')}
    assert {r['source'] for r in rel} <= sources and {s['source'] for s in audit('source')} <= sources
    for c in audit('conflict'):
        assert c['relationship'] in model and c['action'] == 'none: preserved for review'


@check
def t06_stable_order():
    kinds = [r['record'] for r in audit()]
    assert kinds == sorted(kinds, key=ORDER.index), 'records out of order'
    rel = audit('relationship')
    assert [(r['source'], r['estate']) for r in rel] == sorted((r['source'], r['estate']) for r in rel)
    assert [r['rank'] for r in audit('ranking')] == list(range(1, len(audit('ranking')) + 1))
    assert [r['n'] for r in audit('inspection')] == list(range(1, len(audit('inspection')) + 1))
    by = collections.Counter(r['status'] for r in rel)
    ranked = {r['relationship'] for r in audit('ranking')}
    assert all(r['status'] in M.STATUSES[:3] and r['vintage_documents']['suitable'] for r in rel if r['id'] in ranked)
    assert by['NOT_REVIEWED'] == 380


@check
def t07_the_inspection_was_narrow():
    insp = audit('inspection')
    assert len(insp) == 32
    whys = collections.Counter(r['why'] for r in insp)
    assert set(whys) <= {'robots', 'home', 'legal notice', 'privacy policy (linked from home)',
                         'family page (linked from home)', 'legal notice (standard path; none linked)'}, whys
    for r in insp:
        if r.get('sha256'):
            b = open(M.ACQ + 'blobs/' + r['sha256'], 'rb').read()
            assert hashlib.sha256(b).hexdigest() == r['sha256'] and len(b) == r['bytes']
    assert not git('ls-files', '--', 'sources/acquisition').strip(), 'the inspected pages are committed'


@check
def t08_model_evidence_and_app_unchanged():
    __import__('historical_m2_scope').unchanged_but_m310a(BEFORE, 'data/model')   # M3.10A, a later phase
    __import__('historical_m2_scope').evidence_unchanged_but_m310b(BEFORE)   # M3.10B's v9, a later phase
    __import__('historical_m2_scope').register_changes_are_m34b_only(BEFORE)   # M3.10B's resolution, a later linking phase
    paths = ('data/app', 'data/sources.json', 'data/websites.js', ':(glob)data/*.js',
             'assets', 'index.html')
    assert not git('diff', '--stat', BEFORE, '--', *paths).strip()
    assert not git('status', '--porcelain', '--', *paths).strip()
    # the M3.6 evidence decisions and audits as M3.6H left them
    m36 = [p for p in git('ls-files', '--', 'data/audit').split() if '/m3.6' in p]
    assert len(m36) >= 12 and not git('diff', '--stat', BEFORE, '--', *m36).strip()
    import evidence_store as ST
    assert [v for v in ST.versions() if v != __import__('historical_m2_scope').M310B_EVIDENCE_VERSION] == [1, 2, 3, 4, 5, 6, 7, 8] and ST.verify() == []


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
