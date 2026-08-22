"""Tests de suscripciones push (P-01) y del script de avisos de caducidad
(P-07)."""
import base64
import importlib.util
import shutil
import stat
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db
from stockhogar.servicios import push_service


class SuscripcionesPushTests(unittest.TestCase):
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
        with self.client.session_transaction() as sess:
            sess["usuario"] = self.nombre_usuario
            sess["usuario_id"] = self.usuario_id

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM push_subscriptions WHERE usuario_id = ?", (self.usuario_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def test_vapid_clave_publica_devuelve_string(self):
        """Ya no se salta si falta py-vapid: es dependencia obligatoria en
        requirements.txt. Cuando estaba comentada, este test se saltaba y tapaba
        que la clave publica se servia VACIA, con lo que activar las
        notificaciones era imposible."""
        resp = self.client.get("/api/push/vapid-clave-publica")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertTrue(
            resp.get_json()["clave_publica"],
            "clave publica VAPID vacia: el navegador no puede suscribirse",
        )

    def test_borrar_el_usuario_borra_sus_suscripciones(self):
        """La politica de privacidad declara que desactivar/eliminar la cuenta
        borra la suscripcion: depende de ON DELETE CASCADE, que a su vez depende
        de PRAGMA foreign_keys (db.py). Si alguien lo apagara, quedarian
        endpoints huerfanos de cuentas ya borradas."""
        endpoint = f"https://fcm.googleapis.com/fake/{uuid.uuid4().hex}"
        self.client.post(
            "/api/push/suscribir",
            json={"endpoint": endpoint, "keys": {"p256dh": "p", "auth": "a"}},
        )
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()
            fila = db.execute(
                "SELECT id FROM push_subscriptions WHERE endpoint = ?", (endpoint,)
            ).fetchone()
            self.assertIsNone(fila, "la suscripcion sobrevive al borrado de la cuenta")

    def test_suscribir_y_desuscribir(self):
        endpoint = f"https://fcm.googleapis.com/fake/{uuid.uuid4().hex}"
        resp = self.client.post(
            "/api/push/suscribir",
            json={"endpoint": endpoint, "keys": {"p256dh": "clave-p256dh", "auth": "clave-auth"}},
        )
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

        with self.app.app_context():
            db = get_db()
            fila = db.execute("SELECT * FROM push_subscriptions WHERE endpoint = ?", (endpoint,)).fetchone()
            self.assertIsNotNone(fila)
            self.assertEqual(fila["usuario_id"], self.usuario_id)

        resp_desuscribir = self.client.post("/api/push/desuscribir", json={"endpoint": endpoint})
        self.assertEqual(resp_desuscribir.status_code, 200)
        with self.app.app_context():
            db = get_db()
            fila = db.execute("SELECT * FROM push_subscriptions WHERE endpoint = ?", (endpoint,)).fetchone()
            self.assertIsNone(fila)

    def test_resuscribir_mismo_endpoint_actualiza_claves(self):
        endpoint = f"https://fcm.googleapis.com/fake/{uuid.uuid4().hex}"
        self.client.post(
            "/api/push/suscribir",
            json={"endpoint": endpoint, "keys": {"p256dh": "vieja", "auth": "vieja"}},
        )
        resp = self.client.post(
            "/api/push/suscribir",
            json={"endpoint": endpoint, "keys": {"p256dh": "nueva", "auth": "nueva"}},
        )
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

        with self.app.app_context():
            db = get_db()
            filas = db.execute("SELECT * FROM push_subscriptions WHERE endpoint = ?", (endpoint,)).fetchall()
            self.assertEqual(len(filas), 1)
            self.assertEqual(filas[0]["p256dh"], "nueva")

    def test_suscripcion_sin_claves_se_rechaza(self):
        resp = self.client.post("/api/push/suscribir", json={"endpoint": "https://x.example"})
        self.assertEqual(resp.status_code, 400)


