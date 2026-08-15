"""Rutas para escanear tickets de compra y volcarlos al stock."""
import logging
import os
import subprocess
import tempfile
from pathlib import Path

from flask import Blueprint, request, session

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..config import LIMITE_OCR_DIARIO
from ..db import get_db
from ..red import ip_cliente, limite_por_ip
from ..translator import traducir
from ..integraciones import ticket_ocr
from ..servicios import cuota_ocr
from ..servicios.ocr import ProcesadorTicketsV2, crear_respuesta_usuario
from ..servicios.ocr.catalogo import catalogo_del_hogar as _catalogo_del_hogar
from ..servicios.ocr.claude_ocr import ClaudeOCR
from ..servicios.ocr.matcher_inteligente import MatcherInteligente
from ..utils import Validator
from ..utils.imagenes import validar_y_recodificar
from ..servicios.stock import crear_producto_nuevo, sumar_stock, hogar_actual_con_permiso, registrar_precio

bp = Blueprint("tickets", __name__, url_prefix="/api/tickets")

EXTENSIONES_PERMITIDAS = {"png", "jpg", "jpeg", "gif", "bmp", "webp", "heic", "heif", "pdf"}
TAMANO_MAXIMO_MB = 10

_UNIDADES_VALIDAS = ("ud", "kg", "g", "l", "ml")

_MIME_POR_EXTENSION = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".gif": "image/gif", ".bmp": "image/bmp", ".webp": "image/webp",
}


def _items_desde_ia(respuesta_ia, productos_catalogo, db, hogar_id=None):
    """Convierte la respuesta de la IA (ya emparejada con el catálogo) al
    mismo formato de "items" que produce ProcesadorTicketsV2, para que
    crear_respuesta_usuario() y el resto del flujo (confirmar_ticket, UI) no
    tengan que distinguir qué motor de OCR se usó.
    """
    catalogo_por_id = {p["id"]: p for p in productos_catalogo}
    matcher = MatcherInteligente()
    items = []
    for item in respuesta_ia.get("productos", []):
        # Obtener nombre
        nombre = (item.get("nombre_ticket") or "").strip()
        if not nombre:
            nombre = (item.get("nombre") or "").strip()
        if not nombre:
            continue  # Saltar si no hay nombre

        nombre = nombre.title()

        # Obtener producto_id
        producto_id = item.get("producto_id")
        # Convertir string "null" o vacío a None
        if producto_id == "null" or producto_id == "":
            producto_id = None
        # Intentar convertir a int si es string de número
        elif isinstance(producto_id, str):
            try:
                producto_id = int(producto_id)
            except (ValueError, TypeError):
                producto_id = None

        catalogado = catalogo_por_id.get(producto_id) if producto_id is not None else None

        if catalogado:
            nombre = catalogado["nombre"]
            categoria = catalogado["categoria"]
            confianza_match = 1.0
        else:
            categoria = matcher.deducir_categoria(nombre) or "Otros"
            confianza_match = 0
            producto_id = None

        # Convertir cantidad a número (puede venir como string de JSON)
        try:
            cantidad = float(item.get("cantidad") or 1)
            if cantidad <= 0:
                cantidad = 1
        except (ValueError, TypeError):
            cantidad = 1

        # Normalizar unidad
        unidad = (item.get("unidad") or "ud").strip().lower()
        # Validar que unidad sea válida, si no, usar "ud"
        if unidad not in ("ud", "kg", "g", "l", "ml"):
            unidad = "ud"

        # Convertir cantidad a entero si es número entero, sino mantener decimal
        cantidad_formateada = int(cantidad) if cantidad == int(cantidad) else round(cantidad, 2)

        # El item tiene que traer TODAS las claves que produce
        # ProcesadorTicketsV2._procesar_linea, porque crear_respuesta_usuario()
        # -> sugerir_correccion() las lee por indice. Faltaban "alternativas",
        # "razon_precio", "cantidad_sugerida" y "es_promocion", y como
        # sugerir_correccion() entra en la rama de "alternativas" para todo
        # articulo con confianza_match < 0.7 (es decir, para CUALQUIER articulo
        # que no estuviera ya en el catalogo), /api/tickets/analizar respondia
        # 500 en cuanto Claude reconocia un producto nuevo. El escaner solo
        # parecia funcionar con el pipeline local, que si las rellenaba.
        # Precios reales leidos del ticket. Antes iban a 0 fijo porque el
        # esquema de Claude no los pedia; ahora si vienen, y un precio que el
        # ticket no imprime llega como None y se queda en 0 solo de cara al
        # resto del flujo (que espera numeros), pero sin marcarse como valido.
        precio_unitario = item.get("precio_unitario")
        precio_total = item.get("precio_total")
        confianza_lectura = item.get("confianza")

        if precio_total is not None and precio_total > 0:
            precio_valido, razon_precio = matcher.validar_precio(precio_total, categoria)
        else:
            precio_valido, razon_precio = True, "sin_precio"
        if item.get("coherencia_precio") not in (None, "cuadra", "sin_datos"):
            # cantidad x unitario no cuadra con el total: el usuario deberia
            # mirar esa linea antes de confirmar.
            precio_valido = False
            razon_precio = item["coherencia_precio"]

        # confianza_nombre va en escala 0-100 (la que produce ParserMejorado);
        # la del modelo viene en 0..1. Sin dato del modelo se usa 100 como
        # antes, para no cambiar el comportamiento de los motores que no la dan.
        confianza_nombre = (
            round(confianza_lectura * 100, 1) if confianza_lectura is not None else 100
        )

        items.append({
            "nombre": nombre,
            "cantidad": cantidad_formateada,
            "cantidad_sugerida": cantidad_formateada,
            "unidad": unidad,
            "cantidad_texto": f"{cantidad_formateada} {unidad}",
            "precio_unitario": precio_unitario if precio_unitario is not None else 0,
            "precio_total": precio_total if precio_total is not None else 0,
            "precio_unitario_derivado": item.get("precio_unitario_derivado"),
            "confianza_nombre": confianza_nombre,
            "confianza_cantidad": confianza_nombre,
            "es_promocion": False,
            "producto_id": producto_id,
            "categoria": categoria,
            "icono": catalogado.get("icono") if catalogado else None,
            "confianza_match": confianza_match,
            "alternativas": [],
            "precio_valido": precio_valido,
            "razon_precio": razon_precio,
            "linea_original": nombre,
        })
    return items


