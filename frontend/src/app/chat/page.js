'use client';

/**
 * Chat Assistant Page
 * Medical insurance chat powered by the 3-tier Chat Agent:
 * Tier 1: FAQ cache → Tier 2: Fast LLM → Tier 3: Complex reasoning LLM
 *
 * Persistence:
 * - sessionStorage: preserves activeThreadId + messages across in-session navigation
 * - localStorage:   preserves activeThreadId across page refreshes (messages fetched from API)
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { chatWithAssistant, getChatThreads, getChatMessages, deleteChatThread } from '@/lib/api';
import { supabase } from '@/lib/supabase';
import {
    ShieldIcon, UserIcon, ChatIcon, ZapIcon, RocketIcon, LayersIcon,
    MessageSquareIcon, XIcon
} from '@/components/icons';

const STORAGE_KEY_THREAD  = 'chat_active_thread';
const STORAGE_KEY_MSGS    = 'chat_messages';

const QUICK_QUESTIONS = [
    'What is a moratorium period?',
    'How does room rent capping work?',
    'What are pre-existing disease waiting periods?',
    'Explain co-payment vs deductible',
    'What does IRDAI mandate for claim settlement?',
    'How is sum insured calculated?',
];

/* ── Storage helpers ────────────────────────────────────────── */

function persistThreadId(threadId) {
    try {
        if (threadId) {
            sessionStorage.setItem(STORAGE_KEY_THREAD, String(threadId));
            localStorage.setItem(STORAGE_KEY_THREAD, String(threadId));
        } else {
            sessionStorage.removeItem(STORAGE_KEY_THREAD);
            // Don't clear localStorage on "New Chat" — 
            // we only clear it when there's truly no thread.
            // Actually, clear it so refresh doesn't re-open old thread after explicit New Chat.
            localStorage.removeItem(STORAGE_KEY_THREAD);
        }
    } catch (_) { /* storage full / disabled */ }
}

function persistMessages(msgs) {
    try {
        sessionStorage.setItem(STORAGE_KEY_MSGS, JSON.stringify(msgs));
    } catch (_) { /* storage full */ }
}

function getPersistedThreadId() {
    try {
        // sessionStorage wins (same-session navigation)
        const session = sessionStorage.getItem(STORAGE_KEY_THREAD);
        if (session) return Number(session);
        // fallback to localStorage (post-refresh)
        const local = localStorage.getItem(STORAGE_KEY_THREAD);
        if (local) return Number(local);
    } catch (_) {}
    return null;
}

function getPersistedMessages() {
    try {
        const raw = sessionStorage.getItem(STORAGE_KEY_MSGS);
        if (raw) return JSON.parse(raw);
    } catch (_) {}
    return null;
}

function clearPersistedMessages() {
    try { sessionStorage.removeItem(STORAGE_KEY_MSGS); } catch (_) {}
}

/* ── Component ──────────────────────────────────────────────── */

