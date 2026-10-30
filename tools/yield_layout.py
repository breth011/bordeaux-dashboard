"""C6: a yield whose unit a bilingual table splits between its two language lines, read from the page layout.

Grand Mayne's technical sheets set every row of their table as a label cell - the French label, the English one
under it - and a value cell whose French line sits level with the French label and whose English line sits level
with the English one. The yield row reads

    RENDEMENT        37hl
    YIELD            37ha

so neither line says "hl/ha", and the fiche reader (sheetreader, unchanged) rightly reads no yield from it. This
module reads that one layout and nothing else. It is isolated: nothing in production calls it.

Its place is after the identity and after the reader:

    identity established (upstream) -> sheetreader -> this module, only when sheetreader read no yield

Every guard must hold, or it refuses and says which failed:

    1  the identity is SAFE_TO_MAP (it is the caller's; this module never decides a wine or a vintage)
    2  the reader read no yield
    3  a label cell whose lines are "rendement" over "yield", the English line directly under the French
    4  a value cell of exactly two lines in one column, between this label and the next, stating the same number
    5  the French line, level with RENDEMENT, says hl
    6  the English line, level with YIELD, says ha
    7  no other yield in the table, and no permitted, maximum or appellation yield on the row
    8  no other wine of the estate (the caller's names) and no second wine named on the page
    9  no year other than the vintage in the table
   10  the figure within the reader's own yield gate, 5 to 70

and one guard that is applied where the sheet allows it: with the sheet's own area and the grand vin's production in
bottles, the per-hectare reading must be possible. Where the sheet states neither, the guard is recorded as
UNAVAILABLE, not as a failure, and nothing is put in its place.

What it returns is the observation, not a canonical fact. The value and the field are as the sheet states them
(the number, on the row the reader maps to yld); the unit hl/ha is derived from the layout and marked so, and the
two lines the page actually prints are kept as the evidence. Whether that observation is the vintage's harvested
yield is for the field's existing semantics to decide, not for this module.
"""
import re
import unicodedata

import pymupdf

VERSION = 'yield-layout/1'
YLD_GATE = (5.0, 70.0)                   # sheetreader GATES['yld']
FR_LABEL = re.compile(r'^rendements?\s*:?$')
EN_LABEL = re.compile(r'^yields?\s*:?$')
FR_VALUE = re.compile(r'^(\d{1,2}(?:[.,]\d{1,2})?)\s*hl\.?$')
EN_VALUE = re.compile(r'^(\d{1,2}(?:[.,]\d{1,2})?)\s*ha\.?$')
YIELD_WORDS = re.compile(r'\b(?:rendements?|yields?|hl|hectolitres?|hectoliters?)\b|hl\s*/\s*ha')
PERMITTED = re.compile(r'autoris|maxim|plafond|de base|appellation|\baoc\b|\blegal|permitted|allowed')
SECOND_WINE = re.compile(r'\bsecond(?:e)? (?:vin|wine)\b|\b2nd wine\b|\bsecond label\b')
YEAR = re.compile(r'(?<!\d)(1[89]\d\d|20\d\d)(?!\d)')
AREA = re.compile(r'(\d+(?:[.,]\d+)?)\s*(acres|hectares)\b')
BOTTLES = re.compile(r'(\d{1,3}(?:[.\s]\d{3})+|\d+)\s*(?:bouteilles|bottles)\b')
ALIGN = 4.0                              # points: a line level with a label
SAME_X = 2.0                             # points: one column
UNDER = 12.0                             # points: the English label directly under the French one
TABLE_GAP = 30.0                         # points between two rows of one table
GENERIC = {'chateau', 'chateaux', 'clos', 'domaine', 'de', 'du', 'des', 'la', 'le', 'les', 'l', 'd', 'et', 'grand', 'vin'}


def fold(s):
    s = unicodedata.normalize('NFD', s.lower())
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').replace('’', "'")


def num(x):
    return float(x.replace(',', '.'))


def lines_of(page):
    out = []
    for b in page.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            t = ''.join(s['text'] for s in l['spans']).strip()
            if t:
                x0, y0, x1, y1 = l['bbox']
                out.append({'text': t, 'f': ' '.join(fold(t).split()), 'x0': round(x0, 1), 'y0': round(y0, 1),
                            'x1': round(x1, 1), 'y1': round(y1, 1), 'block': b['number']})
    return sorted(out, key=lambda l: (l['y0'], l['x0']))


