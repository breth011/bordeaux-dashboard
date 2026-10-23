# -*- coding: utf-8 -*-
"""Documents that state something no record holds.

    python tools/unread.py                     every estate
    python tools/unread.py --estate talbot
    python tools/unread.py --field alc --field ph
    python tools/unread.py --show 3            and quote the sentence

read-fiches.py reports what it reads. This reports what it does not:
it goes at the documents with a set of probes that are deliberately
looser than the reader's own patterns, and lists every field a
document plainly states that the record for that vintage does not
hold.

The difference between the two is the whole point. The reader has to
be right - a wrong figure is worse than a missing one, and every gate
and guard in sheetreader.py exists because one got through. A probe
here only has to be suggestive, because nothing it finds is written
anywhere; it is a list of places to look.

Three estates found by hand this week are what it is for, and each
was the same shape - plenty of documents, almost nothing read:

  Pouget      5 documents, 2 datapoints. Its fiches are printed on
              Boyd-Cantenac's letterhead and the critic scores run
              into the heading, so every label was refused.
  Talbot     27 documents, 16 datapoints. Its sheet is two columns
              and the flat reading puts every label first and every
              value after, so "Degree" sits 200 characters from
              "13 % vol".
  d'Armailhac 46 documents, 2 blends. Its pages head the assemblage
              "Varietal mix", which BLEND_ANCHOR did not know.

Found one at a time, from addresses somebody sent me. This asks the
question of all 468 at once.

What it cannot tell you is whether the reader is wrong to refuse
something: a press dossier states an alcohol and is still not a
vintage's sheet. The refusals are printed beside the findings for
that reason - an estate whose documents are all refused is a
different problem from one whose documents are read and thin.
"""
import argparse
import collections
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, ROOT + 'tools')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import sheetreader as sr

# The probes. Loose on purpose: each one only has to show that the
# document talks about the field at all, close enough to a figure that
# a reader could have taken it.
PROBE = (
    ('alc', re.compile(
        r'(?i)(?:\b\d{1,2}(?:[.,]\d)?\s*%\s*(?:alc\.?\s*/?\s*)?vol'
        r'|(?:alcool|alcohol|degr[eé]|titre\s+alcoom)[^.\n]{0,40}'
        r'\d{1,2}(?:[.,]\d)?\s*%)')),
    ('ph', re.compile(r'(?i)\bpH\b[^.\n]{0,20}?[2-4][.,]\d')),
    ('yld', re.compile(
        r'(?i)(?:\d{1,2}(?:[.,]\d)?\s*(?:hl\s*/\s*ha|hectolitres?)'
        r'|rendement|yield)[^.\n]{0,30}\d')),
    ('months', re.compile(
        r'(?i)\b\d{1,2}\s*(?:mois|months)\b[^.\n]{0,40}'
        r'(?:barriqu|f[uû]t|barrel|oak|bois|[eé]levage|ageing|aging)')),
    ('oak', re.compile(
        r'(?i)\d{1,3}\s*%[^.\n]{0,30}'
        r'(?:bois\s+neuf|f[uû]ts?\s+neufs?|barriques?\s+neuves?|'
        r'new\s+(?:oak|barrel|wood|french))')),
    # No label: Talbot's "Harvests" is two hundred characters from
    # "From September 13th to October 6th". A day and a month, or a
    # month to a month, is what a date in a wine sheet is for.
    ('pick', re.compile(
        r'(?i)(?:\b\d{1,2}\s*(?:er)?\s*(?:janvier|f[eé]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[eé]cembre|january|february|march|april|may|june|july|august|september|october|november|december)\\b|(?:from|du|des)\s+\d{0,2}\s*(?:janvier|f[eé]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[eé]cembre|january|february|march|april|may|june|july|august|september|october|november|december)\\b[^.\\n]{0,30}(?:to|au|a)\s+\d{0,2}\s*(?:janvier|f[eé]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[eé]cembre|january|february|march|april|may|june|july|august|september|october|november|december))')),
    # No label either: two or more variety-and-percentage pairs, in
    # whichever order the sheet writes them.
    ('blend', re.compile(
        r'(?i)(?:\d{1,3}\s*%\s*(?:de\s+)?(?:cabernets?\s*(?:sauvignons?|francs?)?|merlots?|petits?\s*verdots?|malbec|c[oô]t|carm[eé]n[eè]re|s[eé]millons?|sauvignons?\s*(?:blancs?|gris)?|muscadelles?)|(?:cabernets?\s*(?:sauvignons?|francs?)?|merlots?|petits?\s*verdots?|malbec|c[oô]t|carm[eé]n[eè]re|s[eé]millons?|sauvignons?\s*(?:blancs?|gris)?|muscadelles?)\\s*:?\\s*\\d{1,3}\\s*%)[^%]{0,90}?(?:\d{1,3}\s*%\s*(?:de\s+)?(?:cabernets?\s*(?:sauvignons?|francs?)?|merlots?|petits?\s*verdots?|malbec|c[oô]t|carm[eé]n[eè]re|s[eé]millons?|sauvignons?\s*(?:blancs?|gris)?|muscadelles?)|(?:cabernets?\s*(?:sauvignons?|francs?)?|merlots?|petits?\s*verdots?|malbec|c[oô]t|carm[eé]n[eè]re|s[eé]millons?|sauvignons?\s*(?:blancs?|gris)?|muscadelles?)\\s*:?\\s*\\d{1,3}\\s*%)')),
    ('taste', re.compile(
        r'(?i)(?:d[eé]gustation|tasting\s+note|commentaire\s+de\s+'
        r'd[eé]gustation|nez\b|palais\b|\bpalate\b|\bnose\b|robe\b)')),
    ('note', re.compile(
        r'(?i)(?:conditions?\s+climatiques?|climatolog|'
        r'weather|m[eé]t[eé]o|growing\s+season|le\s+mill[eé]sime|'
        r'd[eé]bourrement|floraison|v[eé]raison|budbreak|flowering)')),
)
READABLE = ('grand', 'combined', 'page')
NOT_A_FIELD = frozenset(('src', 'via', 'url', 'xsrc', 'ttl', 'ntl',
                         'wtl', 'dtl', 'ftl'))
