"""C6, the layout-derived yield (tools/yield_layout.py): Grand Mayne's bilingual "RENDEMENT 37hl / YIELD 37ha" cell.

    python tools/test-yield-layout.py

Read-only. The module is isolated: nothing in production calls it, and sheetreader is unchanged. The 16 Grand Mayne
sheets of the M3.12 P1 corpus (the 15 audited and 2005) are read from the held bytes; every guard is shown refusing,
on real documents that write yields otherwise, on real Grand Mayne pages with one thing added, and on built pages
that break one condition each. Identity is the caller's: here it is given, as the module's contract asks.
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import warnings

warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import migration_lib as L  # noqa: E402
import pymupdf  # noqa: E402
import yield_layout as Y  # noqa: E402

BEFORE = 'bf65c54'               # C1-C4: the state this phase starts from
_s = importlib.util.spec_from_file_location('m36a_yl', L.ROOT + 'tools/m36a-rerun.py')
X = importlib.util.module_from_spec(_s)
_s.loader.exec_module(X)
CHECKS = []
WINE, OTHERS = 'Château Grand Mayne', ('Filia de Grand Mayne',)
GRAND_MAYNE = {   # vintage: (held sha256, the yield both lines state)
    1955: ('61b1c782269a6315988eb0f2edd7077313c12c2ab956b22c42c6916b94652b93', 37.0),
    1988: ('d64657b1098947dc825bf8d1204c6562a0d69f2b79dbd62e9d9e24c06023cc7b', 38.0),
    1989: ('fc4523d9331b9f212a34f3a56335666fd5e6b7fa4c7526f8f87a89c7c9013e20', 45.0),
    1990: ('201e638a67102ce248190f1f4181021041629e0ed74baf5e08f6ead78246e24f', 47.0),
    1995: ('c1ca665bc4e228da7876e305a9252eb91f608798bcf91b816b2568fa078783d2', 40.0),
    1998: ('e621327f77f4cf9fdbe2983b5b6d781583be572e65e4877aa913715434172a4d', 36.0),
    2000: ('35cee7b6f3fa028959aac91c7d6631a5cefec6ac575c050550eb30b25c3ccdd5', 38.0),
    2001: ('8af3865080cd3c5f8bfd52d7061b3ff0b8a8dd8d841c17c73fd9cec95cdd640c', 37.0),
    2002: ('35b5bedee95d80a396414cffabde65bf6b7d544d5de8a0bc700a031660bb2c73', 25.0),
    2003: ('33baec18f8ea05e17a0b16af2838668eb7a0771bcdf79c369e65f9d938001748', 18.0),
    2004: ('ccca092ea82842e7445f49ee35b9fbef0ba27af68ae264eff052e92322427e93', 38.0),
    2005: ('6e2c81c5bdf9cccf791a9edf33b86ac0f5049334c8e0893d5eec51b95f5358ff', 35.0),
    2006: ('f637e8ffdac9e1eb836fd8c0c756dfd7d89b93d4c93e9dd9c87928ea75ee8504', 38.0),
    2007: ('adf1b2fb122a11b9a68410b4162a1ca630b619df25afb83a7a465d25c8b69e05', 38.0),
    2008: ('75420b11802ba498624f55cd43fd5f2b2d71f13d91fe44664cdb586bfbdc5236', 35.0),
    2009: ('729e6c8203200253bfe4e83a85440afd8b4340bc3ec307473521140fb88dd3d9', 38.0),
}
REAL_NEGATIVES = {   # held documents that state a yield another way; none is this layout
    '5c6adcf35966ed0f4e4c7e8a76df1ab7a86d4fda7e64ebe9d9e7c64196763dad': 'Biston-Brillette 2021 "rendement : 34 hl"',
    '8ceafdfe14d291eabd341c152b88c593dc23f2c2e559daeada68322dc69a9fb2': 'Biston-Brillette 2023 "rendement : 40 hl"',
    '987f8307609048a9186b1e743da82cd5384db7b47ca86a90a5ed8406ee54e9f3': 'Lynch-Bages 2021 "yields (appellation) / 35 hl"',
    '2e9f05687822df9ba30443e28d53bbddaffbd7978031c27e61f0aedaa966fafa': 'Echo de Lynch-Bages 2021, the same',
    'e7b9f9c1ea0fbb27f2a6d20f87041590ca2219a31341496ac4da75a0c42d5951': 'Haut de Smith "yield : 30 hl"',
    '650113bd6f953ffb3f2b281192cc6192a08d186f9c99a3e05c1718abd5188f3e': 'Cantenac-Brown 2024 press dossier',
    'ff3f74b8517dd5cc79e186927b57e5806f5d06490f74f755baec132e872e75cf': 'Paloumey 2022 "Rendement (hl/ha)", no figure',
    '87b0089b0f121418d3b28952eea24068e6ab20c1bfcf12fe1949394f49599edd': 'Issan 2004 "Rendement 54 hl/ha"',
}
FINGERPRINTED = ('tools/m34a-mapping-audit.py', 'tools/sheetreader.py', 'tools/web_evidence.py', 'tools/m35_rubric.py',
                 'tools/read-fiches.py', 'tools/model_schema.py')
_BYTES = {}


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode('utf-8')


def held(sha):
    if sha not in _BYTES:
        p = X.Presenter()
        try:
            _BYTES[sha] = p.blob(sha)
        finally:
            p.close()
    return _BYTES[sha]


def read(b, vintage, identity='SAFE_TO_MAP', reader_yld=None, others=OTHERS):
    return Y.read_yield(b, identity, reader_yld, vintage, WINE, others)


def with_text(sha, inserts):
    """A held page with lines added: [(x, baseline y, text, size)]."""
    doc = pymupdf.open(stream=held(sha), filetype='pdf')
    for x, y, t, s in inserts:
        doc[0].insert_text((x, y), t, fontsize=s)
    return doc.tobytes()


def built(rows, area=None, production=None, extra=()):
    """A page laid out as Grand Mayne's table: rows of (French label, English label, [(value, size)])."""
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    y = 400.0
    if area:
        page.insert_text((64, y - 20), 'AREA OF PRODUCTION', fontsize=7)
        page.insert_text((230, y - 20), area, fontsize=7)
    for fr, en, vals in rows:
        page.insert_text((64, y), fr, fontsize=9)
        page.insert_text((64, y + 9.5), en, fontsize=5)
        vy = y
        for t, s in vals:
            page.insert_text((230, vy), t, fontsize=s)
            vy += 9.5 if s >= 9 else 10
        y += 27
    if production:
        page.insert_text((64, y), 'PRODUCTION', fontsize=9)
        page.insert_text((230, y), production, fontsize=9)
    for x, yy, t, s in extra:
        page.insert_text((x, yy), t, fontsize=s)
    return doc.tobytes()


