'use client';

/**
 * Settings Page
 * API key configuration and connection status.
 */

import { useState, useEffect } from 'react';
import { getApiKey, setApiKey, healthCheck } from '@/lib/api';

export default function SettingsPage() {
    const [key, setKey] = useState('');
    const [saved, setSaved] = useState(false);
    const [status, setStatus] = useState(null);
    const [checking, setChecking] = useState(false);

    useEffect(() => {
        setKey(getApiKey());
    }, []);

    function handleSave() {
        setApiKey(key);
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
    }

    async function testConnection() {
        setChecking(true);
        setStatus(null);
        try {
            const data = await healthCheck();
            setStatus({ ok: true, data });
        } catch (e) {
            setStatus({ ok: false, error: e.message });
        }
        setChecking(false);
    }

    return (
        <>
            <div className="page-header">
                <h1 className="page-title">Settings</h1>
                <p className="page-subtitle">Configure your connection to the SecureShield backend</p>
            </div>

            {/* API Key */}
            <div className="card" style={{ marginBottom: 24 }}>
                <div className="card-header">
                    <h2 className="card-title">🔑 API Key</h2>
                </div>
                <div className="form-group" style={{ maxWidth: 600 }}>
                    <label className="form-label">Backend API Key</label>
                    <input
                        className="form-input"
                        type="password"
                        placeholder="Enter your API key (shown in backend console on startup)"
                        value={key}
                        onChange={(e) => setKey(e.target.value)}
                    />
                    <span className="form-hint">
                        The master API key is printed when the backend starts. Look for &quot;🔑 Master API Key:&quot; in the console.
                    </span>
                </div>
                <div style={{ marginTop: 16, display: 'flex', gap: 12, alignItems: 'center' }}>
                    <button className="btn btn-primary" onClick={handleSave}>
                        💾 Save Key
                    </button>
                    <button className="btn btn-secondary" onClick={testConnection} disabled={checking}>
                        {checking ? <><div className="spinner" /> Testing...</> : '🔌 Test Connection'}
                    </button>
                    {saved && <span style={{ color: 'var(--green-500)', fontWeight: 600, fontSize: 14 }}>✅ Saved!</span>}
                </div>
            </div>

            {/* Connection Status */}
            {status && (
                <div className="card result-section">
                    <div className="card-header">
                        <h2 className="card-title">
                            {status.ok ? '🟢 Connection Successful' : '🔴 Connection Failed'}
                        </h2>
                    </div>
                    {status.ok ? (
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
                            <div>
                                <div className="form-label">Status</div>
                                <div style={{ fontWeight: 700, color: 'var(--green-500)' }}>{status.data.status}</div>
                            </div>
                            <div>
                                <div className="form-label">App</div>
                                <div style={{ fontWeight: 700 }}>{status.data.app}</div>
                            </div>
                            <div>
                                <div className="form-label">Version</div>
                                <div style={{ fontWeight: 700 }}>{status.data.version}</div>
                            </div>
                        </div>
                    ) : (
                        <p style={{ color: 'var(--red-500)' }}>Error: {status.error}</p>
                    )}
                </div>
            )}

            {/* Backend Info */}
            <div className="card" style={{ marginTop: 24 }}>
                <div className="card-header">
                    <h2 className="card-title">ℹ️ System Information</h2>
                </div>
                <table className="data-table">
                    <tbody>
                        <tr><td style={{ fontWeight: 600 }}>Backend URL</td><td>http://localhost:8000</td></tr>
                        <tr><td style={{ fontWeight: 600 }}>Architecture</td><td>Agentic AI (ReAct Pattern)</td></tr>
                        <tr><td style={{ fontWeight: 600 }}>Custom Tools</td><td>12 tools across 4 modules</td></tr>
                        <tr><td style={{ fontWeight: 600 }}>Agents</td><td>Policy Agent, Case Agent, Decision Engine, Explanation Agent</td></tr>
                        <tr><td style={{ fontWeight: 600 }}>Knowledge Bases</td><td>IRDAI Regulations, ICD-10 Procedures, Indian City Tiers</td></tr>
                        <tr><td style={{ fontWeight: 600 }}>Decision Mode</td><td>Deterministic (no LLM in decision engine)</td></tr>
                        <tr><td style={{ fontWeight: 600 }}>Tests</td><td>76 passing (decision engine + security + tools)</td></tr>
                    </tbody>
                </table>
            </div>
        </>
    );
}
