import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Briefcase, MapPin, Building, IndianRupee, CheckCircle, RefreshCw } from 'lucide-react';
import { createJob, getOutcomeTemplates } from '../api';
import TemplateSelectionModal from '../components/TemplateSelectionModal';

export default function JobCreate() {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [templates, setTemplates] = useState([]);
    const [selectedTemplate, setSelectedTemplate] = useState('');
    const [isModalOpen, setIsModalOpen] = useState(false);

    const [formData, setFormData] = useState({
        title: '',
        company: 'SignalStack',
        location: 'Remote', // Default
        description: '',
        job_type: 'Full-time',
        salary_min: '',
        salary_max: '',
        currency: 'INR'
    });

    useEffect(() => {
        getOutcomeTemplates()
            .then(data => setTemplates(data))
            .catch(err => console.error("Failed to load templates", err));
    }, []);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            // Convert salary to numbers
            const payload = {
                ...formData,
                salary_min: formData.salary_min ? parseInt(formData.salary_min) : null,
                salary_max: formData.salary_max ? parseInt(formData.salary_max) : null
            };

            const result = await createJob(payload);
            // Pass selected template to the next screen (Job View -> Outcome Create)
            navigate(`/jobs/${result.id}`, { state: { template: selectedTemplate } });
        } catch (error) {
            console.error("Failed to create job", error);
            alert(`Error: ${error.message}`);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-3xl mx-auto space-y-8 pb-12">
            <div className="flex justify-between items-center">
                <h1 className="heading-1">Post New Job</h1>

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
                            {selectedTemplate ? (
                                <>
                                    <CheckCircle className="w-4 h-4 text-green-500" />
                                    <span className="text-gray-900 font-medium">
                                        {selectedTemplate.role_name || selectedTemplate.title}
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
                                setSelectedTemplate(t);
                                setIsModalOpen(false);
                            }}
                        />
                    </div>
                )}
            </div>

            <form onSubmit={handleSubmit} className="card space-y-6">

                {/* Basic Info */}
                <div className="grid grid-cols-1 gap-6">
                    <div>
                        <label className="input-label">Job Title</label>
                        <input
                            type="text"
                            required
                            placeholder="e.g. Senior Backend Engineer"
                            value={formData.title}
                            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                            className="input-field"
                        />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label className="input-label">Company Name</label>
                            <div className="relative">
                                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                    <Building className="h-4 w-4 text-gray-400" />
                                </div>
                                <input
                                    type="text"
                                    required
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
                                    required
                                    value={formData.location}
                                    onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                                    className="input-field pl-10"
                                />
                            </div>
                        </div>
                    </div>

                    <div>
                        <label className="input-label">Employment Type</label>
                        <select
                            value={formData.job_type}
                            onChange={(e) => setFormData({ ...formData, job_type: e.target.value })}
                            className="input-field"
                        >
                            <option>Full-time</option>
                            <option>Contract</option>
                            <option>Part-time</option>
                            <option>Internship</option>
                        </select>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label className="input-label">Salary Min (Annual)</label>
                            <div className="relative">
                                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                    <IndianRupee className="h-4 w-4 text-gray-400" />
                                </div>
                                <input
                                    type="number"
                                    placeholder="80000"
                                    value={formData.salary_min}
                                    onChange={(e) => setFormData({ ...formData, salary_min: e.target.value })}
                                    className="input-field pl-10"
                                />
                            </div>
                        </div>
                        <div>
                            <label className="input-label">Salary Max (Annual)</label>
                            <div className="relative">
                                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                    <IndianRupee className="h-4 w-4 text-gray-400" />
                                </div>
                                <input
                                    type="number"
                                    placeholder="150000"
                                    value={formData.salary_max}
                                    onChange={(e) => setFormData({ ...formData, salary_max: e.target.value })}
                                    className="input-field pl-10"
                                />
                            </div>
                        </div>
                    </div>

                    <div>
                        <label className="input-label">Job Description</label>
                        <textarea
                            rows={8}
                            required
                            placeholder="Describe the role responsibilities, requirements, and tech stack..."
                            value={formData.description}
                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            className="input-field"
                        />
                    </div>
                </div>

                <div className="flex justify-end pt-4 border-t border-gray-100">
                    <button
                        type="submit"
                        disabled={loading}
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
                                Create Job
                            </>
                        )}
                    </button>
                </div>
            </form>
        </div>
    );
}
