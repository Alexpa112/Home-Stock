import pytest


@pytest.fixture(autouse=True)
def _sin_verificacion_real_de_contrasenas_filtradas(monkeypatch):
    """Evita llamadas de red reales a la API de Have I Been Pwned durante los
    tests: no son hermeticos ni deterministas, y contraseñas de fixture como
    "password123" SI estan filtradas de verdad, lo que rompe tests que no
    tienen nada que ver con esa comprobacion. Los tests que quieran cubrir el
    caso "contraseña filtrada" deben mockear
    stockhogar.rutas.auth.es_password_filtrada explicitamente."""
    monkeypatch.setattr("stockhogar.rutas.auth.es_password_filtrada", lambda password: False)
