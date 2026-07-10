import React, { useState } from 'react';
import { FileCode, FileText, ChevronDown, ChevronUp, ExternalLink, GitBranch, Shield, CheckCircle, Terminal, Link, Sparkles } from 'lucide-react';

const SHORTENED_MARKER = '[Snippet shortened. Open the GitHub source link for the full file.]';

function getEvidenceKind(evidence, ref) {
    const type = evidence?.type || '';
    if (ref.startsWith('AI_FINDING:')) return 'ai';
    if (type === 'work_artifact' || ref.startsWith('ARTIFACT:')) return 'artifact';
    if (ref.startsWith('AUTH:') || ref === 'GIT_LOG' || type === 'authorship_context') return 'authorship';
    if (ref.startsWith('SCAN:') || ref === 'PROJECT_SCAN' || type === 'project_health') return 'health';
    if (ref.startsWith('REPO:') || ref === 'REPOSITORY') return 'repository';
    if (ref.startsWith('FILE:') || ref.startsWith('CODE:') || ref.startsWith('ENTRY:') || type === 'code_snippet' || type === 'file_ref') return 'code';
    return 'context';
}

function cleanSnippet(snippet, kind) {
    let value = snippet || '';
    value = value.replace(/^Task: .*?\n\n/i, '');
    if (kind === 'ai') {
        value = value.replace(/^Key Evidence \(AI Analysis\):\s*/i, '');
    }
    return value.trim();
}

function compactTitle(ref, kind) {
    if (kind === 'ai') return 'Key Evidence';
    if (kind === 'artifact') return 'Supporting Artifact';
    if (kind === 'authorship') return 'Authorship Verification';
    if (kind === 'health') return 'Project Health Scan';
    if (kind === 'repository') return 'Repository Structure';
    if (ref.startsWith('FILE:')) return ref.replace(/^FILE:/, '');
    if (ref.startsWith('CODE:') || ref.startsWith('ENTRY:')) {
        const parts = ref.split(':');
        return parts.length > 2 ? parts.slice(2).join(':') : ref;
    }
    return ref || 'Evidence';
}

function renderRepositoryStructure(snippet, isExpanded) {
    const lines = snippet.split('\n').map(line => line.trim()).filter(Boolean);
    const header = lines[0]?.startsWith('Repository Structure') ? lines[0] : 'Repository Structure';
    const readmeIndex = lines.findIndex(line => line.toLowerCase().startsWith('readme'));
    const pathLines = (readmeIndex >= 0 ? lines.slice(1, readmeIndex) : lines.slice(1)).filter(line => !line.startsWith('['));
    const readmeLines = readmeIndex >= 0 ? lines.slice(readmeIndex, readmeIndex + 5) : [];
    const visiblePaths = isExpanded ? pathLines : pathLines.slice(0, 18);

    return (
        <div className="p-3">
            <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-primary-soft px-2.5 py-1 text-[11px] font-semibold text-primary">
                    {header}
                </span>
                {!isExpanded && pathLines.length > visiblePaths.length && (
                    <span className="text-[11px] text-text-muted">showing {visiblePaths.length} of {pathLines.length} paths</span>
                )}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                {visiblePaths.map((path, idx) => (
                    <div key={`${path}-${idx}`} className="min-w-0 rounded-md border border-light-200 bg-white px-2.5 py-1.5 font-mono text-[11px] text-text-secondary">
                        <span className="block truncate" title={path}>{path}</span>
                    </div>
                ))}
            </div>
            {readmeLines.length > 0 && (
                <div className="mt-3 rounded-md border border-accent/20 bg-accent-soft/50 px-3 py-2 text-xs leading-relaxed text-text-secondary">
                    {readmeLines.join('\n')}
                </div>
            )}
        </div>
    );
}

