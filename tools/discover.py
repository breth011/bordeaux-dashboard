# -*- coding: utf-8 -*-
"""Phase 3.3: broad discovery harvest of the classified estates' own sites.

    python -I tools/discover.py targets              write data/discovery/targets.json
    python -I tools/discover.py crawl [--domain D] [--workers N]
    python -I tools/discover.py status               what the crawl state holds

Capture broadly, interpret conservatively, normalize later. This module
only RETRIEVES and RECORDS: robots, sitemaps, WordPress media listings,
links, and the bytes each URL served. What the bytes say is
tools/discover_extract.py's business, and what any of it means is a later
phase's.

Where things go:

  sources/discovery/blobs/<aa>/<sha256>   raw bytes, content-addressed, never
                                          overwritten (sources/ is gitignored:
                                          the estates' material is not ours to
                                          republish)
  sources/discovery/state/<domain>.json   the crawl frontier, for resuming
  data/discovery/locations/<domain>.jsonl one row per fetch: URL, final URL,
                                          status, type, length, sha256, when,
                                          from where, how found
  data/discovery/failures.jsonl           (built by the report) every failure

Access rules, enforced here and never bypassed:
  - robots.txt is honoured for this crawler, for '*', and for the AI-agent
    tokens (ClaudeBot, Claude-User, anthropic-ai): the crawl is run by an
    AI agent, so a site that refuses AI agents is refused;
  - a `Content-Signal: ... ai-input=no` line is honoured the same way;
  - at least MIN_DELAY seconds between requests to one host, or the site's
    Crawl-delay if longer;
  - challenges (Cloudflare and the like), authentication and TLS failures
    are recorded as such and the URL is not retried another way.

Identity is the content: the same bytes at two URLs are one artifact with
two locations; one URL serving new bytes is a new artifact, and the old
bytes stay.
"""
import argparse
import collections
import concurrent.futures as cf
import datetime
import gzip
import hashlib
import heapq
import html
import io
import json
import os
import re
import socket
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
SCRAPER = 'discover/1.0'
UA = ('BordeauxDashboard-Discovery/1.0 (+https://github.com/breth011/bordeaux-dashboard;'
      ' personal research; low rate)')
UA_TOKEN = 'BordeauxDashboard-Discovery'
AI_TOKENS = ('ClaudeBot', 'Claude-User', 'Claude-SearchBot', 'anthropic-ai', 'Claude-Web')
MIN_DELAY = 1.5
MAX_DELAY = 30.0            # a longer Crawl-delay is honoured by giving up the site's crawl
MAX_BYTES = 25 * 1024 * 1024
TIMEOUT = 30
BUDGET = {'pages': 120, 'documents': 200, 'requests': 380, 'seconds': 25 * 60, 'depth': 6}
IMAGE_EXT = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
DOC_EXT = ('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv', '.ppt', '.pptx', '.odt', '.ods',
           '.txt', '.rtf', '.xml', '.json', '.zip', '.jpg', '.jpeg', '.png', '.webp', '.gif')
SKIP_EXT = ('.css', '.js', '.ico', '.svg', '.woff', '.woff2', '.ttf', '.eot', '.mp4', '.mp3',
            '.mov', '.webm', '.avi', '.m4a', '.wav')
SKIP_PATH = re.compile(r'(?i)(/wp-admin|/wp-login|/login|/logout|/account|/my-account|/mon-compte|'
                       r'/cart|/panier|/checkout|/commande|/basket|/wishlist|add-to-cart|'
                       r'/feed/?$|/comments?/|replytocom=|/xmlrpc|/cdn-cgi/|[?&](orderby|filter|'
                       r'sort|s|q|search)=|/tag/|/author/|/wp-json/(?!wp/v2/media))')
GOOD = re.compile(r'(?i)(fiche|technique|technical|tech-?sheet|sheet|spec|vin|wine|cuv[eé]e|'
                  r'mill[eé]sime|vintage|terroir|vignoble|vineyard|histoire|history|domaine|'
                  r'estate|chateau|ch[aâ]teau|download|t[eé]l[eé]charg|press|presse|document|'
                  r'harvest|vendange|r[eé]colte|blend|assemblage|uploads|media|pdf)')
DOC_HINT = re.compile(r'(?i)(fiche|technique|technical|sheet|ft[-_ ]|tech|mill[eé]sime|vintage|'
                      r'harvest|vendange|press|brochure|dossier|carte|plan|certif|label|etiquette)')
CHALLENGE = re.compile(r'(?i)(cf-chl|challenge-platform|just a moment\.\.\.|attention required|'
                       r'captcha|ddos-guard|sucuri website firewall|access denied)')

