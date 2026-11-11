#!/usr/bin/env python3
"""Create a new Python project folder with its own virtual environment."""
import re
import subprocess
import sys
from pathlib import Path

base = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
if base.is_file():
    base = base.parent

name = input(f"New project name (it will be created in {base}): ").strip() or "my-project"
name = re.sub(r"[^\w.-]+", "-", name)
proj = base / name
if proj.exists():
    sys.exit(f"{proj} already exists, choose another name.")

proj.mkdir(parents=True)
print(f"Creating a virtual environment in {proj / '.venv'} ...")
subprocess.run([sys.executable, "-m", "venv", str(proj / ".venv")], check=True)
(proj / "main.py").write_text(
    '"""Your project starts here. Run it with:  python3 main.py"""\n\n\n'
    "def main():\n"
    f'    print("Hello from {name}!")\n\n\n'
    'if __name__ == "__main__":\n'
    "    main()\n")
(proj / "requirements.txt").write_text("# one package per line, then run:  .venv/bin/pip install -r requirements.txt\n")
(proj / "README.md").write_text(
    f"# {name}\n\n"
    "```bash\n"
    "source .venv/bin/activate      # use this project's own Python\n"
    "pip install requests           # install packages just for this project\n"
    "python main.py\n"
    "```\n")
print(f"\nDone! Open {proj} and double-click main.py (or right-click > Run with Python).")
