# Crea un acceso directo con icono en el Escritorio para lanzar el dashboard.
# Uso (PowerShell):  .\scripts\crear_acceso_directo.ps1
# Es idempotente: si ya existe, lo actualiza.

$ErrorActionPreference = "Stop"

# Raiz del repo = carpeta padre de /scripts
$repo = Split-Path -Parent $PSScriptRoot
$bat  = Join-Path $repo "scripts\run_dashboard.bat"
$icon = Join-Path $repo "assets\dashboard_icon.ico"

$desktop = [Environment]::GetFolderPath("Desktop")
$lnkPath = Join-Path $desktop "Dashboard Inmobiliario.lnk"

$ws  = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut($lnkPath)
$lnk.TargetPath       = $bat
$lnk.WorkingDirectory = $repo
$lnk.IconLocation     = "$icon,0"
$lnk.Description       = "Abre el dashboard de inteligencia inmobiliaria (Bogota)"
$lnk.WindowStyle       = 1
$lnk.Save()

Write-Host "Acceso directo creado en:" $lnkPath