class EnviarPushTests(unittest.TestCase):
    """Tests de stockhogar.servicios.push_service, mockeando pywebpush.webpush
    para no hacer llamadas de red reales."""

    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True)

    @patch("stockhogar.servicios.push_service.webpush")
    def test_enviar_push_con_suscripcion_caducada_la_borra(self, mock_webpush):
        from pywebpush import WebPushException

        from stockhogar.servicios.push_service import enviar_push

        respuesta_falsa = MagicMock()
        respuesta_falsa.status_code = 410
        mock_webpush.side_effect = WebPushException("caducada", response=respuesta_falsa)

        with self.app.app_context():
            db = get_db()
            nombre = f"test_{uuid.uuid4().hex[:8]}"
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (nombre, generate_password_hash("password123456"), ahora()),
            )
            usuario_id = cur.lastrowid
            cur = db.execute(
                "INSERT INTO push_subscriptions (usuario_id, endpoint, p256dh, auth, fecha_creacion) "
                "VALUES (?, ?, ?, ?, ?)",
                (usuario_id, f"https://x.example/{uuid.uuid4().hex}", "p", "a", ahora()),
            )
            suscripcion_id = cur.lastrowid
            db.commit()

            suscripcion = db.execute("SELECT * FROM push_subscriptions WHERE id = ?", (suscripcion_id,)).fetchone()
            resultado = enviar_push(db, suscripcion, "titulo", "cuerpo")

            self.assertFalse(resultado)
            fila = db.execute("SELECT * FROM push_subscriptions WHERE id = ?", (suscripcion_id,)).fetchone()
            self.assertIsNone(fila)

            db.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
            db.commit()

    @patch("stockhogar.servicios.push_service.webpush")
    def test_enviar_push_exitoso_devuelve_true(self, mock_webpush):
        from stockhogar.servicios.push_service import enviar_push

        mock_webpush.return_value = None
        with self.app.app_context():
            db = get_db()
            suscripcion = {"id": 1, "endpoint": "https://x.example/y", "p256dh": "p", "auth": "a"}
            self.assertTrue(enviar_push(db, suscripcion, "titulo", "cuerpo"))


