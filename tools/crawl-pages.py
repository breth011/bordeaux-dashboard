# -*- coding: utf-8 -*-
"""Fetch the vintage pages an estate publishes instead of a fiche.

    python tools/crawl-pages.py --estate latour
    python tools/crawl-pages.py --estate latour --apply
    python tools/crawl-pages.py --estate latour --seed <url> --apply

Some estates publish no technical sheet at all. Chateau Margaux has
never issued one and Chateau Latour does not either; what they publish
is a page per vintage, in sentences, and everything the dashboard shows
for Margaux - its blends among them - was read out of those pages.

sources/pages holds 1,673 of them for 58 estates and until now no
committed tool fetched any. harvest.py finds documents: the media
library, the sitemap, hrefs ending .pdf. The pages arrived some other
way and the archive could not be rebuilt, which is the one thing
harvest.py's own docstring says the manifest exists to guarantee. So
this is the missing half.

How it finds them. The sitemap first, because an estate that publishes
a page per vintage lists them all there, and then the links on a seed
page for a site whose sitemap is missing or useless. Only URLs on the
estate's own host, and only those whose path names a year: this tool
is for vintage pages, and a site's news and shop are somebody else's
problem.

What it writes, in the format the readers already expect:

    sources/pages/<estate>/<year>__<slug>.txt

with the address on the first line, the page title on the second, a
blank third, and the text after it a paragraph to a line. page_url()
reads that first line, and the guards depend on it - a page's filename
is the only thing that says whose wine it is.

Which is why the slug keeps its head. The pages already in the archive
were named by something that truncated long names from the front, so
`rose-x-giscours-2020` arrived as `se-x-giscours-2020` and
`produit-...` as `duit-...`; every guard that reads a name was blinded,
and the fix was to hand them the URL as well. Here the tail is dropped
instead, so the estate's name and the wine's survive.

The year comes from the page and not from a guess. The path first,
where a vintage page almost always names it, then the title, then a
millesime the text declares - and the row records which, because
harvest.py learnt the hard way that filenames lie.

Report only unless --apply. Nothing is fetched without it: this talks
to somebody else's server.
"""
import argparse
import collections
import hashlib
import html
import importlib.util
import io
import json
import os
import re
import sys
import time
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, ROOT + 'tools')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import sheetreader as sr

DEST = ROOT + 'sources/pages/'
MANIFEST = ROOT + 'data/sources.json'
# Where a sitemap usually is.
# Where a site says its sitemap is. Asked before the guesses below,
# because a site that bothers to say is telling the truth and the
# guesses are only for those that do not: Leoville-Barton's is at
# /sitemap.php, which no list of likely names would have reached.
ROBOTS_SITEMAP = re.compile(r'(?im)^\s*sitemap\s*:\s*(\S+)')

SITEMAPS = ('/sitemap.xml', '/sitemap_index.xml', '/wp-sitemap.xml',
            '/sitemap-index.xml', '/page-sitemap.xml')
# A year in a URL path. Not 19xx below 1900 or beyond next year's
# vintage, because a page numbered 2050 is not a wine.
# A year with a month and a day behind it is the day a page was
# published, not the vintage it is about: WordPress writes
# /2021/01/05/the-architecture-of-the-chateau/. Cantenac-Brown's
# sitemap holds 197 of these and 103 real vintage pages, and the
# year in the path tells them apart only if this is asked first.
BLOG_DATE = re.compile(r'/(?:19|20)\d\d/\d{1,2}/\d{1,2}/')

PATH_YEAR = re.compile(r'(?<!\d)(18[5-9]\d|19\d\d|20[0-3]\d)(?!\d)')
# A vintage the page declares, for a path that names none.
SAYS_YEAR = re.compile(r'(?i)(?:mill[eé]sime|vintage)\s*:?\s*'
                       r'((?:18|19|20)\d\d)(?!\d)')
# Blocks whose text is never the wine's.
CUT_BLOCK = re.compile(
    r'(?is)<(script|style|noscript|svg|head|nav|footer|form|select)\b'
    r'.*?</\1\s*>')
# Tags that end a line.
BREAKS = re.compile(r'(?i)</?(p|br|div|li|tr|h[1-6]|section|article|'
                    r'blockquote|td)\b[^>]*>')
