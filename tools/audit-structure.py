# -*- coding: utf-8 -*-
"""Phase 3.1: the repository's structure, measured. Read-only.

    python -I tools/audit-structure.py            writes data/audit/phase31-structure.json
    python -I tools/audit-structure.py --check    rebuilds and compares, writes nothing

Three things, each taken from the files rather than from what they say
about themselves:

  tools      every script under tools/: what it reads, what it writes
             (located at the write call, not guessed from its name), whether
             a write is gated by a flag, whether it fetches, which local
             modules it imports;
  data       every file under data/: what kind of thing it is, whether the
             page loads it, which tools read and write it;
  measures   the structural facts the audit's findings rest on: key shapes,
             how provenance names a document, ids derived from names, and so
             on. tools/test-phase31.py checks them.

The report is a view of the repository at one commit. It changes nothing.
"""
import ast
import collections
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
OUT = ROOT + 'data/audit/phase31-structure.json'

# What each data file is. Assigned by reading each file's header and its
# writers; the reasons are in docs/PHASE-3.1-STRUCTURAL-AND-DOMAIN-AUDIT.md
# section 3. `kind` is one of:
#   CANONICAL        values the app shows as the dataset's belief
#   CANONICAL_PROV   provenance of canonical values
#   REFERENCE        hand-curated reference the app shows (lists, prose)
#   MANIFEST         the document register (identity + attribution)
#   EVIDENCE         append-only reader decisions
#   PROPOSAL         dry-run corrections, never applied
#   ANALYSIS         one-off phase outputs (audits, comparisons, censuses)
#   DERIVED_VIEW     generated from other data for the app
#   SCOPE            the Phase 3.0 authoritative universe and its comparisons
#   CONFIG           tool configuration
KINDS = {
    'chateaux.js': 'CANONICAL', 'sauternes.js': 'CANONICAL', 'saintemilion.js': 'CANONICAL',
    'pomerol.js': 'CANONICAL', 'graves.js': 'CANONICAL', 'libournais.js': 'CANONICAL',
    'batch2.js': 'CANONICAL', 'batch3.js': 'CANONICAL', 'batch4.js': 'CANONICAL',
    'crubourgeois.js': 'CANONICAL', 'cruartisan.js': 'CANONICAL', 'rightbank.js': 'CANONICAL',
    'fiches.js': 'CANONICAL', 'cuvees.js': 'CANONICAL', 'plantings.js': 'CANONICAL',
    'terroir.js': 'CANONICAL', 'cellar.js': 'CANONICAL', 'coords.js': 'CANONICAL',
    'websites.js': 'CANONICAL', 'ratings.js': 'CANONICAL', 'overrides.js': 'CANONICAL',
    'fiches-nl.js': 'CANONICAL',
    'field-src.js': 'CANONICAL_PROV', 'cuvee-src.js': 'CANONICAL_PROV',
    'fiches-url.js': 'DERIVED_VIEW', 'cuvee-url.js': 'DERIVED_VIEW',
    'classifications.js': 'REFERENCE', 'appellations.js': 'REFERENCE',
    'geography.js': 'REFERENCE', 'water.js': 'REFERENCE', 'notes.js': 'REFERENCE',
    'notes-nl.js': 'REFERENCE', 'grapes.js': 'REFERENCE', 'grapes-nl.js': 'REFERENCE',
    'vintages.js': 'REFERENCE', 'vintages-nl.js': 'REFERENCE', 'climate.js': 'REFERENCE',
    'phenology.js': 'REFERENCE',
    'sources.json': 'MANIFEST',
    'evidence/': 'EVIDENCE',
    'proposals.jsonl': 'PROPOSAL', 'attribution-candidates.jsonl': 'PROPOSAL',
    'artifact-census.jsonl': 'ANALYSIS', 'wine-identity.jsonl': 'ANALYSIS',
    'echo-baseline.jsonl': 'ANALYSIS', 'provenance-audit.jsonl': 'ANALYSIS',
    'phase26-impact.jsonl': 'ANALYSIS', 'phase28-grand-audit.jsonl': 'ANALYSIS',
    'phase29-grand-dryrun.json': 'ANALYSIS', 'v3-recharacterization.jsonl': 'ANALYSIS',
    'v3-v4-comparison.jsonl': 'ANALYSIS', 'v4-identity-conflicts.jsonl': 'ANALYSIS',
    'v4-v5-comparison.json': 'ANALYSIS',
    'scope/': 'SCOPE', 'audit/': 'ANALYSIS',
    'site-recipes.json': 'CONFIG',
}
CANON_FILES = {f for f, k in KINDS.items() if k in ('CANONICAL', 'CANONICAL_PROV')}
DATA_RE = re.compile(r"""['"]((?:data|sources|reports)/[A-Za-z0-9_./*{}%-]*|"""
                     r"""[a-z0-9-]+\.(?:js|jsonl|json))['"]""")
