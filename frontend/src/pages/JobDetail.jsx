import React, { useCallback, useEffect, useState } from 'react';
import { useParams, Link, useNavigate, useLocation } from 'react-router-dom';
import {
    Briefcase, MapPin, Building, IndianRupee, Clock,
    CheckCircle, Plus, ArrowLeft, ChevronRight, Trash2,
    Send, Copy, ExternalLink, UserPlus, X, RefreshCw,
    Github, Linkedin, FileText, Code, Pencil
} from 'lucide-react';
import {
    getJob, getJobOutcomes, deleteJob, createInvite, getJobInvites, deleteInvite,
    deleteSubmission, updateSubmission, getJobEvaluationProgress, queueJobEvaluation
} from '../api';

export default function JobDetail() {
    const { jobId } = useParams();
    const navigate = useNavigate();
    const location = useLocation();
    const [job, setJob] = useState(null);
    const [outcomes, setOutcomes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [invites, setInvites] = useState([]);
    const [generatingInvite, setGeneratingInvite] = useState(false);
    const [copiedToken, setCopiedToken] = useState(null);
    const [editingSub, setEditingSub] = useState(null); // submission id being edited
    const [editForm, setEditForm] = useState({});
    const [evaluationProgress, setEvaluationProgress] = useState(null);
    const [queueingEvaluation, setQueueingEvaluation] = useState(false);
    const [evaluationMessage, setEvaluationMessage] = useState('');

    const hasEvaluationActivity = useCallback((progress) => {
        if (!progress) return false;
        const submissionCounts = progress.submission_status_counts || {};
        const candidateCounts = progress.candidate_status_counts || {};
        const activeCount = Number(progress.active_count || 0);
        const queueSize = Number(progress.queue_size || 0);
        const queueActive = Boolean(progress.queue_active);
        const queued = Number(submissionCounts.queued || candidateCounts.queued || 0);
        const evaluating = Number(submissionCounts.evaluating || candidateCounts.evaluating || 0);
        return activeCount > 0 || queueActive || queueSize > 0 || queued > 0 || evaluating > 0;
    }, []);

    const refreshEvaluationState = useCallback(async () => {
        const [progressData, invitesData] = await Promise.all([
            getJobEvaluationProgress(jobId),
            getJobInvites(jobId).catch(() => null),
        ]);
        setEvaluationProgress(progressData);
        if (invitesData) {
            setInvites(invitesData);
        }
        return progressData;
    }, [jobId]);

    useEffect(() => {
        async function loadJob() {
            try {
                const [jobData, outcomesData, invitesData, progressData] = await Promise.all([
                    getJob(jobId),
                    getJobOutcomes(jobId),
                    getJobInvites(jobId).catch(() => []),
                    getJobEvaluationProgress(jobId).catch(() => null),
                ]);
                setJob(jobData);
                setOutcomes(outcomesData);
                setInvites(invitesData);
                setEvaluationProgress(progressData);
            } catch (error) {
                console.error("Failed to load job", error);
            } finally {
                setLoading(false);
            }
        }
        loadJob();
    }, [jobId]);

    useEffect(() => {
        if (!queueingEvaluation && !hasEvaluationActivity(evaluationProgress)) return undefined;

        const timer = setInterval(async () => {
            try {
                await refreshEvaluationState();
            } catch (error) {
                console.warn('Failed to refresh evaluation progress', error);
            }
        }, 5000);

        return () => clearInterval(timer);
    }, [evaluationProgress, hasEvaluationActivity, queueingEvaluation, refreshEvaluationState]);

    useEffect(() => {
        const refreshWhenVisible = async () => {
            if (document.visibilityState !== 'visible') return;
            try {
                await refreshEvaluationState();
            } catch (error) {
                console.warn('Failed to refresh evaluation progress after returning to page', error);
            }
        };

        window.addEventListener('focus', refreshWhenVisible);
        document.addEventListener('visibilitychange', refreshWhenVisible);

        return () => {
            window.removeEventListener('focus', refreshWhenVisible);
            document.removeEventListener('visibilitychange', refreshWhenVisible);
        };
    }, [refreshEvaluationState]);

    useEffect(() => {
        if (!evaluationMessage || queueingEvaluation || hasEvaluationActivity(evaluationProgress)) return;
        setEvaluationMessage('');
    }, [evaluationMessage, evaluationProgress, hasEvaluationActivity, queueingEvaluation]);

    useEffect(() => {
        if (loading || location.hash !== '#outcomes') return;
        document.getElementById('outcomes')?.scrollIntoView({ block: 'start' });
    }, [loading, location.hash, outcomes.length]);

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
        if (!window.confirm('Revoke this invite link?\n\nThis will also remove all candidates submitted through this link from every outcome.')) return;
        try {
            await deleteInvite(inviteId);
            setInvites(invites.filter(i => i.id !== inviteId));
        } catch (error) {
            alert(`Failed: ${error.message}`);
        }
    };

    const handleDeleteSubmission = async (submissionId) => {
        if (!window.confirm('Delete this candidate?\n\nThis will also remove them from all outcome evaluations.')) return;
        try {
            await deleteSubmission(submissionId);
            // Remove from local state
            setInvites(invvs => invvs.map(inv => ({
                ...inv,
                submissions: inv.submissions.filter(s => s.id !== submissionId),
                submission_count: inv.submissions.filter(s => s.id !== submissionId).length,
            })));
        } catch (error) {
            alert(`Failed: ${error.message}`);
        }
    };

    const handleEditSubmission = (sub) => {
        setEditingSub(sub.id);
        setEditForm({
            candidate_name: sub.candidate_name || '',
            candidate_email: sub.candidate_email || '',
            github_username: sub.github_username || '',
            repo_url: sub.repo_url || '',
            linkedin_url: sub.linkedin_url || '',
            resume_url: sub.resume_url || '',
            leetcode_username: sub.leetcode_username || '',
            context: sub.context || '',
        });
    };

    const handleSaveSubmission = async (submissionId) => {
        try {
            const updated = await updateSubmission(submissionId, editForm);
            setInvites(invvs => invvs.map(inv => ({
                ...inv,
                submissions: inv.submissions.map(s => s.id === submissionId ? { ...s, ...updated } : s),
            })));
            setEditingSub(null);
        } catch (error) {
            alert(`Failed: ${error.message}`);
        }
    };

    const refreshEvaluationProgress = async () => {
        await refreshEvaluationState();
    };

    const buildOptimisticProgress = (result, totalSubmissions) => {
        const queuedCount = Number(result?.queued_count || 0);
        const previous = evaluationProgress || {};
        const outcomeStatuses = outcomes.map(outcome => ({
            outcome_id: outcome.id,
            title: outcome.title,
            status: previous.outcome_statuses?.find(item => item.outcome_id === outcome.id)?.status || 'pending',
        }));

        return {
            job_id: jobId,
            submissions_total: previous.submissions_total || totalSubmissions,
            candidates_total: previous.candidates_total || totalSubmissions,
            outcomes_total: previous.outcomes_total || outcomes.length,
            outcomes_evaluated: previous.outcomes_evaluated || 0,
            outcome_statuses: previous.outcome_statuses || outcomeStatuses,
            submission_status_counts: {
                ...(previous.submission_status_counts || {}),
                queued: queuedCount || previous.submission_status_counts?.queued || totalSubmissions,
            },
            candidate_status_counts: {
                ...(previous.candidate_status_counts || {}),
                queued: queuedCount || previous.candidate_status_counts?.queued || totalSubmissions,
            },
            active_count: queuedCount || previous.active_count || totalSubmissions,
            evaluated_count: previous.evaluated_count || 0,
            top_candidates: previous.top_candidates || [],
            queue_size: result?.task_id ? Math.max(1, previous.queue_size || 0) : previous.queue_size || 0,
            queue_active: Boolean(result?.task_id || queuedCount || previous.queue_active),
            global_queue_size: previous.global_queue_size || 0,
            queue_backend: previous.queue_backend || 'starting',
        };
    };

    const handleQueueEvaluation = async () => {
        const totalSubmissions = invites.reduce((count, inv) => count + (inv.submissions?.length || 0), 0);
        if (totalSubmissions === 0) {
            alert('No candidate submissions to evaluate yet.');
            return;
        }

        setQueueingEvaluation(true);
        setEvaluationMessage('Starting evaluation...');
        try {
            const result = await queueJobEvaluation(jobId, {
                deep_limit: 100,
                include_deep_evaluation: true,
            });
            setEvaluationMessage(result.message || 'Evaluation queued');
            setEvaluationProgress(result.progress || buildOptimisticProgress(result, totalSubmissions));
            await refreshEvaluationProgress();
        } catch (error) {
            setEvaluationMessage('');
            alert(`Failed to queue evaluation: ${error.message}`);
        } finally {
            setQueueingEvaluation(false);
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

    const evaluationActive = hasEvaluationActivity(evaluationProgress);
    const progress = evaluationProgress || {};
    const visibleEvaluationActive = queueingEvaluation || evaluationActive;
    const submissionsTotal = Number(progress.submissions_total || 0);
    const evaluatedCount = Number(progress.evaluated_count || 0);
    const outcomesTotal = Number(progress.outcomes_total || outcomes.length || 0);
    const outcomesEvaluated = Number(progress.outcomes_evaluated || 0);
    const progressPercent = submissionsTotal > 0
        ? Math.min(100, Math.round((evaluatedCount / submissionsTotal) * 100))
        : 0;
    const getProgressStatusCount = (status) => Math.max(
        Number(progress.submission_status_counts?.[status] || 0),
        Number(progress.candidate_status_counts?.[status] || 0),
    );
    const totalInviteSubmissions = invites.reduce((count, inv) => count + (inv.submissions?.length || 0), 0);

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

            <div className={`bg-white border rounded-xl p-5 shadow-sm ${visibleEvaluationActive ? 'border-indigo-200 ring-1 ring-indigo-100' : 'border-gray-200'}`}>
                <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                            <h2 className="text-xl font-bold text-gray-900">Evaluation Progress</h2>
                            {visibleEvaluationActive && (
                                <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700 border border-indigo-100">
                                    <RefreshCw className="w-3 h-3 animate-spin" />
                                    Processing
                                </span>
                            )}
                            {(progress.queue_backend || queueingEvaluation) && (
                                <span className="inline-flex items-center rounded-full bg-gray-50 px-2.5 py-1 text-xs font-medium text-gray-600 border border-gray-200">
                                    Queue: {progress.queue_backend || 'starting'}
                                </span>
                            )}
                        </div>
                        <p className="mt-1 text-sm text-gray-500">
                            {evaluationMessage || `${evaluatedCount} evaluated from ${submissionsTotal || totalInviteSubmissions} submissions`}
                            {outcomesTotal ? ` - ${outcomesEvaluated}/${outcomesTotal} outcomes ready` : ''}
                            {progress.queue_size ? ` - queue: ${progress.queue_size}` : ''}
                        </p>
                        <div className="mt-4 h-2 rounded-full bg-gray-100 overflow-hidden">
                            <div
                                className={`h-full rounded-full transition-all duration-500 ${visibleEvaluationActive ? 'bg-indigo-500' : 'bg-primary'}`}
                                style={{ width: `${visibleEvaluationActive && progressPercent === 0 ? 8 : progressPercent}%` }}
                            />
                        </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <button
                            onClick={refreshEvaluationProgress}
                            className="inline-flex items-center gap-1.5 px-3 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-200 transition-colors"
                        >
                            <RefreshCw className="w-3.5 h-3.5" /> Refresh
                        </button>
                        <button
                            onClick={handleQueueEvaluation}
                            disabled={queueingEvaluation}
                            className="inline-flex items-center gap-1.5 px-3 py-2 bg-primary text-white text-sm font-medium rounded-lg hover:bg-primary-hover transition-colors disabled:opacity-50"
                        >
                            {queueingEvaluation ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle className="w-3.5 h-3.5" />}
                            Evaluate Submissions
                        </button>
                    </div>
                </div>
                <div className="mt-4 grid grid-cols-2 md:grid-cols-5 gap-2 text-xs">
                    {['submitted', 'queued', 'evaluating', 'evaluated', 'failed'].map(status => (
                        <div key={status} className="rounded-lg bg-gray-50 border border-gray-100 px-3 py-2">
                            <div className="text-gray-400 capitalize">{status}</div>
                            <div className="font-bold text-gray-800">{getProgressStatusCount(status)}</div>
                        </div>
                    ))}
                </div>
                {progress.top_candidates?.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                        {progress.top_candidates.slice(0, 5).map(candidate => (
                            <span key={candidate.candidate_id} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-primary-soft text-primary-hover text-xs font-semibold">
                                {candidate.candidate_id}: {Math.round(candidate.score || 0)}%
                            </span>
                        ))}
                    </div>
                )}
                {progress.outcome_statuses?.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                        {progress.outcome_statuses.map(outcome => (
                            <span
                                key={outcome.outcome_id}
                                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                                    outcome.status === 'evaluated'
                                        ? 'bg-green-50 text-green-700 border border-green-200'
                                        : 'bg-gray-50 text-gray-600 border border-gray-200'
                                }`}
                            >
                                {outcome.title}: {outcome.status}
                            </span>
                        ))}
                    </div>
                )}
            </div>

            {/* Outcomes Section */}
            <div id="outcomes" className="space-y-4 scroll-mt-6">
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
                    <div className="space-y-4">
                        {invites.map((inv) => {
                            const isExpired = inv.is_expired || (inv.expires_at && new Date(inv.expires_at) < new Date());
                            const statusColor = inv.status === 'active' && !isExpired ? 'bg-green-100 text-green-700'
                                : isExpired ? 'bg-red-100 text-red-700'
                                    : 'bg-gray-100 text-gray-600';
                            const statusLabel = isExpired ? 'Expired' : inv.status === 'active' ? 'Active' : inv.status;
                            const subs = inv.submissions || [];

                            return (
                                <div key={inv.id} className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                                    {/* Invite header */}
                                    <div className="p-4 flex items-center justify-between bg-gray-50 border-b border-gray-100">
                                        <div className="flex items-center gap-3">
                                            <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold capitalize ${statusColor}`}>
                                                {statusLabel}
                                            </span>
                                            <span className="text-gray-500 text-sm font-mono">…{inv.token?.slice(-8)}</span>
                                            {subs.length > 0 && (
                                                <span className="bg-indigo-100 text-indigo-700 text-xs font-bold px-2 py-0.5 rounded-full">
                                                    {subs.length} {subs.length === 1 ? 'submission' : 'submissions'}
                                                </span>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs text-gray-400">
                                                {inv.created_at?.split('T')[0]}
                                            </span>
                                            {inv.status === 'active' && !isExpired && (
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
                                            <button
                                                onClick={() => handleRevokeInvite(inv.id)}
                                                className="p-1.5 rounded-md hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors"
                                                title="Revoke invite"
                                            >
                                                <X className="w-4 h-4" />
                                            </button>
                                        </div>
                                    </div>

                                    {/* Submissions list */}
                                    {subs.length === 0 ? (
                                        <div className="p-4 text-sm text-gray-400 text-center">
                                            No submissions yet — share this link with candidates
                                        </div>
                                    ) : (
                                        <div className="divide-y divide-gray-100">
                                            {subs.map((sub) => (
                                                <div key={sub.id} className="p-4 hover:bg-gray-50 transition-colors">
                                                    {editingSub === sub.id ? (
                                                        /* ─── Edit Mode ─── */
                                                        <div className="space-y-3">
                                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                                                <input type="text" placeholder="Name" value={editForm.candidate_name}
                                                                    onChange={e => setEditForm({ ...editForm, candidate_name: e.target.value })}
                                                                    className="px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none" />
                                                                <input type="email" placeholder="Email" value={editForm.candidate_email}
                                                                    onChange={e => setEditForm({ ...editForm, candidate_email: e.target.value })}
                                                                    className="px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none" />
                                                                <input type="text" placeholder="GitHub username" value={editForm.github_username}
                                                                    onChange={e => setEditForm({ ...editForm, github_username: e.target.value })}
                                                                    className="px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none" />
                                                                <input type="url" placeholder="Repository URL" value={editForm.repo_url}
                                                                    onChange={e => setEditForm({ ...editForm, repo_url: e.target.value })}
                                                                    className="px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none" />
                                                                <input type="url" placeholder="LinkedIn URL" value={editForm.linkedin_url}
                                                                    onChange={e => setEditForm({ ...editForm, linkedin_url: e.target.value })}
                                                                    className="px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none" />
                                                                <input type="url" placeholder="Resume URL" value={editForm.resume_url}
                                                                    onChange={e => setEditForm({ ...editForm, resume_url: e.target.value })}
                                                                    className="px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none" />
                                                            </div>
                                                            <textarea placeholder="Context / Notes" rows={2} value={editForm.context}
                                                                onChange={e => setEditForm({ ...editForm, context: e.target.value })}
                                                                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none resize-none" />
                                                            <div className="flex gap-2">
                                                                <button onClick={() => handleSaveSubmission(sub.id)}
                                                                    className="px-4 py-1.5 bg-indigo-600 text-white text-xs font-medium rounded-lg hover:bg-indigo-700 transition-colors">
                                                                    Save Changes
                                                                </button>
                                                                <button onClick={() => setEditingSub(null)}
                                                                    className="px-4 py-1.5 bg-gray-100 text-gray-700 text-xs font-medium rounded-lg hover:bg-gray-200 transition-colors">
                                                                    Cancel
                                                                </button>
                                                            </div>
                                                        </div>
                                                    ) : (
                                                        /* ─── View Mode ─── */
                                                        <>
                                                            {/* Candidate header */}
                                                            <div className="flex items-center justify-between mb-2">
                                                                <div className="flex items-center gap-2">
                                                                    <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center text-sm font-bold">
                                                                        {sub.candidate_name?.charAt(0)?.toUpperCase() || '?'}
                                                                    </div>
                                                                    <div>
                                                                        <div className="flex items-center gap-2">
                                                                            <span className="font-medium text-gray-900">{sub.candidate_name}</span>
                                                                            {sub.status === 'hired' && (
                                                                                <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-bold rounded-full border border-green-200">HIRED</span>
                                                                            )}
                                                                            {sub.status === 'rejected' && (
                                                                                <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs font-medium rounded-full border border-red-200">Rejected</span>
                                                                            )}
                                                                        </div>
                                                                        <span className="text-gray-500 text-sm">{sub.candidate_email}</span>
                                                                    </div>
                                                                </div>
                                                                <div className="flex items-center gap-1">
                                                                    <span className="text-xs text-gray-400 mr-2">
                                                                        {sub.submitted_at && new Date(sub.submitted_at).toLocaleDateString()}
                                                                    </span>
                                                                    <button onClick={() => handleEditSubmission(sub)}
                                                                        className="p-1.5 rounded-md hover:bg-indigo-50 text-gray-400 hover:text-indigo-600 transition-colors"
                                                                        title="Edit candidate">
                                                                        <Pencil className="w-3.5 h-3.5" />
                                                                    </button>
                                                                    <button onClick={() => handleDeleteSubmission(sub.id)}
                                                                        className="p-1.5 rounded-md hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors"
                                                                        title="Delete candidate">
                                                                        <Trash2 className="w-3.5 h-3.5" />
                                                                    </button>
                                                                </div>
                                                            </div>

                                                            {/* Link buttons */}
                                                            <div className="flex flex-wrap gap-2 mb-2">
                                                                {sub.github_username && (
                                                                    <a href={`https://github.com/${sub.github_username}`} target="_blank" rel="noopener noreferrer"
                                                                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-900 text-white text-xs font-medium rounded-lg hover:bg-gray-700 transition-colors">
                                                                        <Github className="w-3.5 h-3.5" /> {sub.github_username}
                                                                    </a>
                                                                )}
                                                                {sub.linkedin_url && (
                                                                    <a href={sub.linkedin_url} target="_blank" rel="noopener noreferrer"
                                                                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-lg hover:bg-blue-700 transition-colors">
                                                                        <Linkedin className="w-3.5 h-3.5" /> LinkedIn
                                                                    </a>
                                                                )}
                                                                {sub.resume_url && (
                                                                    <a href={sub.resume_url} target="_blank" rel="noopener noreferrer"
                                                                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 text-white text-xs font-medium rounded-lg hover:bg-indigo-700 transition-colors">
                                                                        <FileText className="w-3.5 h-3.5" /> Resume
                                                                    </a>
                                                                )}
                                                            </div>

                                                            {/* Details row */}
                                                            <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-gray-500">
                                                                {sub.repo_url && (
                                                                    <a href={sub.repo_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-indigo-600 hover:underline">
                                                                        <Code className="w-3 h-3" /> {sub.repo_url.replace('https://github.com/', '')}
                                                                    </a>
                                                                )}
                                                                {sub.leetcode_username && (
                                                                    <span className="flex items-center gap-1">
                                                                        <Code className="w-3 h-3 text-amber-500" /> LeetCode: <strong>{sub.leetcode_username}</strong>
                                                                    </span>
                                                                )}
                                                            </div>

                                                            {/* Context */}
                                                            {sub.context && (
                                                                <div className="mt-2 text-xs text-gray-600 bg-gray-50 p-3 rounded-md border border-gray-100">
                                                                    <span className="font-semibold text-gray-700">Notes:</span> {sub.context}
                                                                </div>
                                                            )}
                                                        </>
                                                    )}
                                                </div>
                                            ))}
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
