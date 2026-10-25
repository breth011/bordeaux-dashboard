"""Phase 6.7: what is established about each wine, shown above its vintage list.

    python tools/test-phase67.py

Read-only. The facts come from the model (tools/build-app-data.py
wine_established, written to data/app/wine-established.js); the drawer shows
them for the selected wine (assets/app.js wineEstablished), and Compare's
vertical view says once that its rank and appellation are current values.
These checks hold the generated data to the model, re-derived here from the
model's own tables; the page to the generated data on the cases the design
named (docs/NEXT-PHASE-LONGITUDINAL-VINTAGE-DESIGN.md); and the semantics:
nothing is dated or renamed that the model does not date or rename, and a
year without a sheet is never shown as a year the wine was not made.
"""
import collections
import importlib.util
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import migration_lib as L  # noqa: E402

BEFORE = 'aa75bf7'               # the design audit: the application before this phase
CHECKS = []


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


def generated():
    s = open(L.ROOT + 'data/app/wine-established.js', encoding='utf-8').read()
    return json.loads(re.search(r'window\.BDX_WINE_ESTABLISHED = (.*);\n', s).group(1))


# ---------------------------------------------------------------- the generated data

@check
def generated_is_the_model_and_deterministic():
    bad = tool('build-app-data.py')
    assert generated() == bad.wine_established(), 'data/app/wine-established.js is not the model'
    a, b = bad.render(), bad.render()
    assert a == b, 'generation is not deterministic'
    assert open(L.ROOT + 'data/app/wine-established.js', 'rb').read() == a['wine-established.js']


@check
def every_fact_is_a_model_record():
    # Re-derived here from the model's tables, independently of the generator.
    T = L.read_table
    key_of = {}
    for r in T('identity/identity-map.jsonl'):
        if r['namespace'] == 'grand-vin' and r.get('stable_id'):
            key_of[r['stable_id']] = r['legacy_key'] + '|grand'
        elif r['namespace'] == 'wine-by-slug' and r.get('stable_id'):
            key_of[r['stable_id']] = r['legacy_key']
    g = generated()
    assert set(g) == set(key_of.values()), 'one record per wine the page can show'
    names = {n['subject']: n for n in T('identity/names.jsonl') if n['kind'] == 'CURRENT'}
    rel = {r['id']: r for r in T('state/estate-wine.jsonl')}
    tiers = collections.defaultdict(set)
    for a in T('state/rank-assertions.jsonl'):
        tiers[rel[a['relationship']]['wine']].add(a['tier'])
    eds = {e['id']: e for e in T('state/classification-editions.jsonl')}
    schemes = {s['id']: s['name'] for s in T('state/classification-schemes.jsonl')}
    mem = collections.defaultdict(list)
    for m in T('state/classification-memberships.jsonl'):
        e = eds[m['edition']]
        mem[m['wine']].append([m['rank'], schemes[e['scheme']], e['validity']['valid_from'].get('value'), e['status']])
    apps = {a['id']: a['name'] for a in T('state/appellations.jsonl')}
    app = collections.defaultdict(list)
    for m in T('state/appellation-memberships.jsonl'):
        app[m['wine']].append(apps[m['appellation']])
    notmade = collections.defaultdict(list)
    for v in T('state/vintage-statements.jsonl'):
        if v['kind'] == 'NOT_PRODUCED':
            _, w, y = v['vintage'].split(':')
            notmade[w].append(int(y))
    for wine, key in key_of.items():
        f = g[key]
        if wine in names:
            assert f['n'] == names[wine]['name'], key
        else:
            assert 'n' not in f, key
        assert f.get('r') == (sorted(tiers[wine]) or None), key
        assert f.get('c') == (sorted(mem[wine]) or None), key
        assert f.get('a') == (sorted(app[wine]) or None), key
        assert f.get('x') == (sorted(notmade[wine]) or None), key
    # sheets on file: the fiche and cuvee records the wine's observations were read from
    recs = collections.defaultdict(set)
    for o in T('observation/observations.jsonl'):
        ex = o['extraction']
        if ex['file'] in ('data/fiches.js', 'data/cuvees.js'):
            p = ex['record'].split('|')
            recs[p[0] + '|grand' if len(p) == 2 else p[0] + '|' + p[1]].add(int(p[-1]))
    for key, f in g.items():
        ys = recs.get(key)
        assert f.get('s') == ([len(ys), min(ys), max(ys)] if ys else None), key