def _producto_del_hogar(db, producto_id, hogar_id):
    """¿Ese producto pertenece al inventario de este hogar?

    `productos` no tiene columna de hogar: el aislamiento vive en
    `stock_hogar`, asi que la pertenencia se comprueba ahi.
    """
    return db.execute(
        "SELECT 1 FROM stock_hogar WHERE hogar_id = ? AND producto_id = ?",
        (hogar_id, producto_id),
    ).fetchone() is not None


def _extension_permitida(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in EXTENSIONES_PERMITIDAS


def _convertir_pdf_a_imagen(ruta_pdf):
    """Convierte la primera pagina de un PDF a PNG con Poppler (pdftoppm).

    Se usa el binario de sistema en vez de una libreria Python (p.ej.
    PyMuPDF) porque poppler-utils tiene paquete Debian nativo para
    armv7l/aarch64 (Raspberry Pi); las alternativas Python no siempre
    publican wheels para armv7l y forzarian compilar desde fuente.
    """
    prefijo = ruta_pdf + "_pagina"
    try:
        resultado = subprocess.run(
            ["pdftoppm", "-png", "-r", "300", "-singlefile", ruta_pdf, prefijo],
            capture_output=True, timeout=30
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    ruta_png = prefijo + ".png"
    if resultado.returncode != 0 or not os.path.exists(ruta_png):
        return None
    return ruta_png


def _convertir_heic_a_imagen(ruta_heic):
    """Convierte una foto HEIC/HEIF (formato por defecto de la camara de
    iPhone al elegir "Subir archivo" desde la galeria, en vez de "Hacer
    foto") a PNG con libheif (heif-convert).

    Mismo motivo que con el PDF (ver _convertir_pdf_a_imagen): se usa el
    binario de sistema (paquete Debian libheif-examples, con build nativo
    para armv7l/aarch64) en vez de bindings Python (pillow-heif, pyheif),
    que no siempre publican wheels para armv7l y forzarian compilar libheif
    desde fuente en la Raspberry Pi.
    """
    ruta_png = ruta_heic + "_convertida.png"
    try:
        resultado = subprocess.run(
            ["heif-convert", ruta_heic, ruta_png],
            capture_output=True, timeout=30
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    if resultado.returncode != 0 or not os.path.exists(ruta_png):
        return None
    return ruta_png


@bp.route("/analizar", methods=["POST"])
@requerir_sesion
@manejo_errores
def analizar_ticket():
    archivo = request.files.get("foto")
    if archivo is None or archivo.filename == "":
        return APIResponse.validacion("err_sin_imagen")

    if not _extension_permitida(archivo.filename):
        return APIResponse.validacion("err_formato_no_permitido")

    db = get_db()
    usuario_id = session.get("usuario_id")

    # A-1: hasta ahora esta ruta no comprobaba NINGUN permiso de hogar, y leia
    # el catalogo `productos` entero de la instalacion. Se exige 'ver' y el
    # hogar resultante es el que filtra el catalogo mas abajo.
    hogar_id = hogar_actual_con_permiso(db, session, nivel_requerido="ver")
    if hogar_id is None:
        return APIResponse.no_permitido()

    # A-6: la cuota diaria protegia /api/ocr/procesar-ticket, que nadie
    # llamaba, mientras esta ruta -- la que usa el frontend -- no tenia
    # ninguna. Se comprueba antes de gastar nada.
    if cuota_ocr.uso_hoy(db, usuario_id) >= LIMITE_OCR_DIARIO:
        return APIResponse.error("err_limite_ocr_diario", 429)
    if limite_por_ip(f"analizar_ticket:{ip_cliente()}", 30, 60 * 60):
        return APIResponse.error("err_demasiadas_peticiones", 429)

    archivo.seek(0, os.SEEK_END)
    tamano_bytes = archivo.tell()
    archivo.seek(0)
    if tamano_bytes > TAMANO_MAXIMO_MB * 1024 * 1024:
        return APIResponse.validacion(
            traducir("err_archivo_muy_grande").replace("{mb}", str(TAMANO_MAXIMO_MB))
        )

    sufijo = Path(archivo.filename).suffix.lower() or ".jpg"
    tmp = tempfile.NamedTemporaryFile(suffix=sufijo, delete=False)
    tmp.close()
    ruta_png_convertida = None
    try:
        archivo.save(tmp.name)

        ruta_imagen = tmp.name
        es_pdf = sufijo == ".pdf"
        if sufijo in (".heic", ".heif"):
            ruta_png_convertida = _convertir_heic_a_imagen(tmp.name)
            if not ruta_png_convertida:
                return APIResponse.error("err_procesando_ticket", 500)
            ruta_imagen = ruta_png_convertida
        elif es_pdf:
            # El PDF NO se rasteriza aqui: Claude lee el documento completo,
            # mientras que pdftoppm -singlefile solo saca la primera pagina y
            # una factura de varias hojas perdia todos los articulos de la
            # segunda en adelante. La conversion se hace mas abajo, y solo si
            # hay que recurrir a Tesseract.
            # Validacion de contenido real (S-16): antes la daba por buena la
            # propia conversion (si no era un PDF de verdad, fallaba); sin
            # convertir hay que comprobar la firma a mano.
            with open(tmp.name, "rb") as f:
                if not f.read(5).startswith(b"%PDF-"):
                    return APIResponse.validacion("err_formato_no_permitido")
        else:
            # Validacion de contenido real (S-16): el .heic/.heif de arriba ya
            # se "valida" al intentar convertirlo (si no es de verdad ese
            # formato, la conversion falla) y el .pdf comprueba su firma; para
            # el resto de extensiones no habia ninguna comprobacion mas alla
            # del nombre
            # del fichero. No se recodifica aqui (a diferencia de los
            # recibos de gastos.py, que se guardan a largo plazo): esta
            # imagen es efimera, se descarta tras el OCR, y recodificarla
            # podria degradar la calidad que necesita el OCR.
            with open(tmp.name, "rb") as f:
                _, error_validacion = validar_y_recodificar(f.read(), sufijo.lstrip("."))
            if error_validacion:
                return APIResponse.validacion(error_validacion)

        prefiere_ocr_local = bool(
            db.execute("SELECT usuario_ocr_local FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()["usuario_ocr_local"]
        )

        # El catalogo SOLO del hogar activo (A-1). Antes esta consulta no
        # llevaba `hogar_id` y era la unica del backend que leia `productos`
        # sin unir con `stock_hogar` (todo el resto lo hace, ver productos.py y
        # la exportacion RGPD de auth.py). Consecuencias que cerraba:
        #  - _normalizar_producto_id validaba el id devuelto por el modelo
        #    contra el catalogo global, asi que un id de OTRO hogar pasaba la
        #    validacion y su nombre volvia al cliente en la respuesta.
        #  - se enviaban a Anthropic los nombres de producto de todos los
        #    hogares de la instalacion, cosa que la politica de privacidad no
        #    declaraba.
        productos_catalogo = _catalogo_del_hogar(db, hogar_id)

        # Motor principal: Claude Vision API (la mejor visión disponible)
        items = None
        logger = logging.getLogger(__name__)
        uso_motor_nube = False
        totales_ticket = None
        cuadre_ticket = None

        if not prefiere_ocr_local:
            claude = ClaudeOCR()
            if claude.disponible():
                try:
                    with open(ruta_imagen, "rb") as f:
                        imagen_bytes = f.read()
                    uso_motor_nube = True
                    respuesta_ia = claude.procesar(
                        imagen_bytes,
                        productos_catalogo,
                        mime="application/pdf" if es_pdf else None,
                    )
                    if respuesta_ia is not None:
                        items = _items_desde_ia(respuesta_ia, productos_catalogo, db, hogar_id)
                        totales_ticket = respuesta_ia.get("totales")
                        cuadre_ticket = respuesta_ia.get("cuadre")
                        logger.info(
                            "Ticket analizado con Claude Vision: %d items detectados",
                            len(items),
                        )
                except Exception as e:
                    logger.error("Error con Claude Vision, usando Tesseract: %s", str(e))
                    items = None
            else:
                logger.warning("Claude OCR no disponible, usando Tesseract")

        # Fallback a Tesseract si Claude no funcionó (items is None), si está
        # deshabilitado, o si no reconoció ningún artículo (items == []): un
        # segundo intento solo puede añadir candidatos, y el usuario los revisa
        # antes de confirmar el ticket.
        if not items:
            if es_pdf and ruta_png_convertida is None:
                # Tesseract si necesita una imagen: se rasteriza la primera
                # pagina (ver _convertir_pdf_a_imagen).
                ruta_png_convertida = _convertir_pdf_a_imagen(tmp.name)
                if not ruta_png_convertida:
                    return APIResponse.error("err_procesando_ticket", 500)
                ruta_imagen = ruta_png_convertida
            try:
                texto_ocr = ticket_ocr.extraer_texto(ruta_imagen)
                proc = ProcesadorTicketsV2()
                items = proc.procesar_completo(texto_ocr, db, hogar_id)
                logger.info(
                    "Ticket analizado con Tesseract: %d lineas OCR, %d items detectados",
                    len(texto_ocr.splitlines()), len(items),
                )
            except Exception as e:
                logger.error("Error con Tesseract: %s", str(e))
                items = []

        # La cuota se consume solo si se llego a llamar al motor de nube: el
        # pipeline local (Tesseract) es gratuito y no tiene por que gastarla.
        if uso_motor_nube:
            cuota_ocr.incrementar(db, usuario_id)

        # Formatear respuesta para UI con sugerencias
        respuesta = crear_respuesta_usuario(items, db, hogar_id)

        # Totales del pie del ticket y su comprobación aritmética. Solo los da
        # el motor de vision; con Tesseract van a None y el frontend
        # simplemente no los muestra.
        if totales_ticket:
            respuesta["totales"] = totales_ticket
        if cuadre_ticket:
            respuesta["cuadre"] = cuadre_ticket
            if cuadre_ticket.get("comprobado") and not cuadre_ticket.get("cuadra"):
                respuesta.setdefault("advertencias", []).append({
                    "tipo": "descuadre",
                    "mensaje": (
                        "La suma de los artículos no coincide con el total del "
                        "ticket: revisa que no falte ninguno."
                    ),
                })

    except Exception as e:
        # No se devuelve str(e) al cliente: puede filtrar rutas de fichero
        # temporales o detalles internos de librerías (ver @manejo_errores,
        # que para el resto de endpoints ya evita esto con un mensaje
        # generico). Aqui se hacia una excepcion para dar una pista sobre
        # Tesseract, pero el detalle real solo debe ir al log del servidor.
        logging.getLogger(__name__).exception("Error analizando ticket")
        return APIResponse.error("err_interno_generico", 500)
    finally:
        os.unlink(tmp.name)
        if ruta_png_convertida and os.path.exists(ruta_png_convertida):
            os.unlink(ruta_png_convertida)

    return APIResponse.success(respuesta)


@bp.route("/confirmar", methods=["POST"])
@requerir_sesion
@manejo_errores
def confirmar_ticket():
    """Confirma los items de un ticket escaneado y los aplica al stock.

    Requiere permiso de 'editar' en la lista activa: sin esta comprobacion,
    sumar_stock()/crear_producto_nuevo() resolvian la lista de sesion sin
    verificar ningun permiso (a diferencia de todos los endpoints de
    productos.py), permitiendo a un usuario con acceso de solo lectura -o
    sin ningun acceso ya revocado- seguir modificando el stock de una lista
    ajena subiendo un ticket.
    """
    db = get_db()
    hogar_id = hogar_actual_con_permiso(db, session, nivel_requerido="editar")
    if not hogar_id:
        return APIResponse.no_permitido()

    datos = request.get_json(force=True) or {}
    items = datos.get("items") or []

    creados = 0
    actualizados = 0

    for item in items:
        # OJO: lo que llega aqui es JSON del cliente, NO la salida del motor de
        # OCR. El atacante controla cada campo, asi que se valida igual que en
        # POST /api/productos (M-18). Sin el tope de longitud se podia insertar
        # en `productos.nombre` una cadena de megabytes que luego se
        # concatenaba en el prompt de cada escaneo.
        nombre = (item.get("nombre") or "").strip()
        if not nombre:
            continue
        nombre = Validator.string_requerido(nombre, "nombre", 80)
        # cantidad_stock, no entero_no_negativo: este endpoint acepta unidades
        # de peso/volumen (ver _UNIDADES_VALIDAS), asi que "0,850 kg" es una
        # cantidad legitima. Con int() se truncaba a 0 y el articulo entraba al
        # stock vacio mientras la respuesta decia que se habia importado.
        cantidad = Validator.cantidad_stock(Validator.con_defecto(item, "cantidad", 1))
        unidad = (item.get("unidad") or "ud").strip().lower() or "ud"
        if unidad not in _UNIDADES_VALIDAS:
            unidad = "ud"

        precio_unitario = Validator.con_defecto(item, "precio_unitario", None)
        if precio_unitario is not None:
            try:
                precio_unitario = float(precio_unitario)
            except (TypeError, ValueError):
                # Antes esto llegaba crudo a registrar_precio, donde comparar
                # una cadena con 0 lanzaba TypeError -> 500 provocable.
                precio_unitario = None

        producto_id = item.get("producto_id")
        if producto_id:
            producto_id = int(producto_id)
            # El producto_id lo elige el cliente: hay que comprobar que
            # pertenece a ESTE hogar antes de usarlo. sumar_stock ya lo hacia,
            # pero registrar_precio no, y se acababan insertando filas de
            # historial_precios apuntando a productos de otros hogares.
            if not _producto_del_hogar(db, producto_id, hogar_id):
                categoria = item.get("categoria") or "Otros"
                producto_id = crear_producto_nuevo(db, nombre, categoria, cantidad, unidad, hogar_id=hogar_id)
                creados += 1
            else:
                sumar_stock(db, producto_id, cantidad, hogar_id)
                actualizados += 1
        else:
            categoria = item.get("categoria") or "Otros"
            producto_id = crear_producto_nuevo(db, nombre, categoria, cantidad, unidad, hogar_id=hogar_id)
            creados += 1

        registrar_precio(db, producto_id, hogar_id, precio_unitario)

    db.commit()
    return APIResponse.success({"creados": creados, "actualizados": actualizados})
