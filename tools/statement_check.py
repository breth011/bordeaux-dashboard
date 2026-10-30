"""Statement verification, version 2: what a document's own sentence states for a field, and whether a reader's figure
agrees with it. M3.9's check (tools/m39-evidence-review.py: stated, check) is the first version and stays as it is,
with everything built on it; this module is used only where it is called by name.

The order is fixed and this module is only its last step:

    identity established (upstream) -> figure reader (sheetreader, unchanged) -> statement verification (here)

It never establishes a wine or a vintage (verify refuses to run unless the identity is SAFE_TO_MAP), never reads a
figure the reader did not read, and never repairs one: it says CONFIRMED, CONTRADICTED_BY_STATEMENT or
NOT_FOUND_AS_STATED. The text is M3.9's joined form: folded, one line per " / ".

What changed from version 1 (the M3.12 figure-reader audit, C1-C4):

  C1  alc    "degre N %" and "degre alcoolique N %", the French technical label, when no version-1 statement is
             found. The % is required: "degre 13.5" is not read, nor "20 degre" (a temperature), "degres de
             moyenne" (prose) or a "degre potentiel".
  C2  blend  each grape takes its own figure. Version 1 searched every grape for "N % grape" before "grape N %" and
             took the leftmost hit, so in "cabernet sauvignon : 49% / merlot : 51%" merlot took 49 - the figure of
             the grape before it. A list is now read in its own order: its first token decides whether it is
             grape-then-figure or figure-then-grape, the tokens must alternate with nothing but separators between
             them, and the figures must account for the wine (100, within 0.5). An incomplete list states nothing.
  C3  blend  a bare "blend" heading line opens a list, and "merlot noir" is merlot.
  C4  ph     "ph N,NN" with the value directly after the label, between 2.5 and 4.5.

Where a field's statements disagree with each other the document states nothing for it.
"""
import re

VERSION = 'statement-check/2'

NUM = r'(\d+(?:[.,]\d+)?)'
# Version 1's patterns, unchanged (tools/m39-evidence-review.py STATED); test-statement-check.py compares them.
STATED_V1 = {
    'oak': re.compile(NUM + r'\s*%\s*(?:/\s*)?(?:in\s+|en\s+|de\s+)?(?:new\s+(?:oak\s+)?barrels|barriques\s+neuves|new\s+oak)'),
    'months': re.compile(r'(?:ageing|aging|elevage)\b[^%]{0,40}?\b(\d{1,2})\s*(?:months|mois)\b'),
    'yld': re.compile(NUM + r'\s*hl\s*/\s*ha'),
    'alc': re.compile(NUM + r'\s*%\s*(?:alcohol|alc\b|vol)|(?:alcohol|alcool)\s*(?:content)?\s*:?\s*' + NUM + r'\s*%'),
}
MONTHS = {'01': 'january', '02': 'february', '03': 'march', '04': 'april', '05': 'may', '06': 'june', '07': 'july',
          '08': 'august', '09': 'september', '10': 'october', '11': 'november', '12': 'december'}

# C1: the label, singular, then the figure and its %. Only " / " (a line break) or ":" may stand between.
DEGRE = re.compile(r'\bdegre(?:\s+alcoolique)?\s*:?\s*(?:/\s*)?(\d{1,2}(?:[.,]\d{1,2})?)\s*%')

# C2/C3: the labels that open a blend list - version 1's, the longer "blend of <name> YYYY" tried before "the blend"
# so that the year is the label's and not the list's (Durfort-Vivens 2024), and a line that says only "blend".
BLEND_LABEL = re.compile(r'(?:(?:the )?blend of [a-z -]{0,30}\d{4}|the blend|l.?\s?assemblage|assemblage)\b'
                         r'|(?:^|/ )blend\s*:?(?= /|$)')
# The reader's grape codes (sheetreader.VARS), in the folded text; longest names first. A name may break across
# lines, as version 1 allowed: "cabernet / sauvignon" (Durfort-Vivens 2014).
GRAPES = (('CS', r'cabernets?[\s\-/]*sauvignons?'), ('CF', r'cabernets?[\s\-/]*francs?'),
          ('PV', r'petits?[\s\-/]*verdots?'), ('SB', r'sauvignons?[\s\-/]*blancs?'), ('SG', r'sauvignons?[\s\-/]*gris'),
          ('ME', r'merlots?(?:[\s/]+noirs?)?'), ('MA', r'malbecs?'), ('CA', r'carmeneres?'), ('SEM', r'semillons?'),
          ('MU', r'muscadelles?'))
