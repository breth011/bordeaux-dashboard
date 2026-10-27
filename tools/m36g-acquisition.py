"""M3.6G: targeted acquisition for Cuvée Mongravey's open fields - the audit of every candidate, and why none applied.

    python tools/m36g-acquisition.py             write data/audit/m3.6g-cuvee-acquisition.jsonl
    python tools/m36g-acquisition.py --check     recompute and compare, byte for byte

THE GAPS are M3.6F's (data/audit/m3.6f-cuvee-vintages.jsonl): for each of wn_00640's six vintages, the fields
withheld or not stated - blend, yld, alc, ph, ta, sug, harvest, pick - and 2015's months, stated only with a
qualifier. Production (a model decision) and the keeping time (class B, held) are not gaps of this phase.

THE SOURCES, in the brief's order, and what each answered (sources/acquisition/m3.6g/inventory.json):
  1 vignobles-bernaleau.com's media library, asked for "mongravey" and "cuvee": every first-party upload, linked
    or not. It lists three editions of the Cuvée sheets (2023-09 FR, 2024-02 EN, 2025-07 FR+EN) and the press
    reviews; nothing else. The 2023-09 sheets of 2015-2020 were fetched: their sha1 and size are those of five
    artifacts the model already records (ar_010314, ar_010711, ar_001284, ar_007041, ar_011580), four of them
    with their bytes unavailable until now. No new document exists.
  2 mongravey.fr, www.mongravey.fr and www.chateau-mongravey.com redirect to vignobles-bernaleau.com.
  3 Held: the Cuvée's shop pages (/produit/mongravey-cuvee-speciale-YYYY, "Mongravey Cuvée Spéciale", a recorded
    MARKET_ALIAS of wn_00640), the 2024-02 EN sheets, the press reviews.
  4 The négociant: bordeaux-tradition.com's property sitemap names no Mongravey, Bernaleau or Braude property.

A CANDIDATE is a line of a held document of the vintage that states a gap field. It is read with M3.6F's own
rules (tools/m36f-vintages.py: title, sections, the exact months pattern) and it applies only if every one of
these holds - none is weakened here:
  IDENTITY_GATE_NOT_MET  M3.6F's identity gate - every latest evidence answer for these bytes names wn_00640 by
                         this title - is not met: no decision read the bytes, or the latest one is about another
                         wine. Judging them again would be a new evidence version.
  VINEYARD_SECTION       stated in the VINEYARD/VIGNOBLE section, beside the estate's surface and plant density: the
                         plots' planting and the vineyard's yield, not established as the wine's
  TEMPLATE               the page's characteristics are the same words on every vintage's page of that language
  CONTRADICTED           the vintage's own technical sheets state a different figure on the same page block
  QUALIFIED_IN_OTHER_LANGUAGE  the same vintage's sheet in the other language, of the same figure, says "depending
                         on vintages": the producer's own words that the figure is not the vintage's
  EARLIER_REVISION       an earlier upload of a sheet the 2025-07 revision replaced (the model's policy: a later
                         revision of the same document is preferred, the earlier kept)
  QUALIFIED              says more than a figure ("24 months maturing depending on vintages"): M3.6F's rule
  NOT_A_VALUE            says how the harvest was organised ("Vendange parcellaire"), not when or by variety
An exact figure that differs from a value M3.6F applied is a CONFLICT and is recorded here, with both quotes; the
applied value is not changed. A Cuvée sheet whose latest evidence answer still accepts it for another wine is a
FINDING, for a decision outside this phase. Nothing in the model, the evidence store or the app changes.
"""
import glob
import hashlib
import importlib.util
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evidence as EV  # noqa: E402
import evidence_store as ST  # noqa: E402
import migration_lib as L  # noqa: E402
import m35_rubric as RB  # noqa: E402

_spec = importlib.util.spec_from_file_location('m36f', L.ROOT + 'tools/m36f-vintages.py')
F = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(F)

