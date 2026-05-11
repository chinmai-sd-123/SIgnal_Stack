from typing import Dict, Any

class SignalNormalizer:
    def normalize(self, signals: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize signals into a score.
        This roughly corresponds to the scoring logic from the old Extractor.
        """
        # Weight the signals
        weighted_signals = {
            "ml_model_present": 0.2,
            "ml_libraries": 0.15,
            "web_framework": 0.15,
            "nlp_present": 0.1,
            "tests_present": 0.1,
            "deployment_ready": 0.1,
            "frontend_present": 0.1,
            "static_assets": 0.05,
            "ci_cd_present": 0.05
        }
        
        overall_score = sum(signals.get(s, 0) * w for s, w in weighted_signals.items())
        signals["overall_score"] = round(overall_score, 2)
        
        return signals
