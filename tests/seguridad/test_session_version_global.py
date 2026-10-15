"""Regresion: una sesion revocada deja de valer en TODAS las rutas.

Bug real: la comprobacion de session_version vivia solo dentro del decorador
@requerir_sesion, pero el guardian global (exigir_sesion) se limitaba a mirar
que existiese session["usuario"]. Las rutas que leen la sesion sin ese
decorador seguian sirviendo datos con una cookie ya revocada; la mas seria es
/api/auth/estado, que esta en RUTAS_PUBLICAS y devuelve email, nombre y
preferencias del usuario.

Escenario: a la victima le roban la cookie y pulsa "cerrar otras sesiones"
(o cambia la contraseña), lo que sube usuarios.session_version. El resto de
rutas empiezan a rechazar la cookie robada, pero /api/auth/estado seguia
devolviendo sus datos durante los 365 dias de DIAS_SESION.
"""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class SessionVersionGlobalTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        self.nombre_usuario = f"test_sv_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, email, session_version, fecha_creacion) "
                "VALUES (?, ?, ?, 0, ?)",
                (self.nombre_usuario, generate_password_hash("password123"),
                 f"{self.nombre_usuario}@example.com", ahora()),
            )
            self.usuario_id = cur.lastrowid
            db.commit()

        # Cookie emitida cuando la sesion valia (session_version = 0).
        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess["usuario"] = self.nombre_usuario
            sess["usuario_id"] = self.usuario_id
            sess["session_version"] = 0

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def _revocar_sesiones(self):
        """Equivale a 'cerrar otras sesiones' / cambiar la contraseña."""
        with self.app.app_context():
            db = get_db()
            db.execute(
                "UPDATE usuarios SET session_version = session_version + 1 WHERE id = ?",
                (self.usuario_id,),
            )
            db.commit()

    def test_estado_deja_de_exponer_los_datos_tras_revocar(self):
        antes = self.client.get("/api/auth/estado").get_json()
        self.assertEqual(antes.get("usuario"), self.nombre_usuario)

        self._revocar_sesiones()

        despues = self.client.get("/api/auth/estado").get_json()
        self.assertIsNone(
            despues.get("usuario"),
            "una cookie revocada no debe seguir identificando al usuario",
        )
        self.assertIsNone(
            despues.get("email"),
            "una cookie revocada no debe seguir devolviendo el email del usuario",
        )

    def test_ruta_protegida_tambien_rechaza(self):
        self.assertNotEqual(self.client.get("/api/listas").status_code, 401)

        self._revocar_sesiones()

        self.assertEqual(self.client.get("/api/listas").status_code, 401)

    def test_una_sesion_vigente_sigue_funcionando(self):
        respuesta = self.client.get("/api/auth/estado").get_json()
        self.assertEqual(respuesta.get("usuario"), self.nombre_usuario)
        self.assertNotEqual(self.client.get("/api/listas").status_code, 401)

    def test_cookie_antigua_sin_session_version_no_se_expulsa(self):
        """Compatibilidad: cookies emitidas antes de existir el campo."""
        cliente = self.app.test_client()
        with cliente.session_transaction() as sess:
            sess["usuario"] = self.nombre_usuario
            sess["usuario_id"] = self.usuario_id
            # sin session_version, como las cookies previas al despliegue

        self._revocar_sesiones()

        self.assertEqual(
            cliente.get("/api/auth/estado").get_json().get("usuario"),
            self.nombre_usuario,
            "no se debe forzar un cierre de sesion masivo de cookies ya emitidas",
        )


if __name__ == "__main__":
    unittest.main()
