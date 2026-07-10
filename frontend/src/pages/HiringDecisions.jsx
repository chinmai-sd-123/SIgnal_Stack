import React, { useEffect, useState } from 'react';
import { getHiringHistory, getAnalyticsMetrics } from '../api';
import { Users, CheckCircle, XCircle, TrendingUp, Calendar, Briefcase, Activity, RotateCcw, ExternalLink, Sparkles, ArrowUpRight, Clock, Target } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function HiringDecisions() {
    const [history, setHistory] = useState([]);
    const [metrics, setMetrics] = useState(null);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        async function loadData() {
            try {
                const [histData, metData] = await Promise.all([
                    getHiringHistory(),
                    getAnalyticsMetrics()
                ]);
                setHistory(histData);
                setMetrics(metData);
            } catch (error) {
                console.error("Failed to load analytics", error);
            } finally {
                setLoading(false);
            }
        }
        loadData();
    }, []);

    const escapeCsvValue = (value) => {
        const text = value == null ? '' : String(value);
        return `"${text.replace(/"/g, '""')}"`;
    };

    const handleExport = () => {
        const headers = ['Date', 'Candidate', 'Role', 'Company', 'Decision', 'Outcome ID', 'Job ID'];
        const rows = history.map((record) => [
            record.date ? new Date(record.date).toISOString() : '',
            record.candidate || '',
            record.job_title || '',
            record.company || '',
            record.decision || '',
            record.outcome_id || '',
            record.job_id || '',
        ]);
        const csv = [headers, ...rows]
            .map((row) => row.map(escapeCsvValue).join(','))
            .join('\n');
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `hiring-decisions-${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    };

    if (loading) return (
        <div className="max-w-7xl mx-auto space-y-6 pb-12" aria-busy="true" aria-label="Loading hiring decisions">
            <div className="skeleton-card" style={{ height: '160px', borderRadius: '24px' }} />
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="skeleton-card" style={{ height: '110px' }} />
                <div className="skeleton-card" style={{ height: '110px' }} />
                <div className="skeleton-card" style={{ height: '110px' }} />
                <div className="skeleton-card" style={{ height: '110px' }} />
            </div>
            <div className="skeleton-card" style={{ height: '280px' }} />
        </div>
    );

    return (
        <div className="max-w-7xl mx-auto space-y-8 pb-12">
            {/* Hero Header */}
            <div className="relative overflow-hidden rounded-3xl hero-gradient p-8 text-white">
                <div className="absolute top-0 right-0 w-96 h-96 bg-white/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2"></div>
                <div className="absolute bottom-0 left-0 w-64 h-64 bg-accent/20 rounded-full blur-2xl translate-y-1/2 -translate-x-1/2"></div>
                <div className="relative">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 bg-white/20 rounded-xl backdrop-blur-sm">
                            <Sparkles className="w-6 h-6" />
                        </div>
                        <span className="text-white/80 font-medium">Hiring Intelligence</span>
                    </div>
                    <h1 className="text-3xl font-bold mb-2">Analytics Dashboard</h1>
                    <p className="text-white/80 max-w-xl">Track your recruitment velocity, decision quality, and hiring outcomes in real-time.</p>
                </div>
            </div>

            {/* Metrics Cards */}
            {metrics && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    {/* Total Processed */}
                    <div className="group relative bg-white rounded-2xl p-6 border border-gray-100 shadow-sm hover:shadow-xl transition-all duration-300 hover:-translate-y-1">
                        <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity"></div>
                        <div className="relative">
                            <div className="flex justify-between items-start mb-4">
                                <div className="p-3 bg-gradient-to-br from-primary/15 to-primary/5 rounded-xl">
                                    <Users className="w-6 h-6 text-primary" />
                                </div>
                                <div className="flex items-center gap-1 text-green-600 text-sm font-medium">
                                    <ArrowUpRight className="w-4 h-4" />
                                    <span>12%</span>
                                </div>
                            </div>
                            <h3 className="text-3xl font-bold text-gray-900 mb-1">{metrics.total_candidates_processed}</h3>
                            <p className="text-sm text-gray-500 font-medium">Total Processed</p>
                        </div>
                    </div>

                    {/* Hired Candidates */}
                    <div className="group relative bg-white rounded-2xl p-6 border border-gray-100 shadow-sm hover:shadow-xl transition-all duration-300 hover:-translate-y-1">
                        <div className="absolute inset-0 bg-gradient-to-br from-green-50 to-transparent rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity"></div>
                        <div className="relative">
                            <div className="flex justify-between items-start mb-4">
                                <div className="p-3 bg-gradient-to-br from-green-100 to-green-50 rounded-xl">
                                    <CheckCircle className="w-6 h-6 text-green-600" />
                                </div>
                                <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-semibold rounded-full">Active</span>
                            </div>
                            <h3 className="text-3xl font-bold text-green-600 mb-1">{metrics.total_hired}</h3>
                            <p className="text-sm text-gray-500 font-medium">Hired Candidates</p>
                        </div>
                    </div>

                    {/* Acceptance Rate */}
                    <div className="group relative bg-white rounded-2xl p-6 border border-gray-100 shadow-sm hover:shadow-xl transition-all duration-300 hover:-translate-y-1">
                        <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity"></div>
                        <div className="relative">
                            <div className="flex justify-between items-start mb-4">
                                <div className="p-3 bg-gradient-to-br from-primary/15 to-primary/5 rounded-xl">
                                    <Target className="w-6 h-6 text-primary" />
                                </div>
                            </div>
                            <h3 className="text-3xl font-bold text-gray-900 mb-1">{metrics.acceptance_rate}%</h3>
                            <p className="text-sm text-gray-500 font-medium">Acceptance Rate</p>
                            <div className="mt-3 h-2 bg-gray-100 rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-gradient-to-r from-primary to-accent rounded-full transition-all duration-1000"
                                    style={{ width: `${metrics.acceptance_rate}%` }}
                                ></div>
                            </div>
                        </div>
                    </div>

                    {/* Active Roles */}
                    <div className="group relative bg-white rounded-2xl p-6 border border-gray-100 shadow-sm hover:shadow-xl transition-all duration-300 hover:-translate-y-1">
                        <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity"></div>
                        <div className="relative">
                            <div className="flex justify-between items-start mb-4">
                                <div className="p-3 bg-gradient-to-br from-primary/15 to-primary/5 rounded-xl">
                                    <Briefcase className="w-6 h-6 text-primary" />
                                </div>
                                <div className="flex items-center gap-1 text-primary text-sm font-medium">
                                    <Clock className="w-4 h-4" />
                                    <span>Live</span>
                                </div>
                            </div>
                            <h3 className="text-3xl font-bold text-gray-900 mb-1">{metrics.total_active_jobs}</h3>
                            <p className="text-sm text-gray-500 font-medium">Active Roles</p>
                        </div>
                    </div>
                </div>
            )}

            {/* History Table */}
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
                <div className="px-6 py-5 border-b border-gray-100 bg-gradient-to-r from-gray-50 to-white">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-primary-soft rounded-lg">
                                <Activity className="w-5 h-5 text-primary" />
                            </div>
                            <div>
                                <h3 className="text-lg font-semibold text-gray-900">Decision History</h3>
                                <p className="text-sm text-gray-500">Recent hiring decisions and outcomes</p>
                            </div>
                        </div>
                        <button
                            onClick={handleExport}
                            disabled={history.length === 0}
                            className="btn-secondary py-2 px-4 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            Export Data
                        </button>
                    </div>
                </div>

                {history.length === 0 ? (
                    <div className="empty-state m-6">
                        <div className="empty-state-icon">
                            <Users className="w-6 h-6" />
                        </div>
                        <h4 className="empty-state-title">No decisions yet</h4>
                        <p className="empty-state-text">Hiring decisions will appear here once candidates are processed.</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full">
                            <thead>
                                <tr className="bg-gray-50/50">
                                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Date</th>
                                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Candidate</th>
                                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Role</th>
                                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Company</th>
                                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Decision</th>
                                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-50">
                                {history.map((record, index) => (
                                    <tr
                                        key={record.id}
                                        className="group hover:bg-primary-soft transition-colors"
                                        style={{ animationDelay: `${index * 50}ms` }}
                                    >
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center gap-2 text-sm text-gray-500">
                                                <Calendar className="w-4 h-4 text-gray-400" />
                                                {new Date(record.date).toLocaleDateString('en-US', {
                                                    month: 'short',
                                                    day: 'numeric',
                                                    year: 'numeric'
                                                })}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center gap-3">
                                                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary to-primary-hover flex items-center justify-center text-white font-semibold text-sm shadow-sm">
                                                    {record.candidate?.charAt(0)?.toUpperCase() || '?'}
                                                </div>
                                                <span className="font-medium text-gray-900">{record.candidate}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className="text-sm text-gray-600">{record.job_title}</span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className="text-sm text-gray-500">{record.company}</span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            {record.decision === 'Hired' ? (
                                                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-gradient-to-r from-green-50 to-green-100 text-green-700 border border-green-200">
                                                    <CheckCircle className="w-3.5 h-3.5" /> Hired
                                                </span>
                                            ) : (
                                                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-gradient-to-r from-red-50 to-red-100 text-red-700 border border-red-200">
                                                    <XCircle className="w-3.5 h-3.5" /> Rejected
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <button
                                                onClick={() => navigate(record.details_path || `/evaluation/${record.outcome_id}`)}
                                                disabled={!record.details_path && !record.outcome_id}
                                                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-primary hover:text-primary-hover bg-primary-soft hover:bg-primary/10 rounded-lg transition-all group-hover:shadow-sm"
                                            >
                                                <ExternalLink className="w-3.5 h-3.5" />
                                                View Details
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
