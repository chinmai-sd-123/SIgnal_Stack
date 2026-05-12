"""
Identity Verifier Module

Provides robust mapping of candidate identity to commit authors.
Handles:
1. GitHub usernames
2. Email aliases (work, personal)
3. Noreply @github.com addresses
4. Fuzzy name matching (accents, case, tokens)
"""

import re
import unicodedata
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass


@dataclass
class CandidateIdentity:
    """Resolved identity information for a candidate."""
    candidate_emails: Set[str]
    usernames: Set[str]
    name_aliases: Set[str]
    matched_emails: Set[str]  # Emails from commit history that match


def _clean_email(email: str) -> str:
    return (email or "").strip().lower()


def _clean_username(username: str) -> str:
    return (username or "").strip().strip("@").lower()


def normalize_name(name: str) -> str:
    """
    Normalize a name for comparison:
    - Lowercase
    - Remove accents
    - Strip extra whitespace
    """
    # Remove accents
    normalized = unicodedata.normalize('NFKD', name)
    normalized = ''.join(c for c in normalized if not unicodedata.combining(c))
    # Lowercase and clean whitespace
    return ' '.join(normalized.lower().split())


def tokenize_name(name: str) -> Set[str]:
    """Split a name into tokens for fuzzy matching."""
    normalized = normalize_name(name)
    tokens = set(re.split(r'[\s._-]+', normalized))
    return {t for t in tokens if len(t) >= 2}


