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
"""
import concurrent.futures
import glob
import os
import re
import subprocess
import sys
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


def main():
    a = sys.argv[1:]
    workers = int(a[a.index('--workers') + 1]) if '--workers' in a else 2
    names = suites('--reverse' in a)
    t0 = time.perf_counter()
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        for r in ex.map(run, names):
            results.append(r)
            print('%-4s %-20s %6.1fs  %d check(s)' % ('ok' if r['ok'] else 'FAIL', r['suite'],
                                                     r['seconds'], r['checks']), flush=True)
    failed = [r for r in results if not r['ok']]
    for r in failed:
        print('\n--- %s ---\n%s' % (r['suite'], '\n'.join(r['tail'])))
    print('\n%d suite(s), %d check(s), %s; %.1fs with %d worker(s)' % (
        len(results), sum(r['checks'] for r in results),
        'all pass' if not failed else '%d suite(s) FAIL' % len(failed),
        time.perf_counter() - t0, workers))
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
