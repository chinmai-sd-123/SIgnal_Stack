import React, { useState } from 'react';
import ServerWakeupBanner from './ServerWakeupBanner';
import { Link, useLocation } from 'react-router-dom';
import {
    ClipboardList,
    Search,
    CheckCircle,
    Settings,
    BarChart2,
    Menu,
    X,
    Zap,
    LogOut
} from 'lucide-react';

export default function Layout({ children }) {
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const location = useLocation();

    // Hide recruiter chrome on candidate-facing pages
    const isPublicRoute = location.pathname.startsWith('/apply') || location.pathname.startsWith('/login') || location.pathname.startsWith('/signup');
    const recruiterName = localStorage.getItem('recruiterName') || 'Recruiter';
    const recruiterRole = localStorage.getItem('recruiterRole') || 'recruiter';

    const navigation = [
        { name: 'Jobs', href: '/', icon: ClipboardList },
        { name: 'Post Job', href: '/create-job', icon: Zap },
        { name: 'Review Queue', href: '/reviewer', icon: Search },
        { name: 'Decisions', href: '/hiring-decisions', icon: CheckCircle },
        ...(recruiterRole === 'admin' ? [
            { name: 'System Learning', href: '/learning', icon: BarChart2 },
            { name: 'Admin', href: '/admin', icon: Settings },
        ] : []),
    ];

    const handleLogout = () => {
        localStorage.removeItem('authToken');
        localStorage.removeItem('recruiterId');
        localStorage.removeItem('recruiterName');
        localStorage.removeItem('recruiterRole');
        window.location.href = '/login';
    };

    // Clean layout for candidates
    if (isPublicRoute) {
        return <>{children}</>;
    }

    return (
        <div className="min-h-screen bg-light-50 flex flex-col font-sans text-text-primary">
            {/* Navbar */}
            <nav className="bg-white/80 border-b border-gray-200 sticky top-0 z-50 shadow-sm backdrop-blur">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between h-16">
                        <div className="flex">
                            {/* Logo */}
                            <div className="flex-shrink-0 flex items-center">
                                <Link to="/" className="flex items-center gap-2">
                                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center text-white font-bold text-lg shadow-sm">
                                        S
                                    </div>
                                    <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-accent tracking-tight">
                                        SignalStack
                                    </span>
                                </Link>
                            </div>

                            {/* Desktop Nav */}
                            <div className="hidden sm:ml-8 sm:flex sm:space-x-1">
                                {navigation.map((item) => {
                                    const isActive = location.pathname === item.href ||
                                        (item.href !== '/' && location.pathname.startsWith(item.href));
                                    const Icon = item.icon;

                                    return (
                                        <Link
                                            key={item.name}
                                            to={item.href}
                                            aria-current={isActive ? 'page' : undefined}
                                            className={`inline-flex items-center px-4 pt-1 border-b-2 text-sm font-medium transition-colors duration-200 gap-2 ${isActive
                                                ? 'border-primary text-primary'
                                                : 'border-transparent text-text-secondary hover:border-gray-300 hover:text-text-primary'
                                                }`}
                                        >
                                            <Icon className={`w-4 h-4 ${isActive ? 'text-primary' : 'text-gray-400'}`} />
                                            {item.name}
                                        </Link>
                                    );
                                })}
                            </div>
                        </div>

                        {/* Mobile menu button */}
                        <div className="hidden sm:flex items-center gap-3">
                            <div className="text-right">
                                <div className="text-sm font-medium text-gray-900 max-w-[180px] truncate">{recruiterName}</div>
                                <div className="text-xs text-gray-500 capitalize">{recruiterRole}</div>
                            </div>
                            <button
                                onClick={handleLogout}
                                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium text-gray-600 hover:text-red-600 hover:bg-red-50"
                            >
                                <LogOut className="w-4 h-4" />
                                Logout
                            </button>
                        </div>

                        <div className="-mr-2 flex items-center sm:hidden">
                            <button
                                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                                aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
                                aria-expanded={mobileMenuOpen}
                                className="inline-flex items-center justify-center p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-primary-soft focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary"
                            >
                                {mobileMenuOpen ? (
                                    <X className="block h-6 w-6" aria-hidden="true" />
                                ) : (
                                    <Menu className="block h-6 w-6" aria-hidden="true" />
                                )}
                            </button>
                        </div>
                    </div>
                </div>

                {/* Mobile menu */}
                <div className={`sm:hidden ${mobileMenuOpen ? 'block' : 'hidden'} border-b border-gray-200 bg-white/90 backdrop-blur`}>
                    <div className="pt-2 pb-3 space-y-1">
                        {navigation.map((item) => {
                            const isActive = location.pathname === item.href ||
                                (item.href !== '/' && location.pathname.startsWith(item.href));
                            const Icon = item.icon;

                            return (
                                <Link
                                    key={item.name}
                                    to={item.href}
                                    onClick={() => setMobileMenuOpen(false)}
                                    className={`block pl-3 pr-4 py-2 border-l-4 text-base font-medium flex items-center gap-3 ${isActive
                                        ? 'bg-primary-soft border-primary text-primary'
                                        : 'border-transparent text-text-secondary hover:bg-gray-50 hover:border-gray-300 hover:text-text-primary'
                                        }`}
                                >
                                    <Icon className={`w-5 h-5 ${isActive ? 'text-primary' : 'text-gray-400'}`} />
                                    {item.name}
                                </Link>
                            );
                        })}
                        <button
                            onClick={handleLogout}
                            className="w-full block pl-3 pr-4 py-2 border-l-4 border-transparent text-base font-medium text-red-600 hover:bg-red-50 flex items-center gap-3"
                        >
                            <LogOut className="w-5 h-5" />
                            Logout
                        </button>
                    </div>
                </div>
            </nav>

            {/* Backend Wakeup Banner */}
            <ServerWakeupBanner />

            {/* Main Content */}
            <main className="flex-1 max-w-7xl w-full mx-auto py-8 px-4 sm:px-6 lg:px-8">
                {children}
            </main>

            {/* Footer */}
            <footer className="bg-white/80 border-t border-gray-200 mt-auto">
                <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
                    <p className="text-center text-sm text-text-muted">
                        &copy; {new Date().getFullYear()} SignalStack. All rights reserved.
                    </p>
                </div>
            </footer>
        </div>
    );
}
