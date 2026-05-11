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


def resolve_candidate_identities(
    candidate: Dict[str, Any],
    snapshot_metadata: Dict[str, Any]
) -> CandidateIdentity:
    """
    Resolve candidate identities from snapshot author data.
    
    Args:
        candidate: Dict containing:
            - github_username (optional)
            - email (optional)
            - name (optional)
            - emails (optional, list of known emails)
        snapshot_metadata: Dict containing:
            - author_map: {email: {commits, lines_added, name}}
            - top_committers: [names...]
    
    Returns:
        CandidateIdentity with resolved emails, usernames, and aliases
    """
    candidate_emails: Set[str] = set()
    usernames: Set[str] = set()
    name_aliases: Set[str] = set()
    matched_emails: Set[str] = set()
    
    # Extract candidate info
    candidate_name = candidate.get("name", "")
    candidate_email = candidate.get("email", "")
    candidate_username = candidate.get("github_username", "")
    candidate_known_emails = set(candidate.get("emails", []))
    
    # Add known emails
    if candidate_email:
        candidate_emails.add(candidate_email.lower())
    candidate_emails.update(e.lower() for e in candidate_known_emails)
    
    # Add username variants
    if candidate_username:
        usernames.add(candidate_username.lower())
        # Common noreply pattern
        candidate_emails.add(f"{candidate_username.lower()}@users.noreply.github.com")
    
    # Add name aliases
    if candidate_name:
        name_aliases.add(normalize_name(candidate_name))
    
    # Extract from snapshot author_map
    author_map = snapshot_metadata.get("author_map", {})
    
    for email, author_data in author_map.items():
        email_lower = email.lower()
        author_name = author_data.get("name", "")
        
        # Direct email match
        if email_lower in candidate_emails:
            matched_emails.add(email_lower)
            continue
        
        # Check noreply email for username match
        noreply_username = extract_github_username_from_noreply(email_lower)
        if noreply_username and noreply_username in usernames:
            matched_emails.add(email_lower)
            candidate_emails.add(email_lower)
            continue
        
        # Fuzzy name match
        if candidate_name and author_name:
            if fuzzy_match_name(candidate_name, author_name):
                matched_emails.add(email_lower)
                candidate_emails.add(email_lower)
                name_aliases.add(normalize_name(author_name))
                continue
        
        # Check if email prefix matches username
        email_prefix = email_lower.split('@')[0]
        # Remove common suffixes like numbers
        clean_prefix = re.sub(r'\d+$', '', email_prefix)
        if clean_prefix and clean_prefix in usernames:
            matched_emails.add(email_lower)
            candidate_emails.add(email_lower)
    
    return CandidateIdentity(
        candidate_emails=candidate_emails,
        usernames=usernames,
        name_aliases=name_aliases,
        matched_emails=matched_emails
    )


def calculate_authorship_from_identity(
    identity: CandidateIdentity,
    author_map: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate authorship statistics based on resolved identity.
    
    Returns:
        Dict with:
            - authorship_fraction: float 0..1
            - candidate_commits: int
            - total_commits: int
            - candidate_lines: int
            - total_lines: int
            - matched_emails: list
    """
    total_commits = 0
    total_lines = 0
    candidate_commits = 0
    candidate_lines = 0
    
    matched_authors = []
    
    for email, data in author_map.items():
        commits = data.get("commits", 0)
        lines = data.get("lines_added", 0)
        total_commits += commits
        total_lines += lines
        
        if email.lower() in identity.candidate_emails or email.lower() in identity.matched_emails:
            candidate_commits += commits
            candidate_lines += lines
            matched_authors.append(email)
    
    authorship_by_commits = candidate_commits / total_commits if total_commits > 0 else 0.0
    authorship_by_lines = candidate_lines / total_lines if total_lines > 0 else 0.0
    
    # Use average of commit and line authorship
    authorship_fraction = (authorship_by_commits + authorship_by_lines) / 2
    
    return {
        "authorship_fraction": round(authorship_fraction, 4),
        "candidate_commits": candidate_commits,
        "total_commits": total_commits,
        "candidate_lines": candidate_lines,
        "total_lines": total_lines,
        "matched_emails": matched_authors
    }
