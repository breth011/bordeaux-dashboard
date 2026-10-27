# Phase M3.11 — the value-application runner

`tools/apply-value-manifest.py` applies **already-approved** canonical values to the model from one reviewed
manifest, `data/audit/value-application-manifest.jsonl`. It is infrastructure: no document is read, no evidence is
decided, no identity is created, and the production model does not move. The manifest holds M3.10C's nine
Durfort-Vivens values, which the model already holds, so in production every row is `NOOP_EXISTING_IDENTICAL`.

## Why it exists

Until now each population phase (M3.2D, M3.6F, M3.10C) wrote its own tool, its own audited manifest, its own hook
in `mig_m7_observations.py`, and its own set-aside in the older suites, then paid a migration rebuild per batch.
The runner replaces that with one manifest format, one validator, one plan, and one migration hook
(`mig_m7_observations.value_application`). A batch is a list of manifest rows; it costs one model load whatever
its size (see Timings).

## Commands

| Command | Effect |
|---|---|
| `python tools/apply-value-manifest.py` (= `--validate`) | read-only: every problem, or "N rows valid" |
| `--plan` | read-only: the deterministic plan, packet by packet |
| `--apply` | validate → plan → verify → write the four tables and the model manifest → rebuild the indexes; all or nothing |
| `--check` | the model holds every row (each `NOOP_EXISTING_IDENTICAL`) and the model manifest's runner count matches |
| `--check-all` | `--check`, and `migrate.py`, `build-indexes.py`, `build-app-data.py --check` |
| `--manifest <file>` | another manifest (tests) |
| `--expected-scope <file>` | closed world: the exact `(vintage, field)` set; a JSON `{"expected": [...]}` or a JSONL with a `scope` record (M3.10C's manifest is one) |
| `--timings` | each stage's wall time on stderr |

`BDX_MODEL_DIR` (the migration's existing isolation, used by the rollback test) points it at another model
directory. In such a copy `--apply` does not touch `data/app`, which is the real tree's.

## Manifest schema

One JSON line per canonical field of one vintage.

| Field | Rule |
|---|---|
| `manifest_id` | `vam_NNNNNN`, unique, never reused |
| `estate_id`, `wine_id`, `vintage` | must exist; the wine must have an ESTABLISHED relationship to the estate; the vintage (an integer year) must exist for the wine. Nothing is created. |
| `field`, `value` | one of `alc`, `blend`, `months`, `oak`, `pick`, `ph`, `yld`, in the model's existing representation: `blend` `{code: share}` over the model's variety codes summing to 100; `pick` `{"ALL" or code: "MM-DD|MM-DD"}`; `months` a string (`"18"`, `"18-20"`); the others numbers in a plausible range |
| `unit` (optional) | if given, must be the model's unit for the field (`%`, `hl/ha`, or none) |
| `artifact_ids` | the artifacts whose accepted evidence states the value |
| `evidence_version` | the evidence-store version whose decisions accept them |
| `observation_group` | names the packet (see below) |
| `application_class` | `SOURCED` only |
| `source_basis` | `explicit_document_statement` only |
| `source_locations` | one `{artifact, locus, quote, lang}` per artifact |
| `raw_statement`, `notes` (optional) | audit only, never read |

**One deviation from the brief:** `source_locations` is required, not optional. The existing provenance contract
gives every observation a DOCUMENT provenance that carries the document's quote, and `test-phase4` requires one
for every SOURCED value. The runner copies each quote, locus and language into the model verbatim. It never
parses them, and it never derives a value from them.

## Packets

Rows with the same estate, wine, vintage and `observation_group` form one packet, validated and planned as a
unit. One group spanning two vintages is invalid. The same field twice in a packet is invalid, and so is the same
`(vintage, field)` in two packets.

**Several artifacts on one row are one fact.** The row gives one canonical value and one reconciliation. Each
artifact keeps its own observation, so the 2014 English and French sheets give two observations reconciled
UNANIMOUS. That is M3.10C's representation, the convention chosen there. Rows are never grouped by matching
values. A single-artifact row gets the ONLY_CANDIDATE reconciliation that the model contract gives every
canonical value; this is not a new policy.

## Evidence requirements

Every artifact must pass the whole chain, read from the model and the store, never from a file name, URL or domain:

1. the artifact exists (`identity/artifacts.jsonl`);
2. an **ACCEPTED attribution** ties it to the row's exact estate, wine and vintage. Estate-only and legacy rows are not accepted attributions, so they fail;
3. that attribution's provenance names an **evidence decision** of the row's `evidence_version`;
4. that decision is in the store and **ACCEPTED**;
5. it is still the **latest** for its context, so a later version that rejects or corrects it makes the row invalid;
6. it read **the artifact's own bytes** (`read.sha256`), and it is for the row's vintage.

The store is read from the lowest version a manifest names upward: about 0.01 s for v9, against 1.8 s for every version.

## Idempotence and conflicts

Against the model, each valid row is one of:

| Action | When |
|---|---|
| `APPLY` | no canonical value for the field |
| `NOOP_EXISTING_IDENTICAL` | the same value is held, and every artifact of the row has an observation of it |
| `CONFLICT` | a different value is held; or the same value is held, but not from these artifacts; or these artifacts' observations exist without a canonical value; or a planned row's key holds a different row |

Any invalid row or any CONFLICT stops the run before anything is written. The runner never overwrites, never
lets the latest value win, and never writes a duplicate. A second `--apply` of the same manifest writes nothing.
`--apply` computes every file first, then replaces them in turn.

## Provenance

The chain: artifact → evidence decision → manifest row → observation → reconciliation → canonical value →
application provenance.

- **Each observation** has a DOCUMENT provenance: the artifact, its quote, and a `code_state` naming the runner
  (`apply-value-manifest/1`), the manifest, the `manifest_id`, the vintage, the field, the locus, the evidence
  decision key and the evidence version.
- **Each reconciliation** has a DERIVATION provenance, the *application provenance*. It is derived from the
  observations' provenance and names the runner, the `manifest_id`, the artifacts, the observation ids, the
  evidence version, the class and the basis.
- **The canonical value** points to its reconciliation and to the selected observation's provenance, as M3.10C's
  values do.

No existing provenance is rewritten.

## The migration

`mig_m7_observations.value_application` runs last in M7. It calls the runner's own `migration_hook`, which
validates and plans against the model being built, then applies the plan with the same code `--apply` uses.
`migrate.py --check` therefore reproduces what `--apply` wrote, byte for byte; the golden test proves this. An
all-NOOP manifest adds no rows and no stat, so the production model is byte-identical to `88f8c8d`. Once a row
is applied, the model manifest counts it under `M7 / value-application manifest values`.

## M3.10C golden reference

On an isolated copy of the model at `128263f` (before M3.10C), `--apply --expected-scope
data/audit/m3.10c-value-application.jsonl` gives:

| | M3.10C (`88f8c8d`) | Runner |
|---|---:|---:|
| Canonical values | 9 | 9 |
| Observations | 12 | 12 |
| Reconciliations | 9 (3 UNANIMOUS, 6 ONLY_CANDIDATE) | 9 (3 UNANIMOUS, 6 ONLY_CANDIDATE) |
| Provenance rows | 21 | 21 |
| New estates, wines, vintages | 0 | 0 |

**Equal, field by field:**
- the values and their status (SOURCED); 2024 oak is 70;
- each observation's subject, field, value, raw value, artifact, locus, language, unit, confidence, `observed_at` and `subject_status`;
- each reconciliation's rule, status, `decided_at`, and candidate and selection order;
- each DOCUMENT provenance's kind, artifact and quote, and each DERIVATION's `derived_from` chain.

**Different, and only because the runner wrote them:**
- ids, which hash the runner's tag and actor: observation, reconciliation and provenance ids, and the references to them;
- the observation's `extraction` (method `apply-value-manifest/1`, the manifest and `manifest_id`);
- provenance `actor` and `code_state` (the runner's fields above);
- the reconciliation's `resolver` and `reason` (which names the manifest row).

The test asserts this exact set, so any other difference fails it.

**Unchanged:** every other model file is byte for byte as at `128263f`, and the model manifest differs only by
these rows' counts and the runner's stat. A migration rebuild of the same state (M3.10C's own hook set aside)
gives the isolated copy byte for byte, and its indexes check current.

## Timings

All measured on this machine.

`--apply` of the nine rows to the isolated copy:

| Stage | Time |
|---|---:|
| Model loading (ten tables, indexed) | 0.64 s |
| Evidence loading (v9 only) | 0.01 s |
| Manifest validation | < 0.001 s |
| Plan construction | 0.002 s |
| Plan verification | < 0.001 s |
| Application (four tables and the model manifest rendered) | 0.51 s |
| Output generation (`build-indexes.py`) | 0.65 s |
| Deterministic checking (`--check`, separate run) | 0.06 s after a 0.58 s load |
| **Total** | **1.8 s** |

**Scaling.** This was measured in-process with the nine rows replicated, each to its own synthetic vintage, in
memory only. Validation took 0.000 s for 9 rows and 0.002 s for 99; planning took 0.001 s and 0.006 s. Per-row
cost is under 0.1 ms. Everything else is a fixed cost per run: loading, rendering the four tables, and the
indexes. **Applying 100 values costs about what applying 10 does, about 2 s.** The old way, ten independent
mini-migrations, cost each batch its own tool, manifest and hook, plus a rebuild check of about 14 s.

**In the migration**, the hook adds about 0.3 s per build: `migrate.py --check` went from 14.3 s to 14.9 s with
two builds. `--check-all` is dominated by the migration's two builds.

There is no cache and no parallelism (§25, §26). Nothing repeated is left to optimise yet.

## Tests

`tools/test-value-application-manifest.py` has 23 checks, the brief's 22 plus a check that production is
untouched. Every application runs on a temporary copy of the model at `128263f`. They cover:

- valid manifest;
- duplicate id;
- unknown estate, wine, vintage and field;
- wine of another estate;
- invalid types, units, classes and bases;
- missing, rejected and superseded evidence;
- wrong evidence version;
- artifact of another vintage;
- duplicate field in a packet, one fact in two packets, and a group spanning vintages;
- missing and unexpected scope;
- idempotent re-application;
- NOOP in production;
- conflicting value (2024 oak 30 against 70);
- the 2014 multi-artifact rows;
- deterministic and order-independent plans;
- no partial write when row 9 is invalid;
- golden equivalence and rebuild equality;
- production untouched, with `--check-all` passing.

## Known limitations

- **Fields:** `harvest`, `sug`, `ta` and the estate-level `vineyard_area_ha` are not applied. Their units and
  representation are not settled in the model, so a row with them is invalid.
- **Same value, other source:** a value the model holds from other sources cannot be given another source. That
  would change its reconciliation, which needs a policy M3.11 does not introduce, so it is a CONFLICT.
- **Older suites:** suites written before a batch still compare the model with their own commit. The first
  production batch will need one set-aside for the runner's actor in `historical_m2_scope`, as each population
  phase has. It is one set-aside for every later batch, not one per batch. M3.11 adds none, because it changes no
  model row.
- **The app:** it projects the legacy files' records only, so an applied value without a legacy record is not
  shown, exactly as for M3.2D, M3.6F and M3.10C. Showing them is a separate phase.
- **Evidence chain:** only artifacts whose accepted attribution names its evidence decision can be applied. That
  covers M3.4B, M3.5, M3.6B and M3.10B; legacy `data/sources.json` attributions do not qualify.
