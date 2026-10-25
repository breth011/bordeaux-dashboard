"""Historical model M2: decide each held document's own date, and record why.

    python tools/extract-document-dates.py             write data/history/document-dates.jsonl
    python tools/extract-document-dates.py --check     recompute and compare, byte for byte
    python tools/extract-document-dates.py --dry-run   the counts and the ArtifactDate rows the
                                                       model would gain; writes nothing

One row per model artifact (data/model/identity/artifacts.jsonl), sorted by
artifact id, with the decision of tools/document_dates.py and the clues that
named a rejection. The text read is the text already held: the discovery
extraction (sources/discovery/extracted/<sha256>.json, discover-extract/1.0)
or, for a plain-text document, its own bytes. No PDF or page is parsed again
here, nothing is fetched, and no clock is read, so the same store gives the
same file. tools/mig_m6_provenance.py writes the accepted dates into the model
as ArtifactDate rows (STATED_IN_TEXT); nothing else in the model reads this.
"""
import collections
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import document_dates as D  # noqa: E402
import migration_lib as L  # noqa: E402

OUT = L.ROOT + 'data/history/document-dates.jsonl'
EXTRACTED = L.ROOT + 'sources/discovery/extracted/'
YEAR = re.compile(r'(?<!\d)(?:19|20)\d\d(?!\d)')
METADATA_KEYS = re.compile(r'date|published|modified|created', re.IGNORECASE)
NO_RETRIEVAL_LATEST = '2026-12-31'      # used only where no retrieval timestamp is held


def strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings(v)


def segments_of(d):
    """[(locus, text)] in document order from a discovery extraction record."""
    seg = []
    if d.get('title'):
        seg.append(('title', d['title']))
    for i, h in enumerate(d.get('headings') or []):
        if h.get('text'):
            seg.append(('h:%d' % i, h['text']))
    for i, b in enumerate(d.get('blocks') or []):
        if b.get('text'):
            seg.append(('b:%d' % i, b['text']))
    for i, p in enumerate(d.get('pages') or []):
        if isinstance(p, str) and p:
            seg.append(('p:%d' % (i + 1), p))
    for i, t in enumerate(d.get('tables') or []):
        txt = ' | '.join(strings(t))
        if txt:
            seg.append(('t:%d' % i, txt))
    if isinstance(d.get('text'), str) and d['text']:
        seg.append(('text', d['text']))
    return seg


BEFORE_H1, AFTER_H1, TEXT_LINES = 2, 4, 8


def anchored_of(d):
    """The loci where a document dates itself: a PDF's first page; on a web page, the blocks just
    before and after its main (h1) heading, where a post's byline sits. A page with no h1 has none."""
    if d.get('pages'):
        return {'p:1'}
    blocks = d.get('blocks') or []
    out = set()
    for i, b in enumerate(blocks):
        if (b.get('tag') or '').lower() == 'h1':
            out.update('b:%d' % j for j in range(max(0, i - BEFORE_H1), min(len(blocks), i + AFTER_H1 + 1)))
    return out


def metadata_dated(d):
    """Whether the document carries a machine-readable date of its own (JSON-LD, meta, PDF info).
    Recorded as a clue only: such dates are not printed text and are not accepted."""
    meta = d.get('meta') or {}
    if any(METADATA_KEYS.search(k) and v for k, v in meta.items()):
        return True
    return any(re.search(r'"date(Published|Modified|Created)"', j or '') for j in d.get('jsonld') or [])


def main():
    arts = sorted(L.read_table('identity/artifacts.jsonl'), key=lambda a: a['id'])
    places = collections.defaultdict(list)
    for p in L.read_table('document/placements.jsonl'):
        if p.get('artifact'):
            places[p['artifact']].append(p['locator'])
    fetched = collections.defaultdict(list)          # sha256 -> [(at, url)]
    for f in sorted(glob.glob(L.ROOT + 'data/discovery/locations/*.jsonl')):
        for r in L.jsonl_lines(f):
            if r.get('sha256'):
                fetched[r['sha256']].append((r.get('at') or '', r.get('final_url') or r.get('url') or '',
                                             r.get('last_modified')))
    rows = []
    for a in arts:
        sha = a.get('sha256')
        locs = places.get(a['id'], [])
        names = [os.path.basename(l['value']) for l in locs if l['kind'] == 'LOCAL_PATH']
        urls = [l['value'] for l in locs if l['kind'] == 'URL'] + [u for _, u, _ in fetched.get(sha, []) if u]
        clues = {
            'filename_year': any(YEAR.search(n) for n in names) or any(YEAR.search(u.rsplit('/', 1)[-1]) for u in urls),
            'url_year': any(YEAR.search(u.rsplit('/', 1)[0]) for u in urls),
            'retrieved': bool(fetched.get(sha)),
            'http_last_modified': any(lm for _, _, lm in fetched.get(sha, [])),
            'metadata_date': False,
        }
        stamps = sorted(at[:10] for at, _, _ in fetched.get(sha, []) if at)
        latest = stamps[0] if stamps else NO_RETRIEVAL_LATEST
        segs, source, anchored = None, None, None
        if sha and os.path.exists(EXTRACTED + sha + '.json'):
            d = json.load(open(EXTRACTED + sha + '.json', encoding='utf-8'))
            if d.get('status') == 'EXTRACTED':
                segs, source = segments_of(d), 'extracted'
                anchored = anchored_of(d)
                clues['metadata_date'] = metadata_dated(d)
        if segs is None and (a.get('media_type') == 'text/plain' or any(n.endswith('.txt') for n in names)):
            for l in sorted(locs, key=lambda l: l['value']):
                p = L.ROOT + 'sources/' + l['value']
                if l['kind'] == 'LOCAL_PATH' and os.path.exists(p):
                    text = open(p, 'rb').read().decode('utf-8', 'replace')
                    segs, source = [('l:%d' % i, t) for i, t in enumerate(text.split('\n')) if t.strip()], 'raw_text'
                    anchored = {l for l, _ in segs[:TEXT_LINES]}
                    break
        decision = D.decide(segs, clues, latest=latest, anchored=anchored)
        row = {'artifact': a['id'], 'sha256': sha, 'category': decision.pop('category'), 'extractor': D.VERSION}
        if source:
            row['text'] = source
        row.update({k: v for k, v in decision.items() if v not in (None, [], '')})
        rows.append(row)
    body = ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                   for r in rows).encode('utf-8')
    counts = collections.Counter(r['category'] for r in rows)
    if '--check' in sys.argv:
        same = os.path.exists(OUT) and open(OUT, 'rb').read() == body
        print('data/history/document-dates.jsonl ' + ('is current' if same else 'differs from a fresh run'))
        sys.exit(0 if same else 1)
    print('%d documents: %s' % (len(rows), json.dumps(dict(counts.most_common()))))
    accepted = [r for r in rows if r['category'] == D.ACCEPTED]
    print('ArtifactDate rows the model would gain: %d (0 today); by precision %s' % (
        len(accepted), dict(collections.Counter(r['precision'] for r in accepted))))
    if '--dry-run' in sys.argv:
        for r in accepted[:int(os.environ.get('M2_SHOW', '0'))]:
            print('  %s  (none) -> STATED_IN_TEXT %s %s  [%s %s] %s' % (r['artifact'], r['value'], r['precision'],
                                                                       r['label'], r['locus'], r['quote']))
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT + '.tmp', 'wb') as f:
        f.write(body)
    os.replace(OUT + '.tmp', OUT)
    print('wrote', os.path.relpath(OUT, L.ROOT))


if __name__ == '__main__':
    main()
