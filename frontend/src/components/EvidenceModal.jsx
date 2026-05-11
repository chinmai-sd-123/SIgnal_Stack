import React, { useState } from 'react';
import { X, Copy, ExternalLink, AlertTriangle, CheckCircle, FileCode, GitCommit } from 'lucide-react';

/**
 * EvidenceModal - Display evidence details with code snippets and source links
 * 
 * Props:
 * - isOpen: boolean - Controls modal visibility
 * - onClose: function - Called when modal should close
 * - evidence: object - Evidence data to display
 *   - file: string - File path
 *   - commit: string - Git commit hash
 *   - lines: [start, end] - Line numbers
 *   - snippet: string - Code snippet
 *   - source_url: string - GitHub URL
 * - signalName: string - Name of the signal this evidence supports
 * - riskFlags: array - Risk flags to display (e.g., ["low_authorship"])
 */
export default function EvidenceModal({
    isOpen,
    onClose,
    evidence,
    signalName = "Evidence",
    riskFlags = []
}) {
    const [copied, setCopied] = useState(false);

    if (!isOpen) return null;

    const handleCopy = async () => {
        if (evidence?.snippet) {
            await navigator.clipboard.writeText(evidence.snippet);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    const handleOpenGitHub = () => {
        if (evidence?.source_url) {
            window.open(evidence.source_url, '_blank', 'noopener,noreferrer');
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/70 backdrop-blur-sm"
                onClick={onClose}
            />

            {/* Modal */}
            <div className="relative bg-gray-900 border border-gray-700 rounded-xl shadow-2xl w-full max-w-3xl max-h-[80vh] overflow-hidden">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-gray-700 bg-gray-800/50">
                    <div className="flex items-center gap-3">
                        <FileCode className="w-5 h-5 text-blue-400" />
                        <h2 className="text-lg font-semibold text-white">
                            {signalName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1 hover:bg-gray-700 rounded-lg transition-colors"
                    >
                        <X className="w-5 h-5 text-gray-400" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto max-h-[60vh]">
                    {/* Risk Flags */}
                    {riskFlags.length > 0 && (
                        <div className="mb-4 flex flex-wrap gap-2">
                            {riskFlags.map((flag, i) => (
                                <div key={i} className="flex items-center gap-1 px-2 py-1 bg-yellow-500/20 text-yellow-400 rounded text-sm">
                                    <AlertTriangle className="w-3 h-3" />
                                    {flag.replace(/_/g, ' ')}
                                </div>
                            ))}
                        </div>
                    )}

                    {/* File Info */}
                    {evidence?.file && (
                        <div className="mb-4">
                            <span className="text-xs text-gray-500 uppercase tracking-wide">File</span>
                            <p className="font-mono text-sm text-gray-300 mt-1">{evidence.file}</p>
                        </div>
                    )}

                    {/* Commit Info */}
                    {evidence?.commit && (
                        <div className="mb-4 flex items-center gap-2">
                            <GitCommit className="w-4 h-4 text-gray-500" />
                            <span className="font-mono text-sm text-gray-400">{evidence.commit.substring(0, 8)}</span>
                            {evidence?.lines && evidence.lines[0] > 0 && (
                                <span className="text-gray-500">
                                    Lines {evidence.lines[0]}-{evidence.lines[1]}
                                </span>
                            )}
                        </div>
                    )}

                    {/* Code Snippet */}
                    {evidence?.snippet && (
                        <div className="relative">
                            <span className="text-xs text-gray-500 uppercase tracking-wide">Code Snippet</span>
                            <div className="mt-2 relative">
                                <pre className="bg-gray-800 border border-gray-700 rounded-lg p-4 overflow-x-auto">
                                    <code className="text-sm text-gray-300 font-mono whitespace-pre-wrap">
                                        {evidence.snippet}
                                    </code>
                                </pre>
                                <button
                                    onClick={handleCopy}
                                    className="absolute top-2 right-2 p-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
                                    title="Copy to clipboard"
                                >
                                    {copied ? (
                                        <CheckCircle className="w-4 h-4 text-green-400" />
                                    ) : (
                                        <Copy className="w-4 h-4 text-gray-400" />
                                    )}
                                </button>
                            </div>
                        </div>
                    )}

                    {/* No evidence message */}
                    {!evidence?.snippet && !evidence?.file && (
                        <div className="text-center py-8 text-gray-400">
                            <FileCode className="w-12 h-12 mx-auto mb-3 opacity-50" />
                            <p>No detailed evidence available for this signal</p>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-700 bg-gray-800/50">
                    {evidence?.source_url && (
                        <button
                            onClick={handleOpenGitHub}
                            className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors text-gray-300"
                        >
                            <ExternalLink className="w-4 h-4" />
                            View on GitHub
                        </button>
                    )}
                    <button
                        onClick={onClose}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg transition-colors text-white"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
}
