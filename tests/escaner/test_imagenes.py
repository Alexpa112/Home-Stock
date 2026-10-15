"""Tests de stockhogar/utils/imagenes.py::validar_y_recodificar (S-16)."""
import io
import unittest

from PIL import Image

from stockhogar.utils.imagenes import validar_y_recodificar


class ValidarYRecodificarTests(unittest.TestCase):
    def test_imagen_jpeg_real_se_acepta_y_se_recodifica(self):
        buffer = io.BytesIO()
        Image.new("RGB", (4, 4), color="blue").save(buffer, format="JPEG")

        resultado, error = validar_y_recodificar(buffer.getvalue(), "jpg")

        self.assertIsNone(error)
        self.assertIsNotNone(resultado)
        Image.open(io.BytesIO(resultado)).verify()

    def test_recodificar_elimina_metadatos_exif(self):
        buffer = io.BytesIO()
        img = Image.new("RGB", (4, 4), color="green")
        exif = img.getexif()
        exif[0x0131] = "SoftwareDePruebaSensible"  # tag "Software"
        img.save(buffer, format="JPEG", exif=exif)
        original_con_exif = buffer.getvalue()
        self.assertIn(b"SoftwareDePruebaSensible", original_con_exif)

        resultado, error = validar_y_recodificar(original_con_exif, "jpg")

        self.assertIsNone(error)
        self.assertNotIn(b"SoftwareDePruebaSensible", resultado)

    def test_contenido_no_imagen_con_extension_de_imagen_se_rechaza(self):
        resultado, error = validar_y_recodificar(b"esto no es una imagen", "jpg")
        self.assertIsNone(resultado)
        self.assertEqual(error, "err_formato_no_permitido")

    def test_extension_no_coincide_con_el_formato_real_se_rechaza(self):
        buffer = io.BytesIO()
        Image.new("RGB", (4, 4), color="red").save(buffer, format="PNG")

        resultado, error = validar_y_recodificar(buffer.getvalue(), "jpg")

        self.assertIsNone(resultado)
        self.assertEqual(error, "err_formato_no_permitido")

    def test_extension_no_cubierta_por_pillow_se_deja_pasar_sin_recodificar(self):
        """heic/heif: fuera de alcance de esta validacion (ver docstring del
        modulo), se deja pasar tal cual para que la llame quien sepa
        convertirla (heif-convert)."""
        contenido = b"bytes-cualquiera-de-un-heic"
        resultado, error = validar_y_recodificar(contenido, "heic")
        self.assertIsNone(error)
        self.assertEqual(resultado, contenido)


if __name__ == "__main__":
    unittest.main()
