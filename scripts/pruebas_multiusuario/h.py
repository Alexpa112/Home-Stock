import requests, threading, time, uuid, json, io, sys, random
BASE = "http://127.0.0.1:3000"
PW = "Clave-Segura-Test-8841"
RES = []; LOCK = threading.Lock(); TIMES = []

def check(nombre, ok, detalle=""):
    with LOCK: RES.append((nombre, bool(ok), detalle))
    if not ok: print("  FALLO:", nombre, "|", str(detalle)[:300])

class U:
    def __init__(self, tag):
        self.s = requests.Session(); self.nombre = f"{tag}_{uuid.uuid4().hex[:6]}"; self.tok = None; self.id = None; self.hogar = None
    def csrf(self):
        r = self.s.get(BASE + "/api/csrf-token", timeout=60); self.tok = r.json()["csrf_token"]
    def call(self, m, url, **kw):
        if self.tok is None: self.csrf()
        h = kw.pop("headers", {}); h["X-CSRFToken"] = self.tok
        t = time.time()
        r = self.s.request(m, BASE + url, headers=h, timeout=240, **kw)
        with LOCK: TIMES.append((time.time() - t, m, url, r.status_code))
        if r.status_code == 400 and "CSRF" in r.text:
            self.csrf(); h["X-CSRFToken"] = self.tok
            r = self.s.request(m, BASE + url, headers=h, timeout=240, **kw)
        try: j = r.json()
        except Exception: j = None
        if isinstance(j, dict) and "csrf_token" in j: self.tok = j["csrf_token"]
        return r, j
    def get(self, u, **k): return self.call("GET", u, **k)
    def post(self, u, body=None, **k): return self.call("POST", u, json=body if body is not None else {}, **k)
    def patch(self, u, body=None, **k): return self.call("PATCH", u, json=body or {}, **k)
    def put(self, u, body=None, **k): return self.call("PUT", u, json=body or {}, **k)
    def delete(self, u, body=None, **k): return self.call("DELETE", u, json=body or {}, **k)
    def registrar(self):
        r, j = self.post("/api/auth/registrar", {"usuario": self.nombre, "password": PW, "acepta_terminos": True})
        return r.status_code
    def login(self):
        r, j = self.post("/api/auth/login", {"usuario": self.nombre, "password": PW}); return r.status_code
    def estado(self):
        r, j = self.get("/api/auth/estado"); self.id = (j or {}).get("usuario_id"); return j
    def crear_hogar(self, nombre="Casa"):
        r, j = self.post("/api/hogares", {"nombre": nombre})
        self.hogar = (j or {}).get("id") or (j or {}).get("data", {}).get("id")
        return r.status_code
def paralelo(fns, max_hilos=50):
    out = [None] * len(fns); ths = []
    def run(i, f):
        try: out[i] = f()
        except Exception as e: out[i] = e
    for i, f in enumerate(fns):
        t = threading.Thread(target=run, args=(i, f)); t.start(); ths.append(t)
    for t in ths: t.join()
    return out
def resumen():
    ok = sum(1 for r in RES if r[1]); print(f"\nCHECKS {ok}/{len(RES)}")
    for n, o, d in RES:
        if not o: print(" X", n, d)
    if TIMES:
        ts = sorted(t[0] for t in TIMES); print(f"peticiones {len(ts)}  p50 {ts[len(ts)//2]:.2f}s  p95 {ts[int(len(ts)*.95)]:.2f}s  max {ts[-1]:.2f}s")
        e5 = [t for t in TIMES if t[3] >= 500]; print("5xx:", len(e5), e5[:5])
