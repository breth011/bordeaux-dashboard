"""Phase 5: the application's observable outputs, captured and compared.

    python tools/app-reference.py --capture            capture the running application into
                                                       tools/fixtures/app-reference.json (the control)
    python tools/app-reference.py --compare            capture again and compare with the control
    ... --root DIR                                     use a copy of the site instead of the repository

The page (index.html, assets/app.js, the data files it loads) is served by a
local http.server and driven in headless Chrome through the DevTools protocol
(tools/benchmark-phase5.py). What is captured, from the live page after init():

  globals     every window.BDX_* the page holds, value by value (a hash per key or
              per element) and the order of every list
  estates     the expanded estate list app.js builds (window.BDX_CHATEAUX after init)
  search      the list cards and autocomplete rows each query of the benchmark yields
  lookups     the app's own lookups (copied verbatim, tools/benchmark-phase5.py LOOKUP_JS)
  pages       the rendered detail drawer of representative estates, for each of their
              wines, and with vintage rows opened
  health      JavaScript exceptions, console errors, failed or non-2xx requests

The control is a fixture of hashes, counts and orders, not a copy of the data.
A comparison classifies every difference:

  IDENTICAL
  EXPECTED: PRESENTATION ORDER   the same records in another order: the model holds no
                                 display order (Phase 4 M8 classified it; the reordering is
                                 accepted and presentation order is on the backlog)
  UNEXPLAINED                    anything else: a failure
"""
import collections
import hashlib
import importlib.util
import json
import os
import sys
import time

import migration_lib as L

FIXTURE = L.ROOT + 'tools/fixtures/app-reference.json'
_spec = importlib.util.spec_from_file_location('bench', L.ROOT + 'tools/benchmark-phase5.py')
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)

# assets/app.js acSearch: places.slice(0, 3).concat(starts, words, inside).slice(0, 9)
AC_LIMIT = 9
QUERIES = [q for _, q in B.SEARCH] + ['margaux', 'saint-emilion', 'blanc', 'second', 'echo']
ESTATES = ['lafite', 'margaux', 'haut-brion', 'yquem', 'lynch-bages', 'saint-pierre', 'caillou',
           'smith-haut-lafitte', 'stem-chateau-badette', 'bourgeois-chateau-beaumont',
           'artisan-chateau-de-lauga', 'commanderie-lalande', 'pomerol-chateau-l-enclos']

GLOBALS_JS = '''(function () {
  function h(s) {                       /* FNV-1a, 64-bit as two 32-bit halves */
    var a = 0x811c9dc5, b = 0x01000193 ^ 0x5bd1e995;
    for (var i = 0; i < s.length; i++) {
      var c = s.charCodeAt(i);
      a = Math.imul(a ^ c, 0x01000193) >>> 0; b = Math.imul(b ^ c, 0x5bd1e995) >>> 0;
    }
    return ('00000000' + a.toString(16)).slice(-8) + ('00000000' + b.toString(16)).slice(-8);
  }
  function canon(v) {
    if (v === undefined) return 'undefined';
    if (typeof v === 'function') return 'function';
    if (v === null || typeof v !== 'object') return JSON.stringify(v);
    if (Array.isArray(v)) return '[' + v.map(canon).join(',') + ']';
    return '{' + Object.keys(v).sort().map(function (k) { return JSON.stringify(k) + ':' + canon(v[k]); }).join(',') + '}';
  }
  var out = {};
  Object.keys(window).filter(function (k) { return k.indexOf('BDX_') === 0; }).sort().forEach(function (g) {
    var v = window[g];
    if (Array.isArray(v)) {
      out[g] = {kind: 'list', items: v.map(function (x) {
        var id = (x && typeof x === 'object' && !Array.isArray(x) && x.id) ? x.id : null;
        return [id, h(canon(x))];
      })};
    } else if (v && typeof v === 'object') {
      var m = {};
      Object.keys(v).forEach(function (k) {
        var x = v[k];
        m[k] = Array.isArray(x) ? {kind: 'list', items: x.map(function (y) { return h(canon(y)); })} : h(canon(x));
      });
      out[g] = {kind: 'map', keys: Object.keys(v), items: m};
    } else {
      out[g] = {kind: 'value', items: h(canon(v))};
    }
  });
  return out;
})()'''

