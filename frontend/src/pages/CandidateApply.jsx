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
        candidate_name: '', candidate_email: '', github_username: '',
        repo_url: '', linkedin_url: '', resume_url: '',
        leetcode_username: '', context: '',
    });

    const [repos, setRepos] = useState([]);
    const [fetchingRepos, setFetchingRepos] = useState(false);
    const [showRepoList, setShowRepoList] = useState(false);
    const [preview, setPreview] = useState(null);
    const [leetcodeStats, setLeetcodeStats] = useState(null);
    const [leetcodeError, setLeetcodeError] = useState(null);

    useEffect(() => {
        async function loadInvite() {
            try {
                const data = await getInviteByToken(token);
                setInvite(data);
            } catch (err) {
                if (err.message === 'EXPIRED') setError('expired');
                else if (err.message === 'CLOSED') setError('closed');
                else if (err.message === 'SERVER_ERROR') setError('server_error');
                else setError('not_found');
            } finally { setLoading(false); }
        }
        loadInvite();
    }, [token]);

    const isTechnical = invite?.job ? (
        invite.job.category === 'Software Engineering' ||
        invite.job.category === 'Data Science & Analytics' ||
        invite.job.title?.toLowerCase().includes('engineer') ||
        invite.job.title?.toLowerCase().includes('developer') ||
        invite.job.title?.toLowerCase().includes('software')
    ) : true;

    const handleFetchRepos = async () => {
        const username = formData.github_username.trim();
        if (!username) return;
        setFetchingRepos(true); setShowRepoList(true);
        try { setRepos(await getGithubRepos(username, invite?.job?.id)); }
        catch { setRepos([]); }
        finally { setFetchingRepos(false); }
    };

    const selectRepo = (repo) => {
        setFormData({ ...formData, repo_url: repo.url });
        setShowRepoList(false);
    };

    useEffect(() => {
        if (!isTechnical) return;
        const timeout = setTimeout(async () => {
            if (formData.repo_url && formData.repo_url.includes('github.com')) {
                try { setPreview(await getRepoPreview(formData.repo_url)); }
                catch { setPreview(null); }
            } else { setPreview(null); }
            if (formData.leetcode_username && formData.leetcode_username.length > 2) {
                try {
                    const stats = await getLeetCodeStats(formData.leetcode_username);
                    setLeetcodeStats(!stats.error ? stats : null);
                    setLeetcodeError(stats.error || null);
                } catch {
                    setLeetcodeStats(null);
                    setLeetcodeError('Could not verify LeetCode profile right now.');
                }
            } else {
                setLeetcodeStats(null);
                setLeetcodeError(null);
            }
        }, 1000);
        return () => clearTimeout(timeout);
    }, [formData.repo_url, formData.leetcode_username, isTechnical]);

    const handleSubmit = async (e) => {
        e.preventDefault(); setSubmitting(true);
        try { await submitInvite(token, formData); setSubmitted(true); }
        catch (err) {
            if (err.message === 'EXPIRED') setError('expired');
            else if (err.message === 'ALREADY_USED') setError('closed');
            else if (err.message.includes('already submitted')) setError('duplicate');
            else alert(`Error: ${err.message}`);
        } finally { setSubmitting(false); }
    };

    const inputClass = "w-full px-4 py-3 rounded-xl border-[1.5px] border-[#e6e1d7] bg-[#fffdf8] focus:ring-2 focus:ring-[#0b5f66]/20 focus:border-[#0b5f66] outline-none transition-all text-sm";

    // ─── Loading ────────────────────────────────────────
    if (loading) return (
        <div className="min-h-screen flex items-center justify-center" style={{ background: 'linear-gradient(180deg,#f7f5f0,#f2eee6)' }}>
            <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#0b5f66] mx-auto"></div>
                <p className="mt-4 text-[#475569] font-['Sora']">Loading invite…</p>
            </div>
        </div>
    );

    // ─── Error states ───────────────────────────────────
    if (error) {
        const cfg = {
            expired: { icon: <Clock className="w-14 h-14 text-[#c9a227]" />, title: 'Invite Expired', msg: 'This invite link has expired. Please contact the recruiter for a new link.', accent: '#c9a227' },
            closed: { icon: <AlertTriangle className="w-14 h-14 text-[#c9a227]" />, title: 'Applications Closed', msg: 'This invite link is no longer accepting applications.', accent: '#c9a227' },
            duplicate: { icon: <CheckCircle className="w-14 h-14 text-[#0b5f66]" />, title: 'Already Applied', msg: 'You have already submitted an application with this email address.', accent: '#0b5f66' },
            server_error: { icon: <AlertTriangle className="w-14 h-14 text-red-400" />, title: 'Application Link Temporarily Unavailable', msg: 'We could not load this invite because the server returned an error. Please try again shortly or contact the recruiter.', accent: '#EF4444' },
            not_found: { icon: <AlertTriangle className="w-14 h-14 text-red-400" />, title: 'Invite Not Found', msg: 'This invite link is invalid. Please check the URL or contact the recruiter.', accent: '#EF4444' },
        }[error] || { icon: <AlertTriangle className="w-14 h-14 text-red-400" />, title: 'Error', msg: 'Something went wrong.', accent: '#EF4444' };

        return (
            <div className="min-h-screen flex items-center justify-center px-4" style={{ background: 'linear-gradient(180deg,#f7f5f0,#f2eee6)' }}>
                <div className="max-w-md w-full rounded-2xl p-10 text-center border border-[#e6e1d7]" style={{ background: 'rgba(255,253,248,0.92)', boxShadow: '0 10px 30px rgba(15,23,42,0.08)' }}>
                    <div className="mx-auto mb-5">{cfg.icon}</div>
                    <h1 className="text-2xl font-bold text-[#0f172a] mb-3 font-['Sora']">{cfg.title}</h1>
                    <p className="text-[#475569]">{cfg.msg}</p>
                </div>
            </div>
        );
    }

    // ─── Success ────────────────────────────────────────
    if (submitted) return (
        <div className="min-h-screen flex items-center justify-center px-4" style={{ background: 'linear-gradient(180deg,#f7f5f0,#f2eee6)' }}>
            <div className="max-w-md w-full rounded-2xl p-10 text-center border border-[#e6e1d7]" style={{ background: 'rgba(255,253,248,0.92)', boxShadow: '0 18px 44px rgba(15,23,42,0.14)' }}>
                <div className="rounded-full h-20 w-20 flex items-center justify-center mx-auto mb-6" style={{ background: 'rgba(11,95,102,0.1)' }}>
                    <CheckCircle className="h-10 w-10 text-[#0b5f66]" />
                </div>
                <h1 className="text-2xl font-bold text-[#0f172a] mb-3 font-['Sora']">Application Submitted!</h1>
                <p className="text-[#475569] mb-2">
                    Your application for <strong>{invite?.job?.title}</strong> at <strong>{invite?.job?.company}</strong> has been received.
                </p>
                <p className="text-sm text-[#94a3b8]">Our AI system is analyzing your submission. The recruiter will review and contact you if selected.</p>
            </div>
        </div>
    );

    // ─── Main form ──────────────────────────────────────
    const job = invite?.job;

    return (
        <div className="min-h-screen py-8 px-4 font-['Sora']" style={{
            background: 'linear-gradient(180deg, #f7f5f0 0%, #f2eee6 100%)',
            backgroundImage: 'radial-gradient(1200px 600px at 10% -10%, rgba(201,162,39,0.08), transparent 60%), radial-gradient(900px 500px at 90% 0%, rgba(11,95,102,0.08), transparent 60%)',
        }}>
            <div className="max-w-3xl mx-auto">
                {/* Card */}
                <div className="rounded-2xl overflow-hidden border border-[#e6e1d7]" style={{ background: 'rgba(255,253,248,0.92)', backdropFilter: 'blur(20px)', boxShadow: '0 10px 30px rgba(15,23,42,0.08)' }}>

                    {/* Hero Header */}
                    <div className="px-8 py-10 text-white relative overflow-hidden" style={{ background: 'linear-gradient(135deg, #0b5f66 0%, #0f766e 50%, #c9a227 110%)' }}>
                        <div className="absolute top-[-50%] left-[-50%] w-[200%] h-[200%] pointer-events-none" style={{ background: 'radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 60%)', animation: 'float 6s ease-in-out infinite' }}></div>
                        <div className="relative z-10">
                            <div className="flex items-center gap-2 text-white/70 text-sm mb-2">
                                <Briefcase className="w-4 h-4" />
                                <span>You've been invited to apply</span>
                            </div>
                            <h1 className="text-3xl font-bold">{job?.title}</h1>
                            <div className="mt-4 flex flex-wrap gap-4 text-sm text-white/70">
                                {job?.company && <span className="flex items-center gap-1"><Building className="w-4 h-4" /> {job.company}</span>}
                                {job?.location && <span className="flex items-center gap-1"><MapPin className="w-4 h-4" /> {job.location}</span>}
                                {job?.job_type && <span className="flex items-center gap-1"><Clock className="w-4 h-4" /> {job.job_type}</span>}
                            </div>
                        </div>
                    </div>

                    {/* Job description */}
                    {job?.description && (
                        <div className="px-8 py-5 border-b border-[#e6e1d7]" style={{ background: 'rgba(247,245,240,0.5)' }}>
                            <p className="text-sm text-[#475569] whitespace-pre-line">{job.description}</p>
                        </div>
                    )}

                    {/* Outcomes */}
                    {job?.outcomes?.length > 0 && (
                        <div className="px-8 py-5 border-b border-[#e6e1d7]">
                            <h3 className="text-sm font-semibold text-[#0f172a] uppercase tracking-wider mb-3">What We're Looking For</h3>
                            <div className="grid gap-2">
                                {job.outcomes.map((o) => (
                                    <div key={o.id} className="flex items-start gap-2 text-sm">
                                        <CheckCircle className="w-4 h-4 text-[#0b5f66] mt-0.5 flex-shrink-0" />
                                        <div>
                                            <span className="font-medium text-[#0f172a]">{o.title}</span>
                                            {o.description && <span className="text-[#475569] ml-1">— {o.description}</span>}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Form */}
                    <form onSubmit={handleSubmit} className="px-8 py-8 space-y-6">
                        <div className="p-4 rounded-xl border border-[rgba(11,95,102,0.2)]" style={{ background: 'linear-gradient(135deg, rgba(11,95,102,0.08) 0%, rgba(201,162,39,0.06) 100%)' }}>
                            <p className="text-sm text-[#0b5f66]"><strong>How it works:</strong> Submit your profile and proof of work. Our AI system evaluates your actual capabilities — not just your resume.</p>
                        </div>

                        {/* Personal Info */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-semibold text-[#475569] mb-1.5">Full Name <span className="text-red-500">*</span></label>
                                <input type="text" required placeholder="John Doe" value={formData.candidate_name}
                                    onChange={(e) => setFormData({ ...formData, candidate_name: e.target.value })} className={inputClass} />
                            </div>
                            <div>
                                <label className="block text-sm font-semibold text-[#475569] mb-1.5">Email <span className="text-red-500">*</span></label>
                                <input type="email" required placeholder="john@example.com" value={formData.candidate_email}
                                    onChange={(e) => setFormData({ ...formData, candidate_email: e.target.value })} className={inputClass} />
                            </div>
                        </div>

                        {/* Resume — Prominent */}
                        <div className="p-5 rounded-xl border border-[rgba(11,95,102,0.2)]" style={{ background: 'linear-gradient(135deg, rgba(11,95,102,0.06) 0%, rgba(201,162,39,0.04) 100%)' }}>
                            <label className="block text-sm font-semibold text-[#0f172a] mb-2">
                                <span className="flex items-center gap-1.5"><FileText className="w-4 h-4 text-[#0b5f66]" /> Resume / CV Link</span>
                            </label>
                            <input type="url" placeholder="https://drive.google.com/file/d/... or Dropbox/OneDrive link" value={formData.resume_url}
                                onChange={(e) => setFormData({ ...formData, resume_url: e.target.value })} className={inputClass} />
                            <p className="mt-1.5 text-xs text-[#94a3b8]">Upload your resume to Google Drive, Dropbox, or OneDrive and paste the share link here.</p>
                        </div>

                        {/* LinkedIn */}
                        <div>
                            <label className="block text-sm font-semibold text-[#475569] mb-1.5">
                                <span className="flex items-center gap-1.5"><Linkedin className="w-4 h-4 text-[#0b5f66]" /> LinkedIn URL</span>
                            </label>
                            <input type="url" placeholder="https://linkedin.com/in/johndoe" value={formData.linkedin_url}
                                onChange={(e) => setFormData({ ...formData, linkedin_url: e.target.value })} className={inputClass} />
                        </div>

                        {/* GitHub section */}
                        <div className="border-t border-[#e6e1d7] pt-6">
                            <h3 className="text-sm font-semibold text-[#0f172a] uppercase tracking-wider mb-4 flex items-center gap-2">
                                <Github className="w-4 h-4" /> Proof of Work
                            </h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-semibold text-[#475569] mb-1.5">GitHub Username</label>
                                    <div className="flex gap-2">
                                        <input type="text" placeholder="octocat" value={formData.github_username}
                                            onChange={(e) => setFormData({ ...formData, github_username: e.target.value })}
                                            className={`flex-1 ${inputClass}`} />
                                        <button type="button" onClick={handleFetchRepos} disabled={fetchingRepos || !formData.github_username}
                                            className="px-3 py-2.5 rounded-xl border-[1.5px] border-[#e6e1d7] hover:border-[#0b5f66] hover:bg-[#e6f6f5] disabled:opacity-40 transition-colors"
                                            title="Find best repos">
                                            {fetchingRepos ? <RefreshCw className="w-4 h-4 animate-spin text-[#0b5f66]" /> : <Search className="w-4 h-4 text-[#475569]" />}
                                        </button>
                                    </div>
                                </div>
                                <div>
                                    <label className="block text-sm font-semibold text-[#475569] mb-1.5">
                                        Repository URL {isTechnical && <span className="text-red-500">*</span>}
                                    </label>
                                    <div className="relative">
                                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                            <Github className="h-4 w-4 text-[#94a3b8]" />
                                        </div>
                                        <input type="url" required={isTechnical} placeholder="https://github.com/username/project"
                                            value={formData.repo_url}
                                            onChange={(e) => setFormData({ ...formData, repo_url: e.target.value })}
                                            className={`pl-10 ${inputClass}`} />
                                    </div>
                                </div>
                            </div>

                            {/* Repo picker */}
                            {showRepoList && (
                                <div className="mt-3 rounded-xl border border-[#e6e1d7] overflow-hidden" style={{ background: 'rgba(255,253,248,0.95)', boxShadow: '0 10px 30px rgba(15,23,42,0.08)' }}>
                                    <div className="p-2 border-b border-[#e6e1d7] flex justify-between items-center sticky top-0 z-10" style={{ background: 'rgba(247,245,240,0.9)' }}>
                                        <span className="text-xs font-bold text-[#475569] uppercase">Select a Repository</span>
                                        <button type="button" onClick={() => setShowRepoList(false)} className="text-xs text-[#0b5f66] hover:underline">Close</button>
                                    </div>
                                    {repos.length === 0 ? (
                                        <div className="p-4 text-center text-sm text-[#94a3b8]">{fetchingRepos ? "Analyzing repositories…" : "No relevant repositories found."}</div>
                                    ) : (
                                        <ul className="divide-y divide-[#e6e1d7] max-h-60 overflow-y-auto">
                                            {repos.map((repo) => (
                                                <li key={repo.url} onClick={() => selectRepo(repo)} className="p-3 hover:bg-[#e6f6f5] cursor-pointer transition-colors">
                                                    <div className="flex justify-between items-start">
                                                        <div className="font-medium text-[#0f172a] flex items-center gap-2">
                                                            {repo.repo}
                                                            <span className="text-xs font-normal text-[#475569] px-1.5 py-0.5 rounded" style={{ background: 'rgba(11,95,102,0.08)' }}>
                                                                Score: {(repo.score * 10).toFixed(1)}
                                                            </span>
                                                        </div>
                                                        {repo.language && <span className="text-xs px-2 py-0.5 rounded-full bg-[#e6f6f5] text-[#0b5f66]">{repo.language}</span>}
                                                    </div>
                                                    <div className="flex gap-4 mt-1 text-xs text-[#94a3b8]">
                                                        <span className="flex items-center gap-1"><Star className="w-3 h-3" /> Match</span>
                                                        {repo.last_commit_date && (
                                                            <span className="flex items-center gap-1"><GitBranch className="w-3 h-3" /> {new Date(repo.last_commit_date).toLocaleDateString()}</span>
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
                                <div className="mt-3 rounded-xl border border-[#e6e1d7] p-4" style={{ background: 'rgba(247,245,240,0.5)' }}>
                                    <h4 className="text-xs font-semibold text-[#475569] uppercase tracking-wider mb-3">Live Preview</h4>
                                    <div className="flex items-center gap-3 mb-3">
                                        <Folder className="h-5 w-5 text-[#0b5f66]" />
                                        <span className="font-medium text-[#0f172a]">{preview.name}</span>
                                    </div>
                                    <div className="space-y-1 pl-8 border-l-2 border-[#e6e1d7] ml-2.5">
                                        {preview.files?.map((file, i) => (
                                            <div key={i} className="flex items-center gap-2 text-sm text-[#475569]">
                                                <FileCode className="h-3 w-3 text-[#94a3b8]" /> {file}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* LeetCode */}
                            <div className="mt-4">
                                <label className="block text-sm font-semibold text-[#475569] mb-1.5">
                                    <span className="flex items-center gap-1.5"><Code className="w-4 h-4 text-[#c9a227]" /> LeetCode Username (Optional)</span>
                                </label>
                                <input type="text" placeholder="leetcode_user" value={formData.leetcode_username}
                                    onChange={(e) => setFormData({ ...formData, leetcode_username: e.target.value })} className={inputClass} />
                                {leetcodeError && (
                                    <p className="mt-1.5 text-xs text-red-500">{leetcodeError}</p>
                                )}
                            </div>
                            {leetcodeStats && (
                                <div className="mt-2 rounded-xl p-3 border border-[rgba(11,95,102,0.2)] flex items-center gap-4" style={{ background: 'rgba(11,95,102,0.06)' }}>
                                    <div className="p-2 rounded-full" style={{ background: 'rgba(11,95,102,0.1)' }}>
                                        <FileCode className="h-5 w-5 text-[#0b5f66]" />
                                    </div>
                                    <div>
                                        <div className="text-sm font-bold text-[#0f172a]">{leetcodeStats.total_solved} Solved</div>
                                        <div className="text-xs text-[#475569] flex gap-2">
                                            <span className="text-green-600 font-medium">Easy: {leetcodeStats.easy_solved}</span>
                                            <span className="text-[#c9a227] font-medium">Med: {leetcodeStats.medium_solved}</span>
                                            <span className="text-red-500 font-medium">Hard: {leetcodeStats.hard_solved}</span>
                                        </div>
                                    </div>
                                    <div className="ml-auto text-right">
                                        <div className="text-xs font-bold text-[#475569] uppercase tracking-wider">Acceptance</div>
                                        <div className="text-sm font-mono text-[#0f172a]">{leetcodeStats.acceptance_rate ?? 'N/A'}{leetcodeStats.acceptance_rate != null ? '%' : ''}</div>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Context */}
                        <div>
                            <label className="block text-sm font-semibold text-[#475569] mb-1.5">Additional Context / Notes</label>
                            <textarea rows={4} placeholder="Describe the architecture, trade-offs, and key features of your work…"
                                value={formData.context}
                                onChange={(e) => setFormData({ ...formData, context: e.target.value })}
                                className={`${inputClass} resize-none`} />
                        </div>

                        {/* Submit */}
                        <button type="submit" disabled={submitting}
                            className="w-full flex items-center justify-center gap-2 px-6 py-3.5 text-white font-semibold rounded-xl disabled:opacity-50 transition-all relative overflow-hidden"
                            style={{ background: 'linear-gradient(135deg, #0b5f66 0%, #0f766e 65%, #c9a227 120%)', boxShadow: '0 6px 18px rgba(11,95,102,0.28)' }}>
                            {submitting ? (
                                <><RefreshCw className="w-5 h-5 animate-spin" /> Submitting…</>
                            ) : (
                                <><Send className="w-5 h-5" /> Submit Application</>
                            )}
                        </button>
                    </form>
                </div>

                {/* Footer */}
                <p className="text-center text-xs text-[#94a3b8] mt-6">
                    Powered by <span className="font-semibold" style={{ background: 'linear-gradient(135deg,#0b5f66,#c9a227)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>SignalStack</span> — AI-driven hiring
                </p>
            </div>
        </div>
    );
}
