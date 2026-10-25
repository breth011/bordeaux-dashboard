# -*- coding: utf-8 -*-
"""Phase 3.4: the domain contract, as an explicit revision of Phase 3.2.

    python -I tools/build-phase34-model.py           writes docs/phase34-model.json
    python -I tools/build-phase34-model.py --check   rebuilds and compares

Loads docs/phase32-model.json and applies the changes the harvested corpus
(data/review/phase34-corpus-analysis.json) requires. Every change is listed
in DIFF with its evidence, so the architectural diff between 3.2 and 3.4 is
this file, not prose. Conceptual, like 3.2: no schema, no storage, no ids.
"""
import copy
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
IN = ROOT + 'docs/phase32-model.json'
OUT = ROOT + 'docs/phase34-model.json'
REQ = {'required': True}
OPT = {'required': False}


def f(t, req=True):
    return {'type': t, 'required': req}


VALIDITY = f('Validity')
PROV = f('ref:Provenance')

# ------------------------------------------------------------------ enums
ENUMS_ADD = {
    'WineType': {'values': ['RED', 'WHITE_DRY', 'WHITE_SWEET', 'ROSE', 'SPARKLING', 'OTHER', 'UNKNOWN'],
                 'note': 'What kind of wine it is. Independent of rank: Myosotis (WHITE_DRY) is a first wine, Les Tourelles '
                         '(WHITE_SWEET) a third, Les Murets rouge (RED) unranked as far as any source says.'},
    'RankTier': {'values': ['FIRST', 'SECOND', 'THIRD', 'ABOVE_FIRST', 'UNRANKED', 'UNKNOWN'],
                 'note': 'Where a claimant places a wine in a range. FIRST is the grand vin / premier vin; ABOVE_FIRST a '
                         'cuvee placed above it (Mangot: "in truth it is the superior cuvee"); UNRANKED is an explicit '
                         'statement that no rank applies (Le Rey: "do not represent ... first and second label"); '
                         'UNKNOWN is no statement. There is no OTHER: a wine nobody ranks has no rank assertion.'},
    'RankScope': {'values': ['ESTATE_RANGE', 'TYPE_RANGE'],
                  'note': 'The range a rank is within: the estate\'s whole range, or its range of one WineType '
                          '(Caillou: Myosotis FIRST and Les Murets blanc SECOND within WHITE_DRY).'},
    'Claimant': {'values': ['PRODUCER', 'CLASSIFICATION_BODY', 'PRESS', 'TRADE', 'DATASET'],
                 'note': 'Who asserts a rank. Ranks are claims: Mangot\'s cuvee is SECOND for the classification '
                         'authorities and ABOVE_FIRST in the producer\'s and press\'s words.'},
    'RelationshipKind': {'values': ['PRODUCED_BY', 'FROM_ESTATE_VINEYARD', 'MADE_BY_GROUP_TEAM', 'SOLD_BY',
                                    'SAME_OWNER_OTHER_PROPERTY', 'ASSOCIATED_UNSPECIFIED'],
                         'note': 'What links a wine to an estate. Several may hold at once (Les Terrasses: from the '
                                 'estate\'s younger vines, created by the Vignobles K team). A wine on an estate\'s site '
                                 'is not thereby the estate\'s (Chateau Langlet on Latour-Martillac\'s site).'},
    'DescriptorKind': {'values': ['PLOT_SELECTION', 'YOUNG_VINES', 'OLD_VINES', 'LIMITED_RELEASE',
                                  'NOT_COMMERCIALISED', 'PRESSING_ROSE', 'OTHER'],
                       'note': 'How a wine is made or selected - never a rank. "Selection parcellaire" names '
                               'Lacroix-Martillac and also describes vat work at dozens of estates; single-variety is '
                               'derived from the blend, not stored.'},
    'EditionStatus': {'values': ['IN_FORCE', 'SUPERSEDED', 'ANNULLED', 'UNKNOWN'],
                      'note': 'Saint-Emilion 2006 was annulled ("classement annule depuis", Grand Corbin-Despagne).'},
    'ArtifactDateKind': {'values': ['PDF_METADATA', 'UPLOAD_PATH', 'HTTP_LAST_MODIFIED', 'STATED_IN_TEXT',
                                    'YEAR_IN_TITLE_OR_URL', 'RETRIEVED'],
                         'note': '93 % of harvested PDFs carry a metadata date, 70 % an upload-path date: the anchor for '
                                 '"today" and "now" in a document.'},
    'ArtifactRelationKind': {'values': ['LANGUAGE_VERSION_OF', 'REVISION_OF', 'SAME_FAMILY_AS', 'COPY_OF'],
                             'note': 'Between artifacts, always as a candidate with its evidence; never equivalence of '
                                     'content (Murmure 2018: two French revisions, 14.5 % and 14 %; the English, 14 %).'},
    'RelationStatus': {'values': ['CANDIDATE', 'CONFIRMED', 'REJECTED']},
    'SourceRelationKind': {'values': ['OFFICIAL_SITE', 'GROUP_SITE', 'SHOP', 'NEGOCIANT_SITE', 'REGISTER_ENTRY',
                                      'MENTIONS'],
                           'note': '25 domains serve several target estates; 31 sites moved domain.'},
    'ExtractionStatus': {'values': ['PENDING', 'EXTRACTED', 'NEEDS_OCR', 'FAILED', 'UNSUPPORTED', 'STORED_ONLY'],
                         'note': '374 image-only PDFs exist before any OCR; the model must not need their text.'},
    'SubjectStatus': {'values': ['ESTABLISHED', 'PROPOSED', 'UNRESOLVED'],
                      'note': 'Whose statement an observation is, inside a document that may cover several estates.'},
}
ENUMS_REMOVE = ['WineRole', 'WineRange']

