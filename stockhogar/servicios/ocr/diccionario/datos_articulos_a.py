"""Catalogo ampliado (parte A): lacteos, frutas y verduras, carnes, pescados.

Formato por linea:  Nombre canonico | alias1 ; alias2 | unidad
 - Si el nombre ya existe en el catalogo estandar (config.CATALOGO_DEFECTO), solo
   se anaden los alias; si no, es un articulo nuevo de la categoria de la seccion.
 - Los alias son SINONIMOS o NOMBRES PARCIALES que el comparador no deduce solo
   (incluidos catalan, gallego y euskera, que aparecen en tickets reales). NO se
   enumeran variantes: marcas, abreviaturas ("ent", "desn") y modificadores
   ("fresco", "bandeja", "kg") se resuelven aparte.
 - unidad: ud (por defecto), kg, l, pack.
"""

TEXTO = """
== Lácteos y Huevos
Leche entera | llet sencera; leite enteiro; esne osoa; leche fresca; leche de vaca
Leche desnatada | llet desnatada; leite desnatado; esne gaingabetua
Leche semidesnatada | llet semidesnatada; leite semidesnatado
Leche sin lactosa | llet sense lactosa; leite sen lactosa
Leche condensada | llet condensada; leite condensado
Leche en polvo | | kg
Leche con cacao | batido leche cacao
Huevos | ous; ovos; arrautzak; huevo; docena huevos
Huevos camperos | huevos campero; huevos de campo; huevos gallinas camperas
Huevos cocidos | huevo cocido
Yogur natural | iogurt natural; iogur natural; jogurta natural; yogur natural azucarado; yogur sin azucar
Yogur griego | iogurt grec; yogur estilo griego
Yogur de sabores | yogur fresa; yogur limon; yogur vainilla; yogur coco; yogur macedonia; yogur con fruta; yogur sabor
Yogur desnatado | yogur 0; yogur 0 materia grasa
Yogur líquido | yogur para beber; yogur bebible | ud
Yogur proteínas | skyr; yogur proteico; yogur alto en proteinas | ud
Queso | formatge; queixo; gazta
Queso rallado | formatge ratllat; queixo relado; rallado
Queso fresco | queso burgos; queso blanco; formatge fresc
Queso curado | formatge curat; queixo curado
Queso semicurado | queso semi curado; queso tierno; formatge semicurat
Queso en lonchas | queso lonchas; lonchas queso; queso fundido lonchas; queso cheddar; queso gouda; queso emmental lonchas
Queso para untar | queso crema; philadelphia; queso untable
Queso de cabra | rulo de cabra; formatge de cabra
Queso azul | roquefort; gorgonzola; cabrales
Queso parmesano | parmesano; grana padano; parmigiano
Queso brie | brie; camembert | ud
Queso manchego | manchego | ud
Queso emmental | emmental | ud
Queso feta | feta | ud
Queso en porciones | quesitos; porciones queso; babybel | ud
Mantequilla | mantega; manteiga; gurina
Margarina | margarina vegetal | ud
Nata para cocinar | nata liquida; nata cocinar; crema de leche; nata
Nata montada | nata para montar; nata 35; nata en spray
Natillas | natillas vainilla; natillas chocolate
Flan | flan de huevo; flan vainilla
Cuajada | cuallada
Requesón | requeson; requeixo
Postre lácteo | postre de leche; postre chocolate; postre vainilla; mousse chocolate; copa chocolate | ud
Arroz con leche | arros amb llet; arroz leche postre | ud
Actimel | l casei; leche fermentada; yakult; bifidus
Kéfir | kefir | ud
Batido de chocolate | batido chocolate; batido cacao; batido de cacao
Claras de huevo | clara de huevo; claras liquidas
Yemas de huevo | yemas | ud

== Frutas y Verduras
Plátanos | platano; platano canarias; banana; bananas; platans; platano de canarias | kg
Manzanas | manzana; manzana golden; manzana fuji; manzana gala; manzana royal gala; manzana verde; granny smith; pink lady; pomes; mazas; sagarrak | kg
Naranjas | naranja; naranja mesa; naranja zumo; naranja navel; taronges; laranxas; laranjak | kg
Limones | limon; llimones; limons; limoias | kg
Fresas | fresa; fresones; maduixes; amorodos; marrubiak | kg
Uvas | uva; uva blanca; uva negra; uva roja; uva sin pepitas; raim; uvas sin semilla | kg
Aguacates | aguacate; aguacate hass; alvocats; abacates; palta | kg
Tomates | tomate; tomate pera; tomate rama; tomate ensalada; tomate cherry; tomate canario; tomate raf; tomate kumato; tomate liso; tomaquets; tomaquet; tomateak; tomate rojo | kg
Lechuga | lletuga; leituga; enciam; lechuga romana; romana; iceberg; lechuga iceberg; lechuga hoja roble; lollo rosso | ud
Cebollas | cebolla; cebolla blanca; cebolla roja; cebolla dulce; cebolla morada; ceba; cebolas; tipula | kg
Ajos | ajo; allo; alls; all; baratxuri; cabeza de ajos | ud
Patatas | patata; patata lavada; patata roja; patata nueva; patates; patacas; patatak; patata monalisa; patata agria; patata kennebec | kg
Pimientos | pimiento; pimiento verde; pimiento rojo; pimiento amarillo; pimiento italiano; pimiento padron; padron; pebrots; pementos; piper | kg
Zanahorias | zanahoria; pastanaga; cenoria; azenarioak | kg
Pepino | pepinos; cogombre; cogombro | ud
Brócoli | brocoli; bròquil; brócolis; brokolia | ud
Champiñones | champinon; champinones; champi; xampinyons; champinons; portobello | kg
Calabacín | calabacin; calabacines; carabassó; cabazan; kalabazin; zucchini | kg
Berenjena | berenjenas; albergínia; berenxena; alberjinia | kg
Espinacas | espinaca; espinacs | ud
Peras | pera; pera conferencia; pera blanquilla; pera limonera; peres; pera de agua; pera rocha | kg
Melocotones | melocoton; melocoton rojo; melocoton amarillo; presseguer; pexego; melocoton calanda | kg
Sandía | sandia; sindria; sandia sin pepitas; sandia mini | ud
Melón | melon; meló; melon piel de sapo; melon galia; melon amarillo | ud
Piña | pina; pinya; pina natural; pina fresca | ud
Kiwis | kiwi; kiwi verde; kiwi amarillo; kiwi gold | kg
Coliflor | coliflores; romanesco | ud
Calabaza | calabazas; carabassa; cabaza; kalabaza; calabaza butternut | kg
Puerros | puerro; porro; porros | kg
Apio | apios; api; apio verde | ud
Mandarinas | mandarina; clementinas; clementina; satsumas; clemenules; mandarines; mandarinak | kg
Cerezas | cereza; cirera; cereixas; gerezi; picotas; cerezas picota | kg
Ciruelas | ciruela; pruna; ameixas; aranazak | kg
Higos | higo; figues; figos; pikuak; brevas | kg
Judías verdes | judia verde; judias verdes; judia verde plana; judias planas; mongetes; xudias | kg
Espárragos | esparrago; esparrago verde; esparragos verdes; esparragos blancos; esparragos trigueros | ud
Alcachofas | alcachofa; carxofes; carxofa | kg
Remolacha | remolachas; remolatxa; remolacha cocida | ud
Pomelo | pomelos; pomelo rosa; toronja; grapefruit | kg
Lima | limas; lima verde | kg
Nectarinas | nectarina; nectarina amarilla; nectarines | kg
Frambuesas | frambuesa; gerds; framboesas | ud
Moras | mora; mores; amoras | ud
Arándanos | arandano; arandanos; nabius; blueberries | ud
Albaricoques | albaricoque; albercoc | kg
Paraguayos | paraguayo; paraguaya; melocoton plano | kg
Canónigos | canonigos; canonigo | ud
Rúcula | rucula; arugula | ud
Cogollos de lechuga | cogollos; cogollos tudela; cogollo | ud
Ensalada | ensalada lavada; ensalada mezclada; ensalada variada; ensalada bolsa; ensalada lista; mezcla ensalada; ensalada 4 estaciones; ensalada baby | ud
Perejil | perejil fresco; julivert; perexil | ud
Jengibre | jengibre fresco; gingebre; ginger | kg
Boniato | boniatos; moniato; batata | kg
Mango | mangos; mango maduro | ud
Papaya | papayas | ud
Dátiles | datil; datiles medjool | ud
Setas variadas | setas; seta; seta ostra; shiitake; boletus; rovellons; niscalos | kg
Escarola | escarolas | ud
Endibias | endibia; endivias; endivia | ud
Repollo | repollos; col; col blanca; col lombarda; coles; col china; coles de bruselas | ud
Acelgas | acelga; bledas | ud
Cebolleta | cebolletas; cebolla tierna; ceba tendra | ud
Chalotas | chalota; escalonias | ud
Berros | berro | ud
Hinojo | hinojos; fenoll | ud
Nabo | nabos; nabiza; nap | ud
Rábanos | rabano; rabanitos; rabanet | ud
Granada | granadas; magrana; roma | kg
Frutas del bosque | frutos del bosque; frutos rojos frescos; frutas rojas; bayas | ud
Fruta variada | macedonia frutas; fruta cortada; fruta troceada; fruta de temporada | ud
Verdura variada | verduras variadas; menestra; menestra de verduras; sofrito verduras; verduras para sopa; verduras para paella | ud

== Carnes y Embutidos
Pechuga de pollo | pechuga; pechuga pollo; pechugas; pit de pollastre; peito de polo; oilasko bularra; filetes pechuga | kg
Muslos de pollo | muslo pollo; muslos; contramuslo; contramuslos; muslo y contramuslo; cuixes de pollastre; coxas de polo; jamoncitos pollo | kg
Alitas de pollo | alitas; alas de pollo; ales de pollastre | kg
Pollo entero | pollo; pollastre; polo; oilaskoa; pollo asado; pollo campero; pollo troceado | kg
Carne picada | picada; picada mixta; carne picada ternera; carne picada cerdo; carne picada vacuno; carn picada; carne moura | kg
Filetes de ternera | filete ternera; ternera; bistec; filetes de añojo; anojo; vedella; tenreira; filete vacuno; filetes vacuno; filete cadera; filetes aguja; entrecot; chuleton; carne guisar; ternera guisar | kg
Jamón cocido | jamon york; jamon de york; york; jambo cocido; pernil dolc; pernil cuit; xamon cocido; fiambre jamon; jamon cocido extra
Jamón serrano | serrano; pernil serra; xamon serrano; taquitos jamon; jamon curado; jamon reserva; jamon gran reserva
Jamón ibérico | iberico jamon; jamon iberico cebo; jamon bellota; jamon iberico bellota; paleta iberica; paleta bellota; pernil iberic; xamon iberico
Chorizo | choriz; chorizo iberico; chorizo extra; chorizo sarta; chorizo cular; chorizo picante; chorizo dulce; chorizo parrillero; chorizo fresco; chorizo cantimpalo; xoriço; txorizo; chourizo; chourizos
Salchichas | salchicha; salchichas frescas; salchichas pavo; salchichas pollo; salchichas cerdo; bratwurst; salchichas parrilleras; salchichas cocktail; salchichas coctel; salsitxes; salsichas; saltxitxak; hot dog; perritos | ud
Salchichas Frankfurt | frankfurt; frankfurts; salchichas viena; viena; vienesas; wiener | ud
Bacon | beicon; bacon lonchas; bacon ahumado; bacon taquitos; bacon cubos; bacó; bakoia | ud
Panceta | panceta fresca; panceta adobada; panceta curada; panceta lonchas; panceta cerdo | kg
Lomo de cerdo | lomo; lomo cerdo; lomo fresco; lomo fileteado; filetes lomo; filetes de lomo; llom; llom de porc; lombo; saihetsa | kg
Costillas | costilla; costillas cerdo; costilla cerdo; costillas adobadas; costillas bbq; costillas barbacoa; costillar; costella; costelas; saiheski | kg
Solomillo de cerdo | solomillo; solomillo cerdo; solomillo iberico; medallones solomillo; solomillo de porc | kg
Pavo en lonchas | pavo lonchas; pavo loncheado; fiambre pavo; fiambre de pavo; pechuga pavo; pechuga de pavo; pavo cocido; pavo asado; pavo natural; peito de peru | ud
Salchichón | salchichon iberico; salchichon extra; salchichon vic; salchichon lonchas; llonganissa; saltxitxoia | ud
Mortadela | mortadella; mortadela bologna; mortadela aceitunas; mortadela pistachos | ud
Fiambre | fiambre variado; fiambre mixto; fiambres; embutido variado; embutidos; charcuteria; surtido embutidos | ud
Pincho moruno | pinchos morunos; brocheta; brochetas; brochetas pollo; brochetas cerdo | kg
Hamburguesas de ternera | hamburguesa; hamburguesas; hamburguesa ternera; hamburguesa vacuno; hamburguesa mixta; hamburguesa cerdo; hamburguesa pollo; hamburguesa pavo; burger; burgers | ud
Albóndigas | albondiga; albondigas ternera; albondigas cerdo; albondigas pollo; albondigas mixtas; mandonguilles; albondegas; albondigak | kg
Morcilla | morcilla de burgos; morcilla burgos; morcilla arroz; morcilla cebolla; morcela; botifarra negra; odolkia | ud
Sobrasada | sobrassada; sobrasada mallorquina; sobrasada iberica | ud
Fuet | fuet extra; espetec; fuet vic; mini fuet | ud
Paté | pate; pate higado; pate cerdo; pate campo; pate la piara; mousse higado | ud
Foie | foie gras; foie pato; micuit; mousse foie; bloc de foie | ud
Conejo | conill; coello; untxia; conejo troceado | kg
Cordero | cordeiro; xai; ardi; cordero lechal; lechal; pierna cordero; paletilla cordero; chuletas cordero; chuletillas cordero; costillas cordero | kg
Cerdo | porc; porco; txerri; carne cerdo; carne de cerdo troceada; magro cerdo; magro; cinta lomo; secreto iberico; presa iberica; pluma iberica | kg
Chuletas de cerdo | chuletas cerdo; chuleta cerdo; chuletas lomo; chuletas de lomo; chuletas de aguja; chuletas aguja; chuletas cerdo adobadas | kg
Hígado | higado; higado ternera; higado pollo; higaditos; higado de cerdo | kg
Pavo | pavo troceado; pavo entero; muslo pavo; muslos de pavo; pechuga pavo fresca; filetes pavo; filetes de pavo | kg
Pato | pato entero; magret; magret de pato; confit de pato; muslo pato | kg
Jamón de pavo | jamon pavo; jamon de pavo lonchas | ud
Lacón | lacon; lacon cocido; lacon gallego | ud
Cecina | cecina leon; cecina de leon; cecina de vacuno | ud
Chistorra | chistorra pamplona; txistorra | ud
Butifarra | botifarra; botifarra fresca; butifarra fresca; botifarra cocida; botifarra blanca | ud
Longaniza | llonganissa fresca; longaniza fresca | ud

== Pescados y Mariscos
Salmón | salmon fresco; salmon noruego; salmon ahumado; salmon lomo; lomos salmon; filete salmon; salmon filete; salmon supremas; salmo; salmoia; izokina | kg
Merluza | merluza fresca; merluza filetes; filetes merluza; lomos merluza; merluza rodajas; merluza supremas; pescadilla; lluç; luzo; legatza | kg
Atún en lata | atun lata; atun aceite; atun claro; atun claro aceite; atun natural; atun escabeche; atun tomate; atun girasol; atun oliva; tonyina; bonito; bonito del norte; ventresca | ud
Atún fresco | atun rojo; lomo de atun; filete de atun; atun fresco | kg
Gambas | gamba; gambas cocidas; gambas peladas; gambas arroceras; gamba roja; gambones; gambes; camaron; camarones; ganbak | kg
Langostinos | langostino; langostinos cocidos; langostinos crudos; langostinos pelados; langostinos tigre; llagostins; otarrainxkak | kg
Mejillones | mejillon; mejillones frescos; mejillones cocidos; mejillones vapor; mejillones escabeche; mejillones al natural; musclos; mexillons; muskuiluak | kg
Pulpo | pulpo cocido; pulpo gallego; pulpo patas; patas de pulpo; pulpo a la gallega; polp; polbo; olagarroa | kg
Calamares | calamar; calamares anillas; anillas de calamar; calamares romana; calamars; luras; chipirones; chipiron; puntillitas; txipiroiak | kg
Sepia | sepias; sepieta; choco; chocos; choquitos; sepia limpia | kg
Bacalao | bacalao fresco; bacalao desalado; bacalao salado; bacalao lomos; lomos bacalao; bacalao migas; bacalla; bacallà; bakailaoa; bakailao | kg
Boquerones | boqueron; boquerones frescos; boquerones vinagre; boquerones aceite; anxoves; anchoves; antxoak; anchoa; anchoas | kg
Sardinas | sardina; sardinillas; sardinas frescas; sardines; sardiñas; sardina eskalean | kg
Dorada | doradas; dorada fresca; dorada limpia; orada; besugo | kg
Lubina | lubinas; llobarro; robaliza; lubina fresca | kg
Trucha | truchas; truita; troita; amuarraina | kg
Surimi | palitos de cangrejo; palitos cangrejo; palitos de surimi; delicias del mar; barritas surimi | ud
Almejas | almeja; ameixas; cloïsses; almejas chirlas; chirlas; coquinas | kg
Ostras | ostra; ostras frescas | ud
Cigalas | cigala; cigalas cocidas; cigalas frescas | kg
Pescado | pescado fresco; pescado blanco; filetes pescado; filetes de pescado; peix; peixe; arraina | kg
Pescado congelado
Merluza congelada | filetes merluza congelada; merluza cong | kg
Palitos de pescado
Empanadillas de atún | empanadilla atun; empanadillas atun; empanadillas de atun | ud
Pescado ahumado | ahumados; salmon ahumado lonchas; trucha ahumada; bacalao ahumado; ahumado | ud
Huevas | huevas de merluza; huevas de pescado; hueva; huevas de salmon | ud
Caviar | caviar de lumpo; caviar lumpo; sucedaneo caviar | ud
"""
