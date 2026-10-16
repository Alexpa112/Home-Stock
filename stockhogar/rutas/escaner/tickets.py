"""Rutas para escanear tickets de compra y volcarlos al stock."""
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from flask import Blueprint, request, session

from ...api import APIResponse, manejo_errores, requerir_sesion, cuerpo_json
from ...config import LIMITE_OCR_DIARIO
from ...db import get_db
from ...nucleo.red import ip_cliente, limite_por_ip
from ...translator import traducir
from ...integraciones import ticket_ocr
from ...servicios.ocr import cuota_ocr
from ...servicios.ocr import ProcesadorTicketsV2, crear_respuesta_usuario
from ...servicios.ocr.catalogo import catalogo_del_hogar as _catalogo_del_hogar
from ...servicios.ocr.claude_ocr import ClaudeOCR
from ...servicios.ocr.cuadre_ticket import cuadrar_con_total, extraer_total_impreso
from ...servicios.ocr.diccionario import identificar_articulo
from ...servicios.ocr.matcher_inteligente import MatcherInteligente
from ...servicios.ocr.validacion_importes import normalizar_importe
from ...utils import Validator, ValidationError
from ...utils.imagenes import imagen_demasiado_grande, validar_formato
from ...servicios.stock import crear_producto_nuevo, sumar_stock, hogar_actual_con_permiso, registrar_precio

bp = Blueprint("tickets", __name__, url_prefix="/api/tickets")

EXTENSIONES_PERMITIDAS = {"png", "jpg", "jpeg", "gif", "bmp", "webp", "heic", "heif", "pdf"}
TAMANO_MAXIMO_MB = 10

_UNIDADES_VALIDAS = ("ud", "kg", "g", "l", "ml")

# Por encima de esto un "precio unitario" es un error de lectura o un dato
# manipulado, no una compra domestica.
PRECIO_UNITARIO_MAXIMO = 100_000

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
    # Una linea mal formada no debe costar el ticket entero: esta funcion corre
    # dentro del try que cae a Tesseract, asi que cualquier excepcion aqui
    # descartaba TODOS los articulos que el modelo si habia leido bien.
    productos_ia = respuesta_ia.get("productos")
    if not isinstance(productos_ia, list):
        productos_ia = []
    for item in productos_ia:
        if not isinstance(item, dict):
            continue
        # Obtener nombre
        nombre = (item.get("nombre_ticket") or "").strip()
        if not nombre:
            nombre = (item.get("nombre") or "").strip()
        if not nombre:
            continue  # Saltar si no hay nombre

        nombre = nombre.title()
        nombre_ticket = nombre

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
        icono_dic = None

        if catalogado:
            nombre = catalogado["nombre"]
            categoria = catalogado["categoria"]
            confianza_match = 1.0
        else:
            # Producto nuevo para el hogar: el diccionario le da nombre limpio,
            # categoria e icono igual que en el pipeline local, para que los dos
            # motores devuelvan lo mismo ante el mismo ticket.
            ident = identificar_articulo(nombre)
            categoria = (ident.categoria if ident else None) or matcher.deducir_categoria(nombre) or "Otros"
            icono_dic = ident.icono if ident else None
            if ident is not None:
                if ident.fuente == "catalogo":
                    nombre = ident.nombre
                elif ident.nombre_limpio:
                    nombre = ident.nombre_limpio
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
        # normalizar_importe (no el valor crudo del modelo): aunque el esquema
        # pide numeros y _procesar_respuesta ya los normaliza, un importe que
        # llegue como cadena hacia estallar el '>' de aqui con TypeError. Y como
        # esta funcion se llama dentro del try que cae a Tesseract, el ticket
        # ENTERO se perdia en silencio por una sola linea mal tipada.
        precio_unitario = normalizar_importe(item.get("precio_unitario"))
        precio_total = normalizar_importe(item.get("precio_total"))
        confianza_lectura = item.get("confianza")

        # Se valida el precio UNITARIO: el rango de matcher.validar_precio es
        # por unidad, asi que comparar el total de la linea marcaba como anomalo
        # cualquier multipack legitimo ("AGUA 1,5L x6 - 4,50€").
        if precio_unitario is not None and precio_unitario > 0:
            precio_valido, razon_precio = matcher.validar_precio(precio_unitario, categoria)
        elif precio_total is not None and precio_total > 0:
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
            "nombre_ticket": nombre_ticket,
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
            "icono": catalogado.get("icono") if catalogado else icono_dic,
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
            # -scale-to acota el lado largo: con "-r 300" un PDF diminuto con una pagina de
            # 4500x4500 pt gastaba 1,4 GB y 18 s (bomba de descompresion).
            ["pdftoppm", "-png", "-scale-to", "3000", "-singlefile", ruta_pdf, prefijo],
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


