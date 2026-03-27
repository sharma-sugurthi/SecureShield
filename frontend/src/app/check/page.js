'use client';

/**
 * Check Eligibility Page
 * The core workflow: submit patient case → run agentic pipeline → show verdict.
 */

import { useState, useEffect } from 'react';
import { checkEligibility, listPolicies, getApiKey } from '@/lib/api';
import CoverageRing from '@/components/CoverageRing';

const ROOM_TYPES = [
    { value: 'general', label: 'General Ward' },
    { value: 'semi_private', label: 'Semi-Private' },
    { value: 'private', label: 'Private Room' },
    { value: 'single_ac', label: 'Single AC' },
    { value: 'deluxe', label: 'Deluxe Room' },
    { value: 'suite', label: 'Suite' },
    { value: 'icu', label: 'ICU' },
];

const ADMISSION_TYPES = [
    { value: 'planned', label: 'Planned / Elective' },
    { value: 'emergency', label: 'Emergency / Accident' },
];

const INITIAL_FORM = {
    patient_name: '', patient_age: '', room_type: 'semi_private',
    room_cost_per_day: '', stay_duration_days: '', admission_type: 'planned',
    procedure: '', procedure_cost: '', pre_existing_conditions: '',
    hospital_name: '', city: '', total_claimed_amount: '',
};

