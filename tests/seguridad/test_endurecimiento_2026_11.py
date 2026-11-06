"""Tests de regresion de la auditoria de seguridad de 2026-11 sobre produccion:

1. Los limites de tasa de reset-password y registro deben persistir en SQLite
   (no en memoria del proceso), igual que ya hacia intentos_login.py: con
   gunicorn --workers 2, un dict en memoria por proceso daba hasta el doble
   del limite nominal, porque cada worker llevaba su propio contador.
2. generar_enlace_compartible debe respetar la misma cuota diaria de
   invitaciones por hogar que /compartir (ambos insertan en
   invitaciones_hogar).
3. El nombre_usuario derivado del email en el alta por OAuth debe acotarse al
   mismo limite de longitud (50) que usa el registro normal.
"""
import unittest
import unittest.mock
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db
from stockhogar.nucleo import limite_persistido


class LimitePersistidoTests(unittest.TestCase):
    """Unidad: el contador debe sobrevivir a una app/contexto nuevo (lo que
    en produccion equivale a otro worker de gunicorn), a diferencia de un
    dict en memoria del proceso."""

    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.ctx = self.app.app_context()
        self.ctx.push()
        get_db().execute("DELETE FROM intentos_login")
        get_db().commit()

    def tearDown(self):
        get_db().execute("DELETE FROM intentos_login")
        get_db().commit()
        self.ctx.pop()

    def test_respeta_el_limite_dentro_de_la_ventana(self):
        clave = f"test_clave_{uuid.uuid4().hex[:8]}"
        for _ in range(3):
            self.assertFalse(limite_persistido.superado(clave, 3, 60))
        # El cuarto uso ya supera max_por_ventana=3.
        self.assertTrue(limite_persistido.superado(clave, 3, 60))

    def test_el_limite_se_comparte_entre_contextos_de_app_distintos(self):
        """Simula dos workers de gunicorn: cada uno con su propio create_app()
        pero compartiendo el mismo fichero SQLite (parcheado por conftest).
        Antes del fix (dict en memoria) cada "worker" habria visto su propio
        contador vacio y ninguno habria llegado al tope."""
        clave = f"test_workers_{uuid.uuid4().hex[:8]}"

        # "Worker 1": agota el limite.
        for _ in range(3):
            limite_persistido.superado(clave, 3, 60)

        # "Worker 2": otro app/contexto, misma clave.
        app2 = create_app()
        app2.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        with app2.app_context():
            self.assertTrue(
                limite_persistido.superado(clave, 3, 60),
                "el contador debe persistir entre contextos/procesos distintos",
            )


class RateLimitEndpointsPersistidosTests(unittest.TestCase):
    """Integracion: los endpoints de registro y reset-password deben bloquear
    tras el limite incluso si la peticion llega a traves de un "worker"
    (app/cliente) distinto al que registro los intentos anteriores."""

    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = self.app.test_client()
        with self.app.app_context():
            get_db().execute("DELETE FROM intentos_login")
            get_db().commit()

    def tearDown(self):
        with self.app.app_context():
            get_db().execute("DELETE FROM intentos_login")
            get_db().commit()

    def test_registro_se_bloquea_tras_el_limite_en_otro_worker(self):
        ip = "203.0.113.50"
        # Agota el limite (10/hora) desde un primer "worker".
        for i in range(10):
            self.client.post(
                "/api/auth/registrar",
                json={
                    "usuario": f"ratelimit_{uuid.uuid4().hex[:8]}",
                    "password": "password123xyz",
                    "acepta_terminos": True,
                },
                environ_overrides={"REMOTE_ADDR": ip},
            )

        # Un segundo "worker" (app/cliente nuevo, misma BD compartida) debe
        # ver el limite ya agotado, no empezar de cero.
        app_otro_worker = create_app()
        app_otro_worker.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        cliente_otro_worker = app_otro_worker.test_client()
        resp = cliente_otro_worker.post(
            "/api/auth/registrar",
            json={
                "usuario": f"ratelimit_{uuid.uuid4().hex[:8]}",
                "password": "password123xyz",
                "acepta_terminos": True,
            },
            environ_overrides={"REMOTE_ADDR": ip},
        )
        self.assertEqual(resp.status_code, 429, resp.get_data(as_text=True))

        with self.app.app_context():
            get_db().execute("DELETE FROM usuarios WHERE nombre_usuario LIKE 'ratelimit_%'")
            get_db().commit()

    def test_reset_password_se_bloquea_tras_el_limite_en_otro_worker(self):
        ip = "203.0.113.51"
        for i in range(5):
            self.client.post(
                "/api/auth/solicitar-reset-password",
                json={"usuario_o_email": "nadie@example.com"},
                environ_overrides={"REMOTE_ADDR": ip},
            )

        app_otro_worker = create_app()
        app_otro_worker.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        cliente_otro_worker = app_otro_worker.test_client()
        resp = cliente_otro_worker.post(
            "/api/auth/solicitar-reset-password",
            json={"usuario_o_email": "nadie@example.com"},
            environ_overrides={"REMOTE_ADDR": ip},
        )
        self.assertEqual(resp.status_code, 429, resp.get_data(as_text=True))


