"""Evalua el lector de tickets con RECIBOS REALES anotados (formato SROIE).

Uso:  RECIBOS_DIR=/ruta python scripts/evaluar_recibos_reales.py [N] [DESDE] [--fallos]
con /ruta/{img/NNN.jpg, box/NNN.csv, key/NNN.json}. Los 1000 recibos de la
competicion ICDAR-2019 SROIE estan en https://github.com/zzzDavid/ICDAR-2019-SROIE
(carpeta data/). Son recibos malayos en ingles, NO espanoles: miden la LECTURA
(lineas e importes) con papel real, y de forma indirecta la comprension (la suma
de los articulos debe dar el total impreso). No miden nombres ni cantidades.
"""
"""Evalua el lector con RECIBOS REALES (SROIE, fotos/escaneos con anotacion de linea).
Metricas: recall de lineas, recall de importes, total del ticket, recall/precision de articulos (proxy)."""
import sys, re, json, glob, os, time, statistics
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rapidfuzz import fuzz
from stockhogar.integraciones import ticket_ocr
from stockhogar.servicios.ocr.parser_mejorado import ParserMejorado
from stockhogar.servicios.ocr.cuadre_ticket import extraer_total_impreso

D = os.environ.get("RECIBOS_DIR", "/tmp/recibos/").rstrip("/") + "/"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 100
OFFSET = int(sys.argv[2]) if len(sys.argv) > 2 else 0
PRECIO = re.compile(r"(?<![\d.,])(\d{1,5}[.,]\d{2})(?!\d)")
def norm(s): return re.sub(r"[^a-z0-9]", "", s.lower())
def num(s): return round(float(s.replace(",", ".")), 2)
RE_TOTALISH = re.compile(r"total|subtotal|change|cash|tender|amount|gst|tax|round|visa|master|card|disc|saving|payment|balance|credit|debit|tel|invoice|qty|item|sales|rm\\s*\\d|vat|sst|service|received|paid|due", re.I)

def gt_cajas(base):
    out = []
    for l in open(D + "box/" + base + ".csv", encoding="utf-8", errors="ignore"):
        p = l.rstrip("\n").split(",", 8)
        if len(p) == 9 and p[8].strip():
            try: ys = [int(p[1]), int(p[3]), int(p[5]), int(p[7])]; xs = [int(p[0]), int(p[2]), int(p[4]), int(p[6])]
            except ValueError: continue
            out.append(((min(ys) + max(ys)) / 2, max(ys) - min(ys), min(xs), p[8].strip()))
    return out

def gt_lineas(base):
    return [c[3] for c in gt_cajas(base)]

def gt_filas(base):
    """Cajas de la misma altura -> una fila de ticket (nombre + cantidad + importe)."""
    cajas = sorted(gt_cajas(base))
    filas = []
    for y, h, x, t in cajas:
        if filas and abs(y - filas[-1][0]) <= max(6, 0.6 * max(h, filas[-1][1])):
            filas[-1][2].append((x, t)); filas[-1] = (filas[-1][0], max(h, filas[-1][1]), filas[-1][2])
        else: filas.append((y, h, [(x, t)]))
    return [" ".join(t for _, t in sorted(f[2])) for f in filas]

