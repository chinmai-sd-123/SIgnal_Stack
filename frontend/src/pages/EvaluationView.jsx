import React, { useEffect, useState, useMemo } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import { CheckCircle, AlertTriangle, XCircle, Shield, RotateCcw, Users, TrendingUp, Eye, BarChart3, Loader2 } from 'lucide-react';
import {
    Bar,
    BarChart,
    CartesianGrid,
    Legend,
    PolarAngleAxis,
    PolarGrid,
    PolarRadiusAxis,
    Radar,
    RadarChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from 'recharts';
import { submitFeedback, getEvaluation, resetDecision } from '../api';
import CandidateDetailView from './CandidateDetailView';
import FeedbackModal from '../components/FeedbackModal';

const CANDIDATE_COLORS = ['#0b5f66', '#0f766e', '#2d8c8f', '#6aa9a6', '#c9a227', '#f2e4b5'];

const formatSignalLabel = (index) => `S${index + 1}`;

const compactSignalTitle = (title = '', maxLength = 72) => {
    const cleanTitle = String(title || '').replace(/\s+/g, ' ').trim();
    if (!cleanTitle) return 'Untitled signal';
    if (cleanTitle.length <= maxLength) return cleanTitle;
    return `${cleanTitle.slice(0, maxLength - 1).trim()}...`;
};

export default function EvaluationView() {
    const { jobId } = useParams();
    const location = useLocation();
    const [evaluation, setEvaluation] = useState(null);
    const [loading, setLoading] = useState(true);
    const [processing, setProcessing] = useState(false); // Track action button state
    const [feedbackGiven, setFeedbackGiven] = useState(false);

    // NEW: Feedback Modal State
    const [feedbackModalOpen, setFeedbackModalOpen] = useState(false);
    const [lastAction, setLastAction] = useState({ type: null, candidate: null });

    // NEW: Track which candidate is being viewed in detail
    const [selectedCandidate, setSelectedCandidate] = useState(null);

    const anonymized = location.state?.anonymized || false;
    const partialReportInfo = useMemo(() => {
        const params = new URLSearchParams(location.search);
        if (params.get('report_status') !== 'stale') return null;

        return {
            current: Number(params.get('report_candidates') || 0),
            expected: Number(params.get('expected_candidates') || 0),
        };
    }, [location.search]);

    useEffect(() => {
        if (location.state?.result) {
            setEvaluation(location.state.result.evaluation);
            setLoading(false);
        } else {
            getEvaluation(jobId)
                .then(data => {
                    if (data.status === 'pending') {
                        setLoading(true);
                    } else if (data.evaluation) {
                        setEvaluation(data.evaluation);
                        if (data.evaluation.human_action_required === false) {
                            setFeedbackGiven(true);
                        }
                        setLoading(false);
                    } else {
                        setLoading(false);
                    }
                })
                .catch(err => {
                    console.error("Failed to load evaluation", err);
                    setLoading(false);
                });
        }
    }, [location.state, jobId]);

    const handleAction = async (action, candidateName = null) => {
        if (!evaluation || processing) return;
        setProcessing(true);
        try {
            let newCandidatesList = [];
            let newRejectedList = evaluation.decision?.rejected_candidates || [];

            // Get current list of hired candidates
            if (evaluation.decision?.selected_candidates) {
                newCandidatesList = [...evaluation.decision.selected_candidates];
            } else if (evaluation.decision?.selected_candidate) {
                newCandidatesList = [evaluation.decision.selected_candidate];
            }

            // Hiring Logic
            if (action === 'hire' && candidateName) {
                if (!newCandidatesList.includes(candidateName)) {
                    newCandidatesList.push(candidateName);
                    // Remove from rejected if present
                    newRejectedList = newRejectedList.filter(c => c !== candidateName);
                }
            } else if (action === 'reject' && candidateName) {
                if (!newRejectedList.includes(candidateName)) {
                    newRejectedList.push(candidateName);
                    // Remove from hired if present
                    newCandidatesList = newCandidatesList.filter(c => c !== candidateName);
                }
            } else if (action === 'reject_all') {
                newCandidatesList = []; // Clear list
            }

            await submitFeedback({
                job_id: evaluation.job_id,
                evaluation_id: "eval_123",
                result: action.includes('hire') ? 'success' : 'failure',
                metrics: {
                    action_taken: action === 'reject_all' ? 'reject_all' : (action === 'reject' ? 'reject' : 'hire'),
                    selected_candidates: newCandidatesList,
                    rejected_candidates: newRejectedList,
                    selected_candidate: newCandidatesList.length > 0 ? newCandidatesList[0] : null
                }
            });

            // Update local state immediately
            setFeedbackGiven(true);
            setEvaluation(prev => ({
                ...prev,
                decision: {
                    action_taken: action === 'reject_all' ? 'reject_all' : (action === 'reject' ? 'reject' : 'hire'),
                    selected_candidates: newCandidatesList,
                    rejected_candidates: newRejectedList,
                    selected_candidate: newCandidatesList.length > 0 ? newCandidatesList[0] : null
                }
            }));

            setSelectedCandidate(null); // Return to dashboard

            // TRIGGER FEEDBACK MODAL
            if (action === 'hire' || action === 'reject' || action === 'reject_all') {
                setLastAction({ type: action, candidate: candidateName });
                setFeedbackModalOpen(true);
            }

        } catch (error) {
            console.error("Failed to submit feedback", error);
            alert("Failed to submit decision: " + error.message);
        } finally {
            setProcessing(false);
        }
    };

    // ... utility functions ...
    const getScoreColor = (score) => {
        if (score >= 0.7) return 'text-primary';
        if (score >= 0.4) return 'text-amber-700';
        return 'text-rose-700';
    };

    const getConfidenceBadge = (rating) => {
        const styles = {
            'High': 'bg-primary-soft text-primary border-primary/20',
            'Medium': 'bg-accent-soft text-amber-800 border-accent/25',
            'Low': 'bg-rose-50 text-rose-700 border-rose-200'
        };
        return styles[rating] || styles['Medium'];
    };

    const getVerificationBadge = (status) => {
        const styles = {
            verified: 'bg-primary-soft text-primary border-primary/20',
            unverified: 'bg-accent-soft text-amber-800 border-accent/25',
            conflict: 'bg-rose-50 text-rose-700 border-rose-200',
        };
        return styles[status] || styles.unverified;
    };

    const formatStatus = (value) => (value || 'unverified').replace(/_/g, ' ');

    // Memoize summaries to prevent recalculation on every render
    const fallbackSummaries = useMemo(() => {
        if (!evaluation) return [];

        // Use backend summaries if available
        if (evaluation.candidate_summaries?.length > 0) {
            return evaluation.candidate_summaries;
        }

        // Robust fallback logic
        const allocations = evaluation.work_allocation || [];
        if (allocations.length === 0) return [];

        const uniqueCandidates = [...new Set(allocations.map(a => a.recommended_candidate))]
            .filter(name => name && name !== 'None' && name !== 'null');

        return uniqueCandidates.map(candidateName => {
            const wonTasks = allocations.filter(a => a.recommended_candidate === candidateName);
            const avgConf = wonTasks.length > 0
                ? wonTasks.reduce((acc, t) => acc + t.confidence, 0) / wonTasks.length
                : 0;

                            return {
                                candidate_id: candidateName,
                                overall_score: avgConf,
                                capability_score: avgConf,
                                evidence_confidence: null,
                                production_readiness: null,
                                verification_status: 'unverified',
                                tasks_won: wonTasks.length,
                                dimensions: evaluation.dimensions,
                                confidence_rating: avgConf > 0.7 ? 'High' : avgConf > 0.4 ? 'Medium' : 'Low'
            };
        }).sort((a, b) => b.overall_score - a.overall_score); // Sort by highest score
    }, [evaluation]);

    const comparisonCandidates = useMemo(
        () => fallbackSummaries.slice(0, CANDIDATE_COLORS.length).map(candidate => candidate.candidate_id),
        [fallbackSummaries]
    );

    const batchAverageScore = useMemo(() => {
        if (!fallbackSummaries.length) return null;
        const total = fallbackSummaries.reduce(
            (sum, candidate) => sum + Number(candidate.overall_score || 0),
            0
        );
        return total / fallbackSummaries.length;
    }, [fallbackSummaries]);

    const comparisonData = useMemo(() => {
        const allocations = evaluation?.work_allocation || [];

        return allocations.map((alloc, index) => {
            const row = {
                task: formatSignalLabel(index),
                task_title: alloc.task_title || `Signal ${index + 1}`,
            };

            comparisonCandidates.forEach(candidateId => {
                const candidateScore = alloc.top_candidates?.find(tc => tc.candidate_id === candidateId);
                if (candidateScore) {
                    row[candidateId] = candidateScore.score;
                } else if (alloc.recommended_candidate === candidateId) {
                    row[candidateId] = alloc.confidence || 0;
                } else {
                    row[candidateId] = 0;
                }
            });

            return row;
        });
    }, [evaluation, comparisonCandidates]);

    if (loading) return (
        // ... loading state ...
        <div className="flex flex-col items-center justify-center min-h-[60vh]">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent mb-4"></div>
            <h2 className="heading-2">Evaluating Proofs...</h2>
            <p className="text-gray-500 mt-2">Extracting signals • Allocating tasks • Verifying constraints</p>
        </div>
    );

    if (!evaluation) return (
        // ... error state ...
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-8">
            <AlertTriangle className="w-12 h-12 text-yellow-500 mb-4" />
            <h2 className="heading-2">Evaluation Not Ready</h2>
            <p className="text-gray-500 mt-2 max-w-md">The system is still processing signals. Please wait a moment.</p>
            <button onClick={() => window.location.reload()} className="btn btn-primary mt-6">
                Refresh Status
            </button>
        </div>
    );

    // If a candidate is selected, show their detail view
    if (selectedCandidate) {
        const candidateData = fallbackSummaries.find(c => c.candidate_id === selectedCandidate);
        if (!candidateData) {
            setSelectedCandidate(null); // Safety fallback
            return null;
        }
        return (
            <CandidateDetailView
                candidate={candidateData}
                jobId={evaluation.job_id}
                allAllocations={evaluation.work_allocation || []}
                allSummaries={fallbackSummaries}
                onBack={() => setSelectedCandidate(null)}
                onHire={(name) => handleAction('hire', name)}
                onReject={(name) => handleAction('reject', name)}
                processing={processing}
            />
        );
    }

    // DASHBOARD VIEW
    return (
        <div className="max-w-7xl mx-auto px-4 py-8 flex items-start gap-8">

            {/* NEW: Sticky Sidebar Navigation (Desktop) */}
            <nav className="hidden lg:block w-64 sticky top-8 bg-white/80 rounded-xl border border-gray-200 shadow-sm p-4 space-y-1 backdrop-blur">
                <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest px-3 mb-2">Navigation</h3>
                <a href="#dashboard" className="flex items-center gap-3 px-3 py-2 text-sm font-medium text-text-secondary hover:bg-primary-soft hover:text-primary rounded-lg transition-colors">
                    <BarChart3 className="w-4 h-4" />
                    Dashboard
                </a>
                <a href="#decision" className="flex items-center gap-3 px-3 py-2 text-sm font-medium text-text-secondary hover:bg-primary-soft hover:text-primary rounded-lg transition-colors">
                    <CheckCircle className="w-4 h-4" />
                    Hiring Decision
                </a>
                <a href="#candidates" className="flex items-center gap-3 px-3 py-2 text-sm font-medium text-text-secondary hover:bg-primary-soft hover:text-primary rounded-lg transition-colors">
                    <Users className="w-4 h-4" />
                    Evaluated Candidates
                </a>
                <a href="#comparison" className="flex items-center gap-3 px-3 py-2 text-sm font-medium text-text-secondary hover:bg-primary-soft hover:text-primary rounded-lg transition-colors">
                    <TrendingUp className="w-4 h-4" />
                    Comparison
                </a>
                <a href="#signals" className="flex items-center gap-3 px-3 py-2 text-sm font-medium text-text-secondary hover:bg-primary-soft hover:text-primary rounded-lg transition-colors">
                    <Shield className="w-4 h-4" />
                    System Signals
                </a>
            </nav>

            {/* Main Content Area */}
            <div className="flex-1 min-w-0 space-y-8">

                {/* Header */}
                <div id="dashboard" className="mb-8 scroll-mt-8">
                    <h1 className="text-3xl font-bold text-text-primary">{evaluation.job_title || 'Evaluation Dashboard'}</h1>
                    <p className="text-text-secondary mt-1 font-mono text-sm">Job ID: {evaluation.job_id}</p>
                    {anonymized && (
                        <div className="mt-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-soft text-primary">
                            <Shield className="w-3 h-3 mr-1" /> Anonymized Mode
                        </div>
                    )}
                </div>

                {partialReportInfo && (
                    <div className="rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-amber-900 shadow-sm">
                        <div className="flex items-start gap-3">
                            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
                            <div className="min-w-0">
                                <div className="font-bold">Partial report shown</div>
                                <p className="mt-1 text-sm text-amber-800">
                                    This report currently includes {partialReportInfo.current}/{partialReportInfo.expected || partialReportInfo.current} evaluated candidates.
                                    New candidate results are being refreshed in the job queue, so the complete report will replace this once ready.
                                </p>
                            </div>
                        </div>
                    </div>
                )}

                {/* Fit Score Summary Card */}
                <div className="hero-gradient rounded-2xl p-8 text-white mb-8 shadow-xl">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                        <div>
                            <h2 className="text-lg font-medium opacity-80">Top Fit Score</h2>
                            <div className="flex items-baseline gap-2 mt-2">
                                <span className="text-5xl font-black">{Math.round(evaluation.fit_score * 100)}</span>
                                <span className="text-2xl font-medium opacity-70">%</span>
                            </div>
                            <p className="text-sm opacity-70 mt-2">
                                Best candidate score across {evaluation.work_allocation.length} tasks
                            </p>
                            <div className="mt-4 grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs">
                                <div className="bg-white/15 rounded-lg px-3 py-2">
                                    <div className="opacity-70">Batch Avg</div>
                                    <div className="font-bold">{batchAverageScore != null ? `${Math.round(batchAverageScore * 100)}%` : 'N/A'}</div>
                                </div>
                                <div className="bg-white/15 rounded-lg px-3 py-2">
                                    <div className="opacity-70">Capability</div>
                                    <div className="font-bold">{Math.round((evaluation.capability_score ?? evaluation.fit_score) * 100)}%</div>
                                </div>
                                <div className="bg-white/15 rounded-lg px-3 py-2">
                                    <div className="opacity-70">Evidence</div>
                                    <div className="font-bold">{evaluation.evidence_confidence != null ? `${Math.round(evaluation.evidence_confidence * 100)}%` : 'N/A'}</div>
                                </div>
                                <div className="bg-white/15 rounded-lg px-3 py-2">
                                    <div className="opacity-70">Production</div>
                                    <div className="font-bold">{evaluation.production_readiness != null ? `${Math.round(evaluation.production_readiness * 100)}%` : 'N/A'}</div>
                                </div>
                                <div className="bg-white/15 rounded-lg px-3 py-2">
                                    <div className="opacity-70">Verification</div>
                                    <div className="font-bold capitalize">{formatStatus(evaluation.verification_status)}</div>
                                </div>
                            </div>
                        </div>
                        <div className="flex flex-col items-end gap-2">
                            <div className="flex items-center gap-2 bg-white/20 rounded-full px-4 py-2">
                                <Users className="w-5 h-5" />
                                <span className="font-semibold">{fallbackSummaries.length} Candidates Evaluated</span>
                            </div>
                            <div className="text-sm opacity-70">
                                {evaluation.global_signals_used?.length || 0} signals analyzed
                            </div>
                        </div>
                    </div>
                </div>

                {/* Decision Panel - Prominently Placed */}
                <div id="decision" className="bg-white rounded-2xl border-2 border-primary/30 shadow-lg p-8 mb-8 scroll-mt-24">
                    <div className="flex items-center gap-3 mb-6">
                        <div className="w-10 h-10 bg-primary-soft rounded-xl flex items-center justify-center">
                            <CheckCircle className="w-6 h-6 text-primary" />
                        </div>
                        <h2 className="text-2xl font-bold text-text-primary">Hiring Decision</h2>
                    </div>

                    {feedbackGiven ? (
                        <div className="text-center py-6">
                            <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
                            <p className="text-xl font-semibold text-gray-900">Decision Recorded</p>
                            <p className="text-text-secondary mt-2">
                                {(() => {
                                    const hiredList = evaluation.decision?.selected_candidates ||
                                        (evaluation.decision?.selected_candidate ? [evaluation.decision.selected_candidate] : []);

                                    if (hiredList.length > 0) {
                                        return `Selected (${hiredList.length}): ${hiredList.join(', ')}`;
                                    }
                                    return evaluation.decision?.action_taken === 'reject_all' ? 'Rejected All candidates' : 'Decision recorded';
                                })()}
                            </p>
                            <button
                                onClick={async () => {
                                    if (window.confirm('Are you sure you want to change your decision?')) {
                                        try {
                                            await resetDecision(evaluation.job_id);
                                            setFeedbackGiven(false);
                                            // Reset local state to reflect change immediately
                                            setEvaluation(prev => ({ ...prev, decision: null }));
                                            alert('Decision reset.');
                                        } catch (e) {
                                            alert('Error: ' + e.message);
                                        }
                                    }
                                }}
                                className="btn btn-secondary mt-6"
                            >
                                <RotateCcw className="w-4 h-4 mr-2" />
                                Change Decision
                            </button>
                        </div>
                    ) : (
                        <div>
                            <p className="text-text-secondary mb-6">
                                Select a candidate below to view their detailed report, or make a quick decision here.
                            </p>
                            <div className="flex flex-wrap items-center gap-3">
                                <button
                                    onClick={() => handleAction('reject_all')}
                                    disabled={processing}
                                    className="btn bg-white text-red-600 border-2 border-red-200 hover:bg-red-50 px-6 py-2.5 disabled:opacity-50 flex items-center justify-center gap-2 text-sm font-semibold"
                                >
                                    <XCircle className="w-4 h-4" />
                                    Reject All
                                </button>
                            </div>
                        </div>
                    )}
                </div>

                {/* Candidates Section */}
                <div id="candidates" className="mb-8 scroll-mt-24">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-xl font-bold text-text-primary flex items-center gap-2">
                            <Users className="w-6 h-6 text-primary" />
                            Evaluated Candidates
                        </h2>
                        <span className="text-sm text-text-secondary font-medium bg-primary-soft px-3 py-1 rounded-full">
                            Showing All ({fallbackSummaries.length})
                        </span>
                    </div>

                    {fallbackSummaries.length === 0 ? (
                        <div className="bg-gray-50 rounded-xl p-8 text-center border border-gray-200 border-dashed">
                            <Users className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                            <p className="text-gray-500">No candidates matched the requirements.</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                            {fallbackSummaries.map((candidate, idx) => (
                                <div
                                    key={candidate.candidate_id}
                                    className="bg-[rgba(255,253,248,0.96)] rounded-xl border border-light-200 shadow-card hover:shadow-hover hover:border-primary/40 transition-all overflow-hidden flex flex-col min-h-[336px]"
                                >
                                    {/* Rank Badge */}
                                    {idx < 3 && (
                                        <div className={`h-1 ${idx === 0 ? 'bg-accent' : idx === 1 ? 'bg-gray-300' : 'bg-primary'}`}></div>
                                    )}

                                    <div className="p-6 flex flex-1 flex-col">
                                        <div className="grid grid-cols-[48px_minmax(0,1fr)_auto] items-start gap-3 mb-5">
                                            <div className="w-12 h-12 bg-gradient-to-br from-primary to-accent rounded-xl flex items-center justify-center text-white text-lg font-bold shadow-sm">
                                                {candidate.candidate_id.charAt(0).toUpperCase()}
                                            </div>
                                            <div className="min-w-0">
                                                <h3 className="font-bold leading-tight text-gray-900 truncate" title={candidate.candidate_id}>
                                                    {candidate.candidate_id}
                                                </h3>
                                                <div className="mt-2 flex min-h-[48px] flex-wrap content-start gap-1.5">
                                                    <span className={`inline-flex items-center whitespace-nowrap px-2 py-0.5 rounded-full text-xs font-medium border ${getConfidenceBadge(candidate.confidence_rating)}`}>
                                                        {candidate.confidence_rating}
                                                    </span>
                                                    <span className={`inline-flex items-center whitespace-nowrap px-2 py-0.5 rounded-full text-xs font-medium border capitalize ${getVerificationBadge(candidate.verification_status)}`}>
                                                        {formatStatus(candidate.verification_status)}
                                                    </span>
                                                </div>
                                            </div>
                                            <span className={`shrink-0 text-right text-2xl font-bold leading-none tabular-nums ${getScoreColor(candidate.overall_score)}`}>
                                                {Math.round(candidate.overall_score * 100)}%
                                            </span>
                                        </div>

                                        <div className="text-sm text-gray-600 mb-6">
                                            <div className="mb-3 min-h-[22px]">
                                                <span className="font-semibold text-gray-900">{candidate.tasks_won}</span> tasks passed
                                            </div>
                                            <div className="grid grid-cols-3 gap-2 text-xs">
                                                <div className="min-w-0 rounded-lg bg-gray-50 border border-gray-100 px-2 py-2">
                                                    <div className="truncate text-gray-400">Capability</div>
                                                    <div className="font-semibold text-gray-800 tabular-nums">{Math.round((candidate.capability_score ?? candidate.overall_score) * 100)}%</div>
                                                </div>
                                                <div className="min-w-0 rounded-lg bg-gray-50 border border-gray-100 px-2 py-2">
                                                    <div className="truncate text-gray-400">Evidence</div>
                                                    <div className="font-semibold text-gray-800 tabular-nums">{candidate.evidence_confidence != null ? `${Math.round(candidate.evidence_confidence * 100)}%` : 'N/A'}</div>
                                                </div>
                                                <div className="min-w-0 rounded-lg bg-gray-50 border border-gray-100 px-2 py-2">
                                                    <div className="truncate text-gray-400">Production</div>
                                                    <div className="font-semibold text-gray-800 tabular-nums">{candidate.production_readiness != null ? `${Math.round(candidate.production_readiness * 100)}%` : 'N/A'}</div>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="flex flex-col gap-2 mt-auto">
                                            <button
                                                onClick={() => setSelectedCandidate(candidate.candidate_id)}
                                                disabled={processing}
                                                className="w-full btn bg-primary-soft text-primary hover:bg-primary/10 border border-primary/30 py-2.5 text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-2"
                                            >
                                                <Eye className="w-4 h-4" />
                                                View Report
                                            </button>

                                            {/* Show Hire Button OR Hired/Rejected Status */}
                                            {(() => {
                                                const hiredList = evaluation.decision?.selected_candidates ||
                                                    (evaluation.decision?.selected_candidate ? [evaluation.decision.selected_candidate] : []);
                                                const rejectedList = evaluation.decision?.rejected_candidates || [];

                                                const isHired = hiredList.includes(candidate.candidate_id);
                                                const isRejected = rejectedList.includes(candidate.candidate_id);
                                                const isRejectAll = evaluation.decision?.action_taken === 'reject_all';

                                                if (isHired) {
                                                    return (
                                                        <div className="w-full px-4 py-2.5 bg-primary-soft text-primary border border-primary/20 rounded-lg flex items-center justify-center gap-2 font-bold text-sm">
                                                            <CheckCircle className="w-4 h-4" /> HIRED
                                                        </div>
                                                    );
                                                }

                                                if (isRejected || isRejectAll) {
                                                    return (
                                                        <div className="w-full px-4 py-2.5 bg-red-100 text-red-700 border border-red-200 rounded-lg flex items-center justify-center gap-2 text-sm font-medium">
                                                            <XCircle className="w-4 h-4" /> Rejected
                                                        </div>
                                                    );
                                                }

                                                // Default: Show Hire Button
                                                return (
                                                    <button
                                                        onClick={() => handleAction('hire', candidate.candidate_id)}
                                                        disabled={processing}
                                                        className="w-full btn btn-primary py-2.5 text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-2"
                                                    >
                                                        {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : <><CheckCircle className="w-4 h-4" /> Proceed to Interview</>}
                                                    </button>
                                                );
                                            })()}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Candidate Comparison Panel */}
                <div id="comparison" className="bg-[rgba(255,253,248,0.95)] rounded-2xl border border-gray-200 shadow-card p-5 sm:p-6 mb-8 scroll-mt-24">
                    <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <TrendingUp className="w-5 h-5 text-primary" />
                        Candidate Comparison
                    </h3>

                    {fallbackSummaries.length < 2 || comparisonData.length === 0 ? (
                        <div className="bg-gray-50 rounded-lg p-6 text-center text-gray-500 border border-gray-100">
                            <Users className="w-8 h-8 mx-auto mb-2 opacity-50" />
                            <p>Only one candidate evaluated. Comparison unavailable.</p>
                            <p className="text-xs mt-1">Add more candidates to see side-by-side performance.</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                            <div className="rounded-2xl border border-light-200 bg-white/70 p-4 shadow-sm">
                                <div className="mb-3 flex items-center justify-between gap-3">
                                    <h4 className="text-sm font-bold text-gray-900">Candidate Skill Overview</h4>
                                    <span className="rounded-full border border-primary/15 bg-primary-soft px-2.5 py-1 text-[11px] font-bold text-primary">
                                        Top {comparisonCandidates.length}
                                    </span>
                                </div>
                                <div className="h-80 w-full overflow-hidden rounded-xl bg-white/60">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <RadarChart
                                            cx="50%"
                                            cy="48%"
                                            outerRadius="62%"
                                            data={comparisonData}
                                            margin={{ top: 18, right: 28, bottom: 18, left: 28 }}
                                        >
                                            <PolarGrid stroke="#e6e1d7" />
                                            <PolarAngleAxis
                                                dataKey="task"
                                                tick={{ fill: '#475569', fontSize: 12, fontWeight: 700 }}
                                            />
                                            <PolarRadiusAxis
                                                angle={30}
                                                domain={[0, 1]}
                                                tick={{ fill: '#94a3b8', fontSize: 11 }}
                                                tickFormatter={(value) => `${Math.round(value * 100)}%`}
                                            />
                                            <Tooltip
                                                formatter={(value) => `${Math.round(value * 100)}%`}
                                                labelFormatter={(label, payload) => {
                                                    const title = payload?.[0]?.payload?.task_title;
                                                    return `${label}: ${title || 'Signal'}`;
                                                }}
                                                contentStyle={{
                                                    borderRadius: '0.75rem',
                                                    border: '1px solid #e6e1d7',
                                                    boxShadow: '0 10px 30px rgba(15, 23, 42, 0.12)',
                                                }}
                                            />
                                            <Legend wrapperStyle={{ fontSize: 12, paddingTop: 10 }} />
                                            {comparisonCandidates.map((candidate, index) => (
                                                <Radar
                                                    key={candidate}
                                                    name={candidate}
                                                    dataKey={candidate}
                                                    stroke={CANDIDATE_COLORS[index % CANDIDATE_COLORS.length]}
                                                    fill={CANDIDATE_COLORS[index % CANDIDATE_COLORS.length]}
                                                    fillOpacity={0.4}
                                                />
                                            ))}
                                        </RadarChart>
                                    </ResponsiveContainer>
                                </div>
                                <div className="mt-4 grid grid-cols-1 gap-2">
                                    {comparisonData.map((row) => (
                                        <div key={row.task} className="flex gap-2 rounded-lg border border-light-200 bg-white/70 px-3 py-2 text-xs">
                                            <span className="shrink-0 font-bold text-primary">{row.task}</span>
                                            <span className="min-w-0 text-text-secondary" title={row.task_title}>
                                                {compactSignalTitle(row.task_title)}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="rounded-2xl border border-light-200 bg-white/70 p-4 shadow-sm">
                                <h4 className="text-sm font-bold text-gray-900 mb-3">Task Confidence Breakdown</h4>
                                <div className="h-80 w-full">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <BarChart data={comparisonData} margin={{ top: 20, right: 24, left: 0, bottom: 8 }}>
                                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e6e1d7" />
                                            <XAxis
                                                dataKey="task"
                                                tick={{ fill: '#475569', fontSize: 12, fontWeight: 700 }}
                                                axisLine={false}
                                                tickLine={false}
                                            />
                                            <YAxis
                                                domain={[0, 1]}
                                                tick={{ fill: '#9ca3af' }}
                                                axisLine={false}
                                                tickLine={false}
                                                tickFormatter={(value) => `${Math.round(value * 100)}%`}
                                            />
                                            <Tooltip
                                                formatter={(value) => `${Math.round(value * 100)}%`}
                                                labelFormatter={(label, payload) => {
                                                    const title = payload?.[0]?.payload?.task_title;
                                                    return `${label}: ${title || 'Signal'}`;
                                                }}
                                                contentStyle={{
                                                    borderRadius: '0.75rem',
                                                    border: '1px solid #e6e1d7',
                                                    boxShadow: '0 10px 30px rgba(15, 23, 42, 0.12)',
                                                }}
                                            />
                                            <Legend wrapperStyle={{ fontSize: 12 }} />
                                            {comparisonCandidates.map((candidate, index) => (
                                                <Bar
                                                    key={candidate}
                                                    name={candidate}
                                                    dataKey={candidate}
                                                    fill={CANDIDATE_COLORS[index % CANDIDATE_COLORS.length]}
                                                    radius={[4, 4, 0, 0]}
                                                    maxBarSize={40}
                                                />
                                            ))}
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* System Signals */}
                <div id="signals" className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 scroll-mt-24">
                    <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <Shield className="w-5 h-5 text-primary" />
                        System Signals Analysis
                    </h3>
                    <div className="flex flex-wrap gap-2">
                        {evaluation.global_signals_used?.map((signal) => (
                            <span key={signal} className="px-3 py-1.5 bg-primary-soft text-primary rounded-lg text-sm border border-primary/20 font-mono hover:bg-primary/10 transition-colors">
                                {signal}
                            </span>
                        ))}
                        {(!evaluation.global_signals_used || evaluation.global_signals_used.length === 0) && (
                            <span className="text-gray-400 text-sm italic">No specific signals were triggered during this evaluation.</span>
                        )}
                    </div>
                </div>

            </div>

            {/* FEEDBACK MODAL */}
            <FeedbackModal
                isOpen={feedbackModalOpen}
                onClose={() => setFeedbackModalOpen(false)}
                job={{ id: evaluation?.job_id }}
                candidateName={lastAction.candidate}
                action={lastAction.type || 'hire'}
                tasks={[...new Set(evaluation?.work_allocation?.map(a => a.task_title) || [])]}
            />
        </div>
    );
}
