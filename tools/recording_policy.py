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


# The user's sign-off of the independent review's APPROVED_R4 entries (2026-11-18). An entry approved later, or the
# review at another version, is not signed off until it is added here.
SIGNOFF = {'by': 'user', 'date': '2026-11-18', 'review_version': 'r4-listing-review/1',
           'entries': frozenset({
               'desmirail.com/nos-vins/chateau-desmirail/', 'desmirail.com/en/our-wines/chateau-desmirail/',
               'desmirail.com/nos-vins/initial-de-desmirail/', 'desmirail.com/en/our-wines/initial-de-desmirail/',
               'desmirail.com/nos-vins/iris-pourpre-de-desmirail/', 'desmirail.com/en/our-wines/iris-pourpre-de-desmirail/',
               'desmirail.com/nos-vins/la-perle-de-desmirail/', 'desmirail.com/en/our-wines/la-perle-de-desmirail/',
               'desmirail.com/nos-vins/rose-de-desmirail/', 'desmirail.com/en/our-wines/rose-de-desmirail/',
               'chateau-issan.com/fr/vin_moulin_d_issan.html', 'chateau-issan.com/en/vin_moulin_d_issan.html',
               'chateau-issan.com/zh/vin_moulin_d_issan.html'})}
LISTING_RULE = 'R4'


def check_listing_review(c, sha, estate, wine, entries=None):
    """The listing branch of the acceptance path (apply-vintage-creation-manifest.check_review): None when the
    reviewed claim `c` may be recorded as a REVIEWED_LISTING identity of exactly this estate and wine for these
    bytes, else why not. Only the identity is checked here; the caller checks the vintage, which must be the text's.

    The claim's evidence_of_document is {kind: DOCUMENT, rule: R4, basis, listing, headings}: `listing` is
    listing_identity's record, `headings` the main heading of each linking page, {entry: heading}. Each entry is
    read again from the independent review, as it stands now, and must be APPROVED_R4 at the signed-off version,
    signed off, able to attribute (not VETO_ONLY), of this wine and estate, and hold the pages and heading recorded."""
    doc = c.get('evidence_of_document') or {}
    if (doc.get('kind'), doc.get('rule')) != ('DOCUMENT', LISTING_RULE):
        return 'the listing branch needs a DOCUMENT claim by rule %s (%s, %s)' % (LISTING_RULE, doc.get('kind'), doc.get('rule'))
    li = doc.get('listing') or {}
    if (li.get('status'), li.get('wine'), li.get('estate')) != (LISTING_IDENTITY, wine, estate):
        return 'the listing identity is %s for %s of %s' % (li.get('status'), li.get('wine'), li.get('estate'))
    if li.get('attribution_method') != ATTRIBUTION_METHOD[LISTING_IDENTITY]:
        return 'the listing identity is not recorded as %s' % ATTRIBUTION_METHOD[LISTING_IDENTITY]
    pv = li.get('provenance') or {}
    if (pv.get('identity_basis'), pv.get('rule'), pv.get('relationship')) != (
            LISTING_IDENTITY, LISTING_RULE, 'THE_LISTING_PAGE_LINKS_THE_DOCUMENT'):
        return 'the listing provenance is not a reviewed listing relationship'
    if pv.get('filename_used_as_identity_evidence') is not False:
        return 'the filename was used as identity evidence'
    if pv.get('sha256') != sha:
        return 'the listing identity is for other bytes'
    listing = pv.get('listing') or []
    if not listing:
        return 'no listing entry links the document'
    entries = reviewed_entries() if entries is None else entries
    by_id = {r['entry']: (k, r) for k, r in entries.items()}
    heads = doc.get('headings') or {}
    if set(heads) != {x.get('entry') for x in listing}:
        return 'the headings do not match the linking entries'
    for x in listing:
        eid = x.get('entry')
        if eid not in by_id:
            return 'entry %s is not in the independent review' % eid
        k, r = by_id[eid]
        if r['disposition'] != 'APPROVED_R4' or r['version'] != SIGNOFF['review_version']:
            return 'entry %s is %s at %s, not APPROVED_R4 at %s' % (eid, r['disposition'], r['version'],
                                                                   SIGNOFF['review_version'])
        if eid not in SIGNOFF['entries']:
            return 'entry %s is approved but not signed off' % eid
        if r.get('effect') != 'ATTRIBUTE_AND_VETO':
            return 'entry %s can only veto (%s)' % (eid, r.get('effect'))
        if (r['wine'], r['estate']) != (wine, estate):
            return 'entry %s is the page of %s of %s' % (eid, r['wine'], r['estate'])
        if (x.get('review') or {}).get('disposition') != 'APPROVED_R4':
            return 'the recorded review of entry %s is not APPROVED_R4' % eid
        if not x.get('pages') or any(entry_of(p, entries) != k for p in x['pages']):
            return 'a page recorded for entry %s is not under it' % eid
        held = {p['heading'] for p in r.get('pages') or [] if p.get('names_the_wine')}
        if heads[eid] not in held:
            return 'the heading recorded for entry %s is not the review\'s' % eid
    return None


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
