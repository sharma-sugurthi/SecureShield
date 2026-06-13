/**
 * SecureShield API Client
 * Handles all communication with the FastAPI backend.
 */

let API_BASE = process.env.NEXT_PUBLIC_API_URL;
if (!API_BASE) {
  if (typeof window !== 'undefined') {
    API_BASE = `http://${window.location.hostname}:8000`;
  } else {
    API_BASE = 'http://localhost:8000';
  }
}
import { supabase } from './supabase';

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

/**
 * Auto-fetch the master API key from the backend.
 * This avoids the need to manually copy-paste from backend logs.
 */
export async function autoFetchApiKey() {
  try {
    const res = await fetch(`${API_BASE}/api/auto-key`);
    if (res.ok) {
      const data = await res.json();
      if (data.api_key) {
        setApiKey(data.api_key);
        return data.api_key;
      }
    }
  } catch (e) {
    // Backend not running — silently fail
  }
  return null;
}

async function apiFetch(path, options = {}) {
  // First check if we have a Supabase session (JWT)
  const { data: { session } } = await supabase.auth.getSession();
  
  const headers = { ...options.headers };
  
  if (session?.access_token) {
    headers['Authorization'] = `Bearer ${session.access_token}`;
  } else {
    // Fallback to API Key for local development/testing without auth
    const key = getApiKey();
    if (key) {
      headers['X-API-Key'] = key;
    }
  }

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  console.log(`[apiFetch] Attempting to fetch: ${API_BASE}${path}`, options);
  
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Request failed (${res.status})`);
    }

    return res.json();
  } catch (err) {
    if (err.name === 'TypeError' && err.message === 'Failed to fetch') {
      console.warn(`[API] Server unreachable at ${API_BASE}${path}. Backend might be down or starting up.`);
      throw new Error("Cannot connect to the server. Please check your internet connection or try again later.");
    }
    console.error(`[apiFetch Error] URL: ${API_BASE}${path} | Error:`, err);
    throw err;
  }
}

// --- Health ---
export async function healthCheck() {
  return apiFetch('/api/health');
}

// --- System Info ---
export async function getSystemInfo() {
  try {
    return await apiFetch('/api/system-info');
  } catch (e) {
    return null;
  }
}

// --- User Profile ---
export async function getProfile() {
  try {
    return await apiFetch('/api/profile');
  } catch (e) {
    return {};
  }
}

export async function updateProfile(profileData) {
  return apiFetch('/api/profile', {
    method: 'POST',
    body: JSON.stringify(profileData),
  });
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

// --- Chat ---
export async function getChatThreads() {
  return apiFetch('/api/chat/threads');
}

export async function deleteChatThread(threadId) {
  return apiFetch(`/api/chat/threads/${threadId}/delete`, {
    method: 'POST',
  });
}

export async function getChatMessages(threadId) {
  return apiFetch(`/api/chat/threads/${threadId}`);
}

export async function chatWithAssistant(query, threadId = null) {
  return apiFetch('/api/chat', {
    method: 'POST',
    body: JSON.stringify({ query, thread_id: threadId }),
  });
}

export async function sendWelcomeEmail() {
  return apiFetch('/api/users/welcome', {
    method: 'POST',
  });
}

export function getReportDownloadUrl(filename) {
  // Use API key if logged out, otherwise wait for frontend to pass token
  const key = getApiKey();
  return `${API_BASE}/api/download-report/${encodeURIComponent(filename)}?api_key=${key}`;
}
