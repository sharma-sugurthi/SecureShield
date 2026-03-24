"""
SecureShield Configuration
Loads environment variables and defines model routing constants.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- OpenRouter API ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# --- Model Routing ---
# Each agent uses the best free model for its specific task.
MODELS = {
    # Deep document analysis — 1M context window for full policy PDFs
    "policy_ingestion": "google/gemini-2.0-flash-exp:free",
    
    # Structured extraction — best reasoning for JSON extraction
    "case_analysis": "meta-llama/llama-4-maverick:free",
    
    # Patient-friendly explanations — natural conversational tone
    "explanation": "mistralai/mistral-small-3.1-24b-instruct:free",
    
    # Fallback / general-purpose
    "fallback": "deepseek/deepseek-chat-v3-0324:free",
}

# --- Database ---
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "secureshield.db")

# --- App ---
APP_NAME = "SecureShield"
APP_VERSION = "1.0.0"