STORE = ROOT + 'sources/discovery/'
MIN_FREE = 6 * 1024 ** 3     # stop crawling below this much free disk


def compressible(data):
    head = data[:8]
    return not (head.startswith((b'%PDF', b'PK', b'\x89PNG', b'GIF8', b'RIFF', b'\x1f\x8b'))
                or head[:3] == b'\xff\xd8\xff')


def read_blob(store, sha):
    p = '%sblobs/%s/%s' % (store, sha[:2], sha)
    if os.path.exists(p):
        return open(p, 'rb').read()
    return gzip.decompress(open(p + '.gz', 'rb').read())


def disk_free(path):
    import shutil
    return shutil.disk_usage(path).free
OUT = ROOT + 'data/discovery/'


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def host_of(url):
    return (urllib.parse.urlsplit(url).hostname or '').lower()


def site_of(host):
    """The registrable-ish site: the host without a leading www."""
    return re.sub(r'^www\d?\.', '', host)


def norm_url(url, base=None):
    """A canonical form of a link, or None for one that is not a usable
    http(s) URL (malformed ports and hosts included: a bad link on a page
    is skipped, it does not stop the site's crawl)."""
    try:
        if base:
            url = urllib.parse.urljoin(base, url)
        u = urllib.parse.urlsplit(url.strip())
        if u.scheme not in ('http', 'https') or not u.hostname:
            return None
        port = u.port
        path = urllib.parse.quote(urllib.parse.unquote(u.path or '/'), safe="/%:@!$&'()*+,;=-._~")
        q = '&'.join(p for p in u.query.split('&') if p and not re.match(
            r'(?i)(utm_|fbclid|gclid|_ga|mc_|ref=|lang=$)', p))
        return urllib.parse.urlunsplit((u.scheme.lower(), u.hostname.lower()
                                        + ((':%d' % port) if port else ''), path, q, ''))
    except (ValueError, UnicodeError):
        return None


# ------------------------------------------------------------------ store
class Store:
    """Content-addressed blobs plus per-domain location logs and state.
    Thread-safe: blob writes are write-then-rename; each domain's files are
    written by one worker only."""

    def __init__(self, store=STORE, out=OUT):
        self.store, self.out = store, out
        for d in ('blobs', 'state'):
            os.makedirs(store + d, exist_ok=True)
        os.makedirs(out + 'locations', exist_ok=True)

    def blob_path(self, sha):
        """Where the blob is: raw, or gzipped for text-like bytes. Either
        way its name is the sha256 of the RAW bytes."""
        p = '%sblobs/%s/%s' % (self.store, sha[:2], sha)
        return p + '.gz' if not os.path.exists(p) and os.path.exists(p + '.gz') else p

    def put(self, data):
        sha = hashlib.sha256(data).hexdigest()
        raw = '%sblobs/%s/%s' % (self.store, sha[:2], sha)
        if not (os.path.exists(raw) or os.path.exists(raw + '.gz')):
            os.makedirs(os.path.dirname(raw), exist_ok=True)
            # Text-like bytes are stored compressed (a local disk limit);
            # documents and images, which barely compress, are stored raw.
            gz = compressible(data)
            p = raw + '.gz' if gz else raw
            tmp = '%s.%d.%d.tmp' % (p, os.getpid(), threading.get_ident())
            with open(tmp, 'wb') as f:
                f.write(gzip.compress(data, 6, mtime=0) if gz else data)
            try:
                os.replace(tmp, p)
            except PermissionError:
                # Windows: another worker stored the same bytes a moment
                # ago and the file is busy. Same name, same content.
                if not os.path.exists(p):
                    raise
                os.remove(tmp)
        return sha, hashlib.sha1(data).hexdigest()

    def has(self, sha):
        return os.path.exists(self.blob_path(sha))

    def read(self, sha):
        return read_blob(self.store, sha)

    def compact(self):
        """Compress raw text-like blobs written before compression was
        added. Identity is unchanged; each is verified before the raw copy
        goes."""
        freed = 0
        for dp, dn, fn in os.walk(self.store + 'blobs'):
            for f in fn:
                if f.endswith(('.gz', '.tmp')):
                    continue
                p = os.path.join(dp, f)
                data = open(p, 'rb').read()
                if not compressible(data) or hashlib.sha256(data).hexdigest() != f:
                    continue
                z = gzip.compress(data, 6, mtime=0)
                with open(p + '.gz.tmp', 'wb') as o:
                    o.write(z)
                if gzip.decompress(open(p + '.gz.tmp', 'rb').read()) == data:
                    os.replace(p + '.gz.tmp', p + '.gz')
                    os.remove(p)
                    freed += len(data) - len(z)
        return freed

    def log(self, domain, row):
        with io.open('%slocations/%s.jsonl' % (self.out, domain), 'a', encoding='utf-8',
                     newline='\n') as f:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')

    def locations(self, domain):
        p = '%slocations/%s.jsonl' % (self.out, domain)
        if not os.path.exists(p):
            return []
        return [json.loads(l) for l in io.open(p, encoding='utf-8') if l.strip()]

    def state_path(self, domain):
        return '%sstate/%s.json' % (self.store, domain)

    def load_state(self, domain):
        p = self.state_path(domain)
        if os.path.exists(p):
            return json.load(io.open(p, encoding='utf-8'))
        return None

    def save_state(self, domain, st):
        p = self.state_path(domain)
        tmp = p + '.tmp'
        io.open(tmp, 'w', encoding='utf-8').write(json.dumps(st, ensure_ascii=False))
        os.replace(tmp, p)


