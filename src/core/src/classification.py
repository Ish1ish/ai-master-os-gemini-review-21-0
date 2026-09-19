from typing import Dict, Any


CLASS_LEVELS = {
    "public": 0,
    "internal": 1,
    "confidential": 2,
    "restricted": 3,
}


class DataClassifier:
    """
    Lightweight deterministic data classification for runtime policy.
    """

    def classify(self, data: Dict[str, Any]) -> Dict[str, Any]:
        text = str(data).lower()

        if any(k in text for k in ["password", "api_key", "secret", "private_key"]):
            level = "restricted"
        elif any(k in text for k in ["customer", "user_id", "email", "phone"]):
            level = "confidential"
        elif any(k in text for k in ["internal", "draft", "workflow"]):
            level = "internal"
        else:
            level = "public"

        handling = {
            "public": "normal",
            "internal": "limit_to_runtime",
            "confidential": "minimize_and_limit_access",
            "restricted": "never_log_plaintext",
        }

        return {
            "classification": level,
            "handling": handling[level],
            "score": CLASS_LEVELS[level],
        }
