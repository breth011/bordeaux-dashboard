# -*- coding: utf-8 -*-
"""Does the address on file belong to the estate it is filed under?

    python tools/whose-site.py                   every estate with a site
    python tools/whose-site.py --classified      the 61 only
    python tools/whose-site.py --estate belgrave
    python tools/whose-site.py --guess           also probe likely domains

audit-websites.py asks whether an address still answers. This asks a
different question, and it came out of two estates in one afternoon:

    belgrave           dourthe.com, from the UGCB directory
    grand-puy-lacoste  grand-puy-lacoste.com, from the same

Both answered. Both were somebody else's. Dourthe owns Belgrave and
publishes nothing per-vintage for it, so harvest.py asked that site
and came back empty, as it had every time. Grand-Puy-Lacoste's own
site is chateau-grand-puy-lacoste.com, and the crawler was refusing
all eighteen of its vintage links as another host's - "0 candidate
pages", which reads as an estate that publishes nothing and was an
address that was wrong.

Correcting the two gave 75 vintage pages and 7 fiches, and took one
estate from the worst of the 61 to the middle. The cost of the fault
is that it is invisible: a wrong address and a silent estate look
exactly alike from here.

HOW IT DECIDES

It asks what the page calls itself - its <title>, its og:site_name,
its first heading - and looks for the estate's name in that. Nothing
more clever, because nothing more clever is needed: a chateau's home
page says whose it is in the first hundred characters, and the two
that were wrong said "Dourthe" and "Grand-Puy-Lacoste" is not in
"Dourthe".

An estate whose name is absent is reported, not corrected. Some will
be right anyway - a group site that does carry the estate's pages, a
name written differently - and this file's provenance discipline is
that an address is changed by a person who has read the page.

With --guess it also tries the domains an estate is likely to own -
chateau-<name>.com and the rest - and says which of them answer and
name the estate. That is a suggestion to check, not an answer.
"""
import argparse
import collections
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import sheetreader as sr

UA = {'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                     'AppleWebKit/537.36 (KHTML, like Gecko) '
                     'Chrome/127.0 Safari/537.36')}
PAUSE = 0.7
TIMEOUT = 20
# What a page calls itself.
TITLE = re.compile(r'(?is)<title[^>]*>(.*?)</title>')
SITENAME = re.compile(
    r'(?is)<meta[^>]+property=["\']og:site_name["\'][^>]+'
    r'content=["\']([^"\']*)')
H1 = re.compile(r'(?is)<h1[^>]*>(.*?)</h1>')
TAG = re.compile(r'(?s)<[^>]+>')
# What this machine's own network says when it answers instead of the
# site. Nothing is learnt about the address from these, so they go
# with the timeouts and not with the wrong answers.
INTERCEPTED = re.compile(
    r'(?i)browser\s+isolation|zscaler|access\s+denied|'
    r'attention\s+required|cloudflare|just\s+a\s+moment|'
    r'are\s+you\s+a\s+robot|captcha')
# Words that are in every estate's name and so identify none of them.
EMPTY = set("""chateau château domaine clos cru grand vin vins wine
wines de du des la le les et and the of a l'""".split())


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.status, r.read(200000).decode('utf-8', 'replace')


def says_of_itself(body):
    """The three places a page names itself, joined."""
    bits = []
    for rx in (TITLE, SITENAME, H1):
        m = rx.search(body)
        if m:
            bits.append(TAG.sub(' ', m.group(1)))
    return ' '.join(' '.join(bits).split())[:200]


def words_of(name):
    """The parts of an estate's name that identify it."""
    out = []
    for w in re.split(r'[^a-z0-9]+', sr.norm(name or '')):
        if w and w not in EMPTY and len(w) > 2:
            out.append(w)
    return out


def names_it(said, name):
    """Does what the page calls itself contain the estate's name?

    Every identifying word has to be there. "Grand-Puy-Lacoste" is
    not in "Dourthe", and "Belgrave" is not either; a site that does
    carry the estate will almost always put its name in the title.
    """
    w = words_of(name)
    if not w:
        return True
    s = sr.norm(said)
    # One distinctive word is enough, because an estate shortens its
    # own name: Pichon Longueville Baron's site says "Chateau Pichon
    # Baron", and wanting every word called that somebody else's.
    # Croizet-Bages has neither "croizet" nor "bages" in "Domaines
    # Quie", which is the kind of answer this is looking for.
    return any((' ' + x) in s or s.startswith(x) for x in w)


