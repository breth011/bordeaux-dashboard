"""Phase 6.5: provenance display and accessibility.

    python tools/test-phase65.py

Read-only. The figure sources of Phase 6.1 are shown in the Compare tab, and
the details of every source - its file, its type, its address or that it has
none, that its name is shared, that other estates cite the same document -
open from a control a finger and a keyboard can reach, instead of a title
only a mouse could. The details come from the model: figure-sources.js
(Phase 6.1) and source-facts.js (this phase, tools/build-app-data.py
source_facts). Website and sparse-estate wording no longer claims a check
the model does not record. These checks hold the generated data to the
model, the page to both, and everything else on the page to the application
as it was at c15b421.
"""
import collections
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import migration_lib as L  # noqa: E402

BEFORE = 'c15b421'               # Phase 6.4: the application before this phase
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


def packed(name, var):
    s = open(L.ROOT + 'data/app/' + name, encoding='utf-8').read()
    d = json.loads(re.search(r'window\.%s = (.*);\n' % var, s).group(1))
    return {k: {f: d['docs'][i] for f, i in r.items()} for k, r in d['rec'].items()}


def figure_src():
    return packed('figure-sources.js', 'BDX_FIGURE_SRC')


def facts():
    return packed('source-facts.js', 'BDX_SOURCE_FACTS')


# ---------------------------------------------------------------- the generated data

@check
def source_facts_are_the_models():
    bad = tool('build-app-data.py')
    assert facts() == bad.source_facts(), 'data/app/source-facts.js is not the model'
    T = L.read_table
    prov = {p['id']: p for p in T('cross/provenance.jsonl')}
    kind = {a['artifact']: a['document_type'] for a in T('document/assessments.jsonl')}
    art = {}
    estates = collections.defaultdict(set)
    for o in T('observation/observations.jsonl'):
        ex = o['extraction']
        if ex['file'] in ('data/fiches.js', 'data/cuvees.js'):
            p = prov[o['provenance']]
            if p['kind'] == 'LEGACY_FIELD_SOURCE':
                art[(ex['record'], o['field'])] = p['artifact']
                estates[p['artifact']].add(ex['record'].split('|', 1)[0])
    fs, n = facts(), collections.Counter()
    for rec, r in fs.items():
        for field, x in r.items():
            a = art[(rec, field)]           # only a field's own document has facts
            assert set(x) <= {'t', 'o'} and x, (rec, field, x)
            if 't' in x:
                assert x['t'] == kind[a] and x['t'] not in ('UNKNOWN', 'OTHER'), (rec, field)
            if 'o' in x:
                # the same artifact - model identity - cited for other estates, counted exactly
                assert x['o'] == len(estates[a] - {rec.split('|', 1)[0]}), (rec, field)
            n['o' in x and 'shared' or 'typed'] += 1
    for (rec, field), a in art.items():
        if kind.get(a) in bad.TELLING_TYPES or len(estates[a]) > 1:
            assert field in fs.get(rec, {}), ('a model fact left out', rec, field)
    # the four documents the audit found cited for several estates, and no other
    assert sum(len(v) > 1 for v in estates.values()) == 4
    assert fs['lafite|2025']['pick'] == {'o': 3, 't': 'WEB_PAGE'}
    assert fs['bourgeois-chateau-de-braude|1999']['oak'] == {'o': 1}
    assert 'cantemerle|2019' not in fs, 'a PDF with no assessed type and no sharing has no facts'
    # an ambiguous source has none: which artifact it is, is what is not known
    for rec, r in figure_src().items():
        for field, d in r.items():
            if 'a' in d:
                assert field not in fs.get(rec, {}), (rec, field)


@check
def other_generated_files_byte_identical_and_deterministic():
    # Against BEFORE, the only difference in data/app may be this phase's own file, added.
    # (Uncommitted, the new file is untracked and git diff does not list it; committed, it is
    # listed as added. Either way no existing generated file may change.)
    changed = git('diff', '--name-status', BEFORE, '--', 'data/app').splitlines()
    assert [l for l in changed if l.split()[-1] != 'data/app/source-facts.js'] == [], \
        'an existing generated file changed: %s' % changed
    assert all(l.split()[0] == 'A' for l in changed), changed
    assert os.path.exists(L.ROOT + 'data/app/source-facts.js')
    bad = tool('build-app-data.py')
    a, b = bad.render(), bad.render()
    assert a == b, 'generation is not deterministic'
    for f, data in a.items():
        assert open(L.ROOT + 'data/app/' + f, 'rb').read() == data, f


