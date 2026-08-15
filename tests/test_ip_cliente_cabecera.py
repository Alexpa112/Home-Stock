"""Regresion: CF-Connecting-IP solo vale si la peticion viene del proxy.

Bug real: ip_cliente() devolvia sin mas la cabecera CF-Connecting-IP, que la
manda el cliente como cualquier otra. Con eso TODOS los limites de tasa eran
de adorno: cambiando esa cabecera en cada intento, ni el contador por IP ni el
de ip+cuenta de intentos_login llegaban nunca a su tope, asi que se podia
hacer fuerza bruta ilimitada contra cualquier contraseña (y lo mismo con el
reset de contraseña, el 2FA y la cuota diaria de OCR).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stockhogar import create_app
from stockhogar.red import ip_cliente

IP_REAL_DEL_VISITANTE = "203.0.113.7"
IP_INVENTADA = "198.51.100.99"


def _ip_vista_por_la_app(app, entorno, cabeceras=None):
    with app.test_request_context(environ_base=entorno, headers=cabeceras or {}):
        return ip_cliente()


def test_se_confia_en_la_cabecera_si_el_salto_es_el_proxy_interno():
    # Caso real de produccion: Cloudflare -> Next -> Flask, asi que a Flask le
    # llega desde una IP privada de la red de Docker.
    app = create_app()
    ip = _ip_vista_por_la_app(
        app,
        {"REMOTE_ADDR": "172.18.0.5"},
        {"CF-Connecting-IP": IP_REAL_DEL_VISITANTE},
    )
    assert ip == IP_REAL_DEL_VISITANTE


def test_se_ignora_la_cabecera_si_la_peticion_llega_de_una_ip_publica():
    # Esa peticion no ha pasado por nuestro proxy: la cabecera es simplemente
    # lo que el cliente ha querido escribir.
    app = create_app()
    ip = _ip_vista_por_la_app(
        app,
        {"REMOTE_ADDR": "203.0.113.200"},
        {"CF-Connecting-IP": IP_INVENTADA},
    )
    assert ip == "203.0.113.200", (
        "un cliente que llega directo no debe poder elegir con que IP se le "
        "cuentan los intentos: eso anula los limites de tasa"
    )


def test_una_cabecera_que_no_es_una_ip_se_descarta():
    # El valor acaba como clave del contador de tasa y en intentos_login, asi
    # que una cadena arbitraria del cliente no debe llegar hasta ahi.
    app = create_app()
    ip = _ip_vista_por_la_app(
        app,
        {"REMOTE_ADDR": "172.18.0.5"},
        {"CF-Connecting-IP": "no-soy-una-ip" + "A" * 500},
    )
    assert ip == "172.18.0.5"


def test_sin_cabecera_se_usa_la_direccion_de_la_conexion():
    app = create_app()
    ip = _ip_vista_por_la_app(app, {"REMOTE_ADDR": "172.18.0.5"})
    assert ip == "172.18.0.5"


def test_el_atacante_no_puede_repartirse_entre_muchas_ips_falsas():
    """Lo que hacia inutil el limite: mil intentos, mil IPs distintas."""
    app = create_app()
    vistas = {
        _ip_vista_por_la_app(
            app,
            {"REMOTE_ADDR": "203.0.113.200"},
            {"CF-Connecting-IP": f"10.0.0.{n}"},
        )
        for n in range(1, 50)
    }
    assert vistas == {"203.0.113.200"}, (
        "todos los intentos deben contarse contra la misma IP real"
    )
