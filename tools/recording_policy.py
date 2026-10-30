"""The recording policy for an R4 (listing) identity and a C6 (layout) yield, as executable rules: what each must carry
before anything may record it. docs/DECISION-RECORDING-POLICY.md is the contract; nothing in production calls this
module, and nothing here writes - each function returns the record the policy would allow, or why it refuses.

  listing_identity  an identity from the reviewed listing: the document's held URLs, matched by (host, file name) - a
                    locator only - to the links of the listing pages, and every linking entry APPROVED_R4 in the
                    independent review (data/audit/r4-listing-review.jsonl). LISTING_IDENTITY, never TEXT_IDENTITY.
  c6_observation    a C6 read as the observation it would be: the number and the field the sheet states, the unit
                    hl/ha marked as derived from the layout, the two printed lines kept as raw_value.
"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import identity_rules_candidate as I  # noqa: E402
import migration_lib as L  # noqa: E402

VERSION = 'recording-policy/1'
REVIEW = 'data/audit/r4-listing-review.jsonl'
TEXT_IDENTITY, LISTING_IDENTITY = 'TEXT_IDENTITY', 'LISTING_IDENTITY'
ATTRIBUTION_METHOD = {TEXT_IDENTITY: 'DOCUMENT_TEXT', LISTING_IDENTITY: 'REVIEWED_LISTING'}
C6_CONFIDENCE = 'UNIT_FROM_LAYOUT'
C6_DERIVATION = 'UNIT_FROM_LAYOUT'


def reviewed_entries(path=None):
    """(host, path prefix) -> the review's entry row."""
    return {(r['host'], r['path_prefix']): r for r in L.jsonl_lines(path or L.ROOT + REVIEW) if r.get('record') == 'entry'}


def entry_of(url, entries):
    h, p = I.nurl(url)
    hits = [k for k in entries if k[0] == h and p.startswith(k[1])]
    return max(hits, key=lambda k: len(k[1])) if hits else None


def refuse(code, why, **kw):
    return dict({'status': 'REFUSED', 'code': code, 'reason': why, 'version': VERSION}, **kw)


def listing_identity(target_wine, doc_urls, linked, entries, artifact=None, sha256=None):
    """The listing's identity for a document, or why there is none. `linked` is R4's own map, (host, file name) ->
    {wine: {listing page URLs}}; `entries` the review rows. The document's text is not read: a listing may establish
    a wine the text does not name, and a filename is never evidence of whose wine it is."""
    keys = sorted({I.fkey(u) for u in doc_urls})
    wines = collections.defaultdict(set)
    for k in keys:
        for w, pages in linked.get(k, {}).items():
            wines[w] |= set(pages)
    if not wines:
        return refuse('NO_REVIEWED_LISTING', 'no reviewed listing page links the document (a filename alone, whatever '
                      'it says, establishes nothing)')
    if len(wines) > 1:
        return refuse('SHARED_LISTING', 'the document is listed from the pages of %d wines: it establishes nothing '
                      'about any of them' % len(wines), wines=sorted(wines))
    (w, pages), = wines.items()
    ents = sorted({entry_of(p, entries) for p in pages}, key=lambda e: (e is None, e))
    not_ok = [e for e in ents if e is None or entries[e]['disposition'] != 'APPROVED_R4']
    if not_ok:
        return refuse('LISTING_ENTRY_NOT_APPROVED', 'a page listing it is not an approved entry of the independent review '
                      '(%s)' % ', '.join('%s%s: %s' % (e[0], e[1], entries[e]['disposition']) if e else 'no entry'
                                         for e in not_ok))
    if w != target_wine:
        return refuse('LISTED_UNDER_OTHER_WINE', 'the reviewed listing files it under %s: evidence against %s' % (
            w, target_wine), listed_wine=w)
    e0 = entries[ents[0]]
    return {'status': LISTING_IDENTITY, 'wine': w, 'estate': e0['estate'],
            'attribution_method': ATTRIBUTION_METHOD[LISTING_IDENTITY],
            'provenance': {
                'identity_basis': LISTING_IDENTITY, 'rule': 'R4', 'rules_version': I.VERSION,
                'site': e0['host'], 'artifact': artifact, 'sha256': sha256,
                'listing': [{'entry': entries[e]['entry'], 'pages': sorted(p for p in pages if entry_of(p, entries) == e),
                             'review': {'audit': REVIEW, 'entry': entries[e]['entry'],
                                        'disposition': entries[e]['disposition'], 'version': entries[e]['version']}}
                            for e in ents],
                'relationship': 'THE_LISTING_PAGE_LINKS_THE_DOCUMENT',
                'locator': [list(k) for k in keys],
                'locator_role': 'the (host, file name) matches a page\'s link to a held document; it is never evidence '
                                'of whose wine the document is',
                'filename_used_as_identity_evidence': False},
            'version': VERSION}


def c6_observation(c6, identity_status, reader_yld, subject, artifact, lang=None):
    """The observation a C6 read would record, or why none. Identity is the caller's and must be settled; a value the
    reader read is the reader's own path (C6 never ran, and a source that prints "37 hl/ha" is literal evidence)."""
    if identity_status != 'IDENTITY_SETTLED':
        return refuse('IDENTITY_NOT_SETTLED', 'C6 establishes no wine or vintage; nothing is recorded')
    if reader_yld is not None:
        return refuse('READER_PATH', 'the reader read the yield (%s): its literal value is recorded by the ordinary '
                      'path, and C6 does not run' % reader_yld)
    if (c6 or {}).get('status') != 'READ':
        return refuse('C6_NOT_READ', 'C6 %s%s' % ((c6 or {}).get('status'), ' at guard %s' % c6['failed_guard']
                                                if (c6 or {}).get('failed_guard') is not None else ''))
    fr, en = c6['evidence']['lines'][2], c6['evidence']['lines'][3]
    page = c6['evidence']['page']
    return {
        'status': 'RECORDABLE',
        'observation': {'subject': subject, 'field': 'yld', 'value': c6['value'], 'unit': c6['unit'],
                        'raw_value': [fr['text'], en['text']], 'artifact': artifact,
                        'locus': 'p%d: the %s / %s row, value lines at y %.1f and %.1f' % (
                            page + 1, c6['evidence']['label'][0], c6['evidence']['label'][1], fr['y0'], en['y0']),
                        'extraction': {'method': c6['version']}, 'confidence': C6_CONFIDENCE, 'lang': lang},
        'provenance': {'kind': 'DOCUMENT', 'artifact': artifact,
                       'quote': '%s | %s' % (fr['text'], en['text']),
                       'code_state': {'c6': c6['version'], 'unit_basis': c6['unit_basis'], 'field_basis': c6['field_basis'],
                                      'french_line': {k: fr[k] for k in ('text', 'x0', 'y0', 'x1', 'y1')},
                                      'english_line': {k: en[k] for k in ('text', 'x0', 'y0', 'x1', 'y1')},
                                      'labels': c6['evidence']['label'], 'page': page, 'table': c6['evidence']['table'],
                                      'guards': c6['guards'], 'arithmetic': c6['arithmetic'],
                                      'unit_derived': True, 'source_prints_hl_per_ha': False}},
        'canonical': {'field': 'yld', 'value': c6['value'], 'status': 'SOURCED', 'derivation': C6_DERIVATION},
        'version': VERSION}


def value_path(reader_yld, c6):
    """Which evidence path a yield takes: the reader's literal value, the C6 layout, or none."""
    if reader_yld is not None:
        return 'READER'
    if (c6 or {}).get('status') == 'READ':
        return 'C6_LAYOUT'
    return None
