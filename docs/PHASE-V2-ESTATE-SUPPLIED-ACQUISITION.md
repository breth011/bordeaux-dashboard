# Phase V2 (contract): estate-supplied acquisition

A second acquisition mode for the generic registration runner, so that a document an estate itself sends can become
a model artifact without inventing web-fetch facts. **Contract only.** The supplied-acquisition audit and the
registration manifest are committed empty. No estate was contacted, no document was acquired or held, and nothing
in the model, the evidence store or the app changed.

Why it exists: the V2 target, Château de Myrat 2023, has no public first-party sheet. The estate's site lists
vintages only to 2013, and its fiches sit under `/images/`, which its robots.txt disallows. The only clean route is
a file the estate sends. Until now the registration contract could only describe a fetch: URL, final URL, HTTP
status, fetch time.

## The modes

A row's mode is its acquisition audit's (`ACQUISITION_AUDITS[...]['mode']`), never its own fields'.

| Field | HTTP (`data/audit/m3.8-acquisition-pilot.jsonl`) | ESTATE_SUPPLIED (`data/audit/estate-supplied-acquisitions.jsonl`) |
|---|---|---|
| `registration_id`, `sha256`, `bytes`, `media_type`, `held_path`, `retrieval_method`, `acquired_by`, `origin`, `acquisition` | required | required |
| `url`, `final_url`, `http_status`, `fetched_at` | required | **forbidden** |
| `received_at`, `original_filename`, `supply_channel` | **forbidden** | required |
| `source`, `source_relationship` | optional (only where the record attributes the fetch) | required |
| `notes` | optional | optional |
| the record's `retrieval` | `OK` | `SUPPLIED` |
| the row's `origin` | `EXTERNAL_ACQUISITION` | `ESTATE_SUPPLIED` |

HTTP mode is the previous contract unchanged: the same fields, the same exact match against M3.8's record, the same
placement and placement id.

## What makes "estate supplied" true

For a supplied row, all of these must hold. None is specific to an estate:

- the record's `supplier.relationship` and `supplier.source` are the row's;
- the relationship is a confirmed M3.7 one: `CONFIRMED_FIRST_PARTY` or `CONFIRMED_ESTATE_CONTROLLED`;
- the relationship's source is the row's source, and its estate is the record's supplier estate;
- the source is in the model;
- the record's `sender_domain` is that source's host as M3.7 recorded it (`www.` ignored);
- the record holds a hashed receipt and the supplied statement;
- `held_path` is `sources/acquisition/supplied/<sha256>/<original_filename>`, and the filename is one safe path
  segment: no `/ \ : * ? " < > |`, no control characters, not `.` or `..`, no leading or trailing space, no trailing dot.

A different estate needs its own confirmed M3.7 relationship. There is no generic first-party flag. The only supply
channel is `EMAIL_ATTACHMENT`: a link the estate sends is a fetch, and belongs in HTTP mode through an acquisition
audit.

## The recorder

`python tools/record-estate-supplied-acquisition.py --eml <message.eml> --attachment <file name> --relationship <id>`

Every fact is read from the received message. Nothing is typed in:

- **The file:** the attachment's bytes, which are hashed and measured here, and its file name exactly as sent.
- **The receipt date:** the day of the Date header, in UTC.
- **The sender:** the domain of the From address.

All checks run before anything is written. The tool writes:

- **Under `sources/` (gitignored):** the attachment, and beside it a `receipt.json`. The receipt holds the Date
  header, the sender's domain, and hashes of the message, its Message-ID and the attachment. No address, name,
  subject or body is kept.
- **The audit:** one `scope` row, then one `item` row per file, in canonical form.

`--check` re-hashes every held file and receipt, re-runs the runner's own supplied check on every item, and verifies
the audit's form. An empty audit is valid.

## Placement

The model primitives already exist, so `model_schema.py` is unchanged:

- **Locator:** `LOCAL_PATH`, valued relative to `sources/` (`acquisition/supplied/<sha256>/<original_filename>`).
- **Status:** `PRESENT`, on the supplier's source.
- **`observed`:** an EXACT day bound on `received_at`.
- **`retrieval_method`:** "supplied by the estate (EMAIL_ATTACHMENT)".
- **Provenance:** `DOCUMENT`, whose `code_state` names the stream, origin, relationship, channel, received date and
  original filename. It names no URL, status or fetch time.

The placement id is `hid('Placement', 'LOCAL_PATH', value, artifact, 'arm')`. The runner's "already placed" check now
compares (locator kind, value), and URL rows produce exactly the ids they did before.

Legacy `LOCAL_PATH` placements are untouched: legacy references take their candidates from M2's own placements,
before any M6 hook runs.

## Evidence acceptance

Unchanged. A supplied artifact's held file is under `sources/acquisition/`, so its decision folder is
`acquisition:<sha256>`, as M3.10B's are. Its locator's basename is the estate's file name, so the decision names the
document by it. The focused test confirms both points on an isolated copy.

## Tests

`python tools/test-estate-supplied-acquisition.py`: 10 checks covering 22 cases plus the production state.

- **Mutual exclusion:** each HTTP field in a supplied row, and each supplied field in an HTTP row, is refused.
- **Retrieval and origin:** each must be its mode's.
- **Supplier identity:** wrong estate, wrong source, an unconfirmed relationship, another estate's relationship, a
  sender domain that isn't the source's host, a source not in the model.
- **Bytes:** a wrong sha256 or size, tampered held bytes, unsafe filenames.
- **On an isolated copy:** one artifact appended after every existing id, one deterministic `LOCAL_PATH` placement,
  and a rebuild from scratch and with the registry equal to the applied model. Every earlier placement is unchanged,
  and M3.10A's HTTP rows are still NOOP.

The fixture is a generated test PDF in a fabricated message from Château Calon-Ségur's confirmed source, recorded only
into temporary directories. `tools/test-generic-evidence-registration.py` still passes 22 of 22. One of its candidate
selections reads the runner's internal placement index, and was adjusted to the index's new (kind, value) shape.

## What the first real supplied file will need

These are not made here, and no frozen expectation changed:

1. **One real file:** the estate's file, recorded with the recorder, and one registration row in supplied mode.
2. **Set-asides for the frozen checks that will see it,** keyed on the mechanism rather than the file:
   - `historical_m2_scope.model_changes_are_m2_only` and `test-m310a` (t06 pins the sha256-only artifact count at +4);
   - the as-of readers (`data_gap_analysis`, and `extract-document-dates.py`, which reads `LOCAL_PATH` placements);
   - for its acceptance at v10, `test-m310b` t02 and the evidence-store guards (which pin the newest version at v9).
3. **The V2 review audit and its tool.** It uses M3.9's format and the unchanged reader, and presents the file under
   its original name. Its name goes into the acceptance runner's `REVIEW_CHECKS` and V1's `REVIEW_AUDITS` (an
   approved one-line change).
