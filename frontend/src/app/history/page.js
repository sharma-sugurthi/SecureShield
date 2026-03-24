'use client';

/**
 * History Page
 * View past eligibility checks with verdict summaries.
 */

import { useState, useEffect } from 'react';
import { getHistory, getApiKey } from '@/lib/api';

export default function HistoryPage() {
    const [checks, setChecks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [expanded, setExpanded] = useState(null);

    useEffect(() => {
        loadHistory();
    }, []);

    async function loadHistory() {
        setLoading(true);
        if (!getApiKey()) {
            setLoading(false);
            return;
        }
        try {
            const data = await getHistory(50);
            setChecks(data.checks || []);
        } catch (e) { /* no auth */ }
        setLoading(false);
    }

    function parseVerdict(json) {
        try { return JSON.parse(json); } catch { return null; }
    }

    return (
        <>
            <div className="page-header">
                <h1 className="page-title">Eligibility History</h1>
                <p className="page-subtitle">View past eligibility checks and their outcomes</p>
            </div>

            <div className="card">
                {loading ? (
                    <div className="loading-overlay">
                        <div className="spinner" />
                        <div className="loading-text">Loading history...</div>
                    </div>
                ) : checks.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-state-icon">📋</div>
                        <div className="empty-state-text">No eligibility checks yet</div>
                        <div className="empty-state-hint">
                            {getApiKey()
                                ? 'Run your first eligibility check to see results here.'
                                : 'Set your API key in Settings first.'}
                        </div>
                    </div>
                ) : (
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Policy</th>
                                <th>Verdict</th>
                                <th>Coverage</th>
                                <th>Claimed</th>
                                <th>Eligible</th>
                                <th>Date</th>
                            </tr>
                        </thead>
                        <tbody>
                            {checks.map((check) => {
                                const v = parseVerdict(check.verdict_json);
                                return (
                                    <tr key={check.id} onClick={() => setExpanded(expanded === check.id ? null : check.id)}
                                        style={{ cursor: 'pointer' }}>
                                        <td style={{ fontWeight: 600 }}>#{check.id}</td>
                                        <td>Policy #{check.policy_id}</td>
                                        <td>
                                            {v && (
                                                <span className={`verdict-badge ${v.overall_verdict}`}>
                                                    {v.overall_verdict?.toUpperCase()}
                                                </span>
                                            )}
                                        </td>
                                        <td style={{ fontWeight: 600 }}>{v?.coverage_percentage || 0}%</td>
                                        <td>₹{(v?.total_claimed || 0).toLocaleString('en-IN')}</td>
                                        <td style={{ color: 'var(--green-500)', fontWeight: 600 }}>
                                            ₹{(v?.total_eligible || 0).toLocaleString('en-IN')}
                                        </td>
                                        <td style={{ fontSize: 12, color: 'var(--gray-400)' }}>
                                            {check.created_at ? new Date(check.created_at).toLocaleString() : 'N/A'}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Expanded Detail */}
            {expanded && (() => {
                const check = checks.find(c => c.id === expanded);
                if (!check) return null;
                return (
                    <div className="card result-section" style={{ marginTop: 24 }}>
                        <div className="card-header">
                            <h2 className="card-title">Explanation — Check #{check.id}</h2>
                            <button className="btn btn-secondary" onClick={() => setExpanded(null)}>Close</button>
                        </div>
                        <div className="explanation-box">{check.explanation || 'No explanation available.'}</div>
                    </div>
                );
            })()}
        </>
    );
}
