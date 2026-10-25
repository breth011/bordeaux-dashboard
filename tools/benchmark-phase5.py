"""Phase 5 M0: the baseline benchmark. Measurement only.

    python tools/benchmark-phase5.py                  every family, appended to
                                                      data/performance/benchmarks.jsonl
    python tools/benchmark-phase5.py --only startup   one family (env, suite, startup,
                                                      search, lookup, model, rebuild,
                                                      storage, duplicates, large)

Nothing in the project is written except data/performance/benchmarks.jsonl
(appended) and data/performance/storage-inventory.json. Every temporary
thing (a browser profile, a rebuilt model, child scripts) goes into a
directory under the system temporary directory and is removed. No
benchmark family runs if free disk is below 6 GB; one whose temporary
output brings it below 6 GB stops.

Measurement methods:
  time        time.perf_counter in this process; performance.now() inside the
              page; each benchmark repeated, median/min/max and every run kept
  memory      peak working set (psutil peak_wset, Windows): a Python child
              reports its own at exit; a test suite's is the last value polled
              every 50 ms (monotonic, so at most 50 ms of growth is missed); the
              browser's is the sum over its process tree; the page's JS heap from
              the DevTools Performance domain
  the app     the real page (index.html, assets/app.js, data/*.js) served from
              the repository by a local http.server and loaded in headless
              Chrome through the DevTools protocol; nothing in the page is changed
"""
import base64
import collections
import glob
import hashlib
import http.server
import json
import os
import platform
import shutil
import socket
import statistics
import struct
import subprocess
import sys
import tempfile
import threading
import time
import functools
import urllib.request

import psutil

import migration_lib as L

