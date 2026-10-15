"""Regresion: /api/hogares debe informar del hogar EFECTIVO, no del crudo.

Bug real, reproducido en el navegador: nada fija `hogar_actual_id` al iniciar
sesion (solo se pone al CREAR un hogar o al seleccionarlo a mano, y se BORRA al
salir o borrar el que estaba activo). GET /api/hogares devolvia ese valor crudo,
es decir null, mientras el resto del backend ya servia datos del hogar por
defecto que resuelve hogar_actual_con_permiso.

Con ese null, el layout del dashboard (`if (!hogarActivoId) return
<SelectorHogarPantallaCompleta />`, app/dashboard/layout.tsx:99) sustituye TODAS
las paginas por el selector de hogares. Sintoma para el usuario: entra en
"Escanear" y no ve el escaner -- ni la camara, ni el boton de subir fichero --
sino la pantalla de "Tus hogares", en cada pagina y en cada login nuevo.

Se cubre tambien el caso del usuario que solo participa en hogares de OTROS: el
fallback mira primero los hogares propios, y sin la rama de permisos_hogar se
quedaba sin hogar efectivo para siempre.
"""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class HogarActualEfectivoTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        self.nombre_usuario = f"test_hae_{uuid.uuid4().hex[:8]}"
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
                ("Hogar propio hae", self.usuario_id, ahora(), ahora()),
            ).lastrowid
            db.commit()

        # Sesion tal como queda tras un login: SIN hogar_actual_id.
        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess["usuario"] = self.nombre_usuario
            sess["usuario_id"] = self.usuario_id

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM permisos_hogar WHERE usuario_id = ?", (self.usuario_id,))
            db.execute("DELETE FROM hogares WHERE usuario_propietario_id = ?", (self.usuario_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def test_devuelve_un_hogar_aunque_la_sesion_no_lo_traiga(self):
        datos = self.client.get("/api/hogares").get_json()
        self.assertEqual(
            datos.get("hogar_actual_id"), self.hogar_id,
            "sin hogar_actual_id el frontend tapa todas las paginas del "
            "dashboard con el selector de hogares: el escaner no se ve",
        )

    def test_respeta_el_hogar_ya_elegido(self):
        otro = None
        with self.app.app_context():
            db = get_db()
            otro = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, "
                "fecha_creacion, fecha_actualizacion) VALUES (?, ?, 1, ?, ?)",
                ("Segundo hogar hae", self.usuario_id, ahora(), ahora()),
            ).lastrowid
            db.commit()
        with self.client.session_transaction() as sess:
            sess["hogar_actual_id"] = otro

        datos = self.client.get("/api/hogares").get_json()
        self.assertEqual(
            datos.get("hogar_actual_id"), otro,
            "una eleccion explicita del usuario no debe pisarse con el defecto",
        )

    def test_usuario_solo_con_hogares_compartidos(self):
        """El fallback mira los propios primero; sin la rama de permisos_hogar
        un invitado se quedaba sin hogar efectivo."""
        with self.app.app_context():
            db = get_db()
            # El usuario deja de tener hogares propios y pasa a ser invitado.
            db.execute("DELETE FROM hogares WHERE id = ?", (self.hogar_id,))
            dueno_id = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) "
                "VALUES (?, ?, ?)",
                (f"dueno_{uuid.uuid4().hex[:8]}", generate_password_hash("x"), ahora()),
            ).lastrowid
            hogar_ajeno = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, "
                "fecha_creacion, fecha_actualizacion) VALUES (?, ?, 1, ?, ?)",
                ("Hogar de otro hae", dueno_id, ahora(), ahora()),
            ).lastrowid
            db.execute(
                "INSERT INTO permisos_hogar (hogar_id, usuario_id, nivel, fecha_otorgado) "
                "VALUES (?, ?, 'editar', ?)",
                (hogar_ajeno, self.usuario_id, ahora()),
            )
            db.commit()
        self.addCleanup(self._limpiar_ajeno, dueno_id, hogar_ajeno)

        datos = self.client.get("/api/hogares").get_json()
        self.assertEqual(
            datos.get("hogar_actual_id"), hogar_ajeno,
            "un usuario invitado a hogares de otros tambien necesita un hogar "
            "efectivo, o el dashboard queda inservible para el",
        )

    def _limpiar_ajeno(self, dueno_id, hogar_ajeno):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM permisos_hogar WHERE hogar_id = ?", (hogar_ajeno,))
            db.execute("DELETE FROM hogares WHERE id = ?", (hogar_ajeno,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (dueno_id,))
            db.commit()

    def test_usuario_sin_ningun_hogar_sigue_devolviendo_null(self):
        """Quien de verdad no tiene hogares SI debe ver el selector."""
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM hogares WHERE id = ?", (self.hogar_id,))
            db.commit()

        datos = self.client.get("/api/hogares").get_json()
        self.assertIsNone(datos.get("hogar_actual_id"))

    def test_la_eleccion_queda_fijada_en_la_sesion(self):
        """Para que las siguientes peticiones no vuelvan a resolverlo."""
        self.client.get("/api/hogares")
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("hogar_actual_id"), self.hogar_id)


if __name__ == "__main__":
    unittest.main()
