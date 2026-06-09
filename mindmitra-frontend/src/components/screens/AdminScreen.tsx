import React, { useCallback, useEffect, useState } from 'react';
import {
  AlertCircle,
  BookOpen,
  Loader2,
  LogOut,
  RefreshCw,
  ShieldAlert,
  Users,
} from 'lucide-react';

import { loginUser } from '../../api/auth';
import {
  fetchAdminStats,
  fetchRecentJournals,
  type JournalEntry,
  type PlatformStats,
} from '../../api/admin';

// ─── Constants ───────────────────────────────────────────────────────────────

const STORAGE_KEY = 'token';

// ─── Helpers ─────────────────────────────────────────────────────────────────

/**
 * Decode the JWT payload without verifying the signature.
 * The backend already verified the token; here we only need the `role` claim
 * to decide what to show in the UI.
 */
function decodeJwtRole(token: string): string | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.role ?? null;
  } catch {
    return null;
  }
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return '—';
  }
}

function moodLabel(mood: number | null): string {
  if (mood === null || mood === undefined) return '—';
  // Support both 1-5 integer scale (journal model) and 0-1 float scale (analysis model)
  const normalised = mood > 1 ? mood / 5 : mood;
  if (normalised >= 0.8) return '😊 Great';
  if (normalised >= 0.6) return '🙂 Good';
  if (normalised >= 0.4) return '😐 Okay';
  if (normalised >= 0.2) return '😕 Low';
  return '😢 Very Low';
}

// ─── Login Form ───────────────────────────────────────────────────────────────

interface LoginFormProps {
  onLogin: (token: string) => void;
}

const LoginForm: React.FC<LoginFormProps> = ({ onLogin }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await loginUser(email, password);
      onLogin(res.data.access_token);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 flex items-center justify-center p-4">
      <div
        className="w-full max-w-sm rounded-2xl p-8 shadow-2xl"
        style={{ background: 'rgba(255,255,255,0.07)', backdropFilter: 'blur(16px)', border: '1px solid rgba(255,255,255,0.12)' }}
      >
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 bg-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg shadow-indigo-900/50">
            <ShieldAlert className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Admin Portal</h1>
          <p className="text-indigo-300 text-sm mt-1">MindMitra Administration</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4" id="admin-login-form">
          <div>
            <label className="block text-indigo-200 text-sm font-medium mb-1.5">Email</label>
            <input
              id="admin-email"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="admin@example.com"
              required
              autoComplete="email"
              className="w-full px-4 py-3 rounded-xl text-white placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-indigo-400 transition"
              style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.15)' }}
            />
          </div>

          <div>
            <label className="block text-indigo-200 text-sm font-medium mb-1.5">Password</label>
            <input
              id="admin-password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              autoComplete="current-password"
              className="w-full px-4 py-3 rounded-xl text-white placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-indigo-400 transition"
              style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.15)' }}
            />
          </div>

          {error && (
            <div className="flex items-start gap-2.5 rounded-xl px-4 py-3" style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.3)' }}>
              <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
              <span className="text-red-300 text-sm">{error}</span>
            </div>
          )}

          <button
            id="admin-login-btn"
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-all duration-200 flex items-center justify-center gap-2 shadow-lg shadow-indigo-900/40 mt-2"
          >
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
};

// ─── Stat Card ────────────────────────────────────────────────────────────────

interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: number | string;
  iconBg: string;
}

const StatCard: React.FC<StatCardProps> = ({ icon, label, value, iconBg }) => (
  <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 flex items-center gap-4">
    <div className={`w-12 h-12 ${iconBg} rounded-xl flex items-center justify-center shrink-0`}>
      {icon}
    </div>
    <div>
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">{label}</p>
      <p className="text-3xl font-bold text-gray-800 mt-0.5">{value}</p>
    </div>
  </div>
);

