import React from 'react';
import { useNavigate } from 'react-router-dom';
import { PlusCircle, Briefcase } from 'lucide-react';

const RecruiterDashboard = () => {
    const navigate = useNavigate();
    const recruiterName = localStorage.getItem('recruiterName') || 'Recruiter';

    return (
        <div className="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-8">Welcome, {recruiterName}</h1>

            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                <div
                    onClick={() => navigate('/recruiter/create-job')}
                    className="relative block rounded-lg border-2 border-dashed border-gray-300 p-12 text-center hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 cursor-pointer bg-white transition shadow-sm hover:shadow-md"
                >
                    <PlusCircle className="mx-auto h-12 w-12 text-gray-400" />
                    <span className="mt-2 block text-sm font-semibold text-gray-900">Post a Job Vacancy</span>
                    <span className="block text-xs text-gray-500 mt-1">Create a new job listing with detailed requirements</span>
                </div>

                <div
                    onClick={() => navigate('/outcomes')}
                    className="relative block rounded-lg border border-gray-300 bg-white px-6 py-5 shadow-sm flex items-center space-x-3 hover:border-gray-400 focus-within:ring-2 focus-within:ring-primary focus-within:ring-offset-2 cursor-pointer transition hover:shadow-md"
                >
                    <div className="flex-shrink-0">
                        <div className="h-10 w-10 rounded-full bg-primary-soft flex items-center justify-center">
                            <Briefcase className="h-6 w-6 text-primary" />
                        </div>
                    </div>
                    <div className="flex-1 min-w-0">
                        <a href="#" className="focus:outline-none">
                            <span className="absolute inset-0" aria-hidden="true" />
                            <p className="text-sm font-medium text-gray-900">Analyze Existing Jobs</p>
                            <p className="text-sm text-gray-500 truncate">View outcomes and current status of job listings</p>
                        </a>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default RecruiterDashboard;
