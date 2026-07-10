
import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { recruiterLogin } from '../api';

const DEMO_EMAIL = 'demo@signalstack.dev';
const DEMO_PASSWORD = 'Demo@12345';

const RecruiterLogin = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const navigate = useNavigate();

    const fillDemoCredentials = () => {
        setEmail(DEMO_EMAIL);
        setPassword(DEMO_PASSWORD);
        setError('');
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSubmitting(true);

        try {
            const data = await recruiterLogin({ email, password });
            localStorage.setItem('authToken', data.access_token);
            localStorage.setItem('recruiterId', data.recruiter.id);
            localStorage.setItem('recruiterName', data.recruiter.name || data.recruiter.email);
            localStorage.setItem('recruiterRole', data.recruiter.role || 'recruiter');
            navigate('/');
        } catch (err) {
            setError(err.message || 'Login failed. Please check your credentials.');
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
                    <h2 className="mt-5 text-3xl font-bold text-white">Recruiter Login</h2>
                    <p className="mt-2 text-sm text-white/70">
                        Sign in to evaluate candidates on proof of work.
                    </p>
                </div>

                <div className="rounded-3xl bg-bg-card shadow-card p-8">
                    <form className="space-y-5" onSubmit={handleSubmit}>
                        <div>
                            <label htmlFor="email-address" className="block text-sm font-medium text-text-secondary mb-1">
                                Email address
                            </label>
                            <input
                                id="email-address"
                                name="email"
                                type="email"
                                required
                                className={inputClass}
                                placeholder="you@company.com"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                            />
                        </div>
                        <div>
                            <label htmlFor="password" className="block text-sm font-medium text-text-secondary mb-1">
                                Password
                            </label>
                            <input
                                id="password"
                                name="password"
                                type="password"
                                required
                                className={inputClass}
                                placeholder="••••••••"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                            />
                        </div>

                        {error && (
                            <div className="rounded-xl border border-error/30 bg-error/5 px-3 py-2 text-sm text-error">
                                {error}
                            </div>
                        )}

                        <div className="rounded-2xl border border-primary/20 bg-primary-soft/60 p-4">
                            <p className="text-sm font-semibold text-primary">Demo access for visitors</p>
                            <p className="mt-1 text-xs text-text-secondary">
                                Explore SignalStack with the shared demo recruiter account.
                            </p>
                            <div className="mt-3 space-y-1 font-mono text-xs text-text-primary">
                                <div>
                                    <span className="text-text-muted">Email:&nbsp;</span>
                                    <span className="select-all">{DEMO_EMAIL}</span>
                                </div>
                                <div>
                                    <span className="text-text-muted">Password:&nbsp;</span>
                                    <span className="select-all">{DEMO_PASSWORD}</span>
                                </div>
                            </div>
                            <button
                                type="button"
                                onClick={fillDemoCredentials}
                                className="mt-3 inline-flex items-center rounded-lg border border-primary px-3 py-1.5 text-xs font-semibold text-primary transition-colors hover:bg-primary hover:text-white"
                            >
                                Use demo credentials
                            </button>
                        </div>

                        <button
                            type="submit"
                            disabled={submitting}
                            className="w-full rounded-xl bg-primary py-2.5 px-4 text-sm font-semibold text-white shadow-glow-sm transition-colors hover:bg-primary-hover disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
                        >
                            {submitting ? 'Signing in…' : 'Sign in'}
                        </button>
                    </form>

                    <p className="mt-6 text-center text-sm text-text-secondary">
                        Have an invite?{' '}
                        <Link to="/signup" className="font-semibold text-primary hover:underline">
                            Create your account
                        </Link>
                    </p>
                </div>

                <p className="mt-4 text-center text-xs text-white/60">
                    New recruiter accounts require an admin invite.
                </p>
            </div>
        </div>
    );
};

export default RecruiterLogin;
