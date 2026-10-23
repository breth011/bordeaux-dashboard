# -*- coding: utf-8 -*-
"""Merge translations into data/fiches-nl.js.

    python tools/add-dutch.py batch.json
    python tools/add-dutch.py batch.json --dry-run

The batch is a JSON list of {key, field, nl}:

    [{"key": "batailley|2019", "field": "taste",
      "nl": "Donkere, glanzende robe..."}]

Everything the file's own rules require is checked here rather than
trusted to whoever typed the batch:

  the English must exist. A translation of a field the record does
  not hold is what check-language.py spent a morning reporting, and
  six such rows were removed yesterday.

  it must not already be translated. Overwriting a translation
  silently is how the better of two would be lost; a key and field
  already present is refused and named.

  the Dutch must not be the English. A row that came back unchanged
  is a translation that did not happen, and it reads as one in the
  app.

Rows are written in the file's own shape - one record a line, fields
comma-separated, single quotes escaped - and merged into any row the
record already has rather than replacing it.
"""
import argparse
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PROSE = ('taste', 'note', 'food', 'window', 'decant')
ROW = re.compile(r"^'([a-z0-9-]+\|\d{4})':\{(.*)\},$")


def fields_of(body):
    """[(name, 'name:value')] for the top-level fields of a row."""
    spots, depth, i = [], 0, 0
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
            m = re.match(r'([a-z]+)\s*:', body[i:])
            if m and m.group(1) in PROSE:
                spots.append((m.group(1), i))
        i += 1
    out = []
    for n, (name, at) in enumerate(spots):
        end = spots[n + 1][1] - 1 if n + 1 < len(spots) else len(body)
        out.append((name, body[at:end].rstrip(',')))
    return out


def js(s):
    return "'" + s.replace('\\', '\\\\').replace("'", "\\'") + "'"


def english():
    """{key: {field: text}} from fiches.js."""
    out = {}
    t = io.open(ROOT + 'data/fiches.js', encoding='utf-8').read()
    for m in re.finditer(r"(?m)^'([a-z0-9-]+\|\d{4})':\{(.*)\},$", t):
        got = {}
        for name, chunk in fields_of(m.group(2)):
            v = re.match(r"[a-z]+:'((?:[^'\\]|\\.)*)'", chunk)
            if v:
                got[name] = v.group(1)
        out[m.group(1)] = got
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('batch')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--apply', action='store_true',
                    help=argparse.SUPPRESS)
    a = ap.parse_args()

    rows = json.load(io.open(a.batch, encoding='utf-8'))
    en = english()

    src = io.open(ROOT + 'data/fiches-nl.js', encoding='utf-8').read()
    lines = src.split('\n')
    have = {}
    for n, line in enumerate(lines):
        m = ROW.match(line.strip())
        if m:
            have[m.group(1)] = (n, dict(fields_of(m.group(2))))

    added, refused = [], []
    for r in rows:
        key, field, nl = r['key'], r['field'], r['nl'].strip()
        if field not in PROSE:
            refused.append((key, field, 'not a prose field'))
            continue
        src_en = (en.get(key) or {}).get(field)
        if src_en is None:
            refused.append((key, field,
                            'the record holds no English for it'))
            continue
        if key in have and field in have[key][1]:
            refused.append((key, field, 'already translated'))
            continue
        if not nl:
            refused.append((key, field, 'empty'))
            continue
        plain = re.sub(r'\\(.)', r'\1', src_en)
        if nl == plain.strip():
            refused.append((key, field,
                            'identical to the English - not translated'))
            continue
        added.append((key, field, nl))

    print('%d row(s) in the batch: %d to add, %d refused'
          % (len(rows), len(added), len(refused)))
    for key, field, why in refused:
        print('   refused  %-26s %-7s %s' % (key, field, why))
    if a.dry_run or not added:
        for key, field, nl in added[:6]:
            print('   would add %-24s %-7s %s' % (key, field, nl[:60]))
        if a.dry_run:
            print()
            print('--dry-run: wrote nothing')
        return

    for key, field, nl in added:
        chunk = '%s:%s' % (field, js(nl))
        if key in have:
            n, got = have[key]
            got[field] = chunk
            body = ','.join(got[f] for f in PROSE if f in got)
            lines[n] = "'%s':{%s}," % (key, body)
            have[key] = (n, got)
        else:
            # New rows go at the end; the file is not sorted and the
            # reader does not care.
            lines.append("'%s':{%s}," % (key, chunk))
            have[key] = (len(lines) - 1, {field: chunk})

    io.open(ROOT + 'data/fiches-nl.js', 'w', encoding='utf-8',
            newline='').write('\n'.join(lines))
    print()
    print('wrote data/fiches-nl.js - %d field(s) added' % len(added))


if __name__ == '__main__':
    main()
