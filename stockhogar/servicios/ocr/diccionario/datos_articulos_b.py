"""Catalogo ampliado (parte B): despensa, cereales y pasta, panaderia, snacks,
congelados. Mismo formato que la parte A (solo sinonimos y nombres parciales)."""

TEXTO = """
== Despensa
Aceite de oliva | aceite oliva; aceite oliva virgen; aceite virgen extra; aove; oli d oliva; aceite suave; aceite intenso | l
Aceite de girasol | aceite girasol; aceite alto oleico | l
Arroz | arros; arroz redondo; arroz largo; arroz basmati; arroz vaporizado; arroz jazmin; arroz sos | kg
Arroz bomba | arroz paella; arroz calasparra | kg
Arroz preparado [Sobre] | arroz microondas; arroz cocido; arroz vapor; arroz tres delicias | ud
Lentejas | llenties; lentilhas; dilistak; lentejas pardinas; lentejas cocidas | kg
Garbanzos | cigrons; grao; garbanzos cocidos; garbanzo | kg
Alubias | fabes; fabada; alubia; alubias blancas; alubias pintas; fesols; fasoias; babarrunak | kg
Tomate frito | tomate frit; salsa tomate; tomate frito casero | ud
Tomate triturado | tomate pelado; tomate troceado; tomate natural triturado; tomate entero pelado | ud
Pasta de tomate | concentrado de tomate; tomate concentrado | ud
Sal | sal fina; sal gorda; sal marina; sal yodada; sal gruesa; sal de mesa | kg
Azúcar | azucar; sucre; azucre; azukrea; azucar blanco; azucar blanquilla; azucar moreno; azucar glas | kg
Harina | farina; fariña; irina; harina de trigo; harina de fuerza; harina de maiz; harina reposteria | kg
Miel | mel; miel de flores; miel milflores; miel de azahar; miel de romero | ud
Vinagre | vinagre de vino; vinagre de manzana; vinagre blanco; vinagre de jerez | l
Vinagre balsámico | vinagre balsamico; balsamico; crema balsamica | ud
Mayonesa | maionesa; mahonesa; mayonesa light | ud
Ketchup | catsup; salsa ketchup | ud
Mostaza | mostassa; mostaza antigua; mostaza dijon | ud
Alioli | allioli; salsa alioli; ajoaceite | ud
Salsa de soja | salsa soja; salsa de soya; shoyu | ud
Salsa barbacoa | salsa bbq; bbq | ud
Salsa pesto | pesto; salsa de pesto | ud
Salsa picante | tabasco; sriracha; salsa guindilla | ud
Caldo en pastillas | pastillas de caldo; cubitos de caldo; avecrem | ud
Caldo de pollo (brick) | caldo de pollo; caldo pollo | ud
Caldo de verduras (brick) | caldo de verduras; caldo vegetal | ud
Caldo de carne | caldo de ternera; caldo de cocido | ud
Caldo de pescado | fumet; caldo pescado | ud
Sopa de sobre | sopa instantanea; sopa de fideos; sopa de pollo; sopa de verduras; sopa juliana | ud
Crema de verduras | crema verduras; crema de calabacin; crema de calabaza; crema de puerros; crema de champinones | ud
Gazpacho | gaspacho; salmorejo | ud
Mermelada | melmelada; marmelada; mermelada fresa; mermelada melocoton; mermelada albaricoque; mermelada naranja; confitura | ud
Crema de cacao para untar | nutella; crema cacao; crema de cacao; nocilla; crema de avellanas | ud
Mantequilla de cacahuete | crema cacahuete; crema de cacahuete; peanut butter | ud
Cacao en polvo | cacao soluble; colacao; cola cao; nesquik; cacao puro | kg
Pimienta negra | pimienta; pimienta molida; pimienta en grano; pimienta blanca | ud
Especias variadas | especias; condimentos; sazonador; mezcla especias; colorante; curry; comino | ud
Orégano | oregano; oregano seco | ud
Pimentón | pimenton; pimenton dulce; pimenton picante; pimenton de la vera; paprika | ud
Canela en polvo | canela; canela molida; canela en rama; canella | ud
Levadura | levadura quimica; levadura panadera; levadura fresca; llevat | ud
Gelatina | gelatina neutra; gelatina de fresa; cola de pescado; gelatina en polvo | ud
Maíz en lata | maiz dulce; maiz; maiz lata; maiz en conserva; blat de moro | ud
Aceitunas | olivas; olives; azeitonas; olibak; aceitunas verdes; aceitunas negras; aceitunas manzanilla; aceitunas sin hueso; aceitunas deshuesadas | ud
Aceitunas rellenas | olivas rellenas; olives farcides; aceitunas rellenas anchoa | ud
Pepinillos | pepinillo; cornichons; encurtidos; banderillas | ud
Anchoas en lata | anchoas lata; anchoas cantabrico; filetes de anchoa; anchoas santoña | ud
Sardinillas en lata | sardinillas; sardinas lata; sardinas en aceite; sardinas escabeche | ud
Caballa en lata | caballa lata; caballa aceite; filetes de caballa; caballa natural; verdel | ud
Berberechos en lata | berberechos; berberecho; berberechos al natural | ud
Mejillones en lata | mejillones lata; mejillones escabeche lata; mejillones en escabeche | ud
Pimientos asados en conserva | pimientos asados; pimientos del piquillo; piquillos | ud
Espárragos en conserva | esparragos lata; esparragos blancos lata; esparragos blancos | ud
Piña en almíbar | pina almibar; pina lata; pina en rodajas | ud
Melocotón en almíbar | melocoton almibar; melocoton lata; melocoton en mitades | ud
Frutos secos | fruta seca; mezcla frutos secos; frutos secos naturales; fruits secs; frutos secos tostados | kg
Almendras | almendra; ametlles; amendoas; almendras crudas; almendras tostadas; almendras marcona; almendras laminadas; almendra molida | kg
Nueces | nuez; nous; noces; intxaurrak; nueces peladas; nueces california | kg
Cacahuetes | cacahuete; cacauets; cacahuetes fritos; cacahuetes tostados; cacahuetes salados | kg
Pipas de girasol | pipas; pipas girasol; pipas con sal; pipas sin sal; pipas peladas | ud
Pistachos | pistacho; pistachos tostados; pistachos salados; pistachos pelados | kg
Anacardos | anacardo; anacards; anacardos fritos; anacardos tostados | kg
Avellanas | avellana; avellanes; avellanas tostadas; avellanas peladas | kg
Pasas | pasa; panses; pasas sultanas; pasas de corinto; uvas pasas | kg
Semillas de chía | chia; semillas chia; chia semillas | ud
Semillas de lino | lino; semillas lino; linaza | ud
Edulcorante | sacarina; stevia; sucralosa; edulcorante liquido | ud
Hummus | humus; hummus clasico; hummus garbanzos | ud
Guacamole envasado | guacamole; guacamole fresco | ud
Pan rallado | pa ratllat; pan rallao; panko; rebozador | ud
Tapioca | tapioca perlas; perlas de tapioca | kg
Pan tostado | pan tostado rebanadas; rebanadas de pan tostado; biscotes; biscote; torradas; torrades | ud
Conserva de verduras | verduras en conserva; menestra lata; menestra conserva; alcachofas lata; alcachofas en conserva; champinones lata; champinones en conserva; setas lata | ud
Atún en lata | atun lata; atun claro; atun aceite; atun natural; atun escabeche; tonyina; bonito del norte; ventresca | ud
Legumbres cocidas | legumbres cocidas; lentejas cocidas bote; garbanzos cocidos bote; alubias cocidas bote | ud
Fabada | fabada asturiana; fabada lata; fabes con almejas | ud
Cocido | cocido madrileño; cocido lata; cocido en lata; potaje | ud
Platos preparados | plato preparado; plato cocinado; platos cocinados; comida preparada; menu del dia; menu | ud
Pizza fresca | pizza refrigerada; pizza fresca jamon queso; masa pizza fresca | ud
Masa de pizza | masa pizza; base de pizza; base pizza; masa para pizza | ud
Tortilla de patatas | tortilla patata; tortilla patatas; tortilla española; tortilla con cebolla; tortilla sin cebolla; truita de patates | ud
Ensaladilla | ensaladilla rusa; ensaladilla de atun; amanida russa | ud
Salsa de tomate | salsa tomate natural; tomate con albahaca; salsa napolitana; salsa boloñesa; salsa bolonesa; salsa carbonara | ud
Salsa César | salsa cesar; cesar | ud
Salsa de queso | salsa queso; salsa 4 quesos; salsa cuatro quesos | ud
Bechamel | besamel; salsa bechamel; salsa besamel | ud
Pimiento morrón | pimiento morron; morrones; pimiento rojo conserva | ud
Alcaparras | alcaparra; alcaparrones; capers | ud
Coco rallado | coco en polvo; coco seco | ud
Chocolate para postres | chocolate fondant; chocolate de cobertura; cobertura chocolate; pepitas de chocolate; chips de chocolate | ud
Azúcar glas | azucar glass; azucar lustre; azucar de lustre | kg
Natillas en polvo | flan en polvo; preparado flan; preparado natillas; cuajada en polvo | ud
Bicarbonato | bicarbonato sodico; bicarbonato de sodio | ud
Maizena | harina de maiz maizena; almidon de maiz; fecula de maiz; fecula | ud
Pan de higo | pan de higos; turron de higo | ud

== Cereales y Pasta
Espaguetis | espagueti; spaghetti; espaguetis integrales; espaguetis n5 | ud
Macarrones | macarron; macarrons; macaroni; penne; plumas; fusilli; tirabuzones; rigatoni; codos | ud
Fideos | fideo; fideus; fideos finos; fideos gruesos; fideos cabello de angel; fideua; noodles | ud
Pasta | pasta seca; pasta italiana; pasta fresca; pasta rellena; tallarines; tagliatelle; raviolis; tortellini; gnocchi; noquis | ud
Lasaña (placas) | lasaña; lasana; placas lasaña; placas de lasaña; lasaña precocida | ud
Canelones (placas) | canelon; placas canelones; canelones precocidos; canelons | ud
Cereales de desayuno | cereales; cereals; cereais; cereales choco; cereales chocolate; cereales miel; cereales frutas; chocapic; corn flakes; special k; cereales integrales; cereales avena; copos de maiz | ud
Copos de avena | avena; copos avena; avena integral; avena molida; porridge | kg
Galletas | galeta; galetes; galletas maria; galletas de mantequilla; galletas chocolate; galletas rellenas; galletas oreo; oreo; cookies; galletas digestive; galletas integrales; galletas saladas; crackers; galletas surtidas; principe | ud
Muesli | muesli crujiente; muesli frutas; granola; granola avena | ud
Tostadas | torradas; torrades; tostadas redondas; tostadas integrales; biscotes; pan tostado | ud
Cuscús | cuscus; cous cous; couscous | ud
Quinoa | quinua; quinoa real; quinoa cocida | ud
Pasta integral | espaguetis integrales; macarrones integrales | ud
Pasta sin gluten | espaguetis sin gluten; macarrones sin gluten | ud
Sémola | semola; semola de trigo | kg
Arroz con verduras | arroz tres delicias; arroz cantones | ud

== Panadería y Bollería
Pan de barra | pan barra; barra de pan; barra; barra cristal; pan cristal; pan rustico; pan de pueblo; pan payes; pan gallego; hogaza; pan candeal; baguette; barra baguette; chapata; pistola; viena; pa; pa de pages; ogia | ud
Pan de molde | pa de motlle; pan molde; pan molde blanco; pan sin corteza; pan molde integral; pan molde cereales; pan sandwich; pan bimbo; sandwich | ud
Pan integral | pa integral; pan integral rebanado; pan integral molde; pan integral semillas; pan 100 integral | ud
Pan de hamburguesa | pan hamburguesa; panecillos hamburguesa; pan burger; bollos hamburguesa; pan brioche hamburguesa; pan para hamburguesas | ud
Pan de perritos | pan perritos; pan hot dog; panecillos hot dog; bollos perritos | ud
Pan rallado | pa ratllat | ud
Croissants | croissant; cruasan; cruasanes; croissants mantequilla; croissants chocolate; croissants rellenos; mini croissants | ud
Magdalenas | magdalena; magdalenas caseras; magdalenas artesanas; magdalenas naranja; magdalenas limon; magdalenas chocolate; magdalenas con pepitas; magdalenas cuadradas | ud
Bollos de leche | bollo de leche; bollitos de leche; bollos suaves; panecillos de leche; pan de leche; brioche; bollos brioche; panecillos brioche | ud
Donuts | donut; donuts glaseados; donuts chocolate; donuts rellenos; donettes; rosquillas | ud
Bizcocho | bizcocho casero; bizcocho de yogur; bizcocho limon; bizcocho naranja; bizcocho chocolate; bizcocho marmolado; plum cake; plumcake; soletillas; bizcochos soletilla | ud
Palmeras de chocolate | palmera; palmeras; palmeras chocolate; palmeras de hojaldre; palmeritas | ud
Napolitanas de chocolate | napolitana; napolitanas; napolitana chocolate; napolitana crema; napolitana de crema; napolitana de chocolate | ud
Ensaimada | ensaimadas; ensaimada mallorquina; ensaimada cabello de angel; ensaimada crema | ud
Tortillas de trigo | tortilla trigo; tortillas de harina; wraps; wrap; fajitas; tortillas fajitas; tortillas tacos; tortillas de maiz | ud
Pan de pita | pan pita; pita; pan arabe; pan de kebab; pan naan; naan | ud
Colines | colin; grissini; regañás; picos; picos de pan; picos camperos; colines de pan | ud
Tortitas | tortita; tortitas de arroz; tortitas de maiz; tortitas arroz; tortitas avena | ud
Empanadillas | empanadilla; empanadillas de atun; empanadillas de carne; empanadillas jamon y queso; empanadillas verduras | ud
Pan sin gluten | pan sin gluten molde; pan de molde sin gluten; barra sin gluten | ud
Pan de centeno | pan centeno; pan de espelta; pan espelta; pan de cereales; pan multicereales; pan semillas | ud
Bollería | bolleria; bollos; bollycao; bollicao; bollitos; pasteles; pastel; pastelitos; pastelito; pasteleria; dulces | ud
Churros | churro; porras; porra; masa churros; churros congelados | ud
Pan tostado de ajo | pan de ajo; pan ajo; baguette de ajo; pan con ajo | ud
Pan de pasas | pan pasas; pan de nueces; pan nueces; pan con nueces; pan con pasas | ud
Rosca | roscon de reyes; roscon; tortell; rosca de reyes | ud
Tarta | tarta de queso; tarta chocolate; tarta de manzana; tarta fresca; tarta helada; pastel de queso; tarta santiago; tarta de santiago | ud
Crepes | crepe; crepes rellenos; creps; creps rellenos | ud
Gofres | gofre; gofres rellenos; waffles; waffle | ud
Brownie | brownies; brownie chocolate; brownies chocolate | ud
Cookies | cookie; cookies chocolate; cookies chips; cookies artesanas | ud
Pastas de té | pastas te; pastas de te; pastas surtidas; pastas de mantequilla; pastas secas; pastas | ud
Mantecados | mantecado; polvorones; polvoron; mantecados polvorones; turrones; turron | ud

== Snacks y Dulces
Patatas fritas | patatas fritas bolsa; patatas fritas lisas; patatas fritas onduladas; patatas fritas churreria; patatas chips; chips; patatatas fritas sal; patates fregides; patacas fritas; lays; pringles; ruffles | ud
Palomitas | palomitas maiz; palomitas de maiz; palomitas microondas; crispetes; pipoca; krispetak | ud
Chocolate | chocolate con leche; chocolate negro; chocolate blanco; chocolate almendras; chocolate avellanas; tableta chocolate; chocolate a la taza; xocolata; txokolatea; chocolate fondant; chocolate 70 | ud
Frutos secos | frutos secos | ud
Caramelos | caramel; caramelos blandos; caramelos duros; caramelos masticables; caramelos de menta; caramelos de fresa; caramelos eucalipto; caramelos sin azucar | ud
Gominolas | gominola; gominolas azucar; golosinas; chuches; chuche; haribo; ositos de goma; ositos gominola; nubes; nubes de azucar; chucherias | ud
Barritas de cereales | barrita cereales; barritas cereales; barrita de cereales; barritas de chocolate; barritas energeticas; barrita energetica; barritas proteicas; barrita proteica; barritas de frutas | ud
Turrón | turron blando; turron duro; turron de jijona; turron jijona; turron de alicante; turron alicante; turron de chocolate; turron chocolate; turron de yema; turron yema; turron de coco; turron coco; turrones | ud
Nachos | nacho; nachos queso; nachos con queso; totopos; tortilla chips; doritos; nachos picantes | ud
Gusanitos | gusanito; gusanitos maiz; snacks maiz; kikos; kiko; kikos maiz; palomitas gusanitos; maiz frito | ud
Regaliz | regalitz; regaliz rojo; regaliz negro; regaliz natural; palo de regaliz; palos regaliz | ud
Chocolatinas variadas | chocolatina; chocolatinas; barrita chocolate; kit kat; kitkat; snickers; mars; twix; bounty; lion; kinder bueno; kinder; milka; tobleron; toblerone; ferrero rocher; ferrero; bombones ferrero | ud
Chicles | chicle; chiclets; trident; orbit; mentos; chicle sin azucar; chicles sin azucar; chicles menta | ud
Piruletas | piruleta; chupa chups; chupachups; piruletas variadas; lollipop | ud
Bombones | bombon; bombones de chocolate; bombones surtidos; caja bombones; caja de bombones; surtido bombones; ferrero rocher | ud
Barquillos | barquillo; barquillos chocolate; barquillos rellenos; barquillos de chocolate; wafers; waffer; barquillos vainilla; barquillo relleno | ud
Palmeritas de hojaldre | palmeritas; palmeritas hojaldre; palmeritas chocolate | ud
Cortezas de cerdo | cortezas; cortezas cerdo; chicharrones; torreznos; torreznos de soria; torreznos soria | ud
Snacks de queso | snack queso; snacks queso; palitos queso; palitos de queso; quesitos snack; palitos de pan queso | ud
Helado | gelat; xeado; izozkia; helado vainilla; helado chocolate; helado fresa; helado de vainilla; helado de chocolate; helado cucurucho; helado tarrina; tarrina helado; helados; cono; conos; helado palo; helado bombon; helado sandwich; helado nata; helado turron; helado de turron; helado mantecado | ud
Cacahuetes | cacahuetes fritos; cacahuetes salados | ud
Palitos | palitos de pan; palitos sal; palitos salados; palitos de sal; picos sal | ud
Aperitivos | aperitivo; aperitivos variados; snacks; snack; mix aperitivos; surtido aperitivos; piscolabis; pica pica; cocktail aperitivos | ud
Dulce de membrillo | membrillo; carne de membrillo; dulce membrillo; dulce de batata; dulce de leche | ud
Cola de pescado | gelatina hojas; gelatina en hojas; cola pescado | ud
Sirope | sirope de arce; sirope arce; sirope de agave; sirope agave; sirope chocolate; sirope caramelo; sirope fresa; jarabe de arce; miel de arce | ud
Cacao crema | crema de cacao untar; crema de chocolate | ud
Caramelos de goma | caramelos goma; gominolas fruta; gominolas fruta; gominolas acidas; gominolas azucaradas; gominolas sin azucar; gominolas ositos | ud
Fruta deshidratada | fruta desecada; frutas deshidratadas; orejones; orejones albaricoque; ciruelas pasas; ciruela pasa; datiles; higos secos; arandanos secos; arandanos deshidratados; mango deshidratado; coco deshidratado; platano chips; chips platano; chips de platano; manzana deshidratada; manzana chips; chips de manzana | ud
Snack saludable | snack saludable; snack proteico; snack proteina; barrita proteina; snack fruta; snack de frutas; snack de verduras; snack verduras; chips de verduras; chips verduras; chips de remolacha; chips remolacha; chips de zanahoria; chips zanahoria; chips de boniato; chips boniato; chips de kale; chips kale; chips de garbanzos; chips garbanzos; chips de lentejas; chips lentejas; chips de legumbres; chips legumbres | ud

== Congelados
Guisantes congelados | guisantes; guisantes finos; pisum; guisants; ilarrak; guisantes cong | kg
Verdura congelada | verduras congeladas; verdura cong; menestra congelada; salteado verduras; salteado de verduras; brocoli congelado; coliflor congelada; espinacas congeladas; judias verdes congeladas; habas congeladas; zanahoria congelada; espinacas cong | kg
Pizza congelada | pizza; pizzas; pizza cong; pizza jamon y queso; pizza margarita; pizza margherita; pizza 4 quesos; pizza cuatro quesos; pizza barbacoa; pizza atun; pizza prosciutto; pizza pepperoni; pizza vegetal; pizza masa fina; pizza hornear; pizza horno piedra; pizza familiar; mini pizzas; pizzeta; pizzetas; pizza salchichas | ud
Croquetas congeladas | croquetas; croquetas jamon; croquetas de jamon; croquetas pollo; croquetas de pollo; croquetas bacalao; croquetas de bacalao; croquetas cocido; croquetas de cocido; croquetas queso; croquetas de queso; croquetas setas; croquetas de setas; croquetas espinacas; croquetas de espinacas; croquetas gambas; croquetas de gambas; croquetas surtidas; croquetes | ud
Patatas fritas congeladas | patatas congeladas; patatas fritas cong; patatas bastoncillo; patatas 2 5 mm; patatas para freir congeladas; patatas gajo; patatas gajos; patatas especiales; patatas horno; patatas bravas; patatas crinkle; patatas rejilla; patatas noisette; patatas pay | kg
Palitos de pescado | palitos merluza; palitos de merluza; palitos pescado; barritas pescado; barritas de pescado; fish sticks; palitos empanados; palitos de pescado empanados | ud
Rebozados congelados | rebozados; rebozados pescado; rebozados pollo; aros de cebolla; aros cebolla; anillas de cebolla; nuggets verduras; nuggets queso; sticks queso; sticks de queso; bocaditos queso; bocaditos de queso | ud
Empanadillas congeladas | empanadillas cong; empanadillas atun congeladas; empanadillas carne congeladas; empanadillas para freir; empanadillas freir; empanadillas hornear; mini empanadillas; empanadillas surtidas | ud
Gambas congeladas | gambas cong; gambas peladas congeladas; gambas cocidas congeladas; gambon congelado; gambones congelados; gambas arrocera congeladas; gambas rebozadas congeladas | kg
Masa de hojaldre | hojaldre; masa hojaldre; hojaldre fresco; masa de hojaldre refrigerada; hojaldre rectangular; hojaldre redondo; hojaldre mantequilla; hojaldre de mantequilla; masa quebrada; masa brisa; masa de empanada; masa empanada; masa de empanadillas; masa empanadillas; obleas empanadillas; discos empanadillas; discos de empanadillas; masa filo; pasta filo; pasta brick; hojas brick | ud
Langostinos congelados | langostinos cong; langostinos crudos congelados; langostinos cocidos congelados; langostinos pelados congelados; colas langostino congeladas | kg
Tarta helada | tarta de helado; tarta helado; tarta de helado congelada; tarta whisky; tarta de whisky; tarta tres chocolates; tarta 3 chocolates; tarta de tres chocolates; tarta de 3 chocolates; tarta fresa; tarta de fresa; tarta limon; tarta de limon; tarta mouse; tarta de mousse | ud
Filetes de pescado congelado | filetes pescado congelado; filetes de pescado cong; filetes merluza congelada; merluza congelada; merluza cong; bacalao congelado; bacalao cong; salmon congelado; salmon cong; lenguado congelado; lenguado cong; abadejo; abadejo congelado; pescadilla congelada; pescadilla cong; panga; panga congelado; basa; filete basa; tilapia; filete tilapia | kg
Marisco congelado variado | marisco congelado; marisco cong; mariscada; mariscada congelada; mezcla marisco; mezcla de marisco; cocktail marisco; cocktail de marisco; paella marisco; surtido marisco; surtido de marisco; marisco surtido; marisco variado | kg
Alitas de pollo congeladas | alitas pollo congeladas; alitas cong; alitas adobadas congeladas; alitas pollo cong | kg
Nuggets de pollo | nuggets; nugget; nuggets pollo; nuggets de pollo; nuggets pavo; nuggets de pavo; nuggets crujientes; nuggets rebozados; nuggets empanados; nuggets cong; nuggets congelados; fingers pollo; fingers de pollo; tiras pollo empanadas; tiras de pollo empanadas; tiras de pollo rebozadas; tiras pollo rebozadas; crujientes pollo; crujientes de pollo; strips pollo; strips de pollo | ud
Hamburguesas congeladas | hamburguesas cong; hamburguesas ternera congeladas; hamburguesas pollo congeladas; hamburguesas vacuno congeladas; hamburguesas mixtas congeladas | ud
Polos de hielo | polos; polo; polo hielo; polos hielo; helado polo; helados polo; polos fresa; polos limon; polos de fresa; polos de limon; polos frutas; polos de frutas; polos naranja; polos de naranja; polos cola; polos de cola | ud
Frutos rojos congelados | frutos rojos cong; frutas del bosque congeladas; frutos del bosque congelados; frutos del bosque cong; fresas congeladas; fresas cong; frambuesas congeladas; frambuesas cong; arandanos congelados; arandanos cong; moras congeladas; moras cong; mango congelado; mango cong; pina congelada; pina cong; platano congelado; platano cong; fruta congelada; fruta cong; fruta tropical congelada; fruta tropical cong; mezcla frutas congeladas; mezcla frutas cong; mezcla de frutas congeladas; mezcla de frutas cong | kg
Sepia congelada | sepia cong; choco congelado; choco cong; chipirones congelados; chipirones cong; calamares congelados; calamares cong; anillas calamar congeladas; anillas de calamar congeladas; anillas calamar cong; anillas de calamar cong; pulpo congelado; pulpo cong; patas de pulpo congeladas; patas pulpo congeladas; patas de pulpo cong; patas pulpo cong | kg
Lasaña congelada | lasana congelada; lasaña cong; lasana cong; lasaña carne congelada; lasaña de carne congelada; lasaña verduras congelada; lasaña de verduras congelada; canelones congelados; canelones cong; canelones carne congelados; canelones de carne congelados | ud
Platos congelados | plato congelado; platos cong; plato cong; paella congelada; paella cong; arroz congelado; arroz cong; arroz tres delicias congelado; arroz tres delicias cong; tortilla congelada; tortilla cong; tortilla de patatas congelada; tortilla patatas congelada; tortilla de patatas cong; tortilla patatas cong; huevos rotos congelados; huevos rotos cong; patatas huevos; croquetas jamon congeladas; croquetas jamon cong; calamares romana congelados; calamares romana cong; ensaladilla congelada; ensaladilla cong | ud
Pan congelado | pan cong; pan congelado; barras congeladas; barras cong; baguettes congeladas; baguettes cong; bollos congelados; bollos cong; bollería congelada; bolleria congelada; bolleria cong; croissants congelados; croissants cong; masa congelada; masa cong; pan precocido; pan precocido congelado; pan precocido cong; barras precocidas; barras precocidas congeladas; barras precocidas cong; baguettes precocidas; baguettes precocidas congeladas; baguettes precocidas cong | ud
Hielo | hielo cubitos; cubitos de hielo; cubitos hielo; bolsa hielo; bolsa de hielo; hielo picado; hielo en cubitos; hielo en cubos; hielo cubos | ud
"""