# ---------------------------------------------------------------- the page

def site_at(commit):
    """The application as committed at `commit`, in a temporary copy of the site."""
    site = tempfile.mkdtemp(prefix='bdx-65-')
    for f in ['index.html', 'service-worker.js', 'manifest.webmanifest'] + \
            git('ls-tree', '-r', '--name-only', commit, 'assets', 'data/app').split():
        p = os.path.join(site, f)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(subprocess.check_output(['git', 'show', '%s:%s' % (commit, f)], cwd=L.ROOT))
    for f in os.listdir(L.ROOT + 'data'):
        if f.endswith('.js'):
            shutil.copyfile(L.ROOT + 'data/' + f, os.path.join(site, 'data', f))
    return site


ROW_JS = '''(function (id, yr) {
  var box = document.getElementById('search');
  if (box.value !== '') { box.value = ''; box.dispatchEvent(new Event('input')); }
  document.getElementById('tabProducers').click();
  document.querySelector('#paneList .pcard[data-ch="' + id + '"]').click();
  var row = document.querySelector('#drawerBody .vrow[data-year="' + yr + '"]');
  if (!row) return null;
  row.querySelector('.vrow-head').click();
  row = document.querySelector('#drawerBody .vrow[data-year="' + yr + '"]');
  function where(e) {
    var f = e.closest('.fact'); if (f) return f.querySelector('dt').textContent;
    var p = e.closest('p'); return p ? (p.className + ':' + p.textContent.slice(0, 24)) : '?';
  }
  var marks = [];
  Array.prototype.forEach.call(row.querySelectorAll('[data-prov], button[data-src]'), function (e) {
    var m = {where: where(e), tag: e.tagName, cls: e.className, prov: e.getAttribute('data-prov'),
             text: e.textContent, href: e.getAttribute('href'), title: e.getAttribute('title'),
             label: e.getAttribute('aria-label'), expanded: e.getAttribute('aria-expanded'), panel: null};
    if (e.hasAttribute('data-src')) {
      e.click();
      var p = document.getElementById(e.getAttribute('aria-controls'));
      m.expanded = e.getAttribute('aria-expanded');
      m.panel = p ? {text: p.innerText, role: p.getAttribute('role'), label: p.getAttribute('aria-label'),
                     links: Array.prototype.map.call(p.querySelectorAll('a'), function (a) {
                       return [a.getAttribute('href'), a.getAttribute('target'), a.getAttribute('rel')]; })} : null;
      e.click();
      m.after = e.getAttribute('aria-expanded');
      m.left = document.querySelectorAll('.src-panel').length;
    }
    marks.push(m);
  });
  return marks;
})'''

CMP_JS = '''(function (id, years, strip) {
  document.getElementById('tabCompare').click();
  var v = document.querySelector('[data-cmode="vertical"]'); if (v) v.click();
  var sel = document.getElementById('cmpEstate'); sel.value = id; sel.dispatchEvent(new Event('change'));
  Array.prototype.forEach.call(document.querySelectorAll('.cmp-year.on'), function (b) { b.click(); });
  years.forEach(function (y) { var b = document.querySelector('.cmp-year[data-cyear="' + y + '"]'); if (b) b.click(); });
  var t = document.querySelector('table.cmp').cloneNode(true);
  if (strip) Array.prototype.forEach.call(t.querySelectorAll('.fig-src, .src-more, .src-panel'), function (e) {
    e.parentNode.removeChild(e); });
  document.body.appendChild(t);
  var rows = [];
  Array.prototype.forEach.call(t.querySelectorAll('tbody tr'), function (tr) {
    var cells = [];
    Array.prototype.forEach.call(tr.querySelectorAll('td'), function (td) {
      var c = {text: td.innerText.trim(), marks: Array.prototype.map.call(td.querySelectorAll('[data-prov], button[data-src]'),
        function (m) { return {prov: m.getAttribute('data-prov'), href: m.getAttribute('href'), text: m.textContent,
                               key: m.getAttribute('data-src'), tag: m.tagName, cls: m.className}; }),
        links: Array.prototype.map.call(td.querySelectorAll('a'), function (a) { return a.getAttribute('href'); })};
      for (var i = 0; i < (td.colSpan || 1); i++) cells.push(c);
    });
    rows.push([tr.querySelector('th').textContent, cells]);
  });
  t.parentNode.removeChild(t);
  return rows;
})'''

