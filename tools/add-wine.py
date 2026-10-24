# -*- coding: utf-8 -*-
"""Add one of an estate's other wines to BDX_CUVEE_WINES.

    python tools/add-wine.py --estate margaux \
        --name "Pavillon Rouge du Chateau Margaux" --role second --colour red
    python tools/add-wine.py --estate margaux --name "..." --apply

BDX_CUVEE_WINES in data/cuvees.js is the authority on which wines an
estate makes, and three separate things read it:

  whose_sheet puts the names in `others` and refuses a sheet that
  names one of them, which is what keeps a second wine's figures out
  of the grand vin's record;
  read-fiches.py --cuvees takes the slug from it, so a record is
  keyed on a slug this file chose;
  the drawer offers the wine beside the grand vin.

So a wine missing from it is invisible three ways at once, and its
pages either sit unread or go into the grand vin. Aile d'Argent cost
Mouton 23 misfiled fields that way.

WHY A TOOL AND NOT AN EDIT

The slug. The app looks a record up as ch.id|slug|year with the slug
from this list, and the slugs already in it are not one rule's output
- "Les Charmes de Magnol" is charmes-de-magnol where "Les Brulieres
de Beychevelle" is les-brulieres-de-beychevelle, and 33 of the first
116 cannot be derived from their name at all. So a new wine takes
sr.slug's form, and this checks the result collides with nothing the
estate already has.

The colour, which is not decoration: whose_sheet calls wrong_colour
with it before anything is read, so a white entered as red has its
own sheets refused for saying Blanc. Four wines were wrong that way.
This refuses a colour the name contradicts.
"""
import io, os, re, sys, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
P = ROOT + 'data/cuvees.js'

WINE = re.compile(r"\{slug:'((?:[^'\\]|\\.)*)',name:'((?:[^'\\]|\\.)*)'"
                  r",role:'([a-z]*)',colour:'([a-z]*)'\}")
SAYS_WHITE = re.compile(r'(?i)\b(?:blancs?|white|bianco)\b')
SAYS_ROSE = re.compile(u'(?i)\\b(?:ros[eé]s?|rosado|clairet)\\b')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estate', required=True)
    ap.add_argument('--name', required=True,
                    help="the wine's name as the estate writes it")
    ap.add_argument('--role', default='other',
                    choices=('second', 'other'))
    ap.add_argument('--colour', default='red',
                    choices=('red', 'white', 'sweet', 'rose'))
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()

    name = a.name
    # The name contradicting the colour is the mistake this guards
    # against, and it is worth refusing rather than warning: the four
    # that were wrong had been wrong for months.
    if SAYS_ROSE.search(name) and a.colour != 'rose':
        print('the name says rose and --colour is %s; '
              'pass --colour rose' % a.colour)
        return 2
    if SAYS_WHITE.search(name) and a.colour not in ('white', 'sweet'):
        print('the name says blanc and --colour is %s; '
              'pass --colour white (or sweet)' % a.colour)
        return 2

    src = io.open(P, encoding='utf-8').read()
    head, rest = src.split('window.BDX_CUVEE_WINES = {\n', 1)
    wbody, tail = rest.split('};\n', 1)

    line = re.search(r"(?m)^'" + re.escape(a.estate) + r"':\[(.*)\],$",
                     wbody)
    have = [m.groupdict() if False else
            {'slug': m.group(1), 'name': m.group(2).replace("\\'", "'"),
             'role': m.group(3), 'colour': m.group(4)}
            for m in WINE.finditer(line.group(1) if line else '')]

    for w in have:
        if sr.packed(w['name']) == sr.packed(name):
            print('already listed: %s (%s, %s, %s)'
                  % (w['name'], w['slug'], w['role'], w['colour']))
            return 0

    slug = sr.slug(name)
    if not slug:
        print('that name gives no slug')
        return 2
    if slug in set(w['slug'] for w in have):
        print('slug %s is already taken at this estate' % slug)
        return 2

    have.append({'slug': slug, 'name': name, 'role': a.role,
                 'colour': a.colour})
    have.sort(key=lambda w: w['slug'])
    rendered = "'%s':[%s]," % (a.estate, ','.join(
        "{slug:'%s',name:'%s',role:'%s',colour:'%s'}"
        % (w['slug'], w['name'].replace("'", "\\'"), w['role'], w['colour'])
        for w in have))

    print('%s now lists:' % a.estate)
    for w in have:
        mark = ' <- new' if w['slug'] == slug else ''
        print('   %-40s %-7s %-6s %s%s'
              % (w['name'][:40], w['role'], w['colour'], w['slug'], mark))

    if not a.apply:
        print('\nnothing written; pass --apply')
        return 0

    if line:
        wbody = wbody[:line.start()] + rendered + wbody[line.end():]
    else:
        wbody = wbody.rstrip('\n') + '\n' + rendered + '\n'
    io.open(P, 'w', encoding='utf-8', newline='').write(
        head + 'window.BDX_CUVEE_WINES = {\n' + wbody + '};\n' + tail)
    print('\nwritten to data/cuvees.js')
    print('now run: python tools/refile-wine.py --estate %s' % a.estate)
    return 0


if __name__ == '__main__':
    sys.exit(main())
