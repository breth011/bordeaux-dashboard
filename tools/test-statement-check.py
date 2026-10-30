"""Statement verification, version 2 (tools/statement_check.py): the M3.12 figure-reader audit's C1-C4.

    python tools/test-statement-check.py

Read-only. Version 1 (tools/m39-evidence-review.py) and everything built on it are untouched: the module is called
by name, here and nowhere in production. The figure reader runs unchanged on the held bytes; version 2 only says
whether the document's own sentence agrees with the reader's figure.

The audited rows are the M3.12 P1 rows whose identity the M3.4A scratchpad rules would settle and which then failed
the figure layer (59), the five that reached ACCEPT, and the four negative controls (five rows). Their identity is
not this module's business: a row is verified here as if its identity held, which is what the audit asked of it.
"""
import importlib.util
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import migration_lib as L  # noqa: E402
import statement_check as S  # noqa: E402

BEFORE = 'f576de9'               # the audit's state: version 1 only
_s = importlib.util.spec_from_file_location('p1_sc', L.ROOT + 'tools/m312-p1-review.py')
P1 = importlib.util.module_from_spec(_s)
_s.loader.exec_module(P1)
V1 = P1.R                        # tools/m39-evidence-review.py, as P1 loads it
CHECKS = []

# review_id -> (field, version 1's verdict, version 2's verdict); NOT_READ: the reader takes no figure.
AUDITED = {
    # C1: "degre N %" - Desmirail's technical block
    'gs_289919c0662e': ('alc', 'NOT_FOUND_AS_STATED', 'CONFIRMED'),   # Desmirail 2005
    'gs_7035c24bcb13': ('alc', 'NOT_FOUND_AS_STATED', 'CONFIRMED'),   # Desmirail 2006
    'gs_c0ccf1561c6e': ('alc', 'NOT_FOUND_AS_STATED', 'CONFIRMED'),   # Desmirail 2007
    'gs_6dd4a0ee3633': ('alc', 'NOT_FOUND_AS_STATED', 'CONFIRMED'),   # Desmirail 2008
    'gs_cdf89ef3c2f4': ('alc', 'NOT_FOUND_AS_STATED', 'CONFIRMED'),   # Desmirail 2009
    'gs_e9cfb881f9ad': ('alc', 'NOT_FOUND_AS_STATED', 'CONFIRMED'),   # Desmirail 2010
    'gs_761f2ec9037f': ('alc', 'NOT_FOUND_AS_STATED', 'CONFIRMED'),   # Desmirail 2011
    'gs_089232b3ba45': ('alc', 'NOT_FOUND_AS_STATED', 'CONFIRMED'),   # Desmirail 2012
    'gs_8140931c7fe1': ('alc', 'NOT_FOUND_AS_STATED', 'CONFIRMED'),   # Desmirail 2013
    'gs_84502c8a0792': ('alc', 'NOT_FOUND_AS_STATED', 'CONFIRMED'),   # Desmirail 2014
    'gs_9249c56c0170': ('alc', 'NOT_FOUND_AS_STATED', 'CONFIRMED'),   # Desmirail 2015
    'gs_7cbff4d0101b': ('alc', 'NOT_FOUND_AS_STATED', 'CONFIRMED'),   # Desmirail 2017
    'gs_c03cb2c8c4c1': ('alc', 'NOT_FOUND_AS_STATED', 'CONFIRMED'),   # Desmirail 2018
    'gs_8a9bc20c4887': ('alc', 'NOT_FOUND_AS_STATED', 'CONFIRMED'),   # Desmirail 2019
    'gs_976bf03579bf': ('alc', 'NOT_FOUND_AS_STATED', 'CONFIRMED'),   # Desmirail 2022
    'gs_d42883fd173e': ('alc', 'NOT_FOUND_AS_STATED', 'CONFIRMED'),   # Desmirail 2023
    # C2: version 1's false contradictions - each grape took the figure of the one before it
    'gs_6889fad412fc': ('blend', 'CONTRADICTED_BY_STATEMENT', 'CONFIRMED'),   # Desmirail 2005 49/51
    'gs_a9f43fa830e9': ('blend', 'CONTRADICTED_BY_STATEMENT', 'CONFIRMED'),   # Desmirail 2007
    'gs_42a98582999d': ('blend', 'CONTRADICTED_BY_STATEMENT', 'CONFIRMED'),   # Desmirail 2008
    'gs_0a492058504f': ('blend', 'CONTRADICTED_BY_STATEMENT', 'CONFIRMED'),   # Desmirail 2009
    'gs_b610ee1c9be4': ('blend', 'CONTRADICTED_BY_STATEMENT', 'CONFIRMED'),   # Desmirail 2010
    'gs_a1895b5cd70f': ('blend', 'CONTRADICTED_BY_STATEMENT', 'CONFIRMED'),   # Desmirail 2011
    'gs_8ad26666d2e1': ('blend', 'CONTRADICTED_BY_STATEMENT', 'CONFIRMED'),   # Desmirail 2012
    'gs_61b42226c3fc': ('blend', 'CONTRADICTED_BY_STATEMENT', 'CONFIRMED'),   # Desmirail 2013
    'gs_e0480b4f9720': ('blend', 'CONTRADICTED_BY_STATEMENT', 'CONFIRMED'),   # Desmirail 2014
    'gs_2e5c1dec1a76': ('blend', 'CONTRADICTED_BY_STATEMENT', 'CONFIRMED'),   # Desmirail 2015
    'gs_bedaa06eff04': ('blend', 'CONTRADICTED_BY_STATEMENT', 'CONFIRMED'),   # Desmirail 2017
    'gs_af7d5e0dd1db': ('blend', 'CONTRADICTED_BY_STATEMENT', 'CONFIRMED'),   # Desmirail 2018
    'gs_60a69cff9333': ('blend', 'CONTRADICTED_BY_STATEMENT', 'CONFIRMED'),   # Desmirail 2019
    'gs_e4c19028482c': ('blend', 'CONTRADICTED_BY_STATEMENT', 'CONFIRMED'),   # Desmirail 2022
    'gs_eccc4afd2daf': ('blend', 'CONTRADICTED_BY_STATEMENT', 'CONFIRMED'),   # Issan 2004
    'gs_ee18a38f44d1': ('blend', 'CONTRADICTED_BY_STATEMENT', 'CONFIRMED'),   # Issan 2008
    'gs_c655425d035f': ('blend', 'CONTRADICTED_BY_STATEMENT', 'CONFIRMED'),   # Issan 2010
    # C3: a bare "BLEND" heading (the English edition)
    'gs_d98884aecff9': ('blend', 'NOT_FOUND_AS_STATED', 'CONFIRMED'),         # Desmirail 2023
    # C4: pH
    'gs_dd04f3148961': ('ph', 'NOT_FOUND_AS_STATED', 'CONFIRMED'),   # Issan 2004
    'gs_dc7cc333faab': ('ph', 'NOT_FOUND_AS_STATED', 'CONFIRMED'),   # Issan 2008
    'gs_08395b0b4a39': ('ph', 'NOT_FOUND_AS_STATED', 'CONFIRMED'),   # Issan 2010
    # positive controls, unchanged
    'gs_047e5d1937fb': ('blend', 'CONFIRMED', 'CONFIRMED'),   # Calon-Segur 2018, share-first list
    'gs_c5d1cdfc1dea': ('blend', 'CONFIRMED', 'CONFIRMED'),   # Desmirail 2006 50/50: version 1 right by coincidence
    'gs_e0dab80ce8cc': ('yld', 'CONFIRMED', 'CONFIRMED'),     # Issan 2004
    'gs_168c78916435': ('yld', 'CONFIRMED', 'CONFIRMED'),     # Issan 2008
    'gs_ad0c9ecec15c': ('yld', 'CONFIRMED', 'CONFIRMED'),     # Issan 2010
    # the reader takes no figure; verification has nothing to verify (C5, C6 and the deferred rows)
    'gs_0e6ecc34fd9d': ('alc', 'NOT_READ', 'NOT_READ'),       # Issan 2004 "Alcool (en % vol.)" - C5
    'gs_c20b109c0b1a': ('alc', 'NOT_READ', 'NOT_READ'),       # Issan 2008 - C5
    'gs_b9a7ca1b06e8': ('alc', 'NOT_READ', 'NOT_READ'),       # Issan 2010 - C5
    'gs_ac9e56dfd0d4': ('blend', 'NOT_READ', 'NOT_READ'),     # Chapelle 1998 - WINE_NOT_ESTABLISHED, deferred
    'gs_b759e729fea7': ('blend', 'NOT_READ', 'NOT_READ'),     # Taillan 2025 - 67 + 23 = 90
    'gs_9266d3e877fa': ('ph', 'NOT_READ', 'NOT_READ'),        # Figeac 2022 primeur - positional table
    'gs_29eb6d397c97': ('yld', 'NOT_READ', 'NOT_READ'),       # Paloumey 2022 - no figure stated
    'gs_3de4583e5795': ('yld', 'NOT_READ', 'NOT_READ'),       # Grand Mayne 1955 "37hl | 37ha" - C6
    'gs_ac87af1bdfbc': ('yld', 'NOT_READ', 'NOT_READ'),       # Grand Mayne 1988
    'gs_22a884a01ee4': ('yld', 'NOT_READ', 'NOT_READ'),       # Grand Mayne 1989
    'gs_40449d7b8b2d': ('yld', 'NOT_READ', 'NOT_READ'),       # Grand Mayne 1990
    'gs_827f77995885': ('yld', 'NOT_READ', 'NOT_READ'),       # Grand Mayne 1995
    'gs_e459ffcc568c': ('yld', 'NOT_READ', 'NOT_READ'),       # Grand Mayne 1998
    'gs_63bbea39fb6d': ('yld', 'NOT_READ', 'NOT_READ'),       # Grand Mayne 2000
    'gs_04f35b7adf76': ('yld', 'NOT_READ', 'NOT_READ'),       # Grand Mayne 2001
    'gs_0b97859d732a': ('yld', 'NOT_READ', 'NOT_READ'),       # Grand Mayne 2002
    'gs_accf30d82396': ('yld', 'NOT_READ', 'NOT_READ'),       # Grand Mayne 2003
    'gs_dbe66388cced': ('yld', 'NOT_READ', 'NOT_READ'),       # Grand Mayne 2004
    'gs_67b1050182f6': ('yld', 'NOT_READ', 'NOT_READ'),       # Grand Mayne 2006
    'gs_2c6ea2d0d65a': ('yld', 'NOT_READ', 'NOT_READ'),       # Grand Mayne 2007
    'gs_b4ac9d7aa9e7': ('yld', 'NOT_READ', 'NOT_READ'),       # Grand Mayne 2008
    'gs_2c8e628997c8': ('yld', 'NOT_READ', 'NOT_READ'),       # Grand Mayne 2009
}
NEGATIVE = {'gs_c5b8167d47e6': 'yld',      # Biston-Brillette 2021 "rendement : 34 hl"
            'gs_934b75abf5ce': 'blend',    # Biston-Brillette 2023
            'gs_7fc4038c38c3': 'yld',      # Biston-Brillette 2023 "rendement : 40 hl"
            'gs_938f2dc37859': 'alc',      # Jean Faure 2025 "degre 13.5" (no %)
            'gs_74c12681d9d9': 'alc'}      # Mangot 2022