class _Rechazo(Exception):
    """Corta el analisis con una respuesta ya construida (validacion, permiso, formato...)."""

    def __init__(self, respuesta):
        super().__init__("rechazo")
        self.respuesta = respuesta


def _comprobar_peticion(archivo, db, usuario_id):
    """Validaciones previas a gastar nada: fichero, permiso de hogar, cuotas y tamano.
    Devuelve el hogar_id o lanza _Rechazo."""
    if archivo is None or archivo.filename == "":
        raise _Rechazo(APIResponse.validacion("err_sin_imagen"))
    if not _extension_permitida(archivo.filename):
        raise _Rechazo(APIResponse.validacion("err_formato_no_permitido"))

    # A-1: hasta ahora esta ruta no comprobaba NINGUN permiso de hogar, y leia
    # el catalogo `productos` entero de la instalacion. Se exige 'ver' y el
    # hogar resultante es el que filtra el catalogo mas abajo.
    hogar_id = hogar_actual_con_permiso(db, session, nivel_requerido="ver")
    if hogar_id is None:
        raise _Rechazo(APIResponse.no_permitido())

    # A-6: la cuota diaria protegia /api/ocr/procesar-ticket, que nadie
    # llamaba, mientras esta ruta -- la que usa el frontend -- no tenia
    # ninguna. Se comprueba antes de gastar nada.
    if cuota_ocr.uso_hoy(db, usuario_id) >= LIMITE_OCR_DIARIO:
        raise _Rechazo(APIResponse.error("err_limite_ocr_diario", 429))
    if limite_por_ip(f"analizar_ticket:{ip_cliente()}", 30, 60 * 60):
        raise _Rechazo(APIResponse.error("err_demasiadas_peticiones", 429))

    archivo.seek(0, os.SEEK_END)
    tamano_bytes = archivo.tell()
    archivo.seek(0)
    if tamano_bytes > TAMANO_MAXIMO_MB * 1024 * 1024:
        raise _Rechazo(APIResponse.validacion(
            traducir("err_archivo_muy_grande").replace("{mb}", str(TAMANO_MAXIMO_MB))
        ))
    return hogar_id


def _validar_y_preparar_imagen(ruta, sufijo, a_borrar):
    """Comprueba que el fichero es de verdad lo que dice su extension y devuelve la ruta de la
    imagen a leer (la convertida si era HEIC). Las rutas temporales que cree se anaden a `a_borrar`."""
    if sufijo in (".heic", ".heif"):
        convertida = _convertir_heic_a_imagen(ruta)
        if not convertida:
            # Sin el binario es un fallo del servidor (500); con el binario
            # presente, el archivo es el que no se puede leer (400): no es
            # un error del servidor y no debe contarse como tal.
            if shutil.which("heif-convert"):
                raise _Rechazo(APIResponse.validacion("err_formato_no_permitido"))
            raise _Rechazo(APIResponse.error("err_procesando_ticket", 500))
        a_borrar.append(convertida)
        if imagen_demasiado_grande(convertida):
            raise _Rechazo(APIResponse.validacion("err_formato_no_permitido"))
        return convertida

    if sufijo == ".pdf":
        # El PDF NO se rasteriza aqui: Claude lee el documento completo,
        # mientras que pdftoppm -singlefile solo saca la primera pagina y
        # una factura de varias hojas perdia todos los articulos de la
        # segunda en adelante. La conversion se hace mas abajo, y solo si
        # hay que recurrir a Tesseract. Validacion de contenido real (S-16):
        # sin convertir hay que comprobar la firma a mano.
        with open(ruta, "rb") as f:
            if not f.read(5).startswith(b"%PDF-"):
                raise _Rechazo(APIResponse.validacion("err_formato_no_permitido"))
        return ruta

    # Validacion de contenido real (S-16). No se recodifica (a diferencia de los recibos de gastos,
    # que se guardan a largo plazo): esta imagen es efimera, se descarta tras el OCR, y
    # recodificarla podria degradar la calidad que necesita el OCR.
    with open(ruta, "rb") as f:
        error_validacion = validar_formato(f.read(), sufijo.lstrip("."))
    if error_validacion:
        raise _Rechazo(APIResponse.validacion(error_validacion))
    return ruta


