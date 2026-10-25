"""Phase 6.9: the vintage list's heading names the reference's years; sheets outside them are said.

    python tools/test-phase69.py

Read-only. The heading above every wine's vintage list was "All vintages,
1982-2025" for a grand vin and "<current name>, 1982-2025" for any other
wine, read as that name across those years (docs/PHASE-6.8-HEADING-
SEMANTICS-AUDIT.md). It is now "Vintages 1982-2025 in this reference" for
every wine, the span still the regional vintage file's. The block of what is
established about the wine (Phase 6.7) says how many of its sheets lie
outside the years listed, so a 2026 sheet or a 1978 one is neither dropped
nor given a row; and it now counts every sheet record, those that name a
document with no figure taken from it included. These checks hold every one
of the 593 wines to that, the generated change to exactly that, and the
cases the audit named to what they were.
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import migration_lib as L  # noqa: E402

BEFORE = 'aaa90c6'               # Phase 6.7: the application before this phase
CHECKS = []
SPAN = sorted(int(y) for y in L.g('BDX_VINTAGES'))
HEADING = 'Vintages %d–%d in this reference' % (SPAN[0], SPAN[-1])


def check(f):
    CHECKS.append(f)
    return f


def tool(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_')[:-3], L.ROOT + 'tools/' + name)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode()


def established(text=None):
    s = text if text is not None else open(L.ROOT + 'data/app/wine-established.js', encoding='utf-8').read()
    return json.loads(re.search(r'window\.BDX_WINE_ESTABLISHED = (.*);\n', s).group(1))


def outside(f):
    ys = f.get('y', [])
    return sum(1 for y in ys if y < SPAN[0]), sum(1 for y in ys if y > SPAN[-1])


def sheets_line(f):
    if not f.get('s'):
        return 'none'
    n, a, z = f['s']
    line = ('%d vintage, %d' % (n, a)) if n == 1 else ('%d vintages, %d–%d' % (n, a, z))
    before, after = outside(f)
    if before:
        line += '; %d before the years listed below' % before
    if after:
        line += '; %d after the years listed below' % after
    return line


# ---------------------------------------------------------------- every wine, in the page

SWEEP_JS = '''(function (keys) {
  var out = {};
  document.getElementById('tabProducers').click();
  var box = document.getElementById('search');
  keys.forEach(function (key) {
    var p = key.split('|'), id = p[0], slug = p[1];
    if (box.value !== '') { box.value = ''; box.dispatchEvent(new Event('input')); }
    var card = document.querySelector('#paneList .pcard[data-ch="' + id + '"]');
    if (!card) { out[key] = {missing: 'card'}; return; }
    card.click();
    var sel = document.getElementById('wineSel');
    if (slug !== 'grand') {
      if (!sel || !Array.prototype.some.call(sel.options, function (o) { return o.value === slug; })) {
        out[key] = {missing: 'wine'}; document.getElementById('closeDrawer').click(); return;
      }
      sel.value = slug; sel.dispatchEvent(new Event('change'));
    }
    var list = document.querySelector('#drawerBody .vintagelist');
    var h3 = list.parentNode.querySelector('h3');
    var est = document.querySelector('#drawerBody .wine-est'), sheets = null;
    if (est) Array.prototype.forEach.call(est.querySelectorAll('.we-row'), function (r) {
      if (r.querySelector('dt').textContent === 'Sheets on file') sheets = r.querySelector('dd').innerText; });
    out[key] = {title: h3.firstChild.textContent, hint: h3.querySelector('.hint').textContent,
                sheets: sheets, estate: document.querySelector('#drawerHead h2').textContent,
                wine: sel ? sel.options[sel.selectedIndex].textContent.split(' — ')[0] : null,
                /* the main list's rows; a grand vin's "Earlier vintages" section is separate */
                rows: Array.prototype.map.call(list.querySelectorAll('.vrow[data-year]'),
                  function (r) { return +r.getAttribute('data-year'); }),
                early: Array.prototype.map.call(document.querySelectorAll('#drawerBody .vintagelist'),
                  function (l) { return l; }).slice(1).reduce(function (n, l) {
                    return n + l.querySelectorAll('.vrow[data-year]').length; }, 0),
                focusableHeading: h3.querySelectorAll('a, button, [tabindex]').length};
    document.getElementById('closeDrawer').click();
  });
  return out;
})'''
_sweep = {}


def sweep(root=None):
    key = root or 'now'
    if key not in _sweep:
        B = tool('benchmark-phase5.py')
        with B.Server(root) as srv, B.Browser() as b:
            b.c.send('Runtime.enable')
            b.navigate(srv.url)
            time.sleep(0.5)
            res = b.c.js('%s(%s)' % (SWEEP_JS, json.dumps(sorted(established()))))
            res['__errors'] = len([e for e in b.c.events if e.get('method') == 'Runtime.exceptionThrown'])
        _sweep[key] = res
    return _sweep[key]


def shown():
    return {k: v for k, v in sweep().items() if k != '__errors' and 'missing' not in v}


@check
def every_wine_uses_the_reference_heading():
    s = sweep()
    assert s['__errors'] == 0
    w = shown()
    assert len(w) >= 590, ('most wines reachable in the page', len(w))
    for k, v in w.items():
        assert v['title'] == HEADING, (k, v['title'])


@check
def the_heading_names_no_wine_and_no_estate():
    for k, v in shown().items():
        assert v['wine'] is None or v['wine'] not in v['title'], (k, v['title'])
        assert v['estate'] not in v['title'], (k, v['title'])


@check
def grand_vins_no_longer_say_all_vintages():
    js = open(L.ROOT + 'assets/app.js', encoding='utf-8').read()
    assert "'All vintages, '" not in js
    for k, v in shown().items():
        assert not v['title'].startswith('All vintages'), k


@check
def the_heading_is_not_a_control_and_the_list_is_the_reference_span():
    g = established()
    for k, v in shown().items():
        assert v['focusableHeading'] == 0, k
        assert v['rows'] == sorted(SPAN, reverse=True), (k, 'the list is the reference years, unchanged')
        # the separate earlier section holds exactly a grand vin's sheets before the span, as before
        before, _ = outside(g[k])
        assert v['early'] == (before if k.endswith('|grand') else 0), (k, v['early'], before)


@check
def english_and_dutch_heading_and_hint_exist():
    nl = open(L.ROOT + 'assets/i18n.js', encoding='utf-8').read()
    assert r"[/^Vintages (\d+)–(\d+) in this reference$/, 'Jaargangen $1–$2 in deze gids']," in nl
    assert r"[/^(\d+) of (\d+) with a sheet on file$/, '$1 van $2 met een fiche in het archief']," in nl
    assert "'before the years listed below': 'vóór de jaren hieronder'," in nl
    assert "'after the years listed below': 'na de jaren hieronder'," in nl
    B = tool('benchmark-phase5.py')
    with B.Server() as srv, B.Browser() as b:
        b.navigate(srv.url)
        time.sleep(0.5)
        b.c.js("BDX_LANG.set('nl', function () {})")
        time.sleep(0.5)
        got = {}
        for lid, slug in (('lynch-bages', 'grand'), ('lynch-bages', 'echo-de-lynch-bages'),
                          ('margaux', 'pavillon-rouge-du-chateau-margaux'), ('haut-bailly', 'grand')):
            b.c.js("document.getElementById('tabProducers').click();"
                   "document.querySelector('#paneList .pcard[data-ch=\"%s\"]').click();" % lid)
            if slug != 'grand':
                b.c.js("var s = document.getElementById('wineSel'); s.value = '%s'; s.dispatchEvent(new Event('change'));" % slug)
            time.sleep(0.4)
            got[(lid, slug)] = b.c.js('''(function () {
              var h3 = document.querySelector('#drawerBody .vintagelist').parentNode.querySelector('h3');
              var r = {title: h3.firstChild.textContent, hint: h3.querySelector('.hint').textContent,
                       block: document.querySelector('#drawerBody .wine-est').innerText};
              document.getElementById('closeDrawer').click(); return r; })()''')
    for case, r in got.items():
        assert r['title'] == 'Jaargangen %d–%d in deze gids' % (SPAN[0], SPAN[-1]), (case, r['title'])
    assert got[('lynch-bages', 'echo-de-lynch-bages')]['hint'] == '13 van 44 met een fiche in het archief', got
    assert '4 vóór de jaren hieronder' in got[('margaux', 'pavillon-rouge-du-chateau-margaux')]['block']
    assert '1 na de jaren hieronder' in got[('haut-bailly', 'grand')]['block']


@check
def sheet_coverage_stated_for_every_wine():
    g = established()
    for k, v in shown().items():
        assert v['sheets'] == sheets_line(g[k]), (k, v['sheets'], sheets_line(g[k]))


@check
def coverage_inside_the_range_is_worded_as_before():
    # A wine whose sheets all lie within the years listed reads exactly as Phase 6.7 had it.
    old = established(git('show', BEFORE + ':data/app/wine-established.js'))
    n = 0
    for k, v in shown().items():
        f = established()[k]
        if f.get('s') and outside(f) == (0, 0) and old[k].get('s') == f['s']:
            a, z = f['s'][1], f['s'][2]
            was = ('%d vintage, %d' % (f['s'][0], a)) if f['s'][0] == 1 else ('%d vintages, %d–%d' % (f['s'][0], a, z))
            assert v['sheets'] == was, (k, v['sheets'], was)
            n += 1
    assert n > 300, n


@check
def outside_range_sheets_are_counted_and_said():
    g, w = established(), shown()
    out = {k: outside(f) for k, f in g.items() if outside(f) != (0, 0)}
    assert len(out) == 19, len(out)
    for k, (before, after) in out.items():
        line = w[k]['sheets']
        assert (('; %d before the years listed below' % before) in line) == bool(before), (k, line)
        assert (('; %d after the years listed below' % after) in line) == bool(after), (k, line)


@check
def sheets_after_the_range_get_no_row():
    g, w = established(), shown()
    late = sorted(k for k, f in g.items() if f.get('s') and f['s'][2] > SPAN[-1])
    assert late == ['haut-bailly|grand', 'la-tour-blanche|grand', 'langoa-barton|grand',
                    'leoville-barton|grand', 'lynch-moussas|grand'], late
    for k in late:
        assert max(w[k]['rows']) == SPAN[-1] and SPAN[-1] + 1 not in w[k]['rows'], k
        assert '; 1 after the years listed below' in w[k]['sheets'], (k, w[k]['sheets'])
        assert (SPAN[-1] + 1) in g[k]['y'], 'the late sheet is kept in the data'
    assert w['haut-bailly|grand']['sheets'] == '28 vintages, 1998–2026; 1 after the years listed below'


@check
def pavillons_earlier_sheets_are_not_lost():
    g, w = established(), shown()
    for k in ('margaux|pavillon-rouge-du-chateau-margaux', 'margaux|pavillon-blanc-du-chateau-margaux'):
        assert g[k]['s'] == [48, 1978, 2025] and g[k]['y'][:4] == [1978, 1979, 1980, 1981], g[k]['s']
        assert w[k]['sheets'] == '48 vintages, 1978–2025; 4 before the years listed below', w[k]['sheets']
        assert w[k]['hint'] == '44 of 44 with a sheet on file', 'the hint still counts the years listed'


@check
def not_made_years_unchanged():
    old = established(git('show', BEFORE + ':data/app/wine-established.js'))
    g = established()
    for k in g:
        assert g[k].get('x') == old[k].get('x'), k
    assert g['yquem|grand']['x'] == [1992, 2012, 2018]
    assert g['climens|grand']['x'] == [1984, 1987, 1992, 1993, 2012, 2017]


@check
def unresolved_cases_stay_as_they_were():
    B = tool('benchmark-phase5.py')
    with B.Server() as srv, B.Browser() as b:
        b.navigate(srv.url)
        time.sleep(0.5)
        got = {}
        for lid, slug in (('lynch-bages', 'echo-de-lynch-bages'), ('haut-bailly', 'haut-bailly-ii'),
                          ('batailley', 'lions-de-batailley')):
            got[slug] = b.c.js('''(function (id, slug) {
              document.getElementById('tabProducers').click();
              document.querySelector('#paneList .pcard[data-ch="' + id + '"]').click();
              var s = document.getElementById('wineSel'); s.value = slug; s.dispatchEvent(new Event('change'));
              var d = document.getElementById('drawerBody').innerText;
              document.getElementById('closeDrawer').click(); return d; })(%s, %s)''' % (json.dumps(lid), json.dumps(slug)))
    echo = got['echo-de-lynch-bages']
    assert 'Haut-Bages' not in echo and 'renamed' not in echo
    assert 'When it was adopted, and any earlier names, are not recorded.' in echo
    hb = got['haut-bailly-ii']
    assert 'Which wine is the estate’s second wine is not established' in hb and 'renamed' not in hb
    assert 'Not established' in hb, 'the estate fact keeps its Phase 6.3 state'
    lions = got['lions-de-batailley']
    assert 'Conflicting records' in lions and 'The estate’s records conflict about its second wine' in lions


@check
def phone_width_is_clean():
    B = tool('benchmark-phase5.py')
    with B.Server() as srv, B.Browser() as b:
        b.c.send('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
        b.navigate(srv.url)
        time.sleep(0.5)
        r = b.c.js('''(function () {
          document.getElementById('tabProducers').click();
          document.querySelector('#paneList .pcard[data-ch="margaux"]').click();
          var s = document.getElementById('wineSel'); s.value = 'pavillon-rouge-du-chateau-margaux'; s.dispatchEvent(new Event('change'));
          var h3 = document.querySelector('#drawerBody .vintagelist').parentNode.querySelector('h3');
          var e = document.querySelector('#drawerBody .wine-est');
          return {h3fits: h3.scrollWidth <= h3.clientWidth + 1, estfits: e.scrollWidth <= e.clientWidth + 1,
                  page: document.documentElement.scrollWidth}; })()''')
    assert r['h3fits'] and r['estfits'] and r['page'] <= 390, r


@check
def keyboard_path_unchanged():
    # Tab from the wine selector still reaches the first vintage row, nothing in between.
    B = tool('benchmark-phase5.py')
    with B.Server() as srv, B.Browser() as b:
        b.navigate(srv.url)
        time.sleep(0.5)
        b.c.js("document.getElementById('tabProducers').click();"
               "document.querySelector('#paneList .pcard[data-ch=\"lynch-bages\"]').click();"
               "document.getElementById('wineSel').focus();")
        steps = 0
        for steps in range(1, 31):
            for t in ('rawKeyDown', 'keyUp'):
                b.c.send('Input.dispatchKeyEvent', {'type': t, 'key': 'Tab', 'code': 'Tab', 'windowsVirtualKeyCode': 9})
            a = b.c.js('''(function () { var a = document.activeElement;
              return {head: a.classList.contains('vrow-head'), inH3: !!(a.closest && a.closest('h3')),
                      year: a.closest && a.closest('.vrow') ? a.closest('.vrow').getAttribute('data-year') : null}; })()''')
            assert not a['inH3'], 'focus stopped in the heading'
            if a['head']:
                break
    assert a['head'] and a['year'] == str(SPAN[-1]) and steps == 1, (a, steps)


@check
def generated_change_is_exactly_the_sheet_years_and_the_three_counts():
    bad = tool('build-app-data.py')
    a, b2 = bad.render(), bad.render()
    assert a == b2, 'generation is not deterministic'
    for f, data in a.items():
        assert open(L.ROOT + 'data/app/' + f, 'rb').read() == data, f
    changed = git('diff', '--name-only', BEFORE, '--', 'data/app').split()
    assert changed == ['data/app/wine-established.js'], changed
    old, new = established(git('show', BEFORE + ':data/app/wine-established.js')), established()
    assert set(old) == set(new)
    counts_changed = []
    for k in new:
        o, n = old[k], dict(new[k])
        assert ('y' in n) == ('s' in n), k
        n.pop('y', None)
        if n.get('s') != o.get('s'):
            counts_changed.append(k)
            n.pop('s')
            o = {kk: v for kk, v in o.items() if kk != 's'}
        assert n == o, ('anything but the sheet years and counts changed', k)
    assert sorted(counts_changed) == ['latour-martillac|grand', 'malescot|grand', 'prieure-lichine|grand'], counts_changed
    # each correction is a sheet record that names its document and has no figure taken from it
    T = L.read_table
    obs = {o['extraction']['record'] for o in T('observation/observations.jsonl')
           if o['extraction']['file'] in ('data/fiches.js', 'data/cuvees.js')}
    refs = {r['record_key'] for r in T('document/legacy-references.jsonl')
            if r['origin'] == 'fiches.js' and r.get('field') is None}
    for k in counts_changed:
        est = k.split('|')[0]
        added = set(new[k]['y']) - {int(r.split('|')[1]) for r in obs if r.startswith(est + '|') and r.count('|') == 1}
        assert len(added) == 1 and new[k]['s'][0] == old[k]['s'][0] + 1, (k, added)
        assert '%s|%d' % (est, added.pop()) in refs, k


@check
def model_and_protected_data_unchanged():
    assert not git('diff', '--stat', BEFORE, '--', 'data/model').strip(), 'the model changed'
    assert not git('diff', '--stat', BEFORE, '--', ':(glob)data/*.js', 'data/sources.json', 'data/evidence',
                   'data/discovery').strip()
    b = json.load(open(L.MODEL + 'baseline.json', encoding='utf-8'))['groups']
    for g in ('canonical', 'evidence', 'discovery', 'scope', 'phase_records'):
        assert L.group_hashes(g)['digest'] == b[g]['digest'], g


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
