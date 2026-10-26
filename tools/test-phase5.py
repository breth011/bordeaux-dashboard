"""Phase 5 M0: the baseline benchmark, checked.

    python tools/test-phase5.py

Reads only. Holds the benchmark output to its schema and its commit, the
report to its sections, and every protected group, the normalized model
and the application to their Phase 4 state.
"""
import collections
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import migration_lib as L  # noqa: E402

START = 'b1ce39b'
BENCH = L.ROOT + 'data/performance/benchmarks.jsonl'
INV = L.ROOT + 'data/performance/storage-inventory.json'
REPORT = L.ROOT + 'docs/PHASE-5-BASELINE-BENCHMARK.md'
# Phase 5's own paths: its tools, its measurements and its documents (the baseline
# report and the decision documents that follow from it).
OWN = ('tools/benchmark-phase5.py', 'tools/test-phase5.py', 'data/performance/', 'docs/PHASE-5-')
CHECKS = []


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode('utf-8')


_all = []


def all_rows():
    """Every run appended to the log (M0 and the re-measurements after it)."""
    if not _all:
        _all.extend(L.jsonl_lines(BENCH))
    return _all


def rows():
    """The M0 baseline run: the first run, made at the Phase 4 commit."""
    first = all_rows()[0]['run']
    return [r for r in all_rows() if r['run'] == first]


@check
def benchmark_script_exists_and_names_every_family():
    s = open(L.ROOT + 'tools/benchmark-phase5.py', encoding='utf-8').read()
    for fam in ('env', 'suite', 'startup', 'search', 'lookup', 'model', 'rebuild', 'storage',
                'duplicates', 'large'):
        assert "('%s', fam_%s)" % (fam, fam) in s, fam


@check
def benchmark_records_have_the_schema():
    need = {'benchmark_id', 'category', 'workload', 'commit', 'environment', 'cold_warm', 'iteration',
            'elapsed_ms', 'peak_memory_mb', 'input_counts', 'output_counts', 'free_disk_before_mb',
            'free_disk_after_mb', 'status', 'notes', 'runs_ms', 'min_ms', 'max_ms', 'run', 'timestamp'}
    assert rows()
    for r in all_rows():
        assert need <= set(r), (r['benchmark_id'], need - set(r))
        if r['runs_ms']:
            assert r['iteration'] == len(r['runs_ms'])
            assert r['min_ms'] <= r['elapsed_ms'] <= r['max_ms']


@check
def benchmark_records_identify_the_phase4_commit():
    assert {r['commit'] for r in rows()} == {START}
    env = [r for r in rows() if r['benchmark_id'] == 'env.machine'][0]['detail']
    assert env['commit'] == START
    assert set(env['dirty_files']) <= {f for f in env['dirty_files'] if f.startswith(OWN)}, env['dirty_files']


@check
def later_runs_name_real_commits_and_pass():
    runs = collections.OrderedDict()
    for r in all_rows():
        runs.setdefault(r['run'], set()).add(r['commit'])
    first = next(iter(runs))
    for run, commits in runs.items():
        assert len(commits) == 1, (run, commits)
        c = next(iter(commits))
        assert subprocess.call(['git', 'merge-base', '--is-ancestor', START, c], cwd=L.ROOT) == 0, (run, c)
        if run != first:
            assert c != START, 'a re-measurement attributed to the baseline commit'
    assert not [r for r in all_rows() if r['status'] != 'OK']


