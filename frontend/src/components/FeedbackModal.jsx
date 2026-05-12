import React, { useState } from 'react';
import { X, ThumbsUp, ThumbsDown, AlertTriangle, CheckCircle, Lightbulb, TrendingUp, TrendingDown } from 'lucide-react';
import { submitTaskFeedback } from '../api';

export default function FeedbackModal({ isOpen, onClose, job, tasks }) {
    // Map of taskName -> 'boost' | 'penalize' | null
    const [taskFeedback, setTaskFeedback] = useState({});
    const [reason, setReason] = useState('');
    const [submitting, setSubmitting] = useState(false);

    if (!isOpen) return null;

    const setFeedback = (taskName, direction) => {
        setTaskFeedback(prev => {
            const current = prev[taskName];
            if (current === direction) {
                const newState = { ...prev };
                delete newState[taskName];
                return newState;
            }
            return { ...prev, [taskName]: direction };
        });
    };

    const handleSubmit = async () => {
        setSubmitting(true);
        try {
            const promises = Object.entries(taskFeedback).map(([taskName, direction]) => {
                return submitTaskFeedback({
                    job_id: job.id || job.job_id,
                    task_name: taskName,
                    direction: direction,
                    reason: reason || (direction === 'boost' ? `Boosted via Feedback UI` : `Penalized via Feedback UI`)
                });
            });

            if (promises.length === 0) {
                onClose();
                return;
            }

            const results = await Promise.all(promises);
            window.dispatchEvent(new CustomEvent('signalstack:learning-updated', {
                detail: {
                    source: 'task-feedback',
                    results,
                },
            }));
            onClose();
            setTaskFeedback({}); // Reset
            alert(`System updated! weights adjusted.`);
        } catch (error) {
            console.error("Feedback failed", error);
            alert("Failed to save feedback: " + error.message);
        } finally {
            setSubmitting(false);
        }
    };

    const feedbackCount = Object.keys(taskFeedback).length;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in duration-200">

                {/* Header */}
                <div className="p-6 border-b flex justify-between items-start bg-gradient-to-r from-primary-soft to-purple-50 border-primary-soft">
                    <div className="flex gap-4">
                        <div className="p-3 rounded-2xl shadow-sm bg-primary-soft text-primary">
                            <Lightbulb className="w-6 h-6" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-primary">
                                Refine the Hiring Model
                            </h2>
                            <p className="text-sm mt-1 max-w-sm text-primary-hover">
                                Tell the AI which tasks were critical (Boost) or disappointing (Penalize). This tunes future evaluations.
                            </p>
                        </div>
                    </div>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-600 hover:bg-white/50 p-2 rounded-full transition-all">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 space-y-6 flex-1 overflow-y-auto">
                    <div>
                        <div className="flex items-center justify-between mb-3">
                            <label className="block text-sm font-bold text-gray-700">
                                Evaluated Tasks
                            </label>
                            <span className="text-xs font-medium text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
                                {feedbackCount} adjustments pending
                            </span>
                        </div>

                        <div className="space-y-3 max-h-[350px] overflow-y-auto pr-2 custom-scrollbar">
                            {tasks.map((task, idx) => {
                                const direction = taskFeedback[task]; // 'boost' | 'penalize' | undefined

                                return (
                                    <div key={idx} className={`w-full px-4 py-3 rounded-xl border flex items-center justify-between transition-all duration-200 ${direction === 'boost' ? 'border-emerald-300 bg-emerald-50' :
                                            direction === 'penalize' ? 'border-rose-300 bg-rose-50' : 'border-gray-200 bg-white hover:border-gray-300'
                                        }`}>
                                        <span className="font-medium text-sm text-gray-800 pr-4 flex-1">
                                            {task}
                                        </span>

                                        <div className="flex items-center gap-2">
                                            {/* Boost Button */}
                                            <button
                                                onClick={() => setFeedback(task, 'boost')}
                                                className={`p-2 rounded-lg flex items-center gap-1.5 text-xs font-bold transition-all ${direction === 'boost'
                                                        ? 'bg-emerald-500 text-white shadow-md'
                                                        : 'bg-gray-100 text-gray-500 hover:bg-emerald-100 hover:text-emerald-600'
                                                    }`}
                                            >
                                                <TrendingUp className="w-4 h-4" />
                                                Boost
                                            </button>

                                            {/* Penalize Button */}
                                            <button
                                                onClick={() => setFeedback(task, 'penalize')}
                                                className={`p-2 rounded-lg flex items-center gap-1.5 text-xs font-bold transition-all ${direction === 'penalize'
                                                        ? 'bg-rose-500 text-white shadow-md'
                                                        : 'bg-gray-100 text-gray-500 hover:bg-rose-100 hover:text-rose-600'
                                                    }`}
                                            >
                                                <TrendingDown className="w-4 h-4" />
                                                Penalize
                                            </button>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-bold text-gray-700 mb-2">
                            Reason (Optional)
                        </label>
                        <textarea
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            placeholder="Why are you making these adjustments? (Helpful for audit logs)"
                            className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-primary focus:border-primary outline-none h-20 resize-none transition-all placeholder:text-gray-400 text-sm"
                        />
                    </div>
                </div>

                {/* Footer */}
                <div className="p-6 bg-gray-50/80 backdrop-blur-sm border-t border-gray-100 flex justify-end gap-3">
                    <button
                        onClick={onClose}
                        className="btn bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 px-4 py-2 rounded-lg font-medium"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSubmit}
                        disabled={feedbackCount === 0 || submitting}
                        className={`btn px-6 py-2 rounded-lg font-bold text-white flex items-center gap-2 transition-all ${feedbackCount === 0 ? 'bg-gray-300 cursor-not-allowed' : 'bg-primary hover:bg-primary-hover shadow-md'
                            }`}
                    >
                        {submitting ? 'Updating...' : `Apply ${feedbackCount} Changes`}
                    </button>
                </div>
            </div>
        </div>
    );
}