class EnlaceCompartibleCuotaTests(unittest.TestCase):
    """El enlace publico de invitacion debe respetar la misma cuota diaria
    por hogar que /compartir, al insertar en la misma tabla."""

    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = self.app.test_client()
        self.sufijo = uuid.uuid4().hex[:8]

        with self.app.app_context():
            db = get_db()
            self.usuario_id = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (f"propietario_{self.sufijo}", generate_password_hash("password123"), ahora()),
            ).lastrowid
            self.hogar_id = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, "
                "fecha_actualizacion) VALUES (?, ?, 1, ?, ?)",
                (f"Hogar {self.sufijo}", self.usuario_id, ahora(), ahora()),
            ).lastrowid
            db.commit()

        with self.client.session_transaction() as sess:
            sess["usuario"] = f"propietario_{self.sufijo}"
            sess["usuario_id"] = self.usuario_id
            sess["hogar_actual_id"] = self.hogar_id

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM invitaciones_hogar WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM hogares WHERE id = ?", (self.hogar_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def test_enlace_compartible_respeta_cuota_diaria_del_hogar(self):
        with unittest.mock.patch(
            "stockhogar.rutas.hogar.permisos.LIMITE_INVITACIONES_DIARIO_POR_HOGAR", 2
        ):
            for _ in range(2):
                resp = self.client.post(f"/api/hogares/{self.hogar_id}/enlace-compartible")
                self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

            resp = self.client.post(f"/api/hogares/{self.hogar_id}/enlace-compartible")
            self.assertEqual(resp.status_code, 429, resp.get_data(as_text=True))

    def test_enlace_compartible_comparte_cuota_con_compartir_por_email(self):
        """La cuota es por hogar y cubre ambos caminos: agotarla con uno debe
        bloquear tambien al otro."""
        with unittest.mock.patch(
            "stockhogar.rutas.hogar.permisos.LIMITE_INVITACIONES_DIARIO_POR_HOGAR", 1
        ):
            resp = self.client.post(
                f"/api/hogares/{self.hogar_id}/compartir",
                json={"email": "invitado@example.com"},
            )
            self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

            resp = self.client.post(f"/api/hogares/{self.hogar_id}/enlace-compartible")
            self.assertEqual(resp.status_code, 429, resp.get_data(as_text=True))


class OAuthNombreUsuarioAcotadoTests(unittest.TestCase):
    """El nombre_usuario generado en el alta por OAuth debe acotarse al mismo
    limite de longitud (50) que Validator.string_requerido aplica en el
    registro normal, para no crear filas que luego fallen otras
    validaciones."""

    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = self.app.test_client()
        self.email = f"{'x' * 80}@example.com"

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM oauth_accounts WHERE email = ?", (self.email,))
            db.execute("DELETE FROM usuarios WHERE email = ?", (self.email,))
            db.commit()

    def _iniciar_state(self):
        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "estado-de-prueba"

    @unittest.mock.patch("stockhogar.rutas.cuenta.oauth.requests.get")
    @unittest.mock.patch("stockhogar.rutas.cuenta.oauth.requests.post")
    def test_nombre_usuario_oauth_se_acota_a_50_caracteres(self, mock_post, mock_get):
        respuesta_token = unittest.mock.MagicMock()
        respuesta_token.raise_for_status.return_value = None
        respuesta_token.json.return_value = {"access_token": "token-falso"}

        respuesta_usuario = unittest.mock.MagicMock()
        respuesta_usuario.raise_for_status.return_value = None
        respuesta_usuario.json.return_value = {
            "email": self.email,
            "verified_email": True,
            "name": "Usuario Nombre Larguisimo",
            "id": f"google-id-{uuid.uuid4().hex[:8]}",
            "picture": None,
        }
        mock_post.return_value, mock_get.return_value = respuesta_token, respuesta_usuario

        self._iniciar_state()
        resp = self.client.get("/auth/google/callback?code=codigo-falso&state=estado-de-prueba")
        self.assertEqual(resp.status_code, 302)

        with self.app.app_context():
            fila = get_db().execute(
                "SELECT nombre_usuario FROM usuarios WHERE email = ?", (self.email,)
            ).fetchone()
            self.assertIsNotNone(fila)
            self.assertLessEqual(len(fila["nombre_usuario"]), 50)


if __name__ == "__main__":
    unittest.main()
