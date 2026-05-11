from typing import List, Dict, Any
from app.services.github import GitHubService
from app.schemas.schemas import ProofCreate

class SignalExtractor:
    def __init__(self):
        self.github = GitHubService()

    def extract_signals(self, proof: ProofCreate) -> Dict[str, Any]:
        repo_url = proof.payload.get("repo_url", "")
        if not repo_url or "github.com" not in repo_url:
            return {"valid_repo": 0.0}

        signals = {"valid_repo": 1.0}
        files, _ = self.github.get_recursive_tree(repo_url)
        
        # ===== CORE SIGNALS =====
        
        # 1. Test Presence
        has_tests = any("test" in f.lower() or "spec" in f.lower() for f in files)
        signals["tests_present"] = 1.0 if has_tests else 0.0

        # 2. Migrations / DB
        has_migrations = any("migration" in f.lower() or "alembic" in f.lower() or ".sql" in f.lower() for f in files)
        signals["migrations_present"] = 1.0 if has_migrations else 0.0
        
        # 3. Docker / Deployment
        has_docker = any("Dockerfile" in f or "docker-compose" in f or "Procfile" in f for f in files)
        signals["deployment_ready"] = 1.0 if has_docker else 0.0

        # 4. CI/CD
        has_ci = any(".github/workflows" in f for f in files)
        signals["ci_cd_present"] = 1.0 if has_ci else 0.0
        
        # ===== ML / AI SIGNALS =====
        
        # 5. Model Files
        has_model = any(f.endswith(".pkl") or f.endswith(".h5") or f.endswith(".pt") or "models/" in f for f in files)
        signals["ml_model_present"] = 1.0 if has_model else 0.0
        
        # 6. ML Libraries (check requirements.txt or setup.py)
        ml_keywords = ["scikit", "sklearn", "tensorflow", "pytorch", "keras", "xgboost", "numpy", "pandas"]
        signals["ml_libraries"] = 0.0
        for f in files:
            if "requirements" in f.lower() or "setup.py" in f.lower():
                content = self.github.get_file_content(repo_url, f)
                if any(kw in content.lower() for kw in ml_keywords):
                    signals["ml_libraries"] = 1.0
                    break
        
        # ===== WEB / API SIGNALS =====
        
        # 7. Flask / FastAPI / Django
        web_keywords = ["flask", "fastapi", "django", "@app.route", "@router"]
        signals["web_framework"] = 0.0
        for f in files:
            if f.endswith(".py"):
                content = self.github.get_file_content(repo_url, f)
                if any(kw in content.lower() for kw in web_keywords):
                    signals["web_framework"] = 1.0
                    break
        
        # 8. HTML Templates
        has_templates = any("templates/" in f or f.endswith(".html") for f in files)
        signals["frontend_present"] = 1.0 if has_templates else 0.0
        
        # 9. Static files (CSS, JS)
        has_static = any("static/" in f or f.endswith(".css") or f.endswith(".js") for f in files)
        signals["static_assets"] = 1.0 if has_static else 0.0
        
        # ===== NLP SIGNALS =====
        
        # 10. NLP Libraries
        nlp_keywords = ["nltk", "spacy", "textblob", "tfidf", "vectorizer", "tokenizer"]
        signals["nlp_present"] = 0.0
        for f in files:
            if f.endswith(".py"):
                content = self.github.get_file_content(repo_url, f)
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

        # ===== CALCULATE OVERALL SCORE =====
        
        # Weight the signals
        weighted_signals = {
            "ml_model_present": 0.2,
            "ml_libraries": 0.15,
            "web_framework": 0.15,
            "nlp_present": 0.1,
            "tests_present": 0.1,
            "deployment_ready": 0.1,
            "frontend_present": 0.1,
            "static_assets": 0.05,
            "ci_cd_present": 0.05
        }
        
        overall_score = sum(signals.get(s, 0) * w for s, w in weighted_signals.items())
        signals["overall_score"] = round(overall_score, 2)

        return signals
