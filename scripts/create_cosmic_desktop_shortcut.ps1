param(
    [string]$WslProjectDir = "/home/themilkmanj/prtoe_class",
    [string]$IconPath = "",
    [string]$DesktopPath = ""
)

if (-not $DesktopPath) {
    $DesktopPath = [Environment]::GetFolderPath('Desktop')
}

if (-not $IconPath) {
    $IconPath = Join-Path $DesktopPath "CosmicDashboardAssets\galaxy_icon_v3.ico"
}

$shortcutFile = Join-Path $DesktopPath "CosmicDashboard.lnk"
$wslArgs = "bash -c 'cd $WslProjectDir && ./launch_cosmic.sh'"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($shortcutFile)
$Shortcut.TargetPath = "$env:SystemRoot\System32\wsl.exe"
$Shortcut.Arguments = $wslArgs
$Shortcut.WorkingDirectory = "C:\"
$Shortcut.WindowStyle = 1
$Shortcut.Description = "Launch CosmicDashboard in WSL prtoe_gold environment"
if (Test-Path $IconPath) {
    $Shortcut.IconLocation = $IconPath
}
$Shortcut.Save()

Write-Host "Desktop shortcut created at: $shortcutFile"