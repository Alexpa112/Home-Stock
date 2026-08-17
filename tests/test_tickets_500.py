"""Regresion: el escaner de tickets no debe responder 500 ni perder el ticket.

Tres fallos reales, todos introducidos al endurecer tickets.py:

1) `/api/tickets/confirmar` lanzaba `ValidationError` sin haberlo importado en
   el modulo -> NameError -> 500 en vez del 400 que se pretendia. El mismo
   descuido estaba en rutas/auth.py.

2) `_items_desde_ia` comparaba `precio_unitario > 0` con el valor crudo del
   modelo. Si un importe llegaba como cadena, el TypeError lo capturaba el
   `except` que cae a Tesseract, asi que **se descartaba el ticket completo**
   (todos los articulos bien leidos incluidos) por una sola linea mal tipada.
   En un despliegue sin Tesseract el usuario veia "no se detecto ningun
   producto"; con Tesseract, basura.

3) Un cuerpo JSON con `items` que no fuese lista (o con elementos no-dict)
   reventaba el bucle de confirmar -> 500 provocable por cualquier usuario.
"""
import io
import unittest
import uuid
from unittest.mock import patch

from PIL import Image
from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


def _producto_ia(**cambios):
    """Una linea tal como la entrega el motor de vision."""
    base = {
        "nombre_ticket": "Tomate Pera",
        "cantidad": 1,
        "unidad": "ud",
        "producto_id": None,
        "precio_unitario": 1.50,
        "precio_total": 1.50,
        "confianza": 0.95,
        "coherencia_precio": "cuadra",
    }
    base.update(cambios)
    return base


class TicketsSinErrorInternoTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        self.nombre_usuario = f"test_tk_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            self.usuario_id = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (self.nombre_usuario, generate_password_hash("password123"), ahora()),
            ).lastrowid
            self.hogar_id = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, 1, ?, ?)",
                ("Hogar tickets", self.usuario_id, ahora(), ahora()),
            ).lastrowid
            db.execute(
                "INSERT INTO permisos_hogar (hogar_id, usuario_id, nivel, fecha_otorgado) VALUES (?, ?, 'editar', ?)",
                (self.hogar_id, self.usuario_id, ahora()),
            )
            db.commit()

        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess["usuario"] = self.nombre_usuario
            sess["usuario_id"] = self.usuario_id
            sess["hogar_actual_id"] = self.hogar_id

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute(
                "DELETE FROM stock_hogar WHERE hogar_id = ?", (self.hogar_id,)
            )
            db.execute("DELETE FROM permisos_hogar WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM hogares WHERE id = ?", (self.hogar_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def _analizar(self, respuesta_ia):
        """Sube una imagen forzando el motor de vision con la respuesta dada."""
        buf = io.BytesIO()
        Image.new("RGB", (400, 500), "white").save(buf, format="JPEG")
        buf.seek(0)
        with patch("stockhogar.rutas.tickets.ClaudeOCR.disponible", return_value=True), \
             patch("stockhogar.rutas.tickets.ClaudeOCR.procesar", return_value=respuesta_ia):
            return self.client.post(
                "/api/tickets/analizar",
                data={"foto": (buf, "ticket.jpg")},
                content_type="multipart/form-data",
            )

    # --- 1) NameError -> 500 en confirmar -------------------------------

    def test_producto_id_no_numerico_da_400_no_500(self):
        respuesta = self.client.post(
            "/api/tickets/confirmar",
            json={"items": [{"nombre": "Agua", "cantidad": 1, "producto_id": "abc"}]},
        )
        self.assertEqual(
            respuesta.status_code, 400, respuesta.get_data(as_text=True),
        )

    # --- 2) el ticket entero se perdia por un importe mal tipado --------

    def test_un_importe_como_cadena_no_descarta_el_ticket(self):
        respuesta = self._analizar({"productos": [
            _producto_ia(nombre_ticket="Tomate Pera", precio_unitario="2,49"),
            _producto_ia(nombre_ticket="Agua Mineral"),
        ]})

        self.assertEqual(respuesta.status_code, 200, respuesta.get_data(as_text=True))
        nombres = [i["nombre"] for i in respuesta.get_json()["items"]]
        self.assertIn(
            "Agua Mineral", nombres,
            "una sola linea con el importe como cadena no debe costar el ticket "
            "completo: el resto de articulos estaban bien leidos",
        )
        self.assertIn("Tomate Pera", nombres)

    def test_el_importe_en_cadena_se_interpreta_no_se_descarta(self):
        respuesta = self._analizar({"productos": [
            _producto_ia(precio_unitario="2,49", precio_total="2,49"),
        ]})
        item = respuesta.get_json()["items"][0]
        self.assertEqual(
            item["precio_unitario"], 2.49,
            "el importe en texto debe normalizarse, no perderse",
        )

    def test_una_linea_mal_formada_no_descarta_las_demas(self):
        respuesta = self._analizar({"productos": [
            "no soy un producto",
            _producto_ia(nombre_ticket="Agua Mineral"),
        ]})
        self.assertEqual(respuesta.status_code, 200)
        nombres = [i["nombre"] for i in respuesta.get_json()["items"]]
        self.assertIn("Agua Mineral", nombres)

    # --- 3) items mal formado -> 400, no 500 ----------------------------

    def test_items_que_no_es_lista_da_400(self):
        respuesta = self.client.post("/api/tickets/confirmar", json={"items": "no-es-lista"})
        self.assertEqual(respuesta.status_code, 400, respuesta.get_data(as_text=True))

    def test_item_que_no_es_objeto_da_400(self):
        respuesta = self.client.post("/api/tickets/confirmar", json={"items": [5]})
        self.assertEqual(respuesta.status_code, 400, respuesta.get_data(as_text=True))

    # --- el camino normal sigue funcionando ----------------------------

    def test_el_ticket_normal_se_analiza_y_se_confirma(self):
        analisis = self._analizar({"productos": [
            _producto_ia(nombre_ticket="Tomate Pera", cantidad=0.85, unidad="kg"),
        ]})
        self.assertEqual(analisis.status_code, 200, analisis.get_data(as_text=True))
        item = analisis.get_json()["items"][0]

        confirmacion = self.client.post(
            "/api/tickets/confirmar",
            json={"items": [{
                "nombre": item["nombre"],
                "cantidad": item["cantidad"],
                "unidad": item["unidad"],
                "categoria": item["categoria"],
                "producto_id": item["producto_id"],
            }]},
        )
        self.assertEqual(confirmacion.status_code, 200, confirmacion.get_data(as_text=True))
        self.assertEqual(confirmacion.get_json().get("creados"), 1)


class RangosDePrecioPorCategoriaTests(unittest.TestCase):
    """Las claves de rango_precios deben ser categorias reales.

    Al renombrar las categorias deducidas para que coincidieran con
    CATEGORIAS_DEFECTO se quedaron atras las claves de `rango_precios`, asi que
    `validar_precio` caia al rango por defecto (0, 100) y la validacion de
    precio dejaba de aplicarse a carnes, pescados, higiene y bebe sin que nada
    lo avisara.
    """

    def test_todas_las_categorias_del_matcher_existen_en_el_catalogo(self):
        from stockhogar.config import CATEGORIAS_DEFECTO
        from stockhogar.servicios.ocr.matcher_inteligente import MatcherInteligente

        validas = {nombre for nombre, _ in CATEGORIAS_DEFECTO}
        matcher = MatcherInteligente()

        deducibles = set(matcher.palabras_categoria) - validas
        self.assertEqual(
            deducibles, set(),
            "deducir_categoria devolveria categorias que normalizar_categoria "
            "convierte en 'Otros': la deduccion queda muerta",
        )

        rangos = set(matcher.rango_precios) - validas
        self.assertEqual(
            rangos, set(),
            "validar_precio no encontraria estos rangos y caeria al (0, 100) "
            "por defecto, desactivando la validacion de precio",
        )

    def test_el_rango_se_aplica_a_una_categoria_deducida(self):
        from stockhogar.servicios.ocr.matcher_inteligente import MatcherInteligente

        matcher = MatcherInteligente()
        categoria = matcher.deducir_categoria("Pollo Entero")
        self.assertEqual(categoria, "Carnes y Embutidos")

        valido, _ = matcher.validar_precio(80.0, categoria)
        self.assertFalse(
            valido,
            "80€ el kilo de pollo debe salir del rango: si pasa, el rango no "
            "se esta aplicando",
        )


class DeducirCategoriaTests(unittest.TestCase):
    """Como llega el texto de un ticket: en mayusculas y sin tildes.

    Dos fallos que dejaban articulos mal clasificados:
      - las palabras clave llevan tilde ("champú", "salmón") y el ticket no, asi
        que no casaban;
      - se comparaban subcadenas, de modo que "PANAL" casaba con "pan" y
        "SALMON" con "sal".
    """

    def setUp(self):
        from stockhogar.servicios.ocr.matcher_inteligente import MatcherInteligente
        self.matcher = MatcherInteligente()

    def test_reconoce_palabras_clave_sin_tildes(self):
        self.assertEqual(self.matcher.deducir_categoria("CHAMPU ANTICAIDA"), "Higiene")
        self.assertEqual(self.matcher.deducir_categoria("JAMON SERRANO"), "Carnes y Embutidos")
        self.assertEqual(self.matcher.deducir_categoria("MEJILLON EN ESCABECHE"), "Pescados y Mariscos")

    def test_con_tildes_sigue_funcionando(self):
        self.assertEqual(self.matcher.deducir_categoria("Champú Anticaída"), "Higiene")

    def test_no_casa_por_trozos_de_palabra(self):
        self.assertEqual(
            self.matcher.deducir_categoria("PANAL TALLA 4"), "Bebé",
            "'PANAL' casaba con la palabra clave 'pan'",
        )
        self.assertEqual(
            self.matcher.deducir_categoria("SALMON FRESCO"), "Pescados y Mariscos",
            "'SALMON' casaba con la palabra clave 'sal'",
        )

    def test_las_palabras_cortas_legitimas_siguen_casando(self):
        self.assertEqual(self.matcher.deducir_categoria("PAN DE MOLDE"), "Alimentación")
        self.assertEqual(self.matcher.deducir_categoria("SAL FINA"), "Alimentación")


if __name__ == "__main__":
    unittest.main()
