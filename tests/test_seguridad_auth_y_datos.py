"""Auditoria de seguridad: autenticacion, sesion y fuga de datos personales.

Cuatro frentes que no cubria ningun test:

1. Fuerza bruta: el limite de intentos de login debe llegar a activarse de
   verdad, y no debe poder eludirse cambiando la cabecera CF-Connecting-IP
   (ya cubierto en test_ip_cliente_cabecera.py a nivel de funcion; aqui se
   comprueba de punta a punta contra el endpoint).
2. Enumeracion de usuarios: la respuesta a un usuario que NO existe debe ser
   indistinguible de la de una contraseña incorrecta.
3. Falsificacion de cookie: una cookie de sesion inventada o manipulada no
   debe autenticar. Es la unica cosa que separa a un anonimo de cualquier
   cuenta, porque la sesion es de 365 dias.
4. Exportacion RGPD: solo debe contener datos de quien la pide.
"""
import json
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class FuerzaBrutaLoginTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        from stockhogar.red import _contadores
        _contadores.clear()

        self.nombre = f"fb_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            self.usuario_id = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) "
                "VALUES (?, ?, ?)",
                (self.nombre, generate_password_hash("PasswordCorrecta123"), ahora()),
            ).lastrowid
            db.execute("DELETE FROM intentos_login")
            db.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM intentos_login")
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def _login(self, password, cabeceras=None):
        return self.client.post(
            "/api/auth/login",
            json={"usuario": self.nombre, "password": password},
            headers=cabeceras or {},
        )

    def test_el_limite_de_intentos_se_activa(self):
        codigos = [self._login("mala").status_code for _ in range(12)]
        self.assertIn(
            429, codigos,
            "tras una docena de intentos fallidos deberia haber bloqueo; "
            f"codigos vistos: {sorted(set(codigos))}",
        )

    def test_una_cuenta_atacada_desde_muchas_ips_acaba_bloqueada(self):
        """Hallazgo de la auditoria: los dos cubos originales llevaban la IP en
        la clave, asi que quien pudiera variar la IP percibida (lista de
        proxies, o falseando CF-Connecting-IP contra el proxy del frontend
        desde la red local) tenia intentos ILIMITADOS contra una sola cuenta.
        El cubo por cuenta, sin IP, es el que lo acota."""
        from stockhogar.servicios.intentos_login import MAX_INTENTOS_CUENTA
        codigos = []
        for n in range(MAX_INTENTOS_CUENTA + 5):
            # Una IP distinta en cada intento: cada uno cae en un cubo por IP
            # nuevo, y solo el cubo por cuenta puede detenerlo.
            codigos.append(
                self._login("mala", {"CF-Connecting-IP": f"203.0.113.{n % 250}"}).status_code
            )
        self.assertIn(
            429, codigos,
            "una sola cuenta admite intentos ilimitados si el atacante varia la "
            f"IP en cada peticion: codigos {sorted(set(codigos))}",
        )

    def test_el_cubo_por_cuenta_no_deja_fuera_a_un_usuario_normal(self):
        """Contrapartida del cubo por cuenta: un tercero no debe poder bloquear
        la cuenta de otro con unos pocos fallos. El umbral por cuenta es mas
        alto que el de IP a proposito."""
        from stockhogar.servicios.intentos_login import MAX_INTENTOS, MAX_INTENTOS_CUENTA
        self.assertGreater(
            MAX_INTENTOS_CUENTA, MAX_INTENTOS,
            "si el umbral por cuenta no fuera mas alto, cualquiera podria dejar "
            "fuera al dueño de una cuenta con MAX_INTENTOS fallos",
        )

    def test_la_contrasena_correcta_entra_antes_del_bloqueo(self):
        """Contraprueba: el login funciona, no es que rechace siempre."""
        respuesta = self._login("PasswordCorrecta123")
        self.assertEqual(respuesta.status_code, 200, respuesta.get_data(as_text=True))


class EnumeracionUsuariosTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        from stockhogar.red import _contadores
        _contadores.clear()

        self.nombre = f"enum_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            self.usuario_id = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, email, fecha_creacion) "
                "VALUES (?, ?, ?, ?)",
                (self.nombre, generate_password_hash("PasswordCorrecta123"),
                 f"{self.nombre}@example.com", ahora()),
            ).lastrowid
            db.execute("DELETE FROM intentos_login")
            db.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM intentos_login")
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def test_usuario_inexistente_responde_igual_que_password_incorrecta(self):
        existente = self.client.post(
            "/api/auth/login", json={"usuario": self.nombre, "password": "mala"})
        inexistente = self.client.post(
            "/api/auth/login", json={"usuario": f"nadie_{uuid.uuid4().hex[:8]}", "password": "mala"})

        self.assertEqual(
            existente.status_code, inexistente.status_code,
            "el codigo de respuesta permite distinguir si el usuario existe",
        )
        self.assertEqual(
            existente.get_json(), inexistente.get_json(),
            "el mensaje de error permite distinguir si el usuario existe",
        )

    def test_el_reset_de_password_no_revela_si_el_email_existe(self):
        conocido = self.client.post(
            "/api/auth/solicitar-reset-password", json={"email": f"{self.nombre}@example.com"})
        desconocido = self.client.post(
            "/api/auth/solicitar-reset-password", json={"email": "nadie@example.com"})

        self.assertEqual(conocido.status_code, desconocido.status_code)
        self.assertEqual(
            conocido.get_json(), desconocido.get_json(),
            "la respuesta revela si ese email tiene cuenta",
        )


