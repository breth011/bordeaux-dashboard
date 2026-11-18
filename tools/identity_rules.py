"""The adopted identity rules beside M3.4A's decide: blocker 1 of the controlled integration. Nothing in production
calls this module.

    res = identify(m34a_module, args)      # args: decide's own eleven arguments, as its caller would pass them

The adoption is docs/DECISION-CANDIDATE-IDENTITY-RULES.md (5589f7c) and docs/DECISION-RECORDING-POLICY.md (6e86290).
M3.4A's decide (tools/m34a-mapping-audit.py, fingerprinted) is never replaced or patched: identify calls the module's
own decide as it is, first on the document's text and then on the text the rules produce, handed to it through the
module's document_text - the seam M3.9's text_hook already uses - which is restored before identify returns.

What differs from tools/identity_rules_candidate.py, the dry run's rules (left unchanged, so the committed dry run
still reproduces):

  R2      NAMED_BLOCK only: two to four short lines that together read the wine's name, an optional classification
          and the year. A single line (NAMED) can be a table cell and a bare "millesime YYYY" (BARE) names no wine:
          neither is adopted. A heading of the same wine with another year, in any form, still makes R2 do nothing.
  R4      only through recording_policy.listing_identity: every reviewed page linking the document must be an
          APPROVED_R4 entry of the independent review (data/audit/r4-listing-review.jsonl). A page under an entry
          that REQUIRES_REVIEW or was rejected establishes nothing and vetoes nothing; the filename never counts.
  CLAIMS  the reasoned claim list replaces REVIEW_HOLD: two HOLD_FOR_MORE_EVIDENCE and three REFUSE, each with the
          decision's reason. A claim on the list is never SAFE_TO_MAP, whoever settled it.

R1, R1b, R3 and G1 are the candidate module's own functions and patterns, unchanged, in the same order.

The R4 entries are approved by the agent's independent review, and the user signed the 13 APPROVED_R4 entries off on
2026-11-18; every R4 step carries entry_signoff = USER_SIGNED_OFF_2026-11-18 so that whatever records it can tell.
An entry approved later needs its own sign-off before it runs here.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_gap_analysis as A  # noqa: E402
import identity_rules_candidate as I  # noqa: E402
import recording_policy as P  # noqa: E402

VERSION = 'identity-rules/1'
RULES = ('R1', 'R1b', 'R2', 'R3', 'R4')
SAFE = 'SAFE_TO_MAP'
HOLD, REFUSE = 'HOLD_FOR_MORE_EVIDENCE', 'REFUSE'
HELD, REFUSED = 'REVIEW_REQUIRED', 'CLAIM_REFUSED'       # the dispositions identify gives a listed claim
ENTRY_SIGNOFF = 'USER_SIGNED_OFF_2026-11-18'

# (sha256 prefix, wine, vintage) -> (decision, reason): DECISION-CANDIDATE-IDENTITY-RULES.md section 3
CLAIM_DECISIONS = {
    ('ff3f74b8517dd5cc', 'wn_00167', 2022): (
        HOLD, 'Paloumey 2022: "chateau paloumey 2022" is a single line in the sheet\'s label and value column, which '
              'the adopted R2 does not read; no adopted rule establishes the identity, and the yield is labelled '
              '"rendement (hl/ha)" with no figure'),
    ('1c74d87a4ddcd665', 'wn_00534', 1998): (
        HOLD, 'Chapelle 1998: the text never names the wine (only the listing and the filename do), and the year is a '
              'bare "millesime 1998" on the last line; it needs text evidence of the wine'),
    ('a9dd99ecfc891e24', 'wn_00215', 2023): (
        REFUSE, 'Brane-Cantenac 2023 (Critics-Review_Primeurs-2023): a critics\' score sheet whose second score block '
                'names no wine; the identity covers part of the document, which states no technical datum'),
    ('6ee0816c58139392', 'wn_00215', 2023): (
        REFUSE, 'Brane-Cantenac 2023 (Revue-Critiques_Primeurs-2023): the French edition, with the same unnamed second '
                'score block in its own text, and no technical datum'),
    ('f59854e5d18e7e5a', 'wn_00386', 2003): (
        REFUSE, 'Corbin 2003: the estate\'s press compilation, not a vintage document; the reader\'s PRESS_DOCUMENT '
                'veto stands'),
}

_ENTRIES = []


def entries():
    """The independent review's entry rows, (host, path prefix) -> row, read once."""
    if not _ENTRIES:
        _ENTRIES.append(P.reviewed_entries())
    return _ENTRIES[0]


