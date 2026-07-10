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

    const inputClass =
        'block w-full rounded-xl border border-light-200 bg-white px-4 py-2.5 text-text-primary placeholder-text-muted shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30 sm:text-sm';

    return (
        <div className="min-h-screen flex items-center justify-center bg-hero-gradient py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-md w-full animate-slide-up">
                <div className="text-center mb-6">
                    <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-1.5 text-sm font-semibold tracking-wide text-white backdrop-blur">
                        <span className="h-2 w-2 rounded-full bg-accent" />
                        SignalStack
                    </div>
                    <h2 className="mt-5 text-3xl font-bold text-white">Create Recruiter Account</h2>
                    <p className="mt-2 text-sm text-white/70">
                        Accounts are invite-only. Use the email your admin invited.
                    </p>
                </div>

                <div className="rounded-3xl bg-bg-card shadow-card p-8">
                    {loading ? (
                        <div className="text-center text-sm text-text-secondary">Checking invite…</div>
                    ) : error && !invite ? (
                        <div className="rounded-xl border border-error/30 bg-error/5 p-4 text-sm text-error">
                            {error}
                            <div className="mt-3">
                                <Link to="/login" className="font-semibold text-error underline">Back to login</Link>
                            </div>
                        </div>
                    ) : (
                        <form className="space-y-5" onSubmit={handleSubmit}>
                            <div>
                                <label htmlFor="name" className="block text-sm font-medium text-text-secondary mb-1">Name</label>
                                <input
                                    id="name"
                                    name="name"
                                    type="text"
                                    className={inputClass}
                                    placeholder="Your name"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                />
                            </div>
                            <div>
                                <label htmlFor="email-address" className="block text-sm font-medium text-text-secondary mb-1">Email address</label>
                                <input
                                    id="email-address"
                                    name="email"
                                    type="email"
                                    required
                                    className={`${inputClass} bg-light-50`}
                                    placeholder="Email address"
                                    value={email}
                                    readOnly
                                />
                            </div>
                            <div>
                                <label htmlFor="password" className="block text-sm font-medium text-text-secondary mb-1">Password</label>
                                <input
                                    id="password"
                                    name="password"
                                    type="password"
                                    required
                                    minLength={8}
                                    className={inputClass}
                                    placeholder="At least 8 characters"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                />
                            </div>

                            {error && (
                                <div className="rounded-xl border border-error/30 bg-error/5 px-3 py-2 text-sm text-error">{error}</div>
                            )}

                            <button
                                type="submit"
                                disabled={submitting}
                                className="w-full rounded-xl bg-primary py-2.5 px-4 text-sm font-semibold text-white shadow-glow-sm transition-colors hover:bg-primary-hover disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
                            >
                                {submitting ? 'Creating account…' : 'Create account'}
                            </button>

                            <p className="text-center text-sm text-text-secondary">
                                Already have an account?{' '}
                                <Link to="/login" className="font-semibold text-primary hover:underline">Sign in</Link>
                            </p>
                        </form>
                    )}
                </div>
            </div>
        </div>
    );
}