CASES = [('cantemerle', 2019), ('cantemerle', 2020), ('batailley', 2020), ('batailley', 2025),
         ('lafite', 2025), ('bourgeois-chateau-de-braude', 1999)]
COMPARES = [('cantemerle', [2019, 2020]), ('batailley', [2020, 2025]), ('lafite', [2024, 2025]),
            ('lynch-bages', [2010, 2015, 2016, 2019]), ('margaux', [2015, 2016])]
_pages = {}


def page(root=None):
    key = root or 'now'
    if key not in _pages:
        B = tool('benchmark-phase5.py')
        out = {'rows': {}, 'cmp': {}, 'cmp_raw': {}, 'sites': {}, 'sparse': None, 'errors': []}
        with B.Server(root) as srv, B.Browser() as b:
            b.c.send('Runtime.enable')
            b.c.send('Emulation.setDeviceMetricsOverride', {'width': 1400, 'height': 1000,
                                                            'deviceScaleFactor': 1, 'mobile': False})
            b.navigate(srv.url)
            time.sleep(0.5)
            b.c.js("document.getElementById('tabProducers').click()")
            time.sleep(0.3)
            for lid, yr in CASES:
                out['rows'][(lid, yr)] = b.c.js('%s(%s, %d)' % (ROW_JS, json.dumps(lid), yr))
                b.c.js("var c = document.getElementById('closeDrawer'); if (c) c.click();")
            # one estate per website tag, the tag's title as the drawer gives it
            sites = L.g('BDX_SITES')
            per_tag = {}
            for lid in sorted(sites):
                per_tag.setdefault(sites[lid][1], lid)
            for tag, lid in sorted(per_tag.items()):
                out['sites'][tag] = (lid, b.c.js('''(function (id) {
                  var box = document.getElementById('search'); if (box.value !== '') { box.value = ''; box.dispatchEvent(new Event('input')); }
                  document.getElementById('tabProducers').click();
                  var card = document.querySelector('#paneList .pcard[data-ch="' + id + '"]');
                  if (!card) return null; card.click();
                  var t = null;
                  Array.prototype.forEach.call(document.querySelectorAll('#drawerBody .fact'), function (f) {
                    if (f.querySelector('dt').textContent === 'Website') t = f.querySelector('a').getAttribute('title'); });
                  var c = document.getElementById('closeDrawer'); if (c) c.click();
                  return t; })(%s)''' % json.dumps(lid)))
            out['sparse'] = b.c.js('''(function () {
              var box = document.getElementById('search'); if (box.value !== '') { box.value = ''; box.dispatchEvent(new Event('input')); }
              document.getElementById('tabProducers').click();
              document.querySelector('#paneList .pcard[data-ch="bourgeois-chateau-beaumont"]').click();
              var n = document.querySelector('#drawerBody .notice');
              var t = n ? n.innerText : null;
              var c = document.getElementById('closeDrawer'); if (c) c.click();
              return t; })()''')
            for lid, years in COMPARES:
                out['cmp'][lid] = b.c.js('%s(%s, %s, true)' % (CMP_JS, json.dumps(lid), json.dumps(years)))
                out['cmp_raw'][lid] = b.c.js('%s(%s, %s, false)' % (CMP_JS, json.dumps(lid), json.dumps(years)))
            out['errors'] = [e for e in b.c.events if e.get('method') == 'Runtime.exceptionThrown']
        _pages[key] = out
    return _pages[key]


def marks(lid, yr):
    return page()['rows'][(lid, yr)]


def at(lid, yr, where):
    return [m for m in marks(lid, yr) if m['where'].startswith(where)]


