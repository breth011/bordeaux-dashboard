"""Phase 4 M1: the physical layout of the normalized model and its validator.

D3 (storage), decided in M1: files, not a database. One JSON Lines file per
entity, grouped by the layer the Phase 3.4 contract puts it in, each sorted
by its key so a rebuild is byte-identical and a diff is reviewable. The
volumes (tens of thousands of rows per file) need no index server, the app
is a static page, and docs/phase34-model.json says a database is not to be
introduced for convenience. Raw bytes stay outside git, addressed by digest
(tools/raw_store.py); the discovery observations and the evidence decisions
are not copied but read in place through tools/model_reader.py.

D4 (ids), decided in M1: identity entities (Estate, Wine, Source, Party,
Artifact) get opaque sequential ids minted once and kept by the identity
map, so a rebuild reuses them and no id is ever derived from a name. Every
other record's id is its prefix and a hash of its natural key, so it is
deterministic without a registry. Composite identities are written as
references of their own shape: a Vintage as 'vt:<wine id>:<label>', a
Locator inline as {kind, value}.
"""
import json
import re

import migration_lib as L

CONTRACT = json.load(open(L.ROOT + 'docs/phase34-model.json', encoding='utf-8'))
ENTITIES = CONTRACT['entities']
ENUMS = {k: set(v['values']) for k, v in CONTRACT['enums'].items()}

# Historical model M1: the structural extension M0 proposed
# (docs/PHASE-M0-HISTORICAL-SCHEMA.md), kept as its own contract file so the
# Phase 3.4 contract, a protected record, stays as it was. Every field it adds
# is optional and no existing row carries one; it adds structure, not history.
HISTORY = json.load(open(L.ROOT + 'docs/schema/historical-m1-contract.json', encoding='utf-8'))
for _e, _spec in HISTORY['enums_added'].items():
    ENUMS[_e] = set(_spec['values'])
for _e, _spec in HISTORY['enum_values_added'].items():
    ENUMS[_e] |= set(_spec['add'])
for _ent, _fields in HISTORY['entity_fields_added'].items():
    for _f, _spec in _fields.items():
        ENTITIES[_ent]['fields'][_f] = {'type': _spec['type'], 'required': False}
for _path, _spec in HISTORY['entity_fields_changed'].items():
    _ent, _f = _path.split('.')
    ENTITIES[_ent]['fields'][_f]['required'] = _spec['required']
HISTORICAL_FIELDS = set(HISTORY['historical_reconciliation_fields'])
RULES_BEFORE_D5 = set(HISTORY['historical_reconciliation_rules_allowed_before_D5'])

# Identity entities: minted, sequential, kept by the identity map.
MINTED = {'Estate': ('es', 5), 'Wine': ('wn', 5), 'Source': ('sr', 5), 'Party': ('pt', 5),
          'Artifact': ('ar', 6)}
# Everything else with an id: prefix + hash of the natural key.
HASHED = {
    'NameRecord': 'nm', 'IdentityTransition': 'it', 'EstateWineRelationship': 'ew',
    'ClassificationScheme': 'cs', 'ClassificationEdition': 'ce', 'ClassificationMembership': 'cm',
    'Appellation': 'ap', 'AppellationMembership': 'am', 'Ownership': 'ow', 'EstateLocation': 'el',
    'VintageStatement': 'vs', 'EditorialCollectionMembership': 'ec', 'Placement': 'pl',
    'ArtifactAssessment': 'aa', 'Attribution': 'at', 'Observation': 'ob', 'Reconciliation': 'rc',
    'Provenance': 'pv', 'QualityFinding': 'qf', 'RankAssertion': 'ra', 'RankAbsence': 'rb',
    'WineDescriptor': 'wd', 'SourceEstateRelationship': 'se', 'ArtifactDate': 'ad',
    'ArtifactRelation': 'rl', 'DocumentFamily': 'df', 'Translation': 'tr',
}
PREFIX = {p: e for e, (p, _) in MINTED.items()}
PREFIX.update({p: e for e, p in HASHED.items()})

