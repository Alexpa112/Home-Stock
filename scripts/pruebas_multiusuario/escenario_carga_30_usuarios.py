import sys, sqlite3; import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from h import *
from werkzeug.security import generate_password_hash
from datetime import datetime
D = lambda j: j if isinstance(j, list) else (j or {}).get("data", j)
N = 30
db = sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "stock.db")); db.execute("PRAGMA busy_timeout=30000")
hash_ = generate_password_hash(PW); us = []
for i in range(N):
    u = U(f"m{i}"); db.execute("INSERT INTO usuarios (nombre_usuario,password_hash,fecha_creacion,terminos_version_aceptada) VALUES (?,?,?,(SELECT 'x'))", (u.nombre, hash_, datetime.now().isoformat())); us.append(u)
db.commit()
print("== 30 usuarios inician sesion a la vez")
t = time.time(); cods = paralelo([u.login for u in us]); print("   tiempo", round(time.time() - t, 1), "s")
check("30 logins concurrentes 200", all(c == 200 for c in cods), cods)
paralelo([u.estado for u in us]); check("30 ids distintos", len({u.id for u in us}) == N)
print("== 30 usuarios crean hogar, productos y lista a la vez")
paralelo([u.crear_hogar for u in us])
def trabajo(u):
    c = []
    for i in range(5): c.append(u.post("/api/productos", {"nombre": f"P{i}", "cantidad": 3, "categoria": "Otros"})[0].status_code)
    for i in range(3): c.append(u.post("/api/articulos", {"nombre": f"A{i}", "cantidad": 1, "categoria": "Otros", "icono": "h-archive-box"})[0].status_code)
    r, j = u.post("/api/gastos", {"descripcion": "g", "importe_total": 10, "fecha": "2026-10-10", "usuario_pagador_id": u.id, "participantes": [{"usuario_id": u.id, "importe": 10}]}); c.append(r.status_code)
    return c
t = time.time(); res = paralelo([lambda u=u: trabajo(u) for u in us]); print("   tiempo", round(time.time() - t, 1), "s")
check("240+ escrituras concurrentes sin errores", all(all(x in (200, 201) for x in r) for r in res), [r for r in res if not all(x in (200, 201) for x in r)][:3])
bad = 0
for u in us:
    l = D(u.get("/api/productos")[1]); a = D(u.get("/api/articulos")[1])
    if len(l) != 5 or len(a["pendientes"]) < 3: bad += 1
check("cada usuario ve exactamente lo suyo", bad == 0, bad)
print("== reautenticacion: borrar cuenta y 2FA")
u = us[0]
r, j = u.delete(f"/api/usuarios/{u.id}", {}); check("borrar cuenta sin contrasena rechazado", r.status_code == 400, r.status_code)
r, j = u.post("/api/auth/doble-factor", {"activo": True}); check("2FA sin email rechazado", r.status_code == 400, r.text[:100])
r, j = u.put("/api/auth/perfil", {"email": f"{u.nombre}@example.com", "password_actual": PW}); check("anadir email", r.status_code == 200, r.text[:150])
r, j = u.post("/api/auth/doble-factor", {"activo": True}); check("activar 2FA con email", r.status_code == 200, r.text[:100])
r, j = u.post("/api/auth/doble-factor", {"activo": False}); check("desactivar 2FA sin contrasena rechazado", r.status_code == 400)
r, j = u.post("/api/auth/doble-factor", {"activo": False, "password_actual": PW}); check("desactivar 2FA con contrasena", r.status_code == 200)
r, j = u.delete(f"/api/usuarios/{u.id}", {"password_actual": PW}); check("borrar cuenta con contrasena", r.status_code == 200, r.text[:100])
r, j = u.get("/api/productos"); check("tras borrar la cuenta no hay acceso", r.status_code == 401, r.status_code)
x = U("x"); x.nombre = u.nombre; check("la cuenta borrada ya no entra", x.login() == 401)
print("== olvide mi contrasena y eventos")
r, j = U("y").post("/api/auth/solicitar-reset-password", {"usuario": us[1].nombre, "email": "no@example.com"}); check("reset responde generico 200", r.status_code == 200, r.text[:120])
r, j = U("y").post("/api/auth/restablecer-password", {"token": "falso", "password_nueva": PW + "z"}); check("token de reset falso rechazado", r.status_code == 400)
print("== fuerza bruta contra una cuenta")
v = us[2]; z = U("z"); z.nombre = v.nombre
c = [z.post("/api/auth/login", {"usuario": v.nombre, "password": "mala-mala-mala-1"})[0].status_code for _ in range(25)]
check("bloqueo por intentos (429)", 429 in c, c)
check("el dueno legitimo tambien queda bloqueado temporalmente (esperado) o entra", z.login() in (200, 429))
print("== limpieza de sesiones: cerrar otras sesiones")
w = us[3]; w2 = U("w"); w2.nombre = w.nombre; w2.login()
r, j = w.post("/api/auth/cerrar-otras-sesiones"); check("cerrar otras sesiones", r.status_code == 200, r.text[:100])
check("la otra sesion queda cerrada", w2.get("/api/productos")[0].status_code == 401)
check("la sesion actual sigue", w.get("/api/productos")[0].status_code == 200)
db.execute("DELETE FROM usuarios WHERE nombre_usuario LIKE 'm%\\_%' ESCAPE '\\'"); db.commit()
resumen()