const EvidenceItem = ({ evidence }) => {
    const [isExpanded, setIsExpanded] = useState(false);

    // Guard against null/undefined evidence
    if (!evidence) return null;

    let ref = evidence.ref || evidence.reference || 'Unknown';
    const sourceUrl = evidence.source_url || evidence.sourceUrl || null;
    const kind = getEvidenceKind(evidence, ref);
    const snippet = cleanSnippet(evidence.snippet || evidence.content || '', kind);

    let displayTitle = compactTitle(ref, kind);
    let Icon = FileText;
    let iconColor = "text-slate-500";
    let accentClass = "border-light-200";

    if (kind === 'artifact') {
        Icon = Link;
        iconColor = "text-accent";
        accentClass = "border-accent/25";
    } else if (kind === 'code') {
        Icon = FileCode;
        iconColor = "text-primary";
        accentClass = "border-primary/15";
    } else if (kind === 'ai') {
        Icon = Sparkles;
        iconColor = "text-accent";
        accentClass = "border-accent/30";
    } else if (kind === 'authorship') {
        Icon = GitBranch;
        iconColor = "text-primary-hover";
        accentClass = "border-primary/20";
    } else if (kind === 'health') {
        Icon = Shield;
        iconColor = "text-emerald-700";
        accentClass = "border-emerald-200";
    } else if (kind === 'repository') {
        Icon = Terminal;
        iconColor = "text-slate-600";
    }

    const isVerified = kind === 'authorship' && (snippet.includes('MATCHED') || snippet.includes('AUTHORSHIP CONFIRMED'));
    const isShortened = snippet.includes(SHORTENED_MARKER);
    const cleanedSnippet = snippet.replace(SHORTENED_MARKER, '').trim();

    const lines = cleanedSnippet.split('\n');
    const previewLineCount = kind === 'code' ? 5 : 6;
    const isLong = kind === 'repository' || lines.length > previewLineCount || cleanedSnippet.length > 420 || isShortened;
    const displayContent = isExpanded ? cleanedSnippet : lines.slice(0, previewLineCount).join('\n');

    const sourceLabel = kind === 'artifact' ? 'Open artifact' : kind === 'code' ? 'Open full file' : 'Open repository';

    return (
        <div className={`group bg-white rounded-xl border ${accentClass} transition-all duration-200 shadow-sm hover:shadow-md overflow-hidden`}>
            {/* Header / Summary Line */}
            <div
                className="flex items-center justify-between p-3 cursor-pointer bg-white hover:bg-primary-soft/30 transition-colors select-none"
                onClick={() => setIsExpanded(!isExpanded)}
            >
                <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div className={`p-1.5 rounded-lg bg-light-50 border border-light-200 ${iconColor} shadow-sm`}>
                        <Icon className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 min-w-0">
                            <span className="text-xs font-bold text-text-primary truncate font-mono" title={displayTitle}>
                                {displayTitle}
                            </span>
                            {isVerified && (
                                <span className="inline-flex shrink-0 items-center px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-primary-soft text-primary border border-primary/20 shadow-sm">
                                    <CheckCircle className="w-3 h-3 mr-1" />
                                    Verified
                                </span>
                            )}
                            {isShortened && (
                                <span className="hidden sm:inline-flex shrink-0 rounded-full bg-accent-soft px-2 py-0.5 text-[10px] font-semibold text-amber-800">
                                    compact
                                </span>
                            )}
                        </div>
                        {sourceUrl && <div className="mt-0.5 truncate text-[10px] text-text-muted">{sourceLabel} on GitHub</div>}
                    </div>
                </div>

                <div className="flex items-center gap-1 ml-3">
                    {sourceUrl && (
                        <a
                            href={sourceUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-1.5 text-gray-400 hover:text-primary rounded-md hover:bg-primary-soft transition-colors"
                            title={sourceLabel}
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
            <div className="border-t border-light-200 bg-slate-50 relative">
                {kind === 'repository' ? (
                    renderRepositoryStructure(cleanedSnippet, isExpanded)
                ) : (
                    <pre className={`p-3 text-[11px] font-mono leading-relaxed text-text-secondary overflow-x-auto whitespace-pre-wrap break-words ${!isExpanded && isLong ? 'max-h-[145px] opacity-95' : ''}`}>
                        {displayContent}
                    </pre>
                )}

                {/* Fade out effect for collapsed long content */}
                {isLong && !isExpanded && (
                    <div
                        className="absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-slate-50 to-transparent cursor-pointer flex items-end justify-center pb-1"
                        onClick={(e) => {
                            e.stopPropagation();
                            setIsExpanded(true);
                        }}
                    >
                        <span className="text-[10px] font-semibold text-primary bg-white/90 px-2 py-0.5 rounded-full shadow-sm border border-light-200 mb-1 hover:text-primary">
                            Show more
                        </span>
                    </div>
                )}
            </div>

            {/* Footer with Source Link if Expanded */}
            {isExpanded && sourceUrl && (
                <div className="px-3 py-2 bg-white border-t border-light-200 text-[10px] text-right">
                    <a href={sourceUrl} target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-primary flex items-center justify-end gap-1 hover:underline">
                        {sourceLabel} <ExternalLink className="w-2.5 h-2.5" />
                    </a>
                </div>
            )}
        </div>
    );
};

export default EvidenceItem;
