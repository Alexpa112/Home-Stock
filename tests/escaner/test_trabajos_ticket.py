"""Escaner asincrono: POST /api/tickets/trabajos + GET /api/tickets/trabajos/<id>.

Un analisis de ticket puede tardar minutos (Claude Vision, o el lector local en una
Raspberry Pi) y una sola peticion HTTP larga la cortaba cualquier intermediario
(proxy de Next a los 30 s, Cloudflare a los 100 s) con un 500/524. Ahora la
peticion solo crea el trabajo y responde 202 al instante; el cliente consulta.
"""
import io
import threading
import time
import unittest
import uuid
from unittest.mock import patch

from PIL import Image
from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db
from stockhogar.nucleo import red
from stockhogar.rutas.escaner import tickets as modulo_tickets


class _ClaudeFalso:
    """Motor de vision controlable: puede bloquearse hasta que el test lo libere."""

    respuesta = {"productos": [{"nombre_ticket": "Chorizo de Pamplona", "cantidad": 1, "unidad": "ud", "producto_id": None}]}
    liberar = None  # threading.Event opcional
    rutas_vistas = []

    def disponible(self):
        return True

    def procesar(self, imagen_bytes, productos_catalogo, mime=None):
        if type(self).liberar is not None:
            type(self).liberar.wait(20)
        return type(self).respuesta


