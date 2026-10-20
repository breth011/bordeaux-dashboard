/* =========================================================================
   Bordeaux Dashboard — the other wines of each estate
   -------------------------------------------------------------------------
   fiches.js holds the grand vin, the wine an estate is judged on. This
   holds everything else it makes: the second wine, the dry white, the odd
   cuvee. Same fields, read off the same technical sheets.

   BDX_CUVEE_WINES lists an estate's other wines in the order they should
   be offered; BDX_CUVEES carries one record per wine and vintage, keyed
   estate|slug|year.
   ========================================================================= */

window.BDX_CUVEE_WINES = {
'gruaud-larose':[{slug:'sarget-de-gruaud-larose',name:'Sarget de Gruaud-Larose',role:'second',colour:'red'}],
};

window.BDX_CUVEES = {
'gruaud-larose|sarget-de-gruaud-larose|1994':{blend:{CS:64,ME:28,CF:6,PV:2},alc:12.8,oak:'14 months, 10% new oak',src:'sarget-de-gruaud-larose-1994-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|1995':{blend:{CS:66,ME:24,CF:6,PV:2,MA:2},oak:'14 months, 10% new oak',src:'sarget-de-gruaud-larose-1995-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|1996':{blend:{CS:54,ME:39,CF:4,PV:3},alc:12.65,oak:'14 months, 10% new oak',src:'sarget-de-gruaud-larose-1996-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|1997':{blend:{CS:57,ME:30,CF:7,PV:4,MA:2},oak:'14 months, 10% new oak',src:'sarget-de-gruaud-larose-1997-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|1998':{blend:{CS:66,ME:24,CF:6,PV:3,MA:1},alc:12.6,oak:'14 months, 10% new oak',src:'sarget-de-gruaud-larose-1998-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|1999':{blend:{CS:67,ME:25,CF:6,PV:2},alc:12.65,oak:'14 months, 10% new oak',src:'sarget-de-gruaud-larose-1999-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|2000':{blend:{CS:64,ME:31,CF:3,PV:2},alc:12.7,oak:'14 months, 10% new oak',src:'sarget-de-gruaud-larose-2000-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|2001':{blend:{CS:64,ME:29,CF:5,PV:2},alc:12.8,oak:'14 months, 10% new oak',src:'sarget-de-gruaud-larose-2001-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|2002':{blend:{CS:80,ME:11,CF:3,PV:6},alc:12.8,oak:'14 months, 10% new oak',src:'sarget-de-gruaud-larose-2002-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|2003':{blend:{CS:64,ME:28,CF:8},alc:12.9,oak:'14 months, 10% new oak',src:'sarget-de-gruaud-larose-2003-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|2004':{blend:{CS:56,ME:36,CF:4,PV:4},alc:12.9,oak:'14 months, 15% new oak',src:'sarget-de-gruaud-larose-2004-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|2005':{blend:{CS:64,ME:30,CF:4,PV:1,MA:1},alc:12.86,oak:'14 months, 15% new oak',src:'sarget-de-gruaud-larose-2005-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|2006':{blend:{CS:55,ME:35,CF:5,PV:5},alc:12.5,oak:'14 months, 15% new oak',src:'sarget-de-gruaud-larose-2006-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|2007':{blend:{CS:56,ME:32,CF:10,MA:2},alc:12.95,oak:'12 months, 10% new oak',src:'sarget-de-gruaud-larose-2007-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|2008':{blend:{CS:72,ME:21,CF:7},alc:13.15,oak:'14 months, 15% new oak',src:'sarget-de-gruaud-larose-2008-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|2009':{blend:{CS:54,ME:26,CF:13,PV:7},alc:13.66,oak:'14 months, 15% new oak',src:'sarget-de-gruaud-larose-2009-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|2010':{blend:{CS:70,ME:23,CF:3,PV:4},alc:13.5,oak:'14 months, 15% new oak',src:'sarget-de-gruaud-larose-2010-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|2011':{blend:{CS:61,ME:30,CF:4,PV:5},alc:13.01,oak:'14 months, 10% new oak',src:'sarget-de-gruaud-larose-2011-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|2012':{blend:{CS:65,ME:21,CF:13,PV:1},alc:13.09,oak:'14 months, 15% new oak',src:'sarget-de-gruaud-larose-2012-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|2013':{blend:{CS:73,ME:14,CF:6,PV:7},alc:12.8,oak:'14 months, 15% new oak',src:'sarget-de-gruaud-larose-2013-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|2014':{blend:{CS:70,ME:22,CF:4,PV:4},alc:12.92,oak:'14 months, 15% new oak',src:'sarget-de-gruaud-larose-2014-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|2015':{blend:{CS:72,ME:18,CF:2,PV:8},alc:12.78,oak:'14 months, 15% new oak',src:'sarget-de-gruaud-larose-2015-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|2016':{blend:{CS:59,ME:31,CF:6,PV:4},alc:12.66,oak:'14 months, 15% new oak',src:'Sarget-de-Gruaud-Larose-2016-ang-1.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|2017':{blend:{CS:61,ME:30,CF:6,PV:3},alc:12.73,oak:'14 months, 15% new oak',src:'sarget-de-gruaud-larose-2017-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|2018':{blend:{CS:39,ME:49,CF:1,PV:11},oak:'14 months, 15% new oak',src:'sarget-de-gruaud-larose-2018-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|2019':{blend:{CS:48,ME:37,CF:8,PV:7},alc:13.49,src:'sarget-de-gruaud-larose-2019-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|2020':{blend:{CS:45,ME:48,CF:3,PV:4},alc:13.44,oak:'14 months, 15% new oak',src:'Sarget-de-Gruaud-Larose-2020-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|2021':{blend:{CS:52,ME:40,CF:2,PV:6},alc:12.76,oak:'14 months, 15% new oak',src:'Sarget-de-Gruaud-Larose-2021-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|2022':{blend:{CS:49,ME:44,CF:3,PV:4},alc:13.53,oak:'12 months, 15% new oak',src:'Sarget-de-Gruaud-Larose-2022-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|2023':{blend:{CS:52,ME:40.5,CF:4,PV:3.5},alc:12.92,oak:'12 months, 15% new oak',src:'Sarget-de-Gruaud-Larose-2023-ang.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|2024':{blend:{CS:48,ME:46,CF:3,PV:3},alc:12.45,src:'Sarget-de-Gruaud-Larose-2024-FR.pdf'},
'gruaud-larose|sarget-de-gruaud-larose|2024':{blend:{CS:48,ME:46,CF:3,PV:3},alc:12.45,oak:'12 months',src:'Sarget-de-Gruaud-Larose-2024-ang.pdf'},
};