FINGERPRINTED = ('tools/m34a-mapping-audit.py', 'tools/sheetreader.py', 'tools/web_evidence.py', 'tools/m35_rubric.py',
                 'tools/read-fiches.py', 'tools/model_schema.py')


def check(f):
    CHECKS.append(f)
    return f


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode('utf-8')


_ROWS = {}


def audited():
    """review_id -> (P1 row, the reader's figure for the field or None, the document's joined text)."""
    if not _ROWS:
        p1 = {r['review_id']: r for r in L.jsonl_lines(P1.OUT) if r.get('record') == 'review'}
        rd = P1.Reader()
        try:
            for rid in sorted(set(AUDITED) | set(NEGATIVE)):
                r = p1[rid]
                got, how, j = rd.figures(r['sha256'], r['estate_id'], r['vintage'])
                _ROWS[rid] = (r, got.get(r['field']), j)
        finally:
            rd.close()
    return _ROWS


def shifted(statement_order, value):
    """Version 1's defect applied to a reader: each grape takes the figure of the grape before it in the text."""
    codes = list(statement_order)
    return {c: value[codes[i - 1]] for i, c in enumerate(codes)}


@check
def t01_version_1_patterns_kept_and_version_1_untouched():
    for f in ('oak', 'months', 'yld', 'alc'):
        assert S.STATED_V1[f].pattern == V1.STATED[f].pattern, f
    assert S.MONTHS == V1.MONTHS and S.NUM == V1.NUM
    assert not git('diff', '--name-only', BEFORE, '--', 'tools/m39-evidence-review.py', 'tools/m312-p1-review.py')