ROW = re.compile(r"(?m)^'([a-z0-9-]+)\|(\d{4})':\{(.*)\},$")


def held_fields(body):
    """The fields a record body carries, prose and quotes skipped."""
    out, depth, i = set(), 0, 0
    while i < len(body):
        c = body[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
        elif c == "'":
            j = i + 1
            while j < len(body):
                if body[j] == '\\':
                    j += 2
                    continue
                if body[j] == "'":
                    break
                j += 1
            i = j + 1
            continue
        elif depth == 0 and (i == 0 or body[i - 1] == ','):
            m = re.match(r'([a-z]+)[:\{]', body[i:])
            if m:
                out.add(m.group(1))
        i += 1
    return out - NOT_A_FIELD


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estate', action='append', default=[])
    ap.add_argument('--field', action='append', default=[])
    ap.add_argument('--show', type=int, default=0,
                    help='quote this many of the sentences found')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--sheets', action='store_true',
                    help='score each document: used of stated')
    ap.add_argument('--worst', type=int, default=40,
                    help='how many sheets to print (default 40)')
    a = ap.parse_args()
    fields = [f for f, _ in PROBE if not a.field or f in a.field]

    man = json.load(io.open(ROOT + 'data/sources.json',
                            encoding='utf-8'))
    rows = [s for s in man['sheets'] if s.get('role') in READABLE
            and s.get('estate') and s.get('year')]
    if a.estate:
        rows = [s for s in rows if s.get('estate') in a.estate]
    if a.limit:
        rows = rows[:a.limit]

    recs = {}
    t = io.open(ROOT + 'data/fiches.js', encoding='utf-8').read()
    for m in ROW.finditer(t):
        recs[(m.group(1), int(m.group(2)))] = held_fields(m.group(3))

    E = sr.estates(ROOT)
    says = collections.defaultdict(set)      # (estate, yr) -> fields
    persheet = []                            # one row per document
    quote = {}
    refused = collections.Counter()
    byestate = collections.Counter()
    docs = collections.Counter()
    read = collections.Counter()

    print('reading %d document(s)' % len(rows))
    for n, s in enumerate(rows, 1):
        if n % 400 == 0:
            print('   ... %d' % n)
        eid, yr = s.get('estate'), int(s.get('year'))
        docs[eid] += 1
        path = sr.path_of(ROOT, s)
        if not path or not os.path.exists(path):
            continue
        try:
            text = ' '.join(sr.flat(path).split())
        except Exception:
            continue
        e = E.get(eid) or {}
        # Is the reader refusing this document outright? That is a
        # different complaint from reading it and finding little.
        try:
            got, how = sr.fields_of(
                path, grand=e.get('name'),
                others=list(e.get('cuvees') or ()),
                second=e.get('second'), cat=e.get('cat'),
                filename=s.get('file'), year=yr)
        except Exception:
            got, how = {}, {}
        if 'refused' in how:
            refused[how['refused'][:46]] += 1
            continue
        read[eid] += 1
        have = recs.get((eid, yr), set())
        stated, unused = [], []
        for f, rx in PROBE:
            if f not in fields:
                continue
            if not rx.search(text):
                continue
            stated.append(f)
            if f in have or f in got:
                continue
            unused.append(f)
            m = rx.search(text)
            says[(eid, yr)].add(f)
            byestate[eid] += 1
            quote.setdefault((eid, yr, f),
                             (s.get('file'), text[max(0, m.start() - 40):
                                                  m.end() + 40]))
        if stated:
            persheet.append((len(stated) - len(unused), len(stated),
                             eid, yr, s.get('file'), unused))

    print()
    print('DOCUMENTS THAT STATE SOMETHING NO RECORD HOLDS')
    print('%d vintage(s) across %d estate(s); %d field(s) in all'
          % (len(says), len(byestate), sum(byestate.values())))
    print()
    perfield = collections.Counter()
    for fs in says.values():
        for f in fs:
            perfield[f] += 1
    print('   by field:')
    for f, _ in PROBE:
        if perfield.get(f):
            print('      %-8s %4d vintage(s)' % (f, perfield[f]))
    print()
    print('   by estate, worst first — documents read, fields unread:')
    print('      %-28s %5s %6s %7s' % ('estate', 'docs', 'read',
                                       'unread'))
    for eid, n in byestate.most_common(30):
        print('      %-28s %5d %6d %7d'
              % (eid[:28], docs[eid], read[eid], n))
    print()
    if refused:
        print('   refused outright, and so not counted above:')
        for k, n in refused.most_common(10):
            print('      %-50s %4d' % (k, n))
    if a.sheets and persheet:
        used = sum(p[0] for p in persheet)
        tot = sum(p[1] for p in persheet)
        print()
        print('EVERY SHEET, SCORED: DATAPOINTS USED OF DATAPOINTS '
              'STATED')
        print('   %d of %d across %d document(s) — %d%%'
              % (used, tot, len(persheet),
                 round(100.0 * used / max(tot, 1))))
        print()
        whole = [p for p in persheet if p[0] == p[1]]
        print('   %d document(s) give up everything they state'
              % len(whole))
        print('   %d give up none of it'
              % len([p for p in persheet if p[0] == 0]))
        print()
        print('   worst first, by how much is going unused:')
        print('      %-26s %-5s %-34s %7s  %s'
              % ('estate', 'year', 'sheet', 'used', 'not used'))
        persheet.sort(key=lambda p: (-(p[1] - p[0]),
                                     p[0] / float(p[1]), p[2]))
        for u, n, eid, yr, fn, miss in persheet[:a.worst]:
            print('      %-26s %-5s %-34s %3d/%-3d  %s'
                  % (eid[:26], yr, (fn or '')[:34], u, n,
                     ','.join(miss)))

    if a.show:
        print()
        print('   a few of the sentences:')
        for i, ((eid, yr, f), (fn, q)) in enumerate(sorted(
                quote.items())):
            if i >= a.show:
                break
            print('      %s|%s %s  (%s)' % (eid, yr, f, (fn or '')[:40]))
            print('         ...%s' % q)


if __name__ == '__main__':
    main()