def candidates(name):
    base = '-'.join(words_of(name))
    tight = ''.join(words_of(name))
    out = []
    for host in ('chateau-%s.com' % base, '%s.com' % base,
                 'chateau%s.com' % tight, '%s.com' % tight,
                 'chateau-%s.fr' % base, '%s.fr' % base):
        if host not in out:
            out.append(host)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estate', action='append', default=[])
    ap.add_argument('--classified', action='store_true')
    ap.add_argument('--guess', action='store_true',
                    help='probe the domains an estate likely owns')
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()

    sites = {}
    t = io.open(ROOT + 'data/websites.js', encoding='utf-8').read()
    for m in re.finditer(r"^'([a-z0-9-]+)'\s*:\s*\['([^']*)','([^']*)'",
                         t, re.M):
        sites[m.group(1)] = (m.group(2), m.group(3))

    E = sr.estates(ROOT)
    want = list(sites)
    if a.classified:
        ch = io.open(ROOT + 'data/chateaux.js', encoding='utf-8').read()
        ids = set(re.findall(r"id:'([a-z0-9-]+)'", ch))
        want = [e for e in want if e in ids]
    if a.estate:
        want = [e for e in want if e in a.estate]
    want.sort()
    if a.limit:
        want = want[:a.limit]

    man = json.load(io.open(ROOT + 'data/sources.json',
                            encoding='utf-8'))
    docs = collections.Counter(s.get('estate') for s in man['sheets'])

    print('asking %d site(s) whose they are' % len(want))
    bad, unseen, mute, fine = [], [], [], 0
    for i, eid in enumerate(want, 1):
        url, how = sites[eid]
        name = (E.get(eid) or {}).get('name') or eid
        time.sleep(PAUSE)
        try:
            st, body = get(url)
        except Exception as ex:
            unseen.append((eid, url, how, type(ex).__name__))
            continue
        said = says_of_itself(body)
        if INTERCEPTED.search(said):
            unseen.append((eid, url, how, 'intercepted here'))
            continue
        if not said.strip():
            mute.append((eid, url, how, docs.get(eid, 0)))
            continue
        if names_it(said, name):
            fine += 1
            continue
        bad.append((eid, name, url, how, said, docs.get(eid, 0)))
        if i % 25 == 0:
            print('   ... %d' % i)

    print()
    print('THE ADDRESS DOES NOT NAME THE ESTATE - %d of %d'
          % (len(bad), len(want)))
    print('   %d name it, %d could not be reached, %d said nothing'
          % (fine, len(unseen), len(mute)))
    print()
    bad.sort(key=lambda r: r[5])
    for eid, name, url, how, said, n in bad:
        print('   %-26s %3d doc(s)  %s  [%s]'
              % (eid[:26], n, url[:44], how))
        print('        page calls itself: %s' % said[:92])
        if a.guess:
            for host in candidates(name):
                for scheme in ('https://www.', 'https://'):
                    try:
                        st, body = get(scheme + host)
                    except Exception:
                        continue
                    s2 = says_of_itself(body)
                    mark = 'NAMES IT' if names_it(s2, name) else 'no'
                    print('        %-8s %s%-34s %s'
                          % (mark, scheme, host, s2[:58]))
                    break
            time.sleep(PAUSE)
    if mute:
        print()
        print('   THE PAGE NAMED NOBODY - %d. Not evidence either way;'
              ' the page has no title, no og:site_name and no heading'
              ' this could read.' % len(mute))
        for eid, url, how, n in sorted(mute, key=lambda r: -r[3])[:20]:
            print('      %-26s %3d doc(s)  %-42s [%s]'
                  % (eid[:26], n, url[:42], how))
    if unseen:
        print()
        print('   COULD NOT BE REACHED - %d' % len(unseen))
        for eid, url, how, why in unseen[:20]:
            print('      %-26s %-40s %s' % (eid[:26], url[:40], why))


if __name__ == '__main__':
    main()