TAG = re.compile(r'(?s)<[^>]+>')
TITLE = re.compile(r'(?is)<title[^>]*>(.*?)</title>')
HREF = re.compile(r'(?i)href\s*=\s*["\']([^"\'#]+)')
LOC = re.compile(r'(?i)<loc>\s*([^<\s]+)\s*</loc>')
# How long a slug may be. Long enough for an estate's name and a
# wine's, short enough to leave room for the year and the extension.
SLUG = 120
# A heading whose whole text is a year, which is how a page that
# carries every vintage separates them. Latour writes <h5>1961</h5>,
# 75 times, each over its own description and weather notes.
#
# The closing tag must match the opening one, so a stray <h2>2019
# inside a paragraph cannot open a block that never closes.
YEAR_HEAD = re.compile(
    r'(?is)<h([1-6])[^>]*>\s*((?:18[5-9]\d|19\d\d|20[0-3]\d))\s*</h\1>')
# A block has to say something. A page whose years are only a
# navigation strip yields headings with nothing behind them, and an
# empty vintage is worse than an absent one - it looks like a record.
SPLIT_FLOOR = 200
# And so does a page fetched by any other route. Cantenac-Brown's
# vintage pages are 90 to 174 bytes of address and title, their text
# built in JavaScript, and 102 of them were registered as documents -
# inflating every count of what is held and costing a read each time
# to learn nothing. Lower than SPLIT_FLOOR because a real page can be
# short; a shell has nothing at all.
PAGE_FLOOR = 120
# One request a second. This is somebody else's server.
PAUSE = 1.0


def websites():
    """Each estate's address, read the way harvest.py reads it."""
    t = io.open(ROOT + 'data/websites.js', encoding='utf-8').read()
    return dict((m.group(1), m.group(2)) for m in re.finditer(
        r"^'([a-z0-9-]+)':\['([^']+)'", t, re.M))


def host_of(url):
    """A host to compare, without the www that is not part of it."""
    h = urllib.parse.urlsplit(url or '').netloc.lower()
    return h[4:] if h.startswith('www.') else h


def same_host(a, b):
    """Are these the same site?

    data/websites.js has Margaux at www.chateau-margaux.com and its
    sitemap lists every page at chateau-margaux.com. Compared exactly,
    all 726 were thrown away.
    """
    return host_of(a) == host_of(b)


def body_of(get, url):
    """Just the text of a page.

    harvest.get returns (body, final address, content-disposition).
    """
    return get(url)[0]


def read_page(get, url):
    """The text, and the address it was actually served from.

    A page fetched at one URL and delivered from another belongs to
    the second: that is the address page_url() hands the guards.
    """
    body, final, _ = get(url)
    return body, (final or url)


