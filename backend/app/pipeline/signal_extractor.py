from typing import List, Dict, Any, Optional
import re
import math
import unicodedata
from datetime import datetime, timezone
from app.services.github import GitHubService
from app.pipeline.deterministic_signals import DeterministicSignalExtractor
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

NOISE_PREFIXES = ("node_modules/", "dist/", "build/", "vendor/", ".cache/", "__pycache__/")


class SignalExtractor:
    def __init__(self):
        self.github = GitHubService()

    # =========================================================================
    # PUBLIC: extract_signals
    # =========================================================================

    def extract_signals(self, proof: schemas.ProofCreate) -> Dict[str, Any]:
        """
        Extract raw signals from the proof of work.

        Supports multiple submitted repositories (repo_urls, up to 3): each repo
        is scanned separately and the strongest repo's signal set is used for
        screening. The chosen repo is exposed as _best_repo_url so deep
        evaluation can align authorship context with it.
        """
        repo_url = proof.payload.get("repo_url", "")
        artifact_link = proof.payload.get("artifact_link")

        repo_candidates = [
            str(url).strip()
            for url in (proof.payload.get("repo_urls") or [])
            if url and "github.com" in str(url)
        ][:3]
        if not repo_candidates and repo_url and "github.com" in repo_url:
            repo_candidates = [repo_url]

        target = artifact_link or repo_url or (repo_candidates[0] if repo_candidates else "")
        if not target:
            return {"valid_repo": 0.0, "has_evidence": 0.0}

        if not repo_candidates:
            if "github.com" not in target:
                return {
                    "valid_repo": 0.0,
                    "has_evidence": 1.0,
                    "artifact_present": 1.0,
                    "context_length": len(proof.payload.get("context", "")),
                }
            return {"valid_repo": 0.0}

        best_signals: Dict[str, Any] = {"valid_repo": 0.0}
        best_score = -1.0
        for candidate_repo in repo_candidates:
            repo_signals = self._extract_repo_signals(candidate_repo, proof)
            repo_score = self._quick_signal_score(repo_signals)
            if repo_score > best_score:
                best_score = repo_score
                best_signals = repo_signals
                best_signals["_best_repo_url"] = candidate_repo

        best_signals["repos_analyzed"] = len(repo_candidates)
        return best_signals

    def _quick_signal_score(self, signals: Dict[str, Any]) -> float:
        """Deterministic weighted score used only to rank a candidate's repos."""
        from app.pipeline.scoring_engine import DEFAULT_WEIGHTS

        score = 0.0
        for name, weight in DEFAULT_WEIGHTS.items():
            value = signals.get(name, 0.0)
            if isinstance(value, dict):
                value = value.get("value", 0.0)
            try:
                score += min(max(float(value or 0.0), 0.0), 1.0) * weight
            except (TypeError, ValueError):
                continue
        return score

    def _extract_repo_signals(self, repo_url: str, proof: schemas.ProofCreate) -> Dict[str, Any]:
        """Extract the full deterministic signal set for one repository."""
        signals: Dict[str, Any] = {"valid_repo": 1.0}
        files, _ = self.github.get_recursive_tree(repo_url)

        # ── Core binary signals ───────────────────────────────────────────────
        signals["tests_present"]      = 1.0 if any(matches_any_pattern(f, TEST_PATTERNS)       for f in files) else 0.0
        signals["migrations_present"] = 1.0 if any(matches_any_pattern(f, MIGRATION_PATTERNS)  for f in files) else 0.0
        signals["deployment_ready"]   = 1.0 if any(matches_any_pattern(f, DEPLOYMENT_PATTERNS) for f in files) else 0.0
        signals["ci_cd_present"]      = 1.0 if any(matches_any_pattern(f, CI_CD_PATTERNS)      for f in files) else 0.0
        signals["ml_model_present"]   = 1.0 if any(matches_any_pattern(f, ML_MODEL_PATTERNS)   for f in files) else 0.0
        signals["frontend_present"]   = 1.0 if any(matches_any_pattern(f, FRONTEND_PATTERNS)   for f in files) else 0.0

        # ── Static assets (noise-filtered) ────────────────────────────────────
        signals["static_assets"] = 1.0 if any(
            (f.endswith(".css") or (f.endswith(".js") and not f.endswith(".min.js")))
            and not any(f.startswith(p) for p in NOISE_PREFIXES)
            for f in files
        ) else 0.0

        # ── ML library detection ──────────────────────────────────────────────
        DEP_FILES = {"requirements", "setup.py", "pyproject.toml", "pipfile", "environment.yml", "package.json"}
        ml_keywords = ["scikit", "sklearn", "tensorflow", "pytorch", "keras", "xgboost", "numpy", "pandas"]
        signals["ml_libraries"] = 0.0
        checked = 0
        for f in files:
            if checked >= 5:
                break
            fname_lower = f.lower().split("/")[-1]
            if any(dep in fname_lower for dep in DEP_FILES):
                content = self.github.get_file_content(repo_url, f)
                checked += 1
                if any(kw in content.lower() for kw in ml_keywords):
                    signals["ml_libraries"] = 1.0
                    break

        # ── NLP signals ───────────────────────────────────────────────────────
        nlp_keywords = ["nltk", "spacy", "textblob", "tfidf", "vectorizer", "tokenizer"]
        signals["nlp_present"] = 0.0
        checked = 0
        for f in files:
            if checked >= 10:
                break
            if f.endswith(".py"):
                content = self.github.get_file_content(repo_url, f)
                checked += 1
                if any(kw in content.lower() for kw in nlp_keywords):
                    signals["nlp_present"] = 1.0
                    break

        # ── Fork detection ────────────────────────────────────────────────────
        repo_meta = self.github.get_repo_metadata(repo_url)
        is_fork = repo_meta.get("is_fork", False)
        signals["is_fork"] = 1.0 if is_fork else 0.0
        if is_fork:
            signals["fork_parent"] = repo_meta.get("parent_full_name", "")

        # ── Commit history ────────────────────────────────────────────────────
        commits = self.github.get_commit_history(repo_url)
        signals["commit_count"] = min(len(commits), 50)

        author_map: Dict[str, Dict[str, Any]] = {}

        if commits:
            author_commit_counts: Dict[str, int] = {}
            for c in commits:
                key = c.get("author_email") or c.get("author_name", "unknown")
                author_commit_counts[key] = author_commit_counts.get(key, 0) + 1
                email = c.get("author_email", "").lower().strip()
                if email:
                    if email not in author_map:
                        author_map[email] = {
                            "commits": 0,
                            "lines_added": 0,
                            "name": c.get("author_name", ""),
                            "github_login": c.get("github_login", ""),
                        }
                    author_map[email]["commits"] += 1

            signals["unique_authors"] = len(author_commit_counts)

            most_recent_date = commits[0].get("date", "")
            if most_recent_date:
                try:
                    commit_dt = datetime.fromisoformat(most_recent_date.replace("Z", "+00:00"))
                    days_ago = (datetime.now(timezone.utc) - commit_dt).days
                    signals["recent_activity_score"] = round(max(0.0, math.exp(-days_ago / 90)), 3)
                except Exception:
                    signals["recent_activity_score"] = 0.3
            else:
                signals["recent_activity_score"] = 0.0

            if is_fork:
                top_author_count = max(author_commit_counts.values())
                signals["fork_is_unmodified"] = 1.0 if (top_author_count / len(commits)) > 0.70 else 0.0
            else:
                signals["fork_is_unmodified"] = 0.0
        else:
            signals["unique_authors"] = 0
            signals["recent_activity_score"] = 0.0
            signals["fork_is_unmodified"] = 0.0

        # ── Authorship fraction (deterministic) ───────────────────────────────
        signals["_author_map"] = author_map  # internal — stripped before scoring

        _candidate_info = {
            "name":            proof.payload.get("candidate_name", ""),
            "email":           proof.payload.get("email", "") or proof.payload.get("candidate_email", ""),
            "github_username": proof.payload.get("github_username", ""),
        }
        _has_identity = any(_candidate_info.values())

        if _has_identity and author_map:
            from app.pipeline.identity_verifier import (
                resolve_candidate_identities,
                calculate_authorship_from_identity,
                classify_identity_match,
            )
            _identity   = resolve_candidate_identities(_candidate_info, author_map)
            _auth_stats = calculate_authorship_from_identity(_identity, author_map)
            _identity_status = classify_identity_match(_candidate_info, _identity, author_map)
            if _identity_status["basis"] == "verified":
                signals["authorship_fraction"] = _auth_stats["authorship_fraction"]
            elif _auth_stats["authorship_fraction"] > 0:
                signals["authorship_claimed_fraction"] = _auth_stats["authorship_fraction"]
                signals["authorship_requires_manual_review"] = 1.0
            _auth_stats["identity_status"] = _identity_status
            signals["_authorship_stats"]   = _auth_stats

        # ── Deterministic signal layer ────────────────────────────────────────
        CONTENT_SCAN_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".rb", ".go", ".java"}
        CONTENT_SCAN_SKIP = NOISE_PREFIXES + ("test", "spec", ".min.")
        scannable = [
            f for f in files
            if any(f.endswith(ext) for ext in CONTENT_SCAN_EXTENSIONS)
            and not any(skip in f for skip in CONTENT_SCAN_SKIP)
        ][:20]

        file_contents: Dict[str, str] = {}
        for f in scannable:
            content = self.github.get_file_content(repo_url, f)
            if content:
                file_contents[f] = content

        readme_file = next((f for f in files if f.lower().split("/")[-1].startswith("readme")), None)
        if readme_file and readme_file not in file_contents:
            content = self.github.get_file_content(repo_url, readme_file)
            if content:
                file_contents[readme_file] = content

        det_signals = DeterministicSignalExtractor.extract_all_signals(
            files=files,
            file_contents=file_contents,
            author_map=author_map if author_map else None,
            candidate_email=None,
            candidate_aliases=None,
        )

        DET_KEY_MAP = {
            "tests_present":         "tests_present",
            "ci_present":            "ci_cd_present",
            "dockerfile_present":    "deployment_ready",
            "schema_present":        "migrations_present",
            "rate_limiting_present": "rate_limiting_present",
            "readme_quality_score":  "readme_quality_score",
        }
        for det_name, signal_key in DET_KEY_MAP.items():
            if det_name in det_signals:
                signals[signal_key] = det_signals[det_name].value

        signals["_evidence"] = {
            det_name: det_signals[det_name].evidence.to_dict()
            for det_name in det_signals
        }

        return signals

    # =========================================================================
    # PUBLIC: extract_evidence
    # =========================================================================

    def extract_evidence(
        self,
        repo_url: str,
        task_title: str,
        context: str = "",
        artifact_link: str = None,
        keywords: Optional[List[str]] = None,
    ) -> List[schemas.Evidence]:
        """
        Extract relevant evidence for LLM evaluation.

        Supports code (GitHub) and text/link artifacts.
        Uses evidence_selector for priority-ranked, keyword-anchored file
        selection. Falls back gracefully if the selector is unavailable.
        """
        evidence: List[schemas.Evidence] = []
        task_short = task_title[:30].replace(" ", "_") if task_title else "general"

        # ── Non-GitHub artifact ───────────────────────────────────────────────
        repo_is_github = bool(repo_url and "github.com" in repo_url)
        artifact_is_github = bool(artifact_link and "github.com" in artifact_link)

        # Prefer GitHub/code evidence when both a repo and a resume/artifact link
        # are present. Invite submissions include resume_url for profile context,
        # but resumes should not be evaluated as proof-of-work for code tasks.
        if not repo_is_github and artifact_is_github:
            repo_url = artifact_link
            repo_is_github = True

        target = artifact_link or repo_url
        if target and not repo_is_github:
            evidence.append(schemas.Evidence(
                type="work_artifact",
                ref=f"ARTIFACT:{task_short}",
                snippet=f"Task: {task_title}\n\nArtifact: {target}\n\nContext:\n{context[:500]}",
                source_url=target,
            ))
            return evidence

        if not repo_is_github:
            return []

        clean_repo_url = repo_url.rstrip("/")
        if clean_repo_url.endswith(".git"):
            clean_repo_url = clean_repo_url[:-4]

        files, default_branch = self.github.get_recursive_tree(repo_url)
        if not files:
            return []

        files = sorted(files, key=lambda f: f.lower())

        # ── Merge caller keywords with task-derived keywords ──────────────────
        task_keywords = list(keywords or []) + self._get_evidence_keywords(task_title)
        # Deduplicate while preserving order
        seen: set = set()
        merged_keywords: List[str] = []
        for kw in task_keywords:
            kl = kw.lower()
            if kl not in seen:
                seen.add(kl)
                merged_keywords.append(kw)

        # ── Priority-ranked selection via evidence_selector ───────────────────
        try:
            from app.pipeline.evidence_selector import priority_files, extract_snippets
            ranked = priority_files(files, max_files=25, keywords=merged_keywords)
            ranked = self._boost_ranked_files_with_content(
                repo_url=repo_url,
                files=files,
                ranked=ranked,
                keywords=merged_keywords,
            )
            use_selector = bool(ranked)
        except Exception:
            ranked = []
            use_selector = False

        # Cap code evidence items; repo context appended separately after
        MAX_CODE_EVIDENCE = 6

        if use_selector:
            for pf in ranked:
                if len(evidence) >= MAX_CODE_EVIDENCE:
                    break
                content = self.github.get_file_content(repo_url, pf.path)
                if not content:
                    continue

                # Pass merged_keywords so snippets anchor to task-relevant lines
                snippet_data = extract_snippets(
                    pf.path, content,
                    max_length=5000,
                    keywords=merged_keywords,
                )
                if not snippet_data["snippet"].strip():
                    continue

                ev_type = (
                    "repo_context"
                    if pf.category in ("manifest", "config", "readme", "documentation")
                    else "code_snippet"
                )
                evidence.append(schemas.Evidence(
                    type=ev_type,
                    ref=f"FILE:{pf.path}",
                    snippet=(
                        f"[{pf.category.upper()} | priority={pf.priority}] {pf.path}\n"
                        f"Lines {snippet_data['lines']}:\n{snippet_data['snippet']}"
                    ),
                    source_url=f"{clean_repo_url}/blob/{default_branch}/{pf.path}",
                ))

        else:
            # ── Fallback: keyword scan over priority files ────────────────────
            priority_file_list = self._get_priority_files(files, task_title)
            found_snippets: set = set()

            for f in priority_file_list:
                if len(evidence) >= MAX_CODE_EVIDENCE:
                    break
                content = self.github.get_file_content(repo_url, f)
                if not content:
                    continue

                for kw in merged_keywords:
                    if len(evidence) >= MAX_CODE_EVIDENCE:
                        break
                    if kw.lower() in content.lower():
                        lines = content.split("\n")
                        for i, line in enumerate(lines):
                            if kw.lower() in line.lower():
                                snippet_key = f"{f}:{i}"
                                if snippet_key in found_snippets:
                                    continue
                                found_snippets.add(snippet_key)
                                start = max(0, i - 2)
                                end   = min(len(lines), i + 8)
                                snippet = "\n".join(lines[start:end])
                                evidence.append(schemas.Evidence(
                                    type="code_snippet",
                                    ref=f"{f}#L{i + 1}",
                                    snippet=snippet[:1200],
                                    source_url=f"{clean_repo_url}/blob/{default_branch}/{f}#L{start+1}-L{end}",
                                ))
                                break
                        break

        # ── Name-based fallback if still empty ───────────────────────────────
        if not evidence:
            task_words = [w.lower() for w in task_title.split() if len(w) > 3]
            for f in files[:100]:
                if len(evidence) >= MAX_CODE_EVIDENCE:
                    break
                if any(word in f.lower() for word in task_words):
                    content = self.github.get_file_content(repo_url, f)
                    if content:
                        lines = [ln for ln in content.split("\n") if ln.strip() and not ln.strip().startswith("#")][:10]
                        evidence.append(schemas.Evidence(
                            type="code_snippet",
                            ref=f,
                            snippet=f"File related to '{task_title}':\n\n" + "\n".join(lines)[:1200],
                            source_url=f"{clean_repo_url}/blob/{default_branch}/{f}",
                        ))

        # ── Last-resort fallback ──────────────────────────────────────────────
        if not evidence and files:
            def _is_valid_code(f: str) -> bool:
                lower = f.lower()
                if any(x in lower for x in ["docs/", "test/", "example/", "venv", "node_modules"]):
                    return False
                if any(lower.endswith(ext) for ext in [".pkl", ".pyc", ".png", ".jpg", ".svg"]):
                    return False
                if any(x in lower for x in [".env", "config", "setup.", "requirements", ".json", ".yaml", ".yml"]):
                    return False
                return True

            valid_files = [f for f in files if _is_valid_code(f)] or files
            main_file = next(
                (f for f in valid_files if any(x in f.lower() for x in ["app", "main", "core"])),
                valid_files[0],
            )
            content = self.github.get_file_content(repo_url, main_file)
            if content:
                lines = [ln for ln in content.split("\n") if ln.strip()][:15]
                evidence.append(schemas.Evidence(
                    type="code_snippet",
                    ref=main_file,
                    snippet="\n".join(lines)[:1200],
                    source_url=f"{clean_repo_url}/blob/{default_branch}/{main_file}",
                ))
            else:
                evidence.append(schemas.Evidence(
                    type="file_ref",
                    ref=main_file,
                    snippet=f"Repository contains {len(files)} files. Main file: {main_file}",
                    source_url=f"{clean_repo_url}/blob/{default_branch}/{main_file}",
                ))

        # ── Repo structure + README context (always appended, but kept lean) ──
        # Only include README if we have fewer than 3 code evidence items
        # (avoids crowding out code snippets with a 1500-char README dump)
        # Present implementation code before manifests/README/config in the UI.
        # The LLM already buckets evidence by type, but humans should see the
        # proof-bearing files first when auditing a report.
        evidence.sort(key=lambda item: 0 if item.type == "code_snippet" else 1)

        readme_file = next((f for f in files if f.lower().split("/")[-1].startswith("readme")), None)
        readme_content = ""
        if readme_file and len(evidence) < 3:
            readme_content = self.github.get_file_content(repo_url, readme_file) or ""

        # File tree: first 60 paths, skipping noise
        clean_files = [
            f for f in files
            if not any(f.startswith(p) for p in NOISE_PREFIXES)
        ]
        structure_snippet = f"Repository Structure ({len(files)} files total):\n" + "\n".join(clean_files[:60])
        if readme_content:
            structure_snippet += f"\n\nREADME (excerpt):\n{readme_content[:800]}"

        evidence.append(schemas.Evidence(
            type="repo_context",
            ref="REPOSITORY",
            snippet=structure_snippet,
            source_url=clean_repo_url,
        ))

        return evidence

    # =========================================================================
    # PUBLIC: extract_best_evidence (multi-repo routing)
    # =========================================================================

    def extract_best_evidence(
        self,
        repo_urls: List[str],
        task_title: str,
        context: str = "",
        artifact_link: str = None,
        keywords: Optional[List[str]] = None,
    ) -> tuple:
        """
        Route each signal/task to the candidate repository with the strongest
        evidence for it.

        Candidates can submit up to 3 projects relevant to the JD. A RAG signal
        should be judged against their RAG project and an API signal against
        their API project, instead of forcing one repo to prove everything.

        Returns (chosen_repo_url, evidence). chosen_repo_url is "" when no
        GitHub repo produced evidence (artifact-only submissions).
        """
        github_repos = [
            str(url).strip() for url in (repo_urls or [])
            if url and "github.com" in str(url)
        ][:3]

        if not github_repos:
            return "", self.extract_evidence(
                repo_url="",
                task_title=task_title,
                context=context,
                artifact_link=artifact_link,
                keywords=keywords,
            )

        if len(github_repos) == 1:
            return github_repos[0], self.extract_evidence(
                repo_url=github_repos[0],
                task_title=task_title,
                context=context,
                artifact_link=artifact_link,
                keywords=keywords,
            )

        best_repo = github_repos[0]
        best_evidence: List[schemas.Evidence] = []
        best_quality = -1.0

        for repo in github_repos:
            evidence = self.extract_evidence(
                repo_url=repo,
                task_title=task_title,
                context=context,
                artifact_link=artifact_link,
                keywords=keywords,
            )
            quality = self._evidence_quality(evidence)
            if quality > best_quality:
                best_quality = quality
                best_repo = repo
                best_evidence = evidence

        return best_repo, best_evidence

    @staticmethod
    def _evidence_quality(evidence: List[schemas.Evidence]) -> float:
        """
        Score an evidence set for task relevance.

        Code snippets carry a priority marker written by the evidence selector
        ("[CATEGORY | priority=N] path"). Task-specific implementation files
        rank far above generic manifests/README, so summing those priorities is
        a reliable proxy for how well a repo proves this specific signal.
        """
        score = 0.0
        for item in evidence:
            if item.type != "code_snippet":
                continue
            match = re.search(r"priority=(\d+)", item.snippet or "")
            priority = int(match.group(1)) if match else 45
            score += priority
            if "TASK_SPECIFIC" in (item.snippet or "")[:80].upper():
                score += 40
        return score

    # =========================================================================
    # PUBLIC: extract_authorship_signals
    # =========================================================================

    def extract_authorship_signals(
        self,
        repo_url: str,
        candidate_name: str,
        task_title: str = "",
        candidate_info: Dict[str, Any] = None,
        cached_commits: List[Dict] = None,
        cached_author_map: Dict[str, Any] = None,
    ) -> schemas.Evidence:
        """
        Forensic identity check — produces an evidence snippet for the LLM.
        Uses identity_verifier for deterministic matching when identity info
        is available, embedding the numeric result in the snippet.
        """
        task_short = task_title[:30].replace(" ", "_") if task_title else "general"
        clean_repo_url = repo_url.rstrip("/")
        if clean_repo_url.endswith(".git"):
            clean_repo_url = clean_repo_url[:-4]

        commits = (
            cached_commits
            if cached_commits is not None
            else self.github.get_commit_history(repo_url, limit=50)
        )

        if not commits:
            return schemas.Evidence(
                type="authorship_context",
                ref=f"AUTH:{task_short}",
                snippet=f"Task: {task_title}\n\nNo commit history found. Risk: HIGH.",
                source_url=clean_repo_url,
            )

        # ── Build or reuse author_map ─────────────────────────────────────────
        if cached_author_map:
            author_map = cached_author_map
        else:
            author_map: Dict[str, Any] = {}
            for c in commits:
                email = c.get("author_email", "").lower().strip()
                if not email:
                    continue
                if email not in author_map:
                    author_map[email] = {
                        "commits": 0,
                        "lines_added": 0,
                        "name": c.get("author_name", ""),
                        "github_login": c.get("github_login", ""),
                    }
                author_map[email]["commits"] += 1

        # ── Deterministic identity resolution ─────────────────────────────────
        auth_stats = None
        matched_emails: List[str] = []

        _info = candidate_info or {}
        _resolved_name = (
            _info.get("candidate_name", "")
            or _info.get("name", "")
            or candidate_name
        )
        _identity_data = {
            "name":            _resolved_name,
            "email":           _info.get("email", "") or _info.get("candidate_email", ""),
            "github_username": _info.get("github_username", ""),
        }
        _has_identity = any(_identity_data.values())

        if _has_identity:
            from app.pipeline.identity_verifier import (
                resolve_candidate_identities,
                calculate_authorship_from_identity,
                classify_identity_match,
            )
            identity       = resolve_candidate_identities(_identity_data, author_map)
            auth_stats     = calculate_authorship_from_identity(identity, author_map)
            auth_stats["identity_status"] = classify_identity_match(_identity_data, identity, author_map)
            matched_emails = auth_stats.get("matched_emails", [])

        # ── Build evidence snippet ─────────────────────────────────────────────
        def _norm(text: str) -> str:
            return unicodedata.normalize("NFKD", text).encode("ASCII", "ignore").decode().lower().strip()

        authors: Dict[str, Dict[str, Any]] = {}
        for c in commits:
            name = c.get("author_name", "Unknown")
            if "bot" in name.lower():
                continue
            email = (c.get("author_email", "") or "").lower().strip()
            if name not in authors:
                authors[name] = {"count": 0, "emails": set()}
            authors[name]["count"] += 1
            if email:
                authors[name]["emails"].add(email)

        cand_norm = _norm(_resolved_name)
        sorted_authors = sorted(authors.items(), key=lambda x: x[1]["count"], reverse=True)

        snippet  = f"Task: {task_title}\n\n"
        snippet += f"Candidate: '{_resolved_name}'\n"

        if auth_stats:
            identity_status = auth_stats.get("identity_status", {})
            basis = identity_status.get("basis", "unverified")
            snippet += (
                f"Authorship Fraction (deterministic): "
                f"{auth_stats['authorship_fraction']:.1%} "
                f"({auth_stats['candidate_commits']}/{auth_stats['total_commits']} commits)\n"
                f"Matched Emails: {matched_emails or 'none'}\n"
                f"Identity Basis: {basis.replace('_', ' ')}\n"
            )

        snippet += "\nCommit Author Breakdown (last 50):\n"
        matched_email_set = {m.lower() for m in matched_emails}
        for auth, data in sorted_authors[:10]:
            count = data["count"]
            pct = (count / len(commits)) * 100
            auth_norm = _norm(auth)
            is_match = (
                auth_norm in cand_norm
                or cand_norm in auth_norm
                or bool(data["emails"] & matched_email_set)
            )
            tag = " ✓ MATCHED" if is_match else ""
            snippet += f"  {auth}: {count} commits ({pct:.1f}%){tag}\n"

        if auth_stats:
            basis = auth_stats.get("identity_status", {}).get("basis", "unverified")
            if basis != "verified" and auth_stats["authorship_fraction"] > 0:
                snippet += (
                    "\n⚠ AUTHORSHIP NEEDS REVIEW: commit metadata matches the submitted GitHub handle, "
                    "but candidate name/email did not confirm ownership."
                )
            elif auth_stats["authorship_fraction"] < 0.2:
                snippet += "\n⚠ LOW AUTHORSHIP: Candidate appears to own less than 20% of commits."
            elif auth_stats["authorship_fraction"] >= 0.5:
                snippet += "\n✓ AUTHORSHIP CONFIRMED: Candidate is a primary contributor."

        return schemas.Evidence(
            type="authorship_context",
            ref=f"AUTH:{task_short}",
            snippet=snippet,
            source_url=clean_repo_url,
        )

    # =========================================================================
    # PRIVATE helpers
    # =========================================================================

    def _get_evidence_keywords(self, task_title: str) -> List[str]:
        """
        Derive code-search keywords from a task title.

        Handles compound tasks (e.g. "GraphQL API with auth") by collecting
        matches from ALL relevant buckets, not stopping at the first match.
        Returns a deduped, ordered list of up to 20 keywords.
        """
        title_lower = task_title.lower()
        collected: List[str] = []
        task_stopwords = {
            "build", "create", "implement", "add", "with", "using", "backend",
            "frontend", "system", "service", "project", "application", "driven",
            "candidate", "outcome", "description", "signal", "code", "can",
        }
        title_tokens = [
            token for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_]{2,}", title_lower)
            if token not in task_stopwords
        ]
        token_aliases = {
            "authentication": ["auth"],
            "authorization": ["auth"],
            "limiting": ["limit"],
            "migrations": ["migration"],
            "deployment": ["deploy"],
            "retrieval": ["retrieve"],
            "openai": ["llm", "ai", "api_key", "OPENAI_API_KEY", "responses.create", "chat.completions"],
            "claude": ["anthropic", "ANTHROPIC_API_KEY"],
            "anthropic": ["claude", "ANTHROPIC_API_KEY"],
            "gemini": ["google", "genai", "google-generativeai", "GEMINI_API_KEY", "generate_content"],
            "credentials": ["api_key", "config", "settings", "env"],
            "credential": ["api_key", "config", "settings", "env"],
            "configurable": ["config", "settings", "env"],
            "client": ["client", "OpenAI", "Anthropic"],
        }
        collected.extend(title_tokens)
        for token in title_tokens:
            collected.extend(token_aliases.get(token, []))

        KEYWORD_BUCKETS = [
            (
                ["ml", "model", "train", "classification", "prediction", "machine learning",
                 "neural", "deep learning", "embedding", "nlp"],
                ["pickle", "joblib", "fit", "predict", "sklearn", "TfidfVectorizer",
                 "model.save", "train_test_split", "accuracy", "keras", "torch", "tensorflow"],
            ),
            (
                ["api", "restful", "endpoint", "backend", "server", "rest"],
                ["@app.route", "@router", "@api", "def post", "def get", "request",
                 "jsonify", "Response", "FastAPI", "Flask", "Express", "handler"],
            ),
            (
                ["database", "schema", "migration", "sql", "orm", "db"],
                ["CREATE TABLE", "Column", "Model", "Table", "ForeignKey",
                 "migrate", "db.session", "prisma", "mongoose", "sequelize"],
            ),
            (
                ["frontend", "react", "next", "vue", "angular", "component", "ui", "page"],
                ["import React", "export default", "useState", "useEffect",
                 "function", "const App", "getServerSideProps", "<div", "className"],
            ),
            (
                ["graphql", "query", "mutation", "apollo", "resolver"],
                ["gql`", "Query", "Mutation", "Resolver", "typeDefs",
                 "useQuery", "useMutation", "ApolloClient"],
            ),
            (
                ["auth", "login", "jwt", "oauth", "session", "password", "authentication"],
                ["authenticate", "login", "logout", "jwt", "token",
                 "session", "bcrypt", "hash", "verify", "password", "OAuth"],
            ),
            (
                ["deploy", "container", "docker", "kubernetes", "ci/cd", "devops"],
                ["FROM ", "RUN ", "CMD ", "EXPOSE", "docker-compose",
                 "image:", "container", "deployment", "service"],
            ),
            (
                ["test", "testing", "unit test", "integration", "spec"],
                ["def test_", "assert", "expect", "describe", "it(",
                 "pytest", "jest", "mocha", "@Test"],
            ),
            (
                ["openai", "claude", "anthropic", "gemini", "llm", "ai api", "api key",
                 "credentials", "prompt", "rag", "agent"],
                ["OpenAI", "openai", "responses.create", "chat.completions",
                 "anthropic", "Anthropic", "google.generativeai", "google-generativeai",
                 "genai", "Gemini", "generate_content", "api_key", "OPENAI_API_KEY",
                 "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "LLM", "prompt"],
            ),
        ]

        for triggers, keywords in KEYWORD_BUCKETS:
            if any(t in title_lower for t in triggers):
                collected.extend(keywords)

        # Deduplicate while preserving order
        seen: set = set()
        result: List[str] = []
        for kw in collected:
            kl = kw.lower()
            if kl not in seen:
                seen.add(kl)
                result.append(kw)

        # Generic fallback if nothing matched
        if not result:
            words = [w for w in task_title.split() if len(w) > 3]
            result = words + ["def ", "class ", "function ", "export ", "import "]

        return result[:20]

    def _boost_ranked_files_with_content(self, repo_url: str, files: List[str], ranked: List, keywords: List[str]) -> List:
        """
        Promote files whose contents directly match task keywords.

        Path-only ranking is fast but can miss provider integrations living in
        generic modules like services/llm.py. This targeted scan checks likely
        source/config files and then merges strong content hits ahead of generic
        models, seeds, or helper scripts.
        """
        from app.pipeline.evidence_selector import PriorityFile, score_content_relevance

        keyword_set = {kw.lower().strip() for kw in keywords if kw}
        provider_terms = {
            "openai", "claude", "anthropic", "gemini", "llm", "genai",
            "google-generativeai", "api_key", "credentials", "openai_api_key",
            "anthropic_api_key", "gemini_api_key",
        }
        provider_task = bool(keyword_set & provider_terms)
        code_exts = (".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java")
        manifest_names = {"requirements.txt", "pyproject.toml", "package.json", ".env.example"}
        path_hints = (
            "llm", "openai", "anthropic", "claude", "gemini", "genai",
            "prompt", "config", "settings", "secrets", "service",
        )

        def is_noise(path: str) -> bool:
            lower = path.lower()
            return any(
                noise in lower
                for noise in ("node_modules/", "dist/", "build/", "vendor/", "__pycache__/", ".git/")
            )

        candidates: List[str] = []
        for path in files:
            lower = path.lower()
            filename = lower.split("/")[-1]
            if is_noise(path):
                continue
            is_source = lower.endswith(code_exts)
            is_manifest = filename in manifest_names
            if not (is_source or is_manifest):
                continue
            if provider_task and not (is_manifest or any(hint in lower for hint in path_hints)):
                continue
            candidates.append(path)

        if not provider_task:
            ranked_paths = [item.path for item in ranked[:20]]
            generic_candidates = [
                path for path in files
                if path not in ranked_paths
                and path.lower().endswith(code_exts)
                and not is_noise(path)
            ][:20]
            candidates = list(dict.fromkeys(ranked_paths + generic_candidates))

        boosted = {}
        for path in candidates[:40]:
            content = self.github.get_file_content(repo_url, path)
            score = score_content_relevance(path, content, keywords)
            if score <= 0:
                continue
            boosted[path] = PriorityFile(
                path=path,
                priority=150 + min(score, 60),
                category="task_specific",
            )

        merged = {item.path: item for item in ranked}
        for path, item in boosted.items():
            current = merged.get(path)
            if not current or item.priority > current.priority:
                merged[path] = item

        return sorted(merged.values(), key=lambda item: item.priority, reverse=True)

    def _get_priority_files(self, files: List[str], task_title: str) -> List[str]:
        """Return files most likely to contain task implementation (fallback path)."""
        title_lower = task_title.lower()
        priority: List[str] = []

        if any(k in title_lower for k in ["frontend", "react", "next", "component", "ui", "page"]):
            priority = [f for f in files if any(x in f.lower() for x in
                ["pages/", "components/", "app/", "src/", ".tsx", ".jsx", "index.js", "app.js"])]

        elif any(k in title_lower for k in ["graphql", "query", "resolver"]):
            priority = [f for f in files if any(x in f.lower() for x in
                ["graphql", "schema", "resolver", "query", "mutation", ".gql", "apollo"])]

        elif any(k in title_lower for k in ["api", "backend", "endpoint", "server"]):
            priority = [f for f in files if any(x in f.lower() for x in
                ["app.", "main.", "server.", "routes/", "api/", "controller", "handler"])]

        elif any(k in title_lower for k in ["ml", "model", "train"]):
            priority = [f for f in files if any(x in f.lower() for x in
                ["model", "train", "predict", ".pkl", "pipeline", "classifier"])]

        elif any(k in title_lower for k in ["auth", "login", "jwt"]):
            priority = [f for f in files if any(x in f.lower() for x in
                ["auth", "login", "user", "session", "middleware", "jwt"])]

        elif any(k in title_lower for k in ["docker", "deploy", "kubernetes"]):
            priority = [f for f in files if any(x in f.lower() for x in
                ["docker", "compose", "kubernetes", "k8s", "deploy", "ci", "cd"])]

        if not priority:
            priority = [f for f in files if any(x in f.lower() for x in
                ["app.", "main.", "index.", "core.", "service.", "src/"])
                and not any(x in f.lower() for x in ["test", "spec", "node_modules", "venv"])]

        return sorted(priority[:15], key=lambda f: f.lower())
