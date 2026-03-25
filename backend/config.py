"""
SecureShield Configuration
Loads environment variables and defines model routing constants.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Google AI Studio (Primary — fast, free, high limits) ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"

# --- OpenRouter API (Fallback) ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# --- Model Routing ---
# Primary: Google AI Studio Gemini models (fast, reliable)
# Fallback: OpenRouter free models
GOOGLE_MODELS = {
    "policy_ingestion": "gemini-2.0-flash",
    "case_analysis": "gemini-2.0-flash",
    "explanation": "gemini-2.0-flash",
}

OPENROUTER_MODELS = {
    "fallback_chain": [
        "qwen/qwen3-coder:free",
        "google/gemma-3-27b-it:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "mistralai/mistral-small-3.1-24b-instruct:free",
    ]
}

# --- Database ---
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "secureshield.db")

# --- App ---
APP_NAME = "SecureShield"
APP_VERSION = "1.0.0"
