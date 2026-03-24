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
    { label: 'History', icon: '📋', href: '/history' },
    { label: 'Audit Trail', icon: '🛡️', href: '/audit' },
];

export default function Sidebar() {
    const pathname = usePathname();

    return (
        <aside className="sidebar">
            <Link href="/" className="sidebar-logo">
                <div className="sidebar-logo-icon">🛡️</div>
                <div>
                    <div className="sidebar-logo-text">SecureShield</div>
                    <div className="sidebar-logo-badge">AGENTIC AI</div>
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
                <div className="sidebar-footer-text" style={{ marginTop: 16 }}>
                    SecureShield v2.0<br />
                    Agentic Insurance Engine<br />
                    12 Custom Tools • ReAct Pipeline
                </div>
            </div>
        </aside>
    );
}
