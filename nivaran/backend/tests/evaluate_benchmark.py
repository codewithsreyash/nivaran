"""
Evaluation script for the 62-pair synthetic benchmark.
Tests RapidFuzz rules baseline against labeled synthetic pairs.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from app.models import Complaint, ComplaintCategory
from app.services.overlap_engine import compute_overlap

data_path = os.path.join(os.path.dirname(__file__), "data", "overlap_eval_pairs.json")
with open(data_path, "r", encoding="utf-8") as f:
    data = json.load(f)

pairs = data["pairs"]
print(f"Total pairs in synthetic benchmark: {len(pairs)}")

labels = {}
for p in pairs:
    lbl = p["label"]
    labels[lbl] = labels.get(lbl, 0) + 1
print("Class distribution:", labels)

scores_by_label = {"duplicate": [], "related_independent": [], "unrelated": []}

for p in pairs:
    c1_d = p["c1"]
    c2_d = p["c2"]
    d1 = datetime.strptime(c1_d.get("incident_date", "2026-08-01"), "%Y-%m-%d")
    d2 = datetime.strptime(c2_d.get("incident_date", "2026-08-01"), "%Y-%m-%d")

    comp1 = Complaint(
        title=c1_d["title"],
        description=c1_d["description"],
        category=ComplaintCategory(c1_d["category"]),
        institution_name_snapshot=c1_d.get("institution_name"),
        registration_date=d1,
        incident_date=d1,
    )
    comp2 = Complaint(
        title=c2_d["title"],
        description=c2_d["description"],
        category=ComplaintCategory(c2_d["category"]),
        institution_name_snapshot=c2_d.get("institution_name"),
        registration_date=d2,
        incident_date=d2,
    )
    res = compute_overlap(comp1, comp2)
    score = res["similarity_score"]
    scores_by_label[p["label"]].append(score)

print("\nScore ranges by label:")
for k, v in scores_by_label.items():
    print(f"  {k} (n={len(v)}): min={min(v):.1f}, max={max(v):.1f}, avg={sum(v)/len(v):.1f}")

# Binary classification: 'duplicate' (positive) vs 'unrelated' + 'related_independent' (negative)
# Decision threshold = 50.0 (high confidence duplicate)
tp = sum(1 for s in scores_by_label["duplicate"] if s >= 50.0)
fn = sum(1 for s in scores_by_label["duplicate"] if s < 50.0)
fp = sum(1 for s in scores_by_label["related_independent"] + scores_by_label["unrelated"] if s >= 50.0)
tn = sum(1 for s in scores_by_label["related_independent"] + scores_by_label["unrelated"] if s < 50.0)

prec = tp / (tp + fp) if (tp + fp) else 0
rec = tp / (tp + fn) if (tp + fn) else 0
f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0
acc = (tp + tn) / len(pairs)

print(f"\nRules Baseline Performance (Duplicate Detection Threshold >= 50.0):")
print(f"  True Positives (TP):  {tp}")
print(f"  False Positives (FP): {fp}")
print(f"  True Negatives (TN):  {tn}")
print(f"  False Negatives (FN): {fn}")
print(f"  Precision:            {prec:.4f}")
print(f"  Recall:               {rec:.4f}")
print(f"  F1 Score:             {f1:.4f}")
print(f"  Overall Accuracy:     {acc:.4f} ({acc*100:.1f}%)")

# Triage threshold >= 25.0 (flagged for human review)
dup_recalled = sum(1 for s in scores_by_label["duplicate"] if s >= 25.0)
rel_flagged = sum(1 for s in scores_by_label["related_independent"] if s >= 25.0)
unrel_flagged = sum(1 for s in scores_by_label["unrelated"] if s >= 25.0)
unrel_rejected = sum(1 for s in scores_by_label["unrelated"] if s < 25.0)

print(f"\nReview Screening Performance (Triage Threshold >= 25.0):")
print(f"  Duplicates Flagged for Review: {dup_recalled}/{len(scores_by_label['duplicate'])} ({dup_recalled/len(scores_by_label['duplicate']):.1%})")
print(f"  Related Cases Flagged for Review: {rel_flagged}/{len(scores_by_label['related_independent'])} ({rel_flagged/len(scores_by_label['related_independent']):.1%})")
print(f"  Unrelated Cases Rejected (Clean): {unrel_rejected}/{len(scores_by_label['unrelated'])} ({unrel_rejected/len(scores_by_label['unrelated']):.1%})")
