from typing import List, Optional
import app.schemas as schemas

class Allocator:
    def create_allocation(self, task, best_candidate: Optional[str], best_score: float, reasons: List[str], evidence: List[schemas.Evidence]) -> schemas.WorkAllocation:
        return schemas.WorkAllocation(
            task_id=task.id,
            task_title=task.name,
            recommended_candidate=best_candidate or "None",
            confidence=round(best_score, 2),
            reasons=reasons if reasons else ["No matching signals found"],
            evidence=evidence
        )