const SkeletonCard: React.FC = () => (
  <div className="bg-white rounded-2xl border border-gray-100 p-6 flex items-center gap-4 animate-pulse">
    <div className="w-12 h-12 bg-gray-200 rounded-xl shrink-0" />
    <div className="space-y-2 flex-1">
      <div className="h-3 w-20 bg-gray-200 rounded" />
      <div className="h-7 w-14 bg-gray-200 rounded" />
    </div>
  </div>
);

// ─── Dashboard ────────────────────────────────────────────────────────────────

interface DashboardProps {
  token: string;
  onLogout: () => void;
}

const Dashboard: React.FC<DashboardProps> = ({ token, onLogout }) => {
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [journals, setJournals] = useState<JournalEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [statsRes, journalsRes] = await Promise.all([
        fetchAdminStats(token),
        fetchRecentJournals(token, 10),
      ]);
      setStats(statsRes.data);
      setJournals(journalsRes.data);
      setLastRefreshed(new Date());
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 401) {
        setError('Your session has expired. Please log out and sign in again.');
      } else if (status === 403) {
        setError('Access denied — your account does not have admin privileges.');
      } else {
        setError('Could not load data. Ensure the backend is running and reachable.');
      }
    } finally {
      setLoading(false);
    }
  }, [token]);

  // Load on mount
  useEffect(() => {
    loadData();
  }, [loadData]);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ── Header ── */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-5 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-indigo-600 rounded-xl flex items-center justify-center shadow-sm shadow-indigo-200">
              <ShieldAlert className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-base font-bold text-gray-900 leading-tight">MindMitra Admin</h1>
              {lastRefreshed && (
                <p className="text-xs text-gray-400 leading-tight">
                  Updated {lastRefreshed.toLocaleTimeString()}
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              id="admin-refresh-btn"
              onClick={loadData}
              disabled={loading}
              className="flex items-center gap-1.5 px-3.5 py-2 bg-indigo-50 hover:bg-indigo-100 active:bg-indigo-200 text-indigo-700 font-medium rounded-xl text-sm transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button
              id="admin-logout-btn"
              onClick={onLogout}
              className="flex items-center gap-1.5 px-3.5 py-2 bg-gray-100 hover:bg-red-50 hover:text-red-600 text-gray-600 font-medium rounded-xl text-sm transition-all duration-150"
            >
              <LogOut className="w-3.5 h-3.5" />
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* ── Main content ── */}
      <main className="max-w-5xl mx-auto px-5 py-7 space-y-8">

        {/* Error banner */}
        {error && (
          <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-xl px-5 py-3.5">
            <AlertCircle className="w-5 h-5 text-red-500 shrink-0" />
            <p className="text-red-700 text-sm">{error}</p>
          </div>
        )}

        {/* ── Platform Overview ── */}
        <section>
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">
            Platform Overview
          </h2>

          {loading && !stats ? (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <StatCard
                icon={<Users className="w-6 h-6 text-white" />}
                label="Total Users"
                value={stats?.total_users ?? '—'}
                iconBg="bg-blue-500"
              />
              <StatCard
                icon={<Users className="w-6 h-6 text-white" />}
                label="Active Users"
                value={stats?.active_users ?? '—'}
                iconBg="bg-emerald-500"
              />
              <StatCard
                icon={<ShieldAlert className="w-6 h-6 text-white" />}
                label="SOS Alerts"
                value={stats?.sos_count ?? '—'}
                iconBg="bg-rose-500"
              />
            </div>
          )}
        </section>

        {/* ── Recent Journal Entries ── */}
        <section>
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">
            Recent Journal Entries <span className="normal-case font-normal text-gray-400">(anonymised)</span>
          </h2>

          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
            {loading && journals.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 gap-3">
                <Loader2 className="w-7 h-7 text-indigo-400 animate-spin" />
                <p className="text-sm text-gray-400">Loading entries…</p>
              </div>
            ) : journals.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 gap-3">
                <BookOpen className="w-10 h-10 text-gray-200" />
                <p className="text-sm text-gray-400">No journal entries found.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100 bg-gray-50/60">
                      <th className="text-left px-5 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Date</th>
                      <th className="text-left px-5 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Mood</th>
                      <th className="text-left px-5 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Excerpt</th>
                      <th className="text-left px-5 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Anon. User</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {journals.map((entry, i) => (
                      <tr
                        key={i}
                        className="hover:bg-gray-50/70 transition-colors duration-100"
                      >
                        <td className="px-5 py-3.5 text-gray-500 whitespace-nowrap text-xs">
                          {formatDate(entry.created_at)}
                        </td>
                        <td className="px-5 py-3.5 whitespace-nowrap">
                          <span className="text-sm">{moodLabel(entry.mood)}</span>
                        </td>
                        <td className="px-5 py-3.5 text-gray-700 max-w-xs">
                          {entry.text_excerpt ? (
                            <span className="line-clamp-2 text-sm">{entry.text_excerpt}</span>
                          ) : (
                            <span className="italic text-gray-400 text-sm">No content</span>
                          )}
                        </td>
                        <td className="px-5 py-3.5">
                          <code className="bg-gray-100 text-gray-500 text-xs px-2 py-1 rounded-lg font-mono tracking-tight">
                            {entry.anon_user_id}
                          </code>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
};

