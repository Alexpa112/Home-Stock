# 👨‍💻 Desarrollo - Dreame!

## Setup para Developers

```bash
git clone https://github.com/Alexpa112/Home-Stock.git
cd Home-Stock

# Entorno virtual
python -m venv venv
source venv/bin/activate           # Windows: venv\Scripts\activate

# Dependencias + extras dev
pip install -r requirements.txt
pip install pytest pytest-cov black flake8

# Ejecutar en modo desarrollo
FLASK_ENV=development python run.py
```

---

## Estructura para Desarrolladores

Lee primero: [ARQUITECTURA.md](ARQUITECTURA.md)

```
stockhogar/
├── api/
│   ├── __init__.py                 # Exporta APIResponse, decoradores
│   └── base.py                     # ⭐ Clases base para todos los endpoints
│
├── utils/
│   ├── __init__.py
│   ├── validation.py               # ⭐ Validator (todo el proyecto usa esto)
│   └── converters.py               # ⭐ DataConverter (JSON serialization)
│
├── rutas/
│   ├── productos.py                # Usa @requerir_sesion, @manejo_errores, Validator
│   ├── listas.py
│   ├── articulos_lista.py          # antes lista_compra.py
│   ├── categorias.py
│   ├── espacios.py
│   ├── historial.py
│   ├── auth.py
│   ├── tickets.py
│   └── ocr_tickets.py
│
├── servicios/
│   ├── ocr/
│   │   ├── procesador_imagen.py
│   │   ├── extractor_texto.py
│   │   ├── parseador_ticket.py
│   │   └── matcher_productos.py
│   └── __init__.py
│
├── static/
│   ├── core/
│   │   ├── dom-manager.js          # ⭐ window.DOM global
│   │   └── api-client.js           # ⭐ window.API global
│   ├── modules/
│   │   ├── drawer-listas.js        # Listas: crear, compartir, invitar
│   │   ├── form-builder.js
│   │   └── ui-components.js
│   ├── style.css
│   ├── responsive.css
│   └── app.js                      # Orquestador monolítico (~2200 líneas, no refactorizado todavía)
│
└── templates/
    ├── index.html                  # SPA principal
    └── login.html
```

---

## Principios al Desarrollar

### 1. **OOP + DRY**
❌ No hagas:
```python
# En tres rutas diferentes
cantidad = int(datos.get("cantidad"))
if cantidad < 0:
    return error
```

✅ Hazlo así:
```python
from ..utils import Validator
cantidad = Validator.entero_no_negativo(datos.get("cantidad"), "cantidad")
```

### 2. **Backend: Usa decoradores base**
❌ No hagas:
```python
@bp.route("/crear", methods=["POST"])
def crear():
    if not session.get("usuario_id"):
        return jsonify({"error": "..."}), 401
    try:
        # 50 líneas de lógica
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

✅ Hazlo así:
```python
@bp.route("/crear", methods=["POST"])
@requerir_sesion
@manejo_errores
def crear():
    # Solo lógica de negocio, sin boilerplate
    datos = request.get_json(force=True) or {}
    nombre = Validator.string_requerido(datos.get("nombre"), "nombre")
    # ...
    return APIResponse.success(resultado, 201)
```

### 3. **Frontend: Usa DOMManager y APIClient**
❌ No hagas:
```javascript
const btnTema = document.getElementById('btnTema');
const btnCategorias = document.getElementById('btnCategorias');

fetch('/api/productos')
  .then(res => res.json())
  .then(data => console.log(data))
  .catch(err => console.error(err))
```

✅ Hazlo así:
```javascript
// Los elementos están globales en window.DOM
window.DOM.btnTema.addEventListener('click', () => { ... });

// Llamadas API centralizadas
try {
  const productos = await window.API.obtenerProductos();
  console.log(productos);
} catch (error) {
  console.error(error.message);
}
```

### 4. **Frontend: Organiza en módulos**
Cuando extraigas lógica de `app.js`, hazlo como una clase con responsabilidad
única, siguiendo el patrón ya usado en `static/modules/drawer-listas.js`:

```javascript
// static/modules/mi-feature.js
class MiFeatureManager {
  constructor() {
    this.api = window.API;
    this.dom = window.DOM;
  }

  async cargar() {
    this.datos = await this.api.obtenerAlgo();
    this.renderizar();
  }

  renderizar() {
    // Solo renderización, sin lógica de negocio
  }
}

// En app.js
window.miFeatureManager = new MiFeatureManager();
window.miFeatureManager.cargar();
```

Nota: la mayor parte de la lógica de UI sigue viviendo en `app.js`
(~2200 líneas); solo `drawer-listas.js`, `form-builder.js` y
`ui-components.js` se han extraído hasta ahora.

---

## Antes de Commitear

### 1. **Código limpio**
```bash
# Formateo
black stockhogar/