SEARCH_SET_JS = '''(function (q) {
  var box = document.getElementById('search');
  box.value = q; box.dispatchEvent(new Event('input'));
  var cards = Array.prototype.map.call(document.querySelectorAll('#paneList .pcard'), function (b) { return b.getAttribute('data-ch'); });
  var ac = Array.prototype.map.call(document.querySelectorAll('.acrow'), function (b) { return b.getAttribute('data-ch') || b.textContent; });
  var label = (document.getElementById('resultcount') || {}).textContent || '';
  box.value = ''; box.dispatchEvent(new Event('input'));
  return {cards: cards, ac: ac, label: label};
})'''

DRAWER_JS = '''(function (id) {
  var box = document.getElementById('search');
  box.value = ''; box.dispatchEvent(new Event('input'));
  var card = document.querySelector('#paneList .pcard[data-ch="' + id + '"]');
  if (!card) return {missing: true};
  card.click();
  function text() {
    return (document.getElementById('drawerHead').innerText + '\\n' + document.getElementById('drawerBody').innerText);
  }
  var states = [];
  var sel = document.getElementById('wineSel');
  var wines = sel ? Array.prototype.map.call(sel.options, function (o) { return o.value; }) : ['grand'];
  wines.forEach(function (w) {
    var s = document.getElementById('wineSel');
    if (s && s.value !== w) { s.value = w; s.dispatchEvent(new Event('change')); }
    var rows = Array.prototype.slice.call(document.querySelectorAll('#drawerBody .vrow[data-year]'));
    var st = {wine: w, text: text(), years: rows.map(function (r) { return r.getAttribute('data-year'); }), opened: []};
    rows.slice(0, 3).forEach(function (r) {
      var y = r.getAttribute('data-year');
      var again = document.querySelector('#drawerBody .vrow[data-year="' + y + '"]');
      if (again) { again.click(); st.opened.push([y, text()]); }
    });
    states.push(st);
  });
  var close = document.getElementById('closeDrawer');
  if (close) close.click();
  return {states: states};
})'''


