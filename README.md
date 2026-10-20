# Bordeaux Classified — interactive dashboard

Open **`index.html`** in any browser for the standalone dashboard. No build step or install is
needed. To install it as an app and enable offline launch, serve this folder over HTTPS (or
`localhost`) and use the browser's **Install app** option. On iPhone or iPad, open it in Safari
and choose **Share → Add to Home Screen**. The first online visit caches the dashboard for offline use.
For local desktop testing, run this in the project folder and open the printed localhost address:

```powershell
python -m http.server 8000
```

**374 estates across ten collections and 43 vintages (1982–2024)**, on a map and in depth.
You start by choosing a collection; the map and the producer list follow from that.

Some collections hold the whole published roster; others hold its upper tiers only, which the
table below states outright rather than implying.

---

## The ten collections

| Collection | Region | Estates here | Tiers |
|---|---|---|---|
| **Classification of 1855** | Médoc & Graves | 61 — the full list | Premiers → Cinquièmes Crus |
| **Sauternes & Barsac 1855** | Sauternes | 27 — the full list | Premier Cru Supérieur, Premiers, Deuxièmes |
| **Saint-Émilion 2022** | Right Bank | 14 of the 85 — the Premiers Grands Crus Classés | 1er Grand Cru Classé A / B |
| **Pomerol** | Right Bank | 17 leading estates | *editorial grouping — no classification exists* |
| **Crus Classés de Graves** | Pessac-Léognan | 16 — the full list | flat list; red, white, or both |
| **Crus Bourgeois du Médoc 2025** | Médoc | 170 — the full list | Exceptionnel (14), Supérieur (36), Cru Bourgeois (120) |
| **Crus Artisans du Médoc** | Médoc | 34 | flat list |
| **Fronsac & the Libournais satellites** | Right Bank | 15 | appellations, not ranks |
| **The Côtes de Bordeaux** | Both banks | 12 | appellations, not ranks |
| **Graves & Entre-Deux-Mers** | Left Bank | 9 | appellations, not ranks |

Plus **All of Bordeaux** — every estate on one map, which is the only way to see that a Cru
Bourgeois and a First Growth are often three kilometres apart on the same gravel.

Château Haut-Brion is classified under both the 1855 list and the 1959 Graves list — the only
estate in Bordeaux in two systems. It is stored once and appears in both, so the ten collections
list 375 entries between them but 374 distinct estates.

---

## What's in it

**Collections tab** — pick a hierarchy. Each card gives the region, the year, the tiers and what
the classification actually is.

**Producers & map** — two drawn maps. The **overview** shows the ocean, the Gironde, the two
rivers and the outline of all twelve appellations, with the type placed so nothing overlaps and
no estate dots at all — it is for finding your region. Click any outline and you get **that
appellation's own map**: its châteaux coloured by rank and sized by vineyard area, its villages
named, its neighbours ghosted for context, and the producer list beside it filtered to match.
← All regions goes back. Estates are listed estates listed tier by tier, highest first. Filters in one row: search, appellation,
a single vintage, a minimum score, and per-tier toggles.

**Estate drawer** (click any estate or marker)
- Classification, appellation, hectares, proprietor, second wine, house style.
- Typical blend as a labelled stacked bar.
- **Score by vintage** — a 43-column chart; hover or tab for a tooltip, click to jump.
- **All 43 vintages**, each expanding to a tasting note, that season's blend, the score, the
  season rating **for that appellation**, a drinking window, the weather and character of the
  year, and **four price links for that exact vintage**.
- A **Table view** button swaps every chart for the underlying numbers.

**Vintage reports** — all 43 seasons with weather, character, and separate ratings for the Médoc,
Pessac-Léognan, Saint-Émilion & Pomerol, and Sauternes.

**Price links** — per wine, per vintage. The primary link is Wine-Searcher's listing for that
château and year, ordered cheapest-first; then Google Shopping, Vivino and a general web search.

---

## Reading the data: what is sourced and what is not

### ✓ verified — from the record

- **Every château name, rank, classification and appellation.** The Saint-Émilion 2022 list, the
  Cru Bourgeois 2025 list of 170 and the Cru Artisan roster were taken from the published
  classifications, not from memory.
- Blends, hectares, proprietors, second wines and house styles **for the estates that have
  them here** (the 1855 lists, the Graves 16, the Saint-Émilion top 14, the Pomerol top 17).
