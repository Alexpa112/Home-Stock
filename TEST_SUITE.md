# HOME-STOCK TEST SUITE

Batería exhaustiva de pruebas automatizadas para verificar que todos los campos, botones, validaciones y funcionalidad del programa funcionan correctamente.

## Ejecución

```bash
# PowerShell
.\run_tests.ps1

# Bash
bash test_suite.sh
```

## Qué verifica

### 1. Estructura HTML (5 pruebas)
- ✅ Título de la página
- ✅ Formulario principal
- ✅ Secciones de login y registro
- ✅ Botón de alternar entre login/registro

### 2. Inputs (7 pruebas)
Verifica que existen todos los inputs con los IDs correctos:
- `campoUsuario` - usuario (login)
- `campoPassword` - contraseña (login)
- `campoNombre` - nombre completo (registro)
- `campoEmail` - email (registro)
- `campoUsuarioReg` - usuario (registro)
- `campoPasswordReg` - contraseña (registro)
- `campoPassword2Reg` - confirmar contraseña (registro)

### 3. Atributos Name (5 pruebas)
Verifica que cada input tiene el atributo `name` correcto:
- `name="usuario"`
- `name="password"`
- `name="email"`
- `name="nombre"`
- `name="password2"`

### 4. Labels y Accesibilidad (7 pruebas)
Verifica que cada input tiene un label con `for` vinculado:
- `<label for="campoUsuario">Usuario</label>`
- `<label for="campoPassword">Contraseña</label>`
- (y 5 más para los otros inputs)

### 5. Validación HTML5 (4 pruebas)
- ✅ Inputs `required`
- ✅ `minlength="8"` en contraseñas
- ✅ `type="email"` para email
- ✅ `type="password"` para contraseñas

### 6. Botones (3 pruebas)
- ✅ Botón submit del formulario
- ✅ Botón Google OAuth
- ✅ Botón Apple OAuth

### 7. JavaScript (4 pruebas)
- ✅ Función `mostrarLogin()`
- ✅ Función `mostrarRegistro()`
- ✅ Event listeners definidos
- ✅ Fetch API en uso

### 8. API Endpoints (2 pruebas)
- ✅ GET `/api/auth/estado`
- ✅ POST `/api/auth/login` (con credenciales válidas)

### 9. Estilos CSS (3 pruebas)
- ✅ Clase `tarjeta-login`
- ✅ Clase `primario`
- ✅ Clase `oauth-button`

## Total: 40 pruebas

## Cuándo ejecutar

**Ejecutar SIEMPRE después de cambios importantes en:**
- `stockhogar/templates/login.html` (cualquier cambio)
- `stockhogar/rutas/auth.py` (endpoints de auth)
- `stockhogar/static/` (estilos o JavaScript)
- `requirements.txt` (dependencias)

## Ejemplo de flujo

```bash
# 1. Haces un cambio en login.html
# ... editas el archivo ...

# 2. Reinicia servidor y limpia caché (REGLA 8 en CLAUDE.md)
pkill -f "python run.py"
rm -rf __pycache__ *.pyc instance
python run.py &

# 3. Ejecuta las pruebas
.\run_tests.ps1

# 4. Si todas pasan (40/40 100%), puedes hacer commit
git add ...
git commit -m "..."
```

## Resultado esperado

```
HOME-STOCK TEST SUITE
====================

ESTRUCTURA HTML:
PASS: Titulo es Dreame!
... [más pruebas] ...

========================
RESULTADOS: 40/40 (100%)
========================

SUCCESS: All tests passed!
```

## Fallos críticos vs advertencias

- **Critical**: Errores en estructura HTML, inputs, labels, API endpoints
- **Warning**: Errores en estilos CSS o clases (no rompen funcionalidad)

Si hay fallos críticos, el script sale con exit code 1.

## Automatización futura

Estos scripts pueden integrarse en CI/CD para ejecutarse automáticamente:
- Pre-commit hooks
- GitHub Actions
- GitLab CI
- Jenkins

## Archivos

- `run_tests.ps1` - Script PowerShell simplificado (recomendado)
- `test_suite.ps1` - Script PowerShell completo (más verboso)
- `test_suite.sh` - Script Bash (alternativa)
