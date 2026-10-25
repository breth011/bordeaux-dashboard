"""Phase 4 M7: observations backfilled from the legacy values, and the
canonical values of taxonomy class A.

One Observation per legacy value, from information already in the files;
nothing is re-extracted. Its provenance is the field's (M6 value_prov,
I13): the Badette 2020 oak case keeps LEGACY_RECORD_SOURCE, never the
record's sheet as the field's source.

What a record says about its values rides on each value's extraction
record, verbatim: the record's src, url and via; ttl/ntl/dtl/ftl/wtl (the
text was translated) on taste/note/decant/food/window; sugl on sug (the
qualifier 'under'); tau on ta (the unit); wy on window (years parsed from
it). So every record stays reconstructable from its observations.

Canonical values only for taxonomy class A (docs/phase34-model.json
phase4_boundary): per vintage alc, blend, harvest, pick, months, oak, ph,
sug, ta, yld; per estate the vineyard area. Each has one Reconciliation,
rule LEGACY_NEVER_OVERWRITE, status LEGACY_RETAINED, its one legacy
observation as candidate and winner. Everything else (tasting text,
press quotes, ratings, cellar notes, soil, plantings, the estate prose,
and owner and the estate blend, which need Ownership parties and D1 per
estate) stays an observation: no class B-F value is promoted.
"""
import collections

import migration_lib as L
import model_schema as S
import mig_m6_provenance as M6

ACTOR = 'tools/migrate.py M7'
OBSERVED = '2026-10-25'                 # the start commit's date: when the legacy file said it
CLASS_A_VINTAGE = {'alc', 'blend', 'harvest', 'pick', 'months', 'oak', 'ph', 'sug', 'ta', 'yld'}
RECORD_META = ('src', 'url', 'via', 'wy')
FIELD_META = {'ttl': 'taste', 'ntl': 'note', 'dtl': 'decant', 'ftl': 'food', 'wtl': 'window',
              'sugl': 'sug', 'tau': 'ta'}
ESTATE_OBS = ('ha', 'owner', 'blend', 'perf', 'style', 'history', 'terroir', 'sources')


def observe(m, subject, field, value, prov, extraction, unit=None, qualifier=None, locus=None,
            lang=None, source=None, artifact=None):
    oid = S.hid('Observation', subject, field, extraction['file'])
    row = {'id': oid, 'subject': subject, 'field': field, 'value': value, 'extraction': extraction,
           'confidence': 'LEGACY', 'observed_at': OBSERVED, 'provenance': prov,
           'subject_status': 'ESTABLISHED'}
    for k, v in (('unit', unit), ('qualifier', qualifier), ('locus', locus), ('lang', lang),
                 ('source', source), ('artifact', artifact)):
        if v is not None:
            row[k] = v
    m.add('observation/observations.jsonl', row)
    return oid


def canonical(m, subject, field, value, oid, status, prov):
    rid = S.hid('Reconciliation', subject, field, 'legacy')
    m.add('reconciliation/reconciliations.jsonl', {
        'id': rid, 'subject': subject, 'field': field, 'candidates': [oid], 'selected': oid,
        'rule': 'LEGACY_NEVER_OVERWRITE', 'status': 'LEGACY_RETAINED',
        'reason': 'the value the legacy file holds, retained as it was', 'resolver': ACTOR,
        'decided_at': OBSERVED, 'provenance': m.p_rec})
    m.add('canonical/values.jsonl', {'subject': subject, 'field': field, 'value': value,
                                     'status': status, 'reconciliation': rid, 'provenance': prov})


