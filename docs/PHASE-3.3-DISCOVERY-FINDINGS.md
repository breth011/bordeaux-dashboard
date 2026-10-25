# Phase 3.3 — Broad Source Discovery: Findings

**Input:** commit `a112623` (Phase 3.2, `SAFE — NORMALIZATION ARCHITECTURE
COMPLETE`). Harvested 2026-10-25.

This phase **captures and records only**. No canonical file, manifest
row, evidence decision or proposal was changed, nothing was migrated, and
no field semantics were decided. The question it answers is: *what is
actually in these websites and fiches?*

## 1. What was built, and where things are

| Path | What | Committed? |
|---|---|---|
| `tools/discover.py` | the crawler: targets, robots, sitemaps, WordPress media listings, links; content-addressed storage; resumable state | yes |
| `tools/discover_extract.py` | readable content and observations from the stored bytes; pure and reproducible | yes |
| `tools/discover_report.py` | inventory, failures, source profiles, label catalogue, coverage | yes |
| `tools/test-phase33.py` | the brief's 25 properties: a local test site for behaviour, plus checks on the real harvest | yes |
| `sources/discovery/blobs/` | **the raw bytes**, named by sha256 (text-like blobs gzipped; the name is still the raw bytes' sha256) | **no** (gitignored: the estates' material is not ours to republish) |
| `sources/discovery/extracted/<sha256>.json` | the readable representation: title, headings, text blocks, tables, links, images (src, alt, caption), metadata, JSON-LD, PDF page texts | no |
| `sources/discovery/derived/years.jsonl` | every year mention with its context (369,084) | no |
| `sources/discovery/state/` | crawl frontiers, validators, robots results | no |
| `data/discovery/targets.json` | the 388 universe estates, each with its starting site and the basis for it | yes |
| `data/discovery/locations/<domain>.jsonl` | one row per fetch: URL, final URL, status, type, length, sha256, ETag, Last-Modified, when, referrer, how discovered, change status, scraper version | yes |
| `data/discovery/artifacts.jsonl` | one row per unique artifact: media, status, OCR, language detected and declared, pages, title, counts | yes |
| `data/discovery/observations/<aa>.jsonl` | 163,582 label/value statements: raw label, raw value (capped at 200 characters; the full text is local), normalisation beside it, locus, language, method, confidence, an INFERRED category guess | yes |
| `data/discovery/vintage-candidates.jsonl` | per artifact, the years in its URL, title and headings, plus counts of prose years by kind | yes |
| `data/discovery/roles.jsonl` | 10,700 role statements, quoted with context | yes |
| `data/discovery/wines.jsonl` | 3,988 wine-name candidates, each KNOWN_NAME or UNRESOLVED | yes |
| `data/discovery/attribution.jsonl` | candidate estates per artifact, with graded evidence | yes |
| `data/discovery/profiles.json` | per source: every fact marked OBSERVED, INFERRED or UNKNOWN | yes |
| `data/discovery/labels.json`, `coverage.json`, `failures.jsonl`, `inventory.json` | the catalogue of 12,911 labels, per-estate coverage, every failure, the counts | yes |

The layers follow Phase 3.2:

| Phase 3.2 concept | Here |
|---|---|
| Artifact | `artifacts.jsonl` + blob |
| ArtifactLocation | `locations/` |
| ExtractedContent | `extracted/` |
| ObservedStatement | `observations/`, `roles`, `vintage-candidates` |
| AttributionCandidate | `attribution.jsonl` |

## 2. How the crawl behaved, and what limits its claims

**Scope.** The 388 estates of the Phase 3.0 universe. Each starts from
the site `websites.js` gives its matched canonical estate. That address is
a starting point recorded with its basis, not a fact verified here. 339
estates have one, across 304 domains. **49 have no known site** and were
not searched for, because finding sites was not this phase's task.

**Access.** robots.txt was honoured for this crawler, for `*`, and for
the AI-agent tokens (ClaudeBot, Claude-User, Claude-SearchBot,
anthropic-ai, Claude-Web), because the crawl is run by an AI agent. Other
rules:

- **Rate:** at least 1.5 s between requests to one host, or the site's
  Crawl-delay.