@check
def every_benchmark_family_measured():
    ids = {r['benchmark_id'] for r in rows()}
    for want in ('env.machine', 'suite.full.cold', 'suite.full.warm', 'startup.browser-process',
                 'startup.app-ready.cold', 'startup.app-ready.warm', 'startup.data-loading.cold',
                 'rebuild.full', 'storage.walk', 'large.cases', 'large.estate-every-record.model',
                 'model.read.all-tables', 'model.read.projection', 'run.start', 'run.end',
                 'duplicates.legacy-and-blob-store', 'lookup.model.load-structures'):
        assert want in ids, want
    for kind in ('estate', 'wine', 'estate-wines', 'wine-estates', 'wine-vintage', 'estate-vintage',
                 'document', 'field'):
        assert any(i.startswith('lookup.app.%s.' % kind) for i in ids), kind
    search = [r for r in rows() if r['category'] == 'search']
    assert len(search) == 8 and all(r['iteration'] >= 5 for r in search)
    assert not [r for r in rows() if r['status'] not in ('OK',)], \
        [(r['benchmark_id'], r['status']) for r in rows() if r['status'] != 'OK']


@check
def timings_repeated_and_full_suite_green():
    for r in rows():
        if r['category'] in ('startup', 'lookup', 'model', 'search') and r['runs_ms']:
            if not r['benchmark_id'].startswith('lookup.model.load'):
                assert r['iteration'] >= 3, r['benchmark_id']
    for label in ('cold', 'warm'):
        s = [r for r in rows() if r['benchmark_id'] == 'suite.full.' + label][0]
        assert s['output_counts']['failures'] == 0 and s['input_counts']['suites'] == 21
    rb = [r for r in rows() if r['benchmark_id'] == 'rebuild.full'][0]
    assert rb['output_counts']['byte_identical'] is True


@check
def storage_inventory_has_every_category():
    inv = json.load(open(INV, encoding='utf-8'))
    cats = inv['categories']
    assert {'authoritative/protected', 'raw/source', 'derived or potentially derived',
            'repository overhead'} <= set(cats)
    for sub in ('canonical data', 'evidence v1-v5', 'discovery data', 'normalized model', 'scope data',
                'proposal and audit records (phase records)'):
        assert sub in cats['authoritative/protected'], sub
    assert '.git' in cats['repository overhead']
    assert any('sheets' in k for k in cats['raw/source'])
    for c in cats.values():
        for v in c.values():
            assert v['allocated_bytes'] >= v['bytes'] and v['files'] > 0


@check
def disk_pressure_recorded():
    d = [r for r in rows() if r['free_disk_before_mb'] is not None]
    assert d and all(r['free_disk_before_mb'] >= 6 * 1024 for r in d)
    assert not [r for r in rows() if r['status'] == 'STOPPED']


@check
def report_has_its_eighteen_sections():
    s = open(REPORT, encoding='utf-8').read()
    heads = [int(n) for n in re.findall(r'^## (\d+)\. ', s, re.M)]
    assert heads == list(range(1, 19)), heads
    assert START in s
    assert 'SAFE — PHASE 5 BASELINE ESTABLISHED' in s
    assert re.search(r'No optimization', s, re.I)


def same_group(name):
    b = json.load(open(L.MODEL + 'baseline.json', encoding='utf-8'))['groups'][name]
    # M3.6B's evidence version 6 named and set aside; v1-v5 and every other group file by file
    now = __import__('historical_m2_scope').protected_group(name)
    changed = sorted(f for f in set(b['files']) | set(now['files']) if b['files'].get(f) != now['files'].get(f))
    assert not changed, (name, changed[:5])


@check
def no_canonical_change():
    same_group('canonical')


@check
def no_evidence_change_no_v6():
    same_group('evidence')
    # a v6 file only as M3.6B's decisions, verified to be exactly those (historical_m2_scope)
    assert not os.path.exists(L.ROOT + 'data/evidence/decisions-v6.jsonl') or \
        __import__('historical_m2_scope').m36b_evidence_rows()


@check
def no_discovery_change():
    same_group('discovery')


@check
def no_phase2_proposal_applied_and_records_unchanged():
    same_group('phase_records')
    for g in ('scope', 'review', 'phase34_model'):
        same_group(g)
    assert not [w for w in L.jsonl_lines(L.MODEL + 'identity/wines.jsonl') if w['id'].startswith('wn_P')]


