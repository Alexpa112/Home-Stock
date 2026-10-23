"""Revision de seguridad ronda 2 (2026-10-23): instalador, cadena de suministro y frontend.

Todo se prueba leyendo los ficheros (sin servidor, sin Docker, sin red).
"""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
BASH = shutil.which("bash")


def _leer(*ruta):
    return RAIZ.joinpath(*ruta).read_text(encoding="utf-8")


def _paso(install, inicio, fin):
    i = install.index(f'step_start "{inicio}"')
    return install[i:install.index(f'step_start "{fin}"', i)]


class DespliegueFijadoPorCommitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.install = _leer("install.sh")
        cls.compose = _leer("docker-compose.yml")

    def test_compose_usa_la_etiqueta_fijada_y_cae_a_latest(self):
        self.assertIn("home-stock-backend:${STOCKHOGAR_IMAGE_TAG:-latest}", self.compose)
        self.assertIn("home-stock-frontend:${STOCKHOGAR_IMAGE_TAG:-latest}", self.compose)

    def test_el_respaldo_rollback_se_hace_antes_del_pull(self):
        self.assertLess(self.install.index('step_start "Guardar las imágenes actuales (rollback)"'),
                        self.install.index('step_start "Descargar imágenes precompiladas (GHCR)"'))

    def test_el_pin_solo_se_fija_si_las_imagenes_del_commit_existen(self):
        paso = _paso(self.install, "Descargar imágenes precompiladas (GHCR)", "Construir imágenes")
        self.assertIn("scripts/imagen_publicada.sh", paso)
        self.assertLess(paso.index("imagen_publicada.sh"), paso.index('fijar_env STOCKHOGAR_IMAGE_TAG "$COMMIT_DESPLIEGUE"'))
        # sin confirmacion se quita el pin (nunca se bloquea el despliegue)
        self.assertIn('fijar_env STOCKHOGAR_IMAGE_TAG ""', paso)
        # el pin va antes del pull
        self.assertLess(paso.index("fijar_env STOCKHOGAR_IMAGE_TAG"), paso.index('"${COMPOSE[@]}" pull'))

    def test_el_rollback_restaura_el_pin_anterior(self):
        i = self.install.index("rollback() {")
        bloque = self.install[i:self.install.index("handle_error() {")]
        self.assertIn('fijar_env STOCKHOGAR_IMAGE_TAG "${PIN_PREVIO:-}"', bloque)
        self.assertLess(bloque.index("fijar_env STOCKHOGAR_IMAGE_TAG"), bloque.index("up -d --force-recreate"))

    def test_la_firma_se_verifica_antes_de_traer_el_codigo(self):
        paso = _paso(self.install, "Actualizar código (git pull)", "Instalar Docker")
        self.assertEqual(paso.count("bash scripts/verificar_firma.sh"), 2)  # --update y --reinstall
        self.assertLess(paso.index("bash scripts/verificar_firma.sh"), paso.index("run git reset --hard"))
        self.assertLess(paso.rindex("bash scripts/verificar_firma.sh"), paso.index("run git pull --ff-only"))

    def test_el_cron_entrecomilla_la_ruta(self):
        self.assertIn("'$SCRIPT_DIR/scripts/auto_update.sh'", self.install)

    def test_los_permisos_se_repiten_cuando_env_y_data_ya_existen(self):
        resumen = self.install[self.install.index('step_start "Resumen"'):]
        self.assertIn("ajustar_permisos_secretos", resumen)
        validar = _paso(self.install, "Validar configuración de Docker Compose", "Guardar las imágenes actuales (rollback)")
        self.assertIn("chmod 600 .env", validar)


class SshYFirewallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.install = _leer("install.sh")
        cls.paso = _paso(cls.install, "Reforzar la seguridad del sistema", "Detectar Docker Compose")

    def test_no_usa_variables_de_entorno_sin_valor_por_defecto(self):
        # install.sh corre con `set -u` y el cron no define SSH_CONNECTION: sin ":-" aborta el paso
        self.assertNotIn("${SSH_CONNECTION%%", self.paso)
        self.assertIn('${SSH_CONNECTION:-}', self.paso)

    def test_el_ssh_va_en_un_fichero_que_sshd_lee_primero(self):
        self.assertIn("sshd_config.d/00-dreame.conf", self.paso)
        # migra el nombre antiguo (99-) para que no quede un fichero que ya no se mantiene
        self.assertIn("99-dreame.conf", self.paso)
        self.assertIn('rm -f "$SSH_CONF_ANTIGUO"', self.paso)

    def test_se_comprueba_que_lo_pedido_queda_en_vigor(self):
        self.assertIn("sshd -T", self.paso)
        self.assertIn("NO está en vigor", self.paso)

    def test_la_contrasena_de_ssh_exige_permisos_que_sshd_acepte(self):
        self.assertIn("-perm /022", self.paso)
        self.assertIn("StrictModes", self.paso)

    def test_fail2ban_no_bloquea_loopback_ni_a_quien_instala(self):
        self.assertIn("ignoreip", self.paso)
        self.assertIn("127.0.0.1/8", self.paso)
        self.assertIn("SSH_CONNECTION", self.paso)

    def test_las_reglas_ufw_de_permiso_van_antes_de_la_politica_de_denegar(self):
        self.assertLess(self.paso.index('ufw limit "${SSH_PUERTO}/tcp"'), self.paso.index("ufw default deny incoming"))
        self.assertLess(self.paso.index('ufw allow from "$RED_PRIVADA"'), self.paso.index("ufw default deny incoming"))

    def test_daemon_json_se_fusiona_y_no_se_pisa(self):
        self.assertIn('d.setdefault("no-new-privileges", True)', self.paso)
        self.assertIn('d.setdefault("live-restore", True)', self.paso)
        self.assertIn("daemon.json.dreame.bak".replace("daemon.json", "${DAEMON_JSON}"), self.paso)
        # Docker solo se reinicia si no hay contenedores en marcha
        self.assertIn('docker ps -q', self.paso)

    def test_kernel_y_core_dumps(self):
        for marca in ("fs.protected_fifos = 2", "fs.protected_regular = 2", "kernel.unprivileged_bpf_disabled = 1",
                      "fs.suid_dumpable = 0", "limits.d/99-dreame.conf", "* hard core 0"):
            self.assertIn(marca, self.paso, marca)

    def test_avisa_de_la_contrasena_por_defecto_sin_cambiar_nada(self):
        self.assertIn("raspberry", self.paso)
        self.assertIn("POR DEFECTO", self.paso)
        self.assertNotIn("chpasswd", self.paso)
        self.assertNotIn("passwd -l", self.paso)

    def test_el_reinicio_automatico_es_opt_in(self):
        self.assertIn('DREAME_REINICIO_AUTOMATICO:-0}" == "1"', self.paso)

    def test_ssh_con_registro_detallado_y_sin_reenvio_de_agente(self):
        for marca in ("AllowAgentForwarding no", "LogLevel VERBOSE", "MaxSessions 4"):
            self.assertIn(marca, self.paso, marca)
        # el reenvio de puertos NO se desactiva: el usuario puede usarlo para llegar al panel
        self.assertNotIn("AllowTcpForwarding no", self.paso)

    def test_protocolos_en_desuso_y_registro_del_cortafuegos(self):
        for marca in ("install dccp /bin/true", "install sctp /bin/true", "ufw logging low"):
            self.assertIn(marca, self.paso, marca)

    def test_servicios_innecesarios(self):
        self.assertIn("cups cups-browsed rpcbind", self.paso)