OUT = L.ROOT + 'data/audit/m3.6g-cuvee-acquisition.jsonl'
ACQ = L.ROOT + 'sources/acquisition/m3.6g/'
YEARS = L.ROOT + 'sources/discovery/derived/years.jsonl'
AS_OF = 7                        # the evidence as M3.6F left it (v1-v7); M3.6H's later v8 corrects the finding
WINE, ALIAS = 'wn_00640', 'Mongravey Cuvée Spéciale'
FILE = re.compile(r'cuvee.?(de.?)?mongravey|mongravey.?cuvee', re.I)
SHOP = re.compile(r'/(?:produit|en/product)/mongravey-cuvee-speciale-\d{4}(?:-\d)?/$')
SHOP_TITLE = re.compile(r'^(Mongravey Cuvée Spéciale) (\d{4}) - Vignobles Bernaleau$')
BLOCK = re.compile(r'^(Caractéristiques|Characteristics)$')
GAP_FIELDS = ('blend', 'yld', 'alc', 'ph', 'ta', 'sug', 'harvest', 'pick')
SAYS = {
    'blend': re.compile(r'^(Grape Varieties|Encépagement|Assemblage)\s*:', re.I),
    'yld': re.compile(r'^(Yield|Rendement)\s*:', re.I),
    'months': re.compile(r'^(\d+) (?:months maturing|mois d.élevage)|^(?:Ageing|Élevage)\s*:\s*(\d+) (?:months|mois)', re.I),
    'alc': re.compile(r'alcool\s*:|alcohol\s*:|\d\s*% ?vol|\bTAV\b', re.I),
    'ph': re.compile(r'\bpH\b'),
    'ta': re.compile(r'acidit[ée] totale|total acidity', re.I),
    'sug': re.compile(r'sucres? r[ée]siduels?|residual sugar', re.I),
    'harvest': re.compile(r'^(vendanges?|harvest)\b', re.I),
    'pick': re.compile(r'\b\d{1,2}(?:er)? (?:sept|oct)|\bpicking\b|\bcueillette\b', re.I),
}
PRODUCTION = re.compile(r'(\d[\d ]*\d|\d+) (?:bottles|bouteilles)')


def number(s):
    return int(s.replace(' ', ''))


def shares(line):
    return sorted((v.lower(), int(p)) for p, v in re.findall(r'(\d+)%\s*(?:de\s+)?([A-Z][a-z]+(?: [A-Z][a-z]+)?)', line))


def text_lines(path):
    d = json.load(open(path, encoding='utf-8'))
    if d.get('media') == 'html':
        return [('b%d' % i, b['text'].strip()) for i, b in enumerate(d.get('blocks') or []) if b['text'].strip()], d
    out = []
    for p, page in enumerate(x for x in d.get('pages') or [] if isinstance(x, str)):
        for i, l in enumerate(page.splitlines()):
            if l.strip():
                out.append(('p%d:l%d' % (p + 1, i + 1), l.strip()))
    return out, d


def inventory():
    inv = json.load(open(ACQ + 'inventory.json', encoding='utf-8'))
    media = {}
    for p in inv['probes']:
        if p.get('file'):
            for m in json.load(open(ACQ + p['file'], encoding='utf-8')):
                media[m['source_url']] = m['date'][:10]
    blobs = {}
    for f in sorted(glob.glob(ACQ + 'blobs/*.pdf')):
        data = open(f, 'rb').read()
        sha = hashlib.sha256(data).hexdigest()
        assert os.path.basename(f) == sha + '.pdf', f
        blobs[(hashlib.sha1(data).hexdigest(), len(data))] = sha
    return inv, media, blobs


