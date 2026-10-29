import json
d = json.load(open("benchmark_summary.json"))
for r in d["api_benchmark"]["results"]:
    print(f"{r['label']:45s}  mean={r['mean_ms']}  P95={r['p95_ms']}  HTTP {r['dominant_status']}")
print()
print("Overlap:")
o = d["overlap_evaluation"]
print(f"  Pairs={o['total_pairs']}  TP={o['TP']} FP={o['FP']} TN={o['TN']} FN={o['FN']}")
print(f"  Precision={o['precision']}  Recall={o['recall']}  F1={o['f1_score']}")
print()
print("Priority:")
p = d["priority_evaluation"]
print(f"  Cases={p['total_cases']}  Correct={p['correct']}  Rate={p['agreement_rate_pct']}%")
print()
print("RBAC:")
r = d["rbac_evaluation"]
print(f"  Total={r['total']}  Passed={r['passed']}  Failed={r['failed']}")

