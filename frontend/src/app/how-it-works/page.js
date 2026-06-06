'use client';

/**
 * How It Works — Architecture and technical details page
 */

export default function HowItWorksPage() {
  return (
    <div className="card" style={{ maxWidth: 1000, margin: '0 auto' }}>
      <div className="card-header">
        <h1 className="card-title" style={{ fontSize: 24 }}>System Architecture</h1>
        <p style={{ color: 'var(--gray-500)', marginTop: 8 }}>
          Technical overview of the SecureShield backend for developers and auditors.
        </p>
      </div>

      <div className="card-body">
        {/* Agentic Pipeline Overview */}
        <div style={{ marginBottom: 40 }}>
          <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16 }}>🤖 5-Agent Agentic Pipeline</h2>
          <div className="pipeline-flow">
            {[
              { icon: '📄', name: 'Policy Agent', tools: '4 tools', desc: 'PDF extraction + IRDAI lookup' },
              { icon: '🏥', name: 'Case Agent', tools: '4 tools', desc: 'Medical NLP + ICD coding' },
              { icon: '⚖️', name: 'Decision Engine', tools: '1 tool', desc: 'Deterministic rules (no LLM)' },
              { icon: '💬', name: 'Explanation Agent', tools: '3 tools', desc: 'Patient-friendly explainer' },
              { icon: '🛡️', name: 'Grievance Agent', tools: '6 tools', desc: 'Compliance + PDF reports' },
            ].map((node, i) => (
              <div key={i} className="pipeline-node">
                <div className="pipeline-icon">{node.icon}</div>
                <div className="pipeline-label">{node.name}</div>
                <div className="pipeline-tools">{node.tools}</div>
                <div style={{ fontSize: 11, color: 'var(--gray-500)', marginTop: 4 }}>{node.desc}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Technology Stack */}
        <div style={{ marginBottom: 40 }}>
          <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16 }}>🛠️ Technology Stack</h2>
          <div className="tech-badges">
            {[
              '🐍 Python 3.11', '⚡ FastAPI', '🔗 LangGraph', '🧠 Multi-LLM',
              '📊 SQLAlchemy ORM', '🔒 HMAC-SHA256', '📄 PyMuPDF',
              '🇮🇳 IRDAI 2024', '⚛️ Next.js 16', '🎨 React 19',
              '🤖 Cerebras', '🤖 Groq', '🤖 Gemini', '🤖 xAI', '🤖 OpenRouter',
            ].map((tech, i) => (
              <span key={i} className="tech-badge">{tech}</span>
            ))}
          </div>
        </div>

        {/* Core Principles */}
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16 }}>Core Principles</h2>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            <div style={{ padding: 16, background: 'var(--gray-50)', borderRadius: 'var(--radius-md)', border: '1px solid var(--gray-200)' }}>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>Zero LLM in Decisions</div>
              <p style={{ fontSize: 14, color: 'var(--gray-600)', lineHeight: 1.5 }}>
                Large Language Models are used only for extraction and explanation. The actual approval/denial decision is computed via a deterministic rules engine to guarantee zero hallucinations and 100% reliability.
              </p>
            </div>
            <div style={{ padding: 16, background: 'var(--gray-50)', borderRadius: 'var(--radius-md)', border: '1px solid var(--gray-200)' }}>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>IRDAI 2024 Compliance</div>
              <p style={{ fontSize: 14, color: 'var(--gray-600)', lineHeight: 1.5 }}>
                The system strictly enforces the latest IRDAI regulations, including standardized waiting periods, moratorium guidelines, and explicit definitions for pre-existing conditions.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