@check
def no_history_invented():
    # The model holds no FORMER name and no dated name; so neither does the page's data.
    T = L.read_table
    assert not [n for n in T('identity/names.jsonl') if n['kind'] != 'CURRENT']
    assert all(n['validity']['valid_from']['kind'] == 'UNKNOWN' for n in T('identity/names.jsonl'))
    assert not T('identity/transitions.jsonl')
    g = generated()
    assert not [k for k, f in g.items() if 'nf' in f or 'fn' in f], 'a date or former name appeared'
    text = open(L.ROOT + 'data/app/wine-established.js', encoding='utf-8').read()
    # the known, unreconciled renames (P7, P11) are not in the page's data
    for word in ('Haut-Bages Averous', 'La Parde', 'renamed', 'since'):
        assert word not in text, word


@check
def not_made_only_where_recorded():
    g = generated()
    T = L.read_table
    stated = {(v['vintage'].split(':')[1], int(v['vintage'].split(':')[2]))
              for v in T('state/vintage-statements.jsonl') if v['kind'] == 'NOT_PRODUCED'}
    key_of = {r['legacy_key'] + ('|grand' if r['namespace'] == 'grand-vin' else ''): r['stable_id']
              for r in T('identity/identity-map.jsonl') if r['namespace'] in ('grand-vin', 'wine-by-slug')}
    for key, f in g.items():
        for y in f.get('x', []):
            assert (key_of[key], y) in stated, (key, y)
    assert g['yquem|grand']['x'] == [1992, 2012, 2018]
    assert g['climens|grand']['x'] == [1984, 1987, 1992, 1993, 2012, 2017]
    # Echo has sheets only from 2011: none of its earlier, sheetless years is "not made"
    assert g['lynch-bages|echo-de-lynch-bages']['s'][1] == 2011 and 'x' not in g['lynch-bages|echo-de-lynch-bages']
    assert sum(len(f.get('x', [])) for f in g.values()) == 18


# ---------------------------------------------------------------- the page

BLOCK_JS = '''(function (id, slug) {
  var box = document.getElementById('search');
  if (box.value !== '') { box.value = ''; box.dispatchEvent(new Event('input')); }
  document.getElementById('tabProducers').click();
  document.querySelector('#paneList .pcard[data-ch="' + id + '"]').click();
  var sel = document.getElementById('wineSel');
  if (slug && slug !== 'grand' && sel) { sel.value = slug; sel.dispatchEvent(new Event('change')); }
  var b = document.querySelector('#drawerBody .wine-est');
  var rows = {};
  if (b) Array.prototype.forEach.call(b.querySelectorAll('.we-row'), function (r) {
    rows[r.querySelector('dt').textContent] = r.querySelector('dd').innerText; });
  var row2005 = document.querySelector('#drawerBody .vrow[data-year="2005"]');
  var out = {present: !!b, text: b ? b.innerText : null, rows: rows,
             focusable: b ? b.querySelectorAll('a, button, input, select, [tabindex]').length : null,
             row2005: row2005 ? row2005.innerText : null};
  document.getElementById('closeDrawer').click();
  return out;
})'''

CASES = [('lynch-bages', 'grand'), ('lynch-bages', 'echo-de-lynch-bages'), ('haut-bailly', 'grand'),
         ('haut-bailly', 'haut-bailly-ii'), ('batailley', 'lions-de-batailley'), ('yquem', 'grand'),
         ('climens', 'grand'), ('stem-chateau-corbin', 'grand')]
_page = {}


def page():
    if not _page:
        B = tool('benchmark-phase5.py')
        with B.Server() as srv, B.Browser() as b:
            b.c.send('Runtime.enable')
            b.c.send('Emulation.setDeviceMetricsOverride', {'width': 1400, 'height': 1000,
                                                            'deviceScaleFactor': 1, 'mobile': False})
            b.navigate(srv.url)
            time.sleep(0.5)
            for lid, slug in CASES:
                _page[(lid, slug)] = b.c.js('%s(%s, %s)' % (BLOCK_JS, json.dumps(lid), json.dumps(slug)))
            _page['compare'] = b.c.js('''(function () {
              document.getElementById('tabCompare').click();
              var v = document.querySelector('[data-cmode="vertical"]'); v.click();
              var sel = document.getElementById('cmpEstate'); sel.value = 'stem-chateau-corbin'; sel.dispatchEvent(new Event('change'));
              var vert = document.querySelector('.cmp-current');
              var vt = vert ? vert.innerText : null;
              document.querySelector('[data-cmode="horizontal"]').click();
              var hz = document.querySelector('.cmp-current');
              v.click();
              return {vertical: vt, horizontal: hz ? hz.innerText : null}; })()''')
            _page['errors'] = [e for e in b.c.events if e.get('method') == 'Runtime.exceptionThrown']
    return _page


