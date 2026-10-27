"""M3.6F: Cuvée Mongravey's vintages from its held technical sheets - the audited input the migration reads.

    python tools/m36f-vintages.py             write data/audit/m3.6f-cuvee-vintages.jsonl
    python tools/m36f-vintages.py --check     recompute and compare, byte for byte

THE DOCUMENTS are the held Cuvée de Mongravey sheets M3.6E answered for (data/audit/m3.6e-cuvee-historical-
corrections.jsonl): each read from its own held extraction. A sheet counts for a vintage only when
  - its first line is its title, "Cuvée de Mongravey YYYY" - wn_00640's recorded SOURCE_RENDERING and a year;
  - its latest evidence answer (M3.6E's v7) names wn_00640 and that same title;
  - it is a technical sheet: it has the VINEYARD/VIGNOBLE, VINIFICATION and MATURING/ELEVAGE sections.
A press-review sheet, or a sheet whose title states no year, creates nothing. No filename, URL or page
order is read for a year; "1st Vintage: 1999" stays M3.6D's FIRST_VINTAGE_STATED and creates nothing.

THE VALUES are taxonomy class A only (docs/phase34-model.json: ELEVAGE is class A for duration and new-oak
share), as M3.2D's recovered values are: each stated on a line of its own in the sheet's MATURING/ELEVAGE
section, labelled by its own words, read exactly -
  months  "18 months maturing" / "18 mois d'élevage"      -> "18" (the model's months are text)
  oak     "100% new oak" / "100% bois neuf"                -> 100  (the share of new oak, %)
A line that says more ("24 months maturing depending on vintages") is kept verbatim and not taken as the
vintage's figure. Every sheet of a vintage that states a field is one observation; they must agree
(ONLY_CANDIDATE or UNANIMOUS), or the field is a CONFLICT and nothing is applied.

WITHHELD, each recorded with what is missing and what acquisition would settle it:
  yld, blend    stated in the VINEYARD section beside the estate's surface, plant age and density, the same on
                every 2015-2020 sheet and changed only with the surface in 2022: whether they are the
                vintage's or the vineyard's is not established, and the vineyard's grape varieties are not
                the wine's blend
  production    "Annual production: 2 800 bottles" - class B (BOTTLING_PRODUCTION); the model has no field
  window        "Will reach maturity in 8 years" - class B
  alc, ph, ta, sug, harvest, pick    not stated on any sheet
Absent values are absent (the contract: absent -> nothing, UNKNOWN). No wine, name, estate, rank, attribution
or evidence decision is created or changed.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evidence_store as ST  # noqa: E402
import migration_lib as L  # noqa: E402
import m35_rubric as RB  # noqa: E402
import mig_m6_provenance as M6  # noqa: E402

OUT = L.ROOT + 'data/audit/m3.6f-cuvee-vintages.jsonl'
M36E = L.ROOT + 'data/audit/m3.6e-cuvee-historical-corrections.jsonl'
EXTRACTED = L.ROOT + 'sources/discovery/extracted/'
WINE, NAME = 'wn_00640', 'Cuvée de Mongravey'
EXPECT_VINTAGES = [2015, 2016, 2018, 2019, 2020, 2022]

TITLE = re.compile(r'^Cuvée de Mongravey(?: (\d{4}))?\s*$')
SECTIONS = ((r'^(VINEYARD|VIGNOBLE)$',), (r'^VINIFICATION$',), (r'^(MATURING|ELEVAGE)$',))
NEXT = re.compile(r'^(KEEPING TIME|TEMPS DE GARDE|ENGAGEMENT ENVIRONNEMENTAL|ENVIRONMENTAL COMMITMENT)$')
FIELDS = {
    'months': (re.compile(r'^(\d+) (?:months maturing|mois d.élevage)\.?$'),
               re.compile(r'^(\d+) (?:months maturing|mois d.élevage)\b(.+)$'), lambda n: str(int(n)), None),
    'oak': (re.compile(r'^(\d+)% (?:new oak|bois neuf)\.?$'),
            re.compile(r'^(\d+)% (?:new oak|bois neuf)\b(.+)$'), int, '%'),
}
WITHHELD = {
    'yld': ('SCOPE_NOT_ESTABLISHED', r'^(Yield|Rendement):',
            'stated in the VINEYARD section beside the estate\'s surface, plant age and density; the same on every '
            '2015-2020 sheet and changed only with the surface in 2022, so it is not established as the vintage\'s yield',
            'a sheet or report giving this vintage\'s own yield'),
    'blend': ('SCOPE_NOT_ESTABLISHED', r'^(Grape Varieties|Encépagement):',
              'the VINEYARD section\'s grape varieties (the plots\' planting); the MATURING section blends without '
              'stating proportions, so the wine\'s own blend is not stated',
              'a sheet stating this vintage\'s assemblage'),
    'production': ('CLASS_B_NO_FIELD', r'^(Annual production|Production annuelle):',
                   'BOTTLING_PRODUCTION is taxonomy class B and the model has no observation field for it',
                   'none: a model decision (a production field), not a document'),
    'window': ('CLASS_B', r'^(Will reach maturity|Maturité)',
               'the keeping time is taxonomy class B; this phase populates class A only',
               'none: the statement is held'),
}
NOT_STATED = ('alc', 'ph', 'ta', 'sug', 'harvest', 'pick')


def held_lines(sha):
    d = json.load(open(EXTRACTED + sha + '.json', encoding='utf-8'))
    assert d.get('status') == 'EXTRACTED', sha
    out = []
    for p, page in enumerate(x for x in d.get('pages') or [] if isinstance(x, str)):
        for i, l in enumerate(page.splitlines()):
            if l.strip():
                out.append(('p%d:l%d' % (p + 1, i + 1), l.strip()), )
    return out, d.get('lang_detected')


def section(lines, start):
    """The lines of the section whose heading matches `start`, up to the next heading."""
    out, on = [], False
    heads = [re.compile(h) for s in SECTIONS for h in s] + [NEXT]
    for loc, l in lines:
        if any(h.match(l) for h in heads):
            on = bool(re.match(start, l))
            continue
        if on:
            out.append((loc, l))
    return out


def latest_answers():
    """M3.6E's manifest: per artifact, its superseding v7 rows (from the store)."""
    v7 = {M6.row_key(d): d for d in ST.iter_rows([7])}
    out = {}
    for r in L.jsonl_lines(M36E):
        out.setdefault(r['artifact'], []).append(v7[r['superseded_by']])
    return out


