import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Eye, EyeOff, Lock, ArrowLeft } from 'lucide-react';
import { resetPassword, validateResetToken } from '../../api/auth';

const MindMitraLogo: React.FC = () => (
  <div
    className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#4a90d9] shadow-lg shadow-blue-500/10"
    style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      backgroundColor: '#4a90d9',
      borderRadius: '16px',
      height: '64px',
      width: '64px',
      margin: '0 auto 16px',
    }}
  >
    <svg viewBox="0 0 32 24" className="h-8 w-10" aria-hidden="true" style={{ height: '32px', width: '40px' }}>
      <path
        d="M4 14c4-6 8-6 12 0s8 6 12 0"
        fill="none"
        stroke="white"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      <path
        d="M4 10c4-6 8-6 12 0s8 6 12 0"
        fill="none"
        stroke="white"
        strokeWidth="2.5"
        strokeLinecap="round"
        opacity="0.85"
      />
    </svg>
  </div>
);

const glassInputStyle: React.CSSProperties = {
  border: 'none',
  outline: 'none',
  boxShadow: 'none',
  backgroundColor: 'transparent',
  flex: 1,
  minWidth: 0,
  padding: '12px 0',
  color: '#000000',
  fontSize: '14px',
  fontFamily: 'inherit',
  width: '100%',
  boxSizing: 'border-box',
};