@check
def known_web_source_link_kept_details_one_press_away():
    # Cantemerle 2019 new oak: the link to its own sheet, as Phase 6.1 made it, and beside it
    # a control whose details name the document, its type and the same address.
    fs = figure_src()['cantemerle|2019']['oak']
    a, more = at('cantemerle', 2019, 'New oak')
    assert a['tag'] == 'A' and a['href'] == fs['u'] and a['text'] == 'source', a
    assert more['tag'] == 'BUTTON' and more['cls'] == 'src-more' and more['label'] == 'About this source', more
    assert more['expanded'] == 'true' and more['after'] == 'false' and more['left'] == 0, more
    p = more['panel']
    assert p['role'] == 'group' and p['label'] == 'Source details', p
    assert 'FT-Cantemerle-2019-EN.pdf' in p['text'] and 'PDF document' in p['text'], p
    assert p['links'] == [[fs['u'], '_blank', 'noopener noreferrer']], p
    assert 'Kept on file' not in p['text'] and 'Also cited' not in p['text'], p


@check
def several_documents_on_one_record_each_named():
    # Cantemerle 2019: in barrel from the French sheet, new oak from the English one.
    fr = at('cantemerle', 2019, 'In barrel')
    en = at('cantemerle', 2019, 'New oak')
    assert fr[0]['href'] != en[0]['href'] and fr[0]['href'].endswith('FT-Cantemerle-2019-FR.pdf')
    assert 'FT-Cantemerle-2019-FR.pdf' in fr[1]['panel']['text'] and 'FT-Cantemerle-2019-EN.pdf' in en[1]['panel']['text']


@check
def file_only_source_inspectable_without_hover():
    # Cantemerle 2020: the figures' own documents are held, with no address recorded.
    ms = [m for m in marks('cantemerle', 2020) if m['prov'] == 'file']
    fs = figure_src()['cantemerle|2020']
    assert ms, 'no file-only source on Cantemerle 2020'
    for m in ms:
        assert m['tag'] == 'BUTTON' and m['text'] == 'source on file' and m['href'] is None, m
        assert m['title'] is None, 'the file name still lives in a title only'
        names = [d['n'] for d in fs.values() if 'n' in d and 'u' not in d]
        assert any(n in m['panel']['text'] for n in names), m['panel']
        assert 'Kept on file: no web address was recorded' in m['panel']['text'], m['panel']
        assert m['panel']['links'] == [], 'a link invented for a file-only source'


@check
def ambiguous_source_inspectable_without_hover():
    for m in at('batailley', 2020, 'Blend') + at('batailley', 2020, 'New oak'):
        assert m['tag'] == 'BUTTON' and m['text'] == 'source unclear' and m['title'] is None, m
        t = m['panel']['text']
        assert 'web-batailley2020_en.pdf' in t and '2 documents carry this name' in t, t
        assert 'is unclear' in t and m['panel']['links'] == [], t


@check
def no_known_source_no_mark_no_link():
    # Batailley 2025: the blend has no source; nothing is shown beside it, nor in Compare.
    assert figure_src()['batailley|2025'].get('blend') is None
    assert at('batailley', 2025, 'In barrel'), 'the 2025 row was not opened'
    assert at('batailley', 2025, 'subhead:Blend') == [], 'a source given to a figure with none'
    cells = dict(page()['cmp_raw']['batailley'])['Blend']
    assert cells[1]['marks'] == [] and cells[1]['links'] == [], cells[1]


@check
def shared_source_said_only_where_the_model_has_it():
    # Lafite 2025: the group's page, the same artifact cited for three other estates.
    m = [m for m in marks('lafite', 2025) if m['cls'] == 'src-more']
    assert m
    assert any('Also cited for 3 other estates' in x['panel']['text'] for x in m), m
    assert any('a web page; its text is kept on file' in x['panel']['text'] for x in m), m
    # Braude 1999: the 2015 sheet two estates cite. Said, not judged: no year, no correction.
    b = [m for m in marks('bourgeois-chateau-de-braude', 1999) if m['cls'] == 'src-more']
    assert b and all('Also cited for 1 other estate' in x['panel']['text'] for x in b)
    for x in b:
        assert 'FT-Ch-Braude-Fellonneau-2015-GB.pdf' in x['panel']['text']
        assert not re.search(r'1999|wrong|mismatch|incorrect', x['panel']['text'], re.I), x['panel']['text']
    # and nowhere else: Cantemerle's documents are cited for Cantemerle only
    assert not any('Also cited' in (m['panel'] or {}).get('text', '') for m in marks('cantemerle', 2019) if m['panel'])


