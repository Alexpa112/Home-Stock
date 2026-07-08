# 📋 CLAUDE.md - Reglas del Proyecto

**LEE ESTO ANTES DE CUALQUIER TAREA**

---

## 👤 Mi Identidad

**Nombre**: alejandro.paz  
**Email**: alejandro.paz@edisa.com  
**Rol**: Desarrollador principal

---

## 📌 REGLA 1: Git - Commits Siempre con Mi Nombre

**SIEMPRE que subo a GitHub**, el commit debe incluir:

```bash
git config user.name "alejandro.paz"
git config user.email "alejandro.paz@edisa.com"
```

### Formato de Commit:
```bash
git commit -m "Tu mensaje aquí"
```

El co-author automático es:
```
Co-Authored-By: alejandro.paz <alejandro.paz@edisa.com>
```

**⚠️ CRÍTICO**: Antes de cualquier `git commit`, verifica:
```bash
git config --list | grep user
# Debe mostrar:
# user.name=alejandro.paz
# user.email=alejandro.paz@edisa.com
```

Si no es así, configúralo:
```bash
git config user.name "alejandro.paz"
git config user.email "alejandro.paz@edisa.com"
```

---

## 📌 REGLA 2: DRY - Revisa Si el Código Ya Existe

**ANTES de escribir código nuevo:**

1. **Busca si ya existe**
   ```bash
   grep -r "mi_funcion" stockhogar/
   ```

2. **Verifica importaciones**
   - ¿Ya hay una clase similar en `utils/`?
   - ¿Ya hay un conversor en `DataConverter`?
   - ¿Ya hay un validador en `Validator`?

3. **Si existe**: Reutiliza
   ```python
   from ..utils import Validator, DataConverter
   # En lugar de duplicar
   ```

4. **Si NO existe**: Crea en el lugar centralizado
   - Validaciones → `stockhogar/utils/validation.py`
   - Conversiones → `stockhogar/utils/converters.py`
   - Respuestas → `stockhogar/api/base.py`

### Checklist Antes de Programar:
- [ ] ¿Ya existe una función similar?
- [ ] ¿Puedo usar una clase base en lugar de crear nueva?
- [ ] ¿Hay un patrón establecido que debería seguir?
- [ ] ¿Está en `utils/` algo que se podría centralizar?

---

## 📌 REGLA 3: OOP + DRY - Máximas Prioridades

**Directriz máxima**: Código limpio, sin duplicación, Programación Orientada a Objetos.

### Nunca hagas:
```python
# ❌ MALO: Duplicación
cantidad = int(datos.get("cantidad", 0))
# Repetido en 5 rutas
```

### Siempre haz:
```python
# ✅ BUENO: Centralizado
from ..utils import Validator
cantidad = Validator.entero_no_negativo(datos.get("cantidad"), "cantidad")
```

---

## 📌 REGLA 4: Estructura de Archivos

**Siempre respeta esta estructura:**

```
stockhogar/
├── api/              ← Clases base API
├── utils/            ← Validadores, Convertidores
├── rutas/            ← Blueprints (uno por dominio)
├── servicios/        ← Integraciones externas
├── static/
│   ├── core/         ← DOMManager, APIClient
│   ├── modules/      ← Managers específicos
│   └── vendor/       ← Librerías externas
├── templates/        ← HTML
└── db.py, config.py, seguridad.py
```

**No crear archivos sueltos**. Todo va en su carpeta.

---

## 📌 REGLA 5: Documentación

**Antes de hacer cambios grandes:**
1. Actualiza `docs/DESARROLLO.md` si cambias cómo se desarrolla
2. Actualiza `docs/ARQUITECTURA.md` si cambias estructura
3. Actualiza `QUICKSTART.md` si cambias comando básico

**NO dejes código sin documentar si es confuso.**

---

## 📌 REGLA 6: Convenciones de Código

### Python
```python
# Clases: PascalCase
class MyClass:
    pass

# Funciones: snake_case
def my_function():
    pass

# Privadas: _prefijo
def _internal_function():
    pass

# Constantes: UPPER_SNAKE_CASE
MAX_ITEMS = 100
```

### JavaScript
```javascript
// Clases: PascalCase
class MyClass {
  method() { }
}

// Funciones: camelCase
function myFunction() { }
const myFunc = () => { };

// Privadas: #prefijo (o _prefijo)
#privateMethod() { }

// Constantes: UPPER_SNAKE_CASE
const MAX_ITEMS = 100;

// IDs HTML: camelCase con prefijo módulo
<button id="btnAbrirModal">
```

---

## 📌 REGLA 7: Antes de Cualquier Tarea

**SIEMPRE HAGO ESTO PRIMERO:**

1. **Leo este archivo (CLAUDE.md)** ← TÚ ESTÁS AQUÍ
2. **Reviso si código similar existe** (`grep`, búsqueda)
3. **Entiendo la estructura actual** (archivo correcto, patrón)
4. **Busco ejemplos** (productosj.py, categorias.py, etc.)
5. **Reutilizo o creo centralizado** (no duplico)
6. **Testeo antes de subir** (`python run.py`)
7. **Configuro git** (user.name, user.email)
8. **Commit con mensaje claro** (qué + por qué)

---

## 📌 REGLA 8: Después de Cambios - Reiniciar Servidor y Borrar Caché

**SIEMPRE después de editar archivos**, ANTES de probar:

