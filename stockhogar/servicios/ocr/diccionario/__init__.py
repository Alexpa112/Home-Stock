"""Diccionario de articulos de supermercado: une el texto de una linea de ticket
con el articulo real (nombre limpio, categoria, unidad, icono).

Por que existe: el ticket no dice "Leche entera", dice "LECHE ENT PASC 1L" o
"L€CH€ €NT€RA". Hasta ahora solo se comparaba con el stock del propio hogar, asi
que un usuario nuevo recibia el texto crudo del ticket, sin nombre limpio ni
categoria fiable, y el catalogo estandar (751 articulos) no se usaba.

Capas, de la mas segura a la mas laxa (se corta en cuanto una acierta):
 1. Normalizar: minusculas, sin tildes, errores tipicos de OCR (0->o, 5->s,
    EUR->e, @->a...), sin cantidades ("1L", "x4", "500g").
 2. Expandir abreviaturas de ticket ("ent"->"entera", "yog"->"yogur"). Una
    abreviatura puede ser ambigua ("esp": espinacas/espaguetis): se prueban las
    opciones y gana la que mejor casa.
 3. Corregir palabras mal leidas contra el vocabulario ("lechee" -> "leche").
 4. Quitar lo que no identifica: marcas ("hacendado", "pascual"), envases
    ("bolsa", "pack") y tamanos.
 5. Emparejar con el catalogo (estandar + ampliado con sinonimos, incluidos
    catalan, gallego y euskera) por cobertura de palabras: el articulo se da por
    identificado solo si estan TODAS las palabras de su nombre.
 6. Si no hay articulo, la categoria sale de votar las palabras conocidas.

Principio de diseno: ante la duda, NO inventar una coincidencia. Un articulo
desconocido conserva el texto limpio del ticket (y su categoria si se puede
deducir) en vez de convertirse en otro. Una coincidencia falsa es peor que un
articulo sin identificar, porque el usuario no la revisa.
"""
import re
import threading
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from rapidfuzz import fuzz, process

from .datos_abreviaturas import ABREVIATURAS, RELLENO
from .datos_marcas import MARCAS
from . import datos_articulos_a, datos_articulos_b, datos_articulos_c

# Umbrales (ajustados con tests/test_diccionario_articulos.py).
CONFIANZA_CANONICO = 0.80   # a partir de aqui se usa el nombre del catalogo
CONFIANZA_CATEGORIA = 0.55  # a partir de aqui se fia de la categoria votada
MAX_PALABRAS_ALIAS = 5      # un alias mas largo es una frase suelta, no un sinonimo
MAX_COMBINACIONES = 12      # tope de lecturas alternativas por abreviaturas ambiguas

# Palabras que describen el ESTADO o la presentacion pero no cambian el articulo:
# "tomate fresco" y "tomate" son lo mismo para el stock.
MODIFICADORES = {
    "fresco", "fresca", "frescos", "frescas", "congelado", "congelada", "congelados", "congeladas",
    "granel", "pieza", "piezas", "kg", "lavado", "lavada", "pelado", "pelada", "troceado", "troceada",
    "fileteado", "fileteada", "envasado", "envasada", "natural_", "eco", "ecologico", "ecologica",
    "bio", "nacional", "importacion", "primera", "extra_", "categoria", "calibre", "temporada",
    "bandeja", "malla", "granel", "cesta", "clase", "gr", "ud", "uds", "x",
}

_RAICES_MODIFICADORES = None  # se rellena tras definir _raiz
_SIN_TOKEN = re.compile(r"[^a-z0-9]+")
_CANTIDAD = re.compile(
    r"^(?:\d+(?:[.,]\d+)?(?:l|lt|kg|g|gr|ml|cl|dl|ud|uds|x|%|u|m|cm|mm|w|v)?|x\d+|\d+x\d*)$"
)
# Lo que el OCR pone en lugar de una letra DENTRO de una palabra.
_CONFUSION = {"0": "o", "5": "s", "8": "b", "6": "g", "€": "e", "@": "a", "$": "s", "|": "l", "!": "i", "¡": "i"}
_CONFUSION_UNO = ("i", "l")  # el "1" puede ser "i" o "l"


