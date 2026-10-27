"""Phase M3.8: the confirmed-source acquisition pilot (tools/m38-acquire.py, tools/m38-acquisition-pilot.py).

    python tools/test-m38.py

Read-only. The audit recomputes byte for byte; only M3.7's five gated relationships were targets and only their
hosts were asked; nothing was asked of a probable or legacy source; a held URL was not requested again and every
duplicate is a held artifact's bytes; blocked and failed URLs are recorded, never retried; identity comes from
the document's text, never its URL; the model, evidence store (v1-v8), gap register and app are as M3.7 left them.
"""
import collections
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_cache as CC  # noqa: E402
import migration_lib as L  # noqa: E402

BEFORE = 'd0a9756'               # M3.7: the state M3.8 acquires against
_s = importlib.util.spec_from_file_location('m38', L.ROOT + 'tools/m38-acquisition-pilot.py')
M = importlib.util.module_from_spec(_s)
_s.loader.exec_module(M)
A = M.A
HOSTS = {'neipperg.com', 'gc-lurton-estates.com', 'chateau-issan.com', 'chateaudemyrat.fr'}
CHECKS = []


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode('utf-8')


def audit(record=None):
    return [r for r in L.jsonl_lines(M.OUT) if record is None or r['record'] == record]


@check
def t01_deterministic():
    out = CC.run([sys.executable, L.ROOT + 'tools/m38-acquisition-pilot.py', '--check'], cwd=L.ROOT)
    assert out.returncode == 0, (out.stdout + out.stderr)[-400:]


@check
def t02_the_gate_is_m37s_first_five_confirmed():
    a = L.jsonl_lines(A.M37)
    rel = {r['id']: r for r in a if r['record'] == 'relationship'}
    rank = [r for r in a if r['record'] == 'ranking'][:5]
    got = [(rel[k['relationship']]['source_name'], rel[k['relationship']]['estate']) for k in rank]
    assert tuple(got) == A.GATE and all(rel[k['relationship']]['status'].startswith('CONFIRMED_') for k in rank)
    allowed = {k['relationship'] for k in rank}
    for i in audit('item'):
        assert set(i['listed_for']) <= allowed and set(i['eligible_relationships']) <= allowed, i['n']
        assert i['attributed_to'] in allowed | {None}


@check
def t03_no_probable_or_legacy_source_was_asked():
    for r in audit('request') + audit('item'):
        assert A.host(r['url']) in HOSTS, r['url']
    probable = set(A.PROBABLE)
    assert not [r for r in audit('request') if A.host(r['url']) in probable]
    # every target is one of M3.3's locators for a gated relationship, or Myrat's recorded block
    known = {u for u, _, _ in A.targets()}
    assert {i['url'] for i in audit('item')} == known and len(audit('item')) == len(known) == 126


@check
def t04_exactly_the_vocabulary():
    assert M.CLASSES == ('EXACT_ESTATE_WINE_VINTAGE', 'ESTATE_VINTAGE_ONLY', 'ESTATE_DOCUMENT_IDENTITY_UNCLEAR',
                         'NON_VINTAGE_DOCUMENT', 'DUPLICATE_ARTIFACT', 'REVISION_OF_EXISTING_ARTIFACT',
                         'BLOCKED_BY_ROBOTS', 'FETCH_FAILED', 'NOT_FOUND')
    items = audit('item')
    assert all(i['classification'] in M.CLASSES for i in items)
    [s] = audit('summary')
    assert s['by_classification'] == {k: sum(1 for i in items if i['classification'] == k) for k in M.CLASSES}
    assert s['model_changes'] == 0


