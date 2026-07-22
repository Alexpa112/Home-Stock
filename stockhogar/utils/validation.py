"""Validación centralizada y reutilizable."""
from typing import Any, Optional


class ValidationError(ValueError):
    """Error de validación personalizado."""
    pass


class Validator:
    """Sistema centralizado de validación."""

    @staticmethod
    def entero_no_negativo(valor: Any, nombre_campo: str) -> int:
        """Valida que sea entero no negativo."""
        try:
            numero = int(valor)
        except (TypeError, ValueError) as e:
            raise ValidationError(f"La {nombre_campo} debe ser un número entero") from e
        if numero < 0:
            raise ValidationError(f"La {nombre_campo} no puede ser negativa")
        return numero

    @staticmethod
    def entero_minimo(valor: Any, nombre_campo: str, minimo: int = 1) -> int:
        """Valida que sea entero y lo fuerza al mínimo indicado si es menor."""
        try:
            numero = int(valor)
        except (TypeError, ValueError) as e:
            raise ValidationError(f"La {nombre_campo} debe ser un número entero") from e
        return max(minimo, numero)

    @staticmethod
    def string_requerido(valor: Any, nombre_campo: str, max_len: int = 255) -> str:
        """Valida string no vacío."""
        if not isinstance(valor, str):
            valor = str(valor) if valor else ""
        valor = valor.strip()
        if not valor:
            raise ValidationError(f"El {nombre_campo} es obligatorio")
        if len(valor) > max_len:
            raise ValidationError(f"El {nombre_campo} no puede exceder {max_len} caracteres")
        return valor

    @staticmethod
    def string_opcional(valor: Optional[str], default: str = "", max_len: int = 255) -> str:
        """Valida string opcional con valor por defecto."""
        if not valor:
            return default
        valor = str(valor).strip()
        if len(valor) > max_len:
            raise ValidationError(f"El campo no puede exceder {max_len} caracteres")
        return valor or default

    @staticmethod
    def json_de_request(request_data: Any, required_fields: list = None, **defaults) -> dict:
        """Extrae y valida datos JSON de request."""
        datos = request_data or {}
        if required_fields:
            for campo in required_fields:
                if campo not in datos or not datos[campo]:
                    raise ValidationError(f"El campo '{campo}' es obligatorio")
        # Aplicar defaults
        for key, val in defaults.items():
            if key not in datos:
                datos[key] = val
        return datos