WRITE_RE = re.compile(r"""open\([^)]*['"](?:w|a|wb|ab|w\+)['"]|\.write_text\(|"""
                      r"""json\.dump\(|shutil\.(?:copy|move)\(|os\.replace\(|os\.rename\(""")
NET_RE = re.compile(r'urllib|urlopen|requests\.|http\.client')


# Writes whose target is built at run time, placed by reading the code.
# Keyed by tool and a fragment of the write line, so a moved line still
# matches and a changed one stops matching (and shows up as unplaced).
PLACED_BY_HAND = {
    ('tools/read-terroir.py', 'io.open(ROOT + path'): ['data/terroir.js', 'data/cellar.js'],
    ('tools/progress.py', "io.open(path, 'w'"): ['progress-history.tsv'],
    ('tools/progress.py', 'io.open(ROOT + MARKDOWN'): ['PROGRESS.md'],
    ('tools/audit-websites.py', 'json.dump('): ['reports/website-audit.json'],
    ('tools/compare-universe.py', "io.open(p, 'w'"): ['data/scope/canonical-discrepancies.jsonl',
                                                       'data/scope/corpus-discrepancies.jsonl'],
    ('tools/evidence_store.py', "io.open(path, 'a'"): ['data/evidence/'],
    ('tools/dryrun-grand-identity.py', "open(p, 'wb')"): ['(temporary file)'],
    ('tools/recheck-sources.py', "io.open(tmp, 'wb')"): ['(temporary file)'],
    ('tools/add-sheet.py', "io.open(folder + name, 'wb')"): ['sources/fiches/'],
    ('tools/harvest.py', "open(path, 'wb')"): ['sources/fiches/'],
    ('tools/crawl-pages.py', 'io.open(folder + name'): ['sources/pages/'],
    ('tools/dryrun-second-identity.py', 'io.open(CACHE'): ['reports/phase26-dryrun-cache.json'],
    ('tools/dryrun-second-identity.py', "json.dump({'changed'"): ['reports/phase26-dryrun-cache.json'],
    ('tools/audit-estate.py', "io.open(p, 'w'"): ['reports/estates/'],
    ('tools/estate-report.py', "io.open(p, 'w'"): ['reports/estates/'],
}


def rel(p):
    return p.replace(ROOT, '').replace(os.sep, '/')


def norm_data(ref):
    """'data/x.js', 'x.js' or 'data/evidence/...' -> a data/ inventory key."""
    r = ref.split('/')
    if r[0] == 'data':
        r = r[1:]
    if not r or not r[0]:
        return None
    if len(r) > 1:
        # The evidence store is one thing; the phase folders hold
        # separate files, and lumping them invents cycles.
        return r[0] + '/' if r[0] == 'evidence' else '/'.join(r)
    return r[0]