# ------------------------------------------------------------------ entities
CHANGES = {
    'Wine': {'fields': {'id': f('id'), 'name_status': f('enum:NameStatus'), 'type': f('enum:WineType'),
                        'non_vintage': f('bool', False)},
             'note': 'Identity apart from name, type apart from rank. The grand vin is a Wine.'},
    'NameRecord': {'add': {'context': f('text', False)},
                   'note': 'context: the market or channel a name is used in (Desmirail: Initial de Desmirail "aussi '
                           'distribue sous le nom de Origine de Desmirail").'},
    'Party': {'add': {'identifiers': f('list:text', False)},
              'note': 'Legal identifiers (SIRET, RCS) may be attached when established; legal notices themselves stay '
                      'observations about the site publisher.'},
    'EstateWineRelationship': {'add': {'kind': f('enum:RelationshipKind')},
                               'note': 'One record per kind of link; validity per record.'},
    'ClassificationEdition': {'add': {'status': f('enum:EditionStatus')}},
    'Attribution': {'add': {'role': f('enum:RankTier', False)},
                    'note': 'A judgement of what an artifact concerns; role is now a RankTier claim, null when unknown.'},
    'Artifact': {'add': {'extraction_status': f('enum:ExtractionStatus')}},
    'Observation': {'add': {'subject': f('ref:Estate|Wine|Vintage|EstateWineRelationship|Source'),
                            'raw_label': f('text', False), 'lang': f('text', False),
                            'asserted_at': f('TemporalBound', False), 'subject_status': f('enum:SubjectStatus')},
                    'note': 'raw_label and lang as printed; asserted_at anchors "today", "now", "currently" to the '
                            'document\'s date (an ArtifactDate), distinct from when the fact holds (validity of the state '
                            'it supports) and from when it was retrieved.'},
    'CanonicalValue': {'add': {'lang': f('text', False), 'as_of': f('TemporalBound', False)},
                       'note': 'lang: the language of a canonical text value; as_of: the date a time-dependent value '
                               '(vineyard area, owner) is known to hold.'},
}
RENAMES = {
    'RoleAssignment': ('RankAssertion', {
        'id': f('id'), 'relationship': f('ref:EstateWineRelationship'), 'tier': f('enum:RankTier'),
        'scope': f('enum:RankScope'), 'scope_type': f('enum:WineType', False), 'claimant': f('enum:Claimant'),
        'source_term': f('text', False), 'legacy_term': f('text', False), 'validity': VALIDITY, 'provenance': PROV},
        'A claimant\'s statement of where a wine stands in a range, in time.'),
    'RoleAbsence': ('RankAbsence', {
        'id': f('id'), 'estate': f('ref:Estate'), 'tier': f('enum:RankTier'), 'scope': f('enum:RankScope'),
        'scope_type': f('enum:WineType', False), 'claimant': f('enum:Claimant'), 'validity': VALIDITY,
        'provenance': PROV},
        'A statement that a rank is empty - for good, or for one vintage (Corbin 2022: "no second wine was produced '
        'this year").'),
}
ADDS = {
    'WineDescriptor': {'layer': 'STATE', 'identity': 'minted opaque id', 'fields': {
        'id': f('id'), 'wine': f('ref:Wine'), 'kind': f('enum:DescriptorKind'), 'source_term': f('text'),
        'validity': VALIDITY, 'provenance': PROV},
        'note': 'How a wine is made or selected, kept apart from its rank.'},
    'SourceEstateRelationship': {'layer': 'STATE', 'identity': 'minted opaque id', 'fields': {
        'id': f('id'), 'source': f('ref:Source'), 'estate': f('ref:Estate'), 'kind': f('enum:SourceRelationKind'),
        'validity': VALIDITY, 'provenance': PROV},
        'note': 'A source serving or mentioning an estate. Never identity: a group site serves several estates.'},
    'ArtifactDate': {'layer': 'DOCUMENT', 'identity': 'minted opaque id', 'fields': {
        'id': f('id'), 'artifact': f('ref:Artifact'), 'kind': f('enum:ArtifactDateKind'),
        'value': f('TemporalBound'), 'provenance': PROV},
        'note': 'Candidate dates of a document, several per artifact, each with how it is known.'},
    'ArtifactRelation': {'layer': 'DOCUMENT', 'identity': 'minted opaque id', 'fields': {
        'id': f('id'), 'from': f('ref:Artifact'), 'to': f('ref:Artifact'), 'kind': f('enum:ArtifactRelationKind'),
        'status': f('enum:RelationStatus'), 'provenance': PROV},
        'note': 'Language versions, revisions, family membership - candidates, never content equivalence.'},
    'DocumentFamily': {'layer': 'DOCUMENT', 'identity': 'minted opaque id', 'fields': {
        'id': f('id'), 'source': f('ref:Source'), 'label_signature': f('list:text'), 'members': f('list:ref'),
        'languages': f('list:text', False), 'provenance': PROV},
        'note': 'A derived grouping of one source\'s documents that share a layout (849 families; none shared across '
                'domains; 27 span languages). An extraction aid, not domain truth.'},
    'Translation': {'layer': 'CANONICAL', 'identity': 'minted opaque id', 'fields': {
        'id': f('id'), 'source_observation': f('ref:Observation'), 'target_lang': f('text'), 'text': f('text'),
        'method': f('text'), 'provenance': PROV},
        'note': 'A derived text in another language. Never an observation, never evidence of equivalence.'},
}
REJECTS = {
    'enum:WineRole.OTHER_CUVEE': 'Not a rank: "other cuvee" was the absence of a rank statement. A wine without one '
                                 'has no RankAssertion; UNKNOWN is the tier when a rank is claimed but unreadable.',
    'enum:WineRange (as part of the role)': 'Colour/style moved to Wine.type; the range a rank is within is '
                                             'RankScope + scope_type.',
}

