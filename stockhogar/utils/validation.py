"""Validación centralizada y reutilizable."""
import re
from typing import Any, Optional

_RE_COLOR_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


class ValidationError(ValueError):
    """Error de validación personalizado."""
    pass


class Validator:
    """Sistema centralizado de validación."""

    @staticmethod
    def con_defecto(datos: dict, clave: str, defecto: Any) -> Any:
        """Devuelve datos[clave] si viene informado (ni ausente, ni None, ni
        cadena vacía); si no, devuelve defecto. A diferencia de dict.get(clave,
        defecto), también aplica el defecto cuando la clave SÍ está presente
        pero llega a None/'' (input dejado en blanco por el usuario), sin
        pisar valores válidos como 0."""
        valor = datos.get(clave)
        if valor is None or valor == "":
            return defecto
        return valor

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
    def entero_minimo(valor: Any, nombre_campo: str, minimo: int = 1, maximo: int = 100_000) -> int:
        """Valida que sea entero y lo fuerza al rango [minimo, maximo] si se sale.
        El tope superior evita cantidades absurdas (p.ej. un cliente mandando
        999999999999) sin necesidad de rechazar la petición con un error."""
        try:
            numero = int(valor)
        except (TypeError, ValueError) as e:
            raise ValidationError(f"La {nombre_campo} debe ser un número entero") from e
        return max(minimo, min(numero, maximo))

    @staticmethod
    def decimal_positivo(valor: Any, nombre_campo: str, maximo: float = 1_000_000) -> float:
        """Valida un importe monetario: número positivo, redondeado a 2
        decimales, con un tope superior para evitar importes absurdos."""
        try:
            numero = round(float(valor), 2)
        except (TypeError, ValueError) as e:
            raise ValidationError(f"El {nombre_campo} debe ser un número") from e
        if numero <= 0:
            raise ValidationError(f"El {nombre_campo} debe ser mayor que 0")
        if numero > maximo:
            raise ValidationError(f"El {nombre_campo} no puede superar {maximo}")
        return numero

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
    def color_hex(valor: Optional[str], default: str) -> str:
        """Valida que sea un color hexadecimal de 6 dígitos (#RRGGBB). Si no
        viene informado devuelve el default; si viene pero no tiene formato
        válido, rechaza en vez de guardar basura que luego rompa la UI."""
        if not valor:
            return default
        valor = str(valor).strip()
        if not _RE_COLOR_HEX.match(valor):
            raise ValidationError("El color debe tener formato hexadecimal, p.ej. #B5551A")
        return valor

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