def tool_facts(path):
    src = io.open(path, encoding='utf-8').read()
    lines = src.split('\n')
    try:
        tree = ast.parse(src)
        doc = (ast.get_docstring(tree) or '').strip().split('\n')[0]
        imports = sorted({n.name.split('.')[0] for x in ast.walk(tree)
                          if isinstance(x, ast.Import) for n in x.names} |
                         {x.module.split('.')[0] for x in ast.walk(tree)
                          if isinstance(x, ast.ImportFrom) and x.module})
    except SyntaxError:
        doc, imports = '', []
    local = sorted(i for i in imports
                   if os.path.exists(ROOT + 'tools/' + i + '.py'))
    # importlib loads of hyphenated tools (e.g. harvest via spec)
    local += sorted(set(m for m in re.findall(r"tools/([a-z0-9_-]+)\.py", src)
                        if m != os.path.basename(path)[:-3]) - set(local))
    refs = sorted({m.group(1) for m in DATA_RE.finditer(src)})
    # Names bound to data paths - every literal on the line, because
    # `DATA = 'data/cuvees.js' if a.cuvees else 'data/fiches.js'` writes
    # either - so a write through a variable is placed.
    # A name bound from another name inherits its paths (`pf = ROOT + SRCF`).
    bound = {}
    for m in re.finditer(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$', src, re.M):
        lits = [x.group(1) for x in DATA_RE.finditer(m.group(2))]
        for name in re.findall(r'\b([A-Za-z_][A-Za-z0-9_]*)\b', m.group(2)):
            lits += [p for p in bound.get(name, []) if p not in lits]
        if lits and m.group(1) not in bound:
            bound[m.group(1)] = lits
    # A module-level sys.exit: nothing below it runs.
    stop = next((i for i, l in enumerate(lines) if re.match(r'sys\.exit\(', l)), None)
    me = rel(path)
    writes = []
    for i, l in enumerate(lines):
        if not WRITE_RE.search(l) or l.lstrip().startswith('#'):
            continue
        # This file's own patterns are text, not writes.
        if me == 'tools/audit-structure.py' and 'io.open(OUT' not in l:
            continue
        # json.dump(obj, f) into a handle opened on an earlier line is
        # that line's write, already counted.
        if re.search(r'json\.dump\([^,]+,\s*[a-z]\b', l) and not DATA_RE.search(l):
            continue
        hand = [v for (t, frag), v in PLACED_BY_HAND.items() if t == me and frag in l]
        targets = [m.group(1) for m in DATA_RE.finditer(l)]
        how = 'literal'
        if hand:
            targets, how = hand[0], 'placed by hand'
        if not targets:
            # The name opened on this line, not any name the line mentions.
            m = re.search(r'open\(\s*(?:ROOT\s*\+\s*)?([A-Za-z_][A-Za-z0-9_]*)', l)
            names = [m.group(1)] if m else re.findall(r'\b([A-Za-z_][A-Za-z0-9_]*)\b', l)
            for name in names:
                if name in bound:
                    targets, how = bound[name], 'variable'
                    break
        if not targets:
            how = 'unplaced'
        writes.append({'line': i + 1, 'targets': targets, 'how': how,
                       'reachable': stop is None or i < stop})
    flags = sorted(set(re.findall(r"""add_argument\(\s*['"](--(?:apply|write|dry-run))""", src)) |
                   set(re.findall(r"""['"](--(?:apply|write|dry-run))['"]\s+(?:in|not in)\s+sys\.argv""",
                                  src)))
    # Whether a flag stands between the run and each write: an enclosing
    # `if a.apply`/`if a.write`, an earlier `if not a.apply: ... exit` /
    # `if a.dry_run: ... exit` in the same scope, or - for a write inside a
    # helper - the same at every place the helper is called.
    FLAG_IF = re.compile(r'^\s*(?:el)?if\b.*\b(?:a|args)\.(?:apply|write)\b(?!\s*==\s*False)')
    EXIT_IF = re.compile(r'^\s*if\s+(?:not\s+(?:a|args)\.(?:apply|write)|(?:a|args)\.dry_run)\b')

    def indent(s):
        return len(s) - len(s.lstrip())

    def guarded(i, depth=0):
        ind = indent(lines[i])
        j = i - 1
        while j >= 0:
            l = lines[j]
            if l.strip() and not l.lstrip().startswith('#'):
                if indent(l) < ind:
                    ind = indent(l)
                    if FLAG_IF.match(l) and 'not ' not in l.split('if', 1)[1][:6]:
                        return True
                    m = re.match(r'\s*def\s+([A-Za-z_]\w*)', l)
                    if m:
                        if m.group(1) == 'main' or depth > 2:
                            break
                        calls = [k for k, x in enumerate(lines)
                                 if re.search(r'(?<![\w.])%s\(' % m.group(1), x)
                                 and not x.lstrip().startswith('def ')]
                        return bool(calls) and all(guarded(k, depth + 1) for k in calls)
                    # Module level: keep walking up for an earlier exit.
                if EXIT_IF.match(l) and indent(l) <= ind:
                    body = lines[j + 1:j + 12]
                    if any(re.search(r'\b(return|sys\.exit|exit)\b', b) for b in body[:8]):
                        return True
            j -= 1
        return False

    gate = next((i + 1 for i, l in enumerate(lines) if EXIT_IF.match(l) or FLAG_IF.match(l)),
                None)
    for w in writes:
        w['before_gate'] = not guarded(w['line'] - 1)
    live = [t for w in writes if w['reachable'] for t in w['targets']]
    w_data = sorted({norm_data(t) for t in live
                     if t.startswith('data/') or re.match(r'[a-z0-9-]+\.(js|jsonl|json)$', t)}
                    - {None})
    r_data = sorted({norm_data(r) for r in refs
                     if not r.startswith(('reports/', 'sources/')) and norm_data(r)})
    self_ = me == 'tools/audit-structure.py'
    return {
        'tool': me, 'doc': doc[:160], 'imports_local': local,
        'refs': refs, 'reads_data': r_data, 'writes_data': w_data,
        'writes_reports': sorted({t for t in live if t.startswith('reports/')}),
        'writes_sources': sorted({t for t in live if t.startswith('sources/')}),
        'writes_other': sorted({t for t in live if t in ('PROGRESS.md', 'progress-history.tsv')}),
        'write_sites': writes,
        'unreachable_writes': [w['line'] for w in writes if not w['reachable']],
        'unplaced_writes': [w['line'] for w in writes if w['how'] == 'unplaced'],
        'flags': flags,
        'gated': bool(flags),
        'gate_line': gate,
        # Writes of the manifest or canonical data that no flag stops:
        # either the tool has no gate, or the write comes before it.
        'ungated_store_writes': sorted({
            norm_data(t) for w in writes if w['reachable'] and w['before_gate']
            for t in w['targets'] if norm_data(t) in CANON_FILES | {'sources.json'}}),
        # The audit's own source names these things in its patterns.
        'network': (not self_) and bool(NET_RE.search(src)),
        'reads_evidence': (not self_) and ('evidence_store' in local or 'data/evidence' in src),
        'writes_canonical': sorted(set(w_data) & CANON_FILES),
        'basename_first_match': (not self_) and bool(
            re.search(r'setdefault\(\s*f\s*,\s*os\.path\.join\(root,\s*f\)\)', src)),
    }


def data_inventory(tools):
    index = io.open(ROOT + 'index.html', encoding='utf-8').read()
    loaded = set(re.findall(r'src="data/([^"]+)"', index))
    out = {}
    for f in sorted(os.listdir(ROOT + 'data')):
        k = f + '/' if os.path.isdir(ROOT + 'data/' + f) else f
        out[k] = {'kind': KINDS.get(k, 'UNCLASSIFIED'),
                  'loaded_by_app': k in loaded,
                  'read_by': sorted(t['tool'] for t in tools if k in t['reads_data']),
                  'written_by': sorted(t['tool'] for t in tools if k in t['writes_data'])}
    return out


def cycles(tools):
    """Strongly connected sets of tools linked through files they write
    and others read (a tool rewriting its own input is listed apart)."""
    writes = collections.defaultdict(set)
    for t in tools:
        for f in t['writes_data']:
            writes[f].add(t['tool'])
    g = {t['tool']: {w for f in t['reads_data'] for w in writes[f] if w != t['tool']}
         for t in tools}
    index, low, stack, on, comps, n = {}, {}, [], set(), [], [0]

    def strong(v):
        index[v] = low[v] = n[0]
        n[0] += 1
        stack.append(v)
        on.add(v)
        for w in g[v]:
            if w not in index:
                strong(w)
                low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop()
                on.discard(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1:
                comps.append(sorted(comp))

    sys.setrecursionlimit(10000)
    for v in sorted(g):
        if v not in index:
            strong(v)
    inplace = sorted(t['tool'] for t in tools
                     if set(t['writes_data']) & set(t['reads_data']))
    return comps, inplace


def measures():
    m = {}
    S = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))['sheets']
    by = collections.defaultdict(list)
    for s in S:
        by[s['file']].append(s)
    m['manifest'] = {
        'rows': len(S),
        'distinct_folder_file': len({(s['folder'], s['file']) for s in S}),
        'distinct_basename': len(by),
        'distinct_sha1': len({s.get('sha1') for s in S}),
        'rows_with_url': sum(1 for s in S if s.get('url')),
        'rows_without_estate': sum(1 for s in S if not s.get('estate')),
        'basenames_in_more_than_one_row': sum(1 for v in by.values() if len(v) > 1),
        'fields': sorted({k for s in S for k in s}),
        'roles': dict(collections.Counter(s['role'] for s in S)),
    }
    pv = re.compile(r"(\w+):'((?:[^'\\]|\\.)*)'")
    for name in ('field-src.js', 'cuvee-src.js'):
        t = io.open(ROOT + 'data/' + name, encoding='utf-8').read()
        body = t.split('= {', 1)[1]
        pairs = pv.findall(body)
        files = collections.Counter(f for _, f in pairs)
        amb = [f for f in files if len(by.get(f, [])) > 1]
        m[name] = {
            'records': len(re.findall(r"^'[^']+':\{", body, re.M)),
            'field_values': len(pairs),
            'distinct_documents_named': len(files),
            'names_matching_more_than_one_manifest_row': len(amb),
            'of_which_rows_differ_in_bytes': sum(1 for f in amb
                                                 if len({x.get('sha1') for x in by[f]}) > 1),
            'of_which_rows_differ_in_estate': sum(1 for f in amb
                                                  if len({x.get('estate') for x in by[f]}) > 1),
            'field_values_naming_an_ambiguous_document': sum(files[f] for f in amb),
            'names_not_in_manifest': sum(1 for f in files if f not in by),
            'provenance_carries_folder_or_hash': bool(re.search(r"(sha|folder|path):", body)),
        }
    fk = re.findall(r"^'([^']+)':\{", io.open(ROOT + 'data/fiches.js', encoding='utf-8').read(),
                    re.M)
    ct = io.open(ROOT + 'data/cuvees.js', encoding='utf-8').read()
    ck = re.findall(r"^'([^'|]+\|[^']+)':\{", ct, re.M)
    wl = re.findall(r"\{slug:'([^']+)',name:'((?:[^'\\]|\\.)*)',role:'([^']*)'", ct)
    m['records'] = {
        'fiches_key_parts': dict(collections.Counter(len(k.split('|')) for k in fk)),
        'fiches_records': len(fk),
        'cuvees_key_parts': dict(collections.Counter(len(k.split('|')) for k in ck)),
        'cuvee_records': len(ck),
        'cuvee_wines_listed': len(wl),
        'cuvee_wine_roles': dict(collections.Counter(r for _, _, r in wl)),
    }
    cls = io.open(ROOT + 'data/chateaux.js', encoding='utf-8').read()
    m['estate_record'] = {
        'chateaux_fields': sorted(set(re.findall(r"[{,\s]([a-z]+):", cls.split('concat([', 1)[1]))),
        'owner_is_one_string': bool(re.search(r"owner:'", cls)),
        'second_is_one_string': bool(re.search(r"second:'", cls)),
    }
    app = io.open(ROOT + 'assets/app.js', encoding='utf-8').read()
    m['identity'] = {
        'sparse_ids_from_name_in_app_js': "var id = cls + '-' + slug(name);" in app,
        'sparse_ids_from_name_in_sheetreader': "cls + '-' + slug(nm)" in io.open(
            ROOT + 'tools/sheetreader.py', encoding='utf-8').read(),
        'cls_defaulted_from_cat_in_app_js': "ch.cat === 'sweet' ? 'sauternes' : '1855'" in app,
    }
    return m


