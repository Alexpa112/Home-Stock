# 🔐 Configuración Google OAuth + Apple OAuth

## 1. GOOGLE OAUTH

### Paso 1: Crear Proyecto en Google Cloud

1. Ve a https://console.cloud.google.com/
2. Haz clic en "Crear proyecto"
3. Nombre: `Dreame Shopping Lists`
4. Haz clic en "Crear"

### Paso 2: Habilitar OAuth 2.0 API

1. En el menú lateral, ve a "APIs y servicios"
2. Haz clic en "Habilitar APIs y servicios"
3. Busca "Google+ API" o "OAuth 2.0"
4. Haz clic en "Habilitar"

### Paso 3: Crear Pantalla de Consentimiento OAuth

1. En "APIs y servicios", ve a "Pantalla de consentimiento OAuth"
2. Elige "Externo" como tipo de usuario
3. Haz clic en "Crear"
4. Completa:
   - **Nombre de app**: Dreame!
   - **Email de soporte**: tu_email@gmail.com
   - **Permisos**: Deja por defecto
   - Haz clic en "Guardar y continuar"
5. En "Información de contacto del desarrollador":
   - Email: tu_email@gmail.com
   - Haz clic en "Guardar y finalizar"

### Paso 4: Crear Credenciales OAuth

1. En "APIs y servicios", ve a "Credenciales"
2. Haz clic en "Crear credenciales" → "ID de cliente OAuth"
3. Tipo de aplicación: **Aplicación web**
4. Nombre: `Dreame Web Client`
5. En "URI autorizados de redirección":
   ```
   http://localhost:5000/auth/google/callback
   https://tudominio.com/auth/google/callback  (en producción)
   ```
6. Haz clic en "Crear"
7. **Copiar valores**:
   - Client ID
   - Client Secret

### Resultado
```
GOOGLE_CLIENT_ID=xxxxxxxxxxxxxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxx
```

---

## 2. APPLE OAUTH

### Requisitos Previos
- Cuenta de desarrollador Apple ($99/año)
- Identificador de equipo Apple

### Paso 1: Crear App ID

1. Ve a https://developer.apple.com/account/
2. En "Certificates, Identifiers & Profiles", selecciona "Identifiers"
3. Haz clic en "+" para crear nuevo identifier
4. Selecciona "App IDs"
5. Elige "App"
6. Completa:
   - **Descripción**: Dreame Shopping Lists
   - **Bundle ID**: com.dreame.shoppinglists
7. En "Capabilities", busca y activa "Sign in with Apple"
8. Haz clic en "Continuar" y luego "Registrar"

### Paso 2: Crear Service ID

1. En "Identifiers", haz clic en "+" nuevamente
2. Selecciona "Services IDs"
3. Completa:
   - **Descripción**: Dreame Web Service
   - **Identifier**: com.dreame.web (este es tu APPLE_CLIENT_ID)
4. Activa "Sign in with Apple"
5. Haz clic en "Configurar"
6. En "Web Authentication Configuration":
   - Primary App ID: com.dreame.shoppinglists
   - Domains and Subdomains:
     ```
     localhost
     tudominio.com  (en producción)
     ```
   - Return URLs:
     ```
     http://localhost:5000/auth/apple/callback
     https://tudominio.com/auth/apple/callback
     ```
7. Haz clic en "Guardar"

### Paso 3: Crear Clave Privada

1. En "Certificates, Identifiers & Profiles", ve a "Keys"
2. Haz clic en "+" para crear nueva key
3. Nombre: `Dreame Web Key`
4. Activa "Sign in with Apple"
5. Haz clic en "Configurar"
6. Primary App ID: selecciona tu app
7. Haz clic en "Guardar"
8. Haz clic en "Crear"
9. **Descarga la clave** (archivo .p8)
   - **Guarda en lugar seguro** - no se puede descargar de nuevo
   - Anotate el Key ID