@check
def t02_c1_degre():
    def alc(t):
        return S.stated('alc', t)[0]
    assert alc('mise en bouteille / 14 juin 2007 / degre / 13% / assemblage') == 13.0
    assert alc('degre / 13,5% /') == 13.5 and alc('degre 12,5 % /') == 12.5 and alc('degre : 14,01% /') == 14.01
    assert alc('degre: 13 % /') == 13.0 and alc('degre alcoolique 12,5 % /') == 12.5
    assert alc('degre alcoolique : 14.5% /') == 14.5
    # not alcohol: no %, a temperature, prose, a potential, a plural
    assert alc('chiffres cles / assemblage / elevage / degre 13.5 / acidite totale 3.15') is None
    assert alc('entre la nuit et le jour (autour de 20 / degre !). / les cabernets') is None
    assert alc('peu alcooleux (13 degres de moyenne) et des cabernets, une moyenne de 12 degres.') is None
    assert alc('degre potentiel 14,5% /') is None and alc('degres / 13% /') is None
    # two labels that disagree state nothing; version 1's statement comes first
    assert alc('degre / 13% / ... / degre / 13,5% /') is None
    assert alc('degre / 13% / alcool : 13,5 % /') == 13.5
    assert S.check('alc', 13.0, 'degre / 13% /')[0] == 'CONFIRMED'
    assert S.check('alc', 13.5, 'degre / 13% /')[0] == 'CONTRADICTED_BY_STATEMENT'


