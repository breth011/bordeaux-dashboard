/* =========================================================================
   Bordeaux Dashboard — growing-season dates, 1982–2024
   -------------------------------------------------------------------------
   PROVENANCE: VERIFIED. Every date here is read from the Institut des
   Sciences de la Vigne et du Vin's own vintage reports ("Le millésime
   ... à Bordeaux"), which publish the mid-flowering and mid-véraison
   dates observed on their reference plots. Unlike the ratings in
   vintages.js these are measurements, not a reading of consensus.

   Each report restates the dates of neighbouring years, so most values
   are read from several reports independently; `n` is how many agreed.
   Years where two reports disagreed are omitted rather than guessed.

     flowering  mi-floraison, the date half the flowers were open
     veraison   mi-véraison, the date half the berries had turned
     n          number of ISVV reports agreeing on that date

   Dates are MM-DD. Source PDFs are not redistributed with this repo;
   they are published at bordeauxraisins.fr/les-millesimes.html
   ========================================================================= */

window.BDX_PHENOLOGY = {
1982:{flowering:'06-05',veraison:'08-09',n:3},
1985:{veraison:'08-16',n:1},
1989:{flowering:'05-29',veraison:'08-04',n:3},
1990:{flowering:'05-27',veraison:'08-06',n:5},
1992:{veraison:'09-14',n:1},
1993:{flowering:'06-06',n:2},
1994:{flowering:'06-04',veraison:'08-06',n:3},
1995:{flowering:'06-04',veraison:'08-10',n:2},
1996:{flowering:'06-04',veraison:'08-10',n:1},
1997:{flowering:'05-23',veraison:'07-31',n:4},
1998:{flowering:'06-04',veraison:'08-07',n:1},
2000:{flowering:'06-03',veraison:'08-06',n:1},
2001:{veraison:'07-26',n:1},
2003:{flowering:'05-27',veraison:'07-29',n:2},
2004:{flowering:'06-02',veraison:'08-12',n:5},
2005:{flowering:'05-30',veraison:'08-03',n:8},
2006:{flowering:'06-04',veraison:'08-06',n:9},
2007:{flowering:'05-26',veraison:'08-03',n:9},
2008:{flowering:'06-11',veraison:'08-15',n:8},
2009:{flowering:'06-05',veraison:'08-03',n:8},
2010:{flowering:'06-09',veraison:'08-09',n:11},
2011:{flowering:'05-17',veraison:'07-21',n:12},
2012:{flowering:'06-11',veraison:'08-12',n:11},
2013:{flowering:'06-18',veraison:'08-22',n:10},
2014:{flowering:'06-07',veraison:'08-13',n:10},
2015:{flowering:'06-05',veraison:'08-06',n:9},
2016:{flowering:'06-11',veraison:'08-07',n:8},
2017:{flowering:'05-30',veraison:'07-30',n:7},
2018:{flowering:'06-03',veraison:'08-04',n:6},
2019:{flowering:'06-04',veraison:'08-09',n:5},
2020:{flowering:'05-26',veraison:'08-01',n:4},
2021:{flowering:'06-10',veraison:'08-11',n:3},
2022:{flowering:'05-23',veraison:'07-28',n:2},
2023:{flowering:'06-03',veraison:'07-23',n:1},
2024:{flowering:'06-10',veraison:'08-16',n:1},
};
