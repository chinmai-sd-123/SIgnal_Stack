import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
    Briefcase, MapPin, Building, IndianRupee, Clock,
    CheckCircle, Plus, ArrowLeft, ChevronRight, Trash2,
    Send, Copy, ExternalLink, UserPlus, X, RefreshCw,
    Github, Linkedin, FileText, Code
} from 'lucide-react';
import { getJob, getJobOutcomes, deleteJob, finalizeShortlist, archiveJob, createInvite, getJobInvites, deleteInvite } from '../api';

export default function JobDetail() {
    const { jobId } = useParams();
    const navigate = useNavigate();
    const [job, setJob] = useState(null);
    const [outcomes, setOutcomes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [invites, setInvites] = useState([]);
    const [generatingInvite, setGeneratingInvite] = useState(false);
    const [copiedToken, setCopiedToken] = useState(null);

    useEffect(() => {
        async function loadJob() {
            try {
                const [jobData, outcomesData, invitesData] = await Promise.all([
                    getJob(jobId),
                    getJobOutcomes(jobId),
                    getJobInvites(jobId).catch(() => []),
                ]);
                setJob(jobData);
                setOutcomes(outcomesData);
                setInvites(invitesData);
            } catch (error) {
                console.error("Failed to load job", error);
            } finally {
                setLoading(false);
            }
        }
        loadJob();
    }, [jobId]);

    const handleGenerateInvite = async () => {
        setGeneratingInvite(true);
        try {
            const inv = await createInvite(jobId);
            setInvites([inv, ...invites]);
            // Auto-copy the new link
            const url = `${window.location.origin}/apply/${inv.token}`;
            navigator.clipboard.writeText(url);
            setCopiedToken(inv.token);
            setTimeout(() => setCopiedToken(null), 3000);
        } catch (error) {
            alert(`Failed to create invite: ${error.message}`);
        } finally {
            setGeneratingInvite(false);
        }
    };

    const handleCopyLink = (token) => {
        const url = `${window.location.origin}/apply/${token}`;
        navigator.clipboard.writeText(url);
        setCopiedToken(token);
        setTimeout(() => setCopiedToken(null), 3000);
    };

    const handleRevokeInvite = async (inviteId) => {
        if (!window.confirm('Revoke this invite? The link will stop working.')) return;
        try {
            await deleteInvite(inviteId);
            setInvites(invites.filter(i => i.id !== inviteId));
        } catch (error) {
            alert(`Failed: ${error.message}`);
        }
    };

    const handleArchiveJob = async () => {
        const confirmed = window.confirm(
            `Archive this job posting?\n\n"${job.title}"\n\nThis will hide it from listings but keep all data. Outcomes and candidate submissions will be preserved.`
        );

        if (!confirmed) return;

        try {
            await deleteJob(jobId);  // Soft delete by default
            alert('Job archived successfully!');
            navigate('/');  // Redirect to dashboard
        } catch (error) {
            alert(`Failed to archive job: ${error.message}`);
        }
    };

    if (loading) return (
        <div className="flex justify-center items-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
    );

    if (!job) return <div className="p-8 text-center text-gray-500">Job not found.</div>;

    return (
        <div className="max-w-5xl mx-auto space-y-8 pb-12">
            <Link to="/" className="text-gray-500 hover:text-primary flex items-center gap-1 transition-colors">
                <ArrowLeft className="w-4 h-4" /> Back to Jobs
            </Link>

            {/* Job Header */}
            <div className="card">
                <div className="flex flex-col md:flex-row justify-between items-start gap-6">
                    <div>
                        <div className="flex items-center gap-3">
                            <h1 className="heading-1">{job.title}</h1>
                            <span className={`badge ${job.status === 'active' ? 'badge-success' :
                                job.status === 'closed' ? 'badge-info' :
                                    'badge-neutral'
                                }`}>
                                {job.status.toUpperCase()}
                            </span>
                            {job.applications_open !== undefined && (
                                <span className={`badge ${job.applications_open ? 'badge-success' : 'badge-error'
                                    }`}>
                                    Applications {job.applications_open ? 'OPEN' : 'CLOSED'}
                                </span>
                            )}
                        </div>

                        <div className="mt-4 flex flex-wrap gap-4 text-sm text-gray-600">
                            <div className="flex items-center gap-1">
                                <Building className="w-4 h-4 text-gray-400" />
                                {job.company}
                            </div>
                            <div className="flex items-center gap-1">
                                <MapPin className="w-4 h-4 text-gray-400" />
                                {job.location}
                            </div>
                            <div className="flex items-center gap-1">
                                <Clock className="w-4 h-4 text-gray-400" />
                                {job.job_type}
                            </div>
                            {(job.salary_min || job.salary_max) && (
                                <div className="flex items-center gap-1">
                                    <IndianRupee className="w-4 h-4 text-gray-400" />
                                    {job.currency === 'INR' ? '₹' : job.currency} {job.salary_min?.toLocaleString()} - {job.salary_max?.toLocaleString()}
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="flex gap-2">
                        <button
                            onClick={handleArchiveJob}
                            className="btn btn-ghost text-red-600 hover:text-red-700 hover:bg-red-50"
                        >
                            <Trash2 className="w-4 h-4 mr-2" />
                            Archive Job
                        </button>
                    </div>
                </div>

                    <div className="mt-6 pt-6 border-t border-gray-100">
                    <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-2">Description</h3>
                    <p className="text-gray-600 whitespace-pre-line">{job.description}</p>

                    {/* Shortlist Capacity Info */}
                    {job.total_positions !== undefined && (
                        <div className="mt-6 p-4 bg-primary-soft rounded-lg">
                            <h3 className="font-semibold text-primary mb-3">Shortlist Capacity</h3>
                            <div className="grid grid-cols-3 gap-4 text-sm">
                                <div>
                                    <div className="text-gray-600">Positions</div>
                                    <div className="text-2xl font-bold text-primary">{job.total_positions}</div>
                                </div>
                                <div>
                                    <div className="text-gray-600">Multiplier</div>
                                    <div className="text-2xl font-bold text-primary">{job.shortlist_multiplier || 3.0}×</div>
                                </div>
                                <div>
                                    <div className="text-gray-600">Shortlist Size</div>
                                    <div className="text-2xl font-bold text-primary">
                                        {Math.floor((job.total_positions || 1) * (job.shortlist_multiplier || 3.0))}
                                    </div>
                                </div>
                            </div>
                            <p className="text-xs text-gray-600 mt-3">
                                System will recommend {Math.floor((job.total_positions || 1) * (job.shortlist_multiplier || 3.0))} candidates for interviews
                            </p>
                        </div>
                    )}
                </div>
            </div>

            {/* Outcomes Section */}
            <div className="space-y-4">
                <div className="flex justify-between items-center">
                    <h2 className="text-2xl font-bold text-gray-900">Outcomes</h2>
                    <Link
                        to={`/jobs/${job.id}/add-outcome`}
                        className="btn btn-secondary"
                    >
                        <Plus className="w-4 h-4 mr-2" />
                        Add Outcome
                    </Link>
                </div>

                {(!outcomes || outcomes.length === 0) ? (
                    <div className="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed border-gray-200">
                        <CheckCircle className="mx-auto h-12 w-12 text-gray-300" />
                        <h3 className="mt-2 text-sm font-medium text-gray-900">No outcomes defined</h3>
                        <p className="mt-1 text-sm text-gray-500">Define what success looks like for this role.</p>
                        <div className="mt-6">
                            <Link
                                to={`/jobs/${job.id}/add-outcome`}
                                className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary hover:bg-primary-hover"
                            >
                                <Plus className="-ml-1 mr-2 h-5 w-5" aria-hidden="true" />
                                Add Outcome
                            </Link>
                        </div>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 gap-4">
                        {outcomes.map((outcome) => (
                            <Link
                                key={outcome.id}
                                to={`/dashboard/${outcome.id}`}
                                className="block bg-white p-6 rounded-lg shadow-sm border border-gray-200 hover:border-primary transition-colors"
                            >
                                <div className="flex justify-between items-start">
                                    <div>
                                        <h3 className="text-lg font-semibold text-gray-900 group-hover:text-primary">
                                            {outcome.title}
                                        </h3>
                                        <p className="text-gray-500 mt-1 line-clamp-2">{outcome.description}</p>
                                    </div>
                                    <div className="bg-primary-soft p-2 rounded-full text-primary">
                                        <ChevronRight className="w-5 h-5" />
                                    </div>
                                </div>
                                <div className="mt-4 flex items-center gap-4 text-sm text-gray-500">
                                    <span className="flex items-center gap-1">
                                        <CheckCircle className="w-4 h-4" />
                                        {outcome.tasks?.length || 0} Signals
                                    </span>
                                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${outcome.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                                        }`}>
                                        {outcome.status}
                                    </span>
                                </div>
                            </Link>
                        ))}
                    </div>
                )}
            </div>

            {/* Invite Candidates Section */}
            <div className="space-y-4">
                <div className="flex justify-between items-center">
                    <h2 className="text-2xl font-bold text-gray-900">Invite Candidates</h2>
                    <button
                        onClick={handleGenerateInvite}
                        disabled={generatingInvite}
                        className="btn btn-primary"
                    >
                        {generatingInvite ? (
                            <><RefreshCw className="w-4 h-4 mr-2 animate-spin" /> Generating…</>
                        ) : (
                            <><UserPlus className="w-4 h-4 mr-2" /> Generate Invite Link</>
                        )}
                    </button>
                </div>

                {invites.length === 0 ? (
                    <div className="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed border-gray-200">
                        <Send className="mx-auto h-12 w-12 text-gray-300" />
                        <h3 className="mt-2 text-sm font-medium text-gray-900">No invites yet</h3>
                        <p className="mt-1 text-sm text-gray-500">Generate a unique link to send to candidates.</p>
                    </div>
                ) : (
                    <div className="bg-white rounded-lg border border-gray-200 divide-y divide-gray-100 overflow-hidden">
                        {invites.map((inv) => {
                            const isExpired = inv.is_expired || (inv.expires_at && new Date(inv.expires_at) < new Date());
                            const statusColor = inv.status === 'submitted' ? 'bg-green-100 text-green-700'
                                : inv.status === 'evaluated' ? 'bg-blue-100 text-blue-700'
                                : isExpired ? 'bg-red-100 text-red-700'
                                : 'bg-amber-100 text-amber-700';
                            const statusLabel = isExpired && inv.status === 'pending' ? 'Expired' : inv.status;

                            return (
                                <div key={inv.id} className="p-4 hover:bg-gray-50 transition-colors">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-3 min-w-0">
                                            <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold capitalize ${statusColor}`}>
                                                {statusLabel}
                                            </span>
                                            {inv.candidate_name ? (
                                                <div>
                                                    <span className="font-medium text-gray-900">{inv.candidate_name}</span>
                                                    {inv.candidate_email && (
                                                        <span className="text-gray-500 text-sm ml-2">{inv.candidate_email}</span>
                                                    )}
                                                </div>
                                            ) : (
                                                <span className="text-gray-500 text-sm font-mono truncate">…{inv.token?.slice(-8)}</span>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-2 flex-shrink-0">
                                            <span className="text-xs text-gray-400">
                                                {inv.created_at?.split('T')[0]}
                                            </span>
                                            {inv.status === 'pending' && !isExpired && (
                                                <button
                                                    onClick={() => handleCopyLink(inv.token)}
                                                    className="p-1.5 rounded-md hover:bg-gray-100 transition-colors text-gray-400 hover:text-gray-600"
                                                    title="Copy invite link"
                                                >
                                                    {copiedToken === inv.token ? (
                                                        <CheckCircle className="w-4 h-4 text-green-500" />
                                                    ) : (
                                                        <Copy className="w-4 h-4" />
                                                    )}
                                                </button>
                                            )}
                                            {inv.linkedin_url && (
                                                <a href={inv.linkedin_url} target="_blank" rel="noopener noreferrer"
                                                    className="p-1.5 rounded-md hover:bg-blue-50 text-blue-500"
                                                    title="LinkedIn">
                                                    <ExternalLink className="w-4 h-4" />
                                                </a>
                                            )}
                                            <button
                                                onClick={() => handleRevokeInvite(inv.id)}
                                                className="p-1.5 rounded-md hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors"
                                                title="Revoke invite"
                                            >
                                                <X className="w-4 h-4" />
                                            </button>
                                        </div>
                                    </div>
                                    {inv.status === 'submitted' && (
                                        <div className="mt-3 p-4 bg-gray-50 rounded-lg border border-gray-100 space-y-3">
                                            {/* Candidate links row */}
                                            <div className="flex flex-wrap gap-3">
                                                {inv.github_username && (
                                                    <a href={`https://github.com/${inv.github_username}`} target="_blank" rel="noopener noreferrer"
                                                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-900 text-white text-xs font-medium rounded-lg hover:bg-gray-700 transition-colors">
                                                        <Github className="w-3.5 h-3.5" /> {inv.github_username}
                                                    </a>
                                                )}
                                                {inv.linkedin_url && (
                                                    <a href={inv.linkedin_url} target="_blank" rel="noopener noreferrer"
                                                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-lg hover:bg-blue-700 transition-colors">
                                                        <Linkedin className="w-3.5 h-3.5" /> LinkedIn Profile
                                                    </a>
                                                )}
                                                {inv.resume_url && (
                                                    <a href={inv.resume_url} target="_blank" rel="noopener noreferrer"
                                                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 text-white text-xs font-medium rounded-lg hover:bg-indigo-700 transition-colors">
                                                        <FileText className="w-3.5 h-3.5" /> Resume
                                                    </a>
                                                )}
                                            </div>
                                            {/* Repo & LeetCode */}
                                            <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-gray-600">
                                                {inv.repo_url && (
                                                    <a href={inv.repo_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-indigo-600 hover:underline">
                                                        <Code className="w-3 h-3" /> {inv.repo_url.replace('https://github.com/', '')}
                                                    </a>
                                                )}
                                                {inv.leetcode_username && (
                                                    <span className="flex items-center gap-1">
                                                        <Code className="w-3 h-3 text-amber-500" /> LeetCode: <strong>{inv.leetcode_username}</strong>
                                                    </span>
                                                )}
                                                {inv.submitted_at && (
                                                    <span className="text-gray-400">Submitted {new Date(inv.submitted_at).toLocaleDateString()}</span>
                                                )}
                                            </div>
                                            {/* Context notes */}
                                            {inv.context && (
                                                <div className="text-xs text-gray-600 bg-white p-3 rounded-md border border-gray-100">
                                                    <span className="font-semibold text-gray-700">Notes:</span> {inv.context}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                    {/* Minimal info for non-submitted */}
                                    {inv.status !== 'submitted' && inv.github_username && (
                                        <div className="mt-2 text-xs text-gray-500 flex gap-4">
                                            <span>GitHub: <strong>{inv.github_username}</strong></span>
                                            {inv.resume_url && <a href={inv.resume_url} target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:underline">Resume</a>}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}
