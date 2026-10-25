"""Phase 6.1: each vintage figure cites its own source.

    python tools/test-phase61.py

Read-only. The model holds a provenance per field (Phase 4 M6/M7); the
generated application data (data/app/figure-sources.js) now carries it, and
the vintage view shows it beside each figure. These checks hold the
generated data to the model, the page to the generated data, and the values
to what they were: real cases from the Phase 6.0 audit, then every figure.
"""
import collections
import importlib.util
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import migration_lib as L  # noqa: E402

CHECKS = []
SHOWN = ['blend', 'yld', 'alc', 'months', 'oak', 'ph', 'sug', 'ta', 'temp', 'food', 'press', 'note', 'taste']


def check(f):
    CHECKS.append(f)
    return f


def tool(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_')[:-3], L.ROOT + 'tools/' + name)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_g = {}


def generated():
    """BDX_FIGURE_SRC as the page receives it, unpacked to {record: {field: source}}."""
    if not _g:
        s = open(L.ROOT + 'data/app/figure-sources.js', encoding='utf-8').read()
        d = json.loads(re.search(r'window\.BDX_FIGURE_SRC = (.*);\n', s).group(1))
        _g.update({k: {f: d['docs'][i] for f, i in r.items()} for k, r in d['rec'].items()})
    return _g


def src(record, field):
    return generated().get(record, {}).get(field)


# ---------------------------------------------------------------- the audit's real cases

@check
def figure_from_the_estates_sheet():
    # Cantemerle 2019: the blend and the new oak come from the sheet the record links.
    url = L.g('BDX_FICHE_URL')['cantemerle|2019']
    for f in ('blend', 'oak'):
        assert src('cantemerle|2019', f) == {'n': 'FT-Cantemerle-2019-EN.pdf', 'u': url}, f


@check
def figure_from_a_different_document():
    # Cantemerle 2019: the months in barrel come from the French sheet, not the linked English one.
    s = src('cantemerle|2019', 'months')
    assert s['n'] == 'FT-Cantemerle-2019-FR.pdf'
    assert s['u'] != L.g('BDX_FICHE_URL')['cantemerle|2019'] and s['u'].endswith('FT-Cantemerle-2019-FR.pdf')


@check
def two_figures_from_different_documents_on_one_page():
    a, b = src('cantemerle|2019', 'oak'), src('cantemerle|2019', 'months')
    assert a['u'] != b['u']


@check
def figure_with_no_established_source():
    # Batailley 2025: the blend has no field source; the record links a sheet anyway.
    assert 'blend' in L.g('BDX_FICHES')['batailley|2025'] and L.g('BDX_FICHE_URL').get('batailley|2025')
    assert src('batailley|2025', 'blend') is None, 'the record sheet given to a figure with no source'
    # and an ambiguous one stays ambiguous: Batailley 2020 cites a name two documents share
    assert src('batailley|2020', 'blend') == {'a': 'web-batailley2020_en.pdf', 'c': 2}


@check
def source_metadata_is_the_models():
    # The figure's source is its field's provenance in the model, not the record's.
    T = L.read_table
    im = {(r['namespace'], r['legacy_key']): r.get('stable_id') for r in T('identity/identity-map.jsonl')}
    v = im[('estate|vintage', 'cantemerle|2019')]
    prov = {p['id']: p for p in T('cross/provenance.jsonl')}
    o = [o for o in T('observation/observations.jsonl') if o['subject'] == v and o['field'] == 'months'][0]
    p = prov[o['provenance']]
    assert p['kind'] == 'LEGACY_FIELD_SOURCE' and p['legacy_reference']['basename'] == 'FT-Cantemerle-2019-FR.pdf'
    urls = {pl['locator']['value'] for pl in T('document/placements.jsonl')
            if pl['locator']['kind'] == 'URL' and pl.get('artifact') == p['artifact']}
    assert src('cantemerle|2019', 'months')['u'] in urls


# ---------------------------------------------------------------- every figure

@check
def generated_data_carries_exactly_the_models_provenance():
    bad = tool('build-app-data.py')
    assert generated() == bad.figure_sources(), 'data/app/figure-sources.js is not the model'
    T = L.read_table
    prov = {p['id']: p for p in T('cross/provenance.jsonl')}
    urls = collections.defaultdict(set)
    for pl in T('document/placements.jsonl'):
        if pl['locator']['kind'] == 'URL' and pl.get('artifact'):
            urls[pl['artifact']].add(pl['locator']['value'])
    n = collections.Counter()
    for o in T('observation/observations.jsonl'):
        ex = o['extraction']
        if ex['file'] not in ('data/fiches.js', 'data/cuvees.js'):
            continue
        p = prov[o['provenance']]
        s = src(ex['record'], o['field'])
        if p['kind'] == 'LEGACY_FIELD_SOURCE':
            assert s and s['n'] == p['legacy_reference']['basename'], (ex['record'], o['field'])
            assert ('u' in s) == bool(urls[p['artifact']]) and (s.get('u') in urls[p['artifact']] or 'u' not in s)
            n['own document' + (' with an address' if 'u' in s else ', no address')] += 1
        elif p['kind'] == 'LEGACY_AMBIGUOUS_SOURCE':
            assert s and 'a' in s and 'u' not in s, (ex['record'], o['field'])
            n['ambiguous'] += 1
        else:
            assert s is None, ('a source invented for', ex['record'], o['field'], p['kind'])
            n['no source'] += 1
    assert n['own document with an address'] > 3000 and n['no source'] > 1000, n


@check
def no_figure_with_known_provenance_is_given_the_record_sheet():
    # The audit's measure, redone on what the page now receives: every canonical value on a
    # record that links a sheet.
    r = measure()
    assert r.get('linked to another document than its own', 0) == 0, r
    assert r.get('shown without a source although one is known', 0) == 0, r
    assert sum(r.values()) == 4691, r          # the audit's population, all accounted for


def measure():
    T = L.read_table
    pv = {p['id']: p for p in T('cross/provenance.jsonl')}
    urls = collections.defaultdict(set)
    for pl in T('document/placements.jsonl'):
        if pl['locator']['kind'] == 'URL' and pl.get('artifact'):
            urls[pl['artifact']].add(pl['locator']['value'])
    rec_of = {o['subject']: o['extraction']['record'] for o in T('observation/observations.jsonl')
              if o['extraction']['file'] in ('data/fiches.js', 'data/cuvees.js')}
    linked = {o['subject'] for o in T('observation/observations.jsonl') if o['field'] == 'document_url'}
    out = collections.Counter()
    for c in T('canonical/values.jsonl'):
        s = c['subject']
        if s not in linked or s not in rec_of:
            continue
        p = pv[c['provenance']]
        shown = src(rec_of[s], c['field'])
        if p['kind'] == 'LEGACY_FIELD_SOURCE':
            own = urls[p['artifact']]
            if shown is None:
                out['shown without a source although one is known'] += 1
            elif 'u' in shown:
                out['linked to its own source' if shown['u'] in own else
                    'linked to another document than its own'] += 1
            else:
                out['its own source named, no address recorded'] += 1
        elif p['kind'] == 'LEGACY_AMBIGUOUS_SOURCE':
            out['marked "source unclear"' if shown and 'a' in shown else
                'linked to another document than its own'] += 1
        else:
            out['no established source, none shown' if shown is None else
                'linked to another document than its own'] += 1
    return dict(out)


# ---------------------------------------------------------------- the page

FACTS_JS = '''(function (id, yr) {
  var box = document.getElementById('search');
  box.value = ''; box.dispatchEvent(new Event('input'));
  document.querySelector('#paneList .pcard[data-ch="' + id + '"]').click();
  var row = document.querySelector('#drawerBody .vrow[data-year="' + yr + '"]');
  row.querySelector('.vrow-head').click();
  row = document.querySelector('#drawerBody .vrow[data-year="' + yr + '"]');
  var facts = {};
  Array.prototype.forEach.call(row.querySelectorAll('.factgrid .fact'), function (f) {
    var a = f.querySelector('.fig-src');
    facts[f.querySelector('dt').textContent] = a ? (a.getAttribute('href') || a.textContent) : null;
  });
  var blend = null;
  Array.prototype.forEach.call(row.querySelectorAll('.subhead'), function (h) {
    if (h.textContent.indexOf('Blend') === 0) {
      var a = h.querySelector('.fig-src'); blend = a ? (a.getAttribute('href') || a.textContent) : 'none';
    }
  });
  var rec = row.querySelector('.fichelink a');
  return {facts: facts, blend: blend, record: rec ? [rec.textContent, rec.getAttribute('href')] : null};
})'''


@check
def page_uses_each_figures_own_source():
    B = tool('benchmark-phase5.py')
    with B.Server() as srv, B.Browser() as b:
        b.navigate(srv.url)
        time.sleep(0.4)
        b.c.js("document.getElementById('tabProducers').click()")
        time.sleep(0.3)
        cm = b.c.js('%s("cantemerle", "2019")' % FACTS_JS)
        bt = b.c.js('%s("batailley", "2025")' % FACTS_JS)
        b20 = b.c.js('%s("batailley", "2020")' % FACTS_JS)
    sheet = L.g('BDX_FICHE_URL')
    assert cm['facts']['New oak'] == src('cantemerle|2019', 'oak')['u'] == sheet['cantemerle|2019'], cm
    assert cm['facts']['In barrel'] == src('cantemerle|2019', 'months')['u'] != sheet['cantemerle|2019'], cm
    assert cm['blend'] == sheet['cantemerle|2019'], cm
    assert cm['record'] == ['The sheet recorded for this vintage', sheet['cantemerle|2019']], cm
    assert bt['blend'] == 'none', 'Batailley 2025 blend given a source: %r' % bt
    assert bt['facts'].get('In barrel') == src('batailley|2025', 'months')['u'], bt
    assert b20['blend'] == 'source unclear', b20


@check
def values_search_and_lookups_unchanged():
    ar = tool('app-reference.py')
    ref = json.load(open(ar.FIXTURE, encoding='utf-8'))
    r = ar.compare(ref, ar.capture())
    assert not r['unexplained'], r['unexplained'][:5]
    allowed = {'IDENTICAL', 'EXPECTED: PRESENTATION ORDER', 'EXPECTED: PROVENANCE PRESENTATION',
               'EXPECTED: ADDED FIGURE PROVENANCE (Phase 6.1)',
               # Phase 6.3's second-wine row, named the same way
               'EXPECTED: SECOND-WINE STATUS PRESENTATION',
               'EXPECTED: PROVENANCE AND SECOND-WINE STATUS PRESENTATION',
               'EXPECTED: ADDED SECOND-WINE STATUS (Phase 6.3)'}
    assert set(r['summary']) <= allowed, r['summary']
    assert r['summary'].get('EXPECTED: ADDED FIGURE PROVENANCE (Phase 6.1)') == 1


@check
def existing_generated_files_and_protected_data_unchanged():
    import subprocess
    git = lambda *a: subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode()
    # the 23 generated contract files are byte-identical to Phase 6.0's
    changed = [f for f in git('diff', '--name-only', '8b13cb0', '--', 'data/app').split()
               if not f.endswith(('figure-sources.js', 'second-status.js'))]
    assert not changed, changed
    b = json.load(open(L.MODEL + 'baseline.json', encoding='utf-8'))['groups']
    for g in ('canonical', 'evidence', 'discovery', 'scope', 'phase_records'):
        assert L.group_hashes(g)['digest'] == b[g]['digest'], g
    assert not git('diff', '--stat', '8b13cb0', '--', 'data/model').strip(), 'the model changed'


def main():
    fails = 0
    for f in CHECKS:
        try:
            f()
            print('ok   %s' % f.__name__)
        except Exception as ex:
            fails += 1
            print('FAIL %s: %s' % (f.__name__, str(ex)[:300]))
    print('%d check(s), %s' % (len(CHECKS), 'all pass' if not fails else '%d FAIL' % fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    if '--measure' in sys.argv:
        print(json.dumps(measure(), indent=1))
    else:
        main()