BASE = [('AGE MOYEN DES VIGNES', 'AVERAGE AGE OF THE VINES', [('35 ans', 9), ('35 years', 7)]),
        ('RENDEMENT', 'YIELD', [('37hl', 9), ('37ha', 7)]),
        ('VINIFICATION', 'WINEMAKING', [('Cuves bois', 9), ('Wooden tanks', 7)]),
        ('ALCOOL', 'ALCOHOL', [('13,5% vol.', 9)])]


def variant(cell=None, label=None, en_label=None, extra_rows=()):
    rows = []
    for fr, en, vals in BASE:
        if fr == 'RENDEMENT':
            rows.append((label or fr, en_label or en, cell or vals))
        else:
            rows.append((fr, en, vals))
    return rows + list(extra_rows)


@check
def t01_the_sixteen_grand_mayne_sheets():
    for v, (sha, want) in sorted(GRAND_MAYNE.items()):
        r = read(held(sha), v)
        assert r['status'] == 'READ' and r['value'] == want and r['unit'] == 'hl/ha' and r['field'] == 'yld', (v, r)
        a, b = r['evidence']['lines'][2:]
        assert re.fullmatch(r'%dh[l]' % want, a['text']) and re.fullmatch(r'%dha' % want, b['text']), (v, a, b)
        assert r['unit_basis'].startswith('LAYOUT_DERIVED') and 'neither "hl/ha"' in r['unit_basis']
        assert [g['guard'] for g in r['guards']] == list(range(1, 11)) and all(g['ok'] for g in r['guards'])
        assert r['evidence']['label'] == [x['text'] for x in r['evidence']['lines'][:2]]
        assert 'harvest' not in json.dumps(r).lower(), v          # the observation, not a claim about the field
    # 2008 and 2009 set each value line in its label's text block: the same reading
    assert read(held(GRAND_MAYNE[2008][0]), 2008)['value'] == 35.0