# file -> (entity, key, stage that first writes it). Every contract entity has
# a home here or in VIEWS.
LAYOUT = {
    'identity/estates.jsonl': ('Estate', 'id', 'M2'),
    'identity/identity-map.jsonl': ('IdentityMap', ('namespace', 'legacy_key'), 'M2'),
    'identity/names.jsonl': ('NameRecord', 'id', 'M2'),
    'identity/transitions.jsonl': ('IdentityTransition', 'id', 'M2'),
    'identity/parties.jsonl': ('Party', 'id', 'M3'),
    'identity/wines.jsonl': ('Wine', 'id', 'M3'),
    'identity/vintages.jsonl': ('Vintage', ('wine', 'label'), 'M5'),
    'identity/sources.jsonl': ('Source', 'id', 'M6'),
    'identity/artifacts.jsonl': ('Artifact', 'id', 'M2'),
    'state/estate-wine.jsonl': ('EstateWineRelationship', 'id', 'M3'),
    'state/rank-assertions.jsonl': ('RankAssertion', 'id', 'M3'),
    'state/rank-absences.jsonl': ('RankAbsence', 'id', 'M4'),
    'state/wine-descriptors.jsonl': ('WineDescriptor', 'id', 'M4'),
    'state/classification-schemes.jsonl': ('ClassificationScheme', 'id', 'M3'),
    'state/classification-editions.jsonl': ('ClassificationEdition', 'id', 'M3'),
    'state/classification-memberships.jsonl': ('ClassificationMembership', 'id', 'M3'),
    'state/appellations.jsonl': ('Appellation', 'id', 'M3'),
    'state/appellation-memberships.jsonl': ('AppellationMembership', 'id', 'M3'),
    'state/ownership.jsonl': ('Ownership', 'id', 'M3'),
    'state/estate-locations.jsonl': ('EstateLocation', 'id', 'M2'),
    'state/vintage-statements.jsonl': ('VintageStatement', 'id', 'M5'),
    'state/editorial-memberships.jsonl': ('EditorialCollectionMembership', 'id', 'M2'),
    'state/source-estate.jsonl': ('SourceEstateRelationship', 'id', 'M6'),
    'document/locators.jsonl': ('Locator', ('kind', 'value'), 'M2'),
    'document/placements.jsonl': ('Placement', 'id', 'M2'),
    'document/assessments.jsonl': ('ArtifactAssessment', 'id', 'M6'),
    'document/attributions.jsonl': ('Attribution', 'id', 'M6'),
    'document/legacy-references.jsonl': ('LegacyDocumentReference',
                                         ('origin', 'record_key', 'field', 'basename'), 'M2'),
    'document/artifact-dates.jsonl': ('ArtifactDate', 'id', 'M6'),
    'document/artifact-relations.jsonl': ('ArtifactRelation', 'id', 'M6'),
    'document/families.jsonl': ('DocumentFamily', 'id', 'M6'),
    'observation/observations.jsonl': ('Observation', 'id', 'M7'),
    'observation/evidence-links.jsonl': ('EvidenceLink', ('evidence_version', 'row_key'), 'M6'),
    'reconciliation/reconciliations.jsonl': ('Reconciliation', 'id', 'M7'),
    'canonical/values.jsonl': ('CanonicalValue', ('subject', 'field'), 'M7'),
    'canonical/translations.jsonl': ('Translation', 'id', 'M7'),
    'cross/provenance.jsonl': ('Provenance', 'id', 'M2'),
    'cross/findings.jsonl': ('QualityFinding', 'id', 'M2'),
}
# Entities read in place rather than copied (tools/model_reader.py).
VIEWS = {
    'Observation': 'data/discovery/observations/*.jsonl (163,582 harvested observations) '
                   'are presented in the Observation shape, not copied',
    'Placement': 'data/discovery/locations/* are presented as Placements of the discovery '
                 'artifacts, not copied',
}


def ref_entity(ref):
    if isinstance(ref, dict):
        if set(ref) == {'kind', 'value'}:
            return 'Locator'
        if {'origin', 'record_key', 'basename'} <= set(ref) <= {'origin', 'record_key', 'field',
                                                                'basename'}:
            return 'LegacyDocumentReference'
        return None
    if not isinstance(ref, str):
        return None
    if ref.startswith('vt:'):
        return 'Vintage'
    return PREFIX.get(ref.split('_', 1)[0])


DATED = ('EXACT', 'APPROXIMATE', 'NO_LATER_THAN', 'NO_EARLIER_THAN')
# The contract's precision rule (TemporalBound rules; historical M1 enforces it, S2).
PRECISION = {'DAY': re.compile(r'^\d{4}-\d{2}-\d{2}$'), 'MONTH': re.compile(r'^\d{4}-\d{2}$'),
             'YEAR': re.compile(r'^\d{4}$'), 'DECADE': re.compile(r'^\d{3}0s$')}


def check_bound(b, where):
    errs = []
    if not isinstance(b, dict):
        return ['%s: bound is not an object' % where]
    if b.get('kind') not in ENUMS['BoundKind']:
        errs.append('%s: bound kind %r' % (where, b.get('kind')))
    has = b.get('value') is not None
    if b.get('kind') in DATED:
        if not has:
            errs.append('%s: %s bound without a value' % (where, b['kind']))
        if not b.get('basis'):
            errs.append('%s: a dated bound needs a basis' % where)
        if b.get('axis') not in ENUMS['BoundAxis']:
            errs.append('%s: axis %r' % (where, b.get('axis')))
        v, prec = str(b.get('value')), b.get('precision')
        if b.get('axis') == 'VINTAGE' and not (prec == 'VINTAGE' and PRECISION['YEAR'].match(v)):
            errs.append('%s: a VINTAGE bound is a year with precision VINTAGE, not %r %r' % (where, v, prec))
        if b.get('axis') == 'CALENDAR' and not (prec in PRECISION and PRECISION[prec].match(v)):
            errs.append('%s: CALENDAR value %r does not match precision %r' % (where, v, prec))
    elif has:
        errs.append('%s: %s bound with a value' % (where, b.get('kind')))
    return errs


