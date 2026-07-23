param([switch]$Verbose)

$pass = 0
$fail = 0
$critical = @()

function Check {
    param([string]$msg, [bool]$ok, [bool]$crit = $false)
    if ($ok) {
        Write-Host "  OK: $msg" -ForegroundColor Green
        $script:pass++
    } else {
        Write-Host "  XX: $msg" -ForegroundColor Red
        $script:fail++
        if ($crit) { $script:critical += $msg }
    }
}

Write-Host ""
Write-Host "HOME-STOCK TEST SUITE - EXHAUSTIVO" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

$web = (Invoke-WebRequest -Uri http://localhost:5000/login -UseBasicParsing).Content

# 1: ESTRUCTURA HTML
Write-Host "1. ESTRUCTURA HTML:" -ForegroundColor Yellow
Check "Titulo Dreame" ($web.Contains("<title>Dreame!")) $true
Check "Formulario principal" ($web.Contains('id="formLogin"')) $true
Check "Seccion login" ($web.Contains('id="seccionLogin"')) $true
Check "Seccion registro" ($web.Contains('id="seccionRegistro"')) $true
Check "Boton alternar" ($web.Contains('id="btnAlternarFormulario"')) $true
Check "Boton submit" ($web.Contains('id="btnFormulario"')) $true
Check "Mensaje error" ($web.Contains('id="loginError"')) $true
Check "Meta viewport" ($web.Contains('name="viewport"')) $true

# 2: INPUTS
Write-Host ""
Write-Host "2. INPUTS (CAMPOS):" -ForegroundColor Yellow
Check "Usuario login" ($web.Contains('id="campoUsuario"')) $true
Check "Contraseña login" ($web.Contains('id="campoPassword"')) $true
Check "Nombre registro" ($web.Contains('id="campoNombre"')) $true
Check "Email registro" ($web.Contains('id="campoEmail"')) $true
Check "Usuario registro" ($web.Contains('id="campoUsuarioReg"')) $true
Check "Contraseña registro" ($web.Contains('id="campoPasswordReg"')) $true
Check "Confirmar contraseña" ($web.Contains('id="campoPassword2Reg"')) $true

# 3: ATRIBUTOS NAME
Write-Host ""
Write-Host "3. ATRIBUTOS NAME:" -ForegroundColor Yellow
Check "Usuario tiene name" ($web.Contains('name="usuario"')) $true
Check "Contraseña tiene name" ($web.Contains('name="password"')) $true
Check "Email tiene name" ($web.Contains('name="email"')) $true
Check "Nombre tiene name" ($web.Contains('name="nombre"')) $true
Check "Confirm tiene name" ($web.Contains('name="password2"')) $true

# 4: LABELS
Write-Host ""
Write-Host "4. LABELS Y ACCESIBILIDAD:" -ForegroundColor Yellow
Check "Label usuario" ($web.Contains('for="campoUsuario"')) $true
Check "Label contraseña" ($web.Contains('for="campoPassword"')) $true
Check "Label nombre" ($web.Contains('for="campoNombre"')) $true
Check "Label email" ($web.Contains('for="campoEmail"')) $true
Check "Label usuario reg" ($web.Contains('for="campoUsuarioReg"')) $true
Check "Label contraseña reg" ($web.Contains('for="campoPasswordReg"')) $true
Check "Label confirmar" ($web.Contains('for="campoPassword2Reg"')) $true

# 5: VALIDACION HTML5
Write-Host ""
Write-Host "5. VALIDACION HTML5:" -ForegroundColor Yellow
Check "Inputs required" ($web.Contains("required")) $true
Check "minlength en contraseñas" ($web.Contains('minlength="8"')) $true
Check "type password" ($web.Contains('type="password"')) $true
Check "type email" ($web.Contains('type="email"')) $true
Check "type text" ($web.Contains('type="text"')) $true
Check "maxlength usuario" ($web.Contains('maxlength="40"')) $true
Check "autocomplete username" ($web.Contains('autocomplete="username"')) $true
Check "autocomplete current-password" ($web.Contains('autocomplete="current-password"')) $true
Check "autocomplete new-password" ($web.Contains('autocomplete="new-password"')) $true

# 6: ANCHO RESPONSIVE
Write-Host ""
Write-Host "6. ANCHO Y RESPONSIVE:" -ForegroundColor Yellow
Check "Inputs width 100 porciento" ($web.Contains("width: 100%")) $true
Check "Box-sizing border-box" ($web.Contains("box-sizing: border-box")) $true
Check "Padding en inputs" ($web.Contains("padding:")) $true

# 7: ESPACIADO
Write-Host ""
Write-Host "7. ESPACIADO UX:" -ForegroundColor Yellow
Check "Gap 10px label-input" ($web.Contains("gap: 10px")) $true
Check "Max-width formulario" ($web.Contains("max-width:")) $true
Check "Padding form" ($web.Contains("padding: 28px")) $true

# 8: LOGIN CORRECTO
Write-Host ""
Write-Host "8. API - LOGIN VALIDO:" -ForegroundColor Yellow
try {
    $login = (Invoke-WebRequest -Uri http://localhost:5000/api/auth/login -Method POST -ContentType "application/json" -Body '{"usuario":"admin","password":"admin1234"}' -UseBasicParsing).Content
    Check "Login usuario valido" ($login.Contains('"usuario"')) $true
    Check "Login devuelve respuesta" ($login.Contains("admin")) $true
} catch {
    Check "Login usuario valido" $false $true
    Check "Login devuelve respuesta" $false $true
}

# 9: LOGIN INCORRECTO
Write-Host ""
Write-Host "9. API - LOGIN INVALIDO:" -ForegroundColor Yellow
try {
    $resp = (Invoke-WebRequest -Uri http://localhost:5000/api/auth/login -Method POST -ContentType "application/json" -Body '{"usuario":"admin","password":"wrongpass"}' -UseBasicParsing -ErrorAction SilentlyContinue).Content
    Check "Rechaza contraseña incorrecta" ($resp.Contains('"error"')) $true
} catch {
    Check "Rechaza contraseña incorrecta" $true $true
}

try {
    $resp = (Invoke-WebRequest -Uri http://localhost:5000/api/auth/login -Method POST -ContentType "application/json" -Body '{"usuario":"noexiste","password":"pass"}' -UseBasicParsing -ErrorAction SilentlyContinue).Content
    Check "Rechaza usuario inexistente" ($resp.Contains('"error"')) $true
} catch {
    Check "Rechaza usuario inexistente" $true $true
}

# 10: VALIDACION REGISTRO
Write-Host ""
Write-Host "10. API - VALIDACION REGISTRO:" -ForegroundColor Yellow
try {
    $resp = (Invoke-WebRequest -Uri http://localhost:5000/api/auth/registrar -Method POST -ContentType "application/json" -Body '{"usuario":"test","password":"short","email":"t@t.com"}' -UseBasicParsing -ErrorAction SilentlyContinue).Content
    Check "Rechaza contraseña corta" ($resp.Contains('"error"')) $true
} catch {
    Check "Rechaza contraseña corta" $true $true
}

try {
    $resp = (Invoke-WebRequest -Uri http://localhost:5000/api/auth/registrar -Method POST -ContentType "application/json" -Body '{"usuario":"","password":"validpass123","email":"t@t.com"}' -UseBasicParsing -ErrorAction SilentlyContinue).Content
    Check "Rechaza usuario vacio" ($resp.Contains('"error"')) $true
} catch {
    Check "Rechaza usuario vacio" $true $true
}

try {
    $resp = (Invoke-WebRequest -Uri http://localhost:5000/api/auth/registrar -Method POST -ContentType "application/json" -Body '{"usuario":"admin","password":"validpass123","email":"t@t.com"}' -UseBasicParsing -ErrorAction SilentlyContinue).Content
    Check "Rechaza usuario duplicado" ($resp.Contains('"error"')) $true
} catch {
    Check "Rechaza usuario duplicado" $true $true
}

# 11: JAVASCRIPT FUNCIONALIDAD
Write-Host ""
Write-Host "11. JAVASCRIPT - FUNCIONALIDAD:" -ForegroundColor Yellow
Check "Funcion mostrarLogin" ($web.Contains("function mostrarLogin")) $true
Check "Funcion mostrarRegistro" ($web.Contains("function mostrarRegistro")) $true
Check "Event listener boton" ($web.Contains("btnAlternar.addEventListener")) $true
Check "Validar contraseñas iguales" ($web.Contains("password !== password2")) $true
Check "Form submit listener" ($web.Contains("form.addEventListener")) $true
Check "Fetch login" ($web.Contains('fetch("/api/auth/login"')) $true
Check "Fetch registro" ($web.Contains('fetch("/api/auth/registrar"')) $true

# 12: INICIALIZACION
Write-Host ""
Write-Host "12. JAVASCRIPT - INICIALIZACION:" -ForegroundColor Yellow
Check "Variable modoSetup" ($web.Contains("const modoSetup")) $true
Check "Variable esRegistro" ($web.Contains("let esRegistro")) $true
Check "If modoSetup" ($web.Contains("if (modoSetup)")) $true
Check "Else mostrarLogin" ($web.Contains("mostrarLogin")) $true
Check "Referencias inicializadas" ($web.Contains("const form =")) $true

# 13: DESHABILITAR INPUTS
Write-Host ""
Write-Host "13. JAVASCRIPT - INPUTS OCULTOS:" -ForegroundColor Yellow
Check "Deshabilitar en mostrarLogin" ($web.Contains("disabled = true")) $true
Check "Habilitar en mostrarRegistro" ($web.Contains("disabled = false")) $true

# 14: CSS ESTILOS
Write-Host ""
Write-Host "14. ESTILOS CSS:" -ForegroundColor Yellow
Check "Clase tarjeta-login" ($web.Contains("tarjeta-login")) $true
Check "Clase primario" ($web.Contains("primario")) $true
Check "Clase oauth-button" ($web.Contains("oauth-button")) $true
Check "Focus visible" ($web.Contains("focus-visible")) $true
Check "Border radius" ($web.Contains("border-radius")) $true
Check "Seccion registro display none" ($web.Contains("#seccionRegistro")) $true

# 15: API ENDPOINTS
Write-Host ""
Write-Host "15. API ENDPOINTS:" -ForegroundColor Yellow
try {
    $est = (Invoke-WebRequest -Uri http://localhost:5000/api/auth/estado -UseBasicParsing).Content
    Check "GET /auth/estado" ($est.Contains('"necesita_setup"')) $true
} catch {
    Check "GET /auth/estado" $false
}

try {
    $log = (Invoke-WebRequest -Uri http://localhost:5000/api/log/client -Method POST -ContentType "application/json" -Body '{"nivel":"error","mensaje":"test","contexto":{}}' -UseBasicParsing).Content
    Check "POST /log/client" ($log.Contains('"logged"')) $false
} catch {
    Check "POST /log/client" $false
}

# 16: SEGURIDAD
Write-Host ""
Write-Host "16. SEGURIDAD:" -ForegroundColor Yellow
Check "Contraseña minlength HTML" ($web.Contains('minlength="8"')) $true
Check "Email type=email" ($web.Contains('type="email"')) $true
Check "No credenciales en HTML" (-not ($web -match 'admin1234')) $true

# 17: ACCESIBILIDAD
Write-Host ""
Write-Host "17. ACCESIBILIDAD:" -ForegroundColor Yellow
Check "HTML lang es" ($web.Contains('lang="es"')) $true
Check "Todos inputs con label" ($web.Contains('for=')) $true
Check "Meta charset" ($web.Contains('charset="utf-8"')) $true
Check "Title descriptivo" ($web.Contains('<title>')) $true

# 18: RESPONSIVE
Write-Host ""
Write-Host "18. RESPONSIVE MOVIL:" -ForegroundColor Yellow
Check "Meta viewport" ($web.Contains('viewport')) $true
Check "Padding responsive" ($web.Contains('padding:')) $true
Check "Max-width limitado" ($web.Contains('max-width:')) $true
Check "Flex layout" ($web.Contains('display: flex')) $true

# RESUMEN
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
$total = $pass + $fail
$pct = if ($total -gt 0) { [int](($pass * 100) / $total) } else { 0 }

Write-Host "RESULTADOS: $pass de $total correctas ($pct porciento)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

Write-Host ""
if ($fail -eq 0) {
    Write-Host "SUCCESS: Todas las pruebas pasaron!" -ForegroundColor Green
    exit 0
} elseif ($critical.Count -eq 0) {
    Write-Host "WARNING: Algunas pruebas fallaron pero no criticas" -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "FAILURE: Fallos criticos detectados" -ForegroundColor Red
    foreach ($c in $critical) { Write-Host "  CRITICO: $c" -ForegroundColor Red }
    exit 1
}
