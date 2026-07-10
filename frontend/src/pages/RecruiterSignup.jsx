import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { AlertTriangle, ArrowRight, Loader2, Lock, Mail, User } from 'lucide-react';
import { getRecruiterInvite, recruiterSignup } from '../api';
import AuthPageShell from '../components/AuthPageShell';

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
        'block w-full rounded-lg border border-light-200 bg-white py-3 pl-11 pr-4 text-text-primary placeholder-text-muted shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 sm:text-sm';

    return (
        <AuthPageShell
            eyebrow="Invite signup"
            title="Create your recruiter account."
            subtitle="Set up your SignalStack workspace using the email your admin invited."
            footer={
                <>
                    Already have an account?{' '}
                    <Link to="/login" className="font-bold text-primary hover:underline">
                        Sign in
                    </Link>
                </>
            }
        >
            {loading ? (
                <div className="flex items-center gap-3 rounded-lg border border-primary/15 bg-primary-soft/70 p-4 text-sm font-semibold text-primary">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Checking invite...
                </div>
            ) : error && !invite ? (
                <div className="rounded-lg border border-error/30 bg-error/5 p-4 text-sm text-error">
                    <div className="flex items-start gap-3">
                        <AlertTriangle className="mt-0.5 h-5 w-5 flex-none" />
                        <div>
                            <p className="font-bold">Invite unavailable</p>
                            <p className="mt-1 leading-5">{error}</p>
                        </div>
                    </div>
                    <Link
                        to="/login"
                        className="mt-4 inline-flex items-center rounded-lg border border-error/25 px-3 py-2 text-xs font-bold text-error hover:bg-error hover:text-white"
                    >
                        Back to login
                    </Link>
                </div>
            ) : (
                <form className="space-y-5" onSubmit={handleSubmit}>
                    <div>
                        <label htmlFor="name" className="mb-2 block text-sm font-semibold text-text-secondary">
                            Name
                        </label>
                        <div className="relative">
                            <User className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
                            <input
                                id="name"
                                name="name"
                                type="text"
                                className={inputClass}
                                placeholder="Your name"
                                value={name}
                                onChange={(event) => setName(event.target.value)}
                            />
                        </div>
                    </div>

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
                                className={`${inputClass} bg-light-50`}
                                placeholder="Email address"
                                value={email}
                                readOnly
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
                                minLength={8}
                                className={inputClass}
                                placeholder="At least 8 characters"
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

                    <button
                        type="submit"
                        disabled={submitting}
                        className="group inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-bold text-white shadow-glow-sm hover:bg-primary-hover disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
                    >
                        {submitting ? 'Creating account...' : 'Create account'}
                        {!submitting && <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />}
                    </button>
                </form>
            )}
        </AuthPageShell>
    );
}
