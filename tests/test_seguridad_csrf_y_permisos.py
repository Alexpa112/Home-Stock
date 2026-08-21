"""Auditoria de seguridad: CSRF real y escalada de privilegios dentro del hogar.

Dos bloques que el resto de la suite no cubria porque desactiva CSRF:

1. CSRF con la proteccion ACTIVADA, tal como corre en produccion
   (WTF_CSRF_CHECK_DEFAULT = True). Se comprueba que una escritura sin token
   se rechaza, que con token valido pasa, y que las dos unicas rutas exentas
   (@csrf.exempt en rutas/paginas.py) no pueden modificar nada del usuario.

2. Escalada de privilegios de un invitado con nivel "ver": la jerarquia es
   ver < editar < propietario (stockhogar/autorizacion.py). Un miembro de solo
   lectura tiene sesion valida Y pertenece al hogar, asi que las
   comprobaciones de IDOR no le afectan: lo unico que le separa de escribir es
   el nivel. Se le intenta hacer escribir, borrar y administrar.
"""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class SeguridadCsrfTests(unittest.TestCase):
    """CSRF con la proteccion activada, como en produccion."""

    def setUp(self):
        self.app = create_app()
        # WTF_CSRF_ENABLED se deja como en produccion: activado.
        self.app.config.update(TESTING=True)

        self.nombre = f"csrf_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            self.usuario_id = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) "
                "VALUES (?, ?, ?)",
                (self.nombre, generate_password_hash("password123"), ahora()),
            ).lastrowid
            self.hogar_id = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, "
                "fecha_creacion, fecha_actualizacion) VALUES (?, ?, 1, ?, ?)",
                ("Hogar csrf", self.usuario_id, ahora(), ahora()),
            ).lastrowid
            db.execute(
                "INSERT INTO permisos_hogar (hogar_id, usuario_id, nivel, fecha_otorgado) "
                "VALUES (?, ?, 'editar', ?)",
                (self.hogar_id, self.usuario_id, ahora()),
            )
            db.commit()

        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess["usuario"] = self.nombre
            sess["usuario_id"] = self.usuario_id
            sess["hogar_actual_id"] = self.hogar_id

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM articulos_compra WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM permisos_hogar WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM hogares WHERE id = ?", (self.hogar_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def test_una_escritura_sin_token_csrf_se_rechaza(self):
        """Es lo que impide que otra web haga peticiones con tu cookie."""
        respuesta = self.client.post("/api/articulos", json={"nombre": "SinToken"})
        self.assertEqual(
            respuesta.status_code, 400,
            f"una escritura sin token CSRF deberia rechazarse: {respuesta.status_code}",
        )
        with self.app.app_context():
            fila = get_db().execute(
                "SELECT 1 FROM articulos_compra WHERE nombre = ?", ("SinToken",)
            ).fetchone()
        self.assertIsNone(fila, "el articulo se ha creado pese a faltar el token CSRF")

    def test_un_token_csrf_inventado_se_rechaza(self):
        respuesta = self.client.post(
            "/api/articulos", json={"nombre": "TokenFalso"},
            headers={"X-CSRFToken": "token-inventado"},
        )
        self.assertEqual(respuesta.status_code, 400)

    def test_con_token_valido_la_escritura_pasa(self):
        """Contraprueba: si esto fallara, el test de arriba no probaria nada."""
        token = self.client.get("/api/csrf-token").get_json()["csrf_token"]
        respuesta = self.client.post(
            "/api/articulos", json={"nombre": f"ConToken{uuid.uuid4().hex[:6]}"},
            headers={"X-CSRFToken": token},
        )
        self.assertIn(respuesta.status_code, (200, 201), respuesta.get_data(as_text=True))

    def test_las_rutas_exentas_de_csrf_no_modifican_nada_del_usuario(self):
        """Las dos unicas exenciones son un GET de estado y un log de cliente."""
        estado = self.client.get("/api/mantenimiento/estado")
        self.assertEqual(estado.status_code, 200)

        # /api/log/client es POST y esta exento: debe aceptar el beacon pero no
        # tocar datos del usuario.
        log = self.client.post("/api/log/client", json={"nivel": "error", "mensaje": "prueba"})
        self.assertLess(log.status_code, 500)
        with self.app.app_context():
            n = get_db().execute(
                "SELECT COUNT(*) AS n FROM articulos_compra WHERE hogar_id = ?", (self.hogar_id,)
            ).fetchone()["n"]
        self.assertEqual(n, 0, "el endpoint de logs no debe crear datos del usuario")

    def test_el_metodo_get_no_exige_token(self):
        """Las lecturas no deben quedar rotas por la proteccion CSRF."""
        self.assertEqual(self.client.get("/api/articulos").status_code, 200)


