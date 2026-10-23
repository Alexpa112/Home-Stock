"""Revision de seguridad de 2026-10-22: regresiones de lo corregido.

Backend: se prueba con el cliente de Flask. Infraestructura (compose, instalador, CI): se lee el fichero.
"""
import io
import re
import sqlite3
import threading
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import yaml
from PIL import Image
from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db
from stockhogar.nucleo import red
from stockhogar.rutas.escaner import tickets as modulo_tickets
from stockhogar.servicios import cola_segundo_plano
from stockhogar.utils.imagenes import parece_heif, validar_formato, validar_y_recodificar

RAIZ = Path(__file__).resolve().parent.parent.parent


def _leer(*ruta):
    return RAIZ.joinpath(*ruta).read_text(encoding="utf-8")


class _ClienteBase(unittest.TestCase):
    """Usuario + hogar de prueba con sesion iniciada (sin contrasena si `con_password` es False)."""

    con_password = True

    def setUp(self):
        red._contadores.clear()
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.nombre = f"sec_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            self.usuario_id = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (self.nombre, generate_password_hash("password123") if self.con_password else None, ahora()),
            ).lastrowid
            self.hogar_id = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, 1, ?, ?)",
                ("Hogar sec", self.usuario_id, ahora(), ahora()),
            ).lastrowid
            db.commit()
        self.client = self._cliente()

    def _cliente(self, **extra_sesion):
        cliente = self.app.test_client()
        with cliente.session_transaction() as sess:
            sess["usuario"] = self.nombre
            sess["usuario_id"] = self.usuario_id
            sess["hogar_actual_id"] = self.hogar_id
            sess.update(extra_sesion)
        return cliente

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            for tabla in ("trabajos_ticket",):
                db.execute(f"DELETE FROM {tabla} WHERE usuario_id = ?", (self.usuario_id,))
            for tabla in ("stock_hogar", "articulos_compra", "gastos_recurrentes", "gastos"):
                db.execute(f"DELETE FROM {tabla} WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM hogares WHERE usuario_propietario_id = ?", (self.usuario_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()


class EmailDeCuentaSinContrasenaTests(_ClienteBase):
    """Toma de cuenta OAuth: con solo la cookie se fijaba el email propio, se verificaba y se pedia un reset."""

    con_password = False

    def _fijar_email(self, cliente):
        return cliente.put("/api/auth/perfil", json={"email": f"{uuid.uuid4().hex[:6]}@ejemplo.com"})

    def test_una_cookie_sin_login_reciente_no_puede_fijar_el_email(self):
        r = self._fijar_email(self.client)
        self.assertEqual(r.status_code, 403, r.get_data(as_text=True))

    def test_una_cookie_con_login_viejo_tampoco(self):
        cliente = self._cliente(auth_ts=int(time.time()) - 3600)
        self.assertEqual(self._fijar_email(cliente).status_code, 403)

    def test_con_login_reciente_si_puede(self):
        cliente = self._cliente(auth_ts=int(time.time()) - 30)
        with patch("stockhogar.rutas.cuenta.perfil.enviar_token_verificacion_email"):
            r = self._fijar_email(cliente)
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))

    def test_cambiar_solo_el_nombre_no_exige_login_reciente(self):
        r = self.client.put("/api/auth/perfil", json={"nombre": "Ana"})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))

    def test_el_mensaje_existe_en_los_siete_idiomas(self):
        import json
        textos = json.loads(_leer("stockhogar", "translations.json"))
        for idioma, t in textos.items():
            self.assertTrue(t.get("err_reautenticar_para_cambiar_email"), idioma)


class MarcaDeLoginRecienteTests(unittest.TestCase):
    def test_todos_los_caminos_que_abren_sesion_la_marcan(self):
        for fichero in ("sesion.py", "doble_factor.py", "oauth.py"):
            src = _leer("stockhogar", "rutas", "cuenta", fichero)
            aperturas = src.count('session["usuario_id"] =')
            self.assertEqual(src.count('session["auth_ts"] = int(time.time())'), aperturas, fichero)


