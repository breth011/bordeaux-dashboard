"""M3.6D: the canonical Cuvée Mongravey wine - the audited input the migration reads.

    python tools/m36d-cuvee.py             write data/audit/m3.6d-cuvee-mongravey.jsonl
    python tools/m36d-cuvee.py --check     recompute and compare, byte for byte

M3.6C (data/audit/m3.6c-cuvee-mongravey-identity.jsonl) found a distinct, lasting red selection cuvée
of Château Mongravey. M3.6D records that decision in the model with the mechanisms the model already
has (docs/phase34-model.json); nothing in the contract is extended:

  the wine          one Wine, type RED, minted under wine-by-slug bourgeois-chateau-mongravey|cuvee-mongravey
  its names         CURRENT "Cuvée Mongravey"; SOURCE_RENDERING "Cuvée de Mongravey" (its sheets' titles);
                    MARKET_ALIAS "Mongravey Cuvée Spéciale" (its product name). "Mongravey Cuvée Margaux"
                    is NOT recorded: only the estate page's layout ties it to the Cuvée (M3.6C).
  its estate        PRODUCED_BY es_00158, established
  what it is        a WineDescriptor PLOT_SELECTION, source term "cuvée spéciale" - and no RankAssertion:
                    the contract rejects OTHER_CUVEE as a rank ("other cuvee" was the absence of a rank
                    statement); a selection cuvée nobody ranks has none.
  its first vintage recorded here as FIRST_VINTAGE_STATED 1999, the sheet's own words "1st Vintage: 1999" -
                    and NOT applied. A dated statement is a historical claim (Observation.claimed_window,
                    statement_mode EXPLICIT), and Historical M3's gate (docs/PHASE-M3-EXPLICIT-HISTORICAL-
                    CLAIMS.md) admits none yet: E3 holds only through a v5 acceptance of this very sheet as
                    Château Mongravey 2016 (one of the 38 M3.6C names), and E7 through the open naming
                    decision. The relationship stays "current, start unknown", like every other; no 1999
                    Vintage is created, and no vintage at all. Not the earliest documented vintage either.

Every fact names the held document and the exact words it rests on; the run stops if a quote is not in
that document's held text, or if M3.6C's record of the document says something else. No vintage, figure,
attribution or evidence decision is created; the 38 historical acceptances M3.6C named are not touched.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import migration_lib as L  # noqa: E402

OUT = L.ROOT + 'data/audit/m3.6d-cuvee-mongravey.jsonl'
M36C = L.ROOT + 'data/audit/m3.6c-cuvee-mongravey-identity.jsonl'
EXTRACTED = L.ROOT + 'sources/discovery/extracted/'
ESTATE, ESTATE_KEY, GRAND_VIN = 'es_00158', 'bourgeois-chateau-mongravey', 'wn_00158'
SLUG = 'cuvee-mongravey'

# (fact, value, the M3.6C record's artifact, the disposition M3.6C gave it, the words it rests on)
FACTS = [
    ('name', {'name': 'Cuvée Mongravey', 'kind': 'CURRENT'}, 'ar_029337', 'POSITIVE_WINE_IDENTITY',
     'Press Reviews & Technical Sheets Cuvée Mongravey'),
    ('name', {'name': 'Cuvée de Mongravey', 'kind': 'SOURCE_RENDERING'}, 'ar_010576', 'POSITIVE_VINTAGE_EVIDENCE',
     'Cuvée de Mongravey 2016'),
    ('name', {'name': 'Mongravey Cuvée Spéciale', 'kind': 'MARKET_ALIAS'}, 'ar_028855', 'POSITIVE_NAMING_VARIANT',
     'Mongravey Cuvée Spéciale 2009'),
    ('estate', {'estate': ESTATE, 'kind': 'PRODUCED_BY'}, 'ar_028855', 'POSITIVE_NAMING_VARIANT',
     'a meticulous selection of our best plots of vines of Château Mongravey'),
    ('descriptor', {'kind': 'PLOT_SELECTION', 'source_term': 'cuvée spéciale'}, 'ar_028855', 'POSITIVE_NAMING_VARIANT',
     'Confidential cuvée of 3000 bottles resulting from a meticulous selection of our best plots of vines of Château Mongravey'),
    ('type', {'type': 'RED'}, 'ar_010576', 'POSITIVE_VINTAGE_EVIDENCE',
     'Grape Varieties: 30% Merlot, 70% Cabernet Sauvignon'),
    ('type', {'type': 'RED'}, 'ar_013215', 'COLOUR_ESTABLISHED',
     'Brilliant ruby color'),
    ('first_vintage', {'kind': 'FIRST_VINTAGE_STATED', 'vintage': 1999}, 'ar_010576', 'POSITIVE_VINTAGE_EVIDENCE',
     '1st Vintage: 1999'),
]
# Facts the documents state that the model does not take yet, and why.
NOT_APPLIED = {'first_vintage': 'a historical claim; Historical M3 gate: E3 rests on the v5 acceptance of this sheet as '
                                'Château Mongravey 2016 (an M3.6C historical misattribution), E7 on the open naming decision'}
# Named, and deliberately not recorded: a name only the estate page's layout ties to the Cuvée.
UNRESOLVED = [('Mongravey Cuvée Margaux', 'ar_014807',
               'the estate page lists it under "Our wines" beside the grand vin; no held text says it is '
               'Cuvée Mongravey (M3.6C: STRUCTURAL tie only)')]


def held_text(sha):
    """The held extraction's own text (original case): title, headings, blocks, pages, text."""
    p = EXTRACTED + sha + '.json'
    d = json.load(open(p, encoding='utf-8'))
    if d.get('status') != 'EXTRACTED':
        raise SystemExit('M3.6D: %s has no extracted text' % sha)
    parts = [d.get('title') or '']
    parts += [h.get('text') or '' for h in d.get('headings') or []]
    parts += [b.get('text') or '' for b in d.get('blocks') or []]
    parts += [x for x in d.get('pages') or [] if isinstance(x, str)]
    if isinstance(d.get('text'), str):
        parts.append(d['text'])
    return '\n'.join(parts)