# ------------------------------------------------------------------ the diff
DIFF = {
    'ADD': [
        ['WineType', 'type independent of rank; corpus: grand vin blanc sec 94, troisieme vin moelleux (Caillou), rose de pressee (Latour-Martillac)'],
        ['RankTier.THIRD', 'third_wine: 58 artifacts on 13 domains (Batailley "Pauillac de Batailley, the Chateau\'s third wine"; Caillou "notre troisieme vin")'],
        ['RankTier.ABOVE_FIRST', 'prestige: 258 artifacts on 15 domains; Mangot "in truth it is the superior cuvee"'],
        ['RankTier.UNRANKED', 'no_hierarchy: Le Rey "do not represent as usual in Bordeaux first and second label"'],
        ['Claimant', 'Mangot: SECOND for the classification authorities, superior cuvee for producer and press'],
        ['RankScope', 'Caillou: Myosotis "notre grand vin blanc sec", Les Murets "Second Vin blanc sec"'],
        ['RelationshipKind', 'from_estate_vines 219 artifacts; Vignobles K "creee et orchestree par l\'equipe"; Langlet on Latour-Martillac\'s site'],
        ['WineDescriptor', 'plot_selection 654 artifacts (mostly vat work), young_vines 701, old_vines 636; co-occurrence second+young vines 171'],
        ['SourceEstateRelationship', '25 multi-target domains; 31 moved domains; 688 artifacts on several domains'],
        ['ArtifactDate', 'PDF metadata 6,683 of 7,197; upload paths 5,074; HTTP Last-Modified 11,471 fetches'],
        ['ArtifactRelation', '897 PDF groups differing only by a language token; 11 analytical disagreements; Murmure 2018 revision'],
        ['DocumentFamily', '849 layout families, 278 of 3+ sheets, 69 domains with several'],
        ['Translation', '1,053 Chinese and 239 Japanese artifacts; translations must stay derived'],
        ['EditionStatus', 'Saint-Emilion 2006 annulled (Grand Corbin-Despagne press 2008)'],
        ['ExtractionStatus', '374 PDFs need OCR; 2 extraction failures; 610 images stored only'],
        ['SubjectStatus', '519 artifacts naming several estates'],
        ['Observation.asserted_at', 'now: 4,843 artifacts on 218 domains use "today/now/currently"'],
        ['CanonicalValue.as_of', 'vineyard area and planting change over time; area on 155 domains'],
        ['NameRecord.context', 'Desmirail: one wine distributed under two names'],
        ['NameKind.MARKET_ALIAS', 'Desmirail'],
        ['AttributionMethod.CRAWL_CONTEXT', 'Phase 3.3 attribution: crawl context is the weakest evidence'],
        ['PlacementStatus.ACCESS_REFUSED', '19 domains refused crawling site-wide (16 by robots.txt answering 403, 3 by rules naming AI agents)'],
    ],
    'SPLIT': [
        ['RoleAssignment (rank x range)', 'RankAssertion (tier, scope, claimant) + Wine.type + WineDescriptor'],
        ['estate-level blend (D1)', 'Estate planting composition (encepagement) vs Vintage blend (assemblage): 528 documents state both, 476 with different values'],
        ['classification', 'ClassificationMembership (authoritative) vs classification claims kept as Observations (1,851 classification observations on 84 domains)'],
    ],
    'MERGE': [
        ['WineRole.OTHER_CUVEE into "no RankAssertion"', 'other meant "not ranked as far as we know"'],
    ],
    'RENAME': [
        ['RoleAssignment -> RankAssertion', '"role" mixed rank, type and making; what remains is a ranked claim'],
        ['RoleAbsence -> RankAbsence', 'as above; now vintage-scoped as well'],
        ['WineRange -> WineType', 'it was always the type of wine, not a range'],
    ],
    'RETAIN': ['Estate', 'Vintage', 'Source', 'IdentityMap', 'IdentityTransition', 'ClassificationScheme',
               'ClassificationMembership (on the Wine)', 'Appellation', 'AppellationMembership (on the Wine)',
               'Ownership', 'EstateLocation', 'VintageStatement', 'EditorialCollectionMembership', 'Locator',
               'Placement', 'ArtifactAssessment', 'Attribution', 'LegacyDocumentReference', 'EvidenceLink',
               'Reconciliation', 'Provenance', 'QualityFinding', 'Validity', 'TemporalBound'],
    'REJECT': [[k, v] for k, v in REJECTS.items()],
}