def doc_key(a):
    """The document's sha256 as far as the caller holds it: whole for an artifact, 12 characters for an m3.8 id."""
    aid = (a or {}).get('id') or ''
    return (a or {}).get('sha256') or (aid[5:] if aid.startswith('m3.8:') else '')


def claim_decision(key, w, y):
    """(decision, reason, list key) for a listed claim, else None. A 12-character key matches on 12 characters."""
    if not key:
        return None
    for (pre, cw, cy), (d, why) in sorted(CLAIM_DECISIONS.items()):
        if cw == w and cy == y and (key.startswith(pre) if len(key) >= len(pre) else pre.startswith(key) and len(key) >= 12):
            return d, why, pre
    return None


def r2_block(text, wname, y, opening):
    """R2 narrowed to the title block: (text, trace, note)."""
    if re.search(r'(?<!\d)%d(?!\d)' % y, text[:opening]):
        return text, [], None
    hs = I.headings(text, wname, False)
    others = sorted({h[0] for h in hs if h[0] != y})
    mine = [h for h in hs if h[0] == y and h[1] == 'NAMED_BLOCK']
    if not mine:
        single = any(h[0] == y for h in hs)
        return text, [], 'no title block of %s %d%s' % (wname, y, ' (a single-line heading is not adopted)' if single else '')
    if others:
        return text, [], 'competing headings of %s' % others
    h = mine[0]
    return h[2] + '\n' + text, [('R2', h[1], h[2], 'line %d of %d' % (h[3], text.count('\n') + 1))], None


def listing(a, w, ents=None):
    """recording_policy's listing identity of the document for wine w, over R4's own link map."""
    s = I.series()
    return P.listing_identity(w, s.urls(a), s.linked, entries() if ents is None else ents,
                              artifact=(a or {}).get('id'), sha256=(a or {}).get('sha256'))


