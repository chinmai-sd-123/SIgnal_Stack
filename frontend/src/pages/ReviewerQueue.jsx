import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, CheckCircle, Clock, ChevronRight } from 'lucide-react';
// In a real app, we would fetch evaluations from API
import { getEvaluations } from '../api';

export default function ReviewerQueue() {
    const [evaluations, setEvaluations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [anonymized, setAnonymized] = useState(false);

    useEffect(() => {
        const fetchEvaluations = async () => {
            try {
                const data = await getEvaluations();
                // The API returns EvaluationSummary objects
                const formatted = data.map(e => ({
                    id: e.job_id,
                    job_id: e.job_id,
                    outcome_title: e.outcome_title,
                    status: e.human_action_required ? 'Needs Review' : 'Completed',
                    confidence: e.fit_score,
                    risk_flags: e.risk_flags || [],
                    timestamp: e.created_at
                }));
                setEvaluations(formatted);
            } catch (error) {
                console.error("Failed to fetch queue:", error);
            } finally {
                setLoading(false);
            }
        };
        fetchEvaluations();
    }, []);

    return (
        <div className="max-w-7xl mx-auto space-y-6">
            <div className="flex justify-between items-end">
                <div>
                    <h1 className="heading-1">Reviewer Queue</h1>
                    <p className="mt-1 text-sm text-gray-500">Manage pending evaluations and hiring decisions.</p>
                </div>
                <div className="flex items-center">
                    <button
                        onClick={() => setAnonymized(!anonymized)}
                        type="button"
                        className={`${anonymized ? 'bg-primary' : 'bg-gray-200'} relative inline-flex flex-shrink-0 h-6 w-11 border-2 border-transparent rounded-full cursor-pointer transition-colors ease-in-out duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary`}
                        role="switch"
                        aria-checked={anonymized}
                    >
                        <span className="sr-only">Use setting</span>
                        <span
                            aria-hidden="true"
                            className={`${anonymized ? 'translate-x-5' : 'translate-x-0'} pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform ring-0 transition ease-in-out duration-200`}
                        />
                    </button>
                    <span className="ml-3 text-sm font-medium text-gray-900">Anonymized Review</span>
                </div>
            </div>

            <div className="card shadow-sm border border-gray-100 overflow-hidden">
                {loading ? (
                    <div className="p-12 text-center text-gray-500">Loading queue...</div>
                ) : (
                    <ul className="divide-y divide-gray-100">
                        {evaluations.map((evalItem) => (
                            <li key={evalItem.id}>
                                <Link
                                    to={`/evaluation/${evalItem.job_id}`}
                                    state={{ anonymized }}
                                    className="block hover:bg-gray-50 transition duration-150 ease-in-out"
                                >
                                    <div className="px-6 py-5">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center truncate">
                                                <div className={`flex-shrink-0 h-2.5 w-2.5 rounded-full ${evalItem.status === 'Needs Review' ? 'bg-yellow-400' : 'bg-green-400'}`} aria-hidden="true"></div>
                                                <p className="ml-4 text-base font-medium text-primary truncate">{evalItem.outcome_title}</p>
                                            </div>
                                            <div className="ml-2 flex-shrink-0 flex">
                                                <span className={`badge ${evalItem.confidence > 0.8 ? 'badge-success' : 'badge-warning'
                                                    }`}>
                                                    {evalItem.confidence > 0.8 ? 'High Confidence' : 'Medium Confidence'}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="mt-2 sm:flex sm:justify-between">
                                            <div className="sm:flex">
                                                <p className="flex items-center text-sm text-gray-500">
                                                    <Clock className="flex-shrink-0 mr-1.5 h-4 w-4 text-gray-400" />
                                                    {new Date(evalItem.timestamp).toLocaleDateString()}
                                                </p>
                                                {evalItem.risk_flags.length > 0 && (
                                                    <p className="mt-2 flex items-center text-sm text-red-600 sm:mt-0 sm:ml-6">
                                                        <AlertTriangle className="flex-shrink-0 mr-1.5 h-4 w-4 text-red-500" />
                                                        {evalItem.risk_flags.length} Risks
                                                    </p>
                                                )}
                                            </div>
                                            <div className="mt-2 flex items-center text-sm text-gray-500 sm:mt-0">
                                                <span className="mr-2">Review</span>
                                                <ChevronRight className="h-5 w-5 text-gray-400" />
                                            </div>
                                        </div>
                                    </div>
                                </Link>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    );
}
