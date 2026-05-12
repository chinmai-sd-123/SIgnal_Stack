import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, CheckCircle, Plus, RefreshCw, Sparkles, Trash2 } from 'lucide-react';
import { getOutcome, suggestTasks, updateOutcome } from '../api';

export default function OutcomeEdit() {
    const { outcomeId } = useParams();
    const navigate = useNavigate();
    const [outcome, setOutcome] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [generating, setGenerating] = useState(false);

    useEffect(() => {
        async function loadOutcome() {
            try {
                const data = await getOutcome(outcomeId);
                setOutcome({
                    ...data,
                    tasks: (data.tasks || []).map((task) => ({
                        id: task.id,
                        name: task.name,
                        priority: task.priority || 'Medium',
                    })),
                });
            } catch (error) {
                alert(`Failed to load outcome: ${error.message}`);
            } finally {
                setLoading(false);
            }
        }
        loadOutcome();
    }, [outcomeId]);

    const updateField = (field, value) => {
        setOutcome((current) => ({ ...current, [field]: value }));
    };

    const updateTask = (index, field, value) => {
        setOutcome((current) => {
            const tasks = [...current.tasks];
            tasks[index] = { ...tasks[index], [field]: value };
            return { ...current, tasks };
        });
    };

    const addTask = () => {
        setOutcome((current) => ({
            ...current,
            tasks: [...current.tasks, { id: `manual-${Date.now()}`, name: '', priority: 'Medium' }],
        }));
    };

    const removeTask = (index) => {
        setOutcome((current) => ({
            ...current,
            tasks: current.tasks.filter((_, taskIndex) => taskIndex !== index),
        }));
    };

    const normalizeGeneratedSignals = (suggestions) => (
        suggestions
            .map((signal, index) => ({
                id: `generated-${Date.now()}-${index}`,
                name: (signal.name || '').replace(/\s+/g, ' ').trim().slice(0, 180),
                priority: signal.priority || (index < 2 ? 'High' : 'Medium'),
            }))
            .filter((signal) => signal.name.length > 0)
            .slice(0, 6)
    );

    const handleGenerateTasks = async () => {
        if (!outcome?.description) return;
        setGenerating(true);
        try {
            const context = [
                outcome.title ? `Outcome Title: ${outcome.title}` : null,
                `Outcome Goal: ${outcome.description}`,
                'Generate concise evaluation signals that can be verified from candidate repositories or artifacts.',
            ].filter(Boolean).join('\n');
            const suggestions = await suggestTasks(context);
            setOutcome((current) => ({ ...current, tasks: normalizeGeneratedSignals(suggestions) }));
        } catch (error) {
            alert(`Failed to generate signals: ${error.message}`);
        } finally {
            setGenerating(false);
        }
    };

    const handleSave = async () => {
        if (!outcome.title.trim() || !outcome.description.trim()) {
            alert('Outcome title and description are required.');
            return;
        }
        const tasks = outcome.tasks
            .map((task) => ({
                name: task.name.trim(),
                priority: task.priority || 'Medium',
                weight: task.priority === 'High' ? 0.5 : task.priority === 'Medium' ? 0.3 : 0.2,
            }))
            .filter((task) => task.name.length > 0);

        if (tasks.length === 0) {
            alert('Add at least one evaluation signal.');
            return;
        }

        setSaving(true);
        try {
            const updated = await updateOutcome(outcomeId, {
                title: outcome.title.trim(),
                description: outcome.description.trim(),
                proof_type: outcome.proof_type || 'github',
                status: outcome.status || 'active',
                tasks,
            });
            navigate(`/jobs/${updated.job_id}#outcomes`);
        } catch (error) {
            alert(`Failed to update outcome: ${error.message}`);
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return <div className="p-12 text-center text-gray-500">Loading outcome...</div>;
    }

    if (!outcome) {
        return <div className="p-12 text-center text-gray-500">Outcome not found.</div>;
    }

    return (
        <div className="max-w-4xl mx-auto space-y-6 pb-12">
            <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                    <button onClick={() => navigate(`/jobs/${outcome.job_id}#outcomes`)} className="text-gray-500 hover:text-primary">
                        <ArrowLeft className="w-5 h-5" />
                    </button>
                    <div>
                        <h1 className="heading-1">Edit Outcome</h1>
                        <p className="text-sm text-gray-500">Updating an outcome clears its stale evaluation report.</p>
                    </div>
                </div>
                <button onClick={() => navigate(`/jobs/${outcome.job_id}#outcomes`)} className="btn btn-ghost">
                    Cancel
                </button>
            </div>

            <div className="card space-y-6">
                <div>
                    <label className="input-label">Outcome Title</label>
                    <input
                        type="text"
                        value={outcome.title}
                        onChange={(event) => updateField('title', event.target.value)}
                        className="input-field"
                    />
                </div>

                <div>
                    <label className="input-label">Description & Success Criteria</label>
                    <textarea
                        rows={5}
                        value={outcome.description}
                        onChange={(event) => updateField('description', event.target.value)}
                        className="input-field"
                    />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                        <label className="input-label">Proof Type</label>
                        <select
                            value={outcome.proof_type || 'github'}
                            onChange={(event) => updateField('proof_type', event.target.value)}
                            className="input-field"
                        >
                            <option value="github">GitHub</option>
                            <option value="artifact">Artifact</option>
                            <option value="mixed">Mixed</option>
                        </select>
                    </div>
                    <div>
                        <label className="input-label">Status</label>
                        <select
                            value={outcome.status || 'active'}
                            onChange={(event) => updateField('status', event.target.value)}
                            className="input-field"
                        >
                            <option value="active">Active</option>
                            <option value="inprogress">In Progress</option>
                            <option value="completed">Completed</option>
                        </select>
                    </div>
                </div>
            </div>

            <div className="card space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div>
                        <h2 className="heading-2">Evaluation Signals</h2>
                        <p className="text-sm text-gray-500">{outcome.tasks.length} signals configured</p>
                    </div>
                    <div className="flex gap-2">
                        <button onClick={handleGenerateTasks} disabled={generating || !outcome.description} className="btn btn-sm btn-secondary">
                            {generating ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Sparkles className="w-4 h-4 mr-2" />}
                            AI Suggest
                        </button>
                        <button onClick={addTask} className="btn btn-sm btn-secondary">
                            <Plus className="w-4 h-4 mr-1" />
                            Add Manual
                        </button>
                    </div>
                </div>

                <div className="space-y-3">
                    {outcome.tasks.map((task, index) => (
                        <div key={task.id || index} className="flex gap-4 items-center bg-gray-50 p-4 rounded-lg border border-gray-200">
                            <span className="text-xs font-bold text-gray-400 font-mono">{String(index + 1).padStart(2, '0')}</span>
                            <div className="flex-grow grid grid-cols-1 md:grid-cols-3 gap-4">
                                <textarea
                                    rows={2}
                                    value={task.name}
                                    onChange={(event) => updateTask(index, 'name', event.target.value)}
                                    className="md:col-span-2 input-field border-gray-200 bg-white resize-none leading-5"
                                />
                                <select
                                    value={task.priority}
                                    onChange={(event) => updateTask(index, 'priority', event.target.value)}
                                    className="input-field border-gray-200 bg-white"
                                >
                                    <option>High</option>
                                    <option>Medium</option>
                                    <option>Low</option>
                                </select>
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
            </div>

            <div className="flex justify-end sticky bottom-6 bg-white p-4 rounded-lg shadow-lg border border-gray-200">
                <button onClick={handleSave} disabled={saving} className="btn btn-primary px-8 py-3">
                    {saving ? <RefreshCw className="w-5 h-5 mr-2 animate-spin" /> : <CheckCircle className="w-5 h-5 mr-2" />}
                    Save Outcome
                </button>
            </div>
        </div>
    );
}
