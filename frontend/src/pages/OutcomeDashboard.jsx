import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Share2, Play, Users, Clock, ArrowLeft } from 'lucide-react';
import { triggerEvaluation, getOutcome, getProofs } from '../api';

export default function OutcomeDashboard() {
    const { outcomeId } = useParams();
    const navigate = useNavigate();
    const [outcome, setOutcome] = useState(null);
    const [proofs, setProofs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [evaluating, setEvaluating] = useState(false);

    useEffect(() => {
        async function loadData() {
            try {
                const [outcomeData, proofsData] = await Promise.all([
                    getOutcome(outcomeId),
                    getProofs(outcomeId)
                ]);
                setOutcome(outcomeData);
                setProofs(proofsData);
            } catch (error) {
                console.error("Failed to load dashboard data", error);
            } finally {
                setLoading(false);
            }
        }
        loadData();
    }, [outcomeId]);



    const handleEvaluate = async () => {
        setEvaluating(true);
        try {
            if (proofs.length === 0) {
                alert("No proofs submitted yet. Please submit proofs via the candidate link.");
                setEvaluating(false);
                return;
            }

            const payload = {
                request_id: Math.random().toString(36).substring(7),
                outcome: outcome,
                proofs: proofs,
                options: { anonymize: false }
            };

            const result = await triggerEvaluation(payload);
            navigate(`/evaluation/${result.job_id}`, { state: { result } });
        } catch (error) {
            console.error("Evaluation failed", error);
            alert("Evaluation failed. Ensure proofs have been submitted.");
        } finally {
            setEvaluating(false);
        }
    };

    if (loading) return (
        <div className="flex justify-center items-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
    );

    if (!outcome) return <div className="p-8 text-center text-gray-500">Outcome not found.</div>;

    return (
        <div className="max-w-6xl mx-auto space-y-8 px-4 sm:px-6 lg:px-8">
            <button onClick={() => navigate('/outcomes')} className="text-gray-500 hover:text-primary flex items-center gap-1 transition-colors">
                <ArrowLeft className="w-4 h-4" /> Back to Outcomes
            </button>

            {/* Header */}
            <div className="card">
                <div className="flex flex-col md:flex-row justify-between items-start gap-6">
                    <div>
                        <div className="flex items-center gap-3">
                            <h1 className="heading-1">{outcome.title}</h1>
                            <span className="badge badge-success">Active</span>
                        </div>
                        <p className="text-gray-500 mt-2 text-lg">{outcome.description}</p>

                        <div className="mt-6 flex flex-wrap items-center gap-6">
                            <div className="flex items-center gap-2 text-gray-600 bg-gray-50 px-3 py-1.5 rounded-lg border border-gray-100">
                                <Users className="w-4 h-4 text-primary" />
                                <span className="text-sm font-medium">{proofs.length} Candidates</span>
                            </div>
                            <div className="flex items-center gap-2 text-gray-600 bg-gray-50 px-3 py-1.5 rounded-lg border border-gray-100">
                                <Clock className="w-4 h-4 text-primary" />
                                <span className="text-sm font-medium">Created Today</span>
                            </div>
                        </div>
                    </div>
                    <div className="flex flex-col sm:flex-row gap-3 w-full md:w-auto">
                        <button
                            onClick={handleEvaluate}
                            disabled={evaluating || proofs.length === 0}
                            className="btn btn-primary"
                        >
                            {evaluating ? (
                                <>
                                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-opacity-25 border-t-white mr-2"></div>
                                    Processing...
                                </>
                            ) : (
                                <>
                                    <Play className="w-4 h-4 mr-2" />
                                    Run Evaluation
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Main Content - Proofs */}
                <div className="lg:col-span-2 space-y-8">
                    <div className="card">
                        <div className="card-header">
                            <h3 className="heading-2">Submitted Proofs</h3>
                            <span className="badge badge-neutral">{proofs.length}</span>
                        </div>

                        {proofs.length === 0 ? (
                            <div className="text-center py-12 bg-gray-50 rounded-xl border-2 border-dashed border-gray-200">
                                <Users className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                                <p className="text-gray-500 font-medium">No candidates yet</p>
                                <p className="text-sm text-gray-400 mt-1">Share the invite link to start receiving submissions.</p>
                            </div>
                        ) : (
                            <ul className="divide-y divide-gray-100">
                                {proofs.map((proof) => {
                                    const isGit = proof.type === 'github' || (proof.payload && proof.payload.repo_url && proof.payload.repo_url.includes('github'));
                                    const link = isGit ? proof.payload.repo_url : proof.payload.artifact_link;

                                    return (
                                        <li key={proof.id || proof.candidate_id} className="py-4 flex items-center justify-between group">
                                            <div className="flex items-start gap-4">
                                                <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold ${isGit ? 'bg-gray-100 text-gray-600' : 'bg-purple-100 text-primary-hover'}`}>
                                                    {proof.candidate_id.charAt(0).toUpperCase()}
                                                </div>
                                                <div>
                                                    <p className="text-sm font-bold text-gray-900">{proof.candidate_id}</p>
                                                    <a
                                                        href={link}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="text-xs text-primary hover:text-primary-hover hover:underline flex items-center gap-1 mt-0.5"
                                                    >
                                                        {link ? new URL(link).pathname.substring(1) : "No Link"}
                                                        <Share2 className="w-3 h-3" />
                                                    </a>
                                                </div>
                                            </div>
                                            <span className="badge badge-success">Ready</span>
                                        </li>
                                    );
                                })}
                            </ul>
                        )}
                    </div>
                </div>

                {/* Sidebar - Signals & Invite */}
                <div className="space-y-8">

                    {/* Signals Card */}
                    <div className="card overflow-hidden">
                        <div className="card-header">
                            <h3 className="heading-2 text-base">Evaluation Signals</h3>
                        </div>
                        <div className="space-y-3 min-w-0">
                            {outcome.tasks?.map((task) => (
                                <div key={task.id} className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 p-4 bg-gray-50 rounded-lg border border-gray-100 min-w-0">
                                    <p className="text-sm font-medium leading-6 text-gray-700 min-w-0 flex-1 break-words [overflow-wrap:anywhere]">
                                        {task.name}
                                    </p>
                                    <span className={`self-start shrink-0 text-[10px] font-bold px-2.5 py-1 rounded-full ${task.priority === 'High' ? 'bg-red-100 text-red-700' :
                                        task.priority === 'Medium' ? 'bg-yellow-100 text-yellow-700' :
                                            'bg-green-100 text-green-700'
                                        }`}>
                                        {task.priority}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