class CsrfYLogsTests(unittest.TestCase):
    def test_el_token_csrf_caduca(self):
        app = create_app()
        limite = app.config["WTF_CSRF_TIME_LIMIT"]
        self.assertIsNotNone(limite)
        self.assertLessEqual(limite, 24 * 3600)

    def test_ningun_log_lleva_fragmentos_de_la_cookie_de_sesion(self):
        for ruta in (("stockhogar", "__init__.py"), ("stockhogar", "rutas", "sistema", "paginas.py")):
            src = _leer(*ruta)
            self.assertNotIn('request.cookies.get("session"', src, "/".join(ruta))

    def test_los_emails_se_enmascaran_en_los_logs(self):
        from stockhogar.servicios.cuenta.email_service import _enmascarar
        self.assertEqual(_enmascarar("ana.perez@gmail.com"), "a***@gmail.com")
        self.assertEqual(_enmascarar("sin-arroba"), "***")
        self.assertEqual(_enmascarar(None), "***")
        src = _leer("stockhogar", "servicios", "cuenta", "email_service.py")
        for linea in src.splitlines():
            if "logger." in linea:
                self.assertNotIn("{email_destino}", linea)

    def test_no_se_registra_el_texto_de_la_respuesta_del_modelo(self):
        src = _leer("stockhogar", "servicios", "ocr", "claude_ocr.py")
        self.assertNotIn("limpio[:300]", src)
        self.assertNotIn("texto[:300]", src)


