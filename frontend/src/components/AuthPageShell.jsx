import React from 'react';
import { CheckCircle2, ClipboardCheck, GitBranch, ShieldCheck, Sparkles } from 'lucide-react';

const trustSignals = [
    { label: 'Evidence mapped', value: '92%', icon: ClipboardCheck },
    { label: 'Authorship verified', value: '3 repos', icon: GitBranch },
    { label: 'Risk flags clear', value: 'Low', icon: ShieldCheck },
];

export default function AuthPageShell({ eyebrow, title, subtitle, children, footer }) {
    return (
        <div className="min-h-screen bg-light-50 px-4 py-8 text-text-primary sm:px-6 lg:px-8">
            <div className="mx-auto flex min-h-[calc(100vh-4rem)] w-full max-w-6xl items-center">
                <div className="grid w-full gap-8 lg:grid-cols-[minmax(0,0.9fr)_minmax(420px,1fr)] lg:items-center">
                    <section className="mx-auto w-full max-w-md">
                        <LinkLogo />
                        <div className="mt-8 rounded-lg border border-light-200 bg-[#fffdf8]/95 p-6 shadow-card backdrop-blur sm:p-8">
                            <div>
                                <p className="text-xs font-semibold uppercase text-primary">{eyebrow}</p>
                                <h1 className="mt-3 text-3xl font-bold leading-tight text-text-primary sm:text-4xl">
                                    {title}
                                </h1>
                                <p className="mt-3 text-sm leading-6 text-text-secondary">{subtitle}</p>
                            </div>
                            <div className="mt-7">{children}</div>
                        </div>
                        {footer && <div className="mt-5 text-center text-sm text-text-secondary">{footer}</div>}
                    </section>

                    <aside className="hidden lg:block">
                        <div className="mb-6 max-w-xl">
                            <div className="inline-flex items-center gap-2 rounded-full border border-primary/15 bg-white/70 px-3 py-1 text-xs font-semibold text-primary shadow-sm">
                                <Sparkles className="h-3.5 w-3.5 text-accent" />
                                Proof-first hiring workspace
                            </div>
                            <h2 className="mt-5 text-4xl font-bold leading-tight text-text-primary">
                                Review real work before the interview loop starts.
                            </h2>
                            <p className="mt-4 max-w-lg text-base leading-7 text-text-secondary">
                                SignalStack turns repositories, context, and reviewer feedback into a clean evaluation queue for hiring teams.
                            </p>
                        </div>

                        <div className="grid gap-4 sm:grid-cols-3">
                            {trustSignals.map((signal) => {
                                const Icon = signal.icon;
                                return (
                                    <div key={signal.label} className="rounded-lg border border-light-200 bg-white/80 p-4 shadow-sm">
                                        <Icon className="h-5 w-5 text-primary" />
                                        <div className="mt-4 text-xl font-bold text-text-primary">{signal.value}</div>
                                        <div className="mt-1 text-xs font-medium text-text-secondary">{signal.label}</div>
                                    </div>
                                );
                            })}
                        </div>

                        <div className="mt-4 rounded-lg border border-primary/15 bg-white/85 p-5 shadow-card">
                            <div className="flex items-start justify-between border-b border-light-200 pb-4">
                                <div>
                                    <p className="text-xs font-semibold uppercase text-text-muted">Candidate signal</p>
                                    <h3 className="mt-1 text-lg font-bold text-text-primary">Backend Platform Engineer</h3>
                                </div>
                                <span className="rounded-full bg-primary-soft px-3 py-1 text-xs font-semibold text-primary">
                                    Ready
                                </span>
                            </div>

                            <div className="mt-5 space-y-4">
                                {[
                                    ['Repository depth', 'Strong', 'w-[88%]'],
                                    ['Production readiness', 'High', 'w-[76%]'],
                                    ['Role alignment', 'Matched', 'w-[82%]'],
                                ].map(([label, value, width]) => (
                                    <div key={label}>
                                        <div className="mb-2 flex items-center justify-between text-sm">
                                            <span className="font-medium text-text-secondary">{label}</span>
                                            <span className="font-semibold text-primary">{value}</span>
                                        </div>
                                        <div className="h-2 rounded-full bg-light-100">
                                            <div className={`h-2 rounded-full bg-gradient-to-r from-primary to-accent ${width}`} />
                                        </div>
                                    </div>
                                ))}
                            </div>

                            <div className="mt-5 flex items-center gap-2 rounded-lg bg-primary-soft/70 px-3 py-2 text-sm text-primary">
                                <CheckCircle2 className="h-4 w-4 flex-none" />
                                <span className="font-semibold">Evidence-backed report generated</span>
                            </div>
                        </div>
                    </aside>
                </div>
            </div>
        </div>
    );
}

function LinkLogo() {
    return (
        <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent text-lg font-bold text-white shadow-glow-sm">
                S
            </div>
            <div>
                <div className="text-lg font-bold text-text-primary">SignalStack</div>
                <div className="text-xs font-medium text-text-secondary">Proof of work evaluation</div>
            </div>
        </div>
    );
}