- **Not bypassed, only recorded:** challenges, authentication, TLS
  failures.
- **Content-Signal:** no site carried `ai-input=no`.

**Budget.** Each site was capped at 120 pages, 200 documents, 380
requests and 25 minutes, with single files capped at 25 MB (archives at
5 MB). Of 304 domains:

| Outcome | Domains |
|---|---|
| Exhausted their frontier | 256 |
| Stopped at the budget | 29: the largest sites (Margaux, Mouton, Lafite, Haut-Brion, La Mission, Léoville Las Cases, Latour-Martillac, Vignobles K and others) |
| Refused crawlers site-wide | 19 |

**This is therefore not a complete census of any large site.** The
inventory says so in its own `completeness` field.

**Changes made during the run.** The crawl was stopped and resumed once.
The local disk had 14 GB free, and the uncompressed store was on course
to need about 18 GB. Version `discover/1.0` gained these changes mid-run,
none of which alters what is retrieved:

- gzip storage for text-like blobs, with identity unchanged;
- a 6 GB free-space guard;
- the archive cap;
- a fix for malformed-port links, which had crashed two domains (both
  resumed);
- a fix for a Windows rename race, which had crashed one more (resumed);
- link-following from the stored copy on `304 Not Modified`.

The final store is 7.7 GB.

**Estate coverage** (`coverage.json`):

| System | Reached | Partial | Unreachable | Blocked by policy | No known site |
|---|---|---|---|---|---|
| 1855 Médoc/Graves | 50 | 2 | 7 | 2 | 0 |
| 1855 Sauternes–Barsac | 21 | 1 | 1 | 3 | 1 |
| Graves (besides Haut-Brion) | 12 | 0 | 0 | 1 | 0 |
| Saint-Émilion 2022 | 64 | 6 | 4 | 7 | 4 |
| Crus Bourgeois 2025 | 101 | 6 | 19 | 11 | 33 |
| Crus Artisans 2022–26 | 15 | 3 | 3 | 0 | 11 |
| **Total** | **263** | **18** | **34** | **24** | **49** |

**Why estates were unreachable (34):**

| Cause | Estates |
|---|---|
| TLS failure | 19 (e.g. Château Lagrange: the server drops every TLS handshake) |
| Timeout | 9 |
| Network failure | 3 |
| HTTP error | 2 |
| Off-site redirect | 1 |

**Blocked by policy (24 estates, 19 domains).** All 19 domains refuse AI
agents by name in robots.txt while allowing other crawlers. Among them:

- Bernard Magrez (Pape Clément, La Tour Carnet, Clos Haut-Peyraguey);
- Canon, Rauzan-Ségla, Rayne-Vigneau, Suau;
- Berliquet, Larmande, Montlabert;
- Vignobles Cap de Mourlin, Château Castel.

They are recorded and not crawled. That is the policy working as
intended, and it is the main reason some top estates have no
first-party material in this harvest.

**Failures recorded** (`failures.jsonl`, 2,950):

| Kind | Count |
|---|---|
| HTTP errors | 1,644 (mostly 404s for probed sitemaps and media listings) |
| Robots refusals of single URLs | 586 |
| Off-site redirects | 271 |
| Too large | 134 |
| TLS failures | 98 |
| Timeouts | 96 |
| Network failures | 39 |
| Redirects into robots-refused URLs | 25 |
| Site-wide refusals | 19 |
| Bot challenges | 14 |
| Authentication required | 13 |
| Redirect loops | 8 |
| Crawler crashes | 3 (all resumed) |

## 3. The inventory

