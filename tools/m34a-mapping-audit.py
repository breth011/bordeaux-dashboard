"""M3.4A: may an accepted document be linked to its wine and vintage? (audit and dry run only)

    python tools/m34a-mapping-audit.py             write data/audit/m3.4a-mapping-proposals.jsonl
    python tools/m34a-mapping-audit.py --check     recompute and compare, byte for byte
    python tools/m34a-mapping-audit.py --report    write docs/PHASE-M3.4A-MAPPING-AUDIT.md (also --check)

The candidates are M3.3's EXISTING_ACCEPTED_DOCUMENT items, recomputed now: a vintage the model
holds with no document, for which the evidence store ACCEPTED a held document for exactly that
wine and vintage. One candidate per (estate, wine, vintage, artifact).

An accepted decision is not taken as proof of the wine: its target wine came from the legacy
manifest, and its "is_second=False" only says no second-wine name was found. The document itself
must establish the mapping:

  vintage  the document's opening states exactly that year; no decision on the document claims another
  wine     the document names this wine beside the year ("Château Latour 2003"), or says "grand vin"
           for a grand vin, or names a second or other wine by its own distinctive name
  scope    no other wine of the estate is named in it
  colour   where the estate makes red and white, the document leaves no doubt which
  claims   the accepted decisions on the document name one estate and one wine

Nothing here writes to the model or the evidence store; nothing is fetched or OCR'd. A held PDF with
no stored text is read as tools/sheetreader.py reads it.
"""
import collections
import importlib.util
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_gap_analysis as A  # noqa: E402
import migration_lib as L  # noqa: E402

OUT = L.ROOT + 'data/audit/m3.4a-mapping-proposals.jsonl'
REPORT = L.ROOT + 'docs/PHASE-M3.4A-MAPPING-AUDIT.md'

_s = importlib.util.spec_from_file_location('m33', L.ROOT + 'tools/m33-source-plan.py')
P = importlib.util.module_from_spec(_s)
_s.loader.exec_module(P)
_r = importlib.util.spec_from_file_location('m32', L.ROOT + 'tools/m32-recovery.py')
R = importlib.util.module_from_spec(_r)
_r.loader.exec_module(R)

DISPOSITIONS = ['SAFE_TO_MAP', 'ESTATE_VINTAGE_ONLY', 'WINE_AMBIGUOUS', 'COLOUR_AMBIGUOUS', 'MULTI_WINE_AMBIGUOUS',
                'VINTAGE_AMBIGUOUS', 'IDENTITY_BLOCKED', 'CONFLICT', 'EVIDENCE_INSUFFICIENT', 'ALREADY_MAPPED',
                'NOT_FOUND']
OPENING = 600                     # characters of the document's start in which its own vintage must stand
NEAR = 60                         # how close the wine's name and the year must stand
WHITE = re.compile(r'\bblanc\b|\bwhite\b|sauvignon|s[eé]millon|muscadelle|\bweiss|\bwit\b')
RED = re.compile(r'\brouge\b|\bred wine\b|\bvin rouge\b|cabernet|merlot|petit verdot')
# "grand vin" as the wine's role - not "Grand Vin de Bordeaux", the label phrase on nearly every
# sheet, and not "grands vins", the estate's wines in general
# ... and not "grand vin sec" or "grand vin blanc": that names another wine (Doisy-Daëne's dry wine).
# Read only in the document's opening, where it speaks of itself, not in a history paragraph.
GRAND_VIN = re.compile(r'\bgrand vin\b(?!s)(?!\s+d[eu]\s)(?!\s+d.)(?!\s+(?:sec|blanc|rouge|liquoreux|moelleux|dry|white|red)\b)'
                       r'|\bpremier vin\b|\bfirst wine\b|\bthe estate.s flagship\b')
# another wine of the estate spoken of in the opening: a second wine or a named cuvee the model may
# not list (an unlisted cuvee must not pass for the grand vin)
OTHER_WINE = re.compile(r'second vin|second wine|deuxi[eè]me vin|second label|third wine|troisi[eè]me vin'
                        r'|\bcuv[eé]e\s+(?!du\b|de\b)[a-z]{3,}|l.autre vin\b|the other wine\b')
