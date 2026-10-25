"""M3.2: recovering held data. The rules: where a figure stands in a held document, as that figure.

Pure rules over text; no I/O except reading held extraction text. A figure's value counts as
explicitly present only where it stands with its own field's label - the alcohol beside
"alcool"/"alcohol"/"degré"/"% vol", the pH after "pH", the yield with "rendement"/"yield" and hl,
the new-oak share with "neuf"/"new", the months with "mois"/"months" after an élevage word,
every blend share beside its own grape. A number printed elsewhere ("14 % Cabernet Franc" is not
an alcohol) is not evidence of that field.

    classify(field, model_value, segments) -> {classification, hits, locus?, quote?, found?}

classification:
    MODEL_MATCHES    the field, labelled, states exactly the model's value
    MODEL_CONFLICT   the field, labelled, states another value, and never the model's
    DUPLICATE_VALUE  the field, labelled, states the model's value and another one too
    AMBIGUOUS        the value is printed, but not with its field's label
    NOT_FOUND        nothing
    FIELD_NOT_CHECKABLE  the field has no deterministic reading here (dates, free text, ranges)
"""
import re
import unicodedata

VERSION = 'm32-recovery/1'

GRAPES = {
    'CS': r'cabernet[\s-]*sauvignon', 'CF': r'cabernet[\s-]*franc', 'ME': r'merlot', 'PV': r'petit[\s-]*verdot',
    'MA': r'malbec|cot\b', 'CR': r'carmen[eè]re', 'SB': r'sauvignon(?:[\s-]*blanc)?', 'SG': r'sauvignon[\s-]*gris',
    'SE': r's[eé]millon', 'MU': r'muscadelle',
}
NUM = r'(\d{1,3}(?:[.,]\d{1,2})?)'


def fold(s):
    # NFKD: PDF text carries ligatures ("Superﬁcie") that must read as their letters
    return ''.join(c for c in unicodedata.normalize('NFKD', s.lower()) if unicodedata.category(c) != 'Mn')


def _f(x):
    try:
        return float(str(x).replace(',', '.'))
    except ValueError:
        return None


# One anchored pattern per field; group 1 is the value. Each pattern requires the field's label.
ANCHORED = {
    'alc': [re.compile(r'(?:alcool|alcohol|degre(?:\s+d.alcool)?|titre\s+alcoometrique|t\.?a\.?v\.?|alc\.?)'
                       r'[^\d%]{0,30}?' + NUM + r'\s*(?:%|°)'),
            re.compile(NUM + r'\s*%\s*(?:vol\b|alc\.?\s*/\s*vol)')],     # not "100% Alcohol 12,5%"
    'ph': [re.compile(r'(?<![a-z])ph\s*[:=]?\s*' + NUM)],
    'yld': [re.compile(r'(?:rendement|yield)[^\d]{0,40}?' + NUM + r'\s*(?:hl|hecto)')],
    'oak': [re.compile(NUM + r'\s*%\s*(?:de\s+)?(?:(?:fut|barrique|barrel|cask)s?\s+)?(?:neu|new)'),
            # label then value, adjacent: "barriques neuves 73 %", "new oak 80%" (not across ") Blending : 71%")
            re.compile(r'(?:neu(?:f|ve|fs|ves)|new\s+(?:oak|barrels?|casks?|wood))[\s:]{0,4}' + NUM + r'\s*%')],
    'months': [re.compile(r'(?:elevage|eleve|ageing|aging|aged|barrique|barrel|fut|oak|cuve)[^\n]{0,80}?'
                          r'(?<![\d.,])(\d{1,2})\s*(?:mois|months?|maanden)')],
}
# A labelled number outside the field's plausible range is another figure caught by the label.
RANGE = {'alc': (8, 17.5), 'ph': (2.5, 4.5), 'yld': (5, 120), 'oak': (0, 100), 'months': (1, 48)}
PLAIN = {
    'alc': lambda v: re.compile(r'(?<![\d.,])%s\s*(?:%%|°)' % _alt(v)),
    'ph': lambda v: re.compile(r'(?<![\d.,])%s(?![\d])' % _alt(v)),
    'yld': lambda v: re.compile(r'(?<![\d.,])%s\s*(?:hl|hecto)' % _alt(v)),
    'oak': lambda v: re.compile(r'(?<![\d.,])%s\s*%%' % _alt(v)),
    'months': lambda v: re.compile(r'(?<![\d.,])%s\s*(?:mois|months?)' % _alt(v)),
}


RANGE_BEFORE = re.compile(r'\d\s*(?:-|–|à|a|to|et|and)\s*$')
RANGE_AFTER = re.compile(r'^\s*(?:%|°)?\s*(?:-|–|à|a|to)\s*\d')


def in_range_phrase(t, start, end):
    """'50-80 % neuves', '16 to 18 months', '13 à 13,5 %': a bound of a range, not the figure."""
    return bool(RANGE_BEFORE.search(t[max(0, start - 8):start]) or RANGE_AFTER.match(t[end:end + 10]))


def _alt(v):
    s = '%g' % float(v)
    return '(?:%s)' % '|'.join(re.escape(x) for x in sorted({s, s.replace('.', ',')}))


