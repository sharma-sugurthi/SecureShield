"""
Audit Tools — Compliance and traceability tools for the orchestrator.

Tool:
12. audit_trail_logger — Log every agent action with timestamps for compliance
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# In-memory audit trail (in production, this would be a database table)
_AUDIT_TRAIL: list[dict] = []
_AUDIT_COUNTER = 0


def audit_trail_logger(
    agent_name: str,
    action: str,
    input_summary: str,
    output_summary: str,
    tools_used: list[str] | None = None,
    duration_ms: float | None = None,
    status: str = "success",
    metadata: dict | None = None,
) -> dict:
    """
    Log an agent action for compliance and auditability.
    Every step in the pipeline is recorded with full traceability.
    
    Args:
        agent_name: Name of the agent (e.g., "PolicyAgent", "CaseAgent")
        action: What the agent did (e.g., "extract_rules", "normalize_facts")
        input_summary: Brief summary of the input (masked for PII)
        output_summary: Brief summary of the output
        tools_used: List of tools the agent invoked
        duration_ms: How long the action took
        status: "success", "failure", or "partial"
        metadata: Additional context (rule counts, model used, etc.)
    
    Returns:
        {
            "audit_id": str,
            "logged": True,
            "timestamp": str
        }
    """
    global _AUDIT_COUNTER
    _AUDIT_COUNTER += 1
    
    timestamp = datetime.now(timezone.utc).isoformat()
    audit_id = f"AUD-{_AUDIT_COUNTER:06d}"

    record = {
        "audit_id": audit_id,
        "timestamp": timestamp,
        "agent_name": agent_name,
        "action": action,
        "input_summary": input_summary[:500],  # Truncate for storage
        "output_summary": output_summary[:500],
        "tools_used": tools_used or [],
        "duration_ms": duration_ms,
        "status": status,
        "metadata": metadata or {},
    }

    _AUDIT_TRAIL.append(record)
    
    # Also log to standard logger for file-based logging
    logger.info(
        f"[AUDIT] {audit_id} | {agent_name}.{action} | "
        f"Tools: {','.join(tools_used or ['none'])} | "
        f"Status: {status} | "
        f"Duration: {duration_ms:.0f}ms" if duration_ms else 
        f"[AUDIT] {audit_id} | {agent_name}.{action} | "
        f"Tools: {','.join(tools_used or ['none'])} | "
        f"Status: {status}"
    )

    return {
        "audit_id": audit_id,
        "logged": True,
        "timestamp": timestamp,
    }


def get_audit_trail(limit: int = 50) -> list[dict]:
    """Get recent audit trail entries."""
    return _AUDIT_TRAIL[-limit:]


def get_audit_by_id(audit_id: str) -> dict | None:
    """Look up a specific audit record."""
    for record in _AUDIT_TRAIL:
        if record["audit_id"] == audit_id:
            return record
    return None


def get_pipeline_audit(pipeline_run_id: str) -> list[dict]:
    """Get all audit records for a specific pipeline run."""
    return [
        r for r in _AUDIT_TRAIL
        if r.get("metadata", {}).get("pipeline_run_id") == pipeline_run_id
    ]
