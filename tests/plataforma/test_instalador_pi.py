"""Instalador y despliegue en la Raspberry Pi: optimizacion del sistema, compose y auto-actualizacion.

Se leen los ficheros (no se ejecuta nada del sistema); `bash -n` comprueba la sintaxis.
"""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent.parent


def _leer(*ruta):
    return RAIZ.joinpath(*ruta).read_text(encoding="utf-8")


class SintaxisTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("bash"), "sin bash")
    def test_los_scripts_son_sintacticamente_validos(self):
        for script in ("install.sh", "scripts/auto_update.sh", "scripts/docker_cache_prune.sh"):
            r = subprocess.run(["bash", "-n", str(RAIZ / script)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{script}: {r.stderr}")


class OptimizacionDelSistemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.install = _leer("install.sh")
        i = cls.install.index('step_start "Optimizar el sistema')
        cls.paso = cls.install[i:cls.install.index('step_start "Detectar Docker Compose"')]

    def test_se_puede_omitir_y_no_es_fatal(self):
        self.assertIn("DREAME_OPTIMIZAR_SISTEMA", self.paso)
        self.assertIn("DREAME_GPU_MEM", self.paso)
        self.assertNotIn("exit 1", self.paso, "un ajuste de rendimiento nunca debe abortar la instalacion")

    def test_cada_fichero_de_configuracion_se_escribe_de_forma_idempotente(self):
        self.assertIn("escribir_si_cambia()", self.paso)
        self.assertIn("cmp -s", self.paso)
        for destino in ("/etc/sysctl.d/99-dreame.conf", "/etc/systemd/journald.conf.d/99-dreame.conf",
                        "/etc/systemd/system.conf.d/99-dreame-watchdog.conf"):
            self.assertIn(f"escribir_si_cambia {destino}", self.paso, destino)

    def test_swap_ntp_watchdog_y_arranque_de_docker(self):
        for marca in ("dphys-swapfile", "CONF_SWAPSIZE", "/swapfile", "timedatectl set-ntp true",
                      "RuntimeWatchdogSec", "/dev/watchdog", "systemctl enable", "vm.swappiness = 10"):
            self.assertIn(marca, self.paso, marca)

    def test_el_swap_solo_se_amplia_con_disco_de_sobra(self):
        self.assertIn('"${FREE_DISK_MB:-0}" -gt', self.paso)

    def test_los_ajustes_de_pi_solo_se_aplican_en_una_pi(self):
        i = self.paso.index('if [[ "$ES_PI" -eq 1 ]]')
        bloque_pi = self.paso[i:]
        for marca in ("bluetooth", "ModemManager", "gpu_mem", ".dreame.bak"):
            self.assertIn(marca, bloque_pi, marca)
        self.assertIn("grep -qE '^\\s*gpu_mem'", bloque_pi, "no se pisa un gpu_mem que el usuario ya fijo")

    def test_avisa_de_que_hace_falta_reiniciar(self):
        self.assertIn("REBOOT_RECOMENDADO=1", self.paso)
        self.assertIn("sudo reboot", self.install)

    def test_la_optimizacion_va_antes_de_construir_las_imagenes(self):
        self.assertLess(self.install.index("Optimizar el sistema"), self.install.index('step_start "Construir imágenes"'))


class ConcurrenciaYCronTests(unittest.TestCase):
    def test_gunicorn_se_ajusta_a_la_ram_desde_el_env(self):
        install = _leer("install.sh")
        self.assertIn("GUNICORN_WORKERS", install)
        self.assertIn("GUNICORN_THREADS", install)
        for dockerfile in ("Dockerfile", "Dockerfile.raspbian"):
            texto = _leer(dockerfile)
            self.assertIn("--workers ${GUNICORN_WORKERS:-2}", texto, dockerfile)
            self.assertIn("--threads ${GUNICORN_THREADS:-4}", texto, dockerfile)
            self.assertIn("--timeout 240", texto, "la escalera de timeouts del escaner depende de este valor")

    def test_se_instala_el_cron_de_purga_de_la_cache_de_docker(self):
        install = _leer("install.sh")
        self.assertIn("docker_cache_prune.sh", install)
        self.assertRegex(install, r'CRON_PURGA="\d+ \d+ \* \* \* \$SCRIPT_DIR/scripts/docker_cache_prune\.sh')


class ComposeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compose = yaml.safe_load(_leer("docker-compose.yml"))

    def test_los_logs_rotan_en_los_dos_servicios(self):
        for nombre in ("stockhogar", "frontend"):
            log = self.compose["services"][nombre]["logging"]
            self.assertEqual(log["driver"], "json-file", nombre)
            self.assertEqual(log["options"]["max-size"], "10m", nombre)
            self.assertEqual(log["options"]["max-file"], "3", nombre)

    def test_el_backend_usa_init_tmpfs_y_limite_de_procesos(self):
        backend = self.compose["services"]["stockhogar"]
        self.assertTrue(backend["init"])
        self.assertTrue(any(t.startswith("/tmp") for t in backend["tmpfs"]))
        self.assertLessEqual(backend["pids_limit"], 1024)

    def test_el_tmpfs_cabe_en_el_limite_de_memoria(self):
        backend = self.compose["services"]["stockhogar"]
        tmpfs_mb = int(re.search(r"size=(\d+)m", backend["tmpfs"][0]).group(1))
        self.assertLessEqual(tmpfs_mb, 256)

    def test_el_frontend_no_espera_a_service_healthy(self):
        """En una Pi el backend tarda 90-120 s en estar healthy, mas que la ventana de su HEALTHCHECK:
        con service_healthy `compose up` abortaria y install.sh haria rollback de una imagen buena."""
        self.assertEqual(self.compose["services"]["frontend"]["depends_on"], ["stockhogar"])

    def test_los_dos_servicios_se_reinician_solos(self):
        for nombre in ("stockhogar", "frontend"):
            self.assertEqual(self.compose["services"][nombre]["restart"], "unless-stopped", nombre)


class AutoActualizacionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = _leer("scripts", "auto_update.sh")

    def test_con_el_mismo_commit_comprueba_si_hay_imagenes_nuevas(self):
        i = self.script.index('if [[ "$LOCAL_REV" == "$REMOTE_REV" ]]')
        bloque = self.script[i:self.script.index("exec 200>&-\n\necho", i)]
        self.assertIn("refrescar_imagenes", bloque)
        self.assertIn("docker compose pull", bloque)
        self.assertIn("docker image inspect", bloque)
        self.assertIn("ghcr.io/alexpa112/home-stock-backend:latest", bloque)
        self.assertIn("ghcr.io/alexpa112/home-stock-frontend:latest", bloque)

    def test_solo_actua_si_el_id_de_la_imagen_cambio(self):
        self.assertIn('[[ "$antes" != "$despues" ]] || return 0', self.script)

    def test_solo_en_armv7l_donde_se_publican_imagenes(self):
        self.assertIn('[[ "$arch" == armv7l || "$arch" == armv6l ]] || return 0', self.script)

    def test_sin_red_no_es_un_error(self):
        self.assertIn("docker compose pull --quiet >/dev/null 2>&1 || return 0", self.script)

    def test_aplica_con_install_sh_que_hace_backup_y_rollback(self):
        i = self.script.index("refrescar_imagenes() {")
        self.assertIn("./install.sh --update", self.script[i:i + 2500])


if __name__ == "__main__":
    unittest.main()
