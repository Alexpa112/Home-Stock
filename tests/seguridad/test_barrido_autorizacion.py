"""Barrido sistematico de autorizacion multi-hogar / multi-usuario.

Recorre TODAS las rutas /api/* (app.url_map) clasificadas en CLASIFICACION y
comprueba, con dos hogares distintos y BD temporal aislada:

  (a) sin sesion -> 401 (y con una cookie de un usuario ya inexistente -> 401);
  (b) un usuario ajeno sobre recursos de otro hogar -> 403/404 (nunca 200) y
      la BD no cambia ni se filtran datos del otro hogar;
  (c) un rol sin nivel suficiente (ver/comprar/editar) no puede mutar;
  (d) CSRF obligatorio en toda ruta mutadora salvo las exentas a proposito.

test_cobertura_clasificacion falla si aparece una ruta /api nueva sin
clasificar (o queda una entrada obsoleta): anadirla a CLASIFICACION o a las
tablas RUTAS_* decide explicitamente como se protege.

Cada test trabaja sobre una COPIA de una BD plantilla sembrada una sola vez;
nunca se toca data/stock.db.
"""
import hashlib
import io
import re
import shutil
import sqlite3

import pytest
from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar import config as modulo_db
from stockhogar.db import ahora
from stockhogar.nucleo.autorizacion import NIVELES
from stockhogar.rutas.cuenta.blueprint import RUTAS_PUBLICAS

MARCA = "MARCA-HOGAR-A-7f3k"

# Tablas con efectos laterales legitimos (auditoria, contadores de cuota):
# no entran en la comparacion "la BD no ha cambiado".
TABLAS_VOLATILES = {"eventos_seguridad", "uso_ocr_diario", "uso_recibos_diario"}

# --- Clasificacion de las rutas que NO reciben recursos de un hogar ---------

# Accesibles sin sesion (ver RUTAS_PUBLICAS en rutas/auth.py).
PUBLICAS = {
    ("/api/auth/estado", "GET"), ("/api/auth/login", "POST"), ("/api/auth/registrar", "POST"),
    ("/api/auth/verificar-codigo", "POST"), ("/api/auth/reenviar-codigo", "POST"),
    ("/api/auth/verificar-email", "POST"), ("/api/cache-version", "GET"),
    ("/api/auth/solicitar-reset-password", "POST"),
    ("/api/auth/restablecer-password", "POST"), ("/api/csrf-token", "GET"),
    ("/api/log/client", "POST"), ("/api/mantenimiento/estado", "GET"),
    ("/api/idiomas/todos/{idioma}", "GET"), ("/api/idiomas/obtener", "GET"),
    ("/api/legal/config", "GET"),
}

# Exigen sesion pero solo operan sobre el propio usuario / sin ids de recurso.
USUARIO = {
    ("/api/auth/aceptar-terminos", "POST"), ("/api/auth/cambiar-password", "POST"),
    ("/api/auth/cerrar-otras-sesiones", "POST"), ("/api/auth/doble-factor", "POST"),
    ("/api/auth/enviar-verificacion-email", "POST"), ("/api/auth/exportar-mis-datos", "GET"),
    ("/api/auth/logout", "POST"), ("/api/auth/mis-eventos-seguridad", "GET"),
    ("/api/auth/perfil", "PUT"), ("/api/auth/preferencia-ocr", "POST"),
    ("/api/auth/preferencias-listas", "POST"), ("/api/auth/teclado-virtual", "POST"),
    ("/api/auth/tema", "POST"), ("/api/idiomas/cambiar", "POST"),
    ("/api/idiomas/disponibles", "GET"), ("/api/idiomas/traducir", "POST"),
    ("/api/formularios/crear-lista", "GET"),
    ("/api/hogares", "GET"), ("/api/hogares", "POST"), ("/api/listas", "GET"), ("/api/listas", "POST"),
    ("/api/hogares/invitaciones-pendientes", "GET"),
    ("/api/push/desuscribir", "POST"), ("/api/push/suscribir", "POST"),
    ("/api/push/vapid-clave-publica", "GET"), ("/api/usuarios", "GET"),
    ("/api/tickets/analizar", "POST"), ("/api/tickets/trabajos", "POST"),
    ("/api/ocr/validar-instalacion", "GET"),
}

# Catalogos globales compartidos entre TODOS los hogares (sin propietario).
GLOBALES = {
    ("/api/categorias", "GET"), ("/api/categorias", "POST"), ("/api/categorias/{categoria_id}", "DELETE"),
    ("/api/categorias-gasto", "GET"), ("/api/categorias-gasto", "POST"),
    ("/api/categorias-gasto/{categoria_id}", "DELETE"),
    ("/api/historial", "GET"), ("/api/historial/codigo/{codigo_barras}", "GET"),
}

# --- Rutas que operan sobre recursos de un hogar ----------------------------
# t: "hogar_ruta" (hogar_id en la URL), "activo" (hogar activo de la sesion) o
# "recurso" (el recurso se resuelve por su propietario / destinatario).
# nivel: nivel minimo para la operacion. id: la URL lleva el id de un recurso.
# json/files: cuerpo valido para el usuario autorizado (control positivo).