# ------------------------------------------------------------------ taxonomy
TAXONOMY = [
    # category, class, level, temporal, reason
    ['APPELLATION', 'A', 'wine', 'yes', 'structured, 120 sites; varies by wine within one estate (Climens: 1er cru Barsac / Bordeaux Blanc Sec)'],
    ['CLASSIFICATION', 'A (memberships) / B (claims)', 'wine', 'yes', 'authoritative lists vs site claims (cru bourgeois since 2013, confirmed 2018)'],
    ['VINEYARD_AREA', 'A', 'estate', 'yes', '77 % numeric, 155 sites; changes over time (as_of)'],
    ['PLANTING (encepagement, density, vine age)', 'A', 'estate', 'yes', '72 % numeric, 159 sites; distinct from the blend (D1)'],
    ['BLEND', 'A', 'vintage', 'no', '94 % numeric, 135 sites'],
    ['ANALYTICAL (alcohol, pH, acidity, sugar)', 'A', 'vintage', 'no', '128 sites, short values; units vary (H2SO4 vs tartaric)'],
    ['HARVEST_VINTAGE (dates, yield)', 'A (dates, yield) / B (conditions narrative)', 'vintage', 'no', '188 sites; 382 labels'],
    ['ELEVAGE (duration, vessels, new oak)', 'A (months, new-oak share) / B (description)', 'vintage', 'sometimes', '76 % numeric, 172 sites'],
    ['BOTTLING_PRODUCTION', 'B', 'vintage', 'no', 'production volumes and bottling dates recur (141 sites) but mix units and formats'],
    ['SOIL_TERROIR', 'B', 'estate', 'rarely', 'free text, 150 sites; meaning varies (a heading, a soil statement)'],
    ['WINEMAKING', 'B', 'vintage', 'sometimes', '225 labels; process prose; plot selection mostly lives here'],
    ['VITICULTURE', 'B', 'estate', 'yes', 'practices (pruning, cover crops) on 45 sites'],
    ['TASTING', 'B', 'vintage', 'no', '1 % numeric, median 57 characters; already canonical as text in fiches, but per source'],
    ['SERVICE_AGEING', 'B (text) / E (drinking-window years parsed)', 'vintage', 'no', '127 sites'],
    ['OWNERSHIP_PEOPLE', 'A (owner via Ownership) / B (staff)', 'estate', 'yes', '83 sites; dated mentions 11,506'],
    ['PRESS_SCORES', 'C', 'vintage', 'no', 'scores quoted by estates (86 sites): first-party quotations of third parties'],
    ['SUSTAINABILITY', 'B', 'estate', 'yes', '23 sites as labels, more in prose; certifications are dated claims'],
    ['HISTORY', 'F', 'estate', 'yes', 'abundant in prose (founding/history years 7,876) but rarely labelled (34): needs event extraction to be designed'],
    ['COMMERCIAL', 'D', 'wine/vintage', 'yes', 'prices and shop mechanics; volatile, not domain facts'],
    ['TOURISM', 'D', 'estate', 'yes', 'opening hours, visits (53 sites)'],
    ['IDENTITY_CONTACT', 'C', 'source', 'yes', 'telephone, email, address (180 sites); belongs to the source/publisher'],
    ['LEGAL_ENTITY', 'B (auxiliary)', 'source', 'yes', '115 sites carry legal labels; they describe the site publisher, which may be a group or operator, not the estate'],
    ['PRIVACY_LEGAL_TEXT', 'D', 'source', 'no', 'site boilerplate'],
    ['SINGLE_VARIETY', 'E', 'vintage', 'no', 'derived from the blend (100 %)'],
    ['RANK / ROLE WORDING', 'A (RankAssertion)', 'estate-wine', 'yes', 'see the hierarchy analysis'],
    ['UNCLASSIFIED', 'F', '-', '-', '48,169 observations under 10,052 labels: menus, product names, prices, table fragments'],
]

