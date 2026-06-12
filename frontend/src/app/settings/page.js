'use client';

import { useState, useEffect, useRef } from 'react';
import { supabase } from '@/lib/supabase';
import { getProfile, updateProfile } from '@/lib/api';

export default function SettingsPage() {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [savingProfile, setSavingProfile] = useState(false);
    const [profileMessage, setProfileMessage] = useState('');
    
    // Profile Fields
    const [fullName, setFullName] = useState('');
    const [phone, setPhone] = useState('');
    const [dob, setDob] = useState('');
    const [address, setAddress] = useState('');
    const [avatarBase64, setAvatarBase64] = useState(null);
    
    const fileInputRef = useRef(null);

    // Password Fields
    const [currentPassword, setCurrentPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [savingPassword, setSavingPassword] = useState(false);
    const [passwordMessage, setPasswordMessage] = useState({ text: '', type: '' });

    const [notifications, setNotifications] = useState(true);
    const [darkMode, setDarkMode] = useState(false);

    useEffect(() => {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark') {
            setDarkMode(true);
        }
        loadUser();
    }, []);

    async function loadUser() {
        const { data: { user } } = await supabase.auth.getUser();
        if (user) {
            setUser(user);
            
            // Try fetching from Postgres first
            const pgProfile = await getProfile();
            
            if (pgProfile && pgProfile.full_name) {
                setFullName(pgProfile.full_name || '');
                setPhone(pgProfile.phone || '');
                setDob(pgProfile.dob || '');
                setAddress(pgProfile.address || '');
                setAvatarBase64(pgProfile.avatar_base64 || null);
            } else {
                // Fallback to Supabase metadata if Postgres is empty
                setFullName(user.user_metadata?.full_name || '');
                setPhone(user.user_metadata?.phone || '');
                setDob(user.user_metadata?.dob || '');
                setAddress(user.user_metadata?.address || '');
                setAvatarBase64(user.user_metadata?.avatar_url || null);
            }
        }
        setLoading(false);
    }

    const handleImageUpload = (e) => {
        const file = e.target.files[0];
        if (!file) return;

        // Simple client-side compression & base64 encoding
        const reader = new FileReader();
        reader.onload = (event) => {
            const img = new Image();
            img.onload = () => {
                const canvas = document.createElement('canvas');
                const MAX_WIDTH = 200;
                const MAX_HEIGHT = 200;
                let width = img.width;
                let height = img.height;

                if (width > height) {
                    if (width > MAX_WIDTH) {
                        height *= MAX_WIDTH / width;
                        width = MAX_WIDTH;
                    }
                } else {
                    if (height > MAX_HEIGHT) {
                        width *= MAX_HEIGHT / height;
                        height = MAX_HEIGHT;
                    }
                }
                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, width, height);
                
                // Compress heavily to ensure it fits in user_metadata limits
                const dataUrl = canvas.toDataURL('image/jpeg', 0.6);
                setAvatarBase64(dataUrl);
            };
            img.src = event.target.result;
        };
        reader.readAsDataURL(file);
    };

    const handleSaveProfile = async () => {
        setSavingProfile(true);
        setProfileMessage('');
        try {
            // 1. Save to Supabase metadata for instant UI updates
            const { error } = await supabase.auth.updateUser({
                data: {
                    full_name: fullName,
                    phone: phone,
                    dob: dob,
                    address: address,
                    avatar_url: avatarBase64,
                }
            });
            if (error) throw error;
            
            // 2. Save to PostgreSQL for backend persistence
            await updateProfile({
                full_name: fullName,
                phone: phone,
                dob: dob,
                address: address,
                avatar_base64: avatarBase64,
            });

            setProfileMessage('Profile updated successfully!');
            setTimeout(() => setProfileMessage(''), 3000);
            
            // Refresh local session object
            const { data } = await supabase.auth.getSession();
            if (data.session) {
               setUser(data.session.user);
            }
        } catch (error) {
            setProfileMessage(`Error: ${error.message}`);
        }
        setSavingProfile(false);
    };

    const toggleDarkMode = (checked) => {
        setDarkMode(checked);
        if (checked) {
            document.documentElement.classList.add('dark');
            localStorage.setItem('theme', 'dark');
        } else {
            document.documentElement.classList.remove('dark');
            localStorage.setItem('theme', 'light');
        }
    };

    const handleChangePassword = async (e) => {
        e.preventDefault();
        setPasswordMessage({ text: '', type: '' });
        
        if (newPassword !== confirmPassword) {
            return setPasswordMessage({ text: 'New passwords do not match.', type: 'error' });
        }
        
        setSavingPassword(true);
        try {
            // Re-authenticate to verify current password
            const { error: signInError } = await supabase.auth.signInWithPassword({
                email: user.email,
                password: currentPassword
            });
            
            if (signInError) throw new Error('Current password is incorrect.');
            
            // Update to new password
            const { error: updateError } = await supabase.auth.updateUser({
                password: newPassword
            });
            
            if (updateError) throw updateError;
            
            setPasswordMessage({ text: 'Password changed successfully!', type: 'success' });
            setCurrentPassword('');
            setNewPassword('');
            setConfirmPassword('');
        } catch (error) {
            setPasswordMessage({ text: error.message, type: 'error' });
        }
        setSavingPassword(false);
    };

    if (loading) return <div style={{ padding: 40 }}>Loading...</div>;

    return (
        <div style={{ paddingBottom: 60 }}>
            <div className="page-header">
                <h1 className="page-title">Account Settings</h1>
                <p className="page-subtitle">Manage your personal profile and security preferences</p>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 32, maxWidth: 800 }}>
                
                {/* Profile Settings */}
                <div className="card">
                    <div className="card-header">
                        <h2 className="card-title">👤 Personal Profile</h2>
                    </div>
                    <div className="card-body">
                        
                        {/* Avatar Section */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: 24, marginBottom: 32 }}>
                            <div 
                                style={{ 
                                    width: 80, height: 80, borderRadius: '50%', background: 'var(--gray-100)', 
                                    display: 'flex', alignItems: 'center', justifyContent: 'center', 
                                    overflow: 'hidden', border: '1px solid var(--gray-200)', flexShrink: 0
                                }}
                            >
                                {avatarBase64 ? (
                                    <img src={avatarBase64} alt="Profile" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                                ) : (
                                    <span style={{ fontSize: 24, color: 'var(--gray-500)' }}>
                                        {fullName ? fullName.charAt(0).toUpperCase() : 'U'}
                                    </span>
                                )}
                            </div>
                            <div>
                                <button 
                                    onClick={() => fileInputRef.current?.click()}
                                    className="btn-secondary" 
                                    style={{ fontSize: 13, padding: '8px 16px', background: 'white' }}
                                >
                                    Change Photo
                                </button>
                                <p style={{ fontSize: 12, color: 'var(--gray-500)', marginTop: 8 }}>
                                    JPG, GIF or PNG.
                                </p>
                                <input 
                                    type="file" 
                                    ref={fileInputRef} 
                                    onChange={handleImageUpload} 
                                    accept="image/*" 
                                    style={{ display: 'none' }} 
                                />
                            </div>
                        </div>

                        {/* Profile Form */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
                            <div className="form-group">
                                <label className="form-label">Full Name</label>
                                <input className="form-input" type="text" value={fullName} onChange={e => setFullName(e.target.value)} placeholder="John Doe" />
                            </div>
                            <div className="form-group">
                                <label className="form-label">Email Address</label>
                                <input className="form-input" type="email" value={user?.email || ''} disabled style={{ background: 'var(--gray-50)', color: 'var(--gray-500)' }} />
                            </div>
                            <div className="form-group">
                                <label className="form-label">Phone Number</label>
                                <input className="form-input" type="tel" value={phone} onChange={e => setPhone(e.target.value)} placeholder="+91 98765 43210" />
                            </div>
                            <div className="form-group">
                                <label className="form-label">Date of Birth</label>
                                <input className="form-input" type="date" value={dob} onChange={e => setDob(e.target.value)} />
                            </div>
                            <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                                <label className="form-label">Address</label>
                                <textarea className="form-input" rows="3" value={address} onChange={e => setAddress(e.target.value)} placeholder="Enter your full address"></textarea>
                            </div>
                        </div>
                        
                        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 24, paddingTop: 24, borderTop: '1px solid var(--gray-100)' }}>
                            <button onClick={handleSaveProfile} disabled={savingProfile} className="btn-primary">
                                {savingProfile ? 'Saving...' : 'Save Profile'}
                            </button>
                            {profileMessage && (
                                <span style={{ fontSize: 13, color: profileMessage.includes('Error') ? 'var(--red-600)' : 'var(--green-600)' }}>
                                    {profileMessage}
                                </span>
                            )}
                        </div>
                    </div>
                </div>

                {/* Security Settings */}
                <div className="card">
                    <div className="card-header">
                        <h2 className="card-title">🔒 Security Settings</h2>
                    </div>
                    <div className="card-body">
                        <form onSubmit={handleChangePassword} style={{ display: 'flex', flexDirection: 'column', gap: 20, maxWidth: 400 }}>
                            <div className="form-group">
                                <label className="form-label">Current Password</label>
                                <input 
                                    className="form-input" 
                                    type="password" 
                                    value={currentPassword} 
                                    onChange={e => setCurrentPassword(e.target.value)} 
                                    required 
                                />
                            </div>
                            <div className="form-group">
                                <label className="form-label">New Password</label>
                                <input 
                                    className="form-input" 
                                    type="password" 
                                    value={newPassword} 
                                    onChange={e => setNewPassword(e.target.value)} 
                                    required 
                                    minLength="6"
                                />
                            </div>
                            <div className="form-group">
                                <label className="form-label">Confirm New Password</label>
                                <input 
                                    className="form-input" 
                                    type="password" 
                                    value={confirmPassword} 
                                    onChange={e => setConfirmPassword(e.target.value)} 
                                    required 
                                />
                            </div>
                            
                            <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 8 }}>
                                <button type="submit" disabled={savingPassword} className="btn-primary">
                                    {savingPassword ? 'Updating...' : 'Change Password'}
                                </button>
                                {passwordMessage.text && (
                                    <span style={{ fontSize: 13, color: passwordMessage.type === 'error' ? 'var(--red-600)' : 'var(--green-600)' }}>
                                        {passwordMessage.text}
                                    </span>
                                )}
                            </div>
                        </form>
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
                                    onChange={(e) => toggleDarkMode(e.target.checked)} 
                                    style={{ width: 20, height: 20 }}
                                />
                            </label>
                        </div>
                    </div>
                </div>

            </div>
        </div>
    );
}
