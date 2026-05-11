"""
Evidence Selector Module

Smart tree traversal to select the top 20 priority files for evaluation.
Priority order:
1. Manifests (package.json, pyproject.toml, go.mod, pom.xml)
2. Entry points (index.js, app.py, main.go)
3. README (first 2KB)
4. CI configs (.github/workflows/*)
5. Dockerfile
6. Tests (__tests__, test/, *.spec.*)
7. Task-specific filenames (matching outcome keywords)
8. src/components (frontend) or routes/controllers (backend)
9. Migration/model files
10. docs/ and config files
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

CODE_EXTENSIONS = (
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".rb", ".php", ".cs"
)

PATH_KEYWORD_STOPWORDS = {
    "app", "api", "backend", "server", "handler", "request", "response", "model",
    "table", "column", "service", "function", "import", "export", "container",
    "deployment", "image", "from", "run", "cmd",
    "and", "or", "the", "with",
}


# Priority patterns with weights (higher = more important)
PRIORITY_PATTERNS = [
    # Priority 1: Manifests (weight 100)
    (100, r'^package\.json$'),
    (100, r'^pyproject\.toml$'),
    (100, r'^requirements\.txt$'),
    (100, r'^go\.mod$'),
    (100, r'^pom\.xml$'),
    (100, r'^build\.gradle(\.kts)?$'),
    (100, r'^Cargo\.toml$'),
    (100, r'^Gemfile$'),
    (100, r'^composer\.json$'),
    
    # Priority 2: Entry points (weight 90)
    (90, r'^(src/)?index\.(js|ts|tsx)$'),
    (90, r'^(src/)?app\.(py|js|ts)$'),
    (90, r'^(src/)?main\.(py|go|rs|java)$'),
    (90, r'^(cmd/)?main\.go$'),
    (90, r'^server\.(py|js|ts)$'),
    
    # Priority 3: README (weight 85)
    (85, r'^README(\.(md|rst|txt))?$'),
    
    # Priority 4: CI configs (weight 80)
    (80, r'^\.github/workflows/.+\.ya?ml$'),
    (80, r'^\.gitlab-ci\.ya?ml$'),
    (80, r'^\.circleci/config\.yml$'),
    (80, r'^Jenkinsfile$'),
    
    # Priority 5: Docker (weight 75)
    (75, r'^Dockerfile$'),
    (75, r'^docker-compose\.ya?ml$'),
    (75, r'^\.dockerignore$'),
    
    # Priority 6: Tests (weight 70)
    (70, r'^__tests__/.+\.(js|ts|jsx|tsx)$'),
    (70, r'^tests?/.+\.(py|js|ts)$'),
    (70, r'^.+\.(spec|test)\.(js|ts|jsx|tsx)$'),
    (70, r'^test_.+\.py$'),
    (70, r'^.+_test\.go$'),
    
    # Priority 7: Backend patterns (weight 60)
    (60, r'^(src/)?(routes|controllers|api)/.+\.(py|js|ts|go)$'),
    (60, r'^(src/)?middleware/.+\.(py|js|ts)$'),
    (60, r'^(src/)?services?/.+\.(py|js|ts)$'),
    
    # Priority 8: Frontend patterns (weight 55)
    (55, r'^(src/)?components/.+\.(jsx|tsx|vue)$'),
    (55, r'^(src/)?pages/.+\.(jsx|tsx|vue)$'),
    (55, r'^(src/)?views/.+\.(jsx|tsx|vue)$'),
    
    # Priority 9: Database/Models (weight 50)
    (50, r'^(src/)?(models|schemas)/.+\.(py|ts|js)$'),
    (50, r'^migrations?/.+\.(py|sql|go)$'),
    (50, r'^prisma/schema\.prisma$'),
    (50, r'^alembic/.+\.py$'),
    
    # Priority 10: Config files (weight 40)
    (40, r'^(config|settings)\.(py|js|ts|json|ya?ml)$'),
    (40, r'^\.env\.example$'),
    (40, r'^tsconfig\.json$'),
    (40, r'^webpack\.config\.(js|ts)$'),
    (40, r'^vite\.config\.(js|ts)$'),
    
    # Priority 11: Docs (weight 30)
    (30, r'^docs?/.+\.(md|rst)$'),
    (30, r'^CHANGELOG\.md$'),
    (30, r'^CONTRIBUTING\.md$'),
]


@dataclass
class PriorityFile:
    """A file with its priority score."""
    path: str
    priority: int
    category: str


def get_file_priority(file_path: str, keywords: Optional[List[str]] = None) -> Tuple[int, str]:
    """
    Get priority score for a file path.
    Returns (priority, category) tuple.
    """
    filename = file_path.split('/')[-1] if '/' in file_path else file_path
    file_lower = file_path.lower()
    filename_lower = filename.lower()

    if filename_lower == "__init__.py":
        return (0, "other")

    # Task-specific implementation files should outrank generic manifests,
    # README, Docker, and CI files. Otherwise the LLM sees infrastructure before
    # the actual code that proves capability.
    if keywords:
        match_count = 0
        for kw in keywords:
            kw_lower = kw.lower().strip()
            if len(kw_lower) < 3 or kw_lower in PATH_KEYWORD_STOPWORDS:
                continue
            if kw_lower in file_lower:
                match_count += 1
        if match_count > 0:
            middleware_boost = 1 if "/middleware/" in f"/{file_lower}" else 0
            if filename_lower.endswith(CODE_EXTENSIONS):
                return (120 + min(match_count, 10) + middleware_boost, "task_specific")
            return (65 + min(match_count, 10), "task_specific")
    
    # Check against priority patterns
    for weight, pattern in PRIORITY_PATTERNS:
        if re.match(pattern, file_path, re.IGNORECASE) or re.match(pattern, filename, re.IGNORECASE):
            # Determine category from pattern
            if filename_lower in {"package.json", "requirements.txt", "go.mod", "pyproject.toml", "pom.xml", "cargo.toml", "gemfile", "composer.json"}:
                category = "manifest"
            elif 'index' in pattern or 'main' in pattern or 'app' in pattern:
                category = "entry_point"
            elif filename_lower.startswith("readme"):
                category = "readme"
            elif 'github' in pattern or 'gitlab' in pattern or 'circleci' in pattern:
                category = "ci_config"
            elif 'docker' in pattern.lower():
                category = "docker"
            elif 'test' in pattern.lower() or 'spec' in pattern.lower():
                category = "test"
            elif 'route' in pattern or 'controller' in pattern or 'middleware' in pattern:
                category = "backend"
            elif 'component' in pattern or 'page' in pattern or 'view' in pattern:
                category = "frontend"
            elif 'model' in pattern or 'migration' in pattern or 'schema' in pattern:
                category = "database"
            elif 'config' in pattern or 'setting' in pattern:
                category = "config"
            else:
                category = "documentation"
            
            return (weight, category)
    
    # Default priority for source files. Small projects often put the real
    # implementation in modules such as app/github.py or app/gemini.py rather
    # than routes/controllers folders, so do not drop these files entirely.
    if filename_lower.endswith(CODE_EXTENSIONS):
        return (45, "code")

    # Default low priority for other files
    return (0, "other")


def priority_files(
    file_tree: List[str],
    max_files: int = 20,
    keywords: Optional[List[str]] = None
) -> List[PriorityFile]:
    """
    Select top priority files from a file tree.
    
    Args:
        file_tree: List of file paths from repository
        max_files: Maximum files to return (default 20)
        keywords: Optional keywords for task-specific matching
    
    Returns:
        Sorted list of PriorityFile objects (highest priority first)
    """
    scored_files: List[PriorityFile] = []
    
    for file_path in file_tree:
        # Skip hidden files (except CI config)
        if file_path.startswith('.') and not file_path.startswith('.github') and not file_path.startswith('.gitlab'):
            continue
        
        # Skip binary/asset files
        if any(file_path.endswith(ext) for ext in ['.png', '.jpg', '.gif', '.ico', '.svg', '.woff', '.woff2', '.ttf', '.eot', '.mp4', '.mp3', '.pdf', '.zip', '.tar', '.gz']):
            continue
        
        # Skip vendor/node_modules
        if any(segment in file_path for segment in ['node_modules/', 'vendor/', '__pycache__/', '.git/', 'dist/', 'build/', '.next/']):
            continue
        
        priority, category = get_file_priority(file_path, keywords)
        
        if priority > 0:
            scored_files.append(PriorityFile(
                path=file_path,
                priority=priority,
                category=category
            ))
    
    # Sort by priority descending
    scored_files.sort(key=lambda f: f.priority, reverse=True)
    
    return scored_files[:max_files]


def extract_snippets(
    file_path: str,
    content: str,
    max_length: int = 400,
    keywords: Optional[List[str]] = None
) -> Dict[str, str]:
    """
    Extract meaningful snippet from file content.
    
    Args:
        file_path: Path of the file
        content: Full file content
        max_length: Maximum snippet length
        keywords: Optional list of keywords to anchor snippets
    
    Returns:
        Dict with file, lines, and snippet
    """
    if not content:
        return {
            "file": file_path,
            "lines": "0-0",
            "snippet": ""
        }
    
    lines = content.split('\n')
    total_lines = len(lines)

    # Small implementation files are best shown whole. A clipped import-only
    # preview makes weak projects look less auditable than they really are.
    filename = file_path.split('/')[-1].lower()
    if filename.endswith(CODE_EXTENSIONS) and len(content) <= max_length:
        return {
            "file": file_path,
            "lines": f"1-{total_lines}",
            "snippet": content
        }
    
    # For README, get intro section
    if 'readme' in filename:
        snippet = content[:2048]  # First 2KB for README
        return {
            "file": file_path,
            "lines": f"1-{min(50, total_lines)}",
            "snippet": snippet[:max_length]
        }
    
    # For code files, anchor around keyword hits when provided
    if keywords:
        lowered = [kw.lower() for kw in keywords]
        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            if any(kw in line_lower for kw in lowered):
                start_idx = max(0, i - 8)
                end_idx = min(total_lines, i + 30)
                snippet_lines = lines[start_idx:end_idx]
                snippet = "\n".join(snippet_lines)
                return {
                    "file": file_path,
                    "lines": f"{start_idx + 1}-{end_idx}",
                    "snippet": snippet[:max_length]
                }

    # Default: return the first section
    snippet_lines = []
    char_count = 0
    start_line = 1

    for i, line in enumerate(lines, 1):
        if char_count + len(line) > max_length:
            break
        snippet_lines.append(line)
        char_count += len(line) + 1  # +1 for newline

    end_line = start_line + len(snippet_lines) - 1
    
    return {
        "file": file_path,
        "lines": f"{start_line}-{end_line}",
        "snippet": '\n'.join(snippet_lines)
    }


def select_evidence_files(
    file_tree: List[str],
    file_contents: Dict[str, str],
    keywords: Optional[List[str]] = None,
    max_files: int = 20
) -> List[Dict]:
    """
    Main entry point: Select and extract evidence files.
    
    Args:
        file_tree: List of all file paths
        file_contents: Dict of file path -> content for available files
        keywords: Task-specific keywords for matching
        max_files: Max files to return
    
    Returns:
        List of evidence objects with file, category, priority, snippet
    """
    priority_list = priority_files(file_tree, max_files * 2, keywords)
    
    evidence = []
    for pf in priority_list:
        if len(evidence) >= max_files:
            break
        
        content = file_contents.get(pf.path, "")
        snippet_data = extract_snippets(pf.path, content, keywords=keywords)
        
        evidence.append({
            "file": pf.path,
            "category": pf.category,
            "priority": pf.priority,
            "lines": snippet_data["lines"],
            "snippet": snippet_data["snippet"]
        })
    
    return evidence