class EscanerBajoPresionTests(_ClienteBase):
    @classmethod
    def _foto(cls):
        buffer = io.BytesIO()
        Image.new("RGB", (400, 700), (255, 255, 255)).save(buffer, format="JPEG")
        return buffer.getvalue()

    def _crear(self, cliente=None):
        return (cliente or self.client).post(
            "/api/tickets/trabajos",
            data={"foto": (io.BytesIO(self._foto()), "ticket.jpg")},
            content_type="multipart/form-data",
        )

    def _ocupar_todas_las_plazas(self):
        """Otros tests dejan trabajos en segundo plano que aun sujetan una plaza: se espera a que
        se liberen en vez de dar por buena una plaza que no se consiguio."""
        plazas = [modulo_tickets._plazas_escaneo.acquire(timeout=30) for _ in range(modulo_tickets.PLAZAS_ESCANEO)]
        self.assertTrue(all(plazas), "no se consiguieron todas las plazas")
        return plazas

    def test_el_indice_unico_parcial_existe(self):
        with self.app.app_context():
            fila = get_db().execute(
                "SELECT sql FROM sqlite_master WHERE name = 'ux_trabajos_ticket_uno_por_usuario'"
            ).fetchone()
        self.assertIsNotNone(fila)
        self.assertIn("WHERE estado = 'procesando'", fila["sql"])

    def test_la_base_de_datos_impide_dos_trabajos_procesando_del_mismo_usuario(self):
        with self.app.app_context():
            db = get_db()
            ahora_s = int(time.time())
            db.execute("INSERT INTO trabajos_ticket (id, usuario_id, estado, creado, actualizado) VALUES ('a', ?, 'procesando', ?, ?)",
                       (self.usuario_id, ahora_s, ahora_s))
            db.commit()
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO trabajos_ticket (id, usuario_id, estado, creado, actualizado) VALUES ('b', ?, 'procesando', ?, ?)",
                           (self.usuario_id, ahora_s, ahora_s))
            db.rollback()
            # pero si el primero ya termino, se puede
            db.execute("UPDATE trabajos_ticket SET estado = 'listo' WHERE id = 'a'")
            db.execute("INSERT INTO trabajos_ticket (id, usuario_id, estado, creado, actualizado) VALUES ('b', ?, 'procesando', ?, ?)",
                       (self.usuario_id, ahora_s, ahora_s))
            db.commit()

    def test_peticiones_simultaneas_solo_dejan_pasar_una(self):
        class _Lento:
            def disponible(self):
                return True

            def procesar(self, *a, **k):
                time.sleep(1.0)
                return {"productos": []}

        resultados = []
        barrera = threading.Barrier(6)

        def disparar():
            cliente = self._cliente()
            barrera.wait()
            resultados.append(self._crear(cliente).status_code)

        with patch.object(modulo_tickets, "ClaudeOCR", _Lento):
            hilos = [threading.Thread(target=disparar) for _ in range(6)]
            for h in hilos:
                h.start()
            for h in hilos:
                h.join()
            # esperar a que termine el unico trabajo antes de desmontar
            limite = time.time() + 20
            while time.time() < limite:
                with self.app.app_context():
                    n = get_db().execute(
                        "SELECT COUNT(*) AS n FROM trabajos_ticket WHERE usuario_id = ? AND estado = 'procesando'",
                        (self.usuario_id,),
                    ).fetchone()["n"]
                if n == 0:
                    break
                time.sleep(0.1)
        self.assertEqual(sorted(resultados), [202, 429, 429, 429, 429, 429], resultados)

    def test_si_falla_la_validacion_se_libera_la_reserva(self):
        r = self.client.post("/api/tickets/trabajos", data={"foto": (io.BytesIO(b"no soy una imagen"), "x.jpg")},
                             content_type="multipart/form-data")
        self.assertEqual(r.status_code, 400)
        # sin la liberacion, esta segunda subida (valida) daria 429
        with patch.object(modulo_tickets, "_ejecutar_analisis", return_value={"items": []}):
            r2 = self._crear()
        self.assertEqual(r2.status_code, 202, r2.get_data(as_text=True))

    def test_con_el_servidor_saturado_el_sincrono_responde_429_y_no_retiene_hilos(self):
        plazas = self._ocupar_todas_las_plazas()
        try:
            r = self.client.post("/api/tickets/analizar", data={"foto": (io.BytesIO(self._foto()), "t.jpg")},
                                 content_type="multipart/form-data")
            self.assertEqual(r.status_code, 429, r.get_data(as_text=True))
        finally:
            for ok in plazas:
                if ok:
                    modulo_tickets._plazas_escaneo.release()
        # y el usuario no queda marcado como "en curso"
        self.assertNotIn(self.usuario_id, modulo_tickets._sincronos_en_curso)

    def test_un_trabajo_sin_plaza_termina_en_error_claro_en_vez_de_esperar_para_siempre(self):
        plazas = self._ocupar_todas_las_plazas()
        try:
            with patch.object(modulo_tickets, "TIEMPO_MAXIMO_TRABAJO_S", 91):  # espera de plaza = 1 s
                trabajo_id = self._crear().get_json()["id"]
                limite = time.time() + 15
                datos = {}
                while time.time() < limite:
                    datos = self.client.get(f"/api/tickets/trabajos/{trabajo_id}").get_json()
                    if datos["estado"] != "procesando":
                        break
                    time.sleep(0.2)
        finally:
            for ok in plazas:
                if ok:
                    modulo_tickets._plazas_escaneo.release()
        self.assertEqual(datos["estado"], "error")
        self.assertEqual(datos["http"], 429)

    def test_los_trabajos_terminados_se_conservan_una_hora_no_un_dia(self):
        self.assertLessEqual(modulo_tickets.CONSERVAR_TRABAJOS_S, 3600)


