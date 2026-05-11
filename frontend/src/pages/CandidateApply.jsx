import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
    Github, Linkedin, FileText, Send, CheckCircle, Clock,
    AlertTriangle, Building, MapPin, Briefcase, RefreshCw,
    Search, Star, GitBranch, Code, FileCode, Folder, Link2
} from 'lucide-react';
import { getInviteByToken, submitInvite, getGithubRepos, getRepoPreview, getLeetCodeStats } from '../api';

export default function CandidateApply() {
    const { token } = useParams();
    const [invite, setInvite] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [submitting, setSubmitting] = useState(false);
    const [submitted, setSubmitted] = useState(false);

    const [formData, setFormData] = useState({
        candidate_name: '',
        candidate_email: '',
        github_username: '',
        repo_url: '',
        linkedin_url: '',
        resume_url: '',
        leetcode_username: '',
        context: '',
    });

    // Repo selection state
    const [repos, setRepos] = useState([]);
    const [fetchingRepos, setFetchingRepos] = useState(false);
    const [showRepoList, setShowRepoList] = useState(false);
    const [preview, setPreview] = useState(null);
    const [leetcodeStats, setLeetcodeStats] = useState(null);

    useEffect(() => {
        async function loadInvite() {
            try {
                const data = await getInviteByToken(token);
                setInvite(data);
            } catch (err) {
                if (err.message === 'EXPIRED') {
                    setError('expired');
                } else if (err.message === 'ALREADY_USED') {
                    setError('used');
                } else {
                    setError('not_found');
                }
            } finally {
                setLoading(false);
            }
        }
        loadInvite();
    }, [token]);

    // Determine if this is a technical role
    const isTechnical = invite?.job ? (
        invite.job.category === 'Software Engineering' ||
        invite.job.category === 'Data Science & Analytics' ||
        invite.job.title?.toLowerCase().includes('engineer') ||
        invite.job.title?.toLowerCase().includes('developer') ||
        invite.job.title?.toLowerCase().includes('software')
    ) : true; // Default to technical

    // Fetch repos
    const handleFetchRepos = async () => {
        const username = formData.github_username.trim();
        if (!username) return;
        setFetchingRepos(true);
        setShowRepoList(true);
        try {
            const data = await getGithubRepos(username, invite?.job?.id);
            setRepos(data);
        } catch {
            setRepos([]);
        } finally {
            setFetchingRepos(false);
        }
    };

    const selectRepo = (repo) => {
        setFormData({ ...formData, repo_url: repo.url });
        setShowRepoList(false);
    };

    // Live preview debounce
    useEffect(() => {
        if (!isTechnical) return;
        const timeout = setTimeout(async () => {
            if (formData.repo_url && formData.repo_url.includes('github.com')) {
                try {
                    const data = await getRepoPreview(formData.repo_url);
                    setPreview(data);
                } catch { setPreview(null); }
            } else {
                setPreview(null);
            }

            if (formData.leetcode_username && formData.leetcode_username.length > 2) {
                try {
                    const stats = await getLeetCodeStats(formData.leetcode_username);
                    if (!stats.error) setLeetcodeStats(stats);
                    else setLeetcodeStats(null);
                } catch { setLeetcodeStats(null); }
            } else {
                setLeetcodeStats(null);
            }
        }, 1000);
        return () => clearTimeout(timeout);
    }, [formData.repo_url, formData.leetcode_username, isTechnical]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            await submitInvite(token, formData);
            setSubmitted(true);
        } catch (err) {
            if (err.message === 'EXPIRED') setError('expired');
            else if (err.message === 'ALREADY_USED') setError('used');
            else alert(`Error: ${err.message}`);
        } finally {
            setSubmitting(false);
        }
    };

    // ─── Loading ────────────────────────────────────────────────────────────
    if (loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 flex items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
                    <p className="mt-4 text-gray-500">Loading invite…</p>
                </div>
            </div>
        );
    }

    // ─── Error states ───────────────────────────────────────────────────────
    if (error) {
        const errorConfig = {
            expired: {
                icon: <Clock className="w-16 h-16 text-amber-400" />,
                title: 'Invite Expired',
                message: 'This invite link has expired. Please contact the recruiter for a new link.',
                bg: 'bg-amber-50',
            },
            used: {
                icon: <CheckCircle className="w-16 h-16 text-blue-400" />,
                title: 'Already Submitted',
                message: 'This invite has already been used to submit an application.',
                bg: 'bg-blue-50',
            },
            not_found: {
                icon: <AlertTriangle className="w-16 h-16 text-red-400" />,
                title: 'Invite Not Found',
                message: 'This invite link is invalid. Please check the URL or contact the recruiter.',
                bg: 'bg-red-50',
            },
        };
        const cfg = errorConfig[error] || errorConfig.not_found;

        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 flex items-center justify-center px-4">
                <div className={`max-w-md w-full ${cfg.bg} rounded-2xl p-10 text-center shadow-lg`}>
                    <div className="mx-auto mb-6">{cfg.icon}</div>
                    <h1 className="text-2xl font-bold text-gray-900 mb-3">{cfg.title}</h1>
                    <p className="text-gray-600">{cfg.message}</p>
                </div>
            </div>
        );
    }

    // ─── Success ────────────────────────────────────────────────────────────
    if (submitted) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-50 to-green-50 flex items-center justify-center px-4">
                <div className="max-w-md w-full bg-white rounded-2xl p-10 text-center shadow-xl">
                    <div className="bg-green-100 rounded-full h-20 w-20 flex items-center justify-center mx-auto mb-6">
                        <CheckCircle className="h-10 w-10 text-green-600" />
                    </div>
                    <h1 className="text-2xl font-bold text-gray-900 mb-3">Application Submitted!</h1>
                    <p className="text-gray-600 mb-2">
                        Your application for <strong>{invite?.job?.title}</strong> at <strong>{invite?.job?.company}</strong> has been received.
                    </p>
                    <p className="text-sm text-gray-500">
                        Our AI system is analyzing your submission. The recruiter will review and contact you if selected.
                    </p>
                </div>
            </div>
        );
    }

    // ─── Main form ──────────────────────────────────────────────────────────
    const job = invite?.job;

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 py-8 px-4">
            <div className="max-w-3xl mx-auto">
                {/* Header */}
                <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
                    <div className="bg-gradient-to-r from-indigo-600 to-blue-600 px-8 py-10 text-white">
                        <div className="flex items-center gap-2 text-indigo-200 text-sm mb-2">
                            <Briefcase className="w-4 h-4" />
                            <span>You've been invited to apply</span>
                        </div>
                        <h1 className="text-3xl font-bold">{job?.title}</h1>
                        <div className="mt-4 flex flex-wrap gap-4 text-sm text-indigo-200">
                            {job?.company && (
                                <span className="flex items-center gap-1">
                                    <Building className="w-4 h-4" /> {job.company}
                                </span>
                            )}
                            {job?.location && (
                                <span className="flex items-center gap-1">
                                    <MapPin className="w-4 h-4" /> {job.location}
                                </span>
                            )}
                            {job?.job_type && (
                                <span className="flex items-center gap-1">
                                    <Clock className="w-4 h-4" /> {job.job_type}
                                </span>
                            )}
                        </div>
                    </div>

                    {/* Job description */}
                    {job?.description && (
                        <div className="px-8 py-5 border-b border-gray-100 bg-gray-50">
                            <p className="text-sm text-gray-600 whitespace-pre-line">{job.description}</p>
                        </div>
                    )}

                    {/* What we look for */}
                    {job?.outcomes?.length > 0 && (
                        <div className="px-8 py-5 border-b border-gray-100">
                            <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-3">What We're Looking For</h3>
                            <div className="grid gap-2">
                                {job.outcomes.map((o) => (
                                    <div key={o.id} className="flex items-start gap-2 text-sm">
                                        <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                                        <div>
                                            <span className="font-medium text-gray-800">{o.title}</span>
                                            {o.description && (
                                                <span className="text-gray-500 ml-1">— {o.description}</span>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Form */}
                    <form onSubmit={handleSubmit} className="px-8 py-8 space-y-6">
                        <div className="p-4 bg-indigo-50 rounded-lg border border-indigo-100 text-sm text-indigo-800">
                            <strong>How it works:</strong> Submit your profile and proof of work. Our AI system evaluates your actual capabilities — not just your resume.
                        </div>

                        {/* Personal Info */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Full Name <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="text"
                                    required
                                    placeholder="John Doe"
                                    value={formData.candidate_name}
                                    onChange={(e) => setFormData({ ...formData, candidate_name: e.target.value })}
                                    className="w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Email <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="email"
                                    required
                                    placeholder="john@example.com"
                                    value={formData.candidate_email}
                                    onChange={(e) => setFormData({ ...formData, candidate_email: e.target.value })}
                                    className="w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
                                />
                            </div>
                        </div>

                        {/* LinkedIn & Resume */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    <span className="flex items-center gap-1.5"><Linkedin className="w-4 h-4 text-blue-600" /> LinkedIn URL</span>
                                </label>
                                <input
                                    type="url"
                                    placeholder="https://linkedin.com/in/johndoe"
                                    value={formData.linkedin_url}
                                    onChange={(e) => setFormData({ ...formData, linkedin_url: e.target.value })}
                                    className="w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    <span className="flex items-center gap-1.5"><Link2 className="w-4 h-4 text-gray-500" /> Resume Link</span>
                                </label>
                                <input
                                    type="url"
                                    placeholder="https://drive.google.com/..."
                                    value={formData.resume_url}
                                    onChange={(e) => setFormData({ ...formData, resume_url: e.target.value })}
                                    className="w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
                                />
                            </div>
                        </div>

                        {/* GitHub section */}
                        <div className="border-t border-gray-100 pt-6">
                            <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-4 flex items-center gap-2">
                                <Github className="w-4 h-4" /> Proof of Work
                            </h3>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">GitHub Username</label>
                                    <div className="flex gap-2">
                                        <input
                                            type="text"
                                            placeholder="octocat"
                                            value={formData.github_username}
                                            onChange={(e) => setFormData({ ...formData, github_username: e.target.value })}
                                            className="flex-1 px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
                                        />
                                        <button
                                            type="button"
                                            onClick={handleFetchRepos}
                                            disabled={fetchingRepos || !formData.github_username}
                                            className="px-3 py-2.5 rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-40 transition-colors"
                                            title="Find best repos"
                                        >
                                            {fetchingRepos ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                                        </button>
                                    </div>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Repository URL {isTechnical && <span className="text-red-500">*</span>}
                                    </label>
                                    <div className="relative">
                                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                            <Github className="h-4 w-4 text-gray-400" />
                                        </div>
                                        <input
                                            type="url"
                                            required={isTechnical}
                                            placeholder="https://github.com/username/project"
                                            value={formData.repo_url}
                                            onChange={(e) => setFormData({ ...formData, repo_url: e.target.value })}
                                            className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
                                        />
                                    </div>
                                </div>
                            </div>

                            {/* Repo picker dropdown */}
                            {showRepoList && (
                                <div className="mt-3 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                                    <div className="p-2 border-b border-gray-100 bg-gray-50 flex justify-between items-center sticky top-0 z-10">
                                        <span className="text-xs font-bold text-gray-500 uppercase">Select a Repository</span>
                                        <button type="button" onClick={() => setShowRepoList(false)} className="text-xs text-indigo-600 hover:underline">Close</button>
                                    </div>
                                    {repos.length === 0 ? (
                                        <div className="p-4 text-center text-sm text-gray-500">
                                            {fetchingRepos ? "Analyzing repositories…" : "No relevant repositories found."}
                                        </div>
                                    ) : (
                                        <ul className="divide-y divide-gray-100">
                                            {repos.map((repo) => (
                                                <li key={repo.url} onClick={() => selectRepo(repo)} className="p-3 hover:bg-indigo-50 cursor-pointer transition-colors">
                                                    <div className="flex justify-between items-start">
                                                        <div className="font-medium text-gray-900 flex items-center gap-2">
                                                            {repo.repo}
                                                            <span className="text-xs font-normal text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
                                                                Score: {(repo.score * 10).toFixed(1)}
                                                            </span>
                                                        </div>
                                                        {repo.language && (
                                                            <span className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full">{repo.language}</span>
                                                        )}
                                                    </div>
                                                    <div className="flex gap-4 mt-1 text-xs text-gray-500">
                                                        <span className="flex items-center gap-1"><Star className="w-3 h-3" /> Match</span>
                                                        {repo.last_commit_date && (
                                                            <span className="flex items-center gap-1">
                                                                <GitBranch className="w-3 h-3" /> {new Date(repo.last_commit_date).toLocaleDateString()}
                                                            </span>
                                                        )}
                                                    </div>
                                                </li>
                                            ))}
                                        </ul>
                                    )}
                                </div>
                            )}

                            {/* Repo preview */}
                            {preview && (
                                <div className="mt-3 bg-gray-50 rounded-lg border border-gray-200 p-4">
                                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Live Preview</h4>
                                    <div className="flex items-center gap-3 mb-3">
                                        <Folder className="h-5 w-5 text-indigo-600" />
                                        <span className="font-medium text-gray-900">{preview.name}</span>
                                    </div>
                                    <div className="space-y-1 pl-8 border-l-2 border-gray-200 ml-2.5">
                                        {preview.files?.map((file, i) => (
                                            <div key={i} className="flex items-center gap-2 text-sm text-gray-600">
                                                <FileCode className="h-3 w-3 text-gray-400" /> {file}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* LeetCode */}
                            <div className="mt-4">
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    <span className="flex items-center gap-1.5"><Code className="w-4 h-4 text-amber-500" /> LeetCode Username (Optional)</span>
                                </label>
                                <input
                                    type="text"
                                    placeholder="leetcode_user"
                                    value={formData.leetcode_username}
                                    onChange={(e) => setFormData({ ...formData, leetcode_username: e.target.value })}
                                    className="w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
                                />
                            </div>
                            {leetcodeStats && (
                                <div className="mt-2 bg-indigo-50 rounded-lg p-3 border border-indigo-200 flex items-center gap-4">
                                    <div className="bg-indigo-100 p-2 rounded-full">
                                        <FileCode className="h-5 w-5 text-indigo-600" />
                                    </div>
                                    <div>
                                        <div className="text-sm font-bold text-gray-900">{leetcodeStats.total_solved} Solved</div>
                                        <div className="text-xs text-gray-500 flex gap-2">
                                            <span className="text-green-600 font-medium">Easy: {leetcodeStats.easy_solved}</span>
                                            <span className="text-yellow-600 font-medium">Med: {leetcodeStats.medium_solved}</span>
                                            <span className="text-red-600 font-medium">Hard: {leetcodeStats.hard_solved}</span>
                                        </div>
                                    </div>
                                    <div className="ml-auto text-right">
                                        <div className="text-xs font-bold text-gray-500 uppercase tracking-wider">Acceptance</div>
                                        <div className="text-sm font-mono text-gray-900">{leetcodeStats.acceptance_rate}%</div>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Additional Context */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Additional Context / Notes</label>
                            <textarea
                                rows={4}
                                placeholder="Describe the architecture, trade-offs, and key features of your work…"
                                value={formData.context}
                                onChange={(e) => setFormData({ ...formData, context: e.target.value })}
                                className="w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all resize-none"
                            />
                        </div>

                        {/* Submit */}
                        <button
                            type="submit"
                            disabled={submitting}
                            className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-indigo-600 to-blue-600 text-white font-semibold rounded-xl hover:from-indigo-700 hover:to-blue-700 disabled:opacity-50 transition-all shadow-lg shadow-indigo-200"
                        >
                            {submitting ? (
                                <><RefreshCw className="w-5 h-5 animate-spin" /> Submitting…</>
                            ) : (
                                <><Send className="w-5 h-5" /> Submit Application</>
                            )}
                        </button>
                    </form>
                </div>

                {/* Footer */}
                <p className="text-center text-xs text-gray-400 mt-6">
                    Powered by <span className="font-semibold text-gray-500">SignalStack</span> — AI-driven hiring
                </p>
            </div>
        </div>
    );
}