def build():
    paths = sorted(os.path.join(ROOT, 'tools', f) for f in os.listdir(ROOT + 'tools')
                   if f.endswith('.py'))
    tools = [tool_facts(p) for p in paths]
    comps, inplace = cycles([t for t in tools if not t['tool'].startswith('tools/test-')])
    edges = []
    for t in tools:
        if t['tool'].startswith('tools/test-'):
            continue
        for f in t['reads_data']:
            edges.append([f, t['tool'], 'reads'])
        for f in t['writes_data']:
            edges.append([t['tool'], f, 'writes'])
    return {
        'phase': '3.1', 'built_by': 'tools/audit-structure.py',
        'note': 'A static reading of the scripts: a path is a string literal in the '
                'tool, a write is a write call located by line. It can miss a path '
                'built at run time; the document says where that matters.',
        'tools': tools,
        'data': data_inventory(tools),
        'edges': sorted(edges),
        'tool_cycles': comps,
        'tools_rewriting_their_own_input': inplace,
        'measures': measures(),
    }


def main():
    out = build()
    text = json.dumps(out, ensure_ascii=False, indent=1) + '\n'
    if '--check' in sys.argv:
        old = io.open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        print('structure report is current' if old == text else 'structure report DIFFERS')
        sys.exit(0 if old == text else 1)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, 'w', encoding='utf-8', newline='\n').write(text)
    t = [x for x in out['tools'] if not x['tool'].startswith('tools/test-')]
    print('%d tools, %d data entries, %d edges, %d tool cycle(s), %d in-place'
          % (len(t), len(out['data']), len(out['edges']), len(out['tool_cycles']),
             len(out['tools_rewriting_their_own_input'])))


if __name__ == '__main__':
    main()
