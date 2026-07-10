import React, { useEffect, useState } from 'react';
import { getAuditLogs } from '../api';
import { Shield, Clock, Activity } from 'lucide-react';

export default function AdminAudit() {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        getAuditLogs()
            .then(data => setLogs(data))
            .catch(err => console.error("Failed to fetch logs", err))
            .finally(() => setLoading(false));
    }, []);

    return (
        <div className="max-w-7xl mx-auto space-y-8">
            <div className="flex items-center gap-3">
                <div className="p-2 bg-primary-soft rounded-lg">
                    <Shield className="w-6 h-6 text-primary" />
                </div>
                <div>
                    <h1 className="heading-1">System Audit Logs</h1>
                    <p className="text-sm text-gray-500">Track all sensitive actions and system events for compliance.</p>
                </div>
            </div>

            <div className="card shadow-sm border border-gray-100 overflow-hidden p-0">
                {loading ? (
                    <div className="p-12 text-center text-gray-500">Loading audit trail...</div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-100">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Timestamp
                                    </th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Action
                                    </th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Details
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-100">
                                {logs.length === 0 ? (
                                    <tr>
                                        <td colSpan="3" className="px-6 py-8">
                                            <div className="empty-state" style={{ border: 'none', background: 'transparent' }}>
                                                <p className="empty-state-title">No audit logs found</p>
                                                <p className="empty-state-text">System actions will appear here as they happen.</p>
                                            </div>
                                        </td>
                                    </tr>
                                ) : (
                                    logs.map((log) => (
                                        <tr key={log.id} className="hover:bg-gray-50 transition-colors">
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">
                                                {new Date(log.timestamp).toLocaleString()}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className="badge badge-neutral bg-blue-100 text-blue-800">
                                                    {log.action}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 text-sm text-gray-900 font-mono">
                                                {JSON.stringify(log.details)}
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
