/**
 * SecureShield API Client
 * Handles all communication with the FastAPI backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

let apiKey = '';

export function setApiKey(key) {
  apiKey = key;
  if (typeof window !== 'undefined') {
    localStorage.setItem('secureshield_api_key', key);
  }
}

export function getApiKey() {
  if (!apiKey && typeof window !== 'undefined') {
    apiKey = localStorage.getItem('secureshield_api_key') || '';
  }
  return apiKey;
}

async function apiFetch(path, options = {}) {
  const key = getApiKey();
  const headers = {
    'X-API-Key': key,
    ...options.headers,
  };

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `Request failed (${res.status})`);
  }

  return res.json();
}

// --- Health ---
export async function healthCheck() {
  return apiFetch('/api/health');
}

// --- Policies ---
export async function uploadPolicy(file) {
  const form = new FormData();
  form.append('file', file);
  return apiFetch('/api/upload-policy', {
    method: 'POST',
    body: form,
    headers: {}, // Let browser set Content-Type with boundary
  });
}

export async function listPolicies() {
  return apiFetch('/api/policies');
}

export async function getPolicy(id) {
  return apiFetch(`/api/policies/${id}`);
}

// --- Eligibility Check ---
export async function checkEligibility(policyId, caseFacts) {
  return apiFetch('/api/check-eligibility', {
    method: 'POST',
    body: JSON.stringify({
      policy_id: policyId,
      case: caseFacts,
    }),
  });
}

// --- History ---
export async function getHistory(limit = 20) {
  return apiFetch(`/api/history?limit=${limit}`);
}

// --- Audit Trail ---
export async function getAuditTrail(limit = 50) {
  return apiFetch(`/api/audit-trail?limit=${limit}`);
}

// --- Grievance / Dispute ---
export async function disputeClaim(grievanceData) {
  return apiFetch('/api/dispute-claim', {
    method: 'POST',
    body: JSON.stringify(grievanceData),
  });
}

export function getReportDownloadUrl(filename) {
  const key = getApiKey();
  return `${API_BASE}/api/download-report/${encodeURIComponent(filename)}?api_key=${key}`;
}
