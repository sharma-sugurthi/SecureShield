'use client';

/**
 * Upload Policy Page
 * Drag-and-drop PDF upload with extraction results display.
 */

import { useState, useRef } from 'react';
import { uploadPolicy, getApiKey } from '@/lib/api';

export default function UploadPage() {
    const [dragover, setDragover] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');
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

        try {
            const data = await uploadPolicy(file);
            setResult(data);
        } catch (e) {
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

    function onDragOver(e) {
        e.preventDefault();
        setDragover(true);
    }

    return (
        <>
            <div className="page-header">
                <h1 className="page-title">Upload Policy</h1>
                <p className="page-subtitle">
                    Upload an insurance policy PDF — the Policy Agent will extract rules using 4 custom tools
                </p>
            </div>

            {/* Upload Zone */}
            <div className="card" style={{ marginBottom: 24 }}>
                <div
                    className={`upload-zone ${dragover ? 'dragover' : ''}`}
                    onDrop={onDrop}
                    onDragOver={onDragOver}
                    onDragLeave={() => setDragover(false)}
                    onClick={() => fileRef.current?.click()}
                >
                    <input
                        ref={fileRef}
                        type="file"
                        accept=".pdf"
                        style={{ display: 'none' }}
                        onChange={(e) => handleUpload(e.target.files[0])}
                    />
                    {uploading ? (
                        <div className="loading-overlay" style={{ padding: 0 }}>
                            <div className="spinner" style={{ width: 40, height: 40 }} />
                            <div className="loading-text">
                                Running Policy Agent pipeline...<br />
                                <span style={{ fontSize: 12, color: 'var(--gray-400)' }}>
                                    pdf_text_extractor → pdf_table_extractor → irdai_regulation_lookup → rule_validator
                                </span>
                            </div>
                        </div>
                    ) : (
                        <>
                            <div className="upload-icon">📄</div>
                            <div className="upload-text">Drop your policy PDF here, or click to browse</div>
                            <div className="upload-hint">
                                Supports standard Indian health insurance policy documents (up to 20MB)
                            </div>
                        </>
                    )}
                </div>
            </div>

            {/* Error */}
            {error && (
                <div className="toast error" style={{ position: 'relative', marginBottom: 24, top: 0, right: 0 }}>
                    ❌ {error}
                </div>
            )}

            {/* Result */}
            {result && (
                <div className="card result-section">
                    <div className="card-header">
                        <h2 className="card-title">✅ Policy Extracted Successfully</h2>
                        <span className="verdict-badge approved">Processed</span>
                    </div>

                    <div className="stat-grid" style={{ marginBottom: 0 }}>
                        <div className="stat-card teal">
                            <div className="stat-label">Policy ID</div>
                            <div className="stat-value">#{result.policy_id}</div>
                        </div>
                        <div className="stat-card blue">
                            <div className="stat-label">Insurer</div>
                            <div style={{ fontSize: 18, fontWeight: 700, marginTop: 4 }}>{result.insurer}</div>
                        </div>
                        <div className="stat-card green">
                            <div className="stat-label">Sum Insured</div>
                            <div className="stat-value">₹{(result.sum_insured || 0).toLocaleString('en-IN')}</div>
                        </div>
                        <div className="stat-card amber">
                            <div className="stat-label">Rules Extracted</div>
                            <div className="stat-value">{result.rules_count}</div>
                        </div>
                    </div>

                    <p style={{ marginTop: 20, fontSize: 14, color: 'var(--gray-500)' }}>
                        {result.message}
                    </p>
                </div>
            )}

            {/* Tool Pipeline Info */}
            <div className="card" style={{ marginTop: 24 }}>
                <h3 className="card-title" style={{ marginBottom: 16 }}>🛠️ Policy Agent Tool Pipeline</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
                    {[
                        { name: 'pdf_text_extractor', desc: 'Extract text from all PDF pages' },
                        { name: 'pdf_table_extractor', desc: 'Extract structured tables from PDF' },
                        { name: 'irdai_regulation_lookup', desc: 'Cross-reference with IRDAI rules' },
                        { name: 'rule_validator', desc: 'Validate extracted rules for compliance' },
                    ].map((tool) => (
                        <div key={tool.name} style={{
                            padding: 16, borderRadius: 'var(--radius-md)',
                            background: 'var(--gray-50)', border: '1px solid var(--gray-200)',
                        }}>
                            <div className="tool-tag" style={{ marginBottom: 8 }}>{tool.name}</div>
                            <div style={{ fontSize: 12, color: 'var(--gray-500)' }}>{tool.desc}</div>
                        </div>
                    ))}
                </div>
            </div>
        </>
    );
}
