'use client';

/**
 * Audit Trail Page
 * Displays every agent action, tool call, and decision with full traceability.
 * This is a key differentiator for the agentic architecture.
 */

import { useState, useEffect } from 'react';
import { getAuditTrail, getApiKey } from '@/lib/api';

export default function AuditPage() {
    const [trail, setTrail] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('all');

    useEffect(() => {
        loadTrail();
    }, []);

    async function loadTrail() {
        setLoading(true);
        if (!getApiKey()) {
            setLoading(false);
            return;
        }
        try {
            const data = await getAuditTrail(100);
            setTrail(data.audit_trail || []);
        } catch (e) { /* no auth */ }
        setLoading(false);
    }

    const agents = [...new Set(trail.map(e => e.agent_name))];
    const filtered = filter === 'all' ? trail : trail.filter(e => e.agent_name === filter);

    return (
        <>
            <div className="page-header">
                <h1 className="page-title">Audit Trail</h1>
                <p className="page-subtitle">
                    Full traceability of every agent action, tool call, and decision — compliance-ready
                </p>
            </div>

            {/* Filter */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
                <button className={`btn ${filter === 'all' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setFilter('all')} style={{ padding: '8px 16px', fontSize: 13 }}>
                    All ({trail.length})
                </button>
                {agents.map(a => (
                    <button key={a}
                        className={`btn ${filter === a ? 'btn-primary' : 'btn-secondary'}`}
                        onClick={() => setFilter(a)}
                        style={{ padding: '8px 16px', fontSize: 13 }}>
                        {a} ({trail.filter(e => e.agent_name === a).length})
                    </button>
                ))}
            </div>

            <div className="card">
                {loading ? (
                    <div className="loading-overlay">
                        <div className="spinner" />
                        <div className="loading-text">Loading audit trail...</div>
                    </div>
                ) : filtered.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-state-icon">🛡️</div>
                        <div className="empty-state-text">No audit entries yet</div>
                        <div className="empty-state-hint">
                            {getApiKey()
                                ? 'Run an eligibility check to see the agent audit trail.'
                                : 'Set your API key in Settings first.'}
                        </div>
                    </div>
                ) : (
                    <div className="timeline">
                        {filtered.map((entry, i) => (
                            <div key={i} className="timeline-item">
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                    <div>
                                        <div className="timeline-agent">{entry.agent_name}</div>
                                        <div className="timeline-action">
                                            <strong>{entry.action}</strong>
                                        </div>
                                    </div>
                                    <span className={`verdict-badge ${entry.status === 'success' ? 'approved' : entry.status === 'failure' ? 'denied' : 'partial'}`}
                                        style={{ fontSize: 11 }}>
                                        {entry.status || 'success'}
                                    </span>
                                </div>

                                {entry.input_summary && (
                                    <div style={{ fontSize: 12, color: 'var(--gray-500)', marginTop: 8 }}>
                                        <strong>Input:</strong> {entry.input_summary}
                                    </div>
                                )}
                                {entry.output_summary && (
                                    <div style={{ fontSize: 12, color: 'var(--navy-700)', marginTop: 4 }}>
                                        <strong>Output:</strong> {entry.output_summary}
                                    </div>
                                )}

                                {entry.tools_used && entry.tools_used.length > 0 && (
                                    <div className="timeline-tools">
                                        {entry.tools_used.map((tool, j) => (
                                            <span key={j} className="tool-tag">{tool}</span>
                                        ))}
                                    </div>
                                )}

                                <div className="timeline-time">
                                    {entry.duration_ms ? `${entry.duration_ms.toFixed(0)}ms` : ''}
                                    {entry.timestamp && ` • ${new Date(entry.timestamp).toLocaleString()}`}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </>
    );
}
