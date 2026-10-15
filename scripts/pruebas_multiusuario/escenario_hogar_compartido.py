import sys; import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h import *
N = 8
print("== Fase A: registro concurrente de", N, "usuarios")
us = [U(f"u{i}") for i in range(N)]
cods = paralelo([u.registrar for u in us])
check("registro concurrente 201", all(c == 201 for c in cods), cods)
paralelo([u.estado for u in us])
check("ids de usuario distintos", len({u.id for u in us}) == N, [u.id for u in us])
# nombre duplicado
dup = U("dup"); dup.nombre = us[0].nombre.upper()
check("registro duplicado 409", dup.registrar() == 409)
# login incorrecto / correcto en otra sesion
x = U("x"); x.nombre = us[1].nombre
r, j = x.post("/api/auth/login", {"usuario": x.nombre, "password": "incorrecta-123456"})
check("login incorrecto 401", r.status_code == 401, r.text[:100])
check("login correcto desde otro dispositivo", x.login() == 200)

print("== Fase B: cada usuario crea su hogar y su stock (concurrente)")
cods = paralelo([u.crear_hogar for u in us])
check("crear hogar 201", all(c in (200, 201) for c in cods), cods)
def stock(u):
    out = []
    for i in range(6):
        r, j = u.post("/api/productos", {"nombre": f"Prod{i}-{u.nombre}", "cantidad": i + 1, "categoria": "Otros", "stock_minimo": 2, "unidad": "ud"})
        out.append(r.status_code)
    return out
res = paralelo([lambda u=u: stock(u) for u in us])
check("alta de 6 productos por usuario", all(all(c in (200, 201) for c in r) for r in res), res)
def listar(u):
    r, j = u.get("/api/productos"); d = j if isinstance(j, list) else (j or {}).get("data", j)
    return d
ls = paralelo([lambda u=u: listar(u) for u in us])
check("cada usuario ve solo sus 6 productos", all(isinstance(l, list) and len(l) == 6 and all(u.nombre in p["nombre"] for p in l) for u, l in zip(us, ls)), [len(l) if isinstance(l, list) else l for l in ls])

print("== Fase C: hogar compartido y concurrencia sobre el mismo producto")
dueno, miembros = us[0], us[1:5]
for m in miembros:
    r, j = dueno.post(f"/api/hogares/{dueno.hogar}/compartir", {"usuario": m.nombre, "nivel": "editar"})
    check(f"compartir con {m.nombre}", r.status_code in (200, 201), r.text[:150])
def aceptar(m):
    r, j = m.get("/api/hogares/invitaciones-pendientes")
    inv = j if isinstance(j, list) else (j or {}).get("data", [])
    if not inv: return ("sin invitacion", r.status_code, r.text[:100])
    r2, j2 = m.post(f"/api/hogares/aceptar-invitacion/{inv[0]['codigo_invitacion']}")
    return r2.status_code
res = paralelo([lambda m=m: aceptar(m) for m in miembros])
check("aceptar invitaciones", all(c == 200 for c in res), res)
for m in miembros:
    r, j = m.post(f"/api/hogares/{dueno.hogar}/seleccionar"); m.hogar = dueno.hogar
    check(f"{m.nombre} selecciona el hogar compartido", r.status_code == 200, r.text[:100])
r, j = dueno.get("/api/productos"); prods = j if isinstance(j, list) else j["data"]
pid = prods[0]["id"]; base = prods[0]["cantidad"]
todos = [dueno] + miembros
def sumar(u):
    return [u.patch(f"/api/productos/{pid}", {"delta": 1})[0].status_code for _ in range(6)]
res = paralelo([lambda u=u: sumar(u) for u in todos])
r, j = dueno.get("/api/productos"); prods = j if isinstance(j, list) else j["data"]
final = [p for p in prods if p["id"] == pid][0]["cantidad"]
check("30 incrementos concurrentes no se pierden", final == base + 30, f"base {base} final {final}")
for m in miembros:
    r, j = m.get("/api/productos"); l = j if isinstance(j, list) else j["data"]
    check(f"{m.nombre} ve el stock compartido", len(l) == 6 and any(p["id"] == pid for p in l), len(l))
