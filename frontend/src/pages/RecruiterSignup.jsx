import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { getRecruiterInvite, recruiterSignup } from '../api';

export default function RecruiterSignup() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const inviteToken = searchParams.get('token') || '';
    const [invite, setInvite] = useState(null);
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        async function loadInvite() {
            setLoading(true);
            setError('');
            try {
                if (!inviteToken) {
                    throw new Error('Invite token missing');
                }
                const data = await getRecruiterInvite(inviteToken);
                setInvite(data);
                setName(data.name || '');
                setEmail(data.email || '');
            } catch (err) {
                setError(err.message || 'Invite not found');
            } finally {
                setLoading(false);
            }
        }
        loadInvite();
    }, [inviteToken]);

    const handleSubmit = async (event) => {
        event.preventDefault();
        setSubmitting(true);
        setError('');
        try {
            const data = await recruiterSignup({
                name,
                email,
                password,
                invite_token: inviteToken,
            });
            localStorage.setItem('authToken', data.access_token);
            localStorage.setItem('recruiterId', data.recruiter.id);
            localStorage.setItem('recruiterName', data.recruiter.name || data.recruiter.email);
            localStorage.setItem('recruiterRole', data.recruiter.role || 'recruiter');
            navigate('/');
        } catch (err) {
            setError(err.message || 'Failed to create account');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-md w-full space-y-8">
                <div>
                    <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
                        Create Recruiter Account
                    </h2>
                    <p className="mt-2 text-center text-sm text-gray-500">
                        Accounts are invite-only. Use the email your admin invited.
                    </p>
                </div>

                {loading ? (
                    <div className="rounded-lg border border-gray-200 bg-white p-6 text-center text-sm text-gray-500">
                        Checking invite...
                    </div>
                ) : error && !invite ? (
                    <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                        {error}
                        <div className="mt-3">
                            <Link to="/login" className="font-medium text-red-700 underline">Back to login</Link>
                        </div>
                    </div>
                ) : (
                    <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
                        <div className="rounded-md shadow-sm -space-y-px">
                            <div>
                                <label htmlFor="name" className="sr-only">Name</label>
                                <input
                                    id="name"
                                    name="name"
                                    type="text"
                                    className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-primary focus:border-primary focus:z-10 sm:text-sm"
                                    placeholder="Name"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                />
                            </div>
                            <div>
                                <label htmlFor="email-address" className="sr-only">Email address</label>
                                <input
                                    id="email-address"
                                    name="email"
                                    type="email"
                                    required
                                    className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 bg-gray-50 focus:outline-none focus:ring-primary focus:border-primary focus:z-10 sm:text-sm"
                                    placeholder="Email address"
                                    value={email}
                                    readOnly
                                />
                            </div>
                            <div>
                                <label htmlFor="password" className="sr-only">Password</label>
                                <input
                                    id="password"
                                    name="password"
                                    type="password"
                                    required
                                    minLength={8}
                                    className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-primary focus:border-primary focus:z-10 sm:text-sm"
                                    placeholder="Password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                />
                            </div>
                        </div>

                        {error && <div className="text-red-500 text-sm">{error}</div>}

                        <button
                            type="submit"
                            disabled={submitting}
                            className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-primary hover:bg-primary-hover disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
                        >
                            {submitting ? 'Creating account...' : 'Create account'}
                        </button>

                        <p className="text-center text-sm text-gray-500">
                            Already have an account? <Link to="/login" className="font-medium text-primary hover:underline">Sign in</Link>
                        </p>
                    </form>
                )}
            </div>
        </div>
    );
}