def documents():
    arts = {a['id']: a for a in L.read_table('identity/artifacts.jsonl')}
    names = {n['name']: n for n in L.read_table('identity/names.jsonl') if n['subject'] == WINE}
    assert names.get(NAME, {}).get('kind') == 'SOURCE_RENDERING', 'the title rendering is not wn_00640\'s'
    out = []
    for art, answers in sorted(latest_answers().items()):
        sha = arts[art]['sha256']
        lines, lang = held_lines(sha)
        m = TITLE.match(lines[0][1]) if lines else None
        heads = {s[0]: any(re.match(s[0], l) for _, l in lines) for s in SECTIONS}
        title = [RB.fold(NAME), int(m.group(1)) if m and m.group(1) else None]
        agree = all(a['document_is'] == {'title': title, 'model_wines': [WINE], 'unlisted': False} for a in answers)
        kind = 'TECHNICAL_SHEET' if all(heads.values()) else 'OTHER_SHEET'
        why = []
        if not m:
            why.append('the first line is not the title "%s YYYY"' % NAME)
        elif not m.group(1):
            why.append('the title states no vintage')
        if not agree:
            why.append('the latest evidence answer does not name %s with this title' % WINE)
        if kind != 'TECHNICAL_SHEET':
            why.append('not a technical sheet: %s' % ', '.join(h for h, ok in heads.items() if not ok).replace('^', '').replace('$', ''))
        out.append({'record': 'document', 'artifact': art, 'sha256': sha, 'lang': lang, 'title_line': lines[0][1] if lines else None,
                    'vintage': title[1], 'kind': kind, 'evidence_answers': sorted(M6.row_key(a) for a in answers),
                    'used': not why, 'why_not': why, 'lines': lines})
    return out


