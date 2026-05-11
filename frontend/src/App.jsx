import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import JobDashboard from './pages/JobDashboard';
import JobCreate from './pages/JobCreate';
import JobCreateWizard from './pages/JobCreateWizard';
import JobDetail from './pages/JobDetail';
import Dashboard from './pages/Dashboard'; // Legacy
import OutcomeCreate from './pages/OutcomeCreate';
import OutcomeCreateMultiple from './pages/OutcomeCreateMultiple';
import ProofSubmit from './pages/ProofSubmit';
import EvaluationView from './pages/EvaluationView';
import ReviewerQueue from './pages/ReviewerQueue';
import OutcomeDashboard from './pages/OutcomeDashboard';
import FeedbackView from './pages/FeedbackView';
import HiringDecisions from './pages/HiringDecisions';
import AdminAudit from './pages/AdminAudit';
import Admin from './pages/Admin';
import CandidateApply from './pages/CandidateApply';

import Layout from './components/Layout';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          {/* Job-Centric Routes */}
          <Route path="/" element={<JobDashboard />} />
          <Route path="/create-job" element={<JobCreateWizard />} />
          <Route path="/jobs/:jobId" element={<JobDetail />} />
          <Route path="/jobs/:jobId/add-outcome" element={<OutcomeCreate />} />
          <Route path="/jobs/:jobId/outcomes/new" element={<OutcomeCreateMultiple />} />

          {/* New unified flow - creates job and outcomes together */}
          <Route path="/outcomes/create-with-job" element={<OutcomeCreateMultiple />} />

          {/* Legacy / Shared Routes */}
          <Route path="/outcomes" element={<Dashboard />} />
          <Route path="/create-outcome" element={<OutcomeCreate />} />
          <Route path="/dashboard/:outcomeId" element={<OutcomeDashboard />} />
          <Route path="/submit-proof/:outcomeId" element={<ProofSubmit />} />
          <Route path="/evaluation/:jobId" element={<EvaluationView />} />
          <Route path="/reviewer" element={<ReviewerQueue />} />
          <Route path="/hiring-decisions" element={<HiringDecisions />} />
          <Route path="/learning" element={<FeedbackView />} />
          <Route path="/admin" element={<Admin />} />
          <Route path="/admin/audit" element={<AdminAudit />} />
          <Route path="/apply/:token" element={<CandidateApply />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
