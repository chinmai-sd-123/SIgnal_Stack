import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import JobDashboard from './pages/JobDashboard';
import JobCreate from './pages/JobCreate';
import JobCreateWizard from './pages/JobCreateWizard';
import JobDetail from './pages/JobDetail';
import Dashboard from './pages/Dashboard'; // Legacy
import OutcomeCreate from './pages/OutcomeCreate';
import OutcomeCreateMultiple from './pages/OutcomeCreateMultiple';
import OutcomeEdit from './pages/OutcomeEdit';
import ProofSubmit from './pages/ProofSubmit';
import EvaluationView from './pages/EvaluationView';
import ReviewerQueue from './pages/ReviewerQueue';
import OutcomeDashboard from './pages/OutcomeDashboard';
import FeedbackView from './pages/FeedbackView';
import HiringDecisions from './pages/HiringDecisions';
import AdminAudit from './pages/AdminAudit';
import Admin from './pages/Admin';
import CandidateApply from './pages/CandidateApply';
import RecruiterLogin from './pages/RecruiterLogin';
import RecruiterSignup from './pages/RecruiterSignup';

import Layout from './components/Layout';

function ProtectedRoute({ children, adminOnly = false }) {
  const location = useLocation();
  const token = localStorage.getItem('authToken');
  const role = localStorage.getItem('recruiterRole') || 'recruiter';

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (adminOnly && role !== 'admin') {
    return <Navigate to="/" replace />;
  }
  return children;
}

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/login" element={<RecruiterLogin />} />
          <Route path="/signup" element={<RecruiterSignup />} />

          {/* Job-Centric Routes */}
          <Route path="/" element={<ProtectedRoute><JobDashboard /></ProtectedRoute>} />
          <Route path="/create-job" element={<ProtectedRoute><JobCreateWizard /></ProtectedRoute>} />
          <Route path="/jobs/:jobId" element={<ProtectedRoute><JobDetail /></ProtectedRoute>} />
          <Route path="/jobs/:jobId/add-outcome" element={<ProtectedRoute><OutcomeCreate /></ProtectedRoute>} />
          <Route path="/jobs/:jobId/outcomes/new" element={<ProtectedRoute><OutcomeCreateMultiple /></ProtectedRoute>} />
          <Route path="/outcomes/:outcomeId/edit" element={<ProtectedRoute><OutcomeEdit /></ProtectedRoute>} />

          {/* New unified flow - creates job and outcomes together */}
          <Route path="/outcomes/create-with-job" element={<ProtectedRoute><OutcomeCreateMultiple /></ProtectedRoute>} />

          {/* Legacy / Shared Routes */}
          <Route path="/outcomes" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/create-outcome" element={<ProtectedRoute><OutcomeCreate /></ProtectedRoute>} />
          <Route path="/dashboard/:outcomeId" element={<ProtectedRoute><OutcomeDashboard /></ProtectedRoute>} />
          <Route path="/submit-proof/:outcomeId" element={<ProtectedRoute><ProofSubmit /></ProtectedRoute>} />
          <Route path="/evaluation/:jobId" element={<ProtectedRoute><EvaluationView /></ProtectedRoute>} />
          <Route path="/reviewer" element={<ProtectedRoute><ReviewerQueue /></ProtectedRoute>} />
          <Route path="/hiring-decisions" element={<ProtectedRoute><HiringDecisions /></ProtectedRoute>} />
          <Route path="/learning" element={<ProtectedRoute adminOnly><FeedbackView /></ProtectedRoute>} />
          <Route path="/admin" element={<ProtectedRoute adminOnly><Admin /></ProtectedRoute>} />
          <Route path="/admin/audit" element={<ProtectedRoute adminOnly><AdminAudit /></ProtectedRoute>} />
          <Route path="/apply/:token" element={<CandidateApply />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