GRAPE = re.compile('|'.join(r'(?P<%s>\b(?:%s)\b)' % (c, p) for c, p in GRAPES))
SHARE = re.compile(r'(?<![\d.,])(\d{1,3}(?:[.,]\d{1,2})?)\s*%')
# what may stand between a label and its list: words, no figure; between two tokens of a list: separators only
LEAD = re.compile(r'^[^\d%]{0,40}$')
GAP = re.compile(r"^(?:[\s/:;,.\-–+&()]|\bde\b|\bdu\b|\bet\b|\band\b|d')*$")
WINDOW = 200
# Rounding only: "cabernet sauvignon 72 % merlot 27 % cabernet franc 1 / %" loses its 1 % to the line break, and
# 99 must not pass as the whole wine.
TOTAL_TOLERANCE = 0.5

# C4: the label, then the value at once.
PH = re.compile(r'\bph\b\s*:?\s*(?:/\s*)?(\d[.,]\d{1,2})(?![\d%])')
PH_RANGE = (2.5, 4.5)


def num(x):
    return float(x.replace(',', '.'))


def _tokens(window):
    """The window's grapes and shares in text order: (start, end, 'G'|'S', code or value)."""
    out = [(m.start(), m.end(), 'G', m.lastgroup) for m in GRAPE.finditer(window)]
    out += [(m.start(), m.end(), 'S', num(m.group(1))) for m in SHARE.finditer(window)]
    return sorted(out)


def blend_list(window):
    """The list a blend label opens, read in its own order: {code: share} when it accounts for the wine, else None."""
    toks = _tokens(window)
    if not toks or not LEAD.match(window[:toks[0][0]]):
        return None
    first = toks[0][2]
    run = [toks[0]]
    for t in toks[1:]:
        if t[2] == run[-1][2] or not GAP.match(window[run[-1][1]:t[0]]):
            break
        run.append(t)
    if len(run) % 2:
        run = run[:-1]                           # a grape with no figure, or a figure with no grape, ends the list
    out = {}
    for a, b in zip(run[0::2], run[1::2]):
        code, share = (a[3], b[3]) if first == 'G' else (b[3], a[3])
        if code in out:
            return None
        out[code] = share
    if not out or abs(sum(out.values()) - 100) > TOTAL_TOLERANCE:
        return None
    return out


def _one(found):
    """found: [(value, words)]. The value when every statement agrees, with the first one's words."""
    if not found or len({v if not isinstance(v, dict) else tuple(sorted(v.items())) for v, _ in found}) != 1:
        return None, None
    return found[0]


def stated(field, j):
    """(stated value, the words) the document's own text gives for a field, or (None, None)."""
    if field in ('oak', 'months', 'yld'):
        m = STATED_V1[field].search(j)
        if m:
            return num(next(g for g in m.groups() if g)), m.group(0)
        return None, None
    if field == 'alc':
        m = STATED_V1['alc'].search(j)
        if m:
            return num(next(g for g in m.groups() if g)), m.group(0)
        return _one([(num(m.group(1)), m.group(0)) for m in DEGRE.finditer(j)])
    if field == 'blend':
        found = []
        for m in BLEND_LABEL.finditer(j):
            b = blend_list(j[m.end():m.end() + WINDOW])
            if b:
                found.append((b, j[m.start():m.end() + WINDOW][:160]))
        return _one(found)
    if field == 'ph':
        return _one([(num(m.group(1)), m.group(0)) for m in PH.finditer(j)
                     if PH_RANGE[0] <= num(m.group(1)) <= PH_RANGE[1]])
    return None, None


def check(field, value, j):
    """A reader's figure against the document's statement: (CONFIRMED | CONTRADICTED_BY_STATEMENT |
    NOT_FOUND_AS_STATED, stated value, words). The figure is compared, never changed."""
    if field == 'pick':
        dates = [d for v in value.values() for d in v.split('|')]
        ok = all(re.search(r'\b%s\s+0?%d\b|\b0?%d\s+%s\b' % (MONTHS[d[:2]], int(d[3:]), int(d[3:]), MONTHS[d[:2]]), j)
                 for d in dates)
        return ('CONFIRMED' if ok else 'NOT_FOUND_AS_STATED'), None, None
    sv, words = stated(field, j)
    if sv is None:
        return 'NOT_FOUND_AS_STATED', None, None
    if field == 'blend':
        same = {k: float(v) for k, v in value.items()} == sv
    else:
        same = float(value) == sv
    return ('CONFIRMED' if same else 'CONTRADICTED_BY_STATEMENT'), sv, words


def verify(identity, field, value, j):
    """check(), after the identity: a document not yet SAFE_TO_MAP for the wine and vintage is not verified at all."""
    if identity != 'SAFE_TO_MAP':
        return 'NOT_EVALUATED', None, None
    if value is None:
        return 'NOT_READ', None, None
    return check(field, value, j)