def documents(inv, media, blobs):
    """Every held document of the Cuvée: the model's artifacts filed under a Cuvée filename, and the shop pages."""
    arts = {a['id']: a for a in L.read_table('identity/artifacts.jsonl')}
    files, urls = {}, {}
    for p in L.read_table('document/placements.jsonl'):
        v = p['locator']['value']
        if FILE.search(os.path.basename(v)):
            files.setdefault(p['artifact'], set()).add(os.path.basename(v))
            if p['locator']['kind'] == 'URL':
                urls.setdefault(p['artifact'], set()).add(v)
    seen = {}
    for l in open(YEARS, encoding='utf-8'):
        if 'vignobles-bernaleau.com' in l and '"url"' in l:
            r = json.loads(l)
            if r['context'].startswith('https://'):
                seen.setdefault(r['artifact'], set()).add(r['context'])
    fetched = {f['sha256']: f['url'] for f in inv['fetched']}
    answer = {}
    for d in ST.iter_rows([v for v in ST.versions() if v <= AS_OF]):
        k = EV.row_key(d)[:-1]
        if k not in answer or (d.get('v') or 0) >= (answer[k].get('v') or 0):
            answer[k] = d
    latest = {}
    for d in answer.values():
        latest.setdefault((d.get('read') or {}).get('sha256'), []).append(d)
    m36f = {r['artifact']: r for r in L.jsonl_lines(L.ROOT + 'data/audit/m3.6f-cuvee-vintages.jsonl') if r['record'] == 'document'}
    out = []
    for art in sorted(files):
        a = arts[art]
        sha = a.get('sha256') or blobs.get((a.get('sha1'), a.get('bytes')))
        held = None
        for path in (L.ROOT + 'sources/discovery/extracted/%s.json' % sha, ACQ + 'extracted/%s.json' % sha):
            if sha and os.path.exists(path):
                held = path
                break
        u = sorted(urls.get(art, set()) | seen.get(sha, set()) | ({fetched[sha]} if sha in fetched else set()))
        doc = {'record': 'document', 'artifact': art, 'files': sorted(files[art]), 'sha256': sha, 'urls': u,
               'uploaded': sorted({media[x] for x in u if x in media}),
               'bytes_restored_by_m36g': sha in fetched and not a.get('sha256'),
               'latest_evidence': sorted({json.dumps([d['ctx'].get('evaluated_as'), d['v'], d['decision'], d['code']],
                                                     ensure_ascii=False) for d in latest.get(sha, [])}),
               'used_by_m36f': bool(m36f.get(art, {}).get('used'))}
        if not held:
            doc.update(kind='NO_TEXT_HELD', vintage=None, title_line=None, identity_gate=False)
            out.append((doc, []))
            continue
        lines, _ = text_lines(held)
        m = F.TITLE.match(lines[0][1]) if lines else None
        tech = all(any(re.match(s[0], l) for _, l in lines) for s in F.SECTIONS)
        vintage = int(m.group(1)) if m and m.group(1) else None
        want = {'title': [RB.fold(F.NAME), vintage], 'model_wines': [WINE], 'unlisted': False}
        named = [d.get('document_is') for d in latest.get(sha, []) if d.get('document_is')]
        other = sorted({d['ctx'].get('evaluated_as') for d in latest.get(sha, [])
                        if d['decision'] == 'ACCEPTED' and not d.get('document_is')})
        doc.update(title_line=lines[0][1] if lines else None, vintage=vintage,
                   kind='TECHNICAL_SHEET' if m and tech else ('PRESS_REVIEW' if m else 'OTHER'),
                   lang='en' if any(re.match(r'^(VINEYARD|MATURING)$', l) for _, l in lines) else 'fr',
                   identity_gate=bool(named) and all(n == want for n in named) and not other,
                   accepted_for_another_wine=other)
        out.append((doc, lines))
    names = {n['name']: n for n in L.read_table('identity/names.jsonl') if n['subject'] == WINE}
    assert names.get(ALIAS, {}).get('kind') == 'MARKET_ALIAS', 'the shop name is not wn_00640\'s'
    shop = sorted({(sha, url) for sha, us in seen.items() for url in us if SHOP.search(url)}, key=lambda x: x[1])
    for sha, url in shop:
        lines, d = text_lines(L.ROOT + 'sources/discovery/extracted/%s.json' % sha)
        m = SHOP_TITLE.match(d.get('title') or '')
        assert m and RB.fold(m.group(1)) == RB.fold(ALIAS), url
        i = next(i for i, (_, l) in enumerate(lines) if BLOCK.match(l))
        j = next(j for j in range(i + 1, len(lines)) if d['blocks'][int(lines[j][0][1:])]['tag'] == 'h2')
        doc = {'record': 'document', 'artifact': None, 'files': [], 'sha256': sha, 'urls': [url], 'uploaded': [],
               'bytes_restored_by_m36g': False, 'latest_evidence': [], 'used_by_m36f': False, 'identity_gate': False,
               'title_line': d['title'], 'vintage': int(m.group(2)), 'kind': 'SHOP_PAGE',
               'lang': 'en' if '/en/' in url else 'fr', 'block': [l for _, l in lines[i + 1:j]]}
        out.append((doc, lines[i + 1:j]))
    return out