@check
def normalized_model_byte_identical():
    man = json.load(open(L.MODEL + 'manifest.json', encoding='utf-8'))
    import hashlib
    for rel, info in man['files'].items():
        assert hashlib.sha256(open(L.MODEL + rel, 'rb').read()).hexdigest() == info['sha256'], rel
    # Historical M2 adds document dates to three model files, additions only; nothing else changes.
    import historical_m2_scope
    historical_m2_scope.model_changes_are_m2_only(START)


@check
def application_unchanged():
    # The legacy data is untouched, and no Phase 5 commit touched the code. index.html
    # and the service worker differ from Phase 4 by exactly the source switch (the 23
    # contract paths moved to data/app/, the cache name bumped once per change) and by
    # the one generated file later phases added, data/app/figure-sources.js (Phase 6.1).
    assert not git('diff', '--stat', START, '--', ':(glob)data/*.js', 'data/sources.json').strip()
    for h, subject in [l.split(' ', 1) for l in git('log', '--format=%H %s', START + '..HEAD').splitlines()]:
        if subject.startswith('Phase 5'):
            touched = git('diff-tree', '--no-commit-id', '--name-only', '-r', h).split()
            assert not [f for f in touched if f.startswith('assets/')], (subject, touched)
    src = load_tool('app-source.py')
    idx = open(L.ROOT + 'index.html', encoding='utf-8').read()
    sw = open(L.ROOT + 'service-worker.js', encoding='utf-8').read()
    for extra in ('figure-sources.js', 'second-status.js', 'source-facts.js',   # Phase 6.1, 6.3, 6.5
                  'wine-established.js'):                                     # Phase 6.7
        idx = idx.replace('<script src="data/app/%s"></script>\n' % extra, '')
        sw = sw.replace("  './data/app/%s',\n" % extra, '')
    for f in src.CONTRACT:
        idx = idx.replace('"data/app/%s"' % f, '"data/%s"' % f)
        sw = sw.replace("'./data/app/%s'" % f, "'./data/%s'" % f)
    old_idx = git('show', START + ':index.html')
    old_sw = git('show', START + ':service-worker.js')
    assert idx == old_idx, 'index.html changed beyond the switch'
    n0 = int(src.CACHE_RE.search(old_sw).group(1))
    n1 = int(src.CACHE_RE.search(sw).group(1))
    assert n1 > n0
    assert src.CACHE_RE.sub('', sw) == src.CACHE_RE.sub('', old_sw), \
        'service-worker.js changed beyond the switch'


def load_tool(name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name.replace('-', '_')[:-3], L.ROOT + 'tools/' + name)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@check
def only_phase5_baseline_artifacts_changed():
    # M0 itself was measurement only: its commit touched nothing but its own paths.
    log = [l.split(' ', 1) for l in git('log', '--format=%H %s', START + '..HEAD').splitlines()]
    m0 = [h for h, s in log if s.startswith('Phase 5 M0')]
    assert len(m0) == 1, 'the M0 commit'
    changed = set(git('diff-tree', '--no-commit-id', '--name-only', '-r', m0[0]).split())
    assert all(f.startswith(OWN) for f in changed), sorted(f for f in changed if not f.startswith(OWN))
    # Later Phase 5 work changed tools, never data, the model or the application code
    # (the hash checks above hold those; this names the paths). The source switch adds
    # data/app/ (generated) and rewrites index.html and the service worker, which
    # application_unchanged holds to exactly that. Later phases are their own tests'.
    later = set()
    for h, subject in log:
        if subject.startswith('Phase 5'):
            later |= set(git('diff-tree', '--no-commit-id', '--name-only', '-r', h).split())
    banned = [f for f in later if (f.startswith('data/') and not f.startswith(('data/performance/', 'data/app/')))
              or f.startswith(('assets/', 'sources/'))]
    assert not banned, sorted(banned)[:5]


