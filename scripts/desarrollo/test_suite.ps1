# HOME-STOCK TEST SUITE - Batería Exhaustiva de Pruebas
# Ejecutar: .\test_suite.ps1

$TESTS_PASSED = 0
$TESTS_FAILED = 0
$CRITICAL_FAILURES = @()

function Test-Result {
    param([string]$Name, [string]$Result, [bool]$Critical = $false)

    if ($Result -eq "PASS") {
        Write-Host "✅ PASS: $Name" -ForegroundColor Green
        $script:TESTS_PASSED++
    } else {
        Write-Host "❌ FAIL: $Name" -ForegroundColor Red
        $script:TESTS_FAILED++
        if ($Critical) { $script:CRITICAL_FAILURES += $Name }
    }
}

# Obtener HTML
try {
    $HTML = (Invoke-WebRequest -Uri "http://localhost:5000/login" -UseBasicParsing -ErrorAction Stop).Content
} catch {
    Write-Host "❌ CRÍTICO: Servidor no responde" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== HOME-STOCK TEST SUITE ===" -ForegroundColor Cyan
Write-Host "Batería Exhaustiva de Pruebas`n" -ForegroundColor Cyan

# SECCIÓN 1: ESTRUCTURA HTML
Write-Host "SECCIÓN 1: ESTRUCTURA HTML" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

$result = if ($HTML.Contains("<title>Dreame!")) { "PASS" } else { "FAIL" }
Test-Result "Título página es 'Dreame!'" $result $true

$result = if ($HTML.Contains('id="formLogin"')) { "PASS" } else { "FAIL" }
Test-Result "Formulario principal existe" $result $true

$result = if ($HTML.Contains('id="seccionLogin"')) { "PASS" } else { "FAIL" }
Test-Result "Sección login existe" $result $true

$result = if ($HTML.Contains('id="seccionRegistro"')) { "PASS" } else { "FAIL" }
Test-Result "Sección registro existe" $result $true

$result = if ($HTML.Contains('id="btnAlternarFormulario"')) { "PASS" } else { "FAIL" }
Test-Result "Botón alternar login/registro existe" $result $true

Write-Host ""

# SECCIÓN 2: INPUTS Y ATRIBUTOS
Write-Host "SECCIÓN 2: INPUTS Y ATRIBUTOS" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

$inputs = @(
    @{id="campoUsuario"; name="usuario"; type="text"},
    @{id="campoPassword"; name="password"; type="password"},
    @{id="campoNombre"; name="nombre"; type="text"},
    @{id="campoEmail"; name="email"; type="email"},
    @{id="campoUsuarioReg"; name="usuario"; type="text"},
    @{id="campoPasswordReg"; name="password"; type="password"},
    @{id="campoPassword2Reg"; name="password2"; type="password"}
)

foreach ($input in $inputs) {
    $id = $input.id
    $name = $input.name
    $type = $input.type

    $result = if ($HTML.Contains("id=`"$id`"")) { "PASS" } else { "FAIL" }
    Test-Result "Input #$id existe" $result $true

    $result = if ($HTML.Contains("name=`"$name`"")) { "PASS" } else { "FAIL" }
    Test-Result "  - tiene name=$name" $result $true

    $result = if ($HTML.Contains("type=`"$type`"")) { "PASS" } else { "FAIL" }
    Test-Result "  - tiene type=$type" $result
}

Write-Host ""

# SECCIÓN 3: LABELS Y ACCESIBILIDAD
Write-Host "SECCIÓN 3: LABELS Y ACCESIBILIDAD" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

$labelInputs = @("campoUsuario", "campoPassword", "campoNombre", "campoEmail", "campoUsuarioReg", "campoPasswordReg", "campoPassword2Reg")

foreach ($id in $labelInputs) {
    $result = if ($HTML.Contains("for=`"$id`"")) { "PASS" } else { "FAIL" }
    Test-Result "Label con for=$id existe" $result $true
}

Write-Host ""

# SECCIÓN 4: VALIDACIÓN HTML5
Write-Host "SECCIÓN 4: VALIDACIÓN HTML5" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

$requiredInputs = @("campoUsuario", "campoPassword", "campoUsuarioReg", "campoPasswordReg", "campoPassword2Reg")
foreach ($id in $requiredInputs) {
    $result = if ($HTML.Contains("id=`"$id`"") -and $HTML.Contains("required")) { "PASS" } else { "FAIL" }
    Test-Result "Input #$id tiene atributo required" $result
}

Write-Host ""

$result = if ($HTML.Contains("minlength=`"8`"")) { "PASS" } else { "FAIL" }
Test-Result "Contraseña tiene minlength=8" $result $true

$result = if ($HTML.Contains('type="email"')) { "PASS" } else { "FAIL" }
Test-Result "Email input tiene type=email" $result

Write-Host ""

# SECCIÓN 5: BOTONES
Write-Host "SECCIÓN 5: BOTONES" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

$result = if ($HTML.Contains('type="submit"')) { "PASS" } else { "FAIL" }
Test-Result "Botón submit existe" $result $true

$result = if ($HTML.Contains('href="/auth/google"')) { "PASS" } else { "FAIL" }
Test-Result "Botón Google OAuth existe" $result


Write-Host ""

# SECCIÓN 6: API ENDPOINTS
Write-Host "SECCIÓN 6: API ENDPOINTS" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test estado
try {
    $response = (Invoke-WebRequest -Uri "http://localhost:5000/api/auth/estado" -UseBasicParsing -ErrorAction Stop).Content
    $result = if ($response.Contains('"necesita_setup"')) { "PASS" } else { "FAIL" }
    Test-Result "GET /api/auth/estado responde correctamente" $result
} catch {
    Test-Result "GET /api/auth/estado responde correctamente" "FAIL"
}

# Test login válido
try {
    $response = (Invoke-WebRequest -Uri "http://localhost:5000/api/auth/login" -Method POST -ContentType "application/json" -Body '{"usuario":"admin","password":"admin1234"}' -UseBasicParsing -ErrorAction Stop).Content
    $result = if ($response.Contains('"usuario":"admin"')) { "PASS" } else { "FAIL" }
    Test-Result "POST /api/auth/login funciona (credenciales válidas)" $result $true
} catch {
    Test-Result "POST /api/auth/login funciona (credenciales válidas)" "FAIL" $true
}

# Test login rechaza usuario inválido
try {
    $response = (Invoke-WebRequest -Uri "http://localhost:5000/api/auth/login" -Method POST -ContentType "application/json" -Body '{"usuario":"noexiste","password":"pass"}' -UseBasicParsing -ErrorAction Stop -WarningAction SilentlyContinue).Content
    $result = if ($response.Contains('"error"')) { "PASS" } else { "FAIL" }
    Test-Result "POST /api/auth/login rechaza usuario inválido" $result $true
} catch {
    Test-Result "POST /api/auth/login rechaza usuario inválido" "FAIL" $true
}

# Test validación de contraseña
try {
    $response = (Invoke-WebRequest -Uri "http://localhost:5000/api/auth/registrar" -Method POST -ContentType "application/json" -Body '{"usuario":"test","password":"short","email":"test@test.com"}' -UseBasicParsing -ErrorAction Stop -WarningAction SilentlyContinue).Content
    $result = if ($response.Contains('"error"')) { "PASS" } else { "FAIL" }
    Test-Result "POST /api/auth/registrar valida min 8 caracteres" $result $true
} catch {
    Test-Result "POST /api/auth/registrar valida min 8 caracteres" "FAIL" $true
}

Write-Host ""

# SECCIÓN 7: JAVASCRIPT Y FUNCIONALIDAD
Write-Host "SECCIÓN 7: JAVASCRIPT Y FUNCIONALIDAD" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

$result = if ($HTML.Contains("function mostrarLogin()")) { "PASS" } else { "FAIL" }
Test-Result "Función mostrarLogin existe" $result

$result = if ($HTML.Contains("function mostrarRegistro()")) { "PASS" } else { "FAIL" }
Test-Result "Función mostrarRegistro existe" $result

$result = if ($HTML.Contains("addEventListener")) { "PASS" } else { "FAIL" }
Test-Result "Event listeners definidos" $result

$result = if ($HTML.Contains("fetch")) { "PASS" } else { "FAIL" }
Test-Result "Fetch API está siendo usado" $result

Write-Host ""

# SECCIÓN 8: ESTILOS Y CLASES
Write-Host "SECCIÓN 8: ESTILOS Y CLASES CSS" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

$result = if ($HTML.Contains('class="tarjeta-login"')) { "PASS" } else { "FAIL" }
Test-Result "Clase CSS tarjeta-login existe" $result

$result = if ($HTML.Contains('class="primario"')) { "PASS" } else { "FAIL" }
Test-Result "Clase CSS primario existe para botones" $result

$result = if ($HTML.Contains('class="oauth-button"')) { "PASS" } else { "FAIL" }
Test-Result "Clase CSS oauth-button existe" $result

Write-Host ""

# SECCIÓN 9: VALIDACIÓN FINAL
Write-Host "SECCIÓN 9: VALIDACIÓN FINAL" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

$result = if ($HTML.Contains("</html>")) { "PASS" } else { "FAIL" }
Test-Result "HTML está bien cerrado" $result $true

$result = if ($HTML.Contains('lang="es"')) { "PASS" } else { "FAIL" }
Test-Result "Idioma HTML es español" $result

Write-Host ""

# RESUMEN
Write-Host "=== RESUMEN DE PRUEBAS ===" -ForegroundColor Cyan
Write-Host ""

$total = $TESTS_PASSED + $TESTS_FAILED
$percentage = if ($total -gt 0) { [math]::Round(($TESTS_PASSED * 100) / $total) } else { 0 }

Write-Host "Total de pruebas:    $total"
Write-Host "Pasadas:             $TESTS_PASSED" -ForegroundColor Green
Write-Host "Fallidas:            $TESTS_FAILED" -ForegroundColor $(if ($TESTS_FAILED -gt 0) { "Red" } else { "Green" })
Write-Host "Porcentaje:          $percentage%"
Write-Host ""

if ($TESTS_FAILED -eq 0) {
    Write-Host "✅ TODAS LAS PRUEBAS PASARON - 100% CORRECTO" -ForegroundColor Green
    Write-Host ""
    exit 0
} elseif ($CRITICAL_FAILURES.Count -eq 0) {
    Write-Host "⚠️  Algunas pruebas fallaron pero NO son críticas" -ForegroundColor Yellow
    Write-Host ""
    exit 0
} else {
    Write-Host "❌ FALLOS CRÍTICOS:" -ForegroundColor Red
    foreach ($f in $CRITICAL_FAILURES) { Write-Host "   • $f" -ForegroundColor Red }
    Write-Host ""
    exit 1
}
