"""Regresion: un campo de texto con tipo erroneo (null, numero, lista) da 400, nunca 500."""
import uuid

import pytest

from stockhogar import create_app
from stockhogar.config import VERSION_TERMINOS  # noqa: F401  (el registro lo exige)

PW = "Clave-Segura-Test-8841"


@pytest.fixture(scope="module")
def cliente():
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    c = app.test_client()
    r = c.post("/api/auth/registrar", json={"usuario": f"t_{uuid.uuid4().hex[:8]}", "password": PW, "acepta_terminos": True})
    assert r.status_code == 201
    return c


@pytest.mark.parametrize("ruta,cuerpo", [
    ("/api/auth/perfil", {"nombre": None}),
    ("/api/auth/perfil", {"nombre": 5}),
    ("/api/auth/perfil", {"email": 5}),
    ("/api/auth/perfil", {"usuario": ["x"]}),
    ("/api/push/suscribir", {"endpoint": 5}),
    ("/api/push/suscribir", {"endpoint": "https://x", "keys": 5}),
    ("/api/push/suscribir", {"endpoint": "https://x", "keys": {"p256dh": 1, "auth": []}}),
    ("/api/push/desuscribir", {"endpoint": {"a": 1}}),
    ("/api/auth/verificar-2fa", {"codigo": 123456}),
    ("/api/log/client", {"nivel": 5}),
    ("/api/auth/tema", {"tema": 5}),
    ("/api/auth/teclado-virtual", {"teclado_virtual_activo": 5}),
    ("/api/auth/preferencias-listas", {"vista_lista_compra": 5, "agrupar_categorias": []}),
    ("/api/idiomas/cambiar", {"idioma": 5}),
    ("/api/idiomas/traducir", {"idioma": 5, "claves": []}),
    ("/api/articulos", {"nombre": "Leche", "icono": 5, "unidad": [], "categoria": 7, "sub_descripcion": {}, "codigo_barras": 1}),
])
def test_campo_no_texto_no_da_500(cliente, ruta, cuerpo):
    metodo = cliente.put if ruta.endswith("perfil") else cliente.post
    r = metodo(ruta, json=cuerpo)
    assert r.status_code < 500, (ruta, cuerpo, r.get_data(as_text=True))


def test_perfil_nombre_null_se_ignora(cliente):
    assert cliente.put("/api/auth/perfil", json={"nombre": None}).status_code == 200


@pytest.mark.parametrize("campo", ["password", "password_actual"])
def test_password_numerica_no_da_500(cliente, campo):
    assert cliente.post("/api/auth/login", json={"usuario": "x", campo: 12345}).status_code < 500
    assert cliente.post("/api/auth/cambiar-password", json={"password_actual": 5, "password_nueva": 6, "password_confirmacion": 6}).status_code < 500
