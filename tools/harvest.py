# -*- coding: utf-8 -*-
"""Find the technical sheets an estate publishes, and fetch the new ones.

    python tools/harvest.py                     every estate with a site
    python tools/harvest.py --estate margaux    one estate
    python tools/harvest.py --year 2026         only sheets naming that year
    python tools/harvest.py --dry-run           list what it would fetch

This is the step that has to be repeatable, because next year the job
is one new vintage across four hundred estates and nothing else. It
discovers, it skips anything already held, and it records where each
file came from so that the answer survives this session.

Three ways of discovering sheets, tried in order, because they find
different things:

  the media library   /wp-json/wp/v2/media lists every upload a
                      WordPress site holds. It answers for files no
                      page links to, which is most of the archive.
  the sitemap         where the media API is missing or incomplete.
                      bordeaux-tradition.com lists 83 files in its
                      media library and 6,227 in propriete-sitemap.xml,
                      so the sitemap is not a fallback - it is often
                      the better source.
  the pages           hrefs ending .pdf on the site's own pages, for
                      sites that are neither.

What it will not do is guess. A file is registered with the address it
came from and the method that found it, and the vintage is read from
the document rather than from the filename, because filenames lie:
vin.co names a sheet by the year in the URL and serves another year's
code, and Dourthe truncates the estate's name to an ellipsis.

Downloads land in sources/, which is not committed - this repo is
served by GitHub Pages, so anything in it goes live, and none of this
material is ours to republish. The manifest is what is committed, and
the manifest plus this tool is what makes the archive reproducible.
"""
import io, json, os, re, sys, time, hashlib, argparse, collections
import urllib.parse, urllib.request, urllib.error
import xml.etree.ElementTree as ET
import concurrent.futures as cf

# A URL can carry an accent, and this console is cp1252: printing
# one killed a 61-estate run at Calon-Segur, after the work and
# before the report. Every other tool here already does this.
import sys as _sys
_sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
DEST = ROOT + 'sources/fiches/'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/127.0 Safari/537.36')
PAUSE = 0.3          # between requests to one host
TIMEOUT = 45
MEDIA_PAGES = 12     # 100 per page; beyond this a site wants its sitemap
SHEETY = re.compile(r'(?i)(fiche|tech|technical|assemblage|millesime|'
                    r'millésime|vintage|primeur|ft[-_])')


def safe_url(u):
    """An address urllib will accept, from one a web page gave us.

    A full harvest lost 223 sheets to "'ascii' codec can't encode
    character" and 21 more to "URL can't contain control characters".
    Both are urllib refusing the address rather than the server
    refusing the request: a French site is perfectly entitled to call a
    file Fiche-technique-Château.pdf, and a hand-written href is
    perfectly capable of containing a stray newline. Percent-encoding
    the path and dropping control characters costs nothing and those
    244 sheets are real.
    """
    u = ''.join(c for c in (u or '') if ord(c) >= 32 and ord(c) != 127)
    p = urllib.parse.urlsplit(u.strip())
    host = p.netloc
    if any(ord(c) > 127 for c in host):
        try:
            host = host.encode('idna').decode('ascii')
        except Exception:
            pass
    return urllib.parse.urlunsplit((
        p.scheme, host,
        urllib.parse.quote(p.path, safe="/%~"),
        urllib.parse.quote(p.query, safe="=&%?+,:/~"),
        ''))