# the grapes of a stated blend: the colour the sheet is for, whatever the estate's prose says
BLEND = re.compile(r'(?:assemblage|blending|blend|c[eé]pages?|encepagement du millesime)\s*:?\s*((?:[^.;:]{0,25}?\d{1,3}\s*%[^.;:\d]{0,25}){1,5})')
RED_GRAPE = re.compile(r'cabernet|merlot|petit verdot|malbec|carmen[eè]re')
WHITE_GRAPE = re.compile(r's[eé]millon|(?<!cabernet )(?<!cabernet-)sauvignon|muscadelle')
# a document that describes the estate's red and white alike: its colour is not its own to tell
BOTH_COLOURS = re.compile(r'vins? blancs? (?:sec )?et (?:un |des )?vins? rouges?|vins? rouges? et (?:un |des )?vins? blancs?'
                          r'|\bred and white wines\b|\bwhite and red wines\b|\b(?:les )?seconds vins \((?:blanc et rouge|rouge et blanc)\)')
# a year that stands in a calendar date ("le 16 mai 2019") is the date of an event, not a vintage
MONTHS = (r'janvier|fevrier|février|mars|avril|mai|juin|juillet|aout|août|septembre|octobre|novembre|decembre|décembre'
          r'|january|february|march|april|may|june|july|august|september|october|november|december')
DATED = r'\b\d{1,2}(?:er)?[\s-]+(?:%s)[\s-]+%d\b'           # in prose or in the page's URL
# vintage headings in the body: three or more other ones make a multi-vintage compilation
VINTAGE_HEAD = re.compile(r'\b(?:mill[eé]sime|vintage)\s*:?\s*((?:19|20)\d\d)\b')


def open_decision_wines(nm):
    """Wines whose identity an open decision governs: no mapping to them may be proposed."""
    out = {}
    for wid, name in nm.items():
        n = A.fold(name)
        if wid.startswith('wn_') and (('echo' in n and 'lynch' in n) or 'haut-bages averous' in n):
            out[wid] = 'D2'
        elif wid.startswith('wn_') and ('haut-bailly ii' in n or 'la parde' in n):
            out[wid] = 'LAPARDE_IDENTITY'
        elif wid.startswith('wn_') and ('lions de batailley' in n or 'hauts de lynch-moussas' in n):
            out[wid] = 'D5_SECOND_WINE_CONFLICT'
        elif wid.startswith('wn_') and 'terrasses de saint christophe' in n:
            out[wid] = 'TERRASSES_IDENTITY'
    return out


def distinct_name(wine_name, estate_name):
    """The part of a wine's name that tells it from its estate ("forts" in "Les Forts de Latour")."""
    w = A.fold(wine_name)
    for t in re.findall(r'[a-z]+', A.fold(estate_name)):
        w = re.sub(r'\b%s\b' % re.escape(t), ' ', w)
    toks = [t for t in re.findall(r'[a-z]{3,}', w) if t not in ('les', 'des', 'del', 'the', 'vin', 'cru')]
    return toks


def document_text(aid):
    t = A.document_text(aid)
    if t:
        return t, 'stored'
    pdf = R.local_pdf(aid)
    if pdf:
        flat, _, how = R.pdf_text(pdf)
        if flat and len(flat.strip()) >= 80:
            return A.fold(flat), how
    return None, None


def accepted_claims():
    """sha256 -> [(estate id, wine id, vintage, decision row key)] of the latest accepted decisions."""
    raw = collections.defaultdict(list)
    links = {}
    for e in A.table('observation/evidence-links.jsonl'):
        if e['evidence_version'] == 5 and e.get('artifact'):
            links.setdefault((e['artifact'], e.get('estate'), e.get('wine')), []).append(e['row_key'])
    for d in A.decisions():
        if d['decision'] == 'ACCEPTED' and d['sha256']:
            raw[d['sha256']].append(d)
    return raw, links


