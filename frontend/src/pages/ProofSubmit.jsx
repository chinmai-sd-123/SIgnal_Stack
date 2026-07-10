import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Github, FileCode, Folder, CheckCircle, Code, RefreshCw, ArrowRight, Search, Star, GitBranch } from 'lucide-react';
import { getOutcome, submitProof, getRepoPreview, getGithubRepos, getLeetCodeStats } from '../api';

export default function ProofSubmit() {
    const { outcomeId } = useParams();
    const [outcome, setOutcome] = useState(null);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [submitted, setSubmitted] = useState(false);

    const [formData, setFormData] = useState({
        candidate_id: '',
        github_username: '',
        repo_url: '',
        leetcode_username: '',
        context: ''
    });

    // Repo Selection State
    const [repos, setRepos] = useState([]);
    const [fetchingRepos, setFetchingRepos] = useState(false);
    const [showRepoList, setShowRepoList] = useState(false);
    const [repoSearch, setRepoSearch] = useState('');

    const handleFetchRepos = async () => {
        const username = formData.github_username.trim();
        if (!username) {
            alert("Please enter a GitHub username first.");
            return;
        }
        setFetchingRepos(true);
        setShowRepoList(true);
        setRepoSearch('');
        try {
            const data = await getGithubRepos(username, outcomeId);
            setRepos(data);
        } catch (error) {
            console.error("Failed to fetch repos", error);
            setRepos([]);
        } finally {
            setFetchingRepos(false);
        }
    };

    const selectRepo = (repo) => {
        setFormData({ ...formData, repo_url: repo.url });
        setShowRepoList(false);
    };

    const isSweRole = outcome ? (
        outcome.category === 'Software Engineering' ||
        outcome.category === 'Data Science & Analytics' ||
        outcome.proof_type === 'github' ||
        outcome.title.toLowerCase().includes('software') ||
        outcome.title.toLowerCase().includes('engineer') ||
        outcome.title.toLowerCase().includes('developer')
    ) : false;

    const isArtifactType = !isSweRole; // Use this for cleaner logic

    const filteredRepos = repos.filter((repo) => {
        const query = repoSearch.trim().toLowerCase();
        if (!query) return true;
        return [repo.repo, repo.owner, repo.language, repo.url]
            .filter(Boolean)
            .some((value) => String(value).toLowerCase().includes(query));
    });
    const topRepos = filteredRepos.slice(0, 5);
    const otherRepos = filteredRepos.slice(5);
    const renderRepoItem = (repo) => (
        <li
            key={repo.url}
            onClick={() => selectRepo(repo)}
            className="p-3 hover:bg-primary-soft cursor-pointer transition-colors"
        >
            <div className="flex justify-between items-start gap-3">
                <div className="font-medium text-gray-900 flex items-center gap-2 min-w-0">
                    <span className="truncate">{repo.repo}</span>
                    <span className="text-xs font-normal text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded border border-gray-200 flex-shrink-0">
                        Score: {(repo.score * 10).toFixed(1)}
                    </span>
                </div>
                {repo.language && (
                    <span className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full flex-shrink-0">
                        {repo.language}
                    </span>
                )}
            </div>
            <div className="flex gap-4 mt-1 text-xs text-gray-500">
                <span className="flex items-center gap-1">
                    <Star className="w-3 h-3" /> Match
                </span>
                {repo.last_commit_date && (
                    <span className="flex items-center gap-1">
                        <GitBranch className="w-3 h-3" />
                        {new Date(repo.last_commit_date).toLocaleDateString()}
                    </span>
                )}
            </div>
        </li>
    );

    // Mock Live Preview State
    const [preview, setPreview] = useState(null);
    const [leetcodeStats, setLeetCodeStats] = useState(null);
    const [leetcodeError, setLeetCodeError] = useState(null);

    useEffect(() => {
        async function loadOutcome() {
            try {
                const data = await getOutcome(outcomeId);
                setOutcome(data);
            } catch (error) {
                console.error("Failed to load outcome", error);
            } finally {
                setLoading(false);
            }
        }
        loadOutcome();
    }, [outcomeId]);

    useEffect(() => {
        if (!isSweRole) return; // Skip for functional roles

        const fetchPreview = async () => {
            if (formData.repo_url && formData.repo_url.includes('github.com')) {
                try {
                    const data = await getRepoPreview(formData.repo_url);
                    setPreview(data);
                } catch (error) {
                    console.error("Failed to fetch preview", error);
                    setPreview(null);
                }
            } else {
                setPreview(null);
            }
        };

        const fetchLeetCode = async () => {
            if (formData.leetcode_username && formData.leetcode_username.length > 2) {
                try {
                    const stats = await getLeetCodeStats(formData.leetcode_username);
                    if (!stats.error) {
                        setLeetCodeStats(stats);
                        setLeetCodeError(null);
                    } else {
                        setLeetCodeStats(null);
                        setLeetCodeError(stats.error);
                    }
                } catch (error) {
                    console.error("Failed to fetch leetcode stats", error);
                    setLeetCodeStats(null);
                    setLeetCodeError('Could not verify LeetCode profile right now.');
                }
            } else {
                setLeetCodeStats(null);
                setLeetCodeError(null);
            }
        };

        const timeoutId = setTimeout(() => {
            fetchPreview();
            fetchLeetCode();
        }, 1000); // Debounce 1s
        return () => clearTimeout(timeoutId);
    }, [formData.repo_url, formData.leetcode_username, isSweRole]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            await submitProof({
                job_id: outcomeId,
                candidate_id: formData.candidate_id || `cand_${Math.random().toString(36).substr(2, 5)}`,
                type: isSweRole ? 'github' : 'work_artifact',
                payload: {
                    repo_url: isSweRole ? formData.repo_url : undefined,
                    leetcode_username: isSweRole ? formData.leetcode_username : undefined,
                    artifact_link: !isSweRole ? formData.repo_url : undefined, // Reuse repo_url field or add new one? reused for simplicity in form state but sent cleanly
                    context: formData.context
                }
            });
            setSubmitted(true);
        } catch (error) {
            alert(`Error: ${error.message}`);
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) return (
        <div className="max-w-3xl mx-auto space-y-4 p-8" aria-busy="true" aria-label="Loading">
            <div className="skeleton-title" style={{ width: '40%' }} />
            <div className="skeleton-card" style={{ height: '260px' }} />
        </div>
    );
    if (!outcome) return <div className="p-8 text-center">Outcome not found.</div>;

    if (submitted) {
        return (
            <div className="max-w-2xl mx-auto mt-16 text-center">
                <div className="bg-green-100 rounded-full h-20 w-20 flex items-center justify-center mx-auto mb-6">
                    <CheckCircle className="h-10 w-10 text-green-600" />
                </div>
                <h2 className="heading-1 mb-4">Proof Submitted</h2>
                <p className="text-gray-600">
                    Your work has been received and is being processed by SignalStack.
                    You will be notified if you are selected for an interview.
                </p>
            </div>
        );
    }

    return (
        <div className="max-w-3xl mx-auto py-12 px-4">
            <div className="card shadow-xl rounded-2xl overflow-hidden border border-gray-100 p-0">
                <div className="bg-primary px-8 py-10 text-white">
                    <h1 className="text-3xl font-bold">{outcome.title}</h1>
                    <p className="mt-2 text-primary-soft opacity-90">{outcome.description}</p>
                </div>

                <div className="p-8">
                    <div className="mb-8 p-4 bg-yellow-50 rounded-lg border border-yellow-100 text-yellow-800 text-sm">
                        <strong>Instruction:</strong> Submit proof of work relevant to this outcome.
                        We evaluate {isSweRole ? "code" : "operational artifacts"}, not resumes.
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-6">

                        {/* Candidate ID */}
                        <div>
                            <label className="input-label">
                                Candidate ID <span className="text-red-500">*</span>
                            </label>
                            <input
                                type="text"
                                required
                                placeholder="your-unique-handle"
                                value={formData.candidate_id}
                                onChange={(e) => setFormData({ ...formData, candidate_id: e.target.value })}
                                className="input-field"
                            />
                        </div>

                        {/* Dynamic Fields based on Role Type */}
                        {!isArtifactType ? (
                            // TECHNICAL ROLE (GitHub + LeetCode)
                            <>
                                {/* GitHub Username & Repo Selection */}
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div>
                                        <label className="input-label">
                                            GitHub Username
                                        </label>
                                        <div className="flex gap-2">
                                            <input
                                                type="text"
                                                placeholder="octocat"
                                                value={formData.github_username}
                                                onChange={(e) => setFormData({ ...formData, github_username: e.target.value })}
                                                className="input-field"
                                            />
                                            <button
                                                type="button"
                                                onClick={handleFetchRepos}
                                                disabled={fetchingRepos || !formData.github_username}
                                                className="btn btn-secondary px-3"
                                                title="Fetch Repos"
                                            >
                                                {fetchingRepos ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                                            </button>
                                        </div>
                                    </div>

                                    <div>
                                        <label className="input-label">
                                            GitHub Repository URL <span className="text-red-500">*</span>
                                        </label>
                                        <div className="relative rounded-md shadow-sm">
                                            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                                <Github className="h-5 w-5 text-gray-400" />
                                            </div>
                                            <input
                                                type="url"
                                                required
                                                placeholder="https://github.com/username/project"
                                                value={formData.repo_url}
                                                onChange={(e) => setFormData({ ...formData, repo_url: e.target.value })}
                                                className="input-field pl-10"
                                            />
                                        </div>
                                    </div>
                                </div>

                                {/* Repo Selection List */}
                                {showRepoList && (
                                    <div className="bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto animate-fade-in custom-scrollbar">
                                        <div className="p-2 border-b border-gray-100 bg-gray-50 sticky top-0 z-10 space-y-2">
                                            <div className="flex justify-between items-center">
                                                <span className="text-xs font-bold text-gray-500 uppercase">Select a Repository</span>
                                                <button onClick={() => setShowRepoList(false)} className="text-xs text-primary hover:underline">Close</button>
                                            </div>
                                            <div className="relative">
                                                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
                                                <input
                                                    type="search"
                                                    value={repoSearch}
                                                    onChange={(e) => setRepoSearch(e.target.value)}
                                                    placeholder="Search repositories"
                                                    className="w-full pl-8 pr-3 py-2 rounded-lg border border-gray-200 bg-white text-xs outline-none focus:border-primary"
                                                />
                                            </div>
                                        </div>
                                        {repos.length === 0 ? (
                                            <div className="p-4 text-center text-sm text-gray-500">
                                                {fetchingRepos ? "Analyzing repositories..." : "No relevant repositories found."}
                                            </div>
                                        ) : filteredRepos.length === 0 ? (
                                            <div className="p-4 text-center text-sm text-gray-500">
                                                No repositories match.
                                            </div>
                                        ) : (
                                            <>
                                                <div className="px-3 py-2 text-[11px] font-bold uppercase tracking-wide text-primary bg-primary-soft">Top Matches</div>
                                                <ul className="divide-y divide-gray-100">{topRepos.map(renderRepoItem)}</ul>
                                                {otherRepos.length > 0 && (
                                                    <>
                                                        <div className="px-3 py-2 text-[11px] font-bold uppercase tracking-wide text-gray-500 bg-gray-50">All Repositories</div>
                                                        <ul className="divide-y divide-gray-100">{otherRepos.map(renderRepoItem)}</ul>
                                                    </>
                                                )}
                                            </>
                                        )}
                                    </div>
                                )}

                                {preview && (
                                    <div className="bg-gray-50 rounded-lg border border-gray-200 p-4 animate-fade-in">
                                        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Live Preview</h4>
                                        <div className="flex items-center gap-3 mb-3">
                                            <Folder className="h-5 w-5 text-primary" />
                                            <span className="font-medium text-gray-900">{preview.name}</span>
                                        </div>
                                        <div className="space-y-1 pl-8 border-l-2 border-gray-200 ml-2.5">
                                            {preview.files.map((file, i) => (
                                                <div key={i} className="flex items-center gap-2 text-sm text-gray-600">
                                                    <FileCode className="h-3 w-3 text-gray-400" />
                                                    {file}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                <div>
                                    <label className="input-label">
                                        LeetCode Username (Optional)
                                    </label>
                                    <div className="relative rounded-md shadow-sm">
                                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                            <Code className="h-5 w-5 text-gray-400" />
                                        </div>
                                        <input
                                            type="text"
                                            placeholder="leetcode_user"
                                            value={formData.leetcode_username}
                                            onChange={(e) => setFormData({ ...formData, leetcode_username: e.target.value })}
                                            className="input-field pl-10"
                                        />
                                    </div>
                                    {leetcodeError && (
                                        <p className="mt-1.5 text-xs text-red-500">{leetcodeError}</p>
                                    )}
                                </div>
                                {leetcodeStats && (
                                    <div className="mt-2 bg-primary-soft rounded-lg p-3 border border-indigo-200 flex items-center gap-4 animate-fade-in">
                                        <div className="bg-indigo-100 p-2 rounded-full">
                                            <FileCode className="h-5 w-5 text-primary-hover" />
                                        </div>
                                        <div>
                                            <div className="text-sm font-bold text-gray-900">
                                                {leetcodeStats.total_solved} Solved
                                            </div>
                                            <div className="text-xs text-gray-500 flex gap-2">
                                                <span className="text-green-600 font-medium">Easy: {leetcodeStats.easy_solved}</span>
                                                <span className="text-yellow-600 font-medium">Med: {leetcodeStats.medium_solved}</span>
                                                <span className="text-red-600 font-medium">Hard: {leetcodeStats.hard_solved}</span>
                                            </div>
                                        </div>
                                        <div className="ml-auto text-right">
                                            <div className="text-xs font-bold text-gray-500 uppercase tracking-wider">Acceptance</div>
                                            <div className="text-sm font-mono text-gray-900">{leetcodeStats.acceptance_rate ?? 'N/A'}{leetcodeStats.acceptance_rate != null ? '%' : ''}</div>
                                        </div>
                                    </div>
                                )}
                            </>
                        ) : (
                            // NON-TECHNICAL ROLE (Artifact Link)
                            <div>
                                <label className="input-label">
                                    Link to Work Artifact (Google Doc, Notion, Public URL) <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="url"
                                    required
                                    placeholder="https://docs.google.com/document/d/..."
                                    value={formData.repo_url} // We reuse repo_url for artifact_link in state
                                    onChange={(e) => setFormData({ ...formData, repo_url: e.target.value })}
                                    className="input-field"
                                />
                                <p className="mt-1 text-xs text-gray-500">
                                    Please ensure the link is publicly accessible or shared with 'view' access.
                                </p>
                            </div>
                        )}

                        {/* Additional Context - Shared */}
                        <div>
                            <label className="input-label">
                                Additional Context / Notes
                            </label>
                            <textarea
                                rows={4}
                                placeholder={!isArtifactType ?
                                    "Describe the architecture, trade-offs, and key features..." :
                                    "Explain the context of this document, your specific role, and value delivered..."
                                }
                                value={formData.context}
                                onChange={(e) => setFormData({ ...formData, context: e.target.value })}
                                className="input-field"
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={submitting}
                            className="btn btn-primary w-full justify-center"
                        >
                            {submitting ? (
                                <>
                                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                                    Submitting...
                                </>
                            ) : (
                                <>
                                    Submit Proof for Analysis <ArrowRight className="ml-2 w-4 h-4" />
                                </>
                            )}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}

