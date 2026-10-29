"""Fix: add io import and stdout encoding fix"""
import re

path = "run_benchmarks.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# Insert after 'import sys'
old = "import sys\nimport json"
new = "import sys\nimport io\nimport json"
content = content.replace(old, new)

# Insert stdout encoding fix after sys.path.insert
old2 = "sys.path.insert(0, BACKEND_DIR)\n\n# ── imports"
new2 = "sys.path.insert(0, BACKEND_DIR)\n\n# Force UTF-8 stdout on Windows\nif hasattr(sys.stdout, 'buffer') and sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':\n    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')\n\n# ── imports"
content = content.replace(old2, new2)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Done")

