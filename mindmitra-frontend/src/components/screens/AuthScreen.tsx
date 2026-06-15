import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Eye, EyeOff, Mail, User, Lock } from 'lucide-react';

type AuthMode = 'signin' | 'register';

interface AuthScreenProps {
  onSignIn: (email: string, password: string) => void;
  onRegister?: (email: string, password: string, name: string) => void;
  loading?: boolean;
}

const MindMitraLogo: React.FC = () => (
  <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#4a90d9] shadow-lg shadow-blue-500/10" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#4a90d9', borderRadius: '16px', height: '64px', width: '64px', margin: '0 auto 16px' }}>
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

const GlassField: React.FC<{
  label: string;
  children: React.ReactNode;
}> = ({ label, children }) => (
  <div className="space-y-1.5 text-left" style={{ textAlign: 'left', marginBottom: '16px' }}>
    <label className="block text-xs font-bold uppercase tracking-wider text-[#134e4a]" style={{ color: '#134e4a', fontWeight: 'bold', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px', display: 'block' }}>
      {label}
    </label>
    <div
      className="flex min-h-[50px] items-center gap-3 rounded-2xl border border-slate-200 bg-white px-5 focus-within:border-[#134e4a] focus-within:ring-1 focus-within:ring-[#134e4a]/10 transition-all"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        borderRadius: '16px',
        border: '1.5px solid #e2e8f0',
        backgroundColor: '#ffffff',
        paddingLeft: '16px',
        paddingRight: '16px',
        minHeight: '52px',
        transition: 'all 0.2s ease',
        boxSizing: 'border-box'
      }}
    >
      {children}
    </div>
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
  color: '#000000', // Black input text color!
  fontSize: '14px',
  fontFamily: 'inherit',
  width: '100%',
  boxSizing: 'border-box'
};

const AuthScreen: React.FC<AuthScreenProps> = ({ onSignIn, onRegister, loading = false }) => {
  const [mode, setMode] = useState<AuthMode>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [name, setName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Password strength calculation
  const getPasswordStrength = () => {
    const hasMinLength = password.length >= 8;
    const hasNumber = /[0-9]/.test(password);
    const hasUpperLower = /[A-Z]/.test(password) && /[a-z]/.test(password);
    const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(password);
    
    let noPersonalInfo = true;
    if (name.trim() && password.toLowerCase().includes(name.trim().toLowerCase())) {
      noPersonalInfo = false;
    }
    const emailPrefix = email.split('@')[0];
    if (emailPrefix.trim() && password.toLowerCase().includes(emailPrefix.trim().toLowerCase())) {
      noPersonalInfo = false;
    }

    // Common sequences
    let noSequences = true;
    const sequentialPatterns = ["12345", "54321", "abcde", "qwerty"];
    for (const pattern of sequentialPatterns) {
      if (password.toLowerCase().includes(pattern)) {
        noSequences = false;
      }
    }

    // Repeated characters
    let noRepeats = true;
    if (/(.)\1{4,}/.test(password)) {
      noRepeats = false;
    }

    const criteria = {
      minLength: hasMinLength,
      number: hasNumber,
      upperLower: hasUpperLower,
      special: hasSpecial,
      personalInfo: noPersonalInfo && noSequences && noRepeats && password.length > 0
    };

    let score = 0;
    if (hasMinLength) score++;
    if (hasNumber) score++;
    if (hasUpperLower) score++;
    if (hasSpecial) score++;
    if (criteria.personalInfo) score++;

    return { criteria, score };
  };

  const { criteria, score } = getPasswordStrength();
  const isPasswordValid = score === 5;

  useEffect(() => {
    // Dynamic background toggle to prevent Safari flex container portal bugs
    const originalHtmlBg = document.documentElement.style.backgroundColor;
    const originalBodyBg = document.body.style.backgroundColor;
    const originalHtmlColor = document.documentElement.style.color;
    const originalBodyColor = document.body.style.color;

    document.documentElement.style.backgroundColor = '#f8fafc';
    document.body.style.backgroundColor = '#f8fafc';
    document.documentElement.style.color = '#1e293b';
    document.body.style.color = '#1e293b';

    return () => {
      document.documentElement.style.backgroundColor = originalHtmlBg;
      document.body.style.backgroundColor = originalBodyBg;
      document.documentElement.style.color = originalHtmlColor;
      document.body.style.color = originalBodyColor;
    };
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (mode === 'register') {
      if (password !== confirmPassword) return;
      onRegister?.(email, password, name);
      return;
    }
    onSignIn(email, password);
  };

  return (
    <div
      className="relative z-10 w-full max-w-[400px] rounded-[32px] bg-white px-8 py-10 shadow-[0_15px_50px_rgba(0,0,0,0.05)] border border-slate-100 mx-auto"
      style={{
        margin: '0 auto',
        maxWidth: '400px',
        width: '100%',
        boxSizing: 'border-box',
        borderRadius: '32px',
        backgroundColor: '#ffffff',
        padding: '40px 32px',
        border: '1px solid #f1f5f9',
        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.05), 0 10px 10px -5px rgba(0, 0, 0, 0.02)'
      }}
    >
      <div className="mb-8 text-center" style={{ textAlign: 'center', marginBottom: '32px' }}>
        <MindMitraLogo />
        <h1 className="text-3xl font-extrabold tracking-tight text-[#134e4a]" style={{ color: '#134e4a', fontSize: '30px', fontWeight: '800', letterSpacing: '-0.025em', margin: 0 }}>
          MindMitra
        </h1>
        <p className="mt-2 text-sm text-[#4e878c] font-medium" style={{ color: '#4e878c', fontSize: '14px', fontWeight: '500', marginTop: '8px', margin: 0 }}>
          Your gentle companion for emotional wellness
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {mode === 'register' && (
          <GlassField label="Name">
            <User className="h-5 w-5 shrink-0 text-slate-400" aria-hidden="true" style={{ color: '#94a3b8', flexShrink: 0, height: '20px', width: '20px' }} />
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Alex Doe"
              style={glassInputStyle}
              autoComplete="name"
              required
            />
          </GlassField>
        )}

        <GlassField label="Email address">
          <Mail className="h-5 w-5 shrink-0 text-slate-400" aria-hidden="true" style={{ color: '#94a3b8', flexShrink: 0, height: '20px', width: '20px' }} />
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@gmail.com"
            style={glassInputStyle}
            autoComplete="email"
            required
          />
        </GlassField>

        <GlassField label="Password">
          <Lock className="h-5 w-5 shrink-0 text-slate-400" aria-hidden="true" style={{ color: '#94a3b8', flexShrink: 0, height: '20px', width: '20px' }} />
          <input
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            style={glassInputStyle}
            autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
            required
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="shrink-0 border-0 bg-transparent p-0 text-slate-400 shadow-none hover:text-slate-600"
            style={{
              border: 'none',
              background: 'transparent',
              padding: 0,
              boxShadow: 'none',
              cursor: 'pointer',
              color: '#94a3b8',
              flexShrink: 0
            }}
            aria-label={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? <EyeOff className="h-5 w-5" style={{ height: '20px', width: '20px' }} /> : <Eye className="h-5 w-5" style={{ height: '20px', width: '20px' }} />}
          </button>
        </GlassField>

        {mode === 'register' && password.length > 0 && (
          <div style={{ marginTop: '4px', textAlign: 'left' }}>
            {/* Strength Bar */}
            <div style={{ display: 'flex', height: '6px', width: '100%', gap: '4px', borderRadius: '3px', backgroundColor: '#e2e8f0', overflow: 'hidden' }}>
              <div
                style={{
                  height: '100%',
                  borderRadius: '3px',
                  transition: 'all 0.3s ease',
                  width: `${(score / 5) * 100}%`,
                  backgroundColor: score <= 2 ? '#ef4444' : score <= 4 ? '#eab308' : '#22c55e'
                }}
              />
            </div>
            {/* Strength Label */}
            <p style={{ fontSize: '12px', marginTop: '6px', fontWeight: 'bold', color: score <= 2 ? '#ef4444' : score <= 4 ? '#ca8a04' : '#16a34a', margin: '4px 0 0' }}>
              Password Strength: {score <= 2 ? 'Weak' : score <= 4 ? 'Medium' : 'Strong (Valid)'}
            </p>
            {/* Checklist */}
            <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '12px', color: '#64748b' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ color: criteria.minLength ? '#22c55e' : '#94a3b8', fontWeight: 'bold' }}>
                  {criteria.minLength ? '✓' : '○'}
                </span>
                <span style={{ color: criteria.minLength ? '#1e293b' : 'inherit' }}>At least 8 characters</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ color: criteria.number ? '#22c55e' : '#94a3b8', fontWeight: 'bold' }}>
                  {criteria.number ? '✓' : '○'}
                </span>
                <span style={{ color: criteria.number ? '#1e293b' : 'inherit' }}>At least one number (0-9)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ color: criteria.upperLower ? '#22c55e' : '#94a3b8', fontWeight: 'bold' }}>
                  {criteria.upperLower ? '✓' : '○'}
                </span>
                <span style={{ color: criteria.upperLower ? '#1e293b' : 'inherit' }}>Uppercase & lowercase letters</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ color: criteria.special ? '#22c55e' : '#94a3b8', fontWeight: 'bold' }}>
                  {criteria.special ? '✓' : '○'}
                </span>
                <span style={{ color: criteria.special ? '#1e293b' : 'inherit' }}>At least one special character</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ color: criteria.personalInfo ? '#22c55e' : '#94a3b8', fontWeight: 'bold' }}>
                  {criteria.personalInfo ? '✓' : '○'}
                </span>
                <span style={{ color: criteria.personalInfo ? '#1e293b' : 'inherit' }}>No name, email prefix, sequences or repeats</span>
              </div>
            </div>
          </div>
        )}

        {mode === 'signin' && (
          <p className="text-right text-sm" style={{ textAlign: 'right', margin: '-8px 0 0', fontSize: '14px' }}>
            <Link
              to="/forgot-password"
              className="font-semibold text-[#134e4a] hover:underline"
              style={{ color: '#134e4a', fontWeight: 600, textDecoration: 'none' }}
            >
              Forgot password?
            </Link>
          </p>
        )}

        {mode === 'register' && isPasswordValid && (
          <GlassField label="Confirm password">
            <Lock className="h-5 w-5 shrink-0 text-slate-400" aria-hidden="true" style={{ color: '#94a3b8', flexShrink: 0, height: '20px', width: '20px' }} />
            <input
              type={showConfirmPassword ? 'text' : 'password'}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="••••••••"
              style={glassInputStyle}
              autoComplete="new-password"
              required
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              className="shrink-0 border-0 bg-transparent p-0 text-slate-400 shadow-none hover:text-slate-600"
              style={{
                border: 'none',
                background: 'transparent',
                padding: 0,
                boxShadow: 'none',
                cursor: 'pointer',
                color: '#94a3b8',
                flexShrink: 0
              }}
              aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
            >
              {showConfirmPassword ? <EyeOff className="h-5 w-5" style={{ height: '20px', width: '20px' }} /> : <Eye className="h-5 w-5" style={{ height: '20px', width: '20px' }} />}
            </button>
          </GlassField>
        )}

        {mode === 'register' && isPasswordValid && password !== confirmPassword && confirmPassword.length > 0 && (
          <p className="text-center text-sm text-red-500" style={{ color: '#ef4444', fontSize: '14px', textAlign: 'center', margin: 0 }}>Passwords do not match</p>
        )}

        <button
          type="submit"
          disabled={
            loading ||
            (mode === 'register' &&
              (!name.trim() || !email.trim() || !isPasswordValid || password !== confirmPassword))
          }
          className="mt-2 w-full rounded-2xl border-0 bg-[#134e4a] py-3.5 text-base font-semibold text-white shadow-lg transition-all hover:bg-[#0f3d3b] hover:shadow-[#134e4a]/15 active:scale-[0.98] disabled:opacity-50"
          style={{
            backgroundColor: '#134e4a',
            color: '#ffffff',
            borderRadius: '16px',
            paddingTop: '14px',
            paddingBottom: '14px',
            fontSize: '16px',
            fontWeight: '600',
            border: 'none',
            cursor: 'pointer',
            width: '100%',
            marginTop: '8px',
            boxShadow: '0 10px 15px -3px rgba(19, 78, 74, 0.15)',
            boxSizing: 'border-box',
            opacity: loading ? 0.5 : 1
          }}
        >
          {loading
            ? mode === 'register'
              ? 'Creating account...'
              : 'Signing in...'
            : mode === 'register'
              ? 'Create Account'
              : 'Sign In'}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-500" style={{ textAlign: 'center', marginTop: '24px', fontSize: '14px', color: '#64748b', margin: 0 }}>
        {mode === 'signin' ? (
          <>
            <span>Don&apos;t have an account? </span>
            <button
              type="button"
              onClick={() => setMode('register')}
              className="inline border-0 bg-transparent p-0 font-bold text-[#134e4a] hover:underline shadow-none"
              style={{
                border: 'none',
                background: 'transparent',
                padding: 0,
                fontWeight: 'bold',
                color: '#134e4a',
                cursor: 'pointer',
                fontSize: 'inherit',
                textDecoration: 'underline'
              }}
            >
              Register here
            </button>
          </>
        ) : (
          <>
            <span>Already have an account? </span>
            <button
              type="button"
              onClick={() => setMode('signin')}
              className="inline border-0 bg-transparent p-0 font-bold text-[#134e4a] hover:underline shadow-none"
              style={{
                border: 'none',
                background: 'transparent',
                padding: 0,
                fontWeight: 'bold',
                color: '#134e4a',
                cursor: 'pointer',
                fontSize: 'inherit',
                textDecoration: 'underline'
              }}
            >
              Sign in here
            </button>
          </>
        )}
      </p>
    </div>
  );
};

export default AuthScreen;