const ResetPasswordScreen: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') ?? '';

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(true);
  const [tokenValid, setTokenValid] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    document.documentElement.style.backgroundColor = '#f8fafc';
    document.body.style.backgroundColor = '#f8fafc';
    return () => {
      document.documentElement.style.backgroundColor = '';
      document.body.style.backgroundColor = '';
    };
  }, []);

  useEffect(() => {
    if (!token) {
      setValidating(false);
      setTokenValid(false);
      return;
    }

    validateResetToken(token)
      .then(() => setTokenValid(true))
      .catch(() => setTokenValid(false))
      .finally(() => setValidating(false));
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) return;

    setLoading(true);
    setError('');
    try {
      await resetPassword(token, password);
      setSuccess(true);
      setTimeout(() => navigate('/'), 3000);
    } catch {
      setError('Failed to reset password. The link may have expired.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="flex min-h-screen items-center justify-center px-4 py-12"
      style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '48px 16px' }}
    >
      <div
        className="relative z-10 w-full max-w-[400px] rounded-[32px] bg-white px-8 py-10 shadow-[0_15px_50px_rgba(0,0,0,0.05)] border border-slate-100"
        style={{
          maxWidth: '400px',
          width: '100%',
          borderRadius: '32px',
          backgroundColor: '#ffffff',
          padding: '40px 32px',
          border: '1px solid #f1f5f9',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.05), 0 10px 10px -5px rgba(0, 0, 0, 0.02)',
        }}
      >
        <div className="mb-8 text-center" style={{ textAlign: 'center', marginBottom: '32px' }}>
          <MindMitraLogo />
          <h1 className="text-3xl font-extrabold tracking-tight text-[#134e4a]" style={{ color: '#134e4a', fontSize: '30px', fontWeight: 800, margin: 0 }}>
            Reset Password
          </h1>
          <p className="mt-2 text-sm text-[#4e878c] font-medium" style={{ color: '#4e878c', fontSize: '14px', marginTop: '8px' }}>
            Choose a new password for your account.
          </p>
        </div>

        {validating ? (
          <p className="text-center text-sm text-slate-500" style={{ textAlign: 'center', color: '#64748b' }}>
            Validating reset link...
          </p>
        ) : !tokenValid ? (
          <div className="space-y-4 text-center" style={{ textAlign: 'center' }}>
            <p className="text-sm text-red-500" style={{ color: '#ef4444', fontSize: '14px' }}>
              This reset link is invalid or has expired. Please request a new one.
            </p>
            <Link
              to="/forgot-password"
              className="inline-block text-sm font-bold text-[#134e4a] hover:underline"
              style={{ color: '#134e4a', fontWeight: 'bold', fontSize: '14px' }}
            >
              Request new reset link
            </Link>
          </div>
        ) : success ? (
          <div className="space-y-4 text-center" style={{ textAlign: 'center' }}>
            <p className="text-sm text-green-600" style={{ color: '#16a34a', fontSize: '14px' }}>
              Your password has been reset successfully. Redirecting to sign in...
            </p>
            <Link to="/" className="text-sm font-bold text-[#134e4a] hover:underline" style={{ color: '#134e4a', fontWeight: 'bold' }}>
              Sign in now
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-1.5 text-left">
              <label className="block text-xs font-bold uppercase tracking-wider text-[#134e4a]" style={{ color: '#134e4a', fontWeight: 'bold', fontSize: '11px', textTransform: 'uppercase', marginBottom: '6px', display: 'block' }}>
                New password
              </label>
              <div className="flex min-h-[50px] items-center gap-3 rounded-2xl border border-slate-200 bg-white px-5" style={{ display: 'flex', alignItems: 'center', gap: '12px', borderRadius: '16px', border: '1.5px solid #e2e8f0', padding: '0 16px', minHeight: '52px' }}>
                <Lock className="h-5 w-5 shrink-0 text-slate-400" style={{ color: '#94a3b8', height: '20px', width: '20px' }} />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  style={glassInputStyle}
                  autoComplete="new-password"
                  minLength={8}
                  required
                />
                <button type="button" onClick={() => setShowPassword(!showPassword)} className="shrink-0 border-0 bg-transparent p-0" style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: '#94a3b8' }} aria-label={showPassword ? 'Hide password' : 'Show password'}>
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
            </div>

            <div className="space-y-1.5 text-left">
              <label className="block text-xs font-bold uppercase tracking-wider text-[#134e4a]" style={{ color: '#134e4a', fontWeight: 'bold', fontSize: '11px', textTransform: 'uppercase', marginBottom: '6px', display: 'block' }}>
                Confirm password
              </label>
              <div className="flex min-h-[50px] items-center gap-3 rounded-2xl border border-slate-200 bg-white px-5" style={{ display: 'flex', alignItems: 'center', gap: '12px', borderRadius: '16px', border: '1.5px solid #e2e8f0', padding: '0 16px', minHeight: '52px' }}>
                <Lock className="h-5 w-5 shrink-0 text-slate-400" style={{ color: '#94a3b8', height: '20px', width: '20px' }} />
                <input
                  type={showConfirmPassword ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  style={glassInputStyle}
                  autoComplete="new-password"
                  minLength={8}
                  required
                />
                <button type="button" onClick={() => setShowConfirmPassword(!showConfirmPassword)} className="shrink-0 border-0 bg-transparent p-0" style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: '#94a3b8' }} aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}>
                  {showConfirmPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
            </div>

            {password !== confirmPassword && confirmPassword.length > 0 && (
              <p className="text-center text-sm text-red-500" style={{ color: '#ef4444', fontSize: '14px', textAlign: 'center' }}>
                Passwords do not match
              </p>
            )}

            {error && (
              <p className="text-center text-sm text-red-500" style={{ color: '#ef4444', fontSize: '14px', textAlign: 'center' }}>
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading || !password || password !== confirmPassword}
              className="w-full rounded-2xl border-0 bg-[#134e4a] py-3.5 text-base font-semibold text-white disabled:opacity-50"
              style={{
                backgroundColor: '#134e4a',
                color: '#ffffff',
                borderRadius: '16px',
                padding: '14px 0',
                fontSize: '16px',
                fontWeight: 600,
                border: 'none',
                cursor: 'pointer',
                width: '100%',
                opacity: loading || !password || password !== confirmPassword ? 0.5 : 1,
              }}
            >
              {loading ? 'Resetting...' : 'Reset Password'}
            </button>

            <p className="text-center text-sm text-slate-500" style={{ textAlign: 'center', fontSize: '14px', color: '#64748b' }}>
              <Link to="/" className="inline-flex items-center gap-1 font-bold text-[#134e4a] hover:underline" style={{ color: '#134e4a', fontWeight: 'bold' }}>
                <ArrowLeft className="h-4 w-4" />
                Back to sign in
              </Link>
            </p>
          </form>
        )}
      </div>
    </div>
  );
};

export default ResetPasswordScreen;