DECISIONS = {
    'D1': ['RESOLVED (model) / STILL OPEN (legacy data)', 'planting composition and blend are different facts: 528 documents state both, 476 with different values',
           'estate planting composition is an Estate canonical field with as_of; blend is a Vintage field; each legacy estate-level "blend" value is reviewed per estate before it is mapped'],
    'D2': ['RECOMMENDED: RENAMED (one Wine)', 'lynchbages.com/en/vintages: "In 2008, a new identity was given to the second wine, under the name Echo de Lynch-Bages"; FR: "il change d\'identite pour devenir"',
           'the second wine is the continuing subject: one Wine, NameRecord Haut-Bages Averous (FORMER, to vintage 2007 at the latest) and Echo de Lynch-Bages (from vintage 2008); certainty PROBABLE until confirmed by the user'],
    'D3': ['STILL OPEN (Phase 4)', 'raw store 7.7 GB (local, not git); 163,582 observations, 29,517 artifacts; text compresses ~10x',
           'raw artifacts in a content-addressed file store outside git; the normalized layers in an indexed store; decision is Phase 4\'s'],
    'D4': ['STILL OPEN (Phase 4)', 'the harvest has no bearing on id syntax', 'rules unchanged: minted once, opaque'],
    'D5': ['RECOMMENDED (initial policy)', 'language versions disagree in 11 of 897 groups; revisions at different upload paths (Murmure 2018); ranks differ by claimant (Mangot)',
           'no automatic winner across language versions or claimants; a later revision of the same document (by ArtifactDate) is preferred as SOURCE_PRIORITY with the earlier kept; estate publications over trade copies; everything else CONFLICT_OPEN'],
    'D6': ['RESOLVED for new data / STILL OPEN for legacy', 'Phase 3.3 records retrieval (discovered_via, referrer) and attribution evidence (CRAWL_CONTEXT, NAMED_IN_*) separately',
           'new ingestion never mixes them; the 85 legacy "how" texts still need the reviewed table'],
    'D7': ['STILL OPEN (Phase 4)', 'no bearing', 'regenerated files remain the safe first step'],
    'D8': ['RESOLVED BY FIRST-PARTY EVIDENCE (pending application)', 'estates\' own pages: "Chateau Bouscaut Blanc Grand Cru Classe de Graves"; "Chateau Carbonnieux Blanc"; "Chateau Latour-Martillac Blanc"; "Malartic-Lagraviere Blanc"',
           'record these as NameRecords from ESTATE_PUBLICATION in Phase 4; not applied here'],
}

