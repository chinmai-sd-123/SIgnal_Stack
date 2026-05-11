import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
    Briefcase, MapPin, Building, IndianRupee, Clock,
    CheckCircle, Plus, ArrowLeft, ChevronRight, Trash2
} from 'lucide-react';
import { getJob, getJobOutcomes, deleteJob, finalizeShortlist, archiveJob } from '../api';

export default function JobDetail() {
    const { jobId } = useParams();
    const navigate = useNavigate();
    const [job, setJob] = useState(null);
    const [outcomes, setOutcomes] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function loadJob() {
            try {
                const [jobData, outcomesData] = await Promise.all([
                    getJob(jobId),
                    getJobOutcomes(jobId)
                ]);
                setJob(jobData);
                setOutcomes(outcomesData);
            } catch (error) {
                console.error("Failed to load job", error);
            } finally {
                setLoading(false);
            }
        }
        loadJob();
    }, [jobId]);

    const handleArchiveJob = async () => {
        const confirmed = window.confirm(
            `Archive this job posting?\n\n"${job.title}"\n\nThis will hide it from listings but keep all data. Outcomes and candidate submissions will be preserved.`
        );

        if (!confirmed) return;

        try {
            await deleteJob(jobId);  // Soft delete by default
            alert('Job archived successfully!');
            navigate('/');  // Redirect to dashboard
        } catch (error) {
            alert(`Failed to archive job: ${error.message}`);
        }
    };

    if (loading) return (
        <div className="flex justify-center items-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
    );

    if (!job) return <div className="p-8 text-center text-gray-500">Job not found.</div>;

    return (
        <div className="max-w-5xl mx-auto space-y-8 pb-12">
            <Link to="/" className="text-gray-500 hover:text-primary flex items-center gap-1 transition-colors">
                <ArrowLeft className="w-4 h-4" /> Back to Jobs
            </Link>

            {/* Job Header */}
            <div className="card">
                <div className="flex flex-col md:flex-row justify-between items-start gap-6">
                    <div>
                        <div className="flex items-center gap-3">
                            <h1 className="heading-1">{job.title}</h1>
                            <span className={`badge ${job.status === 'active' ? 'badge-success' :
                                job.status === 'closed' ? 'badge-info' :
                                    'badge-neutral'
                                }`}>
                                {job.status.toUpperCase()}
                            </span>
                            {job.applications_open !== undefined && (
                                <span className={`badge ${job.applications_open ? 'badge-success' : 'badge-error'
                                    }`}>
                                    Applications {job.applications_open ? 'OPEN' : 'CLOSED'}
                                </span>
                            )}
                        </div>

                        <div className="mt-4 flex flex-wrap gap-4 text-sm text-gray-600">
                            <div className="flex items-center gap-1">
                                <Building className="w-4 h-4 text-gray-400" />
                                {job.company}
                            </div>
                            <div className="flex items-center gap-1">
                                <MapPin className="w-4 h-4 text-gray-400" />
                                {job.location}
                            </div>
                            <div className="flex items-center gap-1">
                                <Clock className="w-4 h-4 text-gray-400" />
                                {job.job_type}
                            </div>
                            {(job.salary_min || job.salary_max) && (
                                <div className="flex items-center gap-1">
                                    <IndianRupee className="w-4 h-4 text-gray-400" />
                                    {job.currency === 'INR' ? '₹' : job.currency} {job.salary_min?.toLocaleString()} - {job.salary_max?.toLocaleString()}
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="flex gap-2">
                        <button
                            onClick={handleArchiveJob}
                            className="btn btn-ghost text-red-600 hover:text-red-700 hover:bg-red-50"
                        >
                            <Trash2 className="w-4 h-4 mr-2" />
                            Archive Job
                        </button>
                    </div>
                </div>

                    <div className="mt-6 pt-6 border-t border-gray-100">
                    <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-2">Description</h3>
                    <p className="text-gray-600 whitespace-pre-line">{job.description}</p>

                    {/* Shortlist Capacity Info */}
                    {job.total_positions !== undefined && (
                        <div className="mt-6 p-4 bg-primary-soft rounded-lg">
                            <h3 className="font-semibold text-primary mb-3">Shortlist Capacity</h3>
                            <div className="grid grid-cols-3 gap-4 text-sm">
                                <div>
                                    <div className="text-gray-600">Positions</div>
                                    <div className="text-2xl font-bold text-primary">{job.total_positions}</div>
                                </div>
                                <div>
                                    <div className="text-gray-600">Multiplier</div>
                                    <div className="text-2xl font-bold text-primary">{job.shortlist_multiplier || 3.0}×</div>
                                </div>
                                <div>
                                    <div className="text-gray-600">Shortlist Size</div>
                                    <div className="text-2xl font-bold text-primary">
                                        {Math.floor((job.total_positions || 1) * (job.shortlist_multiplier || 3.0))}
                                    </div>
                                </div>
                            </div>
                            <p className="text-xs text-gray-600 mt-3">
                                System will recommend {Math.floor((job.total_positions || 1) * (job.shortlist_multiplier || 3.0))} candidates for interviews
                            </p>
                        </div>
                    )}
                </div>
            </div>

            {/* Outcomes Section */}
            <div className="space-y-4">
                <div className="flex justify-between items-center">
                    <h2 className="text-2xl font-bold text-gray-900">Outcomes</h2>
                    <Link
                        to={`/jobs/${job.id}/add-outcome`}
                        className="btn btn-secondary"
                    >
                        <Plus className="w-4 h-4 mr-2" />
                        Add Outcome
                    </Link>
                </div>

                {(!outcomes || outcomes.length === 0) ? (
                    <div className="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed border-gray-200">
                        <CheckCircle className="mx-auto h-12 w-12 text-gray-300" />
                        <h3 className="mt-2 text-sm font-medium text-gray-900">No outcomes defined</h3>
                        <p className="mt-1 text-sm text-gray-500">Define what success looks like for this role.</p>
                        <div className="mt-6">
                            <Link
                                to={`/jobs/${job.id}/add-outcome`}
                                className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary hover:bg-primary-hover"
                            >
                                <Plus className="-ml-1 mr-2 h-5 w-5" aria-hidden="true" />
                                Add Outcome
                            </Link>
                        </div>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 gap-4">
                        {outcomes.map((outcome) => (
                            <Link
                                key={outcome.id}
                                to={`/dashboard/${outcome.id}`}
                                className="block bg-white p-6 rounded-lg shadow-sm border border-gray-200 hover:border-primary transition-colors"
                            >
                                <div className="flex justify-between items-start">
                                    <div>
                                        <h3 className="text-lg font-semibold text-gray-900 group-hover:text-primary">
                                            {outcome.title}
                                        </h3>
                                        <p className="text-gray-500 mt-1 line-clamp-2">{outcome.description}</p>
                                    </div>
                                    <div className="bg-primary-soft p-2 rounded-full text-primary">
                                        <ChevronRight className="w-5 h-5" />
                                    </div>
                                </div>
                                <div className="mt-4 flex items-center gap-4 text-sm text-gray-500">
                                    <span className="flex items-center gap-1">
                                        <CheckCircle className="w-4 h-4" />
                                        {outcome.tasks?.length || 0} Signals
                                    </span>
                                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${outcome.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                                        }`}>
                                        {outcome.status}
                                    </span>
                                </div>
                            </Link>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
