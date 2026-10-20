# -*- coding: utf-8 -*-
"""Which of the addresses already on file still answer?

    python tools/audit-websites.py


Chasing Joanin Bécot turned up beausejour-becot.com returning 404, and
that address had been on file since the first UGCB harvest. The UGCB
still lists it and the estate still takes email at it, so the domain is
theirs; the web server is simply not serving a home page any more.

The file has always said that a URL rots faster than anything else here.
This counts the rot:

  ok        answers 2xx/3xx
  notfound  the server answers 404 or 410 - the page is gone
  error     the server answers 5xx
  nohost    the domain does not resolve at all
  blocked   no answer from here: reset, timeout, refused certificate.
            Unverifiable from one machine, not disproved

Nothing is changed. This is a report.
"""
import io, json, re, socket, subprocess, unicodedata, collections
import concurrent.futures as cf

import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/127.0 Safari/537.36')


def deacc(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s or '')
                   if not unicodedata.combining(c))


def host_of(u):
    return re.sub(r'^https?://', '', u).split('/')[0].split(':')[0]


def resolves(h):
    try:
        socket.getaddrinfo(h, None)
        return True
    except Exception:
        return False


def head(url):
    p = subprocess.run(
        ['curl', '-sL', '-m', '20', '--insecure', '--compressed', '-A', UA,
         '-o', '/dev/null', '-w', '%{http_code}'], capture_output=True) \
        if False else subprocess.run(
        ['curl', '-sL', '-m', '20', '--insecure', '--compressed', '-A', UA,
         '-o', '/dev/null', '-w', '%{http_code}', url], capture_output=True)
    try:
        return int(p.stdout.decode().strip() or 0)
    except ValueError:
        return 0


txt = io.open(ROOT + 'data/websites.js', encoding='utf-8').read()
rows = [(m.group(1), m.group(2), m.group(3)) for m in
        re.finditer(r"^'([^']+)':\['([^']+)','([^']+)'\],$", txt, re.M)]
# The estate names, read out of chateaux.js so this needs nothing
# but the repository.
src = io.open(ROOT + 'data/chateaux.js', encoding='utf-8').read()
names = dict(re.findall(r"id:'([^']+)'[^}]*?name:'((?:[^'\\]|\\.)*)'", src))
print('%d addresses on file' % len(rows))


def judge(r):
    eid, url, tag = r
    h = host_of(url)
    if not resolves(h) and not resolves('www.' + h):
        return (eid, url, tag, 'nohost', 0)
    code = head(url)
    if code in (404, 410):
        return (eid, url, tag, 'notfound', code)
    if code == 0:
        return (eid, url, tag, 'blocked', code)
    if code >= 500:
        return (eid, url, tag, 'error', code)
    return (eid, url, tag, 'ok', code)


with cf.ThreadPoolExecutor(max_workers=12) as ex:
    out = list(ex.map(judge, rows))

json.dump([{'id': a, 'url': b, 'tag': c, 'state': d, 'code': e}
           for a, b, c, d, e in out],
          io.open(os.path.join(ROOT, 'reports', 'website-audit.json'), 'w',
                    encoding='utf-8'),
          ensure_ascii=False, indent=1)

c = collections.Counter(x[3] for x in out)
for k in ('ok', 'blocked', 'notfound', 'error', 'nohost'):
    print('   %-9s %d' % (k, c[k]))

o = io.open(os.path.join(ROOT, 'reports', 'website-audit.txt'), 'w',
            encoding='utf-8', newline='')
for s in ('notfound', 'error', 'nohost', 'blocked'):
    rs = sorted([x for x in out if x[3] == s])
    o.write('\n===== %s: %d\n' % (s, len(rs)))
    for eid, url, tag, st, code in rs:
        o.write('  %-36s %-44s %-6s %s\n'
                % (deacc(names.get(eid, eid))[:36], url[:44], tag, code or ''))
o.close()
print('\ndetail in reports/website-audit.txt')