class ColaEnSegundoPlanoTests(unittest.TestCase):
    """Cada test usa su PROPIA cola: la compartida del proceso puede estar ocupada por traducciones
    reales de otros tests (en CI Argos tarda segundos en cargar el modelo)."""

    def test_los_trabajos_se_atienden_en_orden_y_por_un_solo_hilo(self):
        cola = cola_segundo_plano.ColaSegundoPlano(nombre_hilo="hilo-de-prueba")
        vistos, hilos = [], set()

        def trabajo(n):
            def _():
                vistos.append(n)
                hilos.add(threading.current_thread().name)
            return _

        for n in range(20):
            self.assertTrue(cola.encolar(trabajo(n), f"t{n}"))
        self.assertTrue(cola.esperar_vacia(timeout=10))
        self.assertEqual(vistos, list(range(20)))
        self.assertEqual(hilos, {"hilo-de-prueba"})

    def test_un_trabajo_que_falla_no_mata_al_consumidor(self):
        cola = cola_segundo_plano.ColaSegundoPlano()
        hecho = []
        cola.encolar(lambda: 1 / 0, "falla")
        cola.encolar(lambda: hecho.append(True), "sigue")
        self.assertTrue(cola.esperar_vacia(timeout=10))
        self.assertEqual(hecho, [True])

    def test_si_la_cola_se_llena_se_descarta_en_vez_de_acumular(self):
        cola = cola_segundo_plano.ColaSegundoPlano(tamano_maximo=10)
        liberar = threading.Event()
        cola.encolar(lambda: liberar.wait(10), "bloquea")
        time.sleep(0.1)
        aceptados = sum(cola.encolar(lambda: None, "x") for _ in range(60))
        liberar.set()
        self.assertTrue(cola.esperar_vacia(timeout=10))
        self.assertLessEqual(aceptados, 10)
        self.assertGreater(aceptados, 0)

    def test_la_cola_compartida_tiene_un_unico_consumidor_y_tope(self):
        self.assertEqual(cola_segundo_plano.cola_por_defecto.tamano_maximo, cola_segundo_plano.TAMANO_MAXIMO)
        self.assertIs(cola_segundo_plano.encolar.__self__, cola_segundo_plano.cola_por_defecto)

    def test_traducir_no_crea_un_hilo_por_articulo(self):
        for ruta in (("stockhogar", "rutas", "compra", "lista.py"), ("stockhogar", "rutas", "inventario", "productos.py")):
            self.assertNotIn("threading.Thread(", _leer(*ruta), "/".join(ruta))


class LongitudesTests(_ClienteBase):
    def test_un_nombre_de_articulo_enorme_se_rechaza(self):
        r = self.client.post("/api/articulos", json={"nombre": "x" * 5000})
        self.assertEqual(r.status_code, 400, r.get_data(as_text=True))

    def test_80_caracteres_siguen_valiendo(self):
        r = self.client.post("/api/articulos", json={"nombre": "y" * 80})
        self.assertIn(r.status_code, (200, 201), r.get_data(as_text=True))

    def test_la_descripcion_tiene_tope(self):
        r = self.client.post("/api/articulos", json={"nombre": "Leche", "sub_descripcion": "z" * 5000})
        self.assertIn(r.status_code, (200, 201, 400))  # la creacion ignora la descripcion; la edicion la acota
        validar = __import__("stockhogar.utils", fromlist=["Validator"]).Validator
        with self.assertRaises(Exception):
            validar.texto_acotado("z" * 201, "descripcion", 200)


class HeicTests(unittest.TestCase):
    CABECERA_HEIC = b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00heicmif1"

    def test_un_contenedor_heif_se_reconoce(self):
        self.assertTrue(parece_heif(self.CABECERA_HEIC))
        self.assertTrue(parece_heif(b"\x00\x00\x00\x20ftypmif1" + b"\x00" * 20))

    def test_cualquier_otra_cosa_renombrada_a_heic_se_rechaza(self):
        for contenido in (b"MZ\x90\x00 ejecutable", b"#!/bin/sh\nrm -rf /", b"<script>alert(1)</script>", b"", b"\x00\x00\x00\x18ftypmp42"):
            self.assertFalse(parece_heif(contenido), contenido)
            self.assertEqual(validar_formato(contenido, "heic"), "err_formato_no_permitido")
            self.assertEqual(validar_formato(contenido, "heif"), "err_formato_no_permitido")
            datos, error = validar_y_recodificar(contenido, "heic")
            self.assertIsNone(datos)
            self.assertEqual(error, "err_formato_no_permitido")

    def test_un_heic_valido_pasa_sin_recodificar(self):
        datos, error = validar_y_recodificar(self.CABECERA_HEIC, "heic")
        self.assertIsNone(error)
        self.assertEqual(datos, self.CABECERA_HEIC)
        self.assertIsNone(validar_formato(self.CABECERA_HEIC, "heif"))