@check
def t03_c2_each_grape_its_own_figure():
    def bl(t):
        return S.stated('blend', t)[0]
    assert bl('assemblage / cabernet sauvignon : 49% / merlot : 51% / consultant') == {'CS': 49.0, 'ME': 51.0}
    assert bl('assemblage / cabernet sauvignon : 51% / merlot : 49% / consultant') == {'CS': 51.0, 'ME': 49.0}
    assert bl('assemblage / merlot : 51% / cabernet sauvignon : 49% / consultant') == {'ME': 51.0, 'CS': 49.0}
    assert bl('assemblage / cabernet sauvignon : 60% / merlot : 30% / petit verdot : 10% /') == \
        {'CS': 60.0, 'ME': 30.0, 'PV': 10.0}
    assert bl('assemblage / 65% cabernet sauvignon, 17% merlot, 15% cabernet franc, / 3% petit verdot / degustation') \
        == {'CS': 65.0, 'ME': 17.0, 'CF': 15.0, 'PV': 3.0}
    assert bl('lassemblage / 1 % / cabernet-franc / 46 % / cabernet-sauvignon / 53 % / merlot / les pratiques') == \
        {'CF': 1.0, 'CS': 46.0, 'ME': 53.0}
    assert bl('the blend / 10 % / merlot / 90 % / cabernet / sauvignon / "un des sommets du medoc."') == \
        {'ME': 10.0, 'CS': 90.0}
    assert bl('assemblage / cabernet sauvignon 60 % / merlot 40 % / elevage / 55 % barriques neuves') == \
        {'CS': 60.0, 'ME': 40.0}
    # a correct reader passes; version 1's shift, and a genuinely different blend, fail
    t = 'assemblage / cabernet sauvignon : 49% / merlot : 51% / consultant'
    assert S.check('blend', {'CS': 49, 'ME': 51}, t)[0] == 'CONFIRMED'
    assert S.check('blend', {'CS': 49, 'ME': 49}, t)[0] == 'CONTRADICTED_BY_STATEMENT'
    assert S.check('blend', {'CS': 51, 'ME': 49}, t)[0] == 'CONTRADICTED_BY_STATEMENT'
    assert S.check('blend', {'CS': 60, 'ME': 40}, t)[0] == 'CONTRADICTED_BY_STATEMENT'
    assert V1.check('blend', {'CS': 49, 'ME': 49}, t)[0] == 'CONFIRMED'        # the defect version 2 removes
    # nothing invented: an incomplete list, a list without figures, mixed orders, a planting, a repeated grape,
    # a 1 % lost to a line break, two lists that disagree
    assert bl('assemblage et recolte / 67% merlot 23% cabernet sauvignon. / 13,5% vol') is None
    assert bl('assemblage / cabernet sauvignon, merlot et petit verdot / elevage') is None
    assert bl('assemblage : merlot 53% - cabernet sauvignon 39% - 8% petit / verdot.') is None
    assert bl('encepagement : cabernet sauvignon 50%, merlot 50% / densite') is None
    assert bl('assemblage / merlot 50% / merlot 50% /') is None
    assert bl('assemblage : cabernet sauvignon 72 % merlot 27 % cabernet franc 1 / % / date') is None
    assert bl('assemblage / merlot 60% / cabernet franc 40% / ... assemblage / merlot 70% / cabernet franc 30% /') is None
    # a label must open the list: prose and figures between them break it
    assert bl('lassemblage. / vendanges / du 5 au 22 octobre 2012 / degre / 12% / cabernet sauvignon : 46% / '
              'merlot : 54%') is None
    assert bl('the blend of durfort-vivens 2024 / 94.5% cabernet sauvignon / 5% merlot / 0.5% cabernet franc / '
              'vinification') == {'CS': 94.5, 'ME': 5.0, 'CF': 0.5}


