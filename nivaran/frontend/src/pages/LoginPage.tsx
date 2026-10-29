import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Network, Eye, EyeOff, Lock, User, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';

const DEMO_ACCOUNTS = [
  { username: 'admin',        password: 'Admin@123',    role: 'System Administrator',      borderColor: 'border-l-4 border-amber-500' },
  { username: 'reviewer1',    password: 'Review@123',   role: 'Supervisory Reviewer',       borderColor: 'border-l-4 border-purple-500' },
  { username: 'officer_acad', password: 'Officer@123',  role: 'Bureau Officer (Academic)',   borderColor: 'border-l-4 border-sky-500' },
  { username: 'officer_fin',  password: 'Officer@123',  role: 'Bureau Officer (Finance)',    borderColor: 'border-l-4 border-sky-500' },
  { username: 'readonly1',    password: 'Readonly@123', role: 'Read-Only Official',          borderColor: 'border-l-4 border-slate-500' },
];

// Floating node configuration
const FLOAT_NODES = [
  { size: 8, top: '12%', left: '8%', color: 'bg-blue-300/20' },
  { size: 16, top: '25%', left: '75%', color: 'bg-blue-200/15' },
  { size: 10, top: '55%', left: '15%', color: 'bg-blue-300/15' },
];

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) { setError('Please enter username and password.'); return; }
    setLoading(true);
    setError('');
    try {
      await login(username, password);
      toast.success('Welcome to AICTE OneView');
      navigate('/');
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const quickLogin = (u: string, p: string) => {
    setUsername(u);
    setPassword(p);
  };

  return (
    <div className="min-h-screen bg-navy-950 flex">
      {/* Left panel */}
      <div className="hidden lg:flex lg:w-1/2 flex-col items-center justify-center p-12 relative overflow-hidden">
        {/* Subtle, static visual markers */}
        {FLOAT_NODES.map((node, i) => (
          <div
            key={i}
            className={`absolute rounded-full ${node.color} pointer-events-none`}
            style={{
              width: node.size,
              height: node.size,
              top: node.top,
              left: node.left,
            }}
          />
        ))}

        <div className="relative z-10 max-w-md text-center">
          <div className="w-14 h-14 mx-auto mb-6 rounded-xl bg-blue-700 flex items-center justify-center">
            <Network size={27} className="text-white" aria-hidden="true" />
          </div>

          <h1 className="text-4xl font-bold text-white mb-3">AICTE OneView</h1>
          <p className="text-lg text-blue-100 mb-2">Complaint workflow prototype</p>
          <p className="text-sm text-slate-400 leading-relaxed mb-8">
            A demonstration interface for complaint intake, review, priority monitoring, and reporting.
          </p>

          <div className="grid grid-cols-2 gap-4 text-left mb-8">
            {[
              { label: 'Cross-Bureau Matching', desc: 'Explainable overlap detection' },
              { label: 'Priority Engine', desc: 'Transparent urgency scoring' },
              { label: 'Evidence Review', desc: 'Completeness assessment' },
              { label: 'Audit Trail', desc: 'Full action history' },
            ].map((f) => (
              <div key={f.label} className="bg-white/5 rounded-xl p-3 border border-white/10">
                <p className="text-xs font-semibold text-indigo-300">{f.label}</p>
                <p className="text-xs text-slate-500 mt-0.5">{f.desc}</p>
              </div>
            ))}
          </div>

          <div className="px-4 py-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-left">
            <p className="text-xs font-semibold text-amber-400">Demonstration Notice</p>
            <p className="text-xs text-amber-600 mt-1">
              All complaint records are Synthetic Demonstration Data.
              No real AICTE complaint data is used.
            </p>
          </div>

          <p className="text-[10px] text-slate-600 mt-6">Powered by AICTE PS-26264</p>
        </div>
      </div>

      {/* Right panel — Login form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md animate-fade-in-up">
          {/* Mobile brand */}
          <div className="flex items-center gap-3 mb-8 lg:hidden">
            <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center">
              <Network size={20} className="text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-slate-100">AICTE OneView</h1>
              <p className="text-xs text-slate-500">Complaint Intelligence Platform</p>
            </div>
          </div>

          {/* Glass card wrapping the form */}
          <div className="glass rounded-2xl p-8">
              <h2 className="text-2xl font-bold text-navy-900 mb-1">Sign in</h2>
            <p className="text-sm text-slate-500 mb-8">Access your dashboard and case management tools.</p>

            {error && (
              <div className="flex items-center gap-2 p-3 mb-4 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-sm">
                <AlertCircle size={16} className="shrink-0" />
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="label">Username</label>
                <div className="relative">
                  <User size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input
                    id="username"
                    className="input pl-9"
                    placeholder="Enter your username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    autoComplete="username"
                  />
                </div>
              </div>

              <div>
                <label className="label">Password</label>
                <div className="relative">
                  <Lock size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input
                    id="password"
                    type={showPass ? 'text' : 'password'}
                    className="input pl-9 pr-10"
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPass(!showPass)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                  >
                    {showPass ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
              </div>

              <button
                id="login-btn"
                type="submit"
                disabled={loading}
                className="btn-primary w-full py-2.5 justify-center"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Signing in…
                  </span>
                ) : 'Sign in'}
              </button>
            </form>

            {/* Demo accounts */}
            <div className="mt-8">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Demo Accounts</p>
              <div className="space-y-2">
                {DEMO_ACCOUNTS.map((acc) => (
                  <button
                    key={acc.username}
                    onClick={() => quickLogin(acc.username, acc.password)}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-lg bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 hover:border-slate-600 transition-all text-left ${acc.borderColor}`}
                  >
                    <div>
                      <p className="text-xs font-medium text-slate-200">{acc.role}</p>
                      <p className="text-[11px] text-slate-500">Select to fill sign-in fields</p>
                    </div>
                    <span className="text-[10px] text-indigo-400 font-medium">Use →</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
