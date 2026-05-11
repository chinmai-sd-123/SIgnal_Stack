import React, { useState, useEffect } from 'react';
import { TrendingUp, ArrowRight, Activity } from 'lucide-react';
import { getSignalWeights } from '../api';

export default function FeedbackView() {
    const [weights, setWeights] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function loadWeights() {
            try {
                const data = await getSignalWeights();
                // Mock historical data for demo visualization
                const enhancedData = data.map(w => ({
                    ...w,
                    previous_weight: w.weight * (0.8 + Math.random() * 0.4), // Mock previous
                    change_reason: 'Correlated with successful hires'
                }));
                setWeights(enhancedData);
            } catch (error) {
                console.error("Failed to load weights", error);
            } finally {
                setLoading(false);
            }
        }
        loadWeights();
    }, []);

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
                                {weights.map((weight, idx) => {
                                    const change = weight.weight - weight.previous_weight;
                                    const isPositive = change >= 0;
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
                                                    <span className="font-bold text-gray-900">{weight.weight.toFixed(2)}</span>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className={`badge ${isPositive ? 'badge-success' : 'badge-error'}`}>
                                                    <TrendingUp className={`w-3 h-3 mr-1 ${!isPositive && 'transform rotate-180'}`} />
                                                    {Math.abs(change * 100).toFixed(0)}%
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 italic">
                                                {weight.change_reason}
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
