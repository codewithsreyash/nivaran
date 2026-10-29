"""Patch RBAC URLs in run_benchmarks.py using simple string replacement."""
path = "run_benchmarks.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

fixes = [
    # (old_string, new_string)
    ('/api/dashboard/summary', '/api/dashboard'),
    ('GET /api/audit without token', 'GET /api/audit-logs without token'),
    ('client.get("/api/audit", headers', 'client.get("/api/audit-logs", headers'),
    ('client.get("/api/audit")', 'client.get("/api/audit-logs")'),
    ('Admin GET /api/audit ', 'Admin GET /api/audit-logs '),
    ('Officer GET /api/audit ', 'Officer GET /api/audit-logs '),
    ('ReadOnly GET /api/audit ', 'ReadOnly GET /api/audit-logs '),
    ('/api/reports/summary', '/api/reports/complaints'),
    ('Reports Summary', 'Reports Complaints'),
]

for old, new in fixes:
    count = content.count(old)
    content = content.replace(old, new)
    print(f"'{old[:40]}' -> replaced {count} times")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("\nDone.")

