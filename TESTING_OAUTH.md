# 🧪 Testing OAuth Completo

## Prerrequisitos

1. **Credenciales Google OAuth**
   - Sigue: `SETUP_OAUTH.md` - Sección 1
   - Ten a mano:
     - `GOOGLE_CLIENT_ID`
     - `GOOGLE_CLIENT_SECRET`

2. **Credenciales Apple OAuth**
   - Sigue: `SETUP_OAUTH.md` - Sección 2
   - Ten a mano:
     - `APPLE_CLIENT_ID`
     - `APPLE_TEAM_ID`
     - `APPLE_CLIENT_SECRET`

3. **Archivo .env configurado**
   ```bash
   cp .env.development .env
   # Edita y agrega tus credenciales
   ```

---

## Test 1: Google OAuth

### Paso 1: Verificar Configuración
```bash
python -c "from stockhogar.config import GOOGLE_CLIENT_ID; print(f'Google Client ID: {GOOGLE_CLIENT_ID[:10]}...')"
# Debe mostrar algo como: Google Client ID: xxxxxxxx.a...
```

### Paso 2: Iniciar Servidor
```bash
python run.py
# Debe mostrar: Running on http://127.0.0.1:5000
```

### Paso 3: Prueba en Navegador
1. Abre http://localhost:5000/login
2. Busca el botón "🔷 Continuar con Google"
3. Haz clic
4. **Deberías ver**: Página de login de Google
5. Inicia sesión con tu cuenta Google
6. **Deberías ver**: Solicitud de permiso ("acceder a perfil, email")
7. Haz clic en "Permitir"
8. **Deberías ser redirigido a**: http://localhost:5000/
9. **Deberías estar logueado** (ver tu nombre en pantalla)

### Paso 4: Verificar Datos
1. Abre DevTools (F12)
2. Abre pestaña "Storage" / "LocalStorage"
3. Busca `stockhogar-usuario`
4. **Deberías ver**: Tu nombre de usuario creado automáticamente

### Paso 5: Verificar en Base de Datos
```bash
python
from stockhogar.db import get_db
from flask import Flask

app = Flask(__name__)
with app.app_context():
    db = get_db()
    usuario = db.execute("SELECT * FROM usuarios ORDER BY id DESC LIMIT 1").fetchone()
    print(f"Último usuario: {usuario['nombre_usuario']} ({usuario['email']})")
    
    oauth = db.execute("SELECT * FROM oauth_accounts WHERE usuario_id = ?", (usuario['id'],)).fetchone()
    print(f"OAuth: {oauth['proveedor']} - {oauth['id_proveedor']}")
```

---

## Test 2: Apple OAuth

### Paso 1: Verificar Configuración
```bash
python -c "from stockhogar.config import APPLE_CLIENT_ID; print(f'Apple Client ID: {APPLE_CLIENT_ID}')"
# Debe mostrar: Apple Client ID: com.dreame.web
```

### Paso 2: Cerrar Sesión
1. Abre http://localhost:5000/
2. Haz clic en ⚙️ (Ajustes)
3. Haz clic en "Cerrar sesión"

### Paso 3: Prueba en Navegador
1. Abre http://localhost:5000/login
2. Busca el botón "🍎 Continuar con Apple"
3. Haz clic
4. **Deberías ver**: Página de login de Apple (o página de consentimiento)
5. Inicia sesión con tu cuenta Apple
6. **Deberías ver**: Solicitud de permiso
7. Haz clic en "Continuar"
8. **Deberías ser redirigido a**: http://localhost:5000/
9. **Deberías estar logueado** (ver tu nombre en pantalla)

### Paso 4: Verificar Datos
```bash
python
from stockhogar.db import get_db
from flask import Flask

app = Flask(__name__)
with app.app_context():
    db = get_db()
    oauth = db.execute("SELECT * FROM oauth_accounts WHERE proveedor = 'apple'").fetchone()
    if oauth:
        print(f"Apple OAuth encontrado: {oauth['email']}")
    else:
        print("No se encontró Apple OAuth")
```

---

## Test 3: Compartir Lista

### Paso 1: Crear Lista
1. Logueate (Google o Apple)
2. Ve a "Mis listas" (botón con nombre lista)
3. Haz clic en "+" (crear nueva)
4. Nombre: "Lista Prueba"
5. Haz clic en "Crear"

### Paso 2: Abrir Ajustes
1. Haz clic en ⚙️ (Ajustes del icono de lista)
2. Busca la sección "Personalizar lista"
3. Haz clic en "👥 Miembros de la lista"
4. **Deberías ver**: Sección "Compartir lista"

### Paso 3: Probar Compartir por Enlace
1. En "Compartir lista", ingresa un email: `test@example.com`
2. Selecciona nivel: "Ver"
3. Haz clic en "Compartir"
4. **Deberías ver**: 
   - Mensaje "Enlace de invitación generado"
   - Modal con enlace copiable
5. Haz clic en "Copiar"
6. **Deberías ver**: "Enlace copiado al portapapeles!"

### Paso 4: Aceptar Invitación
1. Copia el enlace del modal
2. **Abre en nueva ventana anónima** (para simular otro usuario)
3. Pega el enlace
4. **Deberías ser redirigido a login** (porque aún no tienes sesión)
5. Inicia sesión (puedes usar Google o Apple nuevamente)
6. **Automáticamente**, deberías ser redirigido y ver:
   - "✅ ¡Invitación aceptada!"
   - Botón "Ir a la app"
