"""The test runner's performance check (tools/run-tests.py).

    python tools/test-run-tests.py

Read-only, fast: exercises the comparison and the recording on runs built here, in a temporary
file; the suites are not run. A full run more than 10 % slower than the baseline at the same
worker count is a regression (exit status 2); the baseline moves only with --set-baseline; a
failing run is neither compared nor recorded.
"""
import importlib.util
import os
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('run_tests', os.path.join(TOOLS, 'run-tests.py'))
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)
CHECKS = []


def check(f):
    CHECKS.append(f)
    return f


def run(seconds, suites=None, checks=800):
    return {'seconds': seconds, 'checks': checks, 'at': '2026-10-25 12:00',
            'suites': suites or {'test-a.py': seconds * 0.6, 'test-b.py': seconds * 0.4}}


@check
def within_ten_percent_is_not_a_regression():
    assert R.compare(run(300), run(330)) is None                 # exactly 10 %
    assert R.compare(run(300), run(250)) is None                 # faster
    assert R.compare(None, run(999)) is None                     # no reference yet


@check
def more_than_ten_percent_is_a_regression():
    reg = R.compare(run(300), run(331))
    assert reg and abs(reg['growth'] - 31 / 300) < 1e-9, reg
    assert reg['before'] == 300 and reg['after'] == 331


@check
def the_report_names_what_grew_and_what_was_added():
    prev = run(300, {'test-a.py': 200, 'test-b.py': 100})
    now = run(380, {'test-a.py': 210, 'test-b.py': 100, 'test-new.py': 70}, checks=819)
    reg = R.compare(prev, now)
    assert reg['added'] == ['test-new.py'] and reg['removed'] == []
    assert reg['grown'] == [('test-a.py', 200, 210)]
    text = R.describe(reg, 2)
    assert 'PERFORMANCE REGRESSION' in text and 'test-new.py' in text and '800 -> 819' in text


@check
def references_are_kept_per_worker_count():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, 'reports', 'suite-runtime.json')
        log = R.load_log(p)
        assert log == {}
        R.record(log, 2, run(300), path=p)
        R.record(R.load_log(p), 1, run(500), path=p)
        log = R.load_log(p)
        assert log['last']['2']['seconds'] == 300 and log['last']['1']['seconds'] == 500
        assert len(log['history']) == 2 and log['history'][0]['suites'] is None
        for i in range(30):
            R.record(log, 2, run(300 + i), path=p)
        assert len(R.load_log(p)['history']) == R.HISTORY


def drive_main(seconds, d, fail=False, args=()):
    """Run the real main() on two stub suites taking `seconds` in all, logging to a temp file;
    return its exit status and printed text."""
    import contextlib
    import io
    clock = iter([0.0, float(seconds)])
    saved = (R.suites, R.run, R.RUNTIME_LOG, R.time.perf_counter, sys.argv)
    R.suites = lambda reverse=False: ['test-a.py', 'test-b.py']
    R.run = lambda name: {'suite': name, 'ok': not fail, 'checks': 3, 'seconds': seconds / 2, 'tail': ['x']}
    R.RUNTIME_LOG = os.path.join(d, 'reports', 'suite-runtime.json')
    R.time.perf_counter = lambda: next(clock)
    sys.argv = ['run-tests.py'] + list(args)
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            R.main()
        code = 0
    except SystemExit as e:
        code = e.code
    finally:
        R.suites, R.run, R.RUNTIME_LOG, R.time.perf_counter, sys.argv = saved
    return code, out.getvalue()


@check
def main_records_compares_and_sets_the_exit_status():
    with tempfile.TemporaryDirectory() as d:
        code, text = drive_main(300, d)
        assert code == 0 and 'PERFORMANCE' not in text, (code, text)            # first run: the reference
        code, text = drive_main(325, d)
        assert code == 0, (code, text)                                           # +8 %: fine
        code, text = drive_main(400, d)
        assert code == 2 and 'PERFORMANCE REGRESSION' in text, (code, text)      # +23 % over 325
        code, text = drive_main(900, d, fail=True)
        assert code == 1 and 'PERFORMANCE' not in text                           # a failing run is not judged
        assert R.load_log(os.path.join(d, 'reports', 'suite-runtime.json'))['last']['2']['seconds'] == 400


@check
def the_longest_suites_start_first():
    every = R.suites(times={})                                          # no log: LONG first, as before
    assert every[:len([s for s in R.LONG if s in every])] == [s for s in R.LONG if s in every]
    times = {s: float(i) for i, s in enumerate(sorted(every))}         # the last name took longest
    times.pop(every[-1])                                                # one suite never timed: a new one
    order = R.suites(times=times)
    assert sorted(order) == sorted(every)                               # every suite, once
    assert order[0] == every[-1]                                        # the untimed suite goes first
    assert [times[s] for s in order[1:]] == sorted(times.values(), reverse=True)
    assert R.suites(reverse=True, times=times) == sorted(every, reverse=True)


@check
def small_increases_add_up_against_the_baseline():
    # each run under 10 % slower than the one before, together 21 % slower than the baseline
    with tempfile.TemporaryDirectory() as d:
        assert drive_main(300, d)[0] == 0                                        # the baseline
        assert drive_main(325, d)[0] == 0                                        # +8 %
        code, text = drive_main(345, d)                                          # +6 % on 325, +15 % on 300
        assert code == 2 and 'PERFORMANCE REGRESSION' in text and '300.0s' in text, (code, text)
        assert drive_main(363, d)[0] == 2                                        # +5 % on 345: still +21 %


@check
def running_again_does_not_accept_a_regression():
    with tempfile.TemporaryDirectory() as d:
        drive_main(300, d)
        assert drive_main(400, d)[0] == 2
        code, text = drive_main(400, d)
        assert code == 2 and '--set-baseline' in text, (code, text)
        assert R.baseline(R.load_log(os.path.join(d, 'reports', 'suite-runtime.json')), 2)['seconds'] == 300


@check
def only_set_baseline_moves_the_baseline():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, 'reports', 'suite-runtime.json')
        drive_main(300, d)
        assert drive_main(200, d)[0] == 0                                        # faster: fine, and no move
        assert R.baseline(R.load_log(p), 2)['seconds'] == 300
        code, text = drive_main(400, d, args=['--set-baseline'])                 # a deliberate cost
        assert code == 0 and 'baseline for 2 worker(s) set: 400.0s' in text, (code, text)
        assert R.baseline(R.load_log(p), 2)['seconds'] == 400
        assert drive_main(430, d)[0] == 0 and drive_main(441, d)[0] == 2         # judged against 400 now
        assert drive_main(900, d, fail=True, args=['--set-baseline'])[0] == 1    # a failing run never sets it
        assert R.baseline(R.load_log(p), 2)['seconds'] == 400


@check
def the_runtime_log_is_local_and_never_committed():
    assert R.RUNTIME_LOG.replace('\\', '/').endswith('reports/suite-runtime.json')
    rel = os.path.relpath(R.RUNTIME_LOG, R.ROOT).replace('\\', '/')
    out = subprocess.run(['git', 'check-ignore', '-q', rel], cwd=R.ROOT)
    assert out.returncode == 0, 'reports/suite-runtime.json must be gitignored'


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
