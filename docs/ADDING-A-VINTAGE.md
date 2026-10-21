# Adding a vintage

Once a year the estates publish their new sheets and this dashboard
needs to grow by one vintage. This is that job, start to finish. It is
five commands and one piece of reading.

```sh
python tools/harvest.py --year 2026        # find and fetch the new sheets
python tools/read-sheets.py --year 2026    # read them; propose nothing yet
less reports/proposed.txt                  # READ THIS
python tools/read-sheets.py --year 2026 --apply
python tools/check-data.py                 # every gate, over everything
python tools/audit-sources.py              # every record against its sheet
```

Then bump `CACHE_NAME` in `sw.js` — the service worker caches `data/`,
so without the bump nobody gets the new vintage — and commit.

## The one piece of reading

`reports/proposed.txt` opens with the readings that **contradict a
record already held**. That section is the whole point of the report.
A contradiction means one of the two figures was taken off the wrong
wine, and the only way to know which is to open the document.

It is how Branaire-Ducru 2019 was found holding `52.5/44/2.5/1`, which
is Duluc de Branaire-Ducru's blend; the grand vin's own sheet says
`56/35/4/5`. Nothing but reading the two sheets side by side would have
told you that, because both are plausible Saint-Julien blends and both
sum to 100.

Do not skip it, and do not let its being empty one year persuade you it
can be skipped the next.

## What each tool does, and what it refuses

**`tools/harvest.py`** finds what an estate publishes and fetches
anything not already held, by sha1, so it is safe to re-run. It tries
three methods per site, in order:

| method | why it is there |
| --- | --- |
| the media library | `/wp-json/wp/v2/media` lists every upload a WordPress site holds, including the files no page links to — which is most of the archive |
| the sitemap | not a fallback. bordeaux-tradition.com lists 83 files in its media library and 6,227 in `propriete-sitemap.xml` |
| links on the pages | for sites that are neither |

Two methods are **not** in it yet and have to be run by hand; see
*Still by hand* below.

**`tools/read-sheets.py`** reads each sheet and proposes a blend. Before
it takes any figure it refuses three kinds of document:

- **a press dossier** — one document per property rather than per
  vintage: history, plantings, standing practice, clippings. Clos
  Floridène's gave twenty vintages the same `months: 9`, which is its
  *whites'* ageing, and the red's standing assemblage for years in which
  the red did not exist.
- **a second wine** — either because the document says so about itself,
  or because it names the estate's second wine, which `data/chateaux.js`
  and its sister files already record for 136 estates. Duluc never says
  "second vin"; it just says Duluc.
- **another property** — a sheet naming an estate this dashboard does
  not hold goes nowhere. Château Cantegril, Haura and Reynon are
  Dubourdieu properties and none is here. Nor is Diamandes de Uco, the
  Bonnie family's estate in Mendoza, whose sheet gave
  Malartic-Lagravière 2020 an Argentine Cabernet's alcohol, oak and
  press scores.

`confirms_estate` answers this in three ways, not two, because "the
document does not name the estate" and "the document names another
estate" are different facts:

| answer | meaning | what happens |
| --- | --- | --- |
| `named` | the filename or the document names this estate | read it |
| `folder` | nothing in it names any estate | read it, and record `how` as *from the folder, which serves one estate* |
| `other` | it names a sibling property | read nothing from it |

`folder` is common and is not a complaint: Camensac's 2025 sheet,
Desmirail's 2016 and all of Canon-la-Gaffelière's print the château's
name in the logo at the top, which is an image, so no extraction will
ever find it. Those sheets are fine. What the manifest then says about
them is just weaker, and says so.

Then it takes the blend from the window the sheet **labels** as the
wine's — `ASSEMBLAGE`, `BLEND` — and never from the one labelled for
the vineyard. Malartic-Lagravière 2021 says `BLEND Cabernet-Sauvignon
67 %` at the top and `Grape varieties 56% Merlot` under the estate's
description, and a reader that takes the first figures it finds takes
the plantings. Batailley is the same trap in reverse: its sheet opens
with `ENCÉPAGEMENT : 70 % Cabernet Sauvignon 25 % Merlot…`, which is
identical under every year, and gives the vintage lower down as
`ASSEMBLAGE 2021 : 76 % Cabernet Sauvignon 20 % Merlot…`.

