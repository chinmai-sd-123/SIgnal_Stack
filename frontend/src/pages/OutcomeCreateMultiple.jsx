import React, { useState, useEffect } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { Plus, Trash2, CheckCircle, Sparkles, RefreshCw, ArrowLeft, X } from 'lucide-react';
import { createOutcome, suggestTasks, getJob, createJob, getOutcomeTemplates } from '../api';
import TemplateSelectionModal from '../components/TemplateSelectionModal';

export default function OutcomeCreateMultiple() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(null); // Index of outcome being generated
  const [job, setJob] = useState(null);
  const [templates, setTemplates] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Load templates for the dropdown
  useEffect(() => {
    getOutcomeTemplates()
      .then(data => setTemplates(data))
      .catch(err => console.error("Failed to load templates", err));
  }, []);

  // Support for template-based initialization
  const template = location.state?.template;
  const jobData = location.state?.jobData; // Job data from wizard (not yet created)

  // Multiple outcomes (array of outcome objects)
  // Multiple outcomes (array of outcome objects)
  const [outcomes, setOutcomes] = useState(() => {
    // 1. New Role-Based Templates (Multiple Outcomes)
    if (template?.outcomes && template.outcomes.length > 0) {
      return template.outcomes.map((o, idx) => ({
        id: `template-${idx}`,
        title: o.title,
        description: o.description,
        tasks: [], // Tasks usually generated via AI for these
        source_template_id: template.id, // Link to Master Template
        save_as_template: false
      }));
    }
    // 2. Legacy/Single Templates (Title + Tasks)
    else if (template?.title || template?.tasks) {
      return [{
        id: `template-legacy`,
        title: template.title || '',
        description: template.description || '',
        tasks: template.tasks ? template.tasks.map((t, i) => ({
          id: `legacy-task-${i}`,
          name: t.name,
          priority: t.priority || 'Medium'
        })) : [],
        source_template_id: template.id, // Link to Master Template
        save_as_template: false
      }];
    }

    // 3. Fallback: Start with one empty outcome
    return [{
      id: 'outcome-0',
      title: '',
      description: '',
      tasks: [],
      source_template_id: null,
      save_as_template: false
    }];
  });

  // Load Job Context (only if jobId exists - for legacy flow)
  useEffect(() => {
    if (jobId) {
      async function loadJobContext() {
        try {
          const jobData = await getJob(jobId);
          setJob(jobData);
        } catch (error) {
          console.error('Failed to load job context', error);
        }
      }
      loadJobContext();
    } else if (jobData) {
      // Use job data from wizard (not yet created)
      setJob(jobData);
    }
  }, [jobId, jobData]);

  const updateOutcome = (index, field, value) => {
    const newOutcomes = [...outcomes];
    newOutcomes[index][field] = value;
    setOutcomes(newOutcomes);
  };

  const addOutcome = () => {
    setOutcomes([...outcomes, {
      id: `outcome-${Date.now()}`,
      title: '',
      description: '',
      tasks: [],
      save_as_template: false
    }]);
  };

  const removeOutcome = (index) => {
    if (outcomes.length === 1) {
      alert('You must have at least one outcome');
      return;
    }
    const newOutcomes = [...outcomes];
    newOutcomes.splice(index, 1);
    setOutcomes(newOutcomes);
  };

  const handleGenerateTasks = async (outcomeIndex) => {
    const outcome = outcomes[outcomeIndex];
    if (!outcome.description) return;

    setGenerating(outcomeIndex);
    try {
      const context = job
        ? `Job Title: ${job.title}\nJob Description: ${job.description}\n\nOutcome Goal: ${outcome.description}`
        : outcome.description;

      const suggestions = await suggestTasks(context);
      const formatted = suggestions.map((t, i) => ({
        ...t,
        id: `task-${outcomeIndex}-${i}`,
        priority: t.priority || 'Medium'
      }));

      updateOutcome(outcomeIndex, 'tasks', formatted);
    } catch (error) {
      console.error('Failed to generate tasks', error);
      alert('Failed to generate tasks. Please try again.');
    } finally {
      setGenerating(null);
    }
  };

  const updateTask = (outcomeIndex, taskIndex, field, value) => {
    const newOutcomes = [...outcomes];
    newOutcomes[outcomeIndex].tasks[taskIndex][field] = value;
    setOutcomes(newOutcomes);
  };

  const addTask = (outcomeIndex) => {
    const newOutcomes = [...outcomes];
    newOutcomes[outcomeIndex].tasks.push({
      id: `manual-${Date.now()}`,
      name: '',
      priority: 'Medium'
    });
    setOutcomes(newOutcomes);
  };

  const removeTask = (outcomeIndex, taskIndex) => {
    const newOutcomes = [...outcomes];
    newOutcomes[outcomeIndex].tasks.splice(taskIndex, 1);
    setOutcomes(newOutcomes);
  };

  const handleSaveAll = async () => {
    setLoading(true);
    try {
      // Validate all outcomes have tasks
      for (const outcome of outcomes) {
        if (!outcome.title || outcome.tasks.length === 0) {
          alert('Please complete all outcomes and ensure each has at least one task');
          setLoading(false);
          return;
        }
      }

      let finalJobId = jobId;

      // Step 1: Create job if it doesn't exist yet (new flow from wizard)
      if (!jobId && jobData) {
        const jobPayload = {
          ...jobData,
          salary_min: jobData.salary_min ? parseInt(jobData.salary_min) : null,
          salary_max: jobData.salary_max ? parseInt(jobData.salary_max) : null
        };
        const createdJob = await createJob(jobPayload);
        finalJobId = createdJob.id;
      }

      // Step 2: Create each outcome with its tasks
      for (const outcome of outcomes) {
        const payload = {
          title: outcome.title,
          description: outcome.description,
          company: job?.company || 'SignalStack',
          location: job?.location || 'Remote',
          category: job?.category || 'Software Engineering',
          proof_type: 'github',
          job_id: finalJobId,
          source_template_id: outcome.source_template_id, // CRITICAL: Links feedback loop
          save_as_template: outcome.save_as_template,
          tasks: outcome.tasks.map(t => ({
            name: t.name,
            priority: t.priority,
            weight: t.priority === 'High' ? 0.5 : t.priority === 'Medium' ? 0.3 : 0.2
          }))
        };

        await createOutcome(payload);
      }

      // Navigate to the job detail page
      navigate(`/jobs/${finalJobId}`);
    } catch (error) {
      console.error('Failed to save job and outcomes', error);
      alert(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-12">
      <div className="flex justify-between items-end mb-8">
        <div className="flex items-center gap-4">
          {jobId && (
            <button onClick={() => navigate(`/jobs/${jobId}`)} className="text-gray-500 hover:text-primary">
              <ArrowLeft className="w-5 h-5" />
            </button>
          )}
          <div>
            <h1 className="heading-1">{jobId ? 'Define Outcomes' : 'Create Job & Outcomes'}</h1>
            {job && jobId && <p className="text-sm text-gray-500">For Job: <span className="font-semibold">{job.title}</span></p>}
            {job && !jobId && <p className="text-sm text-gray-500">Job: <span className="font-semibold">{job.title}</span> (will be created)</p>}
            {template && (
              <p className="text-xs text-primary mt-1">
                Using template: <span className="font-semibold">{template.role_name || template.title}</span> • {outcomes.length} outcomes
              </p>
            )}
          </div>
        </div>
        <button
          onClick={() => navigate('/')}
          className="btn btn-ghost text-gray-600 hover:text-gray-900"
        >
          Cancel & Return to Dashboard
        </button>
      </div>

      {/* Modal Integration */}
      <TemplateSelectionModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSelect={(t) => {
          let newOutcomesToAdd = [];

          // Case A: Role Template (Multiple Outcomes)
          if (t.role_name && t.outcomes && t.outcomes.length > 0) {
            newOutcomesToAdd = t.outcomes.map((o, idx) => ({
              id: `outcome-${Date.now()}-${idx}`,
              title: o.title,
              description: o.description || '',
              tasks: [], // Typically AI generated
              source_template_id: t.id, // Link to Master Template
              save_as_template: false
            }));
          }
          // Case B: Legacy/Single Template
          else {
            newOutcomesToAdd = [{
              id: `outcome-${Date.now()}`,
              title: t.title || t.role_name || 'Untitled',
              description: t.description || '',
              tasks: t.tasks ? t.tasks.map((task, i) => ({
                id: `tpl-task-${Date.now()}-${i}`,
                name: task.name,
                priority: task.weight >= 0.5 ? 'High' : task.weight >= 0.3 ? 'Medium' : 'Low'
              })) : [],
              source_template_id: t.id, // Link to Master Template
              save_as_template: false
            }];
          }

          setOutcomes([...outcomes, ...newOutcomesToAdd]);
          setIsModalOpen(false);
        }}
      />

      <div className="flex justify-end mb-4">
        <button
          onClick={() => setIsModalOpen(true)}
          className="btn btn-secondary flex items-center gap-2"
        >
          <Sparkles className="w-4 h-4 text-primary-hover" />
          Add from Template
        </button>
      </div>

      {outcomes.map((outcome, outcomeIndex) => (
        <div key={outcome.id} className="card space-y-6 relative">
          {/* Remove Outcome Button */}
          {outcomes.length > 1 && (
            <button
              onClick={() => removeOutcome(outcomeIndex)}
              className="absolute top-4 right-4 p-2 text-gray-400 hover:text-red-500 rounded-full hover:bg-red-50 transition-colors"
              title="Remove outcome"
            >
              <X className="w-5 h-5" />
            </button>
          )}

          <div className="card-header pb-0 border-b-0">
            <h2 className="heading-2">Outcome {outcomeIndex + 1}</h2>
          </div>

          {/* Outcome Details */}
          <div className="grid grid-cols-1 gap-6">
            <div>
              <label className="input-label">Outcome Title</label>
              <input
                type="text"
                placeholder="e.g. Build Core API Service"
                value={outcome.title}
                onChange={(e) => updateOutcome(outcomeIndex, 'title', e.target.value)}
                className="input-field"
              />
            </div>

            <div>
              <label className="input-label">Description & Success Criteria</label>
              <textarea
                rows={4}
                placeholder="Describe what success looks like for this outcome..."
                value={outcome.description}
                onChange={(e) => updateOutcome(outcomeIndex, 'description', e.target.value)}
                className="input-field"
              />
            </div>

            {/* Save Template Option */}
            <div className="flex items-center gap-2 pt-2">
              <input
                type="checkbox"
                id={`saveTemplate-${outcome.id}`}
                checked={outcome.save_as_template || false}
                onChange={(e) => updateOutcome(outcomeIndex, 'save_as_template', e.target.checked)}
                className="checkbox checkbox-primary h-5 w-5 rounded border-gray-300 text-primary focus:ring-primary"
              />
              <label htmlFor={`saveTemplate-${outcome.id}`} className="text-sm font-medium text-gray-700 cursor-pointer select-none">
                Save as reusable Template?
                <span className="block text-xs text-gray-400 font-normal">
                  This creates a Master Template that learns from future feedback.
                </span>
              </label>
            </div>
          </div>

          {/* Tasks Section */}
          <div className="border-t border-gray-100 pt-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                Evaluation Signals
                <span className="ml-2 text-sm text-gray-500">({outcome.tasks.length})</span>
              </h3>
              <div className="flex gap-2">
                <button
                  onClick={() => handleGenerateTasks(outcomeIndex)}
                  disabled={generating === outcomeIndex || !outcome.description}
                  className="btn btn-sm btn-secondary"
                >
                  {generating === outcomeIndex ? (
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
                <button onClick={() => addTask(outcomeIndex)} className="btn btn-sm btn-secondary">
                  <Plus className="w-4 h-4 mr-1" /> Add Manual
                </button>
              </div>
            </div>

            {outcome.tasks.length === 0 ? (
              <div className="text-center py-8 bg-gray-50 rounded-lg border-2 border-dashed border-gray-200">
                <p className="text-gray-500 text-sm">No signals defined yet. Use AI Suggest or Add Manual.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {outcome.tasks.map((task, taskIndex) => (
                  <div key={task.id} className="flex gap-4 items-center bg-gray-50 p-4 rounded-lg border border-gray-200">
                    <span className="text-xs font-bold text-gray-400 font-mono">{(taskIndex + 1).toString().padStart(2, '0')}</span>
                    <div className="flex-grow grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="md:col-span-2">
                        <input
                          type="text"
                          value={task.name}
                          onChange={(e) => updateTask(outcomeIndex, taskIndex, 'name', e.target.value)}
                          className="input-field border-gray-200 bg-white"
                          placeholder="Signal name..."
                        />
                      </div>
                      <div>
                        <select
                          value={task.priority}
                          onChange={(e) => updateTask(outcomeIndex, taskIndex, 'priority', e.target.value)}
                          className="input-field border-gray-200 bg-white"
                        >
                          <option>High</option>
                          <option>Medium</option>
                          <option>Low</option>
                        </select>
                      </div>
                    </div>
                    <button
                      onClick={() => removeTask(outcomeIndex, taskIndex)}
                      className="p-2 text-gray-400 hover:text-red-500 rounded-full hover:bg-red-50 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ))}

      {/* Add Another Outcome */}
      <button
        onClick={addOutcome}
        className="btn btn-ghost w-full border-2 border-dashed border-gray-300 hover:border-primary hover:bg-primary-soft"
      >
        <Plus className="w-5 h-5 mr-2" />
        Add Another Outcome
      </button>

      {/* Save All Button */}
      <div className="flex justify-end pt-4 sticky bottom-6 bg-white p-4 rounded-lg shadow-lg border border-gray-200">
        <button
          onClick={handleSaveAll}
          disabled={loading || outcomes.some(o => !o.title || o.tasks.length === 0)}
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
              {jobId
                ? `Create ${outcomes.length} Outcome${outcomes.length > 1 ? 's' : ''}`
                : `Create Job & ${outcomes.length} Outcome${outcomes.length > 1 ? 's' : ''}`
              }
            </>
          )}
        </button>
      </div>
    </div>
  );
}
