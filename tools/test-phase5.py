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
    now = L.group_hashes(name)
    changed = sorted(f for f in set(b['files']) | set(now['files']) if b['files'].get(f) != now['files'].get(f))
    assert not changed, (name, changed[:5])


@check
def no_canonical_change():
    same_group('canonical')


@check
def no_evidence_change_no_v6():
    same_group('evidence')
    assert not os.path.exists(L.ROOT + 'data/evidence/decisions-v6.jsonl')


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
    assert not git('diff', '--stat', START, '--', 'data/model').strip(), 'data/model changed since Phase 4'


@check
def application_unchanged():
    assert not git('diff', '--stat', START, '--', 'index.html', 'assets', 'service-worker.js', 'data/*.js',
                   'data/sources.json').strip()


@check
def only_phase5_baseline_artifacts_changed():
    # M0 itself was measurement only: its commit touched nothing but its own paths.
    log = [l.split(' ', 1) for l in git('log', '--format=%H %s', START + '..HEAD').splitlines()]
    m0 = [h for h, s in log if s.startswith('Phase 5 M0')]
    assert len(m0) == 1, 'the M0 commit'
    changed = set(git('diff-tree', '--no-commit-id', '--name-only', '-r', m0[0]).split())
    assert all(f.startswith(OWN) for f in changed), sorted(f for f in changed if not f.startswith(OWN))
    # Later Phase 5 work may change tools, never data, the model or the application
    # (the hash checks above hold those; this names the paths).
    later = set(git('diff', '--name-only', START, 'HEAD').split()) | \
        set(l[3:] for l in git('status', '--porcelain', '--untracked-files=all').splitlines())
    banned = [f for f in later if (f.startswith('data/') and not f.startswith('data/performance/'))
              or f.startswith(('assets/', 'index.html', 'service-worker.js', 'sources/'))]
    assert not banned, sorted(banned)[:5]


WRITERS = ('tools/add-sheet.py', 'tools/harvest.py', 'tools/crawl-pages.py')


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
