import { type ReactElement } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';

// Layout
import Layout from './components/Layout';

// Pages
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ComplaintsPage from './pages/ComplaintsPage';
import ComplaintDetailPage from './pages/ComplaintDetailPage';
import InstitutionsPage from './pages/InstitutionsPage';
import PriorityQueuePage from './pages/PriorityQueuePage';
import OverlapsPage from './pages/OverlapsPage';
import EvidencePage from './pages/EvidencePage';
import DeadlinesPage from './pages/DeadlinesPage';
import ReportsPage from './pages/ReportsPage';
import UsersPage from './pages/UsersPage';
import AuditPage from './pages/AuditPage';
import DataSourcesPage from './pages/DataSourcesPage';
import RelationshipGraphPage from './pages/RelationshipGraphPage';

function ProtectedRoute({ children }: { children: ReactElement }) {
  const { user, loading } = useAuth();
  if (loading) return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="w-9 h-9 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm text-slate-500">Initialising…</p>
      </div>
    </div>
  );
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function AdminRoute({ children }: { children: ReactElement }) {
  const { user, isAdmin } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (!isAdmin) return <Navigate to="/" replace />;
  return children;
}

function AppRoutes() {
  const { user } = useAuth();
  return (
    <Routes>
      <Route
        path="/login"
        element={user ? <Navigate to="/" replace /> : <LoginPage />}
      />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="complaints" element={<ComplaintsPage />} />
        <Route path="complaints/:id" element={<ComplaintDetailPage />} />
        <Route path="institutions" element={<InstitutionsPage />} />
        <Route path="priority-queue" element={<PriorityQueuePage />} />
        <Route path="overlaps" element={<OverlapsPage />} />
        <Route path="evidence" element={<EvidencePage />} />
        <Route path="deadlines" element={<DeadlinesPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="graph" element={<RelationshipGraphPage />} />

        {/* Admin-only */}
        <Route path="users" element={<AdminRoute><UsersPage /></AdminRoute>} />
        <Route path="audit" element={<AdminRoute><AuditPage /></AdminRoute>} />
        <Route path="data" element={<AdminRoute><DataSourcesPage /></AdminRoute>} />
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}
