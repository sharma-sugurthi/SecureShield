"""
SecureShield — FastAPI Backend (Production-Grade)
REST API with security middleware, rate limiting, and input validation.
"""

import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

from config import APP_NAME, APP_VERSION
from db.database import init_db, get_all_policies, get_policy, get_check_history
from agents.policy_agent import ingest_policy
from agents.orchestrator import run_eligibility_check
from models.policy import PolicyUploadResponse
from models.case import EligibilityCheckRequest
from models.verdict import EligibilityResponse
from security import (
    get_or_create_master_key,
    require_api_key,
    RateLimitMiddleware,
    sanitize_case_input,
    validate_pdf_upload,
    MAX_PDF_SIZE_BYTES,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and security on startup."""
    await init_db()
    master_key = get_or_create_master_key()
    logger.info(f"🛡️  {APP_NAME} v{APP_VERSION} started")
    logger.info(f"🔑 Master API Key: {master_key}")
    logger.info(f"   Use this key in the X-API-Key header for authenticated endpoints.")
    yield
    logger.info(f"🛡️  {APP_NAME} shutting down")


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=(
        "SecureShield: GenAI-powered health insurance claim eligibility checker "
        "for Indian patients. Uses a neuro-symbolic architecture with deterministic "
        "decision engine for zero-hallucination verdicts."
    ),
    lifespan=lifespan,
)

# --- Middleware ---

# Rate limiting
app.add_middleware(RateLimitMiddleware)

# CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=["X-Request-Id"],
)


# --- Public Endpoints (No Auth) ---

@app.get("/api/health")
async def health_check():
    """Health check endpoint — no authentication required."""
    return {
        "status": "healthy",
        "app": APP_NAME,
        "version": APP_VERSION,
        "security": "enabled",
    }


# --- Authenticated Endpoints ---

@app.post("/api/upload-policy", response_model=PolicyUploadResponse)
async def upload_policy(
    file: UploadFile = File(...),
    _api_key: str = Depends(require_api_key),
):
    """
    Upload and process a health insurance policy PDF.
    Extracts structured rules using the Policy Ingestion Agent.
    
    Requires: X-API-Key header
    Accepts: PDF files up to 20MB
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted. Please upload a .pdf file.",
        )

    try:
        pdf_bytes = await file.read()
        
        # Security: validate PDF
        try:
            validate_pdf_upload(pdf_bytes, file.filename)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        logger.info(f"[API] Policy upload: {file.filename} ({len(pdf_bytes)/1024:.0f}KB)")

        policy = await ingest_policy(pdf_bytes, file.filename)

        return PolicyUploadResponse(
            policy_id=policy.id,
            insurer=policy.insurer,
            plan_name=policy.plan_name,
            sum_insured=policy.sum_insured,
            rules_count=len(policy.rules),
            message=f"Successfully extracted {len(policy.rules)} rules from {file.filename}",
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[API] Policy upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process policy document. Please try again or use a different file.",
        )


@app.get("/api/policies")
async def list_policies(_api_key: str = Depends(require_api_key)):
    """List all ingested policies. Requires: X-API-Key header"""
    policies = await get_all_policies()
    return {"policies": policies, "count": len(policies)}


@app.get("/api/policies/{policy_id}")
async def get_policy_details(
    policy_id: int,
    _api_key: str = Depends(require_api_key),
):
    """Get full details of a specific policy including extracted rules."""
    policy = await get_policy(policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail=f"Policy #{policy_id} not found")
    return policy


@app.post("/api/check-eligibility", response_model=EligibilityResponse)
async def check_eligibility(
    request: EligibilityCheckRequest,
    _api_key: str = Depends(require_api_key),
):
    """
    Check claim eligibility against an ingested policy.
    
    Runs the full agent pipeline:
    1. Case Analysis Agent → extracts structured facts
    2. Decision Engine → deterministic verdict (no LLM)
    3. Explanation Agent → patient-friendly explanation
    
    Requires: X-API-Key header
    """
    try:
        # Sanitize input
        sanitized_case = sanitize_case_input(request.case.model_dump())
        
        logger.info(f"[API] Eligibility check: policy #{request.policy_id}, "
                    f"procedure={sanitized_case.get('procedure', 'N/A')}")
        
        result = await run_eligibility_check(
            policy_id=request.policy_id,
            case_input=sanitized_case,
        )
        
        return result
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[API] Eligibility check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Eligibility check failed: {str(e)}",
        )


@app.get("/api/history")
async def get_history(
    limit: int = 20,
    _api_key: str = Depends(require_api_key),
):
    """Get recent eligibility check history. Requires: X-API-Key header"""
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
    history = await get_check_history(limit)
    return {"checks": history, "count": len(history)}


@app.get("/api/audit-trail")
async def get_audit_trail(
    limit: int = 50,
    _api_key: str = Depends(require_api_key),
):
    """
    Get the agent audit trail — every tool call, LLM invocation, and decision
    made by the agentic pipeline, with timestamps and traceability.
    
    This demonstrates the agentic system's transparency and compliance.
    Requires: X-API-Key header
    """
    from tools.audit_tools import get_audit_trail as _get_trail
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 200")
    trail = _get_trail(limit)
    return {
        "audit_trail": trail,
        "count": len(trail),
        "description": "Every agent action, tool call, and decision is logged for compliance traceability.",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
