# -*- coding: utf-8 -*-
"""Lift every URL the manifest knows out of prose and into a field.

    python tools/promote-urls.py


A sheet's address is the only thing that makes it re-fetchable, and
713 of them were written into the note as "found at https://..." where
nothing can read them. A note is for a human; a field is for the
fetcher. This moves them, leaves the note alone otherwise, and reports
how much of the manifest can and cannot be re-fetched.

It is safe to run twice: a sheet that already has a url is left as it
is.
"""
import io, json, os, re, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
FOUND = re.compile(r'https?://[^\s;,)\]]+')

import sys
sys.path.insert(0, ROOT + 'tools')
import sheetreader as sr

man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))

# fiches.js records the page a record was read from, which is the sheet's
# own address whenever that sheet is a crawled page.
page_url = {}
t = io.open(ROOT + 'data/fiches.js', encoding='utf-8').read()
for line in t.split(chr(10)):
    u = re.search(r"url:'(https?://[^']+)'", line)
    s = re.search(r"src:'([^']+)'", line)
    if u and s:
        page_url.setdefault(s.group(1), u.group(1))

# Where every crawled page is on disk, so its own first line can be
# read.
where = {}
for root, dirs, files in os.walk(ROOT + 'sources'):
    for f in files:
        where.setdefault(f, os.path.join(root, f))


def url_on_the_page(row):
    """The address the crawler wrote on a page's first line.

    Resolved by the row's folder: the same page is saved under several
    of an owner's properties, and the wrong copy carries the wrong
    address.
    """
    p = sr.path_of(ROOT, row, where)
    if not p or p.lower().endswith(('.pdf', '.doc', '.docx', '.xls',
                                    '.xlsx')):
        return None
    try:
        with io.open(p, encoding='utf-8', errors='replace') as fh:
            first = fh.readline().strip()
    except Exception:
        return None
    return first if first[:4].lower() == 'http' else None


moved, from_rec, from_page, already, without = (
    0, 0, 0, 0, collections.Counter())
for s in man['sheets']:
    if s.get('url'):
        already += 1
        continue
    m = FOUND.search(s.get('note') or '')
    if m:
        s['url'] = m.group(0)
        moved += 1
    elif s['file'] in page_url:
        s['url'] = page_url[s['file']]
        from_rec += 1
    elif url_on_the_page(s):
        s['url'] = url_on_the_page(s)
        from_page += 1
    else:
        s['url'] = None
        without[s.get('how') or 'no method recorded'] += 1

man['note'] = (man.get('note') or '').rstrip()
io.open(ROOT + 'data/sources.json', 'w', encoding='utf-8', newline='').write(
    json.dumps(man, ensure_ascii=False, indent=1))

print('%d sheets' % len(man['sheets']))
print('   %d already had a url' % already)
print('   %d lifted out of the note' % moved)
print('   %d taken from the record that cites them' % from_rec)
print('   %d read off the page\u2019s own first line' % from_page)
print('   %d have no address, by how they were found:' % sum(without.values()))
for k, n in without.most_common():
    print('      %-58s %d' % (k[:58], n))
