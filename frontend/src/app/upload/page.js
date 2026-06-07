'use client';

/**
 * Upload Policy Page — Premium UI with animated stepper,
 * drag-drop zone with cloud upload indicator, and result cards.
 */

import { useState, useRef } from 'react';
import { uploadPolicy, getApiKey } from '@/lib/api';

const PIPELINE_STEPS = [
    { key: 'upload', label: 'Upload PDF', icon: '📤', desc: 'Sending to cloud storage' },
    { key: 'extract', label: 'Extract Text', icon: '📖', desc: 'pdf_text_extractor + pdf_table_extractor' },
    { key: 'analyze', label: 'IRDAI Cross-Ref', icon: '⚖️', desc: 'irdai_regulation_lookup (semantic search)' },
    { key: 'validate', label: 'Validate Rules', icon: '✅', desc: 'rule_validator + compliance check' },
];

export default function UploadPage() {
    const [dragover, setDragover] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [currentStep, setCurrentStep] = useState(-1);
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');
    const [fileName, setFileName] = useState('');
    const fileRef = useRef(null);

    async function handleUpload(file) {
        if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
            setError('Please upload a PDF file.');
            return;
        }

        if (!getApiKey()) {
            setError('Please set your API key in Settings first.');
            return;
        }

        setUploading(true);
        setError('');
        setResult(null);
        setFileName(file.name);

        // Animate pipeline steps
        let step = 0;
        setCurrentStep(0);
        const stepTimer = setInterval(() => {
            step++;
            if (step < PIPELINE_STEPS.length) {
                setCurrentStep(step);
            } else {
                clearInterval(stepTimer);
            }
        }, 1200);

        try {
            const data = await uploadPolicy(file);
            clearInterval(stepTimer);
            setCurrentStep(PIPELINE_STEPS.length);
            setResult(data);
        } catch (e) {
            clearInterval(stepTimer);
            setError(e.message);
        }
        setUploading(false);
    }

    function onDrop(e) {
        e.preventDefault();
        setDragover(false);
        const file = e.dataTransfer.files[0];
        handleUpload(file);
    }

    return (
        <>
            <div className="page-header">
                <h1 className="page-title">Upload Policy</h1>
                <p className="page-subtitle">
                    Upload an insurance policy PDF — the Policy Agent extracts every rule, limit, and exclusion automatically
                </p>
            </div>

            {/* Upload Zone */}
            <div className="card" style={{ marginBottom: 24, overflow: 'hidden' }}>
                <div
                    onClick={() => !uploading && fileRef.current?.click()}
                    onDrop={onDrop}
                    onDragOver={(e) => { e.preventDefault(); setDragover(true); }}
                    onDragLeave={() => setDragover(false)}
                    style={{
                        padding: '48px 32px',
                        textAlign: 'center',
                        cursor: uploading ? 'wait' : 'pointer',
                        borderRadius: 'var(--radius-lg)',
                        border: `2px dashed ${dragover ? 'var(--primary-500)' : 'var(--gray-200)'}`,
                        background: dragover ? 'var(--primary-50)' : 'var(--gray-50)',
                        margin: 20,
                        transition: 'all 0.3s ease',
                    }}
                >
                    <input
                        ref={fileRef}
                        type="file"
                        accept=".pdf"
                        style={{ display: 'none' }}
                        onChange={(e) => handleUpload(e.target.files[0])}
                    />
                    {!uploading ? (
                        <>
                            <div style={{ fontSize: 48, marginBottom: 12, opacity: 0.8 }}>
                                {dragover ? '📂' : '☁️'}
                            </div>
                            <div style={{ fontWeight: 700, fontSize: 16, color: 'var(--navy-800)', marginBottom: 8 }}>
                                {dragover ? 'Drop your PDF here' : 'Drop your policy PDF here, or click to browse'}
                            </div>
                            <div style={{ fontSize: 13, color: 'var(--gray-400)' }}>
                                Supports Indian health insurance policy documents up to 20MB • Stored in Supabase Cloud
                            </div>
                        </>
                    ) : (
                        <>
                            <div style={{ fontSize: 48, marginBottom: 12 }}>⚙️</div>
                            <div style={{ fontWeight: 700, fontSize: 16, color: 'var(--primary-600)', marginBottom: 4 }}>
                                Processing {fileName}...
                            </div>
                            <div style={{ fontSize: 13, color: 'var(--gray-400)' }}>
                                Running the 4-tool Policy Agent pipeline
                            </div>
                        </>
                    )}
                </div>
            </div>

            {/* Pipeline Stepper (shows during upload) */}
            {(uploading || result) && (
                <div className="card" style={{ marginBottom: 24 }}>
                    <div className="card-header">
                        <h2 className="card-title">🔄 Agent Pipeline</h2>
                        {result && (
                            <span className="verdict-badge approved" style={{ fontSize: 11 }}>
                                ✅ Complete
                            </span>
                        )}
                    </div>
                    <div style={{ padding: '8px 20px 20px', display: 'flex', gap: 0 }}>
                        {PIPELINE_STEPS.map((step, i) => {
                            const isComplete = currentStep > i || result;
                            const isActive = currentStep === i && !result;
                            return (
                                <div key={step.key} style={{ flex: 1, position: 'relative' }}>
                                    {/* Connector line */}
                                    {i > 0 && (
                                        <div style={{
                                            position: 'absolute', left: 0, top: 20, height: 2, width: '50%',
                                            background: isComplete || isActive ? 'var(--primary-400)' : 'var(--gray-200)',
                                            transition: 'background 0.5s ease',
                                        }} />
                                    )}
                                    {i < PIPELINE_STEPS.length - 1 && (
                                        <div style={{
                                            position: 'absolute', right: 0, top: 20, height: 2, width: '50%',
                                            background: isComplete ? 'var(--primary-400)' : 'var(--gray-200)',
                                            transition: 'background 0.5s ease',
                                        }} />
                                    )}
                                    <div style={{ textAlign: 'center', position: 'relative', zIndex: 1 }}>
                                        <div style={{
                                            width: 40, height: 40, borderRadius: '50%', margin: '0 auto 8px',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            fontSize: 18,
                                            background: isComplete ? 'var(--primary-500)' : isActive ? 'var(--primary-100)' : 'var(--gray-100)',
                                            color: isComplete ? 'white' : 'inherit',
                                            border: isActive ? '2px solid var(--primary-400)' : '2px solid transparent',
                                            transition: 'all 0.4s ease',
                                            animation: isActive ? 'pulse 1.5s infinite' : 'none',
                                        }}>
                                            {isComplete ? '✓' : step.icon}
                                        </div>
                                        <div style={{
                                            fontWeight: 600, fontSize: 12,
                                            color: isComplete ? 'var(--primary-600)' : isActive ? 'var(--navy-800)' : 'var(--gray-400)',
                                        }}>
                                            {step.label}
                                        </div>
                                        <div style={{
                                            fontSize: 10, color: 'var(--gray-400)', marginTop: 2,
                                            maxWidth: 120, margin: '2px auto 0',
                                        }}>
                                            {step.desc}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* Error */}
            {error && (
                <div className="card" style={{
                    marginBottom: 24, padding: 16, borderLeft: '4px solid var(--red-500)',
                    background: 'var(--red-50)', color: 'var(--red-600)', fontWeight: 500, fontSize: 14
                }}>
                    ❌ {error}
                </div>
            )}

            {/* Result */}
            {result && (
                <div className="card" style={{ marginBottom: 24, overflow: 'hidden' }}>
                    <div style={{
                        padding: '24px 24px 0', display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                    }}>
                        <h2 style={{ fontSize: 20, fontWeight: 800, color: 'var(--navy-800)' }}>
                            ✅ Policy Extracted Successfully
                        </h2>
                        <span className="verdict-badge approved">Processed</span>
                    </div>

                    <div style={{
                        padding: 24, display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16
                    }}>
                        {[
                            { label: 'Policy ID', value: `#${result.policy_id}`, color: 'var(--primary-500)', bg: 'var(--primary-50)' },
                            { label: 'Insurer', value: result.insurer, color: 'var(--blue-600)', bg: 'var(--blue-50)' },
                            { label: 'Sum Insured', value: `₹${(result.sum_insured || 0).toLocaleString('en-IN')}`, color: 'var(--green-600)', bg: 'var(--green-50)' },
                            { label: 'Rules Extracted', value: result.rules_count, color: 'var(--amber-600)', bg: 'var(--amber-50)' },
                        ].map((item) => (
                            <div key={item.label} style={{
                                padding: 16, borderRadius: 'var(--radius-md)', background: item.bg,
                                border: `1px solid ${item.bg}`,
                            }}>
                                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--gray-500)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                    {item.label}
                                </div>
                                <div style={{ fontSize: 20, fontWeight: 800, color: item.color }}>
                                    {item.value}
                                </div>
                            </div>
                        ))}
                    </div>

                    <div style={{
                        padding: '0 24px 20px', fontSize: 13, color: 'var(--gray-500)'
                    }}>
                        {result.message}
                    </div>
                </div>
            )}

            {/* Info: What the Agent Does */}
            {!uploading && !result && (
                <div className="card">
                    <div className="card-header">
                        <h2 className="card-title">🤖 How the Policy Agent Works</h2>
                    </div>
                    <div style={{ padding: '4px 24px 24px' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16 }}>
                            {[
                                { icon: '📖', name: 'Text Extraction', desc: 'Reads every page of the PDF using PyMuPDF — extracts all text and metadata' },
                                { icon: '📊', name: 'Table Extraction', desc: 'Identifies and parses structured tables (room rent limits, sub-limits, copay schedules)' },
                                { icon: '⚖️', name: 'IRDAI Cross-Reference', desc: 'Semantic search against 49 embedded IRDAI regulations using pgvector' },
                                { icon: '✅', name: 'Rule Validation', desc: 'Checks extracted rules for compliance (waiting periods, moratorium, exclusions)' },
                            ].map((tool) => (
                                <div key={tool.name} style={{
                                    padding: 20, borderRadius: 'var(--radius-md)',
                                    background: 'var(--gray-50)', border: '1px solid var(--gray-100)',
                                    transition: 'all 0.2s ease',
                                }}>
                                    <div style={{ fontSize: 28, marginBottom: 8 }}>{tool.icon}</div>
                                    <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--navy-800)', marginBottom: 4 }}>
                                        {tool.name}
                                    </div>
                                    <div style={{ fontSize: 12, color: 'var(--gray-500)', lineHeight: 1.6 }}>
                                        {tool.desc}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