class CookieDeSesionTests(unittest.TestCase):
    """La sesion dura 365 dias: la firma de la cookie es lo unico que la
    protege, asi que una cookie inventada no puede autenticar."""

    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    def test_una_cookie_inventada_no_autentica(self):
        cliente = self.app.test_client()
        cliente.set_cookie("session", "esto-no-esta-firmado", domain="localhost")
        respuesta = cliente.get("/api/articulos")
        self.assertEqual(respuesta.status_code, 401, respuesta.get_data(as_text=True))

    def test_una_cookie_manipulada_no_autentica(self):
        """Se toma una cookie legitima y se le cambia un byte."""
        nombre = f"cookie_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            usuario_id = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) "
                "VALUES (?, ?, ?)",
                (nombre, generate_password_hash("password123"), ahora()),
            ).lastrowid
            db.commit()
        self.addCleanup(self._borrar_usuario, usuario_id)

        cliente = self.app.test_client()
        with cliente.session_transaction() as sess:
            sess["usuario"] = nombre
            sess["usuario_id"] = usuario_id

        cookie = next((c for c in cliente._cookies.values() if "session" in str(c)), None)
        self.assertIsNotNone(cookie, "no se ha podido leer la cookie de sesion")

        # La sesion legitima funciona...
        self.assertNotEqual(cliente.get("/api/articulos").status_code, 401)

        # ...y manipulada, no.
        otro = self.app.test_client()
        valor = list(cliente._cookies.values())[0].value
        otro.set_cookie("session", valor[:-3] + "AAA", domain="localhost")
        self.assertEqual(
            otro.get("/api/articulos").status_code, 401,
            "una cookie con la firma alterada sigue autenticando",
        )

    def _borrar_usuario(self, usuario_id):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
            db.commit()


class ExportacionRgpdTests(unittest.TestCase):
    """La exportacion de datos personales solo debe traer los de quien pide."""

    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        sufijo = uuid.uuid4().hex[:8]

        with self.app.app_context():
            db = get_db()
            self.yo = f"rgpd_yo_{sufijo}"
            self.yo_id = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, email, fecha_creacion) "
                "VALUES (?, ?, ?, ?)",
                (self.yo, generate_password_hash("password123"), f"{self.yo}@example.com", ahora()),
            ).lastrowid
            self.otro = f"rgpd_otro_{sufijo}"
            self.otro_id = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, email, fecha_creacion) "
                "VALUES (?, ?, ?, ?)",
                (self.otro, generate_password_hash("password123"),
                 f"{self.otro}@example.com", ahora()),
            ).lastrowid
            self.hogar_otro = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, "
                "fecha_actualizacion) VALUES (?, ?, 1, ?, ?)",
                ("Hogar del otro", self.otro_id, ahora(), ahora()),
            ).lastrowid
            db.execute(
                "INSERT INTO articulos_compra (hogar_id, nombre, fecha_creacion, "
                "fecha_actualizacion) VALUES (?, ?, ?, ?)",
                (self.hogar_otro, f"SecretoDelOtro{sufijo}", ahora(), ahora()),
            )
            db.commit()
        self.sufijo = sufijo

        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess["usuario"] = self.yo
            sess["usuario_id"] = self.yo_id

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM articulos_compra WHERE hogar_id = ?", (self.hogar_otro,))
            db.execute("DELETE FROM hogares WHERE id = ?", (self.hogar_otro,))
            db.execute("DELETE FROM usuarios WHERE id IN (?, ?)", (self.yo_id, self.otro_id))
            db.commit()

    def test_la_exportacion_no_incluye_datos_de_otros(self):
        respuesta = self.client.get("/api/auth/exportar-mis-datos")
        if respuesta.status_code == 404:
            self.skipTest("este despliegue no expone /api/auth/exportar-mis-datos")
        # Sin as_text: el cuerpo es un ZIP binario y decodificarlo revienta.
        self.assertEqual(respuesta.status_code, 200, respuesta.status)

        # Es un ZIP: comprimido, buscar en los bytes crudos no probaria nada.
        import io, zipfile
        with zipfile.ZipFile(io.BytesIO(respuesta.get_data())) as z:
            texto = "\n".join(
                z.read(nombre).decode("utf-8", errors="replace") for nombre in z.namelist()
            )
        self.assertNotIn(
            f"SecretoDelOtro{self.sufijo}", texto,
            "la exportacion incluye articulos de OTRO usuario",
        )
        self.assertNotIn(
            f"{self.otro}@example.com", texto,
            "la exportacion incluye el email de OTRO usuario",
        )
        self.assertIn(
            self.yo, texto,
            "la exportacion deberia contener los datos de quien la pide",
        )


if __name__ == "__main__":
    unittest.main()