### Resultado
```
APPLE_CLIENT_ID=com.dreame.web
APPLE_TEAM_ID=XXXXXXXXXX  (10 caracteres, en tu account)
APPLE_CLIENT_SECRET=<contenido de archivo .p8>  (o generado con JWT)
```

### Generar Client Secret (Avanzado)

Para producción, Apple requiere generar un JWT como client secret:

```python
import jwt
import time

private_key = open('AuthKey_XXXXX.p8').read()
team_id = 'XXXXXXXXXX'
client_id = 'com.dreame.web'
key_id = 'XXXXX'

payload = {
    'iss': team_id,
    'sub': client_id,
    'aud': 'https://appleid.apple.com',
    'iat': int(time.time()),
    'exp': int(time.time()) + 15777000
}

secret = jwt.encode(payload, private_key, algorithm='ES256', headers={'kid': key_id})
print(secret)
```

---

## 3. VERIFICAR CONFIGURACIÓN

### Paso 1: Crear .env

```bash
cp .env.example .env
```

### Paso 2: Completar Credenciales

```env
# OAuth - Google
GOOGLE_CLIENT_ID=xxxxxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxx

# OAuth - Apple
APPLE_CLIENT_ID=com.dreame.web
APPLE_TEAM_ID=XXXXXXXXXX
APPLE_CLIENT_SECRET=<tu-client-secret>

# Email (puede dejarse vacío para desarrollo)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=

# App
APP_URL=http://localhost:5000
```

### Paso 3: Probar

```bash
python test_features.py
# Debe mostrar: All tests passed!
```

### Paso 4: Iniciar Servidor

```bash
python run.py
# Abre http://localhost:5000/login
```

### Paso 5: Probar OAuth

1. Haz clic en "Continuar con Google"
   - Te llevará a login de Google
   - Autoriza el acceso
   - Deberías entrar automáticamente

2. Cierra sesión (⚙️ → Cerrar sesión)

3. Haz clic en "Continuar con Apple"
   - Te llevará a login de Apple
   - Autoriza el acceso
   - Deberías entrar automáticamente

---

## 4. SOLUCIONAR PROBLEMAS

### Error: "Invalid redirect_uri"
- Verifica que `APP_URL` en .env coincida con URL en credentials
- En Google: comprueba "Authorized redirect URIs"
- En Apple: comprueba "Return URLs"

### Error: "The client ID was not recognized"
- Verifica que `GOOGLE_CLIENT_ID` / `APPLE_CLIENT_ID` son correctos
- Copia desde consola sin espacios en blanco

### Error: "Client authentication failed"
- Para Google: verifica `GOOGLE_CLIENT_SECRET`
- Para Apple: verifica `APPLE_CLIENT_SECRET` o JWT válido

### El botón OAuth no aparece
- Verifica que no estés en modo setup (primera vez)
- Los botones solo aparecen después de crear primer usuario

---

## 5. PRODUCCIÓN

### Cambios para Producción

1. **Actualizar APP_URL en .env**
   ```env
   APP_URL=https://tudominio.com
   ```

2. **Agregar URLs a Google Cloud**
   - Console.cloud.google.com
   - Credenciales → OAuth Client
   - Authorized redirect URIs:
     ```
     https://tudominio.com/auth/google/callback
     ```

3. **Agregar URLs a Apple Developer**
   - developer.apple.com
   - Service ID → Web Authentication
   - Return URLs:
     ```
     https://tudominio.com/auth/apple/callback
     ```

4. **Usar certificado SSL/HTTPS** (obligatorio para OAuth)

5. **Cambiar SECRET_KEY en config.py** si es necesario

---

## 6. REFERENCIAS

- Google OAuth: https://developers.google.com/identity/protocols/oauth2
- Apple OAuth: https://developer.apple.com/sign-in-with-apple/
- OAuth 2.0: https://tools.ietf.org/html/rfc6749
