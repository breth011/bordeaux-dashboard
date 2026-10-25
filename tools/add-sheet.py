# -*- coding: utf-8 -*-
"""Fetch a sheet somebody has pointed at, and register it.

    python tools/add-sheet.py --estate giscours <url>
    python tools/add-sheet.py --estate giscours <url> --apply
    python tools/add-sheet.py --estate montrose <url> --year 2020 --apply

harvest.py discovers: it asks a site's media library, its sitemap and
its pages, and fetches what it finds. That is the right way round for
four hundred estates and one new vintage a year. It has no way to be
handed a single address, and the addresses arrive - somebody reads the
coverage table, goes looking for the worst estate, and finds the sheet
that is missing.

So this takes the URL and does the rest the way harvest.py does it:
fetch, sha1, skip what is already held, and register with the address
it came from and the method that found it - which here is "somebody
provided it", because that is the truth and the manifest's job is to
say where a document came from.

The vintage is read from the document and not from the filename, which
is harvest.py's rule and has been paid for: vin.co names a sheet by
the year in the URL and serves another year's code. Where the document
states no vintage the row is registered with none, and --year is the
way to say so by hand - with the row recording that a person did,
rather than leaving it looking read.

Report only unless --apply, because this fetches from somebody else's
server.
"""
import argparse
import hashlib
import importlib.util
import io
import json
import os
import re
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, ROOT + 'tools')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import sheetreader as sr

MANIFEST = ROOT + 'data/sources.json'
DOCS = ROOT + 'sources/fiches/'


def harvest():
    spec = importlib.util.spec_from_file_location(
        'harvest_mod', ROOT + 'tools/harvest.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def name_of(url, disp):
    """The filename to keep it under.

    Content-Disposition first, where the server gives one, then the
    last segment of the URL - unescaped, because "Fiche+Pouget+2018+
    GB.pdf" arrives with its spaces as plusses.
    """
    if disp:
        m = re.search(r'(?i)filename\*?=(?:UTF-8\'\')?"?([^";]+)', disp)
        if m:
            return os.path.basename(urllib.parse.unquote(m.group(1)))
    tail = urllib.parse.unquote(
        urllib.parse.urlsplit(url).path.split('/')[-1])
    return tail.replace('+', ' ').strip() or 'sheet.pdf'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('url', nargs='+')
    ap.add_argument('--estate', required=True,
                    help='the estate id, as chateaux.js spells it')
    ap.add_argument('--year', type=int, default=None,
                    help='the vintage, when the document states none')
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()

    E = sr.estates(ROOT)
    e = E.get(a.estate)
    if not e:
        print('%s: no such estate in chateaux.js' % a.estate)
        return
    man = json.load(io.open(MANIFEST, encoding='utf-8'))
    held_sha = set(s.get('sha1') for s in man['sheets'] if s.get('sha1'))
    held_url = set(s.get('url') for s in man['sheets'] if s.get('url'))
    h = harvest()

    added = 0
    for url in a.url:
        print('=' * 68)
        print(url)
        if url in held_url:
            for s in man['sheets']:
                if s.get('url') == url:
                    print('   already held as %s, estate=%s year=%s '
                          'role=%s' % (s.get('file'), s.get('estate'),
                                       s.get('year'), s.get('role')))
                    break
            continue
        try:
            blob, final, disp = h.get(url, binary=True)
        except Exception as ex:
            print('   could not fetch: %s' % str(ex)[:70])
            continue
        sha = hashlib.sha1(blob).hexdigest()
        if sha in held_sha:
            for s in man['sheets']:
                if s.get('sha1') == sha:
                    print('   the same bytes are already held as %s '
                          '(estate=%s year=%s)'
                          % (s.get('file'), s.get('estate'),
                             s.get('year')))
                    break
            continue
        name = name_of(final or url, disp)
        folder = DOCS + a.estate + '/'
        print('   %d bytes, would be %s%s' % (len(blob), folder[len(ROOT):],
                                              name))
        if not a.apply:
            continue
        if not os.path.isdir(folder):
            os.makedirs(folder)
        if os.path.exists(folder + name):
            os.remove(folder + name)   # Phase 5 C3: remove first, so a hard-linked twin in sources/ is never overwritten.
        io.open(folder + name, 'wb').write(blob)
        # The vintage from the document, as harvest.py insists.
        yr, how = a.year, 'was provided by hand'
        if yr is None:
            # harvest.py's own reader, on harvest.py's own terms: the
            # vintage comes out of the document, never the filename.
            try:
                import pymupdf
                d = pymupdf.open(folder + name)
                text = re.sub(r'\s+', ' ',
                              ' '.join(p.get_text() for p in d))
                d.close()
                yr, how = h.vintage_of(text)
            except Exception as ex:
                yr, how = None, 'could not be read: %s' % str(ex)[:40]
        if yr is None:
            print('   the document states no vintage; registered with '
                  'none. Pass --year to say.')
        man['sheets'].append({
            'file': name, 'folder': a.estate, 'estate': a.estate,
            'estateName': e.get('name'), 'wine': e.get('name'),
            'slug': None, 'role': 'unknown',
            'colour': e.get('cat'), 'year': yr,
            'bytes': len(blob), 'sha1': sha,
            'how': 'somebody provided the address; the vintage %s' % how,
            'url': final or url,
        })
        held_sha.add(sha)
        held_url.add(final or url)
        added += 1
        print('   registered, year=%s' % yr)

    if not a.apply:
        print()
        print('nothing fetched; pass --apply')
        return
    if not added:
        print()
        print('nothing new')
        return
    io.open(MANIFEST, 'w', encoding='utf-8', newline='').write(
        json.dumps(man, ensure_ascii=False, indent=1))
    print()
    print('%d document(s) registered in data/sources.json' % added)
    print('now run: python tools/read-sheets.py --estate %s' % a.estate)
    print('    and: python tools/read-fiches.py --estate %s --prose'
          % a.estate)


if __name__ == '__main__':
    main()
