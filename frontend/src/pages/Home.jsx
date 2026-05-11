import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Target, Shield, Zap } from 'lucide-react';

export default function Home() {
    return (
        <div className="space-y-12">
            <div className="text-center space-y-4 py-16">
                <h1 className="text-5xl font-extrabold tracking-tight text-gray-900 sm:text-6xl">
                    Hire with <span className="text-primary">Signal</span>, not Noise.
                </h1>
                <p className="max-w-2xl mx-auto text-xl text-gray-500">
                    AI-native evaluation that extracts deep signals from candidate code artifacts.
                </p>
                <div className="mt-8 flex justify-center gap-4">
                    <Link to="/create-outcome" className="btn btn-primary text-lg px-8 py-3">
                        Create Outcome
                        <ArrowRight className="ml-2 w-5 h-5" />
                    </Link>
                    <Link to="/reviewer" className="btn btn-secondary text-lg px-8 py-3">
                        Reviewer Queue
                    </Link>
                </div>
            </div>

            <div className="grid grid-cols-1 gap-8 sm:grid-cols-3">
                <div className="p-6 bg-white rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-all duration-300">
                    <Target className="w-10 h-10 text-primary mb-4" />
                    <h3 className="text-lg font-semibold text-gray-900">Outcome Defined</h3>
                    <p className="mt-2 text-gray-500">Define success criteria and bias weights upfront. No vague job descriptions.</p>
                </div>
                <div className="p-6 bg-white rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-all duration-300">
                    <Shield className="w-10 h-10 text-primary mb-4" />
                    <h3 className="text-lg font-semibold text-gray-900">Proof, not Claims</h3>
                    <p className="mt-2 text-gray-500">Candidates submit artifacts (GitHub repos). We extract deterministic signals.</p>
                </div>
                <div className="p-6 bg-white rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-all duration-300">
                    <Zap className="w-10 h-10 text-primary mb-4" />
                    <h3 className="text-lg font-semibold text-gray-900">AI Evaluation</h3>
                    <p className="mt-2 text-gray-500">LLM-assisted scoring with evidence-backed allocation and risk flags.</p>
                </div>
            </div>
        </div>
    );
}