@check
def t02_the_arithmetic_guard_where_the_sheet_allows_it():
    for v, (sha, want) in sorted(GRAND_MAYNE.items()):
        ar = read(held(sha), v)['arithmetic']
        if v == 1955:      # no production row: recorded unavailable, nothing put in its place
            assert ar == {'guard': 'arithmetic', 'status': 'UNAVAILABLE', 'why': 'the sheet states no production in bottles'}
        else:
            assert ar['status'] == 'PASSED' and ar['per_ha_possible'] and not ar['total_possible'], (v, ar)
            assert ar['area'] == '43 acres', (v, ar)
    # a sheet whose own figures make the per-hectare reading impossible is refused
    r = read(built(variant(), area='2 hectares', production='100.000 bouteilles'), 2010)
    assert r['status'] == 'REFUSED' and r['failed_guard'] == 'arithmetic', r
    r = read(built(variant(), area='17 hectares', production='40.000 bouteilles'), 2010)
    assert r['status'] == 'READ' and r['arithmetic']['status'] == 'PASSED', r


@check
def t03_identity_and_the_reader_come_first():
    sha, _ = GRAND_MAYNE[2003]
    for ident in ('ESTATE_ONLY', 'VINTAGE_AMBIGUOUS', 'WINE_AMBIGUOUS', None):
        r = read(held(sha), 2003, identity=ident)
        assert r['status'] == 'NOT_RUN' and r['failed_guard'] == 1, (ident, r)
    r = read(held(sha), 2003, reader_yld=18.0)
    assert r['status'] == 'NOT_RUN' and r['failed_guard'] == 2, r
    # Issan 2004: the reader reads "Rendement 54 hl/ha"; the module is not run
    issan = '87b0089b0f121418d3b28952eea24068e6ab20c1bfcf12fe1949394f49599edd'
    assert read(held(issan), 2004, reader_yld=54.0)['failed_guard'] == 2


@check
def t04_real_documents_that_write_yields_otherwise():
    for sha, what in sorted(REAL_NEGATIVES.items()):
        r = read(held(sha), 2021, others=())
        assert r['status'] == 'REFUSED', (what, r)


@check
def t05_real_grand_mayne_pages_with_one_thing_added():
    sha, _ = GRAND_MAYNE[2003]          # RENDEMENT at y 458-469, value column x 229.6
    r = read(with_text(sha, [(229.6, 475.5, '20hl', 6)]), 2003)
    assert r['status'] == 'REFUSED' and r['failed_guard'] == 4, r                # a third line in the cell
    r = read(with_text(sha, [(300, 600, 'Filia de Grand Mayne', 8)]), 2003)
    assert r['status'] == 'REFUSED' and r['failed_guard'] == 8, r                # the estate's other wine
    r = read(with_text(sha, [(300, 600, 'Second vin', 8)]), 2003)
    assert r['status'] == 'REFUSED' and r['failed_guard'] == 8, r
    r = read(with_text(sha, [(229.6, 504, 'Vendanges 2004', 7)]), 2003)
    assert r['status'] == 'REFUSED' and r['failed_guard'] == 9, r                # another year in the table
    r = read(with_text(sha, [(63.8, 630, 'RENDEMENT', 9), (63.8, 640, 'YIELD', 5), (229.6, 630, '55hl', 9),
                             (229.6, 640, '55ha', 7)]), 2003)
    assert r['status'] == 'REFUSED' and r['failed_guard'] == 7, r                # a second yield row
    assert read(with_text(sha, [(300, 760, 'Drink 2010-2020', 8)]), 2003)['status'] == 'READ'   # years in the notes


