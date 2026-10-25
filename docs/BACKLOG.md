# Backlog

Decisions deferred on purpose, with what is known about each. An item leaves this list when a decision
takes it up.

## Presentation order of estates

*Added 2026-10-25, at the Phase 5 application source switch.*

The normalized model holds no display order, so the generated application files list estates by id.
Since the switch, the producers list reorders within **24 of its 28 growth groups**. For example, the
1855 first growths show Haut-Brion before Lafite instead of in the official classification sequence.
The autocomplete's top nine for a broad query, such as *chateau*, also change.

No value, search result set, lookup, drawer or wine order changed. The reordering was accepted for the
switch and put here.

Open question: where display order belongs. Candidates:

- an order or sequence attribute in the model, as a model decision;
- an editorial presentation asset outside the model, beside the map and notes files;
- sorting rules in the application, such as official listing order or name.

Measured by `tools/app-reference.py`, under "EXPECTED: PRESENTATION ORDER"; see
`docs/PHASE-5-APPLICATION-SOURCE-SWITCH.md` §5.

## C4 — lazy loading of vintage records

*Deferred 2026-10-25, Phase 5 decision §4.4.*

68 % of the startup bytes are vintage records that are read only on demand. The estimated gain is
150–200 ms on a cold start; a warm start is already about 140 ms. See
`docs/PHASE-5-OPTIMIZATION-CANDIDATES.md`.

## C5 — search redraw

*Deferred 2026-10-25, Phase 5 decision §4.4.*

The list and the map redraw on every keystroke: 19–40 ms at M0, 20–46 ms after the switch. The M0
measurement is the reference.

## Document dates — what M2 could not read

*Deferred 2026-10-25, historical model M2 (`docs/PHASE-M2-DOCUMENT-DATES.md` §8, §12).*

- **Text for the PDFs that never had it.** 4,992 PDFs and 612 images hold no extracted text, so a
  date they print is unread (NO_TEXT_HELD). Extracting them is a discovery-store change and needs
  its own reproducibility story.
- **The other ArtifactDate kinds.** PDF_METADATA, HTTP_LAST_MODIFIED, UPLOAD_PATH and RETRIEVED are
  recorded only as audit flags. They could become ArtifactDate rows of their own kinds. They would
  be clues about when a file existed, never the document's stated date.
- **Boilerplate across a site.** A footer date repeated on every page of a site is rejected today
  only because it stands away from the h1. Detecting the same quote across one site's pages would
  make that rule explicit.
- **Suite time.** `test-historical-m2`'s reproducibility check reruns the extractor over every
  document (about 105 s), which adds about 85 s to the full run. A narrower check, rerunning only
  the accepted, ambiguous and rejected-reference rows, would keep most of the proof at a fraction
  of the time.