class EscaladaDePrivilegiosTests(unittest.TestCase):
    """Un invitado con nivel "ver" no puede escribir ni administrar."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        sufijo = uuid.uuid4().hex[:8]

        with cls.app.app_context():
            db = get_db()
            cls.dueno_id = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) "
                "VALUES (?, ?, ?)",
                (f"dueno_{sufijo}", generate_password_hash("password123"), ahora()),
            ).lastrowid
            cls.miron = f"miron_{sufijo}"
            cls.miron_id = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) "
                "VALUES (?, ?, ?)",
                (cls.miron, generate_password_hash("password123"), ahora()),
            ).lastrowid
            cls.hogar_id = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, "
                "fecha_creacion, fecha_actualizacion) VALUES (?, ?, 1, ?, ?)",
                ("Hogar compartido", cls.dueno_id, ahora(), ahora()),
            ).lastrowid
            # El invitado entra SOLO con permiso de lectura.
            db.execute(
                "INSERT INTO permisos_hogar (hogar_id, usuario_id, nivel, fecha_otorgado) "
                "VALUES (?, ?, 'ver', ?)",
                (cls.hogar_id, cls.miron_id, ahora()),
            )
            cls.articulo_id = db.execute(
                "INSERT INTO articulos_compra (hogar_id, nombre, fecha_creacion, "
                "fecha_actualizacion) VALUES (?, 'Articulo del dueno', ?, ?)",
                (cls.hogar_id, ahora(), ahora()),
            ).lastrowid
            cls.gasto_id = db.execute(
                "INSERT INTO gastos (hogar_id, descripcion, importe_total, fecha, "
                "usuario_pagador_id, fecha_creacion) VALUES (?, 'Gasto del dueno', 10.0, ?, ?, ?)",
                (cls.hogar_id, ahora(), cls.dueno_id, ahora()),
            ).lastrowid
            db.commit()

        cls.cliente = cls.app.test_client()
        with cls.cliente.session_transaction() as sess:
            sess["usuario"] = cls.miron
            sess["usuario_id"] = cls.miron_id
            sess["hogar_actual_id"] = cls.hogar_id

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db = get_db()
            db.execute("DELETE FROM gastos_participantes WHERE gasto_id IN "
                       "(SELECT id FROM gastos WHERE hogar_id = ?)", (cls.hogar_id,))
            for tabla in ("gastos", "articulos_compra", "permisos_hogar"):
                db.execute(f"DELETE FROM {tabla} WHERE hogar_id = ?", (cls.hogar_id,))
            db.execute("DELETE FROM hogares WHERE id = ?", (cls.hogar_id,))
            db.execute("DELETE FROM usuarios WHERE id IN (?, ?)", (cls.dueno_id, cls.miron_id))
            db.commit()

    def test_puede_leer_lo_que_se_le_ha_compartido(self):
        """Contraprueba: el nivel "ver" SI da lectura."""
        self.assertEqual(self.cliente.get("/api/articulos").status_code, 200)
        self.assertEqual(self.cliente.get("/api/gastos").status_code, 200)

    def test_no_puede_escribir_con_permiso_de_solo_lectura(self):
        casos = [
            ("POST", "/api/articulos", {"nombre": "colado por el miron"}),
            ("PATCH", f"/api/articulos/{self.articulo_id}", {"nombre": "pirateado"}),
            ("DELETE", f"/api/articulos/{self.articulo_id}", None),
            ("POST", "/api/productos", {"nombre": "colado", "cantidad": 1}),
            ("POST", "/api/gastos", {"descripcion": "colado", "importe_total": 5,
                                     "usuario_pagador_id": None, "participantes": []}),
            ("PATCH", f"/api/gastos/{self.gasto_id}", {"descripcion": "pirateado"}),
            ("DELETE", f"/api/gastos/{self.gasto_id}", None),
            ("POST", "/api/recetas", {"nombre": "colada", "ingredientes": [{"nombre": "x"}]}),
            ("POST", "/api/tickets/confirmar", {"items": [{"nombre": "colado", "cantidad": 1}]}),
        ]
        for metodo, ruta, cuerpo in casos:
            with self.subTest(ruta=f"{metodo} {ruta}"):
                respuesta = self.cliente.open(ruta, method=metodo, json=cuerpo)
                self.assertGreaterEqual(
                    respuesta.status_code, 400,
                    f"{metodo} {ruta} deja escribir a un miembro de SOLO LECTURA: "
                    f"{respuesta.get_data(as_text=True)[:140]}",
                )

    def test_no_puede_administrar_el_hogar(self):
        """Compartir, cambiar permisos o borrar es cosa del propietario."""
        casos = [
            ("PATCH", f"/api/hogares/{self.hogar_id}", {"nombre": "pirateado"}),
            ("DELETE", f"/api/hogares/{self.hogar_id}", None),
            ("POST", f"/api/hogares/{self.hogar_id}/compartir", {"usuario": "otro"}),
            ("POST", f"/api/hogares/{self.hogar_id}/enlace-compartible", {}),
            ("PATCH", f"/api/hogares/{self.hogar_id}/permisos/{self.miron_id}",
             {"nivel": "propietario"}),
        ]
        for metodo, ruta, cuerpo in casos:
            with self.subTest(ruta=f"{metodo} {ruta}"):
                respuesta = self.cliente.open(ruta, method=metodo, json=cuerpo)
                self.assertGreaterEqual(
                    respuesta.status_code, 400,
                    f"{metodo} {ruta} deja administrar el hogar a un miembro de solo lectura",
                )

    def test_no_ha_conseguido_cambiar_nada(self):
        with self.app.app_context():
            db = get_db()
            articulo = db.execute("SELECT nombre FROM articulos_compra WHERE id = ?",
                                  (self.articulo_id,)).fetchone()
            self.assertIsNotNone(articulo, "el articulo del dueño se ha borrado")
            self.assertEqual(articulo["nombre"], "Articulo del dueno")

            gasto = db.execute("SELECT descripcion FROM gastos WHERE id = ?",
                               (self.gasto_id,)).fetchone()
            self.assertIsNotNone(gasto, "el gasto del dueño se ha borrado")
            self.assertEqual(gasto["descripcion"], "Gasto del dueno")

            nivel = db.execute(
                "SELECT nivel FROM permisos_hogar WHERE hogar_id = ? AND usuario_id = ?",
                (self.hogar_id, self.miron_id),
            ).fetchone()
            self.assertEqual(
                nivel["nivel"], "ver",
                "el invitado se ha ascendido a si mismo",
            )


if __name__ == "__main__":
    unittest.main()