@check
def t04_c3_bare_blend_heading_and_merlot_noir():
    def bl(t):
        return S.stated('blend', t)[0]
    assert bl('degree / 13% / blend / cabernet sauvignon : 55% / merlot : 37% / petit verdot : 4% / cabernet franc : '
              '4% / consultant') == {'CS': 55.0, 'ME': 37.0, 'PV': 4.0, 'CF': 4.0}
    assert bl('/ blend: / 70% merlot / 25% cabernet sauvignon / 3% cabernet franc / 2% petit verdot /') == \
        {'ME': 70.0, 'CS': 25.0, 'CF': 3.0, 'PV': 2.0}
    assert bl('assemblage merlot noir : 21 % ; cabernet sauvignon : 79 % / futs neufs 14 %') == {'ME': 21.0, 'CS': 79.0}
    # "blend" with no usable list, and "blend" inside a sentence, state nothing
    assert bl('/ blend / harvest / vinification / winemaking / degre alcoolique /') is None
    assert bl('/ blend / to be confirmed / 2024 /') is None
    assert bl('a blend of ripe fruit and spice / 60% merlot / 40% cabernet franc /') is None
    assert bl('/ blending was completed in march / 60% merlot / 40% cabernet franc /') is None


@check
def t05_c4_ph():
    def ph(t):
        return S.stated('ph', t)[0]
    assert ph('proportion de 1er vin / 60 % / ph / 3,68 / acidite (en g/1 h2so4) / 3,3 /') == 3.68
    assert ph('ph 3.65 / production') == 3.65 and ph('ph: 3.04 /') == 3.04 and ph('ph : 3,9 /') == 3.9
    # a label row then a value row is positional (Figeac 2022): nothing is attributed
    assert ph('elevage / alcool / ph / 14% / 3.7 / +33 (0)5 57') is None
    assert ph('ph : / alcohol : / 3,80 / 12,70 % / 14 months') is None
    assert ph('ph neutre, 3,5 ha de vignes') is None and ph('ph 7,2 /') is None and ph('phase 3,5 /') is None
    assert ph('ph / 3,68 / ... / ph / 3,72 /') is None
    assert S.check('ph', 3.68, 'ph / 3,68 /')[0] == 'CONFIRMED'
    assert S.check('ph', 3.7, 'ph / 3,68 /')[0] == 'CONTRADICTED_BY_STATEMENT'
    assert V1.check('ph', 3.68, 'ph / 3,68 /')[0] == 'NOT_FOUND_AS_STATED'


