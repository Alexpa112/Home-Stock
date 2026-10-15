"""Tests de sesiones revocables (S-08) y auditoria de eventos de seguridad (S-09)."""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class SesionesRevocablesTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = self.app.test_client()
        self.nombre_usuario = f"test_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (self.nombre_usuario, generate_password_hash("password123456"), ahora()),
            )
            self.usuario_id = cur.lastrowid
            db.commit()

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM eventos_seguridad WHERE usuario_id = ?", (self.usuario_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def _sesion_valida(self, cliente):
        with cliente.session_transaction() as sess:
            sess["usuario"] = self.nombre_usuario
            sess["usuario_id"] = self.usuario_id
            sess["session_version"] = 0

    def test_cambiar_password_invalida_otra_sesion_abierta(self):
        cliente_a = self.app.test_client()
        cliente_b = self.app.test_client()
        self._sesion_valida(cliente_a)
        self._sesion_valida(cliente_b)

        resp = cliente_a.post(
            "/api/auth/cambiar-password",
            json={
                "password_actual": "password123456",
                "password_nueva": "nuevaPassword123",
                "password_confirmacion": "nuevaPassword123",
            },
        )
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

        # cliente_a (quien hizo el cambio) sigue autenticado.
        resp_a = cliente_a.put("/api/auth/perfil", json={"nombre": "x"})
        self.assertEqual(resp_a.status_code, 200)

        # cliente_b (otra sesion con la version antigua) queda invalidado.
        resp_b = cliente_b.put("/api/auth/perfil", json={"nombre": "y"})
        self.assertEqual(resp_b.status_code, 401)

    def test_cerrar_otras_sesiones_no_invalida_la_propia(self):
        cliente_a = self.app.test_client()
        cliente_b = self.app.test_client()
        self._sesion_valida(cliente_a)
        self._sesion_valida(cliente_b)

        resp = cliente_a.post("/api/auth/cerrar-otras-sesiones")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

        resp_a = cliente_a.put("/api/auth/perfil", json={"nombre": "x"})
        self.assertEqual(resp_a.status_code, 200)

        resp_b = cliente_b.put("/api/auth/perfil", json={"nombre": "y"})
        self.assertEqual(resp_b.status_code, 401)

    def test_sesion_sin_session_version_no_se_invalida_por_compatibilidad(self):
        """Sesiones creadas antes de este cambio (sin la clave en la cookie)
        no deben quedar bloqueadas de golpe al desplegar (ver api/base.py)."""
        cliente = self.app.test_client()
        with cliente.session_transaction() as sess:
            sess["usuario"] = self.nombre_usuario
            sess["usuario_id"] = self.usuario_id
            # deliberadamente sin "session_version"

        resp = cliente.put("/api/auth/perfil", json={"nombre": "x"})
        self.assertEqual(resp.status_code, 200)


class EventosSeguridadTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = self.app.test_client()
        self.nombre_usuario = f"test_{uuid.uuid4().hex[:8]}"
        self.otro_nombre_usuario = f"test_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (self.nombre_usuario, generate_password_hash("password123456"), ahora()),
            )
            self.usuario_id = cur.lastrowid
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (self.otro_nombre_usuario, generate_password_hash("password123456"), ahora()),
            )
            self.otro_usuario_id = cur.lastrowid
            db.commit()

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM eventos_seguridad WHERE usuario_id IN (?, ?)", (self.usuario_id, self.otro_usuario_id))
            db.execute("DELETE FROM usuarios WHERE id IN (?, ?)", (self.usuario_id, self.otro_usuario_id))
            db.commit()

    def test_login_correcto_e_incorrecto_generan_evento(self):
        self.client.post("/api/auth/login", json={"usuario": self.nombre_usuario, "password": "mala"})
        self.client.post("/api/auth/login", json={"usuario": self.nombre_usuario, "password": "password123456"})

        with self.app.app_context():
            db = get_db()
            filas = db.execute(
                "SELECT resultado FROM eventos_seguridad WHERE usuario_id = ? AND evento = 'login' ORDER BY fecha",
                (self.usuario_id,),
            ).fetchall()
            self.assertEqual([f["resultado"] for f in filas], ["fallo", "ok"])

    def test_mis_eventos_seguridad_no_devuelve_eventos_de_otro_usuario(self):
        self.client.post("/api/auth/login", json={"usuario": self.otro_nombre_usuario, "password": "password123456"})

        with self.client.session_transaction() as sess:
            sess["usuario"] = self.nombre_usuario
            sess["usuario_id"] = self.usuario_id
            sess["session_version"] = 0

        resp = self.client.get("/api/auth/mis-eventos-seguridad")
        self.assertEqual(resp.status_code, 200)
        eventos = resp.get_json()
        self.assertEqual(eventos, [])


if __name__ == "__main__":
    unittest.main()
