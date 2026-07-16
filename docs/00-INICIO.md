# 📱 Dreame! - Inventario del Hogar

**Control inteligente de stock para casa, oficina o negocio pequeño.**

Aplicación web minimalista diseñada para ejecutarse en una Raspberry Pi 3 sin dependencias pesadas. Gestiona inventario, lista de compra automática y escanea tickets con OCR local.

## 🚀 Inicio Rápido

### Docker (Recomendado)
```bash
cd docker
docker compose up -d --build
# Accede a http://localhost:5000
```

### Desarrollo Local
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

## 📚 Documentación

| Documento | Para |
|-----------|------|
| [**ARQUITECTURA.md**](ARQUITECTURA.md) | Developers - Estructura del código |
| [**API.md**](API.md) | Endpoints - Referencia completa |
| [**INSTALACION.md**](INSTALACION.md) | DevOps - Setup en Raspberry Pi |
| [**DESARROLLO.md**](DESARROLLO.md) | Devs - Guía de desarrollo |
| [**TROUBLESHOOTING.md**](TROUBLESHOOTING.md) | Soporte - Problemas comunes |

## ✨ Stack Técnico

| Capa | Tech |
|------|------|
| **Backend** | Python + Flask |
| **BD** | SQLite |
| **Frontend** | HTML + CSS + JavaScript vanilla |
| **OCR** | Tesseract (local) |
| **Deploy** | Docker + Docker Compose |

## 🎯 Características

✅ **Inventario inteligente** - Stock con avisos de mínimos y caducidad  
✅ **Lista de compra automática** - Se genera al bajar stock  
✅ **Escaneo de tickets** - OCR local sin conexión  
✅ **Multi-usuario** - Sesiones persistentes (365 días)  
✅ **Responsive** - Móvil, tablet, desktop  
✅ **Dark mode** - Según preferencias del sistema  
✅ **Bajo consumo** - Cabe en una Raspberry Pi 3

## 🏗️ Estructura

```
Home-Stock/
├── run.py                 # Punto de entrada
├── requirements.txt       # Dependencias Python
│
├── stockhogar/            # Aplicación principal
│   ├── api/              # Clase base para blueprints
│   ├── utils/            # Validación, conversión, helpers
│   ├── rutas/            # Blueprints API
│   ├── servicios/        # OCR, integración
│   ├── static/           # Frontend (JS, CSS)
│   └── templates/        # HTML
│
├── docker/               # Dockerfiles
├── scripts/              # Instalación, setup
├── tests/                # Test suite
└── docs/                 # Documentación
```

## 🔒 Seguridad

- Hashing de contraseñas (Werkzeug)
- Sesiones seguras (Flask)
- CSRF protection automática
- XSS protection en frontend
- Control de acceso por usuario

## 📝 Licencia

MIT - Libre para uso comercial y personal

---

**¿Primer viaje?** → Lee [**INSTALACION.md**](INSTALACION.md)  
**¿Vas a desarrollar?** → Empieza en [**DESARROLLO.md**](DESARROLLO.md)  
**¿Hay un bug?** → Mira [**TROUBLESHOOTING.md**](TROUBLESHOOTING.md)
