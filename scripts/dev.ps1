<#
.SYNOPSIS
  Lance KidAI en developpement : backend FastAPI et frontend Vite, chacun dans sa fenetre.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\dev.ps1            # vrai backend (PostgreSQL)
  powershell -ExecutionPolicy Bypass -File scripts\dev.ps1 -Demo      # frontend seul, API simulee (MSW)
#>
param(
    [switch]$Demo  # frontend seul avec l'API simulee : ni backend ni base de donnees necessaires
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Root "backend\.venv\Scripts\python.exe"

if (-not (Test-Path (Join-Path $Root "frontend\node_modules"))) {
    throw "Dependances absentes : lancez d'abord scripts\setup.ps1"
}

# Un vrai essai de connexion (IPv4 et IPv6) : plus fiable que la table des ports.
function Test-PortInUse([int]$Port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try { $client.Connect("localhost", $Port); return $true }
    catch { return $false }
    finally { $client.Close() }
}

$ports = if ($Demo) { @(5173) } else { @(8000, 5173) }
foreach ($port in $ports) {
    if (Test-PortInUse $port) {
        throw "Le port $port est deja utilise (un serveur KidAI tourne peut-etre deja)."
    }
}

if (-not $Demo) {
    if (-not (Test-Path $Py)) { throw "backend\.venv absent : lancez d'abord scripts\setup.ps1" }
    Start-Process powershell -WorkingDirectory (Join-Path $Root "backend") -ArgumentList @(
        "-NoExit", "-Command",
        "`$host.UI.RawUI.WindowTitle = 'KidAI backend :8000'; & '$Py' -m uvicorn app.main:app --reload --port 8000"
    )
    Write-Host "Backend  : http://localhost:8000/health"
}

# La variable d'environnement prime sur frontend\.env.local.
$mocks = if ($Demo) { "true" } else { "false" }
Start-Process powershell -WorkingDirectory (Join-Path $Root "frontend") -ArgumentList @(
    "-NoExit", "-Command",
    "`$host.UI.RawUI.WindowTitle = 'KidAI frontend :5173'; `$env:VITE_USE_MOCKS = '$mocks'; npm run dev"
)
Write-Host "Frontend : http://localhost:5173  (mode $(if ($Demo) { 'demo, API simulee' } else { 'vrai backend' }))"
Write-Host "Pour arreter : fermez les fenetres ou faites Ctrl+C dedans."