def build():
    nm = P.names()
    st = P.states()
    ev, _ = P.item_evidence(st)
    blocked_wines = open_decision_wines(nm)
    arts = A.by_id('identity/artifacts.jsonl')
    vdocs = json.load(open(L.MODEL + 'derived/vintage-documents.json', encoding='utf-8'))
    raw, links = accepted_claims()
    gaps = {g['gap_key']: g['gap_id'] for g in P.new_data_gaps()}
    wines = A.by_id('identity/wines.jsonl')
    ew = collections.defaultdict(list)
    for r in A.table('state/estate-wine.jsonl'):
        ew[r['estate']].append(r['wine'])
    canon = collections.defaultdict(set)
    for c in A.table('canonical/values.jsonl'):
        canon[c['subject']].add(c['field'])
    rows = []
    for (e, w, y), evs in sorted(ev.items()):
        for x in evs:
            if x['family'] != 'EXISTING_ACCEPTED_DOCUMENT':
                continue
            aid = x['locator']
            a = arts.get(aid) or {}
            vt = 'vt:%s:%d' % (w, y)
            row = {'gap_id': gaps.get('VINTAGE_NO_DOCUMENT|%s' % e), 'estate': e, 'estate_name': nm.get(e, e),
                   'wine': w, 'wine_name': nm.get(w, w), 'vintage': y, 'vintage_id': vt, 'artifact': aid,
                   'sha256': a.get('sha256'), 'media_type': a.get('media_type'),
                   'files': sorted({os.path.basename(p['locator']['value']) for p in A.placements_of(aid)})[:4]}
            claims = raw.get(a.get('sha256'), [])
            row['accepted_claims'] = sorted({(d['estate_slug'] or '', d['wine_name'] or '', int(d['vintage']) if d['vintage'] else 0)
                                             for d in claims})
            row['evidence_refs'] = sorted(set(links.get((aid, e, w), [])))
            disp, reason, basis, facts = decide(row, a, claims, e, w, y, nm, ew, wines, blocked_wines, vdocs)
            row.update(disposition=disp, reason=reason, basis=basis, facts=facts)
            if disp == 'SAFE_TO_MAP':
                role = 'GRAND_VIN' if facts.get('grand_vin') else 'NAMED_WINE'
                row['proposal'] = {'action': 'LINK_ARTIFACT_TO_VINTAGE', 'artifact': aid, 'sha256': a.get('sha256'),
                                   'estate': e, 'wine': w, 'vintage': vt, 'role': role,
                                   'colour': (wines.get(w) or {}).get('type'), 'confidence': 'HIGH',
                                   'evidence_refs': row['evidence_refs'], 'basis': basis}
                held = canon.get(vt, set()) & {'alc', 'blend', 'ph', 'yld', 'oak', 'months'}
                row['extraction_opportunity'] = sorted({'alc', 'blend', 'ph', 'yld', 'oak', 'months'} - held)
            rows.append(row)
    rows.sort(key=lambda r: (r['estate'], r['wine'], r['vintage'], r['artifact']))
    return rows


