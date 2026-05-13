import React, { useState, useMemo } from 'react';
import DimensionChart from '../components/DimensionChart';
import EvidenceItem from '../components/EvidenceItem';
import FeedbackModal from '../components/FeedbackModal'; // Import Feedback Modal
import { ArrowLeft, Award, TrendingUp, CheckCircle, XCircle, ExternalLink, ChevronDown, ChevronUp, BarChart3, Loader2, Trophy, Medal, Lightbulb } from 'lucide-react';

function evidenceRank(evidence) {
    const ref = evidence?.ref || evidence?.reference || '';
    const type = evidence?.type || '';
    if (ref.startsWith('AI_FINDING:')) return 0;
    if (type === 'code_snippet' || type === 'file_ref' || ref.startsWith('FILE:') || ref.startsWith('CODE:') || ref.startsWith('ENTRY:')) return 1;
    if (type === 'work_artifact' || ref.startsWith('ARTIFACT:')) return 2;
    if (ref.startsWith('REPO:') || ref === 'REPOSITORY') return 3;
    if (ref.startsWith('AUTH:') || ref === 'GIT_LOG' || type === 'authorship_context') return 4;
    if (ref.startsWith('SCAN:') || ref === 'PROJECT_SCAN' || type === 'project_health') return 5;
    return 6;
}

function orderEvidence(items = []) {
    return [...items].sort((a, b) => evidenceRank(a) - evidenceRank(b));
}

/**
 * CandidateDetailView - Shows detailed evaluation for a single candidate.
 * Props:
 *   - candidate: CandidateSummary object
 *   - allocations: WorkAllocation[] (filtered for this candidate)
 *   - onBack: function to return to dashboard
 *   - onHire: function to hire this candidate
 *   - onReject: function to reject this candidate
 */
