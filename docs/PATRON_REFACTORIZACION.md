# 🎨 Patrón de Refactorización - Todas las Rutas

**Nota (verificado en el código actual): la Fase 2 ya está completa — todas
las rutas (incluidas `auth.py`, `historial.py`, `tickets.py`, `ocr_tickets.py`,
`paginas.py`) usan ya `@requerir_sesion`/`@manejo_errores`. Esta guía se
conserva como referencia del patrón a seguir para rutas nuevas, no como TODO
pendiente.**

## Paso 1: Actualiza los Imports

**ANTES**:
```python
from flask import Blueprint, jsonify, request, session
from ..db import get_db
```

**DESPUÉS**:
```python
from flask import Blueprint, request, session
from ..api import APIResponse, manejo_errores, requerir_sesion
from ..db import get_db
from ..utils import Validator, DataConverter
```

---

## Paso 2: Añade Decoradores a TODOS los Endpoints

**ANTES**:
```python
@bp.route("", methods=["GET"])
def listar_algo():
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({"error": "No autorizado"}), 401
```

**DESPUÉS**:
```python
@bp.route("", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_algo():
    usuario_id = session.get("usuario_id")
```

---

## Paso 3: Reemplaza Validaciones

**ANTES**:
```python
nombre = (datos.get("nombre") or "").strip()
if not nombre:
    return jsonify({"error": "El nombre es obligatorio"}), 400
```

**DESPUÉS**:
```python
nombre = Validator.string_requerido(datos.get("nombre"), "nombre", 50)
```

**Métodos disponibles**:
```python
Validator.string_requerido(valor, "nombre", max_len=100)
Validator.string_opcional(valor, default="", max_len=50)
Validator.entero_no_negativo(valor, "cantidad")
```

---

## Paso 4: Reemplaza jsonify() por APIResponse

**ANTES**:
```python
return jsonify([...datos...])
return jsonify({"error": "No encontrado"}), 404
return "", 204
```

**DESPUÉS**:
```python
return APIResponse.success([...datos...])
return APIResponse.no_encontrado("Recurso")
return APIResponse.success()
```

**Métodos disponibles**:
```python
APIResponse.success(datos, 200)              # Con status code
APIResponse.success(datos)                   # Default 200
APIResponse.error("Mensaje", 400)            # Error genérico
APIResponse.validacion("Mensaje")            # 400
APIResponse.no_autorizado()                  # 401
APIResponse.no_encontrado("Recurso")         # 404
APIResponse.no_permitido("Mensaje opcional") # 403
```

---

## Paso 5: Reemplaza row_to_dict() por DataConverter

**ANTES**:
```python
def mi_a_dict(row):
    return {
        "id": row["id"],
        "nombre": row["nombre"],
        # ... 10 líneas más
    }

# En endpoint:
return jsonify([mi_a_dict(f) for f in filas])
```

**DESPUÉS**:
```python
# En endpoint:
return APIResponse.success([DataConverter.producto_to_dict(f) for f in filas])
```

**Convertidores disponibles**:
```python
DataConverter.producto_to_dict(row)
DataConverter.categoria_to_dict(row)
DataConverter.espacio_to_dict(row)
DataConverter.lista_to_dict(row, usuario_id, include_detalles)
DataConverter.articulo_lista_to_dict(row)
```

---

## Paso 6: Simplifica Lógica de Errores

**ANTES**:
```python
try:
    # 50 líneas de lógica
except ValueError as e:
    return jsonify({"error": str(e)}), 400
except Exception as e:
    return jsonify({"error": str(e)}), 500
```

**DESPUÉS**:
```python
@manejo_errores
def mi_endpoint():
    # Lógica limpia, sin try-catch
    # ValidationError se convierte en 400 automáticamente
```

---

## Ejemplo Completo

### ANTES (20 líneas + duplicación):
```python
@bp.route("", methods=["POST"])
def crear_categoria():
    datos = request.get_json(force=True) or {}
    nombre = (datos.get("nombre") or "").strip()
    icono = (datos.get("icono") or "🗂️").strip()
    
    if not nombre:
        return jsonify({"error": "El nombre es obligatorio"}), 400
    
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO categorias (nombre, icono) VALUES (?, ?)",
            (nombre, icono)
        )
        db.commit()
        fila = db.execute("SELECT * FROM categorias WHERE id = ?", (cur.lastrowid,)).fetchone()
        
        def categoria_a_dict(row):
            return {"id": row["id"], "nombre": row["nombre"], "icono": row["icono"]}
        
        return jsonify(categoria_a_dict(fila)), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

### DESPUÉS (8 líneas, cero duplicación):
```python
@bp.route("", methods=["POST"])
@requerir_sesion
@manejo_errores
def crear_categoria():
    datos = request.get_json(force=True) or {}
    nombre = Validator.string_requerido(datos.get("nombre"), "nombre", 50)
    icono = Validator.string_opcional(datos.get("icono"), "🗂️", 10)
    
    db = get_db()
    cur = db.execute("INSERT INTO categorias (nombre, icono) VALUES (?, ?)", (nombre, icono))
    db.commit()
    fila = db.execute("SELECT * FROM categorias WHERE id = ?", (cur.lastrowid,)).fetchone()
    return APIResponse.success(DataConverter.categoria_to_dict(fila), 201)
```

---

## Rutas Refactorizadas

Todas las rutas de `stockhogar/rutas/` siguen ya este patrón (`@requerir_sesion`,
`@manejo_errores`, `Validator`, `DataConverter`/`APIResponse`), incluidas las
que en su día quedaron pendientes: `auth.py`, `historial.py`, `tickets.py`,
`ocr_tickets.py`, `paginas.py`.

---

## Checklist para Refactorizar una Ruta

- [ ] Actualizar imports (copiar bloque de arriba)
- [ ] Añadir `@requerir_sesion` + `@manejo_errores` a TODOS los endpoints
- [ ] Reemplazar `(datos.get(...) or "").strip()` por `Validator.string_*`
- [ ] Reemplazar `int(datos.get(...))` por `Validator.entero_no_negativo`
- [ ] Reemplazar `jsonify()` por `APIResponse.success()` o `APIResponse.error()`
- [ ] Reemplazar `tu_a_dict()` por `DataConverter.*_to_dict()`
- [ ] Eliminar try-except (el decorador lo maneja)
- [ ] Prueba: `python run.py` y testea los endpoints

---

## Duda?

Mira:
- `stockhogar/rutas/productos.py` - Ejemplo completamente refactorizado
- `stockhogar/api/base.py` - Clases base (APIResponse)
- `stockhogar/utils/validation.py` - Validator
- `stockhogar/utils/converters.py` - DataConverter

---

**Una vez refactorizado**: Las rutas automáticamente ganan validación centralizada, manejo de errores consistente y seguridad contra inyección de SQL.
