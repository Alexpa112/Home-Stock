"""
Traductor propio español -> gallego para nombres/descripciones de producto.

Argos Translate no distribuye modelo neuronal para gallego, así que aquí
mantenemos nuestro propio diccionario de términos de supermercado y hogar.
Traduce por coincidencia exacta de la frase completa o palabra a palabra.
"""

DICCIONARIO_ES_GL = {
    # Lácteos y huevos
    "leche": "Leite", "queso": "Queixo", "mantequilla": "Manteiga",
    "yogur": "Iogur", "nata": "Nata", "huevo": "Ovo", "huevos": "Ovos",

    # Carnes y pescados
    "carne": "Carne", "pollo": "Polo", "pescado": "Peixe", "jamón": "Xamón",
    "chorizo": "Chourizo", "salchicha": "Salchicha", "salchichas": "Salchichas",
    "ternera": "Tenreira", "cerdo": "Porco", "cordero": "Año",
    "atún": "Atún", "merluza": "Pescada", "gamba": "Gamba", "gambas": "Gambas",
    "mejillón": "Mexillón", "mejillones": "Mexillóns", "pulpo": "Polbo",

    # Frutas y verduras
    "fruta": "Froita", "verdura": "Verdura", "manzana": "Mazá",
    "naranja": "Laranxa", "plátano": "Plátano", "pera": "Pera",
    "uva": "Uva", "uvas": "Uvas", "limón": "Limón", "fresa": "Amorodo",
    "fresas": "Amorodos", "melón": "Melón", "sandía": "Sandía",
    "patata": "Pataca", "patatas": "Patacas", "tomate": "Tomate",
    "cebolla": "Cebola", "ajo": "Allo", "lechuga": "Leituga",
    "pimiento": "Pemento", "zanahoria": "Cenoria", "calabacín": "Cabaciña",
    "pepino": "Cogombro", "espinaca": "Espinaca", "espinacas": "Espinacas",
    "judía": "Xudía", "judías": "Xudías", "guisante": "Chícharo",
    "guisantes": "Chícharos", "champiñón": "Cogomelo", "champiñones": "Cogomelos",

    # Panadería y cereales
    "pan": "Pan", "harina": "Fariña", "arroz": "Arroz", "pasta": "Pasta",
    "cereal": "Cereal", "cereales": "Cereais", "galleta": "Galleta",
    "galletas": "Galletas", "bollo": "Bolo", "bollería": "Bolería",

    # Bebidas
    "agua": "Auga", "café": "Café", "té": "Té", "zumo": "Zume",
    "vino": "Viño", "cerveza": "Cervexa", "refresco": "Refresco",
    "leche entera": "Leite enteiro",

    # Despensa
    "azúcar": "Azucre", "sal": "Sal", "aceite": "Aceite", "vinagre": "Vinagre",
    "miel": "Mel", "mermelada": "Marmelada", "conserva": "Conserva",
    "conservas": "Conservas", "sopa": "Sopa", "caldo": "Caldo",
    "especias": "Especias", "salsa": "Salsa", "chocolate": "Chocolate",

    # Congelados
    "congelado": "Conxelado", "congelados": "Conxelados", "helado": "Xeado",
    "hielo": "Xeo",

    # Limpieza e higiene
    "jabón": "Xabón", "detergente": "Deterxente", "lejía": "Lixivia",
    "suavizante": "Suavizante", "papel": "Papel", "servilleta": "Servilleta",
    "servilletas": "Servilletas", "esponja": "Esponxa", "escoba": "Vasoira",
    "fregona": "Fregona", "bolsa": "Bolsa", "bolsas": "Bolsas",
    "champú": "Xampú", "pasta de dientes": "Pasta de dentes",
    "cepillo de dientes": "Cepillo de dentes", "pañal": "Cueiro",
    "pañales": "Cueiros", "papel higiénico": "Papel hixiénico",

    # Genéricos de casa
    "batería": "Pila", "pilas": "Pilas", "bombilla": "Bombilla",
    "vela": "Candea", "velas": "Candeas",
}


def traducir_texto(texto):
    """
    Traduce un texto de español a gallego usando el diccionario propio.

    Intenta primero la frase completa, luego palabra a palabra.
    Si no encuentra nada, devuelve el texto original.
    """
    if not texto:
        return texto

    texto_limpio = texto.lower().strip()
    if texto_limpio in DICCIONARIO_ES_GL:
        return DICCIONARIO_ES_GL[texto_limpio]

    palabras = texto.split()
    traducidas = []
    alguna_traducida = False
    for palabra in palabras:
        palabra_limpia = palabra.lower().strip('.,')
        if palabra_limpia in DICCIONARIO_ES_GL:
            traducidas.append(DICCIONARIO_ES_GL[palabra_limpia])
            alguna_traducida = True
        else:
            traducidas.append(palabra)

    return " ".join(traducidas) if alguna_traducida else texto


def obtener_diccionario():
    return DICCIONARIO_ES_GL