@check
def no_summary_claims_the_document_proves_the_figure():
    for (lid, yr), ms in page()['rows'].items():
        for m in ms:
            t = (m['panel'] or {}).get('text', '')
            assert not re.search(r'verif|confirm|prove|checked|authorit', t, re.I), (lid, yr, t)


# ---------------------------------------------------------------- Compare

@check
def compare_shows_each_figures_own_source():
    rows = dict(page()['cmp_raw']['cantemerle'])
    fs = figure_src()
    barrel, oak = rows['In barrel'], rows['New oak']
    # 2019's 12 months is the French sheet's; the vintage's sheet is the English one
    assert barrel[0]['marks'][0]['href'] == fs['cantemerle|2019']['months']['u']
    assert oak[0]['marks'][0]['href'] == fs['cantemerle|2019']['oak']['u']
    sheet = rows['Sheet recorded for this vintage']
    assert sheet[0]['links'] == [L.g('BDX_FICHE_URL')['cantemerle|2019']]
    assert barrel[0]['marks'][0]['href'] != sheet[0]['links'][0], 'the figure given the vintage sheet'
    # the two vintages read alike in barrel but have different sources: two cells, not one
    assert barrel[0] is not barrel[1] and barrel[1]['marks'] == [], barrel
    # 2020: no sheet address, figures with their own documents on file
    assert sheet[1]['links'] == [] and any(m['prov'] == 'file' for m in rows['Alcohol'][1]['marks'])


@check
def compare_marks_are_exactly_the_figure_sources():
    fs = figure_src()
    field = {'Blend': 'blend', 'Picked': 'pick', 'Yield': 'yld', 'Alcohol': 'alc', 'In barrel': 'months',
             'New oak': 'oak', 'pH': 'ph', 'Residual sugar': 'sug', 'Total acidity': 'ta', 'Serve at': 'temp',
             'Serve it with': 'food', 'Decant': 'decant', 'The estate on the wine': 'taste'}
    seen = collections.Counter()
    for lid, years in COMPARES:
        for label, cells in page()['cmp_raw'][lid]:
            if label not in field:
                assert not any(c['marks'] for c in cells), (lid, label)
                continue
            for yr, c in zip(years, cells):
                d = fs.get('%s|%d' % (lid, yr), {}).get(field[label])
                ms = [m for m in c['marks'] if m['prov']]
                if not c['text'] or c['text'] == '—':
                    continue
                if d is None:
                    assert not ms, ('a source invented', lid, yr, label, ms)
                elif 'u' in d:
                    assert [m['href'] for m in ms] == [d['u']], (lid, yr, label, ms)
                    seen['doc'] += 1
                else:
                    assert [m['prov'] for m in ms] == ['file' if 'n' in d else 'amb'], (lid, yr, label, ms)
                    assert ms[0]['href'] is None
                    seen['file' if 'n' in d else 'amb'] += 1
    assert seen['doc'] and seen['file'] and seen['amb'], seen


@check
def compare_values_and_sheet_row_unchanged_but_for_the_label():
    old = site_at(BEFORE)
    try:
        before = page(old.replace('\\', '/') + '/')
    finally:
        shutil.rmtree(old, ignore_errors=True)
    for lid, _ in COMPARES:
        a = [(('Sheet recorded for this vintage' if r == 'Sheet' else r), [c['text'] for c in cs])
             for r, cs in before['cmp'][lid]]
        b = [(r, [c['text'] for c in cs]) for r, cs in page()['cmp'][lid]]
        assert a == b, (lid, [x for x in zip(a, b) if x[0] != x[1]][:3])
        # the sheet row links what it linked
        la = [c['links'] for r, cs in before['cmp_raw'][lid] if r == 'Sheet' for c in cs]
        lb = [c['links'] for r, cs in page()['cmp_raw'][lid] if r == 'Sheet recorded for this vintage' for c in cs]
        assert la == lb, lid
    assert not page()['errors'], page()['errors'][:2]


