# -*- coding: utf-8 -*-
"""What does an estate's own site publish that we do not hold?

    python tools/ask-site.py --estate latour
    python tools/ask-site.py --estate latour --site https://...

Asks, in this order, and stops costing anything the moment the
answer is no:

    robots.txt          may we, and where are the sitemaps
    the sitemaps        every address the site admits to
    the media library   /wp-json/wp/v2/media, for the PDFs
    the manifest        which of those we already hold

and then reports the vintage-shaped addresses grouped by the wine
they belong to, which is the thing the estate pass needs: whether
there are years, wines or documents nobody has fetched.

WHY ASK THE SITEMAP AND NOT CRAWL

A sitemap is the site telling us what it has, in one request. Margaux
turned out to publish 126 vintages back to 1900 where the manifest
held 76 from 1950, and that was one fetch rather than fifty guesses -
the fifty guesses came after, aimed at exactly the years that were
missing.

WHAT IT WILL NOT DO

It fetches robots.txt, the sitemaps and one JSON endpoint. It does not
fetch a single page of content: that is tools/crawl-pages.py's job and
it takes --apply before it touches anything.

It respects robots.txt. Where a Disallow covers the sitemap path for
every agent, it says so and stops - Petrus serves `Disallow: /` and
is not to be crawled.
"""
import io, json, os, re, sys, gzip, argparse, collections
import urllib.request as ur
import urllib.parse as up

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
UA = {'User-Agent': 'Mozilla/5.0 (compatible; bordeaux-dashboard/1.0)'}

# A vintage-shaped address: a path segment ending in a four-figure
# year, which is how every estate that publishes per-vintage pages
# seems to spell them.
VINT = re.compile(r'/([a-z0-9][a-z0-9-]*?)-?((?:18|19|20)\d\d)/?$', re.I)


def get(url, timeout=45):
    req = ur.Request(url, headers=UA)
    with ur.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    if raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    return raw.decode('utf-8', 'replace')


def disallows_all(robots):
    """Does a Disallow: / apply to every agent?"""
    agent, blocked = None, False
    for line in robots.splitlines():
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        k, _, v = line.partition(':')
        k, v = k.strip().lower(), v.strip()
        if k == 'user-agent':
            agent = v
        elif k == 'disallow' and agent == '*' and v == '/':
            blocked = True
        elif k == 'allow' and agent == '*' and v in ('/', ''):
            blocked = False
    return blocked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estate', required=True)
    ap.add_argument('--site', default=None,
                    help='override the address on record')
    ap.add_argument('--show', type=int, default=14,
                    help='how many missing years to name per wine')
    a = ap.parse_args()

    site = a.site
    if not site:
        W = {}
        p = ROOT + 'data/websites.js'
        if os.path.exists(p):
            t = io.open(p, encoding='utf-8').read()
            # websites.js writes 'id':['url','where it came from'],
            # so the address is the first string of the row.
            for m in re.finditer(r"'([a-z0-9-]+)':\[\s*'([^']+)'", t):
                W.setdefault(m.group(1), m.group(2))
        site = W.get(a.estate)
    if not site:
        print('no address on record for %s; pass --site' % a.estate)
        return 2
    host = up.urlsplit(site)
    base = '%s://%s' % (host.scheme or 'https', host.netloc)
    print('%s - %s' % (a.estate, base))

    print('\n--- robots.txt')
    try:
        rb = get(base + '/robots.txt', 25)
    except Exception as e:
        print('   could not be read (%s); assuming nothing' % str(e)[:50])
        rb = ''
    for line in rb.splitlines()[:28]:
        if line.strip():
            print('   %s' % line.strip()[:104])
    if disallows_all(rb):
        print('\n   Disallow: / for every agent. This site is not to be '
              'crawled; stopping.')
        return 0

    maps = re.findall(r'(?im)^\s*sitemap:\s*(\S+)', rb)
    if not maps:
        maps = [base + '/sitemap.xml', base + '/sitemap_index.xml']
        print('   (no Sitemap: line; trying the usual two)')

    print('\n--- sitemaps')
    urls, seen, todo = [], set(), list(maps)
    while todo:
        m = todo.pop(0)
        if m in seen or len(seen) > 40:
            continue
        seen.add(m)
        try:
            x = get(m)
        except Exception as e:
            print('   %-58s failed (%s)' % (m[:58], str(e)[:24]))
            continue
        locs = re.findall(r'<loc>\s*([^<\s]+)\s*</loc>', x)
        if '<sitemapindex' in x:
            print('   index %-52s %d' % (m[:52], len(locs)))
            todo.extend(locs)
        else:
            print('   %-58s %d urls' % (m[:58], len(locs)))
            urls.extend(locs)
    print('   %d address(es) in all' % len(urls))

    print('\n--- PDFs')
    pdfs = sorted(set(u for u in urls if u.lower().endswith('.pdf')))
    print('   %d in the sitemaps' % len(pdfs))
    for u in pdfs[:10]:
        print('      %s' % u.replace(base, '')[:94])
    try:
        rows = json.loads(get(base + '/wp-json/wp/v2/media'
                              '?per_page=100&mime_type=application/pdf'))
        print('   media library: %d pdf item(s) on the first page'
              % len(rows))
        for r in rows[:10]:
            print('      %s' % (r.get('source_url') or '')[-86:])
        if len(rows) == 100:
            print('      (a full page - ask for more with &page=2)')
    except Exception as e:
        print('   media library: not available (%s)' % str(e)[:46])

    # What we hold, by address and by year.
    S = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))
    have, held_years = set(), collections.defaultdict(set)
    for s in S['sheets']:
        if s.get('url'):
            u = s['url'].split('#')[0].rstrip('/')
            have.add(u)
            have.add(u.replace('://www.', '://'))
        if s.get('estate') == a.estate and s.get('year'):
            held_years[s.get('wine') or 'grand'].add(int(s['year']))

    by_wine = collections.defaultdict(set)
    missing = collections.defaultdict(set)
    for u in urls:
        m = VINT.search(up.urlsplit(u).path)
        if not m:
            continue
        slug, yr = m.group(1).lower(), int(m.group(2))
        if not (1850 <= yr <= 2030):
            continue
        by_wine[slug].add(yr)
        bare = u.split('#')[0].rstrip('/')
        if bare not in have and bare.replace('://www.', '://') not in have:
            missing[slug].add(yr)

    print('\n--- vintage-shaped addresses the sitemap lists')
    if not by_wine:
        print('   none. This site does not publish a page per vintage, '
              'or does not list them.')
    for slug in sorted(by_wine):
        ys = sorted(by_wine[slug])
        print('   %-46s %3d  %d-%d' % (slug[:46], len(ys), ys[0], ys[-1]))

    print('\n--- of those, no address of ours matches')
    if not missing:
        print('   none: every vintage address the sitemap lists is held')
    for slug in sorted(missing):
        ys = sorted(missing[slug])
        shown = ', '.join(str(y) for y in ys[:a.show])
        more = '' if len(ys) <= a.show else ' ... and %d more' % (
            len(ys) - a.show)
        print('   %-46s %3d  %s%s' % (slug[:46], len(ys), shown, more))
    print('\n   (a mismatch can be the host: the manifest may hold '
          'www. where the sitemap says bare, or the other way round)')

    print('\n--- what the manifest holds for this estate, by wine')
    for w in sorted(held_years):
        ys = sorted(held_years[w])
        print('   %-46s %3d  %d-%d' % (w[:46], len(ys), ys[0], ys[-1]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
