from typing import List, Dict, Any, Optional
import re
from app.services.github import GitHubService
import app.schemas as schemas
from app.services.repo_selector import (
    matches_any_pattern,
    DEPLOYMENT_PATTERNS,
    CI_CD_PATTERNS,
    TEST_PATTERNS,
    ML_MODEL_PATTERNS,
    FRONTEND_PATTERNS,
    MIGRATION_PATTERNS,
    MANIFEST_PATTERNS,
)

class SignalExtractor:
    def __init__(self):
        self.github = GitHubService()

    def extract_signals(self, proof: schemas.ProofCreate) -> Dict[str, Any]:
        """Extract raw signals from the proof of work."""
        repo_url = proof.payload.get("repo_url", "")
        artifact_link = proof.payload.get("artifact_link")
        
        # Priority: Artifact Link (Non-Tech) -> Repo URL (Tech)
        target = artifact_link or repo_url
        
        if not target:
             return {"valid_repo": 0.0, "has_evidence": 0.0}

        # NON-TECHNICAL FLOW (Generic Artifact)
        if "github.com" not in target:
             return {
                 "valid_repo": 0.0,
                 "has_evidence": 1.0,
                 "artifact_present": 1.0,
                 "context_length": len(proof.payload.get("context", ""))
             }

        # TECHNICAL FLOW (GitHub)
        if not repo_url or "github.com" not in repo_url:
            return {"valid_repo": 0.0}

        signals = {"valid_repo": 1.0}
        files, _ = self.github.get_recursive_tree(repo_url)
        
        # ===== CORE SIGNALS (Using Fuzzy Pattern Matching) =====
        # 1. Test Presence - handles test/, tests/, __tests__/, *_test.py, etc.
        has_tests = any(matches_any_pattern(f, TEST_PATTERNS) for f in files)
        signals["tests_present"] = 1.0 if has_tests else 0.0

        # 2. Migrations / DB - handles migrations/, alembic/, prisma/, *.sql
        has_migrations = any(matches_any_pattern(f, MIGRATION_PATTERNS) for f in files)
        signals["migrations_present"] = 1.0 if has_migrations else 0.0
        
        # 3. Docker / Deployment - handles docker.yaml, Dockerfile.prod, kubernetes.yml, etc.
        has_docker = any(matches_any_pattern(f, DEPLOYMENT_PATTERNS) for f in files)
        signals["deployment_ready"] = 1.0 if has_docker else 0.0

        # 4. CI/CD - handles .github/workflows/, .gitlab-ci.yml, Jenkinsfile, etc.
        has_ci = any(matches_any_pattern(f, CI_CD_PATTERNS) for f in files)
        signals["ci_cd_present"] = 1.0 if has_ci else 0.0
        
        # ===== ML / AI SIGNALS =====
        # 5. Model Files - handles *.pkl, *.h5, *.pt, models/, checkpoints/, etc.
        has_model = any(matches_any_pattern(f, ML_MODEL_PATTERNS) for f in files)
        signals["ml_model_present"] = 1.0 if has_model else 0.0
        
        # 6. ML Libraries
        ml_keywords = ["scikit", "sklearn", "tensorflow", "pytorch", "keras", "xgboost", "numpy", "pandas"]
        signals["ml_libraries"] = 0.0
        checked_files = 0
        for f in files:
            if "requirements" in f.lower() or "setup.py" in f.lower():
                if checked_files >= 5: break
                content = self.github.get_file_content(repo_url, f)
                checked_files += 1
                if any(kw in content.lower() for kw in ml_keywords):
                    signals["ml_libraries"] = 1.0
                    break
        
        # 8. Frontend - handles templates/, components/, pages/, *.html, etc.
        has_templates = any(matches_any_pattern(f, FRONTEND_PATTERNS) for f in files)
        signals["frontend_present"] = 1.0 if has_templates else 0.0
        
        # 9. Static files (CSS, JS) - part of frontend patterns
        has_static = any(f.endswith(".css") or f.endswith(".js") or "static/" in f or "assets/" in f for f in files)
        signals["static_assets"] = 1.0 if has_static else 0.0
        
        # ===== NLP SIGNALS =====
        # 10. NLP Libraries
        nlp_keywords = ["nltk", "spacy", "textblob", "tfidf", "vectorizer", "tokenizer"]
        signals["nlp_present"] = 0.0
        checked_files = 0
        for f in files:
            if f.endswith(".py"):
                if checked_files >= 10: break
                content = self.github.get_file_content(repo_url, f)
                checked_files += 1
                if any(kw in content.lower() for kw in nlp_keywords):
                    signals["nlp_present"] = 1.0
                    break

        # ===== COMMIT HISTORY =====
        commits = self.github.get_commit_history(repo_url)
        signals["commit_count"] = min(len(commits), 50)  # Cap at 50 for normalization
        if commits:
            authors = set(c["author_name"] for c in commits)
            signals["unique_authors"] = len(authors)
            signals["recent_activity_score"] = 1.0
        else:
            signals["unique_authors"] = 0
            signals["recent_activity_score"] = 0.0

        return signals

    def _get_evidence_keywords(self, task_title: str) -> List[str]:
        """Get code keywords to search for based on task title - COMPREHENSIVE."""
        title_lower = task_title.lower()
        keywords = []
        
        # ML/AI Tasks
        if any(k in title_lower for k in ["ml", "model", "train", "classification", "prediction", "machine learning"]):
            keywords = ["pickle", "joblib", "fit", "predict", "sklearn", "TfidfVectorizer", "model.save", "train_test_split", "accuracy", "keras", "torch", "tensorflow"]
        
        # API/Backend Tasks
        elif any(k in title_lower for k in ["api", "restful", "endpoint", "backend", "server"]):
            keywords = ["@app.route", "@router", "@api", "def post", "def get", "request", "jsonify", "Response", "FastAPI", "Flask", "Express", "handler"]
        
        # Database Tasks
        elif any(k in title_lower for k in ["database", "schema", "migration", "sql", "orm"]):
            keywords = ["CREATE TABLE", "Column", "Model", "Table", "ForeignKey", "migrate", "db.session", "prisma", "mongoose", "sequelize"]
        
        # Frontend Tasks (React, Next.js, Vue, etc.)
        elif any(k in title_lower for k in ["frontend", "react", "next.js", "nextjs", "vue", "angular", "component", "ui"]):
            keywords = ["import React", "export default", "useState", "useEffect", "function", "const App", "getServerSideProps", "getStaticProps", "<div", "className", "render"]
        
        # GraphQL Tasks
        elif any(k in title_lower for k in ["graphql", "query", "mutation", "apollo"]):
            keywords = ["gql`", "Query", "Mutation", "Resolver", "typeDefs", "schema", "useQuery", "useMutation", "ApolloClient", "graphql"]
        
        # Authentication Tasks
        elif any(k in title_lower for k in ["auth", "login", "jwt", "oauth", "session", "password"]):
            keywords = ["authenticate", "login", "logout", "jwt", "token", "session", "bcrypt", "hash", "verify", "password", "OAuth"]
        
        # Docker/Deployment Tasks
        elif any(k in title_lower for k in ["deploy", "container", "docker", "kubernetes", "k8s", "ci/cd"]):
            keywords = ["FROM ", "RUN ", "CMD ", "EXPOSE", "docker-compose", "image:", "container", "deployment", "service"]
        
        # Testing Tasks
        elif any(k in title_lower for k in ["test", "testing", "unit test", "integration"]):
            keywords = ["def test_", "assert", "expect", "describe", "it(", "pytest", "jest", "mocha", "@Test"]
        
        # Initialize/Setup Tasks
        elif any(k in title_lower for k in ["initialize", "setup", "init", "create", "scaffold"]):
            keywords = ["create", "init", "setup", "config", "install", "package.json", "requirements", "main", "app", "index"]
        
        # Integration Tasks
        elif any(k in title_lower for k in ["integration", "integrate", "connect", "api integration"]):
            keywords = ["import", "fetch", "axios", "request", "client", "connect", "integration", "service"]
        
        # Default - Extract any meaningful code
        else:
            # Parse task title words as potential keywords
            words = [w for w in task_title.split() if len(w) > 3]
            keywords = words + ["def ", "class ", "function ", "export ", "import "]
        
        return keywords

    def _get_priority_files(self, files: List[str], task_title: str) -> List[str]:
        """Get files that are most likely to contain task implementation."""
        title_lower = task_title.lower()
        priority = []
        
        # Frontend/Next.js/React
        if any(k in title_lower for k in ["frontend", "react", "next.js", "nextjs", "component", "ui", "page"]):
            priority = [f for f in files if any(x in f.lower() for x in [
                "pages/", "components/", "app/", "src/", ".tsx", ".jsx", "index.js", "app.js", "layout"
            ])]
        
        # GraphQL
        elif any(k in title_lower for k in ["graphql", "query", "resolver"]):
            priority = [f for f in files if any(x in f.lower() for x in [
                "graphql", "schema", "resolver", "query", "mutation", ".gql", "apollo"
            ])]
        
        # API/Backend
        elif any(k in title_lower for k in ["api", "backend", "endpoint", "server"]):
            priority = [f for f in files if any(x in f.lower() for x in [
                "app.", "main.", "server.", "routes/", "api/", "controller", "handler"
            ])]
        
        # ML/Model
        elif any(k in title_lower for k in ["ml", "model", "train"]):
            priority = [f for f in files if any(x in f.lower() for x in [
                "model", "train", "predict", ".pkl", "pipeline", "classifier"
            ])]
        
        # Auth
        elif any(k in title_lower for k in ["auth", "login", "jwt"]):
            priority = [f for f in files if any(x in f.lower() for x in [
                "auth", "login", "user", "session", "middleware", "jwt"
            ])]
        
        # Docker/Deploy
        elif any(k in title_lower for k in ["docker", "deploy", "kubernetes"]):
            priority = [f for f in files if any(x in f.lower() for x in [
                "docker", "compose", "kubernetes", "k8s", "deploy", "ci", "cd"
            ])]
        
        # Default: Look for main implementation files
        if not priority:
            priority = [f for f in files if any(x in f.lower() for x in [
                "app.", "main.", "index.", "core.", "service.", "src/"
            ]) and not any(x in f.lower() for x in ["test", "spec", "node_modules", "venv"])]
        
        return sorted(priority[:15], key=lambda f: f.lower())  # Sorted for determinism


    def extract_evidence(self, repo_url: str, task_title: str, context: str = "", artifact_link: str = None) -> List[schemas.Evidence]:
        """Extract relevant evidence. Supports Code (GitHub) and Text/Link (Non-Tech)."""
        evidence = []
        
        # Create a short task identifier for unique refs
        task_short = task_title[:30].replace(' ', '_') if task_title else 'general'
        
        # NON-TECHNICAL FLOW
        target = artifact_link or repo_url
        if target and "github.com" not in target:
             evidence.append(schemas.Evidence(
                type="work_artifact",
                ref=f"ARTIFACT:{task_short}",
                snippet=f"Task: {task_title}\n\nUser provided artifact link: {target}\n\nContext/Description:\n{context}",
                source_url=target
            ))
             return evidence
             
        # TECHNICAL FLOW
        if not repo_url or "github.com" not in repo_url:
             return []

        # ... existing GitHub logic ...
        
        # Clean URL for display links (remove .git)
        clean_repo_url = repo_url.rstrip('/')
        if clean_repo_url.endswith('.git'):
            clean_repo_url = clean_repo_url[:-4]
            
        files, default_branch = self.github.get_recursive_tree(repo_url)
        files = sorted(files, key=lambda f: f.lower())  # Ensure deterministic order
        keywords = self._get_evidence_keywords(task_title)
        
        # Use the new priority files method
        priority_files = self._get_priority_files(files, task_title)
        
        # Track found evidence to avoid duplicates
        found_snippets = set()
        MAX_EVIDENCE = 3  # Find up to 3 code snippets per task
        
        # Scan priority files for MULTIPLE implementation evidence
        for f in priority_files:
            if len(evidence) >= MAX_EVIDENCE:
                break
                
            content = self.github.get_file_content(repo_url, f)
            if not content:
                continue
            
            # Search for any keyword match in this file
            for kw in keywords:
                if len(evidence) >= MAX_EVIDENCE:
                    break
                    
                if kw.lower() in content.lower():  # Case-insensitive search
                    # Extract a meaningful snippet around the keyword
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if kw.lower() in line.lower():
                            # Create snippet key to avoid duplicates
                            snippet_key = f"{f}:{i}"
                            if snippet_key in found_snippets:
                                continue
                            found_snippets.add(snippet_key)
                            
                            # Get context around the match (5 lines before, 8 lines after)
                            start = max(0, i - 2)
                            end = min(len(lines), i + 8)
                            snippet_lines = lines[start:end]
                            snippet = "\n".join(snippet_lines)
                            
                            # Add evidence with clear file + line reference
                            evidence.append(schemas.Evidence(
                                type="code_snippet",
                                ref=f"{f}#L{i+1}",  # Clear file:line format
                                snippet=snippet[:500],  # Show more context
                                source_url=f"{clean_repo_url}/blob/{default_branch}/{f}#L{start+1}-L{end}"
                            ))
                            
                            if len(evidence) >= MAX_EVIDENCE:
                                break
                            break  # Move to next file after finding one match per file
        
        # If no keyword matches, try to find relevant files by name pattern
        if not evidence:
            # Look for files that match task keywords in their name/path
            task_words = [w.lower() for w in task_title.split() if len(w) > 3]
            for f in files[:100]:
                if len(evidence) >= MAX_EVIDENCE:
                    break
                f_lower = f.lower()
                if any(word in f_lower for word in task_words):
                    content = self.github.get_file_content(repo_url, f)
                    if content:
                        # Show first 10 meaningful lines
                        lines = [l for l in content.split('\n') if l.strip() and not l.strip().startswith('#')][:10]
                        snippet = "\n".join(lines)
                        evidence.append(schemas.Evidence(
                            type="code_snippet",
                            ref=f"{f}",
                            snippet=f"File likely related to '{task_title}':\n\n{snippet[:500]}",
                            source_url=f"{clean_repo_url}/blob/{default_branch}/{f}"
                        ))
        
        # Fallback evidence ONLY if nothing found
        if not evidence and files:
            # Smart Filter: Ignore docs, tests, examples & binaries
            def is_valid_code(f):
                lower = f.lower()
                # 1. Ignore directories
                if any(x in lower for x in ['docs/', 'test/', 'example/', 'site-packages', 'venv', 'node_modules']):
                    return False
                # 2. Ignore binary extensions
                if any(lower.endswith(ext) for ext in ['.pkl', '.pyc', '.png', '.jpg', '.jpeg', '.svg', '.eot', '.ttf', '.woff']):
                    return False
                # 3. Ignore config and env files
                if any(x in lower for x in ['.env', 'config', 'setup.', 'requirements', '.json', '.yaml', '.yml', '.gitignore', 'lock']):
                    return False
                return True
            
            valid_files = [f for f in files if is_valid_code(f)]
            source_files = valid_files if valid_files else files # Fallback if everything filtered
            
            main_file = next((f for f in source_files if "app" in f.lower() or "main" in f.lower() or "core" in f.lower()), source_files[0])
            # Only show fallback if we have no other evidence - show actual file content
            content = self.github.get_file_content(repo_url, main_file)
            if content:
                lines = [l for l in content.split('\n') if l.strip()][:15]  # First 15 non-empty lines
                snippet = "\n".join(lines)
                evidence.append(schemas.Evidence(
                    type="code_snippet",
                    ref=main_file,
                    snippet=snippet[:500],
                    source_url=f"{clean_repo_url}/blob/{default_branch}/{main_file}"
                ))
            else:
                evidence.append(schemas.Evidence(
                    type="file_ref",
                    ref=main_file,
                    snippet=f"Repository contains {len(files)} files. Main file: {main_file}",
                    source_url=f"{clean_repo_url}/blob/{default_branch}/{main_file}"
                ))
        
        # ADD REPO CONTEXT (After code snippets - shows file structure for LLM interpretation)
        readme_content = ""
        readme_file = next((f for f in files if f.lower().startswith('readme')), None)
        if readme_file:
            readme_content = self.github.get_file_content(repo_url, readme_file)
        
        context_snippet = f"Repository Structure ({len(files)} files):\n" + "\n".join(files[:100])
        if readme_content:
            context_snippet += f"\n\nREADME:\n{readme_content[:1500]}"
            
        evidence.append(schemas.Evidence(
            type="repo_context",
            ref="REPOSITORY",
            snippet=context_snippet,
            source_url=clean_repo_url
        ))
        
        # Sort evidence by ref for deterministic LLM input
        evidence.sort(key=lambda e: e.ref.lower())
        
        return evidence

    def extract_authorship_signals(self, repo_url: str, candidate_name: str, task_title: str = "") -> schemas.Evidence:
        """
        Forensic Identity Check:
        Analyzes the git log to verify if the candidate actually wrote the code.
        """
        commits = self.github.get_commit_history(repo_url, limit=50)

        # Create task-specific identifier
        task_short = task_title[:30].replace(' ', '_') if task_title else 'general'

        # Clean URL for display links (remove .git) - Ensure defined for all paths
        clean_repo_url = repo_url.rstrip('/')
        if clean_repo_url.endswith('.git'):
            clean_repo_url = clean_repo_url[:-4]
        
        if not commits:
             return schemas.Evidence(
                type="authorship_context",
                ref=f"AUTH:{task_short}",
                snippet=f"Task: {task_title}\n\nNo commit history found (Empty repo or API error). Risk: HIGH.",
                source_url=clean_repo_url
            )
            
        # Analysis
        authors = {}
        for c in commits:
            name = c.get("author_name", "Unknown")
            # Filter bots
            if "bot" in name.lower() or "unknown" in name.lower():
                continue
            authors[name] = authors.get(name, 0) + 1
            
        # Helper for normalization
        import unicodedata
        def normalize_name(text):
            return unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8').lower().strip()
            
        cand_norm = normalize_name(candidate_name)
        
        # Sort by frequency
        sorted_authors = sorted(authors.items(), key=lambda x: x[1], reverse=True)
        
        # Format for LLM - EXPLICIT COMPARISON (Task-Specific)
        snippet = f"Task: {task_title}\n\n"
        snippet += f"Candidate Name: '{candidate_name}' (Normalized: '{cand_norm}')\n"
        snippet += "Commit History Analysis (Last 50 commits):\n"
        
        match_found = False
        for auth, count in sorted_authors:
            percentage = (count / len(commits)) * 100
            auth_norm = normalize_name(auth)
            
            # Check for match here to give hint to LLM
            is_match = (cand_norm in auth_norm) or (auth_norm in cand_norm)
            match_str = " [MATCH]" if is_match else ""
            if is_match: match_found = True
            
            snippet += f"- {auth} (Norm: '{auth_norm}'): {count} commits ({percentage:.1f}%){match_str}\n"
            
        snippet += "\nINSTRUCTION: Verify if the Candidate Name matches any of the Top Authors."
        if match_found:
            snippet += "\nSYSTEM HINT: A name verify match was detected in the normalized strings."
        
        return schemas.Evidence(
            type="authorship_context",
            ref=f"AUTH:{task_short}",
            snippet=snippet,
            source_url=clean_repo_url
        )