def get(url, binary=False, limit=20 * 1024 * 1024):
    req = urllib.request.Request(safe_url(url), headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        blob = r.read(limit)
        final = r.geturl()
        disp = r.headers.get('Content-Disposition') or ''
    time.sleep(PAUSE)
    return (blob if binary else blob.decode('utf-8', 'replace')), final, disp


def media_library(site):
    """Every PDF WordPress will admit to holding."""
    out = []
    for page in range(1, MEDIA_PAGES + 1):
        u = (site.rstrip('/') + '/wp-json/wp/v2/media?per_page=100&page=%d'
             % page)
        try:
            body, _, _ = get(u)
            rows = json.loads(body)
        except Exception:
            break
        if not isinstance(rows, list) or not rows:
            break
        for r in rows:
            src = (r or {}).get('source_url') or ''
            if src.lower().endswith('.pdf'):
                # Joined against the site, because 59 of these came back
                # as "/wp-content/uploads/2…" with no host and urllib
                # answered "unknown url type". A media library is
                # supposed to give absolute addresses; some do not.
                out.append(urllib.parse.urljoin(site.rstrip('/') + '/',
                                                src))
        if len(rows) < 100:
            break
    return out


def sitemaps(site):
    """The sitemap, and every sitemap it points at."""
    seen, urls, queue = set(), [], []
    for name in ('/wp-sitemap.xml', '/sitemap_index.xml', '/sitemap.xml'):
        queue.append(site.rstrip('/') + name)
    while queue:
        u = queue.pop(0)
        if u in seen or len(seen) > 60:
            continue
        seen.add(u)
        try:
            body, _, _ = get(u)
            root = ET.fromstring(body.encode('utf-8', 'replace'))
        except Exception:
            continue
        for el in root.iter():
            if not el.tag.endswith('loc') or not (el.text or '').strip():
                continue
            loc = el.text.strip()
            if loc.lower().endswith('.pdf'):
                urls.append(urllib.parse.urljoin(u, loc))
            elif loc.lower().endswith(('.xml', '.xml.gz')):
                queue.append(loc)
    return urls


# A share link out of Nextcloud or ownCloud: /s/ and then the token,
# and nothing after it. Haut-Batailley serves every sheet it has this
# way, from toolbox.hautbatailley.com, and not one of the seventeen
# addresses ends in .pdf - so a harvest that looked for .pdf found the
# estate had published nothing, when it had published seven vintages of
# the grand vin and eight of Verso.
#
# The pattern is kept this tight on purpose. Collecting every href that
# is not a .pdf would drag in the whole site; "any long word that is not
# this estate's" is the tempting general rule that threw away 59 sheets
# the last time it was tried. This matches a file-share address and
# nothing else, and fetch() still throws away anything that does not
# begin %PDF - which is how the toolbox's .zip and its one HTML page
# drop out without being named here.
# Not looked for inside href= either, because this site does not put
# them there: the page is a rendered layout and each address arrives as
# "link":{"B":"https://toolbox.../s/7Tc24kMeRzGZK73"} inside the JSON
# that draws it. A share address is distinctive enough to find loose in
# the body - host, /s/, token, end.
#
# Two things the first version of this got wrong, both found by running
# it over all 408 estates that have a site:
#
#   It truncated a filename into a token. lauga.com serves its sheets
#   from /s/, so "https://lauga.com/s/Fiche-technique-LAUGA-FR.pdf"
#   matched as far as "...LAUGA-FR" and became a request for
#   ".../LAUGA-FR/download", which is nothing. Hence (?![\w.-]): a
#   Nextcloud token has no dot after it, a filename does.
#
#   It required a scheme, so a relative share link - which is how
#   Nextcloud writes its own, href="/index.php/s/<token>" - was missed
#   altogether. The scheme is optional now and urljoin fills it in.
SHARE = re.compile(r'''(?<![\w/])((?:https?://[^\s"'<>\\]+?)?/'''
                   r'''(?:index\.php/)?s/[A-Za-z0-9_-]{10,})(?![\w.-])''')


def pages(site):
    """hrefs ending .pdf, and file-share links, from the obvious few."""
    out, base = [], site.rstrip('/')
    # /en and /fr because a site that serves its English pages under a
    # language prefix answers the bare path with a shell holding no
    # links at all, which is what hautbatailley.com does.
    for path in ('', '/en', '/fr', '/fiches-techniques', '/technical-sheets',
                 '/vins', '/the-wines', '/nos-vins', '/presse', '/press'):
        try:
            body, final, _ = get(base + path)
        except Exception:
            continue
        for href in re.findall(r'''href=["']([^"']+\.pdf[^"']*)["']''', body):
            out.append(urllib.parse.urljoin(final, href))
        for href in SHARE.findall(body):
            out.append(urllib.parse.urljoin(final, href.rstrip('/')
                                            + '/download'))
    return out


METHODS = [
    ('from the site’s own media library', media_library),
    ('from the estate’s own sitemap', sitemaps),
    ('from a link on the estate’s own pages', pages),
]

YEAR = re.compile(r'(?<!\d)(19[89]\d|20[0-4]\d)(?!\d)')
LABEL = re.compile(r'(?i)mill[eé]sime\s*:?\s*(19[89]\d|20[0-4]\d)')
VINTAGE = re.compile(r'(?i)vintage\s*:?\s*(19[89]\d|20[0-4]\d)')


def vintage_of(text):
    """The year the document states, before the year anyone guessed."""
    for rx, how in ((LABEL, 'the millésime label'),
                    (VINTAGE, 'the vintage label')):
        m = rx.search(text)
        if m:
            return int(m.group(1)), how
    years = YEAR.findall(text[:3000])
    if years:
        y, n = collections.Counter(years).most_common(1)[0]
        if n >= 2:
            return int(y), 'the commonest year on the page'
    return None, 'no vintage in the document'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estate', action='append', default=[])
    ap.add_argument('--year', type=int)
    ap.add_argument('--dry-run', action='store_true')
    # Accepted and ignored: four of this repo's six tools are dry
    # until told otherwise and spell it --apply, and this one
    # acts unless told --dry-run. Passing the habit from the
    # majority should not kill a run on an argument.
    ap.add_argument('--apply', action='store_true',
                    help=argparse.SUPPRESS)
    ap.add_argument('--workers', type=int, default=4)
    a = ap.parse_args()

    t = io.open(ROOT + 'data/websites.js', encoding='utf-8').read()
    sites = dict((m.group(1), m.group(2)) for m in re.finditer(
        r"^'([a-z0-9-]+)':\['([^']+)'", t, re.M))
    if a.estate:
        sites = dict((k, v) for k, v in sites.items() if k in a.estate)
        for e in a.estate:
            if e not in sites:
                print('%s: no site in data/websites.js' % e)
    print('%d estates with a site' % len(sites))

    man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))
    have_sha = set(s['sha1'] for s in man['sheets'] if s.get('sha1'))
    have_url = set(s['url'] for s in man['sheets'] if s.get('url'))
    names = {}
    for f in ('chateaux.js', 'crubourgeois.js', 'cruartisan.js', 'graves.js',
              'sauternes.js', 'saintemilion.js', 'pomerol.js', 'rightbank.js',
              'libournais.js'):
        p = ROOT + 'data/' + f
        if os.path.exists(p):
            s = io.open(p, encoding='utf-8').read()
            for m in re.finditer(r"id:'([a-z0-9-]+)',\s*name:'([^']+)'", s):
                names.setdefault(m.group(1), m.group(2))

    def discover(item):
        eid, site = item
        found, how_of = [], {}
        for how, fn in METHODS:
            try:
                urls = fn(site)
            except Exception:
                urls = []
            for u in urls:
                if u not in how_of:
                    how_of[u] = how
                    found.append(u)
        # Every method, not the first one that answers. Stopping early
        # is the mistake the sitemap exists to correct:
        # bordeaux-tradition.com lists 83 files in its media library and
        # 6,227 in propriete-sitemap.xml, and a run that took the media
        # library's answer as the answer would have missed the lot. It
        # costs a few more requests once a year.
        return eid, found, how_of

    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        results = list(ex.map(discover, sorted(sites.items())))

    todo = []
    for eid, found, how_of in results:
        for u in found:
            if u in have_url:
                continue
            base = urllib.parse.unquote(u.rsplit('/', 1)[-1])
            if a.year and str(a.year) not in base and not SHEETY.search(base):
                continue
            todo.append((eid, u, how_of[u]))
    print('%d addresses not already in the manifest' % len(todo))
    if a.dry_run:
        for eid, u, how in todo[:60]:
            print('   %-28s %s' % (eid[:28], u[:110]))
        if len(todo) > 60:
            print('   ... and %d more' % (len(todo) - 60))
        return 0

    try:
        import pymupdf
    except ImportError:
        print('pymupdf is needed to read the vintage out of a document')
        return 2

    def fetch(job):
        eid, u, how = job
        try:
            blob, final, disp = get(u, binary=True)
        except Exception as e:
            return (eid, u, how, None, None, None, str(e)[:40])
        if not blob.startswith(b'%PDF'):
            return (eid, u, how, None, None, None, 'not a PDF')
        sha = hashlib.sha1(blob).hexdigest()
        if sha in have_sha:
            return (eid, u, how, sha, None, None, 'already held, byte for byte')
        # The server's own name for the file beats the one in the URL:
        # vin.co serves a 2023 sheet from a URL that says 1995.
        named = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)', disp or '')
        base = urllib.parse.unquote(
            (named.group(1) if named else u.rsplit('/', 1)[-1]))
        folder = os.path.join(DEST, eid)
        if not os.path.isdir(folder):
            os.makedirs(folder)
        safe = re.sub(r'[^A-Za-z0-9._-]+', '-', base)[:110] or (sha[:12] + '.pdf')
        path = os.path.join(folder, safe)
        open(path, 'wb').write(blob)
        try:
            d = pymupdf.open(path)
            text = re.sub(r'\s+', ' ', ' '.join(p.get_text() for p in d))
            d.close()
        except Exception as e:
            return (eid, u, how, sha, path, None, str(e)[:40])
        yr, yhow = vintage_of(text)
        return (eid, u, how, sha, path, yr, yhow)

    # The manifest is written as the sheets land, every CHECKPOINT of
    # them, and not once at the end.
    #
    # It used to be `out = list(ex.map(...))` - download all 5,451, then
    # register all 5,451, then write. A run of that shape took ninety
    # minutes, and for eighty-nine of them every file it had fetched was
    # on disk with nothing in data/sources.json describing it. Stop it,
    # lose the machine, hit an unhandled error in the last loop, and the
    # whole run is untracked material in sources/ - which is the one
    # thing the manifest exists to prevent, and which this tool was
    # separately fixed this evening for the 944 documents that state no
    # vintage. Same defect, larger blast radius.
    #
    # ex.map yields in order as results arrive, so registering inside
    # the loop costs nothing and the work survives.
    CHECKPOINT = 100

    def save():
        io.open(ROOT + 'data/sources.json', 'w', encoding='utf-8',
                newline='').write(json.dumps(man, ensure_ascii=False,
                                             indent=1))

    added, why = 0, collections.Counter()
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        out = ex.map(fetch, todo)
        for eid, u, how, sha, path, yr, yhow in out:
            if not (path and sha):
                why[yhow] += 1
                continue
            if a.year and yr is not None and yr != a.year:
                why['a vintage other than the one asked for'] += 1
                continue
            if a.year and yr is None:
                why['no vintage in the document, and a year was asked '
                    'for'] += 1
                continue
        # A document stating no vintage is still registered, with
        # year: null. It used to be dropped here - 944 of them in one
        # run - and the file had already been written to disk at that
        # point, so they ended up in sources/ with nothing in the
        # manifest describing them. Untracked material in sources/ is
        # the one thing the manifest exists to prevent: sha1 can prove a
        # file is the one that was read, and a file nothing names cannot
        # be proved or re-fetched.
        #
        # Some of these are multi-vintage documents and some are sheets
        # whose year is only in the filename. The vintage still does not
        # come from the filename - that is a rule this project has paid
        # for - but recording the file and saying the vintage is unknown
        # is better than knowing neither.
            if yr is None:
                why['registered with no vintage, for someone to read'] += 1
            man['sheets'].append({
                'file': os.path.basename(path), 'folder': eid,
                'estate': eid, 'estateName': names.get(eid),
                'wine': None, 'slug': None,
                'role': 'unknown', 'colour': None, 'year': yr,
                'bytes': os.path.getsize(path), 'sha1': sha,
                'url': u, 'how': how,
                'note': ('the vintage came from %s' % yhow
                         if yr is not None
                         else 'no vintage in the document: %s' % yhow),
            })
            have_sha.add(sha)
            added += 1
            if added % CHECKPOINT == 0:
                save()
                print('   ... %d registered so far' % added, flush=True)

    save()
    print('%d sheets registered' % added)
    for k, n in why.most_common(10):
        print('   %-56s %d' % (str(k)[:56], n))
    print('\nnext: python tools/read-sheets.py   then  tools/check-data.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())
