import React, { useState, useEffect } from 'react';
import { X, Layers, ArrowRight, Loader2 } from 'lucide-react';
import { getOutcomeTemplates } from '../api';

export default function TemplateSelectionModal({ isOpen, onClose, onSelect }) {
    const [templates, setTemplates] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (isOpen) {
            setLoading(true);
            getOutcomeTemplates()
                .then(data => {
                    setTemplates(data);
                    setLoading(false);
                })
                .catch(err => {
                    console.error("Failed to load templates", err);
                    setLoading(false);
                });
        }
    }, [isOpen]);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-5xl h-[80vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">

                {/* Header */}
                <div className="flex justify-between items-center p-6 border-b border-gray-100">
                    <div>
                        <h2 className="text-2xl font-bold text-gray-900">Choose a Template</h2>
                        <p className="text-sm text-gray-500">Select a pre-built role or outcome to get started quickly.</p>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full transition-colors text-gray-500">
                        <X className="w-6 h-6" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 bg-gray-50/50">
                    {loading ? (
                        <div className="h-full flex flex-col items-center justify-center text-gray-400">
                            <Loader2 className="w-10 h-10 animate-spin mb-4 text-primary" />
                            <p>Loading templates...</p>
                        </div>
                    ) : templates.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center text-gray-400">
                            <Layers className="w-12 h-12 mb-4 opacity-20" />
                            <p>No templates found.</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {templates.map((template) => {
                                // Determine visual attributes based on template content
                                const displayTitle = template.role_name || template.title;
                                const isRoleTemplate = !!template.role_name;
                                const itemCount = isRoleTemplate
                                    ? (template.outcomes?.length || 0)
                                    : (template.tasks?.length || 0);
                                const itemLabel = isRoleTemplate ? 'outcomes' : 'tasks';

                                // Helper to get preview items (either outcomes titles or task names)
                                const previewItems = isRoleTemplate
                                    ? (template.outcomes || []).slice(0, 3).map(o => o.title)
                                    : (template.tasks || []).slice(0, 3).map(t => t.name);

                                // Icon & Color assignment (stable hash based on title)
                                const colors = ['indigo', 'blue', 'purple', 'cyan', 'emerald'];
                                const color = colors[displayTitle.length % colors.length];

                                return (
                                    <button
                                        key={template.id}
                                        onClick={() => {
                                            onSelect(template);
                                            onClose();
                                        }}
                                        className={`
                        group relative bg-white rounded-xl border border-gray-200 p-6
                        hover:border-${color}-400 hover:shadow-lg hover:-translate-y-1
                        transition-all duration-300 text-left cursor-pointer
                        flex flex-col h-full
                    `}
                                    >
                                        {/* Gradient Header */}
                                        <div className={`
                        absolute top-0 left-0 right-0 h-1.5 rounded-t-xl
                        bg-gradient-to-r from-${color}-500 to-${color}-300
                    `} />

                                        {/* Header Section */}
                                        <div className="flex items-start justify-between mb-4">
                                            <div className={`
                            w-10 h-10 rounded-lg bg-${color}-50 
                            flex items-center justify-center
                            group-hover:bg-${color}-100 transition-colors
                        `}>
                                                <Layers className={`w-5 h-5 text-${color}-600`} />
                                            </div>
                                            <span className={`badge badge-sm bg-${color}-50 text-${color}-700 border-${color}-100`}>
                                                {itemCount} {itemLabel}
                                            </span>
                                        </div>

                                        {/* Content */}
                                        <h3 className="text-lg font-bold text-gray-900 mb-2 group-hover:text-${color}-700 transition-colors">
                                            {displayTitle}
                                        </h3>

                                        <p className="text-xs text-gray-500 mb-4 line-clamp-2 leading-relaxed">
                                            {template.description || "No description available."}
                                        </p>

                                        <div className="mt-auto space-y-2 pt-4 border-t border-gray-50">
                                            {previewItems.map((item, idx) => (
                                                <div key={idx} className="flex items-start gap-2">
                                                    <div className="w-1 h-1 rounded-full bg-gray-300 mt-1.5 flex-shrink-0" />
                                                    <span className="text-xs text-gray-500 line-clamp-1">
                                                        {item}
                                                    </span>
                                                </div>
                                            ))}
                                            {(isRoleTemplate ? (template.outcomes?.length || 0) : (template.tasks?.length || 0)) > 3 && (
                                                <div className="text-xs text-gray-400 pl-3">+ more</div>
                                            )}
                                        </div>
                                    </button>
                                );
                            })}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-4 border-t border-gray-100 bg-gray-50 flex justify-end">
                    <button onClick={onClose} className="btn btn-ghost text-sm">Cancel</button>
                </div>
            </div>
        </div>
    );
}
