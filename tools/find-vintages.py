# -*- coding: utf-8 -*-
"""How, if at all, does this estate publish its vintages?

    python tools/find-vintages.py --classified
    python tools/find-vintages.py --estate latour --estate palmer
    python tools/find-vintages.py --classified --quiet

Six estates in one day went from "0 candidate pages" to 306
documents, and not one of them needed a new source. They needed a
different question:

    grand-puy-lacoste  the address on file was the owner's
    latour, palmer,    every vintage on one page, behind a fragment
    malescot
    the two Bartons    a page per vintage that nothing links to
    belgrave           downloads built in JavaScript

Each was found by hand. This asks all of it of every estate at once,
and reports the route that works. It writes nothing and fetches
nothing into the archive: the answer is a line saying which of
crawl-pages.py's modes to use, and with what.

THE THREE QUESTIONS, in the order that costs least

  the sitemap        including the one robots.txt declares, which is
                     where Leoville-Barton keeps its. How many of its
                     URLs name a year in the path? That is
                     crawl-pages.py with no argument.

  one page, many     a page whose headings are bare years. Latour's
  vintages           carries 75, Palmer's 56, Malescot's 29. That is
                     --split <url>.

  a pattern          a wine page with a year appended. Leoville-
                     Barton's /en/wines/2/<wine>/2023 is in no
                     sitemap and linked by no href, because the year
                     menu is JavaScript. Two probes settle it. That
                     is --pattern <url with {year}>.

WHAT IT WILL NOT DO

robots.txt is read first and obeyed. An estate that disallows the
path is skipped and said so - Petrus serves "Disallow: /" and is not
to be crawled whatever it holds. The pace is deliberate; this is 61
estates' worth of politeness, not a race.
"""
import argparse
import collections
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import sheetreader as sr

UA = {'User-Agent': 'Mozilla/5.0 (compatible; bordeaux-dashboard/1.0)'}
PAUSE = 0.6
TIMEOUT = 22
LOC = re.compile(r'(?i)<loc>\s*([^<\s]+)\s*</loc>')
ROBOTS_SITEMAP = re.compile(r'(?im)^\s*sitemap\s*:\s*(\S+)')
SITEMAPS = ('/sitemap.xml', '/sitemap_index.xml', '/wp-sitemap.xml',
            '/sitemap.php', '/sitemap_index.xml.gz')
# A year with a month and a day behind it is the day a page was
# published, not the vintage it is about: WordPress writes
# /2021/01/05/the-architecture-of-the-chateau/. Cantenac-Brown's
# sitemap holds 197 of these and 103 real vintage pages, and the
# year in the path tells them apart only if this is asked first.
BLOG_DATE = re.compile(r'/(?:19|20)\d\d/\d{1,2}/\d{1,2}/')

PATH_YEAR = re.compile(r'(?<!\d)(19[5-9]\d|20[0-3]\d)(?!\d)')
YEAR_HEAD = re.compile(
    r'(?is)<h([1-6])[^>]*>\s*((?:18[5-9]\d|19\d\d|20[0-3]\d))\s*</h\1>')
# Pages worth opening when hunting for a vintage list.
LIKELY = re.compile(r'(?i)mill[eé]sim|vintage|vins?|wines?|annee|'
                    r'years|library|cellar|chai')
WINE_PATH = re.compile(r'(?i)/(?:wines?|vins?|produits?|our-wines)/')
SKIP = re.compile(r'(?i)\.(pdf|jpe?g|png|gif|svg|zip|mp4|webp|css|js)$')
# A year a vintage page could plausibly be for, used to test a shape.
PROBE_YEARS = (2022, 2019)


def get(url, limit=500000):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read(limit).decode('utf-8', 'replace')


def root_of(url):
    p = urllib.parse.urlsplit(url)
    return '%s://%s' % (p.scheme or 'https', p.netloc)


def host(u):
    return urllib.parse.urlsplit(u).netloc.lower().replace('www.', '')


def robots(site):
    """(may we crawl, the sitemaps it declares).

    Only the wildcard group is read, and only a bare "Disallow: /" is
    treated as a refusal - a site disallowing /wp-admin/ is not
    refusing us.
    """
    try:
        body = get(root_of(site) + '/robots.txt', 60000)
    except Exception:
        return True, []
    maps = [m.group(1).strip() for m in ROBOTS_SITEMAP.finditer(body)]
    allowed, star = True, False
    for line in body.splitlines():
        line = line.split('#')[0].strip()
        if not line:
            continue
        k, _, v = line.partition(':')
        k, v = k.strip().lower(), v.strip()
        if k == 'user-agent':
            star = (v == '*')
        elif k == 'disallow' and star and v == '/':
            allowed = False
    return allowed, maps


