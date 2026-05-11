import React, { useState } from 'react';
import { FileCode, FileText, ChevronDown, ChevronUp, ExternalLink, AlertCircle, Code, GitBranch, Shield, CheckCircle, Terminal } from 'lucide-react';

const EvidenceItem = ({ evidence }) => {
    const [isExpanded, setIsExpanded] = useState(false);

    // Guard against null/undefined evidence
    if (!evidence) return null;

    // Normalize formatting
    let snippet = evidence.snippet || evidence.content || '';
    let ref = evidence.ref || evidence.reference || 'Unknown';
    const sourceUrl = evidence.source_url || evidence.sourceUrl || null;

    // 1. CLEANUP SNIPPET: Remove redundant "Task: ..." header
    // We already know the task context from the parent card.
    snippet = snippet.replace(/^Task: .*?\n\n/i, '');

    // 2. CLEANUP REF: Make it human readable and choose icon
    let displayTitle = ref;
    let Icon = FileText;
    let iconColor = "text-gray-400";

    if (ref.startsWith('CODE:') || ref.startsWith('ENTRY:')) {
        // Format: CODE:task_name:file/path.ext
        const parts = ref.split(':');
        // Join back parts after the 2nd colon in case filename has colons
        displayTitle = parts.length > 2 ? parts.slice(2).join(':') : ref;
        Icon = FileCode;
        iconColor = "text-blue-600";
    } else if (ref.startsWith('AI_FINDING:')) {
        displayTitle = "Key Evidence (AI Analysis)";
        Icon = AlertCircle;
        iconColor = "text-amber-600";
    } else if (ref.startsWith('AUTH:') || ref === 'GIT_LOG') {
        displayTitle = "Authorship Verification";
        Icon = GitBranch;
        iconColor = "text-primary-hover";
    } else if (ref.startsWith('SCAN:') || ref === 'PROJECT_SCAN') {
        displayTitle = "Project Health Scan";
        Icon = Shield;
        iconColor = "text-emerald-600";
    } else if (ref.startsWith('REPO:') || ref === 'REPOSITORY') {
        displayTitle = "Repository Structure";
        Icon = Terminal;
        iconColor = "text-slate-600";
    } else if (ref.includes('#L')) {
        // File path with line number like "app/main.py#L42"
        displayTitle = ref;
        Icon = FileCode;
        iconColor = "text-blue-600";
    }

    // 3. VERIFIED BADGE
    const isVerified = (ref.startsWith('AUTH:') || ref === 'GIT_LOG') && snippet.includes('[MATCH]');

    // Snippet preview logic
    const lines = snippet.split('\n');
    // Consider long if > 6 lines or > 400 chars
    const isLong = lines.length > 6 || snippet.length > 400;

    // If not expanded, show preview (first 6 lines)
    const displayContent = isExpanded ? snippet : lines.slice(0, 6).join('\n');

    return (
        <div className="group bg-white rounded-lg border border-gray-200 hover:border-indigo-300 transition-all duration-200 shadow-sm hover:shadow-md overflow-hidden">
            {/* Header / Summary Line */}
            <div
                className="flex items-center justify-between p-3 cursor-pointer bg-white hover:bg-gray-50/50 transition-colors select-none"
                onClick={() => setIsExpanded(!isExpanded)}
            >
                <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div className={`p-1.5 rounded-md bg-gray-50 border border-gray-100 ${iconColor} shadow-sm`}>
                        <Icon className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-gray-700 truncate font-mono" title={displayTitle}>
                                {displayTitle}
                            </span>
                            {isVerified && (
                                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-green-50 text-green-700 border border-green-200 shadow-sm">
                                    <CheckCircle className="w-3 h-3 mr-1" />
                                    Verified
                                </span>
                            )}
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-1 ml-3">
                    {sourceUrl && (
                        <a
                            href={sourceUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-1.5 text-gray-400 hover:text-primary rounded-md hover:bg-primary-soft transition-colors"
                            title="Open in GitHub"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                    )}
                    <button className="p-1.5 text-gray-400 hover:text-gray-600 rounded-md hover:bg-gray-100 transition-colors">
                        {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                    </button>
                </div>
            </div>

            {/* Code Content */}
            <div className={`border-t border-gray-100 bg-slate-50 relative ${isExpanded ? '' : ''}`}>
                <pre className={`p-3 text-[11px] font-mono leading-relaxed text-gray-700 overflow-x-auto whitespace-pre-wrap ${!isExpanded && isLong ? 'max-h-[150px] opacity-90' : ''}`}>
                    {displayContent}
                </pre>

                {/* Fade out effect for collapsed long content */}
                {isLong && !isExpanded && (
                    <div
                        className="absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-slate-50 to-transparent cursor-pointer flex items-end justify-center pb-1"
                        onClick={(e) => {
                            e.stopPropagation();
                            setIsExpanded(true);
                        }}
                    >
                        <span className="text-[10px] font-semibold text-primary bg-white/80 px-2 py-0.5 rounded shadow-sm border border-gray-100 mb-1 hover:text-primary">
                            Show full snippet
                        </span>
                    </div>
                )}
            </div>

            {/* Footer with Source Link if Expanded */}
            {isExpanded && sourceUrl && (
                <div className="px-3 py-1.5 bg-gray-50 border-t border-gray-100 text-[10px] text-right">
                    <a href={sourceUrl} target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-primary flex items-center justify-end gap-1 hover:underline">
                        View source on GitHub <ExternalLink className="w-2.5 h-2.5" />
                    </a>
                </div>
            )}
        </div>
    );
};

export default EvidenceItem;