class GastosRecurrentesAtomicosTests(_ClienteBase):
    def _crear_recurrente(self):
        with self.app.app_context():
            db = get_db()
            ayer = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))
            rid = db.execute(
                "INSERT INTO gastos_recurrentes (hogar_id, descripcion, importe_total, categoria, usuario_pagador_id, "
                "frecuencia, proxima_fecha, activo, fecha_creacion) VALUES (?, 'Alquiler', 500, 'Vivienda', ?, 'mensual', ?, 1, ?)",
                (self.hogar_id, self.usuario_id, ayer, ahora()),
            ).lastrowid
            db.commit()
            return rid

    def test_dos_generaciones_seguidas_no_duplican_los_gastos(self):
        from stockhogar.rutas.finanzas.recurrentes import generar_gastos_recurrentes_pendientes
        self._crear_recurrente()
        with self.app.app_context():
            db = get_db()
            generar_gastos_recurrentes_pendientes(db, self.hogar_id, self.usuario_id)
            n1 = db.execute("SELECT COUNT(*) AS n FROM gastos WHERE hogar_id = ?", (self.hogar_id,)).fetchone()["n"]
            generar_gastos_recurrentes_pendientes(db, self.hogar_id, self.usuario_id)
            n2 = db.execute("SELECT COUNT(*) AS n FROM gastos WHERE hogar_id = ?", (self.hogar_id,)).fetchone()["n"]
        self.assertGreaterEqual(n1, 1)
        self.assertEqual(n1, n2)

    def test_quien_no_consigue_reclamar_el_recurrente_no_genera_nada(self):
        """Simula la carrera: la peticion B leyo el recurrente ANTES de que A moviera su puntero."""
        from stockhogar.rutas.finanzas import recurrentes as modulo
        self._crear_recurrente()
        with self.app.app_context():
            db = get_db()
            filas_viejas = db.execute("SELECT * FROM gastos_recurrentes WHERE hogar_id = ?", (self.hogar_id,)).fetchall()
            modulo.generar_gastos_recurrentes_pendientes(db, self.hogar_id, self.usuario_id)  # A gana
            antes = db.execute("SELECT COUNT(*) AS n FROM gastos WHERE hogar_id = ?", (self.hogar_id,)).fetchone()["n"]

            real_execute = db.execute

            class _Conexion:
                """B: su SELECT devuelve la foto vieja (puntero sin mover)."""
                def execute(self_, sql, params=()):
                    if sql.lstrip().startswith("SELECT * FROM gastos_recurrentes WHERE hogar_id"):
                        class _R:
                            def fetchall(_):
                                return filas_viejas
                        return _R()
                    return real_execute(sql, params)

                def commit(self_):
                    return db.commit()

            modulo.generar_gastos_recurrentes_pendientes(_Conexion(), self.hogar_id, self.usuario_id)  # B pierde
            despues = db.execute("SELECT COUNT(*) AS n FROM gastos WHERE hogar_id = ?", (self.hogar_id,)).fetchone()["n"]
        self.assertEqual(antes, despues, "la peticion que pierde la carrera no debe insertar gastos")


class InfraestructuraTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compose = yaml.safe_load(_leer("docker-compose.yml"))
        cls.install = _leer("install.sh")

    def test_los_contenedores_no_tienen_capabilities(self):
        for nombre in ("stockhogar", "frontend"):
            self.assertEqual(self.compose["services"][nombre]["cap_drop"], ["ALL"], nombre)
            self.assertNotIn("cap_add", self.compose["services"][nombre], nombre)

    def test_el_frontend_se_publica_en_la_interfaz_que_diga_el_env(self):
        puerto = self.compose["services"]["frontend"]["ports"][0]
        # sin valor en .env el frontend NO queda abierto a la red: el valor por defecto es loopback
        self.assertTrue(puerto.startswith("${STOCKHOGAR_FRONTEND_BIND:-127.0.0.1}:"), puerto)
        self.assertTrue(self.compose["services"]["stockhogar"]["ports"][0].startswith("127.0.0.1:"))

    def test_trivy_esta_fijado_a_una_version(self):
        wf = _leer(".github", "workflows", "docker-build.yml")
        self.assertNotIn("trivy-action@master", wf)
        # fijado por SHA de commit (una etiqueta se puede mover), con la version en un comentario
        self.assertEqual(len(re.findall(r"aquasecurity/trivy-action@[0-9a-f]{40} # v\d+\.\d+\.\d+", wf)), 3)

    def test_get_docker_va_a_un_fichero_temporal_impredecible(self):
        self.assertNotIn("/tmp/get-docker.sh", self.install)
        self.assertIn('mktemp /tmp/get-docker.XXXXXX.sh', self.install)


class InstaladorEndurecidoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.install = _leer("install.sh")
        i = cls.install.index('step_start "Reforzar la seguridad del sistema"')
        cls.paso = cls.install[i:cls.install.index('step_start "Detectar Docker Compose"')]

    def test_se_puede_omitir_y_nada_es_fatal(self):
        self.assertIn("DREAME_ENDURECER_SISTEMA", self.paso)
        self.assertNotIn("exit 1", self.paso)

    def test_hace_lo_que_promete(self):
        for marca in ("unattended-upgrades", "20auto-upgrades", "fail2ban", "ufw default deny incoming",
                      "ufw limit", "sshd_config.d/00-dreame.conf", "99-dreame-seguridad.conf",
                      "net.ipv4.tcp_syncookies", "net.ipv4.conf.all.rp_filter", "chmod 600 .env"):
            self.assertIn(marca, self.paso, marca)

    def test_nunca_deja_al_usuario_sin_acceso(self):
        # SSH solo se recarga si la configuracion valida
        self.assertIn("sshd -t", self.paso)
        self.assertLess(self.paso.index("sshd -t"), self.paso.index("systemctl reload ssh"))
        # y se revierte si no valida
        self.assertIn("se revierte", self.paso)
        # el cortafuegos exige una regla de SSH confirmada antes de activarse
        self.assertIn("NO se activa el cortafuegos", self.paso)
        self.assertIn("grep -qE", self.paso[self.paso.index("ufw show added"):])
        # y las reglas de permiso se anaden ANTES de la politica de denegar
        self.assertLess(self.paso.index('ufw limit "${SSH_PUERTO}/tcp"'), self.paso.index("ufw default deny incoming"))
        # desactivar la contrasena de SSH es opt-in y exige una clave publica autorizada
        self.assertIn("DREAME_SSH_SOLO_CLAVES", self.paso)
        self.assertIn("authorized_keys", self.paso)
        self.assertIn("PasswordAuthentication no", self.paso)
        solo_claves = self.paso[self.paso.index('if [[ "${DREAME_SSH_SOLO_CLAVES:-0}" == "1" ]]'):]
        self.assertLess(solo_claves.index("authorized_keys"), solo_claves.index("SSH_SOLO_CLAVES=1"))

    def test_root_solo_se_prohibe_si_quien_instala_no_es_root(self):
        self.assertIn('if [[ "$(id -u)" -ne 0 ]]; then echo "PermitRootLogin no"; fi', self.paso)

    def test_el_ssh_endurecido_no_toca_el_sshd_config_del_sistema(self):
        self.assertNotIn("/etc/ssh/sshd_config ", self.paso.replace("/etc/ssh/sshd_config.d", ""))

    def test_el_kernel_no_desactiva_ip_forward_que_docker_necesita(self):
        self.assertNotIn("net.ipv4.ip_forward", self.paso)

    def test_ufw_solo_abre_el_frontend_a_redes_privadas_y_solo_si_no_esta_en_loopback(self):
        i = self.paso.index('if [[ "$FRONTEND_BIND_FW" != "127.0.0.1" ]]')
        bloque = self.paso[i:i + 400]
        for red_privada in ("192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12"):
            self.assertIn(red_privada, bloque)
        self.assertNotIn("ufw allow 3000", self.paso)

    def test_el_frontend_escucha_solo_en_loopback_si_hay_tunel_de_cloudflare(self):
        self.assertIn("hay_tunel()", self.paso)
        self.assertIn("cloudflared", self.paso)
        self.assertIn("STOCKHOGAR_FRONTEND_BIND", self.install)
        self.assertIn("DREAME_ABRIR_LAN", self.paso)
        self.assertIn('STOCKHOGAR_FRONTEND_BIND) echo "$FRONTEND_BIND_FW" ;;', self.install)

    def test_va_antes_de_construir_y_despues_de_la_optimizacion(self):
        self.assertLess(self.install.index("Optimizar el sistema"), self.install.index("Reforzar la seguridad del sistema"))
        self.assertLess(self.install.index("Reforzar la seguridad del sistema"), self.install.index('step_start "Construir imágenes"'))


if __name__ == "__main__":
    unittest.main()