- The weather and character of all 43 vintages, and the season ratings — including a separate
  Right Bank table, because 1998 is a great Pomerol year and a mediocre Médoc one, and 1986 is
  the reverse.
- Years in which an estate declared no vintage.
- **Those critic scores and tasting notes that entered the public record.** Each carries its
  attribution. See `data/overrides.js`.

### ≈ modelled — derived, not sourced

- **Score** = the estate's rank baseline moved by how good that season was *in that specific
  appellation*. Montrose 2003 therefore scores well above Palmer 2003, and Pétrus 1998 well
  above any Pauillac of that year.
- **Tasting note** = assembled from the documented character of the season, the estate's
  dominant grape and its appellation's aromatic signature. Not a record of anyone tasting it.
- **Vintage blend** = the typical blend shifted by the varietal character of the season. Applied
  to Left Bank reds only; Right Bank and white blends are shown as typical. Shown only for the
  134 estates whose own encépagement is recorded — never derived from an appellation average.

### Gaps shown as gaps

The 170 Crus Bourgeois and the 34 Crus Artisans carry a **verified name, rank and appellation
and nothing else**. Per-property blends, hectarage, proprietors and house styles for those 204
estates are not in this dataset, and inventing them would have been worse than leaving them
out. Of the other 170 estates, every one has its hectarage and 139 carry a typical blend.
For the 204:

- **no blend is shown at all.** An appellation average is not this château's blend, so the
  dashboard shows the gap instead of a guess — and the tasting notes for those estates say
  nothing about grape character either;
- the map position is **scattered within the appellation**, so several hundred markers stay
  legible. Faded markers mean "this is the appellation, not the property". Do not navigate by them;
- the drawer says all of this before you read anything else.

Everything else — the 43 vintages, the scores, the notes, the drinking windows and all four
price links — works identically for them.

### Two caveats worth knowing

- **Pomerol has no classification and never has.** The three tiers here are this dashboard's
  editorial reading of critical and market standing. They carry no official weight, and the app
  says so on the card, in the list and in every estate drawer.
- **The Cru Artisan roster is historic.** It is the 2006 homologation plus the 2012 additions.
  The source listing showed 43 of the 44 original properties, hence 49 rather than 50. The list
  is revised every five years and later revisions have trimmed it to around 36, so treat this as
  the full historic roster rather than today's live membership.

---

## Files

```
index.html                 the page
manifest.webmanifest       installable app metadata
service-worker.js          offline app-shell cache
assets/icon.svg            app and browser icon
assets/styles.css          design tokens, light + dark
assets/app.js              derivation model, map, charts, price links
assets/icon-192.png        install icon for phones and tablets
assets/icon-512.png        install icon for high-resolution displays
assets/icon.svg            scalable browser icon
data/classifications.js    the ten collections, tiers, appellation geography and norms
data/geography.js          the drawn map: estuary, rivers, towns, region names
data/chateaux.js           61 classified reds (1855)
data/sauternes.js          27 classified Sauternes & Barsac (1855)
data/saintemilion.js       85 (14 full records + the 71 Grands Crus Classés)
data/pomerol.js            40 (17 full records + 23 further estates)
data/graves.js             16 Crus Classés de Graves
data/crubourgeois.js       170 Crus Bourgeois, name + tier + appellation
data/cruartisan.js         49 Crus Artisans
data/vintages.js           43 vintage reports with Médoc/Pessac/Sauternes ratings
data/rightbank.js          Saint-Émilion & Pomerol season ratings
data/overrides.js          verified critic scores, notes, and no-vintage years
```

## Extending it

- **Fill in a sparse estate**: move it out of the compact list into a full record with
  `blend`, `ha`, `owner`, `second`, `style` and real `lat`/`lng`, and drop `sparse`/`normBlend`.
  The flags disappear on their own.
- **Add real scores**: one key per wine in `data/overrides.js` —
  `'petrus|1998': {score: 100, src: 'Vinous', note: '…'}`. The ✓ flag follows automatically.
- **Add a collection**: append to `BDX_CLASSIFICATIONS` in `data/classifications.js`, add a data
  file in the same shape, and load it from `index.html`. Nothing in `app.js` needs to change.
- **Earlier vintages**: add entries to `data/vintages.js` and `data/rightbank.js`.

## Notes

