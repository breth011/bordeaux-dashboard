"""Phase M3.10A: the four Durfort-Vivens documents M3.9 accepted, registered as artifacts from an audited
external-acquisition manifest (tools/m310a-register.py; the migration's fourth artifact input).

    python tools/test-m310a.py

Read-only. Exactly M3.9's four accepted documents are registered, each from its held file (sha256, size, URL,
media type as M3.8 recorded them), as externally acquired - never as crawled; each is one artifact, minted by
sha256 as every other input's digest, with one URL placement in M3.2B's shape. Registration is not
attribution: no evidence decision, attribution, observation, reconciliation, value or gap moves; the discovery
outputs, the reader, the evidence store, the app and the M3.8/M3.9 audits are as they were.
"""
import hashlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_cache as CC  # noqa: E402
import historical_m2_scope as H  # noqa: E402
import migration_lib as L  # noqa: E402

BEFORE = 'de365eb'               # M3.9: the state M3.10A registers against
MANIFEST = L.ROOT + H.M310A_MANIFEST
READER = ('tools/m35_rubric.py', 'tools/web_evidence.py', 'tools/sheetreader.py', 'tools/read-fiches.py',
          'tools/m34a-mapping-audit.py', 'tools/model_schema.py', 'tools/evidence.py')
CHECKS = []


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode('utf-8')


def rows(record):
    return [r for r in L.jsonl_lines(MANIFEST) if r['record'] == record]


@check
def t01_exactly_m39s_four_accepted_documents():
    regs = rows('registration')
    m39 = [r for r in L.jsonl_lines(L.ROOT + 'data/audit/m3.9-evidence-review.jsonl')
           if r['record'] == 'review' and r['disposition'] == 'SAFE_TO_MAP']
    assert len(regs) == 4 and len(m39) == 4 and {r['estate'] for r in m39} == {'es_00263'}
    assert [g['candidate'] for g in regs] == ['m3.9:%d' % r['n'] for r in m39]
    assert [(g['url'], g['sha256']) for g in regs] == [(r['url'], r['sha256']) for r in m39]


@check
def t02_the_held_files_and_m38s_record():
    items = {r['n']: r for r in L.jsonl_lines(L.ROOT + 'data/audit/m3.8-acquisition-pilot.jsonl') if r['record'] == 'item'}
    for g in rows('registration'):
        it = items[g['m38_item']]
        data = open(L.ROOT + g['acquisition_path'], 'rb').read()
        assert hashlib.sha256(data).hexdigest() == g['sha256'] == it['sha256'], g['candidate']
        assert len(data) == g['bytes'] == it['bytes'] and g['url'] == it['url'] and g['fetched_at'] == it['at']
        assert g['media_type'] == it['content_type'] == 'application/pdf' and data[:5] == b'%PDF-'
        assert (g['acquired_by'], g['origin']) == ('M3.8', 'EXTERNAL_ACQUISITION')
        assert 'crawl' not in json.dumps(g).lower().replace('the discovery fetch', ''), g['candidate']


@check
def t03_one_artifact_each_minted_by_sha256():
    arts = L.read_table('identity/artifacts.jsonl')
    by_sha = {}
    for a in arts:
        if a.get('sha256'):
            by_sha.setdefault(a['sha256'], []).append(a)
    idmap = [r for r in L.read_table('identity/identity-map.jsonl') if r['namespace'] == 'artifact-by-sha256']
    res = {r['candidate']: r for r in rows('result')}
    for g in rows('registration'):
        [a] = by_sha[g['sha256']]
        assert a == res[g['candidate']]['artifact_row'] and a['id'] == res[g['candidate']]['artifact']
        assert (a['bytes'], a['media_type'], a['bytes_available'], a['extraction_status']) == \
            (g['bytes'], 'application/pdf', True, 'PENDING') and 'sha1' not in a
        [k] = [r for r in idmap if r['legacy_key'] == g['sha256']]
        assert k['stable_id'] == a['id'] and res[g['candidate']]['minted'] and not res[g['candidate']]['reused']
    old = {json.loads(x)['sha256'] for x in git('show', '%s:data/model/identity/artifacts.jsonl' % BEFORE).splitlines()
           if json.loads(x).get('sha256')}
    assert not old & {g['sha256'] for g in rows('registration')}, 'an artifact already held was minted again'
    assert len({a['id'] for a in arts}) == len(arts)


@check
def t04_the_url_placement_is_m32bs_shape():
    prov = {p['id']: p for p in L.read_table('cross/provenance.jsonl')}
    pls = [p for p in L.read_table('document/placements.jsonl')
           if (prov[p['provenance']].get('code_state') or {}).get('stream') == 'M3.10A']
    res = {r['candidate']: r for r in rows('result')}
    assert len(pls) == 4
    for g in rows('registration'):
        [p] = [p for p in pls if p['locator']['value'] == g['url']]
        assert p['locator'] == {'kind': 'URL', 'value': g['url']} and p['status'] == 'PRESENT'
        assert p['artifact'] == res[g['candidate']]['artifact'] and p['id'] == res[g['candidate']]['placement']
        assert p['source'] == g['source'] == 'sr_00239' and p['retrieval_method'] == g['retrieval_method']
        assert p['observed']['valid_from']['value'] == g['fetched_at'][:10]
        pv = prov[p['provenance']]
        assert pv['kind'] == 'DOCUMENT' and pv['actor'] == H.M310A_ACTOR and pv['artifact'] == p['artifact']
        assert pv['code_state']['origin'] == 'EXTERNAL_ACQUISITION' and pv['code_state']['acquired_by'] == 'M3.8'
    assert set(pls[0]) == {'id', 'locator', 'artifact', 'source', 'status', 'retrieval_method', 'observed', 'provenance'}


