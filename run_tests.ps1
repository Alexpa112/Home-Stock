param([switch]$Verbose)

$pass = 0
$fail = 0

function Check {
    param([string]$msg, [bool]$ok)
    if ($ok) {
        Write-Host "PASS: $msg" -ForegroundColor Green
        $script:pass++
    } else {
        Write-Host "FAIL: $msg" -ForegroundColor Red
        $script:fail++
    }
}

Write-Host ""
Write-Host "HOME-STOCK TEST SUITE" -ForegroundColor Cyan
Write-Host "====================`n" -ForegroundColor Cyan

$web = (Invoke-WebRequest -Uri http://localhost:5000/login -UseBasicParsing).Content

Write-Host "ESTRUCTURA HTML:" -ForegroundColor Yellow
Check "Titulo es Dreame!" ($web.Contains("<title>Dreame!"))
Check "Formulario existe" ($web.Contains('id="formLogin"'))
Check "Seccion login existe" ($web.Contains('id="seccionLogin"'))
Check "Seccion registro existe" ($web.Contains('id="seccionRegistro"'))
Check "Boton alternar existe" ($web.Contains('id="btnAlternarFormulario"'))

Write-Host "`nINPUTS:" -ForegroundColor Yellow
Check "Input campoUsuario" ($web.Contains('id="campoUsuario"'))
Check "Input campoPassword" ($web.Contains('id="campoPassword"'))
Check "Input campoNombre" ($web.Contains('id="campoNombre"'))
Check "Input campoEmail" ($web.Contains('id="campoEmail"'))
Check "Input campoUsuarioReg" ($web.Contains('id="campoUsuarioReg"'))
Check "Input campoPasswordReg" ($web.Contains('id="campoPasswordReg"'))
Check "Input campoPassword2Reg" ($web.Contains('id="campoPassword2Reg"'))

Write-Host "`nATRIBUTOS NAME:" -ForegroundColor Yellow
Check "name=usuario" ($web.Contains('name="usuario"'))
Check "name=password" ($web.Contains('name="password"'))
Check "name=email" ($web.Contains('name="email"'))
Check "name=nombre" ($web.Contains('name="nombre"'))
Check "name=password2" ($web.Contains('name="password2"'))

Write-Host "`nLABELS Y ACCESIBILIDAD:" -ForegroundColor Yellow
Check "Label for=campoUsuario" ($web.Contains('for="campoUsuario"'))
Check "Label for=campoPassword" ($web.Contains('for="campoPassword"'))
Check "Label for=campoNombre" ($web.Contains('for="campoNombre"'))
Check "Label for=campoEmail" ($web.Contains('for="campoEmail"'))
Check "Label for=campoUsuarioReg" ($web.Contains('for="campoUsuarioReg"'))
Check "Label for=campoPasswordReg" ($web.Contains('for="campoPasswordReg"'))
Check "Label for=campoPassword2Reg" ($web.Contains('for="campoPassword2Reg"'))

Write-Host "`nVALIDACION HTML5:" -ForegroundColor Yellow
Check "Inputs required" ($web.Contains("required"))
Check "minlength=8" ($web.Contains('minlength="8"'))
Check "type=email" ($web.Contains('type="email"'))
Check "type=password" ($web.Contains('type="password"'))

Write-Host "`nBOTONES:" -ForegroundColor Yellow
Check "Boton submit" ($web.Contains('type="submit"'))
Check "OAuth Google" ($web.Contains('/auth/google'))
Check "OAuth Apple" ($web.Contains('/auth/apple'))

Write-Host "`nJAVASCRIPT:" -ForegroundColor Yellow
Check "mostrarLogin()" ($web.Contains("function mostrarLogin"))
Check "mostrarRegistro()" ($web.Contains("function mostrarRegistro"))
Check "addEventListener" ($web.Contains("addEventListener"))
Check "fetch API" ($web.Contains("fetch"))

Write-Host "`nAPI ENDPOINTS:" -ForegroundColor Yellow
try {
    $est = (Invoke-WebRequest -Uri http://localhost:5000/api/auth/estado -UseBasicParsing).Content
    Check "GET /auth/estado" ($est.Contains('"necesita_setup"'))
} catch { Check "GET /auth/estado" $false }

try {
    $log = (Invoke-WebRequest -Uri http://localhost:5000/api/auth/login -Method POST -ContentType "application/json" -Body '{"usuario":"admin","password":"admin1234"}' -UseBasicParsing).Content
    Check "POST /auth/login" ($log.Contains('"usuario"'))
} catch { Check "POST /auth/login" $false }

Write-Host "`nESILOS:" -ForegroundColor Yellow
Check "Clase tarjeta-login" ($web.Contains('tarjeta-login'))
Check "Clase primario" ($web.Contains('primario'))
Check "Clase oauth-button" ($web.Contains('oauth-button'))

Write-Host ""
Write-Host "========================" -ForegroundColor Cyan
$total = $pass + $fail
$pct = if ($total -gt 0) { [int](($pass * 100) / $total) } else { 0 }
Write-Host "RESULTADOS: $pass/$total ($pct%)" -ForegroundColor Cyan
Write-Host "========================`n" -ForegroundColor Cyan

if ($fail -eq 0) {
    Write-Host "SUCCESS: All tests passed!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "FAILURE: $fail tests failed" -ForegroundColor Red
    exit 1
}