@check
def t06_identity_upstream_and_no_repair():
    t = 'degre / 13% / assemblage / cabernet sauvignon : 49% / merlot : 51% / ph / 3,68 /'
    for ident in ('ESTATE_ONLY', 'WINE_AMBIGUOUS', 'VINTAGE_AMBIGUOUS', 'EVIDENCE_INSUFFICIENT', None):
        assert S.verify(ident, 'alc', 13.0, t) == ('NOT_EVALUATED', None, None)
    assert S.verify('SAFE_TO_MAP', 'alc', None, t)[0] == 'NOT_READ'
    assert S.verify('SAFE_TO_MAP', 'alc', 13.0, t)[0] == 'CONFIRMED'
    v = {'CS': 49.0, 'ME': 49.0}
    assert S.verify('SAFE_TO_MAP', 'blend', v, t)[0] == 'CONTRADICTED_BY_STATEMENT' and v == {'CS': 49.0, 'ME': 49.0}


@check
def t07_m39s_committed_figures_unchanged():
    """Every figure M3.9 checked: version 2 gives the same verdict and the same stated value."""
    n = 0
    for r in L.jsonl_lines(V1.OUT):
        if r.get('record') != 'review' or not r.get('figures'):
            continue
        j = V1.joined(V1.P.text_of(r['sha256'])[0])
        for f in r['figures']:
            a, b = V1.check(f['field'], f['value'], j), S.check(f['field'], f['value'], j)
            assert a[0] == b[0] == f['statement_check'] and a[1] == b[1], (r['n'], f['field'], a, b)
            n += 1
    assert n == 9, n


@check
def t08_the_audited_rows():
    rows = audited()
    got = {}
    for rid, (field, v1, v2) in AUDITED.items():
        r, value, j = rows[rid]
        assert r['field'] == field, rid
        if value is None:
            got[rid] = ('NOT_READ', 'NOT_READ')
        else:
            got[rid] = (V1.check(field, value, j)[0], S.verify('SAFE_TO_MAP', field, value, j)[0])
        assert got[rid] == (v1, v2), (rid, r['estate'], r['vintage'], field, got[rid])
    changed = [rid for rid in AUDITED if got[rid][0] != got[rid][1]]
    assert len(changed) == 37 and all(got[rid][1] == 'CONFIRMED' for rid in changed)
    assert len(AUDITED) == 64


