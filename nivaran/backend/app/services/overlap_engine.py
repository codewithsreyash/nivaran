"""
Overlap / Duplicate Detection Service — Rules-based baseline.
Status: Rules-based baseline active. No ML model trained.

Similarity score (0–100):
  Institution identity:    30 pts
  Description similarity:  35 pts
  Category match:          15 pts
  Date proximity:          10 pts
  Keyword overlap:         10 pts
"""
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from rapidfuzz import fuzz
from sqlalchemy.orm import Session
from ..models import Complaint, OverlapResult, Institution

ALGORITHM_VERSION = "rules-v1"
MIN_SIMILARITY_THRESHOLD = 25.0


def _institution_score(c1: Complaint, c2: Complaint) -> Tuple[float, str]:
    """Return institution similarity score (0–30) and explanation."""
    if c1.institution_id and c2.institution_id:
        if c1.institution_id == c2.institution_id:
            return 30.0, "Same verified institution."
        else:
            return 0.0, "Different institutions."
    # Fall back to name comparison
    n1 = (c1.institution_name_snapshot or "").strip().lower()
    n2 = (c2.institution_name_snapshot or "").strip().lower()
    if not n1 or not n2:
        return 0.0, "Institution identity uncertain — one or both missing."
    ratio = fuzz.token_sort_ratio(n1, n2) / 100.0
    return round(ratio * 25.0, 2), f"Institution name similarity {ratio:.0%} (unverified)."


def _category_score(c1: Complaint, c2: Complaint) -> Tuple[float, str]:
    if c1.category == c2.category:
        return 15.0, "Same category."
    return 0.0, "Different categories."


def _description_score(c1: Complaint, c2: Complaint) -> Tuple[float, str]:
    d1 = (c1.description or "").strip()
    d2 = (c2.description or "").strip()
    if not d1 or not d2:
        return 0.0, "One or both descriptions missing."
    partial = fuzz.partial_ratio(d1.lower(), d2.lower()) / 100.0
    token = fuzz.token_set_ratio(d1.lower(), d2.lower()) / 100.0
    combined = (partial * 0.4 + token * 0.6)
    return round(combined * 35.0, 2), f"Description similarity {combined:.0%}."


def _date_score(c1: Complaint, c2: Complaint) -> Tuple[float, str]:
    d1 = c1.incident_date or c1.registration_date
    d2 = c2.incident_date or c2.registration_date
    if not d1 or not d2:
        return 0.0, "Date proximity unavailable (missing dates)."
    delta_days = abs((d1 - d2).days)
    if delta_days <= 7:
        return 10.0, f"Dates within {delta_days} day(s) of each other."
    elif delta_days <= 30:
        return 6.0, f"Dates within {delta_days} day(s)."
    elif delta_days <= 90:
        return 3.0, f"Dates {delta_days} days apart."
    return 0.0, f"Dates {delta_days} days apart — likely different events."


def _keyword_overlap(c1: Complaint, c2: Complaint) -> Tuple[float, List[str], str]:
    stop = {"the", "a", "an", "is", "was", "to", "of", "in", "and", "for", "at", "by", "on"}
    def tokens(text: str) -> set:
        return {w for w in text.lower().split() if len(w) > 3 and w not in stop}
    t1 = tokens(c1.title + " " + c1.description)
    t2 = tokens(c2.title + " " + c2.description)
    common = t1 & t2
    if not t1 or not t2:
        return 0.0, [], "Keywords unavailable."
    ratio = len(common) / max(len(t1), len(t2))
    score = min(ratio * 10.0 * 2, 10.0)
    keywords = list(common)[:10]
    return round(score, 2), keywords, f"{len(common)} shared keyword(s)."


def compute_overlap(c1: Complaint, c2: Complaint) -> Dict[str, Any]:
    """Compute full overlap result between two complaints."""
    inst_score, inst_note = _institution_score(c1, c2)
    cat_score, cat_note = _category_score(c1, c2)
    desc_score, desc_note = _description_score(c1, c2)
    date_score, date_note = _date_score(c1, c2)
    kw_score, keywords, kw_note = _keyword_overlap(c1, c2)

    total = inst_score + desc_score + cat_score + date_score + kw_score
    total = min(total, 100.0)

    conflicting = []
    if c1.category != c2.category:
        conflicting.append(f"Category mismatch: {c1.category.value} vs {c2.category.value}")
    if c1.institution_id and c2.institution_id and c1.institution_id != c2.institution_id:
        conflicting.append("Different verified institutions")

    missing = []
    if not c1.institution_id:
        missing.append(f"Institution ID missing for complaint {c1.complaint_id}")
    if not c2.institution_id:
        missing.append(f"Institution ID missing for complaint {c2.complaint_id}")

    return {
        "similarity_score": round(total, 2),
        "institution_score": inst_score,
        "description_score": desc_score,
        "category_score": cat_score,
        "date_score": date_score,
        "keyword_score": kw_score,
        "matching_keywords": keywords,
        "conflicting_info": "; ".join(conflicting) if conflicting else None,
        "missing_data_notes": "; ".join(missing) if missing else None,
        "algorithm_version": ALGORITHM_VERSION,
        "details": {
            "institution": inst_note,
            "category": cat_note,
            "description": desc_note,
            "dates": date_note,
            "keywords": kw_note,
        },
    }


def detect_overlaps_for_complaint(
    db: Session, complaint: Complaint, max_candidates: int = 20
) -> List[OverlapResult]:
    """
    Find potential duplicate/related complaints for a given complaint.
    Saves results to DB and returns list of OverlapResult objects.
    """
    # Candidate pool: same bureau or institution, not itself, not already disposed/closed
    candidates = db.query(Complaint).filter(
        Complaint.id != complaint.id,
        Complaint.status.notin_(["disposed", "closed"]),
    )
    if complaint.institution_id:
        candidates = candidates.filter(Complaint.institution_id == complaint.institution_id)
    candidates = candidates.limit(200).all()

    results = []
    for candidate in candidates:
        # Skip if already computed recently
        existing = db.query(OverlapResult).filter(
            OverlapResult.primary_complaint_id == complaint.id,
            OverlapResult.candidate_complaint_id == candidate.id,
        ).first()
        if existing:
            results.append(existing)
            continue

        data = compute_overlap(complaint, candidate)
        if data["similarity_score"] < MIN_SIMILARITY_THRESHOLD:
            continue

        result = OverlapResult(
            primary_complaint_id=complaint.id,
            candidate_complaint_id=candidate.id,
            **{k: v for k, v in data.items() if k != "details"},
        )
        db.add(result)
        results.append(result)

    db.commit()
    return results