def build():
    m36c = {r['artifact']: r for r in L.jsonl_lines(M36C) if r['record'] == 'document'}
    rows = []
    for fact, value, aid, disposition, quote in FACTS:
        r = m36c.get(aid)
        if not r or r['disposition'] != disposition:
            raise SystemExit('M3.6D: M3.6C no longer records %s as %s' % (aid, disposition))
        if ' '.join(quote.split()) not in ' '.join(held_text(r['sha256']).split()):
            raise SystemExit('M3.6D: %r is not in the held text of %s' % (quote, aid))
        row = {'record': 'fact', 'fact': fact, 'value': value, 'wine_key': '%s|%s' % (ESTATE_KEY, SLUG),
               'estate': ESTATE, 'artifact': aid, 'sha256': r['sha256'],
               'document': (r.get('urls') or r.get('files') or [None])[0],
               'm36c_record': r['id'], 'm36c_disposition': disposition, 'quote': quote, 'applied': fact not in NOT_APPLIED}
        if fact in NOT_APPLIED:
            row['why'] = NOT_APPLIED[fact]
        rows.append(row)
    for name, aid, why in UNRESOLVED:
        r = m36c[aid]
        rows.append({'record': 'unresolved_name', 'fact': 'name', 'value': {'name': name}, 'wine_key': '%s|%s' % (ESTATE_KEY, SLUG),
                     'estate': ESTATE, 'artifact': aid, 'sha256': r['sha256'],
                     'document': (r.get('urls') or [None])[0], 'm36c_record': r['id'],
                     'm36c_disposition': r['disposition'], 'why': why, 'applied': False})
    return rows


def body(rows):
    return ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                   for r in rows).encode('utf-8')


def main():
    b = body(build())
    if '--check' in sys.argv:
        same = os.path.exists(OUT) and open(OUT, 'rb').read() == b
        print('data/audit/m3.6d-cuvee-mongravey.jsonl ' + ('is current' if same else 'differs from a fresh run'))
        sys.exit(0 if same else 1)
    with open(OUT + '.tmp', 'wb') as f:
        f.write(b)
    os.replace(OUT + '.tmp', OUT)
    print('wrote data/audit/m3.6d-cuvee-mongravey.jsonl (%d facts, %d unresolved name)'
          % (sum(1 for x in FACTS), len(UNRESOLVED)))


if __name__ == '__main__':
    main()