| | |
|---|---|
| Requests logged | 35,776 |
| Retrieved OK | 32,794 (22,037 pages, 9,469 documents and other files) |
| Unique artifacts | **29,517** |
| By media | 20,086 HTML pages, 7,197 PDFs (14,550 pages), 896 sitemaps, 610 images, 444 JSON responses, 93 feeds, 88 text files, 8 office files, 8 XML files, 87 unsupported |
| Artifacts at several URLs | 482 |
| URLs that served several versions | 500 |
| Extraction | 28,818 extracted, 2 failed (bytes kept), 610 images stored but not extracted, 87 unsupported |
| OCR | 374 PDFs have too little text, i.e. image PDFs. There is no OCR engine on this machine, so they are kept and flagged `NEEDED_NO_ENGINE` |
| Languages detected (artifacts) | French 16,707 · English 7,880 · Chinese 1,053 · German 250 · Japanese 239 · Spanish 143 · Russian 43 · Portuguese 42 · Dutch 42 · undetected 1,796 |
| Observations | 163,582: label + colon 111,986; label line then value 43,218; two-cell table rows 5,282; definition lists 3,096 |
| Distinct labels | 12,911; 497 occur on five or more sites |
| Year mentions | 369,084, split by context below |
| Role statements | 10,700 |
| Wine-name candidates | 3,988, of which 3,681 match no canonical name |
| Artifacts naming several estates | 519 |
| Sites that moved domain | 31 (e.g. Calon-Ségur `.com` → `.fr`, Belair-Monange → `belairmonange.com`) |
| JSON-LD present | 13,339 artifacts (mostly CMS-generated organisation and page metadata) |
| Re-crawl changes | 0 (the full crawl ran once; change detection is exercised by the tests) |

## 4. What the sources contain

### 4.1 Technical information is far richer than the dashboard holds

The ten most widespread labels on estates' own pages and sheets, by
number of sites:

| Label (folded) | Sites | Category guess |
|---|---|---|
| élevage / ageing / aging | 130 / 77 / 35 | winemaking |
| assemblage / blend | 120 / 67 | winemaking |
| vinification / winemaking | 109 / 32 | winemaking |
| terroir | 92 | vineyard |
| encépagement / grape varieties / cépages | 86 / 37 / 26 | vineyard |
| appellation | 78 | appellation |
| harvest / vendanges / harvest dates | 74 / 44 / 26 | vintage |
| production | 71 | production |
| millésime / vintage | 69 / 41 | vintage |
| superficie / surface / surface area | 59 / 37 / 25 | vineyard |

The current 105-field model already covers blend, ageing months, oak,
yield, alcohol, pH, harvest dates and tasting text. **The sources
regularly state much that it does not hold:**

- **Vineyard.**
  - Planting density: 40 + 27 sites, French and English.
  - Average vine age: "âge moyen des vignes" 49 sites, "âge moyen du
    vignoble" 25, "average age of the vines" 23, "âge des vignes" 20.
  - Soils: "soil" 49 sites, "sol" 28, "sols" 24 (overlapping), plus
    "sous-sol".
  - Vineyard area: "superficie" 59 sites, "surface" 37, "surface area" 25
    (overlapping).
  - Parcels; exposure.
