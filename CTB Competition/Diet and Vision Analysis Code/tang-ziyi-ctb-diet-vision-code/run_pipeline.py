import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent

for script in sorted((root / "scripts").glob("[0-9]*.py")):
    print("\n=== running", script.name, "===")
    subprocess.run([sys.executable, str(script)], cwd=root, check=True)