@check
def compare_label_column_not_widened_on_a_phone():
    # The row labels are sticky and do not wrap: the longest sets the width of the column that
    # covers the cells on a phone. The sheet row's longer name wraps instead of widening it.
    B = tool('benchmark-phase5.py')
    js = '''(function () {
      document.getElementById('tabCompare').click();
      var sel = document.getElementById('cmpEstate'); sel.value = 'cantemerle'; sel.dispatchEvent(new Event('change'));
      Array.prototype.forEach.call(document.querySelectorAll('.cmp-year.on'), function (b) { b.click(); });
      [2019, 2020].forEach(function (y) { document.querySelector('.cmp-year[data-cyear="' + y + '"]').click(); });
      return Math.round(document.querySelector('table.cmp tbody th').getBoundingClientRect().width); })()'''
    old = site_at(BEFORE)
    widths = []
    try:
        for root in (old.replace('\\', '/') + '/', None):
            with B.Server(root) as srv, B.Browser() as b:
                b.c.send('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844,
                                                                'deviceScaleFactor': 2, 'mobile': True})
                b.navigate(srv.url)
                time.sleep(0.5)
                widths.append(b.c.js(js))
    finally:
        shutil.rmtree(old, ignore_errors=True)
    assert widths[1] <= widths[0], ('the label column widened on a phone', widths)


# ---------------------------------------------------------------- wording

@check
def website_sources_claim_no_check():
    js = open(L.ROOT + 'assets/app.js', encoding='utf-8').read()
    block = js[js.index('var SITE_SOURCE = {'):js.index('};', js.index('var SITE_SOURCE = {'))]
    assert not re.search(r'verif|confirm|check|authentic|prove', block, re.I), block
    sites = page()['sites']
    assert sites['dom'][1] == 'from the estate’s own site', sites['dom']
    assert sites['domr'][1] == 'from the estate’s own site, recorded by hand', sites['domr']
    assert sites['hand'][1] == 'from the estate, recorded by hand', sites['hand']
    for tag, (lid, title) in sites.items():
        assert title and not re.search(r'verif|confirm|check', title, re.I), (tag, lid, title)


@check
def unmapped_tag_not_credited_to_wikidata_suau():
    sites = page()['sites']
    assert L.g('BDX_SITES')['suau'][1] == 'handx', 'the tag data changed'
    lid, title = sites['handx']
    assert lid == 'suau' and 'Wikidata' not in title, (lid, title)
    assert title == 'where this address was found is not recorded', title
    assert sites['wikidata'][1] == 'from Wikidata', 'a real Wikidata address lost its credit'


@check
def sparse_estates_not_called_verified():
    t = page()['sparse']
    assert t and t.startswith('A name and rank, and little else.'), t
    assert 'verified' not in t.lower(), t
    js = open(L.ROOT + 'assets/app.js', encoding='utf-8').read()
    assert 'A verified name and rank' not in js


# ---------------------------------------------------------------- keyboard and touch

KEYS = {'Tab': ('Tab', 9, ''), 'Enter': ('Enter', 13, '\r'), 'Space': (' ', 32, ' '), 'Escape': ('Escape', 27, '')}


def press(b, name, shift=False):
    key, code, text = KEYS[name]
    ev = {'key': key, 'code': 'Space' if name == 'Space' else name, 'windowsVirtualKeyCode': code,
          'nativeVirtualKeyCode': code, 'modifiers': 8 if shift else 0}
    b.c.send('Input.dispatchKeyEvent', dict(ev, type='keyDown', text=text) if text else dict(ev, type='rawKeyDown'))
    b.c.send('Input.dispatchKeyEvent', dict(ev, type='keyUp'))
    time.sleep(0.05)


ACTIVE_JS = '''(function () {
  var a = document.activeElement;
  var p = a && a.getAttribute('aria-controls') ? document.getElementById(a.getAttribute('aria-controls')) : null;
  var cs = a ? getComputedStyle(a) : null;
  return {tag: a ? a.tagName : null, cls: a ? a.className : '', src: a ? a.getAttribute('data-src') : null,
          expanded: a ? a.getAttribute('aria-expanded') : null, panel: p ? p.innerText : null,
          panels: document.querySelectorAll('.src-panel').length,
          inPanel: !!(a && a.closest && a.closest('.src-panel')),
          outline: cs ? cs.outlineStyle + ' ' + cs.outlineWidth : null,
          drawer: document.getElementById('drawer') ? document.getElementById('drawer').classList.contains('is-open') : null};
})()'''


