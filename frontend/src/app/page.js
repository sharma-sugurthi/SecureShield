'use client';

/**
 * Dashboard — Home page with hero section, system stats, pipeline visualization,
 * and quick actions for the SecureShield Agentic Insurance Engine.
 */

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { healthCheck, listPolicies, getHistory, getApiKey, getSystemInfo } from '@/lib/api';
import { supabase } from '@/lib/supabase';

export default function DashboardPage() {
  const [stats, setStats] = useState({
    policies: 0,
    checksToday: 0,
    approvalRate: 0,
    avgCoverage: 0,
    serverStatus: 'checking...',
  });
  const [sysInfo, setSysInfo] = useState(null);
  const [recentChecks, setRecentChecks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);

  useEffect(() => {
    loadDashboard();
    
    // Get initial user
    supabase.auth.getUser().then(({ data: { user } }) => {
        setUser(user);
    });

    // Listen for login/logout events
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
        setUser(session?.user ?? null);
    });

    return () => subscription.unsubscribe();
  }, []);

  async function loadDashboard() {
    setLoading(true);
    try {
      const health = await healthCheck();
      let policies = 0, checksToday = 0, approvalRate = 0, avgCoverage = 0;
      let recent = [];

      // Fetch system info (no auth needed)
      try {
        const info = await getSystemInfo();
        if (info) setSysInfo(info);
      } catch (e) { /* not critical */ }

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
      {/* Top Bar Greeting */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 800, color: 'var(--navy-800)', letterSpacing: '-0.02em' }}>
            Good morning, {user?.user_metadata?.full_name?.split(' ')[0] || 'User'}
          </h1>
          <p style={{ color: 'var(--gray-500)', fontSize: 15, marginTop: 4 }}>
            Here is your health insurance overview. {stats.serverStatus}
          </p>
        </div>
        <div style={{ position: 'relative' }}>
          <span style={{ position: 'absolute', left: 14, top: 12, color: 'var(--gray-400)' }}>🔍</span>
          <input 
            type="text" 
            placeholder="Search policies or claims..." 
            className="form-input"
            style={{ paddingLeft: 40, width: 300, borderRadius: 100 }}
          />
        </div>
      </div>

      {/* Stat Cards (Top Row) */}
      <div className="stat-grid stagger-in">
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

      {/* Bento Grid: Middle Row */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 24, marginBottom: 32 }}>
        
        {/* Left Column: Recent Activity */}
        <div className="card" style={{ height: '100%' }}>
          <div className="card-header">
            <h2 className="card-title">Recent Activity</h2>
            <Link href="/history" style={{ fontSize: 13, color: 'var(--primary-600)', textDecoration: 'none', fontWeight: 600 }}>
              View All
            </Link>
          </div>
          <div className="card-body">
            {recentChecks.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {recentChecks.slice(0, 5).map((check, i) => {
                  let verdict = null;
                  try { verdict = JSON.parse(check.verdict_json); } catch (e) {}
                  
                  const vStatus = verdict?.overall_verdict?.toLowerCase() || 'unknown';
                  const badgeClass = `verdict-badge ${vStatus === 'approved' ? 'approved' : vStatus === 'denied' ? 'denied' : 'partial'}`;
                  
                  return (
                    <Link href={`/history`} key={i} style={{ textDecoration: 'none', color: 'inherit' }}>
                      <div style={{ padding: 16, border: '1px solid var(--gray-100)', borderRadius: 'var(--radius-md)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', transition: 'background 0.2s' }} onMouseOver={e => e.currentTarget.style.background = 'var(--gray-50)'} onMouseOut={e => e.currentTarget.style.background = 'transparent'}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                          <div style={{ width: 40, height: 40, borderRadius: 'var(--radius-sm)', background: 'var(--primary-50)', color: 'var(--primary-500)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18 }}>
                            📄
                          </div>
                          <div>
                            <div style={{ fontWeight: 600, color: 'var(--navy-800)' }}>{check.policy_name}</div>
                            <div style={{ fontSize: 13, color: 'var(--gray-500)', marginTop: 4 }}>
                              Claim: ₹{(check.claimed_amount || 0).toLocaleString()} • {new Date(check.created_at).toLocaleDateString()}
                            </div>
                          </div>
                        </div>
                        <div className={badgeClass}>
                          {verdict?.overall_verdict || 'Unknown'}
                        </div>
                      </div>
                    </Link>
                  );
                })}
              </div>
            ) : (
              <div style={{ padding: 32, textAlign: 'center', color: 'var(--gray-500)', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <div style={{ fontSize: 40, marginBottom: 12 }}>📭</div>
                <div style={{ fontWeight: 600, color: 'var(--navy-700)' }}>No recent activity</div>
                <div style={{ fontSize: 14 }}>Start by uploading a policy or running a check.</div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Quick Actions */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          <div className="card" style={{ flex: 1, padding: 0, overflow: 'hidden' }}>
            <div style={{ padding: 24, borderBottom: '1px solid var(--gray-100)' }}>
              <h2 className="card-title">Quick Actions</h2>
            </div>
            
            <Link href="/upload" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 20, padding: '24px', borderBottom: '1px solid var(--gray-100)', transition: 'background 0.2s' }} onMouseOver={e => e.currentTarget.style.background = 'var(--gray-50)'} onMouseOut={e => e.currentTarget.style.background = 'transparent'}>
              <div className="stat-icon teal" style={{ width: 48, height: 48, marginBottom: 0 }}>📄</div>
              <div>
                <div style={{ fontWeight: 600, color: 'var(--navy-800)' }}>Upload Policy</div>
                <p style={{ fontSize: 13, color: 'var(--gray-500)', marginTop: 4 }}>
                  Add a new insurance document
                </p>
              </div>
              <div style={{ marginLeft: 'auto', color: 'var(--gray-400)' }}>→</div>
            </Link>

            <Link href="/check" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 20, padding: '24px', transition: 'background 0.2s' }} onMouseOver={e => e.currentTarget.style.background = 'var(--gray-50)'} onMouseOut={e => e.currentTarget.style.background = 'transparent'}>
              <div className="stat-icon blue" style={{ width: 48, height: 48, marginBottom: 0 }}>🔍</div>
              <div>
                <div style={{ fontWeight: 600, color: 'var(--navy-800)' }}>Check Eligibility</div>
                <p style={{ fontSize: 13, color: 'var(--gray-500)', marginTop: 4 }}>
                  Run a new claim check
                </p>
              </div>
              <div style={{ marginLeft: 'auto', color: 'var(--gray-400)' }}>→</div>
            </Link>
          </div>
        </div>

      </div>
    </>
  );
}
