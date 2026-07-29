"""Tests del endpoint GET /api/historial/catalogo: catalogo combinado
(historial estandar + articulos_personalizados del hogar de la lista activa)
usado por el frontend para autocompletar/mostrar un grid al anadir un
articulo a una lista."""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class HistorialCatalogoTests(unittest.TestCase):
    NOMBRE_ESTANDAR = "ZzzManzanaCatalogoTest"
    NOMBRE_PERSONALIZADO_A = "ZzzRecetaSecretaDeATest"
    NOMBRE_PERSONALIZADO_B = "ZzzRecetaSecretaDeBTest"

    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        self.usuarios_creados = []
        self.listas_creadas = []

        self.usuario_a_id, self.lista_a_id, self.client_a = self._crear_usuario_con_lista("a")
        self.usuario_b_id, self.lista_b_id, self.client_b = self._crear_usuario_con_lista("b")

        with self.app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO historial_articulos (nombre, icono, categoria, unidad, fecha_actualizacion) "
                "VALUES (?, 'apple', 'Fruteria', 'ud', ?)",
                (self.NOMBRE_ESTANDAR, ahora()),
            )
            db.commit()

        # Cada hogar crea su propio articulo personalizado (nombres distintos
        # a proposito para poder comprobar el aislamiento por busqueda).
        resp = self.client_a.post("/api/articulos", json={"nombre": self.NOMBRE_PERSONALIZADO_A, "cantidad": 1})
        self.assertIn(resp.status_code, (200, 201), resp.get_data(as_text=True))
        resp = self.client_b.post("/api/articulos", json={"nombre": self.NOMBRE_PERSONALIZADO_B, "cantidad": 1})
        self.assertIn(resp.status_code, (200, 201), resp.get_data(as_text=True))

    def _crear_usuario_con_lista(self, sufijo):
        nombre_usuario = f"test_{sufijo}_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (nombre_usuario, generate_password_hash("password123"), ahora()),
            )
            usuario_id = cur.lastrowid
            cur = db.execute(
                "INSERT INTO listas (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, 1, ?, ?)",
                (f"Lista de {sufijo}", usuario_id, ahora(), ahora()),
            )
            lista_id = cur.lastrowid
            db.commit()

        self.usuarios_creados.append(usuario_id)
        self.listas_creadas.append(lista_id)

        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess["usuario"] = nombre_usuario
            sess["usuario_id"] = usuario_id
            sess["lista_actual_id"] = lista_id

        return usuario_id, lista_id, client

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            for lista_id in self.listas_creadas:
                db.execute("DELETE FROM articulos_lista WHERE lista_id = ?", (lista_id,))
                db.execute("DELETE FROM listas WHERE id = ?", (lista_id,))
            db.execute(
                "DELETE FROM traducciones_productos WHERE articulo_personalizado_id IN "
                "(SELECT id FROM articulos_personalizados WHERE nombre IN (?, ?))",
                (self.NOMBRE_PERSONALIZADO_A, self.NOMBRE_PERSONALIZADO_B),
            )
            db.execute(
                "DELETE FROM articulos_personalizados WHERE nombre IN (?, ?)",
                (self.NOMBRE_PERSONALIZADO_A, self.NOMBRE_PERSONALIZADO_B),
            )
            db.execute("DELETE FROM historial_articulos WHERE nombre = ?", (self.NOMBRE_ESTANDAR,))
            for usuario_id in self.usuarios_creados:
                db.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
            db.commit()

    def test_busca_articulo_estandar_por_nombre_parcial(self):
        resp = self.client_a.get("/api/historial/catalogo?q=ZzzManzanaCatalogo")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        nombres = [f["nombre"] for f in resp.get_json()]
        self.assertIn(self.NOMBRE_ESTANDAR, nombres)

    def test_incluye_articulo_personalizado_propio(self):
        resp = self.client_a.get(f"/api/historial/catalogo?q={self.NOMBRE_PERSONALIZADO_A}")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        datos = resp.get_json()
        self.assertEqual(len(datos), 1)
        self.assertEqual(datos[0]["nombre"], self.NOMBRE_PERSONALIZADO_A)
        self.assertEqual(datos[0]["origen"], "personalizado")

    def test_no_incluye_articulo_personalizado_de_otro_hogar(self):
        resp = self.client_a.get(f"/api/historial/catalogo?q={self.NOMBRE_PERSONALIZADO_B}")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertEqual(resp.get_json(), [])

    def test_sin_query_devuelve_catalogo_general(self):
        # Sin filtro, el catalogo estandar sembrado tiene muchas mas de 30
        # entradas (limite de la consulta) ordenadas alfabeticamente, asi que
        # un nombre con prefijo "Zzz" no aparecera ahi; lo que importa es que
        # el catalogo personalizado del propio hogar SIEMPRE aparezca.
        resp = self.client_a.get("/api/historial/catalogo")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        nombres = [f["nombre"] for f in resp.get_json()]
        self.assertIn(self.NOMBRE_PERSONALIZADO_A, nombres)
        self.assertNotIn(self.NOMBRE_PERSONALIZADO_B, nombres)

    def test_requiere_sesion(self):
        client_anonimo = self.app.test_client()
        resp = client_anonimo.get("/api/historial/catalogo")
        self.assertEqual(resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()
