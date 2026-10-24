# -*- coding: utf-8 -*-
"""Recover the address of a sheet already on disk, so the app can link.

    python tools/recover-urls.py                 report only
    python tools/recover-urls.py --apply         write data/sources.json
    python tools/recover-urls.py --estate lafite one estate

The dashboard shows, beside each vintage, a link to the sheet it was
read from. build-fiche-links makes those links out of the manifest's
url field, and 1,794 records cannot link because the sheet they cite
has no address recorded: the fetcher kept the file and not where it
came from.

The file is on disk, so its address is recoverable rather than lost.
Two ways, and this tool uses the honest one.

THE GUESS, WHICH THIS DOES NOT DO. Where one of an estate's files is
known to live at https://batailley.com/wp-content/uploads/2025/11/, a
sibling in the same folder probably lives beside it. 768 records could
be given a link that way, and some of those links would be wrong. A
404 in the app is worse than no link at all, because the reader has no
way to tell a broken link from a missing sheet.

THE ANSWER, WHICH IT DOES. A WordPress site publishes
/wp-json/wp/v2/media, which gives the source_url of every file it
holds, a hundred per request. That recovers the address and proves it
in the same breath, and one request per hundred files is politer than
one request per guess. harvest.py has read those libraries since it
was written; this asks them for addresses rather than for documents,
and downloads nothing.

Matching is by filename, and a filename is not unique: 888 of them
exist in more than one folder, because an owner publishes the same
document under several properties. So a library's answer is only
applied to rows whose own estate was asked - Lafite's library may not
name Duhart-Milon's copy as Duhart-Milon's.
"""
import argparse
import collections
import importlib.util
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, ROOT + 'tools')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def load_harvest():
    """harvest.py, for its media_library() and its polite fetcher.

    Its name has a hyphen in it, so it cannot be imported the usual
    way. Loaded rather than copied, so that a fix to the fetcher - the
    percent-encoding, the idna host, the checkpointing - is a fix here
    too.
    """
    spec = importlib.util.spec_from_file_location(
        'harvest', ROOT + 'tools/harvest.py')
    mod = importlib.util.module_from_spec(spec)
    sys.argv = [sys.argv[0]]        # harvest parses argv at import
    spec.loader.exec_module(mod)
    return mod


def sites():
    """The website of each estate, from data/websites.js."""
    out = {}
    t = io.open(ROOT + 'data/websites.js', encoding='utf-8').read()
    for m in re.finditer(r"^'([a-z0-9-]+)':\['([^']*)'", t, re.M):
        if m.group(2).startswith('http'):
            out[m.group(1)] = m.group(2)
    return out


def hosts_known(man):
    """Where an estate's files have been served from before.

    For an estate with no entry in websites.js, an address already in
    the manifest says which site to ask.
    """
    out = collections.defaultdict(collections.Counter)
    for s in man['sheets']:
        u = s.get('url') or ''
        m = re.match(r'(https?://[^/]+)', u)
        if m and s.get('estate'):
            out[s['estate']][m.group(1)] += 1
    return dict((k, v.most_common(1)[0][0]) for k, v in out.items())


def both_hosts(where):
    """The address as recorded, and the same with www. toggled.

    A certificate issued for one form and not the other is a
    common misconfiguration: Grand-Puy Ducasse's www. host fails
    to verify and its bare host serves the library that holds all
    86 of its documents. The recorded form is tried first.
    """
    out = [where]
    if "://www." in where:
        out.append(where.replace("://www.", "://", 1))
    else:
        out.append(re.sub(r"^(https?://)", r"\1www.", where, count=1))
    return [u for u in out if u]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--estate', action='append', default=[])
    ap.add_argument('--limit', type=int, default=0,
                    help='ask this many estates at most')
    a = ap.parse_args()

    man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))

    # What the records cite, because a sheet nothing cites needs no
    # link. 11,307 sheets are in the manifest and 2,213 are cited.
    cited = collections.Counter()
    for line in io.open(ROOT + 'data/fiches.js', encoding='utf-8'):
        m = re.match(r"^'([a-z0-9-]+)\|(\d{4})':\{(.*)\},$", line.rstrip())
        if not m:
            continue
        sm = re.search(r"src:'((?:[^'\\]|\\.)*)'", m.group(3))
        if not sm:
            continue
        for n in [x.strip() for x in re.sub(r'\\(.)', r'\1',
                                            sm.group(1)).split(',')
                  if x.strip()]:
            cited[n] += 1

    # The rows that want an address: cited, and without one.
    want = collections.defaultdict(list)
    for s in man['sheets']:
        if s.get('url') or s['file'] not in cited:
            continue
        if not s.get('estate'):
            continue
        want[s['estate']].append(s)

    site = sites()
    fallback = hosts_known(man)
    order = sorted(want, key=lambda e: -sum(cited[s['file']]
                                            for s in want[e]))
    if a.estate:
        order = [e for e in order if e in a.estate]
    if a.limit:
        order = order[:a.limit]

    print('%d estates have cited sheets with no address; %d records '
          'between them' % (len(want), sum(cited[s['file']]
                                           for v in want.values()
                                           for s in v)))
    print('asking %d of them' % len(order))
    print()

    h = load_harvest()
    filled, why = 0, collections.Counter()
    for eid in order:
        where = site.get(eid) or fallback.get(eid)
        if not where:
            why['no website on record, and no address to infer one from'] += 1
            continue
        urls, last = None, None
        for host in both_hosts(where):
            try:
                urls = h.media_library(host)
            except Exception as e:
                last = str(e)[:30]
                continue
            if urls:
                where = host
                break
        if urls is None:
            why['the library could not be read: %s' % last] += 1
            continue
        if not urls:
            why['the site holds no media library'] += 1
            continue
        byname = {}
        for u in urls:
            byname.setdefault(os.path.basename(
                u.split('?')[0]).lower(), u)
        got = 0
        for s in want[eid]:
            u = byname.get(s['file'].lower())
            if u:
                s['url'] = u
                got += 1
        filled += got
        print('   %-34s %4d of %3d wanted, from %s'
              % (eid[:34], got, len(want[eid]), where[:38]))
        if not got:
            why['the library does not name any of the wanted files'] += 1

    print()
    print('%d addresses recovered' % filled)
    for k, n in why.most_common():
        print('   %-56s %d estates' % (k[:56], n))

    if a.apply and filled:
        io.open(ROOT + 'data/sources.json', 'w', encoding='utf-8',
                newline='').write(json.dumps(man, ensure_ascii=False,
                                             indent=1))
        print('\nwritten to data/sources.json; now run '
              'tools/build-fiche-links.py')
    elif filled:
        print('\nnothing written; pass --apply')


if __name__ == '__main__':
    main()
