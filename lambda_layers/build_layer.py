import os
import shutil
import subprocess
import sys
from pathlib import Path
import zipfile

layer_dir = Path(__file__).parent / "python"
zip_path = Path(__file__).parent.parent / "lambda_layers.zip"

# Clean old __pycache__ and *.dist-info
for item in layer_dir.glob("**/__pycache__"):
    shutil.rmtree(item)
for item in layer_dir.glob("*.dist-info"):
    shutil.rmtree(item)

# Upgrade pip and install requirements into the layer folder
req_file = layer_dir / "requirements.txt"
subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(req_file), "-t", str(layer_dir)])

# Zip the layer
if zip_path.exists():
    zip_path.unlink()
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for f in layer_dir.rglob("*"):
        zf.write(f, f.relative_to(layer_dir.parent))