@check
def t05_registration_is_not_attribution():
    for r in rows('registration') + rows('result'):
        assert (r['evidence_decision'], r['attribution'], r['value_application']) == ('NONE', 'NONE', 'NONE')
    ids = {r['artifact'] for r in rows('result')}
    assert not [a for a in L.read_table('document/attributions.jsonl') if a.get('artifact') in ids]
    assert not [o for o in L.read_table('observation/observations.jsonl') if o.get('artifact') in ids]
    assert not [e for e in L.read_table('observation/evidence-links.jsonl') if e.get('artifact') in ids]
    names = {os.path.basename(g['url']) for g in rows('registration')}
    import evidence_store as ST
    assert ST.versions() == [1, 2, 3, 4, 5, 6, 7, 8] and ST.verify() == []
    assert not [d for d in ST.iter_rows(ST.versions()) if d.get('artifact') in names
                or (d.get('read') or {}).get('sha256') in {g['sha256'] for g in rows('registration')}]


@check
def t06_only_the_registration_moved_in_the_model():
    changed = {f[len('data/model/'):] for f in git('diff', '--name-only', BEFORE, '--', 'data/model').split()}
    assert changed <= set(H.M310A_FILES), sorted(changed - set(H.M310A_FILES))
    H.unchanged_but_m310a(BEFORE, 'data/model')
    for rel in ('canonical/values.jsonl', 'observation/observations.jsonl', 'reconciliation/reconciliations.jsonl',
                'document/attributions.jsonl', 'identity/wines.jsonl', 'identity/vintages.jsonl',
                'observation/evidence-links.jsonl', 'derived/vintage-documents.json', 'derived/source-documents.json'):
        assert rel not in changed, rel
    old, new = (json.loads(t) for t in (git('show', '%s:data/model/manifest.json' % BEFORE),
                                         open(L.MODEL + 'manifest.json', encoding='utf-8').read()))
    assert new['stats']['M6'][H.M310A_STAT] == 4
    assert new['stats']['M2'][H.M310A_ARTIFACT_STAT][1] == old['stats']['M2'][H.M310A_ARTIFACT_STAT][1] + 4


@check
def t07_discovery_evidence_gap_and_app_unchanged():
    paths = ('data/discovery', 'tools/discover.py', 'tools/discover_extract.py', 'data/evidence', 'data/app',
             'data/audit/data-gap-register.jsonl', 'data/sources.json', 'data/websites.js', ':(glob)data/*.js',
             'assets', 'index.html', 'data/audit/m3.8-acquisition-pilot.jsonl',
             'data/audit/m3.9-evidence-review.jsonl', 'data/audit/m3.7-source-confirmation.jsonl', *READER)
    assert not git('diff', '--stat', BEFORE, '--', *paths).strip()
    assert not git('status', '--porcelain', '--', *paths).strip()
    assert not git('ls-files', '--', 'sources/acquisition').strip(), 'acquired material is tracked'


@check
def t08_the_manifest_recomputes():
    out = CC.run([sys.executable, L.ROOT + 'tools/m310a-register.py', '--check'], cwd=L.ROOT)
    assert out.returncode == 0, (out.stdout + out.stderr)[-400:]


@check
def t09_the_model_rebuilds_from_scratch_and_with_its_registry():
    out = CC.run([sys.executable, L.ROOT + 'tools/migrate.py', '--check'], cwd=L.ROOT)
    assert out.returncode == 0, (out.stdout + out.stderr)[-400:]


@check
def t10_the_generated_views_are_current():
    for cmd in ('build-indexes.py', 'build-app-data.py', 'build-data-gap-register.py'):
        out = CC.run([sys.executable, L.ROOT + 'tools/' + cmd, '--check'], cwd=L.ROOT)
        assert out.returncode == 0, (cmd, (out.stdout + out.stderr)[-300:])


@check
def t11_the_earlier_guards_set_m310a_aside():
    H.model_changes_are_m2_only('345f892')           # M3.6E's commit: everything since is a known phase's
    H.unchanged_but_m36d('1a58c92', 'data/model', ':(exclude)data/model/manifest.json')


@check
def t12_no_fake_crawl_fact():
    regs = rows('registration')
    disc = {json.loads(l)['sha256'] for l in open(L.ROOT + 'data/discovery/artifacts.jsonl', encoding='utf-8')}
    assert not disc & {g['sha256'] for g in regs}, 'a registration is in the discovery manifest'
    import glob
    for p in glob.glob(L.ROOT + 'data/discovery/locations/*.jsonl'):
        t = open(p, encoding='utf-8').read()
        assert not [g for g in regs if g['sha256'] in t], p


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
