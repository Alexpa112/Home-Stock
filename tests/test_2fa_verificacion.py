"""Los dos endpoints del segundo factor, que no cubria ningun test.

/api/auth/verificar-codigo y /api/auth/reenviar-codigo son el ultimo paso del
login de una cuenta con 2FA: si fallan, el usuario no entra. Aun asi eran de
las 35 rutas sin ninguna prueba, y encima se les cambio el comportamiento (el
reenvio ahora limpia el contador de intentos fallidos) sin nada que lo fijara.

El caso que motivo ese cambio: con MAX_INTENTOS_CODIGO fallos, la cuenta
quedaba una hora sin poder entrar NI con el codigo correcto y sin ninguna via
de recuperacion. Pedir un codigo nuevo es ahora esa via.
"""
import time
import unittest
import uuid
from unittest.mock import patch

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db
from stockhogar.rutas.auth import (
    DURACION_CODIGO_SEGUNDOS,
    MAX_INTENTOS_CODIGO,
    _hash_codigo,
)

CODIGO_BUENO = "123456"
CODIGO_MALO = "000000"


class DosFactorTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        self.nombre_usuario = f"test_2fa_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            self.usuario_id = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, email, email_verificado, "
                "doble_factor_activo, session_version, fecha_creacion) VALUES (?, ?, ?, 1, 1, 0, ?)",
                (self.nombre_usuario, generate_password_hash("password123"),
                 f"{self.nombre_usuario}@example.com", ahora()),
            ).lastrowid
            db.commit()

        # El limitador por IP (stockhogar/red.py::_contadores) es un dict de
        # modulo, compartido por todo el proceso: sin vaciarlo, los intentos
        # fallidos de un test agotan la cuota del siguiente y el 429 aparece
        # donde no toca.
        from stockhogar.red import _contadores
        _contadores.clear()

        self.client = self.app.test_client()
        self._dejar_2fa_pendiente()

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM intentos_2fa WHERE usuario_id = ?", (self.usuario_id,))
            db.execute("DELETE FROM codigos_dos_factor WHERE usuario_id = ?", (self.usuario_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def _dejar_2fa_pendiente(self, codigo=CODIGO_BUENO, expirado=False):
        """Estado en el que queda el login cuando la cuenta tiene 2FA."""
        expira = int(time.time()) + (-10 if expirado else DURACION_CODIGO_SEGUNDOS)
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM codigos_dos_factor WHERE usuario_id = ?", (self.usuario_id,))
            db.execute(
                "INSERT INTO codigos_dos_factor (usuario_id, codigo_hash, expira) VALUES (?, ?, ?)",
                (self.usuario_id, _hash_codigo(codigo), expira),
            )
            db.commit()
        with self.client.session_transaction() as sess:
            sess["pendiente_2fa_usuario_id"] = self.usuario_id

    def _fallar(self, veces):
        for _ in range(veces):
            self.client.post("/api/auth/verificar-codigo", json={"codigo": CODIGO_MALO})

    # --- camino normal -------------------------------------------------

    def test_el_codigo_correcto_abre_la_sesion(self):
        respuesta = self.client.post("/api/auth/verificar-codigo", json={"codigo": CODIGO_BUENO})
        self.assertEqual(respuesta.status_code, 200, respuesta.get_data(as_text=True))
        self.assertEqual(respuesta.get_json().get("usuario"), self.nombre_usuario)

        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("usuario"), self.nombre_usuario)
            self.assertIsNone(
                sess.get("pendiente_2fa_usuario_id"),
                "el 2FA pendiente debe consumirse al verificarlo",
            )

    def test_el_codigo_se_consume_y_no_vale_dos_veces(self):
        self.client.post("/api/auth/verificar-codigo", json={"codigo": CODIGO_BUENO})
        with self.client.session_transaction() as sess:
            sess["pendiente_2fa_usuario_id"] = self.usuario_id

        respuesta = self.client.post("/api/auth/verificar-codigo", json={"codigo": CODIGO_BUENO})
        self.assertNotEqual(respuesta.status_code, 200)

    # --- casos de error --------------------------------------------------

    def test_sin_2fa_pendiente_responde_401(self):
        cliente = self.app.test_client()
        respuesta = cliente.post("/api/auth/verificar-codigo", json={"codigo": CODIGO_BUENO})
        self.assertEqual(respuesta.status_code, 401)

    def test_codigo_incorrecto_no_abre_sesion(self):
        respuesta = self.client.post("/api/auth/verificar-codigo", json={"codigo": CODIGO_MALO})
        self.assertEqual(respuesta.status_code, 400)
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("usuario"))

    def test_codigo_caducado_se_rechaza(self):
        self._dejar_2fa_pendiente(expirado=True)
        respuesta = self.client.post("/api/auth/verificar-codigo", json={"codigo": CODIGO_BUENO})
        self.assertEqual(respuesta.status_code, 400)

    def test_cuerpo_sin_codigo_no_revienta(self):
        respuesta = self.client.post("/api/auth/verificar-codigo", json={})
        self.assertLess(respuesta.status_code, 500, respuesta.get_data(as_text=True))

    # --- bloqueo por intentos y su via de salida -------------------------

    def test_demasiados_fallos_bloquean(self):
        self._fallar(MAX_INTENTOS_CODIGO)
        self._dejar_2fa_pendiente()  # el bloqueo limpia el 2FA pendiente

        respuesta = self.client.post("/api/auth/verificar-codigo", json={"codigo": CODIGO_BUENO})
        self.assertEqual(
            respuesta.status_code, 429,
            "tras agotar los intentos la cuenta debe quedar bloqueada",
        )

    def test_pedir_un_codigo_nuevo_desbloquea(self):
        """Sin esto la cuenta quedaba 1 h fuera, ni con el codigo correcto."""
        self._fallar(MAX_INTENTOS_CODIGO)
        self._dejar_2fa_pendiente()

        with patch("stockhogar.servicios.email_service.EmailService.enviar_codigo_verificacion",
                   return_value=True):
            reenvio = self.client.post("/api/auth/reenviar-codigo", json={})
        self.assertEqual(reenvio.status_code, 200, reenvio.get_data(as_text=True))

        with self.app.app_context():
            pendientes = get_db().execute(
                "SELECT COUNT(*) AS n FROM intentos_2fa WHERE usuario_id = ? AND tipo = 'verificar'",
                (self.usuario_id,),
            ).fetchone()["n"]
        self.assertEqual(
            pendientes, 0,
            "el reenvio debe limpiar los intentos fallidos: es la unica via de "
            "recuperacion que tiene el usuario",
        )

    def test_reenviar_sin_2fa_pendiente_responde_401(self):
        cliente = self.app.test_client()
        respuesta = cliente.post("/api/auth/reenviar-codigo", json={})
        self.assertEqual(respuesta.status_code, 401)


if __name__ == "__main__":
    unittest.main()