RUTAS_HOGAR = [
    {"m": "GET", "r": "/api/hogares/{hogar_id}", "t": "hogar_ruta", "nivel": "ver"},
    {"m": "PATCH", "r": "/api/hogares/{hogar_id}", "t": "hogar_ruta", "nivel": "propietario", "json": {"nombre": "Renombrado"}},
    {"m": "PUT", "r": "/api/hogares/{hogar_id}", "t": "hogar_ruta", "nivel": "propietario", "json": {"nombre": "Renombrado"}},
    {"m": "DELETE", "r": "/api/hogares/{hogar_id}", "t": "hogar_ruta", "nivel": "propietario"},
    {"m": "POST", "r": "/api/hogares/{hogar_id}/compartir", "t": "hogar_ruta", "nivel": "propietario", "json": {"nombre_usuario": "{u_E}"}},
    {"m": "POST", "r": "/api/hogares/{hogar_id}/enlace-compartible", "t": "hogar_ruta", "nivel": "propietario", "json": {}},
    {"m": "GET", "r": "/api/hogares/{hogar_id}/miembros", "t": "hogar_ruta", "nivel": "propietario"},
    {"m": "GET", "r": "/api/hogares/{hogar_id}/miembros-basico", "t": "hogar_ruta", "nivel": "ver"},
    {"m": "PATCH", "r": "/api/hogares/{hogar_id}/permisos/{usuario_id}", "t": "hogar_ruta", "nivel": "propietario", "json": {"nivel": "ver"}, "ids": {"usuario_id": "V"}},
    {"m": "DELETE", "r": "/api/hogares/{hogar_id}/permisos/{usuario_id}", "t": "hogar_ruta", "nivel": "propietario", "ids": {"usuario_id": "V"}},
    {"m": "POST", "r": "/api/hogares/{hogar_id}/salir", "t": "hogar_ruta", "nivel": "ver", "ctrl_user": "V"},
    {"m": "POST", "r": "/api/hogares/{hogar_id}/seleccionar", "t": "hogar_ruta", "nivel": "ver", "json": {}},
    # Alias legado /api/listas/*: mismas funciones, se barren igual.
    {"m": "GET", "r": "/api/listas/{hogar_id}", "t": "hogar_ruta", "nivel": "ver"},
    {"m": "PATCH", "r": "/api/listas/{hogar_id}", "t": "hogar_ruta", "nivel": "propietario", "json": {"nombre": "Renombrado"}},
    {"m": "PUT", "r": "/api/listas/{hogar_id}", "t": "hogar_ruta", "nivel": "propietario", "json": {"nombre": "Renombrado"}},
    {"m": "DELETE", "r": "/api/listas/{hogar_id}", "t": "hogar_ruta", "nivel": "propietario"},
    {"m": "GET", "r": "/api/listas/{hogar_id}/miembros-basico", "t": "hogar_ruta", "nivel": "ver"},
    {"m": "POST", "r": "/api/listas/{hogar_id}/salir", "t": "hogar_ruta", "nivel": "ver", "ctrl_user": "V"},
    {"m": "POST", "r": "/api/listas/{hogar_id}/seleccionar", "t": "hogar_ruta", "nivel": "ver", "json": {}},
]

CUERPO_GASTO = {
    "descripcion": "Gasto nuevo", "importe_total": 10, "usuario_pagador_id": "{id_A}",
    "participantes": [{"usuario_id": "{id_A}", "importe": 10}],
}

