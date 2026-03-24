"""
Security middleware and utilities for SecureShield.
- API key authentication
- Rate limiting per IP
- Input sanitization and prompt injection protection
- Request size limits
- Sensitive data masking in logs
"""

import time
import re
import hashlib
import logging
import secrets
from collections import defaultdict
from fastapi import Request, HTTPException, Depends
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from config import OPENROUTER_API_KEY

logger = logging.getLogger(__name__)

# --- API Key Management ---

# Generate a default API key on first run (stored in memory for prototype)
# In production, this would come from a secrets manager
_VALID_API_KEYS: set[str] = set()
_MASTER_API_KEY: str | None = None


def generate_api_key() -> str:
    """Generate a new API key."""
    key = f"ss_{secrets.token_urlsafe(32)}"
    _VALID_API_KEYS.add(key)
    return key


def get_or_create_master_key() -> str:
    """Get the master API key, creating one if needed."""
    global _MASTER_API_KEY
    if _MASTER_API_KEY is None:
        _MASTER_API_KEY = generate_api_key()
        logger.info(f"[Security] Master API key generated: {_MASTER_API_KEY[:12]}...")
    return _MASTER_API_KEY


def validate_api_key(key: str) -> bool:
    """Validate an API key."""
    return key in _VALID_API_KEYS


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str = Depends(api_key_header)):
    """Dependency that requires a valid API key."""
    if api_key is None:
        raise HTTPException(status_code=401, detail="Missing API key. Include X-API-Key header.")
    if not validate_api_key(api_key):
        raise HTTPException(status_code=403, detail="Invalid API key.")
    return api_key


# --- Rate Limiting ---

class RateLimiter:
    """
    In-memory sliding window rate limiter per IP address.
    Limits: 30 requests/minute, 200 requests/hour.
    """

    def __init__(self, per_minute: int = 30, per_hour: int = 200):
        self.per_minute = per_minute
        self.per_hour = per_hour
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _cleanup(self, ip: str, now: float):
        """Remove timestamps older than 1 hour."""
        cutoff = now - 3600
        self._requests[ip] = [t for t in self._requests[ip] if t > cutoff]

    def check(self, ip: str) -> tuple[bool, str]:
        """Check if the request is allowed. Returns (allowed, reason)."""
        now = time.time()
        self._cleanup(ip, now)

        timestamps = self._requests[ip]

        # Per-minute check
        recent_minute = [t for t in timestamps if t > now - 60]
        if len(recent_minute) >= self.per_minute:
            return False, f"Rate limit exceeded: {self.per_minute} requests/minute"

        # Per-hour check
        if len(timestamps) >= self.per_hour:
            return False, f"Rate limit exceeded: {self.per_hour} requests/hour"

        # Allow
        self._requests[ip].append(now)
        return True, "OK"


rate_limiter = RateLimiter()


# --- Rate Limiter Middleware ---

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limits."""

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health check
        if request.url.path == "/api/health":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        allowed, reason = rate_limiter.check(client_ip)

        if not allowed:
            logger.warning(f"[RateLimit] {client_ip} — {reason}")
            raise HTTPException(status_code=429, detail=reason)

        return await call_next(request)


# --- Input Sanitization ---

# Patterns that indicate prompt injection attempts
_INJECTION_PATTERNS = [
    r"ignore\s+(previous|above|all)\s+(instructions|prompts|rules)",
    r"you\s+are\s+now\s+a",
    r"forget\s+(everything|all|your)",
    r"system\s*:\s*",
    r"<\s*/?script",
    r"javascript\s*:",
    r"data\s*:\s*text/html",
    r"\{\{\s*.*\s*\}\}",  # Template injection
    r"IGNORE_PREVIOUS",
    r"OVERRIDE_SYSTEM",
]

_compiled_patterns = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]


def sanitize_text_input(text: str, field_name: str = "input") -> str:
    """
    Sanitize text input to prevent prompt injection and XSS.
    Raises ValueError if injection attempt is detected.
    """
    if not text:
        return text

    # Check for prompt injection
    for pattern in _compiled_patterns:
        if pattern.search(text):
            logger.warning(f"[Security] Prompt injection detected in {field_name}: {text[:100]}")
            raise ValueError(f"Invalid input detected in {field_name}. Please use standard medical/insurance terminology.")

    # Strip potentially dangerous characters (but allow medical notation)
    # Keep: letters, numbers, spaces, periods, commas, hyphens, parentheses, slashes, ₹, %
    cleaned = re.sub(r'[<>{}|\\`\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)

    return cleaned.strip()


def sanitize_case_input(case_data: dict) -> dict:
    """Sanitize all string fields in case input data."""
    sanitized = {}
    for key, value in case_data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_text_input(value, key)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_text_input(v, key) if isinstance(v, str) else v
                for v in value
            ]
        else:
            sanitized[key] = value
    return sanitized


# --- Sensitive Data Masking ---

def mask_patient_data(data: dict) -> dict:
    """Mask sensitive patient data for logging purposes."""
    masked = data.copy()
    sensitive_fields = ["patient_name", "hospital_name", "policy_start_date"]
    for field in sensitive_fields:
        if field in masked and masked[field]:
            value = str(masked[field])
            if len(value) > 3:
                masked[field] = value[:2] + "***" + value[-1:]
            else:
                masked[field] = "***"
    return masked


# --- File Upload Validation ---

MAX_PDF_SIZE_MB = 20
MAX_PDF_SIZE_BYTES = MAX_PDF_SIZE_MB * 1024 * 1024
ALLOWED_MIME_TYPES = {"application/pdf"}

# PDF magic bytes
PDF_MAGIC = b"%PDF"


def validate_pdf_upload(content: bytes, filename: str) -> None:
    """
    Validate an uploaded PDF file:
    1. Size check
    2. Magic bytes check (is it actually a PDF?)
    3. Filename sanitization
    """
    # Size check
    if len(content) > MAX_PDF_SIZE_BYTES:
        raise ValueError(
            f"File too large: {len(content) / 1024 / 1024:.1f}MB "
            f"(max {MAX_PDF_SIZE_MB}MB)"
        )

    # Empty file check
    if len(content) < 100:
        raise ValueError("File appears to be empty or corrupted")

    # Magic bytes — verify it's actually a PDF
    if not content[:4].startswith(PDF_MAGIC):
        raise ValueError("File is not a valid PDF document")

    # Filename sanitization
    safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    if not safe_filename.lower().endswith('.pdf'):
        raise ValueError("Only .pdf files are accepted")

    logger.info(f"[Security] PDF validated: {safe_filename} ({len(content)/1024:.0f}KB)")