OUT = L.ROOT + 'data/performance/benchmarks.jsonl'
INVENTORY = L.ROOT + 'data/performance/storage-inventory.json'
MIN_FREE_MB = 6 * 1024
CHROME = [r'C:\Program Files\Google\Chrome\Application\chrome.exe',
          r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe']
RUN = time.strftime('%Y-%m-%dT%H:%M:%S')


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode().strip()


def free_mb():
    return shutil.disk_usage(L.ROOT).free // (1024 * 1024)


ENV = None


def environment():
    global ENV
    if ENV is None:
        node_v = subprocess.check_output([L.node(), '--version']).decode().strip()
        vm = psutil.virtual_memory()
        ENV = {'commit': git('rev-parse', '--short', 'HEAD'),
               'dirty_files': [l[3:] for l in git('status', '--porcelain', '--untracked-files=all').splitlines()],
               'python': platform.python_version(), 'node': node_v,
               'os': platform.platform(), 'cpu': platform.processor(),
               'logical_cpus': psutil.cpu_count(), 'physical_cpus': psutil.cpu_count(logical=False),
               'ram_mb': vm.total // (1024 * 1024), 'run': RUN}
    return ENV


def record(benchmark_id, category, workload, runs_ms=None, cold_warm=None, peak_memory_mb=None,
           input_counts=None, output_counts=None, free_before=None, free_after=None, status='OK',
           notes=None, extra=None):
    env = environment()
    r = {'benchmark_id': benchmark_id, 'category': category, 'workload': workload,
         'commit': env['commit'], 'environment': {k: env[k] for k in ('python', 'node', 'os', 'logical_cpus')},
         'run': RUN, 'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'), 'cold_warm': cold_warm,
         'iteration': len(runs_ms) if runs_ms else 0,
         'elapsed_ms': round(statistics.median(runs_ms), 6) if runs_ms else None,
         'min_ms': round(min(runs_ms), 6) if runs_ms else None,
         'max_ms': round(max(runs_ms), 6) if runs_ms else None,
         'runs_ms': [round(x, 6) for x in runs_ms] if runs_ms else [],
         'peak_memory_mb': peak_memory_mb, 'input_counts': input_counts or {},
         'output_counts': output_counts or {}, 'free_disk_before_mb': free_before,
         'free_disk_after_mb': free_after, 'status': status, 'notes': notes}
    if extra:
        r['detail'] = extra
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'a', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n')
    L.out('%-44s %10s ms  %s' % (benchmark_id, r['elapsed_ms'], status))
    return r


def guard(family):
    f = free_mb()
    if f < MIN_FREE_MB:
        record(family + '.disk-guard', 'disk', 'free disk below 6 GB', free_before=f, status='STOPPED',
               notes='the family did not run: free disk below the crawler threshold')
        return None
    return f


def mb(b):
    return round(b / (1024 * 1024), 1)


# ------------------------------------------------------------------ children

def run_child(code, args=(), env_extra=None):
    """A Python child that reports {'result': ..., 'peak_wset': bytes} as its last line."""
    tmp = tempfile.mkdtemp(prefix='bdx-bench-')
    try:
        p = os.path.join(tmp, 'child.py')
        open(p, 'w', encoding='utf-8').write(
            'import sys, json, time, psutil\nsys.path.insert(0, %r)\n' % (L.ROOT + 'tools') + code +
            '\nprint(json.dumps({"result": RESULT, "peak_wset": psutil.Process().memory_info().peak_wset}))\n')
        env = dict(os.environ, **(env_extra or {}))
        t = time.perf_counter()
        out = subprocess.run([sys.executable, p] + list(args), cwd=L.ROOT, capture_output=True, env=env)
        el = (time.perf_counter() - t) * 1000
        if out.returncode:
            raise RuntimeError(out.stderr.decode()[-800:])
        return el, json.loads(out.stdout.decode().strip().splitlines()[-1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def poll_peak(cmd, cwd=L.ROOT, env=None):
    """Run a command; return (elapsed ms, exit code, last output line, peak working set of the tree)."""
    t = time.perf_counter()
    p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    peak = 0
    out = []
    reader = threading.Thread(target=lambda: out.extend(p.stdout.read().decode('utf-8', 'replace').splitlines()))
    reader.start()
    proc = psutil.Process(p.pid)
    while p.poll() is None:
        try:
            tree = [proc] + proc.children(recursive=True)
            peak = max(peak, sum(x.memory_info().peak_wset for x in tree if x.is_running()))
        except psutil.Error:
            pass
        time.sleep(0.05)
    reader.join()
    return (time.perf_counter() - t) * 1000, p.returncode, (out[-1] if out else ''), peak


# ------------------------------------------------------------------ families

def fam_env():
    env = environment()
    d = shutil.disk_usage(L.ROOT)
    sizes = {k: tree_size(L.ROOT + k) for k in ('data', 'data/model', 'data/discovery', 'data/evidence',
                                                 'sources', '.git')}
    canon = sum(os.path.getsize(p) for p in L.GROUPS['canonical']())
    work = tree_size(L.ROOT, skip={'.git', 'sources'})
    record('env.machine', 'environment', 'the machine and the checkout', free_before=d.free // 2**20,
           input_counts={'disk_total_mb': d.total // 2**20, 'disk_free_mb': d.free // 2**20},
           output_counts={'working_tree_bytes_excl_git_sources': work['bytes'],
                          'canonical_bytes': canon, **{k + '_bytes': v['bytes'] for k, v in sizes.items()},
                          **{k + '_files': v['files'] for k, v in sizes.items()}},
           extra=env, notes='sizes are logical bytes (file length); see storage.* for allocated sizes')


def tree_size(root, skip=()):
    n = b = 0
    for dp, dn, fn in os.walk(root):
        if dp == root.rstrip('/') or dp == root:
            dn[:] = [d for d in dn if d not in skip]
        for f in fn:
            try:
                b += os.stat(os.path.join(dp, f)).st_size
                n += 1
            except OSError:
                pass
    return {'bytes': b, 'files': n}


def fam_suite():
    # The suites as Phase 4 runs them: test-phase5 checks this run's own output.
    tests = sorted(t for t in glob.glob(L.ROOT + 'tools/test-*.py') if not t.endswith('test-phase5.py'))
    for label in ('cold', 'warm'):
        f0 = guard('suite')
        if f0 is None:
            return
        total = 0
        per = {}
        peak = 0
        checks = 0
        fails = 0
        for t in tests:
            el, code, last, pk = poll_peak([sys.executable, t])
            name = os.path.basename(t)
            per[name] = {'ms': round(el), 'exit': code, 'last': last, 'peak_mb': mb(pk)}
            total += el
            peak = max(peak, pk)
            fails += code != 0
            import re
            m = re.match(r'(\d+) check', last)
            checks += int(m.group(1)) if m else 0
        record('suite.full.' + label, 'suite', 'every tools/test-*.py, one after another, as Phase 4 runs them',
               runs_ms=[total], cold_warm=label, peak_memory_mb=mb(peak),
               input_counts={'suites': len(tests)}, output_counts={'checks': checks, 'failures': fails},
               free_before=f0, free_after=free_mb(), status='OK' if not fails else 'FAIL',
               notes='one repetition per state (a run takes minutes); test-reader.py prints no check count',
               extra=per)


# --- a minimal WebSocket client for the DevTools protocol (stdlib only)

class CDP:
    def __init__(self, url):
        host, rest = url[len('ws://'):].split('/', 1)
        h, p = host.split(':')
        self.s = socket.create_connection((h, int(p)), timeout=120)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall(('GET /%s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
                        'Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n' % (rest, host, key)).encode())
        buf = b''
        while b'\r\n\r\n' not in buf:
            buf += self.s.recv(4096)
        self.buf = buf.split(b'\r\n\r\n', 1)[1]
        self.n = 0
        self.events = []

    def _read(self, n):
        while len(self.buf) < n:
            chunk = self.s.recv(1 << 16)
            if not chunk:
                raise ConnectionError('closed')
            self.buf += chunk
        d, self.buf = self.buf[:n], self.buf[n:]
        return d

    def _frame(self):
        msg = b''
        while True:
            b1, b2 = self._read(2)
            ln = b2 & 0x7F
            if ln == 126:
                ln = struct.unpack('>H', self._read(2))[0]
            elif ln == 127:
                ln = struct.unpack('>Q', self._read(8))[0]
            msg += self._read(ln)
            if b1 & 0x80:
                return msg.decode('utf-8')

    def send(self, method, params=None, wait=True):
        self.n += 1
        data = json.dumps({'id': self.n, 'method': method, 'params': params or {}}).encode()
        mask = os.urandom(4)
        hdr = bytes([0x81])
        ln = len(data)
        hdr += bytes([0x80 | ln]) if ln < 126 else (bytes([0x80 | 126]) + struct.pack('>H', ln) if ln < 65536
                                                     else bytes([0x80 | 127]) + struct.pack('>Q', ln))
        self.s.sendall(hdr + mask + bytes(c ^ mask[i % 4] for i, c in enumerate(data)))
        if not wait:
            return None
        want = self.n
        while True:
            m = json.loads(self._frame())
            if m.get('id') == want:
                if 'error' in m:
                    raise RuntimeError(m['error'])
                return m['result']
            self.events.append(m)

    def wait_event(self, method, timeout=120):
        end = time.time() + timeout
        for i, e in enumerate(self.events):
            if e.get('method') == method:
                return self.events.pop(i)
        while time.time() < end:
            m = json.loads(self._frame())
            if m.get('method') == method:
                return m
            self.events.append(m)
        raise TimeoutError(method)

    def js(self, expr):
        r = self.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
        if r.get('exceptionDetails'):
            raise RuntimeError(r['exceptionDetails'])
        return r['result'].get('value')


class Server:
    """The repository (or a copy of the site), served read-only as the page is published."""

    def __init__(self, root=None):
        self.root = root or L.ROOT

    def __enter__(self):
        class Quiet(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *a):
                pass
        self.srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0),
                                                   functools.partial(Quiet, directory=self.root))
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = 'http://127.0.0.1:%d/index.html' % self.srv.server_address[1]
        return self

    def __exit__(self, *a):
        self.srv.shutdown()


class Browser:
    def __enter__(self):
        exe = next(p for p in CHROME if os.path.exists(p))
        self.profile = tempfile.mkdtemp(prefix='bdx-bench-chrome-')
        s = socket.socket()
        s.bind(('127.0.0.1', 0))
        self.port = s.getsockname()[1]
        s.close()
        t = time.perf_counter()
        self.p = subprocess.Popen([exe, '--headless=new', '--remote-debugging-port=%d' % self.port,
                                   '--user-data-dir=' + self.profile, '--no-first-run',
                                   '--no-default-browser-check', '--disable-extensions',
                                   '--window-size=1400,900', 'about:blank'],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        while True:
            try:
                targets = json.load(urllib.request.urlopen('http://127.0.0.1:%d/json/list' % self.port, timeout=1))
                pages = [x for x in targets if x['type'] == 'page']
                if pages:
                    break
            except Exception:
                pass
            time.sleep(0.02)
        self.ready_ms = (time.perf_counter() - t) * 1000
        self.c = CDP(pages[0]['webSocketDebuggerUrl'])
        self.c.send('Page.enable')
        self.c.send('Performance.enable')
        self.exe = exe
        return self

    def tree_peak(self):
        try:
            pr = psutil.Process(self.p.pid)
            return sum(x.memory_info().peak_wset for x in [pr] + pr.children(recursive=True))
        except psutil.Error:
            return None

    def navigate(self, url):
        self.c.events = []
        t = time.perf_counter()
        self.c.send('Page.navigate', {'url': url})
        self.c.wait_event('Page.loadEventFired')
        return (time.perf_counter() - t) * 1000

    def __exit__(self, *a):
        try:
            self.c.send('Browser.close', wait=False)
        except Exception:
            pass
        try:
            self.p.wait(10)
        except Exception:
            self.p.kill()
        time.sleep(0.5)
        shutil.rmtree(self.profile, ignore_errors=True)


PAGE_TIMING = '''(function () {
  var n = performance.getEntriesByType('navigation')[0];
  var data = performance.getEntriesByType('resource').filter(function (r) { return r.name.indexOf('/data/') >= 0; });
  var assets = performance.getEntriesByType('resource').filter(function (r) { return r.name.indexOf('/assets/') >= 0; });
  var sum = function (a, k) { return a.reduce(function (s, r) { return s + (r[k] || 0); }, 0); };
  var first = data.length ? Math.min.apply(null, data.map(function (r) { return r.startTime; })) : 0;
  var last = data.length ? Math.max.apply(null, data.map(function (r) { return r.responseEnd; })) : 0;
  return {
    responseEnd: n.responseEnd, domInteractive: n.domInteractive,
    dclStart: n.domContentLoadedEventStart, dclEnd: n.domContentLoadedEventEnd,
    loadEnd: n.loadEventEnd, dataFiles: data.length, dataDecodedBytes: sum(data, 'decodedBodySize'),
    dataTransferBytes: sum(data, 'transferSize'), dataFetchSpan: last - first,
    assetFiles: assets.length, swControlled: !!navigator.serviceWorker.controller,
    estates: (window.BDX_CHATEAUX || []).length,
    cards: document.querySelectorAll('.apcard').length
  };
})()'''


def heap(c):
    m = {x['name']: x['value'] for x in c.send('Performance.getMetrics')['metrics']}
    return mb(m.get('JSHeapUsedSize', 0)), mb(m.get('JSHeapTotalSize', 0))


def fam_startup():
    f0 = guard('startup')
    if f0 is None:
        return
    rows = {'cold': [], 'warm': []}
    with Server() as srv:
        for rep in range(5):
            with Browser() as b:
                nav = b.navigate(srv.url)
                t = b.c.js(PAGE_TIMING)
                hu, ht = heap(b.c)
                rows['cold'].append(dict(t, browser_ready_ms=b.ready_ms, navigate_to_load_ms=nav,
                                         heap_used_mb=hu, heap_total_mb=ht, tree_peak=b.tree_peak()))
                b.c.js('navigator.serviceWorker.ready.then(function () { return 1; })')
                time.sleep(1.0)
                nav = b.navigate(srv.url)
                t = b.c.js(PAGE_TIMING)
                hu, ht = heap(b.c)
                rows['warm'].append(dict(t, browser_ready_ms=None, navigate_to_load_ms=nav,
                                         heap_used_mb=hu, heap_total_mb=ht, tree_peak=b.tree_peak()))
    data_bytes = sum(os.path.getsize(L.ROOT + 'data/' + f) for f in os.listdir(L.ROOT + 'data')
                     if f.endswith('.js') and ('data/' + f) in open(L.ROOT + 'index.html', encoding='utf-8').read())
    for label, rs in rows.items():
        def col(k):
            return [r[k] for r in rs]
        common = dict(cold_warm=label, input_counts={'data_files_on_disk_bytes': data_bytes,
                                                    'data_files_loaded': rs[0]['dataFiles']},
                      free_before=f0)
        if label == 'cold':
            record('startup.browser-process', 'startup', 'headless Chrome launched to a page target reachable '
                   'over DevTools', runs_ms=col('browser_ready_ms'), **common,
                   notes='process startup: a new profile each repetition')
        record('startup.data-loading.' + label, 'startup', 'navigation response end to domInteractive: every '
               'data/*.js and assets/*.js fetched, parsed and run (they are blocking scripts)',
               runs_ms=[r['domInteractive'] - r['responseEnd'] for r in rs], **common,
               output_counts={'data_decoded_bytes': rs[0]['dataDecodedBytes'],
                              'data_transfer_bytes': rs[0]['dataTransferBytes'],
                              'sw_controlled': rs[-1]['swControlled']},
               extra={'data_fetch_span_ms': [round(r['dataFetchSpan'], 1) for r in rs]})
        record('startup.app-init.' + label, 'startup', 'DOMContentLoaded handler: app.js init() renders the '
               'first view', runs_ms=[r['dclEnd'] - r['dclStart'] for r in rs], **common,
               output_counts={'estates_in_memory': rs[0]['estates'], 'first_view_cards': rs[0]['cards']})
        record('startup.app-ready.' + label, 'startup', 'navigation start to the end of init (domContentLoadedEventEnd)',
               runs_ms=col('dclEnd'), **common,
               peak_memory_mb=max(mb(r['tree_peak']) for r in rs if r['tree_peak']),
               output_counts={'js_heap_used_mb': statistics.median(col('heap_used_mb')),
                              'js_heap_total_mb': statistics.median(col('heap_total_mb'))},
               notes='peak memory: the browser process tree peak working set; heap: the page JS heap after load')
        record('startup.load-event.' + label, 'startup', 'navigation start to the load event',
               runs_ms=col('loadEnd'), **common)
    f1 = free_mb()
    return f1


SEARCH = [('exact estate name', 'Château Pichon-Longueville Baron'), ('partial estate name', 'pichon'),
          ('exact wine name', 'Carruades de Lafite'), ('partial wine name', 'carruades'),
          ('common term', 'pauillac'), ('many matches', 'chateau'), ('few matches', 'lafleur'),
          ('no matches', 'zzqxv')]

SEARCH_JS = '''(function (q, reps) {
  var box = document.getElementById('search');
  var times = [];
  for (var i = 0; i < reps; i++) {
    box.value = ''; box.dispatchEvent(new Event('input'));
    var t = performance.now();
    box.value = q; box.dispatchEvent(new Event('input'));
    times.push(performance.now() - t);
  }
  var res = {times: times, cards: document.querySelectorAll('#paneList .pcard').length,
             ac: document.querySelectorAll('.acrow').length,
             count: (document.getElementById('resultcount') || {}).textContent || ''};
  box.value = ''; box.dispatchEvent(new Event('input'));
  return res;
})'''


def fam_search():
    f0 = guard('search')
    if f0 is None:
        return
    with Server() as srv, Browser() as b:
        b.navigate(srv.url)
        b.c.js("document.getElementById('tabProducers').click()")
        time.sleep(0.5)
        for name, q in SEARCH:
            r = b.c.js('%s(%s, 15)' % (SEARCH_JS, json.dumps(q)))
            hu, _ = heap(b.c)
            record('search.' + name.replace(' ', '-'), 'search', 'type %r into the search box of the '
                   'Producers & map view; one input event (list filter, map and autocomplete render)' % q,
                   runs_ms=r['times'], cold_warm='warm', peak_memory_mb=mb(b.tree_peak() or 0),
                   input_counts={'query': q}, output_counts={'list_cards': r['cards'], 'autocomplete_rows': r['ac'],
                                                            'result_label': r['count'], 'js_heap_used_mb': hu},
                   free_before=f0, notes='15 repetitions in one warm page; each preceded by clearing the box')


# The app's own lookup functions, copied verbatim from assets/app.js (it runs in a
# closure, so they cannot be called from outside); run against the page's globals.
LOOKUP_JS = '''(function (W) {
  var CH = window.BDX_CHATEAUX, CUVEE_WINES = window.BDX_CUVEE_WINES || {}, CUVEES = window.BDX_CUVEES || {};
  var SCORES = window.BDX_SCORES || {}, RATINGS = window.BDX_RATINGS || {};
  function withDutch(a, b) { return a; }
  function notProduced(ch, y) { var n = (window.BDX_NOT_PRODUCED || {})[ch.id]; return !!(n && n.indexOf(y) >= 0); }
  function chateauById(id) {
    for (var i = 0; i < CH.length; i++) if (CH[i].id === id) return CH[i];
    return null;
  }
  function fiche(ch, yr) {
    var F = window.BDX_FICHES, k = ch.id + '|' + yr;
    return withDutch((F && F[k]) || null, (window.BDX_FICHES_NL || {})[k]);
  }
  function ficheUrl(ch, yr, slug) {
    if (!ch) return null;
    if (slug && slug !== 'grand') { var C = window.BDX_CUVEE_URL; return (C && C[ch.id + '|' + slug + '|' + yr]) || null; }
    var U = window.BDX_FICHE_URL; return (U && U[ch.id + '|' + yr]) || null;
  }
  function winesOf(ch) {
    var list = [{ slug: 'grand', name: ch.name, role: 'grand',
                  colour: ch.cat === 'sweet' ? 'sweet' : ch.cat === 'white' ? 'white' : 'red' }];
    var more = CUVEE_WINES[ch.id] || [];
    for (var i = 0; i < more.length; i++) list.push(more[i]);
    return list;
  }
  function wineFiche(ch, slug, yr) {
    if (!slug || slug === 'grand') return fiche(ch, yr);
    var k = ch.id + '|' + slug + '|' + yr;
    return withDutch(CUVEES[k] || null, (window.BDX_CUVEES_NL || {})[k]);
  }
  function scoreFor(ch, year) {
    if (notProduced(ch, year)) return { none: true };
    var o = SCORES[ch.id + '|' + year]; if (o && o.score) return { score: o.score };
    var r = RATINGS[ch.id + '|' + year]; if (r) return { score: Math.round(r[0]) };
    return { none: true };
  }
  function wineByName(name) {          /* no such call in the app: a wine is reached through its estate */
    for (var i = 0; i < CH.length; i++) { var ws = winesOf(CH[i]);
      for (var j = 0; j < ws.length; j++) if (ws[j].name === name) return ws[j]; }
    return null;
  }
  function estatesOfWine(name) {       /* the legacy data holds no wine->estate map: a scan */
    var out = [];
    for (var i = 0; i < CH.length; i++) { var ws = winesOf(CH[i]);
      for (var j = 0; j < ws.length; j++) if (ws[j].name === name) out.push(CH[i].id); }
    return out;
  }
  var ops = {
    estate: function (a) { return chateauById(a.id) ? 1 : 0; },
    wine: function (a) { return wineByName(a.wine) ? 1 : 0; },
    estate_wines: function (a) { return winesOf(chateauById(a.id)).length; },
    wine_estates: function (a) { return estatesOfWine(a.wine).length; },
    wine_vintage: function (a) { var ch = chateauById(a.id); return (wineFiche(ch, a.slug, a.yr) ? 1 : 0) + (scoreFor(ch, a.yr).none ? 0 : 1); },
    estate_vintage: function (a) { var ch = chateauById(a.id); return (fiche(ch, a.yr) ? 1 : 0) + (scoreFor(ch, a.yr).none ? 0 : 1); },
    document: function (a) { var ch = chateauById(a.id); return ficheUrl(ch, a.yr, a.slug) ? 1 : 0; },
    field: function (a) { var f = wineFiche(chateauById(a.id), a.slug, a.yr); return f && f[a.field] != null ? 1 : 0; },
    estate_all_vintages: function (a) { var ch = chateauById(a.id), n = 0;
      for (var y = 1900; y <= 2026; y++) { if (fiche(ch, y)) n++; if (!scoreFor(ch, y).none) n++; } return n; }
  };
  var res = {};
  W.forEach(function (w) {
    var f = ops[w.op], samples = [], out = 0, inner = w.inner;
    for (var s = 0; s < 9; s++) {
      var t = performance.now();
      for (var i = 0; i < inner; i++) out = f(w.args);
      samples.push((performance.now() - t) * 1000 / inner);
    }
    res[w.id] = {us: samples, out: out};
  });
  return res;
})'''


def workloads():
    """Real cases, chosen from the data: small and large, dense and sparse."""
    F, C = L.g('BDX_FICHES'), L.g('BDX_CUVEES')
    per_est = collections.Counter(k.split('|')[0] for k in F)
    per_wine = collections.Counter('|'.join(k.split('|')[:2]) for k in C)
    big = per_est.most_common(1)[0][0]
    small = sorted(e for e, n in per_est.items() if n == 1)[0]
    wine_big = per_wine.most_common(1)[0][0]
    wine_sparse = sorted(w for w, n in per_wine.items() if n == 1)[0]
    multi_doc = sorted(k for k, v in L.g('BDX_FIELD_SRC').items() if len(set(v.values())) >= 3)[0]
    view = L.canonical_view()['estates']
    sparse_estate = sorted(e['id'] for e in view if e['sparse'])[0]
    wines = L.g('BDX_CUVEE_WINES')
    bw_est, bw_slug = wine_big.split('|')
    bw_name = next(w['name'] for w in wines[bw_est] if w['slug'] == bw_slug)
    sw_est, sw_slug = wine_sparse.split('|')
    sw_name = next(w['name'] for w in wines[sw_est] if w['slug'] == sw_slug)
    big_year = sorted(k.split('|')[1] for k in F if k.startswith(big + '|'))[-1]
    md_est, md_year = multi_doc.split('|')
    bw_year = sorted(k.split('|')[2] for k in C if k.startswith(wine_big + '|'))[-1]
    last = view[-1]['id']
    w = [
        ('estate.small', 'estate', {'id': small}, 'an estate with one fiche record'),
        ('estate.large', 'estate', {'id': big}, 'the estate with the most fiche records (%d)' % per_est[big]),
        ('estate.compact-list', 'estate', {'id': sparse_estate}, 'a name-derived compact-list estate'),
        ('estate.last-in-list', 'estate', {'id': last}, 'the last estate in the array: the linear scan\'s worst case'),
        ('wine.many-vintages', 'wine', {'wine': bw_name}, 'the other wine with the most records'),
        ('wine.sparse', 'wine', {'wine': sw_name}, 'an other wine with one record'),
        ('estate-wines.large', 'estate_wines', {'id': bw_est}, 'the estate of that wine'),
        ('estate-wines.small', 'estate_wines', {'id': small}, 'the small estate'),
        ('wine-estates.many-vintages', 'wine_estates', {'wine': bw_name}, 'wine -> estates'),
        ('wine-vintage.many', 'wine_vintage', {'id': bw_est, 'slug': bw_slug, 'yr': int(bw_year)}, 'wine + vintage'),
        ('wine-vintage.sparse', 'wine_vintage', {'id': sw_est, 'slug': sw_slug,
                                                 'yr': int(next(k for k in C if k.startswith(wine_sparse + '|')).split('|')[2])}, 'wine + vintage'),
        ('estate-vintage.large', 'estate_vintage', {'id': big, 'yr': int(big_year)}, 'estate + vintage'),
        ('estate-vintage.small', 'estate_vintage', {'id': small, 'yr': int(next(k for k in F if k.startswith(small + '|')).split('|')[1])}, 'estate + vintage'),
        ('document.multi-source', 'document', {'id': md_est, 'yr': int(md_year)}, 'the sheet link of a record whose fields cite 3+ documents'),
        ('field.blend', 'field', {'id': big, 'slug': 'grand', 'yr': int(big_year), 'field': 'blend'}, 'one field of a fiche'),
        ('estate-all-vintages.large', 'estate_all_vintages', {'id': big}, 'every year 1900-2026 of the largest estate: fiche and score'),
    ]
    return [{'id': i, 'op': op, 'args': a, 'inner': 2000 if op not in ('wine', 'wine_estates', 'estate_all_vintages') else 50,
             'desc': d} for i, op, a, d in w]


def fam_lookup():
    f0 = guard('lookup')
    if f0 is None:
        return
    W = workloads()
    with Server() as srv, Browser() as b:
        b.navigate(srv.url)
        r = b.c.js('%s(%s)' % (LOOKUP_JS, json.dumps(W)))
    for w in W:
        x = r[w['id']]
        record('lookup.app.' + w['id'], 'lookup', '%s (%s)' % (w['desc'], w['op']),
               runs_ms=[u / 1000 for u in x['us']], cold_warm='warm', input_counts=w['args'],
               output_counts={'result': x['out']}, free_before=f0,
               notes='the app\'s own lookup functions run in the live page; per call, from 9 samples of %d calls' % w['inner'])
    # The same questions answered by the normalized model, in Python (not the application):
    # the identity map, the derived indexes and the canonical values, each question its own path.
    code = '''
import time, json, collections, migration_lib as L
t0 = time.perf_counter()
im = {(r['namespace'], r['legacy_key']): r.get('stable_id')
      for r in L.jsonl_lines(L.MODEL + 'identity/identity-map.jsonl')}
ew = json.load(open(L.MODEL + 'derived/estate-wines.json', encoding='utf-8'))
wv = json.load(open(L.MODEL + 'derived/wine-vintages.json', encoding='utf-8'))
vd = json.load(open(L.MODEL + 'derived/vintage-documents.json', encoding='utf-8'))
names = collections.defaultdict(list)
for n in L.jsonl_lines(L.MODEL + 'identity/names.jsonl'):
    names[n['name']].append(n['subject'])
cv = {(c['subject'], c['field']): c['value'] for c in L.jsonl_lines(L.MODEL + 'canonical/values.jsonl')}
load = (time.perf_counter() - t0) * 1000
def wine_estates(w):
    return [e for e, ws in ew.items() if w in ws]
def est(a): return im[('estate', a['id'])]
def vint(a):
    if a.get('slug') and a['slug'] != 'grand':
        return im.get(('estate|slug|vintage', '%s|%s|%s' % (a['id'], a['slug'], a['yr'])))
    return im.get(('estate|vintage', '%s|%s' % (a['id'], a['yr'])))
ops = {
    'estate': lambda a: 1 if est(a) else 0,
    'wine': lambda a: len(names.get(a['wine'], [])),
    'estate_wines': lambda a: len(ew.get(est(a), [])),
    'wine_estates': lambda a: len(wine_estates(names[a['wine']][0])),
    'wine_vintage': lambda a: 1 if vint(a) else 0,
    'estate_vintage': lambda a: 1 if vint(a) else 0,
    'document': lambda a: len(vd.get(vint(a) or '', [])),
    'field': lambda a: 1 if cv.get((vint(a), a['field'])) is not None else 0,
    'estate_all_vintages': lambda a: len(wv.get(im[('grand-vin', a['id'])], [])),
}
W = json.loads(sys.argv[1])
res = {}
for w in W:
    f, a = ops[w['op']], w['args']
    s = []
    for k in range(9):
        t = time.perf_counter()
        for i in range(w['inner']):
            out = f(a)
        s.append((time.perf_counter() - t) * 1e6 / w['inner'])
    res[w['id']] = {'us': s, 'out': out}
RESULT = {'load_ms': load, 'res': res}
'''
    el, out = run_child(code, [json.dumps(W)])
    record('lookup.model.load-structures', 'lookup', 'read the identity map, three derived indexes, the names '
           "and the canonical values into dicts (the model's lookup structures)", runs_ms=[out['result']['load_ms']],
           peak_memory_mb=mb(out['peak_wset']), free_before=f0,
           notes="the normalized model is not the application's source; a model baseline only")
    for w in W:
        x = out['result']['res'][w['id']]
        record('lookup.model.' + w['id'], 'lookup', '%s (%s), answered by the model' % (w['desc'], w['op']),
               runs_ms=[u / 1000 for u in x['us']], cold_warm='warm', input_counts=w['args'],
               output_counts={'result': x['out']},
               notes=("per call, 9 samples of %d calls; results count model entities, so they need not equal "
                      "the app's (the model holds the minted seconds, the app view the estate name)") % w['inner'])


MODEL_OPS = [
    ('estates', "RESULT = len(L.jsonl_lines(L.MODEL + 'identity/estates.jsonl'))"),
    ('wines', "RESULT = len(L.jsonl_lines(L.MODEL + 'identity/wines.jsonl'))"),
    ('vintages', "RESULT = len(L.jsonl_lines(L.MODEL + 'identity/vintages.jsonl'))"),
    ('observations', "RESULT = len(L.jsonl_lines(L.MODEL + 'observation/observations.jsonl'))"),
    ('relationships', "RESULT = sum(len(L.jsonl_lines(L.MODEL + t)) for t in ('state/estate-wine.jsonl', "
                      "'state/rank-assertions.jsonl', 'state/classification-memberships.jsonl', "
                      "'state/appellation-memberships.jsonl'))"),
    ('identity-map', "RESULT = len(L.jsonl_lines(L.MODEL + 'identity/identity-map.jsonl'))"),
    ('evidence-links', "RESULT = len(L.jsonl_lines(L.MODEL + 'observation/evidence-links.jsonl'))"),
    ('all-tables', "import model_schema as S\nRESULT = sum(len(L.jsonl_lines(L.MODEL + t)) for t in S.LAYOUT)"),
    ('projection', "import model_reader as R\nP = R.project(classifications={c['id']: c for c in L.g('BDX_CLASSIFICATIONS')})\n"
                   "RESULT = sum(len(v) for g in P.values() if isinstance(g, dict) for v in g.values() if hasattr(v, '__len__'))"),
    ('new-reader', "import importlib.util\nspec = importlib.util.spec_from_file_location('d', L.ROOT + 'tools/dual-read.py')\n"
                   "d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)\nn = d.NewReader()\nRESULT = len(n.obs)"),
    ('derived-indexes', "import glob\nRESULT = sum(len(json.load(open(p, encoding='utf-8'))) for p in glob.glob(L.MODEL + 'derived/*.json'))"),
]


def fam_model():
    f0 = guard('model')
    if f0 is None:
        return
    for name, code in MODEL_OPS:
        runs, peaks, res = [], [], None
        for i in range(3):
            c = 'import migration_lib as L\nt0 = time.perf_counter()\n' + code + \
                '\nRESULT = {"n": RESULT, "ms": (time.perf_counter() - t0) * 1000}'
            el, out = run_child(c)
            runs.append(out['result']['ms'])
            peaks.append(out['peak_wset'])
            res = out['result']['n']
        record('model.read.' + name, 'model', 'read %s from data/model/ in a fresh Python process' % name,
               runs_ms=runs, cold_warm='warm', peak_memory_mb=mb(max(peaks)), output_counts={'records': res},
               free_before=f0, notes='3 repetitions; time inside the process (interpreter start excluded); '
                                     'the OS file cache is warm after the first')


def fam_rebuild():
    f0 = guard('rebuild')
    if f0 is None:
        return
    import model_schema as S
    committed = {rel: open(L.MODEL + rel, 'rb').read() for rel in list(S.LAYOUT) + ['manifest.json']
                 if os.path.exists(L.MODEL + rel)}
    runs, peaks, identical, size, count, temp_used = [], [], [], 0, 0, 0
    for i in range(2):
        tmp = tempfile.mkdtemp(prefix='bdx-bench-model-')
        try:
            el, code, last, pk = poll_peak([sys.executable, L.ROOT + 'tools/migrate.py', '--until', 'M7'],
                                           env=dict(os.environ, BDX_MODEL_DIR=tmp))
            if code:
                raise RuntimeError(last)
            built = {}
            for rel in list(S.LAYOUT) + ['manifest.json']:
                p = os.path.join(tmp, rel)
                if os.path.exists(p):
                    built[rel] = open(p, 'rb').read()
            identical.append(built == committed)
            size = sum(len(b) for b in built.values())
            count = len(built)
            temp_used = max(temp_used, sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fn in os.walk(tmp) for f in fn))
            runs.append(el)
            peaks.append(pk)
            if free_mb() < MIN_FREE_MB:
                record('rebuild.disk-guard', 'disk', 'rebuild', status='STOPPED', free_before=f0, free_after=free_mb())
                return
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    record('rebuild.full', 'rebuild', 'tools/migrate.py --until M7 into an empty temporary directory '
           '(from scratch: no registry), compared byte for byte with data/model/',
           runs_ms=runs, cold_warm='cold', peak_memory_mb=mb(max(peaks)),
           output_counts={'files': count, 'bytes': size, 'byte_identical': all(identical)},
           free_before=f0, free_after=free_mb(), status='OK' if all(identical) else 'DIFFERS',
           notes='2 repetitions (each takes seconds and writes ~%d MB); temporary space used %d MB, removed'
                 % (size // 2**20, temp_used // 2**20),
           extra={'temp_bytes_used': temp_used})
    # Stage timings: the stage functions run in a child, nothing written.
    code = '''
import migrate, importlib, time
m = migrate.Model()
st = {}
for s in migrate.STAGES[1:]:
    mod = importlib.import_module(migrate.MODULES[s])
    t = time.perf_counter(); mod.run(m); st[s] = (time.perf_counter() - t) * 1000
t = time.perf_counter(); errs = migrate.validate(m); st['validate'] = (time.perf_counter() - t) * 1000
t = time.perf_counter(); files = migrate.render(m, 'M7'); st['render'] = (time.perf_counter() - t) * 1000
RESULT = {'stages': st, 'errors': len(errs)}
'''
    el, out = run_child(code)
    for s, ms in out['result']['stages'].items():
        record('rebuild.stage.' + s, 'rebuild', 'stage %s of the migration, in memory (nothing written)' % s,
               runs_ms=[ms], cold_warm='cold', notes='one run, in one child process; stages share the process')
    record('rebuild.in-memory-total', 'rebuild', 'every stage, validation and rendering in one process, nothing written',
           runs_ms=[el], peak_memory_mb=mb(out['peak_wset']), free_before=f0, free_after=free_mb())


# ------------------------------------------------------------------ storage

def allocated(nbytes, cluster):
    return -(-nbytes // cluster) * cluster if nbytes else 0


def cluster_size():
    import ctypes
    spc, bps, fc, tc = (ctypes.c_ulong() for _ in range(4))
    ctypes.windll.kernel32.GetDiskFreeSpaceW(ctypes.c_wchar_p(L.ROOT[:3]), ctypes.byref(spc), ctypes.byref(bps),
                                             ctypes.byref(fc), ctypes.byref(tc))
    return spc.value * bps.value


def categorize(rel):
    r = rel.replace('\\', '/')
    if r.startswith('.git/'):
        return 'repository overhead', '.git'
    if r.startswith('sources/discovery/blobs/'):
        return 'raw/source', 'discovery blobs (content-addressed)'
    if r.startswith('sources/discovery/extracted/'):
        return 'derived or potentially derived', 'discovery extracted text (local)'
    if r.startswith('sources/discovery/derived/'):
        return 'derived or potentially derived', 'discovery derived (local)'
    if r.startswith('sources/discovery/'):
        return 'raw/source', 'discovery crawl state'
    if r.startswith('sources/pages/'):
        return 'raw/source', 'crawled pages (legacy)'
    if r.startswith('sources/fiches/'):
        return 'raw/source', 'technical sheets (legacy)'
    if r.startswith('sources/'):
        return 'raw/source', 'other source artifacts (' + r.split('/')[1] + ')'
    if r.startswith('data/evidence/'):
        return 'authoritative/protected', 'evidence v1-v5'
    if r.startswith('data/discovery/'):
        return 'authoritative/protected', 'discovery data'
    if r.startswith('data/scope/'):
        return 'authoritative/protected', 'scope data'
    if r.startswith('data/review/') or r.startswith('data/audit/'):
        return 'authoritative/protected', 'review and audit records'
    if r.startswith('data/model/derived/'):
        return 'derived or potentially derived', 'model derived indexes'
    if r.startswith('data/model/checks/'):
        return 'derived or potentially derived', 'model check reports'
    if r.startswith('data/model/'):
        return 'authoritative/protected', 'normalized model'
    if r.startswith('data/performance/'):
        return 'derived or potentially derived', 'benchmark outputs'
    if r.startswith('data/') and r.count('/') == 1:
        if r.endswith('.js') or r == 'data/sources.json':
            return 'authoritative/protected', 'canonical data'
        return 'authoritative/protected', 'proposal and audit records (phase records)'
    if r.startswith('docs/'):
        return 'derived or potentially derived', 'reports and docs'
    if r.startswith('tools/__pycache__') or '__pycache__' in r:
        return 'derived or potentially derived', 'caches (__pycache__)'
    if r.startswith('tools/'):
        return 'code', 'tools'
    return 'code', 'application and other'


def fam_storage():
    f0 = guard('storage')
    cl = cluster_size()
    tracked = set(git('ls-files').splitlines())
    agg = collections.defaultdict(lambda: {'bytes': 0, 'allocated': 0, 'physical': 0, 'files': 0,
                                           'tracked_files': 0, 'ext': collections.Counter()})
    seen = set()                 # (device, file id) of files with several links (Phase 5 C3)
    t = time.perf_counter()
    for dp, dn, fn in os.walk(L.ROOT):
        for f in fn:
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, L.ROOT).replace('\\', '/')
            try:
                st = os.stat(p)
            except OSError:
                continue
            n = st.st_size
            cat, sub = categorize(rel)
            a = agg[(cat, sub)]
            a['bytes'] += n
            a['allocated'] += allocated(n, cl)
            # Physical: a hard-linked file counts once, at the first path the walk meets.
            if st.st_nlink > 1:
                if (st.st_dev, st.st_ino) not in seen:
                    seen.add((st.st_dev, st.st_ino))
                    a['physical'] += allocated(n, cl)
            else:
                a['physical'] += allocated(n, cl)
            a['files'] += 1
            a['tracked_files'] += rel in tracked
            ext = os.path.splitext(f)[1].lower()
            if rel.startswith('sources/discovery/blobs/'):
                ext = '.gz' if f.endswith('.gz') else '(raw blob)'
            a['ext'][ext or '(none)'] += n
    walk_ms = (time.perf_counter() - t) * 1000
    inv = {}
    for (cat, sub), a in sorted(agg.items()):
        inv.setdefault(cat, {})[sub] = {'bytes': a['bytes'], 'allocated_bytes': a['allocated'],
                                        'physical_bytes': a['physical'], 'files': a['files'],
                                        'tracked_files': a['tracked_files'],
                                        'by_extension': dict(a['ext'].most_common(8))}
    doc = {'_': 'Phase 5 storage inventory: descriptive, not normative (tools/benchmark-phase5.py). '
                'bytes = logical length; allocated_bytes = rounded up to the %d-byte cluster; '
                'physical_bytes = allocated, a hard-linked file counted once (NTFS compression and '
                'sparse files are not measured).' % cl,
           'commit': environment()['commit'], 'cluster_bytes': cl, 'categories': inv}
    # The M0 inventory stays as it was; a re-measurement writes its own.
    path = INVENTORY if environment()['commit'] == 'b1ce39b' else \
        INVENTORY.replace('.json', '-%s.json' % environment()['commit'])
    open(path, 'w', encoding='utf-8', newline='\n').write(json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
    for cat, subs in inv.items():
        record('storage.' + cat.split('/')[0].replace(' ', '-'), 'storage', cat,
               output_counts={'bytes': sum(v['bytes'] for v in subs.values()),
                              'allocated_bytes': sum(v['allocated_bytes'] for v in subs.values()),
                              'physical_bytes': sum(v['physical_bytes'] for v in subs.values()),
                              'files': sum(v['files'] for v in subs.values())},
               free_before=f0, extra={k: {kk: vv for kk, vv in v.items() if kk != 'by_extension'}
                                      for k, v in subs.items()})
    record('storage.walk', 'storage', 'one walk of the whole working tree (sizes only, nothing hashed)',
           runs_ms=[walk_ms], output_counts={'files': sum(a['files'] for a in agg.values())})


def fam_duplicates():
    f0 = guard('duplicates')
    sheets = L.sources_rows()['sheets']
    import mig_m2_identity as M2
    by_sha = collections.defaultdict(set)
    size = {}
    for r in sheets:
        by_sha[r['sha1']].add(M2.sources_path(r))
        size[r['sha1']] = r['bytes']
    import raw_store
    on_disk = lambda rel: os.path.exists(L.ROOT + 'sources/' + rel)
    by_sha = {s: {p for p in ps if on_disk(p)} for s, ps in by_sha.items()}
    multi = {s: p for s, p in by_sha.items() if len(p) > 1}
    record('duplicates.legacy-same-content-several-paths', 'duplicates', 'manifest sha1 held at several paths',
           output_counts={'digests': len(multi), 'extra_copies': sum(len(p) - 1 for p in multi.values()),
                          'extra_bytes': sum((len(p) - 1) * (size[s] or 0) for s, p in multi.items())},
           free_before=f0, notes='same content, multiple locations (by the manifest\'s digests)')
    locs = collections.defaultdict(set)
    for p in glob.glob(L.ROOT + 'data/discovery/locations/*.jsonl'):
        for d in L.jsonl_lines(p):
            if d.get('sha256'):
                locs[d['sha256']].add(d.get('final_url') or d.get('url'))
    m2 = {s: u for s, u in locs.items() if len(u) > 1}
    record('duplicates.discovery-same-content-several-urls', 'duplicates', 'harvested bytes found at several URLs '
           '(stored once in the blob store)', output_counts={'digests': len(m2),
                                                              'urls': sum(len(u) for u in m2.values())},
           notes='same content, multiple locations; one blob each')
    # legacy file and discovery blob holding the same bytes (proven joins)
    arts = L.jsonl_lines(L.MODEL + 'identity/artifacts.jsonl')
    both = [a for a in arts if 'sha1' in a and 'sha256' in a]
    legacy_at = collections.defaultdict(set)
    for r in sheets:
        legacy_at[r['sha1']].add(M2.sources_path(r))
    twice = [a for a in both if raw_store.blob_path(a['sha256'])
             and any(on_disk(p) for p in legacy_at.get(a['sha1'], ()))]
    record('duplicates.legacy-and-blob-store', 'duplicates', 'bytes held both under sources/fiches|pages and as a '
           'discovery blob', output_counts={'artifacts': len(twice),
                                            'bytes': sum(a.get('bytes') or 0 for a in twice)},
           notes='same content, two stores; a shared digest is identity, not permission to remove a location')
    # evidence versions: the same decision written again by the next version
    def strip(d):
        d = dict(d)
        d.pop('v', None)
        return L.dumps(d)

    def verdict(d):
        c = dict(d.get('ctx') or {})
        return L.dumps([d.get('artifact'), c, d.get('decision'), d.get('code')])
    ev = {}
    for v in (2, 3, 4, 5):
        ev_path = L.ROOT + 'data/evidence/decisions-v%d.jsonl' % v
        rows = L.jsonl_lines(ev_path)
        ev[v] = (collections.Counter(strip(d) for d in rows), os.path.getsize(ev_path),
                 collections.Counter(verdict(d) for d in rows))
    for a, b in ((2, 3), (4, 5)):
        same = sum((ev[a][0] & ev[b][0]).values())
        same_verdict = sum((ev[a][2] & ev[b][2]).values())
        record('duplicates.evidence-v%d-v%d' % (a, b), 'duplicates', 'decisions of v%d identical to v%d apart from '
               'the version number' % (b, a), output_counts={'rows_v%d' % b: sum(ev[b][0].values()),
                                                              'identical_rows': same,
                                                              'same_verdict_rows': same_verdict,
                                                              'bytes_v%d' % b: ev[b][1]},
               notes='identical_rows: whole rows equal but for v (each row also records its commit and reader); '
                     'same_verdict_rows: same artifact, context, decision and code - the same conclusion '
                     'written again by an append-only store (by design)')
    # representations of the same information
    reps = [('fiche values: data/fiches.js vs model observations+canonical',
             ['data/fiches.js'], ['data/model/observation/observations.jsonl', 'data/model/canonical/values.jsonl',
                                  'data/model/reconciliation/reconciliations.jsonl']),
            ('evidence: the store vs the model\'s evidence links', ['data/evidence/decisions-v4.jsonl',
                                                                  'data/evidence/decisions-v5.jsonl'],
             ['data/model/observation/evidence-links.jsonl']),
            ('manifest: sources.json vs model artifacts+placements+attributions+assessments',
             ['data/sources.json'], ['data/model/identity/artifacts.jsonl', 'data/model/document/placements.jsonl',
                                     'data/model/document/attributions.jsonl', 'data/model/document/assessments.jsonl',
                                     'data/model/document/locators.jsonl']),
            ('discovery: observations jsonl vs the extracted text', ['data/discovery/observations'],
             ['sources/discovery/extracted']),
            ('model tables vs derived indexes', ['data/model/state/estate-wine.jsonl',
                                                 'data/model/identity/vintages.jsonl'], ['data/model/derived']),
            ('Dutch: fiches-nl.js vs model translations', ['data/fiches-nl.js'],
             ['data/model/canonical/translations.jsonl'])]
    for name, a, b in reps:
        sa = sum(tree_size(L.ROOT + x)['bytes'] if os.path.isdir(L.ROOT + x) else os.path.getsize(L.ROOT + x) for x in a)
        sb = sum(tree_size(L.ROOT + x)['bytes'] if os.path.isdir(L.ROOT + x) else os.path.getsize(L.ROOT + x) for x in b)
        record('duplicates.representation.' + hashlib.sha1(name.encode()).hexdigest()[:8], 'duplicates', name,
               output_counts={'bytes_a': sa, 'bytes_b': sb}, extra={'a': a, 'b': b},
               notes='same logical information, different representations')
    # identical files anywhere in the tracked data (exact duplicates)
    hs = collections.defaultdict(list)
    for p in git('ls-files', 'data').splitlines():
        if os.path.getsize(L.ROOT + p) > 0:
            hs[hashlib.sha256(open(L.ROOT + p, 'rb').read()).hexdigest()].append(p)
    d = {h: ps for h, ps in hs.items() if len(ps) > 1}
    record('duplicates.tracked-identical-files', 'duplicates', 'byte-identical tracked files under data/',
           output_counts={'groups': len(d), 'files': sum(len(x) for x in d.values())},
           extra={h[:12]: ps for h, ps in sorted(d.items())[:20]})


def fam_large():
    F, C = L.g('BDX_FICHES'), L.g('BDX_CUVEES')
    recs = collections.Counter()
    for name in ('BDX_FICHES', 'BDX_RATINGS', 'BDX_CELLAR', 'BDX_FICHE_URL'):
        for k in L.g(name):
            recs[k.split('|')[0]] += 1
    for name in ('BDX_CUVEES', 'BDX_CUVEE_URL'):
        for k in L.g(name):
            recs[k.split('|')[0]] += 1
    wv = collections.Counter('|'.join(k.split('|')[:2]) for k in C)
    docs = collections.Counter(r['estate'] for r in L.sources_rows()['sheets'] if r['estate'])

    def largest(globpat):
        fs = [p for p in glob.glob(L.ROOT + globpat, recursive=True) if os.path.isfile(p)]
        p = max(fs, key=os.path.getsize)
        return {'path': L.rel(p), 'bytes': os.path.getsize(p)}
    record('large.cases', 'large', 'the largest cases present', output_counts={
        'estate_most_records': recs.most_common(1)[0], 'estate_most_fiches': collections.Counter(
            k.split('|')[0] for k in F).most_common(1)[0], 'wine_most_vintages': wv.most_common(1)[0],
        'estate_most_documents': docs.most_common(1)[0]},
        extra={'largest_model_file': largest('data/model/**/*.jsonl'),
               'largest_discovery_file': largest('data/discovery/**/*'),
               'largest_evidence_file': largest('data/evidence/*'),
               'largest_canonical_file': largest('data/*.js'),
               'largest_raw_file': largest('sources/**/*')},
        notes='benchmarked as: lookup.app.estate.large, estate-all-vintages.large, wine.many-vintages; '
              'search.many-matches (the broadest search); model.read.all-tables and model.read.projection '
              '(the largest in-memory loads)')
    # the largest estate's every record, through the model's projection path
    code = '''
import model_reader as R, migration_lib as L, time
t = time.perf_counter()
P = R.project(classifications={c['id']: c for c in L.g('BDX_CLASSIFICATIONS')})
load = (time.perf_counter() - t) * 1000
e = sys.argv[1]
t = time.perf_counter()
n = 0
for g in P.values():
    if isinstance(g, dict):
        for name, v in g.items():
            if isinstance(v, dict):
                n += sum(1 for k in v if k.split('|')[0] == e)
RESULT = {'load_ms': load, 'scan_ms': (time.perf_counter() - t) * 1000, 'records': n}
'''
    el, out = run_child(code, [recs.most_common(1)[0][0]])
    record('large.estate-every-record.model', 'large', 'every record of the estate with the most, read through the '
           'model projection (a full projection, then a scan)', runs_ms=[out['result']['load_ms'] + out['result']['scan_ms']],
           peak_memory_mb=mb(out['peak_wset']), input_counts={'estate': recs.most_common(1)[0][0]},
           output_counts={'records': out['result']['records'], 'projection_ms': round(out['result']['load_ms']),
                          'scan_ms': round(out['result']['scan_ms'], 1)})


FAMILIES = collections.OrderedDict([('env', fam_env), ('storage', fam_storage), ('duplicates', fam_duplicates),
                                    ('large', fam_large), ('model', fam_model), ('rebuild', fam_rebuild),
                                    ('startup', fam_startup), ('search', fam_search), ('lookup', fam_lookup),
                                    ('suite', fam_suite)])


def main():
    only = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else list(FAMILIES)
    f0 = free_mb()
    record('run.start', 'disk', 'free disk at the start of the run', free_before=f0, extra=environment())
    for name in only:
        FAMILIES[name]()
    record('run.end', 'disk', 'free disk at the end of the run', free_before=f0, free_after=free_mb())


if __name__ == '__main__':
    main()
