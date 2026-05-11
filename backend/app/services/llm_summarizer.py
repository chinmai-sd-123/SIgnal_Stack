"""
LLM Summarizer Service.

Provides safe, auditable LLM (OpenAI) usage for:
- Summarizing structured signals and evidence
- Schema validation of responses
- Fallback to deterministic summaries
- Full logging to LLMLog table
"""

import json
import time
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.snapshot import LLMLog
from app.services.llm import llm_service


# Expected response schema for validation
# CRITICAL: LLM outputs labels only, NOT numbers or weights.
LABEL_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["label", "explanation"],
    "properties": {
        "label": {"type": "string", "enum": ["High", "Medium", "Low", "None"]},
        "explanation": {"type": "array", "items": {"type": "string"}},
    }
}

# Legacy schema for backward compatibility
SUMMARY_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["summary", "key_strengths", "concerns"],
    "properties": {
        "summary": {"type": "string"},
        "key_strengths": {"type": "array", "items": {"type": "string"}},
        "concerns": {"type": "array", "items": {"type": "string"}},
        "confidence_reason": {"type": "string"},
    }
}


def validate_response_schema(response: Dict[str, Any]) -> bool:
    """
    Validate that the response matches expected schema.
    
    Returns True if valid, False otherwise.
    """
    try:
        # Check required fields
        if not isinstance(response, dict):
            return False
        
        required_fields = ["summary", "key_strengths", "concerns"]
        for field in required_fields:
            if field not in response:
                return False
        
        # Type checks
        if not isinstance(response.get("summary"), str):
            return False
        if not isinstance(response.get("key_strengths"), list):
            return False
        if not isinstance(response.get("concerns"), list):
            return False
        
        return True
    except Exception:
        return False


def validate_label_schema(response: Dict[str, Any]) -> bool:
    """
    Validate that the response matches LABEL_RESPONSE_SCHEMA.
    LLM must return label (High/Medium/Low/None) and explanation array.
    NO numbers, percentages, or scores allowed.
    
    Returns True if valid, False otherwise.
    """
    try:
        if not isinstance(response, dict):
            return False
        
        # Check required fields
        if "label" not in response or "explanation" not in response:
            return False
        
        # Validate label is one of allowed values
        valid_labels = ["High", "Medium", "Low", "None"]
        if response["label"] not in valid_labels:
            return False
        
        # Validate explanation is array of strings
        if not isinstance(response["explanation"], list):
            return False
        
        for item in response["explanation"]:
            if not isinstance(item, str):
                return False
        
        return True
    except Exception:
        return False