// ─── Access Denied ────────────────────────────────────────────────────────────

interface AccessDeniedProps {
  onReset: () => void;
}

const AccessDenied: React.FC<AccessDeniedProps> = ({ onReset }) => (
  <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 flex items-center justify-center p-4">
    <div
      className="w-full max-w-sm rounded-2xl p-8 text-center shadow-2xl"
      style={{ background: 'rgba(255,255,255,0.07)', backdropFilter: 'blur(16px)', border: '1px solid rgba(255,255,255,0.12)' }}
    >
      <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
      <h2 className="text-white text-xl font-bold mb-2">Access Denied</h2>
      <p className="text-indigo-200 text-sm mb-6 leading-relaxed">
        This account does not have admin privileges.
        Only users with <code className="bg-white/10 px-1.5 py-0.5 rounded text-xs font-mono">role=admin</code> can access this panel.
      </p>
      <button
        id="admin-try-again-btn"
        onClick={onReset}
        className="px-6 py-2.5 text-sm font-medium text-white rounded-xl transition-all duration-200 hover:bg-white/20"
        style={{ background: 'rgba(255,255,255,0.1)' }}
      >
        Try a different account
      </button>
    </div>
  </div>
);

// ─── Root Component ───────────────────────────────────────────────────────────

/**
 * AdminScreen — self-contained admin panel at /admin.
 *
 * Auth flow:
 *  1. Check localStorage for a stored token (mm_admin_token).
 *  2. If absent → show LoginForm which calls the existing /api/v1/auth/login endpoint.
 *  3. Decode the JWT payload to read the `role` claim (no signature verification needed
 *     client-side; the backend enforces it on every API call anyway).
 *  4. role !== 'admin' → show AccessDenied.
 *  5. role === 'admin' → show Dashboard.
 */
const AdminScreen: React.FC = () => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY));
  const [accessDenied, setAccessDenied] = useState(false);

  // Validate any token that was loaded from localStorage on mount
  useEffect(() => {
    if (token && decodeJwtRole(token) !== 'admin') {
      localStorage.removeItem(STORAGE_KEY);
      setToken(null);
      setAccessDenied(true);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleLogin = (newToken: string) => {
    const role = decodeJwtRole(newToken);
    if (role !== 'admin') {
      setAccessDenied(true);
      return;
    }
    localStorage.setItem(STORAGE_KEY, newToken);
    setToken(newToken);
    setAccessDenied(false);
  };

  const handleLogout = () => {
    localStorage.removeItem(STORAGE_KEY);
    setToken(null);
    setAccessDenied(false);
  };

  if (accessDenied) return <AccessDenied onReset={handleLogout} />;
  if (!token) return <LoginForm onLogin={handleLogin} />;
  return <Dashboard token={token} onLogout={handleLogout} />;
};

export default AdminScreen;
