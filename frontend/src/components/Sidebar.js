'use client';

/**
 * Sidebar Component
 * Desktop: Premium fixed sidebar.
 * Mobile: Top header + Bottom tab bar (like Flipkart/Zomato) + Slide-up drawer for "More".
 */

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import {
    HomeIcon, UploadIcon, SearchIcon, ScaleIcon, MenuIcon,
    DashboardIcon, ChatIcon, HistoryIcon, ShieldIcon, LightbulbIcon,
    BookOpenIcon, SettingsIcon, LockIcon
} from '@/components/icons';

/* Bottom tab items — shown on mobile bottom bar */
const BOTTOM_TABS = [
    { label: 'Home',    icon: <HomeIcon size={20} />,    href: '/',        protected: true  },
    { label: 'Upload',  icon: <UploadIcon size={20} />,  href: '/upload',  protected: true  },
    { label: 'Check',   icon: <SearchIcon size={20} />,  href: '/check',   protected: true  },
    { label: 'Dispute', icon: <ScaleIcon size={20} />,   href: '/dispute', protected: true  },
    { label: 'More',    icon: <MenuIcon size={20} />,    href: '#more',    protected: false },
];

/* Full nav items — visible in desktop sidebar + mobile "More" drawer */
const NAV_ITEMS = [
    { label: 'Dashboard',       icon: <DashboardIcon size={18} />,  href: '/',           protected: true },
    { label: 'Upload Policy',   icon: <UploadIcon size={18} />,     href: '/upload',     protected: true },
    { label: 'Chat Assistant',  icon: <ChatIcon size={18} />,       href: '/chat',       protected: true },
    { label: 'Check Eligibility', icon: <SearchIcon size={18} />,   href: '/check',      protected: true },
    { label: 'Dispute Claim',   icon: <ScaleIcon size={18} />,      href: '/dispute',    protected: true },
    { label: 'History',         icon: <HistoryIcon size={18} />,    href: '/history',    protected: true },
    { label: 'Audit Trail',     icon: <ShieldIcon size={18} />,     href: '/audit',      protected: true },
    { label: 'About',           icon: <LightbulbIcon size={18} />,  href: '/about',      protected: false },
    { label: 'How It Works',    icon: <BookOpenIcon size={18} />,   href: '/how-it-works', protected: false },
];