# Linting
flake8 stockhogar/ --max-line-length=100

# Pruebas
pytest tests/
```

### 2. **Mensaje de commit**
```
[categoría] Descripción breve

Descripción más larga si es necesario.

Cierra #123
```

Categorías: `[feat]`, `[fix]`, `[refactor]`, `[docs]`, `[test]`

### 3. **PR / Merge**
- [ ] Código formateado (black + flake8)
- [ ] Tests pasan (pytest)
- [ ] Sin código duplicado
- [ ] Sigue convenciones OOP
- [ ] Documentación actualizada

---

## Testing

### Ejecutar tests
```bash
pytest                              # Todos
pytest tests/test_productos.py      # Específico
pytest -v                           # Verbose
pytest --cov=stockhogar            # Con cobertura
```

### Escribir tests
```python
# tests/test_productos.py
def test_crear_producto(client):
    resp = client.post('/api/productos', json={
        'nombre': 'Leche',
        'categoria': 'Lácteos',
        'cantidad': 2
    })
    assert resp.status_code == 201
    assert resp.json['nombre'] == 'Leche'
```

---

## Debugging

### Backend
```python
# En rutas
print(f"DEBUG: {variable}")

# Con debugger
import pdb; pdb.set_trace()

# Flask shell
flask shell
>>> from stockhogar.db import get_db
>>> db = get_db()
>>> db.execute("SELECT * FROM productos LIMIT 1").fetchone()
```

### Frontend
```javascript
// En console (F12)
console.log('DEBUG:', variable);
console.table(arrayDeObjetos);

// Debugger
debugger;   // Se para aquí en F12 → Sources

// Ver requests
F12 → Network → (hacer la acción)
```

---

## Roadmap de Refactorización (Fases)

Ver estado real y detallado en `README.md` (sección "Optimización - Estado
del Proyecto") y `docs/ARQUITECTURA.md`. Resumen:

### Fase 1: ✅ Base OOP (Hecha)
- [x] `api/base.py` - APIResponse + decoradores
- [x] `utils/validation.py` - Validator
- [x] `utils/converters.py` - DataConverter
- [x] `static/core/dom-manager.js` - Selectores centralizados
- [x] `static/core/api-client.js` - Fetch centralizado

### Fase 2: ✅ Refactorizar rutas (Hecha)
- [x] Todas las rutas usan `@requerir_sesion`, `@manejo_errores` y `Validator`

### Fase 3: Refactorizar frontend (parcial)
- [x] `modules/drawer-listas.js`, `modules/form-builder.js`, `modules/ui-components.js`
- [ ] `app.js` sigue siendo un orquestador monolítico (~2200 líneas); falta extraer el resto

### Fase 4: Tests (parcial)
- [x] Tests backend (`tests/`, pytest) para productos, OCR, features generales
- [x] Tests frontend con **Jest** para los módulos ya extraídos
- [ ] Cobertura >80% en backend (sin medir todavía)

---

## Convenciones de Código

### Python
```python
# Archivos
snake_case.py

# Clases
class MyClass:
    pass

# Funciones y métodos
def my_function():
    pass

# Privadas
def _internal_function():
    pass

# Constantes
MAX_ITEMS = 100

# Con type hints (recomendado)
from typing import Optional, List

def crear_producto(db, nombre: str, cantidad: int) -> int:
    return producto_id
```

### JavaScript
```javascript
// Archivos
kebab-case.js  o  MyClass.js

// Clases
class MyClass {
  method() { }
}

// Funciones
function myFunction() { }
const myFunc = () => { };

// Privadas
#privateMethod() { }
_internalVar = null

// Constantes
const MAX_ITEMS = 100;

// Async/Await preferido
async function cargar() {
  const data = await fetch(...);
  return data;
}
```

---

## Preguntas Frecuentes

**P: ¿Cómo agrego un nuevo endpoint API?**
R: 
1. Crea `stockhogar/rutas/mi_feature.py`
2. Usa `@requerir_sesion` + `@manejo_errores`
3. Usa `Validator` para validaciones
4. Devuelve con `APIResponse.success()`
5. Registra en `__init__.py`: `app.register_blueprint(mi_feature.bp)`

**P: ¿Cómo agrego nueva columna a BD?**
R: 
1. Edita la query en `db.py`
2. Añade migración en `init_db()` con `asegurar_columna()`
3. Actualiza `DataConverter` correspondiente

**P: El código JavaScript se ve enorme, ¿qué hago?**
R: Extrae lógica a `modules/`. Las managers son tus amigas.

---

## Recursos

- [Flask Docs](https://flask.palletsprojects.com)
- [MDN - Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API)
- [SQLite3 Docs](https://www.sqlite.org/docs.html)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)

---

**¿Algo bloqueado?** → Lee [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
