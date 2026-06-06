'use client';

/**
 * Sidebar Component
 * Premium navigation sidebar with active page highlighting.
 */

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV_ITEMS = [
    { label: 'Dashboard', icon: '📊', href: '/' },
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
                
                <div className="sidebar-profile" style={{ marginTop: 24 }}>
                    <div className="avatar">JD</div>
                    <div className="profile-info">
                        <span className="profile-name">John Doe</span>
                        <span className="profile-role">Patient ID: #90412</span>
                    </div>
                </div>
            </div>
        </aside>
    );
}
