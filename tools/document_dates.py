"""Historical model M2: a document's own date, as its text states it. Pure rules, no I/O.

A document date is when the document itself is dated: published, issued,
posted, updated, revised. It is not when anything it describes happened, not
the vintage it describes, not when it was fetched, and not a year in its
file name or address. Only a date the text *labels* as the document's own is
accepted; everything else is a reason, recorded, why there is none.

    decide(segments, clues) -> {category, value?, precision?, label?, quote?, locus?,
                                candidates?, flags}

segments: [(locus, text)] in document order (title, headings, blocks, pages,
lines). clues: what else is known about the document (file names, addresses,
retrieval timestamps, embedded metadata), used only to name the reason a date
was not accepted - never to supply one.
"""
import re

VERSION = 'document-dates/1'

ACCEPTED = 'ACCEPTED_DOCUMENT_DATE'
CATEGORIES = [ACCEPTED, 'AMBIGUOUS', 'REJECTED_EXTERNAL_REFERENCE', 'REJECTED_ELSEWHERE_ON_PAGE',
              'REJECTED_IMPLAUSIBLE',
              'REJECTED_FILENAME_ONLY', 'REJECTED_URL_ONLY', 'REJECTED_VINTAGE_ONLY',
              'REJECTED_METADATA_ONLY', 'REJECTED_RETRIEVAL_DATE', 'NO_DOCUMENT_DATE', 'NO_TEXT_HELD']

MONTHS = {
    'janvier': 1, 'février': 2, 'fevrier': 2, 'mars': 3, 'avril': 4, 'mai': 5, 'juin': 6, 'juillet': 7,
    'août': 8, 'aout': 8, 'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12, 'decembre': 12,
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6, 'july': 7, 'august': 8,
    'september': 9, 'october': 10, 'november': 11, 'december': 12,
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'sept': 9,
    'oct': 10, 'nov': 11, 'dec': 12,
    'janv': 1, 'févr': 2, 'fevr': 2, 'avr': 4, 'juil': 7, 'déc': 12,
}
MON = '|'.join(sorted(MONTHS, key=len, reverse=True))

# Labels that say "this document's date". French labels fix day-first numeric dates.
LABEL_FR_PUB = r'date\s+de\s+publication|publi[ée]e?s?\s+le|parue?s?\s+le|mise?\s+en\s+ligne\s+le|[ée]dit[ée]e?s?\s+le'
LABEL_FR_UPD = (r'derni[èe]re\s+mise\s+[àa]\s+jour|mise?\s+[àa]\s+jour\s+le|mise\s+[àa]\s+jour|'
                r'r[ée]vis[ée]e?s?\s+le|modifi[ée]e?s?\s+le')
LABEL_EN_PUB = r'publication\s+date|date\s+of\s+publication|published(?:\s+on)?|issue\s+date|issued(?:\s+on)?|posted(?:\s+on)?'
LABEL_EN_UPD = r'last\s+updated(?:\s+on)?|updated(?:\s+on)?|last\s+modified(?:\s+on)?|revised(?:\s+on)?|revision\s+date'
LABELS = [('PUBLISHED', 'fr', LABEL_FR_PUB), ('UPDATED', 'fr', LABEL_FR_UPD),
          ('PUBLISHED', 'en', LABEL_EN_PUB), ('UPDATED', 'en', LABEL_EN_UPD)]

YEAR = r'(?:19|20)\d\d'
DATE_FORMS = [
    # (form, regex) longest first; each has named groups d, m (number) or mn (name), y
    ('DMY_NAME', r'(?P<d>[0-3]?\d)(?:er|st|nd|rd|th)?\s+(?P<mn>%s)\.?\s+(?P<y>%s)' % (MON, YEAR)),
    ('MDY_NAME', r'(?P<mn>%s)\.?\s+(?P<d>[0-3]?\d)(?:st|nd|rd|th)?,?\s+(?P<y>%s)' % (MON, YEAR)),
    ('ISO', r'(?P<y>%s)-(?P<m>[01]\d)-(?P<d>[0-3]\d)' % YEAR),
    ('NUMERIC', r'(?P<a>[0-3]?\d)[/.](?P<b>[01]?\d)[/.](?P<y>%s)' % YEAR),
    ('MY_NAME', r'(?P<mn>%s)\.?\s+(?P<y>%s)' % (MON, YEAR)),
    ('MY_NUMERIC', r'(?P<m>[01]?\d)[/.](?P<y>%s)' % YEAR),
    ('Y', r'(?P<y>%s)' % YEAR),
]
SEP = r'\s*(?:[:\-–—]\s*)?(?:(?:le|on|the)\s+)?'
NOT_AFTER = r'(?![\d/.-])(?!\s*(?:vintage|mill[ée]sime|harvest|r[ée]colte|vendange))'
EXTERNAL = r'\s+(?:in|dans|by|par)\s+[A-ZÉ][^\n]{0,60}?\b(?:on|le)\s+'