@check
def t06_built_pages_breaking_one_condition_each():
    assert read(built(variant()), 2010)['status'] == 'READ'
    cases = {
        'English number differs': (variant(cell=[('37hl', 9), ('36ha', 7)]), 4),
        'units swapped': (variant(cell=[('37ha', 9), ('37hl', 7)]), 5),
        'hl only, no ha line': (variant(cell=[('37hl', 9)]), 4),
        'conventional "37 hl/ha" (the reader\'s business)': (variant(cell=[('37 hl/ha', 9)]), 4),
        'a number with no unit': (variant(cell=[('37', 9), ('37', 7)]), 5),
        'permitted yield label': (variant(label='RENDEMENT AUTORISE'), 3),
        'appellation yield label': (variant(en_label='YIELD (APPELLATION)'), 3),
        'English label missing': (variant(en_label='-'), 3),
        'a maximum yield row in the table': (variant(extra_rows=[('MAXIMUM', 'MAXIMUM YIELD', [('55 hl/ha', 9)])]), 7),
        'out of the yield gate': (variant(cell=[('85hl', 9), ('85ha', 7)]), 10),
    }
    for name, (rows, guard) in cases.items():
        r = read(built(rows), 2010)
        assert r['status'] == 'REFUSED' and r['failed_guard'] == guard, (name, r)
    # the yield row's baselines: RENDEMENT 427, YIELD 436.5; the next row's label 454
    # the English line out of alignment: below YIELD, between the two rows
    doc = pymupdf.open(stream=built(variant(cell=[('37hl', 9)])), filetype='pdf')
    doc[0].insert_text((230, 447), '37ha', fontsize=7)
    r = read(doc.tobytes(), 2010)
    assert r['status'] == 'REFUSED' and r['failed_guard'] == 6, r
    # the English line level with YIELD, but in another column
    doc = pymupdf.open(stream=built(variant(cell=[('37hl', 9)])), filetype='pdf')
    doc[0].insert_text((300, 437), '37ha', fontsize=7)
    r = read(doc.tobytes(), 2010)
    assert r['status'] == 'REFUSED' and r['failed_guard'] == 4, r


@check
def t07_deterministic():
    once = json.dumps({v: read(held(sha), v) for v, (sha, _) in sorted(GRAND_MAYNE.items())}, sort_keys=True)
    twice = json.dumps({v: read(held(sha), v) for v, (sha, _) in sorted(GRAND_MAYNE.items())}, sort_keys=True)
    assert once == twice


@check
def t08_isolated_and_nothing_in_production_changes():
    assert not git('diff', '--name-only', BEFORE, '--', *FINGERPRINTED)
    users = [p for p in sorted(os.listdir(L.ROOT + 'tools')) if p.endswith('.py') and p not in
             ('yield_layout.py', 'test-yield-layout.py', 'integration-dryrun.py', 'test-integration-dryrun.py',
              'test-recording-policy.py', 'test-recording-branches.py', 'integration-review.py', 'test-integration-review.py')
             and re.search(r'(?m)^\s*(?:import|from)\s+yield_layout\b|yield_layout\.py',
                           open(L.ROOT + 'tools/' + p, encoding='utf-8').read())]
    assert not users, users


def main():
    fails = 0
    for f in CHECKS:
        try:
            f()
            print('ok   %s' % f.__name__)
        except Exception as e:
            fails += 1
            print('FAIL %s: %r' % (f.__name__, e))
    print('%d check(s), %s' % (len(CHECKS), 'all pass' if not fails else '%d FAIL' % fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
