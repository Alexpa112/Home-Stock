"""Conversión centralizada de tipos de datos."""
from datetime import datetime
from typing import Any, Dict, Optional


class DataConverter:
    """Convierte filas de BD a dicts JSON optimizados."""

    @staticmethod
    def safe_field(row: Dict, key: str, default: Any = None) -> Any:
        """Obtiene campo seguro de fila, evitando KeyError."""
        try:
            return row[key] if key in row.keys() else default
        except (TypeError, AttributeError):
            return default

    @staticmethod
    def calcular_dias_desde(fecha_iso: Optional[str], dias_comparacion: int = 0) -> bool:
        """Calcula si han pasado X días desde una fecha."""
        if not fecha_iso or not dias_comparacion:
            return False
        try:
            fecha = datetime.fromisoformat(fecha_iso)
            dias_transcurridos = (datetime.now() - fecha).days
            return dias_transcurridos >= dias_comparacion
        except (ValueError, TypeError):
            return False

    @staticmethod
    def producto_to_dict(row: Dict, dias_aviso_defecto: int = 30) -> Dict:
        """Convierte fila de producto a dict JSON."""
        dias_aviso = DataConverter.safe_field(row, "dias_aviso", dias_aviso_defecto)
        fecha_actualizacion = DataConverter.safe_field(row, "fecha_actualizacion")

        return {
            "id": row["id"],
            "nombre": row["nombre"],
            "categoria": row["categoria"],
            "icono": DataConverter.safe_field(row, "icono"),
            "cantidad": row["cantidad"],
            "unidad": row["unidad"],
            "stock_minimo": row["stock_minimo"],
            "fecha_creacion": DataConverter.safe_field(row, "fecha_creacion"),
            "fecha_actualizacion": fecha_actualizacion,
            "dias_aviso": dias_aviso,
            "revisar_caducidad": DataConverter.calcular_dias_desde(fecha_actualizacion, dias_aviso),
        }

    @staticmethod
    def lista_to_dict(row: Dict, usuario_id: Optional[int] = None, include_detalles: bool = False) -> Dict:
        """Convierte fila de lista a dict JSON."""
        color = DataConverter.safe_field(row, "color", "#B5551A")

        data = {
            "id": row["id"],
            "nombre": row["nombre"],
            "descripcion": row["descripcion"],
            "icono": row["icono"],
            "color": color,
            "privada": bool(row["privada"]),
            "usuario_propietario_id": row["usuario_propietario_id"],
            "fecha_creacion": row["fecha_creacion"],
            "fecha_actualizacion": row["fecha_actualizacion"],
        }

        if usuario_id and include_detalles:
            if row["usuario_propietario_id"] == usuario_id:
                data["mi_rol"] = "propietario"
            else:
                data["mi_rol"] = DataConverter.safe_field(row, "nivel", "ninguno")

        return data

    @staticmethod
    def articulo_lista_to_dict(row: Dict) -> Dict:
        """Convierte fila de artículo de lista a dict JSON."""
        return {
            "id": row["id"],
            "hogar_id": row["hogar_id"],
            "nombre": row["nombre"],
            "cantidad": row["cantidad"],
            "unidad": DataConverter.safe_field(row, "unidad", "ud"),
            "categoria": DataConverter.safe_field(row, "categoria"),
            "icono": DataConverter.safe_field(row, "icono"),
            "sub_descripcion": DataConverter.safe_field(row, "sub_descripcion"),
            "articulo_personalizado_id": DataConverter.safe_field(row, "articulo_personalizado_id"),
            "completado": bool(DataConverter.safe_field(row, "completado", 0)),
            "origen": DataConverter.safe_field(row, "origen", "manual"),
            "fecha_creacion": DataConverter.safe_field(row, "fecha_creacion"),
            "fecha_completado": DataConverter.safe_field(row, "fecha_completado"),
        }

    @staticmethod
    def categoria_to_dict(row: Dict) -> Dict:
        """Convierte fila de categoría a dict JSON."""
        return {
            "id": row["id"],
            "nombre": row["nombre"],
            "icono": row["icono"],
        }

