import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail, ArrowLeft } from 'lucide-react';
import { requestPasswordReset } from '../../api/auth';

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

const ForgotPasswordScreen: React.FC = () => {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    document.documentElement.style.backgroundColor = '#f8fafc';
    document.body.style.backgroundColor = '#f8fafc';
    return () => {
      document.documentElement.style.backgroundColor = '';
      document.body.style.backgroundColor = '';
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await requestPasswordReset(email);
      setSubmitted(true);
    } catch {
      setError('Something went wrong. Please try again.');
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
            Forgot Password
          </h1>
          <p className="mt-2 text-sm text-[#4e878c] font-medium" style={{ color: '#4e878c', fontSize: '14px', marginTop: '8px' }}>
            {submitted
              ? 'Check your inbox for a reset link.'
              : 'Enter your email and we\u2019ll send you a reset link.'}
          </p>
        </div>

        {submitted ? (
          <div className="space-y-4 text-center" style={{ textAlign: 'center' }}>
            <p className="text-sm text-slate-600" style={{ color: '#475569', fontSize: '14px' }}>
              If an account exists for <strong>{email}</strong>, you will receive a password reset link shortly.
              The link expires in 15 minutes.
            </p>
            <Link
              to="/"
              className="inline-flex items-center gap-2 text-sm font-bold text-[#134e4a] hover:underline"
              style={{ color: '#134e4a', fontWeight: 'bold', fontSize: '14px', textDecoration: 'none' }}
            >
              <ArrowLeft className="h-4 w-4" />
              Back to sign in
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-1.5 text-left">
              <label
                className="block text-xs font-bold uppercase tracking-wider text-[#134e4a]"
                style={{ color: '#134e4a', fontWeight: 'bold', fontSize: '11px', textTransform: 'uppercase', marginBottom: '6px', display: 'block' }}
              >
                Email address
              </label>
              <div
                className="flex min-h-[50px] items-center gap-3 rounded-2xl border border-slate-200 bg-white px-5"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  borderRadius: '16px',
                  border: '1.5px solid #e2e8f0',
                  paddingLeft: '16px',
                  paddingRight: '16px',
                  minHeight: '52px',
                }}
              >
                <Mail className="h-5 w-5 shrink-0 text-slate-400" style={{ color: '#94a3b8', height: '20px', width: '20px' }} />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@gmail.com"
                  style={glassInputStyle}
                  autoComplete="email"
                  required
                />
              </div>
            </div>

            {error && (
              <p className="text-center text-sm text-red-500" style={{ color: '#ef4444', fontSize: '14px', textAlign: 'center' }}>
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading || !email.trim()}
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
                opacity: loading ? 0.5 : 1,
              }}
            >
              {loading ? 'Sending...' : 'Send Reset Link'}
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

export default ForgotPasswordScreen;
