# 🔧 Troubleshooting - Dreame!

## Problemas Comunes

### "No puedo acceder a la app"

**Problema**: http://localhost:5000 no carga

**Soluciones**:
1. ¿Está el servidor running?
   ```bash
   # Docker
   docker compose ps
   # Debe estar "Up"
   
   # Local
   python run.py
   # Debe mostrar "Running on..."
   ```

2. ¿Puerto correcto?
   ```bash
   # Default: 5000
   # Si lo cambiaste, usa ese puerto
   netstat -an | findstr 5000  # Windows
   lsof -i :5000               # Mac/Linux
   ```

3. Firewall
   - Asegúrate que puerto 5000 no está bloqueado

---

### "Error: base de datos corrupta"

**Síntoma**: `sqlite3.DatabaseError: database disk image is malformed`

**Soluciones**:
```bash
# Opción 1: Resetear (BORRA DATOS)
rm data/stock.db
docker compose restart

# Opción 2: Backup + reset
cp data/stock.db data/stock.db.broken
rm data/stock.db
docker compose restart

# Opción 3: Usar backup anterior
cp ~/backups/stock.db.20260708 data/stock.db
docker compose restart
```

---

### "Error 401: No has iniciado sesión"

**Problema**: Hice logout y no puedo volver a entrar

**Causa**: Sesión expirada o no iniciada

**Solución**:
```
1. Limpia cookies del navegador (F12 → Aplicación → Cookies)
2. Abre http://localhost:5000
3. Deberías ver página de login
4. Crea usuario o inicia sesión
```

---

### "Error 400: El nombre es obligatorio"

**Problema**: Envío datos a la API pero recibo error de validación

**Causa**: Validación fallida en backend

**Debug**:
```javascript
// En consola (F12)
const respuesta = await window.API.crearProducto({
  nombre: "",  // Vacío = error
});
// Error: "El nombre es obligatorio"

// Correcto:
const respuesta = await window.API.crearProducto({
  nombre: "Leche",  // No vacío
});
```

---

### "OCR no funciona / Tesseract no encontrado"

**Síntoma**: Al escanear ticket, error de OCR

**Soluciones**:

**Windows**:
```powershell
# Instalar Tesseract
choco install tesseract-ocr

# Verificar que está en PATH
tesseract --version

# Si no está, añadir a código:
import pytesseract
pytesseract.pytesseract.pytesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

**Linux**:
```bash
sudo apt-get install tesseract-ocr
tesseract --version
```

**Docker**:
```bash
# La imagen ya tiene Tesseract
docker compose exec app tesseract --version
```

---

### "Docker: no space left on device"

**Problema**: Falta espacio en disco

**Soluciones**:
```bash
# Limpiar imágenes/containers sin usar
docker system prune -a