def decide(row, a, claims, e, w, y, nm, ew, wines, blocked_wines, vdocs):
    """(disposition, reason, basis, facts) for one candidate. The first failing test decides."""
    facts = {}
    if w in blocked_wines:
        return ('IDENTITY_BLOCKED', 'the wine\'s identity waits on %s' % blocked_wines[w], None, facts)
    if a.get('id') and a['id'] in vdocs.get(row['vintage_id'], []):
        return ('ALREADY_MAPPED', 'the model links the document to the vintage now', None, facts)
    if not a or not a.get('bytes_available'):
        return ('NOT_FOUND', 'the document\'s bytes are not held', None, facts)
    # the accepted claims on the document: one estate, one wine, one vintage
    wines_claimed = {(c['estate_slug'], c['wine_name']) for c in claims}
    estates_claimed = {c['estate_slug'] for c in claims}
    years_claimed = {int(c['vintage']) for c in claims if c['vintage']}
    if len(estates_claimed) > 1 or len(wines_claimed) > 1:
        return ('CONFLICT', 'the accepted decisions on this one document name %d estate(s) and %d wine(s): %s' % (
            len(estates_claimed), len(wines_claimed), '; '.join(sorted('%s / %s' % x for x in wines_claimed))[:200]), None, facts)
    if len(years_claimed) > 1:
        return ('VINTAGE_AMBIGUOUS', 'the accepted decisions on this one document claim %d vintages (%s)' % (
            len(years_claimed), ', '.join(str(v) for v in sorted(years_claimed))), None, facts)
    text, how = document_text(a['id'])
    facts['text'] = how
    if not text:
        return ('EVIDENCE_INSUFFICIENT', 'the document holds no readable text (image-only, or a format not read)', None, facts)
    head = text[:OPENING]
    years = sorted({int(v) for v in re.findall(r'(?<!\d)(19[5-9]\d|20[0-2]\d)(?!\d)', head)})
    if y not in years:
        return ('VINTAGE_AMBIGUOUS', 'the document\'s opening does not state %d%s' % (
            y, ' (it states %s)' % ', '.join(map(str, years[:5])) if years else ''), None, facts)
    others_y = [v for v in years if v != y and abs(v - y) <= 15 and v not in (y + 1, y + 2)]
    if len(others_y) >= 2:
        return ('VINTAGE_AMBIGUOUS', 'the opening states several vintages (%s): a multi-vintage document' % (
            ', '.join(map(str, sorted(set([y] + others_y))))), None, facts)
    in_head = len(re.findall(r'(?<!\d)%d(?!\d)' % y, head))
    if in_head and len(re.findall(DATED % (MONTHS, y), head)) >= in_head:
        return ('VINTAGE_AMBIGUOUS', 'the opening states %d only in a calendar date: an event of that year, '
                'not the vintage' % y, None, facts)
    headed = sorted({int(v) for v in VINTAGE_HEAD.findall(text)} - {y})
    if len(headed) >= 3:
        return ('VINTAGE_AMBIGUOUS', 'the document heads %d other vintages (%s): a multi-vintage compilation' % (
            len(headed), ', '.join(map(str, headed[:6]))), None, facts)
    # the wine: named beside the year, by its own name or by "grand vin"
    ename, wname = nm.get(e, ''), nm.get(w, '')
    siblings = [s for s in ew.get(e, []) if s != w]
    own = distinct_name(wname, ename)
    named_siblings = sorted({nm.get(s, s) for s in siblings
                             if (dn := distinct_name(nm.get(s, ''), ename)) and all(t in text for t in dn)})
    if named_siblings:
        return ('MULTI_WINE_AMBIGUOUS', 'the document also names %s' % ', '.join(named_siblings[:3]), None, facts)
    # a sibling whose name lies inside the estate's ("Mondot" in "Troplong Mondot"): named on its own
    rest = head.replace(A.fold(ename), ' ').replace(A.fold(wname), ' ')
    for s in siblings:
        sn = A.fold(nm.get(s, ''))
        if sn and not distinct_name(nm.get(s, ''), ename) and re.search(r'(?<![\w-])%s(?![\w-])' % re.escape(sn), rest):
            return ('MULTI_WINE_AMBIGUOUS', 'the opening names %s on its own, a wine whose name lies inside the '
                    'estate\'s' % nm.get(s), None, facts)
    m_other = OTHER_WINE.search(head)
    if m_other and not own:
        return ('WINE_AMBIGUOUS', 'the opening speaks of another wine ("%s"): the document may be that wine, not %s' % (
            m_other.group(0), wname), None, facts)
    full = A.fold(wname)
    near = any(abs(m.start() - n.start()) <= NEAR for m in re.finditer(re.escape(full), text)
               for n in re.finditer(r'(?<!\d)%d(?!\d)' % y, text)) if full else False
    if own:
        if not all(t in text for t in own):
            return ('WINE_AMBIGUOUS', 'the document does not name the wine (%s)' % wname, None, facts)
        basis = 'the document names "%s" and states %d in its opening; no other wine of the estate is named' % (wname, y)
    elif near:
        basis = 'the document names "%s" beside %d; no other wine of the estate is named' % (wname, y)
        facts['grand_vin'] = True
    elif GRAND_VIN.search(head):
        basis = 'the document states %d in its opening and speaks of the grand vin; no other wine of the estate is named' % y
        facts['grand_vin'] = True
    else:
        return ('ESTATE_VINTAGE_ONLY', 'the document names the estate and %d, not the wine: %d other wine(s) at the estate' % (
            y, len(siblings)) if siblings else 'the document names the estate and %d, not the wine' % y, None, facts)
    # colour: the stated blend must be of the wine's colour, whatever the model lists for the estate
    mine = (wines.get(w) or {}).get('type')
    blends = [b for b in BLEND.findall(text)]
    red_b = any(RED_GRAPE.search(b) for b in blends)
    white_b = any(WHITE_GRAPE.search(b) for b in blends)
    if mine == 'RED' and white_b and not red_b:
        return ('COLOUR_AMBIGUOUS', 'a red wine, and the document\'s blend is of white grapes', None, facts)
    if mine and mine.startswith('WHITE') and red_b and not white_b:
        return ('COLOUR_AMBIGUOUS', 'a white wine, and the document\'s blend is of red grapes', None, facts)
    if BOTH_COLOURS.search(text):
        return ('COLOUR_AMBIGUOUS', 'the document describes the estate\'s red and white wines alike: it does not '
                'say for itself which wine it is', None, facts)
    types = {(wines.get(s) or {}).get('type') for s in ew.get(e, [])}
    if any(t and t.startswith('WHITE') for t in types) and 'RED' in types:
        if mine == 'RED' and WHITE.search(text) and not RED.search(text):
            return ('COLOUR_AMBIGUOUS', 'a red wine, and the document speaks only of white', None, facts)
        if mine and mine.startswith('WHITE') and not WHITE.search(text):
            return ('COLOUR_AMBIGUOUS', 'a white wine, and the document does not say white', None, facts)
        if mine not in ('RED', 'WHITE_DRY', 'WHITE_SWEET'):
            return ('COLOUR_AMBIGUOUS', 'the estate makes red and white; the wine\'s colour is not held', None, facts)
    if not row['evidence_refs']:
        return ('EVIDENCE_INSUFFICIENT', 'no evidence link ties the accepted decision to the model ids', None, facts)
    return ('SAFE_TO_MAP', basis, basis, facts)


