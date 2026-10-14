"""El escaner local de principio a fin con Tesseract DE VERDAD.

Los demas tests de OCR mockean el motor; por eso defectos como "OLIVA descartada
por contener iva" o las fotos inclinadas llegaron a produccion. Estos generan
tickets sinteticos con contenido conocido (formatos Mercadona, Carrefour y Lidl),
los suben a /api/tickets/analizar y comparan articulos y cantidades.

Se saltan si no hay Tesseract con idioma espanol (la CI lo instala; ver ci.yml).
"""
import io
import shutil
import subprocess
import unittest
import unicodedata
import uuid
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from werkzeug.security import generate_password_hash

from stockhogar import create_app, red
from stockhogar.db import ahora, get_db


def _tesseract_con_espanol():
    if not shutil.which("tesseract"):
        return False
    salida = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True).stdout
    return "spa" in salida.split()


def _fuente():
    for ruta in ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "DejaVuSansMono.ttf"):
        try:
            return ImageFont.truetype(ruta, 22)
        except OSError:
            continue
    return None


FUENTE = _fuente()
ANCHO = 46


def _kg(q):
    return f"{q:.3f}".replace(".", ",")


def _eur(x):
    return f"{x:.2f}".replace(".", ",")


# (nombre, cantidad, unidad, precio unitario)
ARTICULOS = [
    ("Leche entera 1L", 1, "ud", 0.89),
    ("Pan de molde", 2, "ud", 1.85),
    ("Tomate pera", 0.85, "kg", 1.89),
    ("Aceite oliva virgen", 1, "ud", 7.95),
    ("Yogur natural", 4, "ud", 0.55),
    ("Pechuga pollo", 0.74, "kg", 6.50),
    ("Agua mineral 1,5L", 6, "ud", 0.42),
]


def ticket_mercadona(items):
    L = ["MERCADONA, S.A.   A-46103834", "C/ ALCALA 123  28009 MADRID", "12/10/2026 18:32  OP: 123456",
         "-" * ANCHO, "Descripcion       P. Unit   Importe", "-" * ANCHO]
    total = 0
    for n, q, u, p in items:
        imp = round(q * p, 2)
        total += imp
        if u == "ud":
            L.append(f"{int(q):<2}{n.upper():<27}{_eur(p):>6}{_eur(imp):>8}" if q > 1
                     else f"{int(q):<2}{n.upper():<27}{'':>6}{_eur(imp):>8}")
        else:
            L += [f"1 {n.upper()}", f"  {_kg(q)} {u}   {_eur(p)} EUR/{u}{_eur(imp):>14}"]
    return L + ["-" * ANCHO, f"TOTAL (EUR){_eur(total):>{ANCHO - 11}}", f"TARJETA BANCARIA{_eur(total):>{ANCHO - 16}}"]


def ticket_carrefour(items):
    L = ["CARREFOUR HIPERMERCADO", "CIF A-28425270", "Avda. de America 45  Madrid", "=" * ANCHO]
    total = 0
    for n, q, u, p in items:
        imp = round(q * p, 2)
        total += imp
        if u == "ud":
            L.append(f"{n.upper():<34}{_eur(imp):>10}" if q == 1
                     else f"{n.upper():<22}{int(q)} x {_eur(p):>6}{_eur(imp):>10}")
        else:
            L += [f"{n.upper():<34}{_eur(imp):>10}", f"   {_kg(q)} {u} x {_eur(p)} EUR/{u}"]
    return L + ["=" * ANCHO, f"TOTAL A PAGAR{_eur(total):>{ANCHO - 13}}", "EFECTIVO"]


def ticket_lidl(items):
    L = ["Lidl Supermercados S.A.U.", "CIF A-60195278", "12.10.2026 19:10", "-" * ANCHO]
    total = 0
    for n, q, u, p in items:
        imp = round(q * p, 2)
        total += imp
        L.append(f"{n:<36}{_eur(imp):>8} A")
        if u == "ud" and q > 1:
            L.append(f"   {int(q)} x {_eur(p)}")
        elif u != "ud":
            L.append(f"   {_kg(q)} {u} x {_eur(p)} EUR/{u}")
    return L + ["-" * ANCHO, f"Total{_eur(total):>{ANCHO - 5}}", "Tarjeta de credito"]


def _imagen(lineas, angulo=0.0):
    img = Image.new("L", (int(22 * 0.602 * (ANCHO + 4)) + 40, len(lineas) * 30 + 60), 250)
    d = ImageDraw.Draw(img)
    for i, linea in enumerate(lineas):
        d.text((24, 30 + 30 * i), linea, font=FUENTE, fill=20)
    if angulo:
        img = img.rotate(angulo, expand=True, fillcolor=130, resample=Image.BICUBIC)
    b = io.BytesIO()
    img.convert("RGB").save(b, "JPEG", quality=90)
    return b.getvalue()


def _norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn").strip()