WRITERS = ('tools/add-sheet.py', 'tools/harvest.py', 'tools/crawl-pages.py')
# What the application gained after Phase 5, named by tools/app-reference.py: each
# figure's own source (Phase 6.1), the second-wine status (Phase 6.3), and the source
# facts and corrected provenance wording (Phase 6.5). Nothing else may differ from the
# control.
PHASE61 = {'EXPECTED: PROVENANCE PRESENTATION', 'EXPECTED: ADDED FIGURE PROVENANCE (Phase 6.1)',
           'EXPECTED: SECOND-WINE STATUS PRESENTATION',
           'EXPECTED: PROVENANCE AND SECOND-WINE STATUS PRESENTATION',
           'EXPECTED: ADDED SECOND-WINE STATUS (Phase 6.3)',
           'EXPECTED: ADDED SOURCE FACTS (Phase 6.5)',
           'EXPECTED: PROVENANCE WORDING PRESENTATION',
           'EXPECTED: PROVENANCE AND PROVENANCE WORDING PRESENTATION',
           # Phase 6.7: the block of what is established about each wine, and its file
           'EXPECTED: ADDED WINE ESTABLISHED FACTS (Phase 6.7)',
           'EXPECTED: ESTABLISHED WINE FACTS PRESENTATION',
           'EXPECTED: PROVENANCE AND ESTABLISHED WINE FACTS PRESENTATION',
           'EXPECTED: PROVENANCE WORDING AND ESTABLISHED WINE FACTS PRESENTATION',
           'EXPECTED: PROVENANCE AND PROVENANCE WORDING AND ESTABLISHED WINE FACTS PRESENTATION',
           'EXPECTED: PROVENANCE AND SECOND-WINE STATUS AND ESTABLISHED WINE FACTS PRESENTATION',
           'EXPECTED: SECOND-WINE STATUS AND ESTABLISHED WINE FACTS PRESENTATION',
           # Phase 6.9: the vintage list heading, with the presentations above
           'EXPECTED: PROVENANCE WORDING AND ESTABLISHED WINE FACTS AND VINTAGE LIST HEADING PRESENTATION',
           'EXPECTED: PROVENANCE AND PROVENANCE WORDING AND ESTABLISHED WINE FACTS AND VINTAGE LIST HEADING PRESENTATION',
           'EXPECTED: PROVENANCE AND ESTABLISHED WINE FACTS AND VINTAGE LIST HEADING PRESENTATION',
           'EXPECTED: ESTABLISHED WINE FACTS AND VINTAGE LIST HEADING PRESENTATION',
           'EXPECTED: PROVENANCE WORDING AND VINTAGE LIST HEADING PRESENTATION',
           'EXPECTED: PROVENANCE AND SECOND-WINE STATUS AND ESTABLISHED WINE FACTS AND VINTAGE LIST HEADING PRESENTATION'}


@check
def c3_writers_into_sources_never_write_through_a_link():
    # A write into an existing file of sources/ would change every hard-linked
    # twin; each writer removes the file first, so the write makes a new one.
    n = 0
    for t in WRITERS:
        lines = open(L.ROOT + t, encoding='utf-8').read().split('\n')
        for i, l in enumerate(lines):
            m = re.search(r"open\((folder \+ name|path), '(?:w|wb)'", l)
            if m:
                n += 1
                guard = '\n'.join(lines[max(0, i - 2):i])
                assert 'os.remove(%s)' % m.group(1) in guard, '%s:%d writes without removing' % (t, i + 1)
    assert n == 5, n


