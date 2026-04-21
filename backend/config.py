"""
SecureShield Configuration
Loads environment variables and defines intelligent multi-model routing.

Routing Strategy:
  - Groq (Llama 3.3 70B)  → Primary for text tasks (case analysis, explanation). Blazing fast, free.
  - Gemini Flash           → Primary for PDF/vision tasks (policy ingestion). Best free vision model.
  - xAI Grok               → Primary for long-form writing (grievance letters). $25/mo free credits.
  - Together.ai            → Backup for all text tasks.
  - OpenRouter             → Final fallback (multiple free models).
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Provider API Keys ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
XAI_API_KEY = os.getenv("XAI_API_KEY")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")

# --- Cloudflare AI Gateway (Optional) ---
CF_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CF_GATEWAY_NAME = os.getenv("CLOUDFLARE_GATEWAY_NAME")

# Providers fully supported by Cloudflare AI Gateway
_CF_SUPPORTED = {"groq", "cerebras", "openrouter"}

def get_gateway_url(provider: str, default_url: str) -> str:
    """Route through Cloudflare only for providers it reliably supports."""
    if CF_ACCOUNT_ID and CF_GATEWAY_NAME and provider in _CF_SUPPORTED:
        cf_provider_map = {
            "groq": "groq",
            "cerebras": "cerebras",
            "openrouter": "openrouter",
        }
        cf_name = cf_provider_map[provider]
        base = f"https://gateway.ai.cloudflare.com/v1/{CF_ACCOUNT_ID}/{CF_GATEWAY_NAME}/{cf_name}"
        # Cloudflare gateway base URL already routes — append the completions path
        return f"{base}/chat/completions"
    return default_url

# --- Provider Base URLs (fallback = direct API) ---
# Google: use direct API (Cloudflare's google-ai-studio gateway has path issues)
GOOGLE_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
GROQ_BASE_URL = get_gateway_url("groq", "https://api.groq.com/openai/v1")
# xAI: bypass Cloudflare (no free credits via gateway)
XAI_BASE_URL = "https://api.x.ai/v1"
# Together: bypass Cloudflare ("Invalid provider" error via gateway)
TOGETHER_BASE_URL = "https://api.together.xyz/v1"
# OpenRouter: Cloudflare proxies it, endpoint needs /chat/completions appended
OPENROUTER_BASE_URL = get_gateway_url("openrouter", "https://openrouter.ai/api/v1/chat/completions")
CEREBRAS_BASE_URL = get_gateway_url("cerebras", "https://api.cerebras.ai/v1")

# --- Provider Model Selections ---
GOOGLE_MODELS = {
    "default": "gemini-2.0-flash",
    "lite": "gemini-2.0-flash-lite",
}

GROQ_MODELS = {
    "primary": "llama-3.3-70b-versatile",
    "fast": "llama-3.1-8b-instant",
}

XAI_MODELS = {
    "primary": "grok-3-mini-fast",
}

TOGETHER_MODELS = {
    "primary": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "fast": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
}

OPENROUTER_MODELS = {
    "fallback_chain": [
        "qwen/qwen3-coder:free",
        "google/gemma-3-27b-it:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "microsoft/phi-4-reasoning-plus:free",
        "nvidia/llama-3.1-nemotron-70b-instruct:free",
    ]
}

CEREBRAS_MODELS = {
    "primary": "llama-3.3-70b",
    "fast": "llama3.1-8b",
}

# --- Intelligent Task-Based Routing ---
# Each role maps to an ordered list of (provider, model) tuples.
# The router tries them in order until one succeeds.
TASK_ROUTING = {
    "policy_ingestion": [
        # Cerebras + Groq first (free, reliable, no gateway issues)
        ("cerebras", CEREBRAS_MODELS["primary"]),
        ("groq", GROQ_MODELS["primary"]),
        # Gemini direct fallback (bypasses Cloudflare, uses native API)
        ("google", GOOGLE_MODELS["default"]),
        ("google", GOOGLE_MODELS["lite"]),
        # Together direct fallback
        ("together", TOGETHER_MODELS["primary"]),
        ("openrouter", None),
    ],
    "case_analysis": [
        ("cerebras", CEREBRAS_MODELS["primary"]),
        ("groq", GROQ_MODELS["primary"]),
        ("google", GOOGLE_MODELS["default"]),
        ("together", TOGETHER_MODELS["primary"]),
        ("openrouter", None),
    ],
    "explanation": [
        ("cerebras", CEREBRAS_MODELS["primary"]),
        ("groq", GROQ_MODELS["primary"]),
        ("google", GOOGLE_MODELS["default"]),
        ("together", TOGETHER_MODELS["primary"]),
        ("openrouter", None),
    ],
    "grievance": [
        ("cerebras", CEREBRAS_MODELS["primary"]),
        ("groq", GROQ_MODELS["primary"]),
        ("google", GOOGLE_MODELS["default"]),
        ("together", TOGETHER_MODELS["primary"]),
        ("openrouter", None),
    ],
    "chat": [
        ("cerebras", CEREBRAS_MODELS["fast"]),
        ("groq", GROQ_MODELS["fast"]),
        ("google", GOOGLE_MODELS["lite"]),
        ("openrouter", None),
    ],
}

# Default routing for any unrecognized role
DEFAULT_ROUTING = [
    ("cerebras", CEREBRAS_MODELS["primary"]),
    ("groq", GROQ_MODELS["primary"]),
    ("google", GOOGLE_MODELS["default"]),
    ("together", TOGETHER_MODELS["primary"]),
    ("openrouter", None),
]

# --- Database ---
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "secureshield.db")

# --- App ---
APP_NAME = "SecureShield"
APP_VERSION = "1.0.0"

# --- Cache ---
CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")
ENABLE_CACHE = os.getenv("ENABLE_CACHE", "true").lower() == "true"