- **Winemaking:** fermentation (25 sites), maceration and its length,
  vat types (stainless, concrete, wood, amphora), bottling date ("mise en
  bouteille", 30 sites), fining and filtration, yeast.
- **People:** oenologue conseil (11 sites), "propriétaire" (40 sites) and
  "owner" (29), technical director, cellar master.
- **Production:** quantities in bottles, on 71 sites; formats and
  capacity ("contenance").
- **Analytical** beyond alcohol and pH: total acidity with its unit,
  residual sugar, volatile acidity, SO₂, IPT/polyphenol index (it appears
  in the Chinese sheets as 总多酚指数).
- **Commercial:** prices ("prix", "tarif", 24 and 26 sites), en-primeur
  release, availability, shops.
- **Tourism:** opening hours, visit length, visit prices, languages
  offered. These are frequent and highly structured.

### 4.2 Highly structured information

The technical sheet is a stable genre. Across French, English and Chinese
it uses one recurring label set, typically: appellation, superficie,
encépagement, sol, densité, âge des vignes, vendanges, rendement,
vinification, élevage, assemblage, degré/alcool, pH, acidité, production,
garde, service. That is where a later schema can be grounded.

Corporate legal notices are also structured, and present on dozens of
sites: siège social (42), SIRET (36 + 12), capital social (16), forme
juridique (14), directeur de la publication (32), hébergeur (27). This is
the estate's **legal entity**, a kind of identity data the model does not
have. It may help resolve ownership and group questions.

### 4.3 Highly variable information

- **The same fact under many labels:** area (superficie, surface, surface
  area, area, "hectares"), ageing (élevage, ageing, aging, durée
  d'élevage).
- **The same label for different facts:** "production" (bottles, hectares
  or both), "terroir" (a soil statement, a page heading, a menu item),
  "note" (a critic's score, or a footnote).
- **Units and forms:** "18 mois", "18 months", "16-20 mois", "en barriques
  pendant 18 mois dont 50 % neuves".

Raw values are kept verbatim, with normalisation beside them, so these can
be reconciled later rather than now.

### 4.4 Roles: far more vocabulary than "second"

Role wording found (10,700 statements):

| Wording | Count |
|---|---|
| grand vin | 3,760 |
| second vin / seconds vins / second wine(s) | 2,176 / 210 / 1,209 |
| cuvée prestige / cuvée spéciale | 707 / 63 |
| blanc sec / vin blanc sec / dry white (wine) | 636 / 99 / 393 |
| liquoreux / vin liquoreux / sweet (white) wine | 415 / 177 / 81 |
| premier vin / first wine | 172 / 141 |
| grand vin blanc sec / grand vin blanc / grand vin rouge | 94 / 50 / 12 |
| second label | 70 |
| deuxième vin | 67 |
| petit frère / little brother | 39 / 12 |
| troisième vin / third wine(s) | 35 / 21 |
| Zweitwein | 45 |

Findings that matter for the role model (Phase 3.2 §5):

- **"Third wine" is real and recurring** (troisième vin, third wine).
- **"Sélection parcellaire" / "plot selection" is a role of its own.**
  Latour-Martillac's own 2026 press kit, in French and English, lists:
  - Château Latour-Martillac (red and white), Grand Cru Classé de Graves;
  - Lagrave-Martillac (red and white), "second vin";
  - Lacroix-Martillac par Latour-Martillac (red and white), "sélection
    parcellaire".
- **"Cuvée prestige" is common on Cru Bourgeois and Cru Artisan sites**,
  as a wine *above* the château wine. The model's GRAND_VIN /
  SECOND_WINE / OTHER_CUVEE ranks have no slot for a wine ranked above the
  grand vin.
- **Some estates reject the hierarchy outright.** Vignobles K: Château Le
  Rey's two wines, Les Argileuses and Les Rocheuses, "do not represent as
  usual in Bordeaux first and second label, but are made like in Burgundy
  with a terroir philosophy".
- **"Grand vin" is also used within a colour range,** as Phase 3.2
  anticipated: "grand vin blanc sec" 94 times (Caillou's Myosotis is one).
- **The detector misses some role wordings.** "2nd vin" (12 contexts,
  e.g. Echo's own sheets: "Classification 2nd vin du Château
  Lynch-Bages"; "Dame de TrotteVieille, 2nd vin du Château TrotteVieille")
  and "2ème vin" were caught only through neighbouring words. **The role
  list is a discovery aid with known gaps, not a complete inventory.**

### 4.5 Wines

3,988 name candidates were extracted from titles, headings, link texts,
filenames, first pages and role contexts. 3,681 match no canonical name,
but **most of these are not wines**:

- section headings ("Le Domaine", "Les Vins", "Le Vignoble");
- grape varieties ("Petit Verdot");
- publications ("La Revue du Vin de France", "Le Figaro");
- places.

The candidate list is raw discovery output, all marked UNRESOLVED. It
needs the identity work of Phase 4 before it says anything about wines.
Among the real finds:

| Wine | What the harvest shows |
|---|---|
| Les Terrasses de Saint Christophe | 22 artifacts on vignoblesk.com, incl. product sheets: "Les Terrasses de Saint Christophe is the second label of Château Tour Saint Christophe … made from some of the younger vines planted on the terrasses of the estate"; surface 11 ha; clay-limestone; 90 % Merlot / 10 % Cabernet Franc |
| Les Murets de Caillou | 72 artifacts on chateaucaillou.com; the 2023 sheets, in French *and English*, say "Second Vin blanc sec du Château Caillou" / "Second dry white wine of Château Caillou"; shop pages call it "AOC Bordeaux blanc sec" |
| Château Haut-Bages Averous | named on 3 Lynch-Bages artifacts, with the historical statement Phase 3.0 used |
| Les Divertissements de Malle | 3 artifacts on chateaudemalle.com, including a press dossier |
| Château Tour Saint Christophe 'Angela' | one artifact, "Bordeaux Blanc" |
| Les Argileuses, Les Rocheuses (Château Le Rey) | about 30 artifacts each on vignoblesk.com, an estate *outside* the universe, recorded and not followed |
| Lacroix-Martillac | named in over 100 extracted artifacts; missed by the name detector, which wants an article or "Château" in front, but present in the role statements |
| Les Arums de Lagrange, Pagus de Lagrange | **not harvested**: Château Lagrange's site was unreachable (TLS). One harvested artifact mentions "Pagus" |
| R de Real Caillou | **not found** in any harvested artifact |

### 4.6 Vintages

Year mentions were classified by where and why they occur, not assumed to
be vintages:

| Kind | Mentions | Means |
|---|---|---|
| URL or filename | 21,054 | the strongest document-vintage candidate (`fiche-2019.pdf`) |
| Title | 9,507 | document-vintage candidate |
| Heading | 25,745 | often a vintage; also "depuis 1855" style headings |
| Harvest or vintage (by nearby word) | 79,268 | "millésime 2019", "vendanges 2022" |
| Ownership | 11,506 | "acquis en 1998", "depuis 2012" |
| Classification | 11,919 | "classé en 1855", "Grand Cru Classé 2022" |
| Founding or history | 7,876 | "fondé en", "XVIIIe siècle" |
| Other dates in prose | 202,209 | everything else |

`vintage-candidates.jsonl` keeps, per artifact, the URL, title and heading
years separately, so a document's vintage can be judged later from its
own evidence.

### 4.7 History and ownership

History is abundant and specific: 11,506 ownership-dated mentions and
7,876 founding or history mentions, plus "propriétaire" labels on 40 sites
and "owner" on 29. The model's single `owner` string cannot hold what the sources
say: successive families, dates of acquisition, groups, directors.
Phase 3.2's Ownership with validity is the right shape for it. The legal
notices (§4.2) add the operating company.

### 4.8 Shared sources and groups

- **25 domains serve several target estates by design.** Bernard Magrez,
  Vignobles K, Neipperg, lafite.com (three estates), Unimédoc (a
  cooperative, six estates), Cave de Listrac, Domaines Quié, Vignobles
  Lacombe, CDF Châteaux, Antoine Moueix and others.
- **Further domains name other universe estates in their titles or
  filenames.** Boyd-Cantenac names Pouget; Antoine Moueix names
  Lacombe-Noaillac and Patache d'Aux; Vignobles de Terroirs names Broustet
  and Les Lattes.
- **519 artifacts name several estates in their title, filename or
  headings.**

Crawl context (the site an artifact was found on) is therefore kept as
the weakest attribution candidate. In the test site, the second estate on
a shared host gets only `CRAWL_CONTEXT`, while the named estate gets
`NAMED_IN_*` evidence.

### 4.9 Multilingual material

**Chinese (1,053 artifacts) and Japanese (239) are significant.** Lynch-Bages,
for instance, publishes complete Chinese technical sheets with their own
labels:

| Label | Means | Value as printed |
|---|---|---|
| 酸度 | acidity | 4.2克/升（以硫酸计） |
| 酒精度 | alcohol | 12.5度 |
| 总多酚指数 | total polyphenol index | — |

French and English versions of one sheet do not always agree (Phase
3.2's Badette case). They are kept as separate artifacts with their own
languages, never assumed equivalent.

### 4.10 Information whose meaning is unclear

- **Two-cell tables and "label then value" lines** without units (e.g.
  "Production | 12").
- **Estate-level versus wine-level statements** on pages covering several
  wines.
- **"Note" labels:** critic scores, or footnotes.
- **Critic score lists** (Yves Beck, Jane Anson, Jeb Dunnuck, Markus del
  Monego, Jean-Marc Quarin, Bernard Burtschy …) on dozens of sites.
  Whether these are first-party claims or reproduced press is a provenance
  question.
- **374 image-only PDFs** await OCR.

## 5. What this means for the Phase 2 proposals

Nothing was applied. What the harvest adds:

**Terrasses.** The owner's own **product sheets** state "second label of
Château Tour Saint Christophe", alongside the wine page Phase 3.0 read.
Phase 3.0 set fiches aside as authority (Rule 3), but these are published
on the owner's site with that wording. That strengthens the role evidence
for a later decision. It does not change the rule that it must be
decided, not inferred.

**Murets.** The English 2023 sheet repeats the French: "Second dry white
wine of Château Caillou". The shop calls it AOC Bordeaux blanc sec, and a
red Murets also exists. This supports the DEFERRED role "second wine of
the dry-white range" (Phase 3.2, C2), and still needs the decision.

**Echo.** The estate's own sheets say "Classification 2nd vin du Château
Lynch-Bages", consistent with Phase 3.0. The proposal (the manifest's 50
rows) remains a canonical decision for later.

## 6. Candidate future information model (discovery-only)

These groups are derived from the labels and statements actually found,
not from the current fields. They are a map for Phase 4's decisions, not
a schema.

| Group | Evidence in the harvest | New relative to the 105 fields |
|---|---|---|
| **ESTATE IDENTITY** | names, addresses, GPS, contact, websites, moved domains | moved domains; aliases from site text |
| **LEGAL ENTITY** | siège social, SIRET, capital, forme juridique, publication director, host | entirely new |
| **OWNERSHIP & PEOPLE** | owner, family, group, director, oenologue conseil, cellar master, with dates | people; dated ownership |
| **GROUP / SHARED SOURCE** | multi-estate domains, letterheads, co-operatives | new as a relation |
| **CLASSIFICATION** | classification statements and years, medal and label claims | dated claims |
| **APPELLATION** | per wine; colour-specific (red and white of one estate) | per wine |
| **VINEYARD** | area, parcels, soils and subsoils, exposure, density, vine age, varieties as planted | mostly new |
| **VINTAGE CONDITIONS** | weather narrative, phenology, harvest dates, yields | partly present |
| **WINEMAKING** | sorting, fermentation, maceration, vessels, temperature, yeast, ageing, oak share and origin, fining, bottling date | mostly new |
| **ANALYTICAL** | alcohol, pH, TA with unit, residual sugar, VA, SO₂, IPT | partly present |
| **BLEND** | per vintage, per wine | present |
| **TASTING** | colour, nose, palate, finish, descriptors | present as prose |
| **SERVICE & AGEING** | serving temperature, decanting, drinking window, food pairing | partly present |
| **PRESS & SCORES** | critic, score, date, as quoted by the estate | new as first-party quotations |
| **PRODUCTION & FORMATS** | bottles produced, formats, capacity | new |
| **COMMERCIAL** | prices, en-primeur release, availability, shops | new |
| **WINE RANGE & ROLE WORDING** | grand vin, second, third, plot selection, cuvée prestige, "not first and second", per colour | richer than any current vocabulary |
| **SUSTAINABILITY** | organic, biodynamic, HVE, Terra Vitis, practices | new |
| **HISTORY** | founding, mergers, acquisitions, renamings, technical changes | new as dated records |
| **VISITS & HOSPITALITY** | opening hours, visit length and price, languages, accommodation | new, highly structured |
| **MEDIA** | images with alt text and captions, image-only documents | new |

## 7. Tests

`tools/test-phase33.py` checks the brief's 25 properties.

**Behaviour**, on a local test site served by `http.server`:

- two estates on one host;
- a robots-refused folder;
- one PDF at two paths;
- a PDF replaced by new bytes;
- a malformed PDF;
- French and English pages.

The real crawler, extractor and report run against it three times:
first, unchanged, then changed.

**On the harvest:**

- consistency between locations and artifacts;
- coverage for every estate;
- blocked sources represented;
- a sample of 25 artifacts re-extracted from the stored bytes, which must
  reproduce the committed observations exactly;
- the scope invariants: canonical files, evidence, proposals.

**SAFE — BROAD DISCOVERY HARVEST COMPLETE**
