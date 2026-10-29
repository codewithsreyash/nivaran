"""
Overlap Detection Evaluation and Lightweight ML Pipeline.

Phase 3 of AICTE OneView validation:
A. Evaluates the existing rules-based baseline (rules-v1) on a labeled dataset.
B. Trains a lightweight sklearn ML model on the same pairs.
C. Compares both on a held-out test split.
D. Saves the ML model artifact only if it demonstrably outperforms the baseline.

All data is SYNTHETIC DEMONSTRATION DATA.
Labels are never used as input features to avoid data leakage.

Usage:
    cd backend
    python -m app.ml.overlap_eval_and_train
"""
import sys, os, json, pickle, warnings
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Any

warnings.filterwarnings("ignore")

# ─── Load dataset ─────────────────────────────────────────────────────────────

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "tests", "data", "overlap_eval_pairs.json")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "overlap_classifier_v1.pkl")
THRESHOLD = 25.0  # Same as overlap_engine.py MIN_SIMILARITY_THRESHOLD


def load_pairs() -> Tuple[List[Dict], List[str]]:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    pairs = data["pairs"]
    labels = [p["label"] for p in pairs]  # kept separate from features
    return pairs, labels


# ─── Feature extraction (no label leakage) ────────────────────────────────────

def extract_features_from_pair(pair: Dict) -> Dict[str, Any]:
    """
    Extract pairwise comparison features from a complaint pair.
    Labels are never used here.
    """
    from rapidfuzz import fuzz

    c1, c2 = pair["c1"], pair["c2"]

    # Institution identity match
    id1 = c1.get("institution_id")
    id2 = c2.get("institution_id")
    if id1 and id2:
        inst_match = 1.0 if id1 == id2 else 0.0
    else:
        # name fallback
        n1 = (c1.get("institution_name") or "").lower().strip()
        n2 = (c2.get("institution_name") or "").lower().strip()
        inst_match = fuzz.token_sort_ratio(n1, n2) / 100.0 if n1 and n2 else 0.0
    inst_id_present = 1.0 if (id1 and id2) else 0.0

    # Category match
    cat_match = 1.0 if c1.get("category") == c2.get("category") else 0.0

    # Text similarity (title + description)
    t1 = (c1.get("title", "") + " " + c1.get("description", "")).lower()
    t2 = (c2.get("title", "") + " " + c2.get("description", "")).lower()
    desc_partial = fuzz.partial_ratio(t1, t2) / 100.0
    desc_token_set = fuzz.token_set_ratio(t1, t2) / 100.0
    title_sim = fuzz.token_sort_ratio(
        c1.get("title", "").lower(), c2.get("title", "").lower()
    ) / 100.0

    # Date distance (days)
    try:
        d1 = datetime.strptime(c1["incident_date"][:10], "%Y-%m-%d") if c1.get("incident_date") else None
        d2 = datetime.strptime(c2["incident_date"][:10], "%Y-%m-%d") if c2.get("incident_date") else None
        date_delta = abs((d1 - d2).days) if d1 and d2 else 30
    except Exception:
        date_delta = 30
    date_proximity = max(0.0, 1.0 - date_delta / 30.0)

    # Keyword overlap
    stop = {"the", "a", "an", "is", "was", "to", "of", "in", "and", "for", "at", "by", "on", "not"}
    tokens1 = {w for w in t1.split() if len(w) > 3 and w not in stop}
    tokens2 = {w for w in t2.split() if len(w) > 3 and w not in stop}
    kw_overlap = len(tokens1 & tokens2) / max(len(tokens1 | tokens2), 1)

    return {
        "inst_match": inst_match,
        "inst_id_present": inst_id_present,
        "cat_match": cat_match,
        "desc_partial": desc_partial,
        "desc_token_set": desc_token_set,
        "title_sim": title_sim,
        "date_proximity": date_proximity,
        "kw_overlap": kw_overlap,
    }