export default function CandidateDetailView({ candidate, allAllocations, allSummaries, processing, onBack, onHire, onReject, jobId }) {
    const [expandedTask, setExpandedTask] = useState(null);
    const [isFeedbackModalOpen, setIsFeedbackModalOpen] = useState(false);

    // Calculate Average Dimensions across all candidates
    const averageDimensions = useMemo(() => {
        if (!allSummaries || allSummaries.length === 0) return null;

        const totals = {
            project_completion: 0,
            engineering_quality: 0,
            communication: 0,
            innovation: 0,
            depth_novelty: 0
        };
        // Count valid dimension entries
        let count = 0;

        allSummaries.forEach(c => {
            if (c.dimensions) {
                totals.project_completion += c.dimensions.project_completion || 0;
                totals.engineering_quality += c.dimensions.engineering_quality || 0;
                totals.communication += c.dimensions.communication || 0;
                totals.innovation += c.dimensions.innovation || 0;
                totals.depth_novelty += c.dimensions.depth_novelty || 0;
                count++;
            }
        });

        if (count === 0) return null;

        return {
            project_completion: totals.project_completion / count,
            engineering_quality: totals.engineering_quality / count,
            communication: totals.communication / count,
            innovation: totals.innovation / count,
            depth_novelty: totals.depth_novelty / count
        };
    }, [allSummaries]);

    if (!candidate) return null;

    // Get tasks where this candidate is recommended OR scored well
    const relevantAllocations = allAllocations.filter(alloc => {
        // Task where this candidate is the winner
        if (alloc.recommended_candidate === candidate.candidate_id) return true;
        // Or where this candidate is in top_candidates
        if (alloc.top_candidates?.some(tc => tc.candidate_id === candidate.candidate_id)) return true;
        return false;
    });

    const getScoreColor = (score) => {
        if (score >= 0.7) return 'text-primary';
        if (score >= 0.4) return 'text-amber-700';
        return 'text-rose-700';
    };

    const getTaskMatchLabel = (score, isWinner) => {
        if (score >= 0.7) return isWinner ? 'Strongest Match' : 'Strong Match';
        if (score >= 0.45) return isWinner ? 'Top Partial Match' : 'Partial Match';
        if (score >= 0.2) return isWinner ? 'Top Weak Evidence' : 'Weak Evidence';
        return 'Insufficient Evidence';
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
            conflict: 'bg-rose-50 text-rose-700 border-rose-200'
        };
        return styles[status] || styles.unverified;
    };

    const formatStatus = (value) => (value || 'unverified').replace(/_/g, ' ');

    return (
        <div className="max-w-5xl mx-auto px-4 py-6">
            {/* Back Button */}
            <button
                onClick={onBack}
                className="flex items-center gap-2 text-text-secondary hover:text-primary mb-6 transition-colors"
            >
                <ArrowLeft className="w-5 h-5" />
                <span className="font-medium">Back to Dashboard</span>
            </button>

            {/* Candidate Header Card */}
            <div className="bg-[rgba(255,253,248,0.96)] rounded-2xl border border-light-200 shadow-card overflow-hidden mb-8">
                {/* Gradient Top Bar */}
                <div className="h-2 bg-gradient-to-r from-primary via-primary-hover to-accent"></div>

                <div className="p-8">
                    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                        {/* Left: Name & Score */}
                        <div className="flex items-center gap-6">
                            <div className="w-20 h-20 bg-gradient-to-br from-primary to-accent rounded-2xl flex items-center justify-center text-white text-2xl font-bold shadow-lg">
                                {candidate.candidate_id.charAt(0).toUpperCase()}
                            </div>
                            <div>
                                <h1 className="text-2xl font-bold text-gray-900">{candidate.candidate_id}</h1>
                                <div className="flex items-center gap-3 mt-2">
                                    <span className={`text-3xl font-bold ${getScoreColor(candidate.overall_score)}`}>
                                        {Math.round(candidate.overall_score * 100)}%
                                    </span>
                                    <span className={`px-3 py-1 rounded-full text-sm font-medium border ${getConfidenceBadge(candidate.confidence_rating)}`}>
                                        {candidate.confidence_rating} Confidence
                                    </span>
                                    <span className={`px-3 py-1 rounded-full text-sm font-medium border capitalize ${getVerificationBadge(candidate.verification_status)}`}>
                                        {formatStatus(candidate.verification_status)}
                                    </span>
                                </div>
                                <p className="text-gray-500 mt-1">
                                    Top candidate on <strong>{candidate.tasks_won}</strong> of {relevantAllocations.length || 'N/A'} signals
                                </p>
                                <div className="mt-4 grid grid-cols-3 gap-2 text-xs max-w-md">
                                    <div className="rounded-lg bg-gray-50 border border-gray-100 px-3 py-2">
                                        <div className="text-gray-400">Capability</div>
                                        <div className="font-semibold text-gray-800">{Math.round((candidate.capability_score ?? candidate.overall_score) * 100)}%</div>
                                    </div>
                                    <div className="rounded-lg bg-gray-50 border border-gray-100 px-3 py-2">
                                        <div className="text-gray-400">Evidence</div>
                                        <div className="font-semibold text-gray-800">{candidate.evidence_confidence != null ? `${Math.round(candidate.evidence_confidence * 100)}%` : 'N/A'}</div>
                                    </div>
                                    <div className="rounded-lg bg-gray-50 border border-gray-100 px-3 py-2">
                                        <div className="text-gray-400">Production</div>
                                        <div className="font-semibold text-gray-800">{candidate.production_readiness != null ? `${Math.round(candidate.production_readiness * 100)}%` : 'N/A'}</div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Right: Action Buttons */}
                        <div className="flex flex-wrap items-center gap-3">
                            {/* Feedback Button */}
                            <button
                                onClick={() => setIsFeedbackModalOpen(true)}
                                className="btn bg-white hover:bg-primary-soft text-primary border-2 border-primary px-5 py-2.5 rounded-xl font-semibold flex items-center justify-center gap-2 transition-all text-sm"
                            >
                                <Lightbulb className="w-4 h-4" />
                                Give Feedback
                            </button>

                            <button
                                onClick={() => onHire(candidate.candidate_id)}
                                disabled={processing}
                                className="btn btn-primary px-6 py-2.5 rounded-xl font-semibold flex items-center justify-center gap-2 shadow-md hover:shadow-lg transition-all disabled:opacity-50 text-sm"
                            >
                                {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                                Proceed to Interview
                            </button>
                            <button
                                onClick={() => onReject(candidate.candidate_id)}
                                disabled={processing}
                                className="btn bg-white hover:bg-red-50 text-red-600 border-2 border-red-200 px-5 py-2.5 rounded-xl font-semibold flex items-center justify-center gap-2 transition-all disabled:opacity-50 text-sm"
                            >
                                <XCircle className="w-4 h-4" />
                                Reject
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Two Column Layout: Dimensions + Tasks */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

                {/* Left Column: Skill Dimensions */}
                <div className="lg:col-span-1">
                    <div className="bg-[rgba(255,253,248,0.95)] rounded-2xl border border-gray-200 shadow-card p-4 sm:p-5 sticky top-6">
                        <h3 className="text-lg font-semibold text-gray-900 mb-5 flex items-center gap-2">
                            <BarChart3 className="w-5 h-5 text-primary" />
                            Skill Dimensions
                        </h3>
                        {candidate.dimensions ? (
                            <DimensionChart dimensions={candidate.dimensions} averageDimensions={averageDimensions} />
                        ) : (
                            <div className="text-gray-400 text-center py-8">
                                No dimension data available
                            </div>
                        )}
                    </div>
                </div>

                {/* Right Column: Task Breakdown */}
                <div className="lg:col-span-2 space-y-4">
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">Task Performance</h3>

                    {relevantAllocations.length === 0 ? (
                        <div className="bg-gray-50 rounded-xl p-8 text-center text-gray-500">
                            No tasks evaluated for this candidate.
                        </div>
                    ) : (
                        relevantAllocations.map((alloc, idx) => {
                            const isWinner = alloc.recommended_candidate === candidate.candidate_id;
                            const candidateScore = alloc.top_candidates?.find(tc => tc.candidate_id === candidate.candidate_id);
                            const score = candidateScore?.score ?? alloc.confidence;
                            const candidateEvidence = isWinner ? alloc.evidence : candidateScore?.evidence;
                            const isExpanded = expandedTask === idx;

                            return (
                                <div
                                    key={idx}
                                    className={`bg-[rgba(255,253,248,0.96)] rounded-xl border ${isWinner ? 'border-primary/25 ring-2 ring-primary/10' : 'border-light-200'} shadow-sm overflow-hidden transition-all`}
                                >
                                    {/* Task Header */}
                                    <button
                                        onClick={() => setExpandedTask(isExpanded ? null : idx)}
                                        className="w-full p-5 flex items-center justify-between hover:bg-gray-50 transition-colors"
                                    >
                                        <div className="flex items-center gap-4">
                                            {isWinner && (
                                                <Award className="w-6 h-6 text-accent" />
                                            )}
                                            <div className="text-left">
                                                <h4 className="font-semibold text-gray-900">{alloc.task_title}</h4>
                                                <span className={`text-xs font-medium ${getScoreColor(score)}`}>
                                                    {getTaskMatchLabel(score, isWinner)}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-4">
                                            <span className={`text-xl font-bold ${getScoreColor(score)}`}>
                                                {Math.round(score * 100)}%
                                            </span>
                                            {isExpanded ? (
                                                <ChevronUp className="w-5 h-5 text-gray-400" />
                                            ) : (
                                                <ChevronDown className="w-5 h-5 text-gray-400" />
                                            )}
                                        </div>
                                    </button>

                                    {/* Expanded Content */}
                                    {isExpanded && (
                                        <div className="border-t border-gray-100 p-5 bg-gray-50">
                                            {/* Justification */}
                                            {(candidateScore?.justification || alloc.reasons?.[0]) && (
                                                <div className="mb-4">
                                                    <h5 className="text-sm font-semibold text-gray-700 mb-2">AI Assessment</h5>
                                                    <p className="text-gray-600 text-sm leading-relaxed">
                                                        {candidateScore?.justification || alloc.reasons?.[0]}
                                                    </p>
                                                </div>
                                            )}

                                            {/* Evidence */}
                                            {candidateEvidence && candidateEvidence.length > 0 && (
                                                <div>
                                                    <h5 className="text-sm font-semibold text-gray-700 mb-3">Evidence Trail</h5>
                                                    <div className="space-y-3">
                                                        {orderEvidence(candidateEvidence).map((ev, evIdx) => (
                                                            <EvidenceItem key={evIdx} evidence={ev} />
                                                        ))}
                                                    </div>
                                                </div>
                                            )}

                                            {/* Top Candidates Comparison */}
                                            {alloc.top_candidates && alloc.top_candidates.length > 1 && (
                                                <div className="mt-4 pt-4 border-t border-gray-200">
                                                    <h5 className="text-sm font-semibold text-gray-700 mb-2">Ranking for this Task</h5>
                                                    <div className="flex flex-wrap gap-2">
                                                        {alloc.top_candidates.slice(0, 3).map((tc, tcIdx) => (
                                                            <span
                                                                key={tcIdx}
                                                                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm ${tc.candidate_id === candidate.candidate_id
                                                                    ? 'bg-primary-soft text-primary-hover font-semibold'
                                                                    : 'bg-gray-100 text-gray-600'
                                                                    }`}
                                                            >
                                                                {tcIdx === 0 && <Trophy className="w-3.5 h-3.5 text-yellow-500" />}
                                                                {tcIdx === 1 && <Medal className="w-3.5 h-3.5 text-gray-400" />}
                                                                {tcIdx === 2 && <Medal className="w-3.5 h-3.5 text-amber-600" />}
                                                                <span className="font-medium">{tc.candidate_id}: {Math.round(tc.score * 100)}%</span>
                                                            </span>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            );
                        })
                    )}
                </div>
            </div>
            {/* Feedback Modal */}
            <FeedbackModal
                isOpen={isFeedbackModalOpen}
                onClose={() => setIsFeedbackModalOpen(false)}
                job={{ id: candidate.job_id || jobId || 'unknown' }}
                tasks={relevantAllocations.map(a => a.task_title)}
            />
        </div>
    );
}
