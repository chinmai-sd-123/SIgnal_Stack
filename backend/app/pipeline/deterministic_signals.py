"""
Deterministic Signal Extractors Module.

This module provides standardized signal extraction with evidence for reproducible evaluations.
Each signal follows the format:
{
    "name": str,
    "value": float (0.0 to 1.0),
    "evidence": {
        "file": str,
        "commit": str,
        "lines": tuple(start, end),
        "snippet": str
    }
}
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import re


@dataclass
class SignalEvidence:
    """Evidence supporting a signal."""
    file: str = ""
    commit: str = ""
    lines: Tuple[int, int] = (0, 0)
    snippet: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file,
            "commit": self.commit,
            "lines": list(self.lines),
            "snippet": self.snippet
        }


@dataclass
class Signal:
    """Standardized signal output."""
    name: str
    value: float
    evidence: SignalEvidence
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "evidence": self.evidence.to_dict()
        }


class DeterministicSignalExtractor:
    """
    Extracts deterministic signals from repository data.
    
    All extractors return Signal objects with evidence for audit trail.
    """
    
    # ==================== AUTHORSHIP ====================
    
    @staticmethod
    def extract_authorship_fraction(
        author_map: Dict[str, Dict[str, int]],
        candidate_email: str,
        candidate_aliases: List[str] = None
    ) -> Signal:
        """
        Calculate the fraction of code authored by the candidate.
        
        Args:
            author_map: {email: {commits: N, lines_added: M, lines_deleted: D}}
            candidate_email: Primary email of candidate
            candidate_aliases: Alternative emails/names
        
        Returns:
            Signal with authorship fraction (0-1)
        """
        if not author_map:
            return Signal(
                name="authorship_fraction",
                value=0.0,
                evidence=SignalEvidence(
                    snippet="No author data available from repository"
                )
            )
        
        aliases = set([candidate_email.lower()])
        if candidate_aliases:
            aliases.update(a.lower() for a in candidate_aliases)
        
        total_commits = sum(a.get("commits", 0) for a in author_map.values())
        total_lines = sum(a.get("lines_added", 0) for a in author_map.values())
        
        candidate_commits = 0
        candidate_lines = 0
        matched_authors = []
        
        for email, stats in author_map.items():
            email_lower = email.lower()
            if any(alias in email_lower or email_lower in alias for alias in aliases):
                candidate_commits += stats.get("commits", 0)
                candidate_lines += stats.get("lines_added", 0)
                matched_authors.append(email)
        
        # Calculate fraction (prefer line-based if available)
        if total_lines > 0:
            fraction = candidate_lines / total_lines
        elif total_commits > 0:
            fraction = candidate_commits / total_commits
        else:
            fraction = 0.0
        
        return Signal(
            name="authorship_fraction",
            value=round(min(fraction, 1.0), 4),
            evidence=SignalEvidence(
                snippet=f"Matched authors: {matched_authors}\n"
                        f"Commits: {candidate_commits}/{total_commits}\n"
                        f"Lines: {candidate_lines}/{total_lines}"
            )
        )
    
    # ==================== FILE PRESENCE SIGNALS ====================
    
    @staticmethod
    def extract_tests_present(files: List[str], file_contents: Dict[str, str] = None) -> Signal:
        """
        Check for presence of test files.
        
        Returns 1.0 if test files found, 0.0 otherwise.
        """
        test_patterns = [
            r'test[s]?/',
            r'test_.*\.py$',
            r'.*_test\.py$',
            r'.*\.test\.(js|ts|jsx|tsx)$',
            r'.*\.spec\.(js|ts|jsx|tsx)$',
            r'__tests__/',
            r'spec/',
        ]
        
        test_files = []
        for f in files:
            for pattern in test_patterns:
                if re.search(pattern, f, re.IGNORECASE):
                    test_files.append(f)
                    break
        
        if test_files:
            return Signal(
                name="tests_present",
                value=1.0,
                evidence=SignalEvidence(
                    file=test_files[0],
                    snippet=f"Found {len(test_files)} test file(s): {', '.join(test_files[:5])}"
                )
            )
        
        return Signal(
            name="tests_present",
            value=0.0,
            evidence=SignalEvidence(snippet="No test files found in repository")
        )
    
    @staticmethod
    def extract_ci_present(files: List[str]) -> Signal:
        """Check for CI/CD configuration files."""
        ci_patterns = {
            '.github/workflows/': 'GitHub Actions',
            '.gitlab-ci.yml': 'GitLab CI',
            '.travis.yml': 'Travis CI',
            'Jenkinsfile': 'Jenkins',
            '.circleci/': 'CircleCI',
            'azure-pipelines.yml': 'Azure Pipelines',
            '.drone.yml': 'Drone CI',
        }
        
        found_ci = []
        for f in files:
            for pattern, name in ci_patterns.items():
                if pattern in f:
                    found_ci.append((f, name))
                    break
        
        if found_ci:
            return Signal(
                name="ci_present",
                value=1.0,
                evidence=SignalEvidence(
                    file=found_ci[0][0],
                    snippet=f"Found CI configuration: {found_ci[0][1]} at {found_ci[0][0]}"
                )
            )
        
        return Signal(
            name="ci_present",
            value=0.0,
            evidence=SignalEvidence(snippet="No CI/CD configuration found")
        )
    
    @staticmethod
    def extract_dockerfile_present(files: List[str]) -> Signal:
        """Check for Docker configuration files."""
        docker_files = []
        for f in files:
            basename = f.split('/')[-1].lower()
            if basename in ['dockerfile', 'docker-compose.yml', 'docker-compose.yaml', '.dockerignore']:
                docker_files.append(f)
            elif 'dockerfile' in basename:
                docker_files.append(f)
        
        if docker_files:
            return Signal(
                name="dockerfile_present",
                value=1.0,
                evidence=SignalEvidence(
                    file=docker_files[0],
                    snippet=f"Found Docker configuration: {', '.join(docker_files)}"
                )
            )
        
        return Signal(
            name="dockerfile_present",
            value=0.0,
            evidence=SignalEvidence(snippet="No Docker configuration found")
        )
    
    @staticmethod
    def extract_schema_present(files: List[str], file_contents: Dict[str, str] = None) -> Signal:
        """
        Check for database schema definitions.
        
        Looks for:
        - SQLAlchemy models
        - Django models
        - SQL migration files
        - Prisma schema
        - TypeORM entities
        """
        schema_patterns = {
            'models.py': 'Django/SQLAlchemy models',
            'schema.prisma': 'Prisma schema',
            'migrations/': 'Database migrations',
            'alembic/': 'Alembic migrations',
            '.sql': 'SQL files',
            'entities/': 'TypeORM entities',
        }
        
        schema_files = []
        for f in files:
            for pattern, desc in schema_patterns.items():
                if pattern in f.lower():
                    schema_files.append((f, desc))
                    break
        
        # Also check file contents for schema definitions if available
        content_evidence = ""
        if file_contents:
            schema_keywords = ['Column(', 'ForeignKey(', 'class Meta:', '@Entity', 'CREATE TABLE']
            for filepath, content in file_contents.items():
                for kw in schema_keywords:
                    if kw in content:
                        content_evidence = f"Found '{kw}' in {filepath}"
                        if not schema_files:
                            schema_files.append((filepath, "Schema definition"))
                        break
        
        if schema_files:
            return Signal(
                name="schema_present",
                value=1.0,
                evidence=SignalEvidence(
                    file=schema_files[0][0],
                    snippet=f"Found schema: {schema_files[0][1]}. {content_evidence}"
                )
            )
        
        return Signal(
            name="schema_present",
            value=0.0,
            evidence=SignalEvidence(snippet="No database schema found")
        )
    
    @staticmethod
    def extract_rate_limiting_present(files: List[str], file_contents: Dict[str, str] = None) -> Signal:
        """
        Check for rate limiting implementation.
        
        Looks for:
        - Rate limit middleware
        - Throttling decorators
        - API quota configurations
        """
        if not file_contents:
            return Signal(
                name="rate_limiting_present",
                value=0.0,
                evidence=SignalEvidence(snippet="No file contents available for analysis")
            )
        
        rate_limit_patterns = [
            r'rate.?limit',
            r'throttle',
            r'ratelimit',
            r'slowapi',
            r'flask.?limiter',
            r'express.?rate.?limit',
            r'@limits\(',
            r'RateLimiter',
            r'requests_per_',
        ]
        
        for filepath, content in file_contents.items():
            content_lower = content.lower()
            for pattern in rate_limit_patterns:
                if re.search(pattern, content_lower):
                    # Find the actual line
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if re.search(pattern, line.lower()):
                            snippet_start = max(0, i - 2)
                            snippet_end = min(len(lines), i + 3)
                            snippet = '\n'.join(lines[snippet_start:snippet_end])
                            return Signal(
                                name="rate_limiting_present",
                                value=1.0,
                                evidence=SignalEvidence(
                                    file=filepath,
                                    lines=(snippet_start + 1, snippet_end),
                                    snippet=snippet[:500]
                                )
                            )
        
        return Signal(
            name="rate_limiting_present",
            value=0.0,
            evidence=SignalEvidence(snippet="No rate limiting implementation found")
        )
    
    @staticmethod
    def extract_readme_quality_score(files: List[str], file_contents: Dict[str, str] = None) -> Signal:
        """
        Score README quality based on content completeness.
        
        Scoring:
        - 0.0: No README
        - 0.2: README exists but minimal (<100 chars)
        - 0.4: Basic README (title, some text)
        - 0.6: Good README (installation, usage sections)
        - 0.8: Great README (examples, badges, contributing)
        - 1.0: Excellent README (all above + API docs, tests info)
        """
        readme_file = None
        for f in files:
            basename = f.split('/')[-1].lower()
            if basename.startswith('readme'):
                readme_file = f
                break
        
        if not readme_file:
            return Signal(
                name="readme_quality_score",
                value=0.0,
                evidence=SignalEvidence(snippet="No README file found")
            )
        
        if not file_contents or readme_file not in file_contents:
            return Signal(
                name="readme_quality_score",
                value=0.2,
                evidence=SignalEvidence(
                    file=readme_file,
                    snippet="README exists but content not available for analysis"
                )
            )
        
        content = file_contents[readme_file].lower()
        score = 0.2  # Base score for having README
        
        quality_indicators = {
            'installation': 0.1,
            'install': 0.1,
            'usage': 0.1,
            'getting started': 0.1,
            'example': 0.1,
            'api': 0.1,
            'contributing': 0.1,
            'license': 0.05,
            'test': 0.1,
            'badge': 0.05,
            '```': 0.1,  # Code blocks
        }
        
        found_indicators = []
        for indicator, points in quality_indicators.items():
            if indicator in content:
                score += points
                found_indicators.append(indicator)
        
        score = min(score, 1.0)
        
        return Signal(
            name="readme_quality_score",
            value=round(score, 2),
            evidence=SignalEvidence(
                file=readme_file,
                snippet=f"README quality indicators found: {', '.join(found_indicators)}"
            )
        )
    
    # ==================== AGGREGATE EXTRACTION ====================
    
    @classmethod
    def extract_all_signals(
        cls,
        files: List[str],
        file_contents: Dict[str, str] = None,
        author_map: Dict[str, Dict[str, int]] = None,
        candidate_email: str = None,
        candidate_aliases: List[str] = None
    ) -> Dict[str, Signal]:
        """
        Extract all deterministic signals from repository data.
        
        Returns:
            Dictionary mapping signal name to Signal object
        """
        signals = {}
        
        # Authorship (if data available)
        if author_map and candidate_email:
            signals["authorship_fraction"] = cls.extract_authorship_fraction(
                author_map, candidate_email, candidate_aliases
            )
        
        # File presence signals
        signals["tests_present"] = cls.extract_tests_present(files, file_contents)
        signals["ci_present"] = cls.extract_ci_present(files)
        signals["dockerfile_present"] = cls.extract_dockerfile_present(files)
        signals["schema_present"] = cls.extract_schema_present(files, file_contents)
        signals["rate_limiting_present"] = cls.extract_rate_limiting_present(files, file_contents)
        signals["readme_quality_score"] = cls.extract_readme_quality_score(files, file_contents)
        
        return signals
    
    @classmethod
    def signals_to_dict(cls, signals: Dict[str, Signal]) -> Dict[str, Dict[str, Any]]:
        """Convert signals dictionary to JSON-serializable format."""
        return {name: sig.to_dict() for name, sig in signals.items()}


# Convenience function for backward compatibility
def extract_deterministic_signals(
    files: List[str],
    file_contents: Dict[str, str] = None,
    author_map: Dict[str, Dict[str, int]] = None,
    candidate_email: str = None,
    candidate_aliases: List[str] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Convenience function to extract all signals and return as dictionary.
    """
    extractor = DeterministicSignalExtractor()
    signals = extractor.extract_all_signals(
        files=files,
        file_contents=file_contents,
        author_map=author_map,
        candidate_email=candidate_email,
        candidate_aliases=candidate_aliases
    )
    return extractor.signals_to_dict(signals)
