# AICTE OneView / Nivaran
### Integrated Dashboard for Monitoring and Tracking Institution-Related Complaint Cases Across AICTE Bureaus/Cells
**Problem Statement ID:** 26264 · **Organisation:** All India Council for Technical Education (AICTE)  
**System Status:** Phase 10 Production Hardened & Verified

> ⚠️ **Data Notice**: All complaint records, institution names, and grievance details in this application are **Synthetic Demonstration Records** created solely for prototype evaluation and testing purposes. No real AICTE complaint data, real individuals, or real institutional secrets are used. Source label: `Synthetic Demonstration Record`.

---

## 1. Executive Summary & Intended Users

AICTE OneView (Nivaran) integrates complaints across AICTE Bureaus and Cells (e.g., Approvals, Academic, Finance, Compliance, Regulatory) into a centralized, transparent operational dashboard. It replaces siloed bureau tracking with cross-bureau visibility, automated priority scoring, duplicate detection, evidence verification, and audit logging.

### Intended User Personas
1. **AICTE Leadership & System Administrators (`ADMIN`):** Real-time visibility into council-wide complaint volume, bottlenecks, overdue escalations, and system-wide audit trails.
2. **Supervisory Reviewers (`SUPERVISORY_REVIEWER`):** Autonomous cross-bureau authorities who review candidate duplicate pairings, inspect evidence completeness, and record duplicate linking decisions with mandatory reasoning.
3. **Bureau Officers (`BUREAU_OFFICER`):** Operational officers assigned to specific bureaus (e.g. Academic, Finance, Compliance) managing the day-to-day lifecycle, notices, and resolution of complaints within their bureau.
4. **Read-Only Auditors (`READ_ONLY`):** Inspection officials and oversight authorities with view-only access across the dashboard and reports without write or decision permissions.

---

## 2. Architecture & Data Flow

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                           React 19 + TypeScript + Vite                         │
│                    Tailwind CSS · Lucide Icons · Recharts                      │
│      [Dashboard]   [Priority Queue]   [Complaints]   [Overlaps]   [Reports]   │
└──────────────────────────────────────┬─────────────────────────────────────────┘
                                       │ REST API (JSON / JWT Bearer)
┌──────────────────────────────────────▼─────────────────────────────────────────┐
│                           FastAPI Application Server                           │
│  ├── Auth & RBAC Middleware (Admin, Reviewer, Officer, Read-Only)              │
│  ├── BOLA / IDOR Protection (Bureau Write Isolation)                           │
│  ├── Complaint State Machine (Valid transitions, Terminal guards)              │
│  └── Reporting & Export Engine (CSV / JSON with Bureau Scoping)                │
├────────────────────────────────────────────────────────────────────────────────┤
│                              Core Logic Engines                                │
│  ├── Priority Engine (6 Dimensions, Rules-v1 Policy)                           │
│  ├── Overlap Engine (5 Dimensions, RapidFuzz Rules Baseline)                   │
│  ├── Evidence Assessment Service (Readiness & Completeness Checklist)          │
│  └── Audit Service (Append-only immutable audit logging)                       │
├────────────────────────────────────────────────────────────────────────────────┤
│                       Database & Storage Layer (SQLite WAL)                    │
│                 Complaints · Overlaps · Users · Bureaus · Audits               │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Role Permissions Matrix

| Feature / Action | Admin | Supervisory Reviewer | Bureau Officer | Read-Only Official |
| :--- | :---: | :---: | :---: | :---: |
| **View Integrated Dashboard & Complaints** | ✅ | ✅ | ✅ | ✅ |
| **Register Synthetic Complaint** | ✅ | ✅ | ✅ | ❌ (403) |
| **Modify Complaint Details / Status** | ✅ | ✅ | ✅ (Assigned bureau only) | ❌ (403) |
| **Cross-Bureau Case Transfer** | ✅ | ✅ | ✅ (Own bureau out) | ❌ (403) |
| **Record Supervisory Overlap Decision** | ✅ | ✅ | ❌ (403) | ❌ (403) |
| **Export Reports (CSV / JSON)** | ✅ (Global) | ✅ (Global) | ✅ (Scoped to bureau) | ✅ (Global) |
| **Access Audit Logs** | ✅ | ❌ (403) | ❌ (403) | ❌ (403) |
| **User Management** | ✅ | ❌ (403) | ❌ (403) | ❌ (403) |

---

## 4. Explainable Priority & Duplicate Engines

### A. 6-Dimension Rules-Based Priority Engine (`rules-v1`)
Score ranges from **0 to 100** categorized into four distinct bands:
- **Critical (75–100):** Immediate action required (e.g. Student safety, ragging, overdue critical cases).
- **High (50–74):** Financial grievances, faculty non-compliance, severe administrative lapses.
- **Medium (30–49):** Academic delays, examination disputes, general grievances.
- **Low (0–29):** Informational requests, recently registered low-urgency cases.

