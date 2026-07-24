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

# Ejecutar backend en modo desarrollo
FLASK_ENV=development python run.py

# Frontend Next.js (en otra terminal)
npm install
npm run dev
```

---

## Estructura para Desarrolladores

Lee primero: [ARQUITECTURA.md](ARQUITECTURA.md)

```
app/
├── dashboard/
│   ├── layout.tsx                  # Shell autenticado + navegación
│   ├── page.tsx                    # Stock
│   ├── shopping/page.tsx           # Lista de compra
│   ├── listas/page.tsx             # Gestión y compartición de listas
│   ├── ticket/page.tsx             # OCR de tickets + confirmación
│   ├── historial/page.tsx          # Consumo y catálogo aprendido
│   └── settings/page.tsx           # Preferencias de usuario
├── layout.tsx
└── page.tsx

components/
├── dashboard/                      # StatsCard, SearchBar, CategoryBadge...
└── shared/                         # ProtectedRoute, StatusMessage...

hooks/
├── useAuth.ts
├── useActiveListSelection.ts
├── useStockPage.ts
├── useShoppingPage.ts
├── useListsPage.ts
└── useSettingsPage.ts

lib/
├── api.ts                          # Cliente HTTP y contratos de endpoints
├── error-utils.ts                  # Helpers de errores y parseo
├── session.ts                      # Logout / redirect
├── types.ts                        # Tipos compartidos del frontend
└── utils.ts

stockhogar/
├── api/
├── rutas/
├── servicios/
└── utils/
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

### 3. **Frontend: usa `lib/api.ts`, hooks y tipos compartidos**
❌ No hagas:
```tsx
const [items, setItems] = useState([])

useEffect(() => {
  fetch('/api/productos')
    .then((res) => res.json())
    .then(setItems)
}, [])
```

✅ Hazlo así:
```tsx
const { items, loading, error, submitForm } = useStockPage()
```

Y cuando necesites contratos o helpers comunes:
- `lib/api.ts` para hablar con Flask
- `lib/types.ts` para las shapes compartidas
- `lib/error-utils.ts` para mensajes/parsers consistentes

### 4. **Frontend: separa página, hook y componentes**
Patrón actual recomendado:

```tsx
// app/dashboard/mi-pagina/page.tsx
export default function MiPagina() {
  const estado = useMiPagina()
  return <MiVista {...estado} />
}
```

```ts
// hooks/useMiPagina.ts
export function useMiPagina() {
  // carga, acciones, estado derivado
}
```

Regla práctica:
- **page.tsx**: composición visual
- **hook**: estado, efectos y acciones async
- **components/**: piezas de UI reutilizables
- **lib/**: contratos, sesión, utilidades, tipos

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

### Fase 1: ✅ Base OOP backend (hecha)
- [x] `api/base.py` - APIResponse + decoradores
- [x] `utils/validation.py` - Validator
- [x] `utils/converters.py` - DataConverter

### Fase 2: ✅ Refactorización de rutas Flask (hecha)
- [x] Todas las rutas usan `@requerir_sesion`, `@manejo_errores` y `Validator`

### Fase 3: ✅ Base frontend Next.js modularizada
- [x] Páginas críticas del dashboard en `app/dashboard/*`
- [x] Hooks por dominio (`useStockPage`, `useShoppingPage`, `useListsPage`, `useSettingsPage`)
- [x] Tipos y utilidades compartidas en `lib/`
- [x] Feedback homogéneo vía `components/shared/StatusMessage.tsx`

### Fase 4: ⏳ Tests y cobertura
- [x] Tests backend (`tests/`, pytest) para productos, OCR y features generales
- [ ] Aumentar regresiones del frontend actual
- [ ] Medir cobertura global y fijar umbrales

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