# O liberar espacio en tu máquina
rm -rf /tmp/*           # Linux
del %temp%\*            # Windows
```

---

### "Productos no aparecen en lista"

**Problema**: Creo productos pero no se ven

**Debug**:
```javascript
// 1. Abre F12 → Network
// 2. Mira si hay peticiones a /api/productos

// 3. En consola:
const productos = await window.API.obtenerProductos();
console.log(productos);

// 4. Si está vacío, comprueba:
// - ¿Estás en la lista correcta?
// - ¿Existe esa lista?

// En backend (dev):
from stockhogar.servicios.stock import lista_actual_con_permiso
from flask import session
db = get_db()
lista_id = lista_actual_con_permiso(db, session)
print(f"Lista actual: {lista_id}")
```

---

### "Modal no cierra"

**Problema**: Después de crear algo, el modal sigue abierto

**Debug**:
```javascript
// En consola (F12):
const modal = window.DOM.modal;
console.log(modal.hidden);  // Debe ser true (cerrado)

// Cerrar manualmente:
modal.hidden = true;
document.body.classList.remove('modal-open');
```

**Causa**: Probablemente error JavaScript no manejado. Mira:
```javascript
// En consola (F12 → Console)
// ¿Hay errores rojos?
```

---

### "Drawer lateral no aparece"

**Problema**: Click en "Mi lista" pero drawer no abre

**Debug**:
```javascript
// En consola:
window.drawerListasManager.abrirModal();  // Abrirlo manualmente

// ¿Error? Mira la consola (F12 → Console)
// Probablemente falta algún elemento HTML o script no cargó
```

**Solución**:
```html
<!-- En templates/index.html, verifica que existe: -->
<div id="modalMisListas" ...>
  <!-- Contenido del drawer -->
</div>

<!-- Y que están cargados los scripts: -->
<script src="{{ url_for('static', filename='drawer-listas.js') }}"></script>
```

---

### "Dark mode no funciona"

**Problema**: Toggle 🌙 en cabecera no cambia tema

**Debug**:
```javascript
// Tema activo:
console.log(document.documentElement.dataset.theme);

// Cambiar manualmente:
document.documentElement.dataset.theme = 'dark';  // o 'light'
localStorage.setItem('stockhogar-tema', 'dark');
```

---

### "Lista de compra vacía pero debería tener items"

**Problema**: Tengo productos bajo stock pero lista vacía

**Causa**: No se ejecutó `revisar_stock_bajo()`

**Debug**:
```python
# Backend (en desarrollo):
from stockhogar.rutas.productos import revisar_stock_bajo
from stockhogar.db import get_db

db = get_db()
producto_id = 1

# Verificar estado
producto = db.execute(
    "SELECT * FROM productos WHERE id = ?", (producto_id,)
).fetchone()
print(f"Cantidad: {producto['cantidad']}, Mínimo: {producto['stock_minimo']}")

# Verificar lista de compra (tabla actual: articulos_lista; "lista_compra" es
# la tabla antigua ya migrada, ver _migrar_lista_compra_a_articulos en db.py)
item = db.execute(
    "SELECT * FROM articulos_lista WHERE producto_id = ? AND origen = 'auto'",
    (producto_id,)
).fetchone()
print(f"En lista: {item}")

# Ejecutar manualmente
revisar_stock_bajo(db, producto_id)
db.commit()
```

---

### "No puedo compartir lista"

**Problema**: Error al intentar compartir

**Debug**:
```javascript
// 1. ¿El otro usuario existe?
// 2. ¿Su nombre_usuario es exacto? (case-sensitive en algunos)
// 3. Mira error en F12 → Console

// Prueba manualmente:
try {
  const res = await window.API.compartirLista(1, {
    usuario: "maria",
    nivel: "editar"
  });
  console.log(res);
} catch (error) {
  console.error(error.message);
}
```

---

### "App lenta después de muchas acciones"

**Problema**: Cambio de velocidad a lo largo del uso

**Causa**: Posiblemente memory leak en JavaScript

**Debug**:
```javascript
// F12 → Memory → Heap Snapshot
// ¿Crece sin parar?

// Solución: Limpiar event listeners
// Al cerrar modal, desuscribir:
element.removeEventListener('click', myHandler);
```

---

### "Contraseña olvidada"

**Problema**: No puedo entrar

**Soluciones**:

**Local**:
```python
# En consola Python
from stockhogar.db import get_db
from werkzeug.security import generate_password_hash

db = get_db()
nueva_contraseña = generate_password_hash("nueva123")
db.execute(
    "UPDATE usuarios SET password_hash = ? WHERE nombre_usuario = ?",
    (nueva_contraseña, "tu_usuario")
)
db.commit()
print("Contraseña cambiada")
```

**Docker**:
```bash
docker compose exec app python
# (después de entrar en Python)
>>> from stockhogar.db import get_db
>>> from werkzeug.security import generate_password_hash
>>> # ... (igual que arriba)
```

**Fácil**: Resetea BD (pierdes datos):
```bash
rm data/stock.db
docker compose restart
# Crea usuario nuevo
```

---

### "Error: CORS / Cross-origin"

**Problema**: "No Access-Control-Allow-Origin header"

**Causa**: Probablemente llamando API desde origen diferente

**Solución**: 
```python
# En stockhogar/__init__.py, después de create_app()
from flask_cors import CORS
CORS(app)  # Solo desarrollo!
```

**Producción**: No deberías tener este problema (mismo dominio)

---

### "Tengo más preguntas"

Documentación:
- [DESARROLLO.md](DESARROLLO.md) - Para developers
- [ARQUITECTURA.md](ARQUITECTURA.md) - Design decisions
- [API.md](API.md) - Referencia de endpoints

Comunidad:
- GitHub Issues
- Pull Requests con mejoras

---

## Logs útiles

### Backend
```bash
# Docker
docker compose logs app -f --tail=50

# Local
python run.py  # Ver logs en consola
```

### Frontend (F12 Console)
```javascript
// Errores
window.addEventListener('error', (e) => {
  console.error('Error global:', e);
});

// Promesas no manejadas
window.addEventListener('unhandledrejection', (e) => {
  console.error('Promise rechazada:', e.reason);
});
```

---

## Tabla de Diagnóstico

| Síntoma | Probable Causa | Verificar |
|---------|----------------|-----------|
| Pantalla blanca | JS error | F12 → Console |
| 401 en log | Sesión expirada | Login nuevamente |
| 400 en API | Validación fallida | Datos enviados |
| Lento | Memory leak o mucho data | DevTools Memory |
| BD corrupta | Proceso matado a la fuerza | Resetear `stock.db` |
| Modal atrapado | Error JS en modal | Consola (F12) |

---

¿Problema no listado? Abre issue en GitHub con:
1. Pasos para reproducir
2. Screenshot/error
3. Logs (backend + F12)
4. Tu setup (Docker/Local/Pi)