LABEL_DATE = []
for cls, lang, lab in LABELS:
    for form, rx in DATE_FORMS:
        LABEL_DATE.append((cls, lang, form, re.compile(r'(?<![\w])(?:%s)%s(%s)%s' % (lab, SEP, rx, NOT_AFTER),
                                                       re.IGNORECASE)))
# Every LABEL_DATE pattern starts with one of these labels after a non-word character, so text in
# which this finds nothing holds no labelled date; it only spares running the 28 patterns over it.
ANY_LABEL = re.compile(r'(?<![\w])(?:%s)' % '|'.join(lab for _, _, lab in LABELS), re.IGNORECASE)
LABEL_EXTERNAL = re.compile(r'(?<![\w])(?:%s|%s)%s(?:%s)' % (
    LABEL_EN_PUB, LABEL_FR_PUB, EXTERNAL,
    '|'.join(re.sub(r'\?P<\w+>', '', r) for _, r in DATE_FORMS[:5])), re.IGNORECASE)
VINTAGE = re.compile(r'(?:mill[ée]sime|vintage|harvest|r[ée]colte|vendanges?)\s*:?\s*%s|%s\s+(?:vintage|mill[ée]sime)'
                     % (YEAR, YEAR), re.IGNORECASE)
ANY_YEAR = re.compile(r'(?<!\d)%s(?!\d)' % YEAR)


def _normalise(form, gd, lang):
    """(value, precision) or ('AMBIGUOUS', reason) or None for an impossible date."""
    y = int(gd['y'])
    if form in ('DMY_NAME', 'MDY_NAME'):
        m, d = MONTHS[gd['mn'].lower()], int(gd['d'])
    elif form == 'ISO':
        m, d = int(gd['m']), int(gd['d'])
    elif form == 'NUMERIC':
        a, b = int(gd['a']), int(gd['b'])
        if lang == 'fr':
            d, m = a, b                                    # a French label: day first
        elif a > 12 >= b:
            d, m = a, b
        elif b > 12 >= a:
            d, m = b, a
        elif a == b:
            d, m = a, b
        else:
            return ('AMBIGUOUS', 'day and month order not fixed by the label: %d/%d/%d' % (a, b, y))
    elif form == 'MY_NAME':
        return ('%04d-%02d' % (y, MONTHS[gd['mn'].lower()]), 'MONTH')
    elif form == 'MY_NUMERIC':
        m = int(gd['m'])
        return ('%04d-%02d' % (y, m), 'MONTH') if 1 <= m <= 12 else None
    else:
        return ('%04d' % y, 'YEAR')
    if not (1 <= m <= 12 and 1 <= d <= 31):
        return None
    return ('%04d-%02d-%02d' % (y, m, d), 'DAY')


def _quote(text, start, end):
    s, e = max(0, start - 30), min(len(text), end + 30)
    return re.sub(r'\s+', ' ', text[s:e]).strip()[:140]


APPOSITIVE = re.compile(r',\s*$')                  # "..., published on": about the thing just named
# "the ranking is published on": the label is the predicate of a sentence about its subject
PREDICATE = re.compile(r'(?<![\w])(?:est|sont|a\s+[ée]t[ée]|ont\s+[ée]t[ée]|fut|furent|sera|seront|'
                       r'is|are|was|were|has\s+been|have\s+been|will\s+be)\s+$', re.IGNORECASE)
OTHER_DOCUMENT = re.compile(r'cookie|privacy|confidentialit|\bpolicy\b|\bpolitique\b|\bterms\b|'
                            r'conditions\s+g[ée]n[ée]rales|mentions\s+l[ée]gales|\bCGU\b|\bCGV\b', re.IGNORECASE)
BARE_DATE = re.compile(r'^\s*(?:%s)\s*$' % '|'.join(re.sub(r'\?P<\w+>', '', r) for _, r in DATE_FORMS[:4]),
                       re.IGNORECASE)
PRESS_SCORE = re.compile(r'^\s*[-–:]?\s*(?:(?:[89]\d|100)(?!\d)|\d{1,3}\s*(?:/\s*(?:100|20)|pts|points))', re.IGNORECASE)


