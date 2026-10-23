/* =========================================================================
   Bordeaux Dashboard — the ground each estate sits on
   -------------------------------------------------------------------------
   Built by tools/read-terroir.py. Do not edit by hand.

   A soil does not belong to a vintage. Lafite prints one soil
   sentence on 48 of its 53 sheets, word for word from 1968 to
   1979; Gruaud-Larose one from 1988 to 2024. Where a soil looks
   as though it moved it is two languages, not two soils.

   What the estate did in its cellar is NOT here, because that
   does move — Franc-Mayne replaced concrete vats with
   gravity-fed stainless. It is in data/cellar.js, per vintage.

     v          the passage, as the estate printed it
     seen / of  sheets agreeing on it / sheets stating any
     from, to   the years of the sheets that agree
     src        one sheet that gave it
     label      the words the sheet filed it under
     lang       en or fr, by the passage and not the filename

   Nothing is written that fewer than two sheets agree on, and
   among those that clear it the most recent wins: an estate
   that rewrites its own description is correcting it.
   ========================================================================== */
var BDX_TERROIR = {
'artisan-chateau-de-lauga':{v:'AND SUBSOIL Gravel over a clay limestone sub-soil',seen:2,of:4,src:'Fiche-technique-LAUGA-ENG.pdf',label:'SOIL ',lang:'en',from:2019,to:2019},
'bourgeois-chateau-d-argan':{v:'Clay-limestone.',seen:2,of:2,src:'FT-Argan-2018-EN-FR.pdf',label:'Soils: ',lang:'en',from:2018,to:2019},
'bourgeois-chateau-magnol':{v:'Sand and gravel.',seen:2,of:12,src:'205_2001.pdf',label:'Soil: ',lang:'en',from:2001,to:2020},
'bourgeois-chateau-moulin-de-canhaut':{v:'ARGILEUX',seen:2,of:4,src:'MOULIN-DE-CANHAUT-2021.pdf',label:'SOLS ',lang:'fr',from:2021,to:2022},
'bourgeois-chateau-paveil-de-luze':{v:'Graves profondes',seen:7,of:7,src:'1998__produit-paveil-de-luze-1998.txt',label:'Terroir : ',lang:'fr',from:1998,to:2018},
'calon-segur':{v:'Vineyard area Area in production',seen:2,of:2,src:'Calon-Segur-2015-FT-GB-33.pdf',label:'Soil ',lang:'en',from:2015,to:2016},
'clos-floridene':{v:'From a geological standpoint, the soil of Pujols sur Ciron where most of the vineyard is situated is much like the one of Barsac. A thin layer of red clayey sands, rich in iron oxide, and known as "Barsac red sands", tops the limestone bed rock. This limits the roots depth of the vine to about 50cm.',seen:3,of:13,src:'Clos-Floridene-2010-FT-GB-599.pdf',label:'Soils ',lang:'en',from:2010,to:2013},
'clos-fourtet':{v:'Argilo-calcaires',seen:8,of:8,src:'Fiche_Technique_CLOS_FOURTET_EMI_RO_2019_Francais.pdf',label:'SOLS ',lang:'fr',from:2018,to:2025},
'dauzac':{v:'Peyrosol complexe graveleux',seen:3,of:4,src:'FT_CHATEAU-DAUZAC-2022_NOTES_FR.pdf',label:'SOL ',lang:'fr',from:2022,to:2024},
'du-tertre':{v:'AREA UNDER VINE AREA IN PRODUCTION PLANTINGS',seen:2,of:4,src:'FT-CHATEAU-DU-TERTRE-2023-ANG.pdf',label:'SOIL ',lang:'fr',from:2023,to:2024},
'duhart-milon':{v:'Château Duhart-Milon’s vineyard consists of a single block of vines adjacent to Château Lafite Rothschild, on the hillside to the west of the Carruades plateau. The property has 76 hectares of vines. The soil consists of fine gravel mixed with aeolian sand on a tertiary limestone.',seen:20,of:32,src:'Chateau-Duhart-Milon-1988.pdf',label:'Terroir : ',lang:'en',from:1988,to:2024},
'giscours':{v:'Graves d’origine garonnaise profondes',seen:4,of:8,src:'CH.-GISCOURS-2024-FR-1.pdf',label:'SOL ',lang:'fr',from:2023,to:2025},
'gruaud-larose':{v:'Garonne gravel from the first quaternary, settled more than 600 000 years ago',seen:37,of:43,src:'1988__en-wines-gruaud-larose-1988.txt',label:'SOIL : ',lang:'en',from:1988,to:2024},
'guiraud':{v:'Sols : 80% graves sableuses 20% graves argileuses Sous-sols : sables translucides profonds et graves pures traversées par des veines d’argiles rouges et blanches, des marnes calcaires et des bandes de calcaire à huîtres.',seen:3,of:8,src:'cha-teau-guiraud-1er-grand-cru-classe-en-1855-2022.pdf',label:'SOLS ',lang:'fr',from:2022,to:2025},
'la-fleur-de-bouard':{v:'16 ha avec des sols argilo-sableux en surface et de graves en sous-sol sur le plateau de Néac, 8 ha d’un seul tenant sur une étonnante croupe graveleuse comportant 15% à 20% d’argiles sur le plateau de Lalande Pomerol, et 9 ha sur des croupes d’argiles graveleuses.',seen:2,of:3,src:'FT-La-Fleur-MILL-2019-FR.pdf',label:'SOL ',lang:'fr',from:2018,to:2019},
'la-lagune':{v:'THE FINESSE OF THE GRAVES AND THE STRENGTH OF THE MÉDOC. The terroir of La Lagune is considered by the famous geologist René Pijassou as «the Medoc island model».',seen:9,of:10,src:'LL_fiche-technique_2012.pdf',label:'SOIL ',lang:'en',from:2012,to:2022},
'la-tour-blanche':{v:'Graves sur sous-sol argilo-calcaire',seen:4,of:4,src:'Fiche_Brumes.pdf',label:'TERROIR : ',lang:'fr'},
'lafite':{v:'Chateau Lafite Rothschild is located to the north of the appellation, bordering Saint Estèphe. Lafite\'s best terroirs stretch on the 50ha Plateau des Carruades to the west of the Château. This plateau, which is the highest point of the Pauillac appellation, is well-drained and enjoys optimal sun exposure.',seen:41,of:48,src:'Chateau-Lafite-Rothschild-1968.pdf',label:'Terroir : ',lang:'en',from:1968,to:2024},
'lafon-rochet':{v:'DEEP GRAVELS + GRAVELS ON CLAY',seen:7,of:7,src:'FT_LafonRochet2009_EN.pdf',label:'SOIL ',lang:'en',from:2009,to:2022},
'lagrange':{v:'Totalement situé sur la commune de Saint­Julien',seen:6,of:6,src:'Chateau-Lagrange-2020-FR.pdf',label:'TERROIR ',lang:'fr',from:2019,to:2025},
'leoville-poyferre':{v:'! Château Léoville Poyferré propose toute l’année des visites',seen:2,of:2,src:'Ch-Leoville-Poyferre-Millesime-2017.pdf',label:'TERROIR ',lang:'fr',from:2017,to:2019},
'levangile':{v:'L’Evangile’s vineyard covers 22 hectares at the heart of the Pomerol plateau, sharing the appellation’s best terroirs with two other prestigious properties. Here, through a mystery of geology, the heavy green clay soils are covered by a bed of gravel.',seen:32,of:32,src:'Chateau-LEvangile-1981.pdf',label:'Terroir : ',lang:'en',from:1981,to:2024},
'marquis-de-terme':{v:'Deep gravel, locally more clayey, settled on 2 major fmilies of soils that give our wines their identity.',seen:9,of:18,src:'MdT-2015-Fiche-technique-Revue-de-Presse-Marquis-de-Terme-EN_compressed.pdf',label:'SOILS ',lang:'en',from:2015,to:2023},
'pedesclaux':{v:'Graves garonnaises sur socle calcaire',seen:5,of:5,src:'Chateau_Pedesclaux_2018-FT-FR.pdf',label:'TERROIR ',lang:'fr',from:2016,to:2020},
'pichon-comtesse':{v:'ARGILO-SABLEUX',seen:4,of:4,src:'Pichon-Comtesse-Lalande-2018-FT-FR.pdf',label:'SOUS-SOLS ',lang:'fr',from:2018,to:2021},
'pomerol-chateau-beauregard':{v:'Graves argileuses en bordure sud-est du célèbre plateau de Pomerol.',seen:3,of:6,src:'Beauregard-2016-FT-FR-17.pdf',label:'TERROIR : ',lang:'fr',from:2013,to:2021},
'prieure-lichine':{v:'Graves garonnaises du Günz •',seen:10,of:12,src:'Fiche-technique-CPL-2010-FR.pdf',label:'SOL : ',lang:'fr',from:2010,to:2023},
'rauzan-segla':{v:'Graves argileuses de la terrasse 4 Mosaïque de graves fines et profondes',seen:4,of:6,src:'FT_RAUZAN_SEGLA_FR_2020.pdf',label:'SOLS ',lang:'fr',from:2016,to:2020},
'rieussec':{v:'Château Rieussec sits on the border of Fargues and Sauternes, bordered by Château d\'Yquem to the West. Rieussec is one of the largest properties in Sauternes and Barsac, covering 93 hectares of gravel sitting on sandy-clay soils.',seen:17,of:29,src:'Chateau-Rieussec-1975.pdf',label:'Terroir : ',lang:'en',from:1975,to:2020},
'siaurac':{v:'Gravel, deep clays and sandy clays',seen:10,of:36,src:'Technical-Sheet-Chateau-Siaurac-2016-Lalande-de-Pomerol.pdf',label:'TERROIR : ',lang:'en',from:2016,to:2024},
'stem-chateau-bellefont-belcier':{v:'SOILS PRATIQUE CULTURALE PRATIQUE CULTURALE VINEYARD MAINTENANCE VINEYARD MAINTENANCE',seen:2,of:7,src:'Bellefont-Belcier-2022-FT-FR-GB-Primeurs.pdf',label:'SOILS ',lang:'en',from:2022,to:2023},
'stem-chateau-cote-de-baleau':{v:'Argilo-calcaires et argilo-sableux',seen:2,of:2,src:'Chateau-Cote-de-Baleau_millesime-2024.pdf',label:'SOL ',lang:'fr',from:2023,to:2024},
'stem-chateau-grand-mayne':{v:'Côteau argilo-calcaire et pied de côteau d’argile Slope clay and limestone and foot of the slope clay',seen:7,of:15,src:'Chateau-Grand-Mayne-2019.pdf',label:'TERROIR ',lang:'en',from:2015,to:2022},
'stem-chateau-la-dominique':{v:'Argilo-graveleux, argilo-calcaire et sables sur argile ÂGE MOYEN DE LA VIGNE 27 ans',seen:3,of:3,src:'ld-2005-sans.notes-fr.pdf',label:'SOL ',lang:'fr',from:2005,to:2021},
'stem-chateau-moulin-du-cadet':{v:'Clay- limestone on a north exposure face of the Cadet hill.',seen:2,of:4,src:'FT-Ch.-Moulin-du-Cadet-2020-ang.pdf',label:'Soils: ',lang:'en',from:2020,to:2020},
'stem-chateau-sansonnet':{v:'Clay- limestone over asteria limestone.',seen:2,of:4,src:'FT-Ch.-Sansonnet-2020-ang.pdf',label:'Soils: ',lang:'en',from:2020,to:2020},
'stem-chateau-tour-saint-christophe':{v:'Clay Limestone',seen:16,of:32,src:'PRODUCT-SHEET-CHATEAU-TOUR-SAINT-CHRISTOPHE-2014.pdf',label:'SOILS ',lang:'en',from:2014,to:2021},
'stem-chateau-yon-figeac':{v:'Argilo-sableux sur crasses de fer.',seen:2,of:3,src:'RY-fr_compressed_merged.pdf',label:'Sols : ',lang:'fr',from:2013,to:2015},
};
if (typeof window !== 'undefined') window.BDX_TERROIR = BDX_TERROIR;
