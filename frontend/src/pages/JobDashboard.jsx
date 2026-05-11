import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, ChevronRight, Briefcase, MapPin, Building, Users, Archive } from 'lucide-react';
import { getJobs } from '../api';

export default function JobDashboard() {
    const [jobs, setJobs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showArchived, setShowArchived] = useState(false);

    // Filter jobs based on archive toggle
    const displayedJobs = showArchived
        ? jobs.filter(job => job.status === 'archived')
        : jobs.filter(job => job.status !== 'archived');

    useEffect(() => {
        async function loadJobs() {
            try {
                const data = await getJobs();
                setJobs(data);
            } catch (error) {
                console.error("Failed to load jobs", error);
            } finally {
                setLoading(false);
            }
        }
        loadJobs();
    }, []);

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">
                        {showArchived ? 'Archived Jobs' : 'Active Jobs'}
                    </h1>
                    <p className="mt-1 text-sm text-gray-500">
                        {showArchived
                            ? `${displayedJobs.length} archived job${displayedJobs.length !== 1 ? 's' : ''}`
                            : 'Manage hiring roles and evaluation criteria.'
                        }
                    </p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={() => setShowArchived(!showArchived)}
                        className={`inline-flex items-center px-4 py-2 border shadow-sm text-sm font-medium rounded-md ${showArchived
                                ? 'border-gray-300 text-gray-700 bg-white hover:bg-gray-50'
                                : 'border-transparent text-white bg-primary hover:bg-primary-hover'
                            } focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary`}
                    >
                        <Archive className="-ml-1 mr-2 h-5 w-5" aria-hidden="true" />
                        {showArchived ? 'Show Active Jobs' : 'View Archive'}
                    </button>
                    {!showArchived && (
                        <Link
                            to="/create-job"
                            className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
                        >
                            <Plus className="-ml-1 mr-2 h-5 w-5" aria-hidden="true" />
                            New Job
                        </Link>
                    )}
                </div>
            </div>

            {loading ? (
                <div className="text-center py-12">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-primary border-t-transparent"></div>
                    <p className="mt-2 text-gray-500">Loading jobs...</p>
                </div>
            ) : displayedJobs.length === 0 ? (
                <div className="text-center py-12 bg-white rounded-lg border-2 border-dashed border-gray-300">
                    <Archive className="mx-auto h-12 w-12 text-gray-400" />
                    <h3 className="mt-2 text-sm font-medium text-gray-900">
                        {showArchived ? 'No archived jobs' : 'No active jobs'}
                    </h3>
                    <p className="mt-1 text-sm text-gray-500">
                        {showArchived
                            ? 'Archived jobs will appear here when you archive them.'
                            : 'Create a job description to start hiring.'
                        }
                    </p>
                    {!showArchived && (
                        <div className="mt-6">
                            <Link
                                to="/create-job"
                                className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary hover:bg-primary-hover"
                            >
                                <Plus className="-ml-1 mr-2 h-5 w-5" aria-hidden="true" />
                                Create Job
                            </Link>
                        </div>
                    )}
                </div>
            ) : (
                <div className="bg-white shadow overflow-hidden sm:rounded-md border border-gray-200">
                    <ul className="divide-y divide-gray-200">
                        {displayedJobs.map((job) => (
                            <li key={job.id}>
                                <Link to={`/jobs/${job.id}`} className="block hover:bg-gray-50 transition duration-150 ease-in-out">
                                    <div className="px-4 py-4 sm:px-6">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center truncate">
                                                <div className="flex-shrink-0">
                                                    <div className="h-10 w-10 rounded-full bg-primary-soft flex items-center justify-center">
                                                        <Briefcase className="h-5 w-5 text-primary" />
                                                    </div>
                                                </div>
                                                <div className="ml-4 truncate">
                                                    <p className="text-lg font-medium text-primary truncate">{job.title}</p>
                                                    <div className="flex items-center gap-4 mt-1">
                                                        <p className="flex items-center text-sm text-gray-500">
                                                            <Building className="flex-shrink-0 mr-1.5 h-4 w-4 text-gray-400" />
                                                            {job.company}
                                                        </p>
                                                        <p className="flex items-center text-sm text-gray-500">
                                                            <MapPin className="flex-shrink-0 mr-1.5 h-4 w-4 text-gray-400" />
                                                            {job.location}
                                                        </p>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="ml-2 flex-shrink-0 flex items-center gap-2">
                                                <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${job.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                                                    }`}>
                                                    {job.status.toUpperCase()}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="mt-2 sm:flex sm:justify-between">
                                            <div className="sm:flex">
                                                <p className="flex items-center text-sm text-gray-500">
                                                    {job.description?.substring(0, 100)}...
                                                </p>
                                            </div>
                                            <div className="mt-2 flex items-center text-sm text-gray-500 sm:mt-0">
                                                <p className="flex items-center mr-6">
                                                    <Users className="mr-1.5 h-4 w-4 text-gray-400" />
                                                    {job.outcomes?.length || 0} Outcomes
                                                </p>
                                                <ChevronRight className="ml-2 h-5 w-5 text-gray-400" />
                                            </div>
                                        </div>
                                    </div>
                                </Link>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}