RUTAS_ACTIVO = [
    {"m": "GET", "r": "/api/hogares/version", "nivel": "ver"},
    {"m": "GET", "r": "/api/listas/version", "nivel": "ver"},
    {"m": "GET", "r": "/api/articulos", "nivel": "ver"},
    {"m": "POST", "r": "/api/articulos", "nivel": "editar", "json": {"nombre": "Zeta", "cantidad": 1}},
    {"m": "GET", "r": "/api/articulos/exportar", "nivel": "ver"},
    {"m": "POST", "r": "/api/articulos/importar", "nivel": "editar", "files": "csv"},
    {"m": "GET", "r": "/api/articulos/personalizados", "nivel": "ver"},
    {"m": "PATCH", "r": "/api/articulos/{item_id}", "nivel": "editar", "id": True, "json": {"nombre": "Renombrado"}},
    {"m": "DELETE", "r": "/api/articulos/{item_id}", "nivel": "editar", "id": True},
    {"m": "GET", "r": "/api/historial/catalogo", "nivel": "ver"},
    {"m": "GET", "r": "/api/gastos", "nivel": "ver"},
    {"m": "POST", "r": "/api/gastos", "nivel": "editar", "json": CUERPO_GASTO},
    {"m": "GET", "r": "/api/gastos/exportar", "nivel": "ver"},
    {"m": "GET", "r": "/api/gastos/resumen-mes", "nivel": "ver"},
    {"m": "GET", "r": "/api/gastos/saldo", "nivel": "ver"},
    {"m": "GET", "r": "/api/gastos/simplificar", "nivel": "ver"},
    {"m": "PUT", "r": "/api/gastos/{gasto_id}", "nivel": "editar", "id": True, "json": {"descripcion": "Nueva"}},
    {"m": "PATCH", "r": "/api/gastos/{gasto_id}", "nivel": "editar", "id": True, "json": {"descripcion": "Nueva"}},
    {"m": "DELETE", "r": "/api/gastos/{gasto_id}", "nivel": "editar", "id": True},
    {"m": "POST", "r": "/api/gastos/{gasto_id}/recibo", "nivel": "editar", "id": True, "files": "png"},
    {"m": "GET", "r": "/api/gastos/{gasto_id}/recibo", "nivel": "ver", "id": True},
    {"m": "DELETE", "r": "/api/gastos/{gasto_id}/recibo", "nivel": "editar", "id": True},
    {"m": "GET", "r": "/api/gastos/liquidaciones", "nivel": "ver"},
    {"m": "POST", "r": "/api/gastos/liquidaciones", "nivel": "editar", "json": {"usuario_origen_id": "{id_V}", "usuario_destino_id": "{id_A}", "importe": 5}},
    {"m": "DELETE", "r": "/api/gastos/liquidaciones/{liquidacion_id}", "nivel": "editar", "id": True},
    {"m": "GET", "r": "/api/gastos/recurrentes", "nivel": "ver"},
    {"m": "POST", "r": "/api/gastos/recurrentes", "nivel": "editar", "json": {
        "descripcion": "Recurrente nuevo", "importe_total": 10, "usuario_pagador_id": "{id_A}",
        "participantes": [{"usuario_id": "{id_A}", "importe": 10}], "frecuencia": "mensual",
        "fecha_inicio": "2099-01-01"}},
    {"m": "PATCH", "r": "/api/gastos/recurrentes/{recurrente_id}", "nivel": "editar", "id": True, "json": {"activo": False}},
    {"m": "DELETE", "r": "/api/gastos/recurrentes/{recurrente_id}", "nivel": "editar", "id": True},
    {"m": "GET", "r": "/api/productos", "nivel": "ver"},
    {"m": "POST", "r": "/api/productos", "nivel": "editar", "json": {"nombre": "Producto nuevo", "cantidad": 1}},
    {"m": "GET", "r": "/api/productos/exportar", "nivel": "ver"},
    {"m": "POST", "r": "/api/productos/importar", "nivel": "editar", "files": "csv"},
    {"m": "PATCH", "r": "/api/productos/{producto_id}", "nivel": "editar", "id": True, "json": {"nombre": "Renombrado"}},
    {"m": "DELETE", "r": "/api/productos/{producto_id}", "nivel": "editar", "id": True},
    {"m": "GET", "r": "/api/productos/{producto_id}/precios", "nivel": "ver", "id": True},
    {"m": "GET", "r": "/api/productos/{producto_id}/traducciones/{idioma}", "nivel": "ver", "id": True},
    {"m": "GET", "r": "/api/recetas", "nivel": "ver"},
    {"m": "POST", "r": "/api/recetas", "nivel": "editar", "json": {"nombre": "Receta nueva", "ingredientes": [{"nombre": "Sal", "cantidad": 1}]}},
    {"m": "PATCH", "r": "/api/recetas/{receta_id}", "nivel": "editar", "id": True, "json": {"nombre": "Receta renombrada"}},
    {"m": "DELETE", "r": "/api/recetas/{receta_id}", "nivel": "editar", "id": True},
    {"m": "POST", "r": "/api/recetas/{receta_id}/anadir-a-lista", "nivel": "editar", "id": True, "json": {}},
    # Devuelve [] (200) para un producto que no es del hogar activo: no filtra
    # nada, igual que un producto inexistente.
    {"m": "GET", "r": "/api/consumo/producto/{producto_id}", "nivel": "ver", "id": True, "ok_vacio": True},
    {"m": "GET", "r": "/api/consumo/resumen", "nivel": "ver"},
    {"m": "POST", "r": "/api/tickets/confirmar", "nivel": "editar", "json": {"items": [{"nombre": "Zumo", "cantidad": 1}]}},
]
for _e in RUTAS_ACTIVO:
    _e["t"] = "activo"

RUTAS_RECURSO = [
    {"m": "GET", "r": "/api/articulos/personalizados/{articulo_id}/traducciones/{idioma}", "t": "recurso", "nivel": "ver", "roles": True},
    {"m": "PATCH", "r": "/api/articulos/personalizados/{articulo_id}", "t": "recurso", "nivel": "editar", "roles": True, "json": {"nombre": "Cambiado"}},
    {"m": "DELETE", "r": "/api/articulos/personalizados/{articulo_id}", "t": "recurso", "nivel": "editar", "roles": True,
     "antes_ctrl": ("DELETE", "/api/articulos/{item_id}")},
    {"m": "POST", "r": "/api/hogares/aceptar-invitacion/{codigo}", "t": "recurso", "nivel": "ver", "ctrl_user": "X", "json": {}},
    {"m": "DELETE", "r": "/api/hogares/invitaciones-pendientes/{codigo}", "t": "recurso", "nivel": "ver", "ctrl_user": "X"},
    {"m": "DELETE", "r": "/api/usuarios/{usuario_id}", "t": "recurso", "nivel": "ver", "ids": {"usuario_id": "A"}, "json": {"password_actual": "password123"}},
    # Con producto_id/articulo_id de otro hogar (cuerpo) debe ser 403.
    # Trabajo de analisis de ticket de A (su resultado lleva el marcador): solo lo ve su creador.
    {"m": "GET", "r": "/api/tickets/trabajos/{trabajo_id}", "t": "recurso", "nivel": "ver"},
    {"m": "POST", "r": "/api/productos/traducir", "t": "recurso", "nivel": "ver", "json": {"nombre": "Leche", "producto_id": "{producto_id}"}},
]

RUTAS_RECURSOS_TODAS = RUTAS_HOGAR + RUTAS_ACTIVO + RUTAS_RECURSO


def _normalizar(regla):
    return re.sub(r"<(?:\w+:)?(\w+)>", r"{\1}", regla)


def _clave(e):
    return (e["r"], e["m"])


CLASIFICACION = {}
for _conjunto, _nombre in ((PUBLICAS, "publica"), (USUARIO, "usuario"), (GLOBALES, "global")):
    for _k in _conjunto:
        assert _k not in CLASIFICACION, f"ruta clasificada dos veces: {_k}"
        CLASIFICACION[_k] = _nombre
for _e in RUTAS_RECURSOS_TODAS:
    assert _clave(_e) not in CLASIFICACION, f"ruta clasificada dos veces: {_clave(_e)}"
    CLASIFICACION[_clave(_e)] = _e["t"]


