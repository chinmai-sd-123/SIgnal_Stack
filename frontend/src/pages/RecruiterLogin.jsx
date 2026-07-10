import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, KeyRound, Lock, Mail } from 'lucide-react';
import { recruiterLogin } from '../api';
import AuthPageShell from '../components/AuthPageShell';

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
        'block w-full rounded-lg border border-light-200 bg-white py-3 pl-11 pr-4 text-text-primary placeholder-text-muted shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 sm:text-sm';

    return (
        <AuthPageShell
            eyebrow="Recruiter login"
            title="Welcome back."
            subtitle="Sign in to your hiring workspace and continue reviewing candidate proof of work."
            footer="New recruiter accounts require an admin invite."
        >
            <form className="space-y-5" onSubmit={handleSubmit}>
                <div>
                    <label htmlFor="email-address" className="mb-2 block text-sm font-semibold text-text-secondary">
                        Email address
                    </label>
                    <div className="relative">
                        <Mail className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
                        <input
                            id="email-address"
                            name="email"
                            type="email"
                            required
                            className={inputClass}
                            placeholder="you@company.com"
                            value={email}
                            onChange={(event) => setEmail(event.target.value)}
                        />
                    </div>
                </div>

                <div>
                    <label htmlFor="password" className="mb-2 block text-sm font-semibold text-text-secondary">
                        Password
                    </label>
                    <div className="relative">
                        <Lock className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
                        <input
                            id="password"
                            name="password"
                            type="password"
                            required
                            className={inputClass}
                            placeholder="Enter password"
                            value={password}
                            onChange={(event) => setPassword(event.target.value)}
                        />
                    </div>
                </div>

                {error && (
                    <div className="rounded-lg border border-error/30 bg-error/5 px-3 py-2 text-sm font-medium text-error">
                        {error}
                    </div>
                )}

                <div className="rounded-lg border border-primary/15 bg-primary-soft/70 p-4">
                    <div className="flex items-start gap-3">
                        <div className="flex h-9 w-9 flex-none items-center justify-center rounded-lg bg-white text-primary shadow-sm">
                            <KeyRound className="h-4 w-4" />
                        </div>
                        <div>
                            <p className="text-sm font-bold text-primary">Demo access</p>
                            <p className="mt-1 text-xs leading-5 text-text-secondary">
                                Use the shared recruiter account to inspect the product.
                            </p>
                        </div>
                    </div>

                    <div className="mt-4 grid gap-2 rounded-lg bg-white/70 p-3 font-mono text-xs text-text-primary">
                        <div className="flex items-center justify-between gap-3">
                            <span className="text-text-muted">Email</span>
                            <span className="select-all text-right">{DEMO_EMAIL}</span>
                        </div>
                        <div className="flex items-center justify-between gap-3">
                            <span className="text-text-muted">Password</span>
                            <span className="select-all">{DEMO_PASSWORD}</span>
                        </div>
                    </div>

                    <button
                        type="button"
                        onClick={fillDemoCredentials}
                        className="mt-3 inline-flex items-center gap-2 rounded-lg border border-primary/25 bg-white px-3 py-2 text-xs font-bold text-primary shadow-sm hover:border-primary hover:bg-primary hover:text-white"
                    >
                        Use demo credentials
                    </button>
                </div>

                <button
                    type="submit"
                    disabled={submitting}
                    className="group inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-bold text-white shadow-glow-sm hover:bg-primary-hover disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
                >
                    {submitting ? 'Signing in...' : 'Sign in'}
                    {!submitting && <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />}
                </button>
            </form>

            <p className="mt-6 text-center text-sm text-text-secondary">
                Have an invite?{' '}
                <Link to="/signup" className="font-bold text-primary hover:underline">
                    Create your account
                </Link>
            </p>
        </AuthPageShell>
    );
};

export default RecruiterLogin;
