<#
.SYNOPSIS
  Lance le monitoring local de KidAI : Prometheus (:9090) et Grafana (:3000), sans Docker.

.DESCRIPTION
  Au premier lancement, telecharge les versions portables officielles dans .tools\ (ignore par
  Git) et verifie leur empreinte SHA-256. Prometheus lit les metriques de l'API sur
  http://localhost:8000/metrics ; Grafana affiche le tableau de bord ops\grafana\dashboards.
  Les deux n'ecoutent que sur 127.0.0.1. Fermer leurs fenetres pour les arreter.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\monitoring.ps1
  powershell -ExecutionPolicy Bypass -File scripts\monitoring.ps1 -ApiPort 8010   # API sur un autre port
  powershell -ExecutionPolicy Bypass -File scripts\monitoring.ps1 -DownloadOnly
#>
param(
    [int]$ApiPort = 8000,  # port de l'API KidAI a surveiller
    [switch]$DownloadOnly  # telecharge et verifie sans lancer
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"  # sinon Invoke-WebRequest est tres lent sous PowerShell 5.1
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Root = Split-Path -Parent $PSScriptRoot
$Tools = Join-Path $Root ".tools"
$Ops = Join-Path $Root "ops"

# Versions figees : changer l'URL impose de changer l'empreinte (publiee avec chaque version).
$Packages = @(
    @{
        Name   = "prometheus"
        Url    = "https://github.com/prometheus/prometheus/releases/download/v3.5.0/prometheus-3.5.0.windows-amd64.zip"
        Sha256 = "b3c2607d1e80a277735fd3cde86432eb1b6843897cb82fb04fbf4c7ffb1d1c36"
    },
    @{
        Name   = "grafana"
        Url    = "https://dl.grafana.com/oss/release/grafana-12.1.0.windows-amd64.zip"
        Sha256 = "507ca9e04233a3853f9e31a2a89ffa627803db7be470e629f48bc93f0056dcde"
    }
)

function Install-Package($Package) {
    $dest = Join-Path $Tools $Package.Name
    if (Test-Path (Join-Path $dest ".ok")) { return Get-ChildItem $dest -Directory | Select-Object -First 1 }

    $zip = Join-Path $Tools ([IO.Path]::GetFileName($Package.Url))
    if (-not (Test-Path $zip)) {
        Write-Host "Telechargement de $($Package.Name)..."
        Invoke-WebRequest -Uri $Package.Url -OutFile "$zip.part" -UseBasicParsing
        Move-Item "$zip.part" $zip
    }
    $hash = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLower()
    if ($hash -ne $Package.Sha256) {
        Remove-Item $zip
        throw "Empreinte SHA-256 incorrecte pour $($Package.Name) : fichier supprime, relancez le script."
    }
    if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
    New-Item -ItemType Directory -Force $dest | Out-Null
    # tar (fourni avec Windows 10+) est bien plus rapide qu'Expand-Archive sur ces archives.
    & tar.exe -xf $zip -C $dest
    if ($LASTEXITCODE -ne 0) { throw "Extraction de $zip echouee" }
    New-Item -ItemType File (Join-Path $dest ".ok") | Out-Null
    Remove-Item $zip
    Write-Host "    OK  $($Package.Name) installe dans $dest" -ForegroundColor Green
    return Get-ChildItem $dest -Directory | Select-Object -First 1
}

function Test-PortInUse([int]$Port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try { $client.Connect("localhost", $Port); return $true }
    catch { return $false }
    finally { $client.Close() }
}

New-Item -ItemType Directory -Force $Tools | Out-Null
$prometheusHome = (Install-Package $Packages[0]).FullName
$grafanaHome = (Install-Package $Packages[1]).FullName
if ($DownloadOnly) { exit 0 }

foreach ($port in 9090, 3000) {
    if (Test-PortInUse $port) { throw "Le port $port est deja utilise (le monitoring tourne peut-etre deja)." }
}
if (-not (Test-PortInUse $ApiPort)) {
    Write-Host "!!  L'API ne repond pas sur le port $ApiPort : les graphiques resteront vides tant qu'elle n'est pas lancee (scripts\dev.ps1)." -ForegroundColor Yellow
}

$data = Join-Path $Tools "data"
New-Item -ItemType Directory -Force $data | Out-Null
# Copie de ops\prometheus\prometheus.yml avec le port de l'API (UTF-8 sans BOM pour Prometheus).
$promConfig = Join-Path $data "prometheus.yml"
$config = (Get-Content (Join-Path $Ops "prometheus\prometheus.yml") -Raw -Encoding UTF8) -replace "localhost:8000", "localhost:$ApiPort"
[IO.File]::WriteAllText($promConfig, $config, (New-Object Text.UTF8Encoding $false))
$promExe = Join-Path $prometheusHome "prometheus.exe"
$promArgs = "--config.file='$promConfig' --storage.tsdb.path='$data\prometheus' --storage.tsdb.retention.time=15d --web.listen-address=127.0.0.1:9090"
Start-Process powershell -WorkingDirectory $prometheusHome -ArgumentList @(
    "-NoExit", "-Command",
    "`$host.UI.RawUI.WindowTitle = 'KidAI Prometheus :9090'; & '$promExe' $promArgs"
)

# Configuration de Grafana par variables d'environnement (heritees par la fenetre lancee).
$env:GF_SERVER_HTTP_ADDR = "127.0.0.1"
$env:GF_SERVER_HTTP_PORT = "3000"
$env:GF_PATHS_DATA = "$data\grafana"
$env:GF_PATHS_LOGS = "$data\grafana\log"
$env:GF_PATHS_PLUGINS = "$data\grafana\plugins"
$env:GF_PATHS_PROVISIONING = "$Ops\grafana\provisioning"
$env:KIDAI_DASHBOARDS = "$Ops\grafana\dashboards"
$env:GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH = "$Ops\grafana\dashboards\kidai-api.json"
# Lecture sans compte (role Viewer) ; compte admin / admin pour modifier.
$env:GF_AUTH_ANONYMOUS_ENABLED = "true"
$env:GF_AUTH_ANONYMOUS_ORG_ROLE = "Viewer"
$env:GF_ANALYTICS_REPORTING_ENABLED = "false"
$env:GF_ANALYTICS_CHECK_FOR_UPDATES = "false"
$env:GF_NEWS_NEWS_FEED_ENABLED = "false"
$grafanaExe = Join-Path $grafanaHome "bin\grafana.exe"
Start-Process powershell -WorkingDirectory $grafanaHome -ArgumentList @(
    "-NoExit", "-Command",
    "`$host.UI.RawUI.WindowTitle = 'KidAI Grafana :3000'; & '$grafanaExe' server --homepath '$grafanaHome'"
)

Write-Host "Prometheus : http://localhost:9090/targets  (la cible kidai-api doit etre UP)"
Write-Host "Grafana    : http://localhost:3000  (tableau de bord KidAI - API : latence et trafic)"
