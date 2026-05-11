from typing import List, Dict, Any

class Matcher:
    def __init__(self):
        # Dynamic task-to-signal mapping based on task title keywords
        self.task_signal_map = {
            # ML Tasks
            "ml": ["ml_model_present", "ml_libraries"],
            "model": ["ml_model_present", "ml_libraries"],
            "train": ["ml_model_present", "ml_libraries"],
            "inference": ["ml_model_present", "web_framework"],
            "classification": ["ml_model_present", "nlp_present"],
            
            # API Tasks
            "api": ["web_framework", "tests_present"],
            "restful": ["web_framework", "tests_present"],
            "endpoint": ["web_framework", "tests_present"],
            
            # Database Tasks
            "database": ["migrations_present", "tests_present"],
            "schema": ["migrations_present", "tests_present"],
            "migration": ["migrations_present"],
            
            # Frontend Tasks
            "component": ["frontend_present", "static_assets"],
            "frontend": ["frontend_present", "static_assets"],
            "layout": ["frontend_present", "static_assets"],
            "ui": ["frontend_present", "static_assets"],
            
            # Deployment Tasks
            "deploy": ["deployment_ready", "ci_cd_present"],
            "container": ["deployment_ready"],
            "docker": ["deployment_ready"],
            "ci/cd": ["ci_cd_present"],
            "pipeline": ["ci_cd_present"],
            
            # Business Logic
            "business": ["web_framework", "tests_present"],
            "logic": ["web_framework", "tests_present"],
            "core": ["web_framework", "tests_present"],
        }

    def _get_task_signals(self, task_title: str) -> List[str]:
        """Dynamically determine which signals are relevant for a task."""
        title_lower = task_title.lower()
        relevant_signals = set()
        
        for keyword, signals in self.task_signal_map.items():
            if keyword in title_lower:
                relevant_signals.update(signals)
        
        # Default to overall capability if no specific match
        if not relevant_signals:
            relevant_signals = {"web_framework", "tests_present"}
        
        return list(relevant_signals)

    def calculate_task_score(self, signal_strength: float) -> float:
        """
        Deterministic Scoring:
        The Score is simply the Signal Strength (0-1) representing how well the candidate satisfied THIS specific task.
        Weighting is handled by the overall Outcome Aggregator.
        """
        return max(0.0, min(1.0, signal_strength))

    def get_matched_reason(self, task_title: str, signals: Dict[str, Any]) -> List[str]:
         matched_signals = self._get_task_signals(task_title)
         
         # Build human-readable reasons
         reason_parts = []
         if signals.get("ml_model_present"):
             reason_parts.append("ML models found")
         if signals.get("web_framework"):
             reason_parts.append("Web framework detected")
         if signals.get("frontend_present"):
             reason_parts.append("Frontend templates present")
         if signals.get("deployment_ready"):
             reason_parts.append("Deployment artifacts found")
         if signals.get("tests_present"):
             reason_parts.append("Tests present")
         
         if reason_parts:
             return [", ".join(reason_parts)]
         else:
             return [f"Matched on {', '.join(matched_signals)}"]
