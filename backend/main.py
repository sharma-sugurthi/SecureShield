"""
SecureShield — FastAPI Backend (Production-Grade)
REST API with security middleware, rate limiting, and input validation.
"""

import json
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware

from config import APP_NAME, APP_VERSION

class ProfileUpdate(BaseModel):
    full_name: str
    phone: str
    dob: str
    address: str
    avatar_base64: Optional[str] = None

from db.database import init_db, get_all_policies, get_policy, get_check_history
from db.llm_cache import init_llm_cache
from agents.policy_agent import ingest_policy
from agents.orchestrator import run_eligibility_check
from models.policy import PolicyUploadResponse
from models.case import EligibilityCheckRequest
from models.verdict import EligibilityResponse
from models.grievance import GrievanceRequest, GrievanceResponse
from models.chat import ChatRequest, ChatResponse
from security import (
    get_or_create_master_key,
    verify_jwt_token,
    verify_jwt_token_optional,
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
    """Initialize database, vector store, and security on startup."""
    await init_db()
    await init_llm_cache()
    master_key = get_or_create_master_key()
    
    # Index IRDAI knowledge base into pgvector (idempotent)
    try:
        from utils.vector_store import index_irdai_knowledge
        index_irdai_knowledge()
    except Exception as e:
        logger.warning(f"Vector store indexing skipped: {e}")
    
    # Activate local Ollama if USE_OLLAMA=true (git-ignored, demo only)
    try:
        from ollama_local import patch_model_router
        patch_model_router()
    except ImportError:
        pass  # ollama_local.py doesn't exist (normal for production/GitHub)
    
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

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

# Note: Middlewares are executed in reverse order of addition.
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

# CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://192.168.1.13:3000"],
    allow_credentials=True,
    allow_methods=["*"],
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


@app.get("/api/auto-key")
async def get_auto_key():
    """Return the master API key for local development.
    
    This allows the frontend to auto-configure without manual copy-paste.
    In production, this endpoint should be disabled or protected.
    """
    return {"api_key": get_or_create_master_key()}


@app.get("/api/system-info")
async def get_system_info(user: dict = Depends(verify_jwt_token)):
    """Return system-level stats for the dashboard (scoped to user)."""
    from db.llm_cache import get_cache_stats
    
    user_id = user.get("sub", "")
    policies = await get_all_policies(user_id=user_id)
    history = await get_check_history(100, user_id=user_id)
    cache_stats = await get_cache_stats()
    
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "total_policies": len(policies),
        "total_checks": len(history),
        "agents": 5,
        "tools": 18,
        "cache": cache_stats,
        "providers": ["Cerebras", "Groq", "Gemini", "xAI", "OpenRouter"],
    }


# --- User Endpoints ---

@app.post("/api/users/welcome")
async def send_welcome(user: dict = Depends(verify_jwt_token)):
    """Trigger a welcome email (zero-cost mailing)."""
    from utils.mailer import send_welcome_email
    email = user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="No email associated with user.")
    await send_welcome_email(email)
    return {"status": "ok", "message": "Welcome email dispatched."}

@app.get("/api/profile")
async def get_profile(user: dict = Depends(verify_jwt_token)):
    """Retrieve user profile from Postgres."""
    user_id = user.get("sub", "")
    from db.database import get_user_profile
    profile = await get_user_profile(user_id)
    if not profile:
        return {}
    return profile

@app.post("/api/profile")
async def update_profile(data: ProfileUpdate, user: dict = Depends(verify_jwt_token)):
    """Save user profile to Postgres."""
    user_id = user.get("sub", "")
    from db.database import save_user_profile
    await save_user_profile(
        user_id=user_id,
        full_name=data.full_name,
        phone=data.phone,
        dob=data.dob,
        address=data.address,
        avatar_base64=data.avatar_base64
    )
    return {"status": "ok", "message": "Profile updated in Postgres"}


# --- Authenticated Endpoints ---

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}


