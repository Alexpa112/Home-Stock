"""Diccionario de articulos del escaner: une el texto del ticket con el articulo.

- Unitarios: abreviaturas, errores de OCR, marcas, desconocidos.
- Corpus: `datos_ocr/lineas_dev.txt` (con el que se ajusto el motor) y
  `datos_ocr/lineas_ciego.txt` (escrito despues, sin ajustar). Los umbrales se
  fijan a lo MEDIDO para que un cambio que empeore la identificacion falle.
- Integracion: el procesador local y la ruta de Claude devuelven nombre limpio.
"""
import unittest
from pathlib import Path
from unittest.mock import patch

from stockhogar.servicios.ocr.diccionario import obtener, identificar_articulo
from stockhogar.servicios.ocr.procesador_tickets_v2 import ProcesadorTicketsV2
from stockhogar.servicios.ocr.parser_mejorado import LineaTicketMejorada, TipoUnidad

DATOS = Path(__file__).parent / "datos_ocr"


def _corpus(nombre):
    filas = []
    for linea in (DATOS / nombre).read_text(encoding="utf-8").splitlines():
        if not linea.strip() or linea.startswith("#"):
            continue
        p = linea.split("|")
        filas.append((p[0], p[1], p[2] if len(p) > 2 else None))
    return filas


class IdentificacionTests(unittest.TestCase):
    def test_abreviaturas_de_ticket(self):
        for texto, esperado in [
            ("LECHE ENT PASC 1L", "Leche entera"),
            ("YOG NAT x4", "Yogur natural"),
            ("DETERG ROPA", "Detergente lavadora"),
        ]:
            with self.subTest(texto=texto):
                self.assertEqual(identificar_articulo(texto).nombre, esperado)

    def test_catalan(self):
        self.assertEqual(identificar_articulo("LLET SENCERA").nombre, "Leche entera")

    def test_simbolos_de_ocr_en_lugar_de_letras(self):
        r = identificar_articulo("T€MAT€ PERA")
        self.assertEqual(r.categoria, "Frutas y Verduras")

    def test_la_marca_no_cambia_el_articulo(self):
        self.assertEqual(identificar_articulo("TOMATE TRITURADO HACENDADO").nombre, "Tomate triturado")

    def test_una_marca_no_borra_un_articulo_parecido(self):
        # "avene" (marca) y "avena" comparten raiz: la marca solo se quita si es la palabra exacta.
        self.assertEqual(identificar_articulo("BEBIDA AVENA").categoria, "Alternativas Vegetales")

    def test_la_correccion_ortografica_no_acorta_palabras(self):
        # "maria" estuvo a punto de corregirse a "mar" y "rioja" a "rojos".
        self.assertIn("maria", identificar_articulo("GALLETAS MARIA").nombre.lower())
        self.assertNotIn("rojo", identificar_articulo("VINO TINTO RIOJA").nombre.lower())

    def test_desconocido_conserva_el_texto_y_no_inventa(self):
        r = identificar_articulo("XYZQ MISTERIO")
        self.assertIsNone(r.categoria)
        self.assertEqual(r.fuente, "ninguna")
        self.assertEqual(r.nombre, "Xyzq Misterio")

    def test_vacio_no_falla(self):
        self.assertEqual(identificar_articulo("").fuente, "ninguna")
        self.assertEqual(identificar_articulo("   ").nombre, "")

    def test_sustantivo_principal_no_afirma_nombre_del_catalogo(self):
        r = identificar_articulo("TOMATE PERA")
        self.assertEqual(r.fuente, "catalogo_parcial")
        self.assertEqual(r.nombre, "Tomate Pera")
        self.assertEqual(r.categoria, "Frutas y Verduras")

    def test_el_catalogo_se_carga_entero(self):
        d = obtener()
        self.assertGreater(len(d.entradas), 850)
        self.assertEqual(obtener(), d)  # instancia unica


class CorpusTests(unittest.TestCase):
    def _medir(self, fichero):
        d = obtener()
        aciertos = 0
        nombres_ok = nombres = 0
        fallos = []
        filas = _corpus(fichero)
        for texto, categoria, nombre in filas:
            r = d.identificar(texto)
            if r.categoria == categoria:
                aciertos += 1
            else:
                fallos.append((texto, categoria, r.categoria))
            if nombre:
                nombres += 1
                nombres_ok += r.nombre == nombre
        return aciertos / len(filas), (nombres_ok, nombres), fallos

    def test_conjunto_de_desarrollo(self):
        tasa, (ok, total), fallos = self._medir("lineas_dev.txt")
        self.assertGreaterEqual(tasa, 0.97, fallos)
        self.assertEqual(ok, total)

    def test_conjunto_ciego(self):
        # Medido: 0.886. La barra se deja algo por debajo; subirla al mejorar.
        tasa, _, fallos = self._medir("lineas_ciego.txt")
        self.assertGreaterEqual(tasa, 0.85, fallos)

    def test_ninguna_linea_conocida_se_queda_sin_categoria(self):
        d = obtener()
        sin = [t for t, _, _ in _corpus("lineas_dev.txt") + _corpus("lineas_ciego.txt") if d.identificar(t).categoria is None]
        self.assertLessEqual(len(sin), 2, sin)


class IntegracionProcesadorTests(unittest.TestCase):
    def _linea(self, nombre, cantidad=1.0):
        return LineaTicketMejorada(
            nombre=nombre, cantidad=cantidad, unidad=TipoUnidad.UNIDAD, cantidad_texto=f"{cantidad:g} ud",
            precio_unitario=1.0, precio_total=cantidad, confianza_nombre=90.0, confianza_cantidad=90.0,
            es_promocion=False, linea_original=nombre,
        )

    def _procesar(self, linea, match=None):
        proc = ProcesadorTicketsV2()
        with patch.object(proc.matcher, "buscar_en_catalogo", return_value=match), \
                patch.object(proc.matcher, "sugerir_cantidad_estandar", return_value=1):
            return proc._procesar_linea(linea, db=None, hogar_id=1)

    def test_producto_nuevo_recibe_nombre_limpio_categoria_e_icono(self):
        item = self._procesar(self._linea("LECHE ENT PASC 1L"))
        self.assertEqual(item["nombre"], "Leche entera")
        self.assertEqual(item["nombre_ticket"], "LECHE ENT PASC 1L")
        self.assertEqual(item["categoria"], "Lácteos y Huevos")
        self.assertEqual(item["origen_nombre"], "catalogo")

    def test_el_stock_del_hogar_manda_sobre_el_diccionario(self):
        match = {"id": 7, "nombre": "Mi leche", "categoria": "Bebidas", "icono": "🥛", "confianza": 0.9}
        item = self._procesar(self._linea("LECHE ENT PASC 1L"), match)
        self.assertEqual(item["producto_id"], 7)
        self.assertEqual(item["categoria"], "Bebidas")
        self.assertEqual(item["origen_nombre"], "hogar")

    def test_un_fallo_del_diccionario_no_tumba_el_ticket(self):
        with patch("stockhogar.servicios.ocr.diccionario.obtener", side_effect=RuntimeError("boom")):
            item = self._procesar(self._linea("LECHE ENT PASC 1L"))
        self.assertEqual(item["nombre"], "LECHE ENT PASC 1L")
        self.assertEqual(item["origen_nombre"], "ticket")

    def test_la_cantidad_no_se_toca(self):
        item = self._procesar(self._linea("YOG NAT", 4.0))
        self.assertEqual(item["cantidad"], 4.0)


if __name__ == "__main__":
    unittest.main()