def sha(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()[:16]


def capture(root=None):
    errors = []
    with B.Server(root) as srv, B.Browser() as b:
        c = b.c
        c.send('Runtime.enable')
        c.send('Log.enable')
        c.send('Network.enable')
        b.navigate(srv.url)
        time.sleep(0.5)
        out = {'globals': c.js(GLOBALS_JS)}
        c.js("document.getElementById('tabProducers').click()")
        time.sleep(0.3)
        out['producers_list'] = c.js("Array.prototype.map.call(document.querySelectorAll('#paneList .pcard'),"
                                     "function (b) { return b.getAttribute('data-ch'); })")
        out['search'] = {q: c.js('%s(%s)' % (SEARCH_SET_JS, json.dumps(q))) for q in QUERIES}
        W = B.workloads()
        out['lookups'] = {k: v['out'] for k, v in c.js('%s(%s)' % (B.LOOKUP_JS, json.dumps(
            [dict(w, inner=1) for w in W]))).items()}
        pages = {}
        for e in ESTATES:
            r = c.js('%s(%s)' % (DRAWER_JS, json.dumps(e)))
            if r.get('missing'):
                pages[e] = {'missing': True}
                continue
            pages[e] = [{'wine': s['wine'], 'text': sha(s['text']), 'chars': len(s['text']),
                         'years': s['years'], 'opened': [[y, sha(t)] for y, t in s['opened']],
                         'empty': not s['text'].strip()} for s in r['states']]
        out['pages'] = pages
        for e in c.events:
            m = e.get('method')
            p = e.get('params', {})
            if m == 'Runtime.exceptionThrown':
                errors.append('exception: ' + json.dumps(p.get('exceptionDetails', {}).get('text'))[:200])
            elif m == 'Log.entryAdded' and p.get('entry', {}).get('level') == 'error':
                errors.append('console: ' + p['entry'].get('text', '')[:200])
            elif m == 'Network.loadingFailed' and not p.get('canceled'):
                errors.append('request failed: ' + p.get('errorText', ''))
            elif m == 'Network.responseReceived' and p.get('response', {}).get('status', 200) >= 400:
                errors.append('HTTP %s %s' % (p['response']['status'], p['response']['url']))
        data_urls = sorted({e['params']['response']['url'].split('/', 3)[3] for e in c.events
                            if e.get('method') == 'Network.responseReceived'
                            and '/data/' in e['params']['response']['url']})
        out['data_requests'] = data_urls
    out['health'] = errors
    return out


def compare(ref, now):
    res = collections.Counter()
    unexplained = []
    ordered = []

    def same(kind, where, a, b):
        if a == b:
            res['IDENTICAL'] += 1
            return
        if kind == 'list' and isinstance(a, list) and sorted(map(json.dumps, a)) == sorted(map(json.dumps, b)):
            res['EXPECTED: PRESENTATION ORDER'] += 1
            ordered.append(where)
            return
        res['UNEXPLAINED'] += 1
        unexplained.append(where)

    for g in sorted(set(ref['globals']) | set(now['globals'])):
        a, b = ref['globals'].get(g), now['globals'].get(g)
        if a is None or b is None or a['kind'] != b['kind']:
            same('value', 'global %s' % g, a, b)
            continue
        if a['kind'] == 'map':
            for k in sorted(set(a['items']) | set(b['items'])):
                x, y = a['items'].get(k), b['items'].get(k)
                if isinstance(x, dict) and isinstance(y, dict):
                    same('list', 'global %s[%s]' % (g, k), x['items'], y['items'])
                else:
                    same('value', 'global %s[%s]' % (g, k), x, y)
            same('list', 'global %s key order' % g, a['keys'], b['keys'])
        else:
            same(a['kind'], 'global %s' % g, a['items'], b['items'])
    same('list', 'producers list', ref['producers_list'], now['producers_list'])
    for q in ref['search']:
        x, y = ref['search'][q], now['search'].get(q, {})
        same('list', 'search %r cards' % q, x['cards'], y.get('cards'))
        ac_x, ac_y = x['ac'], y.get('ac') or []
        if ac_x != ac_y and len(ac_x) == len(ac_y) == AC_LIMIT \
                and sorted(x['cards']) == sorted(y.get('cards') or []) \
                and [r for r in ac_x if r not in x['cards']] == [r for r in ac_y if r not in y['cards']] \
                and all(r in y['cards'] for r in ac_y if r not in ac_x):
            # The autocomplete shows the first AC_LIMIT matches in the estate list's
            # order: another order picks other, equally valid, matches. Proven here:
            # same card set, same place rows, every shown estate a match.
            res['EXPECTED: PRESENTATION ORDER'] += 1
            ordered.append('search %r autocomplete (top %d of a reordered list)' % (q, AC_LIMIT))
        else:
            same('list', 'search %r autocomplete' % q, ac_x, ac_y)
        same('value', 'search %r label' % q, x['label'], y.get('label'))
    for k in ref['lookups']:
        same('value', 'lookup %s' % k, ref['lookups'][k], now['lookups'].get(k))
    for e in ref['pages']:
        same('value', 'page %s' % e, ref['pages'][e], now['pages'].get(e))
    same('value', 'health', ref['health'], now['health'])
    return {'summary': dict(res), 'unexplained': unexplained, 'presentation_order': ordered}


def main():
    a = sys.argv[1:]
    root = (a[a.index('--root') + 1].replace('\\', '/').rstrip('/') + '/') if '--root' in a else None
    now = capture(root)
    if '--capture' in a:
        os.makedirs(os.path.dirname(FIXTURE), exist_ok=True)
        doc = {'_': 'Phase 5 control: the application\'s observable outputs under the legacy source, '
                    'as hashes, counts and orders (tools/app-reference.py). A comparison fixture, '
                    'not a source of truth.', 'commit': B.git('rev-parse', '--short', 'HEAD'), **now}
        open(FIXTURE, 'w', encoding='utf-8', newline='\n').write(json.dumps(doc, ensure_ascii=False, indent=1,
                                                                             sort_keys=True) + '\n')
        L.out('captured: %d globals, %d estates in the list, %d searches, %d pages; health: %s' % (
            len(now['globals']), len(now['producers_list']), len(now['search']), len(now['pages']),
            now['health'] or 'clean'))
        return
    ref = json.load(open(FIXTURE, encoding='utf-8'))
    r = compare(ref, now)
    L.out(json.dumps(r['summary']))
    for w in r['unexplained'][:30]:
        L.out('  UNEXPLAINED ' + w)
    L.out('presentation order differs in: %d place(s)' % len(r['presentation_order']))
    L.out('data requests: %d (%s)' % (len(now['data_requests']), 'data/app' if all(
        u.startswith('data/app/') or u.split('/')[-1] not in B_contract() for u in now['data_requests'])
        else 'legacy'))
    sys.exit(1 if r['unexplained'] else 0)


def B_contract():
    spec = importlib.util.spec_from_file_location('bad', L.ROOT + 'tools/build-app-data.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return set(m.CONTRACT)


if __name__ == '__main__':
    main()
