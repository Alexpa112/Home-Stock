"""Test de regresion de la migracion aditiva listas -> hogares (ver
stockhogar/db.py, bloque al final de _init_db_impl, y
docs/HOGAR_REESTRUCTURACION.md Punto 1).

Simula una instalacion con datos "viejos" insertados directamente en las
tablas legadas (listas/permisos_lista/articulos_lista/stock_lista) y
comprueba que, tras reinicializar la app (lo que dispara la migracion de
forma idempotente en cada arranque), los mismos datos aparecen en las
tablas nuevas (hogares/permisos_hogar/articulos_compra/stock_hogar) con
las claves foraneas correctas, sin duplicar filas si se ejecuta dos veces."""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class MigracionHogaresTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        sufijo = uuid.uuid4().hex[:8]

        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (f"test_migra_a_{sufijo}", generate_password_hash("password123"), ahora()),
            )
            self.usuario_a_id = cur.lastrowid
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (f"test_migra_b_{sufijo}", generate_password_hash("password123"), ahora()),
            )
            self.usuario_b_id = cur.lastrowid

            # Fila "vieja": insertada directamente en la tabla legada `listas`,
            # simulando una instalacion previa a la migracion. Se fuerza un id
            # explicito muy por encima del maximo actual en AMBAS tablas: en la
            # BD compartida de tests, `listas` dejo de recibir INSERTs tras el
            # Punto 2 (todo el alta nueva va a `hogares`), asi que sus secuencias
            # de autoincrement estan desincronizadas; sin este id explicito, uno
            # nuevo en `listas` podria coincidir por casualidad con el id de un
            # hogar real ya existente y la migracion (que empareja por id) lo
            # ignoraria creyendolo ya migrado, dando un falso negativo aqui.
            max_listas = db.execute("SELECT COALESCE(MAX(id), 0) AS m FROM listas").fetchone()["m"]
            max_hogares = db.execute("SELECT COALESCE(MAX(id), 0) AS m FROM hogares").fetchone()["m"]
            self.lista_vieja_id = max(max_listas, max_hogares) + 1000
            db.execute(
                "INSERT INTO listas (id, nombre, descripcion, usuario_propietario_id, privada, "
                "icono, color, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)",
                (self.lista_vieja_id, f"Hogar legado {sufijo}", "desc legada", self.usuario_a_id,
                 "📋", "#B5551A", ahora(), ahora()),
            )

            cur = db.execute(
                "INSERT INTO productos (nombre, categoria, cantidad, unidad, stock_minimo, "
                "fecha_creacion, fecha_actualizacion) VALUES (?, 'Otros', 3, 'ud', 1, ?, ?)",
                (f"ProductoMigracion{sufijo}", ahora(), ahora()),
            )
            self.producto_id = cur.lastrowid

            db.execute(
                "INSERT INTO stock_lista (lista_id, producto_id, cantidad, stock_minimo, "
                "fecha_creacion, fecha_actualizacion) VALUES (?, ?, 3, 1, ?, ?)",
                (self.lista_vieja_id, self.producto_id, ahora(), ahora()),
            )
            db.execute(
                "INSERT INTO articulos_lista (lista_id, producto_id, nombre, unidad, categoria, "
                "cantidad, origen, fecha_creacion) VALUES (?, ?, ?, 'ud', 'Otros', 1, 'manual', ?)",
                (self.lista_vieja_id, self.producto_id, f"ProductoMigracion{sufijo}", ahora()),
            )
            db.execute(
                "INSERT INTO permisos_lista (lista_id, usuario_id, nivel, fecha_otorgado) "
                "VALUES (?, ?, 'editar', ?)",
                (self.lista_vieja_id, self.usuario_b_id, ahora()),
            )
            db.commit()

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            for tabla, columna in (
                ("stock_lista", "lista_id"), ("stock_hogar", "hogar_id"),
                ("articulos_lista", "lista_id"), ("articulos_compra", "hogar_id"),
                ("permisos_lista", "lista_id"), ("permisos_hogar", "hogar_id"),
            ):
                db.execute(f"DELETE FROM {tabla} WHERE {columna} = ?", (self.lista_vieja_id,))
            db.execute("DELETE FROM productos WHERE id = ?", (self.producto_id,))
            db.execute("DELETE FROM listas WHERE id = ?", (self.lista_vieja_id,))
            db.execute("DELETE FROM hogares WHERE id = ?", (self.lista_vieja_id,))
            db.execute("DELETE FROM usuarios WHERE id IN (?, ?)", (self.usuario_a_id, self.usuario_b_id))
            db.commit()

    def _reiniciar_app_para_disparar_migracion(self):
        """create_app() vuelve a correr _init_db_impl; al ser idempotente, debe
        copiar cualquier fila vieja que aun no tenga su equivalente en la tabla
        nueva, sin duplicar las que ya se copiaron en una ejecucion anterior."""
        create_app()

    def test_fila_vieja_en_listas_aparece_en_hogares_tras_reiniciar(self):
        self._reiniciar_app_para_disparar_migracion()
        with self.app.app_context():
            db = get_db()
            hogar = db.execute("SELECT * FROM hogares WHERE id = ?", (self.lista_vieja_id,)).fetchone()
        self.assertIsNotNone(hogar, "la fila vieja de `listas` no se copio a `hogares`")
        self.assertEqual(hogar["usuario_propietario_id"], self.usuario_a_id)
        self.assertTrue(hogar["nombre"].startswith("Hogar legado"))

    def test_stock_lista_aparece_en_stock_hogar_con_mismos_datos(self):
        self._reiniciar_app_para_disparar_migracion()
        with self.app.app_context():
            db = get_db()
            fila = db.execute(
                "SELECT * FROM stock_hogar WHERE hogar_id = ? AND producto_id = ?",
                (self.lista_vieja_id, self.producto_id),
            ).fetchone()
        self.assertIsNotNone(fila, "la fila de `stock_lista` no se copio a `stock_hogar`")
        self.assertEqual(fila["cantidad"], 3)
        self.assertEqual(fila["stock_minimo"], 1)

    def test_articulos_lista_aparece_en_articulos_compra(self):
        self._reiniciar_app_para_disparar_migracion()
        with self.app.app_context():
            db = get_db()
            fila = db.execute(
                "SELECT * FROM articulos_compra WHERE hogar_id = ? AND producto_id = ?",
                (self.lista_vieja_id, self.producto_id),
            ).fetchone()
        self.assertIsNotNone(fila, "la fila de `articulos_lista` no se copio a `articulos_compra`")

    def test_permisos_lista_aparece_en_permisos_hogar(self):
        self._reiniciar_app_para_disparar_migracion()
        with self.app.app_context():
            db = get_db()
            fila = db.execute(
                "SELECT * FROM permisos_hogar WHERE hogar_id = ? AND usuario_id = ?",
                (self.lista_vieja_id, self.usuario_b_id),
            ).fetchone()
        self.assertIsNotNone(fila, "la fila de `permisos_lista` no se copio a `permisos_hogar`")
        self.assertEqual(fila["nivel"], "editar")

    def test_reiniciar_dos_veces_no_duplica_filas(self):
        self._reiniciar_app_para_disparar_migracion()
        self._reiniciar_app_para_disparar_migracion()
        with self.app.app_context():
            db = get_db()
            total = db.execute(
                "SELECT COUNT(*) AS n FROM hogares WHERE id = ?", (self.lista_vieja_id,)
            ).fetchone()["n"]
        self.assertEqual(total, 1, "la migracion no es idempotente: duplico la fila en `hogares`")


if __name__ == "__main__":
    unittest.main()
