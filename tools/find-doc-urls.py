# -*- coding: utf-8 -*-
"""Read a document's address off the page that links to it.

    python tools/find-doc-urls.py --estate palmer
    python tools/find-doc-urls.py --estate palmer --apply
    python tools/find-doc-urls.py --classified --apply

An estate's PDFs were fetched before harvest.py recorded where it got
them, so the manifest holds the file and not its address, and the
records that cite it cannot link to their source. Palmer has 56 such
PDFs - and 73 crawled pages whose addresses ARE on record, and those
pages are where the PDFs were linked from in the first place.

So: fetch the pages we can already reach, take every document link off
them, and match by filename. Nothing is guessed - a match means that
page carries a link whose last path segment is exactly this file.

WHY NOT THE MEDIA LIBRARY

tools/recover-urls.py asks /wp-json/wp/v2/media, which is the cheapest
question and the right one for a WordPress site. It is close to
exhausted: of the twelve estates with the most records wanting an
address it filled none, because Lafite, Rieussec and Duhart-Milon
share a library that does not name their files and five of the twelve
serve no library at all.

This works on any site that links its own documents, whatever it is
built with. Palmer is Webflow and its filenames carry a CDN hash -
6708fceb328ad893ef618242_Fiche_millesime_EN_1978.pdf - which no
library would have told us and the linking page states exactly.

WHAT IT COSTS

One fetch per page, with a cap. It only fetches pages whose address
the manifest already holds, so it visits nothing it was not already
sent to, and it reads the markup for links without following them.
"""
import io, json, os, re, sys, time, gzip, argparse, collections
import urllib.request as ur
import urllib.parse as up
import html as H

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
MAN = ROOT + 'data/sources.json'
UA = {'User-Agent': 'Mozilla/5.0 (compatible; bordeaux-dashboard/1.0)'}
DOC = re.compile(r'(?i)\.(pdf|docx?|xlsx?)(?:\?|$)')


def get(url, timeout=35):
    req = ur.Request(url, headers=UA)
    with ur.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    if raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    return raw.decode('utf-8', 'replace')


def doc_links(page, base):
    """Every document address the markup points at, made absolute."""
    out = []
    for m in re.finditer(r'(?i)(?:href|src|content|data-[a-z-]+)\s*=\s*'
                         r'["\']([^"\']+)["\']', page):
        u = H.unescape(m.group(1)).strip()
        if DOC.search(u):
            out.append(up.urljoin(base, u))
    # Webflow and others put the real address in a JSON blob.
    for m in re.finditer(r'(?i)"(https?:[^"\s]+?\.(?:pdf|docx?))"', page):
        out.append(H.unescape(m.group(1)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estate', action='append', default=[])
    ap.add_argument('--classified', action='store_true')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--pages', type=int, default=80,
                    help='at most this many pages per estate (default 80)')
    ap.add_argument('--pause', type=float, default=0.4)
    a = ap.parse_args()

    man = json.load(io.open(MAN, encoding='utf-8'))
    want = list(a.estate)
    if a.classified:
        t = io.open(ROOT + 'data/chateaux.js', encoding='utf-8').read()
        want += sorted(set(
            m.group(1) for m in
            re.finditer(r"id:'([a-z0-9-]+)'[^}]{0,400}?growth:\d", t)))
    if not want:
        ap.error('--estate or --classified')
    want = list(dict.fromkeys(want))

    # Which files a record actually cites, because a document nothing
    # cites needs no address.
    cited = set()
    for p in ('data/fiches.js', 'data/cuvees.js'):
        if not os.path.exists(ROOT + p):
            continue
        for line in io.open(ROOT + p, encoding='utf-8'):
            m = re.search(r"src:'((?:[^'\\]|\\.)*)'", line)
            if m:
                for x in re.sub(r'\\(.)', r'\1', m.group(1)).split(','):
                    cited.add(x.strip())

    rows = collections.defaultdict(list)
    for s in man['sheets']:
        if s.get('estate'):
            rows[s['estate']].append(s)

    filled, why = 0, collections.Counter()
    for eid in want:
        mine = rows.get(eid) or []
        need = dict((s['file'].lower(), s) for s in mine
                    if not s.get('url') and s['file'] in cited)
        if not need:
            why['every cited document already has an address'] += 1
            continue
        pages = [s['url'] for s in mine
                 if s.get('url') and not DOC.search(s['url'])]
        pages = list(dict.fromkeys(pages))[:a.pages]
        if not pages:
            why['no page of its own to read the links off'] += 1
            continue

        found, seen = {}, 0
        for u in pages:
            try:
                page = get(u)
            except Exception:
                continue
            seen += 1
            for link in doc_links(page, u):
                nm = os.path.basename(up.urlsplit(link).path).lower()
                if nm in need and nm not in found:
                    found[nm] = link
            time.sleep(a.pause)
            if len(found) >= len(need):
                break

        print('   %-32s %3d of %3d wanted, from %d page(s)'
              % (eid[:32], len(found), len(need), seen))
        for nm, link in found.items():
            need[nm]['url'] = link
        filled += len(found)
        if not found:
            why['its pages link none of the wanted files'] += 1

    print('\n%d address(es) found' % filled)
    for k, n in why.most_common():
        print('   %-54s %d estate(s)' % (k, n))
    if not a.apply:
        print('\nnothing written; pass --apply')
        return 0
    if not filled:
        return 0
    import shutil
    shutil.copy(MAN, MAN + '.bak')
    io.open(MAN, 'w', encoding='utf-8', newline='').write(
        json.dumps(man, ensure_ascii=False, indent=1))
    print('\nwritten to data/sources.json; now run '
          'tools/build-fiche-links.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())