**Score Contributions:**
1. **Urgency Contribution (0–35 pts):** Category severity weight.
2. **Impact Contribution (0–25 pts):** Institutional risk, verified status, and stakeholder scale.
3. **Deadline Pressure (0–20 pts):** Overdue cases receive maximum pressure (+20); near-deadline tiers scaled dynamically.
4. **Ageing & Inaction (0–10 pts):** Days since last recorded action penalty.
5. **Escalation Multiplier (0–10 pts):** Escalated cases receive an active escalation bonus.
6. **Transfer Penalty (0–5 pts):** Repeated inter-bureau transfers incur an administrative friction penalty.

### B. 5-Dimension Overlap Engine (RapidFuzz `rules-v1`)
Matches potential cross-bureau duplicates without fabricating probabilities:
1. **Institution Match (0–30 pts):** Exact AICTE institution ID match (+30) or fuzzy token match (+25 max).
2. **Description Similarity (0–35 pts):** Combined RapidFuzz token sort and partial ratio.
3. **Category Match (0–15 pts):** Exact grievance category alignment.
4. **Date Proximity (0–10 pts):** Within 7 days (+10), 30 days (+6), 90 days (+3). Null-safe for missing dates.
5. **Keyword Overlap (0–10 pts):** Stop-word stripped domain token intersection with matched keywords exposed to human reviewers.

---

## 5. Local Setup & Windows PowerShell Startup

### Prerequisites
- Python 3.9+
- Node.js 18+ (tested on Node.js v22.14.0)

### Terminal 1 — FastAPI Backend
```powershell
cd c:\Users\sreyash\Downloads\nivaran\backend

# Install python dependencies
pip install -r requirements.txt

# Start backend server with auto-reload
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Root: `http://127.0.0.1:8000`
- Interactive Swagger API Docs: `http://127.0.0.1:8000/api/docs`
- Health Endpoint: `http://127.0.0.1:8000/api/health`

### Terminal 2 — Vite + React Frontend
```powershell
cd c:\Users\sreyash\Downloads\nivaran\frontend

# Install npm dependencies
npm install

# Start Vite dev server
npm run dev
```
- Frontend Portal: `http://localhost:5173`

---

## 6. Verification & Test Commands

### 1. Full Backend Pytest Suite (94 Tests)
```powershell
cd c:\Users\sreyash\Downloads\nivaran\backend
python -m pytest tests/ -v --tb=short
```
*Expected Result:* `94 passed in ~14s` (100% pass rate).

### 2. Synthetic Duplicate Benchmark Evaluation (62 Pairs)
```powershell
python tests/evaluate_benchmark.py
```
*Expected Result:* Evaluates 62 labeled pairs (24 duplicates, 17 related, 21 unrelated) confirming 100% duplicate recall with 0 false negatives.

### 3. Automated 12-Step Demonstration Scenario
```powershell
python demo_scenario.py
```
*Expected Result:* Exercises authentication, complaint registration, priority calculation, duplicate detection, supervisory decision, status lifecycle updates, timeline actions, dashboard verification, audit logging, and security denial checks.

### 4. Frontend TypeScript Check & Production Build
```powershell
cd c:\Users\sreyash\Downloads\nivaran\frontend
npx tsc -b
npm run build
```
*Expected Result:* Exit code `0`; clean bundle in `dist/`.

---

## 7. Demo Accounts

| Username | Password | Role | Assigned Bureau | Scope / Intended Use |
| :--- | :--- | :--- | :--- | :--- |
| `admin` | `Admin@123` | `ADMIN` | None (Global) | Executive dashboard, user management, audit logs, global transfers |
| `reviewer1` | `Review@123` | `SUPERVISORY_REVIEWER` | None (Cross-Bureau) | Supervisory duplicate decisions, evidence assessments, cross-bureau triage |
| `officer_acad` | `Officer@123` | `BUREAU_OFFICER` | Academic (ACAD) | Academic grievance investigations, syllabus issues, exam complaints |
| `officer_fin` | `Officer@123` | `BUREAU_OFFICER` | Finance (FIN) | Scholarship disbursals, fee irregularities, GATE stipend grievances |
| `officer_comp` | `Officer@123` | `BUREAU_OFFICER` | Compliance (COMP) | Accreditation compliance, faculty deficiency, inspection notices |
| `readonly1` | `Readonly@123` | `READ_ONLY` | None (Audit) | View-only access across complaints and reports; write operations blocked (403) |

---

## 8. Known Limitations & Roadmap

1. **Synthetic Data Context:** Operates strictly on synthetic demonstration data representing AICTE Problem Statement 26264.
2. **Local SQLite Architecture:** SQLite with WAL mode is used for simple zero-dependency demonstration. In multi-server production environments, migrate to PostgreSQL with Alembic migrations.
3. **Optional ML Pipeline:** The current active baseline is RapidFuzz `rules-v1`. Future machine learning candidates can be plugged into `backend/app/ml/` once real-world labeled datasets exceeding 1,000+ pairs become available.
