"""Phase 6.3: the second-wine fact shows the model's state, and nothing else changes.

    python tools/test-phase63.py

Read-only. The state comes from the model (tools/build-app-data.py
second_status, written to data/app/second-status.js); the drawer renders it
(assets/app.js secondFact). These checks hold the generated states to the
model's records, the drawer to the presentation contract on the cases the
Phase 6.2 audit named, and every one of the 137 estates with a second-wine
statement to the application as it was at c775ea7: the second-wine row is
the only thing on the drawer that may change, and a resolved name not even
that.
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

BEFORE = 'c775ea7'               # Phase 6.2: the application before this phase
CHECKS = []


def check(f):
    CHECKS.append(f)
    return f


def tool(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_')[:-3], L.ROOT + 'tools/' + name)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def generated():
    s = open(L.ROOT + 'data/app/second-status.js', encoding='utf-8').read()
    return json.loads(re.search(r'window\.BDX_SECOND_STATUS = (.*);\n', s).group(1))


# ---------------------------------------------------------------- the generated state is the model's

@check
def generated_state_is_the_models():
    g = generated()
    assert g == tool('build-app-data.py').second_status()
    assert collections.Counter(v['s'] for v in g.values()) == {
        'resolved': 86, 'none': 32, 'unestablished': 13, 'note': 4, 'conflict': 2}
    T = L.read_table
    im = {r['legacy_key']: r for r in T('identity/identity-map.jsonl') if r['namespace'] == 'second-by-name'}
    est = {r['legacy_key']: r['stable_id'] for r in T('identity/identity-map.jsonl')
           if r['namespace'] == 'estate' and r.get('stable_id')}
    absent = {r['estate'] for r in T('state/rank-absences.jsonl')}
    names = {}
    for n in T('identity/names.jsonl'):
        names.setdefault(n['subject'], n['name'])
    assert set(g) == {k.split('|', 1)[0] for k in im}, 'one state per estate-file second string'
    for key, r in im.items():
        lid, text = key.split('|', 1)
        st = g[lid]
        if r['status'] == 'ACTIVE':
            assert st == {'s': 'resolved'}
        elif r['status'] == 'RETIRED':
            assert text == '—' and est[lid] in absent and st['s'] in ('none', 'conflict')
        else:
            assert st['s'] in ('unestablished', 'note') and st['n'] == text
            if st['s'] == 'unestablished':
                assert st['w'] == sorted(names[c] for c in r.get('candidates', [])), lid


@check
def no_hard_coded_estates_in_the_application():
    js = open(L.ROOT + 'assets/app.js', encoding='utf-8').read()
    body = js[js.index('function secondFact'):js.index('function openDrawer')]
    for lid in generated():
        assert "'%s'" % lid not in body and '"%s"' % lid not in body, lid


# ---------------------------------------------------------------- the drawer

FACT_JS = '''(function (id) {
  var box = document.getElementById('search');
  box.value = ''; box.dispatchEvent(new Event('input'));
  var card = document.querySelector('#paneList .pcard[data-ch="' + id + '"]');
  if (!card) return {missing: true};
  card.click();
  var row = null;
  Array.prototype.forEach.call(document.querySelectorAll('#drawerBody .factgrid .fact'), function (f) {
    var dt = f.querySelector('dt');
    if (f.hasAttribute('data-sw') || (dt && dt.textContent === 'Second wine')) row = f;
  });
  var b = document.getElementById('drawerBody').cloneNode(true);
  Array.prototype.forEach.call(b.querySelectorAll('.factgrid .fact'), function (f) {
    var dt = f.querySelector('dt');
    if (f.hasAttribute('data-sw') || (dt && dt.textContent === 'Second wine')) f.parentNode.removeChild(f);
  });
  document.body.appendChild(b);
  var rest = document.getElementById('drawerHead').innerText + '\\n' + b.innerText;
  b.parentNode.removeChild(b);
  var close = document.getElementById('closeDrawer'); if (close) close.click();
  return {label: row ? row.querySelector('dt').textContent : null,
          text: row ? row.querySelector('dd').innerText : null,
          state: row ? row.getAttribute('data-sw') : null,
          italic: row ? Array.prototype.map.call(row.querySelectorAll('dd i'), function (i) { return i.textContent; }) : [],
          rest: rest};
})'''


def site_at(commit):
    """The application as committed at `commit`, in a temporary copy of the site."""
    site = tempfile.mkdtemp(prefix='bdx-63-')
    git = lambda *a: subprocess.check_output(['git'] + list(a), cwd=L.ROOT)
    for f in ['index.html', 'service-worker.js', 'manifest.webmanifest'] + \
            git('ls-tree', '-r', '--name-only', commit, 'assets', 'data/app').decode().split():
        p = os.path.join(site, f)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(git('show', '%s:%s' % (commit, f)))
    for f in os.listdir(L.ROOT + 'data'):
        if f.endswith('.js'):
            shutil.copyfile(L.ROOT + 'data/' + f, os.path.join(site, 'data', f))
    return site


_pages = {}


def drawers(root=None):
    key = root or 'now'
    if key not in _pages:
        B = tool('benchmark-phase5.py')
        out = {}
        with B.Server(root) as srv, B.Browser() as b:
            b.navigate(srv.url)
            time.sleep(0.4)
            b.c.js("document.getElementById('tabProducers').click()")
            time.sleep(0.3)
            for lid in sorted(generated()):
                out[lid] = b.c.js('%s(%s)' % (FACT_JS, json.dumps(lid)))
        _pages[key] = out
    return _pages[key]


def fact(lid):
    return drawers()[lid]


@check
def resolved_name_shown_as_before():
    f = fact('lafite')
    assert (f['label'], f['text'], f['state']) == ('Second wine', 'Carruades de Lafite', 'resolved'), f


@check
def plain_dash_is_no_second_wine_recorded():
    # Saint-Pierre: never crawled. Couhins-Lurton: crawled, nothing said. Both: the dataset's "—".
    for lid in ('saint-pierre', 'couhins-lurton'):
        f = fact(lid)
        assert (f['label'], f['text'], f['state']) == ('Second wine', 'No second wine recorded', 'none'), f
        assert '—' not in f['text']


@check
def conflict_is_shown_as_a_conflict_batailley_lynch_moussas():
    for lid, listed in (('batailley', 'Lions de Batailley'), ('lynch-moussas', 'Les Hauts de Lynch-Moussas')):
        f = fact(lid)
        assert f['state'] == 'conflict' and f['label'] == 'Second wine', f
        assert f['text'].startswith('Conflicting records'), f
        assert 'one record lists none' in f['text'] and f['italic'] == [listed], f
        assert f['text'] != listed, 'the conflict resolved to the listed wine'


@check
def unestablished_name_haut_bailly_and_pichon_baron():
    for lid, recorded, listed in (('haut-bailly', 'La Parde de Haut-Bailly', ['Haut-Bailly II']),
                                  ('pichon-baron', 'Les Tourelles de Longueville', ['Les Griffons de Pichon Baron'])):
        f = fact(lid)
        assert f['state'] == 'unestablished' and f['text'].startswith('Not established'), f
        assert f['italic'] == [recorded] + listed, f
        # neither name is presented as the second wine, and no rename is implied
        assert f['text'] not in (recorded, listed[0]) and 'renamed' not in f['text'].lower(), f
    f = fact('leoville-barton')
    assert f['italic'] == ['La Réserve de Léoville-Barton'] and 'wine list' not in f['text'], f


@check
def notes_are_not_second_wines_yquem_de_carles():
    for lid, text in (('yquem', 'Y d’Yquem (a dry white, not a second wine)'),
                      ('de-carles', 'Haut-Carles (prestige cuvée)')):
        f = fact(lid)
        assert (f['label'], f['text'], f['state']) == ('Recorded note', text, 'note'), f


@check
def every_state_renders_its_contract():
    g = generated()
    want = {'none': 'No second wine recorded', 'conflict': 'Conflicting records', 'unestablished': 'Not established'}
    strings = {r['id']: r.get('second') for r in L.canonical_view()['estates']}
    for lid, st in g.items():
        f = fact(lid)
        assert f.get('state') == st['s'], (lid, f)
        if st['s'] == 'resolved':
            assert f['label'] == 'Second wine' and f['text'] == strings[lid], (lid, f)
        elif st['s'] == 'note':
            assert f['label'] == 'Recorded note' and f['text'] == st['n'], (lid, f)
        else:
            assert f['label'] == 'Second wine' and f['text'].startswith(want[st['s']]), (lid, f)


@check
def nothing_else_on_any_drawer_changed():
    site = site_at(BEFORE)
    try:
        before = drawers(site.replace('\\', '/') + '/')
    finally:
        shutil.rmtree(site, ignore_errors=True)
    now = drawers()
    for lid in generated():
        a, b = before[lid], now[lid]
        assert a['rest'] == b['rest'], 'drawer of %s changed beyond its second-wine row' % lid
        if generated()[lid]['s'] == 'resolved':
            assert (a['label'], a['text']) == (b['label'], b['text']), lid
        else:
            # it was shown as the second wine; now its state is (a note keeps its words
            # and changes its label)
            assert a['label'] == 'Second wine' and (b['label'], b['text']) != (a['label'], a['text']), lid


@check
def search_lookups_and_values_unchanged_against_phase62():
    ar = tool('app-reference.py')
    site = site_at(BEFORE)
    try:
        ref = ar.capture(site.replace('\\', '/') + '/')
    finally:
        shutil.rmtree(site, ignore_errors=True)
    r = ar.compare(ref, ar.capture())
    assert not r['unexplained'], r['unexplained'][:5]
    assert set(r['summary']) <= {'IDENTICAL', 'EXPECTED: SECOND-WINE STATUS PRESENTATION',
                                 'EXPECTED: ADDED SECOND-WINE STATUS (Phase 6.3)',
                                 # Phase 6.5, named: its source facts and provenance wording
                                 'EXPECTED: ADDED SOURCE FACTS (Phase 6.5)',
                                 'EXPECTED: PROVENANCE WORDING PRESENTATION'}, r['summary']
    assert not r['presentation_order'], 'order changed'


@check
def model_and_protected_data_unchanged():
    git = lambda *a: subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode()
    assert not git('diff', '--stat', BEFORE, '--', 'data/model').strip(), 'the model changed'
    changed = [f for f in git('diff', '--name-only', BEFORE, '--', 'data/app').split()
               if not f.endswith(('second-status.js', 'source-facts.js'))]     # Phase 6.3, 6.5
    assert not changed, changed
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
            print('FAIL %s: %s' % (f.__name__, str(ex)[:300]))
    print('%d check(s), %s' % (len(CHECKS), 'all pass' if not fails else '%d FAIL' % fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
