"""El paso de seguridad de install.sh corre con `set -Eeuo pipefail` y un trap ERR que aborta la
instalacion: este test ejecuta el bloque con las ordenes del sistema simuladas y rutas temporales,
en las condiciones del cron (sin SSH_CONNECTION), y exige que termine sin abortar."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
BASH = shutil.which("bash")


@unittest.skipUnless(BASH, "requiere bash")
class PasoSeguridadNoAbortaTests(unittest.TestCase):
    def test_el_bloque_termina_bajo_errexit_nounset_pipefail_sin_ssh_connection(self):
        s=(RAIZ/'install.sh').read_text(encoding='utf-8')
        i=s.index('step_start "Reforzar la seguridad del sistema"'); j=s.index('step_start "Detectar Docker Compose"')
        bloque=s[i:j]
        k=s.index('escribir_si_cambia() {'); fn=s[k:s.index('\n}\n',k)+3]
        root=tempfile.mkdtemp().replace(chr(92),'/')
        bloque=bloque.replace('step_start "Reforzar la seguridad del sistema"','').replace('step_end','')
        bloque=bloque.replace('/etc/',root+'/etc/').replace('/run/systemd/system',root+'/run')
        os.makedirs(root+'/run');
        for d in ('apt/apt.conf.d','sysctl.d','security/limits.d','ssh/sshd_config.d','fail2ban/jail.d','docker'): os.makedirs(root+'/etc/'+d,exist_ok=True)
        pre=r'''
        set -Eeuo pipefail
        trap 'echo "ERR linea $LINENO (cmd: $BASH_COMMAND)"; exit 99' ERR
        SCRIPT_DIR="%s"; LOG_FILE=/dev/null; SUDO=""
        cd "$SCRIPT_DIR"; : > .env
        log_info(){ :; }; log_success(){ :; }; log_warning(){ echo "WARN: $*"; }
        check_cmd(){ command -v "$1" >/dev/null 2>&1 || declare -F "$1" >/dev/null; }
        systemctl(){ return 0; }; dpkg(){ return 0; }; apt-get(){ return 0; }
        ufw(){ if [[ "$1" == show ]]; then echo "ufw limit 22/tcp"; fi; return 0; }
        sshd(){ if [[ "$1" == -T ]]; then printf 'port 22\nmaxauthtries 6\npermitemptypasswords no\nx11forwarding no\n'; fi; return 0; }
        docker(){ return 0; }; fail2ban-client(){ return 0; }; sysctl(){ return 0; }; ss(){ echo "LISTEN 0 4096 0.0.0.0:22 x"; }
        getent(){ return 2; }; pgrep(){ return 1; }
        id(){ if [[ "${1:-}" == pi ]]; then return 1; fi; command id "$@"; }
        unset SSH_CONNECTION
        ''' % root
        tail='\necho HARNESS_OK\n'
        open(root+'/h.sh','w',newline=chr(10),encoding='utf-8').write(pre+fn+chr(10)+bloque+tail)
        r=subprocess.run([BASH,root+'/h.sh'],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60)

        self.assertEqual(r.returncode, 0, r.stdout[-600:] + r.stderr[-600:])
        self.assertIn("HARNESS_OK", r.stdout)


if __name__ == "__main__":
    unittest.main()