def _rutas_api_reales(app):
    reales = {}
    for regla in app.url_map.iter_rules():
        if not regla.rule.startswith("/api"):
            continue
        for metodo in regla.methods - {"HEAD", "OPTIONS"}:
            reales[(_normalizar(regla.rule), metodo)] = regla.endpoint
    return reales


# --- Entorno aislado ---------------------------------------------------------


class Ctx:
    """Entorno de un test: app + copia de la BD plantilla + ids sembrados."""

    def __init__(self, app, ruta_db, usuarios, hogares, ids):
        self.app = app
        self.ruta_db = ruta_db
        self.u = usuarios  # "A" -> {"id", "nombre"}
        self.h = hogares  # "A"/"B" -> id
        self.ids = ids

    def cliente(self, usuario=None, hogar_activo=None):
        c = self.app.test_client()
        if usuario:
            with c.session_transaction() as sess:
                sess["usuario"] = self.u[usuario]["nombre"]
                sess["usuario_id"] = self.u[usuario]["id"]
                sess["session_version"] = 0
                if hogar_activo is not None:
                    sess["hogar_actual_id"] = hogar_activo
        return c

    def hash_bd(self):
        con = sqlite3.connect(self.ruta_db)
        try:
            tablas = [
                f[0] for f in con.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                ).fetchall() if f[0] not in TABLAS_VOLATILES
            ]
            resumen = hashlib.sha256()
            for tabla in tablas:
                try:
                    filas = con.execute(f'SELECT * FROM "{tabla}" ORDER BY rowid').fetchall()  # nosec B608
                except sqlite3.OperationalError:
                    filas = con.execute(f'SELECT * FROM "{tabla}"').fetchall()  # nosec B608
                resumen.update(repr((tabla, filas)).encode("utf-8", "replace"))
            return resumen.hexdigest()
        finally:
            con.close()

    def _sustituir(self, valor, extra=None):
        """Sustituye {marcadores} por ids/nombres sembrados en str/dict/list."""
        datos = {**self.ids, **{f"id_{k}": v["id"] for k, v in self.u.items()},
                 **{f"u_{k}": v["nombre"] for k, v in self.u.items()}}
        if isinstance(valor, str):
            if re.fullmatch(r"\{\w+\}", valor):
                return datos[valor[1:-1]]
            return valor.format(**datos)
        if isinstance(valor, dict):
            return {k: self._sustituir(v) for k, v in valor.items()}
        if isinstance(valor, list):
            return [self._sustituir(v) for v in valor]
        return valor

    def url(self, e):
        ids = dict(self.ids)
        for nombre, quien in e.get("ids", {}).items():
            ids[nombre] = self.u[quien]["id"]
        return e["r"].format(**ids)

    def enviar(self, cliente, e):
        argumentos = {"method": e["m"]}
        if e.get("files"):
            argumentos["data"] = {FICHEROS[e["files"]][0]: (FICHEROS[e["files"]][1](), FICHEROS[e["files"]][2])}
            argumentos["content_type"] = "multipart/form-data"
        elif e["m"] in ("POST", "PUT", "PATCH") or "json" in e:
            argumentos["json"] = self._sustituir(e.get("json", {}))
        return cliente.open(self.url(e), **argumentos)


def _png():
    from PIL import Image
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), (200, 30, 30)).save(buffer, "PNG")
    return buffer.getvalue()


def _csv():
    return b"nombre;categoria;unidad;cantidad;stock_minimo;dias_aviso\nLeche importada;Otros;ud;1;1;30\n"


FICHEROS = {
    "csv": ("fichero", lambda: io.BytesIO(_csv()), "datos.csv"),
    "png": ("foto", lambda: io.BytesIO(_png()), "recibo.png"),
}


@pytest.fixture(autouse=True)
def _sin_traduccion_real(monkeypatch):
    """La traduccion automatica (Argos) es lenta y no es lo que se barre."""
    monkeypatch.setattr(
        "stockhogar.servicios.traduccion.traductor_auto.TraductorAutomatico.traducir_a_todos_idiomas",
        staticmethod(lambda texto, *a, **k: {}),
    )
    # Sin hilos de traduccion en segundo plano que sobrevivan al test (cargan Argos/torch).
    for modulo in ("stockhogar.rutas.compra.lista", "stockhogar.rutas.inventario.productos"):
        monkeypatch.setattr(modulo + ".encolar", lambda *a, **k: True)


def _crear_usuario(con, nombre):
    cur = con.execute(
        "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
        (nombre, generate_password_hash("password123"), ahora()),
    )
    return cur.lastrowid


def _crear_hogar(con, nombre, propietario_id):
    cur = con.execute(
        "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
        "VALUES (?, ?, 1, ?, ?)",
        (nombre, propietario_id, ahora(), ahora()),
    )
    return cur.lastrowid


