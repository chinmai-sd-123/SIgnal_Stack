import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Briefcase, MapPin, Building, IndianRupee, CheckCircle, RefreshCw, ArrowRight } from 'lucide-react';
import { getOutcomeTemplates } from '../api';
import TemplateSelector from '../components/TemplateSelector';

export default function JobCreateWizard() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1); // 1: Job Info, 2: Template Selection
  const [loading] = useState(false);
  const [templates, setTemplates] = useState([]);

  const [formData, setFormData] = useState({
    title: '',
    company: 'SignalStack',
    location: 'Remote',
    description: '',
    category: 'Software Engineering',
    subcategory: '',
    job_type: 'Full-time',
    salary_min: '',
    salary_max: '',
    currency: 'INR'
  });

  // Load templates on mount
  useEffect(() => {
    getOutcomeTemplates('software-engineering')
      .then(data => setTemplates(data))
      .catch(err => console.error('Failed to load templates', err));
  }, []);

  const handleJobSubmit = async (e) => {
    e.preventDefault();
    // Don't create job yet - just move to template selection
    // Job will be created together with outcomes to ensure atomicity
    setStep(2);
  };

  const handleTemplateSelect = (template) => {
    // Navigate to outcome creation with template data AND job form data
    navigate('/outcomes/create-with-job', {
      state: { template, jobData: formData }
    });
  };

  const handleSkipTemplate = () => {
    // Navigate to outcome creation without template but WITH job data
    navigate('/outcomes/create-with-job', {
      state: { jobData: formData }
    });
  };

  if (step === 2) {
    return (
      <TemplateSelector
        templates={templates}
        onSelect={handleTemplateSelect}
        onSkip={handleSkipTemplate}
      />
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-8 pb-12">
      <div className="flex justify-between items-center">
        <h1 className="heading-1">Post New Job</h1>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center text-sm font-bold">1</div>
            <span className="font-medium text-text-primary">Job Details</span>
          </div>
          <ArrowRight className="w-4 h-4" />
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-primary-soft text-primary flex items-center justify-center text-sm font-bold">2</div>
            <span className="text-text-secondary">Outcomes</span>
          </div>
        </div>
      </div>

      <form onSubmit={handleJobSubmit} className="card space-y-6">
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

        <div className="flex justify-between pt-4 border-t border-gray-100">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="btn btn-ghost text-gray-600 hover:text-gray-900"
          >
            Cancel & Return to Dashboard
          </button>
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
                Continue to Outcomes
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