def _parts(value):
    """Comparable parts of a bound value: (year[, month[, day]]); a decade is its first year."""
    v = str(value)
    return (int(v[:4]),) if v.endswith('s') else tuple(int(x) for x in v.split('-'))


def check_order(lo, hi, where):
    """Two dated bounds of one interval share an axis (never converted, S3) and the lower is
    not after the upper, compared at the coarser precision (S4)."""
    if not (isinstance(lo, dict) and isinstance(hi, dict)
            and lo.get('kind') in DATED and hi.get('kind') in DATED
            and lo.get('value') is not None and hi.get('value') is not None):
        return []
    if lo.get('axis') != hi.get('axis'):
        return ['%s: bounds on two axes, %s and %s' % (where, lo.get('axis'), hi.get('axis'))]
    try:
        a, b = _parts(lo['value']), _parts(hi['value'])
    except ValueError:
        return []                       # an unparseable value is check_bound's error
    n = min(len(a), len(b))
    return ['%s: lower bound %s after upper bound %s' % (where, lo['value'], hi['value'])] if a[:n] > b[:n] else []


def check_validity(v, where):
    if not isinstance(v, dict) or set(v) - {'valid_from', 'valid_to', 'as_of'}:
        return ['%s: validity shape %r' % (where, v)]
    errs = check_bound(v.get('valid_from'), where + '.valid_from')
    errs += check_bound(v.get('valid_to'), where + '.valid_to')
    if (v.get('valid_from') or {}).get('kind') == 'OPEN':
        errs.append('%s: OPEN only as valid_to' % where)
    return errs + check_order(v.get('valid_from'), v.get('valid_to'), where)


def check_window(w, where):
    """A TimeWindow: when an event happened, as tightly as known (historical M1)."""
    if not isinstance(w, dict) or set(w) != {'earliest', 'latest'}:
        return ['%s: window shape %r' % (where, w)]
    errs = []
    for side in ('earliest', 'latest'):
        if isinstance(w[side], dict) and w[side].get('kind') in ('OPEN', 'NOT_APPLICABLE'):
            errs.append('%s.%s: %s in a window' % (where, side, w[side]['kind']))
        errs += check_bound(w[side], '%s.%s' % (where, side))
    return errs + check_order(w['earliest'], w['latest'], where)


def check_dispositions(d, where):
    """{candidate observation id: {disposition, reason?}} (historical M1)."""
    if not isinstance(d, dict):
        return ['%s: dispositions are not an object' % where]
    errs = []
    for k, v in d.items():
        if not isinstance(v, dict) or set(v) - {'disposition', 'reason'}:
            errs.append('%s[%s]: shape %r' % (where, k, v))
            continue
        if v.get('disposition') not in ENUMS['CandidateDisposition']:
            errs.append('%s[%s]: disposition %r' % (where, k, v.get('disposition')))
        if v.get('disposition') == 'REJECTED' and not v.get('reason'):
            errs.append('%s[%s]: REJECTED without a reason' % (where, k))
    return errs