PROPOSALS = {
    'Echo de Lynch-Bages': {'identity': 'ESTABLISHED (47 artifacts, sheets 2008-2025, FR/EN/CN)',
                            'estate_relationship': 'ESTABLISHED (PRODUCED_BY; "2nd vin du Chateau Lynch-Bages")',
                            'role': 'ESTABLISHED: SECOND, scope ESTATE_RANGE, claimant PRODUCER ("2nd vin"; CN "副牌")',
                            'time_range': 'from vintage 2008 (EXACT); predecessor Haut-Bages Averous (D2)',
                            'status': 'READY FOR DOMAIN DECISION'},
    'Les Terrasses de Saint Christophe': {'identity': 'ESTABLISHED (22 artifacts on vignoblesk.com, sheets 2016-2023)',
                                          'estate_relationship': 'ESTABLISHED: FROM_ESTATE_VINEYARD ("made from some of the younger vines planted on the terrasses of the estate") and MADE_BY_GROUP_TEAM ("creee et orchestree par l\'equipe des Vignobles K")',
                                          'role': 'SECOND for vintages 2016-2019 ("second label of Chateau Tour Saint Christophe", product sheets); UNKNOWN for 2020-2023',
                                          'time_range': 'NO_LATER_THAN vintage 2016 to at least 2023',
                                          'status': 'READY FOR DOMAIN DECISION for 2016-2019; STILL NEEDS EVIDENCE for the role from 2020'},
    'Les Murets de Caillou': {'identity': 'ESTABLISHED: two Wines of one name (blanc: Bordeaux Blanc Sec; rouge: Bordeaux Superieur, 100 % Merlot)',
                              'estate_relationship': 'ESTABLISHED (PRODUCED_BY; estate shop and sheets)',
                              'role': 'blanc: SECOND within TYPE_RANGE WHITE_DRY ("Second Vin blanc sec" / "Second dry white wine", 2023 sheet, FR and EN); rouge: no rank stated',
                              'time_range': 'blanc: at least vintage 2023; rouge: at least vintage 2023',
                              'status': 'READY FOR DOMAIN DECISION (blanc); rouge has no rank to decide'},
}