# rol 'ver'
ver = miembros[0]
dueno.patch(f"/api/hogares/{dueno.hogar}/permisos/{ver.id}", {"nivel": "ver"})
r, j = ver.post("/api/productos", {"nombre": "No deberia", "cantidad": 1, "categoria": "Otros"})
check("rol ver no puede crear (403)", r.status_code == 403, r.status_code)
r, j = ver.get("/api/productos"); check("rol ver puede leer", r.status_code == 200)
dueno.patch(f"/api/hogares/{dueno.hogar}/permisos/{ver.id}", {"nivel": "editar"})
# aislamiento: usuario fuera del hogar
fuera = us[6]
r, j = fuera.patch(f"/api/productos/{pid}", {"delta": 1}); check("ajeno no puede modificar (403/404)", r.status_code in (403, 404), r.status_code)
r, j = fuera.get(f"/api/hogares/{dueno.hogar}/miembros"); check("ajeno no ve miembros", r.status_code in (403, 404), r.status_code)

print("== Fase D: lista de la compra concurrente")
def compra(u):
    ids = []
    for i in range(4):
        r, j = u.post("/api/articulos", {"nombre": f"Item{i}-{u.nombre}", "cantidad": 1, "categoria": "Otros", "icono": "h-archive-box"})
        ids.append((r.status_code, (j or {}).get("id") or (j or {}).get("data", {}).get("id")))
    return ids
res = paralelo([lambda u=u: compra(u) for u in todos])
check("12+ articulos de compra creados", all(all(c in (200, 201) for c, _ in r) for r in res), res)
r, j = dueno.get("/api/articulos"); d = j if isinstance(j, dict) else {}
d = d.get("data", d)
pend = d.get("pendientes", [])
nom = {a["nombre"] for a in pend}
check("el dueno ve los 20 articulos de todos", all(f"Item{i}-{u.nombre}" in nom or (i == 0 and u is dueno) for u in todos for i in range(4)), len(pend))
it = pend[0]["id"]
res = paralelo([lambda u=u: u.patch(f"/api/articulos/{it}", {"activo": False})[0].status_code for u in todos])
check("marcar comprado a la vez no da 5xx", all(c < 500 for c in res), res)
r, j = dueno.get("/api/articulos"); d = (j or {}); d = d.get("data", d)
print("   completados:", [(x["nombre"], x["cantidad"]) for x in d.get("completados", [])]); print("   pendientes:", [x["nombre"] for x in d["pendientes"]][:30])
check("el articulo marcado esta en completados una sola vez", sum(1 for x in d.get("completados", []) if x["nombre"].startswith("Item0-")) == 1, d.get("completados"))
r, j = dueno.get("/api/hogares/version"); v1 = (j or {}).get("version") or (j or {}).get("data", {}).get("version")
miembros[1].post("/api/articulos", {"nombre": "CambioVersion", "cantidad": 1, "categoria": "Otros", "icono": "h-archive-box"})
r, j = dueno.get("/api/hogares/version"); v2 = (j or {}).get("version") or (j or {}).get("data", {}).get("version")
check("la version del hogar cambia al editar otro miembro", v1 != v2, (v1, v2))

print("== Fase E: gastos repartidos")
ids = [u.id for u in todos]
def gasto(u, i):
    parts = [{"usuario_id": x, "importe": 0} for x in ids]
    tot = 100.0 + i
    reparto = round(tot / len(ids), 2); resto = round(tot - reparto * len(ids), 2)
    for k, p in enumerate(parts): p["importe"] = round(reparto + (resto if k == len(parts) - 1 else 0), 2)
    r, j = u.post("/api/gastos", {"descripcion": f"Gasto {i} de {u.nombre}", "importe_total": tot, "fecha": "2026-10-10", "usuario_pagador_id": u.id, "participantes": parts})
    return r.status_code