@app.post("/api/upload-policy", response_model=PolicyUploadResponse)
async def upload_policy(
    file: UploadFile = File(...),
    user: dict = Depends(verify_jwt_token),
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

        # Upload PDF to Supabase Storage (cloud)
        pdf_url = None
        try:
            from utils.storage import upload_pdf
            storage_result = upload_pdf(pdf_bytes, file.filename)
            pdf_url = storage_result.get("public_url")
            logger.info(f"[API] PDF stored in cloud: {pdf_url}")
        except Exception as e:
            logger.warning(f"[API] Cloud storage failed, continuing without: {e}")

        policy = await ingest_policy(pdf_bytes, file.filename, pdf_storage_url=pdf_url,
                                     user_id=user.get("sub", ""))

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
async def list_policies(user: dict = Depends(verify_jwt_token)):
    """List all ingested policies for the authenticated user."""
    user_id = user.get("sub", "")
    policies = await get_all_policies(user_id=user_id)
    return {"policies": policies, "count": len(policies)}


@app.get("/api/policies/{policy_id}")
async def get_policy_details(
    policy_id: int,
    user: dict = Depends(verify_jwt_token),
):
    """Get full details of a specific policy including extracted rules."""
    user_id = user.get("sub", "")
    policy = await get_policy(policy_id, user_id=user_id)
    if policy is None:
        raise HTTPException(status_code=404, detail=f"Policy #{policy_id} not found")
    return policy


@app.post("/api/check-eligibility", response_model=EligibilityResponse)
async def check_eligibility(
    request: EligibilityCheckRequest,
    user: dict = Depends(verify_jwt_token),
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
            user_id=user.get("sub", ""),
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
    user: dict = Depends(verify_jwt_token),
):
    """Get recent eligibility check history for the authenticated user."""
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
    user_id = user.get("sub", "")
    history = await get_check_history(limit, user_id=user_id)
    return {"checks": history, "count": len(history)}


@app.get("/api/audit-trail")
async def get_audit_trail(
    limit: int = 50,
    user: dict = Depends(verify_jwt_token),
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


# --- Grievance Agent Endpoints ---

@app.post("/api/dispute-claim", response_model=GrievanceResponse)
async def dispute_claim(
    request: GrievanceRequest,
    user: dict = Depends(verify_jwt_token),
):
    """
    Trigger the Grievance Agent pipeline for a denied/partial claim.
    
    The Grievance Agent will:
    1. Analyze the verdict for compliance violations
    2. Search for IRDAI precedent rulings
    3. Draft a formal grievance letter (LLM)
    4. Generate a professional PDF report
    5. "Send" the grievance email (mocked)
    
    Requires: X-API-Key header
    """
    from agents.grievance_agent import run_grievance_pipeline
    
    if request.overall_verdict == "APPROVED" and request.coverage_percentage >= 95:
        raise HTTPException(
            status_code=400,
            detail="This claim was fully approved. Grievance is not applicable."
        )
    
    try:
        logger.info(f"[API] Grievance pipeline: policy #{request.policy_id}, "
                    f"verdict={request.overall_verdict}, denied=₹{request.total_denied:,.0f}")
        
        result = await run_grievance_pipeline(
            patient_name=request.patient_name,
            patient_age=request.patient_age,
            procedure=request.procedure,
            hospital_name=request.hospital_name,
            insurer=request.insurer,
            policy_name=request.policy_name,
            total_claimed=request.total_claimed,
            total_eligible=request.total_eligible,
            total_denied=request.total_denied,
            coverage_percentage=request.coverage_percentage,
            overall_verdict=request.overall_verdict,
            matched_rules=request.matched_rules,
            explanation=request.explanation,
            suggestions=request.suggestions,
        )
        
        # Email the grievance package if user has an email
        if user.get("type") == "jwt" and user.get("email"):
            import os
            from utils.mailer import send_grievance_email
            from tools.grievance_tools import REPORTS_DIR
            pdf_path = os.path.join(REPORTS_DIR, result["pdf_filename"])
            insurer_email = result.get("email_status", {}).get("recipient", None)
            
            # Send email to user, CC the insurer
            await send_grievance_email(user["email"], pdf_path, cc_email=insurer_email)
            
        return GrievanceResponse(**result)
    
    except Exception as e:
        logger.error(f"[API] Grievance pipeline failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Grievance pipeline failed: {str(e)}",
        )


@app.get("/api/chat/threads")
async def get_threads(user: dict = Depends(verify_jwt_token)):
    from db.database import get_chat_threads
    user_id = user.get("sub", "")
    threads = await get_chat_threads(user_id)
    return {"threads": threads}

@app.post("/api/chat/threads/{thread_id}/delete")
async def delete_thread(thread_id: int, user: dict = Depends(verify_jwt_token)):
    from db.database import delete_chat_thread
    await delete_chat_thread(thread_id)
    return {"status": "success"}


@app.get("/api/chat/threads/{thread_id}")
async def get_thread_messages(thread_id: int, user: dict = Depends(verify_jwt_token)):
    from db.database import get_chat_messages
    messages = await get_chat_messages(thread_id)
    return {"messages": messages}


@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_assistant(
    request: ChatRequest,
    user: dict = Depends(verify_jwt_token_optional),
):
    """
    Chat with the SecureShield AI Medical Assistant.
    Uses a 3-tier hierarchy: FAQ Cache -> Cerebras (Free) -> Gemini.
    """
    from agents.chat_agent import handle_chat_query
    from db.database import create_chat_thread, save_chat_message, get_chat_messages
    
    try:
        logger.info(f"[API] Chat query: '{request.query[:50]}...'")
        
        thread_id = request.thread_id
        history = []
        user_id = None
        
        if user and user.get("sub"):
            user_id = user.get("sub")
            if not thread_id:
                # Generate a quick title
                title = " ".join(request.query.split()[:5]) + "..."
                thread_id = await create_chat_thread(user_id, title)
            else:
                # Load history
                history = await get_chat_messages(thread_id)
            
            # Save user message
            await save_chat_message(thread_id, "user", request.query)
            
        result = await handle_chat_query(request.query, history=history, user_id=user_id)
        
        if thread_id:
            # Save assistant message
            await save_chat_message(thread_id, "assistant", result["answer"], result.get("method"), result.get("duration_ms"))
            result["thread_id"] = thread_id
            
        return result
    except Exception as e:
        logger.error(f"[API] Chat failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Chat assistant failed: {str(e)}",
        )


@app.get("/api/download-report/{filename}")
async def download_report(
    filename: str,
    # Allow passing token via query param for direct download links
    token: str = None,
    api_key: str = None,
):
    """
    Download a generated PDF claim report.
    Since it's a GET request often used in a href, we accept token/api_key via query params.
    """
    from security import validate_api_key, SUPABASE_JWT_SECRET
    import jwt
    
    # Custom auth for this endpoint
    authenticated = False
    if api_key and validate_api_key(api_key):
        authenticated = True
    elif token and SUPABASE_JWT_SECRET:
        try:
            jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"], options={"verify_aud": False})
            authenticated = True
        except:
            pass
            
    if not authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized download")
    from tools.grievance_tools import REPORTS_DIR
    
    # Security: prevent path traversal
    safe_filename = os.path.basename(filename)
    filepath = os.path.join(REPORTS_DIR, safe_filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Report not found")
    
    return FileResponse(
        path=filepath,
        media_type="application/pdf",
        filename=safe_filename,
    )


# --- MCP Server (Model Context Protocol) ---
# Exposes all API endpoints as tools callable by AI assistants
# (Claude Desktop, Cursor, etc.) via the /mcp endpoint.
try:
    from fastapi_mcp import FastApiMCP
    mcp = FastApiMCP(app)
    mcp.mount()
    logger.info("[MCP] MCP server mounted at /mcp")
except ImportError:
    logger.info("[MCP] fastapi-mcp not installed, MCP server disabled")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, reload_excludes=["*.db"])