@check
def t09_a_shifted_or_wrong_reader_still_fails():
    """Each blend version 2 confirms, with version 1's shift applied to the reader: refused unless the shift changes
    nothing (equal neighbouring shares - Desmirail 2006's 50/50 is the one such row); each figure off by 0.5: refused."""
    rows = audited()
    unchanged = []
    for rid, (field, _, v2) in sorted(AUDITED.items()):
        r, value, j = rows[rid]
        if v2 != 'CONFIRMED':
            continue
        sv, _ = S.stated(field, j)
        if field == 'blend':
            bad = shifted(sv, {k: float(v) for k, v in value.items()})
            if bad == sv:
                unchanged.append(rid)
            else:
                assert S.check(field, bad, j)[0] == 'CONTRADICTED_BY_STATEMENT', rid
            first = sorted(value)[0]
            wrong = dict(value, **{first: float(value[first]) + 0.5})
        else:
            wrong = float(value) + 0.5
        assert S.check(field, wrong, j)[0] == 'CONTRADICTED_BY_STATEMENT', rid
    assert unchanged == ['gs_c5d1cdfc1dea'], unchanged


@check
def t10_deferred_and_refused_rows_stay_as_they_are():
    rows = audited()
    r, value, j = rows['gs_ac9e56dfd0d4']           # Chapelle 1998: stated, but the reader is refused the wine
    assert value is None and S.stated('blend', j)[0] == {'ME': 21.0, 'CS': 79.0}
    assert r['decision'] == 'READER_REFUSED'
    r, value, j = rows['gs_b759e729fea7']           # Taillan 2025: 90 %, no statement
    assert value is None and S.stated('blend', j)[0] is None
    r, value, j = rows['gs_9266d3e877fa']           # Figeac 2022 primeur: positional, no statement, not read
    assert value is None and S.stated('ph', j)[0] is None
    r, value, j = rows['gs_29eb6d397c97']           # Paloumey 2022: no yield stated
    assert value is None and S.stated('yld', j)[0] is None


@check
def t11_negative_controls_stay_refused():
    rows = audited()
    for rid, field in NEGATIVE.items():
        r, value, j = rows[rid]
        assert r['field'] == field and r['decision'] == 'READER_REFUSED' and r['reader_status'] == 'ESTATE_ONLY', rid
        assert S.verify(r['reader_status'], field, 13.0, j) == ('NOT_EVALUATED', None, None), rid
        assert value is None, rid
    # what a broader statement check might have taken from them, it does not
    assert S.stated('alc', rows['gs_938f2dc37859'][2])[0] is None             # "degre 13.5", no %
    assert S.stated('yld', rows['gs_c5b8167d47e6'][2])[0] is None             # "rendement : 34 hl"
    assert S.stated('yld', rows['gs_7fc4038c38c3'][2])[0] is None             # "rendement : 40 hl"
    assert S.stated('blend', rows['gs_c5b8167d47e6'][2])[0] is None           # "encepagement : ... 50%, 50%"


@check
def t12_nothing_in_production_changes():
    assert not git('diff', '--name-only', BEFORE, '--', *FINGERPRINTED)
    users = [p for p in sorted(os.listdir(L.ROOT + 'tools')) if p.endswith('.py') and p not in
             ('statement_check.py', 'test-statement-check.py', 'integration-dryrun.py', 'test-integration-dryrun.py')
             and re.search(r'(?m)^\s*(?:import|from)\s+statement_check\b|statement_check\.py',
                           open(L.ROOT + 'tools/' + p, encoding='utf-8').read())]
    assert not users, users


@check
def t13_deterministic():
    rows = audited()
    once = json.dumps({rid: S.stated(AUDITED[rid][0], rows[rid][2]) for rid in sorted(AUDITED)}, sort_keys=True)
    twice = json.dumps({rid: S.stated(AUDITED[rid][0], rows[rid][2]) for rid in sorted(AUDITED)}, sort_keys=True)
    assert once == twice


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
