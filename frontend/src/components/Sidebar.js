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
    { label: 'Dashboard', icon: '📊', href: '/' },
    { label: 'About', icon: '💡', href: '/about' },
    { label: 'Upload Policy', icon: '📄', href: '/upload' },
    { label: 'Check Eligibility', icon: '🔍', href: '/check' },
    { label: 'Dispute Claim', icon: '⚖️', href: '/dispute' },
    { label: 'Chat Assistant', icon: '💬', href: '/chat' },
    { label: 'History', icon: '📋', href: '/history' },
    { label: 'Audit Trail', icon: '🛡️', href: '/audit' },
    { label: 'How It Works', icon: '📚', href: '/how-it-works' },
];

export default function Sidebar() {
    const pathname = usePathname();
    const router = useRouter();
    const [user, setUser] = useState(null);

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
                
                <div className="sidebar-profile" style={{ marginTop: 24, display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <div className="avatar">{getInitials(user?.user_metadata?.full_name || user?.email)}</div>
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
            </div>
        </aside>
    );
}