READINESS = [
    ['third wines', 'RankTier.THIRD', 'P1 Batailley; P3 Caillou Tourelles'],
    ['prestige / superior wines', 'RankTier.ABOVE_FIRST + Claimant', 'P5 Mangot'],
    ['explicit no hierarchy', 'RankTier.UNRANKED', 'P2 Le Rey'],
    ['wine type independent of hierarchy', 'Wine.type vs RankAssertion', 'P3 Caillou'],
    ['wine identity independent of display name', 'Wine has no name field; NameRecord; MARKET_ALIAS', 'P8 Desmirail'],
    ['historical estate-wine relationships', 'EstateWineRelationship.validity', 'P7 Echo/Averous'],
    ['temporal rank changes', 'RankAssertion.validity', 'P7 Echo/Averous'],
    ['wine-level classification (Graves)', 'ClassificationMembership on Wine', 'P9 Bouscaut'],
    ['temporal appellation', 'AppellationMembership.validity', 'P10 Climens'],
    ['historical wine identity without guesswork', 'IdentityTransition with certainty; evidence criteria', 'P7 Echo; P11 Haut-Bailly'],
    ['shared sources', 'SourceEstateRelationship', 'P12 Vignobles K'],
    ['multi-estate documents', 'Attribution many-per-artifact; Observation.subject_status', 'P12'],
    ['observations keep source wording', 'Observation.raw_label, raw_value, lang', 'P13 Murmure'],
    ['multilingual observations distinct', 'Observation.lang; ArtifactRelation LANGUAGE_VERSION_OF (candidate); Translation derived', 'P13'],
    ['canonical values without deleting observations', 'Reconciliation lists candidates', 'P13'],
    ['discovery-only information outside canonical fields', 'taxonomy classes B-F stay Observations', 'P14 SIRET'],
    ['unreachable / blocked sources represented', 'Placement + QualityFinding SOURCE_FAILURE; SourceEstateRelationship', 'P15 Canon'],
    ['OCR-dependent documents before OCR', 'Artifact.extraction_status NEEDS_OCR', 'P16'],
    ['no complete wine universe needed', 'absence of RankAssertion is UNKNOWN', 'all cases'],
    ['Phase 2 proposals decidable without special-case schema', 'RankAssertion + RelationshipKind + NameRecord', 'P7, P4, P3'],
]

BOUNDARY = {
    'phase4_may_implement': ['the entities and enums of this contract', 'the migration stages M0-M9 of Phase 3.2, with RankAssertion in place of RoleAssignment',
                             'ingestion of the Phase 3.3 harvest into Artifact/Placement/Observation/Attribution',
                             'canonical fields of taxonomy class A only', 'D3, D4, D7'],
    'phase4_must_not': ['promote class B-F information to canonical fields without a later review',
                        'apply Echo, Terrasses or Murets except as recorded domain decisions in the new model',
                        'resolve UNRESOLVED identities or ranks by inference', 'rewrite v1-v5 evidence or the discovery data'],
}


