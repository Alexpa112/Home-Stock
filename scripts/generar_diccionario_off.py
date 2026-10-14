"""Genera stockhogar/servicios/ocr/diccionario/datos_off.py a partir de la
taxonomia de categorias de Open Food Facts (ODbL; https://world.openfoodfacts.org).

Uso:  python scripts/generar_diccionario_off.py categories.txt
(categories.txt: https://raw.githubusercontent.com/openfoodfacts/openfoodfacts-server/main/taxonomies/food/categories.txt)

De cada categoria se toma el nombre en espanol y los sinonimos en espanol,
catalan, gallego y euskera, y se le asigna una categoria de la app segun su
antepasado mas cercano. Se descartan nombres genericos o demasiado largos.
Los articulos curados a mano (datos_articulos_*.py) tienen prioridad: este
fichero solo rellena lo que ellos no cubren.
"""
import json
import re
import sys
import unicodedata
from collections import deque
from pathlib import Path

# antepasado (nombre en ingles de OFF) -> categoria de la app. Gana el MAS CERCANO.
MAPA = [
    ("Plant-based beverages", "Alternativas Vegetales"), ("Dairy substitutes", "Alternativas Vegetales"),
    ("Meat alternatives", "Alternativas Vegetales"), ("Egg substitutes", "Alternativas Vegetales"),
    ("Baby foods", "Bebé"),
    ("Frozen foods", "Congelados"), ("Ice creams and sorbets", "Congelados"), ("Pizzas pies and quiches", "Congelados"),
    ("Breaded products", "Congelados"),
    ("Eggs and their products", "Lácteos y Huevos"), ("Cheeses", "Lácteos y Huevos"), ("Dairies", "Lácteos y Huevos"),
    ("Fermented milk products", "Lácteos y Huevos"),
    ("Meats and their products", "Carnes y Embutidos"), ("Meats", "Carnes y Embutidos"),
    ("Seafood", "Pescados y Mariscos"), ("Fishes and their products", "Pescados y Mariscos"),
    ("Fruits", "Frutas y Verduras"), ("Vegetables", "Frutas y Verduras"), ("Fresh fruits", "Frutas y Verduras"),
    ("Fresh vegetables", "Frutas y Verduras"), ("Mushrooms and their products", "Frutas y Verduras"),
    ("Aromatic herbs", "Frutas y Verduras"),
    ("Bakery products", "Panadería y Bollería"), ("Breads", "Panadería y Bollería"), ("Viennoiseries", "Panadería y Bollería"),
    ("Pastas", "Cereales y Pasta"), ("Pastas and dumplings", "Cereales y Pasta"), ("Breakfast cereals", "Cereales y Pasta"),
    ("Cereals and their products", "Cereales y Pasta"), ("Rices", "Cereales y Pasta"), ("Flours", "Despensa"),
    ("Biscuits and crackers", "Snacks y Dulces"), ("Chocolates", "Snacks y Dulces"), ("Confectioneries", "Snacks y Dulces"),
    ("Cocoa and its products", "Snacks y Dulces"), ("Salty snacks", "Snacks y Dulces"), ("Sweet snacks", "Snacks y Dulces"),
    ("Snacks", "Snacks y Dulces"), ("Desserts", "Snacks y Dulces"), ("Chips and fries", "Snacks y Dulces"),
    ("Nuts and their products", "Snacks y Dulces"),
    ("Waters", "Bebidas"), ("Alcoholic beverages", "Bebidas"), ("Coffees", "Bebidas"), ("Teas", "Bebidas"),
    ("Carbonated drinks", "Bebidas"), ("Beverages", "Bebidas"), ("Beverages and beverages preparations", "Bebidas"),
    ("Legumes and their products", "Despensa"), ("Condiments", "Despensa"), ("Sauces", "Despensa"), ("Fats", "Despensa"),
    ("Canned foods", "Despensa"), ("Spreads", "Despensa"), ("Sweeteners", "Despensa"), ("Vegetable pickles", "Despensa"),
    ("Dried products", "Despensa"), ("Bee products", "Despensa"), ("Soups", "Despensa"), ("Meals", "Despensa"),
    ("Sandwiches", "Despensa"),
]
IDIOMAS = ("es", "ca", "gl", "eu")
GENERICAS = {
    "producto", "productos", "alimento", "alimentos", "derivado", "derivados", "variado", "variados", "surtido",
    "surtidos", "mezcla", "mezclas", "tipo", "otro", "otros", "otra", "otras", "diverso", "diversos", "preparado",
    "preparados", "base", "elaborado", "elaborados", "ingrediente", "ingredientes", "especialidad", "especialidades",
    "de", "con", "sin", "para", "y", "o", "del", "al", "en", "a", "la", "el", "los", "las", "un", "una",
}
MAX_PALABRAS = 4