def _leer_con_claude(ruta_imagen, es_pdf, productos_catalogo, db, hogar_id):
    """Claude Vision. Devuelve (items, totales, cuadre, llamo_a_la_nube); items es None si no
    esta disponible o falla, y quien llama recurre entonces al OCR local."""
    logger = logging.getLogger(__name__)
    claude = ClaudeOCR()
    if not claude.disponible():
        logger.warning("Claude OCR no disponible, usando Tesseract")
        return None, None, None, False
    llamo = False
    try:
        with open(ruta_imagen, "rb") as f:
            imagen_bytes = f.read()
        llamo = True
        respuesta_ia = claude.procesar(
            imagen_bytes, productos_catalogo, mime="application/pdf" if es_pdf else None,
        )
        if respuesta_ia is None:
            return None, None, None, llamo
        items = _items_desde_ia(respuesta_ia, productos_catalogo, db, hogar_id)
        logger.info("Ticket analizado con Claude Vision: %d items detectados", len(items))
        return items, respuesta_ia.get("totales"), respuesta_ia.get("cuadre"), llamo
    except Exception as e:
        logger.error("Error con Claude Vision, usando Tesseract: %s", str(e))
        return None, None, None, llamo


def _leer_con_ocr_local(ruta_imagen, ruta_original, es_pdf, db, hogar_id, a_borrar):
    """RapidOCR/Tesseract + parser + dictionary + cuadre con el TOTAL impreso. Devuelve
    (items, totales, cuadre)."""
    logger = logging.getLogger(__name__)
    if es_pdf and ruta_imagen == ruta_original:
        # El OCR local necesita una imagen: se rasteriza la primera pagina (ver _convertir_pdf_a_imagen).
        convertida = _convertir_pdf_a_imagen(ruta_original)
        if not convertida:
            if shutil.which("pdftoppm"):
                raise _Rechazo(APIResponse.validacion("err_formato_no_permitido"))
            raise _Rechazo(APIResponse.error("err_procesando_ticket", 500))
        a_borrar.append(convertida)
        ruta_imagen = convertida
    try:
        texto_ocr = ticket_ocr.extraer_texto(ruta_imagen)
        items = ProcesadorTicketsV2().procesar_completo(texto_ocr, db, hogar_id)
        # El TOTAL impreso comprueba la lectura (y corrige lo que solo
        # tiene una solucion): ver servicios/ocr/cuadre_ticket.py.
        items, cuadre = cuadrar_con_total(items, texto_ocr)
        totales = {"total": extraer_total_impreso(texto_ocr)} if cuadre else None
        logger.info(
            "Ticket analizado con Tesseract: %d lineas OCR, %d items detectados",
            len(texto_ocr.splitlines()), len(items),
        )
        return items, totales, cuadre
    except Exception as e:
        logger.error("Error con Tesseract: %s", str(e))
        return [], None, None


def _construir_respuesta(items, totales, cuadre, db, hogar_id):
    """Respuesta para la interfaz: articulos con sugerencias + totales y aviso de descuadre."""
    respuesta = crear_respuesta_usuario(items, db, hogar_id)
    # Totales del pie del ticket y su comprobacion aritmetica. Con Claude vienen del modelo; con el
    # lector local, del TOTAL impreso; si no hay, el frontend simplemente no los muestra.
    if totales:
        respuesta["totales"] = totales
    if cuadre:
        respuesta["cuadre"] = cuadre
        if cuadre.get("comprobado") and not cuadre.get("cuadra"):
            respuesta.setdefault("advertencias", []).append({
                "tipo": "descuadre",
                "suma": cuadre.get("suma_articulos"),
                "total": cuadre.get("total_ticket"),
                "mensaje": (
                    "La suma de los artículos no coincide con el total del "
                    "ticket: revisa que no falte ninguno."
                ),
            })
    return respuesta


