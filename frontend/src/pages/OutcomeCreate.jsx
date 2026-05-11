import React, { useState, useEffect } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { Plus, Trash2, CheckCircle, Sparkles, RefreshCw, Briefcase, MapPin, ArrowLeft } from 'lucide-react';
import { createOutcome, suggestTasks, getJob, getOutcomeTemplates, createJob } from '../api';
import TemplateSelectionModal from '../components/TemplateSelectionModal';

export default function OutcomeCreate() {
    const { jobId } = useParams(); // Optional job context
    const location = useLocation();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [generating, setGenerating] = useState(false);
    const [job, setJob] = useState(null);
    const [isModalOpen, setIsModalOpen] = useState(false);

    // Initial Data from Wizard?
    const wizardJobData = location.state?.jobData;

    // Outcome Data
    const [formData, setFormData] = useState({
        title: '',
        description: '',
        company: 'SignalStack',
        location: 'Remote',
        category: 'Software Engineering',
        proof_type: 'github',
        save_as_template: false
    });

    // Templates
    const [templates, setTemplates] = useState([]);

    useEffect(() => {
        getOutcomeTemplates()
            .then(data => setTemplates(data))
            .catch(err => console.error("Failed to load templates", err));
    }, []);

    const handleTemplateSelect = (template) => {
        if (template) {
            // Support NEW role-based templates (multiple outcomes)
            if (template.role_name && template.outcomes) {
                // New structure: Use first outcome as prefill
                const firstOutcome = template.outcomes[0];
                setFormData(prev => ({
                    ...prev,
                    title: firstOutcome.title,
                    description: firstOutcome.description || prev.description,
                    category: prev.category, // Keep existing category
                    save_as_template: false,
                    source_template_id: template.id // Link linkage
                }));

                // Note: Tasks need to be generated via AI for new templates
                // They don't come pre-defined in the new structure
                setTasks([]);

                alert(`Template selected: ${template.role_name}\n\nOutcome "${firstOutcome.title}" has been prefilled.\n\nClick "Generate Tasks with AI" to create evaluation signals.`);
            }
            // Support OLD single-outcome templates (legacy)
            else if (template.title) {
                setFormData(prev => ({
                    ...prev,
                    title: template.title,
                    description: template.description || prev.description,
                    category: template.category || prev.category,
                    save_as_template: false,
                    source_template_id: template.id
                }));

                // Pre-fill tasks from template
                if (template.tasks && template.tasks.length > 0) {
                    setTasks(template.tasks.map((t, i) => ({
                        id: `tpl-${Date.now()}-${i}`,
                        name: t.name,
                        priority: t.weight >= 0.5 ? 'High' : t.weight >= 0.3 ? 'Medium' : 'Low'
                    })));
                }
            }
        }
    };

    // Load Job Context if available
    useEffect(() => {
        if (jobId) {
            async function loadJobContext() {
                try {
                    const jobData = await getJob(jobId);
                    setJob(jobData);
                    setFormData(prev => ({
                        ...prev,
                        company: jobData.company,
                        location: jobData.location,
                        // Could also pre-fill category if job had it
                    }));
                } catch (error) {
                    console.error("Failed to load job context", error);
                }
            }
            loadJobContext();
        }
    }, [jobId]);

    // Generated Tasks
    const [tasks, setTasks] = useState([]);

    const normalizeGeneratedSignals = (suggestions) => (
        suggestions
            .map((signal, i) => ({
                ...signal,
                id: `temp-${i}`,
                name: (signal.name || '').replace(/\s+/g, ' ').trim().slice(0, 160),
                priority: signal.priority || (i < 2 ? 'High' : 'Medium')
            }))
            .filter(signal => signal.name.length > 0)
            .slice(0, 5)
    );

    const handleGenerateTasks = async () => {
        if (!formData.description) return;
        setGenerating(true);
        try {
            const context = [
                job ? `Job Title: ${job.title}` : null,
                job ? `Job Description: ${job.description}` : null,
                formData.title ? `Outcome Title: ${formData.title}` : null,
                `Outcome Goal: ${formData.description}`,
                'Generate concise evaluation signals that can be verified from candidate repositories or artifacts.'
            ].filter(Boolean).join('\n');

            const suggestions = await suggestTasks(context);
            setTasks(normalizeGeneratedSignals(suggestions));
        } catch (error) {
            console.error("Failed to generate tasks", error);
            alert("Failed to generate tasks. Please try again.");
        } finally {
            setGenerating(false);
        }
    };

    const handleTaskChange = (index, field, value) => {
        const newTasks = [...tasks];
        newTasks[index][field] = value;
        setTasks(newTasks);
    };

    const removeTask = (index) => {
        const newTasks = [...tasks];
        newTasks.splice(index, 1);
        setTasks(newTasks);
    };

    const addTask = () => {
        setTasks([...tasks, { id: `manual-${Date.now()}`, name: '', priority: 'Medium' }]);
    };

    const handleFinalSave = async () => {
        setLoading(true);
        try {
            let activeJobId = jobId;

            // 1. If coming from Wizard, Create Job FIRST
            if (!activeJobId && wizardJobData) {
                const newJob = await createJob(wizardJobData);
                activeJobId = newJob.job_id || newJob.id; // Handle variable API response
            }

            const payload = {
                ...formData,
                salary_min: formData.salary_min ? parseInt(formData.salary_min) : null,
                salary_max: formData.salary_max ? parseInt(formData.salary_max) : null,
                tasks: tasks.map(t => ({
                    name: t.name,
                    priority: t.priority,
                    weight: t.priority === 'High' ? 0.5 : t.priority === 'Medium' ? 0.3 : 0.2
                })),
                source_template_id: formData.source_template_id
            };

            if (activeJobId) {
                payload.job_id = activeJobId;
            }

            // Backend now handles task creation within createOutcome
            const outcomeResult = await createOutcome(payload);
            const outcomeId = outcomeResult.id;

            // Redirect back to Job Detail if in Job context
            if (activeJobId) {
                navigate(`/jobs/${activeJobId}`);
            } else {
                navigate(`/dashboard/${outcomeId}`);
            }
        } catch (error) {
            console.error("Failed to save outcome flow", error);
            alert(`Error: ${error.message}`);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-4xl mx-auto space-y-8 pb-12">
            <div className="flex justify-between items-end mb-8">
                <div className="flex items-center gap-4">
                    {jobId && (
                        <button onClick={() => navigate(`/jobs/${jobId}`)} className="text-gray-500 hover:text-primary">
                            <ArrowLeft className="w-5 h-5" />
                        </button>
                    )}
                    <div>
                        <h1 className="heading-1">Define Outcome</h1>
                        {job && <p className="text-sm text-gray-500">For Job: <span className="font-semibold">{job.title}</span></p>}
                    </div>
                </div>

                {/* Improved Template Selection Modal */}
                {templates.length > 0 && (
                    <div className="flex flex-col items-end">
                        <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                            Start from Template
                        </label>
                        <button
                            type="button"
                            onClick={() => setIsModalOpen(true)}
                            className="btn btn-secondary flex items-center gap-2"
                        >
                            {formData.title && templates.some(t => t.title === formData.title) ? (
                                <>
                                    <CheckCircle className="w-4 h-4 text-green-500" />
                                    <span className="text-gray-900 font-medium">
                                        {formData.title}
                                    </span>
                                </>
                            ) : (
                                "Select a Template"
                            )}
                        </button>

                        <TemplateSelectionModal
                            isOpen={isModalOpen}
                            onClose={() => setIsModalOpen(false)}
                            onSelect={(t) => {
                                handleTemplateSelect(t);
                                setIsModalOpen(false);
                            }}
                        />
                    </div>
                )}
            </div>

            {/* 1. Definition Section */}
            <div className="card space-y-6">
                <div className="card-header pb-0 border-b-0 mb-0 flex justify-between items-center">
                    <h2 className="heading-2">1. Outcome Goal</h2>

                    {/* Small Reselect Dropdown if already selected */}
                    {templates.length > 0 && formData.title && (
                        <div className="flex items-center gap-2">
                            <span className="text-xs text-gray-500">Change Template:</span>
                            <button
                                onClick={() => setIsModalOpen(true)}
                                className="btn btn-xs btn-ghost text-primary"
                            >
                                Select Different Template
                            </button>
                        </div>
                    )}
                </div>
                <div className="grid grid-cols-1 gap-6">
                    <div>
                        <label className="input-label">Outcome Title</label>
                        <input
                            type="text"
                            placeholder="e.g. Build Core API Service"
                            value={formData.title}
                            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                            className="input-field"
                        />
                    </div>

                    {!jobId && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div>
                                <label className="input-label">Company Name</label>
                                <div className="relative">
                                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                        <Briefcase className="h-4 w-4 text-gray-400" />
                                    </div>
                                    <input
                                        type="text"
                                        value={formData.company}
                                        onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                                        className="input-field pl-10"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="input-label">Location</label>
                                <div className="relative">
                                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                        <MapPin className="h-4 w-4 text-gray-400" />
                                    </div>
                                    <input
                                        type="text"
                                        value={formData.location}
                                        onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                                        className="input-field pl-10"
                                    />
                                </div>
                            </div>
                        </div>
                    )}

                    <div>
                        <label className="input-label">Description & Success Criteria</label>
                        <textarea
                            rows={4}
                            placeholder="Describe what success looks like for this specific outcome..."
                            value={formData.description}
                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            className="input-field"
                        />
                        <p className="mt-1 text-xs text-gray-500">
                            Our AI will suggest evaluation signals based on this description.
                        </p>
                    </div>

                    {/* Always allow saving as template if desired */}
                    <div className="flex items-center gap-2 pt-2 border-t border-gray-100 mt-4">
                        <input
                            type="checkbox"
                            id="saveTemplate"
                            checked={formData.save_as_template}
                            onChange={(e) => setFormData({ ...formData, save_as_template: e.target.checked })}
                            className="checkbox checkbox-primary h-5 w-5 rounded border-gray-300 text-primary focus:ring-primary"
                        />
                        <label htmlFor="saveTemplate" className="text-sm font-medium text-gray-700 cursor-pointer select-none">
                            Save as reusable Template?
                            <span className="block text-xs text-gray-400 font-normal">
                                This creates a Master Template that learns from future feedback.
                            </span>
                        </label>
                    </div>

                </div>
            </div>

            {/* 2. Tasks Section */}
            <div className="card">
                <div className="card-header">
                    <div>
                        <h2 className="heading-2 flex items-center gap-3">
                            2. Evaluation Signals
                            <span className="badge badge-neutral">
                                {tasks.length} Signals
                            </span>
                        </h2>
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={handleGenerateTasks}
                            disabled={generating || !formData.description}
                            className="btn btn-secondary"
                        >
                            {generating ? (
                                <>
                                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                                    Generating...
                                </>
                            ) : (
                                <>
                                    <Sparkles className="w-4 h-4 mr-2 text-primary-hover" />
                                    AI Suggest
                                </>
                            )}
                        </button>
                        <button onClick={addTask} className="btn btn-secondary">
                            <Plus className="w-4 h-4 mr-1" /> Add Manual
                        </button>
                    </div>
                </div>

                {tasks.length === 0 ? (
                    <div className="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed border-gray-200">
                        <p className="text-gray-500 font-medium">No signals defined yet.</p>
                        <p className="text-sm text-gray-400 mt-1">Use "AI Suggest" to generate signals from the description.</p>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {tasks.map((task, index) => (
                            <div key={task.id} className="flex gap-4 items-center bg-gray-50 p-4 rounded-lg border border-gray-200 hover:border-indigo-300 transition-colors">
                                <span className="text-xs font-bold text-gray-400 font-mono">{(index + 1).toString().padStart(2, '0')}</span>
                                <div className="flex-grow grid grid-cols-1 md:grid-cols-3 gap-4">
                                    <div className="md:col-span-2">
                                        <textarea
                                            rows={2}
                                            value={task.name}
                                            onChange={(e) => handleTaskChange(index, 'name', e.target.value)}
                                            className="input-field border-gray-200 bg-white resize-none leading-5"
                                            placeholder="Evidence-checkable signal..."
                                        />
                                    </div>
                                    <div>
                                        <select
                                            value={task.priority}
                                            onChange={(e) => handleTaskChange(index, 'priority', e.target.value)}
                                            className="input-field border-gray-200 bg-white"
                                        >
                                            <option>High</option>
                                            <option>Medium</option>
                                            <option>Low</option>
                                        </select>
                                    </div>
                                </div>
                                <button
                                    onClick={() => removeTask(index)}
                                    className="p-2 text-gray-400 hover:text-red-500 rounded-full hover:bg-red-50 transition-colors"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Final Action */}
            <div className="flex justify-end pt-4">
                <button
                    onClick={handleFinalSave}
                    disabled={loading || tasks.length === 0 || !formData.title}
                    className="btn btn-primary px-8 py-3 text-lg"
                >
                    {loading ? (
                        <>
                            <RefreshCw className="w-5 h-5 mr-2 animate-spin" />
                            Creating...
                        </>
                    ) : (
                        <>
                            <CheckCircle className="w-5 h-5 mr-2" />
                            {jobId ? 'Add Outcome to Job' : 'Create Outcome'}
                        </>
                    )}
                </button>
            </div>
        </div>
    );
}
