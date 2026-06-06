'use client';

/**
 * Dispute Claim Page
 * Trigger the Grievance Agent to generate PDF reports, formal letters,
 * and send grievance emails on behalf of the patient.
 */

import { useState, useEffect } from 'react';
import { disputeClaim, getHistory, getApiKey, getReportDownloadUrl } from '@/lib/api';

export default function DisputePage() {
    const [checks, setChecks] = useState([]);
    const [selectedCheck, setSelectedCheck] = useState(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');
    const [pipelineStep, setPipelineStep] = useState('');

    // Load recent eligibility checks
    useEffect(() => {
        if (getApiKey()) {
            getHistory(20)
                .then(d => setChecks(d.checks || []))
                .catch(() => { });
        }
    }, []);

    function selectCheck(check) {
        setSelectedCheck(check);
        setResult(null);
        setError('');
    }

    async function handleDispute() {
        if (!selectedCheck) {
            setError('Please select a claim to dispute.');
            return;
        }

        setError('');
        setResult(null);
        setLoading(true);

        // Pipeline step animation
        const steps = [
            '🔍 Analyzing verdict for compliance violations...',
            '📚 Searching IRDAI precedent rulings...',
            '✍️ Drafting formal grievance letter...',
            '📄 Generating professional PDF report...',
            '📧 Sending grievance to insurer GRO...',
        ];
        let stepI = 0;
        const stepTimer = setInterval(() => {
            setPipelineStep(steps[stepI] || steps[steps.length - 1]);
            stepI++;
            if (stepI >= steps.length) clearInterval(stepTimer);
        }, 1500);

        try {
            // Parse the stored check data from API response format
            let verdict = {};
            let caseInput = {};

            try {
                verdict = JSON.parse(selectedCheck.verdict_json || '{}');
            } catch { /* empty */ }

            try {
                caseInput = JSON.parse(selectedCheck.case_json || '{}');
            } catch { /* empty */ }

            const grievanceData = {
                policy_id: selectedCheck.policy_id || 0,
                check_id: selectedCheck.id || 0,
                verdict_summary: verdict.summary || '',
                overall_verdict: verdict.overall_verdict || 'PARTIAL',
                total_claimed: verdict.total_claimed || 0,
                total_eligible: verdict.total_eligible || 0,
                total_denied: verdict.total_denied || 0,
                coverage_percentage: verdict.coverage_percentage || 0,
                patient_name: caseInput.patient_name || 'Patient',
                patient_age: caseInput.patient_age || null,
                procedure: caseInput.procedure || '',
                hospital_name: caseInput.hospital_name || '',
                insurer: selectedCheck.insurer || '',
                policy_name: selectedCheck.policy_name || '',
                matched_rules: verdict.matched_rules || [],
                explanation: selectedCheck.explanation || '',
                suggestions: [],
            };

            const data = await disputeClaim(grievanceData);
            clearInterval(stepTimer);
            setResult(data);
        } catch (e) {
            clearInterval(stepTimer);
            setError(e.message);
        }
        setLoading(false);
        setPipelineStep('');
    }

    const verdictColor = (v) => {
        if (!v) return 'var(--gray-400)';
        const upper = v.toUpperCase();
        if (upper === 'APPROVED') return 'var(--green-500)';
        if (upper === 'DENIED') return 'var(--red-500)';
        return 'var(--amber-500)';
    };

    return (
        <>
            <div className="page-header">
                <h1 className="page-title">⚖️ Dispute Claim</h1>
                <p className="page-subtitle">
                    Select a denied or partially approved claim — the Grievance Agent will generate a
                    formal complaint letter, PDF report, and send it to the insurer
                </p>
            </div>

            {/* Step 1: Select a claim */}
            <div className="card" style={{ marginBottom: 24 }}>
                <div className="card-header">
                    <h2 className="card-title">📋 Select Claim to Dispute</h2>
                </div>

                {checks.length === 0 ? (
                    <div style={{ padding: 24, textAlign: 'center', color: 'var(--gray-400)' }}>
                        No eligibility checks found. Run a check first on the
                        <a href="/check" style={{ color: 'var(--teal-500)', marginLeft: 4 }}>Check Eligibility</a> page.
                    </div>
                ) : (
                    <div style={{ maxHeight: 300, overflowY: 'auto' }}>
                        {checks.map((check, i) => {
                            let verdict = {};
                            let caseInput = {};
                            try { verdict = JSON.parse(check.verdict_json || '{}'); } catch { /* empty */ }
                            try { caseInput = JSON.parse(check.case_json || '{}'); } catch { /* empty */ }

                            const isSelected = selectedCheck?.id === check.id;
                            const isApproved = (verdict.overall_verdict || '').toUpperCase() === 'APPROVED'
                                && (verdict.coverage_percentage || 0) >= 95;

                            return (
                                <div
                                    key={check.id || i}
                                    onClick={() => !isApproved && selectCheck(check)}
                                    style={{
                                        padding: '12px 16px',
                                        borderBottom: '1px solid var(--gray-100)',
                                        cursor: isApproved ? 'not-allowed' : 'pointer',
                                        opacity: isApproved ? 0.4 : 1,
                                        background: isSelected
                                            ? 'rgba(20, 184, 166, 0.06)'
                                            : 'transparent',
                                        borderLeft: isSelected ? '3px solid var(--teal-500)' : '3px solid transparent',
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        alignItems: 'center',
                                        transition: 'all 0.2s ease',
                                    }}
                                >
                                    <div>
                                        <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--navy-700)' }}>
                                            {caseInput.procedure || 'Unknown Procedure'}
                                        </div>
                                        <div style={{ fontSize: 12, color: 'var(--gray-500)', marginTop: 2 }}>
                                            {caseInput.patient_name || 'Patient'} •{' '}
                                            Policy #{check.policy_id} •{' '}
                                            {check.created_at ? new Date(check.created_at).toLocaleDateString() : ''}
                                        </div>
                                    </div>
                                    <div style={{ textAlign: 'right' }}>
                                        <div style={{
                                            fontWeight: 700,
                                            fontSize: 13,
                                            color: verdictColor(verdict.overall_verdict),
                                        }}>
                                            {verdict.overall_verdict || 'N/A'}
                                        </div>
                                        <div style={{ fontSize: 11, color: 'var(--gray-500)' }}>
                                            {(verdict.coverage_percentage || 0).toFixed(0)}% covered
                                        </div>
                                        {isApproved && (
                                            <div style={{ fontSize: 10, color: 'var(--gray-400)' }}>
                                                (Fully approved)
                                            </div>
                                        )}
                                        {verdict.requires_manual_review && (
                                            <div style={{ fontSize: 10, color: 'var(--red-500)', fontWeight: 700, marginTop: 4 }}>
                                                ⚠️ REVIEW REQD
                                            </div>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* Dispute Button */}
            {selectedCheck && (
                <div style={{ marginBottom: 24, display: 'flex', alignItems: 'center', gap: 16 }}>
                    <button
                        className="btn btn-primary btn-lg"
                        onClick={handleDispute}
                        disabled={loading}
                        style={{ background: 'linear-gradient(135deg, #e74c3c, #c0392b)' }}
                    >
                        {loading ? (
                            <><div className="spinner" /> Running Grievance Agent...</>
                        ) : (
                            <>🛡️ Generate Grievance Package</>
                        )}
                    </button>
                    {loading && pipelineStep && (
                        <span style={{ fontSize: 13, color: 'var(--amber-500)', fontWeight: 500 }}>
                            {pipelineStep}
                        </span>
                    )}
                </div>
            )}

            {/* Error */}
            {error && (
                <div className="toast error" style={{ position: 'relative', top: 0, right: 0, marginBottom: 24 }}>
                    ❌ {error}
                </div>
            )}

            {/* Results */}
            {result && (
                <div className="result-section">

                    {/* Compliance Violations */}
                    {result.compliance_violations && result.compliance_violations.length > 0 && (
                        <div className="card" style={{ marginBottom: 24, borderLeft: '4px solid var(--red-500)' }}>
                            <div className="card-header">
                                <h2 className="card-title">🚨 Compliance Violations Detected</h2>
                            </div>
                            <div style={{ padding: '0 16px 16px' }}>
                                {result.compliance_violations.map((v, i) => (
                                    <div key={i} style={{
                                        padding: '10px 14px',
                                        marginBottom: 8,
                                        background: 'rgba(239, 68, 68, 0.06)',
                                        borderRadius: 8,
                                        fontSize: 13,
                                        lineHeight: 1.5,
                                        color: 'var(--navy-700)',
                                    }}>
                                        ⚠️ {v}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Precedents */}
                    {result.precedents && result.precedents.length > 0 && (
                        <div className="card" style={{ marginBottom: 24 }}>
                            <div className="card-header">
                                <h2 className="card-title">📚 IRDAI Precedent Rulings</h2>
                            </div>
                            <div style={{ padding: '0 16px 16px' }}>
                                {result.precedents.map((p, i) => (
                                    <div key={i} style={{
                                        padding: '12px 14px',
                                        marginBottom: 8,
                                        background: 'rgba(20, 184, 166, 0.04)',
                                        borderRadius: 8,
                                        borderLeft: `3px solid ${p.relevance === 'high' ? 'var(--teal-500)' : 'var(--gray-300)'}`,
                                    }}>
                                        <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4, color: 'var(--navy-700)' }}>
                                            {p.title}
                                            <span style={{
                                                marginLeft: 8,
                                                fontSize: 10,
                                                padding: '2px 6px',
                                                borderRadius: 4,
                                                background: p.relevance === 'high' ? 'rgba(20,184,166,0.1)' : 'rgba(150,150,150,0.1)',
                                                color: p.relevance === 'high' ? 'var(--teal-600)' : 'var(--gray-500)',
                                            }}>
                                                {p.relevance}
                                            </span>
                                        </div>
                                        <div style={{ fontSize: 12, color: 'var(--gray-600)', lineHeight: 1.5 }}>
                                            {p.summary}
                                        </div>
                                        <div style={{ fontSize: 10, color: 'var(--gray-400)', marginTop: 4 }}>
                                            Source: {p.source}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Grievance Letter */}
                    {result.grievance_letter && (
                        <div className="card" style={{ marginBottom: 24 }}>
                            <div className="card-header">
                                <h2 className="card-title">✍️ Formal Grievance Letter</h2>
                                <button
                                    className="btn btn-secondary"
                                    style={{ fontSize: 12, padding: '6px 12px' }}
                                    onClick={() => {
                                        navigator.clipboard.writeText(result.grievance_letter);
                                    }}
                                >
                                    📋 Copy to Clipboard
                                </button>
                            </div>
                            <div style={{
                                padding: '20px',
                                background: 'var(--gray-50)',
                                borderRadius: 8,
                                margin: '0 16px 16px',
                                fontFamily: '"Georgia", serif',
                                fontSize: 13,
                                lineHeight: 1.8,
                                whiteSpace: 'pre-wrap',
                                color: 'var(--navy-700)',
                                maxHeight: 500,
                                overflowY: 'auto',
                                border: '1px solid var(--gray-200)',
                            }}>
                                {result.grievance_letter}
                            </div>
                        </div>
                    )}

                    {/* PDF + Email Status */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 24 }}>
                        {/* PDF Download */}
                        <div className="card">
                            <div className="card-header">
                                <h2 className="card-title">📄 PDF Report</h2>
                            </div>
                            <div style={{ padding: '16px', textAlign: 'center' }}>
                                <div style={{ fontSize: 48, marginBottom: 12 }}>📋</div>
                                <div style={{ fontWeight: 600, marginBottom: 8, color: 'var(--navy-700)' }}>
                                    {result.pdf_filename || 'Report Generated'}
                                </div>
                                {result.pdf_filename && (
                                    <a
                                        href={getReportDownloadUrl(result.pdf_filename)}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="btn btn-primary"
                                        style={{ display: 'inline-block', marginTop: 8 }}
                                    >
                                        ⬇️ Download PDF
                                    </a>
                                )}
                            </div>
                        </div>

                        {/* Email Status */}
                        <div className="card">
                            <div className="card-header">
                                <h2 className="card-title">📧 Email Status</h2>
                            </div>
                            {result.email_status && (
                                <div style={{ padding: '16px' }}>
                                    <div style={{
                                        display: 'inline-block',
                                        padding: '4px 12px',
                                        borderRadius: 20,
                                        fontSize: 12,
                                        fontWeight: 700,
                                        background: result.email_status.status === 'sent'
                                            ? 'rgba(34, 197, 94, 0.1)'
                                            : 'rgba(239, 68, 68, 0.1)',
                                        color: result.email_status.status === 'sent'
                                            ? 'var(--green-500)'
                                            : 'var(--red-500)',
                                        marginBottom: 12,
                                    }}>
                                        {result.email_status.status === 'sent' ? '✅ SENT' : '❌ FAILED'}
                                    </div>
                                    <div style={{ fontSize: 13, lineHeight: 2, color: 'var(--navy-700)' }}>
                                        <div><strong>Tracking ID:</strong> {result.email_status.tracking_id}</div>
                                        <div><strong>Recipient:</strong> {result.email_status.recipient}</div>
                                        <div><strong>Sent At:</strong> {result.email_status.sent_at}</div>
                                    </div>
                                    <div style={{
                                        marginTop: 12,
                                        padding: '10px 14px',
                                        background: 'rgba(20, 184, 166, 0.04)',
                                        borderRadius: 8,
                                        fontSize: 12,
                                        color: 'var(--gray-600)',
                                        lineHeight: 1.5,
                                        border: '1px solid var(--gray-100)',
                                    }}>
                                        {result.email_status.message}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Tools Used */}
                    {result.tools_used && result.tools_used.length > 0 && (
                        <div className="card" style={{ marginBottom: 24 }}>
                            <div className="card-header">
                                <h2 className="card-title">🔧 Agent Tools Invoked</h2>
                            </div>
                            <div style={{ padding: '12px 16px', display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                                {result.tools_used.map((tool, i) => (
                                    <span key={i} className="tool-tag" style={{
                                        padding: '6px 14px',
                                        fontSize: 12,
                                    }}>
                                        {i + 1}. {tool}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}

                </div>
            )}
        </>
    );
}
