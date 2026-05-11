from typing import List
from app.services.llm import OpenAILLMService as LLMService
import app.schemas as schemas

class TaskDecomposer:
    def __init__(self, llm_service: LLMService = None):
        self.llm_service = llm_service or LLMService()

    def split(self, description: str) -> List[schemas.TaskSuggestion]:
        try:
            tasks = self.llm_service.generate_tasks(description)
            return [schemas.TaskSuggestion(**t) for t in tasks]
        except Exception as e:
            print(f"TaskDecomposer Error: {e}")
            # Absolute fallback
            return [
                schemas.TaskSuggestion(name="Analyze Requirements", priority="High"),
                schemas.TaskSuggestion(name="Implementation", priority="Medium"),
                schemas.TaskSuggestion(name="Testing & Verification", priority="Low")
            ]
