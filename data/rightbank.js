/* ===========================================================================
   Bordeaux Dashboard — Right Bank vintage ratings, 1982–2024
   ---------------------------------------------------------------------------
   Saint-Émilion and Pomerol are Merlot country on clay and limestone, and
   their vintages diverge sharply from the Médoc's. 1998 is a great Pomerol
   year and a mediocre Médoc one; 1986 is the reverse. Without this table the
   dashboard would score Pétrus 1998 as if it were a Pauillac, which is wrong
   by about ten points.

   `app` holds appellation adjustments for years that split the two communes —
   above all 2017, when the April frost cut deep into Saint-Émilion while much
   of the Pomerol plateau escaped.

   PROVENANCE: a 100-point summary of settled critical consensus on each
   season, in the same spirit as the Médoc ratings in vintages.js.
   =========================================================================== */

window.BDX_RIGHTBANK = {
1982: { r: 96 },
1983: { r: 86 },
1984: { r: 62 },   /* the Merlot flowering failure — catastrophic here */
1985: { r: 92 },
1986: { r: 85 },   /* a Cabernet year; the Médoc's triumph, not Pomerol's */
1987: { r: 74 },
1988: { r: 90 },
1989: { r: 95 },
1990: { r: 97 },
1991: { r: 60 },   /* April frost, worse on the Right Bank than the Médoc */
1992: { r: 70 },
1993: { r: 76 },
1994: { r: 82 },
1995: { r: 92 },
1996: { r: 86 },   /* cool September suited Cabernet, not Merlot */
1997: { r: 80 },
1998: { r: 97 },   /* the great Right Bank vintage — Pétrus, Cheval Blanc */
1999: { r: 85 },
2000: { r: 96 },
2001: { r: 92 },   /* better here than on the Left Bank */
2002: { r: 82 },   /* a late-Cabernet year; Merlot was picked before the sun */
2003: { r: 86, app: { 'Pomerol': 2 } },
2004: { r: 85 },
2005: { r: 98 },
2006: { r: 88 },
2007: { r: 82 },
2008: { r: 90 },
2009: { r: 98 },
2010: { r: 97 },
2011: { r: 86 },
2012: { r: 89 },   /* Merlot ripened well — a Right Bank year */
2013: { r: 70 },
2014: { r: 88 },
2015: { r: 96 },
2016: { r: 95 },
2017: { r: 84, app: { 'Saint-Émilion': -5, 'Pomerol': 2 } },
2018: { r: 96 },
2019: { r: 95 },
2020: { r: 96 },   /* outstanding Merlot */
2021: { r: 84 },
2022: { r: 96 },
2023: { r: 92 },
2024: { r: 80 }
};