def block(lid, slug):
    return page()[(lid, slug)]


def sheets_line(f):
    if not f.get('s'):
        return 'none'
    n, a, z = f['s']
    return ('%d vintage, %d' % (n, a)) if n == 1 else ('%d vintages, %d–%d' % (n, a, z))


@check
def every_case_shows_the_generated_facts_labelled_as_current():
    g = generated()
    for lid, slug in CASES:
        b, f = block(lid, slug), g[lid + '|' + slug]
        assert b['present'], (lid, slug)
        rows = b['rows']
        assert rows['Name'].startswith(f['n'] + ' current name'), (lid, slug, rows['Name'])
        assert 'When it was adopted, and any earlier names, are not recorded.' in rows['Name']
        assert 'current, as this dataset records it' in rows['Rank'], rows['Rank']
        if f.get('c'):
            assert 'the current list' in rows['Classification'], rows['Classification']
            assert 'which list applied to each vintage is not recorded' in rows['Classification']
        else:
            assert rows['Classification'] == 'none recorded for this wine', rows
        if f.get('a'):
            assert rows['Appellation'].startswith(', '.join(f['a']) + ' current'), rows['Appellation']
        else:
            assert rows['Appellation'].startswith('none recorded for this wine itself'), rows
        assert rows['Sheets on file'] == sheets_line(f), (lid, slug, rows['Sheets on file'])
        assert 'A year without a sheet is not evidence that the wine was not made' in b['text']
    assert not page()['errors'], page()['errors'][:2]


@check
def lynch_bages_grand_vin():
    r = block('lynch-bages', 'grand')['rows']
    assert r['Rank'].startswith('first wine') and r['Appellation'].startswith('Pauillac current')
    assert r['Classification'].startswith('Cinquièmes Crus, Classification of 1855 the current list (1855)')
    assert r['Sheets on file'] == '31 vintages, 1988–2025'


@check
def echo_current_identity_only():
    b = block('lynch-bages', 'echo-de-lynch-bages')
    assert b['rows']['Name'].startswith('Echo de Lynch-Bages current name')
    assert 'Haut-Bages' not in b['text'] and '2008' not in b['text'] and 'renamed' not in b['text']
    assert b['rows']['Sheets on file'] == '13 vintages, 2011–2025'
    # 2005 has no sheet: the row says so, and the block does not call it not made
    assert 'No sheet on file' in b['row2005'] and 'Recorded as not made' not in b['rows']


@check
def haut_bailly_ii_stays_not_established():
    b = block('haut-bailly', 'haut-bailly-ii')
    assert b['rows']['Name'].startswith('Haut-Bailly II current name')
    assert 'Which wine is the estate’s second wine is not established' in b['rows']['Rank']
    assert 'La Parde' not in b['text'] and 'renamed' not in b['text'] and '2018 vintage' not in b['text']


@check
def lions_de_batailley_conflict_unresolved():
    b = block('batailley', 'lions-de-batailley')
    assert 'The estate’s records conflict about its second wine' in b['rows']['Rank']
    assert b['rows']['Sheets on file'] == '4 vintages, 2014–2017'


@check
def yquem_and_climens_not_made_years():
    assert block('yquem', 'grand')['rows']['Recorded as not made'] == '1992, 2012, 2018'
    assert block('climens', 'grand')['rows']['Recorded as not made'] == '1984, 1987, 1992, 1993, 2012, 2017'
    # no other case shows a not-made line
    for case in CASES:
        if case not in (('yquem', 'grand'), ('climens', 'grand')):
            assert 'Recorded as not made' not in block(*case)['rows'], case


@check
def corbin_classification_is_the_current_list():
    r = block('stem-chateau-corbin', 'grand')['rows']
    assert r['Classification'].startswith('Grands Crus Classés, Saint-Émilion 2022 the current list (2022)'), r
    assert 'which list applied to each vintage is not recorded' in r['Classification']
    assert 'no second wine' not in block('stem-chateau-corbin', 'grand')['text'].lower()   # P6 is not in the model


@check
def compare_vertical_says_rank_and_appellation_are_current():
    c = page()['compare']
    assert c['vertical'] and 'current values' in c['vertical'] and 'not established for each vintage' in c['vertical'], c
    assert c['horizontal'] is None, 'the note belongs to the vertical view'


