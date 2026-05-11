import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle, User, Briefcase, Calendar } from 'lucide-react';
import { getEvaluations } from '../api';

export default function AssessmentResults() {
    const [hires, setHires] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchHires() {
            try {
                // In a real app we might have a specific endpoint for hired candidates
                // For now we filter the evaluations list
                const allEvals = await getEvaluations();
                const hiredList = allEvals.filter(e => !e.human_action_required);
                // Note: The backend "get_evaluation_summaries" doesn't strictly return feedback status 'success' vs 'failure' directly in the summary list yet
                // But we can infer "action taken" or update backend. 
                // For MVP speed, let's assume we show all *Decided* evaluations here.
                setHires(hiredList);
            } catch (error) {
                console.error("Failed to load results", error);
            } finally {
                setLoading(false);
            }
        }
        fetchHires();
    }, []);

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <h1 className="heading-1 mb-8">Hiring Decisions</h1>

            {loading ? (
                <div className="text-center py-12">Loading results...</div>
            ) : hires.length === 0 ? (
                <div className="card p-12 text-center">
                    <p className="text-gray-500">No hiring decisions made yet.</p>
                    <Link to="/reviewer-queue" className="btn btn-link mt-2 inline-block">
                        Go to Reviewer Queue
                    </Link>
                </div>
            ) : (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                    {hires.map((hire) => (
                        <div key={hire.job_id} className="card p-0 overflow-hidden hover:shadow-md transition-shadow">
                            <div className="bg-green-50 px-6 py-4 border-b border-green-100 flex justify-between items-center">
                                <div className="flex items-center gap-2">
                                    <CheckCircle className="w-5 h-5 text-green-600" />
                                    <span className="font-bold text-green-800">Decision Recorded</span>
                                </div>
                                <span className="text-xs text-gray-500">
                                    {new Date(hire.created_at).toLocaleDateString()}
                                </span>
                            </div>
                            <div className="p-6">
                                <div className="flex items-start gap-4 mb-4">
                                    <div className="bg-primary-soft p-3 rounded-full">
                                        <User className="w-6 h-6 text-primary" />
                                    </div>
                                    <div>
                                        <h3 className="font-bold text-gray-900 text-lg">Candidate</h3>
                                        <div className="flex items-center gap-2 text-sm text-gray-500 mt-1">
                                            <Briefcase className="w-4 h-4" />
                                            {hire.outcome_title}
                                        </div>
                                    </div>
                                </div>

                                <div className="mt-4 pt-4 border-t border-gray-100 flex justify-between items-center">
                                    <div className="text-sm">
                                        <span className="text-gray-500">Fit Score: </span>
                                        <span className="font-bold text-primary">{(hire.fit_score * 100).toFixed(0)}%</span>
                                    </div>
                                    <Link
                                        to={`/evaluation/${hire.job_id}`}
                                        className="text-primary hover:text-primary-hover text-sm font-medium"
                                    >
                                        View Details →
                                    </Link>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
