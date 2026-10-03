[CmdletBinding()]
param([switch]$DoNotStartServer)

$ErrorActionPreference = "Stop"

$launcher = Join-Path $PSScriptRoot "launch_t3.py"
$icon = Join-Path $PSScriptRoot "assets\pingdotgg-official.ico"
$runtimeDirectory = Join-Path $PSScriptRoot "runtime"
$t3Executable = Join-Path $runtimeDirectory "t3.exe"

if (-not (Test-Path -LiteralPath $launcher)) {
    throw "Não foi encontrado launch_t3.py em $PSScriptRoot"
}

if (-not (Test-Path -LiteralPath $t3Executable)) {
    throw "Extraia o T3 Code para $RuntimeDirectory antes de executar o instalador."
}

if (-not (Test-Path -LiteralPath $icon)) {
    throw "Não foi encontrado o ícone em $icon"
}

$python = Get-Command python.exe -ErrorAction SilentlyContinue
if (-not $python) {
    throw "Instale o Python 3 e confirme que python.exe está disponível no PATH."
}

$pythonw = Join-Path (Split-Path $python.Source) "pythonw.exe"
if (-not (Test-Path -LiteralPath $pythonw)) {
    throw "Não foi encontrado pythonw.exe junto de $($python.Source)"
}

$chromeCandidates = @(
    (Get-ItemProperty -Path "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" -ErrorAction SilentlyContinue)."(default)",
    (Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" -ErrorAction SilentlyContinue)."(default)",
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)
$chrome = $chromeCandidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
if (-not $chrome) {
    throw "Instale o Google Chrome antes de executar o instalador."
}

$shell = New-Object -ComObject WScript.Shell
$desktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "T3 Code.lnk"
$startMenuShortcut = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\T3 Code.lnk"
$startupShortcut = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup\T3 Code Server.lnk"

foreach ($shortcutPath in @($desktopShortcut, $startMenuShortcut)) {
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $chrome
    $shortcut.Arguments = "--app=http://localhost:3773 --start-maximized"
    $shortcut.WorkingDirectory = $PSScriptRoot
    $shortcut.IconLocation = "$icon,0"
    $shortcut.Description = "T3 Code"
    $shortcut.Save()
}

$startup = $shell.CreateShortcut($startupShortcut)
$startup.TargetPath = $pythonw
$startup.Arguments = "`"$launcher`" --server-only"
$startup.WorkingDirectory = $PSScriptRoot
$startup.IconLocation = "$icon,0"
$startup.Description = "Servidor local do T3 Code"
$startup.Save()

if (-not $DoNotStartServer) {
    Start-Process -FilePath $pythonw -ArgumentList @("`"$launcher`"", "--server-only") -WindowStyle Hidden
}

Write-Host "T3 Code Windows Launcher instalado."
Write-Host "Fixe o atalho do menu Iniciar na barra de tarefas se desejar."