def build():
    inv, media, blobs = inventory()
    docs = documents(inv, media, blobs)
    f_rows = L.jsonl_lines(L.ROOT + 'data/audit/m3.6f-cuvee-vintages.jsonl')
    years = F.EXPECT_VINTAGES
    gaps = {(int(r['vintage'][-4:]), r['field']) for r in f_rows
            if r['record'] == 'withheld' and r['field'] in GAP_FIELDS}
    gaps |= {(int(r['vintage'][-4:]), r['field']) for r in f_rows if r['record'] == 'value' and not r['applied']}
    applied = {(int(r['vintage'][-4:]), r['field']): r for r in f_rows if r['record'] == 'value' and r['applied']}
    sheet_says = {}   # the vintage's M3.6F sheets: production figures and blend shares, to test a page against
    for r in f_rows:
        if r['record'] == 'withheld' and r['field'] in ('production', 'blend'):
            for e in r['evidence']:
                v = number(PRODUCTION.search(e['quote']).group(1)) if r['field'] == 'production' else shares(e['quote'])
                sheet_says.setdefault((int(r['vintage'][-4:]), r['field']), set()).add(json.dumps(v))
    shop_blocks = {}
    for d, _ in docs:
        if d['kind'] == 'SHOP_PAGE':
            shop_blocks.setdefault(d['lang'], {}).setdefault(json.dumps(d['block'], ensure_ascii=False), set()).add(d['vintage'])
    qualified_other = {}  # (vintage, lang, figure) -> the other-language sheet's qualified months line
    for d, lines in docs:
        if d['kind'] == 'TECHNICAL_SHEET':
            for loc, l in F.section(lines, F.SECTIONS[2][0]):
                e = F.FIELDS['months'][1].match(l)
                if e and not F.FIELDS['months'][0].match(l):
                    qualified_other[(d['vintage'], d['lang'], e.group(1))] = (d['artifact'], loc, l)
    rows, cands = [], []
    for d, lines in docs:
        if d['vintage'] not in years or d['kind'] not in ('TECHNICAL_SHEET', 'SHOP_PAGE'):
            continue
        vineyard = {loc for loc, _ in F.section(lines, F.SECTIONS[0][0])} if d['kind'] == 'TECHNICAL_SHEET' else set()
        for field, pat in sorted(SAYS.items()):
            for loc, l in lines:
                if not pat.search(l) or (field == 'months' and (d['vintage'], field) not in gaps
                                         and (d['vintage'], field) not in applied):
                    continue
                if field not in ('months',) and (d['vintage'], field) not in gaps:
                    continue
                codes, why = [], []
                if d['used_by_m36f']:
                    continue  # already read by M3.6F, with the same rules: its decision stands in its manifest
                if not d['identity_gate']:
                    codes.append('IDENTITY_GATE_NOT_MET')
                    why.append('latest evidence answers for these bytes: %s' % ('; '.join(d['latest_evidence']) or 'none'))
                if loc in vineyard:
                    codes.append('VINEYARD_SECTION')
                if field == 'harvest':
                    codes.append('NOT_A_VALUE')
                if d['kind'] == 'SHOP_PAGE':
                    same = shop_blocks[d['lang']][json.dumps(d['block'], ensure_ascii=False)]
                    if len(same) > 1:
                        codes.append('TEMPLATE')
                        why.append('the same characteristics, word for word, on the %s pages of %d vintages (%s)'
                                   % (d['lang'], len(same), ', '.join(map(str, sorted(same)))))
                    against = []
                    for bl in d['block']:
                        p = PRODUCTION.search(bl)
                        if p and sheet_says.get((d['vintage'], 'production')) and \
                                json.dumps(number(p.group(1))) not in sheet_says[(d['vintage'], 'production')]:
                            against.append('production %s on the page, %s on the vintage\'s sheets' % (
                                number(p.group(1)), ' / '.join(sorted(sheet_says[(d['vintage'], 'production')]))))
                        if SAYS['blend'].search(bl) and sheet_says.get((d['vintage'], 'blend')) and \
                                json.dumps(shares(bl)) not in sheet_says[(d['vintage'], 'blend')]:
                            against.append('grapes %s on the page, %s on the vintage\'s sheets' % (
                                json.dumps(shares(bl)), ' / '.join(sorted(sheet_says[(d['vintage'], 'blend')]))))
                    if against:
                        codes.append('CONTRADICTED')
                        why += against
                fig = None
                if field == 'months':
                    mm = SAYS['months'].search(l)
                    if F.FIELDS['months'][0].match(l) or mm.group(2):
                        fig = mm.group(1) or mm.group(2)
                    else:
                        codes.append('QUALIFIED')
                    other = fig and qualified_other.get((d['vintage'], 'en' if d['lang'] == 'fr' else 'fr', fig))
                    if other and other[0] != d['artifact']:
                        codes.append('QUALIFIED_IN_OTHER_LANGUAGE')
                        why.append('%s (%s, %s) of the same vintage: "%s"' % (other[0], other[1], d['lang'] == 'fr' and 'en' or 'fr', other[2]))
                    if d['kind'] == 'TECHNICAL_SHEET' and d['uploaded'] and (d['vintage'], 'months') in applied:
                        later = sorted({u for x, _ in docs if x['used_by_m36f'] and x['vintage'] == d['vintage'] for u in x['uploaded']})
                        if later and max(d['uploaded']) < min(later):
                            codes.append('EARLIER_REVISION')
                            why.append('uploaded %s; the sheets M3.6F applied were uploaded %s' % (', '.join(d['uploaded']), ', '.join(later)))
                c = {'record': 'candidate', 'vintage': 'vt:%s:%d' % (WINE, d['vintage']), 'field': field,
                     'source': d['artifact'] or d['urls'][0], 'kind': d['kind'], 'lang': d['lang'], 'locus': loc, 'quote': l,
                     'codes': codes, 'why': why, 'decision': 'REJECTED' if codes else 'ACCEPTED'}
                if (d['vintage'], field) in applied:
                    cur = applied[(d['vintage'], field)]
                    c['existing'] = {'value': cur['value'], 'rule': cur['rule']}
                    c['conflict'] = fig is not None and fig != cur['value']
                    c['decision'] = 'NOT_ENTERED' if codes else 'TO_RECONCILE'
                cands.append(c)
    for c in sorted(cands, key=lambda c: (c['vintage'], c['field'], c['source'], c['locus'])):
        rows.append(c)
    for year in years:
        for field in GAP_FIELDS + ('months',):
            if (year, field) not in gaps:
                continue
            mine = [c for c in cands if c['vintage'].endswith(str(year)) and c['field'] == field]
            acc = [c for c in mine if c['decision'] == 'ACCEPTED']
            rows.append({'record': 'gap', 'vintage': 'vt:%s:%d' % (WINE, year), 'field': field,
                         'status': 'RESOLVED' if acc else 'UNRESOLVED', 'candidates': len(mine), 'accepted': len(acc),
                         'acquisition': None if acc else
                         'no first-party or trade source publishes it (sources/acquisition/m3.6g/inventory.json); '
                         'only a direct request to Vignobles Bernaleau could settle it'})
    for d, _ in docs:
        rows.append({k: v for k, v in d.items() if k != 'block'})
        for asked in d.get('accepted_for_another_wine') or []:
            rows.append({'record': 'finding', 'artifact': d['artifact'], 'title_line': d['title_line'], 'asked': asked,
                         'why': 'a Cuvée de Mongravey sheet whose latest evidence answer accepts it as "%s"; no later '
                                'version corrects it (M3.6E corrected 38 others; this one held no text until M3.6G)' % asked,
                         'proposal': 'an M3.6E-style correction, a new evidence version: not made in M3.6G'})
    for p in inv['probes']:
        rows.append(dict(p, record='probe'))
    for f in inv['fetched']:
        rows.append(dict(f, record='fetched'))
    rows.append({'record': 'summary', 'gaps': len(gaps), 'resolved': sum(1 for r in rows if r['record'] == 'gap' and r['status'] == 'RESOLVED'),
                 'candidates': len(cands), 'accepted': sum(1 for c in cands if c['decision'] == 'ACCEPTED'),
                 'conflicts': sum(1 for c in cands if c.get('conflict')),
                 'findings': sum(1 for r in rows if r['record'] == 'finding'), 'model_changes': 0})
    return rows


def main():
    b = F.body(build())
    if '--check' in sys.argv:
        same = os.path.exists(OUT) and open(OUT, 'rb').read() == b
        print('data/audit/m3.6g-cuvee-acquisition.jsonl ' + ('is current' if same else 'differs from a fresh run'))
        sys.exit(0 if same else 1)
    open(OUT, 'wb').write(b)
    print('wrote data/audit/m3.6g-cuvee-acquisition.jsonl')


if __name__ == '__main__':
    main()
