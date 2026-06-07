'use client';

import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { sendWelcomeEmail } from '@/lib/api';

export default function LoginPage() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const router = useRouter();

    useEffect(() => {
        // Hide sidebar
        document.body.classList.add('auth-page');
        return () => document.body.classList.remove('auth-page');
    }, []);

    const handleLogin = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        const { data, error } = await supabase.auth.signInWithPassword({
            email,
            password,
        });

        if (error) {
            setError(error.message);
            setLoading(false);
        } else {
            // Check if this is a new signup — if so, send welcome email
            if (typeof window !== 'undefined' && sessionStorage.getItem('secureshield_new_signup')) {
                sessionStorage.removeItem('secureshield_new_signup');
                // Fire and forget — don't block login
                sendWelcomeEmail().catch((err) => console.error('Welcome email failed:', err));
            }
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
                    <h1 style={{ fontSize: 24, fontWeight: 800, color: 'var(--navy-800)' }}>Welcome back</h1>
                    <p style={{ color: 'var(--gray-500)', fontSize: 14, marginTop: 4 }}>Sign in to SecureShield to continue</p>
                </div>

                {error && (
                    <div style={{ padding: 12, background: 'var(--red-50)', color: 'var(--red-600)', borderRadius: 'var(--radius-sm)', fontSize: 13, marginBottom: 20, border: '1px solid var(--red-100)' }}>
                        {error}
                    </div>
                )}

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
                        <label className="form-label">Password</label>
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

                <div style={{ textAlign: 'center', marginTop: 24, fontSize: 14, color: 'var(--gray-500)' }}>
                    Don't have an account? <Link href="/signup" style={{ color: 'var(--primary-600)', fontWeight: 600, textDecoration: 'none' }}>Sign up</Link>
                </div>
            </div>
        </div>
    );
}
