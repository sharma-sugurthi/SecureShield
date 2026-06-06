'use client';

/**
 * Settings Page
 * Patient preferences and account settings.
 */

import { useState } from 'react';

export default function SettingsPage() {
    const [notifications, setNotifications] = useState(true);
    const [darkMode, setDarkMode] = useState(false);

    return (
        <>
            <div className="page-header">
                <h1 className="page-title">Account Preferences</h1>
                <p className="page-subtitle">Manage your portal settings and notifications</p>
            </div>

            {/* Profile Settings */}
            <div className="card" style={{ marginBottom: 24 }}>
                <div className="card-header">
                    <h2 className="card-title">👤 Personal Information</h2>
                </div>
                <div className="card-body">
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, maxWidth: 600 }}>
                        <div className="form-group">
                            <label className="form-label">Full Name</label>
                            <input className="form-input" type="text" defaultValue="John Doe" disabled />
                        </div>
                        <div className="form-group">
                            <label className="form-label">Email Address</label>
                            <input className="form-input" type="email" defaultValue="patient@example.com" disabled />
                        </div>
                    </div>
                    <p style={{ fontSize: 13, color: 'var(--gray-500)', marginTop: 12 }}>
                        Please contact your administrator to update personal information.
                    </p>
                </div>
            </div>

            {/* Application Preferences */}
            <div className="card">
                <div className="card-header">
                    <h2 className="card-title">⚙️ Preferences</h2>
                </div>
                <div className="card-body">
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 400 }}>
                        <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}>
                            <div>
                                <div style={{ fontWeight: 600 }}>Email Notifications</div>
                                <div style={{ fontSize: 13, color: 'var(--gray-500)' }}>Receive updates on claim status</div>
                            </div>
                            <input 
                                type="checkbox" 
                                checked={notifications} 
                                onChange={(e) => setNotifications(e.target.checked)} 
                                style={{ width: 20, height: 20 }}
                            />
                        </label>
                        
                        <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}>
                            <div>
                                <div style={{ fontWeight: 600 }}>Dark Mode</div>
                                <div style={{ fontSize: 13, color: 'var(--gray-500)' }}>Use dark theme across the portal</div>
                            </div>
                            <input 
                                type="checkbox" 
                                checked={darkMode} 
                                onChange={(e) => setDarkMode(e.target.checked)} 
                                style={{ width: 20, height: 20 }}
                            />
                        </label>
                    </div>
                </div>
            </div>
        </>
    );
}
