import os
import sys
import shutil
from pathlib import Path

# Paths
project_dir = Path("/home/themilkmanj/prtoe_class")
assets_dir = project_dir / "dashboard" / "assets"
assets_dir.mkdir(parents=True, exist_ok=True)

dest_ico = assets_dir / "galaxy_icon.ico"
dest_png = assets_dir / "galaxy_icon.png"

# 1. Create Windows Desktop Shortcut (.url file)
# WSL maps the C drive to /mnt/c
windows_desktop = Path("/mnt/c/Users/themi/Desktop")
if not windows_desktop.exists():
    windows_desktop = Path("/mnt/c/Users/themi/OneDrive/Desktop")
if windows_desktop.exists():
    shortcut_path = windows_desktop / "CosmicDashboard.url"
    
    # Store the icon in a local Windows directory to avoid WSL UNC path loading issues
    windows_app_dir = Path("/mnt/c/Users/themi/CosmicDashboardAssets")
    try:
        windows_app_dir.mkdir(parents=True, exist_ok=True)
        local_win_ico = windows_app_dir / "galaxy_icon.ico"
        shutil.copy(dest_ico, local_win_ico)
        print(f"Copied icon to Windows directory: {local_win_ico}")
        
        # Windows-style local path for the shortcut IconFile field
        windows_icon_path = r"C:\Users\themi\CosmicDashboardAssets\galaxy_icon.ico"
        
        url_content = f"""[InternetShortcut]
URL=http://localhost:8000/
IconIndex=0
IconFile={windows_icon_path}
"""
        with open(shortcut_path, 'w') as f:
            f.write(url_content)
        print(f"Windows Desktop shortcut created at: {shortcut_path}")
    except Exception as e:
        print(f"Failed to copy icon or create Windows shortcut: {e}")
else:
    print("Windows Desktop path not found. Skipping Windows shortcut creation.")

# 2. Create Linux Desktop Shortcut (.desktop file)
linux_desktop = Path.home() / "Desktop"
if linux_desktop.exists():
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