def _sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def _raiz(token: str) -> str:
    """Forma comparable de una palabra: sin plural ni genero (tomates -> tomat,
    entera/entero -> enter). Se aplica a los DOS lados de cada comparacion."""
    if len(token) > 4 and token.endswith("es") and token[-3] in "nrldzjx":
        token = token[:-2]
    elif len(token) > 3 and token.endswith("s"):
        token = token[:-1]
    if len(token) > 4 and token[-1] in "aeo":
        token = token[:-1]
    return token


def _tokens_crudos(texto: str) -> List[str]:
    """Palabras del texto en minusculas y sin tildes. Los simbolos que el OCR usa
    en lugar de letras ("€", "@", "$", "|") se conservan DENTRO de la palabra
    para poder deshacer la confusion despues; el resto separa palabras."""
    t = _sin_tildes(texto.lower().replace("ñ", "n"))
    t = re.sub(r"[^a-z0-9€@$|!/%.,]+", " ", t)
    salida = []
    for pieza in t.split():
        pieza = pieza.strip(".,/")
        if not pieza:
            continue
        # "s/lactosa" -> "sin lactosa"
        if pieza.startswith("s/") and len(pieza) > 2:
            salida += ["sin", pieza[2:]]
            continue
        if pieza.startswith("c/") and len(pieza) > 2:
            salida += ["con", pieza[2:]]
            continue
        pieza = pieza.replace("/", "")
        pieza = re.sub(r"[,]", "", pieza)
        if pieza:
            salida.append(pieza)
    return salida


_RAICES_MODIFICADORES = {_raiz(m) for m in MODIFICADORES}


@dataclass
class Entrada:
    nombre: str
    categoria: str
    unidad: str = "ud"
    icono: Optional[str] = None
    variantes: List[Tuple[str, ...]] = field(default_factory=list)  # tuplas de raices


@dataclass
class Identificacion:
    nombre: str                      # nombre a mostrar (canonico si es fiable)
    categoria: Optional[str]
    unidad: Optional[str]
    icono: Optional[str]
    confianza: float                 # 0..1
    fuente: str                      # 'catalogo' | 'categoria' | 'ninguna'
    nombre_limpio: str               # texto del ticket ya expandido y corregido
    canonico: Optional[str] = None   # nombre del catalogo si hubo coincidencia