class TrabajosTicketTests(unittest.TestCase):
    def setUp(self):
        # El limite por IP (30 analisis/hora) es un contador en memoria compartido por todo
        # el proceso: con el resto de tests del escaner en la misma suite se agotaria.
        red._contadores.clear()
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        nombre = f"test_job_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            self.usuario_id = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (nombre, generate_password_hash("password123"), ahora()),
            ).lastrowid
            self.hogar_id = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, 1, ?, ?)",
                ("Hogar job", self.usuario_id, ahora(), ahora()),
            ).lastrowid
            db.commit()
        self.nombre = nombre
        self.client = self._cliente(self.usuario_id, nombre)
        buffer = io.BytesIO()
        Image.new("RGB", (400, 700), (255, 255, 255)).save(buffer, format="JPEG")
        self.foto = buffer.getvalue()
        _ClaudeFalso.liberar = None

    def _cliente(self, usuario_id, nombre):
        cliente = self.app.test_client()
        with cliente.session_transaction() as sess:
            sess["usuario"] = nombre
            sess["usuario_id"] = usuario_id
            sess["hogar_actual_id"] = self.hogar_id
        return cliente

    def tearDown(self):
        _ClaudeFalso.liberar = None
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM trabajos_ticket WHERE usuario_id = ?", (self.usuario_id,))
            db.execute("DELETE FROM hogares WHERE usuario_propietario_id = ?", (self.usuario_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def _crear(self, cliente=None, nombre="ticket.jpg", contenido=None):
        return (cliente or self.client).post(
            "/api/tickets/trabajos",
            data={"foto": (io.BytesIO(contenido if contenido is not None else self.foto), nombre)},
            content_type="multipart/form-data",
        )

    def _esperar(self, trabajo_id, cliente=None, segundos=20):
        limite = time.time() + segundos
        while time.time() < limite:
            r = (cliente or self.client).get(f"/api/tickets/trabajos/{trabajo_id}")
            self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
            datos = r.get_json()
            if datos["estado"] != "procesando":
                return datos
            time.sleep(0.1)
        self.fail("el trabajo no termino a tiempo")

    def test_crear_responde_202_al_instante_y_el_resultado_llega_despues(self):
        _ClaudeFalso.liberar = threading.Event()
        with patch.object(modulo_tickets, "ClaudeOCR", _ClaudeFalso):
            inicio = time.time()
            r = self._crear()
            self.assertEqual(r.status_code, 202, r.get_data(as_text=True))
            self.assertLess(time.time() - inicio, 5, "crear el trabajo no debe esperar al analisis")
            trabajo_id = r.get_json()["id"]

            # Mientras Claude no responda, el estado es "procesando"
            self.assertEqual(self.client.get(f"/api/tickets/trabajos/{trabajo_id}").get_json(), {"estado": "procesando"})

            _ClaudeFalso.liberar.set()
            datos = self._esperar(trabajo_id)

        self.assertEqual(datos["estado"], "listo")
        self.assertEqual(datos["resultado"]["items"][0]["nombre"], "Chorizo De Pamplona")

    def test_un_formato_no_permitido_se_rechaza_sin_crear_trabajo(self):
        r = self._crear(nombre="ticket.exe", contenido=b"MZ")
        self.assertEqual(r.status_code, 400)
        with self.app.app_context():
            n = get_db().execute("SELECT COUNT(*) AS n FROM trabajos_ticket WHERE usuario_id = ?", (self.usuario_id,)).fetchone()["n"]
        self.assertEqual(n, 0)

    def test_un_contenido_que_no_es_imagen_se_rechaza(self):
        r = self._crear(nombre="ticket.jpg", contenido=b"esto no es una imagen")
        self.assertEqual(r.status_code, 400)

    def test_solo_un_trabajo_a_la_vez_por_usuario(self):
        _ClaudeFalso.liberar = threading.Event()
        with patch.object(modulo_tickets, "ClaudeOCR", _ClaudeFalso):
            primero = self._crear()
            self.assertEqual(primero.status_code, 202)
            segundo = self._crear()
            self.assertEqual(segundo.status_code, 429)
            _ClaudeFalso.liberar.set()
            self._esperar(primero.get_json()["id"])
            # Terminado el primero, se puede subir otro
            tercero = self._crear()
            self.assertEqual(tercero.status_code, 202)
            self._esperar(tercero.get_json()["id"])

    def test_nadie_mas_puede_ver_un_trabajo_ajeno(self):
        with patch.object(modulo_tickets, "ClaudeOCR", _ClaudeFalso):
            trabajo_id = self._crear().get_json()["id"]
            self._esperar(trabajo_id)
        with self.app.app_context():
            otro_id = get_db().execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (f"otro_{uuid.uuid4().hex[:8]}", generate_password_hash("password123"), ahora()),
            ).lastrowid
            get_db().commit()
        try:
            ajeno = self._cliente(otro_id, "otro")
            self.assertEqual(ajeno.get(f"/api/tickets/trabajos/{trabajo_id}").status_code, 404)
        finally:
            with self.app.app_context():
                get_db().execute("DELETE FROM usuarios WHERE id = ?", (otro_id,))
                get_db().commit()

    def test_un_trabajo_inexistente_es_404(self):
        self.assertEqual(self.client.get("/api/tickets/trabajos/no-existe").status_code, 404)

    def test_un_fallo_del_analisis_queda_como_error_y_no_cuelga(self):
        with patch.object(modulo_tickets, "_ejecutar_analisis", side_effect=RuntimeError("boom")):
            trabajo_id = self._crear().get_json()["id"]
            datos = self._esperar(trabajo_id)
        self.assertEqual(datos["estado"], "error")
        self.assertEqual(datos["http"], 500)
        self.assertTrue(datos["error"])

    def test_un_rechazo_conserva_su_clave_y_su_estado_http(self):
        rechazo = modulo_tickets._Rechazo(clave="err_procesando_ticket", status=500)
        with patch.object(modulo_tickets, "_ejecutar_analisis", side_effect=rechazo):
            datos = self._esperar(self._crear().get_json()["id"])
        self.assertEqual(datos["estado"], "error")
        self.assertEqual(datos["http"], 500)

    def test_un_trabajo_atascado_se_da_por_perdido(self):
        """El hilo murio con su worker: el cliente no debe esperar para siempre."""
        viejo = uuid.uuid4().hex
        pasado = int(time.time()) - modulo_tickets.TIEMPO_MAXIMO_TRABAJO_S - 5
        with self.app.app_context():
            get_db().execute(
                "INSERT INTO trabajos_ticket (id, usuario_id, estado, creado, actualizado) VALUES (?, ?, 'procesando', ?, ?)",
                (viejo, self.usuario_id, pasado, pasado),
            )
            get_db().commit()
        datos = self.client.get(f"/api/tickets/trabajos/{viejo}").get_json()
        self.assertEqual(datos["estado"], "error")
        self.assertEqual(datos["http"], 504)

    def test_un_trabajo_atascado_no_bloquea_subir_otro(self):
        viejo = uuid.uuid4().hex
        pasado = int(time.time()) - modulo_tickets.TIEMPO_MAXIMO_TRABAJO_S - 5
        with self.app.app_context():
            get_db().execute(
                "INSERT INTO trabajos_ticket (id, usuario_id, estado, creado, actualizado) VALUES (?, ?, 'procesando', ?, ?)",
                (viejo, self.usuario_id, pasado, pasado),
            )
            get_db().commit()
        with patch.object(modulo_tickets, "ClaudeOCR", _ClaudeFalso):
            r = self._crear()
            self.assertEqual(r.status_code, 202)
            self._esperar(r.get_json()["id"])

    def test_los_ficheros_temporales_se_borran_al_terminar(self):
        vistos = []
        original = modulo_tickets._ejecutar_analisis

        def espia(db, usuario_id, hogar_id, ruta_imagen, ruta_original, es_pdf, a_borrar):
            vistos.append(ruta_original)
            return original(db, usuario_id, hogar_id, ruta_imagen, ruta_original, es_pdf, a_borrar)

        import os
        with patch.object(modulo_tickets, "ClaudeOCR", _ClaudeFalso), patch.object(modulo_tickets, "_ejecutar_analisis", espia):
            self._esperar(self._crear().get_json()["id"])
            # el borrado ocurre en el finally del hilo, justo despues de guardar el resultado
            limite = time.time() + 5
            while time.time() < limite and os.path.exists(vistos[0]):
                time.sleep(0.05)
        self.assertFalse(os.path.exists(vistos[0]))

    def test_la_ruta_sincrona_antigua_sigue_funcionando(self):
        with patch.object(modulo_tickets, "ClaudeOCR", _ClaudeFalso):
            r = self.client.post(
                "/api/tickets/analizar",
                data={"foto": (io.BytesIO(self.foto), "ticket.jpg")},
                content_type="multipart/form-data",
            )
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        self.assertEqual(r.get_json()["items"][0]["nombre"], "Chorizo De Pamplona")


if __name__ == "__main__":
    unittest.main()