@pytest.fixture(scope="module")
def plantilla(tmp_path_factory):
    """BD plantilla: dos hogares (A con miembros ver/comprar/editar y B), con
    datos de A sembrados a traves de la propia API."""
    ruta = tmp_path_factory.mktemp("barrido") / "plantilla.db"
    mp = pytest.MonkeyPatch()
    mp.setattr(modulo_db, "DB_PATH", ruta)
    mp.setattr("stockhogar.rutas.cuenta.credenciales.es_password_filtrada", lambda password: False)
    mp.setattr(
        "stockhogar.servicios.traduccion.traductor_auto.TraductorAutomatico.traducir_a_todos_idiomas",
        staticmethod(lambda texto, *a, **k: {}),
    )
    for modulo in ("stockhogar.rutas.compra.lista", "stockhogar.rutas.inventario.productos"):
        mp.setattr(modulo + ".encolar", lambda *a, **k: True)
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    con = sqlite3.connect(ruta)
    con.execute("PRAGMA foreign_keys = ON")
    usuarios = {}
    for clave in ("A", "B", "V", "C", "E", "X"):
        nombre = f"barrido_{clave.lower()}_7f3k"
        usuarios[clave] = {"id": _crear_usuario(con, nombre), "nombre": nombre}
    hogares = {"A": _crear_hogar(con, f"Hogar {MARCA}", usuarios["A"]["id"]),
               "B": _crear_hogar(con, "Hogar B", usuarios["B"]["id"])}
    for clave, nivel in (("V", "ver"), ("C", "comprar"), ("E", "editar")):
        con.execute(
            "INSERT INTO permisos_hogar (hogar_id, usuario_id, nivel, fecha_otorgado) VALUES (?, ?, ?, ?)",
            (hogares["A"], usuarios[clave]["id"], nivel, ahora()),
        )
    con.commit()
    con.close()

    ctx = Ctx(app, ruta, usuarios, hogares, {
        "hogar_id": hogares["A"], "idioma": "en", "codigo_barras": "8410000000000", "token": "x",
        "usuario_id": usuarios["V"]["id"], "categoria_id": 1,
    })
    a = ctx.cliente("A", hogares["A"])

    def sembrar(metodo, ruta_api, **kw):
        resp = a.open(ruta_api, method=metodo, **kw)
        assert resp.status_code in (200, 201, 204), (ruta_api, resp.status_code, resp.get_data(as_text=True))
        return resp

    ctx.ids["producto_id"] = sembrar("POST", "/api/productos", json={"nombre": f"{MARCA} Producto", "cantidad": 3, "stock_minimo": 1}).get_json()["id"]
    sembrar("PATCH", f"/api/productos/{ctx.ids['producto_id']}", json={"delta": -1})  # genera un movimiento de stock
    sembrar("POST", "/api/articulos", json={"nombre": f"{MARCA} Articulo", "cantidad": 2})
    articulos = sembrar("GET", "/api/articulos").get_json()["pendientes"]
    ctx.ids["item_id"] = next(x["id"] for x in articulos if MARCA in x["nombre"])
    personalizados = sembrar("GET", "/api/articulos/personalizados").get_json()
    ctx.ids["articulo_id"] = next(x["id"] for x in personalizados if MARCA in x["nombre"])
    cuerpo_gasto = {
        "descripcion": f"{MARCA} Gasto", "importe_total": 20, "usuario_pagador_id": usuarios["A"]["id"],
        "participantes": [{"usuario_id": usuarios["A"]["id"], "importe": 10}, {"usuario_id": usuarios["V"]["id"], "importe": 10}],
    }
    ctx.ids["gasto_id"] = sembrar("POST", "/api/gastos", json=cuerpo_gasto).get_json()["id"]
    sembrar("POST", f"/api/gastos/{ctx.ids['gasto_id']}/recibo", data={"foto": (io.BytesIO(_png()), "recibo.png")}, content_type="multipart/form-data")
    sembrar("POST", "/api/gastos/liquidaciones", json={"usuario_origen_id": usuarios["V"]["id"], "usuario_destino_id": usuarios["A"]["id"], "importe": 3, "nota": MARCA})
    ctx.ids["liquidacion_id"] = sembrar("GET", "/api/gastos/liquidaciones").get_json()[0]["id"]
    ctx.ids["recurrente_id"] = sembrar("POST", "/api/gastos/recurrentes", json={
        "descripcion": f"{MARCA} Recurrente", "importe_total": 10, "usuario_pagador_id": usuarios["A"]["id"],
        "participantes": [{"usuario_id": usuarios["A"]["id"], "importe": 10}], "frecuencia": "mensual",
        "fecha_inicio": "2099-01-01"}).get_json()["id"]
    ctx.ids["receta_id"] = sembrar("POST", "/api/recetas", json={"nombre": f"{MARCA} Receta", "ingredientes": [{"nombre": "Sal", "cantidad": 1}]}).get_json()["id"]
    # Invitacion dirigida a X (solo X puede aceptarla/rechazarla).
    sembrar("POST", f"/api/hogares/{hogares['A']}/compartir", json={"nombre_usuario": usuarios["X"]["nombre"], "nivel": "ver"})

    con = sqlite3.connect(ruta)
    ctx.ids["trabajo_id"] = "trabajo-barrido-a"
    con.execute(
        "INSERT INTO trabajos_ticket (id, usuario_id, estado, resultado, creado, actualizado) VALUES (?, ?, 'listo', ?, 4102444800, 4102444800)",
        (ctx.ids["trabajo_id"], usuarios["A"]["id"], '{"items": [{"nombre": "%s"}]}' % MARCA),
    )
    con.commit()
    ctx.ids["codigo"] = con.execute(
        "SELECT codigo_invitacion FROM invitaciones_hogar WHERE usuario_destino_id = ?", (usuarios["X"]["id"],)
    ).fetchone()[0]
    con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    con.close()

    yield ctx
    mp.undo()


@pytest.fixture
def ctx(plantilla, tmp_path, monkeypatch):
    copia = tmp_path / "stock.db"
    shutil.copy(plantilla.ruta_db, copia)
    monkeypatch.setattr(modulo_db, "DB_PATH", copia)
    return Ctx(plantilla.app, copia, plantilla.u, plantilla.h, dict(plantilla.ids))


def _id_test(e):
    return f"{e['m']} {e['r']}"


# --- Cobertura ---------------------------------------------------------------


