'use client';

/**
 * Dashboard — Home page with system stats and quick actions
 */

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { healthCheck, listPolicies, getHistory, getApiKey } from '@/lib/api';

export default function DashboardPage() {
  const [stats, setStats] = useState({
    policies: 0,
    checksToday: 0,
    approvalRate: 0,
    avgCoverage: 0,
    serverStatus: 'checking...',
  });
  const [recentChecks, setRecentChecks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  async function loadDashboard() {
    setLoading(true);
    try {
      const health = await healthCheck();
      let policies = 0, checksToday = 0, approvalRate = 0, avgCoverage = 0;
      let recent = [];

      if (getApiKey()) {
        try {
          const polData = await listPolicies();
          policies = polData.count || 0;
        } catch (e) { /* no API key set */ }

        try {
          const histData = await getHistory(10);
          recent = histData.checks || [];
          checksToday = recent.length;

          if (recent.length > 0) {
            const verdicts = recent.map(c => {
              try { return JSON.parse(c.verdict_json); } catch { return null; }
            }).filter(Boolean);

            const approved = verdicts.filter(v => v.overall_verdict === 'approved').length;
            approvalRate = verdicts.length ? Math.round((approved / verdicts.length) * 100) : 0;
            avgCoverage = verdicts.length
              ? Math.round(verdicts.reduce((s, v) => s + (v.coverage_percentage || 0), 0) / verdicts.length)
              : 0;
          }
        } catch (e) { /* no history */ }
      }

      setStats({
        policies,
        checksToday,
        approvalRate,
        avgCoverage,
        serverStatus: health.status === 'healthy' ? '🟢 Online' : '🔴 Offline',
      });
      setRecentChecks(recent);
    } catch (e) {
      setStats(prev => ({ ...prev, serverStatus: '🔴 Offline' }));
    }
    setLoading(false);
  }

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">
          SecureShield Agentic Insurance Engine — {stats.serverStatus}
        </p>
      </div>

      {/* Stat Cards */}
      <div className="stat-grid">
        <div className="stat-card teal">
          <div className="stat-icon teal">📄</div>
          <div className="stat-value">{stats.policies}</div>
          <div className="stat-label">Active Policies</div>
        </div>
        <div className="stat-card blue">
          <div className="stat-icon blue">🔍</div>
          <div className="stat-value">{stats.checksToday}</div>
          <div className="stat-label">Recent Checks</div>
        </div>
        <div className="stat-card green">
          <div className="stat-icon green">✅</div>
          <div className="stat-value">{stats.approvalRate}%</div>
          <div className="stat-label">Approval Rate</div>
        </div>
        <div className="stat-card amber">
          <div className="stat-icon amber">📊</div>
          <div className="stat-value">{stats.avgCoverage}%</div>
          <div className="stat-label">Avg Coverage</div>
        </div>
      </div>

      {/* Quick Actions */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 32 }}>
        <Link href="/upload" className="card" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 20 }}>
          <div className="stat-icon teal" style={{ fontSize: 28, width: 56, height: 56 }}>📄</div>
          <div>
            <div className="card-title">Upload Policy PDF</div>
            <p style={{ fontSize: 13, color: 'var(--gray-500)', marginTop: 4 }}>
              Upload and extract rules from insurance policy documents
            </p>
          </div>
        </Link>
        <Link href="/check" className="card" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 20 }}>
          <div className="stat-icon blue" style={{ fontSize: 28, width: 56, height: 56 }}>🔍</div>
          <div>
            <div className="card-title">Check Eligibility</div>
            <p style={{ fontSize: 13, color: 'var(--gray-500)', marginTop: 4 }}>
              Run a patient claim through the agentic eligibility pipeline
            </p>
          </div>
        </Link>
      </div>

      {/* Agentic Pipeline Overview */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">🤖 Agentic Pipeline Overview</h2>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
          {[
            { step: '1', name: 'Policy Agent', desc: 'PDF extraction, IRDAI lookup, rule validation', tools: 4, icon: '📄' },
            { step: '2', name: 'Case Agent', desc: 'Medical normalizer, ICD lookup, cost estimation', tools: 4, icon: '🏥' },
            { step: '3', name: 'Decision Engine', desc: 'Deterministic rule application (no LLM)', tools: 1, icon: '⚖️' },
            { step: '4', name: 'Explanation Agent', desc: 'Clause explainer, savings calculator', tools: 3, icon: '💬' },
          ].map(({ step, name, desc, tools, icon }) => (
            <div key={step} style={{ textAlign: 'center', padding: 20 }}>
              <div style={{
                width: 56, height: 56, borderRadius: '50%', margin: '0 auto 12px',
                background: 'linear-gradient(135deg, var(--teal-500), var(--teal-400))',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 24, color: 'white', boxShadow: 'var(--shadow-glow)',
              }}>
                {icon}
              </div>
              <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>{name}</div>
              <div style={{ fontSize: 12, color: 'var(--gray-500)', lineHeight: 1.4 }}>{desc}</div>
              <div className="tool-tag" style={{ marginTop: 8, display: 'inline-block' }}>
                {tools} tools
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
