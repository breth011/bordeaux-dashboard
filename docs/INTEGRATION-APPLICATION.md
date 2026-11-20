# The integration application: its lifecycle and its two states

The first controlled application of the integration review's manifests (`tools/integration-review.py --manifests`). `tools/integration_application.py` names it exactly; this document says how it is carried out and how the repository's checks see it.

## The lifecycle

Each step is an existing runner or generator. Nothing is edited by hand.

| Step | Command | Result |
|---|---|---|
| 1. Manifests | `python tools/integration-review.py --manifests` | 34 acceptance rows, 33 vintage rows, 51 value rows after M3.10C's nine. Their bytes are pinned (`DIGEST`), and every acceptance row records reader `6f68a0af15d3`. |
| 2. Evidence | `python tools/apply-evidence-acceptance-manifest.py --apply`, then `--check` | Store v9 → v10: 34 decisions. |
| 3. Attributions | `python tools/apply-vintage-creation-manifest.py --apply`, then `--check` | 0 vintages created, 33 `ATTRIBUTION_ONLY`: 34 attributions (17 `REVIEWED_LISTING`, 17 `DOCUMENT_TEXT`) on 51 provenance rows. |
| 4. Values | `python tools/apply-value-manifest.py --apply`, then `--check` | 51 values, observations and reconciliations on 102 provenance rows (36 statements, 15 C6 `UNIT_FROM_LAYOUT`). M3.10C's nine are held. |
| 5. Derived | `python tools/quality-audit.py`, then `--check` | Phase 4's audit of the live model: one orphan document fewer (723 → 722). |
| 6. Rebuild check | `python tools/apply-vintage-creation-manifest.py --check-all` | The migration, the indexes and `data/app` rebuild byte for byte. The dashboard data does not change. |
| 7. Commit | — | The application. |
| 8. Register | `python tools/integration_application.py --record-resolution`, then `python tools/build-data-gap-register.py`, `--report` and `--check-all` | `data/audit/m32-resolutions.json` gains `INTEGRATION`, with the commit of step 7. The register records it on the 4 gaps it reduced (32 items). |
| 9. Commit | — | The register's record. |
| 10. Verify | `python tools/integration_application.py --check`, then the full suite | Every figure of the post-apply state is exact. |

The final counts are 5,292 vintages, 13,055 canonical values and 12,245 attributions.

## The two states

`integration_application.phase()` returns `PRE_APPLY` or `POST_APPLY`. A state partway between them (manifests written but not applied, one stage applied without the next, a row edited afterwards) is neither, and `phase()` fails. `verify()` checks the current state's figures exactly, and `tools/test-integration-application.py` asserts them.

The application's model rows are recognised by their own provenance only: one of its two runners, its stream, its manifest file and one of its pinned manifest ids. A later run of the same runners carries other ids, and nothing here sets it aside.

## How the earlier phases' checks see it

- **"Nothing else changed" guards** (`tools/historical_m2_scope.py`): the application is set aside exactly, as M3.10C is.
  - Its rows, by `is_row`.
  - Its v10, verified to be exactly its 34 decisions (`LATER_EVIDENCE_VERSIONS`).
  - Its stats and row counts in the model manifest.
  - Its resolution entries in the gap register (`LINKING_PHASES`).
  - The quality audit's change: exactly the documents its attributions newly attribute (`quality_audit_unchanged_but_ia`).
- **Historical reports read the model as of their phase.** `data_gap_analysis` hides the application's rows, as it hides M3.6D's, M3.6F's and M3.10C's. M3.3's source plan counts what `INTEGRATION` resolved as unresolved when the plan was made (`LATER`). M3.6B's report sets aside the evidence diff of v10, as it does v7–v9. M3.4A, M3.4B, M3.5, M3.6A-RERUN and M3.6B therefore reproduce byte for byte. No fingerprinted file changed.
- **The integration dry run** reads values and attributions without the application's rows. It is the record of the state before the application.
- **The runner suites' synthetic cases** (V1, M3.11, generic registration) are built on the state before the application: the model as committed at `PRE_APPLY_COMMIT`, the value manifest's first nine rows, and a store without v10. Their production checks assert each state's exact figures.
- **Pre-apply guards** (for example `test-integration-review` t07 and the runners' "production manifest empty" checks) assert exactly the pre-apply state in `PRE_APPLY`, and exactly the applied state in `POST_APPLY`. No check accepts either.
