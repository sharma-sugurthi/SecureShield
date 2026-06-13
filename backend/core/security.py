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
import os
from collections import defaultdict
from fastapi import Request, HTTPException, Depends
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from core.config import OPENROUTER_API_KEY, SUPABASE_JWT_SECRET

logger = logging.getLogger(__name__)

# Initialize a global Supabase client for RS256 token verification
_supabase_client = None
def get_supabase_client():
    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
        if supabase_url and supabase_key:
            _supabase_client = create_client(supabase_url, supabase_key)
    return _supabase_client

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
security_bearer = HTTPBearer(auto_error=False)

async def require_api_key(api_key: str = Depends(api_key_header)):
    """Legacy dependency that requires a valid API key (for development/scripts)."""
    if api_key is None:
        raise HTTPException(status_code=401, detail="Missing API key. Include X-API-Key header.")
    if not validate_api_key(api_key):
        raise HTTPException(status_code=403, detail="Invalid API key.")
    return api_key


async def verify_jwt_token(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
    api_key: str = Depends(api_key_header),
):
    """
    Validates either a Supabase JWT (Authorization: Bearer <token>) OR a valid API Key.
    Returns a dict with user context if authenticated via JWT, or string if API key.
    """
    # 1. Check for API key (backward compatibility for local scripts/MCP)
    if api_key and validate_api_key(api_key):
        return {"type": "api_key", "sub": "api_client"}
        
    # 2. Check for JWT (Production Frontend)
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authentication token.")
        
    token = credentials.credentials
    
    if not SUPABASE_JWT_SECRET:
        # If no JWT secret is configured, fallback to accepting the master key only,
        # but since we got here, they didn't provide a valid API key.
        raise HTTPException(status_code=500, detail="Server not configured for JWT auth (missing SUPABASE_JWT_SECRET).")
        
    try:
        unverified_header = jwt.get_unverified_header(token)
        alg = unverified_header.get("alg", "HS256")
        
        if alg == "HS256":
            # Verify using symmetric secret
            payload = jwt.decode(
                token, 
                SUPABASE_JWT_SECRET, 
                algorithms=["HS256"], 
                options={"verify_aud": False}
            )
            return {"type": "jwt", "sub": payload.get("sub"), "email": payload.get("email")}
        else:
            # For RS256 tokens, verify securely via Supabase Auth network call
            supabase = get_supabase_client()
            if not supabase:
                raise HTTPException(status_code=500, detail="Missing Supabase URL/Key to verify RS256 tokens securely.")
                
            try:
                from fastapi.concurrency import run_in_threadpool
                import asyncio
                
                user_res = None
                for attempt in range(3):
                    try:
                        user_res = await run_in_threadpool(supabase.auth.get_user, token)
                        break
                    except Exception as e:
                        if attempt == 2:
                            raise e
                        await asyncio.sleep(0.2)
                
                if user_res and user_res.user:
                    return {"type": "jwt", "sub": user_res.user.id, "email": user_res.user.email}
                else:
                    raise HTTPException(status_code=401, detail="Invalid token.")
            except Exception as e:
                logger.error(f"Supabase Auth verification failed: {e}")
                raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired.")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


async def verify_jwt_token_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
    api_key: str = Depends(api_key_header),
):
    """Same as verify_jwt_token, but returns None instead of raising an error if auth fails."""
    try:
        return await verify_jwt_token(credentials, api_key)
    except HTTPException:
        return None

# --- Rate Limiting ---

class RateLimiter:
    """
    In-memory sliding window rate limiter per IP address.
    Limits: 30 requests/minute, 200 requests/hour.
    """

    def __init__(self, default_per_minute: int = 60, default_per_hour: int = 300):
        self.default_per_minute = default_per_minute
        self.default_per_hour = default_per_hour
        # Track by key: f"{ip}:{path}"
        self._requests: dict[str, list[float]] = defaultdict(list)
        
        # Strict endpoint limits
        self.endpoint_limits = {
            "/api/check-eligibility": {"min": 5, "hour": 20},
            "/api/chat": {"min": 15, "hour": 60},
            "/api/upload-policy": {"min": 10, "hour": 30},
        }

    def _cleanup(self, key: str, now: float):
        """Remove timestamps older than 1 hour."""
        cutoff = now - 3600
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]

    def check(self, ip: str, path: str) -> tuple[bool, str]:
        """Check if the request is allowed. Returns (allowed, reason)."""
        now = time.time()
        
        # We apply rate limits globally per IP, and per IP+path
        global_key = ip
        path_key = f"{ip}:{path}"
        
        self._cleanup(global_key, now)
        self._cleanup(path_key, now)

        # Global limits check
        global_timestamps = self._requests[global_key]
        if len([t for t in global_timestamps if t > now - 60]) >= self.default_per_minute:
            return False, "Global rate limit exceeded."
        if len(global_timestamps) >= self.default_per_hour:
            return False, "Global rate limit exceeded."

        # Path limits check
        path_limits = self.endpoint_limits.get(path)
        if path_limits:
            path_timestamps = self._requests[path_key]
            if len([t for t in path_timestamps if t > now - 60]) >= path_limits["min"]:
                return False, f"Rate limit exceeded for {path}: {path_limits['min']} requests/minute allowed."
            if len(path_timestamps) >= path_limits["hour"]:
                return False, f"Rate limit exceeded for {path}: {path_limits['hour']} requests/hour allowed."

        # Allow
        self._requests[global_key].append(now)
        if path_limits:
            self._requests[path_key].append(now)
            
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
        allowed, reason = rate_limiter.check(client_ip, request.url.path)

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
    r"base64[=:]",        # Catch base64 encoded attacks
    r"hex\s*(decode|encode)",
    r"(exec|eval|os\.system|subprocess)\(",
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