@unittest.skipUnless(BASH, "requiere bash")
class ScriptsDeDespliegueTests(unittest.TestCase):
    def _ejecutar(self, *args, env=None):
        return subprocess.run([BASH, str(RAIZ / "scripts" / args[0]), *args[1:]], capture_output=True, text=True,
                              env=env, timeout=60)

    def test_sintaxis_valida(self):
        for nombre in ("install.sh", "scripts/auto_update.sh", "scripts/imagen_publicada.sh", "scripts/verificar_firma.sh"):
            r = subprocess.run([BASH, "-n", str(RAIZ / nombre)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{nombre}: {r.stderr}")

    def test_imagen_publicada_rechaza_etiquetas_raras(self):
        # la etiqueta acaba en una referencia de imagen: nada de espacios, ';' ni '$()'
        for rara in ("a b", "x;rm -rf /", "$(id)", "../../x", ""):
            r = self._ejecutar("imagen_publicada.sh", rara)
            self.assertEqual(r.returncode, 2, repr(rara))

    def test_verificar_firma_no_hace_nada_sin_fichero_de_firmantes(self):
        import os
        env = {**os.environ, "HOME": str(RAIZ / "no-existe"), "DREAME_ALLOWED_SIGNERS": ""}
        r = self._ejecutar("verificar_firma.sh", "HEAD", env=env)
        if Path("/etc/dreame/allowed_signers").exists():
            self.skipTest("esta maquina tiene firmantes configurados")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_auto_update_espera_las_imagenes_del_commit_y_verifica_la_firma(self):
        txt = _leer("scripts", "auto_update.sh")
        self.assertIn("imagen_publicada.sh", txt)
        self.assertIn("verificar_firma.sh", txt)
        self.assertIn("mktemp", txt)


class CadenaDeSuministroTests(unittest.TestCase):
    def test_todas_las_acciones_estan_fijadas_por_sha(self):
        for wf in sorted((RAIZ / ".github" / "workflows").glob("*.yml")):
            for linea in wf.read_text(encoding="utf-8").splitlines():
                m = re.match(r"\s*-?\s*uses:\s*(\S+)", linea)
                if m and not m.group(1).startswith("./"):
                    self.assertRegex(m.group(1), r"@[0-9a-f]{40}$", f"{wf.name}: {linea.strip()}")

    def test_publicar_etiqueta_por_commit_y_no_se_pisa_entre_ejecuciones(self):
        wf = _leer(".github", "workflows", "docker-publish.yml")
        self.assertIn("group: publicar-imagenes", wf)
        self.assertIn("${{ env.COMMIT }}", wf)
        self.assertIn("github.event.workflow_run.head_sha", wf)
        self.assertIn("conclusion != 'success'", wf)

    def test_dependabot_vigila_las_acciones(self):
        self.assertIn('package-ecosystem: "github-actions"', _leer(".github", "dependabot.yml").replace("'", '"'))


class FrontendTests(unittest.TestCase):
    def test_diagnose_no_existe_en_produccion(self):
        txt = _leer("app", "diagnose", "layout.tsx")
        self.assertIn("process.env.NODE_ENV === 'production'", txt)
        self.assertIn("notFound()", txt)

    def test_el_service_worker_no_navega_a_otro_origen(self):
        sw = _leer("public", "sw.js")
        self.assertIn("destinoSeguro", sw)
        self.assertIn("new URL(", sw)
        self.assertIn("location.origin", sw)

    def test_cabeceras_de_aislamiento_y_sin_x_powered_by(self):
        cfg = _leer("next.config.mjs")
        self.assertIn("poweredByHeader: false", cfg)
        self.assertIn("Cross-Origin-Opener-Policy", cfg)
        self.assertIn("Cross-Origin-Resource-Policy", cfg)
        self.assertIn("no-referrer", cfg)

    def test_la_cache_se_vincula_al_usuario(self):
        self.assertIn("sincronizarCacheConUsuario", _leer("lib", "dataCache.ts"))
        self.assertIn("sincronizarCacheConUsuario", _leer("components", "shared", "ProtectedRoute.tsx"))
        api = _leer("lib", "api.ts")
        self.assertGreaterEqual(api.count("clearAllCache()"), 3)

    def test_la_version_no_revela_el_origen(self):
        self.assertNotIn('"source"', _leer("stockhogar", "rutas", "sistema", "version.py"))


if __name__ == "__main__":
    unittest.main()