def extract_github_username_from_noreply(email: str) -> Optional[str]:
    """
    Extract username from GitHub noreply email.
    Formats:
      - username@users.noreply.github.com
      - 12345678+username@users.noreply.github.com
    """
    if "noreply.github.com" not in email:
        return None
    
    # Pattern: optional_numbers+username@users.noreply.github.com
    match = re.match(r'^(?:\d+\+)?([^@]+)@users\.noreply\.github\.com$', email, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    
    # Older format: username@users.noreply.github.com
    match = re.match(r'^([^@]+)@users\.noreply\.github\.com$', email, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    
    return None


def fuzzy_match_name(name1: str, name2: str, threshold: float = 0.5) -> bool:
    """
    Check if two names loosely match using token intersection.
    Returns True if token overlap exceeds threshold.
    """
    tokens1 = tokenize_name(name1)
    tokens2 = tokenize_name(name2)
    
    if not tokens1 or not tokens2:
        return False
    
    intersection = tokens1 & tokens2
    min_tokens = min(len(tokens1), len(tokens2))
    
    return len(intersection) / min_tokens >= threshold


# PATCH 1: resolve_candidate_identities — accept author_map directly, add github_login matching

def resolve_candidate_identities(
    candidate: Dict[str, Any],
    author_map: Dict[str, Any],          # ← flat dict, NOT wrapped in snapshot_metadata
) -> CandidateIdentity:
    """
    Resolve candidate identities from commit author data.

    Args:
        candidate: Dict with any of:
            - name, email, emails (list), github_username
        author_map: flat {email: {commits, lines_added, name, github_login}}
    """
    candidate_emails: Set[str] = set()
    usernames: Set[str] = set()
    name_aliases: Set[str] = set()
    matched_emails: Set[str] = set()

    candidate_name     = candidate.get("name", "")
    candidate_email    = candidate.get("email", "") or candidate.get("candidate_email", "")
    candidate_username = candidate.get("github_username", "")
    candidate_known_emails = set(candidate.get("emails", []))

    if candidate_email:
        candidate_emails.add(candidate_email.lower())
    candidate_emails.update(e.lower() for e in candidate_known_emails)

    if candidate_username:
        usernames.add(candidate_username.lower())
        candidate_emails.add(f"{candidate_username.lower()}@users.noreply.github.com")

    if candidate_name:
        name_aliases.add(normalize_name(candidate_name))

    for email, author_data in author_map.items():
        email_lower = email.lower()
        author_name  = author_data.get("name", "")
        github_login = author_data.get("github_login", "").lower()

        # ── 1. Direct email match ─────────────────────────────────────────
        if email_lower in candidate_emails:
            matched_emails.add(email_lower)
            continue

        # ── 2. GitHub login match (most reliable for web-UI commits) ──────
        if github_login and github_login in usernames:
            matched_emails.add(email_lower)
            candidate_emails.add(email_lower)
            continue

        # ── 3. Noreply email → username ───────────────────────────────────
        noreply_username = extract_github_username_from_noreply(email_lower)
        if noreply_username and noreply_username in usernames:
            matched_emails.add(email_lower)
            candidate_emails.add(email_lower)
            continue

        # ── 4. Email prefix matches username ──────────────────────────────
        email_prefix = re.sub(r'\d+$', '', email_lower.split('@')[0])
        if email_prefix and email_prefix in usernames:
            matched_emails.add(email_lower)
            candidate_emails.add(email_lower)
            continue

        # ── 5. Fuzzy name match (last resort) ─────────────────────────────
        if candidate_name and author_name:
            if fuzzy_match_name(candidate_name, author_name):
                matched_emails.add(email_lower)
                candidate_emails.add(email_lower)
                name_aliases.add(normalize_name(author_name))

    return CandidateIdentity(
        candidate_emails=candidate_emails,
        usernames=usernames,
        name_aliases=name_aliases,
        matched_emails=matched_emails,
    )


# PATCH 2: calculate_authorship_from_identity — use commits-only when lines unavailable

def calculate_authorship_from_identity(
    identity: CandidateIdentity,
    author_map: Dict[str, Any],
) -> Dict[str, Any]:
    total_commits = 0
    total_lines   = 0
    candidate_commits = 0
    candidate_lines   = 0
    matched_authors   = []

    for email, data in author_map.items():
        commits = data.get("commits", 0)
        lines   = data.get("lines_added", 0)
        total_commits += commits
        total_lines   += lines

        if email.lower() in identity.candidate_emails or email.lower() in identity.matched_emails:
            candidate_commits += commits
            candidate_lines   += lines
            matched_authors.append(email)

    authorship_by_commits = candidate_commits / total_commits if total_commits > 0 else 0.0

    # Only blend line-based authorship when lines data is actually present.
    # The GitHub Commits list API doesn't return per-commit line stats,
    # so lines_added is often 0 — averaging with 0 would silently halve every score.
    if total_lines > 0:
        authorship_by_lines   = candidate_lines / total_lines
        authorship_fraction   = (authorship_by_commits + authorship_by_lines) / 2
    else:
        authorship_fraction   = authorship_by_commits

    return {
        "authorship_fraction": round(authorship_fraction, 4),
        "candidate_commits":   candidate_commits,
        "total_commits":       total_commits,
        "candidate_lines":     candidate_lines,
        "total_lines":         total_lines,
        "matched_emails":      matched_authors,
    }


def classify_identity_match(
    candidate: Dict[str, Any],
    identity: CandidateIdentity,
    author_map: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Classify how strong the authorship identity match is.

    A submitted GitHub handle is useful evidence, but by itself it is still a
    candidate claim. To avoid falsely confirming ownership when someone submits
    another user's repo/handle, we only call authorship verified when commit
    metadata also matches candidate email or candidate name.
    """
    candidate_email = _clean_email(candidate.get("email", "") or candidate.get("candidate_email", ""))
    candidate_name = candidate.get("name", "") or candidate.get("candidate_name", "")
    candidate_username = _clean_username(candidate.get("github_username", ""))

    matched_emails = {_clean_email(email) for email in identity.matched_emails}
    exact_email_match = bool(candidate_email and candidate_email in matched_emails)
    name_match = False
    github_handle_match = False

    for email in matched_emails:
        author_data = author_map.get(email) or {}
        author_name = author_data.get("name", "")
        github_login = _clean_username(author_data.get("github_login", ""))
        noreply_username = extract_github_username_from_noreply(email)
        email_prefix = re.sub(r"\d+$", "", email.split("@")[0])

        if candidate_name and author_name and fuzzy_match_name(candidate_name, author_name, threshold=0.67):
            name_match = True

        if candidate_username and (
            github_login == candidate_username
            or noreply_username == candidate_username
            or email_prefix == candidate_username
        ):
            github_handle_match = True

    if exact_email_match or name_match:
        basis = "verified"
    elif github_handle_match:
        basis = "claimed_github_handle_only"
    elif matched_emails:
        basis = "weak_metadata_match"
    else:
        basis = "unverified"

    return {
        "basis": basis,
        "exact_email_match": exact_email_match,
        "name_match": name_match,
        "github_handle_match": github_handle_match,
        "requires_manual_review": basis != "verified",
    }
