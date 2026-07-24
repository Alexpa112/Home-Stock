param(
    [switch]$SkipFetch,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $repoRoot

try {
    Write-Host "== Promote dev2 -> produccion =="

    $insideRepo = git rev-parse --is-inside-work-tree 2>$null
    if ($LASTEXITCODE -ne 0 -or $insideRepo -ne "true") {
        throw "No se encontro un repositorio Git valido en $repoRoot"
    }

    if (-not $SkipFetch) {
        Write-Host "Fetching origin..."
        git fetch origin --prune
        if ($LASTEXITCODE -ne 0) {
            throw "Fallo git fetch origin --prune"
        }
    }

    git rev-parse --verify dev2 *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "La rama local dev2 no existe"
    }

    git rev-parse --verify origin/dev2 *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "La referencia origin/dev2 no existe. Haz fetch o push de dev2 primero"
    }

    $counts = (git rev-list --left-right --count origin/dev2...dev2).Trim() -split "\s+"
    $behind = [int]$counts[0]
    $ahead = [int]$counts[1]

    if ($behind -gt 0) {
        throw "Tu dev2 local esta por detras de origin/dev2 ($behind commit/s). Sincroniza antes de promocionar"
    }

    $dev2Sha = (git rev-parse --short dev2).Trim()
    Write-Host "dev2 local: $dev2Sha (ahead $ahead, behind $behind frente a origin/dev2)"

    $pushArgs = @("push", "origin", "dev2:produccion")
    if ($DryRun) {
        $pushArgs += "--dry-run"
        Write-Host "Dry run habilitado"
    }

    Write-Host "Ejecutando: git $($pushArgs -join ' ')"
    git @pushArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Fallo el push de promocion a produccion"
    }

    if (-not $DryRun) {
        git fetch origin --prune
        if ($LASTEXITCODE -ne 0) {
            throw "Fallo al refrescar referencias remotas despues del push"
        }

        $originProdSha = (git rev-parse --short origin/produccion).Trim()
        if ($originProdSha -ne $dev2Sha) {
            throw "Verificacion fallida: origin/produccion=$originProdSha y dev2=$dev2Sha"
        }

        Write-Host "Promocion completada: origin/produccion -> $originProdSha"
    } else {
        Write-Host "Dry run completado sin cambios"
    }
}
finally {
    Pop-Location
}