export default function Sidebar() {
    const pathname = usePathname();
    const router = useRouter();
    const [user, setUser] = useState(null);
    const [showLoginPopup, setShowLoginPopup] = useState(false);
    const [showMoreDrawer, setShowMoreDrawer] = useState(false);

    useEffect(() => {
        setShowMoreDrawer(false);
    }, [pathname]);

    useEffect(() => {
        supabase.auth.getUser().then(({ data: { user } }) => {
            setUser(user);
        });
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

    const handleNavClick = (e, item) => {
        if (item.protected && !user) {
            e.preventDefault();
            setShowLoginPopup(true);
        }
    };

    const isActive = (href) => {
        if (href === '/') return pathname === '/';
        return pathname.startsWith(href);
    };

    return (
        <>
            {/* ======================== MOBILE TOP HEADER ======================== */}
            <header className="mobile-header">
                <Link href="/" className="mobile-logo">
                    <img src="/logo.png" alt="PolicyEye" className="mobile-logo-icon" />
                    <div className="mobile-logo-text">
                        <span className="mobile-logo-name">PolicyEye</span>
                        <span className="mobile-logo-badge">INSURANCE PORTAL</span>
                    </div>
                </Link>
                <div className="mobile-header-actions">
                    {user ? (
                        <Link href="/settings" className="mobile-avatar">
                            {user?.user_metadata?.avatar_url ? (
                                <img src={user.user_metadata.avatar_url} alt="Profile" />
                            ) : (
                                <span>{getInitials(user?.user_metadata?.full_name || user?.email)}</span>
                            )}
                        </Link>
                    ) : (
                        <Link href="/login" className="mobile-login-btn">Sign In</Link>
                    )}
                </div>
            </header>

            {/* ======================== MOBILE BOTTOM TAB BAR ======================== */}
            <nav className="mobile-bottom-bar">
                {BOTTOM_TABS.map((tab) => {
                    if (tab.href === '#more') {
                        return (
                            <button
                                key="more"
                                className={`mobile-tab ${showMoreDrawer ? 'active' : ''}`}
                                onClick={() => setShowMoreDrawer(!showMoreDrawer)}
                            >
                                <span className="mobile-tab-icon">{tab.icon}</span>
                                <span className="mobile-tab-label">{tab.label}</span>
                            </button>
                        );
                    }
                    return (
                        <Link
                            key={tab.href}
                            href={tab.href}
                            onClick={(e) => handleNavClick(e, tab)}
                            className={`mobile-tab ${isActive(tab.href) ? 'active' : ''}`}
                        >
                            <span className="mobile-tab-icon">{tab.icon}</span>
                            <span className="mobile-tab-label">{tab.label}</span>
                        </Link>
                    );
                })}
            </nav>

            {/* ======================== MOBILE "MORE" DRAWER ======================== */}
            {showMoreDrawer && (
                <div className="mobile-drawer-backdrop" onClick={() => setShowMoreDrawer(false)} />
            )}
            <div className={`mobile-drawer ${showMoreDrawer ? 'open' : ''}`}>
                <div className="mobile-drawer-handle" onClick={() => setShowMoreDrawer(false)}>
                    <div className="mobile-drawer-pill" />
                </div>

                {user && (
                    <div className="mobile-drawer-profile">
                        <div className="mobile-drawer-avatar">
                            {user?.user_metadata?.avatar_url ? (
                                <img src={user.user_metadata.avatar_url} alt="Profile" />
                            ) : (
                                getInitials(user?.user_metadata?.full_name || user?.email)
                            )}
                        </div>
                        <div>
                            <div className="mobile-drawer-name">{user?.user_metadata?.full_name || 'User'}</div>
                            <div className="mobile-drawer-email">{user?.email}</div>
                        </div>
                    </div>
                )}

                <div className="mobile-drawer-grid">
                    {NAV_ITEMS.filter(n => !['/'].includes(n.href)).map((item) => (
                        <Link
                            key={item.href}
                            href={item.href}
                            onClick={(e) => { handleNavClick(e, item); setShowMoreDrawer(false); }}
                            className={`mobile-drawer-item ${isActive(item.href) ? 'active' : ''}`}
                        >
                            <span className="mobile-drawer-item-icon">{item.icon}</span>
                            <span className="mobile-drawer-item-label">{item.label}</span>
                        </Link>
                    ))}
                    <Link href="/settings" className={`mobile-drawer-item ${isActive('/settings') ? 'active' : ''}`} onClick={() => setShowMoreDrawer(false)}>
                        <span className="mobile-drawer-item-icon"><SettingsIcon size={18} /></span>
                        <span className="mobile-drawer-item-label">Settings</span>
                    </Link>
                </div>

                {user ? (
                    <button className="mobile-drawer-signout" onClick={() => { handleSignOut(); setShowMoreDrawer(false); }}>
                        Sign Out
                    </button>
                ) : (
                    <Link href="/login" className="mobile-drawer-signin" onClick={() => setShowMoreDrawer(false)}>
                        Sign In / Create Account
                    </Link>
                )}
            </div>

            {/* ======================== DESKTOP SIDEBAR ======================== */}
            <aside className="sidebar">
                <Link href="/" className="sidebar-logo">
                    <img src="/logo.png" alt="PolicyEye Logo" className="sidebar-logo-icon" style={{ background: 'transparent', padding: 0, objectFit: 'contain' }} />
                    <div>
                        <div className="sidebar-logo-text">PolicyEye</div>
                        <div className="sidebar-logo-badge">INSURANCE PORTAL</div>
                    </div>
                </Link>

                <nav className="sidebar-nav">
                    <div className="sidebar-section-title">Navigation</div>
                    {NAV_ITEMS.map((item) => (
                        <Link
                            key={item.href}
                            href={item.href}
                            onClick={(e) => handleNavClick(e, item)}
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
                        <span className="nav-icon"><SettingsIcon size={18} /></span>
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
            </aside>

            {/* Login Required Popup — rendered outside sidebar so it works on mobile */}
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
                        animation: 'slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1)'
                    }} onClick={e => e.stopPropagation()}>
                        <div style={{ marginBottom: '16px', color: 'var(--primary-500)' }}><LockIcon size={48} /></div>
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
        </>
    );
}