def labelled_dates(segments):
    """Every labelled document-date mention: [{label, lang, value|ambiguous, precision, quote, locus,
    external?}]. A mention is external when it dates something else the text names: introduced
    after a comma, the predicate of a sentence about its own subject, in a sentence about another
    document (a privacy or cookie policy, terms), or followed by a critic's score."""
    found = []
    if not ANY_LABEL.search('\n'.join(t for _, t in segments)):
        return found
    for locus, text in segments:
        if not ANY_LABEL.search(text):
            continue
        taken = []
        for cls, lang, form, rx in LABEL_DATE:
            for m in rx.finditer(text):
                if any(m.start() < e and s < m.end() for s, e in taken):
                    continue                               # a longer form already read this mention
                taken.append((m.start(), m.end()))
                n = _normalise(form, m.groupdict(), lang)
                if n is None:
                    continue
                row = {'label': cls, 'lang': lang, 'quote': _quote(text, m.start(), m.end()), 'locus': locus}
                if (APPOSITIVE.search(text[:m.start()]) or PREDICATE.search(text[:m.start()])
                        or PRESS_SCORE.match(text[m.end():])
                        or OTHER_DOCUMENT.search(text)):
                    row['external'] = True
                if n[0] == 'AMBIGUOUS':
                    row['ambiguous'] = n[1]
                else:
                    row['value'], row['precision'] = n
                found.append(row)
    return found


def decide(segments, clues, latest='2026-12-31', earliest='1900', anchored=None):
    """The document-date decision for one document. clues: {'filename_year', 'url_year',
    'metadata_date', 'retrieved'} booleans/values, used only to name a reason.

    anchored: the loci where the document dates itself - by its main heading, at its top, on a
    PDF's first page. A labelled date elsewhere (a teaser, a footer, a cookie banner, a press
    quote) belongs to something else on the page and is not this document's date."""
    if segments is None:
        return {'category': 'NO_TEXT_HELD', 'flags': sorted(k for k, v in clues.items() if v)}
    flags = set(k for k, v in clues.items() if v)
    text_all = '\n'.join(t for _, t in segments)
    if VINTAGE.search(text_all):
        flags.add('vintage_year')
    if ANY_YEAR.search(text_all):
        flags.add('year_in_text')
    every = labelled_dates(segments)
    if any(LABEL_EXTERNAL.search(t) for _, t in segments) or any(x.get('external') for x in every):
        flags.add('external_reference')
    if any(anchored is not None and x['locus'] not in anchored for x in every):
        flags.add('labelled_date_elsewhere')
    mentions = [x for x in every if not x.get('external') and (anchored is None or x['locus'] in anchored)]
    plausible, implausible = [], []
    for x in mentions:
        if 'value' in x:
            (plausible if earliest <= x['value'] <= latest else implausible).append(x)
    ambiguous = [x for x in mentions if 'ambiguous' in x]
    out = {'flags': sorted(flags)}
    values = sorted({(x['value'], x['precision']) for x in plausible})
    if ambiguous or len(values) > 1:
        out['category'] = 'AMBIGUOUS'
        out['candidates'] = [{k: x[k] for k in ('label', 'value', 'ambiguous', 'locus', 'quote') if k in x}
                             for x in (plausible + ambiguous)][:6]
        return out
    if len(values) == 1:
        first = [x for x in plausible if (x['value'], x['precision']) == values[0]][0]
        bare = [(l, t) for l, t in segments if BARE_DATE.match(t) and (anchored is None or l in anchored)]
        if first['label'] == 'UPDATED' and bare:
            # an unlabelled date beside a labelled update: the page has a first date and a revision,
            # and only one of them says which it is
            out['category'] = 'AMBIGUOUS'
            out['candidates'] = [{k: first[k] for k in ('label', 'value', 'locus', 'quote')}] + [
                {'label': 'UNLABELLED', 'locus': l, 'quote': t.strip()[:60]} for l, t in bare[:3]]
            return out
        out.update(category=ACCEPTED, value=first['value'], precision=first['precision'],
                   label=first['label'], quote=first['quote'], locus=first['locus'],
                   mentions=sum(1 for x in plausible))
        return out
    if implausible:
        out['category'] = 'REJECTED_IMPLAUSIBLE'
        out['candidates'] = [{k: x[k] for k in ('label', 'value', 'locus') if k in x} for x in implausible][:3]
        return out
    for cat, flag in (('REJECTED_EXTERNAL_REFERENCE', 'external_reference'),
                      ('REJECTED_ELSEWHERE_ON_PAGE', 'labelled_date_elsewhere'),
                      ('REJECTED_FILENAME_ONLY', 'filename_year'), ('REJECTED_URL_ONLY', 'url_year'),
                      ('REJECTED_VINTAGE_ONLY', 'vintage_year'), ('REJECTED_METADATA_ONLY', 'metadata_date'),
                      ('REJECTED_RETRIEVAL_DATE', 'retrieved')):
        if flag in flags:
            out['category'] = cat
            return out
    out['category'] = 'NO_DOCUMENT_DATE'
    return out
