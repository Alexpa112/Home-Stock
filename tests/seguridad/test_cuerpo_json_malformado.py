"""Regresion: un cuerpo JSON mal formado debe dar 400, nunca 500.

Las rutas leian el cuerpo con `request.get_json(force=True) or {}`, que acepta
cualquier JSON valido. Con un cuerpo escalar (`5`) o una lista, `datos` NO era
un dict y el primer `datos.get(...)` lanzaba AttributeError, que
@manejo_errores convierte en 500.

Se pudo provocar en 8 rutas, cuatro de ellas **publicas** (login, registrar,
solicitar-reset-password y log/client), es decir un 500 sin autenticar. Ahora
todas leen el cuerpo con `cuerpo_json()`, que valida que sea un objeto.

Ademas se cubren dos entradas que pasaban el `or ""` y reventaban el `.strip()`
por no ser texto, y el renombrado de un articulo personalizado a un nombre ya
usado (violaba UNIQUE(nombre, usuario_propietario_id) -> IntegrityError -> 500).
"""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.config import VERSION_TERMINOS
from stockhogar.db import ahora, get_db

# Un cuerpo escalar y uno de tipo lista: ninguno es un objeto JSON.
CUERPOS_NO_OBJETO = [5, [], "texto", True]


class CuerpoNoObjetoTests(unittest.TestCase):
    """Rutas publicas: el 500 se podia provocar sin estar autenticado."""

    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = self.app.test_client()

    def test_rutas_publicas_no_dan_500(self):
        rutas = [
            "/api/auth/login",
            "/api/auth/registrar",
            "/api/auth/solicitar-reset-password",
            "/api/auth/restablecer-password",
            "/api/log/client",
        ]
        for ruta in rutas:
            for cuerpo in CUERPOS_NO_OBJETO:
                with self.subTest(ruta=ruta, cuerpo=cuerpo):
                    respuesta = self.client.post(ruta, json=cuerpo)
                    self.assertLess(
                        respuesta.status_code, 500,
                        f"{ruta} con cuerpo {cuerpo!r} responde "
                        f"{respuesta.status_code}: un cuerpo mal formado no debe "
                        "ser un error del servidor",
                    )


class CuerpoNoObjetoAutenticadoTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        self.nombre_usuario = f"test_cj_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            self.usuario_id = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion, "
                "terminos_version_aceptada) VALUES (?, ?, ?, ?)",
                (self.nombre_usuario, generate_password_hash("password123"), ahora(),
                 VERSION_TERMINOS),
            ).lastrowid
            self.hogar_id = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, "
                "fecha_creacion, fecha_actualizacion) VALUES (?, ?, 1, ?, ?)",
                ("Hogar cj", self.usuario_id, ahora(), ahora()),
            ).lastrowid
            db.execute(
                "INSERT INTO permisos_hogar (hogar_id, usuario_id, nivel, fecha_otorgado) "
                "VALUES (?, ?, 'editar', ?)",
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
                "DELETE FROM articulos_compra WHERE hogar_id = ?", (self.hogar_id,)
            )
            db.execute(
                "DELETE FROM articulos_personalizados WHERE usuario_propietario_id = ?",
                (self.usuario_id,),
            )
            db.execute("DELETE FROM permisos_hogar WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM hogares WHERE id = ?", (self.hogar_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def test_rutas_autenticadas_no_dan_500(self):
        rutas = [
            "/api/articulos",
            "/api/auth/cambiar-password",
            "/api/auth/doble-factor",
            "/api/hogares",
            "/api/gastos",
            "/api/recetas",
            "/api/tickets/confirmar",
        ]
        for ruta in rutas:
            for cuerpo in CUERPOS_NO_OBJETO:
                with self.subTest(ruta=ruta, cuerpo=cuerpo):
                    respuesta = self.client.post(ruta, json=cuerpo)
                    self.assertLess(
                        respuesta.status_code, 500,
                        f"{ruta} con cuerpo {cuerpo!r} responde {respuesta.status_code}",
                    )

    def test_nombre_no_textual_da_400_no_500(self):
        """{"nombre": 5} pasaba el `or ""` porque 5 es truthy."""
        respuesta = self.client.post("/api/articulos", json={"nombre": 5})
        self.assertLess(respuesta.status_code, 500, respuesta.get_data(as_text=True))

    def test_cuerpo_vacio_sigue_comportandose_igual(self):
        """Un {} valido no debe empezar a fallar por el cambio."""
        respuesta = self.client.post("/api/articulos", json={})
        self.assertEqual(respuesta.status_code, 400, respuesta.get_data(as_text=True))

    def test_articulo_normal_sigue_creandose(self):
        nombre = f"ZzzArt{uuid.uuid4().hex[:6]}"
        respuesta = self.client.post("/api/articulos", json={"nombre": nombre})
        self.assertIn(respuesta.status_code, (200, 201), respuesta.get_data(as_text=True))


class RenombrarPersonalizadoDuplicadoTests(unittest.TestCase):
    """Renombrar un articulo personalizado a un nombre que ya tienes.

    articulos_personalizados tiene UNIQUE(nombre, usuario_propietario_id), asi
    que el UPDATE lanzaba IntegrityError y salia como 500 sin decir nada. Es un
    caso corriente: tener "Leche" y "Leche desnatada" y renombrar la segunda.
    """

    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        self.nombre_usuario = f"test_dup_{uuid.uuid4().hex[:8]}"
        self.alfa = f"ZzzAlfa{uuid.uuid4().hex[:6]}"
        self.beta = f"ZzzBeta{uuid.uuid4().hex[:6]}"
        with self.app.app_context():
            db = get_db()
            self.usuario_id = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) "
                "VALUES (?, ?, ?)",
                (self.nombre_usuario, generate_password_hash("password123"), ahora()),
            ).lastrowid
            self.hogar_id = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, "
                "fecha_creacion, fecha_actualizacion) VALUES (?, ?, 1, ?, ?)",
                ("Hogar dup", self.usuario_id, ahora(), ahora()),
            ).lastrowid
            db.execute(
                "INSERT INTO permisos_hogar (hogar_id, usuario_id, nivel, fecha_otorgado) "
                "VALUES (?, ?, 'editar', ?)",
                (self.hogar_id, self.usuario_id, ahora()),
            )
            self.id_alfa = db.execute(
                "INSERT INTO articulos_personalizados (nombre, categoria, unidad, "
                "usuario_propietario_id, fecha_creacion) VALUES (?, 'Otros', 'ud', ?, ?)",
                (self.alfa, self.usuario_id, ahora()),
            ).lastrowid
            self.id_beta = db.execute(
                "INSERT INTO articulos_personalizados (nombre, categoria, unidad, "
                "usuario_propietario_id, fecha_creacion) VALUES (?, 'Otros', 'ud', ?, ?)",
                (self.beta, self.usuario_id, ahora()),
            ).lastrowid
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
                "DELETE FROM articulos_personalizados WHERE usuario_propietario_id = ?",
                (self.usuario_id,),
            )
            db.execute("DELETE FROM permisos_hogar WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM hogares WHERE id = ?", (self.hogar_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def test_renombrar_a_nombre_ya_usado_da_400(self):
        respuesta = self.client.patch(
            f"/api/articulos/personalizados/{self.id_beta}", json={"nombre": self.alfa}
        )
        self.assertEqual(
            respuesta.status_code, 400, respuesta.get_data(as_text=True),
        )

    def test_el_articulo_no_se_queda_a_medias(self):
        self.client.patch(
            f"/api/articulos/personalizados/{self.id_beta}", json={"nombre": self.alfa}
        )
        with self.app.app_context():
            fila = get_db().execute(
                "SELECT nombre FROM articulos_personalizados WHERE id = ?", (self.id_beta,)
            ).fetchone()
        self.assertEqual(
            fila["nombre"], self.beta,
            "si el renombrado se rechaza, el nombre original debe seguir intacto",
        )

    def test_renombrar_a_un_nombre_libre_sigue_funcionando(self):
        nuevo = f"ZzzLibre{uuid.uuid4().hex[:6]}"
        respuesta = self.client.patch(
            f"/api/articulos/personalizados/{self.id_beta}", json={"nombre": nuevo}
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