export default function ChatPage() {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    
    // Thread State
    const [threads, setThreads] = useState([]);
    const [activeThreadId, setActiveThreadId] = useState(null);
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [isSidebarHovered, setIsSidebarHovered] = useState(false);

    // Guard: prevent the restore-on-mount effect from re-running
    const hasRestoredRef = useRef(false);
    const chatMessagesRef = useRef(null);
    const inputRef = useRef(null);

    /* ── Persist activeThreadId whenever it changes ─────────── */
    useEffect(() => {
        // Skip the very first render (initial null) — handled by restore logic
        if (!hasRestoredRef.current) return;
        persistThreadId(activeThreadId);
    }, [activeThreadId]);

    /* ── Persist messages whenever they change ──────────────── */
    useEffect(() => {
        if (!hasRestoredRef.current) return;
        persistMessages(messages);
    }, [messages]);

    /* ── Mount: check auth, load threads, restore last session ─ */
    useEffect(() => {
        supabase.auth.getSession().then(({ data: { session } }) => {
            if (session) {
                setIsLoggedIn(true);
                loadThreadsAndRestore();
            } else {
                // Not logged in — still try to restore any anonymous messages from sessionStorage
                restoreFromSessionStorage();
            }
        });
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    async function loadThreadsAndRestore() {
        try {
            const data = await getChatThreads();
            const loadedThreads = data.threads || [];
            setThreads(loadedThreads);

            // Try to restore last active thread
            const persistedId = getPersistedThreadId();
            if (persistedId) {
                // Verify the thread still exists in the user's threads
                const threadExists = loadedThreads.some(t => t.id === persistedId);
                if (threadExists) {
                    setActiveThreadId(persistedId);

                    // Try sessionStorage messages first (instant, no API call)
                    const cachedMsgs = getPersistedMessages();
                    if (cachedMsgs && cachedMsgs.length > 0) {
                        setMessages(cachedMsgs);
                    } else {
                        // Fetch from API (post-refresh scenario)
                        try {
                            const msgData = await getChatMessages(persistedId);
                            setMessages(msgData.messages || []);
                        } catch (_) {
                            // Thread may have been deleted server-side
                            clearPersistedMessages();
                        }
                    }
                } else {
                    // Thread was deleted or doesn't belong to user anymore
                    persistThreadId(null);
                    clearPersistedMessages();
                }
            }
        } catch (e) {
            console.error("Failed to load threads", e);
        }

        hasRestoredRef.current = true;
    }

    function restoreFromSessionStorage() {
        const cachedMsgs = getPersistedMessages();
        if (cachedMsgs && cachedMsgs.length > 0) {
            setMessages(cachedMsgs);
        }
        hasRestoredRef.current = true;
    }

    /* ── Auto-scroll ────────────────────────────────────────── */
    useEffect(() => {
        if (chatMessagesRef.current) {
            chatMessagesRef.current.scrollTop = chatMessagesRef.current.scrollHeight;
        }
    }, [messages]);

    /* ── Thread management ──────────────────────────────────── */

    async function loadThreads() {
        try {
            const data = await getChatThreads();
            setThreads(data.threads || []);
        } catch (e) {
            console.error("Failed to load threads", e);
        }
    }

    async function handleThreadSelect(threadId) {
        if (activeThreadId === threadId) return;
        setActiveThreadId(threadId);
        setLoading(true);
        try {
            const data = await getChatMessages(threadId);
            const msgs = data.messages || [];
            setMessages(msgs);
        } catch (e) {
            console.error("Failed to load messages", e);
        }
        setLoading(false);
    }

    async function handleDeleteThread(e, threadId) {
        e.stopPropagation();
        if (!confirm('Are you sure you want to delete this conversation?')) return;
        
        try {
            await deleteChatThread(threadId);
            if (activeThreadId === threadId) {
                handleNewChat();
            }
            loadThreads();
        } catch (e) {
            console.error("Failed to delete thread", e);
            alert("Failed to delete conversation.");
        }
    }

    function handleNewChat() {
        setActiveThreadId(null);
        setMessages([]);
        // Clear persisted state so we start fresh
        persistThreadId(null);
        clearPersistedMessages();
    }

    /* ── Send message ───────────────────────────────────────── */

    async function sendMessage(text) {
        if (!text.trim()) return;

        const userMsg = { role: 'user', content: text.trim() };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);

        try {
            const data = await chatWithAssistant(text.trim(), activeThreadId);
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: data.answer,
                method: data.method,
                duration: data.duration_ms,
            }]);
            
            // If a new thread was created on the backend, update our state
            if (data.thread_id && !activeThreadId) {
                setActiveThreadId(data.thread_id);
                loadThreads();
            }
        } catch (e) {
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: `Sorry, I encountered an error: ${e.message}`,
                method: 'error',
                duration: 0,
            }]);
        }
        setLoading(false);
        inputRef.current?.focus({ preventScroll: true });
    }

    function handleSubmit(e) {
        e.preventDefault();
        sendMessage(input);
    }

    return (
        <>
            <div className="page-header">
                <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}><ChatIcon size={22} /> Chat Assistant</h1>
                <p className="page-subtitle">
                    Ask questions about health insurance, IRDAI regulations, or policy terms —
                    powered by 3-tier AI (FAQ Cache → Fast LLM → Deep Reasoning)
                </p>
            </div>

            <div className="chat-layout">
                
                {/* Threads Sidebar (Only for logged in users) */}
                {isLoggedIn && (
                    <div 
                        className="card" 
                        style={{ 
                            width: isSidebarHovered ? 280 : 72, 
                            flexShrink: 0, 
                            padding: isSidebarHovered ? '16px' : '16px 8px', 
                            height: 'calc(100vh - 120px)', 
                            display: 'flex', 
                            flexDirection: 'column',
                            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                            overflow: 'hidden'
                        }}
                        onMouseEnter={() => setIsSidebarHovered(true)}
                        onMouseLeave={() => setIsSidebarHovered(false)}
                    >
                        <button onClick={handleNewChat} className="btn btn-primary" style={{ width: '100%', marginBottom: 16, display: 'flex', justifyContent: 'center', padding: isSidebarHovered ? '12px 24px' : '12px 0' }}>
                            {isSidebarHovered ? '+ New Chat' : '+'}
                        </button>
                        <div style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden', display: 'flex', flexDirection: 'column', gap: 4 }}>
                            {isSidebarHovered && (
                                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--gray-400)', textTransform: 'uppercase', marginBottom: 8, paddingLeft: 8 }}>
                                    Recent Threads
                                </div>
                            )}
                            {threads.length === 0 ? (
                                <div style={{ fontSize: 13, color: 'var(--gray-500)', padding: 8, textAlign: 'center' }}>
                                    No past conversations
                                </div>
                            ) : (
                                threads.map(t => (
                                    <div 
                                        key={t.id}
                                        onClick={() => handleThreadSelect(t.id)}
                                        style={{
                                            padding: '10px 12px',
                                            borderRadius: 'var(--radius-sm)',
                                            background: activeThreadId === t.id ? 'var(--primary-50)' : 'transparent',
                                            border: 'none',
                                            textAlign: 'left',
                                            cursor: 'pointer',
                                            color: activeThreadId === t.id ? 'var(--primary-600)' : 'var(--navy-700)',
                                            fontWeight: activeThreadId === t.id ? 600 : 500,
                                            fontSize: 14,
                                            whiteSpace: 'nowrap',
                                            overflow: 'hidden',
                                            textOverflow: 'ellipsis',
                                            transition: 'all 0.2s',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '8px'
                                        }}
                                        title={t.title}
                                    >
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, overflow: 'hidden' }}>
                                            <span style={{ fontSize: 16, display: 'flex' }}><MessageSquareIcon size={16} /></span> 
                                            {isSidebarHovered && <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{t.title}</span>}
                                        </div>
                                        {isSidebarHovered && (
                                            <button 
                                                onClick={(e) => handleDeleteThread(e, t.id)}
                                                style={{ 
                                                    background: 'none', 
                                                    border: 'none', 
                                                    cursor: 'pointer', 
                                                    opacity: 0.5, 
                                                    padding: '2px 4px', 
                                                    fontSize: 14 
                                                }}
                                                title="Delete conversation"
                                                onMouseEnter={(e) => e.target.style.opacity = 1}
                                                onMouseLeave={(e) => e.target.style.opacity = 0.5}
                                            >
                                                ✕
                                            </button>
                                        )}
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                )}

                {/* Chat Container */}
                <div className="card chat-main-card">
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
                        <div className="chat-messages" ref={chatMessagesRef} style={{ flex: 1, overflowY: 'auto' }}>
                            {messages.length === 0 && (
                                <div className="empty-state" style={{ padding: '60px 20px' }}>
                                    <div className="empty-state-icon" style={{ color: 'var(--primary-400)' }}><ShieldIcon size={48} /></div>
                                    <div className="empty-state-text">PolicyEye Chat Assistant</div>
                                    <div className="empty-state-hint">
                                        Ask anything about health insurance policies, IRDAI regulations,
                                        claim procedures, or medical coverage terms.
                                    </div>
                                </div>
                            )}

                            {messages.map((msg, i) => (
                                <div key={i} className={`chat-message ${msg.role}`}>
                                    <div className="chat-avatar">
                                        {msg.role === 'user' ? <UserIcon size={16} /> : <ShieldIcon size={16} />}
                                    </div>
                                    <div style={{ maxWidth: '100%', minWidth: 0, overflow: 'hidden' }}>
                                        <div className="chat-bubble markdown-body" style={{ whiteSpace: 'normal', lineHeight: 1.6, overflowWrap: 'break-word', wordBreak: 'break-word' }}>
                                            {msg.role === 'assistant' ? (
                                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                    {msg.content}
                                                </ReactMarkdown>
                                            ) : (
                                                msg.content
                                            )}
                                        </div>
                                        {msg.role === 'assistant' && (
                                            <div className="chat-meta">
                                                {msg.method && (
                                                    <span className={`chat-method-badge ${msg.method === 'cache' || msg.method === 'faq_cache' ? 'cache' : msg.method === 'error' ? 'error' : 'llm'}`}>
                                                        {msg.method === 'cache' || msg.method === 'faq_cache' ? 'CACHE' : msg.method === 'error' ? 'ERROR' : 'LLM'}
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
                                    <div className="chat-avatar"><ShieldIcon size={16} /></div>
                                    <div className="chat-bubble">
                                        <div className="typing-indicator">
                                            <div className="typing-dot" />
                                            <div className="typing-dot" />
                                            <div className="typing-dot" />
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Input */}
                        <form onSubmit={handleSubmit} className="chat-input-area" style={{ marginTop: 'auto', borderBottom: 'none' }}>
                            <input
                                ref={inputRef}
                                className="chat-input"
                                placeholder="Ask about insurance policies, IRDAI rules, claim processes..."
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                disabled={loading}
                            />
                            <button
                                type="submit"
                                className="chat-send-btn"
                                disabled={loading || !input.trim()}
                            >
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                                </svg>
                            </button>
                        </form>
                        <div style={{ textAlign: 'center', fontSize: 10, color: 'var(--gray-400)', paddingBottom: 12, marginTop: -8 }}>
                            This is an AI summary. Always refer to your specific policy document for final details.
                        </div>
                    </div>
                </div>
            </div>

            {/* Info */}
            <div className="card" style={{ marginTop: 24, padding: '16px 24px' }}>
                <h3 className="card-title" style={{ marginBottom: 12, fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ display: 'flex', alignItems: 'center' }}><LayersIcon size={16} /></span> 3-Tier Chat Architecture
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }} className="chat-tier-grid">
                    {[
                        { tier: 'Tier 1', name: 'FAQ Cache', desc: 'Instant answers from pre-loaded FAQ database', speed: '< 5ms', icon: <ZapIcon size={24} /> },
                        { tier: 'Tier 2', name: 'Fast LLM', desc: 'Quick responses via Cerebras/Groq for common queries', speed: '< 500ms', icon: <RocketIcon size={24} /> },
                        { tier: 'Tier 3', name: 'Deep Reasoning', desc: 'Complex analysis via Gemini for nuanced questions', speed: '< 3s', icon: <LayersIcon size={24} /> },
                    ].map((t) => (
                        <div key={t.tier} style={{
                            padding: 12, borderRadius: 'var(--radius-sm)',
                            background: 'var(--gray-50)', border: '1px solid var(--gray-200)',
                            textAlign: 'left', display: 'flex', alignItems: 'flex-start', gap: 12
                        }}>
                            <div style={{ color: 'var(--primary-500)' }}>{t.icon}</div>
                            <div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                                    <div style={{ fontWeight: 700, fontSize: 12, color: 'var(--navy-800)' }}>{t.name}</div>
                                    <div className="tool-tag" style={{ fontSize: 9, padding: '2px 6px' }}>{t.tier}</div>
                                </div>
                                <div style={{ fontSize: 11, color: 'var(--gray-500)', lineHeight: 1.3, marginBottom: 4 }}>{t.desc}</div>
                                <div style={{ fontSize: 10, color: 'var(--teal-600)', fontWeight: 700 }}>{t.speed}</div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </>
    );
}
