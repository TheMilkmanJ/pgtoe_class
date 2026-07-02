import os
import sys
import shutil
import subprocess
from pathlib import Path

# Paths
project_dir = Path(__file__).resolve().parent.parent

def _first_existing(*candidates: Path) -> Path | None:
    for path in candidates:
        if path.exists():
            return path
    return None

dest_ico = _first_existing(
    project_dir / "cosmic_dashboard" / "frontend" / "assets" / "galaxy_icon.ico",
    project_dir / "cosmic_dashboard" / "CosmicDashboardAssets" / "galaxy_icon_v3.ico",
    project_dir / "dashboard" / "assets" / "galaxy_icon.ico",
)
dest_png = _first_existing(
    project_dir / "cosmic_dashboard" / "frontend" / "assets" / "galaxy_icon.png",
    project_dir / "dashboard" / "assets" / "galaxy_icon.png",
)

# Automatically ensure all shell scripts are executable
scripts_to_chmod = ["launch_cosmic.sh", "wait_for_build.sh"]
for script_name in scripts_to_chmod:
    script_path = project_dir / script_name
    if script_path.exists():
        try:
            os.chmod(script_path, 0o755)
            print(f"Set executable permissions for: {script_path}")
        except Exception as e:
            print(f"Failed to set permissions for {script_name}: {e}")

def to_windows_path(linux_path: Path) -> str:
    parts = list(linux_path.parts)
    if len(parts) > 2 and parts[1] == 'mnt' and parts[2] == 'c':
        return "C:\\" + "\\".join(parts[3:])
    return str(linux_path)

# 1. Create Windows Desktop Shortcut (.lnk file) via PowerShell or pylnk3
# Dynamically query Windows for the active Desktop path (handles OneDrive and custom paths)
windows_desktop = None
try:
    desktop_res = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", "[Environment]::GetFolderPath('Desktop')"],
        capture_output=True,
        text=True,
    )
    if desktop_res.returncode == 0 and desktop_res.stdout.strip():
        wsl_res = subprocess.run(
            ["wslpath", "-u", desktop_res.stdout.strip()],
            capture_output=True,
            text=True,
        )
        if wsl_res.returncode == 0:
            windows_desktop = Path(wsl_res.stdout.strip())
except OSError:
    pass

# Fallback: Scan /mnt/c/Users for valid Desktop directories if PowerShell query failed
if not windows_desktop or not windows_desktop.exists():
    users_dir = Path("/mnt/c/Users")
    if users_dir.exists():
        for user_folder in users_dir.iterdir():
            if user_folder.is_dir() and user_folder.name not in ("All Users", "Default", "Default User", "Public"):
                # Try OneDrive Desktop first
                onedrive_desktop = user_folder / "OneDrive" / "Desktop"
                if onedrive_desktop.exists():
                    windows_desktop = onedrive_desktop
                    break
                # Try standard Desktop
                std_desktop = user_folder / "Desktop"
                if std_desktop.exists():
                    windows_desktop = std_desktop
                    break

LNK_TEMPLATE = Path(__file__).resolve().parent / "assets" / "CosmicDashboard.lnk.template"


def _patch_utf16(data: bytearray, old: str, new: str) -> bool:
    """Replace a UTF-16LE string in-place when both strings are the same length."""
    if len(old) != len(new):
        return False
    old_b = old.encode("utf-16-le")
    new_b = new.encode("utf-16-le")
    idx = data.find(old_b)
    if idx < 0:
        return False
    data[idx : idx + len(old_b)] = new_b
    return True


def create_windows_lnk_from_template(shortcut_path: Path, win_icon_str: str) -> bool:
    """Copy a Windows-generated template .lnk and patch paths in-place."""
    template = LNK_TEMPLATE
    if not template.exists():
        backup = shortcut_path.with_suffix(".lnk.bak")
        if backup.exists():
            template = backup
        elif shortcut_path.exists() and shortcut_path.stat().st_size > 1000:
            template = shortcut_path
        else:
            print("No valid .lnk template found; skipping template fallback")
            return False

    wsl_args = f"bash -c 'cd {project_dir.as_posix()} && ./launch_cosmic.sh'"
    description = "Launch CosmicDashboard in WSL prtoe_gold environment"
    data = bytearray(template.read_bytes())

    replacements = [
        (
            "bash -c 'cd /home/themilkmanj/prtoe_class && ./launch_cosmic.sh'",
            wsl_args,
        ),
        (
            "Launch CosmicDashboard in WSL pgtoe_gold environment",
            description,
        ),
        (
            r"C:\Users\themi\OneDrive\Desktop\CosmicDashboardAssets\galaxy_icon_v3.ico",
            win_icon_str.replace("/", "\\"),
        ),
    ]
    for old, new in replacements:
        if old == new:
            continue
        if len(old) != len(new):
            print(f"Template patch skipped (length mismatch): {old!r} -> {new!r}")
            continue
        if not _patch_utf16(data, old, new):
            print(f"Template patch not found: {old!r}")

    shortcut_path.write_bytes(data)
    print(f"Created shortcut from Windows template: {template}")
    return True