def tab_to(b, want, limit=80):
    for _ in range(limit):
        press(b, 'Tab')
        a = b.c.js(ACTIVE_JS)
        if want(a):
            return a
    raise AssertionError('not reachable by Tab')


def keyboard_round(b, want):
    a = tab_to(b, want)
    assert a['expanded'] == 'false' and a['outline'].startswith('solid'), ('focus not visible', a)
    press(b, 'Enter')
    a = b.c.js(ACTIVE_JS)
    assert a['expanded'] == 'true' and a['panel'] and a['panels'] == 1, ('Enter did not open', a)
    opened_by_enter = a['panel']
    press(b, 'Escape')
    a = b.c.js(ACTIVE_JS)
    assert a['expanded'] == 'false' and a['panels'] == 0 and want(a), ('Escape: closed, focus back', a)
    press(b, 'Space')
    a = b.c.js(ACTIVE_JS)
    assert a['expanded'] == 'true' and a['panel'] == opened_by_enter, ('Space opens the same summary', a)
    # no trap: Tab moves on, into the summary's link or past it, and keeps going
    press(b, 'Tab')
    n = b.c.js(ACTIVE_JS)
    press(b, 'Tab')
    m = b.c.js(ACTIVE_JS)
    assert (n['src'], n['cls']) != (a['src'], a['cls']) or n['inPanel'], 'focus stuck'
    assert m != n or m['tag'] == 'BODY', 'focus stuck'
    return opened_by_enter


@check
def keyboard_reaches_and_operates_source_controls():
    B = tool('benchmark-phase5.py')
    with B.Server() as srv, B.Browser() as b:
        b.c.send('Emulation.setDeviceMetricsOverride', {'width': 1400, 'height': 1000, 'deviceScaleFactor': 1, 'mobile': False})
        b.navigate(srv.url)
        time.sleep(0.5)
        # the drawer: Cantemerle 2020's "source on file"
        b.c.js('''(function () {
          document.getElementById('tabProducers').click();
          document.querySelector('#paneList .pcard[data-ch="cantemerle"]').click();
          var row = document.querySelector('#drawerBody .vrow[data-year="2020"]');
          row.querySelector('.vrow-head').click();
          document.querySelector('#drawerBody .vrow[data-year="2020"] .vrow-head').focus(); })()''')
        t = keyboard_round(b, lambda a: a['tag'] == 'BUTTON' and 'src-btn' in a['cls'])
        assert 'Kept on file' in t, t
        # Escape with no summary open still closes the drawer, as it did
        b.c.js("document.querySelectorAll('.src-panel').length && document.body.click()")
        b.c.js("document.querySelector('#drawerBody .vrow-head').focus()")
        press(b, 'Escape')
        assert b.c.js("document.getElementById('drawer').classList.contains('is-open')") is False
        # Compare: Cantemerle 2019 against 2020, the "about this source" of a linked figure
        b.c.js('''(function () {
          document.getElementById('tabCompare').click();
          var sel = document.getElementById('cmpEstate'); sel.value = 'cantemerle'; sel.dispatchEvent(new Event('change'));
          Array.prototype.forEach.call(document.querySelectorAll('.cmp-year.on'), function (b) { b.click(); });
          [2019, 2020].forEach(function (y) { document.querySelector('.cmp-year[data-cyear="' + y + '"]').click(); });
          document.getElementById('cmpEstate').focus(); })()''')
        t = keyboard_round(b, lambda a: a['tag'] == 'BUTTON' and a['cls'] == 'src-more')
        assert 'The document this figure was recorded from' in t and 'Document' in t, t


