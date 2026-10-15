"""Dependency-free build/syntax validation and the real test suite."""
import ast
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent.parent
for folder in ("wanda", "tests", "scripts"):
    for file in (root / folder).glob("*.py"):
        ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
print("Python syntax checks passed.", flush=True)
raise SystemExit(subprocess.call([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=root))