def harvest():
    """harvest.py, for its fetcher and its user agent."""
    spec = importlib.util.spec_from_file_location(
        'harvest_mod', ROOT + 'tools/harvest.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def to_text(body):
    """The page's readable text, a paragraph to a line.

    Regex and not a parser because this repo has no bs4 and the shape
    wanted is coarse: the furniture out, the block tags turned into
    line breaks, the entities undone.
    """
    body = CUT_BLOCK.sub(' ', body)
    body = BREAKS.sub('\n', body)
    body = TAG.sub(' ', body)
    body = html.unescape(body)
    out = []
    for line in body.split('\n'):
        line = ' '.join(line.split())
        if line:
            out.append(line)
    return out


def page_title(body):
    m = TITLE.search(body)
    if not m:
        return ''
    return ' '.join(html.unescape(TAG.sub(' ', m.group(1))).split())


def slug_of(url):
    """The filename's stem: the URL's path, hyphenated.

    Truncated at the tail and never at the head. The pages already in
    the archive were cut from the front - `rose-x-giscours-2020` became
    `se-x-giscours-2020` - and a name with its head missing tells the
    guards nothing about whose wine it is.
    """
    path = urllib.parse.urlsplit(url).path
    s = re.sub(r'[^A-Za-z0-9]+', '-', path).strip('-').lower()
    return s[:SLUG].rstrip('-') or 'page'


def year_of(url, title, text):
    """The vintage this page is for, and where it was read.

    The path, then the title, then a millesime the text declares.
    Returns (year, how) or (None, why not).
    """
    hits = PATH_YEAR.findall(urllib.parse.urlsplit(url).path)
    if hits:
        return int(hits[-1]), 'from the name of the page'
    hits = PATH_YEAR.findall(title or '')
    if hits:
        return int(hits[-1]), 'from the title of the page'
    m = SAYS_YEAR.search('\n'.join(text[:12]))
    if m:
        return int(m.group(1)), 'the page declares the vintage'
    return None, 'nothing on the page states a vintage'


def pattern_urls(get, pattern, years):
    """Every year in the range whose page the server actually serves.

    For a site that links its vintages in JavaScript, so there is no
    href to follow and no sitemap entry to read. The shape comes from
    a person who has seen one of the pages; the server decides each
    case, and a 404 simply means that year has none.
    """
    lo, _, hi = years.partition('-')
    lo, hi = int(lo), int(hi or lo)
    out, miss, seen = [], 0, {}
    for y in range(hi, lo - 1, -1):
        u = pattern.replace('{year}', str(y))
        try:
            body = body_of(get, u)
        except Exception:
            miss += 1
            # Long enough to cross a gap of unmade vintages - 1991,
            # 1992 and 1993 together, say - and short enough not to
            # walk the whole range for a site that has none.
            if miss >= 12:
                break
            continue
        miss = 0
        # The same page for every year is a catch-all, not a page per
        # vintage. Marquis de Terme answers /en/wines/<anything> with
        # its wines page - 37 identical answers over 1990 to 2026 -
        # and fetching them would have registered one page as 37
        # vintages, which is worse than finding nothing: the manifest
        # would then say the estate publishes per vintage and nobody
        # would look again.
        sig = hashlib.sha1(
            ' '.join(to_text(body)).encode('utf-8')).hexdigest()
        if sig in seen:
            print('   the same page answers for %d as for %d; this is '
                  'a catch-all, not a page per vintage'
                  % (y, seen[sig]))
            return []
        seen[sig] = y
        out.append(u)
    return out


def declared_sitemaps(get, site):
    """The sitemap addresses robots.txt gives, if any."""
    root = '%s://%s' % (urllib.parse.urlsplit(site).scheme or 'https',
                        urllib.parse.urlsplit(site).netloc)
    try:
        body = body_of(get, root + '/robots.txt')
    except Exception:
        return []
    out = []
    for m in ROBOTS_SITEMAP.finditer(body or ''):
        u = m.group(1).strip()
        if u and same_host(u, site) and u not in out:
            out.append(u)
    return out


def sitemap_urls(get, site, seen=None, depth=0):
    """Every URL a site's sitemaps list, following indexes once."""
    out, seen = [], seen if seen is not None else set()
    # What robots.txt declares first, then the usual names. A site
    # that says where its sitemap is has been asked and answered;
    # the guesses are for those that say nothing.
    tries = list(SITEMAPS)
    if depth == 0:
        tries = declared_sitemaps(get, site) + tries
    for path in (tries if depth == 0 else ('',)):
        u = (path if path.startswith('http')
             else urllib.parse.urljoin(site, path)) if path else site
        if u in seen:
            continue
        seen.add(u)
        try:
            body = body_of(get, u)
        except Exception:
            continue
        locs = LOC.findall(body)
        if not locs:
            continue
        # An index of sitemaps, or a list of pages.
        inner = [l for l in locs if l.lower().endswith('.xml')]
        if inner and depth < 2:
            for l in inner[:40]:
                out += sitemap_urls(get, l, seen, depth + 1)
            out += [l for l in locs if l not in inner]
        else:
            out += locs
        if depth == 0 and out:
            break
    return out


def seed_urls(get, seed):
    """The links a listing page offers, on its own host."""
    try:
        body = body_of(get, seed)
    except Exception as e:
        print('   the seed page could not be read: %s' % str(e)[:60])
        return []
    out = []
    for h in HREF.findall(body):
        u = urllib.parse.urljoin(seed, h)
        if same_host(u, seed):
            out.append(u)
    return out


def take_estate_page(get, man, e, eid, url, held_url, held_sha,
                     apply):
    """One page about the estate, carrying no vintage.

    Registered with year None, because that is what it says. The
    vintage readers key on the year and pass over it; read-terroir.py
    and read-plantings.py read by estate and do not need one.
    """
    try:
        body, url = read_page(get, url)
    except Exception as ex:
        print('   could not fetch %s: %s' % (url[:60], str(ex)[:40]))
        return 0
    title = page_title(body)
    text = to_text(body)
    n = sum(len(l) for l in text)
    print('   %s — %d character(s) of text' % (title[:50], n))
    if n < SPLIT_FLOOR:
        print('   too thin to be an estate page')
        return 0
    if url in held_url:
        print('   already held')
        return 0
    blob = '\n'.join([url, title, ''] + [' ' + l for l in text])
    data = blob.encode('utf-8')
    sha = hashlib.sha1(data).hexdigest()
    if sha in held_sha:
        print('   already held under another name')
        return 0
    says = [w for w in ('appellation', 'terroir', 'encépagement',
                        'encepagement', 'superficie', 'vinification')
            if re.search(r'(?i)' + w, ' '.join(text))]
    print('   names: %s' % (', '.join(says) or 'none of the usual'))
    if not apply:
        print('   would take it as an estate page, no vintage')
        return 1
    folder = DEST + eid + '/'
    if not os.path.isdir(folder):
        os.makedirs(folder)
    # Named without a year, because it has none and a filename that
    # implied one would be read as a claim.
    name = 'estate__%s.txt' % slug_of(url)
    io.open(folder + name, 'w', encoding='utf-8',
            newline='').write(blob)
    man['sheets'].append({
        'file': name, 'folder': 'pages/' + eid,
        'estate': eid, 'estateName': e.get('name'),
        'wine': None, 'role': 'page', 'colour': None,
        'year': None, 'bytes': len(data), 'sha1': sha,
        'url': url,
        'how': 'an estate page, naming no vintage',
    })
    held_sha.add(sha)
    held_url.add(url)
    print('   took %s' % name)
    return 1


def split_one(get, man, e, eid, url, held_url, held_sha, apply):
    """Cut one page into a record per vintage, at its year headings.

    Returns nothing; it prints what it did and appends to the
    manifest, which main() writes once at the end.
    """
    try:
        body, url = read_page(get, url)
    except Exception as ex:
        print('   could not fetch %s: %s' % (url[:60], str(ex)[:40]))
        return 0
    title = page_title(body)
    heads = list(YEAR_HEAD.finditer(body))
    print('   %d year heading(s) on %s' % (len(heads), url[:66]))
    if not heads:
        print('   nothing to split; this page does not head its '
              'vintages with a year')
        return 0

    folder = DEST + eid + '/'
    added, thin, dup = 0, 0, 0
    for i, m in enumerate(heads):
        yr = int(m.group(2))
        end = heads[i + 1].start() if i + 1 < len(heads) else len(body)
        text = to_text(body[m.end():end])
        if sum(len(l) for l in text) < SPLIT_FLOOR:
            thin += 1
            continue
        at = '%s#%d' % (url, yr)
        if at in held_url:
            dup += 1
            continue
        blob = '\n'.join([at, '%s %d' % (title, yr), '']
                          + [' ' + l for l in text])
        data = blob.encode('utf-8')
        sha = hashlib.sha1(data).hexdigest()
        if sha in held_sha:
            dup += 1
            continue
        if not apply:
            if added < 8:
                print('      %-5s %s' % (yr, ' '.join(
                    ' '.join(text).split())[:74]))
            added += 1
            continue
        if not os.path.isdir(folder):
            os.makedirs(folder)
        # Named for the estate and the page, not for the route.
        # slug_of() would give "en-a-time-for-sharing-vintages",
        # whose "for" the filename guards read as "Forts" - Les
        # Forts de Latour - and refuse all 75 of them. See the
        # note above the function.
        tail = [p for p in urllib.parse.urlsplit(url).path.split('/')
                if p]
        name = '%d__%s.txt' % (
            yr, slug_of('/%s/%s' % (eid, tail[-1] if tail else 'page')))
        io.open(folder + name, 'w', encoding='utf-8',
                newline='').write(blob)
        man['sheets'].append({
            'file': name, 'folder': 'pages/' + eid,
            'estate': eid, 'estateName': e.get('name'),
            'wine': None, 'role': 'page', 'colour': None,
            'year': yr, 'bytes': len(data), 'sha1': sha,
            'url': at,
            'how': 'a year heading on a page carrying every vintage',
        })
        held_sha.add(sha)
        held_url.add(at)
        added += 1
        print('   %-5s %-46s' % (yr, name[:46]))
    print('   %d vintage(s)%s, %d too thin to be one, %d already held'
          % (added, '' if apply else ' it would take', thin, dup))
    return added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estate', action='append', default=[],
                    help='the estate id, as chateaux.js spells it')
    ap.add_argument('--seed', default=None,
                    help='a listing page to take links from')
    ap.add_argument('--pattern', default=None,
                    help='a vintage address with {year} in it, for a '
                         'site that links its years in JavaScript')
    ap.add_argument('--years', default='1980-2026',
                    help='the range --pattern walks (default '
                         '1980-2026)')
    ap.add_argument('--page', default=None,
                    help='one page about the estate, naming no '
                         'vintage: terroir, planting, appellation')
    ap.add_argument('--split', default=None,
                    help='one page carrying every vintage, to be cut '
                         'into one record each at its year headings')
    ap.add_argument('--apply', action='store_true',
                    help='fetch the pages and register them')
    ap.add_argument('--limit', type=int, default=120,
                    help='at most this many pages (default 120)')
    a = ap.parse_args()
    if not a.estate:
        ap.error('--estate is required: this talks to one estate\'s site')

    E = sr.estates(ROOT)
    sites = websites()
    man = json.load(io.open(MANIFEST, encoding='utf-8'))
    held_url = set(s.get('url') for s in man['sheets'] if s.get('url'))
    held_sha = set(s.get('sha1') for s in man['sheets'] if s.get('sha1'))
    h = harvest()
    get = h.get
    started = len(man['sheets'])

    added = 0
    for eid in a.estate:
        e = E.get(eid)
        if not e:
            print('%s: no such estate in chateaux.js' % eid)
            continue
        site = sites.get(eid)
        print('%s — %s' % (eid, site or 'no website on record'))

        if a.pattern:
            found = pattern_urls(get, a.pattern, a.years)
            print('   %d page(s) answered' % len(found))
        elif a.page:
            take_estate_page(get, man, e, eid, a.page, held_url,
                             held_sha, a.apply)
            continue

        if a.split:
            split_one(get, man, e, eid, a.split, held_url, held_sha,
                      a.apply)
            continue

        if a.pattern:
            pass
        elif a.seed:
            found = seed_urls(get, a.seed)
            print('   %d link(s) on the seed page' % len(found))
        if not a.pattern and not a.seed and site:
            found = sitemap_urls(get, site)
            print('   %d URL(s) in the sitemap' % len(found))
        if not found:
            print('   nothing to look at; pass --seed <url>')
            continue

        home = site or a.seed
        want, why = [], collections.Counter()
        for u in dict.fromkeys(found):
            if not same_host(u, home):
                why['on another host'] += 1
                continue
            if re.search(r'(?i)\.(pdf|jpe?g|png|gif|svg|zip|mp4)$', u):
                why['not a page'] += 1
                continue
            path = urllib.parse.urlsplit(u).path
            if BLOG_DATE.search(path):
                why['the path names a publication date'] += 1
                continue
            if not PATH_YEAR.search(path):
                why['the path names no vintage'] += 1
                continue
            if u in held_url:
                why['already held'] += 1
                continue
            want.append(u)
        print('   %d candidate page(s)' % len(want))
        for k, n in why.most_common():
            print('      %-36s %4d' % (k, n))
        if len(want) > a.limit:
            print('      (taking the first %d)' % a.limit)
            want = want[:a.limit]

        if not a.apply:
            for u in want[:12]:
                yr = PATH_YEAR.findall(urllib.parse.urlsplit(u).path)
                print('      %-5s %s' % (yr[-1] if yr else '?', u[:88]))
            if len(want) > 12:
                print('      ... and %d more' % (len(want) - 12))
            continue

        folder = DEST + eid + '/'
        if not os.path.isdir(folder):
            os.makedirs(folder)
        for u in want:
            time.sleep(PAUSE)
            try:
                body, u = read_page(get, u)
            except Exception as ex:
                print('   could not fetch %s: %s' % (u[:60],
                                                     str(ex)[:40]))
                continue
            title = page_title(body)
            text = to_text(body)
            if sum(len(l) for l in text) < PAGE_FLOOR:
                print('   no text on the page, built in JavaScript? '
                      '%s' % u[:56])
                continue
            yr, how = year_of(u, title, text)
            if yr is None:
                print('   skipped, %s: %s' % (how, u[:62]))
                continue
            blob = '\n'.join([u, title, ''] + [' ' + l for l in text])
            data = blob.encode('utf-8')
            sha = hashlib.sha1(data).hexdigest()
            if sha in held_sha:
                print('   already held under another name: %s' % u[:58])
                continue
            name = '%d__%s.txt' % (yr, slug_of(u))
            io.open(folder + name, 'w', encoding='utf-8',
                    newline='').write(blob)
            man['sheets'].append({
                'file': name, 'folder': 'pages/' + eid,
                'estate': eid, 'estateName': e.get('name'),
                'wine': None, 'role': 'page', 'colour': None,
                'year': yr, 'bytes': len(data), 'sha1': sha,
                'url': u, 'how': how,
            })
            held_sha.add(sha)
            held_url.add(u)
            added += 1
            print('   %-5s %-44s %s' % (yr, name[:44], how))

    if (a.split or a.page) and a.apply:
        # split_one appended as it went, and counts its own work.
        added = max(added, len(man['sheets']) - started)
    if not a.apply:
        print()
        print('nothing fetched; pass --apply to fetch and register')
        return
    if not added:
        print()
        print('nothing new')
        return
    io.open(MANIFEST, 'w', encoding='utf-8', newline='').write(
        json.dumps(man, ensure_ascii=False, indent=1))
    print()
    print('%d page(s) registered in data/sources.json' % added)
    print('now run: python tools/read-fiches.py --estate <each> --prose')


if __name__ == '__main__':
    main()