Where a sheet carries several labelled windows, which is common, they
are ranked:

1. a data block that names this wine
2. any data block
3. prose that names this wine
4. any prose

A data block is `Blend: 87% Merlot & 13% Cabernet Franc`; prose is
"blend **of** 80% Merlot and 20% Cabernet Franc" from the tasting note
two inches below it. La Conseillante's 2020 sheet has both and they
disagree; so do Dauzac's 2010 and d'Issan's 2009.

And if several data blocks disagree while **none** names a wine, it
returns nothing. Giscours' Carnet Primeurs 2025 prints `ASSEMBLAGE ·
BLEND 60 % Merlot…` and `ASSEMBLAGE · BLEND 86 % Cabernet Sauvignon…`
under identical headings — the second wine and the grand vin, in that
order. A coin toss recorded as a fact is worse than a gap.

Both readings of every page are tried — flat, and column by column —
and the one that resolves more of the windows it found wins. Each fails
differently: a flat extraction interleaves two columns into nonsense
(`Sauvignon terroirssont entreprisde Pauillac`, which is how
Grand-Puy-Ducasse's sixty-two vintages all came out wrong), while
reading column by column can attach one wine's figures to another's
label, which is how Haut-Bailly's 2022 sheet yielded Haut-Bailly II's
blend under Château Haut-Bailly's heading. The second is the more
dangerous, because it is a wrong answer that looks like a right one.

### Roles, once set, are not un-set

`read-sheets.py` writes a sheet's `role` into the manifest when it
decides the sheet is a dossier, a second wine or another property. It
never writes one back. So if a rule is wrong on Monday and fixed on
Tuesday, the roles it wrote on Monday are still wrong — which happened
here with Figeac's own 2021 datasheet, marked as a second wine's by a
name test that was matching `petit` from Petit-Figeac against "2% Petit
Verdot".

Rather than have the tool flip roles back and forth without saying so,
it re-reads every sheet already filed as another wine and lists the ones
it no longer agrees with, under *sheets filed as another wine but no
longer read as one*. Correct those in `data/sources.json`. The manifest
is the record; something that rewrites it silently in both directions
is not a record.

### When the estate's own sheet is wrong

`PINNED`, at the top of `read-sheets.py`. La Mission Haut-Brion's 2024
sheet reads `Blend Cabernet Franc: 51%; Merlot: 46.5% Cabernet
Sauvignon: 2.5%` — the two Cabernets swapped in the typesetting, since
La Mission is about half Cabernet Sauvignon with a few per cent Franc.
The record holds the corrected reading and the pin stops the reader
putting the sheet's version back. Each entry carries the sentence from
the sheet and why it cannot be right.

**`tools/check-data.py`** is every gate, over the whole dataset and not
the batch. Running it only over the batch is what let Château Margaux
sit at 87% *Merlot* for a month — Margaux is 87% Cabernet, and the
record held the estate's own figures with the varieties shuffled.

Its exceptions are listed in the file by name, each with the sentence
from the estate's own sheet that justifies it. Add to that list rather
than loosening a gate, so the check stays loud.

**`tools/audit-sources.py`** asks `data/sources.json`, for every record,
what wine the sheet in `src` is actually for, and complains when the
answer is not this estate's grand vin.

## Still by hand

Two discovery methods are not in `harvest.py`, because both need a
browser rather than an HTTP request:

- **the estate's own technical-sheets page**, where the list of sheets
  is built in JavaScript and the HTML arrives empty. Fetch it with
  `chrome --headless=new --virtual-time-budget=8000 --dump-dom <url>`
  and take the `.pdf` hrefs out of the result.
- **vin.co vintage pages** (`/vin/{n}/{slug}/{year}`), where each
  vintage's sheet sits behind an opaque per-vintage code. Two traps: a
  `/wp-json` 404 means "not WordPress", not "no API"; and the year in
  the URL lies — asking for 1995 returns 2023's code — so the vintage
  has to come from the `Content-Disposition` filename.

And one source that is neither, and matters more than either:

- **the négociants.** A merchant house holds the sheets its châteaux
  never publish; one house filled twenty classified estates that had
  nothing of their own. Their sitemaps are the way in
  (`propriete-sitemap.xml`, `grands-crus-sitemap.xml`). Matching a
  filename to an estate is the hard part, and the rules that work are
  in *Matching a name* below.

## Matching a name

Every one of these cost a wrong blend before it was a rule.

- **Strip the house word *and* the article.** `Château d'Yquem`
  reduces to `dyquem`, which does not match a file called
  `Yquem-2015-FT-FR`. Missing this discarded 29 Domaine de Chevalier
  sheets, 28 Camensac and 8 Ferrand in one direction and failed to
  match 126 files in the other. Allow the plural too —
  `Marquis-dAlesmes`.