@check
def t05_duplicates_are_held_bytes_and_held_urls_were_not_asked():
    H = M.Held()
    asked = collections.Counter(r['url'] for r in audit('request') if r['why'] == 'target')
    for i in audit('item'):
        if i['classification'] != 'DUPLICATE_ARTIFACT':
            continue
        if i['retrieval'] == 'NOT_REQUESTED_ALREADY_HELD':
            assert not asked[i['url']] and i['duplicate_of'], i['n']
        elif i['duplicate_of'].startswith('m3.8 item #'):
            # the same bytes under another known URL of this pilot: stored once, both URLs kept
            first = audit('item')[int(i['duplicate_of'].split('#')[1]) - 1]
            assert first['sha256'] == i['sha256'] and first['n'] < i['n'] and first['url'] != i['url'], i['n']
        else:
            assert H.sha.get(i['sha256']) == i['duplicate_of'], i['n']
    # no content stored twice: each acquired sha256 once per distinct artifact, and none of a held artifact
    # becomes a new one
    for i in audit('item'):
        if i['sha256'] and i['classification'] not in ('DUPLICATE_ARTIFACT',):
            assert not H.duplicate(i['sha256'], None, None), i['n']


@check
def t06_blocked_and_failed_are_recorded_never_retried():
    asked = collections.Counter(r['url'] for r in audit('request') if r['why'] == 'target')
    assert all(n == 1 for n in asked.values()), 'a URL asked twice'
    for i in audit('item'):
        c = i['classification']
        if c == 'BLOCKED_BY_ROBOTS':
            assert not asked[i['url']] or i['retrieval'] == 'ROBOTS_DISALLOW', i['n']
            assert i['retry'].startswith('no') and 'robots_allows_now' in i
        if c in ('FETCH_FAILED', 'NOT_FOUND'):
            assert asked[i['url']] == 1 and i['retry'] and i['retrieval'] != 'OK', i['n']
        if c == 'NOT_FOUND':
            assert i['status'] in (404, 410)
    assert sum(1 for i in audit('item') if i['classification'] == 'BLOCKED_BY_ROBOTS') == 5


@check
def t07_identity_is_the_documents_own_text():
    for i in audit('item'):
        d = i['identity']
        c = i['classification']
        if c in ('EXACT_ESTATE_WINE_VINTAGE', 'ESTATE_VINTAGE_ONLY'):
            assert d['estate'] and d['vintage'] and d['vintage_basis'], i['n']
            assert d['vintage_basis'].startswith(('statement', 'wine and year')), i['n']
            assert i['attributed_to'] and i['identity_basis'] == "the document's own text"
            text, _ = M.text_of(i['sha256'])
            assert str(d['vintage']) in text, ('the stated vintage is not in the text', i['n'])
        if c == 'EXACT_ESTATE_WINE_VINTAGE':
            assert d['wine'] in M.wines_of({d['estate']})[d['estate']].values()
        if c == 'ESTATE_VINTAGE_ONLY':
            assert d['wine'] is None
    # the URL is never evidence: La Mondotte's German and English sheets carry the vintage in their URL and
    # state no estate in their text, and stay unclear
    mondotte = [i for i in audit('item') if 'mondotte' in i['url'].lower() and re.search(r'(?:de|gb)\.pdf$', i['url'].lower())]
    assert len(mondotte) == 22 and all(i['classification'] == 'ESTATE_DOCUMENT_IDENTITY_UNCLEAR' for i in mondotte)
    assert all(i['identity']['vintage'] for i in mondotte), 'their text states the vintage'


@check
def t08_the_stored_bytes_are_what_the_audit_says():
    for i in audit('item'):
        if i['sha256'] and i['retrieval'] == 'OK':
            b = open(A.ACQ + 'blobs/' + i['sha256'], 'rb').read()
            assert hashlib.sha256(b).hexdigest() == i['sha256'] and len(b) == i['bytes'], i['n']
    assert not git('ls-files', '--', 'sources/acquisition').strip(), 'acquired material is committed'


@check
def t09_model_evidence_gap_and_app_unchanged():
    __import__('historical_m2_scope').unchanged_but_m310a(BEFORE, 'data/model')   # M3.10A, a later phase
    __import__('historical_m2_scope').evidence_unchanged_but_m310b(BEFORE)   # M3.10B's v9, a later phase
    paths = ('data/app', 'data/sources.json', 'data/websites.js', ':(glob)data/*.js',
             'assets', 'index.html', 'data/audit/data-gap-register.jsonl', 'data/audit/m3.7-source-confirmation.jsonl',
             'data/discovery')
    assert not git('diff', '--stat', BEFORE, '--', *paths).strip()
    assert not git('status', '--porcelain', '--', *paths).strip()
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
