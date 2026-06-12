'use client';

/**
 * Sidebar Component
 * Premium navigation sidebar with active page highlighting.
 */

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';

const NAV_ITEMS = [
    { label: 'Dashboard', icon: '📊', href: '/', protected: true },
    { label: 'Upload Policy', icon: '📄', href: '/upload', protected: true },
    { label: 'Chat Assistant', icon: '💬', href: '/chat', protected: false },
    { label: 'Check Eligibility', icon: '🔍', href: '/check', protected: true },
    { label: 'Dispute Claim', icon: '⚖️', href: '/dispute', protected: true },
    { label: 'History', icon: '📋', href: '/history', protected: true },
    { label: 'Audit Trail', icon: '🛡️', href: '/audit', protected: true },
    { label: 'About', icon: '💡', href: '/about', protected: false },
    { label: 'How It Works', icon: '📚', href: '/how-it-works', protected: false },
];

export default function Sidebar() {
    const pathname = usePathname();
    const router = useRouter();
    const [user, setUser] = useState(null);
    const [showLoginPopup, setShowLoginPopup] = useState(false);

    useEffect(() => {
        // Get initial user
        supabase.auth.getUser().then(({ data: { user } }) => {
            setUser(user);
        });

        // Listen for login/logout events so the sidebar updates in real-time
        const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
            setUser(session?.user ?? null);
        });

        return () => subscription.unsubscribe();
    }, []);

    const handleSignOut = async () => {
        await supabase.auth.signOut();
        router.push('/login');
    };

    const getInitials = (name) => {
        if (!name) return 'U';
        return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
    };

    return (
        <aside className="sidebar">
            <Link href="/" className="sidebar-logo">
                <div className="sidebar-logo-icon">🛡️</div>
                <div>
                    <div className="sidebar-logo-text">SecureShield</div>
                    <div className="sidebar-logo-badge">SECURE HEALTH PORTAL</div>
                </div>
            </Link>

            <nav className="sidebar-nav">
                <div className="sidebar-section-title">Navigation</div>
                {NAV_ITEMS.map((item) => (
                    <Link
                        key={item.href}
                        href={item.href}
                        onClick={(e) => {
                            if (item.protected && !user) {
                                e.preventDefault();
                                setShowLoginPopup(true);
                            }
                        }}
                        className={`nav-link ${pathname === item.href ? 'active' : ''}`}
                    >
                        <span className="nav-icon">{item.icon}</span>
                        {item.label}
                    </Link>
                ))}
            </nav>

            <div className="sidebar-footer">
                <div className="sidebar-section-title">System</div>
                <Link href="/settings" className={`nav-link ${pathname === '/settings' ? 'active' : ''}`}>
                    <span className="nav-icon">⚙️</span>
                    Settings
                </Link>
                
                {user ? (
                    <div className="sidebar-profile" style={{ marginTop: 24, display: 'flex', flexDirection: 'column', gap: 12 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                            <div className="avatar" style={{ overflow: 'hidden', padding: 0 }}>
                                {user?.user_metadata?.avatar_url ? (
                                    <img src={user.user_metadata.avatar_url} alt="Profile" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                                ) : (
                                    getInitials(user?.user_metadata?.full_name || user?.email)
                                )}
                            </div>
                            <div className="profile-info" style={{ overflow: 'hidden' }}>
                                <span className="profile-name" style={{ whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden', display: 'block' }}>
                                    {user?.user_metadata?.full_name || 'User'}
                                </span>
                                <span className="profile-role" style={{ whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden', display: 'block' }}>
                                    {user?.email || 'Patient'}
                                </span>
                            </div>
                        </div>
                        <button 
                            onClick={handleSignOut} 
                            style={{ background: 'transparent', border: '1px solid var(--gray-200)', borderRadius: 'var(--radius-sm)', padding: '6px 12px', fontSize: 12, color: 'var(--gray-600)', cursor: 'pointer', textAlign: 'center', width: '100%', fontWeight: 500 }}
                        >
                            Sign out
                        </button>
                    </div>
                ) : (
                    <div style={{ marginTop: 24 }}>
                        <Link href="/login" style={{ display: 'block', background: 'var(--primary-600)', color: 'white', textDecoration: 'none', textAlign: 'center', padding: '10px', borderRadius: 'var(--radius-md)', fontWeight: 600, transition: 'background 0.2s' }}>
                            Sign In
                        </Link>
                    </div>
                )}
            </div>

            {/* Login Required Popup */}
            {showLoginPopup && (
                <div style={{
                    position: 'fixed',
                    top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.4)',
                    backdropFilter: 'blur(4px)',
                    zIndex: 9999,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    animation: 'fadeIn 0.2s ease-out'
                }} onClick={() => setShowLoginPopup(false)}>
                    <div style={{
                        background: 'white',
                        padding: '40px',
                        borderRadius: '24px',
                        maxWidth: '400px',
                        width: '90%',
                        textAlign: 'center',
                        boxShadow: '0 20px 40px rgba(0,0,0,0.1)',
                        transform: 'translateY(0)',
                        animation: 'slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1)'
                    }} onClick={e => e.stopPropagation()}>
                        <div style={{ fontSize: '48px', marginBottom: '16px' }}>🔒</div>
                        <h2 style={{ color: 'var(--navy-900)', fontSize: '24px', fontWeight: 800, marginBottom: '12px' }}>
                            Sign in Required
                        </h2>
                        <p style={{ color: 'var(--gray-500)', fontSize: '15px', lineHeight: 1.5, marginBottom: '32px' }}>
                            To access your dashboard, policies, and claim history, please sign in or create an account.
                        </p>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            <Link href="/login" 
                                className="btn-primary" 
                                style={{ width: '100%', padding: '14px', borderRadius: '12px', fontSize: '16px', textDecoration: 'none', display: 'block' }}>
                                Sign In
                            </Link>
                            <Link href="/signup" 
                                className="btn-secondary" 
                                style={{ width: '100%', padding: '14px', borderRadius: '12px', fontSize: '16px', textDecoration: 'none', display: 'block', background: 'white' }}>
                                Create an Account
                            </Link>
                        </div>
                    </div>
                </div>
            )}
            <style jsx>{`
                @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
                @keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
            `}</style>
        </aside>
    );
}
