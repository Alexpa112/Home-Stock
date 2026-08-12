"""Catalogo de productos visible para un hogar concreto.

Punto unico desde el que el escaner de tickets lee `productos`. Existe porque
esa tabla NO tiene columna de hogar (el aislamiento vive en `stock_hogar`) y
habia cuatro sitios distintos consultandola sin filtrar -- las unicas consultas
de todo el backend que lo hacian, ver hallazgo A-1 de la auditoria 2026-08.

Que rompia:

- El id que devuelve el modelo se validaba contra el catalogo global, asi que
  un id de OTRO hogar pasaba la validacion y su nombre acababa en la respuesta
  HTTP (claude_ocr._normalizar_producto_id).
- El matcher local publicaba hasta 3 "alternativas" por linea con nombres de
  cualquier hogar, asi que el opt-out de OCR en la nube NO cerraba la fuga.
- Se enviaba a Anthropic la lista completa de nombres de producto de toda la
  instalacion en cada escaneo de cualquier usuario.

Teniendolo en un solo sitio, cualquier consumidor nuevo hereda el filtro en vez
de reintroducir la fuga.
"""

# Tope de entradas enviadas al prompt del modelo y usadas por el matcher. Un
# catalogo sin techo permitia una denegacion de servicio persistente: bastaba
# insertar un nombre de varios megabytes (confirmar_ticket no acotaba la
# longitud, hallazgo M-18) para que toda llamada excediese el contexto.
MAX_ENTRADAS_CATALOGO = 2000

# Longitud maxima por nombre al construir el prompt, por el mismo motivo.
MAX_LONGITUD_NOMBRE = 80


def catalogo_del_hogar(db, hogar_id):
    """Devuelve [{id, nombre, categoria, icono}] de los productos del hogar.

    El JOIN con `stock_hogar` es el mismo que usa el resto del backend
    (productos.py, la exportacion RGPD de auth.py). Estilo Oracle-like de
    joins implicitos, como el resto del repo.
    """
    if hogar_id is None:
        return []
    filas = db.execute(
        "SELECT p.id, p.nombre, p.categoria, p.icono "
        "FROM productos p, stock_hogar sh "
        "WHERE sh.producto_id = p.id AND sh.hogar_id = ? "
        "ORDER BY p.nombre LIMIT ?",
        (hogar_id, MAX_ENTRADAS_CATALOGO),
    ).fetchall()
    return [dict(f) for f in filas]