```bash
# 1. Detener el servidor
# Ctrl+C si está en foreground, o:
pkill -f "python run.py"  # En Bash/Linux
# o en PowerShell:
Get-Process | Where-Object {$_.ProcessName -eq 'python'} | Stop-Process -Force

# 2. Limpiar caché de Python
rm -rf __pycache__ 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

# 3. Limpiar caché de Flask/Jinja2
rm -rf instance 2>/dev/null

# 4. Reiniciar el servidor
python run.py
```

### ¿Por Qué?
- **Flask cachea templates** (archivos .html) cuando no está en DEBUG
- **Python cachea bytecode** (.pyc files)
- Sin borrar caché, ves cambios **SOLO en el archivo** pero NO en el navegador
- Parece que no funcionó, cuando realmente funciona pero está caché

### Archivos que REQUIEREN reinicio:
- ✅ Cualquier `.html` en `templates/`
- ✅ Cualquier `.py` en `stockhogar/`
- ✅ `static/` archivos (si están minificados)
- ✅ Cambios en `requirements.txt`

### Archivos que NO requieren reinicio:
- ❌ `.css` sin minificación (se recargan en el navegador)
- ❌ `.js` sin minificación (se recargan en el navegador)

---

## 📌 CHECKLIST ANTES DE HACER COMMIT

```
DESPUÉS DE EDITAR ARCHIVOS (SIEMPRE):
- [ ] Reinicié el servidor (Ctrl+C)
- [ ] Borré caché: rm -rf __pycache__ *.pyc instance
- [ ] Reinicié con python run.py
- [ ] Verifiqué en navegador que se ve el cambio

ANTES DE GIT COMMIT:
- [ ] Verifiqué que user.name = "alejandro.paz"
- [ ] Verifiqué que user.email = "alejandro.paz@edisa.com"
- [ ] Reviso git status (¿incluyo lo correcto?)
- [ ] No hay .env, secrets, o archivos sensibles
- [ ] Probé: python run.py (o tests)
- [ ] Mensaje de commit es claro
- [ ] Sigo el patrón OOP/DRY

GIT CONFIG:
git config user.name "alejandro.paz"
git config user.email "alejandro.paz@edisa.com"

GIT COMMIT:
git commit -m "Tu mensaje"
```

---

## 🎯 Flujo Completo Ejemplo

### Tarea: "Añadir nuevo endpoint de reportes"

**1. Leo CLAUDE.md** ← Ahora
**2. Reviso código existente**
```bash
grep -r "APIResponse" stockhogar/rutas/
# Veo que productos.py usa el patrón
```

**3. Busco si reportes.py existe**
```bash
ls stockhogar/rutas/reportes.py
# No existe, lo creo
```

**4. Copio patrón de productos.py**
```python
from ..api import APIResponse, requerir_sesion, manejo_errores
from ..utils import Validator, DataConverter

@bp.route("", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_reportes():
    # ...
```

**5. Pruebo**
```bash
python run.py
# Test el endpoint
```

**6. Configuro git**
```bash
git config user.name "alejandro.paz"
git config user.email "alejandro.paz@edisa.com"
```

**7. Commit**
```bash
git add stockhogar/rutas/reportes.py
git commit -m "feat: añadir endpoints de reportes

Nuevo módulo reportes con endpoints:
- GET /api/reportes (listar)
- POST /api/reportes (crear)

Sigue patrón OOP de APIResponse + Validator

Co-Authored-By: alejandro.paz <alejandro.paz@edisa.com>"
```

---

## 📚 Referencias Rápidas

| Necesito | Archivo | Ubicación |
|----------|---------|-----------|
| Validar datos | `Validator` | `stockhogar/utils/validation.py` |
| Convertir a JSON | `DataConverter` | `stockhogar/utils/converters.py` |
| Responder API | `APIResponse` | `stockhogar/api/base.py` |
| Selectores DOM | `window.DOM` | `stockhogar/static/core/dom-manager.js` |
| Fetch centralizado | `window.API` | `stockhogar/static/core/api-client.js` |
| Patrón de ruta | `productos.py` | `stockhogar/rutas/productos.py` |
| Patrón de refactor | `PATRON_*` | `docs/PATRON_REFACTORIZACION.md` |

---

## ⚠️ COSAS QUE NUNCA HAGO

```
❌ Duplicar validación en múltiples rutas
❌ Crear nuevas funciones _a_dict (usar DataConverter)
❌ Usar jsonify() directamente (usar APIResponse)
❌ Hacer try-catch sin @manejo_errores
❌ Cambiar estructura sin actualizar CLAUDE.md
❌ Subir a GitHub sin verificar git config
❌ Crear archivos sueltos (siempre en su carpeta)
❌ Escribir código sin revisar si existe
❌ EDITAR TEMPLATES/PYTHON Y PROBAR SIN REINICIAR SERVIDOR
   → Siempre borrar __pycache__, *.pyc, instance/
   → Flask cachea templates - sin reinicio veo versión vieja
❌ Asumir que "se ven los cambios" en el navegador sin verificar
```

---

## 🚀 Resumen Ejecutivo

**ANTES DE PROGRAMAR:**
1. Leo CLAUDE.md
2. Busco código similar (grep)
3. Reutilizo patrones existentes
4. Configuro git (user.name, user.email)
5. Codifico siguiendo OOP/DRY
6. Testeo (python run.py)
7. Commit con mi nombre

**DIRECTRICES MÁXIMAS:**
- OOP puro
- DRY (no repetir)
- Código centralizado
- Git config siempre

---

**Última actualización**: 2026-07-08  
**Versión**: 1.0  
**Estado**: ✅ Activo