def sitemap_urls(site, maps):
    seen, out = set(), []
    tries = list(maps) + [root_of(site) + p for p in SITEMAPS]
    for u in tries:
        if u in seen:
            continue
        seen.add(u)
        try:
            body = get(u)
        except Exception:
            continue
        locs = LOC.findall(body)
        if not locs:
            continue
        inner = [l for l in locs if l.lower().endswith(('.xml', '.php'))]
        if inner:
            for l in inner[:12]:
                if l in seen:
                    continue
                seen.add(l)
                try:
                    out += LOC.findall(get(l))
                except Exception:
                    pass
            out += [l for l in locs if l not in inner]
        else:
            out += locs
        if out:
            break
        time.sleep(PAUSE)
    return [u for u in dict.fromkeys(out)
            if host(u) == host(site) and not SKIP.search(u)]


# Filler in a URL that identifies no wine.
PATH_FILLER = set("""en fr de es zh hans cn jp us wine wines vin vins
le la les du de des un une the our nos notre chateau domaine clos
grand grands cru crus classe millesime millesimes vintage vintages
produit produits index html php notre-vin nos-vins
year""".split())


def words_of(name):
    """The parts of an estate's name that identify it."""
    out = []
    for w in re.split(r'[^a-z0-9]+', sr.norm(name or '')):
        if w and len(w) > 2 and w not in PATH_FILLER:
            out.append(w)
    return out


def left_over(url, name):
    """The distinctive words a path has beyond the estate's own name.

    chateau-dauzac leaves nothing; bacchus-de-dauzac leaves
    "bacchus"; la-reserve-de-leoville-barton leaves "reserve". No
    list of the estate's other wines is needed, which matters because
    those lists are incomplete - Bacchus is not among Dauzac's.
    """
    mine = set(words_of(name))
    out = []
    # The path only. The host repeats in every candidate for an
    # estate and so separates none of them, and it carries the
    # estate's name in a spelling this would not recognise -
    # chateaudauzac.com, run together.
    path = urllib.parse.urlsplit(url).path
    for w in re.split(r'[^a-z0-9]+', sr.norm(path)):
        if not w or len(w) < 3 or w in PATH_FILLER or w in mine:
            continue
        if w.isdigit():
            continue
        out.append(w)
    return out


def rank_for(urls, name):
    """The estate's own pages first, then its other wines'."""
    return sorted(urls, key=lambda u: (len(left_over(u, name)), len(u)))


def try_split(urls, name=''):
    """The page with the most bare-year headings, if any."""
    best = (0, None)
    # The estate's own pages first: Dauzac's /vins/chateau-dauzac/
    # carries 26 vintages and its Bacchus page carries none, and only
    # the order decided which the sweep found.
    cand = rank_for([u for u in urls if LIKELY.search(u)], name)[:14]
    for u in cand:
        time.sleep(PAUSE)
        try:
            h = get(u)
        except Exception:
            continue
        n = len(set(m.group(2) for m in YEAR_HEAD.finditer(h)))
        if n > best[0]:
            best = (n, u)
    return best