@bp.route("/analizar", methods=["POST"])
@requerir_sesion
@manejo_errores
def analizar_ticket():
    db = get_db()
    usuario_id = session.get("usuario_id")
    archivo = request.files.get("foto")
    a_borrar = []
    try:
        hogar_id = _comprobar_peticion(archivo, db, usuario_id)

        sufijo = Path(archivo.filename).suffix.lower() or ".jpg"
        tmp = tempfile.NamedTemporaryFile(suffix=sufijo, delete=False)
        tmp.close()
        a_borrar.append(tmp.name)
        archivo.save(tmp.name)

        es_pdf = sufijo == ".pdf"
        ruta_imagen = _validar_y_preparar_imagen(tmp.name, sufijo, a_borrar)

        prefiere_ocr_local = bool(
            db.execute("SELECT usuario_ocr_local FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()["usuario_ocr_local"]
        )

        # El catalogo SOLO del hogar activo (A-1): sin filtrar por hogar, el id devuelto por el
        # modelo se validaba contra el catalogo global y se enviaban a Anthropic nombres de
        # producto de todos los hogares, cosa que la politica de privacidad no declaraba.
        productos_catalogo = _catalogo_del_hogar(db, hogar_id)

        # Motor principal: Claude Vision (la mejor vision disponible), salvo opt-out del usuario.
        items = totales = cuadre = None
        uso_motor_nube = False
        if not prefiere_ocr_local:
            items, totales, cuadre, uso_motor_nube = _leer_con_claude(
                ruta_imagen, es_pdf, productos_catalogo, db, hogar_id
            )

        # Fallback al lector local si Claude no funciono (items is None), esta deshabilitado, o no
        # reconocio ningun articulo (items == []): un segundo intento solo puede anadir candidatos,
        # y el usuario los revisa antes de confirmar el ticket.
        if not items:
            items, totales, cuadre = _leer_con_ocr_local(ruta_imagen, tmp.name, es_pdf, db, hogar_id, a_borrar)

        # La cuota se consume solo si se llego a llamar al motor de nube: el
        # pipeline local es gratuito y no tiene por que gastarla.
        if uso_motor_nube:
            cuota_ocr.incrementar(db, usuario_id)

        respuesta = _construir_respuesta(items, totales, cuadre, db, hogar_id)
    except _Rechazo as r:
        return r.respuesta
    except Exception:
        # No se devuelve str(e) al cliente: puede filtrar rutas de fichero temporales o detalles
        # internos de librerias; el detalle real solo va al log del servidor.
        logging.getLogger(__name__).exception("Error analizando ticket")
        return APIResponse.error("err_interno_generico", 500)
    finally:
        for ruta in a_borrar:
            if os.path.exists(ruta):
                os.unlink(ruta)

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

    datos = cuerpo_json()
    if not isinstance(datos, dict):
        raise ValidationError("el cuerpo de la peticion debe ser un objeto JSON")
    items = datos.get("items") or []
    if not isinstance(items, list):
        raise ValidationError("items debe ser una lista")
    if len(items) > 300:  # un ticket real no llega ni a 100 lineas
        raise ValidationError("Demasiados artículos en un ticket")

    creados = 0
    actualizados = 0

    for item in items:
        if not isinstance(item, dict):
            raise ValidationError("cada item debe ser un objeto JSON")
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
            # float("nan") / float("inf") (el json de Python los acepta) pasan
            # el "> 0" de registrar_precio y acababan en historial_precios.
            if precio_unitario is not None and not (0 < precio_unitario <= PRECIO_UNITARIO_MAXIMO):
                precio_unitario = None

        producto_id = item.get("producto_id")
        if producto_id:
            try:
                producto_id = int(producto_id)
            except (TypeError, ValueError):
                raise ValidationError("producto_id debe ser un número entero")
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
