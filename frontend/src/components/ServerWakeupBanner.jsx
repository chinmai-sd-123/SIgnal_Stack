import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ServerCrash, CheckCircle2, Loader2, X } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const PING_TIMEOUT_MS = 2000;   // show banner if no response in 2s
const POLL_INTERVAL_MS = 5000;  // retry every 5s while sleeping

// Status values: 'checking' | 'sleeping' | 'awake' | 'hidden'
export default function ServerWakeupBanner() {
    const [status, setStatus] = useState('checking');
    const [elapsed, setElapsed] = useState(0);
    const [dismissed, setDismissed] = useState(false);
    const pollRef = useRef(null);
    const timerRef = useRef(null);
    const startTimeRef = useRef(null);

    const stopPolling = useCallback(() => {
        if (pollRef.current) clearInterval(pollRef.current);
        if (timerRef.current) clearInterval(timerRef.current);
    }, []);

    const pingBackend = useCallback(async () => {
        try {
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), PING_TIMEOUT_MS);
            const res = await fetch(`${API_URL}/`, { signal: controller.signal });
            clearTimeout(timeout);
            if (res.ok || res.status < 500) {
                setStatus('awake');
                stopPolling();
                // Auto-dismiss after 3s
                setTimeout(() => setStatus('hidden'), 3000);
                return true;
            }
        } catch {
            // Timed out or network error = still sleeping
        }
        return false;
    }, [stopPolling]);

    useEffect(() => {
        let initialCheckTimer;

        const init = async () => {
            const awake = await pingBackend();
            if (awake) {
                setStatus('hidden');
                return;
            }

            // Backend didn't respond within timeout — show sleeping banner
            setStatus('sleeping');
            startTimeRef.current = Date.now();

            // Elapsed seconds counter
            timerRef.current = setInterval(() => {
                setElapsed(Math.round((Date.now() - startTimeRef.current) / 1000));
            }, 1000);

            // Keep pinging
            pollRef.current = setInterval(async () => {
                await pingBackend();
            }, POLL_INTERVAL_MS);
        };

        // Give the page 300ms to settle before the first ping
        initialCheckTimer = setTimeout(init, 300);

        return () => {
            clearTimeout(initialCheckTimer);
            stopPolling();
        };
    }, [pingBackend, stopPolling]);

    if (status === 'hidden' || dismissed) return null;

    if (status === 'checking') return null; // silent until we know

    // ─── Sleeping banner ───────────────────────────────────────────────────────
    if (status === 'sleeping') {
        return (
            <div
                style={{
                    background: 'linear-gradient(90deg, #1e3a5f 0%, #1a2f4e 100%)',
                    borderBottom: '1px solid rgba(96,165,250,0.2)',
                }}
                className="relative w-full px-4 py-2.5 flex items-center justify-between gap-3 text-sm z-40"
            >
                {/* Left: Icon + message */}
                <div className="flex items-center gap-3 min-w-0">
                    <div className="flex-shrink-0 w-7 h-7 rounded-full bg-blue-500/20 flex items-center justify-center">
                        <Loader2 className="w-4 h-4 text-blue-300 animate-spin" />
                    </div>
                    <div className="min-w-0">
                        <span className="font-semibold text-blue-100">Waking up the backend server…</span>
                        <span className="ml-2 text-blue-300/70 hidden sm:inline">
                            Render free-tier spins down after inactivity. Usually takes 30–60 seconds.
                        </span>
                    </div>
                </div>

                {/* Right: timer + dismiss */}
                <div className="flex items-center gap-3 flex-shrink-0">
                    {/* Animated dots */}
                    <div className="flex items-center gap-1">
                        {[0, 1, 2].map(i => (
                            <span
                                key={i}
                                className="w-1.5 h-1.5 rounded-full bg-blue-400"
                                style={{
                                    animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite`,
                                }}
                            />
                        ))}
                    </div>
                    <span className="text-xs text-blue-300/60 font-mono tabular-nums">
                        {elapsed}s
                    </span>
                    <button
                        onClick={() => setDismissed(true)}
                        className="text-blue-400/60 hover:text-blue-200 transition-colors p-0.5 rounded"
                        aria-label="Dismiss"
                    >
                        <X className="w-3.5 h-3.5" />
                    </button>
                </div>

                {/* Progress shimmer bar */}
                <div className="absolute bottom-0 left-0 w-full h-0.5 bg-blue-900/40 overflow-hidden">
                    <div
                        className="h-full bg-blue-400/60"
                        style={{
                            width: `${Math.min((elapsed / 60) * 100, 95)}%`,
                            transition: 'width 1s linear',
                        }}
                    />
                </div>

                <style>{`
                    @keyframes bounce {
                        0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
                        40% { transform: translateY(-4px); opacity: 1; }
                    }
                `}</style>
            </div>
        );
    }

    // ─── Awake banner ──────────────────────────────────────────────────────────
    if (status === 'awake') {
        return (
            <div
                style={{
                    background: 'linear-gradient(90deg, #052e16 0%, #064e3b 100%)',
                    borderBottom: '1px solid rgba(52,211,153,0.2)',
                }}
                className="w-full px-4 py-2 flex items-center gap-3 text-sm z-40 animate-[fadeIn_0.3s_ease]"
            >
                <div className="w-6 h-6 rounded-full bg-green-500/20 flex items-center justify-center flex-shrink-0">
                    <CheckCircle2 className="w-4 h-4 text-green-400" />
                </div>
                <span className="font-semibold text-green-300">Backend is awake!</span>
                <span className="text-green-400/60 text-xs">All systems operational — loading your data…</span>
            </div>
        );
    }

    return null;
}
