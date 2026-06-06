'use client';

/**
 * Chat Assistant Page
 * Medical insurance chat powered by the 3-tier Chat Agent:
 * Tier 1: FAQ cache → Tier 2: Fast LLM → Tier 3: Complex reasoning LLM
 */

import { useState, useRef, useEffect } from 'react';
import { chatWithAssistant, getApiKey } from '@/lib/api';

const QUICK_QUESTIONS = [
    'What is a moratorium period?',
    'How does room rent capping work?',
    'What are pre-existing disease waiting periods?',
    'Explain co-payment vs deductible',
    'What does IRDAI mandate for claim settlement?',
    'How is sum insured calculated?',
];

export default function ChatPage() {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    async function sendMessage(text) {
        if (!text.trim()) return;
        if (!getApiKey()) {
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: 'Please set your API key in Settings first, or wait for auto-configuration.',
                method: 'error',
                duration: 0,
            }]);
            return;
        }

        const userMsg = { role: 'user', content: text.trim() };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);

        try {
            const data = await chatWithAssistant(text.trim());
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: data.answer,
                method: data.method,
                duration: data.duration_ms,
            }]);
        } catch (e) {
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: `Sorry, I encountered an error: ${e.message}`,
                method: 'error',
                duration: 0,
            }]);
        }
        setLoading(false);
        inputRef.current?.focus();
    }

    function handleSubmit(e) {
        e.preventDefault();
        sendMessage(input);
    }

    return (
        <>
            <div className="page-header">
                <h1 className="page-title">💬 Chat Assistant</h1>
                <p className="page-subtitle">
                    Ask questions about health insurance, IRDAI regulations, or policy terms —
                    powered by 3-tier AI (FAQ Cache → Fast LLM → Deep Reasoning)
                </p>
            </div>

            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                <div className="chat-container">
                    {/* Quick Questions */}
                    {messages.length === 0 && (
                        <div className="quick-questions">
                            <span style={{ fontSize: 12, color: 'var(--gray-400)', fontWeight: 600, marginRight: 4 }}>
                                Try:
                            </span>
                            {QUICK_QUESTIONS.map((q, i) => (
                                <button
                                    key={i}
                                    className="quick-question-btn"
                                    onClick={() => sendMessage(q)}
                                >
                                    {q}
                                </button>
                            ))}
                        </div>
                    )}

                    {/* Messages */}
                    <div className="chat-messages">
                        {messages.length === 0 && (
                            <div className="empty-state" style={{ padding: '60px 20px' }}>
                                <div className="empty-state-icon">🛡️</div>
                                <div className="empty-state-text">SecureShield Chat Assistant</div>
                                <div className="empty-state-hint">
                                    Ask anything about health insurance policies, IRDAI regulations,
                                    claim procedures, or medical coverage terms.
                                </div>
                            </div>
                        )}

                        {messages.map((msg, i) => (
                            <div key={i} className={`chat-message ${msg.role}`}>
                                <div className="chat-avatar">
                                    {msg.role === 'user' ? '👤' : '🛡️'}
                                </div>
                                <div>
                                    <div className="chat-bubble">
                                        {msg.content}
                                    </div>
                                    {msg.role === 'assistant' && (
                                        <div className="chat-meta">
                                            {msg.method && (
                                                <span className={`chat-method-badge ${msg.method === 'faq_cache' ? 'cache' : msg.method === 'error' ? 'error' : 'llm'}`}>
                                                    {msg.method === 'faq_cache' ? '⚡ CACHE' : msg.method === 'error' ? '❌ ERROR' : '🤖 LLM'}
                                                </span>
                                            )}
                                            {msg.duration > 0 && (
                                                <span>{msg.duration.toFixed(0)}ms</span>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}

                        {/* Typing Indicator */}
                        {loading && (
                            <div className="chat-message assistant">
                                <div className="chat-avatar">🛡️</div>
                                <div className="chat-bubble">
                                    <div className="typing-indicator">
                                        <div className="typing-dot" />
                                        <div className="typing-dot" />
                                        <div className="typing-dot" />
                                    </div>
                                </div>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input */}
                    <form onSubmit={handleSubmit} className="chat-input-area">
                        <input
                            ref={inputRef}
                            className="chat-input"
                            placeholder="Ask about insurance policies, IRDAI rules, claim processes..."
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            disabled={loading}
                            autoFocus
                        />
                        <button
                            type="submit"
                            className="chat-send-btn"
                            disabled={loading || !input.trim()}
                        >
                            ➤
                        </button>
                    </form>
                </div>
            </div>

            {/* Info */}
            <div className="card" style={{ marginTop: 24 }}>
                <h3 className="card-title" style={{ marginBottom: 16 }}>🧠 3-Tier Chat Architecture</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
                    {[
                        { tier: 'Tier 1', name: 'FAQ Cache', desc: 'Instant answers from pre-loaded IRDAI FAQ database', speed: '< 5ms', icon: '⚡' },
                        { tier: 'Tier 2', name: 'Fast LLM', desc: 'Quick responses via Cerebras/Groq for common queries', speed: '< 500ms', icon: '🚀' },
                        { tier: 'Tier 3', name: 'Deep Reasoning', desc: 'Complex analysis via Gemini for nuanced questions', speed: '< 3s', icon: '🧠' },
                    ].map((t) => (
                        <div key={t.tier} style={{
                            padding: 20, borderRadius: 'var(--radius-md)',
                            background: 'var(--gray-50)', border: '1px solid var(--gray-200)',
                            textAlign: 'center',
                        }}>
                            <div style={{ fontSize: 28, marginBottom: 8 }}>{t.icon}</div>
                            <div className="tool-tag" style={{ marginBottom: 8, display: 'inline-block' }}>{t.tier}</div>
                            <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>{t.name}</div>
                            <div style={{ fontSize: 12, color: 'var(--gray-500)', lineHeight: 1.4 }}>{t.desc}</div>
                            <div style={{ fontSize: 11, color: 'var(--teal-600)', fontWeight: 700, marginTop: 8 }}>{t.speed}</div>
                        </div>
                    ))}
                </div>
            </div>
        </>
    );
}