def sin_tildes(t):
    return "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))


def cargar(ruta):
    nodos = {}
    for b in Path(ruta).read_text(encoding="utf-8").split("\n\n"):
        lin = [l for l in b.split("\n") if l and not l.startswith("#")]
        if not lin or lin[0].startswith(("synonyms:", "stopwords:")):
            continue
        padres, nombres = [], {}
        for l in lin:
            if l.startswith("<"):
                m = re.match(r"<\s*en:\s*(.+)", l)
                if m:
                    padres.append(m.group(1).strip().lower())
            else:
                m = re.match(r"^([a-z]{2}):\s*(.+)$", l)
                if m:
                    nombres[m.group(1)] = [x.strip() for x in m.group(2).split(",") if x.strip()]
        if "en" in nombres:
            nodos[nombres["en"][0].lower()] = {"padres": padres, "n": nombres}
    return nodos


def categoria_de(clave, nodos, mapa):
    visto = {clave}
    nivel = [clave]
    for _ in range(10):
        for k in nivel:
            if k in mapa:
                return mapa[k]
        siguiente = []
        for k in nivel:
            for p in nodos.get(k, {}).get("padres", []):
                if p not in visto:
                    visto.add(p)
                    siguiente.append(p)
        if not siguiente:
            return None
        nivel = siguiente
    return None


def valido(nombre):
    if re.search(r"[\d%/()&:;|=<>]", nombre):
        return False
    palabras = [p for p in re.split(r"[\s\-']+", sin_tildes(nombre.lower())) if p]
    if not palabras or len(palabras) > MAX_PALABRAS:
        return False
    if any(p in GENERICAS for p in palabras if len(palabras) > 1 and p not in ("de", "con", "sin", "y", "al", "del", "en", "a", "la", "el")):
        return False
    return len(sin_tildes(nombre)) >= 3 and not all(p in GENERICAS for p in palabras)


def main(ruta, salida):
    nodos = cargar(ruta)
    mapa = {k.lower(): v for k, v in MAPA}
    por_cat = {}
    vistos = set()
    for clave, nodo in nodos.items():
        n = nodo["n"]
        if "es" not in n:
            continue
        cat = categoria_de(clave, nodos, mapa)
        if not cat:
            continue
        nombres_es = [x for x in n["es"] if valido(x)]
        if not nombres_es:
            continue
        nombre = nombres_es[0]
        nombre = nombre[0].upper() + nombre[1:]
        k = sin_tildes(nombre.lower())
        if k in vistos:
            continue
        vistos.add(k)
        alias = []
        for idioma in IDIOMAS:
            for x in n.get(idioma, []):
                if valido(x) and sin_tildes(x.lower()) != k and x not in alias:
                    alias.append(x)
        por_cat.setdefault(cat, []).append((nombre, alias[:8]))
    lineas = [
        '"""Articulos generados desde Open Food Facts (ODbL). NO editar a mano:',
        'ver scripts/generar_diccionario_off.py."""',
        "TEXTO = \"\"\"",
    ]
    total = 0
    for cat in sorted(por_cat):
        lineas.append(f"== {cat}")
        for nombre, alias in sorted(por_cat[cat]):
            lineas.append(f"{nombre} | {' ; '.join(alias)} | ud")
            total += 1
    lineas.append('"""')
    Path(salida).write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(total, "articulos,", {c: len(v) for c, v in por_cat.items()})


if __name__ == "__main__":
    main(sys.argv[1], Path(__file__).resolve().parent.parent / "stockhogar" / "servicios" / "ocr" / "diccionario" / "datos_off.py")