def _mid(l):
    return (l['y0'] + l['y1']) / 2


def _level_with(line, label, other):
    """The line sits level with this label: centres within ALIGN, and nearer this label than the other. The two
    language lines of a cell overlap by a point or so (1955), so overlap alone cannot say which is which."""
    d = abs(_mid(line) - _mid(label))
    return d <= ALIGN and d < abs(_mid(line) - _mid(other))


def _distinct_words(name, target):
    t = set(re.findall(r"[a-z0-9]+", fold(target)))
    return [w for w in re.findall(r"[a-z0-9]+", fold(name)) if w not in t and w not in GENERIC and len(w) > 2]


def _refuse(guards, n, why, **kw):
    guards.append({'guard': n, 'ok': False, 'why': why})
    return dict({'status': 'REFUSED', 'failed_guard': n, 'reason': why, 'guards': guards, 'version': VERSION}, **kw)


def read_yield(pdf_bytes, identity, reader_yld, vintage, wine_name, other_wine_names=()):
    """The layout's yield for an identified wine and vintage, or the reason there is none."""
    guards = []
    if identity != 'SAFE_TO_MAP':
        return {'status': 'NOT_RUN', 'failed_guard': 1, 'reason': 'identity is %s, not SAFE_TO_MAP' % identity,
                'guards': [{'guard': 1, 'ok': False}], 'version': VERSION}
    guards.append({'guard': 1, 'ok': True})
    if reader_yld is not None:
        return {'status': 'NOT_RUN', 'failed_guard': 2, 'reason': 'the reader read a yield (%s)' % reader_yld,
                'guards': guards + [{'guard': 2, 'ok': False}], 'version': VERSION}
    guards.append({'guard': 2, 'ok': True})

    doc = pymupdf.open(stream=pdf_bytes, filetype='pdf')
    found = []
    for pno, page in enumerate(doc):
        ls = lines_of(page)
        for fr in (l for l in ls if FR_LABEL.match(l['f'])):
            en = [l for l in ls if EN_LABEL.match(l['f']) and abs(l['x0'] - fr['x0']) <= SAME_X
                  and fr['y0'] < l['y0'] <= fr['y1'] + UNDER]
            found.append((pno, ls, fr, en))
    if not found:
        return _refuse(guards, 3, 'no "rendement" label line')
    if len(found) > 1:
        return _refuse(guards, 7, 'more than one "rendement" label (%d)' % len(found))
    pno, ls, fr, en = found[0]
    if len(en) != 1:
        return _refuse(guards, 3, 'no "yield" label directly under "rendement" in the same column')
    en = en[0]
    guards.append({'guard': 3, 'ok': True})

    column = [l for l in ls if abs(l['x0'] - fr['x0']) <= SAME_X]
    after = [l for l in column if l['y0'] > en['y1']]
    next_y = min((l['y0'] for l in after), default=None)
    label_x1 = max(fr['x1'], en['x1'])
    cell = [l for l in ls if l['x0'] > label_x1 + 10 and l['y0'] >= fr['y0'] - ALIGN
            and (next_y is None or l['y0'] < next_y - 1)]
    if len(cell) != 2:
        return _refuse(guards, 4, 'the value cell holds %d lines, not two' % len(cell), cell=[l['text'] for l in cell])
    a, b = cell
    if abs(a['x0'] - b['x0']) > SAME_X:
        return _refuse(guards, 4, 'the two value lines are not in one column')
    ma, mb = FR_VALUE.match(a['f']), EN_VALUE.match(b['f'])
    if not _level_with(a, fr, en):
        return _refuse(guards, 5, 'the first value line is not level with RENDEMENT')
    if not ma:
        return _refuse(guards, 5, 'the line level with RENDEMENT is "%s", not a number with hl' % a['text'])
    if not _level_with(b, en, fr):
        return _refuse(guards, 6, 'the second value line is not level with YIELD')
    if not mb:
        return _refuse(guards, 6, 'the line level with YIELD is "%s", not a number with ha' % b['text'])
    if num(ma.group(1)) != num(mb.group(1)):
        return _refuse(guards, 4, 'the lines state different numbers (%s, %s)' % (ma.group(1), mb.group(1)))
    guards += [{'guard': 4, 'ok': True}, {'guard': 5, 'ok': True}, {'guard': 6, 'ok': True}]
    value = num(ma.group(1))

    # the table: the label column's rows around this one, and their value cells
    rows = sorted(column, key=lambda l: l['y0'])
    i = rows.index(fr)
    lo = hi = i
    while lo > 0 and rows[lo]['y0'] - rows[lo - 1]['y1'] <= TABLE_GAP:
        lo -= 1
    while hi < len(rows) - 1 and rows[hi + 1]['y0'] - rows[hi]['y1'] <= TABLE_GAP:
        hi += 1
    top, last = rows[lo]['y0'] - ALIGN, rows[hi]
    values = [l for l in ls if abs(l['x0'] - a['x0']) <= SAME_X and top <= l['y0'] <= last['y1'] + TABLE_GAP]
    bottom = max([last['y1']] + [l['y1'] for l in values])
    table = [l for l in ls if top <= l['y0'] <= bottom and (abs(l['x0'] - fr['x0']) <= SAME_X or l in values)]
    own = (fr, en, a, b)
    other_yield = [l['text'] for l in table if l not in own and YIELD_WORDS.search(l['f'])]
    if other_yield:
        return _refuse(guards, 7, 'another yield in the table: %s' % other_yield)
    if any(PERMITTED.search(l['f']) for l in own):
        return _refuse(guards, 7, 'a permitted, maximum or appellation yield on the row')
    guards.append({'guard': 7, 'ok': True})

    page_text = '\n'.join(l['f'] for l in ls)
    for name in other_wine_names:
        words = _distinct_words(name, wine_name)
        hit = fold(name) in page_text or any(re.search(r'\b%s\b' % re.escape(w), page_text) for w in words)
        if hit:
            return _refuse(guards, 8, 'another wine of the estate is named on the page: %s' % name)
    if SECOND_WINE.search(page_text):
        return _refuse(guards, 8, 'a second wine is named on the page')
    guards.append({'guard': 8, 'ok': True})

    years = sorted({int(y) for l in table for y in YEAR.findall(l['f'])} - {vintage})
    if years:
        return _refuse(guards, 9, 'another year in the table: %s' % years)
    guards.append({'guard': 9, 'ok': True})

    if not YLD_GATE[0] <= value <= YLD_GATE[1]:
        return _refuse(guards, 10, '%g is outside the yield gate %s' % (value, YLD_GATE))
    guards.append({'guard': 10, 'ok': True})

    rest = '\n'.join(l['f'] for l in ls if l not in own)
    area, bottles = AREA.search(rest), BOTTLES.search(rest)
    arithmetic = {'guard': 'arithmetic', 'status': 'UNAVAILABLE',
                  'why': 'the sheet states %s' % ('no area' if not area else 'no production in bottles')}
    if area and bottles:
        ha = num(area.group(1)) * (0.404686 if area.group(2) == 'acres' else 1.0)
        grand_vin_hl = int(re.sub(r'\D', '', bottles.group(1))) * 0.75 / 100
        per_ha, total = value * ha >= grand_vin_hl, value >= grand_vin_hl
        arithmetic = {'guard': 'arithmetic', 'area': area.group(0), 'production': bottles.group(0),
                      'grand_vin_hl': round(grand_vin_hl, 1), 'hl_on_the_area_if_per_ha': round(value * ha, 1),
                      'per_ha_possible': per_ha, 'total_possible': total,
                      'status': 'PASSED' if per_ha and not total else 'NOT_DISCRIMINATING' if per_ha else 'FAILED'}
        if not per_ha:
            return _refuse(guards, 'arithmetic', 'per hectare, %g on %s is less than the grand vin\'s %s' % (
                value, area.group(0), bottles.group(0)), arithmetic=arithmetic)
    return {'status': 'READ', 'field': 'yld', 'value': value, 'unit': 'hl/ha',
            'unit_basis': 'LAYOUT_DERIVED: "%s" on the French line level with "%s", "%s" on the English line level '
                          'with "%s"; the page prints neither "hl/ha" nor "per hectare"' % (a['text'], fr['text'],
                                                                                         b['text'], en['text']),
            'field_basis': 'the row labelled "%s" / "%s", which the fiche reader maps to yld' % (fr['text'], en['text']),
            'evidence': {'page': pno, 'label': [fr['text'], en['text']], 'lines': [
                {k: l[k] for k in ('text', 'x0', 'y0', 'x1', 'y1')} for l in own],
                'table': {'first_label': rows[lo]['text'], 'last_label': last['text'], 'y': [round(top, 1), bottom],
                          'lines': len(table)}},
            'arithmetic': arithmetic, 'guards': guards, 'version': VERSION}
