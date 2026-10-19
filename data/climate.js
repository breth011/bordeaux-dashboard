/* =========================================================================
   Bordeaux Dashboard — rainfall by vintage, yields by appellation
   -------------------------------------------------------------------------
   PROVENANCE: VERIFIED, APPELLATION-LEVEL. Not this estate — the
   appellation it sits in, and in the case of rain the whole region.

   Read by OCR from the tables Gavin Quinney publishes with his annual
   Bordeaux weather and crop report (gavinquinney.com), whose own figures
   come from Customs and the CIVB for the crop and from six weather
   stations for the rain.

   OCR on a dense numeric table is not trustworthy on its own, so every
   year of rainfall was checked against the Mar–Sep total the table
   states for itself and dropped where the arithmetic disagreed. 2016 and
   2023 failed that test and are absent: in 2016 May’s 106 mm was read as
   6. The temperature table could not be made to validate at all and is
   not here.

     rain  mm per month, March to September, then the stated total
     yld   hl/ha by appellation and vintage, with the appellation’s
           planted area in hectares as of 2023
   ========================================================================= */

window.BDX_RAIN = {
2009:{mm:[36,109,80,55,55,37,48],marSep:420},
2010:{mm:[62,24,45,76,20,17,34],marSep:278},
2011:{mm:[33,10,17,38,60,76,36],marSep:269},
2012:{mm:[22,179,44,86,32,14,63],marSep:440},
2013:{mm:[63,55,110,133,51,44,70],marSep:526},
2014:{mm:[76,67,70,83,83,62,32],marSep:473},
2015:{mm:[38,51,38,52,22,103,49],marSep:353},
2017:{mm:[80,21,82,136,28,30,93],marSep:470},
2018:{mm:[126,87,71,77,35,23,24],marSep:443},
2019:{mm:[43,104,45,83,44,29,51],marSep:399},
2020:{mm:[99,111,126,87,5,59,72],marSep:560},
2021:{mm:[17,21,111,184,53,24,60],marSep:469},
2022:{mm:[34,58,21,94,3,27,39],marSep:278},
};

window.BDX_YIELDS = {
'Margaux':{ha:1519,y:{2009:42.9,2010:42.4,2011:37,2012:42.1,2013:31.9,2014:43.2,2015:47.1,2016:49.4,2017:32.3,2018:37.4,2019:49.2,2020:36.3,2021:38.6,2022:31.3,2023:37.7}},
'Saint-Julien':{ha:896,y:{2009:45.8,2010:43.5,2011:38.9,2012:39,2013:32.1,2014:38.5,2015:47.9,2016:46,2017:44.3,2018:42.6,2019:45.5,2020:34.3,2021:35.2,2022:34.3,2023:50.3}},
'Pauillac':{ha:1223,y:{2009:46.6,2010:44.6,2011:43.6,2012:38.3,2013:29.8,2014:38.2,2015:44.5,2016:44.9,2017:46.2,2018:38.5,2019:46.7,2020:37.4,2021:35.1,2022:34.8,2023:47.1}},
'Saint-Estèphe':{ha:1166,y:{2009:49.3,2010:43.9,2011:46.3,2012:43,2013:32.9,2014:42.9,2015:49.4,2016:50.5,2017:49.7,2018:44.6,2019:49.7,2020:41.2,2021:40.7,2022:31.5,2023:51.6}},
'Pessac-Léognan':{ha:1599,y:{2009:43.2,2010:41.9,2011:39.4,2012:41.7,2013:32.4,2014:46.8,2015:42.6,2016:45.4,2017:30.6,2018:36.9,2019:47.2,2020:34.6,2021:33.2,2022:35.7,2023:38.1}},
'Saint-Émilion':{ha:4164,as:'Saint-Émilion Grand Cru',y:{2009:37.4,2010:40.5,2011:43.5,2012:41,2013:29.9,2014:41.4,2015:44.2,2016:46.2,2017:21.7,2018:39.7,2019:43,2020:36.7,2021:27.5,2022:41.2,2023:40.5}},
'Pomerol':{ha:780,y:{2009:41.1,2010:37.5,2011:43.1,2012:36.4,2013:28,2014:41.6,2015:42.6,2016:44.4,2017:23.9,2018:36.2,2019:43,2020:39.8,2021:28.9,2022:32.3,2023:45.2}},
'Sauternes':{ha:1751,as:'Sauternes & Barsac together',y:{2009:22.4,2010:23.4,2011:17.4,2012:17,2013:16.4,2014:13.6,2015:18.3,2016:21.8,2017:12,2018:15.7,2019:13.6,2020:12.3,2021:3.5,2022:14.5,2023:12.3}},
'Barsac':{ha:1751,as:'Sauternes & Barsac together',y:{2009:22.4,2010:23.4,2011:17.4,2012:17,2013:16.4,2014:13.6,2015:18.3,2016:21.8,2017:12,2018:15.7,2019:13.6,2020:12.3,2021:3.5,2022:14.5,2023:12.3}},
};