def build():
    m = json.load(io.open(IN, encoding='utf-8'))
    out = copy.deepcopy(m)
    out['meta'] = {'phase': '3.4', 'revises': 'docs/phase32-model.json', 'input': 'b278121',
                   'evidence': 'data/review/phase34-corpus-analysis.json', 'built_by': 'tools/build-phase34-model.py',
                   'status': 'CONCEPTUAL DOMAIN CONTRACT for Phase 4. Not a schema.',
                   'fixtures': 'docs/phase34-fixtures.json'}
    for k in ENUMS_REMOVE:
        out['enums'].pop(k, None)
    out['enums'].update(ENUMS_ADD)
    out['enums']['NameKind']['values'] = out['enums']['NameKind']['values'] + ['MARKET_ALIAS']
    out['enums']['AttributionMethod']['values'] = out['enums']['AttributionMethod']['values'] + ['CRAWL_CONTEXT']
    out['enums']['DocumentType']['values'] = out['enums']['DocumentType']['values'] + ['LEGAL_NOTICE', 'SHOP_PAGE']
    # A source that refused access is still a place the model must hold
    # (24 estates blocked by policy in Phase 3.3).
    out['enums']['PlacementStatus']['values'] = out['enums']['PlacementStatus']['values'] + ['ACCESS_REFUSED']
    E = out['entities']
    for old, (new, fields, note) in RENAMES.items():
        layer = E[old]['layer']
        del E[old]
        E[new] = {'layer': layer, 'identity': 'minted opaque id', 'fields': fields, 'note': note, 'renamed_from': old}
    for name, ch in CHANGES.items():
        if 'fields' in ch:
            E[name]['fields'] = ch['fields']
        for k, v in ch.get('add', {}).items():
            E[name]['fields'][k] = v
        if ch.get('note'):
            E[name]['note'] = ch['note']
    for name, d in ADDS.items():
        E[name] = d
    # layers follow the entities
    for l in out['layers']:
        l['holds'] = [('RankAssertion' if h == 'RoleAssignment' else 'RankAbsence' if h == 'RoleAbsence' else h)
                      for h in l['holds']]
    add_layer = {'STATE': ['WineDescriptor', 'SourceEstateRelationship'],
                 'DOCUMENT': ['ArtifactDate', 'ArtifactRelation', 'DocumentFamily'], 'CANONICAL': ['Translation']}
    for l in out['layers']:
        l['holds'] += add_layer.get(l['id'], [])
    out['relationships'] = [r for r in out['relationships'] if r[1] not in ('RoleAssignment', 'RoleAbsence')] + [
        ['EstateWineRelationship', 'RankAssertion', 'RankTier x RankScope', 'a claimant places the wine in a range, in time'],
        ['Estate', 'RankAbsence', 'RankTier x RankScope', 'a rank is empty, for good or for a vintage'],
        ['Wine', 'WineDescriptor', None, 'how the wine is made or selected'],
        ['Source', 'SourceEstateRelationship', 'Estate', 'a source serves or mentions an estate'],
        ['Artifact', 'ArtifactDate', None, 'candidate dates of a document'],
        ['Artifact', 'ArtifactRelation', 'Artifact', 'language versions, revisions, families'],
        ['Source', 'DocumentFamily', 'Artifact', 'documents sharing a layout'],
        ['Observation', 'Translation', None, 'a derived text in another language'],
    ]
    out['diff'] = DIFF
    out['taxonomy'] = [dict(zip(('category', 'class', 'level', 'temporal', 'reason'), t)) for t in TAXONOMY]
    out['taxonomy_classes'] = {'A': 'core canonical domain', 'B': 'structured observation', 'C': 'source-specific structured data',
                               'D': 'raw evidence only', 'E': 'derived', 'F': 'unknown / future study'}
    out['decisions'] = {k: dict(zip(('status', 'evidence', 'recommendation'), v)) for k, v in DECISIONS.items()}
    out['proposals'] = PROPOSALS
    out['readiness'] = [dict(zip(('requirement', 'model', 'fixtures'), r)) for r in READINESS]
    out['phase4_boundary'] = BOUNDARY
    out['identity_change_evidence'] = {
        'RENAMED': 'the source names one wine as the continuing subject under a new name (Haut-Bailly: "La Parde ... se voit renommer"; Lynch-Bages EN: "a new identity was given to the second wine")',
        'SUCCEEDED_BY': 'the source presents the new wine as replacing a discontinued one, without continuity of the wine',
        'SPLIT_FROM': 'one wine (or estate) becomes two, with dated statements for both',
        'MERGED_INTO': 'two become one, with a dated statement (La Tour Haut-Brion 2006)',
        'POSSIBLY_SAME': 'same name, no statement either way (Bellevue, La Commanderie)',
        'NEW_UNRELATED': 'no transition record at all: absence of evidence is not a transition'}
    return out


def main():
    out = build()
    text = json.dumps(out, ensure_ascii=False, indent=1) + '\n'
    if '--check' in sys.argv:
        old = io.open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        print('model is current' if old == text else 'model DIFFERS')
        sys.exit(0 if old == text else 1)
    io.open(OUT, 'w', encoding='utf-8', newline='\n').write(text)
    print('%d entities, %d enums' % (len(out['entities']), len(out['enums'])))


if __name__ == '__main__':
    main()
