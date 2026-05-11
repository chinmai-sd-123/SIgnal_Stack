import json
import logging
import time
from typing import Any, Dict, List

import app.schemas as schemas
from app.config.config import config
from app.services.cache import cache
from app.services.leetcode import LeetCodeService


logger = logging.getLogger(__name__)


class OpenAILLMService:
    def __init__(self):
        self.api_key = config.OPENAI_API_KEY
        self.model = config.OPENAI_MODEL or "gpt-5.4-mini"
        self.leetcode_service = LeetCodeService()
        self.client = None

        if not self.api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables.")
            return

        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except Exception as e:
            logger.warning("OpenAI client unavailable: %s", e)

    def _extract_text(self, response: Any) -> str:
        if hasattr(response, "output_text"):
            return response.output_text
        if hasattr(response, "output") and response.output:
            first = response.output[0]
            if hasattr(first, "content") and first.content:
                content = first.content[0]
                if hasattr(content, "text"):
                    return content.text
        if hasattr(response, "choices") and response.choices:
            message = response.choices[0].message
            if isinstance(message, dict):
                return message.get("content", "")
            return getattr(message, "content", "") or ""
        return str(response)

    def _call_with_retry(self, prompt: str, schema: Dict[str, Any] = None) -> str:
        if not self.client:
            raise RuntimeError("OpenAI client is not configured.")

        retries = 3
        delay = 2
        payload = {
            "model": self.model,
            "input": prompt,
        }

        cache_key = None
        if prompt:
            schema_name = schema.get("name", "none") if schema else "none"
            cache_key = f"{self.model}|{schema_name}|{prompt}"
            cached = cache.get_llm_response_by_prompt(cache_key)
            if isinstance(cached, str) and cached.strip():
                return cached

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
                text = self._extract_text(response)
                if cache_key:
                    cache.set_llm_response(cache_key, text, ttl=3600)
                return text
            except Exception as e:
                message = str(e).lower()
                if ("429" in message or "rate limit" in message or "temporarily unavailable" in message) and i < retries - 1:
                    logger.warning("OpenAI rate limit. Retrying in %ss...", delay)
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

    # ── NEW: structured evidence formatter ──────────────────────────────────
    def _build_evidence_sections(self, evidence: List[Dict]) -> str:
        """
        Format evidence into clearly labelled sections so the LLM can
        distinguish deterministic facts from code from authorship context.
        Caps each section to avoid primacy-bias from front-loading.
        """
        sections = {
            "DETERMINISTIC_FACTS": [],   # heuristic_context — machine-verified
            "CODE_SNIPPETS":        [],  # code_snippet
            "REPO_STRUCTURE":       [],  # repo_context
            "AUTHORSHIP":           [],  # authorship_context
            "WORK_ARTIFACT":        [],  # work_artifact
            "LEETCODE":             [],  # leetcode_stats
        }

        TYPE_MAP = {
            "heuristic_context":  "DETERMINISTIC_FACTS",
            "code_snippet":       "CODE_SNIPPETS",
            "repo_context":       "REPO_STRUCTURE",
            "authorship_context": "AUTHORSHIP",
            "work_artifact":      "WORK_ARTIFACT",
            "leetcode_stats":     "LEETCODE",
            "file_ref":           "CODE_SNIPPETS",
        }

        for item in evidence:
            bucket = TYPE_MAP.get(item.get("type", ""), "CODE_SNIPPETS")
            ref = item.get("ref", "")
            snippet = item.get("snippet", "")
            # Skip AI_FINDING injections — they're derived, not source evidence
            if ref.startswith("AI_FINDING:"):
                continue
            sections[bucket].append(f"[{ref}]\n{snippet}")

        parts = []

        # Deterministic facts always come first and are labelled as authoritative
        if sections["DETERMINISTIC_FACTS"]:
            parts.append(
                "=== DETERMINISTIC FACTS (machine-verified, do not contradict) ===\n"
                + "\n---\n".join(sections["DETERMINISTIC_FACTS"])
            )

        # Code snippets — capped at 8000 chars to avoid primacy bias
        if sections["CODE_SNIPPETS"]:
            code_block = "\n---\n".join(sections["CODE_SNIPPETS"])
            parts.append(
                "=== CODE EVIDENCE ===\n"
                + code_block[:8000]
                + ("\n[... truncated ...]" if len(code_block) > 8000 else "")
            )

        if sections["AUTHORSHIP"]:
            parts.append(
                "=== AUTHORSHIP ANALYSIS ===\n"
                + "\n---\n".join(sections["AUTHORSHIP"])
            )

        if sections["REPO_STRUCTURE"]:
            repo_block = "\n---\n".join(sections["REPO_STRUCTURE"])
            parts.append(
                "=== REPOSITORY STRUCTURE ===\n"
                + repo_block[:3000]
                + ("\n[... truncated ...]" if len(repo_block) > 3000 else "")
            )

        if sections["WORK_ARTIFACT"]:
            parts.append(
                "=== WORK ARTIFACT ===\n"
                + "\n---\n".join(sections["WORK_ARTIFACT"])
            )

        if sections["LEETCODE"]:
            parts.append(
                "=== LEETCODE STATS ===\n"
                + "\n---\n".join(sections["LEETCODE"])
            )

        return "\n\n".join(parts)

    # ── FIXED: interpret_signals ────────────────────────────────────────────
    def interpret_signals(
        self,
        task_description: str,
        evidence: List[Dict],
        payload: Dict[str, Any] = None
    ) -> Dict[str, Any]:

        if not self.api_key or not self.client:
            return {
                "strength": 0.0,
                "justification": "API Key missing.",
                "relevant_evidence": "None",
                "dimensions": {k: 0.0 for k in [
                    "project_completion", "engineering_quality",
                    "communication", "innovation", "depth_novelty"
                ]}
            }

        try:
            # LeetCode injection if not already in evidence
            if payload and payload.get("leetcode_username"):
                if not any(e.get("type") == "leetcode_stats" for e in evidence):
                    username = payload["leetcode_username"]
                    stats = self.leetcode_service.fetch_stats(username)
                    evidence = list(evidence) + [{
                        "type": "leetcode_stats",
                        "ref": "LEETCODE",
                        "snippet": (
                            f"LeetCode Profile: {username}\n"
                            f"Total Solved: {stats.get('total_solved')} "
                            f"(Easy: {stats.get('easy_solved')}, "
                            f"Med: {stats.get('medium_solved')}, "
                            f"Hard: {stats.get('hard_solved')})\n"
                            f"Acceptance Rate: {stats.get('acceptance_rate')}%\n"
                            f"Ranking: {stats.get('ranking')}"
                        )
                    }]

            has_code = any(e.get("type") in ("code_snippet", "repo_context") for e in evidence)
            has_artifact = any(e.get("type") == "work_artifact" for e in evidence)

            evidence_text = self._build_evidence_sections(evidence)

            # ── Persona + evaluation mode ─────────────────────────────────
            if has_artifact and not has_code:
                persona = (
                    "You are a senior hiring manager evaluating a non-technical work artifact. "
                    "You assess relevance, quality, and clarity of contribution."
                )
                scoring_rules = """
SCORING RULES:
- 0.0–0.2: Artifact is unrelated to the task or missing entirely.
- 0.2–0.4: Artifact exists but relevance to the task is weak or unclear.
- 0.4–0.6: Artifact is relevant but lacks depth, specificity, or professionalism.
- 0.6–0.8: Artifact clearly supports the task with good quality evidence.
- 0.8–1.0: Artifact is directly on-point, high quality, and demonstrates clear ownership.

EARLY APPLICATION GUIDANCE:
- Treat tests, CI, Docker, and deployment files as bonus quality signals for personal projects, not baseline requirements.
- A working, relevant implementation can score in the 0.6-0.8 range even without tests or CI.

PENALTIES (apply before scoring):
- If the artifact description could apply to any candidate generically: -0.2
- If the candidate's specific contribution is not explained: -0.15
"""
            else:
                persona = (
                    "You are a senior software engineer conducting a technical code review "
                    "to determine if a candidate has implemented a specific capability."
                )
                scoring_rules = """
SCORING RULES (follow strictly):
- 0.0–0.2: No relevant code found, or code is clearly copied/template boilerplate.
- 0.2–0.4: Some related files exist but implementation is incomplete or incorrect.
- 0.4–0.6: Partial implementation — core logic present but missing key parts.
- 0.6–0.8: Complete implementation with minor gaps (e.g. no error handling, no tests).
- 0.8–1.0: Full, working implementation with tests, error handling, and clean structure.

PENALTIES (apply before scoring):
- If DETERMINISTIC FACTS show tests_present=NO and the task explicitly requires tests or production-grade reliability: -0.05
- If DETERMINISTIC FACTS show ci_cd_present=NO and the task is specifically about deployment, CI/CD, or DevOps automation: -0.05
- If authorship is unverified: do not penalize; mention it as uncertainty only.
- If the top committer explicitly conflicts with the candidate identity: -0.08
- If is_fork=YES and fork_is_unmodified=YES: cap strength at 0.3
- If only a README mentions the feature but no implementation code is found: cap at 0.45
- If code appears copied/template-generated with no candidate-specific implementation changes: -0.1

IMPORTANT: You may only cite evidence that appears verbatim in the provided sections above.
Do not invent file names, function names, or quotes.
"""

            task_brief = task_description.strip() if task_description.strip() else "General task evaluation"

            prompt = f"""{persona}

TASK BEING EVALUATED:
\"\"\"{task_brief}\"\"\"

EVIDENCE (read all sections before scoring):
{evidence_text}

{scoring_rules}

YOUR RESPONSE MUST:
1. Score based on what the code ACTUALLY DOES, not what the README claims.
2. Set relevant_evidence to a direct quote or file reference from the CODE EVIDENCE section above.
   If no code evidence exists, write "No code evidence found."
3. Not give scores above 0.6 unless working implementation code is present in CODE EVIDENCE.
4. Apply all applicable penalties before arriving at your final strength score.

Respond with JSON only. No explanation outside the JSON.
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
                                "project_completion", "engineering_quality",
                                "communication", "innovation", "depth_novelty"
                            ],
                            "properties": {
                                "project_completion":  {"type": "number"},
                                "engineering_quality": {"type": "number"},
                                "communication":       {"type": "number"},
                                "innovation":          {"type": "number"},
                                "depth_novelty":       {"type": "number"},
                            },
                        },
                    },
                },
            }

            text = self._call_with_retry(prompt, schema)
            result = self._parse_json(text)

            # Clamp all values
            result["strength"] = max(0.0, min(1.0, float(result.get("strength", 0.0))))
            for key in ["project_completion", "engineering_quality", "communication", "innovation", "depth_novelty"]:
                dims = result.setdefault("dimensions", {})
                dims[key] = max(0.0, min(10.0, float(dims.get(key, 0.0))))

            # ── Post-hoc hard cap: fork with no original work ─────────────
            # Belt-and-suspenders in case the LLM ignored the penalty rule
            heuristic = next(
                (e for e in evidence if e.get("type") == "heuristic_context"), None
            )
            if heuristic:
                snippet = heuristic.get("snippet", "")
                if "Is Fork: YES" in snippet and "Fork Is Unmodified: YES" in snippet:
                    result["strength"] = min(result["strength"], 0.3)

            return result

        except Exception as e:
            logger.warning("[LLM] Interpretation error: %s", e)
            return {
                "strength": 0.0,
                "justification": "Error processing evidence via AI.",
                "relevant_evidence": "Error",
                "dimensions": {k: 0.0 for k in [
                    "project_completion", "engineering_quality",
                    "communication", "innovation", "depth_novelty"
                ]},
            }

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

Return JSON only:
{{
    "summary": "Brief summary of the submission...",
    "tech_stack": ["list", "of", "technologies"],
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
            return self._parse_json(self._call_with_retry(prompt, schema))
        except Exception as e:
            logger.warning("[LLM] Summary error: %s", e)
            return {"summary": "Error generating summary via OpenAI."}

    # ── FIXED: generate_tasks ───────────────────────────────────────────────
    def generate_tasks(self, description: str) -> List[Dict[str, Any]]:

        def get_fallback_tasks(desc: str):
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
                possible_tasks.extend([
                    {"name": "System Architecture Design", "priority": "High"},
                    {"name": "Write Comprehensive Unit Tests", "priority": "Medium"},
                    {"name": "Update Documentation", "priority": "Low"},
                ])

            seen, final = set(), []
            for task in possible_tasks:
                if task["name"] not in seen:
                    final.append(task)
                    seen.add(task["name"])
                if len(final) >= 5:
                    break
            return final

        if not self.api_key or not self.client:
            return get_fallback_tasks(description)

        try:
            prompt = f"""You are a Principal Engineer decomposing a specific project into evaluable technical tasks.

Project Description:
\"\"\"{description}\"\"\"

Rules:
- Each task must be directly derivable from the project description above. Do not add generic tasks unrelated to it.
- Task names must be specific enough that a code reviewer could look at a GitHub repo and verify completion.
- Bad example: "Implement Core Business Logic" (too vague)
- Good example: "Implement JWT authentication with refresh token rotation" (verifiable)
- Return 3-5 tasks with a realistic mix of High / Medium / Low priority.
- Do not mark all tasks High priority.

Return JSON only, no explanation.
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
            logger.warning("[LLM] Task generation error: %s", e)
            return get_fallback_tasks(description)


llm_service = OpenAILLMService()