def identify(mod, args, ents=None):
    """decide's answer with the adopted rules, as a record:

        result      decide's 4-tuple as the rules leave it (a listed claim: REVIEW_REQUIRED or CLAIM_REFUSED)
        base        decide's own 4-tuple on the document's text
        settled_by  PRODUCTION | ADOPTED_RULES | None
        trace       every rule step, in order; notes: why a rule did nothing
        listing     recording_policy.listing_identity's record (R4's evidence), or None where no text was read
        claim       the claim list's (decision, reason, key) where the claim is listed
    """
    row, a, claims, e, w, y, nm, ew, wines, blocked, vdocs = args
    decide = mod.decide
    base = decide(*args)
    rec = {'version': VERSION, 'base': base, 'result': base, 'trace': [], 'notes': [], 'listing': None,
           'claim': claim_decision(doc_key(a), w, y), 'settled_by': None}
    if not a or not a.get('bytes_available') or not a.get('id'):
        return finish(rec)
    text, how = mod.document_text(a['id'])
    if not text:
        return finish(rec)
    ename, wname = nm.get(e, ''), nm.get(w, '')
    siblings = [s for s in ew.get(e, []) if s != w]
    t, trace, notes = text, rec['trace'], rec['notes']

    def run(tx):
        old = mod.document_text
        mod.document_text = lambda aid: (tx, how)
        try:
            return decide(*args)
        finally:
            mod.document_text = old

    t, tr = I.r3(t, y)
    trace += tr
    t, tr = I.r1(t, [ename] + [nm.get(s, '') for s in ew.get(e, [])])
    trace += tr
    t, tr, why = r2_block(t, wname, y, mod.OPENING)
    trace += tr
    if why:
        notes.append('R2: ' + why)
    result = run(t) if t != text else base
    if result[0] == 'ESTATE_VINTAGE_ONLY' and not siblings:
        notes.append('R1b: the model lists one wine for the estate; one wine decides nothing (M3.9)')
    elif result[0] == 'ESTATE_VINTAGE_ONLY' and not mod.distinct_name(wname, ename):
        sw = [x for s in siblings for x in (mod.distinct_name(nm.get(s, ''), ename) or [])]
        t2, tr, why = I.r1b(t, ename, wname, y, sw)
        if tr:
            trace += tr
            result = run(t2)
        elif why:
            notes.append('R1b: ' + why)
    li = rec['listing'] = listing(a, w, ents)
    if li['status'] == P.LISTING_IDENTITY:
        # the wine is not named in the text: by the estate's name only, or not at all (a cuvee's own name)
        unnamed = result[0] == 'ESTATE_VINTAGE_ONLY' or (
            result[0] == 'WINE_AMBIGUOUS' and result[1].startswith('the document does not name the wine'))
        if unnamed:
            m = re.search(r'(?<!\d)%d(?!\d)' % y, t[:mod.OPENING])      # the vintage stays the text's own
            if m:
                t2 = t[:m.start()] + A.fold(wname) + ' ' + t[m.start():]
                trace.append(('R4', 'REVIEWED_LISTING', w, [x['entry'] for x in li['provenance']['listing']],
                              ENTRY_SIGNOFF))
                result = run(t2)
            else:
                notes.append('R4: the listing names the wine, but the year does not stand in the opening')
    elif li.get('code') == 'LISTED_UNDER_OTHER_WINE' and result[0] == SAFE:
        lw = li['listed_wine']
        trace.append(('R4_VETO', 'REVIEWED_LISTING', lw, ENTRY_SIGNOFF))
        result = ('WINE_AMBIGUOUS', 'the site\'s own listing files this document under %s, not %s' % (
            nm.get(lw, lw), wname), None, result[3])
    elif li.get('code') != 'NO_REVIEWED_LISTING':
        notes.append('R4: %s: %s' % (li['code'], li['reason']))
    # G1, unchanged: an acceptance a rule created, resting on the grand vin's name, where the text anywhere speaks of
    # another wine of the estate - not where the site's own listing (R4) says whose document it is
    if (result[0] == SAFE and base[0] != SAFE and (result[3] or {}).get('grand_vin')
            and not any(x[0] == 'R4' for x in trace)):
        sweet = ((wines.get(w) or {}).get('type') == 'WHITE_SWEET')
        m = re.compile(mod.OTHER_WINE.pattern + I.G1_EXTRA + (I.G1_SWEET if sweet else '')).search(t)
        if m:
            trace.append(('G1', m.group(0)))
            result = ('WINE_AMBIGUOUS', 'G1: the document also speaks of "%s": the grand vin is not established '
                      'by its name alone' % m.group(0), None, result[3])
    rec['result'] = result
    return finish(rec)


def finish(rec):
    result, base, c = rec['result'], rec['base'], rec['claim']
    if c and result[0] == SAFE:
        d, why, pre = c
        rec['trace'].append(('CLAIM_LIST', d, pre))
        result = (HELD if d == HOLD else REFUSED, why, None, result[3])
    if result[0] == SAFE:
        rec['settled_by'] = 'PRODUCTION' if base[0] == SAFE else 'ADOPTED_RULES'
    if rec['trace'] and result[0] != base[0]:
        result = result[:3] + (dict(result[3] or {}, identity_rules=[list(x) for x in rec['trace']],
                                    identity_rules_version=VERSION),)
    rec['result'] = result
    return rec
