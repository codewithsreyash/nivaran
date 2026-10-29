# Nivaran / AICTE OneView — Phase 10: Final Acceptance Testing and Presentation Readiness Report

**Project:** AICTE Problem Statement 26264 — Integrated Dashboard for Monitoring and Tracking Institution-Related Complaint Cases Across AICTE Bureaus/Cells  
**Version:** Phase 10 Final Acceptance Release  
**Evaluation Date:** October 28, 2026  
**Environment:** Windows 10/11, Python 3.9.13, Node.js v22.14.0, Vite 8.3.5, FastAPI 0.111.0, SQLite 3 (WAL Mode)  
**Active Baseline Detector:** RapidFuzz `rules-v1` (Deterministic 5-Dimension Rules Baseline)  
**Active Priority Engine:** 6-Dimension Deterministic Policy Engine `rules-v1`  

---

## 1. Baseline Verification & Actual Command Results

All checks were executed directly in the project environment without simulation or mocking:

| # | Command Executed | Directory | Exit Code | Result Summary |
| :-: | :--- | :--- | :-: | :--- |
| **1** | `npx tsc -b` | `frontend/` | **0** | Clean compile; 0 TypeScript errors. |
| **2** | `npm run build` | `frontend/` | **0** | Production bundle generated in 827ms (`dist/index.html`, CSS, JS chunks). |
| **3** | `python -m pytest tests/ -v --tb=short` | `backend/` | **0** | **94 passed**, 0 failed, 0 skipped in 14.02s. |
| **4** | `python tests/evaluate_benchmark.py` | `backend/` | **0** | 62 pairs evaluated; 100% duplicate recall (24/24), 0 false negatives. |
| **5** | `python demo_scenario.py` | `backend/` | **0** | Complete 12-step deterministic E2E workflow passed against live database. |
| **6** | `GET http://127.0.0.1:8000/api/health` | Backend API | **200** | `status: "ok"`, `detector_type: "rules_baseline"`, `algorithm_version: "rules-v1"`. |
| **7** | `GET http://127.0.0.1:8000/api/ml/status` | Backend API | **200** | `overall: "Rules-based baseline active. No ML model trained."`. |

---

## 2. Full Test Suite Execution Summary