def create_windows_lnk(shortcut_path: Path, win_icon_str: str) -> bool:
    """Create CosmicDashboard.lnk via PowerShell, else patch a known-good template."""
    win_shortcut_str = to_windows_path(shortcut_path)
    wsl_args = f"bash -c 'cd {project_dir.as_posix()} && ./launch_cosmic.sh'"
    description = "Launch CosmicDashboard in WSL prtoe_gold environment"

    powershell_cmd = f"""
$wshell = New-Object -ComObject WScript.Shell
$shortcut = $wshell.CreateShortcut("{win_shortcut_str}")
$shortcut.TargetPath = "wsl.exe"
$shortcut.Arguments = "{wsl_args}"
$shortcut.IconLocation = "{win_icon_str}"
$shortcut.Description = "{description}"
$shortcut.WorkingDirectory = "C:\\"
$shortcut.Save()
"""
    try:
        res = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", powershell_cmd],
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            return True
        stderr = (res.stderr or "").strip()
        if stderr:
            print(f"PowerShell shortcut creation failed: {stderr}")
    except OSError:
        print("PowerShell unavailable in WSL; using template fallback")

    return create_windows_lnk_from_template(shortcut_path, win_icon_str)


if windows_desktop and windows_desktop.exists():
    shortcut_path = windows_desktop / "CosmicDashboard.lnk"
    
    # Store the icon in OneDrive Desktop CosmicDashboardAssets directory
    windows_app_dir = windows_desktop / "CosmicDashboardAssets"
    try:
        windows_app_dir.mkdir(parents=True, exist_ok=True)
        local_win_ico = windows_app_dir / "galaxy_icon_v3.ico"
        if dest_ico is None:
            raise FileNotFoundError(
                "galaxy_icon.ico not found under cosmic_dashboard/frontend/assets"
            )
        shutil.copy(dest_ico, local_win_ico)
        print(f"Copied icon to Windows directory: {local_win_ico}")
        
        win_icon_str = to_windows_path(local_win_ico)

        if shortcut_path.exists():
            backup = shortcut_path.with_suffix(".lnk.bak")
            shutil.copy(shortcut_path, backup)
            print(f"Backed up existing shortcut to: {backup}")
        
        if create_windows_lnk(shortcut_path, win_icon_str):
            print(f"Windows Desktop LNK shortcut created at: {shortcut_path}")
            old_url_shortcut = windows_desktop / "CosmicDashboard.url"
            if old_url_shortcut.exists():
                old_url_shortcut.unlink()
        else:
            url_content = f"""[InternetShortcut]
URL=http://localhost:8000/
IconIndex=0
IconFile={win_icon_str}
"""
            fallback_url = windows_desktop / "CosmicDashboard.url"
            with open(fallback_url, 'w') as f:
                f.write(url_content)
            print(f"Created fallback URL shortcut at: {fallback_url}")
    except Exception as e:
        print(f"Failed to copy icon or create Windows shortcut: {e}")
else:
    print("Windows Desktop path not found. Skipping Windows shortcut creation.")

# 2. Create Linux Desktop Shortcut (.desktop file)
linux_desktop = Path.home() / "Desktop"
if linux_desktop.exists() and dest_png is not None:
    desktop_file = linux_desktop / "cosmic-dashboard.desktop"
    desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=CosmicDashboard
Comment=Launch CosmicDashboard Web UI
Exec=xdg-open http://localhost:8000/
Icon={dest_png}
Terminal=false
Categories=Science;Astronomy;Education;
"""
    try:
        with open(desktop_file, 'w') as f:
            f.write(desktop_content)
        os.chmod(desktop_file, 0o755)
        print(f"Linux Desktop shortcut created at: {desktop_file}")
    except Exception as e:
        print(f"Failed to create Linux shortcut: {e}")

print("Desktop icon deployment complete!")
