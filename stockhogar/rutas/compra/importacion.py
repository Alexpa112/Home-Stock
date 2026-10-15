"""Exportacion e importacion CSV de la lista de la compra."""
from .blueprint import bp
from .lista import anadir_o_sumar_articulo, resolver_hogar_id
import io
from flask import Response, request, session
from ...api import APIResponse, manejo_errores, requerir_sesion
from ...db import ahora, get_db
from ...utils.csv_seguro import EscritorCsvSeguro, desproteger, leer_csv_subido
from ..hogar.hogares import _usuario_tiene_permiso


CABECERAS_CSV_LISTA = ["nombre", "categoria", "unidad", "cantidad", "sub_descripcion"]


MAX_FILAS_IMPORTACION = 500


@bp.route("/exportar", methods=["GET"])
@requerir_sesion
@manejo_errores
def exportar_lista_csv():
    """Exporta los artículos pendientes de la lista activa a CSV (P-09)."""
    db = get_db()
    hogar_id = resolver_hogar_id(db, session)
    if not hogar_id:
        return APIResponse.error("err_no_hay_hogar_activo", 400)

    permiso = _usuario_tiene_permiso(db, hogar_id, session.get("usuario_id"))
    if not permiso:
        return APIResponse.no_permitido()

    filas = db.execute(
        "SELECT nombre, categoria, unidad, cantidad, sub_descripcion FROM articulos_compra "
        "WHERE activo = 1 AND hogar_id = ? ORDER BY categoria, LOWER(nombre)",
        (hogar_id,),
    ).fetchall()

    buffer = io.StringIO()
    writer = EscritorCsvSeguro(buffer)
    writer.writerow(CABECERAS_CSV_LISTA)
    for fila in filas:
        writer.writerow([
            fila["nombre"], fila["categoria"], fila["unidad"], fila["cantidad"], fila["sub_descripcion"] or "",
        ])

    contenido = buffer.getvalue().encode("utf-8-sig")
    nombre_fichero = f"lista_compra_{ahora()[:10]}.csv"
    return Response(
        contenido,
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{nombre_fichero}"'},
    )


@bp.route("/importar", methods=["POST"])
@requerir_sesion
@manejo_errores
def importar_lista_csv():
    """Importa un CSV con el mismo formato de /exportar (P-09): cada fila se
    añade o suma a la lista activa igual que anadir_o_sumar_articulo."""
    db = get_db()
    usuario_id = session.get("usuario_id")
    hogar_id = resolver_hogar_id(db, session)
    if not hogar_id:
        return APIResponse.error("err_no_hay_hogar_activo", 400)

    permiso = _usuario_tiene_permiso(db, hogar_id, usuario_id, nivel_requerido="editar")
    if not permiso or (permiso != "propietario" and permiso != "editar"):
        return APIResponse.no_permitido()

    filas = leer_csv_subido(request.files, MAX_FILAS_IMPORTACION)
    if filas is None:
        return APIResponse.validacion("err_sin_fichero")

    anadidos = 0
    for fila in filas:
        nombre = desproteger((fila.get("nombre") or "").strip())[:100]
        if not nombre:
            continue
        try:
            cantidad = max(1, int(fila.get("cantidad") or 1))
        except (TypeError, ValueError):
            cantidad = 1
        anadir_o_sumar_articulo(
            db, hogar_id, nombre, cantidad=cantidad,
            categoria=fila.get("categoria"), unidad=fila.get("unidad"),
            sub_descripcion=fila.get("sub_descripcion"),
        )
        anadidos += 1

    return APIResponse.success({"anadidos": anadidos})
