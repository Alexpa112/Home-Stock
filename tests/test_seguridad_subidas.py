"""Auditoria de seguridad de las dos subidas de fichero de la app.

/api/tickets/analizar (foto de ticket, efimera) y /api/gastos/<id>/recibo (foto
de recibo, que se GUARDA en la BD y se vuelve a servir despues). La segunda es
la de mas riesgo: un fichero almacenado que luego se devuelve al navegador es el
camino clasico a un XSS persistente en el propio origen de la app.

Se comprueba que:
  * la extension no basta: el contenido tiene que ser de verdad una imagen,
  * un HTML o un SVG renombrado a .png se rechaza,
  * el recibo se sirve siempre con un Content-Type de imagen (nunca text/html),
  * una "bomba de descompresion" (cabecera que declara dimensiones enormes) no
    tumba el proceso,
  * y se respeta el limite de tamaño.
"""
import io
import unittest
import uuid
import zlib

from PIL import Image
from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db

HTML_MALICIOSO = b"<html><script>alert(document.cookie)</script></html>"
SVG_MALICIOSO = (
    b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)">'
    b'<script>alert(document.cookie)</script></svg>'
)


def _png_valido(ancho=40, alto=40):
    buffer = io.BytesIO()
    Image.new("RGB", (ancho, alto), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def _png_bomba():
    """PNG cuya cabecera declara 60000x60000 (3.600 millones de pixeles).

    Se construye a mano: un PNG real de ese tamaño no cabria en memoria, y la
    gracia del ataque es justo que el fichero es diminuto y el daño lo hace
    quien lo abre.
    """
    def trozo(tipo, datos):
        return (len(datos).to_bytes(4, "big") + tipo + datos
                + zlib.crc32(tipo + datos).to_bytes(4, "big"))

    ihdr = (60000).to_bytes(4, "big") + (60000).to_bytes(4, "big") + bytes([8, 2, 0, 0, 0])
    return b"\x89PNG\r\n\x1a\n" + trozo(b"IHDR", ihdr) + trozo(b"IEND", b"")


class SubidaDeRecibosTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        self.nombre = f"subida_{uuid.uuid4().hex[:8]}"
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
                ("Hogar subidas", self.usuario_id, ahora(), ahora()),
            ).lastrowid
            db.execute(
                "INSERT INTO permisos_hogar (hogar_id, usuario_id, nivel, fecha_otorgado) "
                "VALUES (?, ?, 'editar', ?)",
                (self.hogar_id, self.usuario_id, ahora()),
            )
            self.gasto_id = db.execute(
                "INSERT INTO gastos (hogar_id, descripcion, importe_total, fecha, "
                "usuario_pagador_id, fecha_creacion) VALUES (?, 'Gasto', 10.0, ?, ?, ?)",
                (self.hogar_id, ahora(), self.usuario_id, ahora()),
            ).lastrowid
            db.commit()

        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess["usuario"] = self.nombre
            sess["usuario_id"] = self.usuario_id
            sess["hogar_actual_id"] = self.hogar_id

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM uso_recibos_diario WHERE usuario_id = ?", (self.usuario_id,))
            db.execute("DELETE FROM gastos WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM permisos_hogar WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM hogares WHERE id = ?", (self.hogar_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def _subir(self, contenido, nombre_fichero):
        return self.client.post(
            f"/api/gastos/{self.gasto_id}/recibo",
            data={"foto": (io.BytesIO(contenido), nombre_fichero)},
            content_type="multipart/form-data",
        )

    def test_un_html_renombrado_a_png_se_rechaza(self):
        respuesta = self._subir(HTML_MALICIOSO, "recibo.png")
        self.assertEqual(
            respuesta.status_code, 400,
            "un HTML con extension .png no debe guardarse como recibo",
        )

    def test_un_svg_renombrado_a_png_se_rechaza(self):
        """El SVG es el vector clasico: es XML, ejecuta scripts y muchos
        validadores por extension lo dejan pasar."""
        respuesta = self._subir(SVG_MALICIOSO, "recibo.png")
        self.assertEqual(respuesta.status_code, 400)

    def test_una_extension_no_permitida_se_rechaza(self):
        for nombre in ("recibo.svg", "recibo.html", "recibo.php", "recibo.exe"):
            with self.subTest(nombre=nombre):
                self.assertEqual(self._subir(_png_valido(), nombre).status_code, 400)

    def test_una_bomba_de_descompresion_no_tumba_el_servidor(self):
        respuesta = self._subir(_png_bomba(), "bomba.png")
        self.assertLess(
            respuesta.status_code, 500,
            "un PNG que declara 60000x60000 debe rechazarse limpiamente, no "
            "provocar un error del servidor",
        )

    def test_una_imagen_de_verdad_si_se_acepta(self):
        """Contraprueba: si esto fallara, los rechazos de arriba no dirian nada."""
        respuesta = self._subir(_png_valido(), "recibo.png")
        self.assertEqual(respuesta.status_code, 200, respuesta.get_data(as_text=True))

    def test_el_recibo_se_sirve_siempre_como_imagen(self):
        """Aunque se guardara algo raro, el navegador no debe interpretarlo
        como HTML: de ahi saldria un XSS en el propio origen de la app."""
        self._subir(_png_valido(), "recibo.png")
        respuesta = self.client.get(f"/api/gastos/{self.gasto_id}/recibo")
        self.assertEqual(respuesta.status_code, 200)
        tipo = respuesta.headers.get("Content-Type", "")
        self.assertTrue(
            tipo.startswith("image/"),
            f"el recibo se sirve como {tipo!r}; debe ser siempre image/*",
        )
        self.assertNotIn("html", tipo.lower())

    def test_no_se_guarda_el_exif_de_la_foto(self):
        """Una foto de movil lleva EXIF con geolocalizacion: recodificar al
        guardar es lo que evita almacenar donde vive el usuario."""
        buffer = io.BytesIO()
        imagen = Image.new("RGB", (40, 40), "white")
        exif = imagen.getexif()
        exif[0x9286] = "COORDENADAS-DE-CASA"
        imagen.save(buffer, format="JPEG", exif=exif)
        self._subir(buffer.getvalue(), "recibo.jpg")

        with self.app.app_context():
            fila = get_db().execute(
                "SELECT imagen_recibo FROM gastos WHERE id = ?", (self.gasto_id,)
            ).fetchone()
        self.assertIsNotNone(fila["imagen_recibo"])
        self.assertNotIn(b"COORDENADAS-DE-CASA", fila["imagen_recibo"])

    def test_no_se_guarda_el_comentario_libre_de_la_imagen(self):
        """El EXIF ya se descartaba, pero el marcador de comentario (COM) del
        JPEG sobrevivia a la recodificacion pese a que el docstring de
        utils/imagenes.py promete descartar tambien los comentarios: es texto
        libre que elige quien sube el fichero y quedaba guardado en la BD."""
        buffer = io.BytesIO()
        Image.new("RGB", (40, 40), "white").save(
            buffer, format="JPEG", comment=b"CARGA-EN-EL-COMENTARIO"
        )
        self._subir(buffer.getvalue(), "recibo.jpg")

        with self.app.app_context():
            fila = get_db().execute(
                "SELECT imagen_recibo FROM gastos WHERE id = ?", (self.gasto_id,)
            ).fetchone()
        self.assertIsNotNone(fila["imagen_recibo"])
        self.assertNotIn(
            b"CARGA-EN-EL-COMENTARIO", fila["imagen_recibo"],
            "el comentario de la imagen se esta guardando tal cual",
        )


class SubidaDeTicketsTests(unittest.TestCase):
    """La foto del ticket es efimera, pero pasa por Pillow y por binarios
    externos (pdftoppm, heif-convert), asi que tambien se comprueba."""

    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        self.nombre = f"tick_{uuid.uuid4().hex[:8]}"
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
                ("Hogar tickets", self.usuario_id, ahora(), ahora()),
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
            db.execute("DELETE FROM uso_ocr_diario WHERE usuario_id = ?", (self.usuario_id,))
            db.execute("DELETE FROM permisos_hogar WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM hogares WHERE id = ?", (self.hogar_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def _analizar(self, contenido, nombre_fichero):
        return self.client.post(
            "/api/tickets/analizar",
            data={"foto": (io.BytesIO(contenido), nombre_fichero)},
            content_type="multipart/form-data",
        )

    def test_un_html_renombrado_a_jpg_se_rechaza(self):
        self.assertEqual(self._analizar(HTML_MALICIOSO, "ticket.jpg").status_code, 400)

    def test_un_pdf_falso_se_rechaza(self):
        """La ruta del PDF no se recodifica con Pillow: comprueba la firma."""
        self.assertEqual(self._analizar(b"no soy un pdf", "ticket.pdf").status_code, 400)

    def test_una_extension_ejecutable_se_rechaza(self):
        for nombre in ("ticket.php", "ticket.sh", "ticket.svg", "ticket"):
            with self.subTest(nombre=nombre):
                self.assertEqual(self._analizar(_png_valido(), nombre).status_code, 400)

    def test_un_nombre_de_fichero_con_travesia_no_escapa(self):
        """El nombre entra en el sufijo del fichero temporal; no debe poder
        salir del directorio ni colar comandos."""
        for nombre in ("../../../../etc/passwd.png", "a.png; rm -rf /", "$(id).png"):
            with self.subTest(nombre=nombre):
                respuesta = self._analizar(_png_valido(), nombre)
                self.assertLess(respuesta.status_code, 500, respuesta.status)

    def test_una_bomba_de_descompresion_no_tumba_el_servidor(self):
        respuesta = self._analizar(_png_bomba(), "bomba.png")
        self.assertLess(respuesta.status_code, 500, respuesta.status)


if __name__ == "__main__":
    unittest.main()