def records(m, file, name, src_file, n):
    for key, rec in sorted(L.g(name).items()):
        v = m.vintage_of.get(key)
        if not v:
            continue                       # kept verbatim by M5
        meta = {k: rec[k] for k in RECORD_META if k in rec}
        fmeta = {FIELD_META[k]: (k, rec[k]) for k in FIELD_META if k in rec}
        # A field's flag whose field is absent stays with the record's metadata.
        for f in [f for f in fmeta if f not in rec]:
            mk, mv = fmeta.pop(f)
            meta[mk] = mv
            n['field flags without their field'] += 1
        for field in sorted(rec):
            if field in RECORD_META or field in FIELD_META:
                continue
            prov, status = M6.value_prov(m, src_file, key, field, file, rec)
            ex = {'method': 'LEGACY', 'file': 'data/' + file, 'record': key}
            if meta:
                ex['record_meta'] = meta
            unit = qualifier = None
            if field in fmeta:
                mk, mv = fmeta[field]
                ex['field_meta'] = {mk: mv}
                if mk == 'tau':
                    unit = mv
                elif mk == 'sugl':
                    qualifier = 'under'
            oid = observe(m, v, field, rec[field], prov, ex, unit=unit, qualifier=qualifier)
            n['observations ' + name] += 1
            if field in CLASS_A_VINTAGE:
                canonical(m, v, field, rec[field], oid, status, prov)
                n['canonical %s (%s)' % (name, status)] += 1
        if not [f for f in rec if f not in RECORD_META and f not in FIELD_META]:
            # A record with no value (a src left behind): kept verbatim, flagged.
            p = m.prov('LEGACY_RECORD_SOURCE', 'data/' + file, quote=rec.get('src'),
                       code_state={'legacy_file': 'data/' + file, 'global': name, 'key': key,
                                   'empty_record': rec})
            m.finding(p, 'MISSING', '%s[%r] holds no value, only %s' % (name, key, ', '.join(sorted(rec))),
                      ACTOR, p)
            n['records holding no value'] += 1


def translations(m, n):
    p = m.prov('LEGACY_UNSOURCED', 'data/fiches-nl.js')
    obs = {(r['subject'], r['field'], r['extraction']['file']): r['id']
           for r in m.rows('observation/observations.jsonl')}
    for key, rec in sorted(L.g('BDX_FICHES_NL').items()):
        v = m.vintage_of[key]
        for field, text in sorted(rec.items()):
            src = obs.get((v, field, 'data/fiches.js'))
            if not src:
                # A translation of a field the English record does not hold.
                q = m.prov('LEGACY_UNSOURCED', 'data/fiches-nl.js', quote=text,
                           code_state={'legacy_file': 'data/fiches-nl.js', 'global': 'BDX_FICHES_NL',
                                       'key': key, 'field': field, 'orphan_translation': True})
                m.finding(q, 'ORPHAN_PROVENANCE', 'BDX_FICHES_NL[%r].%s translates a field '
                          'BDX_FICHES[%r] does not hold' % (key, field, key), ACTOR, q)
                n['translations of an absent field'] += 1
                continue
            m.add('canonical/translations.jsonl', {
                'id': S.hid('Translation', src, 'nl'), 'source_observation': src, 'target_lang': 'nl',
                'text': text, 'method': 'legacy: data/fiches-nl.js', 'provenance': p})
            n['translations nl'] += 1


