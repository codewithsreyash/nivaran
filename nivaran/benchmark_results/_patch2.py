"""Patch run_benchmarks.py to fix URLs and RBAC test paths."""
path = "run_benchmarks.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# Fix API endpoint URLs
replacements = [
    ('"/api/dashboard/summary", admin_h,  "Dashboard Summary (admin)"',
     '"/api/dashboard", admin_h,      "Dashboard (admin)"'),
    ('"/api/priority/queue",    admin_h,  "Priority Queue (admin)"',
     '"/api/priority-queue",    admin_h,  "Priority Queue (admin)"'),
    ('"/api/reports/summary",   admin_h,  "Reports Summary (admin)"',
     '"/api/reports/complaints",admin_h,  "Reports Complaints (admin)"'),
    ('"/api/audit",             admin_h,  "Audit Log (admin)"',
     '"/api/audit-logs",        admin_h,  "Audit Logs (admin)"'),
]
for old, new in replacements:
    if old in content:
        content = content.replace(old, new)
        print(f"Replaced: {old[:50]}...")
    else:
        print(f"NOT FOUND: {old[:50]}...")

# Fix RBAC test URLs
rbac_replacements = [
    ('"/api/dashboard/summary", without token', '/api/dashboard/summary'),
    ('client.get("/api/dashboard/summary")', '/api/dashboard'),
    ('"/api/audit")', '"/api/audit-logs")'),
]

# Fix RBAC URLs more carefully
rbac_fixes = [
    ('check("UNAUTH-02", "GET /api/dashboard/summary without token -> 401",\n          client.get("/api/dashboard/summary"), 401)',
     'check("UNAUTH-02", "GET /api/dashboard without token -> 401",\n          client.get("/api/dashboard"), 401)'),
    ('check("UNAUTH-04", "GET /api/audit without token -> 401",\n          client.get("/api/audit"), 401)',
     'check("UNAUTH-04", "GET /api/audit-logs without token -> 401",\n          client.get("/api/audit-logs"), 401)'),
    ('check("RBAC-ADMIN-03", "Admin GET /api/audit -> 200",\n          client.get("/api/audit", headers=hdr(admin_tok)), 200)',
     'check("RBAC-ADMIN-03", "Admin GET /api/audit-logs -> 200",\n          client.get("/api/audit-logs", headers=hdr(admin_tok)), 200)'),
    ('check("RBAC-ADMIN-04", "Admin GET /api/dashboard/summary -> 200",\n          client.get("/api/dashboard/summary", headers=hdr(admin_tok)), 200)',
     'check("RBAC-ADMIN-04", "Admin GET /api/dashboard -> 200",\n          client.get("/api/dashboard", headers=hdr(admin_tok)), 200)'),
    ('check("RBAC-ADMIN-05", "Admin GET /api/reports/summary -> 200",\n          client.get("/api/reports/summary", headers=hdr(admin_tok)), 200)',
     'check("RBAC-ADMIN-05", "Admin GET /api/reports/complaints -> 200",\n          client.get("/api/reports/complaints", headers=hdr(admin_tok)), 200)'),
    ('check("RBAC-OFFICER-03", "Officer GET /api/audit -> 403",\n          client.get("/api/audit", headers=hdr(officer_tok)), 403)',
     'check("RBAC-OFFICER-03", "Officer GET /api/audit-logs -> 403",\n          client.get("/api/audit-logs", headers=hdr(officer_tok)), 403)'),
    ('check("RBAC-OFFICER-04", "Officer GET /api/dashboard/summary -> 200",\n          client.get("/api/dashboard/summary", headers=hdr(officer_tok)), 200)',
     'check("RBAC-OFFICER-04", "Officer GET /api/dashboard -> 200",\n          client.get("/api/dashboard", headers=hdr(officer_tok)), 200)'),
    ('check("RBAC-REVIEWER-02", "Reviewer GET /api/dashboard/summary -> 200",\n          client.get("/api/dashboard/summary", headers=hdr(reviewer_tok)), 200)',
     'check("RBAC-REVIEWER-02", "Reviewer GET /api/dashboard -> 200",\n          client.get("/api/dashboard", headers=hdr(reviewer_tok)), 200)'),
    ('check("RBAC-READONLY-03", "ReadOnly GET /api/audit -> 403",\n          client.get("/api/audit", headers=hdr(readonly_tok)), 403)',
     'check("RBAC-READONLY-03", "ReadOnly GET /api/audit-logs -> 403",\n          client.get("/api/audit-logs", headers=hdr(readonly_tok)), 403)'),
]

# Normalize CRLF for matching
content_norm = content.replace('\r\n', '\n')
for old, new in rbac_fixes:
    if old in content_norm:
        content_norm = content_norm.replace(old, new)
        print(f"RBAC replaced: {old[:50]}...")
    else:
        # Try without leading whitespace constraint
        print(f"RBAC NOT FOUND (trying raw): {old[:50]}...")

content = content_norm

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch complete.")

