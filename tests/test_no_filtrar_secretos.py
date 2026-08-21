"""Regresion: los secretos no pueden entrar ni en git ni en la imagen Docker.

Contexto (auditoria 2026-08, hallazgos C-1, A-8 y A-9):

- C-1: el commit d3cb82d2 publico `data/secret.json` (la clave que firma las
  cookies de sesion), `data/stock.db` con usuarios y hashes scrypt reales, y
  4.900 lineas de `logs/stockhogar.log`, en una rama que siguio viva en origin
  durante semanas. Los patrones de .gitignore iban por extension y no cubrian
  todo lo que un `git add -A` arrastraba.
- A-8: `.dockerignore` no excluia `.env`, asi que los dos Dockerfile de backend
  (`COPY . /app/`) horneaban las credenciales en una capa de la imagen cada vez
  que install.sh compilaba localmente en la Pi.
- A-9: install.sh copiaba el `.env` en claro a `data/backups/`, que es el
  directorio que el Panel de Gestion sirve por HTTP para descargar copias.

Estos tests son baratos y de fichero, no de aplicacion: su valor es que fallan
en CI si alguien afloja un patron.
"""
import subprocess
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Rutas que NUNCA deben poder entrar en un commit.
RUTAS_PROHIBIDAS_EN_GIT = [
    ".env",
    ".env.production",
    "data/secret.json",
    "data/stock.db",
    "data/stock.db-wal",
    # El que se escapaba: scripts/maintenance.sh genera este nombre y
    # `data/*.db` no lo cubria.
    "data/stock.db.backup.20260101-120000",
    "data/backups/stockhogar-20260101.db",
    "logs/stockhogar.log",
    "logs/stockhogar.log.1",
    "uploads/ticket.jpg",
]


class GitignoreTests(unittest.TestCase):
    def test_los_ficheros_sensibles_estan_ignorados(self):
        # `git check-ignore` evalua los patrones sin necesidad de crear nada.
        proceso = subprocess.run(
            ["git", "check-ignore", "--no-index", *RUTAS_PROHIBIDAS_EN_GIT],
            cwd=RAIZ, capture_output=True, text=True,
        )
        ignoradas = set(proceso.stdout.split())
        sin_cubrir = [r for r in RUTAS_PROHIBIDAS_EN_GIT if r not in ignoradas]
        self.assertFalse(
            sin_cubrir,
            "estas rutas NO estan cubiertas por .gitignore y un `git add -A` "
            f"las commitearia: {sin_cubrir}",
        )

    def test_env_example_sigue_versionado(self):
        """La plantilla si tiene que viajar en el repo: es la que copia install.sh."""
        proceso = subprocess.run(
            ["git", "check-ignore", "--no-index", ".env.example"],
            cwd=RAIZ, capture_output=True, text=True,
        )
        self.assertNotEqual(
            proceso.returncode, 0,
            ".env.example esta ignorado; install.sh lo necesita para crear el .env",
        )

    def test_no_hay_nada_versionado_bajo_data_logs_o_uploads(self):
        proceso = subprocess.run(
            ["git", "ls-files", "data/", "logs/", "uploads/"],
            cwd=RAIZ, capture_output=True, text=True,
        )
        self.assertEqual(
            proceso.stdout.strip(), "",
            "hay ficheros versionados bajo data/, logs/ o uploads/:\n" + proceso.stdout,
        )


class DockerignoreTests(unittest.TestCase):
    """El .dockerignore no admite `git check-ignore`, asi que se comprueban los
    patrones textualmente. Docker los evalua con las mismas reglas de glob."""

    def setUp(self):
        self.lineas = {
            l.strip()
            for l in (RAIZ / ".dockerignore").read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.strip().startswith("#")
        }

    def test_excluye_el_env_y_sus_variantes(self):
        for patron in (".env", ".env.*"):
            self.assertIn(
                patron, self.lineas,
                f"falta '{patron}' en .dockerignore: COPY . /app/ hornearia las "
                "credenciales en una capa de la imagen",
            )

    def test_excluye_datos_de_ejecucion_y_claves(self):
        for patron in ("data/", "logs/", "*.pem", ".git"):
            self.assertIn(patron, self.lineas, f"falta '{patron}' en .dockerignore")

    def test_los_dockerfile_de_backend_copian_todo_el_contexto(self):
        """Justifica por que el .dockerignore es la unica defensa: si algun dia
        los Dockerfile dejasen de hacer COPY masivo, este test avisa de que la
        premisa cambio."""
        copia_masiva = False
        for nombre in ("Dockerfile", "Dockerfile.raspbian"):
            texto = (RAIZ / nombre).read_text(encoding="utf-8")
            if "COPY . " in texto:
                copia_masiva = True
        self.assertTrue(
            copia_masiva,
            "ningun Dockerfile copia el contexto entero; revisa si los patrones "
            "de .dockerignore siguen siendo necesarios",
        )