def single_value_files(m, n):
    """ratings, cellar, BDX_SCORES: vintage-level; plantings, terroir: estate-level."""
    for key, val in sorted(L.g('BDX_RATINGS').items()):
        v = m.vintage_of.get(key)
        if not v:
            continue
        p = m.prov('DERIVATION', 'data/ratings.js', source=m.src_bordoverview,
                   quote='mean of the critics bordoverview.com gathered, on one scale')
        observe(m, v, 'rating', val, p, {'method': 'LEGACY', 'file': 'data/ratings.js', 'record': key})
        n['observations BDX_RATINGS'] += 1
    for key, rec in sorted(L.g('BDX_CELLAR').items()):
        v = m.vintage_of[key]
        prov, _ = cellar_prov(m, 'cellar.js', key, rec)
        extra = {k: rec[k] for k in rec if k not in ('v', 'label', 'lang', 'src')}
        ex = {'method': 'LEGACY', 'file': 'data/cellar.js', 'record': key}
        if 'src' in rec:
            ex['record_meta'] = {'src': rec['src']}
        if extra:
            ex['other'] = extra
        observe(m, v, 'cellar_note', rec['v'], prov, ex, locus=rec.get('label'), lang=rec.get('lang'))
        n['observations BDX_CELLAR'] += 1
    for key, rec in sorted(L.g('BDX_SCORES').items()):
        v = m.vintage_of[key]
        sid = m.src_critic.get(rec['src'])
        p = m.prov('CITATION_UNVERIFIED', 'data/overrides.js', source=sid, quote=rec['src'])
        for field in sorted(rec):
            if field == 'src':
                continue
            observe(m, v, field, rec[field], p,
                    {'method': 'LEGACY', 'file': 'data/overrides.js', 'record': key,
                     'record_meta': {'src': rec['src']}}, source=sid)
            n['observations BDX_SCORES'] += 1
    for name, file, field in (('BDX_PLANTINGS', 'plantings.js', 'vineyard_planting'),
                              ('BDX_TERROIR', 'terroir.js', 'soil')):
        for lid, rec in sorted(L.g(name).items()):
            prov, _ = cellar_prov(m, file, lid, rec)
            value = rec['blend'] if name == 'BDX_PLANTINGS' else rec['v']
            other = {k: rec[k] for k in rec if k not in ('blend', 'v', 'label', 'lang', 'src')}
            ex = {'method': 'LEGACY', 'file': 'data/' + file, 'record': lid}
            if 'src' in rec:
                ex['record_meta'] = {'src': rec['src']}
            if other:
                ex['other'] = other
            observe(m, m.estate[lid], field, value, prov, ex, locus=rec.get('label'),
                    lang=rec.get('lang'))
            n['observations ' + name] += 1


def cellar_prov(m, file, key, rec):
    """A one-value record: its src is that value's source."""
    if not rec.get('src'):
        return m.prov('LEGACY_UNSOURCED', 'data/' + file), 'LEGACY_UNSOURCED'
    r = m.get('document/legacy-references.jsonl', (file, key, None, rec['src']))
    lref = {'origin': file, 'record_key': key, 'basename': rec['src']}
    if r and r['resolution'] == 'ACTIVE':
        return m.prov('LEGACY_FIELD_SOURCE', 'data/' + file, artifact=m.pl_artifact[r['candidates'][0]],
                      legacy_reference=lref), 'LEGACY_FIELD_SOURCE'
    return m.prov('LEGACY_AMBIGUOUS_SOURCE', 'data/' + file, legacy_reference=lref), \
        'LEGACY_AMBIGUOUS_SOURCE'


def estate_fields(m, n):
    for f, r in L.estate_files():
        eid = m.estate[r['id']]
        p = m.prov('LEGACY_UNSOURCED', 'data/' + f)
        for field in ESTATE_OBS:
            if field not in r:
                continue
            oid = observe(m, eid, field, r[field], p, {'method': 'LEGACY', 'file': 'data/' + f,
                                                       'record': r['id']})
            n['observations estate ' + field] += 1
            if field == 'ha':
                canonical(m, eid, 'vineyard_area_ha', r['ha'], oid, 'LEGACY_UNSOURCED', p)
                n['canonical vineyard_area_ha'] += 1
            if field == 'blend':
                m.finding(oid, 'AMBIGUOUS_SEMANTICS', 'the estate blend of data/%s: plantings or the '
                          'usual assemblage, decided per estate (D1); kept as an observation' % f,
                          ACTOR, p)


def run(m):
    m.p_rec = m.prov('DERIVATION', ACTOR, quote='legacy values are retained; no reconciliation '
                     'rule chose them (LEGACY_NEVER_OVERWRITE)')
    n = collections.Counter()
    records(m, 'fiches.js', 'BDX_FICHES', 'field-src.js', n)
    records(m, 'cuvees.js', 'BDX_CUVEES', 'cuvee-src.js', n)
    translations(m, n)
    single_value_files(m, n)
    estate_fields(m, n)
    m.stat('M7', 'backfill', dict(sorted(n.items())))
