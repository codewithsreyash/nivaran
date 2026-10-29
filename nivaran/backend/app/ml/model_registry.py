# ML Module — Model Registry
# Status: Rules-based baseline active. No model file loaded.

from typing import Dict, Any

MODEL_STATUS: Dict[str, str] = {
    "duplicate_detector": "rules_fallback",
    "priority_predictor": "rules_fallback",
    "category_classifier": "not_implemented",
    "credibility_review": "rules_fallback",
}


def get_model_status() -> Dict[str, Any]:
    return {
        "overall": "Rules-based baseline active. No ML model trained.",
        "models": MODEL_STATUS,
        "note": (
            "To integrate a trained model, place the artifact in models/<model_name>/v1/, "
            "update MODEL_STATUS, and implement the load/predict interface in the "
            "corresponding module. See ml/README.md for instructions."
        ),
    }