res = paralelo([lambda u=u, i=i: gasto(u, i) for i, u in enumerate(todos)])
check("5 gastos concurrentes entre 5", all(c in (200, 201) for c in res), res)
r, j = dueno.get("/api/gastos/saldo"); sd = j if isinstance(j, list) else (j or {}).get("data", j)
tot = round(sum(s["saldo"] for s in sd), 2) if isinstance(sd, list) else None
check("los saldos suman cero", tot is not None and abs(tot) < 0.05, (tot, sd))
r, j = dueno.get("/api/gastos/simplificar"); check("simplificar deudas 200", r.status_code == 200, r.text[:100])
deudor = [s for s in sd if s["saldo"] < -0.5][0]; ud = [u for u in todos if u.id == deudor["usuario_id"]][0]
acre = [s for s in sd if s["saldo"] > 0.5][0]
r, j = ud.post("/api/gastos/liquidaciones", {"usuario_origen_id": ud.id, "usuario_destino_id": acre["usuario_id"], "importe": 5.0})
check("liquidacion creada", r.status_code in (200, 201), r.text[:150])
r, j = dueno.get("/api/gastos/saldo"); sd2 = j if isinstance(j, list) else (j or {}).get("data", j)
check("saldos siguen sumando cero tras liquidar", abs(sum(s["saldo"] for s in sd2)) < 0.05)
r, j = dueno.get("/api/gastos/exportar"); check("exportar gastos CSV", r.status_code == 200 and "Gasto" in r.text)
r, j = dueno.get("/api/gastos"); lg = j if isinstance(j, list) else (j or {}).get("data", j)
check("el listado trae 5 gastos", isinstance(lg, list) and len(lg) == 5, len(lg) if isinstance(lg, list) else lg)

print("== Fase F: recetas")
r, j = dueno.post("/api/recetas", {"nombre": "Tortilla", "ingredientes": [{"nombre": "Huevos", "cantidad": 6, "unidad": "ud"}, {"nombre": "Patatas", "cantidad": 3, "unidad": "ud"}]})
check("crear receta", r.status_code in (200, 201), r.text[:200])
rid = (j or {}).get("id") or (j or {}).get("data", {}).get("id")
r, j = miembros[2].get("/api/recetas"); lr = j if isinstance(j, list) else (j or {}).get("data", j)
check("otro miembro ve la receta", isinstance(lr, list) and any(x["id"] == rid for x in lr), r.text[:100])
r, j = miembros[2].post(f"/api/recetas/{rid}/anadir-a-lista"); check("anadir receta a la lista", r.status_code == 200, r.text[:150])
r, j = dueno.get("/api/articulos"); d = (j or {}); d = d.get("data", d)
check("ingredientes en la lista", any("Huevos" in a["nombre"] for a in d["pendientes"]))
r, j = fuera.get("/api/recetas"); lf = j if isinstance(j, list) else (j or {}).get("data", j)
check("ajeno no ve recetas ajenas", isinstance(lf, list) and not any(x["id"] == rid for x in lf))

print("== Fase G: ajustes y sesiones")
u = todos[2]
r, j = u.post("/api/auth/tema", {"tema": "dark"}); check("cambiar tema", r.status_code == 200)
r, j = u.post("/api/idiomas/cambiar", {"idioma": "en"}); check("cambiar idioma", r.status_code == 200)
r, j = u.get("/api/auth/estado"); check("estado refleja preferencias", (j or {}).get("tema_preferido") == "dark" or (j or {}).get("data", {}).get("tema_preferido") == "dark", str(j)[:200])
r, j = u.get("/api/auth/exportar-mis-datos"); check("exportar mis datos (zip/json)", r.status_code == 200 and len(r.content) > 100)
r, j = u.put("/api/auth/perfil", {"nombre": "Nombre Visible"}); check("cambiar nombre visible", r.status_code == 200, r.text[:100])
r, j = u.post("/api/auth/cambiar-password", {"password_actual": PW, "password_nueva": PW + "x", "password_confirmacion": PW + "x"}); check("cambiar contrasena", r.status_code == 200, r.text[:200])
r, j = u.get("/api/productos"); check("sesion propia sigue viva tras cambiar contrasena", r.status_code == 200, r.status_code)
u2 = U("x"); u2.nombre = u.nombre; check("login con la contrasena nueva", u2.post("/api/auth/login", {"usuario": u.nombre, "password": PW + "x"})[0].status_code == 200)
logout = todos[3]; copia = logout.s.cookies.get("session")
r, j = logout.post("/api/auth/logout"); check("logout", r.status_code == 200)
ladron = requests.get(BASE + "/api/productos", cookies={"session": copia}, timeout=30); check("cookie copiada deja de valer", ladron.status_code == 401, ladron.status_code)
r, j = todos[4].get("/api/auth/mis-eventos-seguridad"); check("eventos de seguridad", r.status_code == 200 and len(j if isinstance(j, list) else (j or {}).get("data", [])) >= 1, r.text[:100])
resumen()
