import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
    AlertTriangle,
    Briefcase,
    CheckCircle,
    ChevronRight,
    Clock,
    FileText,
    Layers,
    PlayCircle,
    RefreshCw,
    Search,
    Users,
} from 'lucide-react';
import { getJobEvaluationProgress, getJobs, queueJobEvaluation } from '../api';

const STATUSES = ['submitted', 'queued', 'evaluating', 'evaluated', 'failed'];
const FILTERS = [
    { id: 'active', label: 'Active' },
    { id: 'reports', label: 'Reports Ready' },
    { id: 'needs_action', label: 'Needs Action' },
    { id: 'completed', label: 'Completed' },
    { id: 'all', label: 'All Open' },
    { id: 'archived', label: 'Archived' },
];

function hasActivity(progress) {
    if (!progress) return false;
    const submissionCounts = progress.submission_status_counts || {};
    const candidateCounts = progress.candidate_status_counts || {};
    return (
        Number(progress.active_count || 0) > 0 ||
        Boolean(progress.queue_active) ||
        Number(progress.queue_size || 0) > 0 ||
        Number(submissionCounts.queued || candidateCounts.queued || 0) > 0 ||
        Number(submissionCounts.evaluating || candidateCounts.evaluating || 0) > 0
    );
}

function statusCount(progress, status) {
    return Math.max(
        Number(progress?.submission_status_counts?.[status] || 0),
        Number(progress?.candidate_status_counts?.[status] || 0),
    );
}

function progressPercent(progress) {
    const total = Number(progress?.submissions_total || progress?.candidates_total || 0);
    if (!total) return 0;
    return Math.min(100, Math.round((Number(progress?.evaluated_count || 0) / total) * 100));
}

function isArchived(job) {
    return job?.status === 'archived';
}

function evaluatedOutcomes(progress) {
    return (progress?.outcome_statuses || []).filter((outcome) => outcome.status === 'evaluated');
}

