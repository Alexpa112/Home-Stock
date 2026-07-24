param(
    [switch]$DryRun,
    [switch]$SkipFetch
)

$target = Join-Path $PSScriptRoot "promote_dev2_to_produccion.ps1"

if (-not (Test-Path $target)) {
    throw "No se encontro el script objetivo: $target"
}

$args = @()
if ($DryRun) { $args += "-DryRun" }
if ($SkipFetch) { $args += "-SkipFetch" }

powershell -ExecutionPolicy Bypass -File $target @args
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
