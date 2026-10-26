"""Run every test suite (tools/test-*.py), each in its own process.

    python tools/run-tests.py                 2 suites at a time (the recommended setting)
    python tools/run-tests.py --workers 1     one after another (the reference run)
    python tools/run-tests.py --reverse       in reverse order (an order-independence check)

Each suite is a separate Python process, exactly as when it is run by hand, so no state
is shared between suites (Phase 6.6A showed they are independent and order-free). Two
workers is the measured choice (Phase 6.6C, docs/PHASE-6.6-PERFORMANCE-OPTIMIZATION.md):
about a third off the wall clock, with stable times and a safe memory margin. Three
saved little more and varied by 23 s between runs; four left 8 MB of memory free.

The longest suites start first so that two workers finish together. Exit status 1 if
any suite fails; its last lines are printed.

Shared checks. The suites of one run share a cache of --check results (tools/check_cache.py):
a check one suite has run is not rebuilt by the next, as long as nothing in the repository has
changed. The cache lives only for the run.

    python tools/run-tests.py --no-cache        every suite runs every check itself

Performance check. After a run in which every suite passes, the wall time is compared with a
fixed baseline for the worker count. More than 10 % slower is a performance regression: the
suites that grew most are printed, with any suites added or removed, and the exit status is 2.
The baseline does not follow the runs: several changes each under 10 % still add up against it,
and running again does not accept a regression. It moves only when asked:

    python tools/run-tests.py --set-baseline    this run, if every suite passes, is the baseline

(after a deliberate speed-up, or a new suite whose cost is accepted). The first passing run at
a worker count with no baseline sets it. Times are kept locally in reports/suite-runtime.json
(gitignored: they belong to the machine, not to the repository).

    python tools/run-tests.py --no-perf-check   run and record, without comparing
"""
import concurrent.futures
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
# The longest suites, from the Phase 6.6B profile; started first so the workers end together.
LONG = ['test-phase63.py', 'test-phase4.py', 'test-phase5.py', 'test-phase65.py', 'test-phase61.py',
        'test-phase33.py']


def suites(reverse=False):
    names = sorted(os.path.basename(p) for p in glob.glob(os.path.join(TOOLS, 'test-*.py')))
    if reverse:
        return names[::-1]
    return [s for s in LONG if s in names] + [s for s in names if s not in LONG]


def run(name):
    t = time.perf_counter()
    r = subprocess.run([sys.executable, os.path.join(TOOLS, name)], cwd=ROOT, capture_output=True)
    out = r.stdout.decode('utf-8', 'replace') + r.stderr.decode('utf-8', 'replace')
    m = re.search(r'(\d+) check\(s\), (all pass|\d+ FAIL\w*)', out)
    if m:
        checks, ok = int(m.group(1)), m.group(2) == 'all pass'
    else:
        # test-reader.py reports "all pass" without a count; it is counted as one check.
        checks, ok = 1, bool(re.search(r'(?m)^all pass\s*$', out))
    return {'suite': name, 'ok': ok and r.returncode == 0, 'checks': checks,
            'seconds': time.perf_counter() - t, 'tail': out.strip().splitlines()[-6:]}


RUNTIME_LOG = os.path.join(ROOT, 'reports', 'suite-runtime.json')
LIMIT = 0.10                     # more than 10 % slower than the baseline is a regression
HISTORY = 20


def compare(prev, now, limit=LIMIT):
    """None when `now` is within `limit` of the baseline `prev` (or there is none); otherwise what
    grew. prev and now: {'seconds', 'suites': {name: seconds}, 'checks'}."""
    if not prev or not prev.get('seconds'):
        return None
    growth = now['seconds'] / prev['seconds'] - 1
    if growth <= limit + 1e-9:          # 330 / 300 - 1 is 0.10000000000000009: exactly 10 % is within
        return None
    old, new = prev.get('suites', {}), now.get('suites', {})
    grown = sorted(((new[s] - old[s], s) for s in new if s in old), reverse=True)[:5]
    return {'growth': growth, 'before': prev['seconds'], 'after': now['seconds'],
            'grown': [(s, old[s], new[s]) for d, s in grown if d > 0],
            'added': sorted(set(new) - set(old)), 'removed': sorted(set(old) - set(new)),
            'checks': (prev.get('checks'), now.get('checks')), 'reference_at': prev.get('at')}


