import React from 'react';
import { Code, Server, Layers, ArrowRight } from 'lucide-react';

/**
 * TemplateSelector Component
 * 
 * Displays role template cards for quick outcome creation.
 * Allows recruiters to select a template or start from scratch.
 */
export default function TemplateSelector({ templates, onSelect, onSkip }) {
  return (
    <div className="max-w-5xl mx-auto py-12">
      {/* Header with Cancel Button */}
      <div className="flex justify-between items-start mb-12">
        <div className="text-center flex-1">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Choose Your Starting Point
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Select a role template to prefill outcomes, or start from scratch.
            All outcomes are fully customizable.
          </p>
        </div>
        <button
          onClick={() => window.location.href = '/'}
          className="btn btn-ghost text-gray-600 hover:text-gray-900 flex-shrink-0"
        >
          Cancel & Return to Dashboard
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
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
              onClick={() => onSelect(template)}
              className={`
                      group relative bg-white rounded-2xl border-2 border-gray-200 p-8
                      hover:border-${color}-400 hover:shadow-xl
                      transition-all duration-300 text-left cursor-pointer
                  `}
            >
              {/* Gradient Header */}
              <div className={`
                      absolute top-0 left-0 right-0 h-2 rounded-t-2xl
                      bg-gradient-to-r from-${color}-500 to-${color}-300
                  `} />

              {/* Icon Placeholder */}
              <div className={`
                      w-14 h-14 rounded-xl bg-${color}-50 
                      flex items-center justify-center mb-4
                      group-hover:bg-${color}-100 transition-colors
                  `}>
                <Layers className={`w-7 h-7 text-${color}-600`} />
              </div>

              {/* Content */}
              <h3 className="text-xl font-bold text-gray-900 mb-2">
                {displayTitle}
              </h3>

              <p className="text-sm text-gray-500 mb-4">
                {itemCount} pre-written {itemLabel}
              </p>

              <div className="space-y-2">
                {previewItems.map((item, idx) => (
                  <div key={idx} className="flex items-start gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-gray-400 mt-2 flex-shrink-0" />
                    <span className="text-sm text-gray-600 line-clamp-1">
                      {item}
                    </span>
                  </div>
                ))}
              </div>

              {/* Hover Arrow */}
              <ArrowRight className={`
                      w-5 h-5 text-${color}-600 
                      absolute bottom-6 right-6
                      opacity-0 group-hover:opacity-100 
                      transform translate-x-0 group-hover:translate-x-1
                      transition-all duration-300
                  `} />
            </button>
          );
        })}

        {templates.length === 0 && (
          <div className="col-span-full text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed border-gray-200">
            <p className="text-gray-500">No templates found. Please start from scratch.</p>
          </div>
        )}
      </div>

      {/* Start from Scratch */}
      <div className="text-center">
        <button
          onClick={onSkip}
          className="btn btn-secondary px-8 py-3"
        >
          Start from Scratch
        </button>
      </div>
    </div>
  );
}