class InstaladorTests(unittest.TestCase):
    def test_install_no_respalda_el_env_en_la_carpeta_que_sirve_el_panel(self):
        texto = (RAIZ / "install.sh").read_text(encoding="utf-8")
        self.assertNotIn(
            'cp ".env" "data/backups/', texto,
            "install.sh vuelve a dejar el .env en claro en data/backups/, que es "
            "el directorio que el Panel expone por HTTP para descargar copias",
        )
        self.assertIn(
            'install -m 600 ".env"', texto,
            "el respaldo del .env debe crearse con permisos 600 desde el origen",
        )



class ClaveFiltradaEnElHistorialTests(unittest.TestCase):
    """La clave de firma que se publico en d3cb82d2 no puede seguir en uso.

    Hallazgo C-1 (ver la cabecera de este fichero): ese commit publico
    `data/secret.json`. Los tests de arriba evitan filtraciones NUEVAS, pero
    ninguno comprobaba lo que de verdad decide el riesgo: si el despliegue
    sigue firmando cookies con la clave que ya es publica.

    Mientras lo siga haciendo, cualquiera que clone el repositorio puede
    fabricar una cookie de sesion valida para CUALQUIER usuario y entrar sin
    contraseña. `claves_verificacion_previas` (stockhogar/seguridad.py)
    mantiene validas hasta dos claves anteriores, asi que una sola rotacion no
    basta si la filtrada quedo en esa lista.

    La constante de abajo NO filtra nada nuevo: ese valor ya es publico. Esta
    aqui justo para poder reconocerlo y rechazarlo.
    """

    CLAVE_PUBLICADA = "6def2a03996f0fdcaf8b857e7308910a2d404331e63db13d98a6ac727b949d1c"

    def test_el_despliegue_no_usa_la_clave_publicada(self):
        import json

        ruta = RAIZ / "data" / "secret.json"
        if not ruta.exists():
            self.skipTest("no hay data/secret.json en este entorno")

        claves = json.loads(ruta.read_text(encoding="utf-8"))
        self.assertNotEqual(
            claves.get("flask_secret_key"), self.CLAVE_PUBLICADA,
            "ESTE DESPLIEGUE FIRMA LAS COOKIES CON UNA CLAVE PUBLICA: cualquiera "
            "puede falsificar la sesion de cualquier usuario. Rota la clave "
            "(stockhogar.seguridad.rotar_clave()) y reinicia el proceso.",
        )
        self.assertNotIn(
            self.CLAVE_PUBLICADA, claves.get("claves_verificacion_previas", []),
            "la clave publica sigue en claves_verificacion_previas, asi que las "
            "cookies firmadas con ella se siguen aceptando. Rota dos veces mas o "
            "vacia esa lista.",
        )

    @unittest.expectedFailure
    def test_el_historial_de_git_sigue_conteniendo_la_clave(self):
        """EXPOSICION CONOCIDA Y PENDIENTE, marcada como fallo esperado.

        Hoy la clave SIGUE siendo recuperable de `d3cb82d2` en un repositorio
        publico, asi que esta comprobacion falla; se marca como fallo esperado
        para no dejar CI en rojo de forma permanente por algo que no se arregla
        con codigo. El arreglo real es del dueño del repositorio:

          1. Rotar la clave de firma (stockhogar.seguridad.rotar_clave()) y
             reiniciar, DOS veces mas si la publicada quedo en
             claves_verificacion_previas.
          2. Purgar el historial publicado (git filter-repo --path data/ --path
             logs/ --invert-paths) y forzar el push en todas las ramas.
          3. Dar por comprometidas las contraseñas cuyos hashes se publicaron y
             pedir su cambio.

        En cuanto se purgue, este test pasara y unittest lo marcara como
        "unexpected success": ESE es el aviso para venir aqui y quitar el
        decorador @unittest.expectedFailure.
        """
        proceso = subprocess.run(
            ["git", "cat-file", "-e", "d3cb82d2:data/secret.json"],
            cwd=RAIZ, capture_output=True, text=True,
        )
        self.assertNotEqual(
            proceso.returncode, 0,
            "data/secret.json sigue siendo recuperable del historial de git "
            "(commit d3cb82d2) y el repositorio es publico. Hay que purgar el "
            "historial Y rotar la clave: rotar sin purgar deja los hashes de "
            "contraseña expuestos, y purgar sin rotar no sirve de nada porque "
            "cualquiera pudo clonarlo ya.",
        )


if __name__ == "__main__":
    unittest.main()