def load_log(path=None):
    try:
        with open(path or RUNTIME_LOG, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def baseline(log, workers):
    return log.get('baseline', {}).get(str(workers))


def record(log, workers, run, path=None, set_baseline=False):
    """The run is kept as the last for its worker count, with a short history beside it. It becomes
    the baseline only when asked, or when that worker count has none."""
    path = path or RUNTIME_LOG
    key = str(workers)
    log.setdefault('last', {})[key] = run
    if set_baseline or not baseline(log, workers):
        log.setdefault('baseline', {})[key] = run
    log['history'] = (log.get('history', []) + [dict(run, workers=workers, suites=None)])[-HISTORY:]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(log, f, indent=1, sort_keys=True)
    for attempt in range(20):
        try:
            os.replace(path + '.tmp', path)
            return
        except PermissionError:          # Windows: an indexer or scanner briefly holds a new file
            if attempt == 19:
                raise
            time.sleep(0.1)


def describe(reg, workers):
    lines = ['PERFORMANCE REGRESSION: the full suite took %.1fs, %.0f %% slower than the baseline '
             '(%.1fs, set %s) with %d worker(s); the limit is %.0f %%.' % (
                 reg['after'], reg['growth'] * 100, reg['before'], reg['reference_at'] or '?', workers, LIMIT * 100)]
    if reg['added'] or reg['removed']:
        lines.append('  suites added: %s; removed: %s' % (
            ', '.join(reg['added']) or 'none', ', '.join(reg['removed']) or 'none'))
    lines.append('  running again does not accept it; if the cost is deliberate: run-tests.py --set-baseline')
    for s, a, b in reg['grown']:
        lines.append('  %-28s %6.1fs -> %6.1fs (+%.1fs)' % (s, a, b, b - a))
    lines.append('  checks: %s -> %s' % reg['checks'])
    return '\n'.join(lines)


def main():
    a = sys.argv[1:]
    workers = int(a[a.index('--workers') + 1]) if '--workers' in a else 2
    names = suites('--reverse' in a)
    t0 = time.perf_counter()
    results = []
    cache = None if '--no-cache' in a else tempfile.mkdtemp(prefix='bdx-check-cache-')
    if cache:
        os.environ['BDX_CHECK_CACHE'] = cache            # the suites inherit it (tools/check_cache.py)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
            for r in ex.map(run, names):
                results.append(r)
                print('%-4s %-20s %6.1fs  %d check(s)' % ('ok' if r['ok'] else 'FAIL', r['suite'],
                                                         r['seconds'], r['checks']), flush=True)
    finally:
        if cache:
            os.environ.pop('BDX_CHECK_CACHE', None)
            shutil.rmtree(cache, ignore_errors=True)
    failed = [r for r in results if not r['ok']]
    for r in failed:
        print('\n--- %s ---\n%s' % (r['suite'], '\n'.join(r['tail'])))
    total = time.perf_counter() - t0
    print('\n%d suite(s), %d check(s), %s; %.1fs with %d worker(s)' % (
        len(results), sum(r['checks'] for r in results),
        'all pass' if not failed else '%d suite(s) FAIL' % len(failed), total, workers))
    if failed:
        sys.exit(1)                       # a failing run's time says nothing; it is not recorded
    this_run = {'seconds': round(total, 1), 'checks': sum(r['checks'] for r in results),
                'suites': {r['suite']: round(r['seconds'], 1) for r in results},
                'at': time.strftime('%Y-%m-%d %H:%M')}
    log = load_log()
    setting = '--set-baseline' in a
    reg = None if '--no-perf-check' in a or setting else compare(baseline(log, workers), this_run)
    record(log, workers, this_run, set_baseline=setting)
    if setting:
        print('baseline for %d worker(s) set: %.1fs' % (workers, this_run['seconds']))
    if reg:
        print('\n' + describe(reg, workers))
        sys.exit(2)
    sys.exit(0)


if __name__ == '__main__':
    main()
