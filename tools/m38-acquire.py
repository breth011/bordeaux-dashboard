"""M3.8: fetch the confirmed-source pilot's known URLs, once each - the network step.

    python tools/m38-acquire.py --targets   print the gated target list and stop (no request)
    python tools/m38-acquire.py --fetch     fetch every target not yet in the inventory

THE GATE is M3.7's ranking (data/audit/m3.7-source-confirmation.jsonl), its first five relationships and
nothing else: La Mondotte (neipperg.com), Durfort-Vivens (G&C Lurton), Issan, Myrat, Haut-Bages Libéral
(G&C Lurton). Each must still be CONFIRMED_* there. The probable sources and the 380 legacy relationships are
never targets. A target whose host is not its relationship's host stops the run.

THE TARGETS are the URLs M3.7 relied on: each relationship's M3.3 candidate locators, in M3.3's order. The
two G&C Lurton relationships share one download pool; a URL on both lists is one target, listed for both.
Myrat's fiche PDFs, which M3.3 found blocked by policy, are targets that are never requested: their outcome
is the recorded block and the current robots.txt decision.

THE FETCH is tools/discover.py's: its user agent, redirects followed by hand with robots checked at each
hop, its 25 MB limit and its 1.5 s floor between requests. A URL the repository already holds (discovery
crawl or model locator) is not requested. A URL already in the inventory is never requested again: the
inventory (sources/acquisition/m3.8/inventory.json, outside Git like the stores of M3.6G and M3.7) is
written after every request, and a second --fetch only completes what is missing. Bytes go to
blobs/<sha256>, text extraction (tools/discover_extract.py, no OCR) to extracted/<sha256>.json.
"""
import datetime
import hashlib
import json
import os
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import discover as D  # noqa: E402
import discover_extract as X  # noqa: E402
import migration_lib as L  # noqa: E402

M37 = L.ROOT + 'data/audit/m3.7-source-confirmation.jsonl'
M33 = L.ROOT + 'data/audit/m3.3-source-acquisition-plan.jsonl'
ACQ = L.ROOT + 'sources/acquisition/m3.8/'
GATE = (('neipperg.com', 'es_00293'), ('durfort-vivens.fr', 'es_00263'), ('chateau-issan.com', 'es_00283'),
        ('chateaudemyrat.fr', 'es_00253'), ('hautbagesliberal.com', 'es_00277'))
PROBABLE = ('mission-haut-brion.com', 'haut-brion.com', 'latourmartillac.com', 'malartic-lagraviere.com')


class Stop(Exception):
    pass


def host(u):
    h = urllib.parse.urlsplit(u).netloc.lower()
    return h[4:] if h.startswith('www.') else h


def targets():
    """[(url, [relationship ids], kind)] in gate order; kind TARGET or RECORDED_BLOCK."""
    a = L.jsonl_lines(M37)
    rel = {r['id']: r for r in a if r['record'] == 'relationship'}
    src = {s['source']: s for s in a if s['record'] == 'source'}
    rank = [r for r in a if r['record'] == 'ranking'][:len(GATE)]
    plan = L.jsonl_lines(M33)
    cand = {p['source_candidate_id']: p for p in plan}
    out, seen = [], {}
    for (name, estate), k in zip(GATE, rank):
        r = rel[k['relationship']]
        if (r['source_name'], r['estate']) != (name, estate) or not r['status'].startswith('CONFIRMED_'):
            raise Stop('M3.7 ranking #%d is %s/%s %s, not the gate\'s %s/%s'
                       % (k['rank'], r['source_name'], r['estate'], r['status'], name, estate))
        hosts = {name, src[r['source']]['canonical_host']}
        p = cand[r['acquisition']['m33']['ranked']['candidate']]
        urls = [(u, 'TARGET') for u in p['locators']]
        if r['acquisition']['m33']['blocked_by_policy']:
            urls += [(u, 'RECORDED_BLOCK') for q in plan if q['source_family'] == 'BLOCKED_BY_POLICY'
                     and name in q['domains'] and estate in q['estates'] for u in q['locators']]
        for u, kind in urls:
            if host(u) not in hosts or host(u) in PROBABLE:
                raise Stop('%s is not on %s\'s host %s' % (u, name, sorted(hosts)))
            if u in seen:
                out[seen[u]][1].append(r['id'])
                continue
            seen[u] = len(out)
            out.append((u, [r['id']], kind))
    return out


