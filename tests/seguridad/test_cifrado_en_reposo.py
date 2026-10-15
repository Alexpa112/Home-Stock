"""Cifrado en reposo de recibos y claves push, y cabeceras de seguridad."""
import io
import json
import unittest
import uuid

from PIL import Image
from werkzeug.security import generate_password_hash

from stockhogar.nucleo import cifrado, seguridad
from stockhogar import create_app
from stockhogar.db import ahora, get_db


class CifradoUnitTests(unittest.TestCase):
    def test_ida_y_vuelta(self):
        self.assertEqual(cifrado.descifrar_texto(cifrado.cifrar_texto("hola")), "hola")
        self.assertEqual(cifrado.descifrar_bytes(cifrado.cifrar_bytes(b"\x00\x01abc")), b"\x00\x01abc")

    def test_lo_cifrado_no_contiene_el_original(self):
        self.assertNotIn(b"secreto", cifrado.cifrar_bytes(b"secreto"))
        self.assertNotIn("secreto", cifrado.cifrar_texto("secreto"))

    def test_no_se_cifra_dos_veces(self):
        una = cifrado.cifrar_texto("x")
        self.assertEqual(cifrado.cifrar_texto(una), una)

    def test_dato_antiguo_sin_cifrar_se_lee(self):
        self.assertEqual(cifrado.descifrar_texto("claro"), "claro")
        self.assertEqual(cifrado.descifrar_bytes(b"claro"), b"claro")
        self.assertIsNone(cifrado.cifrar_texto(None))

    def test_manipulado_no_descifra(self):
        mal = cifrado.cifrar_texto("x")[:-4] + "AAAA"
        self.assertIsNone(cifrado.descifrar_texto(mal))

    def test_rotacion_conserva_lo_anterior(self):
        antes = (seguridad.CLAVE_CIFRADO, list(seguridad.CLAVES_CIFRADO_PREVIAS), dict(seguridad._claves))
        viejo = cifrado.cifrar_texto("persistente")
        try:
            seguridad.CLAVES_CIFRADO_PREVIAS = [seguridad.CLAVE_CIFRADO] + seguridad.CLAVES_CIFRADO_PREVIAS
            seguridad.CLAVE_CIFRADO = cifrado.Fernet.generate_key().decode()
            self.assertEqual(cifrado.descifrar_texto(viejo), "persistente")
            nuevo = cifrado.cifrar_texto("otro")
            self.assertNotEqual(nuevo, viejo)
        finally:
            seguridad.CLAVE_CIFRADO, seguridad.CLAVES_CIFRADO_PREVIAS = antes[0], antes[1]


class RecibosYPushTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.nombre = "cif_" + uuid.uuid4().hex[:6]
        with self.app.app_context():
            db = get_db()
            self.uid = db.execute(
                "INSERT INTO usuarios (nombre_usuario,password_hash,fecha_creacion) VALUES (?,?,?)",
                (self.nombre, generate_password_hash("password123"), ahora())).lastrowid
            self.hid = db.execute(
                "INSERT INTO hogares (nombre,usuario_propietario_id,privada,fecha_creacion,fecha_actualizacion) VALUES (?,?,1,?,?)",
                ("Cif", self.uid, ahora(), ahora())).lastrowid
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

    def _gasto(self):
        r = self.c.post("/api/gastos", json={"descripcion": "A", "importe_total": 5, "fecha": "2024-01-01",
                                             "usuario_pagador_id": self.uid,
                                             "participantes": [{"usuario_id": self.uid, "importe": 5}]})
        self.assertIn(r.status_code, (200, 201), r.get_data(as_text=True))
        j = r.get_json()
        return j.get("id") or j["data"]["id"]

    def test_recibo_se_guarda_cifrado_y_se_sirve_en_claro(self):
        gid = self._gasto()
        buf = io.BytesIO()
        Image.new("RGB", (20, 20), (200, 10, 10)).save(buf, "PNG")
        r = self.c.post(f"/api/gastos/{gid}/recibo", data={"foto": (io.BytesIO(buf.getvalue()), "r.png")},
                        content_type="multipart/form-data")
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        with self.app.app_context():
            crudo = bytes(get_db().execute("SELECT imagen_recibo FROM gastos WHERE id=?", (gid,)).fetchone()[0])
        self.assertTrue(crudo.startswith(b"DRM1\x00"))
        self.assertNotIn(b"PNG", crudo[:40])
        r = self.c.get(f"/api/gastos/{gid}/recibo")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Image.open(io.BytesIO(r.data)).size, (20, 20))

    def test_recibo_antiguo_en_claro_se_cifra_al_migrar(self):
        gid = self._gasto()
        with self.app.app_context():
            db = get_db()
            db.execute("UPDATE gastos SET imagen_recibo=?, imagen_recibo_mime='image/png' WHERE id=?", (b"viejo-en-claro", gid))
            db.commit()
            self.assertGreaterEqual(cifrado.cifrar_existentes(db), 1)
            crudo = bytes(db.execute("SELECT imagen_recibo FROM gastos WHERE id=?", (gid,)).fetchone()[0])
        self.assertTrue(crudo.startswith(b"DRM1\x00"))
        self.assertEqual(cifrado.descifrar_bytes(crudo), b"viejo-en-claro")

    def test_claves_push_cifradas(self):
        ep = "https://fcm.googleapis.com/fake/" + uuid.uuid4().hex
        r = self.c.post("/api/push/suscribir", json={"endpoint": ep, "keys": {"p256dh": "PUBKEY", "auth": "AUTHSECRET"}})
        self.assertIn(r.status_code, (200, 201), r.get_data(as_text=True))
        with self.app.app_context():
            f = get_db().execute("SELECT p256dh, auth FROM push_subscriptions WHERE endpoint=?", (ep,)).fetchone()
        self.assertTrue(f["auth"].startswith("DRM1:"))
        self.assertEqual(cifrado.descifrar_texto(f["auth"]), "AUTHSECRET")

    def test_cabeceras(self):
        r = self.c.get("/api/auth/estado")
        self.assertEqual(r.headers.get("Cache-Control"), "no-store")
        self.assertEqual(r.headers.get("Cross-Origin-Opener-Policy"), "same-origin")
        self.assertEqual(r.headers.get("X-Content-Type-Options"), "nosniff")


if __name__ == "__main__":
    unittest.main()