def try_pattern(urls, name=''):
    """A wine page that serves <page>/<year>."""
    # Ranked, so the grand vin's page is probed before the second
    # wine's: Leoville-Barton's /wines/1/ is La Reserve and its
    # /wines/2/ is the chateau.
    wines = rank_for(
        [u for u in urls if WINE_PATH.search(u)
         and not PATH_YEAR.search(urllib.parse.urlsplit(u).path)
         and not BLOG_DATE.search(u)], name)
    for u in wines[:6]:
        # Both years must answer AND differ from each other. A site
        # that serves one page for any trailing path answers every
        # probe: Marquis de Terme gives the same 11,951 characters
        # for 1990 as for 2026, and two identical answers are not
        # evidence of two pages.
        seen = []
        for y in PROBE_YEARS:
            time.sleep(PAUSE)
            try:
                seen.append(hashlib.sha1(
                    get(u.rstrip('/') + '/%d' % y, 120000)
                    .encode('utf-8')).hexdigest())
            except Exception:
                break
        if len(seen) == len(PROBE_YEARS) and len(set(seen)) > 1:
            return u.rstrip('/') + '/{year}'
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estate', action='append', default=[])
    ap.add_argument('--classified', action='store_true')
    ap.add_argument('--quiet', action='store_true',
                    help='only the estates with something to fetch')
    a = ap.parse_args()

    sites = {}
    t = io.open(ROOT + 'data/websites.js', encoding='utf-8').read()
    for m in re.finditer(r"^'([a-z0-9-]+)'\s*:\s*\['([^']*)'", t, re.M):
        sites[m.group(1)] = m.group(2)
    want = sorted(sites)
    if a.classified:
        ch = io.open(ROOT + 'data/chateaux.js', encoding='utf-8').read()
        ids = set(re.findall(r"id:'([a-z0-9-]+)'", ch))
        want = [e for e in want if e in ids]
    if a.estate:
        want = [e for e in want if e in a.estate]

    E = sr.estates(ROOT)
    man = json.load(io.open(ROOT + 'data/sources.json',
                            encoding='utf-8'))
    held = collections.Counter(s.get('estate') for s in man['sheets'])
    pages = collections.Counter(
        s.get('estate') for s in man['sheets']
        if (s.get('folder') or '').startswith('pages/'))

    print('asking %d estate(s) how they publish their vintages'
          % len(want))
    found = []
    for i, eid in enumerate(want, 1):
        site = sites[eid]
        name = (E.get(eid) or {}).get('name') or eid
        time.sleep(PAUSE)
        ok, maps = robots(site)
        if not ok:
            found.append((eid, 'refuses crawling', site, 0, ''))
            continue
        try:
            urls = sitemap_urls(site, maps)
        except Exception:
            urls = []
        yr = [u for u in urls
              if PATH_YEAR.search(urllib.parse.urlsplit(u).path)
              and not BLOG_DATE.search(urllib.parse.urlsplit(u).path)]
        if yr:
            found.append((eid, 'sitemap', site, len(yr), ''))
        else:
            n, where = try_split(urls, name)
            if n >= 5:
                found.append((eid, 'split', site, n, where))
            else:
                pat = try_pattern(urls, name)
                if pat:
                    found.append((eid, 'pattern', site, 0, pat))
                else:
                    found.append((eid, 'nothing found', site,
                                  len(urls), ''))
        print('   %2d/%d %-24s %s' % (i, len(want), eid[:24],
                                      found[-1][1]))

    print()
    print('HOW EACH ESTATE PUBLISHES ITS VINTAGES')
    by = collections.Counter(r[1] for r in found)
    for k, c in by.most_common():
        print('   %-18s %3d' % (k, c))
    for kind, how in (('split', '--split <url>'),
                      ('pattern', '--pattern <url>'),
                      ('sitemap', 'no argument')):
        rows = [r for r in found if r[1] == kind]
        if not rows:
            continue
        print()
        print('   %s   (crawl-pages.py %s)' % (kind.upper(), how))
        rows.sort(key=lambda r: (pages.get(r[0], 0), -r[3]))
        for eid, _, site, n, where in rows:
            # Say which wine the route was found on. Ranking puts the
            # grand vin first where both exist, but where only another
            # wine has vintage pages - as with Dauzac's Bacchus, found
            # because no chateau-dauzac page was among the candidates -
            # the route is still the wrong one to crawl, and the report
            # is the only place that can say so before somebody does.
            others = left_over(where or site,
                               (E.get(eid) or {}).get('name') or eid)
            print('      %-24s %3d doc(s), %3d page(s) held  %s%s%s'
                  % (eid[:24], held.get(eid, 0), pages.get(eid, 0),
                     ('%d vintages  ' % n) if n else '',
                     (where or site)[:62],
                     ('   <- another wine: %s' % ', '.join(others))
                     if others else ''))
    if not a.quiet:
        rest = [r for r in found if r[1] in ('nothing found',
                                             'refuses crawling')]
        print()
        print('   NOTHING FOUND OR REFUSED - %d' % len(rest))
        for eid, kind, site, n, _ in rest:
            print('      %-24s %-18s %3d sitemap url(s)  %s'
                  % (eid[:24], kind, n, site[:44]))


if __name__ == '__main__':
    main()