def rules_baseline_prediction(pair: Dict) -> Tuple[float, str]:
    """
    Run the rules-based engine on a pair and return (similarity_score, predicted_label).
    Threshold logic follows overlap_engine.py.
    """
    from rapidfuzz import fuzz

    c1, c2 = pair["c1"], pair["c2"]

    # Institution
    id1 = c1.get("institution_id")
    id2 = c2.get("institution_id")
    if id1 and id2:
        inst_score = 30.0 if id1 == id2 else 0.0
    else:
        n1 = (c1.get("institution_name") or "").lower()
        n2 = (c2.get("institution_name") or "").lower()
        inst_score = fuzz.token_sort_ratio(n1, n2) / 100.0 * 25.0 if (n1 and n2) else 0.0

    # Category
    cat_score = 15.0 if c1.get("category") == c2.get("category") else 0.0

    # Description
    d1 = (c1.get("description", "")).lower()
    d2 = (c2.get("description", "")).lower()
    if d1 and d2:
        p = fuzz.partial_ratio(d1, d2) / 100.0
        t = fuzz.token_set_ratio(d1, d2) / 100.0
        desc_score = (p * 0.4 + t * 0.6) * 35.0
    else:
        desc_score = 0.0

    # Date
    try:
        dt1 = datetime.strptime(c1["incident_date"][:10], "%Y-%m-%d") if c1.get("incident_date") else None
        dt2 = datetime.strptime(c2["incident_date"][:10], "%Y-%m-%d") if c2.get("incident_date") else None
        days = abs((dt1 - dt2).days) if dt1 and dt2 else 91
    except Exception:
        days = 91
    if days <= 7: date_score = 10.0
    elif days <= 30: date_score = 6.0
    elif days <= 90: date_score = 3.0
    else: date_score = 0.0

    # Keywords
    stop = {"the", "a", "an", "is", "was", "to", "of", "in", "and", "for", "at", "by", "on"}
    t1t = {w for w in (c1.get("title", "") + " " + c1.get("description", "")).lower().split()
           if len(w) > 3 and w not in stop}
    t2t = {w for w in (c2.get("title", "") + " " + c2.get("description", "")).lower().split()
           if len(w) > 3 and w not in stop}
    common = t1t & t2t
    kw_ratio = len(common) / max(len(t1t | t2t), 1)
    kw_score = min(kw_ratio * 20.0, 10.0)

    total = min(inst_score + cat_score + desc_score + date_score + kw_score, 100.0)
    # Baseline predicts "duplicate" if score >= threshold and same institution, else related/unrelated
    if total >= 70 and (inst_score >= 25):
        pred = "duplicate"
    elif total >= THRESHOLD and (inst_score >= 20 or cat_score > 0):
        pred = "related_independent"
    else:
        pred = "unrelated"

    return total, pred


# ─── Metrics ─────────────────────────────────────────────────────────────────

def compute_metrics(y_true: List[str], y_pred: List[str]) -> Dict:
    from collections import Counter
    classes = ["duplicate", "related_independent", "unrelated"]

    # Per-class P/R/F1
    results = {}
    for cls in classes:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == cls and p == cls)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != cls and p == cls)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == cls and p != cls)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        results[cls] = {"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3)}

    # Binary duplicate vs non-duplicate
    bin_true = ["duplicate" if y == "duplicate" else "not_duplicate" for y in y_true]
    bin_pred = ["duplicate" if y == "duplicate" else "not_duplicate" for y in y_pred]
    tp_b = sum(1 for t, p in zip(bin_true, bin_pred) if t == "duplicate" and p == "duplicate")
    fp_b = sum(1 for t, p in zip(bin_true, bin_pred) if t != "duplicate" and p == "duplicate")
    fn_b = sum(1 for t, p in zip(bin_true, bin_pred) if t == "duplicate" and p != "duplicate")
    prec_b = tp_b / (tp_b + fp_b) if (tp_b + fp_b) > 0 else 0.0
    rec_b = tp_b / (tp_b + fn_b) if (tp_b + fn_b) > 0 else 0.0
    f1_b = 2 * prec_b * rec_b / (prec_b + rec_b) if (prec_b + rec_b) > 0 else 0.0

    # Confusion matrix
    counts = Counter((t, p) for t, p in zip(y_true, y_pred))
    cm = {(t, p): counts.get((t, p), 0) for t in classes for p in classes}

    accuracy = sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true)

    return {
        "accuracy": round(accuracy, 3),
        "per_class": results,
        "binary_duplicate": {
            "precision": round(prec_b, 3), "recall": round(rec_b, 3), "f1": round(f1_b, 3)
        },
        "confusion_matrix": {str(k): v for k, v in cm.items()},
    }