# ------------------------------------------------------------------ fetch
class Fetched(object):
    __slots__ = ('url', 'final', 'status', 'ctype', 'data', 'headers', 'error', 'kind')

    def __init__(self, url):
        self.url, self.final, self.status, self.ctype = url, url, None, None
        self.data, self.headers, self.error, self.kind = None, {}, None, None


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Redirects are followed by hand, so each hop is checked against robots
    and the site boundary."""
    def redirect_request(self, *a, **k):
        return None


_ctx = ssl.create_default_context()
_opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=_ctx))


def fetch(url, headers=None, max_bytes=MAX_BYTES, allowed=None):
    """One GET, redirects followed by hand (at most 5). Each hop is put to
    `allowed(url)`, which returns None to proceed or the kind of refusal.
    Never raises: errors come back as a kind."""
    f = Fetched(url)
    cur = url
    for hop in range(6):
        refusal = allowed(cur) if allowed else None
        if refusal:
            f.kind, f.error, f.final = refusal, cur, cur
            return f
        req = urllib.request.Request(cur, headers=dict({'User-Agent': UA, 'Accept': '*/*',
                                                        'Accept-Encoding': 'gzip, deflate'},
                                                       **(headers or {})))
        try:
            resp = _opener.open(req, timeout=TIMEOUT)
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308) and e.headers.get('Location'):
                nxt = norm_url(e.headers['Location'], cur)
                if not nxt:
                    f.kind, f.error, f.status = 'BAD_REDIRECT', e.headers['Location'], e.code
                    return f
                cur = nxt
                continue
            f.status, f.final, f.headers = e.code, cur, dict(e.headers or {})
            body = b''
            try:
                body = e.read(65536) or b''
            except Exception:
                pass
            if e.code == 304:
                f.kind = 'NOT_MODIFIED'
            elif e.code in (401, 407):
                f.kind = 'AUTH_REQUIRED'
            elif e.code in (403, 429, 503) and CHALLENGE.search(body.decode('latin-1', 'replace')):
                f.kind = 'BLOCKED_CHALLENGE'
            elif e.code == 429:
                f.kind = 'RATE_LIMITED'
            else:
                f.kind = 'HTTP_ERROR'
            f.error = 'HTTP %d' % e.code
            return f
        except (ssl.SSLError, ssl.CertificateError) as e:
            f.kind, f.error = 'TLS_FAILURE', str(e)[:200]
            return f
        except urllib.error.URLError as e:
            r = getattr(e, 'reason', e)
            f.kind = 'TLS_FAILURE' if isinstance(r, ssl.SSLError) else (
                'TIMEOUT' if isinstance(r, socket.timeout) else 'NETWORK_FAILURE')
            f.error = str(r)[:200]
            return f
        except (socket.timeout, TimeoutError) as e:
            f.kind, f.error = 'TIMEOUT', str(e)[:200]
            return f
        except Exception as e:      # malformed responses, resets
            f.kind, f.error = 'NETWORK_FAILURE', ('%s: %s' % (type(e).__name__, e))[:200]
            return f
        f.status, f.final, f.headers = resp.status, cur, dict(resp.headers or {})
        f.ctype = (resp.headers.get('Content-Type') or '').split(';')[0].strip().lower()
        try:
            data = resp.read(max_bytes + 1)
        except Exception as e:
            f.kind, f.error = 'NETWORK_FAILURE', ('read: %s' % e)[:200]
            return f
        if len(data) > max_bytes:
            f.kind, f.error = 'TOO_LARGE', '> %d bytes' % max_bytes
            return f
        enc = (resp.headers.get('Content-Encoding') or '').lower()
        try:
            if enc == 'gzip':
                data = gzip.decompress(data)
            elif enc == 'deflate':
                data = zlib.decompress(data, -zlib.MAX_WBITS)
        except Exception as e:
            f.kind, f.error = 'MALFORMED', ('content-encoding: %s' % e)[:200]
            return f
        f.data = data
        head = data[:4096].decode('latin-1', 'replace')
        if f.ctype.startswith('text/html') and CHALLENGE.search(head) and len(data) < 30000:
            f.kind = 'BLOCKED_CHALLENGE'
        else:
            f.kind = 'OK'
        return f
    f.kind, f.error = 'TOO_MANY_REDIRECTS', cur
    return f


# ------------------------------------------------------------------ robots
class Robots:
    """robots.txt as it applies to this crawl: every token must allow."""

    def __init__(self, base, text, status):
        self.base, self.status, self.text = base, status, text or ''
        self.rp = urllib.robotparser.RobotFileParser()
        self.rp.set_url(base + '/robots.txt')
        if status in (401, 403):
            self.rp.disallow_all = True
        elif status is None or status >= 400 or text is None:
            self.rp.allow_all = True
        else:
            self.rp.parse(self.text.splitlines())
        self.signals = re.findall(r'(?im)^\s*content-signal\s*:\s*(.+)$', self.text)
        self.ai_input_no = any(re.search(r'ai-input\s*=\s*no', s, re.I) for s in self.signals)
        self.sitemaps = re.findall(r'(?im)^\s*sitemap\s*:\s*(\S+)', self.text)

    def allows(self, url):
        if self.ai_input_no:
            return False
        for tok in (UA_TOKEN, '*') + AI_TOKENS:
            if not self.rp.can_fetch(tok, url):
                return False
        return True

    def ai_refused(self):
        root = self.base + '/'
        return [t for t in AI_TOKENS if not self.rp.can_fetch(t, root)]

    def delay(self):
        d = [self.rp.crawl_delay(t) for t in (UA_TOKEN, '*') + AI_TOKENS]
        d = [float(x) for x in d if x]
        return max([MIN_DELAY] + d)


# ------------------------------------------------------------------ links
class LinkParser(object):
    """Links, anchors and images out of HTML, with the stdlib parser."""

    def __init__(self, base):
        from html.parser import HTMLParser
        outer = self
        self.base, self.links, self.alts, self.lang = base, [], [], None
        self._a = None

        class P(HTMLParser):
            def handle_starttag(self, tag, attrs):
                a = dict(attrs)
                if tag == 'base' and a.get('href'):
                    outer.base = norm_url(a['href'], outer.base) or outer.base
                elif tag == 'html' and a.get('lang'):
                    outer.lang = a['lang']
                elif tag == 'a' and a.get('href'):
                    outer._a = [a['href'], '']
                    outer.links.append(outer._a)
                elif tag in ('link',) and a.get('href') and (a.get('rel') or '').lower() in (
                        'alternate', 'canonical', 'next'):
                    outer.links.append([a['href'], 'link:' + (a.get('rel') or '')])
                elif tag == 'iframe' and a.get('src'):
                    outer.links.append([a['src'], 'iframe'])
                elif tag in ('embed', 'object') and (a.get('src') or a.get('data')):
                    outer.links.append([a.get('src') or a.get('data'), tag])

            def handle_endtag(self, tag):
                if tag == 'a':
                    outer._a = None

            def handle_data(self, data):
                if outer._a is not None and len(outer._a[1]) < 200:
                    outer._a[1] += data

        self.p = P(convert_charrefs=True)

    def feed(self, text):
        try:
            self.p.feed(text)
            self.p.close()
        except Exception:
            pass
        out = []
        for href, anchor in self.links:
            u = norm_url(html.unescape(href), self.base)
            if u:
                out.append((u, ' '.join(anchor.split())[:120]))
        return out


def decode(data, ctype=''):
    m = re.search(rb'charset=["\']?([A-Za-z0-9_-]+)', data[:2048])
    for enc in ([m.group(1).decode('ascii', 'ignore')] if m else []) + ['utf-8', 'cp1252']:
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode('utf-8', 'replace')


def is_doc(url, ctype=None):
    path = urllib.parse.urlsplit(url).path.lower()
    if path.endswith(DOC_EXT):
        return True
    return bool(ctype) and not ctype.startswith(('text/html', 'application/xhtml'))


def score(url, anchor, depth):
    s = 0
    path = urllib.parse.unquote(urllib.parse.urlsplit(url).path)
    if is_doc(url):
        s -= 50
        if DOC_HINT.search(path + ' ' + anchor):
            s -= 30
    if GOOD.search(path + ' ' + anchor):
        s -= 20
    if re.search(r'(19|20)\d\d', path):
        s -= 5
    return s + depth * 3 + min(len(path), 200) / 40.0


# ------------------------------------------------------------------ crawl
class SiteCrawl:
    def __init__(self, store, domain, seeds, estates, budget=BUDGET, min_delay=MIN_DELAY,
                 scheme_hint='https', log=print):
        self.S, self.domain, self.estates = store, domain, estates
        self.seeds, self.budget, self.min_delay, self.say = seeds, dict(budget), min_delay, log
        self.scheme = scheme_hint
        self.robots = {}
        self.moved = []

    def in_site(self, url):
        h = host_of(url)
        return any(h == d or h.endswith('.' + d) for d in [self.domain] + self.moved)

    def hop(self, seed):
        """The redirect check for one fetch. A seed may redirect to a new
        domain - the estate's site has moved - and that domain is then
        crawled as the site, recorded as SITE_MOVED. Any other off-site
        hop is refused."""
        def check(url):
            if not self.in_site(url):
                if seed:
                    d = site_of(host_of(url))
                    if d and d not in self.moved:
                        self.moved.append(d)
                        self.S.log(self.domain, {'url': url, 'kind': 'SITE_MOVED', 'at': now(),
                                                 'scraper': SCRAPER, 'moved_to': d})
                else:
                    return 'OFFSITE_REDIRECT'
            if not self.robots_for(url).allows(url):
                return 'ROBOTS_DISALLOW_REDIRECT'
            return None
        return check

    def robots_for(self, url):
        u = urllib.parse.urlsplit(url)
        base = '%s://%s' % (u.scheme, u.netloc)
        if base not in self.robots:
            f = fetch(base + '/robots.txt', max_bytes=512 * 1024)
            text = decode(f.data) if f.data is not None and f.kind == 'OK' else None
            status = f.status if f.kind in ('OK', 'HTTP_ERROR', 'AUTH_REQUIRED') else None
            if f.kind in ('BLOCKED_CHALLENGE',):
                status = 403
            self.robots[base] = Robots(base, text, status)
            self.robots[base].fetch_kind = f.kind
            self.robots[base].fetched_at = now()
            if f.data is not None and f.kind == 'OK':
                sha, sha1 = self.S.put(f.data)
                self.robots[base].sha256 = sha
            else:
                self.robots[base].sha256 = None
        return self.robots[base]

    def allowed(self, url):
        return self.in_site(url) and self.robots_for(url).allows(url)

    def run(self):
        st = self.S.load_state(self.domain)
        if not st or st.get('scraper') != SCRAPER:
            st = {'domain': self.domain, 'scraper': SCRAPER, 'estates': self.estates,
                  'started': now(), 'finished': None, 'frontier': [], 'seen': {},
                  'counts': {'pages': 0, 'documents': 0, 'requests': 0}, 'elapsed': 0.0,
                  'validators': {}, 'last_sha': {}, 'robots': {}, 'stopped': None}
            for u in self.seeds:
                self.push(st, u, '', 0, 'SEED', None)
        if st.get('finished'):
            # A finished crawl is resumed as a re-crawl: the seen set is
            # cleared so pages are revisited with their validators.
            st.update({'finished': None, 'frontier': [], 'seen': {}, 'stopped': None,
                       'counts': {'pages': 0, 'documents': 0, 'requests': 0}, 'elapsed': 0.0,
                       'started': now()})
            for u in self.seeds:
                self.push(st, u, '', 0, 'SEED', None)
        self.moved = st.setdefault('moved', [])     # the same list, so it persists
        r = self.robots_for(self.seeds[0])
        st['robots'] = {'base': r.base, 'status': r.status, 'kind': r.fetch_kind,
                        'sha256': r.sha256, 'ai_refused': r.ai_refused(),
                        'ai_input_no': r.ai_input_no, 'delay': r.delay(),
                        'sitemaps': r.sitemaps, 'at': r.fetched_at}
        if not r.allows(self.seeds[0]):
            st['stopped'] = 'ROBOTS_DISALLOW_SITE'
            self.record_block(st, self.seeds[0], 'ROBOTS_DISALLOW_SITE', r)
            st['finished'] = now()
            self.S.save_state(self.domain, st)
            return st
        delay = r.delay()
        if delay > MAX_DELAY:
            st['stopped'] = 'CRAWL_DELAY_TOO_LONG'
            self.record_block(st, self.seeds[0], 'CRAWL_DELAY_TOO_LONG', r)
            st['finished'] = now()
            self.S.save_state(self.domain, st)
            return st
        delay = max(delay, self.min_delay)
        if not st.get('seeded_extra'):
            for sm in list(r.sitemaps) + [r.base + '/sitemap.xml', r.base + '/sitemap_index.xml',
                                          r.base + '/wp-sitemap.xml']:
                self.push(st, norm_url(sm) or sm, 'sitemap', 1, 'SITEMAP', None)
            self.push(st, r.base + '/wp-json/wp/v2/media?per_page=100&page=1', 'wp-media', 1,
                      'WP_MEDIA', None)
            st['seeded_extra'] = True
        t0 = time.time() - st.get('elapsed', 0.0)
        last = 0.0
        since_save = 0
        while st['frontier']:
            c = st['counts']
            if (c['requests'] >= self.budget['requests'] or time.time() - t0 > self.budget['seconds']
                    or (c['pages'] >= self.budget['pages'] and c['documents'] >= self.budget['documents'])):
                st['stopped'] = 'BUDGET'
                break
            if disk_free(self.S.store) < MIN_FREE:
                st['stopped'] = 'STOPPED_LOCAL_DISK_LIMIT'
                self.S.log(self.domain, {'url': self.seeds[0], 'kind': 'STOPPED_LOCAL_DISK_LIMIT',
                                         'at': now(), 'scraper': SCRAPER})
                st['elapsed'] = time.time() - t0
                self.S.save_state(self.domain, st)     # not finished: resumable
                return st
            pri, n, url, anchor, depth, how, ref = heapq.heappop(st['frontier'])
            if st['seen'].get(url) not in (None, 'QUEUED'):
                continue
            doc = is_doc(url)
            if doc and c['documents'] >= self.budget['documents']:
                st['seen'][url] = 'SKIPPED_BUDGET'
                continue
            if not doc and how not in ('SITEMAP', 'WP_MEDIA') and c['pages'] >= self.budget['pages']:
                st['seen'][url] = 'SKIPPED_BUDGET'
                continue
            if not self.allowed(url):
                st['seen'][url] = 'ROBOTS_DISALLOW'
                self.S.log(self.domain, {'url': url, 'kind': 'ROBOTS_DISALLOW', 'at': now(),
                                         'referrer': ref, 'discovered_via': how, 'anchor': anchor,
                                         'scraper': SCRAPER})
                continue
            wait = last + delay - time.time()
            if wait > 0:
                time.sleep(wait)
            hdr = {}
            v = st['validators'].get(url)
            if v and v.get('etag'):
                hdr['If-None-Match'] = v['etag']
            if v and v.get('last_modified'):
                hdr['If-Modified-Since'] = v['last_modified']
            # Archives are the largest and least informative downloads.
            cap = 5 * 1024 * 1024 if urllib.parse.urlsplit(url).path.lower().endswith(
                ('.zip', '.rar', '.7z', '.tar', '.gz')) else MAX_BYTES
            f = fetch(url, headers=hdr, allowed=self.hop(how == 'SEED'), max_bytes=cap)
            last = time.time()
            c['requests'] += 1
            self.record(st, f, url, anchor, depth, how, ref)
            since_save += 1
            if since_save >= 15:
                st['elapsed'] = time.time() - t0
                self.S.save_state(self.domain, st)
                since_save = 0
        else:
            st['stopped'] = st.get('stopped') or 'FRONTIER_EMPTY'
        st['elapsed'] = time.time() - t0
        st['finished'] = now()
        self.S.save_state(self.domain, st)
        return st

    def push(self, st, url, anchor, depth, how, ref):
        if not url or url in st['seen']:
            return
        path = urllib.parse.urlsplit(url).path.lower()
        if path.endswith(SKIP_EXT) or SKIP_PATH.search(url):
            st['seen'][url] = 'SKIPPED_POLICY'
            return
        if depth > self.budget['depth']:
            return
        # Photographs are recorded where they appear (by the extractor) and
        # not fetched; an image that looks like a document is.
        if path.endswith(IMAGE_EXT) and not DOC_HINT.search(
                urllib.parse.unquote(path) + ' ' + (anchor or '')):
            st['seen'][url] = 'SKIPPED_IMAGE'
            return
        st['seen'][url] = 'QUEUED'
        heapq.heappush(st['frontier'], [score(url, anchor, depth), len(st['seen']), url, anchor,
                                        depth, how, ref])

    def record_block(self, st, url, kind, r):
        self.S.log(self.domain, {'url': url, 'kind': kind, 'at': now(), 'scraper': SCRAPER,
                                 'robots_status': r.status, 'robots_sha256': r.sha256,
                                 'ai_refused': r.ai_refused(), 'ai_input_no': r.ai_input_no,
                                 'crawl_delay': r.delay()})

    def record(self, st, f, url, anchor, depth, how, ref):
        row = {'url': url, 'final_url': f.final, 'status': f.status, 'kind': f.kind,
               'content_type': f.ctype, 'at': now(), 'referrer': ref, 'discovered_via': how,
               'anchor': anchor, 'depth': depth, 'scraper': SCRAPER, 'error': f.error}
        if f.kind == 'NOT_MODIFIED':
            sha = st['last_sha'].get(url)
            row['sha256'] = sha
            row['change'] = 'UNCHANGED'
            st['seen'][url] = 'UNCHANGED'
            self.S.log(self.domain, row)
            # The page has not changed, but what it links to may have: its
            # links are followed from the stored copy, or a re-crawl would
            # never see a changed document behind an unchanged page.
            if sha and self.S.has(sha):
                f.data = self.S.read(sha)
                f.ctype = st.setdefault('ctype', {}).get(url)
                f.kind = 'OK'
                if self.in_site(f.final):
                    self.follow(st, f, url, depth, how)
            return
        if f.kind != 'OK' or f.data is None:
            st['seen'][url] = f.kind or 'FAILED'
            self.S.log(self.domain, row)
            return
        sha, sha1 = self.S.put(f.data)
        prev = st['last_sha'].get(url)
        row.update({'sha256': sha, 'sha1': sha1, 'length': len(f.data),
                    'etag': f.headers.get('ETag'), 'last_modified': f.headers.get('Last-Modified'),
                    'change': 'NEW' if prev is None else ('UNCHANGED' if prev == sha else 'CHANGED')})
        st['last_sha'][url] = sha
        st['validators'][url] = {'etag': f.headers.get('ETag'),
                                 'last_modified': f.headers.get('Last-Modified')}
        st['seen'][url] = 'RETRIEVED'
        st.setdefault('ctype', {})[url] = f.ctype
        final_in = self.in_site(f.final)
        doc = is_doc(f.final, f.ctype)
        st['counts']['documents' if doc else 'pages'] += 1
        self.S.log(self.domain, row)
        if not final_in:
            return
        if how == 'SEED' and site_of(host_of(f.final)) != site_of(host_of(url)):
            # The site has moved: its own sitemaps and media listing too.
            u = urllib.parse.urlsplit(f.final)
            base = '%s://%s' % (u.scheme, u.netloc)
            for sm in self.robots_for(f.final).sitemaps + [base + '/sitemap.xml',
                                                            base + '/wp-sitemap.xml']:
                self.push(st, norm_url(sm) or sm, 'sitemap', 1, 'SITEMAP', f.final)
            self.push(st, base + '/wp-json/wp/v2/media?per_page=100&page=1', 'wp-media', 1,
                      'WP_MEDIA', f.final)
        self.follow(st, f, url, depth, how)

    def follow(self, st, f, url, depth, how):
        """Follow: HTML links, sitemap entries, WordPress media listings."""
        doc = is_doc(f.final, f.ctype)
        text = None
        if how == 'WP_MEDIA' or (f.ctype or '').endswith('json') and '/wp-json/wp/v2/media' in url:
            try:
                items = json.loads(decode(f.data))
            except Exception:
                items = []
            if isinstance(items, list):
                for it in items:
                    src = (it or {}).get('source_url') if isinstance(it, dict) else None
                    mt = (it or {}).get('mime_type', '') if isinstance(it, dict) else ''
                    if src and not str(mt).startswith(('video', 'audio')):
                        self.push(st, norm_url(src), (it.get('title') or {}).get('rendered', '')
                                  if isinstance(it.get('title'), dict) else '', depth + 1,
                                  'WP_MEDIA', url)
                if len(items) == 100:
                    m = re.search(r'page=(\d+)', url)
                    p = int(m.group(1)) + 1 if m else 2
                    if p <= 20:
                        self.push(st, re.sub(r'page=\d+', 'page=%d' % p, url), 'wp-media',
                                  depth, 'WP_MEDIA', url)
            return
        if 'xml' in (f.ctype or '') or url.endswith('.xml'):
            text = decode(f.data)
            if '<urlset' in text or '<sitemapindex' in text:
                for loc in re.findall(r'<loc>\s*([^<\s]+)\s*</loc>', text)[:5000]:
                    u = norm_url(html.unescape(loc))
                    if u and self.in_site(u):
                        self.push(st, u, 'sitemap', depth + 1, 'SITEMAP', url)
                return
        if (f.ctype or '').startswith(('text/html', 'application/xhtml')) and not doc:
            text = decode(f.data)
            lp = LinkParser(f.final)
            for u, anc in lp.feed(text):
                if self.in_site(u):
                    self.push(st, u, anc, depth + 1, 'LINK', f.final)


def crawl_site(store, target, log=print, budget=BUDGET, min_delay=MIN_DELAY):
    sc = SiteCrawl(store, target['domain'], target['seeds'], target['estates'], budget=budget,
                   min_delay=min_delay, log=log)
    st = sc.run()
    return st


# ------------------------------------------------------------------ targets
def build_targets():
    """The Phase 3.0 universe, each estate with the site websites.js gives
    its matched canonical estate. websites.js is prior data: its address is
    a starting point recorded as such, not a fact about the estate."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('cu', ROOT + 'tools/compare-universe.py')
    cu = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cu)
    U = json.load(io.open(ROOT + 'data/scope/authoritative-universe.json', encoding='utf-8'))
    C = cu.canonical()
    _rows, matched = cu.compare_canonical(U, C)
    u2c = collections.defaultdict(list)
    for cid, us in matched.items():
        for u in us:
            u2c[u].append(cid)
    ws = io.open(ROOT + 'data/websites.js', encoding='utf-8').read()
    sites = {k: (u, t) for k, u, t in re.findall(r"^'([^']+)':\['([^']+)','([^']*)'\]", ws, re.M)}
    names = {e['id']: e['name'] for e in C['estates']}
    estates, domains = [], collections.OrderedDict()
    for e in U['estates']:
        cids = sorted(set(u2c.get(e['id'], [])))
        site = next((sites[c] for c in cids if c in sites), None)
        rec = {'universe_id': e['id'], 'name': e['names'][0]['name'],
               'systems': sorted({m['system'] for m in e['memberships']}),
               'canonical_ids': cids, 'canonical_names': [names.get(c) for c in cids],
               'site': site[0] if site else None,
               'site_basis': ('websites.js tag %r (prior record, not verified here)' % site[1])
               if site else None,
               'status': 'TARGET' if site else 'NO_KNOWN_SITE'}
        estates.append(rec)
        if site:
            u = norm_url(site[0] if '://' in site[0] else 'https://' + site[0])
            d = site_of(host_of(u))
            t = domains.setdefault(d, {'domain': d, 'seeds': [], 'estates': []})
            if u not in t['seeds']:
                t['seeds'].append(u)
            t['estates'].append(e['id'])
    out = {'phase': '3.3', 'built_by': 'tools/discover.py targets', 'at': now()[:10],
           'counts': {'estates': len(estates),
                      'with_site': sum(1 for e in estates if e['site']),
                      'no_known_site': sum(1 for e in estates if not e['site']),
                      'domains': len(domains),
                      'shared_domains': sum(1 for d in domains.values() if len(d['estates']) > 1)},
           'estates': estates, 'domains': list(domains.values())}
    os.makedirs(OUT, exist_ok=True)
    io.open(OUT + 'targets.json', 'w', encoding='utf-8', newline='\n').write(
        json.dumps(out, ensure_ascii=False, indent=1) + '\n')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('targets', 'crawl', 'status'))
    ap.add_argument('--domain', action='append')
    ap.add_argument('--workers', type=int, default=12)
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    if a.cmd == 'targets':
        t = build_targets()
        print(t['counts'])
        return
    T = json.load(io.open(OUT + 'targets.json', encoding='utf-8'))
    doms = [d for d in T['domains'] if not a.domain or d['domain'] in a.domain]
    if a.limit:
        doms = doms[:a.limit]
    store = Store()
    if a.cmd == 'status':
        c = collections.Counter()
        for d in T['domains']:
            st = store.load_state(d['domain'])
            c['finished' if st and st.get('finished') else ('started' if st else 'not started')] += 1
        print(dict(c))
        return
    lock = threading.Lock()
    done = [0]

    def one(d):
        st = store.load_state(d['domain'])
        if st and st.get('finished') and st.get('scraper') == SCRAPER and not a.domain:
            with lock:
                done[0] += 1
            return d['domain'], 'already finished'
        try:
            st = crawl_site(store, d)
            res = '%s %s' % (st.get('stopped'), st['counts'])
        except Exception as e:
            res = 'CRASH %s: %s' % (type(e).__name__, e)
            store.log(d['domain'], {'url': d['seeds'][0], 'kind': 'CRAWLER_CRASH', 'at': now(),
                                    'error': res[:300], 'scraper': SCRAPER})
        with lock:
            done[0] += 1
            print('[%d/%d] %s %s' % (done[0], len(doms), d['domain'], res), flush=True)
        return d['domain'], res

    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        list(ex.map(one, doms))


if __name__ == '__main__':
    main()