@check
def every_phrase_has_dutch_and_renders_dutch():
    js = open(L.ROOT + 'assets/app.js', encoding='utf-8').read()
    body = js[js.index('function wineEstablished'):js.index('function wineSwitcher')]
    nl = open(L.ROOT + 'assets/i18n.js', encoding='utf-8').read()
    phrases = set(re.findall(r"'([A-Z][^'<>]{3,}?[.]?)'", body)) | {
        'current name', 'current', 'first wine', 'second wine', 'the current list', 'vintages', 'vintage',
        'none', 'none recorded for this wine', 'none recorded for this wine itself',
        'current, as this dataset records it', 'rank not established'}
    phrases = {p for p in phrases if not p.startswith(('FIRST', 'SECOND', 'THIRD', 'ABOVE', 'UNRANKED', 'UNKNOWN',
                                                       'IN_FORCE'))}
    missing = [p for p in sorted(phrases) if ("'%s':" % p) not in nl]
    assert not missing, missing
    B = tool('benchmark-phase5.py')
    with B.Server() as srv, B.Browser() as b:
        b.navigate(srv.url)
        time.sleep(0.5)
        b.c.js("BDX_LANG.set('nl', function () {})")
        time.sleep(0.5)
        b.c.js("document.getElementById('tabProducers').click();"
               "document.querySelector('#paneList .pcard[data-ch=\"haut-bailly\"]').click();"
               "var s = document.getElementById('wineSel'); s.value = 'haut-bailly-ii'; s.dispatchEvent(new Event('change'));")
        time.sleep(0.4)
        t = b.c.js("document.querySelector('#drawerBody .wine-est').innerText")
    for nl_phrase in ('WAT OVER DEZE WIJN VASTSTAAT', 'huidige naam', 'tweede wijn', 'jaargangen',
                      'Een jaar zonder fiche bewijst niet'):
        assert nl_phrase in t, (nl_phrase, t)
    for en in ('current name', 'second wine', 'not recorded', 'Sheets on file'):
        assert en not in t, (en, t)


@check
def phone_width_fits():
    B = tool('benchmark-phase5.py')
    with B.Server() as srv, B.Browser() as b:
        b.c.send('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
        b.navigate(srv.url)
        time.sleep(0.5)
        r = b.c.js('''(function () {
          document.getElementById('tabProducers').click();
          document.querySelector('#paneList .pcard[data-ch="climens"]').click();
          var e = document.querySelector('#drawerBody .wine-est');
          var row = e.querySelector('.we-row'), dt = row.querySelector('dt').getBoundingClientRect(),
              dd = row.querySelector('dd').getBoundingClientRect();
          return {fits: e.scrollWidth <= e.clientWidth + 1, page: document.documentElement.scrollWidth,
                  stacked: dd.top >= dt.bottom - 1}; })()''')
    assert r['fits'] and r['page'] <= 390 and r['stacked'], r


@check
def keyboard_passes_the_block_without_a_stop():
    # The block is reference text: nothing in it takes focus, and Tab from the wine
    # selector reaches the first vintage row's control as before.
    for case in CASES:
        assert block(*case)['focusable'] == 0, case
    B = tool('benchmark-phase5.py')
    with B.Server() as srv, B.Browser() as b:
        b.navigate(srv.url)
        time.sleep(0.5)
        b.c.js("document.getElementById('tabProducers').click();"
               "document.querySelector('#paneList .pcard[data-ch=\"lynch-bages\"]').click();"
               "document.getElementById('wineSel').focus();")
        for _ in range(30):
            for t in ('rawKeyDown', 'keyUp'):
                b.c.send('Input.dispatchKeyEvent', {'type': t, 'key': 'Tab', 'code': 'Tab', 'windowsVirtualKeyCode': 9})
            a = b.c.js('''(function () { var a = document.activeElement;
              return {inBlock: !!(a.closest && a.closest('.wine-est')), head: a.classList.contains('vrow-head'),
                      year: a.closest && a.closest('.vrow') ? a.closest('.vrow').getAttribute('data-year') : null}; })()''')
            assert not a['inBlock'], 'focus stopped inside the block'
            if a['head']:
                break
        assert a['head'] and a['year'] == '2025', ('Tab did not reach the first vintage row', a)


# ---------------------------------------------------------------- nothing else

@check
def model_and_protected_data_unchanged():
    assert not git('diff', '--stat', BEFORE, '--', 'data/model').strip(), 'the model changed'
    changed = git('diff', '--name-status', BEFORE, '--', 'data/app').splitlines()
    assert all(l.split()[-1] == 'data/app/wine-established.js' for l in changed), changed
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
