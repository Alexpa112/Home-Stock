# 🚀 Quick Start - Dreame! Features

## Para Desarrollo (Recomendado)

### 1. Configurar Entorno
```bash
# Copiar configuración de desarrollo
cp .env.development .env

# Instalar dependencias
pip install -r requirements.txt

# Iniciar servidor
python run.py
```

**Dirección**: http://localhost:5000/login

### 2. Crear Primer Usuario
1. Abre http://localhost:5000/login
2. Rellena formulario de registro (primera vez)
3. Usuario: `test`
4. Contraseña: `test123`
5. Confirma contraseña
6. ¡Listo! Ya estás dentro

### 3. Probar Features

#### OAuth (Sin configuración)
- Los botones están disponibles pero requieren credenciales
- Sigue `SETUP_OAUTH.md` si quieres probarlos

#### Compartir Lista (Listo para usar)
1. Crea una lista
2. Haz clic en ⚙️ → "Miembros de la lista"
3. Ingresa email de otro usuario
4. ¡Automáticamente ves enlace copiable!
5. Comparte enlace por WhatsApp o como quieras

#### WhatsApp (Listo para usar)
1. En "Miembros de la lista"
2. Haz clic en botón verde "💬 WhatsApp"
3. Se abre WhatsApp con mensaje preformateado

---

## Para Producción

### 1. Configurar OAuth (Google + Apple)
Sigue: **`SETUP_OAUTH.md`**
- Obtén credenciales de Google Cloud
- Obtén credenciales de Apple Developer
- Agrega a `.env`

### 2. (Opcional) Configurar Email SMTP
Sigue: **`SETUP_EMAIL.md`**
- **Recomendación**: SendGrid o AWS SES
- O usa cliente del dispositivo (por defecto)

### 3. Probar Todo
Sigue: **`TESTING_OAUTH.md`**
- Test de Google OAuth
- Test de Apple OAuth
- Test de compartir listas
- Test de WhatsApp

### 4. Deploy
```bash
# Generar .env con credenciales reales
# Cambiar APP_URL a tu dominio
# Ejecutar con WSGI (gunicorn, etc.)
```

---

## 📁 Documentación por Feature

| Feature | Archivo | Estado |
|---------|---------|--------|
| **Autenticación OAuth** | `SETUP_OAUTH.md` | ✅ Listo |
| **Compartir Listas** | `IMPLEMENTACION_COMPLETA.md` | ✅ Listo |
| **Email (Opcional)** | `SETUP_EMAIL.md` | ✅ Listo |
| **Testing Completo** | `TESTING_OAUTH.md` | ✅ Listo |
| **Documentación Técnica** | `IMPLEMENTACION_COMPLETA.md` | ✅ Completa |

---

## ✨ Características Principales

### ✅ Autenticación
- Login/Registro tradicicional
- Google OAuth
- Apple OAuth
- Cambio de contraseña

### ✅ Compartir Listas
- Compartir por username (inmediato)
- Compartir por email (con invitación)
- Permisos: "Ver" y "Editar"
- Gestión de miembros
- Revocar acceso

### ✅ Compartir Externo
- WhatsApp integration (con/sin número)
- Enlace copiable para compartir
- 7 días de validez

### ✅ Sistema de Invitaciones
- Códigos únicos
- Auto-aceptación
- Email del dispositivo (respeta privacidad)

---

## 🧪 Testing Rápido

```bash
# Verificar que todo está bien
python test_features.py

# Resultado esperado:
# Total: 7/7 test groups passed
# All tests passed!
```

---

## 🔧 Archivos Clave

```
.env.development          ← Configuración de desarrollo
SETUP_OAUTH.md            ← Guía Google + Apple OAuth
SETUP_EMAIL.md            ← Guía email (opcional)
TESTING_OAUTH.md          ← Guía de testing
IMPLEMENTACION_COMPLETA.md ← Documentación técnica
test_features.py          ← Script de validación
```

---

## 🆘 Problemas Comunes

### "No veo botones de OAuth"
→ Eso es normal en desarrollo sin credenciales. 
   Sigue `SETUP_OAUTH.md` para obtenerlas.

### "Error al aceptar invitación"
→ El enlace puede haber expirado (7 días).
   Genera uno nuevo desde "Miembros de la lista".

### "WhatsApp no abre"
→ En desktop: Abre web.whatsapp.com (normal)
   En móvil: Asegúrate de tener WhatsApp instalado

### "No puedo cambiar permisos"
→ Solo el propietario puede cambiar permisos.
   Verifica que estés logueado como propietario.

---

## 📊 Flujos de Usuario

### Flujo 1: Iniciar Sesión
```
Login → Google/Apple/Password → Crear usuario si necesario → Home
```

### Flujo 2: Compartir por Email
```
Crear lista → Abrir Miembros → Ingresar email → 
Copiar enlace → Compartir por WhatsApp → Otro usuario acepta
```

### Flujo 3: Compartir por WhatsApp
```
Crear lista → Abrir Miembros → Clic en WhatsApp →
Mensaje preformateado → Enviar
```

---

## 🎯 Próximos Pasos

1. **Inmediato**: Prueba compartir listas (no requiere OAuth)
2. **Opcional**: Configura OAuth si quieres probarlo
3. **Producción**: Sigue `SETUP_OAUTH.md` + `SETUP_EMAIL.md`

---

## 📞 Soporte

- Documentación técnica: `IMPLEMENTACION_COMPLETA.md`
- Guías de setup: `SETUP_OAUTH.md`, `SETUP_EMAIL.md`
- Testing: `TESTING_OAUTH.md`
- Issues: Abre un issue en GitHub

---

**Status**: ✅ Completamente funcional  
**Última actualización**: 2026-07-08  
**Versión**: 1.0