def test_cobertura_clasificacion(plantilla):
    """Cada ruta /api/* debe estar clasificada: si falla por una ruta nueva,
    decidir si es publica, de usuario, global o de recurso de hogar y
    anadirla a la tabla correspondiente (con su cuerpo de prueba)."""
    reales = _rutas_api_reales(plantilla.app)
    sin_clasificar = sorted(set(reales) - set(CLASIFICACION))
    obsoletas = sorted(set(CLASIFICACION) - set(reales))
    assert not sin_clasificar, f"Rutas /api sin clasificar en el barrido de autorizacion: {sin_clasificar}"
    assert not obsoletas, f"Entradas del barrido que ya no existen como ruta: {obsoletas}"


def test_publicas_coinciden_con_rutas_publicas(plantilla):
    """Las rutas clasificadas como publicas son exactamente las de
    RUTAS_PUBLICAS: una ruta nueva sin sesion obligatoria no pasa inadvertida."""
    reales = _rutas_api_reales(plantilla.app)
    publicas_reales = {k for k, endpoint in reales.items() if endpoint in RUTAS_PUBLICAS}
    assert publicas_reales == PUBLICAS


# --- (a) Sin sesion ------------------------------------------------------------


def _rutas_con_sesion():
    return sorted(k for k, v in CLASIFICACION.items() if v != "publica")


@pytest.mark.parametrize("clave", _rutas_con_sesion(), ids=lambda k: f"{k[1]} {k[0]}")
def test_sin_sesion_401(ctx, clave):
    e = {"m": clave[1], "r": clave[0]}
    antes = ctx.hash_bd()
    resp = ctx.enviar(ctx.cliente(), e)
    assert resp.status_code == 401, resp.get_data(as_text=True)
    assert ctx.hash_bd() == antes


@pytest.mark.parametrize("clave", _rutas_con_sesion(), ids=lambda k: f"{k[1]} {k[0]}")
def test_cookie_de_usuario_inexistente_401(ctx, clave):
    """Una cookie firmada de una cuenta ya borrada no debe dar acceso a nada
    (todas las rutas deben llevar @requerir_sesion, no solo el guardian global)."""
    c = ctx.app.test_client()
    with c.session_transaction() as sess:
        sess["usuario"] = "fantasma"
        sess["usuario_id"] = 999999
        sess["session_version"] = 0
    e = {"m": clave[1], "r": clave[0]}
    resp = ctx.enviar(c, e)
    assert resp.status_code == 401, resp.get_data(as_text=True)


# --- (b) y (c) Usuario ajeno / rol sin permiso --------------------------------


def _escenarios_denegacion(ctx, e):
    """Genera (nombre, cliente, codigos_permitidos) para cada escenario donde
    la peticion NO debe prosperar."""
    hA, hB = ctx.h["A"], ctx.h["B"]
    nivel = NIVELES[e["nivel"]]
    # Rol insuficiente: miembro del hogar A con nivel menor al exigido.
    for rol, usuario in (("ver", "V"), ("comprar", "C"), ("editar", "E")):
        if e["t"] in ("hogar_ruta", "activo") or e.get("roles"):
            if NIVELES[rol] < nivel:
                yield f"rol_{rol}", ctx.cliente(usuario, hA), {403}

    if e["t"] == "hogar_ruta":
        yield "ajeno", ctx.cliente("B", hB), {403, 404}
    elif e["t"] == "activo":
        if e.get("id"):
            yield "ajeno_hogar_propio_activo", ctx.cliente("B", hB), {403, 404}
        # Sesion de B apuntando a un hogar de A sin permiso (p.ej. acceso
        # revocado con la cookie aun viva): lo que no sea denegar, vacio.
        yield "ajeno_hogar_ajeno_activo", ctx.cliente("B", hA), {400, 403, 404}
    else:
        yield "ajeno", ctx.cliente("B", hB), {403, 404}


@pytest.mark.parametrize("e", [x for x in RUTAS_RECURSOS_TODAS], ids=_id_test)
def test_ajeno_y_roles_sin_permiso(ctx, e):
    for nombre, cliente, permitidos in _escenarios_denegacion(ctx, e):
        antes = ctx.hash_bd()
        resp = ctx.enviar(cliente, e)
        cuerpo = resp.get_data(as_text=True)
        if resp.status_code == 200 and e["m"] == "GET" and (not e.get("id") or e.get("ok_vacio")):
            # Lectura sin id que devuelve solo los datos propios del usuario.
            assert MARCA not in cuerpo, f"[{nombre}] filtra datos del hogar A"
            if e.get("ok_vacio"):
                assert resp.get_json() in ([], {}), f"[{nombre}] {cuerpo}"
        else:
            assert resp.status_code in permitidos, f"[{nombre}] status {resp.status_code}: {cuerpo}"
        assert MARCA not in cuerpo, f"[{nombre}] filtra datos del hogar A"
        assert ctx.hash_bd() == antes, f"[{nombre}] la peticion modifico la BD"


# --- Control positivo: la ruta funciona para quien SI tiene permiso -----------


@pytest.mark.parametrize("e", RUTAS_RECURSOS_TODAS, ids=_id_test)
def test_control_positivo_usuario_autorizado(ctx, e):
    """Sin este control, un 403/404 por URL o cuerpo mal formado haria pasar
    el barrido en falso: aqui el usuario con permiso suficiente consigue 2xx."""
    quien = e.get("ctrl_user", "A")
    cliente = ctx.cliente(quien, ctx.h["A"])
    if e.get("antes_ctrl"):
        metodo, ruta = e["antes_ctrl"]
        assert ctx.cliente("A", ctx.h["A"]).open(ruta.format(**ctx.ids), method=metodo).status_code in (200, 204)
    resp = ctx.enviar(cliente, e)
    assert resp.status_code in (200, 201, 204), f"{resp.status_code}: {resp.get_data(as_text=True)}"


# --- Casos especificos (regresion) --------------------------------------------