class Diccionario:
    """Indice en memoria del catalogo. Se construye una vez (ver `obtener`)."""

    def __init__(self):
        self.entradas: List[Entrada] = []
        self._por_nombre: Dict[str, Entrada] = {}
        self._indice: Dict[str, List[Tuple[int, int]]] = {}  # raiz -> [(entrada, variante)]
        self._vocabulario: Dict[str, int] = {}                # raiz -> frecuencia
        self._palabra_raiz: Dict[str, str] = {}               # raiz -> palabra mostrable
        self._marcas: List[Tuple[str, ...]] = []
        self._votos_categoria: Dict[str, Dict[str, float]] = {}
        self._cargar()

    # ------------------------------------------------------------------ carga
    def _normalizar_nombre(self, nombre: str) -> str:
        return " ".join(_tokens_crudos(nombre))

    def _tokens_contenido(self, texto: str) -> List[str]:
        """Raices de las palabras que IDENTIFICAN (sin relleno ni cantidades)."""
        salida = []
        for t in _tokens_crudos(texto):
            if _CANTIDAD.match(t) or t in RELLENO:
                continue
            salida.append(_raiz(t))
        return salida

    def _anadir_entrada(self, nombre, categoria, unidad, icono, alias):
        clave = self._normalizar_nombre(nombre)
        entrada = self._por_nombre.get(clave)
        if entrada is None:
            entrada = Entrada(nombre=nombre, categoria=categoria, unidad=unidad or "ud", icono=icono)
            self._por_nombre[clave] = entrada
            self.entradas.append(entrada)
            self._anadir_variante(entrada, nombre)
        else:
            if icono and not entrada.icono:
                entrada.icono = icono
        for a in alias:
            self._anadir_variante(entrada, a)

    def _anadir_variante(self, entrada: Entrada, texto: str):
        raices = tuple(dict.fromkeys(self._tokens_contenido(self._expandir_para_carga(texto))))
        if not raices or raices in entrada.variantes:
            return
        entrada.variantes.append(raices)

    def _expandir_para_carga(self, texto: str) -> str:
        # En los datos no hay abreviaturas; solo se resuelven marcas pegadas.
        return texto

    def _cargar(self):
        from stockhogar.config import CATALOGO_DEFECTO, CATEGORIAS_DEFECTO

        categorias = {self._normalizar_nombre(c if isinstance(c, str) else c[0]) for c in CATEGORIAS_DEFECTO}
        self._categorias_validas = categorias

        for nombre, categoria, icono, unidad, _sub in CATALOGO_DEFECTO:
            self._anadir_entrada(nombre, categoria, unidad, icono, [])

        for modulo in (datos_articulos_a, datos_articulos_b, datos_articulos_c):
            categoria = None
            for linea in modulo.TEXTO.splitlines():
                linea = linea.strip()
                if not linea or linea.startswith("#"):
                    continue
                if linea.startswith("=="):
                    categoria = linea[2:].strip()
                    continue
                partes = [p.strip() for p in linea.split("|")]
                nombre = partes[0]
                alias = [a.strip() for a in partes[1].split(";")] if len(partes) > 1 and partes[1] else []
                unidad = partes[2] if len(partes) > 2 and partes[2] else None
                if not nombre or categoria is None:
                    continue
                existente = self._por_nombre.get(self._normalizar_nombre(nombre))
                cat = existente.categoria if existente else categoria
                self._anadir_entrada(nombre, cat, unidad or (existente.unidad if existente else "ud"), None, alias)

        self._podar_variantes()
        self._construir_indices()

    def _podar_variantes(self):
        """Quita alias redundantes: uno que ya contiene todas las palabras del
        nombre canonico no aporta (el comparador lo cubre), y uno demasiado
        largo es una frase suelta, no un sinonimo. Asi un alias mal escrito en
        los datos no puede provocar coincidencias raras."""
        for e in self.entradas:
            canonica = e.variantes[0] if e.variantes else ()
            conjunto = set(canonica)
            utiles = [canonica] if canonica else []
            vistos = {canonica}
            for v in e.variantes[1:]:
                if v in vistos or len(v) > MAX_PALABRAS_ALIAS:
                    continue
                if conjunto and conjunto.issubset(set(v)):
                    continue
                vistos.add(v)
                utiles.append(v)
            e.variantes = utiles

    def _construir_indices(self):
        self._indice.clear()
        self._vocabulario.clear()
        for i, e in enumerate(self.entradas):
            for j, v in enumerate(e.variantes):
                for raiz in v:
                    self._indice.setdefault(raiz, []).append((i, j))
                    self._vocabulario[raiz] = self._vocabulario.get(raiz, 0) + 1
                    peso = 1.0 / len(v)
                    votos = self._votos_categoria.setdefault(raiz, {})
                    votos[e.categoria] = votos.get(e.categoria, 0.0) + peso
        # Palabras conocidas aunque no esten en un nombre de articulo.
        for exp in ABREVIATURAS.values():
            for palabra in exp:
                for t in palabra.split():
                    self._vocabulario.setdefault(_raiz(t), 1)
        for t in RELLENO:
            self._vocabulario.setdefault(_raiz(t), 1)
        for m in MARCAS:
            partes = tuple(_tokens_crudos(m))  # palabra exacta: "avene" no debe borrar "avena"
            if partes:
                self._marcas.append(partes)
                for p in partes:
                    self._vocabulario.setdefault(_raiz(p), 1)
        self._marcas.sort(key=len, reverse=True)
        self._lista_vocabulario = list(self._vocabulario)
        # Palabras mostrables (para devolver "entera" y no "enter").
        for palabra in {t for e in self.entradas for v in (e.nombre,) for t in _tokens_crudos(v)}:
            self._palabra_raiz.setdefault(_raiz(palabra), palabra)
        for exp in ABREVIATURAS.values():
            for palabra in exp:
                for t in palabra.split():
                    self._palabra_raiz.setdefault(_raiz(t), t)

    # --------------------------------------------------------------- lectura
    def _corregir_token(self, token: str) -> str:
        """Devuelve el token (ya sin confusiones de OCR) o su correccion mas
        cercana del vocabulario. Mantiene el original si no hay una clara."""
        if not token:
            return token
        candidatos = {token}
        if any(c in token for c in "0568€@$|!1"):
            base = "".join(_CONFUSION.get(c, c) for c in token)
            candidatos.add(base)
            if "1" in base:
                for sust in _CONFUSION_UNO:
                    candidatos.add(base.replace("1", sust))
            candidatos = {re.sub(r"[^a-z0-9]", "", c) for c in candidatos} - {""}
        for c in candidatos:
            if _raiz(c) in self._vocabulario:
                return c
        mejor = None
        for c in candidatos:
            if c.isdigit() or len(c) < 4:
                continue
            raiz = _raiz(c)
            if len(raiz) < 5:
                continue  # raices cortas ("mari") se parecen a cualquier otra ("mar")
            corte = 85 if len(raiz) <= 6 else (84 if len(raiz) <= 8 else 88)
            r = process.extractOne(raiz, [v for v in self._lista_vocabulario if abs(len(v) - len(raiz)) <= 1],
                                   scorer=fuzz.ratio, score_cutoff=corte)
            if r and (mejor is None or r[1] > mejor[1]):
                mejor = r
        if mejor:
            return self._palabra_raiz.get(mejor[0], mejor[0])
        # Truncado de impresora ("MANTEQ", "DETERG"): prefijo unico del vocabulario.
        base = re.sub(r"[^a-z]", "", next(iter(candidatos)))
        if len(base) >= 4:
            cands = [v for v in self._lista_vocabulario if v.startswith(_raiz(base)) and len(v) <= len(base) + 6]
            if len(cands) == 1:
                return self._palabra_raiz.get(cands[0], cands[0])
        return re.sub(r"[^a-z0-9]", "", token) or token

    def _opciones_abreviatura(self, token: str) -> Tuple[str, ...]:
        exp = ABREVIATURAS.get(token)
        if exp:
            return tuple(" ".join(dict.fromkeys(" ".join(e for e in exp[:1]).split())) for _ in (0,)) if len(exp) == 1 else exp
        return (token,)

    def _quitar_marcas(self, raices: List[str]) -> List[str]:
        if not raices:
            return raices
        salida = []
        i = 0
        n = len(raices)
        while i < n:
            quitado = False
            for marca in self._marcas:
                m = len(marca)
                if tuple(raices[i:i + m]) == marca:
                    # "dia" (cadena) coincide con la palabra: solo si va al final o al principio
                    if marca == ("dia",) and n > 2 and 0 < i < n - 1:
                        continue
                    i += m
                    quitado = True
                    break
            if not quitado:
                salida.append(raices[i])
                i += 1
        return salida

    def _lecturas(self, texto: str) -> List[List[str]]:
        """Posibles lecturas del texto como listas de palabras ya corregidas."""
        crudos = [t for t in _tokens_crudos(texto) if not _CANTIDAD.match(t)]
        opciones: List[List[str]] = []
        for t in crudos:
            exp = ABREVIATURAS.get(t)
            if exp:
                opciones.append([w for w in exp])
            else:
                opciones.append([self._corregir_token(t)])
        # producto de opciones, acotado
        lecturas: List[List[str]] = [[]]
        for ops in opciones:
            nuevas = []
            for base in lecturas:
                for o in ops:
                    nuevas.append(base + o.split())
            lecturas = nuevas[:MAX_COMBINACIONES]
        return lecturas

    def _contenido(self, palabras: List[str]) -> List[str]:
        palabras = [p for p in palabras if p not in RELLENO and not _CANTIDAD.match(p)]
        palabras = self._quitar_marcas(palabras)
        return [r for r in map(_raiz, palabras) if r not in _RAICES_MODIFICADORES]

    def _emparejar(self, contenido: List[str]) -> Tuple[Optional[Entrada], float, bool]:
        """Mejor articulo cuyo nombre esta COMPLETO en el texto. El tercer valor
        indica coincidencia por sustantivo principal: el nombre del articulo abre
        el texto ("tomate pera" -> Tomates). El sustantivo principal va primero
        en espanol, asi que sirve para categoria/unidad, pero el nombre mostrado
        sigue siendo el del ticket (no se afirma que "tomate pera" sea "Tomates")."""
        if not contenido:
            return None, 0.0, False
        conjunto = set(contenido)
        candidatos: Dict[Tuple[int, int], int] = {}
        for raiz in conjunto:
            for (i, j) in self._indice.get(raiz, ()):
                candidatos[(i, j)] = candidatos.get((i, j), 0) + 1
        mejor = None
        mejor_clave = None
        for (i, j), aciertos in candidatos.items():
            variante = self.entradas[i].variantes[j]
            if aciertos < len(variante):
                continue  # faltan palabras del nombre: no esta identificado
            extra = len(conjunto) - len(set(variante))
            confianza = len(variante) / (len(variante) + 0.5 * extra)
            prefijo = tuple(contenido[:len(variante)]) == variante or set(contenido[:len(variante)]) == set(variante)
            if len(variante) == 1 and extra >= 2 and not prefijo:
                continue  # una palabra suelta en mitad de una frase larga no identifica
            clave = (confianza >= CONFIANZA_CANONICO, prefijo, confianza, len(variante), -extra, -j)
            if mejor_clave is None or clave > mejor_clave:
                mejor_clave = clave
                mejor = (self.entradas[i], confianza, prefijo)
        if mejor is None:
            return None, 0.0, False
        return mejor

    def _votar_categoria(self, contenido: List[str]) -> Tuple[Optional[str], float]:
        total: Dict[str, float] = {}
        for raiz in contenido:
            for cat, peso in self._votos_categoria.get(raiz, {}).items():
                total[cat] = total.get(cat, 0.0) + peso
        if not total:
            return None, 0.0
        ordenado = sorted(total.items(), key=lambda kv: kv[1], reverse=True)
        mejor, valor = ordenado[0]
        suma = sum(total.values())
        segundo = ordenado[1][1] if len(ordenado) > 1 else 0.0
        confianza = valor / suma if suma else 0.0
        if valor - segundo < 0.15 * valor:
            confianza *= 0.7
        return mejor, round(confianza, 3)

    def identificar(self, texto: str) -> Identificacion:
        texto = (texto or "").strip()
        if not texto:
            return Identificacion("", None, None, None, 0.0, "ninguna", "")
        mejor_ent, mejor_conf, mejor_lectura, mejor_pref = None, 0.0, None, False
        for lectura in self._lecturas(texto):
            contenido = self._contenido(lectura)
            ent, conf, pref = self._emparejar(contenido)
            if mejor_lectura is None or conf > mejor_conf:
                mejor_ent, mejor_conf, mejor_lectura, mejor_pref = ent, conf, lectura, pref
        lectura = mejor_lectura or []
        limpio = " ".join(w for w in lectura if not _CANTIDAD.match(w)).strip()
        limpio = limpio.title() if limpio else texto.title()
        if mejor_ent is not None and mejor_conf >= CONFIANZA_CANONICO:
            return Identificacion(
                nombre=mejor_ent.nombre, categoria=mejor_ent.categoria, unidad=mejor_ent.unidad,
                icono=mejor_ent.icono, confianza=round(mejor_conf, 3), fuente="catalogo",
                nombre_limpio=limpio, canonico=mejor_ent.nombre,
            )
        if mejor_ent is not None and mejor_pref:
            return Identificacion(
                nombre=limpio, categoria=mejor_ent.categoria, unidad=mejor_ent.unidad,
                icono=mejor_ent.icono, confianza=0.7, fuente="catalogo_parcial",
                nombre_limpio=limpio, canonico=mejor_ent.nombre,
            )
        contenido = self._contenido(lectura)
        categoria, conf_cat = self._votar_categoria(contenido)
        if categoria and conf_cat >= CONFIANZA_CATEGORIA:
            return Identificacion(
                nombre=limpio, categoria=categoria, unidad=None, icono=None,
                confianza=conf_cat * 0.6, fuente="categoria", nombre_limpio=limpio,
            )
        return Identificacion(nombre=limpio, categoria=None, unidad=None, icono=None,
                              confianza=0.0, fuente="ninguna", nombre_limpio=limpio)


_instancia: Optional[Diccionario] = None
_cerrojo = threading.Lock()


def obtener() -> Diccionario:
    """Instancia unica (construirla lleva ~100 ms y no cambia entre peticiones)."""
    global _instancia
    if _instancia is None:
        with _cerrojo:
            if _instancia is None:
                _instancia = Diccionario()
    return _instancia


def identificar_articulo(texto: str) -> Optional[Identificacion]:
    """Como `obtener().identificar`, pero un fallo del diccionario nunca debe
    tumbar la lectura del ticket: se devuelve None y el llamador usa el texto
    crudo (el comportamiento anterior)."""
    try:
        return obtener().identificar(texto)
    except Exception:  # pragma: no cover - red de seguridad
        import logging
        logging.getLogger(__name__).exception("Diccionario de articulos: fallo al identificar %r", texto)
        return None