7. Haz clic en "Ir a la app"
8. **Deberías ver**: La lista compartida

### Paso 5: Verificar Acceso
1. Ve a "Mis listas"
2. **Deberías ver**: La lista con nivel "VER" (no puedes editar)
3. Intenta editar un artículo
4. **Deberías ver error**: "No tienes permiso"

---

## Test 4: Compartir por WhatsApp

### Paso 1: Desde el Modal de Ajustes
1. En sección "Miembros de la lista"
2. Busca sección "Compartir lista"
3. Ve al campo de "WhatsApp" (botón verde 💬)
4. Haz clic en "WhatsApp"

### Paso 2: Verificar
1. **En desktop**: Deberías ver http://web.whatsapp.com
2. **En móvil**: Se debería abrir la app de WhatsApp
3. Deberías ver un mensaje preformateado como:
   ```
   Hola! Te quiero compartir mi lista de compra "Lista Prueba" 
   en Dreame! (aplicacion de listas compartidas).
   
   Puedes verla y actualizarla en tiempo real.
   ```

### Paso 3: Con Número de Teléfono
1. En campo "Teléfono" (optional), ingresa: `+34612345678`
2. Haz clic en "WhatsApp"
3. **Deberías ver**: Chat directo con ese número (si tienes WhatsApp)

---

## Test 5: Cambiar Contraseña

### Paso 1: Crear Usuario con Password
1. Cierra sesión
2. Abre http://localhost:5000/login
3. **Si es la primera vez**, verás formulario de registro
4. Ingresa:
   - Usuario: `test_user`
   - Contraseña: `test123`
   - Confirmar: `test123`
5. Haz clic en "Crear cuenta y entrar"
6. **Deberías estar logueado**

### Paso 2: Cambiar Contraseña
1. Abre DevTools (F12)
2. Abre pestaña "Console"
3. Ejecuta:
   ```javascript
   fetch('/api/auth/cambiar-password', {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({
       password_actual: 'test123',
       password_nueva: 'test456',
       password_confirmacion: 'test456'
     })
   }).then(r => r.json()).then(console.log)
   ```
4. **Deberías ver**: `{"exito": true, "mensaje": "Contraseña cambiada correctamente"}`

### Paso 3: Verificar
1. Cierra sesión
2. Intenta login con contraseña antigua (`test123`)
3. **Deberías ver error**: "Usuario o contraseña incorrectos"
4. Intenta login con contraseña nueva (`test456`)
5. **Deberías estar logueado**

---

## Test 6: Búsqueda de Usuarios

### Paso 1: Crear Dos Usuarios
1. Crea usuario 1: `usuario1` (con password o OAuth)
2. Crea usuario 2: `usuario2` (con password o OAuth)

### Paso 2: Buscar desde Usuario 2
1. **Logueado como usuario2**
2. Abre DevTools (F12)
3. En pestaña "Console", ejecuta:
   ```javascript
   fetch('/api/listas/buscar-usuarios?q=usuario1')
     .then(r => r.json())
     .then(console.log)
   ```
4. **Deberías ver**:
   ```json
   {
     "exito": true,
     "data": {
       "usuarios": [
         {
           "id": 1,
           "nombre_usuario": "usuario1",
           "email": "..."
         }
       ]
     }
   }
   ```

### Paso 3: Búsqueda por Email
1. Ejecuta:
   ```javascript
   fetch('/api/listas/buscar-usuarios?q=usuario1@example')
     .then(r => r.json())
     .then(console.log)
   ```
2. **Deberías ver**: El usuario encontrado

---

## Checklist de Testing Completo

### OAuth
- [ ] Google OAuth funciona
- [ ] Apple OAuth funciona
- [ ] Usuario creado automáticamente
- [ ] Email registrado

### Compartir
- [ ] Enlace de invitación se genera
- [ ] Enlace se puede copiar
- [ ] Enlace caduca después de 7 días
- [ ] Invitación puede aceptarse

### Permisos
- [ ] Nivel "Ver" restringe edición
- [ ] Nivel "Editar" permite cambios
- [ ] Propietario tiene control total

### WhatsApp
- [ ] Botón WhatsApp abre chat
- [ ] Con número específico funciona
- [ ] Mensaje está preformateado

### Contraseña
- [ ] Cambio de contraseña funciona
- [ ] Contraseña antigua no funciona
- [ ] Contraseña nueva funciona

### Búsqueda
- [ ] Búsqueda por username funciona
- [ ] Búsqueda por email funciona
- [ ] Usuario actual excluido
- [ ] Máximo 10 resultados

---

## Solucionar Problemas

### Google OAuth no funciona
```
Error: "redirect_uri_mismatch"
Solución: Verifica que APP_URL en .env coincida con 
          OAuth Redirect URIs en Google Console
```

### Apple OAuth no funciona
```
Error: "invalid_client"
Solución: Verifica que APPLE_CLIENT_ID y APPLE_CLIENT_SECRET 
          sean correctos
```

### Invitación no se acepta
```
Error: "Invitación no encontrada"
Solución: El enlace puede haber expirado (7 días)
          O el código es inválido
```

### WhatsApp no abre
```
En desktop: Puede abrir web.whatsapp.com en lugar de app
En móvil: Asegúrate de tener WhatsApp instalado
```

---

## Recursos

- OAuth 2.0: https://tools.ietf.org/html/rfc6749
- Google OAuth: https://developers.google.com/identity/protocols/oauth2
- Apple OAuth: https://developer.apple.com/sign-in-with-apple/
- JWT: https://jwt.io/