def context(rows):
    """What the report needs beyond the rows: the baseline it measured, and the wines it may not map."""
    nm = P.names()
    nodoc = P.documentless()
    blocked = open_decision_wines(nm)
    nodoc_by_wine = collections.Counter(w for v in nodoc.values() for w, _ in v)
    return {'documentless': sum(len(v) for v in nodoc.values()),
            'documentless_estates': len(nodoc),
            'blocked': sorted((d, nm.get(w, w), w, nodoc_by_wine.get(w, 0)) for w, d in blocked.items()),
            'thresholds': {'opening': OPENING, 'near': NEAR}}


def body(rows):
    return ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                   for r in rows).encode('utf-8')


def main():
    rows = build()
    if '--report' in sys.argv:
        import m34a_report
        text = m34a_report.report(rows, context(rows))
        if '--check' in sys.argv:
            same = os.path.exists(REPORT) and open(REPORT, encoding='utf-8').read() == text
            print('docs/PHASE-M3.4A-MAPPING-AUDIT.md ' + ('is current' if same else 'differs from a fresh run'))
            sys.exit(0 if same else 1)
        open(REPORT, 'w', encoding='utf-8', newline='\n').write(text)
        print('wrote docs/PHASE-M3.4A-MAPPING-AUDIT.md')
        return
    b = body(rows)
    if '--check' in sys.argv:
        same = os.path.exists(OUT) and open(OUT, 'rb').read() == b
        print('data/audit/m3.4a-mapping-proposals.jsonl ' + ('is current' if same else 'differs from a fresh run'))
        sys.exit(0 if same else 1)
    print('%d candidates (%d vintages); %s' % (len(rows), len({(r['wine'], r['vintage']) for r in rows}),
                                               dict(collections.Counter(r['disposition'] for r in rows).most_common())))
    with open(OUT + '.tmp', 'wb') as f:
        f.write(b)
    os.replace(OUT + '.tmp', OUT)
    print('wrote', os.path.relpath(OUT, L.ROOT))


if __name__ == '__main__':
    main()