def find_errors(pairs, labels, predictions, label_type="false_positive", target_class="duplicate"):
    errors = []
    for pair, true, pred in zip(pairs, labels, predictions):
        if label_type == "false_positive" and pred == target_class and true != target_class:
            errors.append({"pair_id": pair["pair_id"], "true": true, "pred": pred,
                           "c1_title": pair["c1"]["title"][:60], "c2_title": pair["c2"]["title"][:60]})
        elif label_type == "false_negative" and true == target_class and pred != target_class:
            errors.append({"pair_id": pair["pair_id"], "true": true, "pred": pred,
                           "c1_title": pair["c1"]["title"][:60], "c2_title": pair["c2"]["title"][:60]})
    return errors


# ─── ML Pipeline ─────────────────────────────────────────────────────────────

def build_feature_matrix(pairs: List[Dict]) -> np.ndarray:
    rows = []
    for p in pairs:
        f = extract_features_from_pair(p)
        rows.append([
            f["inst_match"], f["inst_id_present"], f["cat_match"],
            f["desc_partial"], f["desc_token_set"], f["title_sim"],
            f["date_proximity"], f["kw_overlap"],
        ])
    return np.array(rows)


def train_and_evaluate():
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import GroupShuffleSplit
    import random

    pairs, labels = load_pairs()
    n = len(pairs)
    print(f"\n{'='*60}")
    print(f"OVERLAP DETECTION EVALUATION — Phase 3")
    print(f"{'='*60}")
    print(f"Dataset: {n} synthetic pairs")
    from collections import Counter
    print(f"Label distribution: {dict(Counter(labels))}")
    print(f"\nNOTICE: All data is SYNTHETIC DEMONSTRATION DATA only.")

    # ─── Step A: Baseline evaluation (all pairs) ─────────────────────────────
    print(f"\n{'─'*40}")
    print("A. RULES-BASED BASELINE (rules-v1) — all {n} pairs".format(n=n))
    print(f"   Threshold: {THRESHOLD}")
    baseline_preds = []
    baseline_scores = []
    for p in pairs:
        score, pred = rules_baseline_prediction(p)
        baseline_preds.append(pred)
        baseline_scores.append(score)

    b_metrics = compute_metrics(labels, baseline_preds)
    print(f"   Accuracy : {b_metrics['accuracy']:.3f}")
    print(f"   Binary Duplicate — P:{b_metrics['binary_duplicate']['precision']:.3f}  "
          f"R:{b_metrics['binary_duplicate']['recall']:.3f}  "
          f"F1:{b_metrics['binary_duplicate']['f1']:.3f}")
    print(f"   Per-class:")
    for cls, m in b_metrics["per_class"].items():
        print(f"     {cls:25s} P={m['precision']:.3f}  R={m['recall']:.3f}  F1={m['f1']:.3f}")

    fp_list = find_errors(pairs, labels, baseline_preds, "false_positive", "duplicate")
    fn_list = find_errors(pairs, labels, baseline_preds, "false_negative", "duplicate")
    print(f"   False positives (predicted duplicate, not duplicate): {len(fp_list)}")
    for e in fp_list[:3]:
        print(f"     [{e['pair_id']}] true={e['true']:20s} | {e['c1_title'][:40]}…")
    print(f"   False negatives (missed duplicates): {len(fn_list)}")
    for e in fn_list[:3]:
        print(f"     [{e['pair_id']}] true={e['true']:20s} | {e['c1_title'][:40]}…")

    # ─── Step B: Train/test split — group by pair_id prefix ──────────────────
    # Use group-based split: pairs in same group stay in same split
    random.seed(42)
    group_ids = [p.get("group", p["pair_id"]) for p in pairs]
    unique_groups = list(set(group_ids))
    random.shuffle(unique_groups)
    split_idx = int(len(unique_groups) * 0.7)
    train_groups = set(unique_groups[:split_idx])

    train_mask = [g in train_groups for g in group_ids]
    test_mask = [not m for m in train_mask]

    pairs_train = [p for p, m in zip(pairs, train_mask) if m]
    pairs_test = [p for p, m in zip(pairs, test_mask) if m]
    labels_train = [l for l, m in zip(labels, train_mask) if m]
    labels_test = [l for l, m in zip(labels, test_mask) if m]

    print(f"\n{'─'*40}")
    print(f"B. ML MODEL — Train: {len(pairs_train)} pairs, Test: {len(pairs_test)} pairs")
    print(f"   Train labels: {dict(Counter(labels_train))}")
    print(f"   Test  labels: {dict(Counter(labels_test))}")

    if len(pairs_train) < 10 or len(set(labels_train)) < 2:
        print("   SKIP: insufficient training data for ML model.")
        return {"baseline": b_metrics, "ml": None, "decision": "rules_baseline_retained"}

    X_train = build_feature_matrix(pairs_train)
    X_test = build_feature_matrix(pairs_test)

    # Gradient Boosting Classifier (small, interpretable)
    clf = GradientBoostingClassifier(n_estimators=50, max_depth=3, random_state=42)
    clf.fit(X_train, labels_train)
    ml_preds_test = clf.predict(X_test).tolist()

    # Evaluate ML on test split
    ml_metrics = compute_metrics(labels_test, ml_preds_test)
    print(f"   ML Accuracy : {ml_metrics['accuracy']:.3f}")
    print(f"   ML Binary Duplicate — P:{ml_metrics['binary_duplicate']['precision']:.3f}  "
          f"R:{ml_metrics['binary_duplicate']['recall']:.3f}  "
          f"F1:{ml_metrics['binary_duplicate']['f1']:.3f}")
    print(f"   ML Per-class:")
    for cls, m in ml_metrics["per_class"].items():
        print(f"     {cls:25s} P={m['precision']:.3f}  R={m['recall']:.3f}  F1={m['f1']:.3f}")

    # Evaluate baseline on same test split
    baseline_test_preds = [rules_baseline_prediction(p)[1] for p in pairs_test]
    baseline_test_metrics = compute_metrics(labels_test, baseline_test_preds)
    print(f"\n   Baseline (same test split):")
    print(f"   Baseline Accuracy : {baseline_test_metrics['accuracy']:.3f}")
    print(f"   Baseline Binary F1: {baseline_test_metrics['binary_duplicate']['f1']:.3f}")

    # Feature importances
    feat_names = ["inst_match", "inst_id_present", "cat_match", "desc_partial",
                  "desc_token_set", "title_sim", "date_proximity", "kw_overlap"]
    importances = sorted(zip(feat_names, clf.feature_importances_), key=lambda x: -x[1])
    print(f"\n   Feature importances:")
    for fname, imp in importances:
        print(f"     {fname:20s}: {imp:.3f}")

    # ─── Step C: Decide whether ML is better ─────────────────────────────────
    ml_f1 = ml_metrics["binary_duplicate"]["f1"]
    base_f1 = baseline_test_metrics["binary_duplicate"]["f1"]
    ml_is_better = ml_f1 > base_f1 + 0.02  # require at least 2% improvement

    print(f"\n{'─'*40}")
    print(f"C. DECISION:")
    print(f"   Baseline F1 (test): {base_f1:.3f}")
    print(f"   ML       F1 (test): {ml_f1:.3f}")

    if ml_is_better:
        # Save model
        os.makedirs(MODEL_DIR, exist_ok=True)
        artifact = {
            "model": clf,
            "feature_names": feat_names,
            "version": "ml-v1",
            "trained_on": datetime.utcnow().isoformat(),
            "training_pairs": len(pairs_train),
            "test_pairs": len(pairs_test),
            "train_metrics": None,  # no train metrics to avoid leakage confusion
            "test_metrics": ml_metrics,
            "baseline_test_metrics": baseline_test_metrics,
            "dataset_note": "Trained on SYNTHETIC DEMONSTRATION DATA only.",
            "classes": list(clf.classes_),
            "threshold_for_positivity": 0.5,
        }
        with open(MODEL_PATH, "wb") as f:
            pickle.dump(artifact, f)
        print(f"   ML model SAVED to: {MODEL_PATH}")
        print(f"   Status: ML model integration recommended.")
        decision = "ml_model_saved"
    else:
        print(f"   ML improvement ({ml_f1:.3f} vs {base_f1:.3f}) insufficient.")
        print(f"   Status: Rules-based baseline retained. No ML artifact saved.")
        decision = "rules_baseline_retained"

    return {
        "baseline_all_pairs": b_metrics,
        "baseline_test_split": baseline_test_metrics,
        "ml_test_split": ml_metrics,
        "decision": decision,
        "ml_f1": ml_f1,
        "baseline_f1": base_f1,
    }


if __name__ == "__main__":
    results = train_and_evaluate()
    print(f"\n{'='*60}")
    print(f"FINAL DECISION: {results['decision']}")
    print(f"{'='*60}")
