<#
.SYNOPSIS
  Installe KidAI sur une machine Windows apres un "git clone" (sans Docker).

.DESCRIPTION
  Idempotent : on peut le relancer sans risque, il ne refait que ce qui manque.
    1. verifie les prerequis (Python 3.11, Node.js >= 20, PostgreSQL, Ollama) ;
    2. cree backend\.venv et installe les dependances Python ;
    3. cree .env a partir de .env.example et genere les secrets (JWT, cle de chiffrement) ;
    4. applique les migrations si la base PostgreSQL est joignable ;
    5. installe les dependances du frontend (+ Chromium pour Playwright) ;
    6. active pre-commit.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -WithData   # + environnement des scripts de donnees
#>
param(
    [switch]$WithData,     # cree aussi .venv (racine) pour data\download_cnp.py
    [switch]$SkipBrowsers  # ne telecharge pas Chromium pour les tests Playwright
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Py = Join-Path $Backend ".venv\Scripts\python.exe"
$EnvFile = Join-Path $Root ".env"
$Problems = New-Object System.Collections.Generic.List[string]

function Step([string]$Message) { Write-Host "`n==> $Message" -ForegroundColor Cyan }
function Ok([string]$Message) { Write-Host "    OK  $Message" -ForegroundColor Green }
function Warn([string]$Message) {
    Write-Host "    !!  $Message" -ForegroundColor Yellow
    $Problems.Add($Message)
}
function Invoke-Checked([string]$What, [scriptblock]$Command) {
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "$What a echoue (code $LASTEXITCODE)" }
}

# ---------------------------------------------------------------------------- 1. prerequis
Step "Verification des prerequis"

& py -3.11 --version *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.11 introuvable. Installez-le : winget install Python.Python.3.11"
}
Ok (& py -3.11 --version)

$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) { throw "Node.js introuvable. Installez-le : winget install OpenJS.NodeJS.LTS" }
$nodeVersion = (& node --version).TrimStart("v")
if ([int]($nodeVersion.Split(".")[0]) -lt 20) { throw "Node.js $nodeVersion trop ancien : version 20 ou plus requise." }
Ok "Node.js $nodeVersion"

$psql = Get-ChildItem "C:\Program Files\PostgreSQL\*\bin\psql.exe" -ErrorAction SilentlyContinue |
    Sort-Object FullName -Descending | Select-Object -First 1
if ($psql) { Ok "PostgreSQL ($($psql.FullName))" }
else { Warn "PostgreSQL introuvable. Installez-le : winget install PostgreSQL.PostgreSQL.17" }

if (Get-Command ollama -ErrorAction SilentlyContinue) {
    if ((& ollama list 2>$null) -match "qwen3:4b") { Ok "Ollama + qwen3:4b" }
    else { Warn "Modele manquant (utile a partir de l'etape 2) : ollama pull qwen3:4b" }
}
else { Warn "Ollama introuvable (utile a partir de l'etape 2) : https://ollama.com/download" }

# ---------------------------------------------------------------------------- 2. backend
Step "Backend : environnement Python"
if (-not (Test-Path $Py)) {
    Invoke-Checked "Creation de backend\.venv" { py -3.11 -m venv (Join-Path $Backend ".venv") }
}
Invoke-Checked "pip" { & $Py -m pip install --quiet --upgrade pip }
Invoke-Checked "Installation des dependances backend" {
    & $Py -m pip install --quiet -r (Join-Path $Backend "requirements-dev.txt")
}
Ok "backend\.venv pret"

# ---------------------------------------------------------------------------- 3. .env
Step "Configuration (.env)"
if (-not (Test-Path $EnvFile)) {
    Copy-Item (Join-Path $Root ".env.example") $EnvFile
    Ok ".env cree a partir de .env.example"
}
$lines = [System.IO.File]::ReadAllLines($EnvFile)
$generated = @()
for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match "^JWT_SECRET=\s*$") {
        $lines[$i] = "JWT_SECRET=" + (& $Py -c "import secrets; print(secrets.token_urlsafe(48))")
        $generated += "JWT_SECRET"
    }
    elseif ($lines[$i] -match "^DATA_ENCRYPTION_KEY=\s*$") {
        $lines[$i] = "DATA_ENCRYPTION_KEY=" + (& $Py -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
        $generated += "DATA_ENCRYPTION_KEY"
    }
}
# UTF-8 sans BOM : un BOM casserait la lecture de la premiere variable.
[System.IO.File]::WriteAllLines($EnvFile, $lines, (New-Object System.Text.UTF8Encoding($false)))
if ($generated) { Ok ("Secrets generes : " + ($generated -join ", ")) } else { Ok "Secrets deja presents" }

# ---------------------------------------------------------------------------- 4. base de donnees
Step "Base de donnees PostgreSQL"
Push-Location $Backend
try {
    & $Py -c "import sys; from app.db.session import check_database; sys.exit(0 if check_database() else 1)"
    if ($LASTEXITCODE -eq 0) {
        Invoke-Checked "Migrations Alembic" { & $Py -m alembic upgrade head }
        Ok "Tables a jour"
    }
    else {
        $psqlCmd = if ($psql) { "& `"$($psql.FullName)`"" } else { "psql" }
        Warn ("Base injoignable avec DATABASE_URL (.env). Creez l'utilisateur et la base, puis relancez ce script :`n" +
            "        $psqlCmd -U postgres -h localhost -c `"CREATE USER kidai WITH PASSWORD 'kidai_dev';`"`n" +
            "        $psqlCmd -U postgres -h localhost -c `"CREATE DATABASE kidai OWNER kidai;`"")
    }
}
finally { Pop-Location }

# ---------------------------------------------------------------------------- 5. frontend
Step "Frontend : dependances npm"
Push-Location $Frontend
try {
    Invoke-Checked "npm install" { npm install --no-fund --no-audit }
    Ok "node_modules pret"
    if (-not $SkipBrowsers) {
        Invoke-Checked "Installation de Chromium (Playwright)" { npx playwright install chromium }
        Ok "Chromium pour les tests de bout en bout"
    }
}
finally { Pop-Location }

# ---------------------------------------------------------------------------- 6. donnees (option)
if ($WithData) {
    Step "Scripts de donnees : environnement .venv (racine)"
    $DataPy = Join-Path $Root ".venv\Scripts\python.exe"
    if (-not (Test-Path $DataPy)) { Invoke-Checked "Creation de .venv" { py -3.11 -m venv (Join-Path $Root ".venv") } }
    Invoke-Checked "Installation des dependances data" {
        & $DataPy -m pip install --quiet -r (Join-Path $Root "data\requirements.txt")
    }
    Ok ".venv pret (data\download_cnp.py)"
}

# ---------------------------------------------------------------------------- 7. pre-commit
Step "Hooks Git (pre-commit)"
if (Test-Path (Join-Path $Root ".git")) {
    Push-Location $Root
    try { Invoke-Checked "pre-commit install" { & (Join-Path $Backend ".venv\Scripts\pre-commit.exe") install } }
    finally { Pop-Location }
    Ok "ruff, black, eslint et prettier verifies a chaque commit"
}

# ---------------------------------------------------------------------------- bilan
Write-Host ""
if ($Problems.Count -eq 0) {
    Write-Host "Installation terminee." -ForegroundColor Green
}
else {
    Write-Host "Installation terminee avec $($Problems.Count) point(s) a regler :" -ForegroundColor Yellow
    $Problems | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
}
Write-Host "Lancer le projet : powershell -ExecutionPolicy Bypass -File scripts\dev.ps1"