def held_urls():
    out = {}
    for l in open(L.ROOT + 'data/discovery/artifacts.jsonl', encoding='utf-8'):
        a = json.loads(l)
        out.setdefault(a['first_url'], ('discovery', a['sha256']))
    for p in L.read_table('document/placements.jsonl'):
        loc = p.get('locator') or {}
        if loc.get('kind') == 'URL' and p.get('artifact'):
            out.setdefault(loc['value'], ('model', p['artifact']))
    return out


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


class Fetcher:
    def __init__(self):
        self.robots, self.last = {}, 0.0

    def wait(self):
        d = D.MIN_DELAY - (time.time() - self.last)
        if d > 0:
            time.sleep(d)
        self.last = time.time()

    def robots_for(self, url, inv):
        p = urllib.parse.urlsplit(url)
        base = '%s://%s' % (p.scheme, p.netloc)
        if base not in self.robots:
            self.wait()
            f = D.fetch(base + '/robots.txt')
            text = (f.data or b'').decode('utf-8', 'replace') if f.kind == 'OK' else None
            self.robots[base] = D.Robots(base, text, f.status)
            inv['requests'].append({'url': base + '/robots.txt', 'why': 'robots', 'status': f.status, 'kind': f.kind,
                                    'sha256': hashlib.sha256(f.data).hexdigest() if f.data else None, 'at': now()})
        return self.robots[base]

    def allowed(self, inv):
        return lambda u: None if self.robots_for(u, inv).allows(u) else 'ROBOTS_DISALLOW'


def store(data, ctype, url):
    sha = hashlib.sha256(data).hexdigest()
    open(ACQ + 'blobs/' + sha, 'wb').write(data)
    rep = None
    pdf = data[:5] == b'%PDF-' or 'pdf' in (ctype or '')
    if pdf:
        rep = dict(X.parse_pdf(data), media='pdf')
    elif 'html' in (ctype or ''):
        rep = dict(X.parse_html(data), media='html')
    if rep is not None:
        json.dump(rep, open(ACQ + 'extracted/%s.json' % sha, 'w', encoding='utf-8'), ensure_ascii=False)
    return sha, hashlib.sha1(data).hexdigest()


def fetch_all():
    for d in ('blobs', 'extracted'):
        os.makedirs(ACQ + d, exist_ok=True)
    path = ACQ + 'inventory.json'
    inv = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {'requests': [], 'items': []}
    done = {i['url'] for i in inv['items']}
    held = held_urls()
    F = Fetcher()
    for url, rels, kind in targets():
        if url in done:
            continue
        item = {'url': url, 'relationships': rels, 'target': kind, 'at': now()}
        if url in held:
            item.update(retrieval='NOT_REQUESTED_ALREADY_HELD', held=list(held[url]))
        elif kind == 'RECORDED_BLOCK':
            allows = F.robots_for(url, inv).allows(url)
            item.update(retrieval='NOT_REQUESTED_RECORDED_BLOCK', robots_allows_now=allows)
        else:
            F.wait()
            f = D.fetch(url, allowed=F.allowed(inv))
            item.update(retrieval=f.kind, status=f.status, final=f.final, ctype=f.ctype, error=f.error)
            if f.kind == 'OK' and f.data:
                sha, sha1 = store(f.data, f.ctype, f.final)
                item.update(sha256=sha, sha1=sha1, bytes=len(f.data))
            inv['requests'].append({'url': url, 'why': 'target', 'status': f.status, 'kind': f.kind,
                                    'sha256': item.get('sha256'), 'at': item['at']})
        inv['items'].append(item)
        json.dump(inv, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('%-28s %s' % (item['retrieval'], url[:110]), flush=True)
    print('%d item(s), %d request(s)' % (len(inv['items']), len(inv['requests'])))


def main():
    try:
        if '--targets' in sys.argv:
            t = targets()
            for u, rels, kind in t:
                print(kind, len(rels), u)
            print(len(t), 'targets')
        elif '--fetch' in sys.argv:
            fetch_all()
        else:
            print(__doc__)
    except Stop as s:
        print('BLOCKED - %s' % s)
        sys.exit(2)


if __name__ == '__main__':
    main()
