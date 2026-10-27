"""Phase 4 M5: the 'estate|vintage' and 'estate|slug|vintage' records decomposed.

Every key of the six structures sharing 'estate|vintage' (fiches,
field-src, fiches-url, ratings, cellar, BDX_SCORES; and fiches-nl) maps
through the identity map to one Vintage of that estate's grand-vin Wine
(I4); every 'estate|slug|vintage' key (cuvees, cuvee-src, cuvee-url) to a
Vintage of the wine the slug names. BDX_NOT_PRODUCED becomes
VintageStatements NOT_PRODUCED.

A key whose estate or slug resolves to nothing is classified unresolved
(identity map AMBIGUOUS, no stable id) and its record is kept verbatim on
a provenance record (code_state names file, global and key; quote holds
the value as JSON) with an IDENTITY_UNCERTAIN finding, so it stays
reconstructable without inventing a wine. A provenance key with no data
record is an ORPHAN_PROVENANCE finding; its filename references (M2)
keep it.
"""
import collections
import json

import migration_lib as L
import model_schema as S
import mig_m2_identity as M2

ACTOR = 'tools/migrate.py M5'
GRAND = [('fiches.js', 'BDX_FICHES'), ('field-src.js', 'BDX_FIELD_SRC'),
         ('fiches-url.js', 'BDX_FICHE_URL'), ('ratings.js', 'BDX_RATINGS'),
         ('cellar.js', 'BDX_CELLAR'), ('overrides.js', 'BDX_SCORES'), ('fiches-nl.js', 'BDX_FICHES_NL')]
CUVEE = [('cuvees.js', 'BDX_CUVEES'), ('cuvee-src.js', 'BDX_CUVEE_SRC'), ('cuvee-url.js', 'BDX_CUVEE_URL')]


def keep_unresolved(m, f, name, key, value, why):
    p = m.prov('LEGACY_UNSOURCED', 'data/' + f, quote=L.dumps(value),
               code_state={'legacy_file': 'data/' + f, 'global': name, 'key': key,
                           'unresolved': why})
    m.finding(p, 'IDENTITY_UNCERTAIN', '%s[%r] is kept verbatim: %s' % (name, key, why), ACTOR, p)
    return p


def vintage(m, wine, year):
    m.add('identity/vintages.jsonl', {'wine': wine, 'label': str(year)})
    return S.vref(wine, year)


def run(m):
    p_rule = m.prov('DERIVATION', ACTOR, quote="'estate|vintage' -> the Vintage of the estate's "
                    "grand-vin Wine; 'estate|slug|vintage' -> the Vintage of the slug's Wine")
    m.vintage_of = {}                  # legacy key -> vintage ref
    m.unresolved_records = []          # (file, global, key)
    n = collections.Counter()
    seen = set()
    for f, name in GRAND:
        for key, value in sorted(L.g(name).items()):
            lid, year = key.split('|')
            if lid in m.grand:
                v = vintage(m, m.grand[lid], year)
                m.vintage_of[key] = v
                if key not in seen:
                    M2.idmap(m, 'estate|vintage', key, v, p_rule)
                    seen.add(key)
                n['grand-vin vintage keys'] += 1
            else:
                keep_unresolved(m, f, name, key, value, 'the estate id %r resolves to no estate with a '
                                'grand-vin Wine' % lid)
                m.unresolved_records.append((f, name, key))
                if key not in seen:
                    M2.idmap(m, 'estate|vintage', key, None, p_rule, status='AMBIGUOUS', candidates=[])
                    seen.add(key)
                n['unresolved estate|vintage records'] += 1
    records = set(L.g('BDX_CUVEES'))
    for f, name in CUVEE:
        for key, value in sorted(L.g(name).items()):
            lid, slug, year = key.split('|')
            wid = m.cuvee.get((lid, slug))
            if name == 'BDX_CUVEE_SRC' and key not in records:
                p = m.prov('LEGACY_UNSOURCED', 'data/' + f,
                           code_state={'legacy_file': 'data/' + f, 'global': name, 'key': key})
                m.finding(p, 'ORPHAN_PROVENANCE', 'cuvee-src.js names sources for %r, which no cuvees.js '
                          'record holds' % key, ACTOR, p)
                n['orphan provenance keys'] += 1
                continue
            if wid:
                v = vintage(m, wid, year)
                m.vintage_of[key] = v
                if key not in seen:
                    M2.idmap(m, 'estate|slug|vintage', key, v, p_rule)
                    seen.add(key)
                n['other-wine vintage keys'] += 1
            else:
                keep_unresolved(m, f, name, key, value, 'the slug %r is not listed for %r in '
                                'BDX_CUVEE_WINES' % (slug, lid))
                m.unresolved_records.append((f, name, key))
                if key not in seen:
                    M2.idmap(m, 'estate|slug|vintage', key, None, p_rule, status='AMBIGUOUS',
                             candidates=[])
                    seen.add(key)
                n['unresolved estate|slug|vintage records'] += 1
    p_np = m.prov('LEGACY_UNSOURCED', 'data/overrides.js')
    for lid, years in sorted(L.g('BDX_NOT_PRODUCED').items()):
        for y in years:
            v = vintage(m, m.grand[lid], y)
            m.add('state/vintage-statements.jsonl', {
                'id': S.hid('VintageStatement', v, 'NOT_PRODUCED'), 'vintage': v,
                'kind': 'NOT_PRODUCED', 'provenance': p_np})
            n['NOT_PRODUCED statements'] += 1
    n['vintages'] = len(m.rows('identity/vintages.jsonl'))
    m.stat('M5', 'decomposition', dict(sorted(n.items())))
    m36f_vintages(m)
    vintage_creation(m)


M36F = 'data/audit/m3.6f-cuvee-vintages.jsonl'


def m36f_vintages(m):
    """M3.6F: the vintages of Cuvée Mongravey its held technical sheets title, each read from the audited
    manifest (tools/m36f-vintages.py): the wine M3.6D minted, the year in the sheet's own title. Nothing else
    of the wine changes; a vintage nobody's sheet titles - 1999 among them - is not created."""
    import os
    if not os.path.exists(L.ROOT + M36F):
        return
    n = 0
    for r in L.jsonl_lines(L.ROOT + M36F):
        if r['record'] == 'vintage' and r['applied']:
            vintage(m, r['wine'], r['label'])
            n += 1
    m.stat('M5', 'M3.6F Cuvée vintages', n)


def vintage_creator():
    """tools/apply-vintage-creation-manifest.py, loaded once per process (the M5 and M6 hooks share it)."""
    import importlib.util
    import sys
    name = 'apply_vintage_creation_manifest'
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, L.ROOT + 'tools/apply-vintage-creation-manifest.py')
        sys.modules[name] = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sys.modules[name])
    return sys.modules[name]


def vintage_creation(m):
    """V1: the grand-vin vintages the reviewed vintage-creation manifest (data/audit/vintage-creation-manifest.jsonl)
    asks for and the model being built lacks - the shell only; their existence attributions are M6's. Planned and
    applied by the runner itself, so --apply and a rebuild agree; an empty manifest adds nothing."""
    vintage_creator().m5_hook(m)
