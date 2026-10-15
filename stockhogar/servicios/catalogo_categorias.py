"""Logica comun de los dos catalogos de categorias (productos y gastos).

Ambos tienen la misma forma (tabla con `nombre` e `icono`, categorias de serie que nadie borra,
una categoria comodin, y no se puede borrar una que este en uso) y solo cambian la tabla, la
tabla donde se usan y los textos. Los nombres de tabla son literales fijos de este proyecto,
nunca datos del usuario."""
from dataclasses import dataclass
from typing import Tuple

from flask import jsonify, session

from ..api import APIResponse, cuerpo_json
from ..db import get_db
from ..translator import traducir
from ..utils import DataConverter, Validator


@dataclass(frozen=True)
class CatalogoCategorias:
    tabla: str                 # "categorias" | "categorias_gasto"
    tabla_uso: str             # donde se referencia por nombre: "productos" | "gastos"
    comodin: str               # categoria por defecto, no borrable
    de_serie: Tuple[str, ...]  # nombres sembrados, no borrables
    clave_en_uso: str          # clave de traduccion del aviso "en uso"

    def listar(self):
        filas = get_db().execute(f"SELECT * FROM {self.tabla} ORDER BY LOWER(nombre)").fetchall()  # nosec B608 - tabla literal fija
        return APIResponse.success([DataConverter.categoria_to_dict(f) for f in filas])

    def _sin_permiso_de_edicion(self, db):
        from .stock import hogar_actual_con_permiso  # import local: servicios.stock importa rutas
        return not hogar_actual_con_permiso(db, session, nivel_requerido="editar")

    def crear(self):
        db = get_db()
        if self._sin_permiso_de_edicion(db):
            return APIResponse.no_permitido()
        datos = cuerpo_json()
        nombre = Validator.string_requerido(datos.get("nombre"), "nombre", 50)
        icono = Validator.string_opcional(datos.get("icono"), "h-folder", 30)

        if db.execute(
            f"SELECT id FROM {self.tabla} WHERE LOWER(nombre) = LOWER(?)", (nombre,)  # nosec B608
        ).fetchone():
            return APIResponse.error("err_categoria_duplicada", 400)

        nueva_id = db.execute(
            f"INSERT INTO {self.tabla} (nombre, icono) VALUES (?, ?) RETURNING id", (nombre, icono)  # nosec B608
        ).fetchone()["id"]
        db.commit()
        fila = db.execute(f"SELECT * FROM {self.tabla} WHERE id = ?", (nueva_id,)).fetchone()  # nosec B608
        return APIResponse.success(DataConverter.categoria_to_dict(fila), 201)

    def borrar(self, categoria_id):
        db = get_db()
        if self._sin_permiso_de_edicion(db):
            return APIResponse.no_permitido()
        fila = db.execute(f"SELECT * FROM {self.tabla} WHERE id = ?", (categoria_id,)).fetchone()  # nosec B608
        if not fila:
            return APIResponse.no_encontrado("recurso_categoria")
        # Las categorias de serie son de todos los hogares: nadie las borra.
        if fila["nombre"] == self.comodin or fila["nombre"] in self.de_serie:
            mensaje = traducir("err_no_borrar_categoria_defecto").replace("{nombre}", self.comodin)
            return jsonify({"error": mensaje}), 400

        en_uso = db.execute(
            f"SELECT COUNT(*) AS n FROM {self.tabla_uso} WHERE categoria = ?", (fila["nombre"],)  # nosec B608
        ).fetchone()["n"]
        if en_uso:
            return APIResponse.error(traducir(self.clave_en_uso).replace("{en_uso}", str(en_uso)), 409)

        db.execute(f"DELETE FROM {self.tabla} WHERE id = ?", (categoria_id,))  # nosec B608
        db.commit()
        return APIResponse.success()