def test_comprar_marca_comprado_pero_no_edita(ctx):
    c = ctx.cliente("C", ctx.h["A"])
    item = ctx.ids["item_id"]
    assert c.patch(f"/api/articulos/{item}", json={"activo": False}).status_code == 200
    antes = ctx.hash_bd()
    assert c.patch(f"/api/articulos/{item}", json={"nombre": "Hackeado"}).status_code == 403
    assert c.patch(f"/api/articulos/{item}", json={"cantidad": 99}).status_code == 403
    assert c.delete(f"/api/articulos/{item}").status_code == 403
    assert ctx.hash_bd() == antes
    pid = ctx.ids["producto_id"]
    assert c.patch(f"/api/productos/{pid}", json={"delta": 1}).status_code == 200
    assert c.patch(f"/api/productos/{pid}", json={"nombre": "Hackeado"}).status_code == 403


def test_no_se_puede_escalar_nivel_al_compartir_ni_mover_propietario(ctx):
    """El propietario solo puede conceder ver/comprar/editar: nunca
    'propietario' ni un nivel arbitrario."""
    c = ctx.cliente("A", ctx.h["A"])
    antes = ctx.hash_bd()
    assert c.post(f"/api/hogares/{ctx.h['A']}/compartir", json={"nombre_usuario": ctx.u["E"]["nombre"], "nivel": "propietario"}).status_code == 400
    assert c.patch(f"/api/hogares/{ctx.h['A']}/permisos/{ctx.u['V']['id']}", json={"nivel": "propietario"}).status_code == 400
    assert ctx.hash_bd() == antes


def test_mass_assignment_hogar_no_cambia_propietario(ctx):
    c = ctx.cliente("A", ctx.h["A"])
    resp = c.patch(f"/api/hogares/{ctx.h['A']}", json={
        "nombre": "Ok", "usuario_propietario_id": ctx.u["B"]["id"], "id": 9999, "hogar_id": ctx.h["B"]})
    assert resp.status_code == 200
    con = sqlite3.connect(ctx.ruta_db)
    fila = con.execute("SELECT usuario_propietario_id FROM hogares WHERE id = ?", (ctx.h["A"],)).fetchone()
    con.close()
    assert fila[0] == ctx.u["A"]["id"]


def test_mass_assignment_articulo_y_gasto_no_mueven_de_hogar(ctx):
    c = ctx.cliente("A", ctx.h["A"])
    assert c.patch(f"/api/articulos/{ctx.ids['item_id']}", json={"nombre": "Ok2", "hogar_id": ctx.h["B"]}).status_code == 200
    assert c.patch(f"/api/gastos/{ctx.ids['gasto_id']}", json={"descripcion": "Ok2", "hogar_id": ctx.h["B"]}).status_code == 200
    con = sqlite3.connect(ctx.ruta_db)
    assert con.execute("SELECT hogar_id FROM articulos_compra WHERE id = ?", (ctx.ids["item_id"],)).fetchone()[0] == ctx.h["A"]
    assert con.execute("SELECT hogar_id FROM gastos WHERE id = ?", (ctx.ids["gasto_id"],)).fetchone()[0] == ctx.h["A"]
    con.close()


def test_perfil_no_acepta_rol_ni_session_version(ctx):
    c = ctx.cliente("B", ctx.h["B"])
    con = sqlite3.connect(ctx.ruta_db)
    antes = con.execute("SELECT session_version FROM usuarios WHERE id = ?", (ctx.u["B"]["id"],)).fetchone()[0]
    con.close()
    resp = c.put("/api/auth/perfil", json={"nombre": "Nombre", "session_version": 99, "rol": "admin", "id": ctx.u["A"]["id"]})
    assert resp.status_code == 200
    con = sqlite3.connect(ctx.ruta_db)
    assert con.execute("SELECT session_version FROM usuarios WHERE id = ?", (ctx.u["B"]["id"],)).fetchone()[0] == antes
    assert con.execute("SELECT nombre FROM usuarios WHERE id = ?", (ctx.u["A"]["id"],)).fetchone()[0] != "Nombre"
    con.close()


def test_listado_de_usuarios_solo_con_quien_se_comparte(ctx):
    resp = ctx.cliente("B", ctx.h["B"]).get("/api/usuarios")
    nombres = {u["nombre_usuario"] for u in resp.get_json()}
    assert nombres == {ctx.u["B"]["nombre"]}


def test_confirmar_ticket_no_toca_stock_de_otro_hogar(ctx):
    """producto_id de un producto de A enviado por B: no cambia el stock de A
    ni deja un historial de precios de B colgando de ese producto."""
    antes = ctx.hash_bd()
    c = ctx.cliente("B", ctx.h["B"])
    resp = c.post("/api/tickets/confirmar", json={"items": [
        {"nombre": "Zumo", "cantidad": 5, "producto_id": ctx.ids["producto_id"], "precio_unitario": 2.5}]})
    assert resp.status_code == 200
    con = sqlite3.connect(ctx.ruta_db)
    stock_a = con.execute(
        "SELECT cantidad FROM stock_hogar WHERE hogar_id = ? AND producto_id = ?", (ctx.h["A"], ctx.ids["producto_id"])
    ).fetchone()[0]
    ajeno_en_b = con.execute(
        "SELECT COUNT(*) FROM stock_hogar WHERE hogar_id = ? AND producto_id = ?", (ctx.h["B"], ctx.ids["producto_id"])
    ).fetchone()[0]
    precios = con.execute("SELECT COUNT(*) FROM historial_precios WHERE producto_id = ?", (ctx.ids["producto_id"],)).fetchone()[0]
    con.close()
    assert stock_a == 2  # 3 sembrado - 1 del delta
    assert ajeno_en_b == 0
    assert precios == 0
    assert ctx.hash_bd() != antes  # B si crea su propio producto "Zumo"


