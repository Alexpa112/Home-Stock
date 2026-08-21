"""Auditoria de autorizacion: ningun endpoint con id debe servir a otro hogar.

Barrido sistematico de referencia directa insegura a objetos (IDOR). El usuario B
-con su propio hogar, sin ninguna relacion con A- intenta leer, modificar y
borrar TODOS los recursos de A usando sus identificadores. Cualquier respuesta
2xx es una fuga o una escritura ajena.

Se cubren los recursos de cada tabla con hogar_id o propietario: productos y su
stock, articulos de la lista, articulos personalizados, gastos (y su recibo),
gastos recurrentes, recetas, hogares y sus permisos, y el historial de precios.

Esta clase de fallo ya ha aparecido dos veces en el proyecto (el catalogo de
`productos` y luego `historial_articulos` se servian sin filtrar por hogar), asi
que el barrido queda como test permanente y no como comprobacion de una vez.
"""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db

# Un 2xx en cualquiera de estas llamadas es un hallazgo.
CODIGOS_ACEPTABLES = (400, 401, 403, 404, 405)


class IdorEntreHogaresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        cls.sufijo = uuid.uuid4().hex[:8]

        with cls.app.app_context():
            db = get_db()
            cls.a = cls._crear_usuario_con_hogar(db, f"idor_a_{cls.sufijo}")
            cls.b = cls._crear_usuario_con_hogar(db, f"idor_b_{cls.sufijo}")
            cls.recursos = cls._sembrar_recursos(db, cls.a)
            db.commit()

        cls.cliente_b = cls.app.test_client()
        with cls.cliente_b.session_transaction() as sess:
            sess["usuario"] = cls.b["nombre"]
            sess["usuario_id"] = cls.b["usuario_id"]
            sess["hogar_actual_id"] = cls.b["hogar_id"]

    @classmethod
    def _crear_usuario_con_hogar(cls, db, nombre):
        usuario_id = db.execute(
            "INSERT INTO usuarios (nombre_usuario, password_hash, email, fecha_creacion) "
            "VALUES (?, ?, ?, ?)",
            (nombre, generate_password_hash("password123"), f"{nombre}@example.com", ahora()),
        ).lastrowid
        hogar_id = db.execute(
            "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, "
            "fecha_actualizacion) VALUES (?, ?, 1, ?, ?)",
            (f"Hogar {nombre}", usuario_id, ahora(), ahora()),
        ).lastrowid
        db.execute(
            "INSERT INTO permisos_hogar (hogar_id, usuario_id, nivel, fecha_otorgado) "
            "VALUES (?, ?, 'editar', ?)",
            (hogar_id, usuario_id, ahora()),
        )
        return {"nombre": nombre, "usuario_id": usuario_id, "hogar_id": hogar_id}

    @classmethod
    def _sembrar_recursos(cls, db, a):
        """Un recurso de cada tipo, todos del hogar de A."""
        r = {}
        r["producto_id"] = db.execute(
            "INSERT INTO productos (nombre, categoria, fecha_creacion) VALUES (?, 'Otros', ?)",
            (f"ProdSecreto{cls.sufijo}", ahora()),
        ).lastrowid
        db.execute(
            "INSERT INTO stock_hogar (hogar_id, producto_id, cantidad, fecha_creacion, "
            "fecha_actualizacion) VALUES (?, ?, 5, ?, ?)",
            (a["hogar_id"], r["producto_id"], ahora(), ahora()),
        )
        db.execute(
            "INSERT INTO historial_precios (producto_id, hogar_id, precio, fecha) VALUES (?, ?, 9.99, ?)",
            (r["producto_id"], a["hogar_id"], ahora()),
        )
        r["articulo_id"] = db.execute(
            "INSERT INTO articulos_compra (hogar_id, nombre, fecha_creacion, fecha_actualizacion) "
            "VALUES (?, ?, ?, ?)",
            (a["hogar_id"], f"ArtSecreto{cls.sufijo}", ahora(), ahora()),
        ).lastrowid
        r["personalizado_id"] = db.execute(
            "INSERT INTO articulos_personalizados (nombre, categoria, unidad, "
            "usuario_propietario_id, fecha_creacion) VALUES (?, 'Otros', 'ud', ?, ?)",
            (f"PersSecreto{cls.sufijo}", a["usuario_id"], ahora()),
        ).lastrowid
        r["gasto_id"] = db.execute(
            "INSERT INTO gastos (hogar_id, descripcion, importe_total, fecha, "
            "usuario_pagador_id, fecha_creacion) VALUES (?, ?, 42.0, ?, ?, ?)",
            (a["hogar_id"], f"GastoSecreto{cls.sufijo}", ahora(), a["usuario_id"], ahora()),
        ).lastrowid
        r["recurrente_id"] = db.execute(
            "INSERT INTO gastos_recurrentes (hogar_id, descripcion, importe_total, "
            "usuario_pagador_id, frecuencia, proxima_fecha, fecha_creacion) "
            "VALUES (?, ?, 10.0, ?, 'mensual', ?, ?)",
            (a["hogar_id"], f"RecSecreto{cls.sufijo}", a["usuario_id"], ahora(), ahora()),
        ).lastrowid
        db.execute(
            "INSERT INTO movimientos_stock (producto_id, hogar_id, usuario_id, delta, "
            "cantidad_resultante, origen, fecha) VALUES (?, ?, ?, -1, 4, 'ajuste', ?)",
            (r["producto_id"], a["hogar_id"], a["usuario_id"], ahora()),
        )
        r["receta_id"] = db.execute(
            "INSERT INTO recetas (hogar_id, nombre, fecha_creacion) VALUES (?, ?, ?)",
            (a["hogar_id"], f"RecetaSecreta{cls.sufijo}", ahora()),
        ).lastrowid
        return r

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db = get_db()
            for lado in (cls.a, cls.b):
                h = lado["hogar_id"]
                db.execute("DELETE FROM gastos_participantes WHERE gasto_id IN "
                           "(SELECT id FROM gastos WHERE hogar_id = ?)", (h,))
                for tabla in ("gastos", "gastos_recurrentes", "articulos_compra",
                              "stock_hogar", "historial_precios", "recetas", "permisos_hogar"):
                    db.execute(f"DELETE FROM {tabla} WHERE hogar_id = ?", (h,))
                db.execute("DELETE FROM hogares WHERE id = ?", (h,))
                db.execute("DELETE FROM articulos_personalizados WHERE usuario_propietario_id = ?",
                           (lado["usuario_id"],))
                db.execute("DELETE FROM usuarios WHERE id = ?", (lado["usuario_id"],))
            db.execute("DELETE FROM productos WHERE nombre LIKE ?", (f"ProdSecreto{cls.sufijo}%",))
            db.commit()

    def _comprobar(self, metodo, ruta, cuerpo=None):
        respuesta = self.cliente_b.open(ruta, method=metodo, json=cuerpo)
        self.assertIn(
            respuesta.status_code, CODIGOS_ACEPTABLES,
            f"{metodo} {ruta} responde {respuesta.status_code} a un usuario de OTRO "
            f"hogar: {respuesta.get_data(as_text=True)[:160]}",
        )
        return respuesta

    # --- lectura de recursos ajenos --------------------------------------

    def test_no_puede_leer_recursos_de_otro_hogar(self):
        r, a = self.recursos, self.a
        casos = [
            ("GET", f"/api/hogares/{a['hogar_id']}"),
            ("GET", f"/api/hogares/{a['hogar_id']}/miembros"),
            ("GET", f"/api/hogares/{a['hogar_id']}/miembros-basico"),
            ("GET", f"/api/productos/{r['producto_id']}/precios"),
            ("GET", f"/api/gastos/{r['gasto_id']}/recibo"),
            ("GET", f"/api/articulos/personalizados/{r['personalizado_id']}/traducciones/en"),
            ("GET", f"/api/productos/{r['producto_id']}/traducciones/en"),
        ]
        for metodo, ruta in casos:
            with self.subTest(ruta=ruta):
                self._comprobar(metodo, ruta)

    # --- modificacion de recursos ajenos ---------------------------------

    def test_no_puede_modificar_recursos_de_otro_hogar(self):
        r, a = self.recursos, self.a
        casos = [
            ("PATCH", f"/api/productos/{r['producto_id']}", {"cantidad": 999}),
            ("PATCH", f"/api/articulos/{r['articulo_id']}", {"nombre": "pirateado"}),
            ("PATCH", f"/api/articulos/personalizados/{r['personalizado_id']}", {"nombre": "pirateado"}),
            ("PATCH", f"/api/gastos/{r['gasto_id']}", {"descripcion": "pirateado"}),
            ("PUT", f"/api/gastos/{r['gasto_id']}", {"descripcion": "pirateado"}),
            ("PATCH", f"/api/gastos/recurrentes/{r['recurrente_id']}", {"activo": False}),
            ("PATCH", f"/api/recetas/{r['receta_id']}", {"nombre": "pirateada"}),
            ("PATCH", f"/api/hogares/{a['hogar_id']}", {"nombre": "pirateado"}),
            ("PUT", f"/api/hogares/{a['hogar_id']}", {"nombre": "pirateado"}),
            ("PATCH", f"/api/hogares/{a['hogar_id']}/permisos/{a['usuario_id']}", {"nivel": "ver"}),
            ("POST", f"/api/hogares/{a['hogar_id']}/compartir", {"usuario": "alguien"}),
            ("POST", f"/api/hogares/{a['hogar_id']}/enlace-compartible", {}),
            ("POST", f"/api/recetas/{r['receta_id']}/anadir-a-lista", {}),
        ]
        for metodo, ruta, cuerpo in casos:
            with self.subTest(ruta=f"{metodo} {ruta}"):
                self._comprobar(metodo, ruta, cuerpo)

    # --- borrado de recursos ajenos --------------------------------------

    def test_no_puede_borrar_recursos_de_otro_hogar(self):
        r, a = self.recursos, self.a
        casos = [
            ("DELETE", f"/api/productos/{r['producto_id']}"),
            ("DELETE", f"/api/articulos/{r['articulo_id']}"),
            ("DELETE", f"/api/articulos/personalizados/{r['personalizado_id']}"),
            ("DELETE", f"/api/gastos/{r['gasto_id']}"),
            ("DELETE", f"/api/gastos/{r['gasto_id']}/recibo"),
            ("DELETE", f"/api/gastos/recurrentes/{r['recurrente_id']}"),
            ("DELETE", f"/api/recetas/{r['receta_id']}"),
            ("DELETE", f"/api/hogares/{a['hogar_id']}"),
            ("DELETE", f"/api/hogares/{a['hogar_id']}/permisos/{a['usuario_id']}"),
            ("DELETE", f"/api/usuarios/{a['usuario_id']}"),
        ]
        for metodo, ruta in casos:
            with self.subTest(ruta=f"{metodo} {ruta}"):
                self._comprobar(metodo, ruta)

    def test_el_consumo_de_otro_hogar_no_se_filtra(self):
        """Este endpoint responde 200 con lista vacia en vez de 403 (filtra por
        el hogar de quien pregunta, no por el dueño del producto). Lo que hay
        que exigir, entonces, no es el codigo sino que no salga ni un dato: A
        tiene un movimiento sembrado para ese producto."""
        respuesta = self.cliente_b.get(f"/api/consumo/producto/{self.recursos['producto_id']}")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.get_json(), [],
            "B esta viendo los movimientos de stock del hogar de A",
        )

    def test_los_recursos_de_a_siguen_intactos(self):
        """Comprobacion final: nada de lo anterior ha llegado a la BD."""
        r, a = self.recursos, self.a
        with self.app.app_context():
            db = get_db()
            self.assertIsNotNone(
                db.execute("SELECT 1 FROM productos WHERE id = ?", (r["producto_id"],)).fetchone(),
                "el producto de A se ha borrado desde la sesion de B",
            )
            self.assertIsNotNone(
                db.execute("SELECT 1 FROM gastos WHERE id = ?", (r["gasto_id"],)).fetchone(),
                "el gasto de A se ha borrado desde la sesion de B",
            )
            self.assertIsNotNone(
                db.execute("SELECT 1 FROM hogares WHERE id = ?", (a["hogar_id"],)).fetchone(),
                "el hogar de A se ha borrado desde la sesion de B",
            )
            gasto = db.execute("SELECT descripcion FROM gastos WHERE id = ?",
                               (r["gasto_id"],)).fetchone()
            self.assertNotEqual(gasto["descripcion"], "pirateado")
            hogar = db.execute("SELECT nombre FROM hogares WHERE id = ?",
                               (a["hogar_id"],)).fetchone()
            self.assertNotEqual(hogar["nombre"], "pirateado")

    # --- la sesion anonima no debe pasar de la puerta ---------------------

    def test_sin_sesion_todo_responde_401(self):
        anonimo = self.app.test_client()
        r, a = self.recursos, self.a
        for metodo, ruta in (
            ("GET", f"/api/hogares/{a['hogar_id']}"),
            ("PATCH", f"/api/productos/{r['producto_id']}"),
            ("DELETE", f"/api/gastos/{r['gasto_id']}"),
            ("GET", f"/api/gastos/{r['gasto_id']}/recibo"),
        ):
            with self.subTest(ruta=f"{metodo} {ruta}"):
                respuesta = anonimo.open(ruta, method=metodo, json={})
                self.assertEqual(respuesta.status_code, 401, f"{metodo} {ruta}")


if __name__ == "__main__":
    unittest.main()
