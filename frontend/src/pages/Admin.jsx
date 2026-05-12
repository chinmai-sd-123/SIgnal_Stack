import React, { useCallback, useEffect, useState } from 'react';
import { Settings, History, FileText, AlertTriangle, RefreshCw, ChevronDown, ChevronUp, Activity } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const fetchJson = async (path) => {
    const response = await fetch(`${API_BASE}${path}`, {
        cache: 'no-store',
        headers: { 'Cache-Control': 'no-cache' },
    });
    if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || payload.message || `Failed to fetch ${path}`);
    }
    return response.json();
};

export default function Admin() {
    const [activeTab, setActiveTab] = useState('weights');
    const [weights, setWeights] = useState([]);
    const [weightHistory, setWeightHistory] = useState([]);
    const [taskWeightHistory, setTaskWeightHistory] = useState([]);
    const [auditLogs, setAuditLogs] = useState([]);
    const [llmLogs, setLlmLogs] = useState([]);
    const [llmMetrics, setLlmMetrics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [expandedLog, setExpandedLog] = useState(null);

    const fetchData = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            if (activeTab === 'weights') {
                const data = await fetchJson('/admin/signal-weights');
                setWeights(Array.isArray(data) ? data : []);

                const histData = await fetchJson('/admin/weight-history');
                setWeightHistory(histData.history || []);
            } else if (activeTab === 'tasks') {
                const data = await fetchJson('/admin/task-weight-history');
                setTaskWeightHistory(Array.isArray(data) ? data : []);
            } else if (activeTab === 'audit') {
                const data = await fetchJson('/admin/audit-logs');
                setAuditLogs(Array.isArray(data) ? data : []);
            } else if (activeTab === 'llm') {
                const [logData, metricsData] = await Promise.all([
                    fetchJson('/admin/llm-logs'),
                    fetchJson('/metrics'),
                ]);
                setLlmLogs(Array.isArray(logData) ? logData : []);
                setLlmMetrics(metricsData || null);
            }
        } catch (error) {
            console.error('Error fetching data:', error);
            setError(error.message || 'Failed to load admin data');
        }
        setLoading(false);
    }, [activeTab]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const tabs = [
        { id: 'weights', label: 'Signal Weights', icon: Settings },
        { id: 'tasks', label: 'Task Learning', icon: Activity },
        { id: 'audit', label: 'Audit Logs', icon: History },
        { id: 'llm', label: 'LLM Logs', icon: FileText },
    ];

    const formatCount = (value) => Number(value || 0).toLocaleString();
    const formatCost = (value) => `$${Number(value || 0).toFixed(4)}`;
    const formatSeconds = (value) => `${Number(value || 0).toFixed(2)}s`;
    const llmCounters = llmMetrics?.counters || {};
    const llmLatency = llmMetrics?.histograms?.llm_latency_seconds || {};
    const llmCostByCandidate = llmMetrics?.labeled_gauges?.cost_per_candidate || {};
    const llmCostByJob = llmMetrics?.labeled_gauges?.cost_per_job || {};

    return (
        <div className="max-w-7xl mx-auto space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="heading-1">Admin Dashboard</h1>
                    <p className="text-gray-500 mt-1">Manage weights, view logs, and monitor system health</p>
                </div>
                <button
                    onClick={fetchData}
                    className="btn btn-secondary"
                >
                    <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                    Refresh
                </button>
            </div>

            {/* Tabs */}
            <div className="border-b border-gray-200">
                <nav className="-mb-px flex space-x-8">
                    {tabs.map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`
                                flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors
                                ${activeTab === tab.id
                                    ? 'border-primary text-primary'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                }
                            `}
                        >
                            <tab.icon className="w-4 h-4" />
                            {tab.label}
                        </button>
                    ))}
                </nav>
            </div>

            {/* Content */}
            <div className="card min-h-[500px]">
                {error && (
                    <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4" />
                        {error}
                    </div>
                )}
                {loading ? (
                    <div className="flex items-center justify-center py-12">
                        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
                    </div>
                ) : (
                    <>
                        {/* Weights Tab */}
                        {activeTab === 'weights' && (
                            <div className="space-y-8">
                                <div>
                                    <h2 className="heading-2 mb-4">Current Signal Weights</h2>
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                        {weights.map((w, i) => (
                                            <div key={i} className="rounded-lg p-4 border border-gray-200 bg-gray-50 min-w-0">
                                                <div className="flex justify-between items-start gap-3 min-w-0">
                                                    <span
                                                        className="font-medium text-gray-700 text-sm leading-5 break-all min-w-0"
                                                        title={w.signal_name}
                                                    >
                                                        {w.signal_name}
                                                    </span>
                                                    <span className="text-lg font-bold text-primary flex-shrink-0">{(w.weight * 100).toFixed(0)}%</span>
                                                </div>
                                                <div className="mt-2 h-2 bg-gray-200 rounded-full overflow-hidden">
                                                    <div
                                                        className="h-full bg-gradient-to-r from-primary to-primary transition-all"
                                                        style={{ width: `${w.weight * 100}%` }}
                                                    />
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <div className="border-t border-gray-100 pt-6">
                                    <h3 className="heading-2 mb-4">Weight History</h3>
                                    <div className="space-y-2 max-h-96 overflow-y-auto">
                                        {weightHistory.length === 0 ? (
                                            <p className="text-gray-400 text-center py-4">No weight changes recorded yet</p>
                                        ) : (
                                            weightHistory.map((h, i) => (
                                                <div key={i} className="flex items-center justify-between bg-white rounded-lg p-3 text-sm border border-gray-100">
                                                    <span className="font-medium text-gray-900">{h.signal_name}</span>
                                                    <div className="flex items-center gap-4">
                                                        <span className="badge badge-neutral">{h.old_weight} -&gt; {h.new_weight}</span>
                                                        <span className="text-xs text-gray-500">{h.change_reason}</span>
                                                        <span className="text-xs text-gray-400">{h.created_at?.split('T')[0]}</span>
                                                    </div>
                                                </div>
                                            ))
                                        )}
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Task Learning Tab */}
                        {activeTab === 'tasks' && (
                            <div>
                                <h2 className="heading-2 mb-4">Task Weight History</h2>
                                <div className="space-y-2 max-h-[600px] overflow-y-auto">
                                    {taskWeightHistory.length === 0 ? (
                                        <p className="text-gray-400 text-center py-8">No task learning recorded yet</p>
                                    ) : (
                                        taskWeightHistory.map((item) => (
                                            <div key={item.id} className="bg-gray-50 rounded-lg p-4 border border-gray-100">
                                                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                                                    <div>
                                                        <div className="font-semibold text-gray-900">{item.task_name || item.task_id}</div>
                                                        <div className="text-xs text-gray-500 mt-1">{item.outcome_title || item.outcome_id}</div>
                                                    </div>
                                                    <div className="flex flex-wrap items-center gap-3">
                                                        <span className="badge badge-neutral">
                                                            {Number(item.old_weight || 0).toFixed(2)} -&gt; {Number(item.new_weight || 0).toFixed(2)}
                                                        </span>
                                                        <span className="text-xs text-gray-500">{item.reason || 'No reason provided'}</span>
                                                        <span className="text-xs text-gray-400">{item.created_at?.split('T')[0]}</span>
                                                    </div>
                                                </div>
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Audit Logs Tab */}
                        {activeTab === 'audit' && (
                            <div>
                                <h2 className="heading-2 mb-4">Audit Logs</h2>
                                <div className="space-y-2 max-h-[600px] overflow-y-auto">
                                    {auditLogs.length === 0 ? (
                                        <p className="text-gray-400 text-center py-8">No audit logs recorded yet</p>
                                    ) : (
                                        auditLogs.map((log, i) => (
                                            <div key={i} className="bg-gray-50 rounded-lg p-4 border border-gray-100">
                                                <div className="flex items-center justify-between">
                                                    <div className="flex items-center gap-3">
                                                        <span className="badge badge-neutral">
                                                            {log.entity_type}
                                                        </span>
                                                        <span className="font-medium text-gray-900">{log.action}</span>
                                                    </div>
                                                    <span className="text-xs text-gray-500">{log.created_at?.split('T')[0]}</span>
                                                </div>
                                                {log.details && (
                                                    <pre className="mt-2 text-xs text-gray-500 bg-white p-3 rounded border border-gray-100 overflow-x-auto">
                                                        {JSON.stringify(log.details, null, 2)}
                                                    </pre>
                                                )}
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>
                        )}

                        {/* LLM Logs Tab */}
                        {activeTab === 'llm' && (
                            <div className="space-y-6">
                                <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-3">
                                    <div>
                                        <h2 className="heading-2">LLM Interaction Logs</h2>
                                        <p className="text-sm text-gray-500 mt-1">
                                            Runtime usage metrics come from the live metrics endpoint; detailed prompt logs are shown when persisted.
                                        </p>
                                    </div>
                                    <a
                                        href={`${API_BASE}/metrics/prometheus`}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-sm font-medium text-primary hover:underline"
                                    >
                                        Prometheus metrics
                                    </a>
                                </div>

                                <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
                                    <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                                        <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">LLM Calls</div>
                                        <div className="mt-2 text-2xl font-bold text-gray-900">{formatCount(llmCounters.llm_calls_total)}</div>
                                        <div className="mt-1 text-xs text-gray-500">{formatCount(llmCounters.llm_failures_total)} failures</div>
                                    </div>
                                    <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                                        <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">Tokens</div>
                                        <div className="mt-2 text-2xl font-bold text-gray-900">
                                            {formatCount(Number(llmCounters.llm_input_tokens_total || 0) + Number(llmCounters.llm_output_tokens_total || 0))}
                                        </div>
                                        <div className="mt-1 text-xs text-gray-500">
                                            {formatCount(llmCounters.llm_input_tokens_total)} in / {formatCount(llmCounters.llm_output_tokens_total)} out
                                        </div>
                                    </div>
                                    <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                                        <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">Estimated Cost</div>
                                        <div className="mt-2 text-2xl font-bold text-gray-900">{formatCost(llmCounters.llm_estimated_cost_total)}</div>
                                        <div className="mt-1 text-xs text-gray-500">Tracked from provider usage</div>
                                    </div>
                                    <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                                        <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">Latency</div>
                                        <div className="mt-2 text-2xl font-bold text-gray-900">{formatSeconds(llmLatency.avg)}</div>
                                        <div className="mt-1 text-xs text-gray-500">p95 {formatSeconds(llmLatency.p95)} / {formatCount(llmLatency.count)} samples</div>
                                    </div>
                                </div>

                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                    <div className="rounded-lg border border-gray-200 bg-white p-4">
                                        <h3 className="font-semibold text-gray-900 mb-3">Cache</h3>
                                        <div className="grid grid-cols-3 gap-3 text-sm">
                                            <div>
                                                <div className="text-gray-500">Hits</div>
                                                <div className="font-bold text-gray-900">{formatCount(llmCounters.llm_cache_hits_total)}</div>
                                            </div>
                                            <div>
                                                <div className="text-gray-500">Misses</div>
                                                <div className="font-bold text-gray-900">{formatCount(llmCounters.llm_cache_misses_total)}</div>
                                            </div>
                                            <div>
                                                <div className="text-gray-500">Usage Missing</div>
                                                <div className="font-bold text-gray-900">{formatCount(llmCounters.llm_usage_missing_total)}</div>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="rounded-lg border border-gray-200 bg-white p-4">
                                        <h3 className="font-semibold text-gray-900 mb-3">Cost Attribution</h3>
                                        <div className="grid grid-cols-2 gap-3 text-sm">
                                            <div>
                                                <div className="text-gray-500">Candidates</div>
                                                <div className="font-bold text-gray-900">{formatCount(Object.keys(llmCostByCandidate).length)}</div>
                                            </div>
                                            <div>
                                                <div className="text-gray-500">Jobs</div>
                                                <div className="font-bold text-gray-900">{formatCount(Object.keys(llmCostByJob).length)}</div>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div className="space-y-3 max-h-[600px] overflow-y-auto">
                                    {llmLogs.length === 0 ? (
                                        <div className="text-center py-8 border border-dashed border-gray-200 rounded-lg bg-gray-50">
                                            <AlertTriangle className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                                            <p className="text-gray-500">No persisted prompt logs recorded yet</p>
                                            <p className="text-xs text-gray-400 mt-1">Usage, token, latency, cache, and cost metrics are still shown above.</p>
                                        </div>
                                    ) : (
                                        llmLogs.map((log, i) => (
                                            <div key={i} className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                                                <button
                                                    onClick={() => setExpandedLog(expandedLog === i ? null : i)}
                                                    className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
                                                >
                                                    <div className="flex items-center gap-3">
                                                        <FileText className="w-4 h-4 text-primary" />
                                                        <span className="font-medium text-gray-900">Evaluation: {log.evaluation_id || 'N/A'}</span>
                                                        <span className={`px-2 py-0.5 rounded text-xs ${log.is_valid ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                                                            }`}>
                                                            {log.is_valid ? 'valid' : 'invalid'}
                                                        </span>
                                                        {log.latency_ms != null && (
                                                            <span className="px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-600">
                                                                {Math.round(log.latency_ms)} ms
                                                            </span>
                                                        )}
                                                    </div>
                                                    <div className="flex items-center gap-3">
                                                        <span className="text-xs text-gray-500">{log.created_at?.split('T')[0]}</span>
                                                        {expandedLog === i ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
                                                    </div>
                                                </button>
                                                {expandedLog === i && (
                                                    <div className="p-4 border-t border-gray-100 bg-gray-50">
                                                        <pre className="text-xs text-gray-600 overflow-x-auto font-mono">
                                                            {JSON.stringify({
                                                                prompt: log.prompt,
                                                                raw_response: log.raw_response,
                                                            }, null, 2)}
                                                        </pre>
                                                    </div>
                                                )}
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}