export default function CheckPage() {
    const [form, setForm] = useState(INITIAL_FORM);
    const [policyId, setPolicyId] = useState('');
    const [policies, setPolicies] = useState([]);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');
    const [pipelineStep, setPipelineStep] = useState('');

    useEffect(() => {
        if (getApiKey()) {
            listPolicies().then(d => setPolicies(d.policies || [])).catch(() => { });
        }
    }, []);

    function updateField(field, value) {
        setForm(prev => ({ ...prev, [field]: value }));
    }

    async function handleSubmit(e) {
        e.preventDefault();
        setError('');
        setResult(null);

        if (!policyId) { setError('Please select a policy.'); return; }
        if (!form.procedure) { setError('Please enter the procedure.'); return; }
        if (!form.total_claimed_amount) { setError('Please enter the total claimed amount.'); return; }

        setLoading(true);

        // Simulate pipeline step updates
        const steps = [
            'Running medical_term_normalizer...',
            'Running icd_procedure_lookup...',
            'Running city_tier_classifier...',
            'Running hospital_cost_estimator...',
            'Running decision_engine...',
            'Running clause_explainer...',
            'Running savings_calculator...',
            'Generating explanation...',
        ];
        let stepI = 0;
        const stepTimer = setInterval(() => {
            setPipelineStep(steps[stepI] || steps[steps.length - 1]);
            stepI++;
            if (stepI >= steps.length) clearInterval(stepTimer);
        }, 800);

        try {
            const caseFacts = {
                ...form,
                patient_age: form.patient_age ? parseInt(form.patient_age) : undefined,
                room_cost_per_day: form.room_cost_per_day ? parseFloat(form.room_cost_per_day) : undefined,
                stay_duration_days: form.stay_duration_days ? parseInt(form.stay_duration_days) : undefined,
                procedure_cost: form.procedure_cost ? parseFloat(form.procedure_cost) : undefined,
                total_claimed_amount: parseFloat(form.total_claimed_amount),
                pre_existing_conditions: form.pre_existing_conditions
                    ? form.pre_existing_conditions.split(',').map(s => s.trim()).filter(Boolean)
                    : [],
            };

            const data = await checkEligibility(parseInt(policyId), caseFacts);
            clearInterval(stepTimer);
            setResult(data);
        } catch (e) {
            clearInterval(stepTimer);
            setError(e.message);
        }
        setLoading(false);
        setPipelineStep('');
    }

    const verdict = result?.verdict;

    return (
        <>
            <div className="page-header">
                <h1 className="page-title">Check Eligibility</h1>
                <p className="page-subtitle">
                    Enter patient case details — the agentic pipeline will analyze, decide, and explain
                </p>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit}>
                <div className="card" style={{ marginBottom: 24 }}>
                    <div className="card-header">
                        <h2 className="card-title">📋 Patient Case Details</h2>
                    </div>

                    <div className="form-grid">
                        {/* Row 1: Policy + Patient */}
                        <div className="form-group">
                            <label className="form-label">Policy *</label>
                            <select className="form-select" value={policyId} onChange={(e) => setPolicyId(e.target.value)}>
                                <option value="">Select policy...</option>
                                {policies.map(p => (
                                    <option key={p.id} value={p.id}>
                                        #{p.id} — {p.plan_name} ({p.insurer})
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div className="form-group">
                            <label className="form-label">Patient Name</label>
                            <input className="form-input" placeholder="e.g. Rajesh Kumar"
                                value={form.patient_name} onChange={e => updateField('patient_name', e.target.value)} />
                        </div>
                        <div className="form-group">
                            <label className="form-label">Age</label>
                            <input className="form-input" type="number" placeholder="e.g. 45"
                                value={form.patient_age} onChange={e => updateField('patient_age', e.target.value)} />
                        </div>

                        {/* Row 2: Room + Stay */}
                        <div className="form-group">
                            <label className="form-label">Room Type</label>
                            <select className="form-select" value={form.room_type}
                                onChange={e => updateField('room_type', e.target.value)}>
                                {ROOM_TYPES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                            </select>
                        </div>
                        <div className="form-group">
                            <label className="form-label">Room Cost/Day (₹)</label>
                            <input className="form-input" type="number" placeholder="e.g. 5000"
                                value={form.room_cost_per_day} onChange={e => updateField('room_cost_per_day', e.target.value)} />
                        </div>
                        <div className="form-group">
                            <label className="form-label">Stay Duration (days)</label>
                            <input className="form-input" type="number" placeholder="e.g. 3"
                                value={form.stay_duration_days} onChange={e => updateField('stay_duration_days', e.target.value)} />
                        </div>

                        {/* Row 3: Procedure */}
                        <div className="form-group">
                            <label className="form-label">Admission Type</label>
                            <select className="form-select" value={form.admission_type}
                                onChange={e => updateField('admission_type', e.target.value)}>
                                {ADMISSION_TYPES.map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
                            </select>
                        </div>
                        <div className="form-group">
                            <label className="form-label">Procedure / Diagnosis *</label>
                            <input className="form-input" placeholder="e.g. Appendectomy, CABG, knee replacement"
                                value={form.procedure} onChange={e => updateField('procedure', e.target.value)} />
                            <span className="form-hint">Medical abbreviations (CABG, PTCA, etc.) are auto-expanded</span>
                        </div>
                        <div className="form-group">
                            <label className="form-label">Procedure Cost (₹)</label>
                            <input className="form-input" type="number" placeholder="e.g. 75000"
                                value={form.procedure_cost} onChange={e => updateField('procedure_cost', e.target.value)} />
                        </div>

                        {/* Row 4: Location + Amount */}
                        <div className="form-group">
                            <label className="form-label">Hospital Name</label>
                            <input className="form-input" placeholder="e.g. Apollo Hospital"
                                value={form.hospital_name} onChange={e => updateField('hospital_name', e.target.value)} />
                        </div>
                        <div className="form-group">
                            <label className="form-label">City</label>
                            <input className="form-input" placeholder="e.g. Mumbai, Jaipur"
                                value={form.city} onChange={e => updateField('city', e.target.value)} />
                            <span className="form-hint">Auto-classified into IRDAI city tier</span>
                        </div>
                        <div className="form-group">
                            <label className="form-label">Total Claimed Amount (₹) *</label>
                            <input className="form-input" type="number" placeholder="e.g. 150000"
                                value={form.total_claimed_amount}
                                onChange={e => updateField('total_claimed_amount', e.target.value)} />
                        </div>

                        {/* Row 5: Conditions */}
                        <div className="form-group full-width">
                            <label className="form-label">Pre-existing Conditions</label>
                            <input className="form-input" placeholder="e.g. Diabetes, Hypertension (comma-separated)"
                                value={form.pre_existing_conditions}
                                onChange={e => updateField('pre_existing_conditions', e.target.value)} />
                        </div>
                    </div>

                    {/* Submit */}
                    <div style={{ marginTop: 24, display: 'flex', alignItems: 'center', gap: 16 }}>
                        <button type="submit" className="btn btn-primary btn-lg" disabled={loading}>
                            {loading ? (
                                <><div className="spinner" /> Running Pipeline...</>
                            ) : (
                                <>🔍 Run Eligibility Check</>
                            )}
                        </button>
                        {loading && pipelineStep && (
                            <span style={{ fontSize: 13, color: 'var(--teal-600)', fontWeight: 500 }}>
                                {pipelineStep}
                            </span>
                        )}
                    </div>
                </div>
            </form>

            {/* Error */}
            {error && (
                <div className="toast error" style={{ position: 'relative', top: 0, right: 0, marginBottom: 24 }}>
                    ❌ {error}
                </div>
            )}

            {/* Results */}
            {result && verdict && (
                <div className="result-section">
                    {/* Verdict Header */}
                    <div className="card" style={{ marginBottom: 24 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 32 }}>
                            <CoverageRing percentage={verdict.coverage_percentage} />
                            <div style={{ flex: 1 }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                                    <h2 style={{ fontSize: 24, fontWeight: 800 }}>Eligibility Verdict</h2>
                                    <span className={`verdict-badge ${verdict.overall_verdict}`}>
                                        {verdict.overall_verdict === 'approved' ? '✅' : verdict.overall_verdict === 'denied' ? '❌' : '⚠️'}
                                        {' '}{verdict.overall_verdict.toUpperCase()}
                                    </span>
                                </div>

                                <div className="amount-grid">
                                    <div className="amount-item">
                                        <div className="amount-value claimed">₹{(verdict.total_claimed || 0).toLocaleString('en-IN')}</div>
                                        <div className="amount-label">Total Claimed</div>
                                    </div>
                                    <div className="amount-item">
                                        <div className="amount-value eligible">₹{(verdict.total_eligible || 0).toLocaleString('en-IN')}</div>
                                        <div className="amount-label">Eligible Amount</div>
                                    </div>
                                    <div className="amount-item">
                                        <div className="amount-value denied">₹{(verdict.total_denied || 0).toLocaleString('en-IN')}</div>
                                        <div className="amount-label">Not Covered</div>
                                    </div>
                                </div>

                                <p style={{ fontSize: 14, color: 'var(--gray-500)' }}>{verdict.summary}</p>

                                <div style={{ marginTop: 16, display: 'flex', gap: 16, alignItems: 'center' }}>
                                    <div className="confidence-pill" style={{
                                        padding: '4px 12px',
                                        borderRadius: 20,
                                        fontSize: 12,
                                        fontWeight: 600,
                                        background: verdict.confidence_score >= 0.8 ? 'rgba(46, 204, 113, 0.1)' : 'rgba(243, 156, 18, 0.1)',
                                        color: verdict.confidence_score >= 0.8 ? '#2ecc71' : '#f39c12',
                                        border: `1px solid ${verdict.confidence_score >= 0.8 ? 'rgba(46, 204, 113, 0.2)' : 'rgba(243, 156, 18, 0.2)'}`
                                    }}>
                                        🛡️ Confidence: {(verdict.confidence_score * 100).toFixed(0)}%
                                    </div>
                                    {verdict.requires_manual_review && (
                                        <div className="warning-pill" style={{
                                            padding: '4px 12px',
                                            borderRadius: 20,
                                            fontSize: 12,
                                            fontWeight: 700,
                                            background: 'rgba(231, 76, 60, 0.15)',
                                            color: '#e74c3c',
                                            animation: 'pulse 2s infinite'
                                        }}>
                                            ⚠️ MANUAL REVIEW RECOMMENDED
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Rule Breakdown */}
                    {verdict.matched_rules && verdict.matched_rules.length > 0 && (
                        <div className="card" style={{ marginBottom: 24 }}>
                            <div className="card-header">
                                <h2 className="card-title">📜 Rule-by-Rule Breakdown</h2>
                            </div>
                            {verdict.matched_rules.map((rule, i) => (
                                <div key={i} className="rule-item">
                                    <div className={`rule-status ${rule.status}`}>
                                        {rule.status === 'passed' ? '✓' : rule.status === 'capped' ? '⚠' : '✗'}
                                    </div>
                                    <div className="rule-details">
                                        <div className="rule-category">{rule.rule_category?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</div>
                                        <div className="rule-reason">{rule.rule_condition}</div>
                                        {rule.clause_reference && (
                                            <div style={{ fontSize: 11, color: 'var(--gray-400)', marginTop: 2 }}>
                                                Ref: {rule.clause_reference}
                                            </div>
                                        )}
                                    </div>
                                    {rule.shortfall > 0 && (
                                        <div className="rule-amount shortfall">
                                            -₹{rule.shortfall.toLocaleString('en-IN')}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Explanation */}
                    <div className="card" style={{ marginBottom: 24 }}>
                        <div className="card-header">
                            <h2 className="card-title">💬 Patient-Friendly Explanation</h2>
                            <span style={{ fontSize: 12, color: 'var(--gray-400)' }}>
                                {result.insurer} — {result.policy_name}
                            </span>
                        </div>
                        <div className="explanation-box">
                            {result.explanation}
                        </div>
                        {result.suggestions && result.suggestions.length > 0 && (
                            <>
                                <h3 style={{ marginTop: 20, fontSize: 14, fontWeight: 700 }}>Actionable Suggestions</h3>
                                <ul className="suggestions-list">
                                    {result.suggestions.map((s, i) => <li key={i}>{s}</li>)}
                                </ul>
                            </>
                        )}
                    </div>
                </div>
            )}
        </>
    );
}
