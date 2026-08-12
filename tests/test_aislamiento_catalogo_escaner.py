"""Regresion A-1: el escaner de tickets no puede ver el catalogo de otros hogares.

`productos` no tiene columna de hogar -- el aislamiento vive en `stock_hogar` --
y el escaner era el UNICO sitio del backend que leia esa tabla sin el JOIN.
Cuatro consultas lo hacian: rutas/tickets.py, servicios/ocr/gestor_ocr.py (ya
eliminado), matcher_inteligente.py y matcher_productos.py.

Consecuencias que se cierran aqui:

1. `_normalizar_producto_id` validaba el id devuelto por el modelo contra el
   catalogo GLOBAL, asi que un id de otro hogar pasaba la validacion y
   `tickets._items_desde_ia` sustituia el nombre leido del ticket por el del
   producto ajeno, devolviendolo al cliente.
2. El matcher local publicaba hasta 3 "alternativas" por linea con nombres de
   cualquier hogar, asi que marcar el opt-out de OCR en la nube NO cerraba la
   fuga entre hogares.
3. Se enviaba a Anthropic la lista completa de nombres de producto de toda la
   instalacion en cada escaneo de cualquier usuario.
"""
import base64
import unittest
import uuid
from io import BytesIO
from unittest.mock import patch

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db
from stockhogar.servicios.ocr.catalogo import catalogo_del_hogar
from stockhogar.servicios.ocr.claude_ocr import ClaudeOCR
from stockhogar.servicios.ocr.matcher_inteligente import MatcherInteligente
from stockhogar.servicios.ocr.matcher_productos import MatcherProductos
from stockhogar.servicios.stock import crear_producto_nuevo

_PNG_MINIMO = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

# Nombre inequivoco: si aparece en cualquier salida, viene del hogar ajeno.
NOMBRE_AJENO = "Medicamento Privado De La Otra Familia"
NOMBRE_PROPIO = "Leche Entera"


class AislamientoCatalogoEscanerTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = self.app.test_client()
        self.creados = {"usuarios": [], "hogares": [], "productos": []}

        with self.app.app_context():
            db = get_db()
            self.usuario_id, self.hogar_propio = self._crear_usuario_con_hogar(db, "propio")
            self.otro_id, self.hogar_ajeno = self._crear_usuario_con_hogar(db, "ajeno")
            self.producto_propio = self._crear_producto(db, NOMBRE_PROPIO, self.hogar_propio)
            self.producto_ajeno = self._crear_producto(db, NOMBRE_AJENO, self.hogar_ajeno)
            db.commit()

        with self.client.session_transaction() as sess:
            sess["usuario"] = self.nombre_propio
            sess["usuario_id"] = self.usuario_id
            sess["hogar_actual_id"] = self.hogar_propio

    def _crear_usuario_con_hogar(self, db, etiqueta):
        nombre = f"{etiqueta}_{uuid.uuid4().hex[:8]}"
        if etiqueta == "propio":
            self.nombre_propio = nombre
        cur = db.execute(
            "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
            (nombre, generate_password_hash("password123"), ahora()),
        )
        usuario_id = cur.lastrowid
        cur = db.execute(
            "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
            "VALUES (?, ?, 0, ?, ?)",
            (f"Hogar {etiqueta}", usuario_id, ahora(), ahora()),
        )
        hogar_id = cur.lastrowid
        self.creados["usuarios"].append(usuario_id)
        self.creados["hogares"].append(hogar_id)
        return usuario_id, hogar_id

    def _crear_producto(self, db, nombre, hogar_id):
        """Se usa el helper de produccion para no duplicar el esquema aqui."""
        producto_id = crear_producto_nuevo(
            db, nombre, "Otros", 1, "ud", hogar_id=hogar_id
        )
        self.creados["productos"].append(producto_id)
        return producto_id

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            for pid in self.creados["productos"]:
                db.execute("DELETE FROM productos WHERE id = ?", (pid,))
            for hid in self.creados["hogares"]:
                db.execute("DELETE FROM hogares WHERE id = ?", (hid,))
            for uid in self.creados["usuarios"]:
                db.execute("DELETE FROM usuarios WHERE id = ?", (uid,))
            db.commit()

    # --- la fuente unica del catalogo ---

    def test_catalogo_del_hogar_no_incluye_productos_de_otros(self):
        with self.app.app_context():
            nombres = [p["nombre"] for p in catalogo_del_hogar(get_db(), self.hogar_propio)]
        self.assertIn(NOMBRE_PROPIO, nombres)
        self.assertNotIn(NOMBRE_AJENO, nombres)

    def test_sin_hogar_el_catalogo_es_vacio(self):
        """Preferimos no emparejar a emparejar contra el catalogo de otro."""
        with self.app.app_context():
            self.assertEqual(catalogo_del_hogar(get_db(), None), [])

    # --- los dos matchers locales (el camino del opt-out) ---

    def test_el_matcher_inteligente_no_empareja_contra_otro_hogar(self):
        matcher = MatcherInteligente()
        with self.app.app_context():
            db = get_db()
            ajeno = matcher.buscar_en_catalogo(NOMBRE_AJENO, db, hogar_id=self.hogar_propio)
            propio = matcher.buscar_en_catalogo(NOMBRE_PROPIO, db, hogar_id=self.hogar_propio)
        self.assertIsNone(ajeno, "el matcher devolvio un producto de otro hogar")
        self.assertIsNotNone(propio, "el matcher dejo de encontrar los del hogar propio")

    def test_las_alternativas_nunca_traen_nombres_de_otro_hogar(self):
        matcher = MatcherInteligente()
        with self.app.app_context():
            resultado = matcher.buscar_en_catalogo(
                NOMBRE_PROPIO, get_db(), hogar_id=self.hogar_propio
            )
        alternativas = (resultado or {}).get("alternativas", [])
        self.assertNotIn(NOMBRE_AJENO, [a["nombre"] for a in alternativas])

    def test_el_matcher_productos_tambien_filtra(self):
        matcher = MatcherProductos()
        with self.app.app_context():
            self.assertIsNone(
                matcher.buscar_en_catalogo(NOMBRE_AJENO, get_db(), hogar_id=self.hogar_propio)
            )

    # --- el camino completo por HTTP ---

    def test_lo_que_se_envia_a_anthropic_solo_lleva_el_catalogo_del_hogar(self):
        capturado = {}

        def espia(self_ocr, imagen_bytes, productos_catalogo, mime=None):
            capturado["catalogo"] = list(productos_catalogo)
            return {"productos": []}

        with patch.object(ClaudeOCR, "disponible", return_value=True), \
             patch.object(ClaudeOCR, "procesar", espia):
            resp = self.client.post(
                "/api/tickets/analizar",
                data={"foto": (BytesIO(_PNG_MINIMO), "t.png")},
                content_type="multipart/form-data",
            )
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        nombres = [p["nombre"] for p in capturado["catalogo"]]
        self.assertIn(NOMBRE_PROPIO, nombres)
        self.assertNotIn(
            NOMBRE_AJENO, nombres,
            "se enviaron a Anthropic nombres de producto de otro hogar",
        )

    def test_un_producto_id_de_otro_hogar_devuelto_por_el_modelo_se_descarta(self):
        """El caso concreto que _normalizar_producto_id decia cubrir y no cubria."""
        respuesta_ia = {
            "productos": [
                {"nombre_ticket": "algo", "producto_id": self.producto_ajeno, "cantidad": 1}
            ]
        }
        with patch.object(ClaudeOCR, "disponible", return_value=True), \
             patch.object(ClaudeOCR, "procesar", return_value=respuesta_ia):
            resp = self.client.post(
                "/api/tickets/analizar",
                data={"foto": (BytesIO(_PNG_MINIMO), "t.png")},
                content_type="multipart/form-data",
            )
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        cuerpo = resp.get_data(as_text=True)
        self.assertNotIn(NOMBRE_AJENO, cuerpo)
        for item in resp.get_json()["items"]:
            self.assertNotEqual(item.get("producto_id"), self.producto_ajeno)

    def test_confirmar_con_producto_id_ajeno_no_toca_el_producto_ajeno(self):
        resp = self.client.post(
            "/api/tickets/confirmar",
            json={"items": [{
                "nombre": "Intento",
                "cantidad": 5,
                "producto_id": self.producto_ajeno,
                "precio_unitario": 9999,
            }]},
        )
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        with self.app.app_context():
            db = get_db()
            stock_ajeno = db.execute(
                "SELECT cantidad FROM stock_hogar WHERE hogar_id = ? AND producto_id = ?",
                (self.hogar_ajeno, self.producto_ajeno),
            ).fetchone()
            precios = db.execute(
                "SELECT COUNT(*) AS n FROM historial_precios WHERE producto_id = ?",
                (self.producto_ajeno,),
            ).fetchone()["n"]
        self.assertEqual(stock_ajeno["cantidad"], 1, "se modifico el stock de otro hogar")
        self.assertEqual(precios, 0, "se escribio historial_precios de un producto ajeno")

    def test_confirmar_acota_la_longitud_del_nombre(self):
        """M-18: sin tope, ese nombre acababa concatenado en el prompt de
        todos los escaneos hasta reventar el contexto del modelo."""
        resp = self.client.post(
            "/api/tickets/confirmar",
            json={"items": [{"nombre": "A" * 5000, "cantidad": 1}]},
        )
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True))

    def test_confirmar_con_precio_no_numerico_no_revienta(self):
        resp = self.client.post(
            "/api/tickets/confirmar",
            json={"items": [{"nombre": "Cosa", "cantidad": 1, "precio_unitario": "no-es-un-numero"}]},
        )
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
