'use client';

import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function LoginPage() {
    // Shared states
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState(''); // Used for both login and new password
    const [confirmPassword, setConfirmPassword] = useState('');
    const [otpCode, setOtpCode] = useState('');
    
    // UI state
    const [mode, setMode] = useState('login'); // 'login' | 'email' | 'otp' | 'password'
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [message, setMessage] = useState(null);
    
    const router = useRouter();

    useEffect(() => {
        // Hide sidebar
        document.body.classList.add('auth-page');
        return () => document.body.classList.remove('auth-page');
    }, []);

    const resetMessages = () => {
        setError(null);
        setMessage(null);
    };

    // 1. Standard Login
    const handleLogin = async (e) => {
        e.preventDefault();
        setLoading(true);
        resetMessages();

        const { data, error } = await supabase.auth.signInWithPassword({
            email,
            password,
        });

        if (error) {
            setError(error.message);
            setLoading(false);
        } else {
            router.push('/');
        }
    };

    // 2. Send Forgot Password OTP
    const handleSendResetCode = async (e) => {
        e.preventDefault();
        setLoading(true);
        resetMessages();

        const { error } = await supabase.auth.resetPasswordForEmail(email);

        if (error) {
            setError(error.message);
        } else {
            setMode('otp');
            setMessage('A verification code has been sent to your email.');
        }
        setLoading(false);
    };

    // 3. Verify OTP Code
    const handleVerifyOtp = async (e) => {
        e.preventDefault();
        setLoading(true);
        resetMessages();

        const { data, error } = await supabase.auth.verifyOtp({
            email,
            token: otpCode,
            type: 'recovery'
        });

        if (error) {
            setError(error.message);
        } else {
            setMode('password');
            setMessage('Code verified! Please enter your new password.');
        }
        setLoading(false);
    };

    // 4. Set New Password
    const handleUpdatePassword = async (e) => {
        e.preventDefault();
        resetMessages();

        if (password !== confirmPassword) {
            setError('Passwords do not match');
            return;
        }

        setLoading(true);

        const { error } = await supabase.auth.updateUser({
            password: password
        });

        if (error) {
            setError(error.message);
        } else {
            setMode('login');
            setPassword('');
            setConfirmPassword('');
            setOtpCode('');
            setMessage('Password updated successfully! You can now sign in.');
            // Log out the user so they have to explicitly sign in with new credentials
            await supabase.auth.signOut();
        }
        setLoading(false);
    };

    return (
        <div style={{ display: 'flex', minHeight: '100vh', width: '100vw', background: 'var(--gray-50)', position: 'absolute', top: 0, left: 0, zIndex: 1000, alignItems: 'center', justifyContent: 'center' }}>
            <div className="card" style={{ width: '100%', maxWidth: 440, padding: 40 }}>
                <div style={{ textAlign: 'center', marginBottom: 32 }}>
                    <div style={{
                        width: 56, height: 56, background: 'var(--primary-500)', borderRadius: 'var(--radius-md)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 28, color: 'white',
                        margin: '0 auto 16px', boxShadow: '0 8px 16px var(--primary-glow)'
                    }}>🛡️</div>
                    <h1 style={{ fontSize: 24, fontWeight: 800, color: 'var(--navy-800)' }}>
                        {mode === 'login' ? 'Welcome back' : 'Reset Password'}
                    </h1>
                    <p style={{ color: 'var(--gray-500)', fontSize: 14, marginTop: 4 }}>
                        {mode === 'login' ? 'Sign in to SecureShield to continue' : 'Follow the steps to secure your account'}
                    </p>
                </div>

                {error && (
                    <div style={{ padding: 12, background: 'var(--red-50)', color: 'var(--red-600)', borderRadius: 'var(--radius-sm)', fontSize: 13, marginBottom: 20, border: '1px solid var(--red-100)' }}>
                        {error}
                    </div>
                )}

                {message && (
                    <div style={{ padding: 12, background: 'var(--green-50)', color: 'var(--green-600)', borderRadius: 'var(--radius-sm)', fontSize: 13, marginBottom: 20, border: '1px solid var(--green-100)' }}>
                        {message}
                    </div>
                )}

                {mode === 'login' && (
                    <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                        <div className="form-group">
                            <label className="form-label">Email address</label>
                            <input
                                type="email"
                                className="form-input"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                                placeholder="you@example.com"
                            />
                        </div>
                        <div className="form-group">
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <label className="form-label">Password</label>
                                <button 
                                    type="button" 
                                    onClick={() => { setMode('email'); resetMessages(); }}
                                    style={{ background: 'none', border: 'none', color: 'var(--primary-600)', fontSize: 13, fontWeight: 600, cursor: 'pointer', padding: 0 }}
                                >
                                    Forgot password?
                                </button>
                            </div>
                            <input
                                type="password"
                                className="form-input"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                placeholder="••••••••"
                            />
                        </div>
                        <button type="submit" className="btn btn-primary" disabled={loading} style={{ marginTop: 8, height: 44, background: 'var(--primary-500)' }}>
                            {loading ? 'Signing in...' : 'Sign in'}
                        </button>
                    </form>
                )}

                {mode === 'email' && (
                    <form onSubmit={handleSendResetCode} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                        <div className="form-group">
                            <label className="form-label">Email address</label>
                            <input
                                type="email"
                                className="form-input"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                                placeholder="you@example.com"
                            />
                            <p style={{ fontSize: 12, color: 'var(--gray-500)', marginTop: 8 }}>
                                We will send a verification code to this email to reset your password.
                            </p>
                        </div>
                        <button type="submit" className="btn btn-primary" disabled={loading} style={{ marginTop: 8, height: 44, background: 'var(--primary-500)' }}>
                            {loading ? 'Sending code...' : 'Send Verification Code'}
                        </button>
                        <button 
                            type="button" 
                            onClick={() => { setMode('login'); resetMessages(); }}
                            style={{ background: 'none', border: 'none', color: 'var(--gray-500)', fontSize: 14, cursor: 'pointer', marginTop: 8, fontWeight: 500 }}
                        >
                            Back to login
                        </button>
                    </form>
                )}

                {mode === 'otp' && (
                    <form onSubmit={handleVerifyOtp} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                        <div className="form-group">
                            <label className="form-label">Verification Code</label>
                            <input
                                type="text"
                                className="form-input"
                                value={otpCode}
                                onChange={(e) => setOtpCode(e.target.value)}
                                required
                                placeholder="12345678"
                                maxLength={8}
                                style={{ letterSpacing: 8, fontSize: 20, textAlign: 'center' }}
                            />
                        </div>
                        <button type="submit" className="btn btn-primary" disabled={loading} style={{ marginTop: 8, height: 44, background: 'var(--primary-500)' }}>
                            {loading ? 'Verifying...' : 'Verify Code'}
                        </button>
                        <button 
                            type="button" 
                            onClick={() => { setMode('email'); resetMessages(); }}
                            style={{ background: 'none', border: 'none', color: 'var(--gray-500)', fontSize: 14, cursor: 'pointer', marginTop: 8, fontWeight: 500 }}
                        >
                            Change email
                        </button>
                    </form>
                )}

                {mode === 'password' && (
                    <form onSubmit={handleUpdatePassword} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                        <div className="form-group">
                            <label className="form-label">New Password</label>
                            <input
                                type="password"
                                className="form-input"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                placeholder="••••••••"
                                minLength={6}
                            />
                        </div>
                        <div className="form-group">
                            <label className="form-label">Confirm New Password</label>
                            <input
                                type="password"
                                className="form-input"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                required
                                placeholder="••••••••"
                                minLength={6}
                            />
                        </div>
                        <button type="submit" className="btn btn-primary" disabled={loading} style={{ marginTop: 8, height: 44, background: 'var(--primary-500)' }}>
                            {loading ? 'Updating...' : 'Update Password'}
                        </button>
                    </form>
                )}

                {mode === 'login' && (
                    <div style={{ textAlign: 'center', marginTop: 24, fontSize: 14, color: 'var(--gray-500)' }}>
                        Don't have an account? <Link href="/signup" style={{ color: 'var(--primary-600)', fontWeight: 600, textDecoration: 'none' }}>Sign up</Link>
                    </div>
                )}
            </div>
        </div>
    );
}
