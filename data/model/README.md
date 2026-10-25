# The normalized model (Phase 4)

Built by `tools/migrate.py` from the legacy data files, the manifest, the
evidence store and the discovery harvest, none of which it writes. Do not
edit these files by hand: `python tools/migrate.py --check` rebuilds them
from scratch and compares them byte for byte.

The entities and their meaning are the Phase 3.4 contract
(`docs/phase34-model.json`, `docs/PHASE-3.4-DOMAIN-MODEL.md`).

## Layout (D3)

One JSON Lines file per entity, sorted by its key, in a directory per layer:

| Directory | Layer | Holds |
|---|---|---|
| `identity/` | IDENTITY | estates, wines, vintages, sources, parties, artifacts, the identity map, names, transitions |
| `state/` | STATE | estate-wine relationships, rank assertions and absences, classification, appellation, ownership, locations, vintage statements, editorial collections, descriptors, source-estate links |
| `document/` | DOCUMENT | locators, placements, assessments, attributions, legacy document references, artifact dates and relations, families |
| `observation/` | OBSERVATION | observations from the legacy values, evidence links |
| `reconciliation/` | RECONCILIATION | one reconciliation per (subject, field) |
| `canonical/` | CANONICAL | canonical values, translations |
| `cross/` | CROSS_CUTTING | provenance records, quality findings |

`manifest.json` lists every file with its entity, row count and sha256, and
the stage the model was built to. `baseline.json` is stage M0's record of the
bytes Phase 4 must not change.

No database: the volumes do not need one and the app is a static page. The
raw documents are not copied: they stay in the gitignored `sources/`,
addressed by digest (`tools/raw_store.py`). The 163,582 harvested
observations and the 177,127 evidence decisions are read in place
(`tools/model_reader.py`), not duplicated here.

## Ids (D4)

Estates, wines, sources, parties and artifacts have opaque sequential ids
(`es_00001`, `wn_00001`, `ar_000001`, ...) minted once and kept by the
identity map; a rebuild reuses them. Every other record's id is a prefix and
a hash of its natural key. A vintage is referred to as `vt:<wine id>:<year>`.
No id is derived from, or may be parsed for, a name.