@check
def touch_opens_and_closes_without_navigating():
    B = tool('benchmark-phase5.py')
    with B.Server() as srv, B.Browser() as b:
        b.c.send('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
        b.c.send('Emulation.setTouchEmulationEnabled', {'enabled': True, 'maxTouchPoints': 5})
        b.navigate(srv.url)
        time.sleep(0.5)
        start = b.c.js('location.href')

        def until(js, timeout=10):
            # Wait for a condition in the page, not a fixed time: under load (two suites at
            # once, Phase 6.6C) the drawer's slide-in and a tap's click took longer than the
            # fixed sleeps that stood here, and the tap landed where the button had been.
            end = time.time() + timeout
            while time.time() < end:
                v = b.c.js(js)
                if v:
                    return v
                time.sleep(0.05)
            return b.c.js(js)

        def tap(sel, then):
            # the drawer has finished sliding in and the target has stopped moving
            point = '''(function () { var e = document.querySelector(%s); e.scrollIntoView({block: 'center'});
              var r = e.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })()''' % json.dumps(sel)
            until("getComputedStyle(document.getElementById('drawer')).transform === 'none'")
            r, last = b.c.js(point), None
            while r != last:
                time.sleep(0.05)
                r, last = b.c.js(point), r
            for t in ('touchStart', 'touchEnd'):
                b.c.send('Input.dispatchTouchEvent', {'type': t, 'touchPoints': [] if t == 'touchEnd' else
                                                      [{'x': r[0], 'y': r[1]}]})
            until(then)                     # the tap's effect; asserted below either way

        opened = "document.querySelectorAll('.src-panel').length === 1"
        closed = "document.querySelectorAll('.src-panel').length === 0"

        b.c.js('''(function () {
          document.getElementById('tabProducers').click();
          document.querySelector('#paneList .pcard[data-ch="batailley"]').click();
          document.querySelector('#drawerBody .vrow[data-year="2020"] .vrow-head').click(); })()''')
        sel = '#drawerBody .vrow[data-year="2020"] button[data-prov="amb"]'
        tap(sel, opened)
        st = b.c.js('''(function (s) { var e = document.querySelector(s);
          var p = document.getElementById(e.getAttribute('aria-controls'));
          return {exp: e.getAttribute('aria-expanded'), text: p ? p.innerText : null,
                  fits: p ? p.scrollWidth <= p.clientWidth + 1 : null,
                  page: document.documentElement.scrollWidth}; })(%s)''' % json.dumps(sel))
        assert st['exp'] == 'true' and '2 documents carry this name' in st['text'], st
        assert st['fits'] and st['page'] <= 390, ('the summary overflows a phone', st)
        tap(sel, closed)
        assert b.c.js('document.querySelectorAll(".src-panel").length') == 0
        # a long file name wraps inside the summary (Lafite 2025's page text)
        b.c.js('''(function () {
          document.getElementById('closeDrawer').click();
          document.querySelector('#paneList .pcard[data-ch="cantemerle"]').click();
          document.querySelector('#drawerBody .vrow[data-year="2019"] .vrow-head').click(); })()''')
        tap('#drawerBody .vrow[data-year="2019"] .src-more', opened)
        st = b.c.js('''(function () { var p = document.querySelector('.src-panel');
          return {text: p.innerText, fits: p.scrollWidth <= p.clientWidth + 1, page: document.documentElement.scrollWidth}; })()''')
        assert 'FT-Cantemerle-2019-EN.pdf' in st['text'] and st['fits'] and st['page'] <= 390, st
        assert b.c.js('location.href') == start, 'a tap on the details control navigated'
        # the source link itself opens a new tab, never this one
        a = b.c.js('''(function () { var a = document.querySelector('#drawerBody .vrow[data-year="2019"] a.fig-src');
          return [a.getAttribute('target'), a.getAttribute('rel')]; })()''')
        assert a == ['_blank', 'noopener noreferrer'], a


@check
def no_essential_provenance_in_a_title_only():
    # Every source mark that is not a link is a button whose words are its name, and nothing
    # it has to say lives in a title: the file and the count are in the details.
    for (lid, yr), ms in page()['rows'].items():
        for m in ms:
            if m['prov'] in ('file', 'amb'):
                assert m['tag'] == 'BUTTON' and m['title'] is None and m['text'], (lid, yr, m)
            if m['tag'] == 'BUTTON':
                assert m['text'] or m['label'], ('a control with no accessible name', lid, yr, m)
                assert m['panel'] and m['panel']['text'], (lid, yr, m)
    css = open(L.ROOT + 'assets/styles.css', encoding='utf-8').read()
    assert '.src-btn:focus-visible' in css and '.src-more:focus-visible' in css


# ---------------------------------------------------------------- nothing else

@check
def model_and_protected_data_unchanged():
    assert not git('diff', '--stat', BEFORE, '--', 'data/model').strip(), 'the model changed'
    assert not git('diff', '--stat', BEFORE, '--', 'docs/PHASE-6.4-PROVENANCE-EVIDENCE-AUDIT.md').strip()
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
