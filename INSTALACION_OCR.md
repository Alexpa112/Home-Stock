# 🚀 INSTALACIÓN Y SETUP - SISTEMA OCR

## Paso 1: Instalar dependencias Python

```bash
cd "C:\Users\alejandro.paz\Desktop\Claude Pruebas\StockHogar"
.\venv\Scripts\Activate.ps1

pip install pytesseract Pillow fuzzywuzzy python-Levenshtein
```

## Paso 2: Instalar Tesseract OCR (Sistema)

### Windows:
**Opción A:** Descargar instalador
- Descargar: https://github.com/UB-Mannheim/tesseract/wiki
- Instalar en: `C:\Program Files\Tesseract-OCR`
- Agregar al PATH

**Opción B:** Con Chocolatey
```powershell
choco install tesseract
```

### Linux/WSL:
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-spa
```

## Paso 3: Instalar OpenCV (Importante)

```bash
pip install opencv-python
```

Si fallasutton (issue de wheel):
```bash
pip install --upgrade pip setuptools wheel
pip install opencv-python --no-cache-dir
```

## Paso 4: Verificar Instalación

```bash
python tests_ocr.py
```

Debería ver:
```
============================================================
TESTING EXHAUSTIVO - SISTEMA OCR TICKETS
============================================================
[Tests ejecutándose...]

Total: 8/8 tests pasados

🎉 TODOS LOS TESTS PASARON - SISTEMA LISTO
```

## Paso 5: Iniciar servidor y probar API

```bash
# En una terminal:
python -m flask --app stockhogar run

# En otra terminal, probar endpoint:
curl -X GET http://localhost:5000/api/ocr/validar-instalacion
```

Respuesta esperada:
```json
{
  "ok": true,
  "validaciones": {
    "tesseract": true,
    "opencv": true,
    "pytesseract": true,
    "fuzzywuzzy": true
  }
}
```

## Paso 6: Probar con imagen real

```bash
# Usar el frontend o curl:
curl -X POST \
  -F "archivo=@ticket.jpg" \
  http://localhost:5000/api/ocr/procesar-ticket
```

---

## 🐛 Troubleshooting

### Error: "tesseract is not installed"
- Windows: Descargar desde https://github.com/UB-Mannheim/tesseract/wiki
- Linux: `sudo apt-get install tesseract-ocr tesseract-ocr-spa`
- Verificar PATH

### Error: "No module named cv2"
```bash
pip install --upgrade opencv-python --no-cache-dir
```

### Error: "fuzzywuzzy..."
```bash
pip install python-Levenshtein
```

---

## 📁 Estructura Archivos Creados

```
stockhogar/
├── servicios/
│   ├── __init__.py
│   └── ocr/
│       ├── __init__.py
│       ├── procesador_imagen.py (ProcesadorImagen)
│       ├── extractor_texto.py (ExtractorTexto)
│       ├── parseador_ticket.py (ParseadorTicket)
│       ├── matcher_productos.py (MatcherProductos)
│       └── gestor_ocr.py (GestorOCR - Facade)
├── rutas/
│   └── ocr_tickets.py (API endpoints)
├── tests_ocr.py (Testing exhaustivo)
├── REPORTE_OCR.md (Documentación técnica)
└── INSTALACION_OCR.md (Este archivo)
```

---

## ✅ Checklist de Verificación

- [ ] Instalar Python deps (pytesseract, Pillow, fuzzywuzzy)
- [ ] Instalar Tesseract OCR (sistema)
- [ ] Instalar opencv-python
- [ ] Ejecutar `python tests_ocr.py` → 8/8 pasados
- [ ] Iniciar Flask server
- [ ] Verificar endpoint `/api/ocr/validar-instalacion`
- [ ] Probar con ticket real
- [ ] Verificar que productos se detectan correctamente

---

## 📚 Documentación Relacionada

- `REPORTE_OCR.md`: Arquitectura y componentes
- `tests_ocr.py`: Tests exhaustivos
- `stockhogar/servicios/ocr/`: Código fuente

---

**Estado:** Listo para instalar y usar  
**Complejidad:** Media (requiere setup de sistema)  
**Tiempo estimado:** 15-30 minutos
