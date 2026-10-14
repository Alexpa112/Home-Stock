"""Ampliacion (ronda 2): articulos que los tickets traen con nombre de marca o
truncados y que no estaban. Mismo formato que datos_articulos_a.py."""
TEXTO = """
== Snacks y Dulces
Donuts | donut ; dónut ; bollo glaseado | ud
Ganchitos | ganchito ; kikos ; gusanitos ; palomitas maiz | ud
Crema de cacao con avellanas | nutella ; nocilla ; nusi ; crema avellanas ; cacaoyas | ud
Galletas rellenas de chocolate | oreo ; filipinos ; tosta rica ; chips ahoy ; principe ; fontaneda | ud
Bombones | lacasitos ; kinder bueno ; kinder ; ferrero ; mon cheri ; conguitos | ud
Mousse | mousse chocolate ; mousse limon | ud
Tarta de queso | cheesecake ; tarta queso | ud
Tarta | pastel ; tarta chocolate ; tarta manzana ; tarta whisky | ud
== Bebidas
Cacao soluble | cola cao ; colacao ; nesquik ; nestle cacao ; cacao polvo | ud
Bebida energética | red bull ; monster ; burn ; energy drink ; bebida energetica | ud
Bebida isotónica | aquarius ; powerade ; gatorade ; isotonica | ud
Té helado | nestea ; fuze tea ; te frio ; ice tea | ud
Refresco de naranja | fanta naranja ; fanta ; refresco naranja | ud
Refresco de limón | sprite ; 7up ; seven up ; limonada gas ; refresco limon | ud
Refresco de cola | pepsi ; coca cola ; cocacola ; cola | ud
Bitter sin alcohol | bitter kas ; kas ; kas limon ; kas naranja | ud
Cápsulas de café | capsulas dolce gusto ; capsulas nespresso ; capsulas senseo ; capsulas tassimo ; cafe capsulas | ud
Café en cápsulas compatibles | capsulas compatibles ; capsulas cafe compatibles | ud
Cerveza sin alcohol | cerveza 0,0 ; cerveza 00 ; cerveza sin ; 0,0 cerveza | ud
== Lácteos y Huevos
Queso crema | philadelphia ; queso untar ; queso para untar ; queso crema untable | ud
Queso en porciones | la vaca que rie ; la vaca que ríe ; babybel ; quesitos ; el caserio ; porciones queso | ud
Yogur bebible | actimel ; yogur liquido ; yogur liq ; yakult ; l casei ; bifidus liquido | ud
Yogur de sabores | danone ; yoghourt ; yogures sabores ; yogur fresa ; yogur limon ; yogur coco ; yogur macedonia | ud
Yogur griego | yoghourt griego ; yogur griego natural ; griego | ud
== Carnes y Embutidos
Rabo de toro | rabo ; rabo toro ; rabo ternera | ud
Callos | callos cocidos ; callos madrileña ; callos lata | ud
Codorniz | codornices ; codorniz limpia | ud
Carne de buey | buey ; chuleton buey ; entrecot buey | ud
Chuletas | chuletas cerdo ; chuletas cordero ; chuletas ternera ; chuleta | ud
Hígado | higado ternera ; higado cerdo ; higado pollo | ud
== Pescados y Mariscos
Palitos de surimi | palitos surimi ; surimi ; palitos cangrejo ; barritas surimi | ud
Gulas | gulas del norte ; gula ; anguriñas ; angulas | ud
Pescadilla | filete pescadilla ; pescadilla rodajas ; pescadilla fresca ; pescadilla cong | ud
Anchoas en aceite | anchoas ; anchoas aceite ; anchoas aceite oliva ; filetes anchoa ; anchoa | ud
== Frutas y Verduras
Papas arrugadas | papas ; papas canarias ; papas negras ; patatas arrugadas ; papas arrugadas | ud
Cilantro | cilantro fresco ; culantro ; coriandro | ud
Borraja | borraja bolsa ; borraja fresca | ud
Edamame | edamame congelado ; soja verde ; edamames | ud
== Cereales y Pasta
Bulgur | bulgur cocido ; bulgur integral ; trigo bulgur | ud
== Panadería y Bollería
Tostadas | tostadas integrales ; tostadas pan ; pan tostado ; tostadas finas ; biscotes ; biscottes | ud
Rosquilletas | rosquilleta ; rosquilletas pan ; rosquillas pan | ud
== Congelados
Patatas prefritas | patatas prefritas ; patatas fritas congeladas ; patatas bastones ; patatas gajo ; patatas horno congeladas | ud
== Despensa
Vinagre balsámico | aceto ; aceto balsamico ; vinagre modena ; balsamico ; vinagre balsamico modena | ud
Tzatziki | salsa tzatziki ; tzaziki ; salsa yogur pepino | ud
Arroz largo | arroz grano largo ; arroz largo ; arroz basmati ; arroz thai ; arroz jazmin | ud
Papel de horno | papel horno ; papel vegetal ; papel sulfurizado ; papel cocina horno | ud
== Alternativas Vegetales
Bebida de almendras | bebida almendra ; leche almendra vegetal ; bebida almendras ; almendra drink ; bebida de almendra | ud
Bebida de soja | bebida soja ; leche soja vegetal ; soja drink ; bebida soja calcio | ud
Bebida de arroz | bebida arroz ; leche arroz vegetal ; rice drink | ud
Bebida de coco | bebida coco ; leche coco vegetal | ud
== Limpieza
Abrillantador | abrillantador lavavajillas ; abrillantador vajilla ; finish abrillantador ; rinse aid | ud
Fregaplatos | fregaplatos ; lavaplatos mano ; lavavajillas mano ; fairy ; quix | ud
Sal para lavavajillas | sal lavavajillas ; sal regeneradora ; sal lavavaj | ud
Limpiahogar | limpia hogar ; limpiador multiusos ; multiusos ; limpiador multiuso ; limpiadora | ud
Amoníaco | amoniaco ; amoniaco perfumado | ud
Bolsas de congelación | bolsas congelar ; bolsas congelacion ; bolsas congelador ; bolsa congelar ; bolsas zip | ud
Tapers | taper ; tuppers ; tupper ; recipientes ; fiambreras ; recipiente hermetico | ud
Esponjas | esponja ; esponja fibra ; esponja vegetal ; esponjas cocina ; esponja salvauñas | ud
Jabón para lavadora | jabon lavadora ; jabon ropa ; jabon liquido ropa ; jabon marsella ; jabon en escamas | ud
Pinzas de la ropa | pinzas ; pinzas ropa ; pinzas madera ; pinzas tendedero | ud
== Higiene
Talco | polvos talco ; talco bebe ; talco pies | ud
Sérum facial | serum ; sérum ; serum facial ; serum vitamina c ; serum antiarrugas | ud
Cera depilatoria | depilatoria ; cera ; cera fria ; bandas depilatorias ; crema depilatoria | ud
== Farmacia y Botiquín
Aspirina | aspirina ; ácido acetilsalicílico ; acido acetilsalicilico ; aspirina c | ud
Alcohol | alcohol 96 ; alcohol sanitario ; alcohol isopropilico ; alcohol desinfectante | ud
== Mascotas
Rascador para gatos | rascador ; rascador gato ; poste rascador | ud
== Hogar
Pilas | pilas ; pilas alcalinas ; pila ; pila alcalina ; pilas boton | ud
"""
