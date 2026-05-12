import json
import logging
import re
import time
from typing import Any, Dict, List

import app.schemas as schemas
from app.config.config import config
from app.monitoring import track_llm_cache_hit, track_llm_usage
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

    def _usage_value(self, usage: Any, *names: str) -> int:
        if not usage:
            return 0
        for name in names:
            if isinstance(usage, dict) and usage.get(name) is not None:
                return int(usage.get(name) or 0)
            value = getattr(usage, name, None)
            if value is not None:
                return int(value or 0)
        return 0

    def _extract_usage(self, response: Any) -> Dict[str, int]:
        usage = getattr(response, "usage", None)
        if usage is None and isinstance(response, dict):
            usage = response.get("usage")
        input_tokens = self._usage_value(usage, "input_tokens", "prompt_tokens")
        output_tokens = self._usage_value(usage, "output_tokens", "completion_tokens")
        total_tokens = self._usage_value(usage, "total_tokens")
        if total_tokens and not (input_tokens or output_tokens):
            input_tokens = total_tokens
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens or input_tokens + output_tokens,
        }

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        input_cost = (input_tokens / 1_000_000) * config.LLM_INPUT_COST_PER_1M
        output_cost = (output_tokens / 1_000_000) * config.LLM_OUTPUT_COST_PER_1M
        return round(input_cost + output_cost, 8)

    def _call_with_retry(
        self,
        prompt: str,
        schema: Dict[str, Any] = None,
        tracking_context: Dict[str, Any] = None,
    ) -> str:
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
                track_llm_cache_hit(model=self.model, context=tracking_context)
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
            start = time.time()
            try:
                response = self.client.responses.create(**payload)
                latency = time.time() - start
                text = self._extract_text(response)
                usage = self._extract_usage(response)
                track_llm_usage(
                    latency_seconds=latency,
                    success=True,
                    model=self.model,
                    input_tokens=usage["input_tokens"],
                    output_tokens=usage["output_tokens"],
                    estimated_cost=self._estimate_cost(
                        usage["input_tokens"],
                        usage["output_tokens"],
                    ),
                    cached=False,
                    context=tracking_context,
                )
                if cache_key:
                    cache.set_llm_response(cache_key, text, ttl=config.LLM_RESPONSE_CACHE_TTL_SECONDS)
                return text
            except Exception as e:
                latency = time.time() - start
                message = str(e).lower()
                if ("429" in message or "rate limit" in message or "temporarily unavailable" in message) and i < retries - 1:
                    track_llm_usage(
                        latency_seconds=latency,
                        success=False,
                        model=self.model,
                        cached=False,
                        context=tracking_context,
                    )
                    logger.warning("OpenAI rate limit. Retrying in %ss...", delay)
                    time.sleep(delay)
                    delay *= 2
                    continue
                track_llm_usage(
                    latency_seconds=latency,
                    success=False,
                    model=self.model,
                    cached=False,
                    context=tracking_context,
                )
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
    def _build_evidence_sections(
        self,
        evidence: List[Dict],
        code_char_limit: int = 8000,
        repo_char_limit: int = 3000,
    ) -> str:
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
                + code_block[:code_char_limit]
                + ("\n[... truncated ...]" if len(code_block) > code_char_limit else "")
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
                + repo_block[:repo_char_limit]
                + ("\n[... truncated ...]" if len(repo_block) > repo_char_limit else "")
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

    def _source_code_evidence(self, evidence: List[Dict]) -> List[Dict]:
        """Return source code evidence only, excluding model-generated findings."""
        return [
            item for item in evidence
            if item.get("type") == "code_snippet"
            and not str(item.get("ref", "")).startswith("AI_FINDING:")
        ]

    def _fallback_relevant_evidence(self, evidence: List[Dict]) -> str:
        """Build grounded key evidence from the first source snippet."""
        source_items = self._source_code_evidence(evidence)
        if not source_items:
            return "No code evidence found."

        item = source_items[0]
        ref = item.get("ref", "CODE")
        snippet = item.get("snippet", "")
        lines = snippet.splitlines()
        preview = "\n".join(lines[:24]).strip()
        if len(preview) > 1600:
            preview = preview[:1600].rstrip() + "\n[... truncated ...]"
        return f"{ref}\n{preview}"

    def _is_grounded_relevant_evidence(self, relevant_evidence: str, evidence: List[Dict]) -> bool:
        """
        Check that model-selected key evidence is actually traceable to supplied
        evidence. This prevents invented file/function claims from becoming the
        trusted "Key Evidence" card.
        """
        text = (relevant_evidence or "").strip()
        if not text or text.lower() in {"none", "error", "no code evidence found."}:
            return True

        normalized_text = re.sub(r"\s+", " ", text).lower()
        for item in evidence:
            if str(item.get("ref", "")).startswith("AI_FINDING:"):
                continue
            snippet = str(item.get("snippet", ""))
            normalized_snippet = re.sub(r"\s+", " ", snippet).lower()
            if len(normalized_text) >= 40 and normalized_text in normalized_snippet:
                return True

            # Allow shorter direct line quotes when at least one meaningful
            # non-comment line is copied exactly.
            for line in snippet.splitlines():
                line = line.strip()
                if len(line) >= 24 and line.lower() in normalized_text:
                    return True

        return False

    # ── FIXED: interpret_signals ────────────────────────────────────────────
    def interpret_signals(
        self,
        task_description: str,
        evidence: List[Dict],
        payload: Dict[str, Any] = None,
        tracking_context: Dict[str, Any] = None,
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
                    if not stats.get("error"):
                        evidence = list(evidence) + [{
                            "type": "leetcode_stats",
                            "ref": "LEETCODE",
                            "snippet": (
                                f"LeetCode Profile: {stats.get('username') or username}\n"
                                f"Total Solved: {stats.get('total_solved')} "
                                f"(Easy: {stats.get('easy_solved')}, "
                                f"Med: {stats.get('medium_solved')}, "
                                f"Hard: {stats.get('hard_solved')})\n"
                                f"Acceptance Rate: {stats.get('acceptance_rate')}%\n"
                                f"Ranking: {stats.get('ranking')}"
                            )
                        }]

            has_code = bool(self._source_code_evidence(evidence))
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
   It must include the source ref, for example "FILE:app/main.py".
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

            text = (
                self._call_with_retry(prompt, schema, tracking_context=tracking_context)
                if tracking_context
                else self._call_with_retry(prompt, schema)
            )
            result = self._parse_json(text)

            # Clamp all values
            result["strength"] = max(0.0, min(1.0, float(result.get("strength", 0.0))))
            if not has_code and not has_artifact:
                result["strength"] = min(result["strength"], 0.2)
            elif not has_code and has_artifact:
                result["strength"] = min(result["strength"], 0.6)

            relevant = str(result.get("relevant_evidence", "") or "").strip()
            if not self._is_grounded_relevant_evidence(relevant, evidence):
                relevant = self._fallback_relevant_evidence(evidence)
            if relevant.lower() in {"", "none", "error"} and has_code:
                relevant = self._fallback_relevant_evidence(evidence)
            result["relevant_evidence"] = relevant

            dimension_keys = ["project_completion", "engineering_quality", "communication", "innovation", "depth_novelty"]
            dims = result.setdefault("dimensions", {})
            raw_dims = []
            for key in dimension_keys:
                try:
                    raw_dims.append(float(dims.get(key, 0.0)))
                except (TypeError, ValueError):
                    raw_dims.append(0.0)
            dim_scale = 10.0 if raw_dims and max(raw_dims) <= 1.0 and max(raw_dims) > 0 else 1.0
            for key, value in zip(dimension_keys, raw_dims):
                dims[key] = max(0.0, min(10.0, value * dim_scale))

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

    def interpret_outcome_signals(
        self,
        outcome_description: str,
        task_evidence: List[Dict[str, Any]],
        payload: Dict[str, Any] = None,
        tracking_context: Dict[str, Any] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Interpret every signal for one candidate/outcome in a single LLM call.

        This is used by high-volume job evaluation. It preserves per-signal
        scoring and evidence output while reducing calls from
        candidates x outcomes x signals to candidates x outcomes.
        """
        dimension_keys = [
            "project_completion", "engineering_quality",
            "communication", "innovation", "depth_novelty",
        ]

        def empty_result(task_id: str, reason: str = "No interpretation available.") -> Dict[str, Any]:
            return {
                "strength": 0.0,
                "justification": reason,
                "relevant_evidence": "None",
                "dimensions": {key: 0.0 for key in dimension_keys},
            }

        task_evidence = task_evidence or []
        if not task_evidence:
            return {}

        if not self.api_key or not self.client:
            return {
                str(item.get("task_id")): empty_result(str(item.get("task_id")), "API Key missing.")
                for item in task_evidence
            }

        try:
            leetcode_evidence = None
            if payload and payload.get("leetcode_username"):
                username = payload["leetcode_username"]
                stats = self.leetcode_service.fetch_stats(username)
                if not stats.get("error"):
                    leetcode_evidence = {
                        "type": "leetcode_stats",
                        "ref": "LEETCODE",
                        "snippet": (
                            f"LeetCode Profile: {stats.get('username') or username}\n"
                            f"Total Solved: {stats.get('total_solved')} "
                            f"(Easy: {stats.get('easy_solved')}, "
                            f"Med: {stats.get('medium_solved')}, "
                            f"Hard: {stats.get('hard_solved')})\n"
                            f"Acceptance Rate: {stats.get('acceptance_rate')}%\n"
                            f"Ranking: {stats.get('ranking')}"
                        ),
                    }

            task_sections = []
            effective_evidence_by_task: Dict[str, List[Dict[str, Any]]] = {}
            code_presence: Dict[str, bool] = {}
            artifact_presence: Dict[str, bool] = {}

            for index, item in enumerate(task_evidence, start=1):
                task_id = str(item.get("task_id") or f"task_{index}")
                evidence = list(item.get("evidence") or [])
                if leetcode_evidence and not any(e.get("type") == "leetcode_stats" for e in evidence):
                    evidence.append(leetcode_evidence)

                effective_evidence_by_task[task_id] = evidence
                code_presence[task_id] = bool(self._source_code_evidence(evidence))
                artifact_presence[task_id] = any(e.get("type") == "work_artifact" for e in evidence)

                evidence_text = self._build_evidence_sections(
                    evidence,
                    code_char_limit=3500,
                    repo_char_limit=1200,
                )
                task_sections.append(
                    f"--- TASK {index} ---\n"
                    f"TASK_ID: {task_id}\n"
                    f"TASK_TITLE: {item.get('task_name') or 'Untitled signal'}\n"
                    f"TASK_CONTEXT:\n{item.get('task_description') or ''}\n\n"
                    f"EVIDENCE:\n{evidence_text or 'No evidence provided.'}"
                )

            prompt = f"""You are a senior software engineer evaluating one candidate repository against multiple signals for a single hiring outcome.

OUTCOME BEING EVALUATED:
\"\"\"{outcome_description.strip() or "General outcome evaluation"}\"\"\"

For each TASK_ID below, score only that task using only its evidence section.
Do not borrow implementation evidence from one task to justify another task.

{chr(10).join(task_sections)}

SCORING RULES:
- 0.0-0.2: No relevant code found, unrelated code, or copied/template boilerplate.
- 0.2-0.4: Related files exist but implementation is incomplete or incorrect.
- 0.4-0.6: Partial implementation; core logic is visible but important pieces are missing.
- 0.6-0.8: Complete implementation with minor gaps such as limited tests or error handling.
- 0.8-1.0: Full working implementation with strong structure, validation, and verification.

EARLY APPLICATION GUIDANCE:
- Missing tests, CI, Docker, or deployment should not heavily punish personal projects unless the task explicitly asks for them.
- Authorship uncertainty is a trust note, not a capability penalty unless there is an explicit conflict.
- If only README text mentions a feature and no implementation code is present, cap that task at 0.45.
- If no code evidence exists for a code task, cap that task at 0.2.
- If is_fork=YES and fork_is_unmodified=YES, cap that task at 0.3.

For every task, relevant_evidence must be a direct quote or source ref from that task's evidence.
Return JSON only.
"""

            schema = {
                "name": "outcome_signal_interpretation",
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
                                "required": [
                                    "task_id", "strength", "justification",
                                    "relevant_evidence", "dimensions",
                                ],
                                "properties": {
                                    "task_id": {"type": "string"},
                                    "strength": {"type": "number"},
                                    "justification": {"type": "string"},
                                    "relevant_evidence": {"type": "string"},
                                    "dimensions": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "required": dimension_keys,
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
                        },
                    },
                },
            }

            text = self._call_with_retry(prompt, schema, tracking_context=tracking_context)
            parsed = self._parse_json(text)
            raw_results = parsed.get("tasks", []) if isinstance(parsed, dict) else []
            results: Dict[str, Dict[str, Any]] = {}

            for item in raw_results:
                task_id = str(item.get("task_id") or "")
                if not task_id or task_id not in effective_evidence_by_task:
                    continue

                evidence = effective_evidence_by_task[task_id]
                result = {
                    "strength": max(0.0, min(1.0, float(item.get("strength", 0.0) or 0.0))),
                    "justification": item.get("justification") or "No justification provided.",
                    "relevant_evidence": str(item.get("relevant_evidence", "") or "").strip(),
                    "dimensions": item.get("dimensions") or {},
                }

                if not code_presence[task_id] and not artifact_presence[task_id]:
                    result["strength"] = min(result["strength"], 0.2)
                elif not code_presence[task_id] and artifact_presence[task_id]:
                    result["strength"] = min(result["strength"], 0.6)

                relevant = result["relevant_evidence"]
                if not self._is_grounded_relevant_evidence(relevant, evidence):
                    relevant = self._fallback_relevant_evidence(evidence)
                if relevant.lower() in {"", "none", "error"} and code_presence[task_id]:
                    relevant = self._fallback_relevant_evidence(evidence)
                result["relevant_evidence"] = relevant

                dims = result.setdefault("dimensions", {})
                raw_dims = []
                for key in dimension_keys:
                    try:
                        raw_dims.append(float(dims.get(key, 0.0)))
                    except (TypeError, ValueError):
                        raw_dims.append(0.0)
                dim_scale = 10.0 if raw_dims and max(raw_dims) <= 1.0 and max(raw_dims) > 0 else 1.0
                for key, value in zip(dimension_keys, raw_dims):
                    dims[key] = max(0.0, min(10.0, value * dim_scale))

                heuristic = next(
                    (e for e in evidence if e.get("type") == "heuristic_context"), None
                )
                if heuristic:
                    snippet = heuristic.get("snippet", "")
                    if "Is Fork: YES" in snippet and "Fork Is Unmodified: YES" in snippet:
                        result["strength"] = min(result["strength"], 0.3)

                results[task_id] = result

            for item in task_evidence:
                task_id = str(item.get("task_id") or "")
                if task_id and task_id not in results:
                    results[task_id] = empty_result(task_id)

            return results

        except Exception as e:
            logger.warning("[LLM] Batched outcome interpretation error: %s", e)
            return {
                str(item.get("task_id")): empty_result(str(item.get("task_id")), "Error processing evidence via AI.")
                for item in task_evidence
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
            return self._parse_json(self._call_with_retry(
                prompt,
                schema,
                tracking_context={
                    "candidate_id": proof.candidate_id,
                    "outcome_id": proof.job_id,
                    "operation": "proof_summary",
                },
            ))
        except Exception as e:
            logger.warning("[LLM] Summary error: %s", e)
            return {"summary": "Error generating summary via OpenAI."}

    # ── FIXED: generate_tasks ───────────────────────────────────────────────
    def generate_tasks(self, description: str) -> List[Dict[str, Any]]:

        def normalize_task_name(name: str) -> str:
            text = " ".join((name or "").replace("\n", " ").split())
            text = text.strip(" -:;.")
            if len(text) > 140:
                text = text[:137].rsplit(" ", 1)[0].strip(" -:;.") + "..."
            return text

        def normalize_priority(priority: str, index: int) -> str:
            value = (priority or "").strip().title()
            if value not in {"High", "Medium", "Low"}:
                return "High" if index < 2 else "Medium"
            return value

        def clean_tasks(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            seen, final = set(), []
            for task in tasks:
                name = normalize_task_name(task.get("name", ""))
                if len(name) < 12:
                    continue
                key = name.lower()
                if key in seen:
                    continue
                seen.add(key)
                final.append({
                    "name": name,
                    "priority": normalize_priority(task.get("priority", "Medium"), len(final)),
                })
                if len(final) >= 5:
                    break

            if final and all(task["priority"] == "High" for task in final):
                for task in final[2:]:
                    task["priority"] = "Medium"

            return final

        def get_fallback_tasks(desc: str):
            desc_lower = desc.lower()
            possible_tasks = []

            if any(k in desc_lower for k in ["api", "backend", "fastapi", "flask", "django", "node", "express"]):
                possible_tasks.append({"name": "Expose working API endpoints for the core user workflow", "priority": "High"})
                possible_tasks.append({"name": "Implement request validation and clear error responses", "priority": "Medium"})
            if any(k in desc_lower for k in ["data", "sql", "schema", "db", "postgres", "mongo"]):
                possible_tasks.append({"name": "Persist domain data with a clear schema or model layer", "priority": "High"})
            if any(k in desc_lower for k in ["ui", "frontend", "react", "vue", "angular", "css", "web"]):
                possible_tasks.append({"name": "Build the primary user interface for the outcome workflow", "priority": "High"})
                possible_tasks.append({"name": "Handle loading, empty, success, and error states in the UI", "priority": "Medium"})
            if any(k in desc_lower for k in ["auth", "login", "security", "jwt", "oauth"]):
                possible_tasks.append({"name": "Implement authentication and authorization checks around protected actions", "priority": "High"})
            if any(k in desc_lower for k in ["ml", "ai", "scikit", "nlp", "classification", "model", "train"]):
                possible_tasks.append({"name": "Prepare data and features used by the model or AI workflow", "priority": "High"})
                possible_tasks.append({"name": "Implement model inference or LLM call flow with usable outputs", "priority": "High"})
                possible_tasks.append({"name": "Report evaluation metrics or qualitative validation for the AI output", "priority": "Medium"})
            if any(k in desc_lower for k in ["ci", "cd", "docker", "cloud", "deploy", "aws", "render", "vercel"]):
                possible_tasks.append({"name": "Provide runnable setup instructions or deployment configuration", "priority": "Low"})
            if len(possible_tasks) < 3:
                possible_tasks.extend([
                    {"name": "Implement the main end-to-end workflow described by the outcome", "priority": "High"},
                    {"name": "Organize code into readable modules with clear responsibilities", "priority": "Medium"},
                    {"name": "Document how to run and verify the project locally", "priority": "Low"},
                ])

            return clean_tasks(possible_tasks)

        if not self.api_key or not self.client:
            return get_fallback_tasks(description)

        try:
            prompt = f"""You are a senior engineering evaluator creating evaluation signals for early-career candidate repositories.

Context:
\"\"\"{description}\"\"\"

Rules:
- Create 4-5 evaluation signals, not a full implementation spec.
- Each signal must be directly derivable from the context. Do not add unrelated technologies.
- Each signal must be verifiable from a GitHub repo, code files, notebook, README, or artifact.
- Keep each signal short: 8-18 words, maximum 140 characters.
- Prefer evidence of working product logic over CI/CD, Docker, perfect tests, or deployment.
- Include tests, CI, Docker, or deployment only when the context explicitly requires them.
- Good signal: "Sends submitted code/context to an LLM review service"
- Bad signal: "Implement a complete production-grade scalable cloud platform with tests and CI"
- Return a realistic priority mix: 1-2 High, 2-3 Medium, optional 1 Low.
- Do not mark every signal High.

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
            tasks = clean_tasks(data.get("tasks", []))
            return tasks if len(tasks) >= 3 else get_fallback_tasks(description)
        except Exception as e:
            logger.warning("[LLM] Task generation error: %s", e)
            return get_fallback_tasks(description)


llm_service = OpenAILLMService()
