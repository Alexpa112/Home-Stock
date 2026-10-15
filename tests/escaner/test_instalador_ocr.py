"""El instalador y los Dockerfiles contemplan el lector neuronal de tickets."""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
INSTALL = (RAIZ / "install.sh").read_text(encoding="utf-8")


def _valor_por_defecto(variable, arch, memoria_mb):
    """Ejecuta la funcion DEFAULT_VALUE real de install.sh con ARCH/MEMORY_MB dados."""
    funcion = re.search(r"^DEFAULT_VALUE\(\) \{.*?^\}", INSTALL, re.S | re.M).group(0)
    salida = subprocess.run(
        ["bash", "-c", f'ARCH={arch}; MEMORY_MB={memoria_mb}; {funcion}\nDEFAULT_VALUE {variable}'],
        capture_output=True, text=True, check=True,
    )
    return salida.stdout.strip()


class InstaladorTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("bash"), "sin bash")
    def test_sintaxis_valida(self):
        subprocess.run(["bash", "-n", str(RAIZ / "install.sh")], check=True)

    def test_exige_los_ficheros_nuevos_del_escaner(self):
        for f in ("stockhogar/integraciones/ocr_rapid.py", "stockhogar/servicios/ocr/diccionario/datos_off.py",
                  "stockhogar/servicios/ocr/cuadre_ticket.py", "stockhogar/servicios/ocr/diccionario/__init__.py"):
            with self.subTest(f=f):
                self.assertIn(f'"{f}"', INSTALL)
                self.assertTrue((RAIZ / f).is_file())

    def test_variables_nuevas_en_el_env(self):
        bloque = re.search(r"REQUIRED_VARS=\((.*?)\n\)", INSTALL, re.S).group(1)
        for v in ("ANTHROPIC_API_KEY", "STOCKHOGAR_MEM_LIMIT"):
            self.assertIn(v, bloque)
        ejemplo = (RAIZ / ".env.example").read_text(encoding="utf-8")
        for v in ("DREAME_OCR_HILOS", "STOCKHOGAR_MEM_LIMIT"):
            self.assertIn(v, ejemplo)

    @unittest.skipUnless(shutil.which("bash"), "sin bash")
    def test_limite_de_memoria_segun_arquitectura_y_ram(self):
        self.assertEqual(_valor_por_defecto("STOCKHOGAR_MEM_LIMIT", "x86_64", 4000), "1024m")
        self.assertEqual(_valor_por_defecto("STOCKHOGAR_MEM_LIMIT", "aarch64", 2000), "1024m")
        self.assertEqual(_valor_por_defecto("STOCKHOGAR_MEM_LIMIT", "armv7l", 4000), "768m")
        self.assertEqual(_valor_por_defecto("STOCKHOGAR_MEM_LIMIT", "aarch64", 1000), "768m")

    def test_compose_usa_el_limite_configurable(self):
        compose = (RAIZ / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("mem_limit: ${STOCKHOGAR_MEM_LIMIT:-1024m}", compose)

    def test_no_se_descargan_imagenes_de_32_bits_en_64_bits(self):
        # docker-publish.yml solo publica linux/arm/v7 (sin lector neuronal).
        publicacion = (RAIZ / ".github" / "workflows" / "docker-publish.yml").read_text(encoding="utf-8")
        if "linux/arm64" not in publicacion:
            self.assertIn('"$ARCH" != "armv7l"', INSTALL)

    def test_comprueba_el_escaner_dentro_del_contenedor(self):
        self.assertIn("ocr_rapid.disponible()", INSTALL)
        self.assertIn("docker exec stockhogar-app", INSTALL)

    def test_avisa_en_32_bits(self):
        self.assertIn("no hay onnxruntime", INSTALL)


class DependenciasTests(unittest.TestCase):
    def test_requirements_lleva_las_dependencias_del_lector_neuronal(self):
        req = (RAIZ / "requirements.txt").read_text(encoding="utf-8")
        for paquete in ("onnxruntime", "pyclipper", "Shapely", "PyYAML"):
            self.assertRegex(req, rf'(?m)^{paquete}.*armv7l')
        # rapidocr NO va en requirements (arrastra opencv-python y choca con headless)
        self.assertNotRegex(req, r"(?m)^rapidocr")

    def test_los_dockerfiles_y_el_ci_instalan_rapidocr_sin_dependencias(self):
        for f in ("Dockerfile", "Dockerfile.raspbian", ".github/workflows/ci.yml"):
            with self.subTest(f=f):
                self.assertRegex((RAIZ / f).read_text(encoding="utf-8"), r"pip install --no-deps rapidocr-onnxruntime==1\.4\.4")

    def test_la_version_es_la_misma_en_todos_los_sitios(self):
        versiones = {re.search(r"rapidocr-onnxruntime==([\d.]+)", (RAIZ / f).read_text(encoding="utf-8")).group(1)
                     for f in ("Dockerfile", "Dockerfile.raspbian", ".github/workflows/ci.yml", "requirements.txt")}
        self.assertEqual(len(versiones), 1, versiones)


if __name__ == "__main__":
    unittest.main()


class DiagnosticoOcrTests(unittest.TestCase):
    """/api/ocr/validar-instalacion: la forma de la respuesta que lee Ajustes."""

    def test_la_respuesta_anida_las_validaciones_y_ajustes_las_lee_ahi(self):
        import uuid
        from werkzeug.security import generate_password_hash
        from stockhogar import create_app
        from stockhogar.db import ahora, get_db
        app = create_app()
        nombre = f"diag_{uuid.uuid4().hex[:8]}"
        with app.app_context():
            db = get_db()
            uid = db.execute("INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                             (nombre, generate_password_hash("password123"), ahora())).lastrowid
            db.commit()
        try:
            cliente = app.test_client()
            with cliente.session_transaction() as s:
                s["usuario"], s["usuario_id"] = nombre, uid
            cuerpo = cliente.get("/api/ocr/validar-instalacion").get_json()
            self.assertIn("validaciones", cuerpo)
            self.assertNotIn("claude_api_key", cuerpo)            # NO en el nivel superior
            for clave in ("claude_api_key", "claude_paquete", "tesseract", "motor_neuronal", "diccionario_articulos"):
                self.assertIn(clave, cuerpo["validaciones"])
            self.assertGreater(cuerpo["validaciones"]["diccionario_articulos"], 3000)
            ajustes = (RAIZ / "app" / "dashboard" / "settings" / "page.tsx").read_text(encoding="utf-8")
            self.assertIn("diag?.validaciones?.claude_api_key", ajustes)
        finally:
            with app.app_context():
                db = get_db()
                db.execute("DELETE FROM usuarios WHERE id = ?", (uid,))
                db.commit()