class ClaveVapidTests(unittest.TestCase):
    """La clave VAPID identifica al SERVIDOR ante el servicio push de cada
    navegador. push_service.py solo la CARGABA `if ruta.exists()` y nada la
    generaba nunca, asi que `_vapid` quedaba en None para siempre y
    `clave_publica_vapid()` devolvia "": el navegador no tenia con que
    suscribirse y el interruptor de Ajustes no podia funcionar en ningun
    despliegue. Estos tests atan la generacion."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.ruta = Path(self.tmp) / "vapid_private_key.pem"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _con_ruta_temporal(self):
        return patch.object(push_service, "_VAPID_KEY_PATH", self.ruta)

    def test_la_clave_se_genera_si_el_fichero_no_existe(self):
        with self._con_ruta_temporal():
            self.assertFalse(self.ruta.exists())
            vapid = push_service._cargar_o_crear_vapid()
            self.assertTrue(self.ruta.exists(), "no se genero data/vapid_private_key.pem")
            self.assertIsNotNone(vapid)

    def test_la_clave_privada_se_crea_con_permisos_0600(self):
        with self._con_ruta_temporal():
            push_service._cargar_o_crear_vapid()
            self.assertEqual(stat.S_IMODE(self.ruta.stat().st_mode), 0o600)

    def test_la_clave_no_cambia_entre_arranques(self):
        """Si cambiara, las suscripciones ya entregadas al navegador (que
        guarda la clave publica con la que se suscribio) dejarian de valer."""
        with self._con_ruta_temporal():
            push_service._cargar_o_crear_vapid()
            primera = self.ruta.read_bytes()
            push_service._cargar_o_crear_vapid()
            self.assertEqual(self.ruta.read_bytes(), primera)

    def test_dos_workers_a_la_vez_no_se_pisan_la_clave(self):
        """Con varios workers de gunicorn arrancando en paralelo, el segundo en
        crear el fichero no debe sobrescribir la clave del primero (O_EXCL)."""
        with self._con_ruta_temporal():
            push_service._crear_clave_vapid()
            primera = self.ruta.read_bytes()
            push_service._crear_clave_vapid()  # El que pierde la carrera.
            self.assertEqual(self.ruta.read_bytes(), primera)

    def test_la_clave_publica_es_un_punto_p256_sin_comprimir(self):
        """Formato que exige PushManager.subscribe({applicationServerKey}):
        base64url sin padding de 65 bytes (0x04 + X + Y)."""
        with self._con_ruta_temporal():
            vapid = push_service._cargar_o_crear_vapid()
            with patch.object(push_service, "_vapid", vapid):
                clave = push_service.clave_publica_vapid()

        self.assertTrue(clave)
        self.assertNotIn("=", clave)
        crudo = base64.urlsafe_b64decode(clave + "=" * (-len(clave) % 4))
        self.assertEqual(len(crudo), 65)
        self.assertEqual(crudo[0], 0x04)

    def test_install_sh_programa_el_cron_de_avisos_de_caducidad(self):
        """El script de avisos se escribio para un cron diario y ese cron no se
        instalaba en ningun sitio: se podian activar las notificaciones y no
        llegar nunca ninguna, porque nadie ejecutaba el script."""
        raiz = Path(__file__).resolve().parent.parent
        instalador = (raiz / "install.sh").read_text(encoding="utf-8")
        self.assertIn(
            "enviar_avisos_caducidad.py", instalador,
            "install.sh no programa el envio de avisos: las notificaciones push "
            "se activarian pero no llegaria ninguna",
        )
        self.assertIn("crontab -", instalador)

    def test_requirements_declara_las_dependencias_de_push(self):
        """Estuvieron comentadas ("opcional, se instala en produccion"), asi que
        ningun despliegue construido desde requirements.txt podia enviar push."""
        texto = Path(__file__).resolve().parent.parent / "requirements.txt"
        lineas = [
            l.strip() for l in texto.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.strip().startswith("#")
        ]
        for paquete in ("py-vapid", "pywebpush"):
            with self.subTest(paquete=paquete):
                self.assertTrue(
                    any(l.startswith(paquete) for l in lineas),
                    f"{paquete} no esta declarado (o sigue comentado) en requirements.txt",
                )


class AvisosCaducidadScriptTests(unittest.TestCase):
    """Tests del script scripts/enviar_avisos_caducidad.py: se importa como
    modulo (no se ejecuta como subproceso) para poder mockear el envio push
    y no depender de tesseract/servidor ni de red real."""

    @classmethod
    def setUpClass(cls):
        ruta = Path(__file__).resolve().parent.parent / "scripts" / "enviar_avisos_caducidad.py"
        spec = importlib.util.spec_from_file_location("enviar_avisos_caducidad", ruta)
        cls.modulo = importlib.util.module_from_spec(spec)
        sys.modules["enviar_avisos_caducidad"] = cls.modulo
        spec.loader.exec_module(cls.modulo)

    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True)
        with self.app.app_context():
            db = get_db()
            sufijo = uuid.uuid4().hex[:8]
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (f"test_{sufijo}", generate_password_hash("password123456"), ahora()),
            )
            self.usuario_id = cur.lastrowid
            cur = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES ('Hogar caducidad', ?, 1, ?, ?)",
                (self.usuario_id, ahora(), ahora()),
            )
            self.hogar_id = cur.lastrowid
            fecha_vieja = "2020-01-01T00:00:00"
            cur = db.execute(
                "INSERT INTO productos (nombre, categoria, cantidad, unidad, stock_minimo, fecha_creacion, "
                "fecha_actualizacion, dias_aviso) VALUES ('Leche caducidad test', 'Otros', 1, 'ud', 1, ?, ?, 5)",
                (fecha_vieja, fecha_vieja),
            )
            self.producto_id = cur.lastrowid
            db.execute(
                "INSERT INTO stock_hogar (hogar_id, producto_id, cantidad, stock_minimo, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, 1, 1, ?, ?)",
                (self.hogar_id, self.producto_id, ahora(), ahora()),
            )
            db.commit()

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM stock_hogar WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM productos WHERE id = ?", (self.producto_id,))
            db.execute("DELETE FROM hogares WHERE id = ?", (self.hogar_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def _llamadas_para_mi_usuario(self, mock_enviar):
        # La BD es la real de la app (no aislada por test, ver conftest.py
        # y el resto de tests de este proyecto): puede haber otros
        # productos vencidos de datos previos, asi que se filtra por el
        # usuario_id de este test en vez de asumir que el mock no se llamo
        # para NADA.
        return [c for c in mock_enviar.call_args_list if c.args[1] == self.usuario_id]

    @patch("enviar_avisos_caducidad.enviar_push_a_usuario", return_value=1)
    def test_producto_vencido_genera_aviso_y_marca_fecha(self, mock_enviar):
        self.modulo.main()
        self.assertTrue(self._llamadas_para_mi_usuario(mock_enviar))

        with self.app.app_context():
            db = get_db()
            fila = db.execute(
                "SELECT fecha_ultimo_aviso_caducidad FROM productos WHERE id = ?", (self.producto_id,)
            ).fetchone()
            self.assertIsNotNone(fila["fecha_ultimo_aviso_caducidad"])

    @patch("enviar_avisos_caducidad.enviar_push_a_usuario", return_value=1)
    def test_no_reavisar_antes_de_repetir_aviso_tras_dias(self, mock_enviar):
        with self.app.app_context():
            db = get_db()
            db.execute(
                "UPDATE productos SET fecha_ultimo_aviso_caducidad = ? WHERE id = ?",
                (ahora(), self.producto_id),
            )
            db.commit()

        mock_enviar.reset_mock()
        self.modulo.main()
        self.assertFalse(self._llamadas_para_mi_usuario(mock_enviar))


if __name__ == "__main__":
    unittest.main()