- Colours: bordeaux for estate rank (a one-hue ordinal ramp, validated for monotone lightness
  and surface contrast in both modes), dark blue for water, gold for towns and rules. The
  grape-variety palette in the blend charts is the separate categorical set, validated for
  colour-vision deficiency and contrast in both modes. Blend segments carry visible labels and a table view because three light-mode slots
  sit below 3:1 on the surface.
- **The maps are drawn, not tiled.** Coastline, estuary, rivers, appellation outlines, towns and
  region names are an inline SVG projected from real coordinates in `data/geography.js` — no tile
  server, no API key, no usage policy, no network. The whole dashboard works offline.
  **The map is the page.** The title and the tabs stay where they were; beneath them the map
  fills everything else. That is the default, not a mode, because the map is height-constrained and never
  width-constrained: in a two-pane layout it used barely two thirds of its pane's width and all
  of its height, so the only way to make it bigger was to give it the whole window. Controls sit
  over the map: ← Collections, the appellation name, Filters, and a Châteaux button. Clicking an
  appellation frames it and slides its châteaux in from the right over the map; ✕ or Escape
  closes the panel, then steps back to all appellations.
  Zoom with the wheel or the +/− buttons; drag to pan once zoomed in (at full zoom-out the
  map is locked, since there is nowhere to pan to). Appellation names place themselves
  automatically. In the overview each starts where it is written, several out in open country
  on a leader line, which is what keeps twenty-two names legible in one frame, and searches
  outward if it collides. Zoomed in, those written positions would strand a name far from its
  appellation, so past the overview each name is placed on its own shape and may only shuffle
  a little to dodge a clash; appellations off the edge of the view are not named at all. The scale bar is
  recomputed on every zoom, and map type holds a constant size on screen while the geography scales.
- **Appellation outlines are drawn from the terrain, not from the cadastre.** The Médoc
  appellations are generated from a single shared riverbank polyline: every commune takes its
  river edge as a slice of that same list, and every dividing line is one pair of points used by
  both neighbours — so adjacent appellations cannot overlap by construction rather than by
  inspection. 271 vertices across 12 regions; the Médoc communes follow the actual line of the Gironde's west bank on their river
  edge, and Sauternes & Barsac is drawn as the two separate parts it really is — Barsac on its
  limestone north of the Ciron, the four Sauternes communes on gravel to the south. They are
  correct in position, proportion, shape and adjacency, but they are still not legal boundaries
  and should not be used as such.
- **An appellation is drawn only if four or more of its châteaux are documented here.** Seven
  were removed on that rule after research failed to lift them past three: Puisseguin- and
  Saint-Georges-Saint-Émilion, Cérons, Cadillac, Loupiac, Sainte-Croix-du-Mont and Francs. A
  region drawn around one estate is a region that misleads about what is known.
- **No outline crosses itself.** A ring listed in the wrong order ties a bow-tie: it overlaps
  no other region, so every overlap check passes while the border renders as nonsense. Graves
  and Cotes de Bourg each did this until it was caught; the geometry suite now tests every ring
  against itself as well as against its neighbours.
- **No two appellations overlap.** Neighbours share their dividing lines vertex for vertex, and
  the six communal appellations — Saint-Estèphe, Pauillac, Saint-Julien, Listrac, Moulis and
  Margaux — are cut out of the Haut-Médoc as true holes, because on the ground a parcel is one
  or the other and never both. The hole rings are the neighbours' own rings, so a cut-out cannot
  drift from the shape it is cut from. Sauternes & Barsac is two parts that share the line of the
  Ciron the same way. Checked by grid sampling at roughly 65 m, in two passes — region against
  region, and the separate parts of a single region against each other, since two overlapping
  parts of one shape would punch a hole through it under the even-odd fill. Both pass at zero.
  Estates without a surveyed position are placed by sampling a deterministic point inside
  their appellation's polygon, so such a dot never lands in the wrong region — but it shows
  the appellation, not the property. The 170 estates that do carry coordinates are checked
  against the official delimitation, and **125 of them fall inside it**. The rest are a known
  gap rather than a surprise: those coordinates are commune-level, roughly ±400 m, while the
  boundaries they are now drawn against are surveyed. Some of the misses are real — a
  château's buildings can stand outside the delimited vineyard, since the house is not
  planted — and Lafite is one of those.
- Dark mode follows your OS and can be overridden with the toggle; the choice persists.