def check_history(entity, row, provenance=None):
    """The historical M1 rules that need more than one field of a row."""
    errs = []
    if entity == 'Observation':
        cv, cw, mode = row.get('claimed_validity'), row.get('claimed_window'), row.get('statement_mode')
        if cv is not None and cw is not None:
            errs.append('Observation: a claim is about a state or an event, not both')
        if (cv is not None or cw is not None) and mode is None:
            errs.append('Observation: a temporal claim needs a statement_mode')
        if mode is not None and cv is None and cw is None:
            errs.append('Observation: statement_mode without a temporal claim')
        if (cv is not None or cw is not None) and not row.get('artifact'):
            quote = (provenance or {}).get(row.get('provenance'), {}).get('quote')
            if not quote:
                errs.append('Observation: a temporal claim cites no artifact and no quote')
    elif entity == 'IdentityTransition':
        has_at, has_window = row.get('at') is not None, row.get('occurred') is not None
        if has_at == has_window:
            errs.append('IdentityTransition: exactly one of at and occurred')
        kind, a, b = row.get('kind'), row.get('from'), row.get('to')
        if kind == 'RENAMED' and a != b:
            errs.append('IdentityTransition: RENAMED relates one subject to itself')
        if kind == 'SUCCEEDED_BY' and (a == b or ref_entity(a) != ref_entity(b)):
            errs.append('IdentityTransition: SUCCEEDED_BY relates two subjects of one type')
        if kind in ('RELATED_UNSPECIFIED', 'POSSIBLY_SAME') and row.get('certainty') != 'UNRESOLVED':
            errs.append('IdentityTransition: %s establishes nothing and is UNRESOLVED' % kind)
    elif entity == 'Reconciliation':
        disp = row.get('dispositions')
        cands = row.get('candidates') or []
        if disp is not None and isinstance(disp, dict):
            stray = sorted(set(disp) - set(cands))
            if stray:
                errs.append('Reconciliation: dispositions for non-candidates %s' % stray)
            chosen = [k for k, v in disp.items() if isinstance(v, dict) and v.get('disposition') == 'SELECTED']
            if len(chosen) > 1 or (chosen and chosen != [row.get('selected')]) or \
                    (row.get('selected') and disp and row['selected'] not in chosen):
                errs.append('Reconciliation: the selected candidate and the SELECTED disposition differ')
        if row.get('status') in ('CONFLICT_OPEN', 'DEFERRED') and row.get('selected'):
            errs.append('Reconciliation: a selection while %s' % row['status'])
        if row.get('field') in HISTORICAL_FIELDS and row.get('rule') not in RULES_BEFORE_D5:
            errs.append('Reconciliation: rule %s for a historical field before D5' % row.get('rule'))
    return errs


def check_row(entity, row, ids=None, provenance=None):
    """Errors in one row: unknown or missing fields, enum values, shapes,
    and (with ids) dangling references; and the historical M1 rules
    (provenance: {id: Provenance row}, for a claim sourced by a quote)."""
    spec = ENTITIES[entity]['fields']
    errs = []
    for f in row:
        if f not in spec:
            errs.append('%s: unknown field %s' % (entity, f))
    for f, s in spec.items():
        v = row.get(f)
        t = s['type']
        if v is None:
            if s['required'] and not t.startswith('list'):
                errs.append('%s: missing %s' % (entity, f))
            continue
        if t.startswith('enum:'):
            if v not in ENUMS[t[5:]]:
                errs.append('%s.%s: %r not in %s' % (entity, f, v, t[5:]))
        elif t == 'Validity':
            errs += check_validity(v, '%s.%s' % (entity, f))
        elif t == 'TemporalBound':
            errs += check_bound(v, '%s.%s' % (entity, f))
        elif t == 'TimeWindow':
            errs += check_window(v, '%s.%s' % (entity, f))
        elif t == 'Dispositions':
            errs += check_dispositions(v, '%s.%s' % (entity, f))
        elif t == 'id':
            want = MINTED.get(entity, (HASHED.get(entity),))[0]
            if not (isinstance(v, str) and v.startswith(want + '_')):
                errs.append('%s.id %r lacks prefix %s_' % (entity, v, want))
        elif t.startswith('ref:') or t.startswith('list:ref'):
            vals = v if isinstance(v, list) else [v]
            want = t.split('ref:', 1)[1] if 'ref:' in t else '*'
            for x in vals:
                e = ref_entity(x)
                if e is None:
                    errs.append('%s.%s: %r is not a reference' % (entity, f, x))
                elif want not in ('*', '') and e not in want.split('|'):
                    errs.append('%s.%s: %r is a %s, not %s' % (entity, f, x, e, want))
                elif ids is not None and not isinstance(x, dict) and x not in ids:
                    errs.append('%s.%s: dangling %r' % (entity, f, x))
        elif t == 'bool' and not isinstance(v, bool):
            errs.append('%s.%s: not a bool' % (entity, f))
        elif t == 'number' and not isinstance(v, (int, float)):
            errs.append('%s.%s: not a number' % (entity, f))
    return errs + check_history(entity, row, provenance)


def mint(entity, n):
    p, w = MINTED[entity]
    return '%s_%0*d' % (p, w, n)


def hid(entity, *natural):
    return '%s_%s' % (HASHED[entity], L.stable_hash(entity, *natural))


def vref(wine, label):
    return 'vt:%s:%s' % (wine, label)


def bound(kind, value=None, axis=None, precision=None, basis=None):
    b = {'kind': kind}
    if value is not None:
        b.update(value=value, axis=axis, precision=precision, basis=basis)
    return b


UNKNOWN_VALIDITY = {'valid_from': bound('UNKNOWN'), 'valid_to': bound('UNKNOWN')}
CURRENT_UNKNOWN_START = {'valid_from': bound('UNKNOWN'), 'valid_to': bound('OPEN')}
TIMELESS = {'valid_from': bound('NOT_APPLICABLE'), 'valid_to': bound('NOT_APPLICABLE')}
