import json
import time
from typing import Any, Dict, List

import app.schemas as schemas
from app.config.config import config
from app.services.leetcode import LeetCodeService


class OpenAILLMService:
    def __init__(self):
        self.api_key = config.OPENAI_API_KEY
        self.model = config.OPENAI_MODEL or "gpt-5.4-mini"
        self.leetcode_service = LeetCodeService()
        self.client = None

        if not self.api_key:
            print("Warning: OPENAI_API_KEY not found in environment variables.")
            return

        try:
            from openai import OpenAI

            self.client = OpenAI(api_key=self.api_key)
        except Exception as e:
            print(f"Warning: OpenAI client unavailable: {e}")

    def _call_with_retry(self, prompt: str, schema: Dict[str, Any] = None) -> str:
        if not self.client:
            raise RuntimeError("OpenAI client is not configured.")

        retries = 3
        delay = 2
        payload = {
            "model": self.model,
            "input": prompt,
        }

        if schema:
            payload["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": schema["name"],
                    "schema": schema["schema"],
                    "strict": True,
                }
            }

        for i in range(retries):
            try:
                response = self.client.responses.create(**payload)
                return response.output_text
            except Exception as e:
                message = str(e).lower()
                if ("429" in message or "rate limit" in message or "temporarily unavailable" in message) and i < retries - 1:
                    print(f"[WARNING] OpenAI rate limit or transient error. Retrying in {delay}s...")
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise e

    def _parse_json(self, text: str) -> Any:
        text = text.replace("```json", "").replace("```", "").strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start_obj = text.find("{")
            end_obj = text.rfind("}") + 1
            start_arr = text.find("[")
            end_arr = text.rfind("]") + 1

            if start_arr != -1 and end_arr > start_arr and (start_obj == -1 or start_arr < start_obj):
                return json.loads(text[start_arr:end_arr])
            if start_obj != -1 and end_obj > start_obj:
                return json.loads(text[start_obj:end_obj])
            raise

    def generate(self, prompt: str) -> str:
        if not self.api_key or not self.client:
            raise RuntimeError("OPENAI_API_KEY missing or OpenAI client unavailable.")
        return self._call_with_retry(prompt)

    def summarize(self, proof: schemas.ProofCreate) -> Dict[str, Any]:
        if not self.api_key or not self.client:
            return {"summary": "OpenAI API key missing. Using mock summary."}

        try:
            repo_url = proof.payload.get("repo_url")
            artifact_link = proof.payload.get("artifact_link")
            context = proof.payload.get("context", "No context provided")

            target_type = "GitHub repository" if repo_url else "Work Artifact"
            target_ref = repo_url or artifact_link or "No link provided"

            prompt = f"""
            Analyze the following {target_type} proof and provide a concise summary.
            Reference: {target_ref}
            Context: {context}

            Output JSON format:
            {{
                "summary": "Brief summary of the submission...",
                "tech_stack": ["list", "of", "technologies", "or", "skills"],
                "complexity": "Low/Medium/High"
            }}
            """
            schema = {
                "name": "proof_summary",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["summary", "tech_stack", "complexity"],
                    "properties": {
                        "summary": {"type": "string"},
                        "tech_stack": {"type": "array", "items": {"type": "string"}},
                        "complexity": {"type": "string", "enum": ["Low", "Medium", "High"]},
                    },
                },
            }
            text = self._call_with_retry(prompt, schema)
            return self._parse_json(text)
        except Exception as e:
            print(f"OpenAI Summary Error: {e}")
            return {"summary": "Error generating summary via OpenAI."}

    def interpret_signals(self, task_description: str, evidence: List[Dict], payload: Dict[str, Any] = None) -> Dict[str, Any]:
        if not self.api_key or not self.client:
            return {"strength": 0.0, "justification": "API Key missing.", "relevant_evidence": "None"}

        try:
            evidence_text = ""
            for item in evidence:
                if item.get("type") == "code_snippet":
                    evidence_text += f"File: {item.get('ref')}\nCode:\n{item.get('snippet')}\n\n"
                elif item.get("type") == "file_ref":
                    evidence_text += f"File Reference: {item.get('ref')}\ninfo: {item.get('snippet')}\n\n"
                elif item.get("type") == "repo_context":
                    evidence_text += f"\nRepo Context:\n{item.get('snippet')}\n\n"
                elif item.get("type") == "heuristic_context":
                    evidence_text += f"\n{item.get('snippet')}\n\n"
                elif item.get("type") == "leetcode_stats":
                    evidence_text += f"\n[Signal: LeetCode Stats]\n{item.get('snippet')}\n\n"

            if payload and payload.get("leetcode_username"):
                if not any(e.get("type") == "leetcode_stats" for e in evidence):
                    username = payload.get("leetcode_username")
                    stats = self.leetcode_service.fetch_stats(username)
                    evidence_text += f"\nLeetCode Stats for user '{username}':\n{stats}\n\n"

            has_code = any(item.get("type") in ["code_snippet", "repo_context"] for item in evidence)
            has_artifact = any(item.get("type") == "work_artifact" for item in evidence)

            if has_artifact and not has_code:
                persona = "Act as an EXPERT HIRING MANAGER evaluating a candidate's work artifact."
                criteria = """
                Your job is to verify THREE things:
                1. RELEVANCE: Does this artifact directly support the outcome?
                2. QUALITY: Is the artifact professional, thoughtful, and high-quality?
                3. CONTEXT: Does the candidate's description explain their specific contribution clearly?

                If the evidence is unrelated, cap strength at 0.1. Score from 0.0 to 1.0 based on confidence that this person is capable.
                """
            else:
                persona = "Act as an EXPERT TECHNICAL EVALUATOR."
                criteria = """
                Analyze whether the evidence proves capability for the specific task.
                Weight capability most heavily, then identity verification and project quality as secondary bonuses.
                Strong relevant code should score 0.7-1.0, partial matches 0.4-0.7, and weak or irrelevant evidence 0.0-0.4.
                """

            prompt = f"""
            {persona}

            Task: "{task_description}"

            Evidence Provided:
            {evidence_text[:50000]}

            Scoring criteria:
            {criteria}

            Return only JSON with:
            - strength: 0.0 to 1.0
            - justification: 2-3 sentences
            - relevant_evidence: key quote, file, or detail
            - dimensions: project_completion, engineering_quality, communication, innovation, depth_novelty from 0.0 to 10.0
            """
            schema = {
                "name": "signal_interpretation",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["strength", "justification", "relevant_evidence", "dimensions"],
                    "properties": {
                        "strength": {"type": "number"},
                        "justification": {"type": "string"},
                        "relevant_evidence": {"type": "string"},
                        "dimensions": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": [
                                "project_completion",
                                "engineering_quality",
                                "communication",
                                "innovation",
                                "depth_novelty",
                            ],
                            "properties": {
                                "project_completion": {"type": "number"},
                                "engineering_quality": {"type": "number"},
                                "communication": {"type": "number"},
                                "innovation": {"type": "number"},
                                "depth_novelty": {"type": "number"},
                            },
                        },
                    },
                },
            }

            print(f"DEBUG: Sent OpenAI Prompt (Length: {len(prompt)})")
            text = self._call_with_retry(prompt, schema)
            print(f"DEBUG: OpenAI Raw Output: {text[:500]}...")
            result = self._parse_json(text)
            result["strength"] = max(0.0, min(1.0, float(result.get("strength", 0.0))))
            for key in ["project_completion", "engineering_quality", "communication", "innovation", "depth_novelty"]:
                dimensions = result.setdefault("dimensions", {})
                dimensions[key] = max(0.0, min(10.0, float(dimensions.get(key, 0.0))))
            return result
        except Exception as e:
            print(f"LLM Interpretation Error: {e}")
            return {
                "strength": 0.0,
                "justification": "Error processing evidence via AI.",
                "relevant_evidence": "Error",
                "dimensions": {
                    "project_completion": 0,
                    "engineering_quality": 0,
                    "communication": 0,
                    "innovation": 0,
                    "depth_novelty": 0,
                },
            }

    def generate_tasks(self, description: str) -> List[Dict[str, Any]]:
        def get_fallback_tasks(desc: str):
            print(f"Triggering Smart Fallback v2 for: {desc[:50]}...")
            desc_lower = desc.lower()
            possible_tasks = []

            if any(k in desc_lower for k in ["api", "backend", "fastapi", "flask", "django", "node", "express"]):
                possible_tasks.append({"name": "Design RESTful API Specification", "priority": "High"})
                possible_tasks.append({"name": "Implement Core Business Logic", "priority": "High"})

            if any(k in desc_lower for k in ["data", "sql", "schema", "db", "postgres", "mongo"]):
                possible_tasks.append({"name": "Design Database Schema & Migrations", "priority": "High"})

            if any(k in desc_lower for k in ["ui", "frontend", "react", "vue", "angular", "css", "web"]):
                possible_tasks.append({"name": "Build Reusable Component Library", "priority": "Medium"})
                possible_tasks.append({"name": "Implement Responsive Layouts", "priority": "Medium"})

            if any(k in desc_lower for k in ["auth", "login", "security", "jwt", "oauth"]):
                possible_tasks.append({"name": "Implement Secure Authentication", "priority": "High"})

            if any(k in desc_lower for k in ["ml", "ai", "scikit", "nlp", "classification", "model", "train"]):
                possible_tasks.append({"name": "Train & Evaluate ML Model", "priority": "High"})
                possible_tasks.append({"name": "Implement Inference Pipeline", "priority": "High"})

            if any(k in desc_lower for k in ["ci", "cd", "docker", "cloud", "deploy", "aws", "render"]):
                possible_tasks.append({"name": "Containerize Application", "priority": "Medium"})
                possible_tasks.append({"name": "Setup CI/CD Pipeline", "priority": "Medium"})

            if len(possible_tasks) < 3:
                possible_tasks.append({"name": "System Architecture Design", "priority": "High"})
                possible_tasks.append({"name": "Write Comprehensive Unit Tests", "priority": "Medium"})
                possible_tasks.append({"name": "Update Documentation", "priority": "Low"})

            seen_names = set()
            final_tasks = []
            for task in possible_tasks:
                if task["name"] not in seen_names:
                    final_tasks.append(task)
                    seen_names.add(task["name"])
                if len(final_tasks) >= 5:
                    break

            return final_tasks

        if not self.api_key or not self.client:
            print("No OpenAI API key found, using fallback.")
            return get_fallback_tasks(description)

        try:
            prompt = f"""
            Act as a Principal Engineer decomposing a project into technical tasks.

            Project Description: "{description}"

            Return 3-5 task objects. Each task must have:
            - name: short actionable title, e.g. "Design Database Schema"
            - priority: one of High, Medium, Low

            Ensure a mix of priorities. Do not mark everything High.
            """
            schema = {
                "name": "task_suggestions",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["tasks"],
                    "properties": {
                        "tasks": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["name", "priority"],
                                "properties": {
                                    "name": {"type": "string"},
                                    "priority": {"type": "string", "enum": ["High", "Medium", "Low"]},
                                },
                            },
                        }
                    },
                },
            }
            data = self._parse_json(self._call_with_retry(prompt, schema))
            return data["tasks"]
        except Exception as e:
            print(f"LLM Task Generation Error: {e}")
            return get_fallback_tasks(description)


llm_service = OpenAILLMService()