export default function ReviewerQueue() {
    const [jobs, setJobs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [actionJobId, setActionJobId] = useState(null);
    const [error, setError] = useState('');
    const [anonymized, setAnonymized] = useState(false);
    const [filter, setFilter] = useState('all');
    const [search, setSearch] = useState('');

    const loadQueue = useCallback(async ({ silent = false } = {}) => {
        if (!silent) setLoading(true);
        setRefreshing(true);
        setError('');
        try {
            const jobData = await getJobs();
            const rows = await Promise.all(
                jobData.map(async (job) => {
                    try {
                        const progress = await getJobEvaluationProgress(job.id);
                        return { job, progress, progressError: null };
                    } catch (progressError) {
                        console.warn('Failed to fetch job progress', job.id, progressError);
                        return { job, progress: null, progressError };
                    }
                }),
            );
            setJobs(rows);
        } catch (loadError) {
            console.error('Failed to load reviewer queue', loadError);
            setError(loadError.message || 'Failed to load reviewer queue');
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, []);

    useEffect(() => {
        loadQueue();
    }, [loadQueue]);

    const hasActiveJobs = useMemo(
        () => jobs.some((row) => hasActivity(row.progress)),
        [jobs],
    );

    useEffect(() => {
        if (!hasActiveJobs) return undefined;
        const timer = setInterval(() => {
            loadQueue({ silent: true });
        }, 5000);
        return () => clearInterval(timer);
    }, [hasActiveJobs, loadQueue]);

    const visibleJobs = useMemo(() => {
        const query = search.trim().toLowerCase();
        return jobs.filter(({ job, progress, progressError }) => {
            const active = hasActivity(progress);
            const failed = statusCount(progress, 'failed') > 0 || Boolean(progressError);
            const total = Number(progress?.submissions_total || progress?.candidates_total || 0);
            const evaluated = Number(progress?.evaluated_count || 0);
            const completed = total > 0 && evaluated >= total && !active && !failed;
            const archived = isArchived(job);
            const hasReports = evaluatedOutcomes(progress).length > 0;

            if (filter === 'archived' && !archived) return false;
            if (filter !== 'archived' && archived) return false;
            if (filter === 'active' && !active) return false;
            if (filter === 'reports' && !hasReports) return false;
            if (filter === 'needs_action' && !failed) return false;
            if (filter === 'completed' && !completed) return false;

            if (!query) return true;
            return [job.title, job.company, job.location, job.category, job.status]
                .filter(Boolean)
                .some((value) => String(value).toLowerCase().includes(query));
        });
    }, [filter, jobs, search]);

    const sortedJobs = useMemo(() => {
        return [...visibleJobs].sort((a, b) => {
            const activeDiff = Number(hasActivity(b.progress)) - Number(hasActivity(a.progress));
            if (activeDiff) return activeDiff;
            const failedDiff = statusCount(b.progress, 'failed') - statusCount(a.progress, 'failed');
            if (failedDiff) return failedDiff;
            const pendingDiff = Number(b.progress?.submissions_total || 0) - Number(a.progress?.submissions_total || 0);
            if (pendingDiff) return pendingDiff;
            return new Date(b.job.created_at || 0) - new Date(a.job.created_at || 0);
        });
    }, [visibleJobs]);

    const filterCounts = useMemo(() => {
        return jobs.reduce((counts, { job, progress, progressError }) => {
            const active = hasActivity(progress);
            const failed = statusCount(progress, 'failed') > 0 || Boolean(progressError);
            const total = Number(progress?.submissions_total || progress?.candidates_total || 0);
            const evaluated = Number(progress?.evaluated_count || 0);
            const completed = total > 0 && evaluated >= total && !active && !failed;
            const archived = isArchived(job);
            const hasReports = evaluatedOutcomes(progress).length > 0;

            if (archived) counts.archived += 1;
            else counts.all += 1;
            if (!archived && active) counts.active += 1;
            if (!archived && hasReports) counts.reports += 1;
            if (!archived && failed) counts.needs_action += 1;
            if (!archived && completed) counts.completed += 1;
            return counts;
        }, { active: 0, reports: 0, needs_action: 0, completed: 0, all: 0, archived: 0 });
    }, [jobs]);

    const handleEvaluate = async (jobId) => {
        setActionJobId(jobId);
        setError('');
        try {
            const result = await queueJobEvaluation(jobId, {
                deep_limit: 100,
                include_deep_evaluation: true,
            });
            if (result.progress) {
                setJobs((current) => current.map((row) => (
                    row.job.id === jobId ? { ...row, progress: result.progress, progressError: null } : row
                )));
            }
            await loadQueue({ silent: true });
        } catch (queueError) {
            console.error('Failed to queue job evaluation', queueError);
            setError(queueError.message || 'Failed to queue job evaluation');
        } finally {
            setActionJobId(null);
        }
    };

    const handleRetryFailed = async (jobId) => {
        setActionJobId(jobId);
        setError('');
        try {
            const result = await queueJobEvaluation(jobId, {
                deep_limit: 100,
                include_deep_evaluation: true,
                retry_failed_only: true,
            });
            if (result.progress) {
                setJobs((current) => current.map((row) => (
                    row.job.id === jobId ? { ...row, progress: result.progress, progressError: null } : row
                )));
            }
            await loadQueue({ silent: true });
        } catch (queueError) {
            console.error('Failed to retry failed evaluations', queueError);
            setError(queueError.message || 'Failed to retry failed evaluations');
        } finally {
            setActionJobId(null);
        }
    };

    return (
        <div className="max-w-7xl mx-auto space-y-6">
            <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
                <div>
                    <h1 className="heading-1">Reviewer Queue</h1>
                    <p className="mt-1 text-sm text-gray-500">
                        Review evaluation progress by job, then drill into outcomes and candidates.
                    </p>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                    <button
                        onClick={() => loadQueue({ silent: true })}
                        disabled={refreshing}
                        className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-100 text-gray-700 text-sm font-medium hover:bg-gray-200 disabled:opacity-50"
                    >
                        <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                        Refresh
                    </button>
                    <div className="flex items-center">
                        <button
                            onClick={() => setAnonymized(!anonymized)}
                            type="button"
                            className={`${anonymized ? 'bg-primary' : 'bg-gray-200'} relative inline-flex flex-shrink-0 h-6 w-11 border-2 border-transparent rounded-full cursor-pointer transition-colors ease-in-out duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary`}
                            role="switch"
                            aria-checked={anonymized}
                        >
                            <span className="sr-only">Toggle anonymized review</span>
                            <span
                                aria-hidden="true"
                                className={`${anonymized ? 'translate-x-5' : 'translate-x-0'} pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform ring-0 transition ease-in-out duration-200`}
                            />
                        </button>
                        <span className="ml-3 text-sm font-medium text-gray-900">Anonymized Review</span>
                    </div>
                </div>
            </div>

            {error && (
                <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4" />
                    {error}
                </div>
            )}

            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-3 flex flex-col lg:flex-row gap-3 lg:items-center justify-between">
                <div className="flex flex-wrap gap-2">
                    {FILTERS.map((item) => (
                        <button
                            key={item.id}
                            type="button"
                            onClick={() => setFilter(item.id)}
                            className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-semibold border transition-colors ${
                                filter === item.id
                                    ? 'bg-primary text-white border-primary'
                                    : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
                            }`}
                        >
                            {item.label}
                            <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                                filter === item.id ? 'bg-white/20 text-white' : 'bg-gray-100 text-gray-500'
                            }`}>
                                {filterCounts[item.id] || 0}
                            </span>
                        </button>
                    ))}
                </div>
                <div className="relative w-full lg:w-72">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                        type="search"
                        value={search}
                        onChange={(event) => setSearch(event.target.value)}
                        placeholder="Search jobs"
                        className="w-full pl-9 pr-3 py-2 rounded-lg border border-gray-200 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/10"
                    />
                </div>
            </div>

            {loading ? (
                <div className="card p-12 text-center text-gray-500">Loading queue...</div>
            ) : sortedJobs.length === 0 ? (
                <div className="card p-12 text-center text-gray-500">No jobs match this view.</div>
            ) : (
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
                    {sortedJobs.map(({ job, progress, progressError }) => {
                        const active = hasActivity(progress);
                        const percent = progressPercent(progress);
                        const totalSubmissions = Number(progress?.submissions_total || 0);
                        const outcomesTotal = Number(progress?.outcomes_total || job.outcomes?.length || 0);
                        const outcomesReady = Number(progress?.outcomes_evaluated || 0);
                        const failedCount = statusCount(progress, 'failed');
                        const readyReports = evaluatedOutcomes(progress);
                        const pendingOutcomes = (progress?.outcome_statuses || []).filter((outcome) => outcome.status !== 'evaluated');
                        const firstReport = readyReports[0];

                        return (
                            <div
                                key={job.id}
                                className={`bg-white rounded-xl border shadow-sm overflow-hidden ${active ? 'border-indigo-200 ring-1 ring-indigo-100' : 'border-gray-200'}`}
                            >
                                <div className="p-5 border-b border-gray-100">
                                    <div className="flex items-start justify-between gap-4">
                                        <div className="min-w-0">
                                            <div className="flex flex-wrap items-center gap-2">
                                                <h2 className="text-lg font-bold text-gray-900 truncate">{job.title}</h2>
                                                {active && (
                                                    <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700 border border-indigo-100">
                                                        <RefreshCw className="w-3 h-3 animate-spin" />
                                                        Processing
                                                    </span>
                                                )}
                                                {progress?.queue_backend && (
                                                    <span className="inline-flex items-center rounded-full bg-gray-50 px-2.5 py-1 text-xs font-medium text-gray-600 border border-gray-200">
                                                        Queue: {progress.queue_backend}
                                                    </span>
                                                )}
                                            </div>
                                            <div className="mt-2 flex flex-wrap gap-3 text-xs text-gray-500">
                                                <span className="inline-flex items-center gap-1">
                                                    <Briefcase className="w-3.5 h-3.5" />
                                                    {job.company}
                                                </span>
                                                <span className="inline-flex items-center gap-1">
                                                    <Users className="w-3.5 h-3.5" />
                                                    {totalSubmissions} submissions
                                                </span>
                                                <span className="inline-flex items-center gap-1">
                                                    <Layers className="w-3.5 h-3.5" />
                                                    {outcomesReady}/{outcomesTotal} outcomes ready
                                                </span>
                                                <span className="inline-flex items-center gap-1">
                                                    <Clock className="w-3.5 h-3.5" />
                                                    {job.created_at ? new Date(job.created_at).toLocaleDateString() : 'New'}
                                                </span>
                                            </div>
                                        </div>
                                        <Link
                                            to={`/jobs/${job.id}`}
                                            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gray-200 text-sm font-medium text-gray-700 hover:bg-gray-50 flex-shrink-0"
                                        >
                                            Job
                                            <ChevronRight className="w-4 h-4" />
                                        </Link>
                                    </div>

                                    <div className="mt-4 h-2 rounded-full bg-gray-100 overflow-hidden">
                                        <div
                                            className={`h-full rounded-full transition-all duration-500 ${active ? 'bg-indigo-500' : 'bg-primary'}`}
                                            style={{ width: `${active && percent === 0 ? 8 : percent}%` }}
                                        />
                                    </div>
                                </div>

                                {progressError ? (
                                    <div className="p-5 text-sm text-red-600 flex items-center gap-2">
                                        <AlertTriangle className="w-4 h-4" />
                                        Could not load progress for this job.
                                    </div>
                                ) : (
                                    <div className="p-5 space-y-4">
                                        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs">
                                            {STATUSES.map((status) => (
                                                <div key={status} className="rounded-lg bg-gray-50 border border-gray-100 px-3 py-2">
                                                    <div className="text-gray-400 capitalize">{status}</div>
                                                    <div className="font-bold text-gray-800">{statusCount(progress, status)}</div>
                                                </div>
                                            ))}
                                        </div>

                                        {progress?.top_candidates?.length > 0 && (
                                            <div className="flex flex-wrap gap-2">
                                                {progress.top_candidates.slice(0, 5).map((candidate) => (
                                                    <span key={candidate.candidate_id} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-primary-soft text-primary-hover text-xs font-semibold">
                                                        {candidate.candidate_id}: {Math.round(candidate.score || 0)}%
                                                    </span>
                                                ))}
                                            </div>
                                        )}

                                        {readyReports.length > 0 && (
                                            <div className="rounded-xl border border-green-100 bg-green-50/60 p-3">
                                                <div className="flex items-center justify-between gap-3 mb-2">
                                                    <div className="inline-flex items-center gap-2 text-sm font-bold text-green-800">
                                                        <FileText className="w-4 h-4" />
                                                        Reports Ready
                                                    </div>
                                                    <span className="text-xs font-semibold text-green-700">
                                                        {readyReports.length}/{outcomesTotal}
                                                    </span>
                                                </div>
                                                <div className="flex flex-wrap gap-2">
                                                    {readyReports.map((outcome) => (
                                                        <Link
                                                            key={outcome.outcome_id}
                                                            to={`/evaluation/${outcome.outcome_id}`}
                                                            state={{ anonymized }}
                                                            className="inline-flex max-w-full items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white text-green-800 border border-green-200 hover:border-green-300 hover:bg-green-100"
                                                        >
                                                            <CheckCircle className="w-3.5 h-3.5 shrink-0" />
                                                            <span className="truncate">{outcome.title}</span>
                                                            <span className="shrink-0 text-green-600">View Report</span>
                                                        </Link>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {pendingOutcomes.length > 0 && (
                                            <div className="flex flex-wrap gap-2">
                                                {pendingOutcomes.map((outcome) => (
                                                    <Link
                                                        key={outcome.outcome_id}
                                                        to={`/dashboard/${outcome.outcome_id}`}
                                                        state={{ anonymized }}
                                                        className="inline-flex max-w-full items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-gray-50 text-gray-600 border border-gray-200 hover:bg-gray-100"
                                                    >
                                                        <span className="truncate">{outcome.title}</span>
                                                        <span className="shrink-0">pending</span>
                                                    </Link>
                                                ))}
                                            </div>
                                        )}

                                        <div className="flex flex-wrap justify-between gap-2 pt-1">
                                            <div className="flex flex-wrap gap-2">
                                                <button
                                                    type="button"
                                                    onClick={() => handleEvaluate(job.id)}
                                                    disabled={actionJobId === job.id}
                                                    className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-hover disabled:opacity-50"
                                                >
                                                    {actionJobId === job.id ? (
                                                        <RefreshCw className="w-4 h-4 animate-spin" />
                                                    ) : (
                                                        <PlayCircle className="w-4 h-4" />
                                                    )}
                                                    Evaluate New Submissions
                                                </button>
                                                {failedCount > 0 && (
                                                    <button
                                                        type="button"
                                                        onClick={() => handleRetryFailed(job.id)}
                                                        disabled={actionJobId === job.id}
                                                        className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-red-50 text-red-700 border border-red-200 text-sm font-medium hover:bg-red-100 disabled:opacity-50"
                                                    >
                                                        {actionJobId === job.id ? (
                                                            <RefreshCw className="w-4 h-4 animate-spin" />
                                                        ) : (
                                                            <AlertTriangle className="w-4 h-4" />
                                                        )}
                                                        Retry Failed ({failedCount})
                                                    </button>
                                                )}
                                            </div>
                                            <Link
                                                to={firstReport ? `/evaluation/${firstReport.outcome_id}` : `/jobs/${job.id}#outcomes`}
                                                state={{ anonymized }}
                                                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-gray-100 text-gray-700 text-sm font-medium hover:bg-gray-200"
                                            >
                                                {firstReport ? 'View Reports' : 'View Outcomes'}
                                                <ChevronRight className="w-4 h-4" />
                                            </Link>
                                        </div>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
