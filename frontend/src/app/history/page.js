'use client';

/**
 * History Page — Premium card-based history view
 * with pastel verdict badges, expandable detail panels,
 * and animated transitions.
 */

import { useState, useEffect } from 'react';
import { getHistory, getApiKey } from '@/lib/api';

const VERDICT_CONFIG = {
    approved: { emoji: '✅', label: 'Approved', color: 'var(--green-600)', bg: 'var(--green-50)', border: 'var(--green-100)' },
    denied: { emoji: '❌', label: 'Denied', color: 'var(--red-600)', bg: 'var(--red-50)', border: 'var(--red-100)' },
    partial: { emoji: '⚠️', label: 'Partial', color: 'var(--amber-600)', bg: 'var(--amber-50)', border: 'var(--amber-100)' },
};

export default function HistoryPage() {
    const [checks, setChecks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [expanded, setExpanded] = useState(null);
    const [filter, setFilter] = useState('all');

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

    const filteredChecks = filter === 'all'
        ? checks
        : checks.filter(c => {
            const v = parseVerdict(c.verdict_json);
            return v?.overall_verdict?.toLowerCase() === filter;
        });

    const stats = {
        total: checks.length,
        approved: checks.filter(c => parseVerdict(c.verdict_json)?.overall_verdict === 'approved').length,
        denied: checks.filter(c => parseVerdict(c.verdict_json)?.overall_verdict === 'denied').length,
        partial: checks.filter(c => {
            const v = parseVerdict(c.verdict_json)?.overall_verdict;
            return v && v !== 'approved' && v !== 'denied';
        }).length,
    };

    return (
        <>
            <div className="page-header">
                <h1 className="page-title">Eligibility History</h1>
                <p className="page-subtitle">Review past eligibility checks, verdicts, and coverage breakdowns</p>
            </div>

            {/* Summary Stats */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
                {[
                    { label: 'Total Checks', value: stats.total, icon: '📋', color: 'var(--primary-500)', bg: 'var(--primary-50)' },
                    { label: 'Approved', value: stats.approved, icon: '✅', color: 'var(--green-600)', bg: 'var(--green-50)' },
                    { label: 'Denied', value: stats.denied, icon: '❌', color: 'var(--red-600)', bg: 'var(--red-50)' },
                    { label: 'Partial', value: stats.partial, icon: '⚠️', color: 'var(--amber-600)', bg: 'var(--amber-50)' },
                ].map((stat) => (
                    <div key={stat.label} className="card" style={{
                        padding: 20, display: 'flex', alignItems: 'center', gap: 16, cursor: 'pointer',
                        border: filter === stat.label.toLowerCase() ? `2px solid ${stat.color}` : undefined,
                    }} onClick={() => setFilter(
                        stat.label === 'Total Checks' ? 'all' : stat.label.toLowerCase()
                    )}>
                        <div style={{
                            width: 44, height: 44, borderRadius: 'var(--radius-md)',
                            background: stat.bg, display: 'flex', alignItems: 'center',
                            justifyContent: 'center', fontSize: 20, flexShrink: 0,
                        }}>
                            {stat.icon}
                        </div>
                        <div>
                            <div style={{ fontSize: 24, fontWeight: 800, color: stat.color }}>{stat.value}</div>
                            <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--gray-500)' }}>{stat.label}</div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Filter Bar */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
                {['all', 'approved', 'denied', 'partial'].map((f) => (
                    <button
                        key={f}
                        onClick={() => setFilter(f)}
                        style={{
                            padding: '6px 16px', borderRadius: 100, fontSize: 12, fontWeight: 600,
                            border: '1px solid', cursor: 'pointer', transition: 'all 0.2s',
                            background: filter === f ? 'var(--primary-500)' : 'var(--white)',
                            color: filter === f ? 'white' : 'var(--gray-500)',
                            borderColor: filter === f ? 'var(--primary-500)' : 'var(--gray-200)',
                        }}
                    >
                        {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)} ({
                            f === 'all' ? stats.total : stats[f] || 0
                        })
                    </button>
                ))}
            </div>

            {/* Content */}
            <div className="card">
                {loading ? (
                    <div className="loading-overlay">
                        <div className="spinner" />
                        <div className="loading-text">Loading history...</div>
                    </div>
                ) : filteredChecks.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-state-icon">📋</div>
                        <div className="empty-state-text">
                            {filter !== 'all' ? `No ${filter} checks found` : 'No eligibility checks yet'}
                        </div>
                        <div className="empty-state-hint">
                            {getApiKey()
                                ? 'Run your first eligibility check to see results here.'
                                : 'Set your API key in Settings first.'}
                        </div>
                    </div>
                ) : (
                    <div>
                        {filteredChecks.map((check, idx) => {
                            const v = parseVerdict(check.verdict_json);
                            const vKey = v?.overall_verdict?.toLowerCase() || 'partial';
                            const config = VERDICT_CONFIG[vKey] || VERDICT_CONFIG.partial;
                            const isExpanded = expanded === check.id;
                            let caseInput = {};
                            try { caseInput = JSON.parse(check.case_json || '{}'); } catch { }

                            return (
                                <div key={check.id || idx}>
                                    <div
                                        onClick={() => setExpanded(isExpanded ? null : check.id)}
                                        style={{
                                            padding: '16px 24px',
                                            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                            cursor: 'pointer',
                                            borderBottom: '1px solid var(--gray-100)',
                                            background: isExpanded ? 'var(--gray-50)' : 'transparent',
                                            transition: 'background 0.2s ease',
                                        }}
                                    >
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                                            <div style={{
                                                width: 40, height: 40, borderRadius: '50%',
                                                background: config.bg, display: 'flex', alignItems: 'center',
                                                justifyContent: 'center', fontSize: 16, flexShrink: 0,
                                                border: `1px solid ${config.border}`,
                                            }}>
                                                {config.emoji}
                                            </div>
                                            <div>
                                                <div style={{ fontWeight: 600, color: 'var(--navy-800)', fontSize: 14 }}>
                                                    {caseInput.procedure || `Check #${check.id}`}
                                                </div>
                                                <div style={{ fontSize: 12, color: 'var(--gray-500)', marginTop: 2 }}>
                                                    {caseInput.patient_name || 'Patient'} • Policy #{check.policy_id} •{' '}
                                                    {check.created_at ? new Date(check.created_at).toLocaleDateString() : ''}
                                                </div>
                                            </div>
                                        </div>

                                        <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
                                            <div style={{ textAlign: 'right' }}>
                                                <div style={{
                                                    fontWeight: 700, fontSize: 15, color: 'var(--green-600)',
                                                }}>
                                                    ₹{(v?.total_eligible || 0).toLocaleString('en-IN')}
                                                </div>
                                                <div style={{ fontSize: 11, color: 'var(--gray-400)' }}>
                                                    of ₹{(v?.total_claimed || 0).toLocaleString('en-IN')} claimed
                                                </div>
                                            </div>

                                            <div style={{
                                                padding: '4px 12px', borderRadius: 100, fontSize: 11, fontWeight: 700,
                                                background: config.bg, color: config.color,
                                                border: `1px solid ${config.border}`,
                                            }}>
                                                {v?.coverage_percentage || 0}% • {config.label}
                                            </div>

                                            <div style={{
                                                color: 'var(--gray-400)', fontSize: 12,
                                                transform: isExpanded ? 'rotate(180deg)' : 'rotate(0)',
                                                transition: 'transform 0.2s ease',
                                            }}>
                                                ▼
                                            </div>
                                        </div>
                                    </div>

                                    {/* Expanded Detail */}
                                    {isExpanded && (
                                        <div style={{
                                            padding: '20px 24px', background: 'var(--gray-50)',
                                            borderBottom: '1px solid var(--gray-100)',
                                        }}>
                                            <div style={{ fontWeight: 700, fontSize: 13, color: 'var(--navy-700)', marginBottom: 12 }}>
                                                Patient Explanation
                                            </div>
                                            <div className="explanation-box" style={{
                                                background: 'var(--white)', margin: 0,
                                                borderRadius: 'var(--radius-md)', padding: 16,
                                            }}>
                                                {check.explanation || 'No explanation available.'}
                                            </div>

                                            {v?.matched_rules && v.matched_rules.length > 0 && (
                                                <div style={{ marginTop: 16 }}>
                                                    <div style={{ fontWeight: 700, fontSize: 13, color: 'var(--navy-700)', marginBottom: 8 }}>
                                                        Matched Rules ({v.matched_rules.length})
                                                    </div>
                                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                                                        {v.matched_rules.map((rule, ri) => (
                                                            <span key={ri} style={{
                                                                padding: '3px 10px', borderRadius: 100, fontSize: 11,
                                                                fontWeight: 500,
                                                                background: rule.status === 'passed' ? 'var(--green-50)' : rule.status === 'capped' ? 'var(--amber-50)' : 'var(--red-50)',
                                                                color: rule.status === 'passed' ? 'var(--green-600)' : rule.status === 'capped' ? 'var(--amber-600)' : 'var(--red-600)',
                                                                border: `1px solid ${rule.status === 'passed' ? 'var(--green-100)' : rule.status === 'capped' ? 'var(--amber-100)' : 'var(--red-100)'}`,
                                                            }}>
                                                                {rule.status === 'passed' ? '✓' : rule.status === 'capped' ? '⚠' : '✗'}{' '}
                                                                {rule.rule_category?.replace(/_/g, ' ')}
                                                                {rule.shortfall > 0 && ` (-₹${rule.shortfall.toLocaleString('en-IN')})`}
                                                            </span>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </>
    );
}