def generate_deterministic_summary(
    signals: Dict[str, Dict[str, Any]],
    scoring_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate a deterministic summary when LLM fails or is invalid.
    
    This ensures we always have a usable summary.
    """
    strengths = []
    concerns = []
    
    for signal_name, signal_data in signals.items():
        if not isinstance(signal_data, dict):
            continue
            
        value = signal_data.get("value", 0)
        
        if value >= 0.7:
            strengths.append(f"{signal_name.replace('_', ' ').title()}: Strong ({value:.0%})")
        elif value <= 0.3 and signal_name in ["authorship_fraction", "tests_present", "ci_present"]:
            concerns.append(f"{signal_name.replace('_', ' ').title()}: Needs improvement ({value:.0%})")
    
    # Check risk flags
    risk_flags = scoring_result.get("risk_flags", [])
    if "low_authorship" in risk_flags:
        concerns.append("Low authorship fraction - candidate may not be the primary contributor")
    
    score = scoring_result.get("capped_score", 0)
    
    summary = f"Evaluation complete with a score of {score:.0%}. "
    if strengths:
        summary += f"Key strengths include: {', '.join(strengths[:3])}. "
    if concerns:
        summary += f"Areas of concern: {', '.join(concerns[:3])}."
    
    return {
        "summary": summary,
        "key_strengths": strengths[:5],
        "concerns": concerns[:5],
        "confidence_reason": "Deterministic summary - LLM unavailable or validation failed"
    }


def build_summarization_prompt(
    signals: Dict[str, Dict[str, Any]],
    scoring_result: Dict[str, Any],
    task_context: str = ""
) -> str:
    """
    Build a structured prompt for LLM summarization.
    """
    prompt = """You are an AI assistant helping recruiters understand candidate evaluations.

Based on the following structured signals and scoring data, provide a JSON summary.

SIGNALS:
"""
    
    for signal_name, signal_data in signals.items():
        if isinstance(signal_data, dict):
            value = signal_data.get("value", 0)
            evidence = signal_data.get("evidence", {})
            snippet = evidence.get("snippet", "No evidence") if isinstance(evidence, dict) else "No evidence"
            prompt += f"\n- {signal_name}: {value:.2f}"
            prompt += f"\n  Evidence: {snippet[:200]}"
    
    prompt += f"""

SCORING:
- Raw Score: {scoring_result.get('raw_score', 0):.2f}
- Normalized Score: {scoring_result.get('normalized_score', 0):.2f}
- Final Score: {scoring_result.get('capped_score', 0):.2f}
- Confidence: {scoring_result.get('confidence', 0):.2f}
- Risk Flags: {scoring_result.get('risk_flags', [])}

{f'TASK CONTEXT: {task_context}' if task_context else ''}

Respond with ONLY a JSON object in this format:
{{
    "summary": "A 2-3 sentence summary of the candidate's evaluation",
    "key_strengths": ["strength1", "strength2", "strength3"],
    "concerns": ["concern1", "concern2"],
    "confidence_reason": "Why we are confident/uncertain about this evaluation"
}}

IMPORTANT: Respond with ONLY the JSON, no additional text."""
    
    return prompt


def summarize_with_llm(
    db: Session,
    signals: Dict[str, Dict[str, Any]],
    scoring_result: Dict[str, Any],
    evaluation_id: int = None,
    task_context: str = ""
) -> Dict[str, Any]:
    """
    Summarize signals using LLM with full audit logging.
    
    Args:
        db: Database session for logging
        signals: Dictionary of signals
        scoring_result: Scoring result dictionary
        evaluation_id: Optional evaluation ID for linking
        task_context: Optional task context
    
    Returns:
        Summary dictionary (from LLM or deterministic fallback)
    """
    prompt = build_summarization_prompt(signals, scoring_result, task_context)
    
    start_time = time.time()
    raw_response = ""
    validated_json = None
    is_valid = False
    
    try:
        # Call LLM
        raw_response = llm_service.generate(prompt)
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Try to parse JSON from response
        try:
            # Handle potential markdown code blocks
            response_text = raw_response.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            
            validated_json = json.loads(response_text)
            is_valid = validate_response_schema(validated_json)
        except json.JSONDecodeError:
            is_valid = False
        
    except Exception as e:
        raw_response = f"Error: {str(e)}"
        latency_ms = int((time.time() - start_time) * 1000)
    
    # Log to database
    log_entry = LLMLog(
        evaluation_id=evaluation_id,
        prompt=prompt,
        raw_response=raw_response,
        validated_json=validated_json if is_valid else None,
        is_valid=1 if is_valid else 0,
        latency_ms=latency_ms
    )
    db.add(log_entry)
    db.commit()
    
    # Return validated response or deterministic fallback
    if is_valid and validated_json:
        return validated_json
    else:
        return generate_deterministic_summary(signals, scoring_result)


def get_llm_logs_for_evaluation(db: Session, evaluation_id: int) -> list:
    """
    Retrieve all LLM logs for a specific evaluation.
    """
    logs = db.query(LLMLog).filter(LLMLog.evaluation_id == evaluation_id).all()
    return [
        {
            "id": log.id,
            "prompt": log.prompt[:500] + "..." if len(log.prompt) > 500 else log.prompt,
            "raw_response": log.raw_response[:500] + "..." if len(log.raw_response) > 500 else log.raw_response,
            "is_valid": bool(log.is_valid),
            "latency_ms": log.latency_ms,
            "created_at": log.created_at.isoformat() if log.created_at else None
        }
        for log in logs
    ]
