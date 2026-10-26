"""The shared --check cache of one full run (tools/check_cache.py).

    python tools/test-check-cache.py

Read-only, fast: the cache is pointed at a temporary directory standing in for the repository, so
nothing here writes into the repository while other suites run beside it. Each check names a rule
under which a result is reused, or is not.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_cache as CC  # noqa: E402

CHECKS = []


def check(f):
    CHECKS.append(f)
    return f


# A "check" that counts its own runs in a file outside the stand-in repository.
COUNTER = r'''
import sys
p = sys.argv[1]
n = int(open(p).read()) + 1 if __import__("os").path.exists(p) else 1
open(p, "w").write(str(n))
print("run", n)
sys.exit(int(sys.argv[2]))
'''


class Env:
    """A stand-in repository, a cache directory and a counter; restores everything after."""

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.tmp.name
        self.repo, self.cache, self.count = os.path.join(t, 'repo'), os.path.join(t, 'cache'), os.path.join(t, 'n')
        os.makedirs(os.path.join(self.repo, 'data'))
        os.makedirs(self.cache)
        with open(os.path.join(self.repo, 'data', 'x.json'), 'w') as f:
            f.write('{}')
        self.saved = (CC.ROOT, os.environ.get(CC.ENV), sys.argv[0])
        CC.ROOT = self.repo
        os.environ[CC.ENV] = self.cache
        return self

    def __exit__(self, *a):
        CC.ROOT = self.saved[0]
        if self.saved[1] is None:
            os.environ.pop(CC.ENV, None)
        else:
            os.environ[CC.ENV] = self.saved[1]
        sys.argv[0] = self.saved[2]
        self.tmp.cleanup()

    def run(self, suite, flag='--check', code=0):
        sys.argv[0] = suite
        return CC.run([sys.executable, '-c', COUNTER, self.count, str(code), flag], cwd=self.repo)

    def runs(self):
        return int(open(self.count).read()) if os.path.exists(self.count) else 0


@check
def another_suite_is_given_the_result():
    with Env() as e:
        a = e.run('test-a.py')
        b = e.run('test-b.py')
        assert e.runs() == 1 and a.stdout == b.stdout == 'run 1\n' and b.returncode == 0


@check
def a_suite_never_reuses_its_own_result():
    # a suite that runs a check twice to prove it deterministic runs it twice
    with Env() as e:
        e.run('test-a.py')
        e.run('test-a.py')
        assert e.runs() == 2


@check
def a_changed_file_is_a_different_state():
    with Env() as e:
        e.run('test-a.py')
        with open(os.path.join(e.repo, 'data', 'x.json'), 'w') as f:
            f.write('{"changed": true}')
        e.run('test-b.py')
        assert e.runs() == 2


@check
def a_failing_check_is_never_stored():
    with Env() as e:
        assert e.run('test-a.py', code=1).returncode == 1
        assert e.run('test-b.py', code=1).returncode == 1
        assert e.runs() == 2


@check
def only_checks_are_cached():
    with Env() as e:
        e.run('test-a.py', flag='--write')
        e.run('test-b.py', flag='--write')
        assert e.runs() == 2
    assert CC.cacheable(['python', 'tools/migrate.py', '--check'])
    assert CC.cacheable(['python', 'tools/evidence_store.py', '--verify'])
    assert CC.cacheable(['python', 'C:/x/tools/test-m36a-r1.py'])
    assert not CC.cacheable(['python', 'tools/migrate.py', '--until', 'M7'])


@check
def a_check_already_running_elsewhere_is_waited_for():
    # another suite holds the lock: its stored answer is given, and the check does not run again
    import json
    import threading
    with Env() as e:
        sys.argv[0] = 'test-b.py'
        cmd = [sys.executable, '-c', COUNTER, e.count, '0', '--check']
        key = CC._state(cmd, e.repo, True)
        lock = os.path.join(e.cache, key + '.lock')
        open(lock, 'w').close()

        def other_suite_finishes():
            with open(os.path.join(e.cache, key + '.json'), 'w', encoding='utf-8') as f:
                json.dump({'suite': 'test-a.py', 'returncode': 0, 'stdout': 'run elsewhere\n', 'stderr': ''}, f)
            os.remove(lock)
        threading.Timer(1.0, other_suite_finishes).start()
        out = CC.run(cmd, cwd=e.repo)
        assert out.stdout == 'run elsewhere\n' and e.runs() == 0, (out.stdout, e.runs())
        # the other run stored nothing (it failed, or the state changed): this suite runs the check itself
        open(lock, 'w').close()
        os.remove(os.path.join(e.cache, key + '.json'))
        threading.Timer(1.0, lambda: os.remove(lock)).start()
        assert CC.run(cmd, cwd=e.repo).stdout == 'run 1\n' and e.runs() == 1


@check
def without_the_run_s_cache_every_check_runs():
    # a suite run by hand, or tools/run-tests.py --no-cache
    with Env() as e:
        os.environ.pop(CC.ENV)
        e.run('test-a.py')
        e.run('test-b.py')
        assert e.runs() == 2 and not os.listdir(e.cache)


@check
def a_tool_is_one_question_however_its_path_is_spelled():
    root = CC.ROOT
    fwd = root.replace('\\', '/') + '/tools/migrate.py'
    bwd = os.path.join(root, 'tools', 'migrate.py')
    assert CC._norm(fwd) == CC._norm(bwd) == 'tools/migrate.py'
    assert CC._norm('--check') == '--check'


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