@check
def c3_linked_paths_hold_their_own_bytes():
    j = L.ROOT + 'sources/.link-journal.jsonl'
    if not os.path.exists(j):
        return              # the raw store is local; another checkout has no links
    import hashlib
    entries = L.jsonl_lines(j)
    for e in entries:
        p, k = L.ROOT + e['path'], L.ROOT + e['keeper']
        sp, sk = os.stat(p), os.stat(k)
        assert (sp.st_dev, sp.st_ino) == (sk.st_dev, sk.st_ino), 'no longer linked: ' + e['path']
    for e in entries[::max(1, len(entries) // 40)]:
        h = hashlib.sha256(open(L.ROOT + e['path'], 'rb').read()).hexdigest()
        assert h == e['sha256'], 'bytes changed: ' + e['path']


# Two raw files whose bytes match no version the manifest records (found in C3).
# Pinned to preserve them, not to vouch for them: nothing reconciles, corrects or
# promotes them. If a hash changes, STOP; the expected value may only change in a
# separately documented data-integrity decision.
ANOMALIES = {
    'sources/fiches/domaine-de-chevalier/2020-rouge-domaine-de-chevalier-francais.pdf':
        (394634, '0c1a54293689b223674fb4f109d9797cd613fbb081eaf49f5febf38789139896'),
    'sources/fiches/valandraud/VIRGINIE-DE-VALANDRAUD.pdf':
        (135273, '57f351bc7e376c2f6ae42b2169ad8a889a41c1cf557ad6a4909863893a65bdc4'),
}


@check
def known_raw_file_anomalies_preserved():
    import hashlib
    for rel, (size, sha) in ANOMALIES.items():
        p = L.ROOT + rel
        assert os.path.isfile(p), 'missing: ' + rel
        b = open(p, 'rb').read()
        assert len(b) == size and hashlib.sha256(b).hexdigest() == sha, 'CHANGED: ' + rel
    # still anomalies: the manifest's digest for each path is not the file's
    sheets = {(r['folder'], r['file']): r['sha1'] for r in L.sources_rows()['sheets']}
    for rel in ANOMALIES:
        folder, file = rel[len('sources/fiches/'):].rsplit('/', 1)
        b = open(L.ROOT + rel, 'rb').read()
        assert sheets[(folder, file)] != hashlib.sha1(b).hexdigest(), 'no longer an anomaly: ' + rel


# ---------------------------------------------------------------- the application source switch

@check
def switch_app_reads_generated_model_output():
    src = load_tool('app-source.py')
    assert src.state() == 'model', src.state()
    bad = load_tool('build-app-data.py')
    files = bad.render()
    for f, b in files.items():
        assert open(L.ROOT + 'data/app/' + f, 'rb').read() == b, 'data/app/%s is not the model' % f
    assert sorted(os.listdir(L.ROOT + 'data/app')) == sorted(files), 'data/app holds more than the contract'


@check
def switch_app_reads_no_prohibited_input():
    src = load_tool('app-source.py')
    idx = open(L.ROOT + 'index.html', encoding='utf-8').read()
    sw = open(L.ROOT + 'service-worker.js', encoding='utf-8').read()
    for f in src.CONTRACT:
        assert '"data/%s"' % f not in idx and "'./data/%s'" % f not in sw, 'still loads legacy data/' + f
    ab = load_tool('app-boundary.py')
    r = ab.build()
    assert not r['forbidden'], r['forbidden']
    loads = set(r['loads'])
    allowed_legacy = {'data/%s' % f for f in os.listdir(L.ROOT + 'data')
                      if f.endswith('.js') and f not in src.CONTRACT}
    for p in loads:
        assert p.startswith(('data/app/', 'assets/')) or p in allowed_legacy, p


@check
def switch_no_runtime_migration():
    # The page loads only assets/*.js and data files; none of them reaches the
    # migration, the evidence, the discovery corpus, the raw store or the tools.
    idx = open(L.ROOT + 'index.html', encoding='utf-8').read()
    srcs = re.findall(r'<script[^>]*src="([^"]+)"', idx)
    assert srcs and all(s.startswith(('assets/', 'data/')) for s in srcs), srcs
    banned = ('tools/', 'data/model', 'data/evidence', 'data/discovery', 'sources/', 'sources.json',
              'migrate', 'model_reader', 'evidence_store')
    for f in [L.ROOT + 'assets/' + x for x in os.listdir(L.ROOT + 'assets') if x.endswith('.js')] + \
            [L.ROOT + 'service-worker.js']:
        text = open(f, encoding='utf-8').read()
        # code, not prose: block comments and whole-line // comments removed
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
        text = '\n'.join(l for l in text.split('\n') if not l.lstrip().startswith('//'))
        hit = [b for b in banned if b in text]
        assert not hit, (f, hit)
    for f in os.listdir(L.ROOT + 'data/app'):
        lines = open(L.ROOT + 'data/app/' + f, encoding='utf-8').read().split('\n')
        code = [l for l in lines[2:] if l.strip()]
        assert code and all(l.startswith('window.BDX_') for l in code), f


@check
def switch_outputs_agree_with_the_control():
    ar = load_tool('app-reference.py')
    ref = json.load(open(ar.FIXTURE, encoding='utf-8'))
    now = ar.capture()
    r = ar.compare(ref, now)
    assert not r['unexplained'], r['unexplained'][:5]
    assert not now['health'], now['health']
    assert all(u.startswith('data/app/') or u.split('/')[-1] not in load_tool('app-source.py').CONTRACT
               for u in now['data_requests']), now['data_requests']
    # every difference is the accepted presentation order (Phase 4 M8; backlog)
    assert set(r['summary']) <= {'IDENTICAL', 'EXPECTED: PRESENTATION ORDER'} | PHASE61, r['summary']
    assert r['summary']['IDENTICAL'] >= 10700


@check
def switch_rollback_restores_the_legacy_source():
    import shutil
    import tempfile
    before = {g: L.group_hashes(g)['digest'] for g in L.GROUPS}
    src = load_tool('app-source.py')
    ar = load_tool('app-reference.py')
    ref = json.load(open(ar.FIXTURE, encoding='utf-8'))
    site = tempfile.mkdtemp(prefix='bdx-rollback-site-')
    try:
        for f in ('index.html', 'service-worker.js', 'manifest.webmanifest'):
            shutil.copyfile(L.ROOT + f, os.path.join(site, f))
        shutil.copytree(L.ROOT + 'assets', os.path.join(site, 'assets'))
        os.makedirs(os.path.join(site, 'data', 'app'))
        for f in os.listdir(L.ROOT + 'data'):
            if f.endswith('.js'):
                shutil.copyfile(L.ROOT + 'data/' + f, os.path.join(site, 'data', f))
        for f in os.listdir(L.ROOT + 'data/app'):
            shutil.copyfile(L.ROOT + 'data/app/' + f, os.path.join(site, 'data', 'app', f))
        root = site.replace('\\', '/') + '/'
        assert src.state(root) == 'model'
        assert src.switch('legacy', root) and src.state(root) == 'legacy'
        back = ar.compare(ref, ar.capture(root))
        # back on legacy data: no reordering at all; only Phase 6.1's presentation
        assert set(back['summary']) <= {'IDENTICAL'} | PHASE61, back['summary']
        assert not back['unexplained']
        assert src.switch('model', root) and src.state(root) == 'model'
        again = ar.compare(ref, ar.capture(root))
        assert not again['unexplained'], again['unexplained'][:3]
    finally:
        shutil.rmtree(site, ignore_errors=True)
    after = {g: L.group_hashes(g)['digest'] for g in L.GROUPS}
    assert before == after, 'a protected group changed during rollback'
    assert os.path.isdir(L.MODEL + 'identity'), 'the model must survive a rollback'


@check
def switch_dual_read_still_passes():
    d = load_tool('dual-read.py')
    r = d.build()
    assert r['pass'], (r['page_path']['disagreements'][:3], r['query_disagreements'][:3])


def main():
    fails = 0
    for f in CHECKS:
        try:
            f()
            print('ok   %s' % f.__name__)
        except Exception as ex:
            fails += 1
            print('FAIL %s: %s' % (f.__name__, str(ex)[:300]))
    print('%d check(s), %s' % (len(CHECKS), 'all pass' if not fails else '%d FAIL' % fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
