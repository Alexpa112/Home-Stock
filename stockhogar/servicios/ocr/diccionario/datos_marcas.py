"""Marcas y marcas blancas de supermercado en Espana.

Se ignoran al identificar un articulo: "LECHE ENTERA PASCUAL" y "LECHE ENTERA
HACENDADO" son el mismo articulo para el stock. Normalizadas (minusculas, sin
tildes); admiten varias palabras ("central lechera asturiana").
"""

MARCAS = {
    "hacendado", "deliplus", "bosque verde", "compy", "carrefour", "auchan", "alcampo", "eroski", "basic",
    "consum", "lidl", "milbona", "pilos", "solevita", "freeway", "w5", "silvercrest", "parkside",
    "crivit", "livarno", "bellarom", "chef select", "fin carre", "alesto", "sondey", "vitasia", "dulano",
    "aldi", "milsani", "gutbio", "lacura", "tandil", "casa morando", "elvital",
    "bonpreu", "esclat", "caprabo", "condis", "bon area", "bonarea", "ahorramas", "supersol",
    "el corte ingles", "hipercor", "mercadona",
    "mdd", "primer precio",
    "pascual", "central lechera asturiana", "puleva", "kaiku", "president", "danone", "danet", "danacol",
    "activia", "actimel", "yoplait", "nestle", "capsa", "larsa", "covap", "feiraco", "lactalis", "arla",
    "llet nostra", "hochland", "philadelphia", "babybel", "el caserio", "garcia baquero",
    "entrepinares", "asturiana", "iparlat",
    "coca cola", "cocacola", "pepsi", "fanta", "sprite", "aquarius", "nestea", "schweppes", "red bull",
    "monster", "powerade", "font vella", "lanjaron", "solan de cabras", "bezoya", "evian", "vichy catalan",
    "mahou", "estrella damm", "estrella galicia", "san miguel", "cruzcampo", "heineken", "amstel", "alhambra", "voll damm",
    "moritz", "keler", "buckler", "budweiser", "paulaner", "don simon", "marques de caceres",
    "freixenet", "codorniu", "faustino", "campo viejo", "vina pomal", "protos",
    "nescafe", "marcilla", "bonka", "saimaza", "ricoh", "nespresso", "dolce gusto", "tassimo", "senseo", "lavazza",
    "cola cao", "colacao", "nesquik", "nutriben", "nutrexpa", "pickwick", "twinings", "lipton", "hornimans",
    "knorr", "gallina blanca", "maggi", "avecrem", "carbonell", "koipe", "coosur", "abril", "hojiblanca",
    "borges", "la espanola", "bertolli", "brillante", "la fallera", "nomen", "brillante",
    "solis", "heinz", "ligeresa", "ortiz", "frinsa", "escurra",
    "campofrio", "navidul", "el pozo", "oscar mayer", "casademont", "argal", "fuentetaja", "revilla", "mahesos",
    "gvtarra", "tomate frito solis", "yatekomo",
    "barilla", "garofalo", "la molisana", "buitoni", "panzani",
    "bimbo", "panrico", "donuts", "dulcesol", "artiach", "fontaneda", "cuetara", "gullon", "marbu", "chiquilin",
    "oreo", "tosta rica", "ritz", "milka", "nestle", "lindt", "ferrero", "kinder", "nutella", "toblerone",
    "haribo", "chupa chups", "trolli", "mentos", "tic tac", "lacasitos", "conguitos", "pringles", "lays",
    "ruffles", "doritos", "cheetos", "matutano", "risi", "facundo", "gustavo", "aperitivos", "pepsico",
    "kelloggs", "kellogs", "chocapic", "estrellitas", "weetabix", "quaker", "ceregumil",
    "ariel", "skip", "dixan", "asevi", "persil", "wipp",
    "fairy", "mistol", "quix", "finish", "somat", "calgonit", "cillit bang", "domestos",
    "ajax", "mr proper", "don limpio", "sanytol", "kh7", "glade", "ambipur", "air wick",
    "scottex", "colhogar", "renova", "foxy", "elegant", "kleenex", "nenuco", "huggies", "pampers",
    "johnson", "avene", "nivea", "dove", "palmolive", "heno de pravia", "rexona", "axe",
    "head shoulders", "pantene", "garnier", "elvive", "loreal", "l oreal", "schwarzkopf", "gliss", "timotei", "fructis",
    "colgate", "oral b", "oral-b", "sensodyne", "binaca", "listerine", "lacer", "vitis", "phb", "kukident",
    "gillette", "wilkinson", "bic",
    "whiskas", "pedigree", "purina", "friskies", "felix", "royal canin", "brekkies", "affinity", "dreamies",
    "kitekat", "dogui", "cesar", "advance", "tetra",
}
