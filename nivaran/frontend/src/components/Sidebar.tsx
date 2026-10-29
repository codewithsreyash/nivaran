import { NavLink } from 'react-router-dom';
import type { ComponentType } from 'react';
import { useAuth } from '../contexts/AuthContext';
import {
  LayoutDashboard, Building2, FileText, ListOrdered, GitMerge, Shield, Network,
  BarChart3, Users, ClipboardList, Database, LogOut, X, AlertTriangle,
} from 'lucide-react';

const navItems = [
  { path: '/', label: 'Executive Dashboard', icon: LayoutDashboard },
  { path: '/institutions', label: 'Institution Registry', icon: Building2 },
  { path: '/complaints', label: 'Complaint Management', icon: FileText },
  { path: '/priority-queue', label: 'Priority Queue', icon: ListOrdered },
  { path: '/overlaps', label: 'Overlap Detection', icon: GitMerge },
  { path: '/evidence', label: 'Evidence Review', icon: Shield },
  { path: '/deadlines', label: 'Deadlines & Alerts', icon: AlertTriangle },
  { path: '/graph', label: 'Relationship Graph', icon: Network },
  { path: '/reports', label: 'Reports & Analytics', icon: BarChart3 },
];

const adminItems = [
  { path: '/users', label: 'User Management', icon: Users },
  { path: '/audit', label: 'Audit History', icon: ClipboardList },
  { path: '/data', label: 'Data Sources', icon: Database },
];

type NavItemProps = {
  path: string;
  label: string;
  icon: ComponentType<{ size?: number; className?: string }>;
  onNavigate?: () => void;
};

function NavItem({ path, label, icon: Icon, onNavigate }: NavItemProps) {
  return (
    <NavLink to={path} end={path === '/'} onClick={onNavigate}
      className={({ isActive }) => isActive ? 'nav-item-active' : 'nav-item'}>
      <Icon size={18} aria-hidden="true" />
      <span>{label}</span>
    </NavLink>
  );
}

interface SidebarProps {
  isMobile: boolean;
  mobileOpen: boolean;
  onClose: () => void;
}

export default function Sidebar({ isMobile, mobileOpen, onClose }: SidebarProps) {
  const { user, logout, isAdmin } = useAuth();
  const roleLabel: Record<string, string> = {
    admin: 'System Administrator',
    bureau_officer: 'Bureau Officer',
    supervisory_reviewer: 'Supervisory Reviewer',
    read_only: 'Read-Only Official',
  };

  return (
    <>
      {isMobile && mobileOpen && <button className="nav-backdrop" onClick={onClose} aria-label="Close navigation menu" />}
      <aside id="primary-navigation" aria-label="Primary navigation"
        aria-hidden={isMobile && !mobileOpen}
        className={`app-sidebar ${isMobile ? 'app-sidebar-mobile' : ''} ${mobileOpen ? 'is-open' : ''}`}>
        <div className="sidebar-brand">
          <div className="brand-mark" aria-hidden="true"><Network size={21} /></div>
          <div className="min-w-0">
            <h1>AICTE OneView</h1>
            <p>Complaint Intelligence Platform</p>
          </div>
          {isMobile && <button className="icon-button sidebar-close" onClick={onClose} aria-label="Close navigation menu"><X size={20} /></button>}
        </div>

        <nav className="sidebar-nav">
          <p className="nav-section-label">Workspace</p>
          {navItems.map((item) => <NavItem key={item.path} {...item} onNavigate={onClose} />)}
          {isAdmin && <>
            <p className="nav-section-label nav-section-spaced">Administration</p>
            {adminItems.map((item) => <NavItem key={item.path} {...item} onNavigate={onClose} />)}
          </>}
        </nav>

        <div className="sidebar-note">
          <p>Demonstration environment</p>
          <span>Complaint records are synthetic.</span>
        </div>

        <div className="sidebar-account">
          <div className="account-avatar" aria-hidden="true">{user?.full_name?.charAt(0) ?? 'U'}</div>
          <div className="account-details">
            <p>{user?.full_name}</p>
            <span>{roleLabel[user?.role ?? ''] ?? user?.role}</span>
          </div>
          <button onClick={logout} className="icon-button logout-button" aria-label="Log out" title="Log out">
            <LogOut size={17} />
          </button>
        </div>
      </aside>
    </>
  );
}
