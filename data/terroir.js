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
'bourgeois-chateau-beauvillage':{v:'sol argilo-calcaire et sables graveleux',seen:6,of:6,src:'Fiche-technique-Chateau-Beauvillage-millesime-2017.pdf',label:'Terroir : ',lang:'fr',from:2017,to:2022},
'bourgeois-chateau-bellegrave':{v:'Garonne gravel',seen:4,of:11,src:'Bellegrave-2014-FR-GB-C0866.pdf',label:'Soil : ',lang:'en',from:2014,to:2022},
'bourgeois-chateau-biston-brillette':{v:'graves et argilo calcaire',seen:8,of:8,src:'Fiche-Technique-BB-2019-1.pdf',label:'Terroir: ',lang:'fr',from:2019,to:2023},
'bourgeois-chateau-d-argan':{v:'Clay-limestone.',seen:2,of:4,src:'FT-Argan-2018-EN-FR.pdf',label:'Soils: ',lang:'en',from:2018,to:2019},
'bourgeois-chateau-de-braude':{v:'Gravely soil from the Garonne and partly from the Pyrennees.',seen:3,of:3,src:'FT-Ch-de-Braude-2013-GB.pdf',label:'Soil: ',lang:'en',from:2013,to:2015},
'bourgeois-chateau-du-moulin-rouge':{v:'gravelly hillocks.',seen:3,of:4,src:'technical-sheet-chateau-du-moulin-rouge-2014.pdf',label:'Soil ',lang:'fr',from:2014,to:2018},
'bourgeois-chateau-la-branne':{v:'sablo graveleux',seen:3,of:11,src:'2021__chateau-la-branne-2021.txt',label:'Terroir : ',lang:'fr',from:2021,to:2023},
'bourgeois-chateau-lalande':{v:'Sablo-graveleux',seen:7,of:8,src:'CHATEAU_LALANDE_2019_FT-FR.pdf',label:'Sol : ',lang:'fr',from:2015,to:2023},
'bourgeois-chateau-magnol':{v:'Sand and gravel.',seen:2,of:13,src:'205_2001.pdf',label:'Soil: ',lang:'en',from:2001,to:2020},
'bourgeois-chateau-mongravey':{v:'gravely soil from the garonne area dating from the quaternary period and composed of sand and pebbles Annual',seen:5,of:5,src:'FT-Ch-Mongravey-2009-GB.pdf',label:'Soil: ',lang:'en',from:2009,to:2014},
'bourgeois-chateau-moulin-de-canhaut':{v:'ARGILEUX',seen:2,of:4,src:'MOULIN-DE-CANHAUT-2021.pdf',label:'SOLS ',lang:'fr',from:2021,to:2022},
'bourgeois-chateau-paloumey':{v:'graves garonnaises quaternaires ',seen:3,of:3,src:'Fiche-Chateau-Paloumey-2016-FR.pdf',label:'Sol : ',lang:'fr',from:2016,to:2019},
'bourgeois-chateau-paveil-de-luze':{v:'Graves profondes',seen:22,of:23,src:'1998__produit-paveil-de-luze-1998.txt',label:'Terroir : ',lang:'fr',from:1998,to:2022},
'bourgeois-chateau-reverdi':{v:'Graves garonnaises Couleur: Rouge',seen:2,of:3,src:'Croix-Reverdi-2010-FT-FR-C0763.pdf',label:'Sols: ',lang:'fr',from:2010,to:2011},
'bourgeois-chateau-tour-des-termes':{v:'2/3 Graves, 1/3 Argilo calcaire',seen:2,of:2,src:'Tour-des-Termes-2018-FT-FR.pdf',label:'SOl : ',lang:'fr',from:2018,to:2020},
'bouscaut':{v:'argiles sur calcaire & graves',seen:2,of:2,src:'Bouscaut-Rouge-Blanc-2018-FT-GB.pdf',label:'Terroir : ',lang:'fr',from:2018,to:2019},
'boyd-cantenac':{v:'graves siliceuses maigres et drainantes du Quaternaire, qui donnent des sols chauds permettant un enracinement profond de la vigne.',seen:6,of:9,src:'FT-Ch.-Boyd-Cantenac-2018-FR.pdf',label:'Terroir : ',lang:'fr',from:2018,to:2025},
'calon-segur':{v:'Vineyard area Area in production',seen:2,of:2,src:'Calon-Segur-2015-FT-GB-33.pdf',label:'Soil ',lang:'en',from:2015,to:2016},
'clos-floridene':{v:'From a geological standpoint, the soil of Pujols sur Ciron where most of the vineyard is situated is much like the one of Barsac. A thin layer of red clayey sands, rich in iron oxide, and known as "Barsac red sands", tops the limestone bed rock. This limits the roots depth of the vine to about 50cm.',seen:3,of:14,src:'Clos-Floridene-2010-FT-GB-599.pdf',label:'Soils ',lang:'en',from:2010,to:2013},
'clos-fourtet':{v:'Argilo-calcaires',seen:8,of:11,src:'Fiche_Technique_CLOS_FOURTET_EMI_RO_2019_Francais.pdf',label:'SOLS ',lang:'fr',from:2018,to:2025},
'clos-haut-peyraguey':{v:'Sol gravelo-sableux sur sous-sol argileux.',seen:19,of:26,src:'Clos-Haut-Peyraguey-2020-FT-FR.pdf',label:'Nature du sol : ',lang:'fr',from:2011,to:2023},
'dalem':{v:'Plateaux et coteaux argilo-calcaire, diversité de terroirs - 15 parcelles / Limestone-clay plateaux and slopes, variety of terroirs - 15 plots Pratiques culturales / Vineyard management : Conduite raisonnée, orientation bio /biocontrôle / Sustainable vineyard management, organic or biocontrol phytosanitary treatments',seen:3,of:3,src:'FT-Primeur_DALEM_2022_FR.pdf',label:'Terroir : ',lang:'en',from:2022,to:2024},
'dauzac':{v:'Peyrosol complexe graveleux',seen:3,of:25,src:'FT_CHATEAU-DAUZAC-2022_NOTES_FR.pdf',label:'SOL ',lang:'fr',from:2022,to:2024},
'de-carles':{v:'Argile et argilo-calcaire sur molasse du Fronsadais',seen:3,of:4,src:'Fiche-technique-CDC-2017.pdf',label:'Terroir : ',lang:'fr',from:2017,to:2019},
'domaine-de-chevalier':{v:'gravel on clay-gravel subsoil.',seen:20,of:40,src:'2011-DOMAINE-de-CHEVALIER-Rouge-Anglais.pdf_.pdf',label:'Soil : ',lang:'en',from:1989,to:2015},
'du-tertre':{v:'AREA UNDER VINE AREA IN PRODUCTION PLANTINGS',seen:2,of:4,src:'FT-CHATEAU-DU-TERTRE-2023-ANG.pdf',label:'SOIL ',lang:'fr',from:2023,to:2024},
'duhart-milon':{v:'Château Duhart-Milon’s vineyard consists of a single block of vines adjacent to Château Lafite Rothschild, on the hillside to the west of the Carruades plateau. The property has 76 hectares of vines. The soil consists of fine gravel mixed with aeolian sand on a tertiary limestone.',seen:20,of:32,src:'Chateau-Duhart-Milon-1988.pdf',label:'Terroir : ',lang:'en',from:1988,to:2024},
'giscours':{v:'Graves d’origine garonnaise profondes',seen:4,of:10,src:'CH.-GISCOURS-2024-FR-1.pdf',label:'SOL ',lang:'fr',from:2023,to:2025},
'grand-puy-lacoste':{v:'Terroir Very deep coarse gravel Vineyard',seen:2,of:27,src:'chateau-grand-puy-lacoste-2017EN.pdf',label:'Soil - ',lang:'en',from:2017,to:2018},
'gruaud-larose':{v:'Garonne gravel from the first quaternary, settled more than 600 000 years ago',seen:37,of:43,src:'1988__en-wines-gruaud-larose-1988.txt',label:'SOIL : ',lang:'en',from:1988,to:2024},
'guiraud':{v:'80 % sandy gravels, 20% clay gravels.',seen:5,of:10,src:'Guiraud-2012-FT-FR-89.pdf',label:'Soils: ',lang:'en',from:2010,to:2017},
'la-conseillante':{v:'60% grey clay and 40% sandy gravel',seen:18,of:35,src:'Tech-sheet-la-Conseillante-2020.pdf',label:'Soil ',lang:'en',from:2001,to:2023},
'la-fleur-de-bouard':{v:'16 ha avec des sols argilo-sableux en surface et de graves en sous-sol sur le plateau de Néac, 8 ha d’un seul tenant sur une étonnante croupe graveleuse comportant 15% à 20% d’argiles sur le plateau de Lalande Pomerol, et 9 ha sur des croupes d’argiles graveleuses.',seen:2,of:3,src:'FT-La-Fleur-MILL-2019-FR.pdf',label:'SOL ',lang:'fr',from:2018,to:2019},
'la-lagune':{v:'THE FINESSE OF THE GRAVES AND THE STRENGTH OF THE MÉDOC. The terroir of La Lagune is considered by the famous geologist René Pijassou as «the Medoc island model».',seen:9,of:10,src:'LL_fiche-technique_2012.pdf',label:'SOIL ',lang:'en',from:2012,to:2022},
'la-tour-blanche':{v:'Graves sur sous-sol argilo-calcaire',seen:4,of:6,src:'Fiche_Brumes.pdf',label:'TERROIR : ',lang:'fr'},
'la-tour-carnet':{v:'Clay subsoil with a large proportion of limestone covered by a deep layer of Günz gravel Vineyard management : -Detailed-oriented',seen:2,of:19,src:'LA-TOUR-CARNET-2014-FT-GB-168.pdf',label:'Soil : ',lang:'en',from:2014,to:2017},
'lafite':{v:'Chateau Lafite Rothschild is located to the north of the appellation, bordering Saint Estèphe. Lafite\'s best terroirs stretch on the 50ha Plateau des Carruades to the west of the Château. This plateau, which is the highest point of the Pauillac appellation, is well-drained and enjoys optimal sun exposure.',seen:41,of:48,src:'Chateau-Lafite-Rothschild-1968.pdf',label:'Terroir : ',lang:'en',from:1968,to:2024},
'lafon-rochet':{v:'DEEP GRAVELS + GRAVELS ON CLAY',seen:8,of:13,src:'FT_LafonRochet2009_EN.pdf',label:'SOIL ',lang:'en',from:2009,to:2022},
'lagrange':{v:'Totalement situé sur la commune de Saint­Julien',seen:6,of:8,src:'Chateau-Lagrange-2020-FR.pdf',label:'TERROIR ',lang:'fr',from:2019,to:2025},
'langoa-barton':{v:'graves sur sous-sol d\'argile / Deep gravel on clay subsoil',seen:10,of:10,src:'Chateau-Langoa-Barton-Primeurs-2019.pdf',label:'Soil: ',lang:'fr',from:2016,to:2025},
'larcis-ducasse':{v:'10% de plateau argilo-calcaire sur calcaire à astéries.',seen:4,of:13,src:'Larcis-Ducasse-2016-FR.pdf',label:'Terroirs : ',lang:'fr',from:2016,to:2023},
'leoville-barton':{v:'graves sur sous-sol d\'argile / Deep gravel on clay subsoil',seen:10,of:10,src:'Chateau-Leoville-Barton-Primeurs-2022.pdf',label:'Soil: ',lang:'fr',from:2015,to:2025},
'leoville-poyferre':{v:'! Château Léoville Poyferré propose toute l’année des visites',seen:2,of:7,src:'Ch-Leoville-Poyferre-Millesime-2017.pdf',label:'TERROIR ',lang:'fr',from:2017,to:2019},
'levangile':{v:'L’Evangile’s vineyard covers 22 hectares at the heart of the Pomerol plateau, sharing the appellation’s best terroirs with two other prestigious properties. Here, through a mystery of geology, the heavy green clay soils are covered by a bed of gravel.',seen:32,of:32,src:'Chateau-LEvangile-1981.pdf',label:'Terroir : ',lang:'en',from:1981,to:2024},
'lynch-bages':{v:'Garonne Gravel',seen:21,of:21,src:'Chateau-Lynch-Bages-2000-EN.pdf',label:'soil',lang:'en',from:2000,to:2020},
'marjosse':{v:'argilo-calcaire',seen:2,of:2,src:'MARJOSSE-BLANC-2020-FR.pdf',label:'Nature du sol : ',lang:'fr',from:2014,to:2020},
'marquis-de-terme':{v:'Deep gravel, locally more clayey, settled on 2 major fmilies of soils that give our wines their identity.',seen:9,of:21,src:'MdT-2015-Fiche-technique-Revue-de-Presse-Marquis-de-Terme-EN_compressed.pdf',label:'SOILS ',lang:'en',from:2015,to:2023},
'olivier':{v:'graves (50%), argilo-calcaire (35%) et sables (15%) ¨',seen:11,of:12,src:'FT-Chateau-Olivier-2017-ROUGE-FR.pdf',label:'Sols : ',lang:'fr',from:2013,to:2021},
'pape-clement':{v:'Clay gravels dating back to the end of the Pliocene epoch and the Quaternary period.',seen:2,of:15,src:'FT-Chateau-Pape-Clement-rouge-2019-EN.pdf',label:'Soil : ',lang:'en',from:2019,to:2020},
'pavie-macquin':{v:'Plateau argilo-calcaire sur calcaire à astéries/limestone-clay plateau over asteriated limestone Pratiques culturales/Vineyard practices : Combinaison de façons traditionnelles (labours) et d’enherbement naturel.',seen:3,of:13,src:'FT-PavieMacquin-2022-VFVA.pdf',label:'Terroir : ',lang:'fr',from:2022,to:2025},
'pedesclaux':{v:'complexe.',seen:5,of:7,src:'Chateau_Pedesclaux_2018-FT-FR.pdf',label:'terroir : ',lang:'fr',from:2016,to:2020},
'pichon-comtesse':{v:'ARGILO-SABLEUX',seen:4,of:4,src:'Pichon-Comtesse-Lalande-2018-FT-FR.pdf',label:'SOUS-SOLS ',lang:'fr',from:2018,to:2021},
'pomerol-chateau-beauregard':{v:'Graves argileuses en bordure sud-est du célèbre plateau de Pomerol.',seen:3,of:8,src:'Beauregard-2016-FT-FR-17.pdf',label:'TERROIR : ',lang:'fr',from:2013,to:2021},
'pomerol-chateau-la-croix-de-gay':{v:'- Gravels of Günz era on clay - Pure blue clay with iron oxides',seen:3,of:5,src:'Mill2019-FT-CDG-ENG.pdf',label:'Soil ',lang:'en',from:2017,to:2020},
'pomerol-chateau-taillefer':{v:'silica and gravel on a clay base, rich in iron deposits',seen:4,of:13,src:'Taillefer_2022_fichetechnique_fr_en-.pdf',label:'Soil : ',lang:'en',from:2021,to:2025},
'pomerol-chateau-vray-croix-de-gay':{v:'gravel, deep clays, sandy clays',seen:6,of:6,src:'FT_Plaisir_2012_EN.pdf',label:'TERROIR : ',lang:'en',from:2012,to:2017},
'pouget':{v:'graves silencieuses maigres de Margaux',seen:2,of:2,src:'Fiche-Pouget-2017-FR.pdf',label:'Sols: ',lang:'fr',from:2017,to:2018},
'prieure-lichine':{v:'Garonne gravel from the Günz era •',seen:2,of:17,src:'Fiche_Technique_Chateau_PRIEURE_LICHINE_MAR_RO_2023_Francais_et_Anglais.pdf',label:'SOIL ',lang:'en',from:2023,to:2024},
'rauzan-segla':{v:'Graves argileuses de la terrasse 4 Mosaïque de graves fines et profondes',seen:4,of:6,src:'FT_RAUZAN_SEGLA_FR_2020.pdf',label:'SOLS ',lang:'fr',from:2016,to:2020},
'rieussec':{v:'Château Rieussec sits on the border of Fargues and Sauternes, bordered by Château d\'Yquem to the West. Rieussec is one of the largest properties in Sauternes and Barsac, covering 93 hectares of gravel sitting on sandy-clay soils.',seen:17,of:29,src:'Chateau-Rieussec-1975.pdf',label:'Terroir : ',lang:'en',from:1975,to:2020},
'siaurac':{v:'Gravel, deep clays and sandy clays Vineyard area : 45,15 hectares - 43 plots',seen:4,of:46,src:'FT-GB-2023-Chateau-Siaurac-.pdf',label:'Soil : ',lang:'en',from:2023,to:2025},
'stem-chateau-bellefont-belcier':{v:'SOILS PRATIQUE CULTURALE PRATIQUE CULTURALE VINEYARD MAINTENANCE VINEYARD MAINTENANCE',seen:2,of:7,src:'Bellefont-Belcier-2022-FT-FR-GB-Primeurs.pdf',label:'SOILS ',lang:'en',from:2022,to:2023},
'stem-chateau-cote-de-baleau':{v:'Argilo-calcaires et argilo-sableux',seen:2,of:3,src:'Chateau-Cote-de-Baleau_millesime-2024.pdf',label:'SOL ',lang:'fr',from:2023,to:2024},
'stem-chateau-dassault':{v:'sablo-argileux, argilo-sableux et argile sur molasse du fronsadais',seen:2,of:6,src:'Dassault-2018-FT-FR.pdf',label:'Sol : ',lang:'fr',from:2018,to:2021},
'stem-chateau-fombrauge':{v:'argilo-calcaire et molasse du fronsadais Mode de conduite des vignes : - Entretien du sol de façon parcellaire (enherbement, labour) - Ebourgeonnage et échardage début juillet - 1er effeuillage en juillet _ 2ème effeuillage en septembre',seen:2,of:6,src:'Fombrauge-2014-FT-FR.pdf',label:'Nature du sol : ',lang:'fr',from:2013,to:2014},
'stem-chateau-grand-corbin-despagne':{v:'argilo-siliceux sur crasse de fer et sables anciens sur argile bleue',seen:28,of:34,src:'fiche_technique_GCD_1996.pdf',label:'Terroir : ',lang:'fr',from:1996,to:2025},
'stem-chateau-grand-mayne':{v:'Côteau argilo-calcaire et pied de côteau d’argile Slope clay and limestone and foot of the slope clay',seen:7,of:15,src:'Chateau-Grand-Mayne-2019.pdf',label:'TERROIR ',lang:'en',from:2015,to:2022},
'stem-chateau-la-dominique':{v:'Argilo-graveleux, argilo-calcaire et sables sur argile ÂGE MOYEN DE LA VIGNE 27 ans',seen:3,of:6,src:'ld-2005-sans.notes-fr.pdf',label:'SOL ',lang:'fr',from:2005,to:2021},
'stem-chateau-le-chatelet':{v:'Plateau calcaire à astéries.',seen:15,of:15,src:'Fiche-millesime-2008-PDF.pdf',label:'Sol : ',lang:'fr',from:2008,to:2023},
'stem-chateau-moulin-du-cadet':{v:'Clay-limestone over the plateau of Saint Emilion',seen:6,of:50,src:'FT-Moulin-du-Cadet-2022-GB.pdf',label:'Soil ',lang:'en',from:2020,to:2022},
'stem-chateau-ripeau':{v:'slightly stony, sandy soil with iron-bearing clay in the subsoil.',seen:6,of:22,src:'2020-FT-RIPEAU-GB1.pdf',label:'Soil ',lang:'en',from:2019,to:2024},
'stem-chateau-rol-valentin':{v:'Sable ancien sur argile (1.80 ha) Argilo-calcaire sur coteaux et plateaux (5.50 ha) ',seen:4,of:4,src:'Chateau-Rol-Valentin-2014-FR.pdf',label:'Terroir : ',lang:'fr',from:2014,to:2018},
'stem-chateau-sansonnet':{v:'Clay-limestone over the plateau of Saint Emilion',seen:4,of:62,src:'FT-SANSONNET-2020-gb.pdf',label:'Soil ',lang:'en',from:2020,to:2022},
'stem-chateau-soutard':{v:'70 % of clay & limestone plateau, 17 % of clay slopes, 13 % of sandy slopes',seen:4,of:7,src:'Fiche-Technique-Soutard-2016-GB-comments.pdf',label:'Terroirs : ',lang:'en',from:2016,to:2022},
'stem-chateau-tour-saint-christophe':{v:'Clay Limestone',seen:16,of:32,src:'PRODUCT-SHEET-CHATEAU-TOUR-SAINT-CHRISTOPHE-2014.pdf',label:'SOILS ',lang:'en',from:2014,to:2021},
'stem-chateau-villemaurine':{v:'Argilo-calcaire au dessus du calcaire à Astéries.',seen:8,of:9,src:'fiche_technique_Villemaurine_generale.pdf',label:'SOL : ',lang:'fr',from:2014,to:2021},
'stem-chateau-yon-figeac':{v:'Argilo-sableux sur "crasses de fer"',seen:4,of:5,src:'Yon-Figeac-2010-FT-FR-175.pdf',label:'Sols : ',lang:'fr',from:2010,to:2015},
'stem-clos-de-l-oratoire':{v:'Argilo-calcaire et molasse de Fronsac en haut de côte ; argilo-sableux en pied de côte',seen:2,of:3,src:'Clos-de-lOratoire-2012-FT-FR-439.pdf',label:'Terroirs : ',lang:'fr',from:2012,to:2014},
'valandraud':{v:'clayey-limestone',seen:3,of:7,src:'Chateau-Valandraud-2022.pdf',label:'Soil : ',lang:'en',from:2020,to:2022},
'vrai-canon-bouche':{v:'calcaire à astérie recouvert d’argile de décarbonatation Pratiques culturales : travail mécanique en totalité, lutte phytosani- taire raisonnée, effeuillage et éclaircissage manuel.',seen:2,of:2,src:'Fiche-Technique-Vrai-Canon-Bouche-2019.pdf',label:'sols : ',lang:'fr',from:2018,to:2019},
};
if (typeof window !== 'undefined') window.BDX_TERROIR = BDX_TERROIR;
