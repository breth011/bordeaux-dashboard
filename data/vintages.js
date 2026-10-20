/* ===========================================================================
   Bordeaux Dashboard — Vintage reference, 1982–2024
   ---------------------------------------------------------------------------
   PROVENANCE: the weather accounts and vintage characterisations below are
   VERIFIED — they describe documented growing seasons and the settled
   critical consensus on each year. The numeric ratings are a 100-point
   summary of that consensus and should be read as indicative, not as any
   single critic's published vintage score.

     medoc      base rating for the Médoc appellations
     pessac     base rating for Pessac-Léognan (Haut-Brion)
     sauternes  base rating for Sauternes & Barsac
     app        per-appellation adjustments, where the year treated
                communes very differently (e.g. 2003, 2015, 1996)
     drinkFrom / drinkTo
                indicative maturity window for a classified-growth red
                of that year. drinkWindow() in app.js moves it per estate,
                by rank, blend and whatever the critics scored that wine,
                and shows it against the estate as derived. Sweet and dry
                white wines are not on this clock at all and are worked
                out there rather than here.
   =========================================================================== */

window.BDX_VINTAGES = {

1982:{medoc:98,pessac:95,sauternes:72,drinkFrom:1992,drinkTo:2035,
 weather:'A hot, dry summer and a warm September produced the ripest Médoc crop since 1961. Harvest began unusually early in mid-September under perfect conditions.',
 report:'The vintage that changed Bordeaux. Enormous ripeness, low acidity and sweet tannins produced wines that tasted delicious young yet have aged for forty years. Robert Parker’s early championing of the vintage against a sceptical British trade made both his reputation and the modern en primeur market. Pauillac and Saint-Julien are at the summit. Rain during the Sauternes harvest cut short botrytis, making it a poor year for the sweet wines.'},

1983:{medoc:88,pessac:88,sauternes:95,drinkFrom:1993,drinkTo:2025,app:{'Margaux':4},
 weather:'A hot, humid August brought mildew pressure, followed by a fine, dry September. A large crop.',
 report:'Overshadowed by 1982 but a genuinely classic year, firmer and more tannic than its neighbour. Margaux was the clear star — the 1983 Château Margaux is widely held to surpass its 1982. Humidity that troubled the reds was ideal for Sauternes, where botrytis was abundant and the wines are excellent.'},

1984:{medoc:70,pessac:70,sauternes:70,drinkFrom:1990,drinkTo:2000,
 weather:'Catastrophic coulure during Merlot flowering destroyed much of that crop; a cool, wet autumn followed.',
 report:'The weakest vintage of the modern era in the Médoc. With Merlot largely lost, many wines were made almost entirely from Cabernet Sauvignon and came out lean, hard and hollow. Of historical interest only; almost all are now past.'},

1985:{medoc:90,pessac:90,sauternes:80,drinkFrom:1993,drinkTo:2025,
 weather:'A cold January damaged some vines, but a warm, dry late summer and a gloriously fine October allowed a long, unhurried harvest.',
 report:'Charming, ripe and harmonious — a vintage of seduction rather than power. The wines were approachable early and the best have aged far longer than anyone predicted. Sauternes was decent but botrytis arrived patchily.'},

1986:{medoc:93,pessac:88,sauternes:93,drinkFrom:1998,drinkTo:2035,app:{'Pauillac':2,'Saint-Estèphe':2},
 weather:'A very large crop ripened under a hot August; September rain arrived but a dry, windy spell before harvest concentrated the Cabernet.',
 report:'A monumental Cabernet Sauvignon year in the northern Médoc, producing some of the most tannic wines of the century. Mouton Rothschild 1986 is the vintage’s emblem. The wines demanded enormous patience and some never fully resolved their tannin; Margaux and the Merlot-led properties are less successful. Excellent in Sauternes.'},

1987:{medoc:72,pessac:74,sauternes:72,drinkFrom:1991,drinkTo:2000,
 weather:'A fine summer was undone by heavy rain in early October, right across the Cabernet harvest.',
 report:'Dilute and light. Estates that picked their Merlot before the rain did best. A vintage for curiosity rather than the cellar.'},

1988:{medoc:88,pessac:88,sauternes:97,drinkFrom:1998,drinkTo:2030,
 weather:'A wet winter and spring, then a dry, sunny late summer. A long, cool autumn allowed slow, even ripening and perfect botrytis in Sauternes.',
 report:'A classical, structured vintage with firm tannins and high acidity — austere in youth and often underrated beside 1989 and 1990. In Sauternes it is the first of a legendary trio; 1988, 1989 and 1990 are the finest consecutive run the appellation has had.'},

1989:{medoc:94,pessac:95,sauternes:96,drinkFrom:1997,drinkTo:2035,app:{'Pessac-Léognan':2},
 weather:'The hottest, earliest growing season since 1947. Flowering was exceptionally early and harvest began in late August for some whites.',
 report:'Opulent, fleshy and high in alcohol, with lower acidity than 1990. Haut-Brion 1989 is regarded by many as the single greatest wine of the post-war era in Bordeaux. Superb in Sauternes, where heat and humidity gave rich, powerful wines.'},

1990:{medoc:96,pessac:94,sauternes:98,drinkFrom:1998,drinkTo:2040,
 weather:'A third consecutive hot year, with real drought stress in August broken by light, timely rain. A warm, dry harvest.',
 report:'The greatest vintage between 1982 and 2000, and for many the finest of the three great consecutive years. More concentrated and better balanced than 1989, with the structure to go much further. Montrose 1990 and Margaux 1990 are reference points. Sauternes reached its modern peak.'},

1991:{medoc:65,pessac:68,sauternes:70,drinkFrom:1995,drinkTo:2002,
 weather:'A severe frost on 20–21 April destroyed the primary buds across much of the Médoc, cutting the crop by more than half.',
 report:'The smallest and poorest crop in decades. Secondary buds gave uneven, unripe fruit and September rain finished the job. Several estates declassified their entire production.'},

1992:{medoc:68,pessac:70,sauternes:60,drinkFrom:1995,drinkTo:2003,
 weather:'The wettest year on record at the time, with rain through the summer and a deluge at harvest.',
 report:'Thoroughly dilute. Yquem declared no vintage. One of the few years in which almost nothing is worth seeking out.'},

1993:{medoc:74,pessac:76,sauternes:62,drinkFrom:1998,drinkTo:2008,
 weather:'A promising dry summer was ruined by persistent September rain that arrived just as the Cabernet approached ripeness.',
 report:'Lean, herbaceous and quick to fade, though the best northern Médoc estates made honest, if slender, wines. A washout for Sauternes.'},

1994:{medoc:80,pessac:80,sauternes:72,drinkFrom:1999,drinkTo:2012,
 weather:'An excellent summer and an exceptionally promising early September, then two weeks of heavy rain from 7 September.',
 report:'The great "what if" vintage. Properties that had already picked, or that could wait out the rain, made firm, tannic, respectable wines. Most are now drying out.'},

1995:{medoc:90,pessac:90,sauternes:88,drinkFrom:2003,drinkTo:2028,
 weather:'A hot, dry summer with real drought, then some rain in September that swelled the berries before a fine harvest.',
 report:'The first genuinely fine vintage since 1990 and greeted with great relief. Ripe, structured and generous, firmer than 1996 in the south and softer in the north. Good, clean botrytis in Sauternes.'},

1996:{medoc:92,pessac:86,sauternes:88,drinkFrom:2006,drinkTo:2035,
 app:{'Pauillac':2,'Saint-Estèphe':2,'Saint-Julien':2,'Margaux':-2,'Pessac-Léognan':-2},
 weather:'A cool, dry September with strong northerly winds gave textbook late-season conditions for Cabernet Sauvignon; Merlot was picked earlier and less successfully.',
 report:'A great Cabernet vintage, sharply split by geography. Pauillac, Saint-Julien and Saint-Estèphe made structured, classically proportioned wines that are only now reaching their peak — Léoville-Las Cases 1996 is the emblem. Margaux and the Merlot-led properties of the south and Pessac are markedly weaker.'},

1997:{medoc:76,pessac:78,sauternes:93,drinkFrom:2001,drinkTo:2012,
 weather:'Erratic flowering spread ripeness unevenly across each bunch; a warm, humid August and a damp harvest followed.',
 report:'Soft, light and early-maturing reds, released at absurdly high prices on the back of 1995 and 1996. Sauternes, by contrast, had near-perfect botrytis conditions and the vintage is outstanding there.'},

1998:{medoc:85,pessac:88,sauternes:88,drinkFrom:2006,drinkTo:2025,app:{'Pessac-Léognan':3},
 weather:'An intensely hot August, then rain from late September that fell before most Médoc Cabernet was ready.',
 report:'Fundamentally a Right Bank and Pessac-Léognan year — Merlot was picked in good conditions, Médoc Cabernet was not. Haut-Brion made one of the wines of the decade. In the Médoc the wines are respectable but rarely more.'},

1999:{medoc:82,pessac:82,sauternes:88,drinkFrom:2005,drinkTo:2018,
 weather:'Hail in several communes, a hot humid summer and rain during the harvest.',
 report:'A difficult, patchy year rescued by rigorous selection at the top estates. The wines are soft, mid-weight and have mostly been drunk.'},

2000:{medoc:95,pessac:94,sauternes:72,drinkFrom:2010,drinkTo:2040,
 weather:'A wet, worrying spring and early summer gave way to a hot, bone-dry August and September — one of the driest late seasons on record.',
 report:'The millennium vintage, and the most uniformly excellent year the Médoc had seen since 1982. Dark, dense and powerfully structured across every commune, with remarkable consistency even among the lesser growths. The dryness that made the reds left Sauternes with almost no botrytis, and it is a poor year there.'},

2001:{medoc:88,pessac:88,sauternes:99,drinkFrom:2008,drinkTo:2028,
 weather:'A cooler, slower season than 2000, with a fine October. Sauternes enjoyed a textbook alternation of morning mist and warm afternoons.',
 report:'Unfairly dismissed for years as the shadow of 2000, and in fact a fresh, fragrant, beautifully balanced classic that has aged gracefully — often the better bottle to open today. In Sauternes 2001 is simply the greatest vintage in living memory; Yquem 2001 and Climens 2001 are the definitive wines.'},

2002:{medoc:86,pessac:84,sauternes:88,drinkFrom:2009,drinkTo:2025,app:{'Pauillac':2,'Saint-Estèphe':1},
 weather:'A poor, cool summer with difficult flowering, transformed by an exceptionally sunny, dry September and October.',
 report:'Saved at the eleventh hour, and strictly a late-ripening Cabernet year. The northern Médoc made firm, fresh, classically styled wines well above the vintage’s reputation; Merlot-dominated properties struggled.'},

2003:{medoc:89,pessac:85,sauternes:92,drinkFrom:2008,drinkTo:2030,
 app:{'Saint-Estèphe':4,'Pauillac':3,'Margaux':-3,'Pessac-Léognan':-3,'Haut-Médoc':-2},
 weather:'The European heatwave. Temperatures reached 40°C for days on end in August and vines shut down; harvest was the earliest since 1893.',
 report:'A freak vintage, and strongly site-dependent. The heavy clay soils of Saint-Estèphe and northern Pauillac retained water and produced spectacular, exotic wines — Montrose 2003 and Latour 2003 are triumphs. On the lighter gravels of Margaux and Pessac the vines suffered badly and the wines are jammy, low in acid and already tiring. Rich, if atypical, in Sauternes.'},

2004:{medoc:85,pessac:85,sauternes:86,drinkFrom:2010,drinkTo:2022,
 weather:'A large crop and a cool, damp August, followed by a dry and sunny September that allowed full ripening.',
 report:'A return to classicism after 2003 — fresh, medium-bodied and correct, with good acidity and moderate alcohol. Never exciting, but honest and now drinking well. Yields needed firm control.'},

2005:{medoc:98,pessac:97,sauternes:94,drinkFrom:2015,drinkTo:2050,
 weather:'A textbook season: a dry spring, a warm summer with mild, steady drought that never became stressful, cool nights, and a dry harvest with no rain at all.',
 report:'As close to a perfect growing season as Bordeaux has had. Every commune succeeded, the tannins are both abundant and ripe, and the balance of fruit, acidity and structure is exceptional. Still tightly wound two decades on; the greatest wines will outlive most of their buyers. Excellent in Sauternes too.'},

2006:{medoc:87,pessac:86,sauternes:90,drinkFrom:2013,drinkTo:2028,
 weather:'A scorching July, an unusually cold and wet August, then rain that interrupted the harvest from late September.',
 report:'A stop-start season that demanded picking decisions be made well. The Cabernet-dominated northern Médoc did best; the wines are firm, slightly austere and have aged better than their initially cool reception suggested.'},

2007:{medoc:80,pessac:82,sauternes:95,drinkFrom:2011,drinkTo:2020,
 weather:'A warm spring, a cold wet summer with relentless mildew pressure, then a dry and sunny September and October.',
 report:'A difficult red vintage saved only partially by the autumn; the wines are light, fresh and were made for early drinking, most of which has now happened. Sauternes, however, had near-ideal botrytis and 2007 is one of its great modern years.'},

2008:{medoc:88,pessac:88,sauternes:90,drinkFrom:2014,drinkTo:2032,
 weather:'A cold, wet, mildew-ridden summer, then a long, dry, sunny autumn that allowed one of the latest harvests in decades.',
 report:'The quiet success of the era. Saved by October sunshine and sold cheaply into the financial crisis, the wines are fresh, firm, classically proportioned and have aged far better than expected. Still one of the best-value fine vintages on the market.'},

2009:{medoc:98,pessac:97,sauternes:95,drinkFrom:2017,drinkTo:2050,
 weather:'A warm, dry and almost trouble-free season, with a hot August, cool nights preserving acidity, and a perfectly dry harvest.',
 report:'A vintage of extraordinary ripeness and opulence — high alcohol, sumptuous fruit and velvety tannins. The most immediately hedonistic great Bordeaux vintage, and the one that produced an unprecedented run of perfect scores. The point of comparison with its sterner twin, 2010, divides collectors to this day.'},

2010:{medoc:98,pessac:96,sauternes:95,drinkFrom:2020,drinkTo:2055,
 weather:'A dry, cool season with significant drought and very cold nights in September; small berries with very thick skins.',
 report:'The structural counterpart to 2009 — the same ripeness but with far higher tannin and acidity, and often even higher alcohol. Darker, sterner and more Cabernet-driven, built for the very long haul. Many critics consider it the greater of the pair for the Médoc, though it demands real patience.'},

2011:{medoc:85,pessac:84,sauternes:94,drinkFrom:2016,drinkTo:2026,
 weather:'A record-hot spring brought the earliest flowering ever recorded, then a cool, damp summer reversed the advance. Hail hit parts of the Médoc.',
 report:'An inverted season that left the fruit ripe in sugar but not always in tannin. The reds are medium-bodied and a little angular, best drunk now. Sauternes, by contrast, was excellent — an early, abundant and very clean botrytis.'},

2012:{medoc:84,pessac:84,sauternes:84,drinkFrom:2017,drinkTo:2026,
 weather:'A cold, wet spring disrupted flowering, the summer was hot and dry, and October rain arrived before the Cabernet was fully ripe.',
 report:'Merlot ripened well, Cabernet Sauvignon frequently did not — the opposite of what the Left Bank needs. Pleasant, forward, mid-weight wines for current drinking. Yquem declared no vintage.'},

2013:{medoc:72,pessac:74,sauternes:88,drinkFrom:2016,drinkTo:2022,
 weather:'Disastrous flowering in a cold wet June, hail in July and August, then rot-inducing rain through the September harvest.',
 report:'The weakest Bordeaux vintage since 1991, and for the Médoc arguably since 1984. Crops were tiny and selection brutal; even first growths made light, simple wines. The single bright spot is Sauternes, where a short, concentrated and very clean botrytised crop produced genuinely fine wines.'},

2014:{medoc:88,pessac:88,sauternes:92,drinkFrom:2020,drinkTo:2035,
 weather:'A mediocre, cool summer followed by a remarkable Indian summer — September and October were warm, dry and sunny, with one of the latest harvests on record.',
 report:'Rescued outright by the autumn. The Cabernet ripened slowly and fully, and the northern Médoc in particular made fresh, finely structured, properly classical wines at modest prices. A consistently rewarding vintage to buy.'},

2015:{medoc:92,pessac:95,sauternes:92,drinkFrom:2021,drinkTo:2045,
 app:{'Margaux':3,'Pessac-Léognan':3,'Saint-Estèphe':-2,'Pauillac':-1},
 weather:'A hot, dry June and July, then August rain that fell very unevenly — heavily in the southern Médoc and Pessac, barely at all further north.',
 report:'A great vintage in the south. Margaux and Pessac-Léognan, which received the rain they needed at the right moment, produced wines of exceptional perfume and silkiness — Château Margaux 2015, Jean-Paul Pontallier’s last vintage, is a monument. Saint-Estèphe and northern Pauillac, drier and more stressed, are good but a clear step behind.'},

2016:{medoc:97,pessac:96,sauternes:90,drinkFrom:2024,drinkTo:2055,
 weather:'An extraordinarily wet winter and spring — the wettest on record in places — then a total drought from late June to mid-September, broken by perfectly timed rain on 13 September.',
 report:'A vintage of almost improbable quality from an alarming season. The winter rain left deep water reserves that carried the vines through the drought; the September rain arrived exactly when needed. The result combines 2010’s structure with 2009’s ripeness and adds freshness neither had — tannins of remarkable fineness and volume. For many, the finest Médoc vintage of the century so far.'},

2017:{medoc:86,pessac:82,sauternes:92,drinkFrom:2022,drinkTo:2032,
 app:{'Pessac-Léognan':-4,'Haut-Médoc':-2},
 weather:'Severe frosts on 27–28 April devastated low-lying and inland vineyards. The classified Médoc estates on the riverside gravel were largely spared; Pessac-Léognan and the Haut-Médoc were hit hard.',
 report:'A tale of two Bordeaux. The great riverside Médoc estates, protected by the Gironde’s thermal mass, made fresh, elegant, early-maturing wines of real charm. Properties further inland lost most or all of their crop. Check provenance carefully: quality varies more by vineyard location this year than by reputation.'},

2018:{medoc:95,pessac:94,sauternes:90,drinkFrom:2026,drinkTo:2050,
 weather:'A wet, warm spring brought the worst mildew epidemic in thirty years — some organic estates lost most of their crop — then an unbroken hot, dry summer from July to harvest.',
 report:'A vintage of extremes and of enormous power. Alcohol levels reached 14.5–15% at many estates and tannin loads were the highest ever measured at some. The best wines are magnificent and deep; the less careful are ponderous. Those who fought the mildew successfully, Pontet-Canet and Palmer among them, were heavily rewarded.'},

2019:{medoc:95,pessac:94,sauternes:92,drinkFrom:2025,drinkTo:2048,
 weather:'A warm, dry season with two heat spikes in June and July, then cool nights in September and a dry harvest.',
 report:'All the ripeness of 2018 with better balance and lower alcohol — fresher, more precise and more drinkable. Released at reduced prices during the pandemic, it is one of the strongest quality-to-price vintages of the last twenty years.'},

2020:{medoc:94,pessac:93,sauternes:88,drinkFrom:2026,drinkTo:2048,
 weather:'The third hot, dry year in a row. An early budbreak, serious summer drought, tiny berries and a very early harvest; a brief mid-August rain saved the vines from shutting down.',
 report:'Intensely concentrated, with deep colour and dense fruit from very high skin-to-juice ratios. Slightly less complete than 2019 and more variable between estates, but the best wines are superb. The last of the great 2018–2019–2020 run.'},

2021:{medoc:85,pessac:84,sauternes:88,drinkFrom:2026,drinkTo:2038,
 weather:'April frost, a cool, wet summer and heavy mildew pressure — a return to the old Bordeaux pattern after three hot years.',
 report:'A genuinely classical vintage, and a useful corrective. Alcohols are back down near 12.5–13%, acidities are high and the wines are fresh, aromatic and medium-bodied in the manner of the 1980s. Not for long ageing at most estates, but a pleasure to drink and modestly priced.'},

2022:{medoc:97,pessac:96,sauternes:92,drinkFrom:2028,drinkTo:2055,
 weather:'The hottest and driest year ever recorded in Bordeaux — repeated heatwaves, almost no summer rain, and widespread hydric stress. Hail struck parts of the region in June.',
 report:'The great surprise of the decade. By every historical expectation the wines should have been cooked, and instead they are fresh, precise and extraordinarily fine-tannined. The vines appear to have adapted to drought by shutting down early rather than suffering; the result is deep colour, ripe tannin and acidity that nobody can quite explain. Widely rated alongside 2016 and 2010.'},

2023:{medoc:92,pessac:91,sauternes:90,drinkFrom:2028,drinkTo:2045,
 weather:'A warm, humid spring and summer with relentless mildew pressure, a brief September heat spike, and a large crop that needed aggressive sorting.',
 report:'A good, sometimes very good, classical vintage that rewarded the diligent. Those who sprayed carefully and green-harvested made fresh, well-balanced wines with real Cabernet definition; those who let yields run made dilute ones. Quality is less uniform than 2022 but the top wines are excellent and sensibly priced.'},

2024:{medoc:83,pessac:82,sauternes:85,drinkFrom:2028,drinkTo:2038,
 weather:'A cold, exceptionally wet spring caused poor flowering and coulure, mildew pressure persisted all season, and the summer was among the dullest and coolest in years.',
 report:'A difficult, small vintage in the old style. Cabernet Sauvignon on the best-drained Médoc gravel ripened adequately and the leading estates, through severe selection, made light, fresh, early-drinking wines with genuine classical charm. Merlot suffered. Expectations should be modest, and prices reflect it.'}

};