def _quote(text, start, end):
    return re.sub(r'\s+', ' ', text[max(0, start - 60):min(len(text), end + 40)]).strip()[:200]


def classify(field, model_value, segments):
    """segments: [(locus, original text)]. See the module docstring."""
    if field == 'blend':
        return _classify_blend(model_value, segments)
    if field not in ANCHORED or _f(model_value) is None:
        return {'classification': 'FIELD_NOT_CHECKABLE', 'hits': 0}
    want = _f(model_value)
    hits, plain, ranged = [], [], []
    for locus, text in segments:
        t = fold(text)
        for rx in ANCHORED[field]:
            for m in rx.finditer(t):
                v = _f(m.group(1))
                if v is None or not RANGE[field][0] <= v <= RANGE[field][1]:
                    continue
                if in_range_phrase(t, m.start(1), m.end(1)):
                    ranged.append((locus, _quote(text, m.start(), m.end())))
                    continue
                hits.append((v, locus, _quote(text, m.start(), m.end())))
        if PLAIN[field](want).search(t):
            m = PLAIN[field](want).search(t)
            plain.append((locus, _quote(text, m.start(), m.end())))
    same = [h for h in hits if abs(h[0] - want) < 1e-9]
    other = sorted({h[0] for h in hits if abs(h[0] - want) >= 1e-9})
    out = {'hits': len(hits)}
    if same and other:
        out.update(classification='DUPLICATE_VALUE', found=[want] + other, locus=same[0][1], quote=same[0][2])
    elif same:
        out.update(classification='MODEL_MATCHES', found=[want], locus=same[0][1], quote=same[0][2])
    elif other:
        out.update(classification='MODEL_CONFLICT', found=other, locus=hits[0][1], quote=hits[0][2])
    elif ranged:
        out.update(classification='AMBIGUOUS', locus=ranged[0][0], quote=ranged[0][1], range=True)
    elif plain:
        out.update(classification='AMBIGUOUS', locus=plain[0][0], quote=plain[0][1])
    else:
        out['classification'] = 'NOT_FOUND'
    return out


BLEND_LABEL = re.compile(r'assemblage|blend|coupage')
PLANTING_LABEL = re.compile(r'encepagement|grape variet|cepages?\s*(?:plantes|:)|soil|sol\s*:|superficie|vineyard|vignoble|planted|plantation')
RUN = 200


def _planting_heads(t, start):
    """True when the nearest heading before the shares (within 120 characters) is a planting or soil
    heading rather than a blend one ("Superficie 7 ha Assemblage 70 % Merlot" is a blend)."""
    window = t[max(0, start - 120):start]
    last_plant = max((m.end() for m in PLANTING_LABEL.finditer(window)), default=-1)
    last_blend = max((m.end() for m in BLEND_LABEL.finditer(window)), default=-1)
    return last_plant > last_blend


def _classify_blend(value, segments):
    """Every share of the model's blend must stand beside its own grape, all in one contiguous run
    (one table or sentence), in a passage that names the blend - and not straight after a planting or
    soil heading: an estate's planting mix is not a vintage's assemblage (D1 stays open)."""
    if not isinstance(value, dict) or not value or any(k not in GRAPES for k in value):
        return {'classification': 'FIELD_NOT_CHECKABLE', 'hits': 0}
    codes = sorted(value)
    pair = {c: re.compile(r'(?:(?<![\d.,])%s\s*%%[^%%\d]{0,20}?(?:%s))|(?:(?:%s)[^%%\d]{0,20}?(?<![\d.,])%s\s*%%)' % (
        _alt(value[c]), GRAPES[c], GRAPES[c], _alt(value[c]))) for c in codes}
    unlabelled = None
    for locus, text in segments:
        t = fold(text)
        for m0 in pair[codes[0]].finditer(t):
            lo, hi = max(0, m0.start() - RUN), m0.end() + RUN
            ms = [m0] + [pair[c].search(t, lo, hi) for c in codes[1:]]
            if not all(ms):
                continue
            start, end = min(m.start() for m in ms), max(m.end() for m in ms)
            if end - start > RUN:
                continue
            if BLEND_LABEL.search(t) and not _planting_heads(t, start):
                return {'classification': 'MODEL_MATCHES', 'hits': len(value), 'found': [value], 'locus': locus,
                        'quote': _quote(text, start, end)}
            unlabelled = unlabelled or (locus, _quote(text, start, end))
    if unlabelled:
        return {'classification': 'AMBIGUOUS', 'hits': 0, 'locus': unlabelled[0], 'quote': unlabelled[1],
                'reason': 'the shares stand together, but not in a passage that names the blend, or straight after a planting/soil heading'}
    # some passage names every grape with some share, but not these shares: a conflict to review
    for locus, text in segments:
        t = fold(text)
        if all(re.search(r'(?:%s)[^%%\d]{0,20}?\d{1,3}(?:[.,]\d)?\s*%%|\d{1,3}(?:[.,]\d)?\s*%%[^%%\d]{0,20}?(?:%s)' % (GRAPES[c], GRAPES[c]), t)
               for c in value):
            return {'classification': 'MODEL_CONFLICT', 'hits': 0, 'locus': locus, 'quote': _quote(text, 0, 120)}
    return {'classification': 'NOT_FOUND', 'hits': 0}