archivos = sorted(glob.glob(D + "img/*.jpg"))[OFFSET:OFFSET + N]
T = dict(n=0, lin=0, lin_ok=0, imp=0, imp_ok=0, tot=0, tot_ok=0, it=0, it_ok=0, pred=0, pred_ok=0, err=0)
tiempos = []; fallos = []
for f in archivos:
    base = os.path.basename(f)[:-4]
    gt = gt_lineas(base); key = json.load(open(D + "key/" + base + ".json", encoding="utf-8", errors="ignore"))
    t0 = time.time()
    try: texto = ticket_ocr.extraer_texto(f)
    except Exception as e: T["err"] += 1; fallos.append((base, "ERR", str(e)[:60])); continue
    tiempos.append(time.time() - t0)
    T["n"] += 1
    lineas_ocr = [norm(x) for x in texto.split("\n") if x.strip()]
    blob = norm(texto)
    for g in gt:
        if len(norm(g)) < 4: continue
        T["lin"] += 1
        gn = norm(g)
        if gn in blob or any(fuzz.partial_ratio(gn, l) >= 88 for l in lineas_ocr if abs(len(l) - len(gn)) < 25): T["lin_ok"] += 1
    gt_imp = [num(m) for g in gt for m in PRECIO.findall(g)]
    ocr_imp = [num(m) for m in PRECIO.findall(texto)]
    for v in gt_imp:
        T["imp"] += 1
        if v in ocr_imp: T["imp_ok"] += 1
    # total
    try: tot = float(key.get("total", "").replace(",", ".").replace("RM", "").strip() or "nan")
    except ValueError: tot = None
    if tot is not None and tot == tot:
        T["tot"] += 1
        got = extraer_total_impreso(texto)
        # tambien vale si el importe del total aparece como importe leido
        if (got is not None and abs(got - tot) <= 0.06) or (got is None and tot in ocr_imp): T["tot_ok"] += 1
        elif len(fallos) < 400: fallos.append((base, "TOTAL", tot, got))
    # articulos (proxy): filas GT que acaban en importe y no son de cierre/impuestos/pago
    gt_items = []
    for g in gt_filas(base):
        m = re.search(r"(\d{1,5}[.,]\d{2})\s*(?:RM)?\s*[A-Za-z]{0,2}\s*$", g)
        if m and not RE_TOTALISH.search(g) and len(norm(g)) > 5: gt_items.append((g, num(m.group(1))))
    from stockhogar.servicios.ocr.procesador_tickets_v2 import ProcesadorTicketsV2
    proc = ProcesadorTicketsV2(); proc.matcher.buscar_en_catalogo = lambda *a, **k: None; proc.matcher.sugerir_cantidad_estandar = lambda *a, **k: 1
    class _P:  # adaptador: el item del procesador con los atributos del parser
        def __init__(self, d): self.nombre = d["nombre"]; self.precio_total = d["precio_total"]
    from stockhogar.servicios.ocr.cuadre_ticket import cuadrar_con_total
    its, _cu = cuadrar_con_total(proc.procesar_completo(texto, None), texto)
    pr = [_P(d) for d in its]
    usados = set()
    for g, v in gt_items:
        T["it"] += 1
        for i, p in enumerate(pr):
            if i in usados: continue
            if abs((p.precio_total or 0) - v) < 0.011:
                usados.add(i); T["it_ok"] += 1; break
    suma = round(sum(x.precio_total or 0 for x in pr), 2)
    if tot is not None and tot == tot:
        T["cu"] = T.get("cu", 0) + 1
        if abs(suma - tot) <= 0.06: T["cu_ok"] = T.get("cu_ok", 0) + 1
        elif len(fallos) < 2000: fallos.append((base, "CUADRE", "suma", suma, "total", tot, [(x.nombre[:22], x.precio_total) for x in pr][:8]))
    importes_items = [v for _, v in gt_items]
    for p in pr:
        T["pred"] += 1
        if any(abs((p.precio_total or 0) - v) < 0.011 for v in importes_items): T["pred_ok"] += 1

def pct(a, b): return f"{100 * a / b:.1f}%" if b else "n/a"
print(f"recibos {T['n']} (errores {T['err']})  tiempo medio {statistics.mean(tiempos):.2f}s  max {max(tiempos):.1f}s")
print("recall lineas   ", pct(T["lin_ok"], T["lin"]), f"({T['lin_ok']}/{T['lin']})")
print("recall importes ", pct(T["imp_ok"], T["imp"]), f"({T['imp_ok']}/{T['imp']})")
print("total ticket    ", pct(T["tot_ok"], T["tot"]), f"({T['tot_ok']}/{T['tot']})")
print("CUADRE suma items == total", pct(T.get("cu_ok",0), T.get("cu",0)), f"({T.get('cu_ok',0)}/{T.get('cu',0)})")
print("articulos recall", pct(T["it_ok"], T["it"]), f"({T['it_ok']}/{T['it']})")
print("articulos precision(importe real)", pct(T["pred_ok"], T["pred"]), f"({T['pred_ok']}/{T['pred']})")
if "--fallos" in sys.argv:
    for x in fallos[:40]: print(x)
