# ⚡ Quick Start - Dreame!

Referencia rápida para developers.

## Setup (5 min)

```bash
cd Home-Stock
python -m venv venv
source venv/bin/activate              # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py
# → http://localhost:5000
```

## Desarrollo

### Crear endpoint nuevo

```python
# stockhogar/rutas/mi_feature.py
from ..api import APIResponse, requerir_sesion, manejo_errores
from ..utils import Validator, DataConverter

bp = Blueprint("mi_feature", __name__, url_prefix="/api/mi_feature")

@bp.route("", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar():
    resultado = [...]
    return APIResponse.success(resultado)

@bp.route("", methods=["POST"])
@requerir_sesion
@manejo_errores
def crear():
    datos = request.get_json(force=True) or {}
    nombre = Validator.string_requerido(datos.get("nombre"), "nombre")
    # ...
    return APIResponse.success(nuevo, 201)
```

Luego en `stockhogar/__init__.py`:
```python
from .rutas import mi_feature
app.register_blueprint(mi_feature.bp)
```

### Crear módulo JavaScript

```javascript
// stockhogar/static/modules/mi-manager.js
class MiManager {
  constructor() {
    this.api = window.API;
    this.dom = window.DOM;
  }

  async cargar() {
    const datos = await this.api.obtenerMiRuta();
    this.renderizar(datos);
  }

  renderizar(datos) {
    // DOM updates aquí
  }
}

// En app.js
window.miManager = new MiManager();
```

## Testing

```bash
# Ejecutar tests
pytest

# Cobertura
pytest --cov=stockhogar

# Específico
pytest tests/test_productos.py::test_crear_producto
```

## Debugging

**Backend**:
```python
# Breakpoint
import pdb; pdb.set_trace()

# Logging
print(f"DEBUG: {variable}")

# Flask shell
flask shell
>>> from stockhogar.db import get_db
>>> db = get_db()
```

**Frontend** (F12 Console):
```javascript
console.log("DEBUG:", data);
debugger;  // Se para aquí
window.API.obtenerProductos().catch(console.error);
```

## Estructura Clave

```
stockhogar/
├── api/base.py              ← Clases base
├── utils/
│   ├── validation.py        ← Validaciones
│   └── converters.py        ← JSON serialization
├── rutas/                   ← Blueprints
└── static/
    ├── core/
    │   ├── dom-manager.js   ← window.DOM
    │   └── api-client.js    ← window.API
    └── modules/             ← Managers
```

## Imports Comunes

**Backend**:
```python
from ..api import APIResponse, requerir_sesion, manejo_errores
from ..utils import Validator, DataConverter
from ..db import get_db, ahora
from flask import Blueprint, request, session
```

**Frontend**:
```javascript
window.API              // Cliente HTTP
window.DOM              // Selectores
window.drawerListasManager  // Managers
```

## Comandos Docker

```bash
# Construir e iniciar
docker compose up -d --build

# Ver logs
docker compose logs app -f

# Entrar en contenedor
docker compose exec app bash

# Parar
docker compose down
```

## Convenciones

| Lenguaje | Archivo | Clase | Función |
|----------|---------|-------|---------|
| **Python** | `snake_case.py` | `PascalCase` | `snake_case()` |
| **JS** | `kebab-case.js` | `PascalCase` | `camelCase()` |
| **HTML ID** | - | - | `camelCase` (ej: `btnAbrirModal`) |

## Checklist Antes de Commitear

- [ ] `black stockhogar/` (formateado)
- [ ] `flake8 stockhogar/` (sin lint errors)
- [ ] `pytest` (tests pasan)
- [ ] No hay código duplicado
- [ ] Sigue convenciones OOP
- [ ] Documentación actualizada

## Rutas Útiles

| Acción | Ruta |
|--------|------|
| Ver inicio | `docs/00-INICIO.md` |
| Instalar | `docs/INSTALACION.md` |
| Desarrollar | `docs/DESARROLLO.md` |
| Ver API | `docs/API.md` |
| Debug | `docs/TROUBLESHOOTING.md` |
| Arquitectura | `docs/ARQUITECTURA.md` |

## Errores Comunes

**"ImportError: cannot import X"**
→ Asegúrate que el módulo está en `__init__.py`

**"No autorizado (401)"**
→ Añade `@requerir_sesion` al endpoint

**"Modal no cierra"**
→ Mira consola (F12 → Console) por JavaScript errors

**"BD corrupta"**
→ `rm data/stock.db && docker compose restart`

---

**¿Más info?** → `docs/DESARROLLO.md`
