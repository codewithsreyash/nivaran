import re

path = "run_benchmarks.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# Replace unicode check/cross marks with ASCII
content = content.replace("PASS", "PASS")  # no-op to test
content = content.replace("\u2713", "PASS")
content = content.replace("\u2717", "FAIL")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed unicode chars in run_benchmarks.py")

