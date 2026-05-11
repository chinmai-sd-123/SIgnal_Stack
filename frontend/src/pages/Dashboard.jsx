import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, ChevronRight, Activity, Users, CheckCircle } from 'lucide-react';
import { getOutcomes } from '../api';

export default function Dashboard() {
    const [outcomes, setOutcomes] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function loadOutcomes() {
            try {
                const data = await getOutcomes();
                setOutcomes(data);
            } catch (error) {
                console.error("Failed to load outcomes", error);
            } finally {
                setLoading(false);
            }
        }
        loadOutcomes();
    }, []);

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">Outcomes</h1>
                    <p className="mt-1 text-sm text-gray-500">Manage work definitions and evaluations.</p>
                </div>
                <Link
                    to="/create-outcome"
                    className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
                >
                    <Plus className="-ml-1 mr-2 h-5 w-5" aria-hidden="true" />
                    New Outcome
                </Link>
            </div>

            {loading ? (
                <div className="text-center py-12">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-primary border-t-transparent"></div>
                    <p className="mt-2 text-gray-500">Loading outcomes...</p>
                </div>
            ) : outcomes.length === 0 ? (
                <div className="text-center py-12 bg-white rounded-lg border-2 border-dashed border-gray-300">
                    <Activity className="mx-auto h-12 w-12 text-gray-400" />
                    <h3 className="mt-2 text-sm font-medium text-gray-900">No outcomes defined</h3>
                    <p className="mt-1 text-sm text-gray-500">Get started by creating a new outcome definition.</p>
                    <div className="mt-6">
                        <Link
                            to="/create-outcome"
                            className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary hover:bg-primary-hover"
                        >
                            <Plus className="-ml-1 mr-2 h-5 w-5" aria-hidden="true" />
                            Create Outcome
                        </Link>
                    </div>
                </div>
            ) : (
                <div className="bg-white shadow overflow-hidden sm:rounded-md border border-gray-200">
                    <ul className="divide-y divide-gray-200">
                        {outcomes.map((outcome) => (
                            <li key={outcome.id}>
                                <Link to={`/dashboard/${outcome.id}`} className="block hover:bg-gray-50 transition duration-150 ease-in-out">
                                    <div className="px-4 py-4 sm:px-6">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center truncate">
                                                <div className="flex-shrink-0">
                                                    <div className="h-10 w-10 rounded-full bg-primary-soft flex items-center justify-center">
                                                        <Activity className="h-5 w-5 text-primary" />
                                                    </div>
                                                </div>
                                                <div className="ml-4 truncate">
                                                    <p className="text-sm font-medium text-primary truncate">{outcome.title}</p>
                                                    <p className="text-sm text-gray-500 truncate">{outcome.description}</p>
                                                </div>
                                            </div>
                                            <div className="ml-2 flex-shrink-0 flex">
                                                <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                                                    Active
                                                </span>
                                            </div>
                                        </div>
                                        <div className="mt-2 sm:flex sm:justify-between">
                                            <div className="sm:flex">
                                                <p className="flex items-center text-sm text-gray-500">
                                                    <CheckCircle className="flex-shrink-0 mr-1.5 h-4 w-4 text-gray-400" />
                                                    Status: {outcome.status || 'Active'}
                                                </p>
                                                <p className="mt-2 flex items-center text-sm text-gray-500 sm:mt-0 sm:ml-6">
                                                    <Users className="flex-shrink-0 mr-1.5 h-4 w-4 text-gray-400" />
                                                    Candidates Invited
                                                </p>
                                            </div>
                                            <div className="mt-2 flex items-center text-sm text-gray-500 sm:mt-0">
                                                <p>
                                                    ID: <span className="font-mono">{outcome.id}</span>
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
            )
            }
        </div >
    );
}