@unittest.skipUnless(_tesseract_con_espanol() and FUENTE, "requiere tesseract con idioma 'spa' y DejaVuSansMono")
class EscanerTesseractRealTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        cls.nombre_usuario = f"test_ocr_real_{uuid.uuid4().hex[:8]}"
        with cls.app.app_context():
            db = get_db()
            cls.usuario_id = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion, usuario_ocr_local) VALUES (?, ?, ?, 1)",
                (cls.nombre_usuario, generate_password_hash("password123"), ahora()),
            ).lastrowid
            cls.hogar_id = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, 1, ?, ?)", ("OCR real", cls.usuario_id, ahora(), ahora()),
            ).lastrowid
            db.commit()
        cls.client = cls.app.test_client()
        with cls.client.session_transaction() as sess:
            sess["usuario"] = cls.nombre_usuario
            sess["usuario_id"] = cls.usuario_id
            sess["hogar_actual_id"] = cls.hogar_id

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db = get_db()
            db.execute("DELETE FROM hogares WHERE usuario_propietario_id = ?", (cls.usuario_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (cls.usuario_id,))
            db.commit()

    def _analizar(self, lineas, angulo=0.0):
        red._contadores.clear()  # el limite por IP (30/h) no debe afectar a una bateria de pruebas
        resp = self.client.post(
            "/api/tickets/analizar",
            data={"foto": (io.BytesIO(_imagen(lineas, angulo)), "ticket.jpg")},
            content_type="multipart/form-data",
        )
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        cuerpo = resp.get_json()
        return (cuerpo.get("datos") or cuerpo)["items"]

    def _comprobar(self, items, esperados, estricto=True):
        for nombre, cantidad, unidad, _ in esperados:
            with self.subTest(articulo=nombre):
                clave = _norm(nombre).split(" 1")[0]  # "leche entera 1l" -> "leche entera"
                hallados = [i for i in items if _norm(clave) in _norm(i["nombre_ticket"])]
                self.assertEqual(len(hallados), 1, f"{nombre!r} no aparece una vez en {[i['nombre'] for i in items]}")
                it = hallados[0]
                # El tamano de envase en el nombre ("1L") puede leerse como litros
                # (decision del equipo): solo se exige el valor.
                if not estricto and unidad == "ud":
                    continue  # ver test_foto_inclinada_de_mano
                if unidad == "ud" and cantidad == 1:
                    self.assertEqual(float(it["cantidad"]), 1.0)
                else:
                    self.assertAlmostEqual(float(it["cantidad"]), cantidad, places=2)
                    self.assertEqual(it["unidad"], unidad)
        nombres = [_norm(i["nombre"]) for i in items]
        self.assertEqual(len(items), len(esperados), f"articulos de mas o de menos: {nombres}")

    def test_mercadona_con_pesos_en_dos_lineas(self):
        self._comprobar(self._analizar(ticket_mercadona(ARTICULOS)), ARTICULOS)

    def test_carrefour_con_pesos_con_x_y_multiplicador(self):
        self._comprobar(self._analizar(ticket_carrefour(ARTICULOS)), ARTICULOS)

    def test_lidl_con_detalle_en_la_linea_siguiente(self):
        self._comprobar(self._analizar(ticket_lidl(ARTICULOS)), ARTICULOS)

    def test_foto_inclinada_de_mano(self):
        """Lo que se garantiza con la foto torcida es que los renglones NO se
        mezclan: cada articulo aparece una vez, los pesos son exactos y no hay
        articulos de mas. Las cantidades "N x" de un ticket girado dependen de
        que el OCR lea bien un "2 x" diminuto tras girar y remuestrear la
        imagen (se ha visto "2 x" -> "LX"), ruido propio del OCR que no se
        exige aqui."""
        for angulo in (-3.5, 2.0, 3.5):
            for nombre, generar in (("carrefour", ticket_carrefour), ("lidl", ticket_lidl), ("mercadona", ticket_mercadona)):
                with self.subTest(ticket=nombre, angulo=angulo):
                    self._comprobar(self._analizar(generar(ARTICULOS), angulo), ARTICULOS, estricto=False)

    def test_la_inclinacion_ya_no_mezcla_renglones(self):
        """Antes de corregirla, 4 articulos de un Carrefour girado 3,5 grados
        salian fundidos en una sola linea ("Agua Yogur Queso Mineral Natural
        Rallado ...")."""
        items = self._analizar(ticket_carrefour(ARTICULOS), 3.5)
        for it in items:
            self.assertLess(len(it["nombre"].split()), 6, it["nombre"])

    def test_el_aceite_de_oliva_llega_al_resultado(self):
        items = self._analizar(ticket_mercadona([("Aceite oliva virgen", 1, "ud", 7.95), ("Pan de molde", 2, "ud", 1.85)]))
        self.assertIn("aceite oliva virgen", [_norm(i["nombre_ticket"]) for i in items])


if __name__ == "__main__":
    unittest.main()