- **Test the boundary.** Estate names contain each other. Maucaillou
  contains Caillou; Les Carmes Haut-Brion contains Haut-Brion; Madame
  de Beaucaillou contains Caillou; `LA_TOUR_DE_MONS` contains Latour,
  and filed 57% Merlot at a 90%-Cabernet estate.
- **Underscores are word characters.** `\bbrio\b` never matches
  `BriO_de_Cantenac_Brown`. Use `(^|[-_])brio([-_]|$)`.
- **Order the rules so the broad catch-all runs last.** Otherwise it
  swallows the cases the specific rules exist for.
- **Never read an estate's name out of the letterhead.** Every sheet in
  the Dubourdieu library carries `doisy-daene@wanadoo.fr` in its
  header, so a reader looking for a name anywhere in the document found
  the email address and filed 454 sheets of Cantegril, Haura and Reynon
  as Doisy-Daëne. `sheetreader.body_without_letterhead` takes the
  contact block off first.
- **Match names as words, never as substrings.** This is
  `sheetreader.says`, and it exists because matching on text with the
  punctuation stripped out put `parde` inside "mar**qué par des**
  conditions" and filed a Haut-Bailly sheet as La Parde's, and put
  `petit` from Petit-Figeac inside "2% **Petit** Verdot". Letters bound
  a name; digits do not, because `batailley2000-web_fr.pdf` is the name
  with the year run onto it.
- **A parenthetical is a note, not a name.** `Haut-Carles (prestige
  cuvée)` is called Haut-Carles on its own sheet.
- **Resist the tempting general rule.** I tried "reject a filename
  carrying any long word that belongs to no wine of this estate", which
  sounds right and rejected 59 correctly-filed sheets: filenames are
  full of appellations (`Chateau_Suduiraut_..._Sauternes_2001`), of
  words like `compressed`, and of hex that reads as letters
  (`66deb5cbdbede8689cb3c02d`). Every exception wanted another word in a
  list. Needing a list that keeps growing is the sign of a rule shaped
  wrong — replace it with the two or three narrow tests it was standing
  in for.
- **A truncated filename is not an unreadable sheet.** Dourthe writes
  `fichetechnique-2023-fiche-prod---ahoul-2023-en`, and the document
  inside names the château on its first line. If the source is
  recorded, open the file.

## Provenance, and what it cannot yet do

`data/sources.json` is the committed record: one entry per sheet, with
`file`, `sha1`, `estate`, `wine`, `role`, `year`, `url` and `how` — how
it was found. `sources/` itself is **not** committed, because GitHub
Pages serves this repo and none of that material is ours to republish.

So the manifest is what makes the archive reproducible, and it has a
gap: **8,553 of 9,467 sheets have no `url`.** Their addresses were known
when they were fetched and thrown away. `sha1` can prove a file is the
one that was read; nothing can fetch it again.

`tools/promote-urls.py` recovered the 914 that were recoverable — 713
written into a note as prose, 201 from the record that cites them. The
rest need their estate re-harvested, which is what `harvest.py` is for,
and the ones behind a browser or a négociant are the reason the two
methods above still matter.

**Every sheet added from now on carries its `url`.** `harvest.py` writes
it and `promote-urls.py` reports anything that does not, so the gap
closes rather than grows. That report is worth a glance each year:

```sh
python tools/promote-urls.py        # safe to re-run; it only fills blanks
```

## The rule under all of it

Read the document. Never count them.

A filename, a folder, a URL and a file count have each been wrong here
in a way that looked exactly like success: 454 sheets for an estate that
published none, 6,227 PDFs where a media library admitted 83, 641 files
that yielded 27 records of which every single one was wrong. The number
is never the evidence.
