"""Regresiones del contrato frontend-backend detectadas en la auditoria."""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class ContratoTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.nombre = "ctr_" + uuid.uuid4().hex[:6]
        with self.app.app_context():
            db = get_db()
            self.uid = db.execute(
                "INSERT INTO usuarios (nombre_usuario,password_hash,idioma_preferido,fecha_creacion) VALUES (?,?,?,?)",
                (self.nombre, generate_password_hash("password123"), "en", ahora())).lastrowid
            self.hid = db.execute(
                "INSERT INTO hogares (nombre,usuario_propietario_id,privada,fecha_creacion,fecha_actualizacion) VALUES (?,?,1,?,?)",
                ("Ctr", self.uid, ahora(), ahora())).lastrowid
            db.commit()
        self.c = self.app.test_client()
        with self.c.session_transaction() as s:
            s["usuario"] = self.nombre
            s["usuario_id"] = self.uid
            s["hogar_actual_id"] = self.hid

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM hogares WHERE usuario_propietario_id=?", (self.uid,))
            db.execute("DELETE FROM usuarios WHERE id=?", (self.uid,))
            db.commit()

    def test_producto_conserva_cantidad_decimal(self):
        r = self.c.post("/api/productos", json={"nombre": "Jamon", "cantidad": 0.85, "stock_minimo": 2.5, "categoria": "Otros"})
        self.assertIn(r.status_code, (200, 201), r.get_data(as_text=True))
        pid = r.get_json().get("id") or r.get_json().get("data", {}).get("id")
        lista = self.c.get("/api/productos").get_json()
        filas = lista if isinstance(lista, list) else lista.get("productos", lista)
        fila = [p for p in filas if p["id"] == pid][0]
        self.assertAlmostEqual(fila["cantidad"], 0.85)
        self.assertAlmostEqual(fila["stock_minimo"], 2.5)

    def test_gasto_igual_entre_tres(self):
        with self.app.app_context():
            db = get_db()
            ids = [self.uid]
            for i in range(2):
                n = "ctr_x%s%d" % (uuid.uuid4().hex[:4], i)
                u = db.execute("INSERT INTO usuarios (nombre_usuario,password_hash,fecha_creacion) VALUES (?,?,?)",
                               (n, generate_password_hash("password123"), ahora())).lastrowid
                db.execute("INSERT INTO permisos_hogar (hogar_id,usuario_id,nivel,fecha_otorgado) VALUES (?,?,?,?)",
                           (self.hid, u, "editar", ahora()))
                ids.append(u)
            db.commit()
        try:
            r = self.c.post("/api/gastos", json={
                "descripcion": "Cena", "importe_total": 100, "fecha": "2024-01-01",
                "usuario_pagador_id": self.uid,
                "participantes": [{"usuario_id": ids[0], "importe": 33.34}, {"usuario_id": ids[1], "importe": 33.33}, {"usuario_id": ids[2], "importe": 33.33}],
            })
            self.assertIn(r.status_code, (200, 201), r.get_data(as_text=True))
            r = self.c.post("/api/gastos", json={
                "descripcion": "Cena2", "importe_total": 100, "fecha": "2024-01-01",
                "usuario_pagador_id": self.uid,
                "participantes": [{"usuario_id": i, "importe": 33.0} for i in ids],
            })
            self.assertEqual(r.status_code, 400)
        finally:
            with self.app.app_context():
                db = get_db()
                for u in ids[1:]:
                    db.execute("DELETE FROM usuarios WHERE id=?", (u,))
                db.commit()

    def test_version_cambia_al_crear_gasto(self):
        v1 = self.c.get("/api/hogares/version").get_json()
        v1 = v1.get("version") if "version" in v1 else v1["data"]["version"]
        r = self.c.post("/api/gastos", json={
            "descripcion": "A", "importe_total": 10, "fecha": "2024-01-01",
            "usuario_pagador_id": self.uid, "participantes": [{"usuario_id": self.uid, "importe": 10}]})
        self.assertIn(r.status_code, (200, 201), r.get_data(as_text=True))
        v2 = self.c.get("/api/hogares/version").get_json()
        v2 = v2.get("version") if "version" in v2 else v2["data"]["version"]
        self.assertNotEqual(v1, v2)

    def test_idioma_se_restaura_en_login(self):
        c = self.app.test_client()
        r = c.post("/api/auth/login", json={"usuario": self.nombre, "password": "password123"})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        self.assertEqual(c.get("/api/idiomas/obtener").get_json().get("idioma"), "en")


if __name__ == "__main__":
    unittest.main()


class CategoriasPermisoTests(ContratoTests):
    def test_sin_permiso_de_edicion_no_crea_categoria(self):
        with self.app.app_context():
            db = get_db()
            otro = db.execute("INSERT INTO usuarios (nombre_usuario,password_hash,fecha_creacion) VALUES (?,?,?)",
                              ("ctr_v" + uuid.uuid4().hex[:5], generate_password_hash("password123"), ahora())).lastrowid
            db.execute("INSERT INTO permisos_hogar (hogar_id,usuario_id,nivel,fecha_otorgado) VALUES (?,?,?,?)",
                       (self.hid, otro, "ver", ahora()))
            db.commit()
        try:
            c = self.app.test_client()
            with c.session_transaction() as s:
                s["usuario"] = "x"
                s["usuario_id"] = otro
                s["hogar_actual_id"] = self.hid
            r = c.post("/api/categorias", json={"nombre": "Cat" + uuid.uuid4().hex[:5]})
            self.assertEqual(r.status_code, 403)
            nombre = "Cat" + uuid.uuid4().hex[:5]
            r = self.c.post("/api/categorias", json={"nombre": nombre})
            self.assertEqual(r.status_code, 201)
            self.c.delete("/api/categorias/%d" % r.get_json().get("id", 0))
        finally:
            with self.app.app_context():
                db = get_db()
                db.execute("DELETE FROM usuarios WHERE id=?", (otro,))
                db.commit()


class TraduccionNoBloqueaLaBdTests(ContratoTests):
    def test_anadir_articulo_nuevo_no_espera_a_la_traduccion(self):
        """Antes la traduccion (red/CPU) se hacia con la transaccion de escritura abierta:
        varios usuarios anadiendo articulos a la vez recibian 'database is locked' (500)."""
        import time
        from unittest.mock import patch

        def lenta(texto):
            time.sleep(3)
            return {"en": "x"}

        with patch("stockhogar.servicios.traduccion.traductor_auto.TraductorAutomatico.traducir_a_todos_idiomas", side_effect=lenta):
            t = time.time()
            r = self.c.post("/api/articulos", json={"nombre": "Articulo raro " + uuid.uuid4().hex[:6], "cantidad": 1,
                                                    "categoria": "Otros", "icono": "h-archive-box"})
            self.assertEqual(r.status_code, 201, r.get_data(as_text=True))
            self.assertLess(time.time() - t, 2.0)
            # y mientras traduce, otra escritura entra sin problema
            r2 = self.c.post("/api/productos", json={"nombre": "Otro " + uuid.uuid4().hex[:6], "cantidad": 1, "categoria": "Otros"})
            self.assertIn(r2.status_code, (200, 201))