def build():
    docs = documents()
    rows = []
    by_year = {}
    for d in docs:
        if d['used']:
            by_year.setdefault(d['vintage'], []).append(d)
    for year in sorted(by_year):
        vt = 'vt:%s:%d' % (WINE, year)
        sheets = by_year[year]
        rows.append({'record': 'vintage', 'vintage': vt, 'wine': WINE, 'label': str(year), 'applied': True,
                     'documents': [s['artifact'] for s in sheets],
                     'basis': 'the title of each technical sheet: %s' % '; '.join('"%s" (%s)' % (s['title_line'], s['artifact']) for s in sheets)})
        for field, (exact, loose, conv, unit) in sorted(FIELDS.items()):
            obs, held = [], []
            for s in sheets:
                for loc, l in section(s['lines'], SECTIONS[2][0]):
                    e = exact.match(l)
                    if e:
                        obs.append({'artifact': s['artifact'], 'locus': loc, 'quote': l, 'value': conv(e.group(1)), 'lang': s['lang']})
                    elif loose.match(l):
                        held.append({'artifact': s['artifact'], 'locus': loc, 'quote': l})
            row = {'record': 'value', 'vintage': vt, 'field': field, 'observations': obs, 'qualified': held}
            if unit:
                row['unit'] = unit
            values = sorted({json.dumps(o['value']) for o in obs})
            if len(values) == 1:
                row.update(applied=True, value=obs[0]['value'], rule='ONLY_CANDIDATE' if len(obs) == 1 else 'UNANIMOUS')
            elif len(values) > 1:
                row.update(applied=False, value=None, status='CONFLICT',
                           why='the vintage\'s sheets state different values: %s' % ', '.join(values))
            else:
                row.update(applied=False, value=None, status='QUALIFIED_ONLY' if held else 'NOT_STATED',
                           why=('stated only with more words than a figure: %s' % ' | '.join(h['quote'] for h in held))
                           if held else 'no sheet of this vintage states it')
            rows.append(row)
        for field, (status, label, why, acquire) in sorted(WITHHELD.items()):
            q = [{'artifact': s['artifact'], 'locus': loc, 'quote': l} for s in sheets for loc, l in s['lines'] if re.match(label, l)]
            rows.append({'record': 'withheld', 'vintage': vt, 'field': field, 'status': status, 'applied': False,
                         'why': why, 'evidence': q, 'acquisition': acquire})
        for field in NOT_STATED:
            rows.append({'record': 'withheld', 'vintage': vt, 'field': field, 'status': 'NOT_STATED', 'applied': False,
                         'why': 'no held sheet of this vintage states it', 'evidence': [],
                         'acquisition': 'a technical sheet or analysis giving this vintage\'s %s' % field})
    for d in docs:
        rows.append({k: v for k, v in d.items() if k != 'lines'})
    rows.append({'record': 'not_created', 'vintage': 'vt:%s:1999' % WINE, 'applied': False,
                 'why': '"1st Vintage: 1999" is M3.6D\'s FIRST_VINTAGE_STATED, a historical statement; no sheet of 1999 is held'})
    got = sorted(int(r['label']) for r in rows if r['record'] == 'vintage')
    if got != EXPECT_VINTAGES:
        raise SystemExit('M3.6F: the held sheets support %s, expected %s' % (got, EXPECT_VINTAGES))
    return rows


def body(rows):
    return ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                   for r in rows).encode('utf-8')


def main():
    b = body(build())
    if '--check' in sys.argv:
        same = os.path.exists(OUT) and open(OUT, 'rb').read() == b
        print('data/audit/m3.6f-cuvee-vintages.jsonl ' + ('is current' if same else 'differs from a fresh run'))
        sys.exit(0 if same else 1)
    open(OUT, 'wb').write(b)
    print('wrote data/audit/m3.6f-cuvee-vintages.jsonl')


if __name__ == '__main__':
    main()
