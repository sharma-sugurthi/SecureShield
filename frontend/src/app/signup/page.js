'use client';

import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { sendWelcomeEmail } from '@/lib/api';

export default function SignupPage() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [name, setName] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [otpMode, setOtpMode] = useState(false);
    const [otpCode, setOtpCode] = useState('');
    const [verifying, setVerifying] = useState(false);
    const router = useRouter();

    useEffect(() => {
        // Hide sidebar
        document.body.classList.add('auth-page');
        return () => document.body.classList.remove('auth-page');
    }, []);

    const handleSignup = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        const { data, error } = await supabase.auth.signUp({
            email,
            password,
            options: {
                data: {
                    full_name: name,
                }
            }
        });

        if (error) {
            setError(error.message);
            setLoading(false);
        } else {
            setOtpMode(true);
            setLoading(false);
        }
    };

    const handleVerifyOtp = async (e) => {
        e.preventDefault();
        setVerifying(true);
        setError(null);

        const { data, error } = await supabase.auth.verifyOtp({
            email,
            token: otpCode,
            type: 'signup'
        });

        if (error) {
            setError(error.message);
            setVerifying(false);
        } else {
            // Success! Send welcome email
            sendWelcomeEmail().catch((err) => console.error('Welcome email failed:', err));
            router.push('/');
        }
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
                    <h1 style={{ fontSize: 24, fontWeight: 800, color: 'var(--navy-800)' }}>Create an account</h1>
                    <p style={{ color: 'var(--gray-500)', fontSize: 14, marginTop: 4 }}>Start checking insurance claims with AI</p>
                </div>

                {error && (
                    <div style={{ padding: 12, background: 'var(--red-50)', color: 'var(--red-600)', borderRadius: 'var(--radius-sm)', fontSize: 13, marginBottom: 20, border: '1px solid var(--red-100)' }}>
                        {error}
                    </div>
                )}

                {otpMode ? (
                    <form onSubmit={handleVerifyOtp} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                        <div style={{ padding: 16, background: 'var(--blue-50)', color: 'var(--blue-600)', borderRadius: 'var(--radius-sm)', fontSize: 14, border: '1px solid var(--blue-100)', marginBottom: 12 }}>
                            We sent a verification code to <strong>{email}</strong>. This code is valid for 10 minutes.
                        </div>
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
                        <button type="submit" className="btn btn-primary" disabled={verifying} style={{ marginTop: 8, height: 44, background: 'var(--primary-500)' }}>
                            {verifying ? 'Verifying...' : 'Verify Email & Login'}
                        </button>
                    </form>
                ) : (
                    <form onSubmit={handleSignup} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                        <div className="form-group">
                            <label className="form-label">Full Name</label>
                            <input
                                type="text"
                                className="form-input"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                required
                                placeholder="John Doe"
                            />
                        </div>
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
                            <label className="form-label">Password</label>
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
                        <button type="submit" className="btn btn-primary" disabled={loading} style={{ marginTop: 8, height: 44, background: 'var(--primary-500)' }}>
                            {loading ? 'Creating account...' : 'Create account'}
                        </button>
                    </form>
                )}

                {!otpMode && (
                    <div style={{ textAlign: 'center', marginTop: 24, fontSize: 14, color: 'var(--gray-500)' }}>
                        Already have an account? <Link href="/login" style={{ color: 'var(--primary-600)', fontWeight: 600, textDecoration: 'none' }}>Sign in</Link>
                    </div>
                )}
            </div>
        </div>
    );
}
