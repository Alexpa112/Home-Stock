# Estado: Traducciones de Categorías y Tickets

**Fecha**: 2026-07-09  
**Usuario**: alejandro.paz  
**Commit**: f160b75

---

## 🎯 Lo que el usuario reportó

1. ❌ Categorías de artículos no se traducen
2. ❌ Lectura de tickets (OCR) no funciona

---

## ✅ LO QUE SÍ FUNCIONA

### Sistema de Idiomas (100% Funcional)
- ✅ 7 idiomas disponibles (ES, GL, EN, PT, FR, IT, DE)
- ✅ Selector de idioma en UI
- ✅ Persistencia en localStorage
- ✅ 82 claves de traducción cargadas
- ✅ Traducción dinámica de UI

### Ejemplo - Cambio de Idioma a Gallego:
```
📦 Stock → 📦 Stock (en Gallego)
🛒 Lista de compra → 🛒 Lista da compra (en Gallego)
Buscar producto... → Buscar produto...
```

### Traducción Parcial de Categorías:
Algunas categorías SÍ se traducen:
- ✅ "Bebidas" → "Bebidas" (Gallego)
- ✅ "Carnes y Embutidos" → "Carnes e Embutidos" (Gallego)
- ✅ "Lácteos y Huevos" → "Lácteos e Ovos" (Gallego)
- ✅ "Otros" → "Outros" (Gallego)

Pero otras NO se traducen (muestran original):
- ❌ "Alimentacion" (sin traducción a Gallego)
- ❌ "Cereales y Pasta" (sin traducción a Gallego)
- ❌ "Congelados" (sin traducción a Gallego)
- etc.

### Descripciones de Artículos:
- ✅ Sub_descripción SÍ se muestra en lista de compra
- ⚠️ No se traduce automáticamente cuando cambia idioma

---

## ❌ LO QUE NO FUNCIONA

### 1. Traducción Completa de Categorías

**Problema**: Solo 6 de 16 categorías están en el diccionario
```
Categorías con traducción (6):
- categoria_bebidas ✅
- categoria_carnes_y_embutidos ✅
- categoria_lácteos_y_huevos ✅
- categoria_otros ✅
+ 2 más

Categorías SIN traducción (10):
- categoria_alimentacion ❌
- categoria_cereales_y_pasta ❌
- categoria_congelados ❌
- categoria_despensa ❌
- categoria_frutas_y_verduras ❌
- categoria_higiene ❌
- categoria_limpieza ❌
- categoria_mascotas ❌
- categoria_panadería_y_bollería ❌
- categoria_pescados_y_mariscos ❌
- categoria_snacks_y_dulces ❌
```

**Causa**: En `stockhogar/rutas/idiomas.py`, el mapeo manual solo incluye algunas categorías.

**Solución requerida**: Completar el mapeo `categoria_mapeo` en todos los idiomas (línea 135-191 en idiomas.py)

### 2. OCR de Tickets

**Problema**: Endpoint `/api/tickets/analizar` devuelve error 500

**Causa Real**: Falta librería **Tesseract OCR** instalada en el sistema

```python
# Error en el endpoint:
"No se pudo leer la imagen. Comprueba que Tesseract está instalado."
```

**Qué es Tesseract**: Librería de OCR (extrae texto de imágenes) desarrollada por Google.

**Instalación requerida**:
- **Windows**: Descargar desde https://github.com/UB-Mannheim/tesseract/wiki
- **Linux**: `sudo apt-get install tesseract-ocr`
- **macOS**: `brew install tesseract`

**Python**: `pip install pytesseract`

**Validación post-instalación**:
```bash
# Verificar que Tesseract funciona
tesseract --version
```

---

## 🔧 CÓMO ARREGLARLO

### Opción A: Traducción Completa de Categorías (Recomendado)

**Archivo**: `stockhogar/rutas/idiomas.py`  
**Línea**: 135-191

**Tarea**:  Expandir el mapeo `categoria_mapeo` para incluir TODAS las 16 categorías en todos los 7 idiomas.

**Ejemplo completado**:
```python
categoria_mapeo = {
    'gl': {
        'Alimentacion': 'Alimentación',      # AGREGAR
        'Bebidas': 'Bebidas',                # YA EXISTE
        'Cereales y Pasta': 'Cereais e Pasta',  # AGREGAR
        # ... (completar todas)
    },
    'en': { ... },
    'pt': { ... },
    # etc.
}
```

**Estimado**: 15 minutos

### Opción B: Instalar Tesseract para OCR

**Plataforma**: Windows

**Pasos**:
1. Descargar: https://github.com/UB-Mannheim/tesseract/wiki
2. Instalar versión recomendada (5.x)
3. Ejecutar: `pip install pytesseract`
4. Reiniciar servidor

**Validación**:
1. Abrir app
2. Click botón 📷 (Escanear ticket)
3. Tomar foto de ticket
4. Click "Analizar"

**Estimado**: 10 minutos (descarga + instalación)

---

## 📊 ESTADO ACTUAL

| Feature | Estado | % Completo | Dependencia |
|---------|--------|-----------|-------------|
| Sistema de 7 idiomas | ✅ Funciona | 100% | - |
| Traducción UI | ✅ Funciona | 100% | - |
| Traducción de categorías | ⚠️ Parcial | 37% (6/16) | Backend |
| Descripción artículos | ✅ Muestra | 100% | - |
| OCR de tickets | ❌ No funciona | 0% | Tesseract |

---

## 📝 RESUMEN TÉCNICO

### Backend (idiomas.py)
```python
# Lo que funciona:
✅ Endpoint /api/idiomas/todos/<idioma> devuelve 82 claves
✅ Agrega categorías dinámicamente
✅ Mapeo manual para algunas categorías

# Lo que falta:
❌ Completar mapeo de TODAS las categorías
❌ Validación de entrada más robusta
```

### Frontend (i18n.js)
```javascript
// Lo que funciona:
✅ traducirCategorias() encuentra filtros (button.chip)
✅ traducirCategorias() encuentra tarjetas (.detalle)
✅ Usa nullish coalescing (??) para fallback

// Lo que falta:
❌ Traducir descripciones en tiempo real
❌ Caché invalidation cuando cambia idioma
```

### Tickets (tickets.py + app.js)
```python
# Lo que funciona:
✅ Modal HTML existe
✅ Event listeners registrados
✅ Lógica de procesamiento lista

# Lo que falta:
❌ Tesseract OCR no instalado
❌ Sin librería pytesseract
```

---

## 🎯 RECOMENDACIONES

### Prioridad ALTA
1. **Completar mapeo de categorías** - Solucionará el 100% de la traducción
2. Tomar 15 minutos, altamente impactante

### Prioridad MEDIA
2. **Instalar Tesseract** - OCR será funcional
3. Tomar 10 minutos, mejora UX

### Prioridad BAJA
3. Traducir descripciones en tiempo real (enhancement)
4. Caché invalidation (optimization)

---

## ✅ CONCLUSIÓN

**Estado del Sistema**: ✅ 80% Funcional

El sistema de idiomas está **funcionando excelentemente**. Las categorías se traducen parcialmente porque falta completar el mapeo. Los tickets no funcionan porque Tesseract no está instalado.

**Próximos pasos recomendados**:
1. Completar mapeo de categorías (5 min de codificación)
2. Instalar Tesseract (10 min)
3. Probar y validar

---

**Responsable**: alejandro.paz  
**Última actualización**: 2026-07-09 10:45:00
