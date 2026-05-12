import React, { useCallback, useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, ArrowRight, Activity, Clock } from 'lucide-react';
import { getSignalWeights, getTaskWeightHistory, getWeightHistory } from '../api';

export default function FeedbackView() {
    const [weights, setWeights] = useState([]);
    const [history, setHistory] = useState([]);
    const [taskHistory, setTaskHistory] = useState([]);
    const [loading, setLoading] = useState(true);

    const loadWeights = useCallback(async ({ silent = false } = {}) => {
        if (!silent) setLoading(true);
        try {
            const [weightData, historyData, taskHistoryData] = await Promise.all([
                getSignalWeights(),
                getWeightHistory(100),
                getTaskWeightHistory(100),
            ]);
            setWeights(weightData);
            setHistory(historyData.history || []);
            setTaskHistory(taskHistoryData || []);
        } catch (error) {
            console.error("Failed to load weights", error);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadWeights();
    }, [loadWeights]);

    useEffect(() => {
        const refreshLearning = () => loadWeights({ silent: true });
        window.addEventListener('signalstack:learning-updated', refreshLearning);
        return () => window.removeEventListener('signalstack:learning-updated', refreshLearning);
    }, [loadWeights]);

    const latestBySignal = history.reduce((acc, item) => {
        if (!acc[item.signal_name]) acc[item.signal_name] = item;
        return acc;
    }, {});

    const learningRows = weights.map((weight) => {
        const latest = latestBySignal[weight.signal_name];
        const previous = latest ? Number(latest.old_weight) : Number(weight.weight);
        const current = latest ? Number(latest.new_weight) : Number(weight.weight);
        return {
            ...weight,
            previous_weight: Number.isFinite(previous) ? previous : Number(weight.weight),
            current_weight: Number.isFinite(current) ? current : Number(weight.weight),
            change_reason: latest?.change_reason || 'No feedback update yet',
            changed_at: latest?.created_at,
        };
    });

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="mb-8">
                <h1 className="heading-1">System Learning</h1>
                <p className="mt-1 text-sm text-gray-500">View how the system adapts signal weights based on hiring outcomes.</p>
            </div>

            <div className="card shadow-sm border border-gray-100 overflow-hidden p-0">
                <div className="px-6 py-5 border-b border-gray-100 bg-gray-50 flex items-center justify-between">
                    <h3 className="text-lg font-medium leading-6 text-gray-900 flex items-center gap-2">
                        <Activity className="w-5 h-5 text-primary" />
                        Signal Weight Adjustments
                    </h3>
                    <span className="badge badge-success">
                        Active Learning
                    </span>
                </div>

                {loading ? (
                    <div className="p-12 text-center text-gray-500">Loading learning data...</div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-100">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Signal Name</th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Context</th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Weight Change</th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Impact</th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Reason</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-100">
                                {learningRows.map((weight, idx) => {
                                    const change = weight.current_weight - weight.previous_weight;
                                    const isPositive = change >= 0;
                                    const hasChange = Math.abs(change) > 0.0001;
                                    const TrendIcon = isPositive ? TrendingUp : TrendingDown;
                                    return (
                                        <tr key={idx}>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 font-mono">
                                                {weight.signal_name}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {weight.task_context || 'Global'}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                <div className="flex items-center gap-2">
                                                    <span className="text-gray-400">{weight.previous_weight.toFixed(2)}</span>
                                                    <ArrowRight className="w-4 h-4 text-gray-300" />
                                                    <span className="font-bold text-gray-900">{weight.current_weight.toFixed(2)}</span>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className={`badge ${!hasChange ? 'badge-neutral' : isPositive ? 'badge-success' : 'badge-error'}`}>
                                                    {hasChange ? <TrendIcon className="w-3 h-3 mr-1" /> : <Clock className="w-3 h-3 mr-1" />}
                                                    {hasChange ? `${Math.abs(change * 100).toFixed(0)}%` : 'Stable'}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 text-sm text-gray-500">
                                                <div>{weight.change_reason}</div>
                                                {weight.changed_at && (
                                                    <div className="text-xs text-gray-400 mt-1">{weight.changed_at.split('T')[0]}</div>
                                                )}
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            <div className="card shadow-sm border border-gray-100 overflow-hidden p-0 mt-8">
                <div className="px-6 py-5 border-b border-gray-100 bg-gray-50 flex items-center justify-between">
                    <h3 className="text-lg font-medium leading-6 text-gray-900 flex items-center gap-2">
                        <Activity className="w-5 h-5 text-primary" />
                        Task Weight Adjustments
                    </h3>
                    <span className="badge badge-neutral">{taskHistory.length}</span>
                </div>

                {loading ? (
                    <div className="p-12 text-center text-gray-500">Loading task learning data...</div>
                ) : taskHistory.length === 0 ? (
                    <div className="p-12 text-center text-gray-500">No task-level feedback recorded yet.</div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-100">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Task</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Outcome</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Weight Change</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Reason</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-100">
                                {taskHistory.map((item) => {
                                    const delta = Number(item.new_weight || 0) - Number(item.old_weight || 0);
                                    return (
                                        <tr key={item.id}>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 font-mono">
                                                {item.task_name || item.task_id}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">
                                                {item.outcome_title || item.outcome_id}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                <div className="flex items-center gap-2">
                                                    <span className="text-gray-400">{Number(item.old_weight || 0).toFixed(2)}</span>
                                                    <ArrowRight className="w-4 h-4 text-gray-300" />
                                                    <span className="font-bold text-gray-900">{Number(item.new_weight || 0).toFixed(2)}</span>
                                                    <span className={`badge ${delta >= 0 ? 'badge-success' : 'badge-error'}`}>
                                                        {delta >= 0 ? '+' : ''}{delta.toFixed(2)}
                                                    </span>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-sm text-gray-500">
                                                <div>{item.reason || 'No reason provided'}</div>
                                                {item.created_at && (
                                                    <div className="text-xs text-gray-400 mt-1">{item.created_at.split('T')[0]}</div>
                                                )}
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
