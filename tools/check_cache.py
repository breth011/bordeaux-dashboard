"""One full run's shared --check results: a check one suite has run is not rebuilt by the next.

    import check_cache as CC
    out = CC.run([sys.executable, L.ROOT + 'tools/migrate.py', '--check'])   # a CompletedProcess

Several suites end by proving the same thing - the model rebuilds byte for byte, the application
data is the model, the gap register is current - and each proof rebuilds from scratch. Within one
run of tools/run-tests.py the repository does not change between them, so the second suite to ask
is given the first one's answer.

A result is reused only when all of these hold; otherwise the command runs as it always did:
- tools/run-tests.py made the cache for this run (BDX_CHECK_CACHE): a suite run by hand, or a run
  with --no-cache, runs every check;
- the command is a check: it carries --check or --verify, or it is a test-*.py suite;
- the result came from another suite: a suite that runs a check twice to prove it deterministic
  runs it twice;
- the state is the one it was computed in: the command, its directory, the environment, HEAD and
  the size and modification time of every file in the repository (sources/ included) all match;
- it passed, and the run changed no file: a failing or writing check is never stored.

When another suite is already running the same check in the same state, the second waits for its
answer rather than rebuilding beside it; if that run stores nothing, the second runs the check.
"""
import hashlib
import json
import os
import subprocess
import sys
import time

WAIT = 900                       # seconds to wait for another suite's run of the same check

ENV = 'BDX_CHECK_CACHE'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = {'.git', '__pycache__', 'node_modules'}
CHECK_ARGS = ('--check', '--verify')


def caller():
    return os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else '?'


def _tree():
    """Every file's path, size and modification time: what a check could have read."""
    h = hashlib.sha256()
    stack = [ROOT]
    while stack:
        d = stack.pop()
        try:
            entries = sorted(os.scandir(d), key=lambda e: e.name)
        except OSError:
            continue
        for e in entries:
            if e.is_dir(follow_symlinks=False):
                if e.name not in SKIP:
                    stack.append(e.path)
            else:
                st = e.stat(follow_symlinks=False)
                h.update(('%s|%d|%d\n' % (e.path[len(ROOT):], st.st_size, st.st_mtime_ns)).encode('utf-8'))
    return h.hexdigest()


def _norm(arg):
    """A path inside the repository as its relative path, however it was spelled (L.ROOT's
    forward slashes, a drive letter's case), so two suites naming one tool ask the same thing."""
    a = str(arg)
    if os.path.isabs(a):
        p, root = os.path.normcase(os.path.abspath(a)), os.path.normcase(ROOT)
        if p.startswith(root + os.sep):
            return p[len(root) + 1:].replace('\\', '/')
    return a


def _state(cmd, cwd, text):
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    env = sorted((k, v) for k, v in os.environ.items() if k != ENV)
    return hashlib.sha256(json.dumps([[_norm(c) for c in cmd], _norm(os.path.abspath(cwd or os.getcwd())), env,
                                      bool(text), head, _tree()]).encode('utf-8')).hexdigest()


def cacheable(cmd):
    names = [os.path.basename(str(c)) for c in cmd]
    return any(c in CHECK_ARGS for c in names) or any(n.startswith('test-') and n.endswith('.py') for n in names)


def run(cmd, cwd=None, text=True):
    """subprocess.run(cmd, cwd=cwd, capture_output=True, text=text), reusing another suite's result
    for the same check in the same state."""
    d = os.environ.get(ENV)
    if not d or not os.path.isdir(d) or not cacheable(cmd):
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=text)
    key = _state(cmd, cwd, text)
    path, lock = os.path.join(d, key + '.json'), os.path.join(d, key + '.lock')
    hit = _stored(cmd, path)
    if hit:
        return hit
    try:
        os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    except FileExistsError:
        # another suite is running this check now: its answer, once it has one
        end = time.monotonic() + WAIT
        while os.path.exists(lock) and time.monotonic() < end:
            time.sleep(0.5)
        hit = _stored(cmd, path)
        if hit:
            return hit
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=text)
    try:
        out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=text)
        if out.returncode == 0 and text and _state(cmd, cwd, text) == key:
            tmp = '%s.%d.tmp' % (path, os.getpid())
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump({'suite': caller(), 'cmd': [_norm(c) for c in cmd], 'returncode': out.returncode,
                           'stdout': out.stdout, 'stderr': out.stderr}, f)
            os.replace(tmp, path)
        return out
    finally:
        os.remove(lock)


def _stored(cmd, path):
    """Another suite's stored result for this check and state, or None."""
    try:
        with open(path, encoding='utf-8') as f:
            hit = json.load(f)
    except (OSError, ValueError):
        return None
    if hit.get('suite') == caller():
        return None
    return subprocess.CompletedProcess(cmd, hit['returncode'], hit['stdout'], hit['stderr'])