def test_analisis_de_ticket_no_expone_catalogo_de_otros_hogares(ctx, monkeypatch):
    """/api/tickets/analizar envia a la IA y empareja contra el catalogo de
    productos: solo debe ser el del hogar activo del usuario."""
    capturado = {}

    class FalsoClaude:
        def disponible(self):
            return True

        def procesar(self, imagen_bytes, productos_catalogo, mime=None):
            capturado["catalogo"] = productos_catalogo
            return {"productos": [{"producto_id": ctx.ids["producto_id"], "cantidad": 1}]}

    monkeypatch.setattr("stockhogar.rutas.escaner.tickets.ClaudeOCR", FalsoClaude)
    c = ctx.cliente("B", ctx.h["B"])
    resp = c.post("/api/tickets/analizar", data={"foto": (io.BytesIO(_png()), "ticket.png")}, content_type="multipart/form-data")
    assert "catalogo" in capturado
    assert all(MARCA not in p["nombre"] for p in capturado["catalogo"])
    assert MARCA not in resp.get_data(as_text=True)


def test_get_gastos_no_muta_la_bd_para_roles_de_solo_lectura(ctx):
    """Un recurrente vencido se materializa en gasto al listar: solo si quien
    lista puede editar. ver/comprar no deben escribir nada con un GET."""
    con = sqlite3.connect(ctx.ruta_db)
    con.execute("UPDATE gastos_recurrentes SET proxima_fecha = '2000-01-01' WHERE id = ?", (ctx.ids["recurrente_id"],))
    con.commit()
    con.close()
    for usuario in ("V", "C"):
        antes = ctx.hash_bd()
        assert ctx.cliente(usuario, ctx.h["A"]).get("/api/gastos").status_code == 200
        assert ctx.hash_bd() == antes, f"GET /api/gastos mutó la BD para el rol de {usuario}"
    assert ctx.cliente("E", ctx.h["A"]).get("/api/gastos").status_code == 200
    assert ctx.hash_bd() != antes  # un editor si los genera


def test_perfil_no_cambia_contrasena_ni_credenciales_sin_la_actual(ctx):
    c = ctx.cliente("B", ctx.h["B"])
    antes = ctx.hash_bd()
    assert c.put("/api/auth/perfil", json={"password": "NuevaClave-99xyz"}).status_code == 400
    assert c.put("/api/auth/perfil", json={"usuario": "otro_nombre_x"}).status_code == 400
    assert c.put("/api/auth/perfil", json={"email": "otro@example.com"}).status_code == 400
    assert ctx.hash_bd() == antes


def test_cambiar_password_exige_la_actual_y_rechaza_filtradas(ctx, monkeypatch):
    c = ctx.cliente("B", ctx.h["B"])
    antes = ctx.hash_bd()
    base = {"password_nueva": "NuevaClave-99xyz", "password_confirmacion": "NuevaClave-99xyz"}
    assert c.post("/api/auth/cambiar-password", json={**base, "password_actual": "incorrecta"}).status_code == 400
    assert c.post("/api/auth/cambiar-password", json=base).status_code == 400
    assert ctx.hash_bd() == antes
    monkeypatch.setattr("stockhogar.rutas.cuenta.credenciales.es_password_filtrada", lambda p: True)
    assert c.post("/api/auth/cambiar-password", json={**base, "password_actual": "password123"}).status_code == 400
    assert ctx.hash_bd() == antes


def test_buscar_usuarios_no_existe_ni_enumera_con_comodines(ctx):
    c = ctx.cliente("B", ctx.h["B"])
    for q in ("%25%25", "__", "ba"):
        resp = c.get(f"/api/hogares/buscar-usuarios?q={q}")
        assert resp.status_code == 404
        assert "@" not in resp.get_data(as_text=True)


@pytest.mark.xfail(strict=True, reason=(
    "Vulnerabilidad CONOCIDA, no corregida (requiere esquema con propietario): las categorias de "
    "producto/gasto son un catalogo global compartido, cualquier usuario autenticado puede borrar "
    "las categorias que creo otro hogar. Ver informe del barrido."))
def test_categoria_creada_por_a_no_la_borra_b(ctx):
    creada = ctx.cliente("A", ctx.h["A"]).post("/api/categorias", json={"nombre": f"{MARCA} Categoria"})
    assert creada.status_code == 201
    resp = ctx.cliente("B", ctx.h["B"]).delete(f"/api/categorias/{creada.get_json()['id']}")
    assert resp.status_code in (403, 404)


# --- (d) CSRF -----------------------------------------------------------------

# Rutas /api mutadoras exentas de CSRF a proposito (ver rutas/paginas.py).
EXENTAS_CSRF = {("/api/log/client", "POST")}


def test_csrf_exigido_en_todas_las_rutas_mutadoras(ctx):
    reales = _rutas_api_reales(ctx.app)
    ctx.app.config["WTF_CSRF_ENABLED"] = True
    try:
        cliente = ctx.cliente("A", ctx.h["A"])
        for (regla, metodo), _endpoint in sorted(reales.items()):
            if metodo not in ("POST", "PUT", "PATCH", "DELETE") or (regla, metodo) in EXENTAS_CSRF:
                continue
            url = regla.format(**ctx.ids)
            resp = cliente.open(url, method=metodo, json={})
            assert resp.status_code == 400 and "CSRF" in resp.get_data(as_text=True), f"{metodo} {regla} -> {resp.status_code}"
    finally:
        ctx.app.config["WTF_CSRF_ENABLED"] = False
