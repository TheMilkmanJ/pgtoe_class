import shutil
from pathlib import Path
from PIL import Image, ImageDraw

project_dir = Path("/home/themilkmanj/prtoe_class")
assets_dir = project_dir / "dashboard" / "assets"
src_jpg = assets_dir / "galaxy_icon.jpg"
dest_ico = assets_dir / "galaxy_icon.ico"
dest_png = assets_dir / "galaxy_icon.png"

print("Trimming background off the galaxy icon...")

# Open the original JPG image
img = Image.open(src_jpg)
width, height = img.size

# Bounding box of the rounded square icon in the 1024x1024 image
x_min, y_min = 117, 117
x_max, y_max = 907, 907

# Create an alpha mask initialized to 0 (fully transparent)
mask = Image.new('L', (width, height), 0)
draw = ImageDraw.Draw(mask)

# Corner radius to match the rounded corners of the app icon
radius = 160

# Draw rounded rectangle on mask
try:
    draw.rounded_rectangle([x_min, y_min, x_max, y_max], radius=radius, fill=255)
except AttributeError:
    # Robust fallback for older PIL versions
    draw.ellipse([x_min, y_min, x_min + 2*radius, y_min + 2*radius], fill=255)
    draw.ellipse([x_max - 2*radius, y_min, x_max, y_min + 2*radius], fill=255)
    draw.ellipse([x_min, y_max - 2*radius, x_min + 2*radius, y_max], fill=255)
    draw.ellipse([x_max - 2*radius, y_max - 2*radius, x_max, y_max], fill=255)
    draw.rectangle([x_min + radius, y_min, x_max - radius, y_max], fill=255)
    draw.rectangle([x_min, y_min + radius, x_max, y_max - radius], fill=255)

# Convert original to RGBA and apply the mask
rgba_img = img.convert('RGBA')
rgba_img.putalpha(mask)

# Crop the image to the bounding box of the icon
cropped = rgba_img.crop((x_min, y_min, x_max, y_max))

# Save transparent PNG format
cropped.save(dest_png, format='PNG')
print(f"Saved transparent PNG at: {dest_png}")

# Save transparent ICO format with multiple standard sizes (excluding 256x256 to ensure BMP compatibility)
ico_sizes = [(128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
cropped.save(dest_ico, format='ICO', sizes=ico_sizes)
print(f"Saved transparent ICO at: {dest_ico}")

# Copy the updated transparent ICO to the local Windows user directory
windows_app_dir = Path("/mnt/c/Users/themi/CosmicDashboardAssets")
try:
    windows_app_dir.mkdir(parents=True, exist_ok=True)
    local_win_ico = windows_app_dir / "galaxy_icon.ico"
    shutil.copy(dest_ico, local_win_ico)
    print(f"Successfully copied transparent icon to Windows: {local_win_ico}")
except Exception as e:
    print(f"Failed to copy icon to Windows directory: {e}")

print("Galaxy icon background trim complete!")