| Test Module | Tests Run | Passed | Failed | Skipped | Status | Key Coverage Areas |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| [tests/test_auth.py](file:///c:/Users/sreyash/Downloads/nivaran/backend/tests/test_auth.py) | 6 | 6 | 0 | 0 | **PASS** | JWT login, credential rejection, `/me` profile, logout |
| [tests/test_complaints_api.py](file:///c:/Users/sreyash/Downloads/nivaran/backend/tests/test_complaints_api.py) | 7 | 7 | 0 | 0 | **PASS** | CRUD, 404 handling, read-only rejection, case actions, status lifecycle |
| [tests/test_evidence_service.py](file:///c:/Users/sreyash/Downloads/nivaran/backend/tests/test_evidence_service.py) | 3 | 3 | 0 | 0 | **PASS** | Evidence completeness, readiness checklists, date anomaly detection |
| [tests/test_institutions_and_misc_api.py](file:///c:/Users/sreyash/Downloads/nivaran/backend/tests/test_institutions_and_misc_api.py) | 7 | 7 | 0 | 0 | **PASS** | Institutions, dashboard counters, bureaus, priority queue, deadlines |
| [tests/test_overlap_engine.py](file:///c:/Users/sreyash/Downloads/nivaran/backend/tests/test_overlap_engine.py) | 7 | 7 | 0 | 0 | **PASS** | Institution match, fuzzy description, keywords, null-safe date ranges |
| [tests/test_priority_engine.py](file:///c:/Users/sreyash/Downloads/nivaran/backend/tests/test_priority_engine.py) | 7 | 7 | 0 | 0 | **PASS** | Category urgency weights, deadline pressure tiers, ageing penalties |
| [tests/test_priority_engine_extended.py](file:///c:/Users/sreyash/Downloads/nivaran/backend/tests/test_priority_engine_extended.py) | 14 | 14 | 0 | 0 | **PASS** | Student safety critical score, transfer friction, 100 pt score cap, bands |
| [tests/test_regression.py](file:///c:/Users/sreyash/Downloads/nivaran/backend/tests/test_regression.py) | 43 | 43 | 0 | 0 | **PASS** | BOLA/IDOR isolation, supervisory roles, dedup guard, export filtering |
| **Total Test Suite** | **94** | **94** | **0** | **0** | **PASS (100%)** | Comprehensive unit, integration, edge-case & acceptance suite |

---

## 3. Security Acceptance Matrix by Role

We verified real backend authorization across every user role on read, write, transfer, decision, export, and audit endpoints:

| Endpoint & Action | Admin (`admin`) | Supervisory Reviewer (`reviewer1`) | Bureau Officer (`officer_acad` / `officer_fin`) | Read-Only User (`readonly1`) | Status Code & Behavior |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `GET /api/complaints` | Allowed | Allowed | Allowed | Allowed | **200 OK** (Integrated Cross-Bureau Visibility) |
| `GET /api/complaints/{id}` | Allowed | Allowed | Allowed | Allowed | **200 OK** (Full case details, priority explainability) |
| `POST /api/complaints` | Allowed | Allowed | Allowed | **Forbidden (403)** | Read-only cannot submit complaints |
| `PATCH /api/complaints/{id}` (Own Bureau) | Allowed | Allowed | Allowed | **Forbidden (403)** | Bureau officers can update their bureau's cases |
| `PATCH /api/complaints/{id}` (Other Bureau) | Allowed | Allowed | **Forbidden (403)** | **Forbidden (403)** | **BOLA / IDOR Protection Active** |
| `POST /api/complaints/{id}/transfer` | Allowed | Allowed | Allowed (Own case) | **Forbidden (403)** | Closed/disposed cases blocked (400) |
| `POST /api/overlaps/{id}/decision` | Allowed | Allowed | **Forbidden (403)** | **Forbidden (403)** | Only Admin & Reviewer can decide duplicate merges |
| `GET /api/reports/export` | Global | Global | **Scoped to assigned bureau** | Global (Read-only) | Bureau officers cannot export other bureaus (403) |
| `GET /api/audit-logs` | Allowed | **Forbidden (403)** | **Forbidden (403)** | **Forbidden (403)** | Audit history restricted strictly to Admin |
| `GET /api/users` | Allowed | **Forbidden (403)** | **Forbidden (403)** | **Forbidden (403)** | User administration restricted to Admin |

### Privacy & Data Secrecy Audit
- **Audit Logs:** Verified via `test_audit_logs_privacy_and_secrecy` that neither `hashed_password`, raw tokens, nor session secrets appear in `/api/audit-logs` responses or logs.
- **User Schemas:** `UserOut` exposes only public demographic metadata (`id`, `username`, `email`, `full_name`, `role`, `bureau_id`, `is_active`, `created_at`).

---

## 4. Duplicate Benchmark Methodology & Reproduction

The evaluation harness in [tests/evaluate_benchmark.py](file:///c:/Users/sreyash/Downloads/nivaran/backend/tests/evaluate_benchmark.py) tests the active RapidFuzz `rules-v1` baseline on the 62-pair synthetic evaluation dataset ([tests/data/overlap_eval_pairs.json](file:///c:/Users/sreyash/Downloads/nivaran/backend/tests/data/overlap_eval_pairs.json)).

### Dataset Composition (62 Pairs)
- **`duplicate` (24 pairs):** Paraphrased and direct duplicate filings describing the identical grievance at the same institution.
- **`related_independent` (17 pairs):** Different incidents from the same institution or sharing grievance categories.
- **`unrelated` (21 pairs):** Distinct institutions, non-overlapping dates, and disparate categories.

### Reproduced Empirical Results
```
Score Ranges by Label:
  • duplicate (n=24):            min=71.4, max=86.4, avg=80.3
  • related_independent (n=17):  min=24.6, max=70.8, avg=52.4
  • unrelated (n=21):            min=24.8, max=56.8, avg=33.9

Triage Screening (Threshold >= 25.0):
  • Duplicate Recall:                24/24 (100.0%) — 0 False Negatives
  • Related Cases Flagged:           16/17 (94.1%)
  • Unrelated Cases Cleanly Filtered: 3/21 (14.3%)

High-Confidence Duplicate Detection (Threshold >= 70.0):
  • True Positives (TP):  24
  • False Positives (FP): 1  (only 1 related case exceeded 70)
  • True Negatives (TN):  37
  • False Negatives (FN): 0
  • Precision:            0.9600 (96.0%)
  • Recall:               1.0000 (100.0%)
  • F1 Score:             0.9796 (98.0%)
  • Overall Accuracy:     0.9839 (98.4%)
```

### Methodological Integrity & No Label Leakage
1. **Zero Data Leakage:** Labels (`duplicate`, `related_independent`, `unrelated`) are stored separately from complaint features. The detection engine does not inspect labels during feature extraction or comparison.
2. **Defensible Positioning:** Similarity scores are displayed explicitly as **heuristic match scores out of 100**, never as calibrated machine learning probabilities or real-world accuracy claims.
3. **Mandatory Human-in-the-Loop:** Overlap suggestions remain advisory; an authorized `SUPERVISORY_REVIEWER` must inspect side-by-side evidence and provide written justification before any case is officially merged or linked.

---

## 5. Report & Export Verification Results

The export endpoint (`GET /api/reports/export`) was validated across multiple scenarios:

1. **Empty Query Results:** Verified via `test_export_empty_results_handling`. Filtering for non-matching parameters (e.g. `category=student_safety_welfare&status=closed`) returns HTTP 200 with `{"total": 0, "data": []}` in JSON mode and a 1-line column header in CSV mode.
2. **CSV Escaping of Special Characters:** Verified via `test_export_csv_escaping_special_characters`. Titles containing commas, quotes, and special symbols (e.g., `'Fee hike, "special charges", and extra exam fees'`) are properly quoted and escaped by Python's `csv.DictWriter`, preserving column alignment when parsed by RFC 4180 compliant CSV readers.
3. **Invalid Filter Validation:** Passing non-existent categories or statuses returns HTTP 400 Bad Request with clear error details (`"Invalid category filter: 'xyz'"`).
4. **Invalid Date Range Sanity:** Submitting `start_date > end_date` returns HTTP 422 Unprocessable Entity (`"End date cannot be earlier than start date"`).
5. **Dashboard Counter Consistency:** Verified via `test_dashboard_totals_bucket_consistency`:
   $$\text{pending\_complaints} + \text{under\_process} + \text{disposed\_complaints} == \text{total\_complaints}$$

---

## 6. Known Defects and Remaining Risks

1. **Synthetic Data Disclaimer:** The system currently operates on synthetic demonstration data representing AICTE Problem Statement 26264. It is not connected to live AICTE production databases.
2. **Single-Node SQLite Deployment:** The local database uses SQLite in WAL mode, which is ideal for single-server demonstration and evaluation. Enterprise multi-tenant deployments should migrate to PostgreSQL with Alembic migrations.
3. **Pydantic v2 Class-Based Config Deprecation:** Pydantic v2 logs 14 non-fatal deprecation warnings regarding `class Config:` in older third-party dependencies; these do not affect runtime behavior.

---

## 7. Concise 5-Minute Live Demonstration Script

Follow this rehearsed walkthrough during presentation to showcase end-to-end functionality within 5 minutes:

### Minute 1: Overview & Authentication
1. Navigate to `http://localhost:5173`.
2. Point out the AICTE Problem Statement 26264 banner and Synthetic Data disclaimer.
3. Click **Admin** quick-fill and log in (`admin` / `Admin@123`).
4. Display the **Executive Dashboard**: explain total complaint metrics, bureau workloads, and overdue alerts. Point out that `pending + under_process + disposed == total`.

### Minute 2: Priority Engine Explainability
1. Click **Priority Queue** in the sidebar.
2. Note that complaints are strictly sorted by descending priority score.
3. Click on a High/Critical case: show the **Explainable Breakdown**:
   - Urgency Contribution (Category weight)
   - Impact Contribution (Institution scale/status)
   - Deadline Pressure & Ageing
   - Next Required Action recommendation.

### Minute 3: Registering Overlapping Complaints
1. Click **Register Complaint**.
2. Register a complaint:
   - Institution: *Apex Institute of Advanced Engineering & Technology*
   - Category: *Scholarship & Financial Grievances*
   - Title: *Withholding of M.Tech GATE Stipends*
   - Description: *Administration has delayed stipend disbursal for 18 M.Tech GATE students.*
3. Submit and show that priority is automatically scored (~48/100, Medium).
4. Register a second, paraphrased complaint with similar wording for the same institution.

### Minute 4: Duplicate Detection & Supervisory Decision
1. Log in as `reviewer1` (`Review@123`).
2. Navigate to **Overlap Reviews**: show that RapidFuzz `rules-v1` surfaced the new pair with ~74.8/100 match score.
3. Show the side-by-side evidence comparison: shared keywords (`stipend`, `gate`, `m.tech`), identical verified institution, and description similarity.
4. Record a supervisory decision: select **Confirmed Duplicate**, enter mandatory reason: *"Verified identical stipend withholding incident"*, and submit.

### Minute 5: Bureau Officer Progress, Reports & Security Denial
1. Log in as `officer_acad` (`Officer@123`).
2. Demonstrate complaint lifecycle: transition complaint `registered` $\to$ `under_initial_review` $\to$ `under_process`. Log an investigation timeline action.
3. Navigate to **Reports & Analytics**: click **Export CSV** to show instant download of `aicte_oneview_complaints_report.csv`.
4. Log out and log in as `readonly1` (`Readonly@123`): attempt to register a complaint $\to$ Show UI restriction and backend HTTP 403 Forbidden rejection.

---

## 8. Evaluator Questions & Technically Accurate Answers

**Q1: Why are you using a RapidFuzz rules baseline instead of an LLM or deep learning embedding model?**  
*Answer:* In administrative regulatory oversight, transparency, determinism, and explainability are paramount. RapidFuzz `rules-v1` delivers a 5-dimension score breakdown (Institution 30 pts, Description 35 pts, Category 15 pts, Date 10 pts, Keyword 10 pts) that officers can understand and verify in seconds. Furthermore, our synthetic benchmark of 62 pairs demonstrated 100% recall with 0 false negatives on duplicate cases. Using an opaque deep learning model on a small dataset would introduce high hallucination and data leakage risks without demonstrable accuracy benefits. The architecture provides pluggable interfaces in `backend/app/ml/` for when a real-world dataset with thousands of labeled records becomes available.

**Q2: How does the system prevent Broken Object Level Authorization (BOLA/IDOR)?**  
*Answer:* Backend authorization is enforced at the service and route layer, independent of frontend button visibility. In `backend/app/api/complaints.py`, `check_complaint_write_access` inspects the authenticated JWT token: if the user has role `BUREAU_OFFICER`, their assigned `bureau_id` must match the complaint's `bureau_id`. Cross-bureau write, transfer, and case action attempts are rejected with HTTP 403 Forbidden. Similarly, supervisory duplicate linking decisions are restricted exclusively to `ADMIN` and `SUPERVISORY_REVIEWER`.

**Q3: How are priority scores calculated, and can officers arbitrarily override them?**  
*Answer:* The Priority Engine evaluates six objective dimensions: category urgency weight (0–35), institutional impact/risk (0–25), deadline pressure (0–20), ageing inaction (0–10), escalation multiplier (0–10), and transfer penalty (0–5). The calculated score is capped at 100. An officer cannot silently alter the score; authorized supervisors can submit an official priority override, which requires a mandatory written reason and is permanently recorded in the immutable audit log and case history.

**Q4: How do you prevent accidental duplicate submissions from users clicking 'Submit' repeatedly?**  
*Answer:* We implemented an idempotent deduplication guard in `POST /api/complaints`. If an identical request (same title, category, and institution) arrives within 30 seconds of an existing submission, the backend detects the collision and responds with HTTP 409 Conflict, citing the existing complaint ID without creating redundant database records.

**Q5: How does the application handle data exports for officers from different bureaus?**  
*Answer:* The export endpoint (`GET /api/reports/export`) enforces role scoping. While Administrators, Supervisory Reviewers, and Auditors can export council-wide records, Bureau Officers are automatically restricted to complaints belonging to their assigned bureau. If an officer explicitly requests another bureau's ID in the query parameters, the request is rejected with HTTP 403 Forbidden.
