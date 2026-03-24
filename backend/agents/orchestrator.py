"""
Agent Orchestrator — LangGraph state machine coordinating the agentic pipeline.

Pipeline: Policy Lookup → Case Analysis (with tools) → Decision Engine → Explanation (with tools) → Response

Every node uses custom tools. Every step is audited.
"""

import json
import logging
import time
import uuid
from typing import TypedDict
from langgraph.graph import StateGraph, END

from agents.policy_agent import ingest_policy
from agents.case_agent import extract_case_facts
from agents.explanation_agent import generate_explanation
from engine.decision_engine import evaluate
from models.case import CaseFacts
from models.verdict import Verdict, EligibilityResponse
from db.database import get_policy, save_eligibility_check
from tools.audit_tools import audit_trail_logger

logger = logging.getLogger(__name__)


# --- State Definition ---

class PipelineState(TypedDict):
    """State passed through the orchestrator pipeline."""
    # Identity
    pipeline_run_id: str
    
    # Input
    policy_id: int
    case_input: dict
    
    # Intermediate (enriched by tools)
    policy_data: dict | None
    case_facts: dict | None
    verdict: dict | None
    
    # Output
    explanation: str
    suggestions: list[str]
    error: str | None
    
    # Tool tracking
    tools_invoked: list[str]
    step: str


# --- Node Functions ---

async def load_policy_node(state: PipelineState) -> dict:
    """Load policy rules from database."""
    run_id = state["pipeline_run_id"]
    logger.info(f"[Orchestrator:{run_id}] Step 1: Loading policy #{state['policy_id']}")
    
    t0 = time.time()
    policy = await get_policy(state["policy_id"])
    t1 = time.time()
    
    if policy is None:
        audit_trail_logger(
            agent_name="Orchestrator", action="load_policy",
            input_summary=f"Policy ID: {state['policy_id']}",
            output_summary="FAILED — Policy not found",
            tools_used=["get_policy"],
            duration_ms=(t1 - t0) * 1000,
            status="failure",
            metadata={"pipeline_run_id": run_id},
        )
        return {
            "error": f"Policy #{state['policy_id']} not found. Please upload the policy first.",
            "step": "error",
            "tools_invoked": state.get("tools_invoked", []) + ["get_policy"],
        }
    
    audit_trail_logger(
        agent_name="Orchestrator", action="load_policy",
        input_summary=f"Policy ID: {state['policy_id']}",
        output_summary=f"Loaded: {policy['plan_name']} by {policy['insurer']}, "
                       f"SI: ₹{policy['sum_insured']:,.0f}, {len(policy.get('rules', []))} rules",
        tools_used=["get_policy"],
        duration_ms=(t1 - t0) * 1000,
        metadata={"pipeline_run_id": run_id},
    )
    
    return {
        "policy_data": policy,
        "step": "analyze_case",
        "error": None,
        "tools_invoked": state.get("tools_invoked", []) + ["get_policy"],
    }


async def analyze_case_node(state: PipelineState) -> dict:
    """
    Extract structured facts using Case Agent (with tool pipeline):
    - medical_term_normalizer
    - icd_procedure_lookup
    - city_tier_classifier
    - hospital_cost_estimator
    """
    run_id = state["pipeline_run_id"]
    logger.info(f"[Orchestrator:{run_id}] Step 2: Analyzing case with tools")
    
    t0 = time.time()
    try:
        case_facts = await extract_case_facts(state["case_input"])
        t1 = time.time()
        
        audit_trail_logger(
            agent_name="Orchestrator", action="analyze_case",
            input_summary=f"Raw case with {len(state['case_input'])} fields",
            output_summary=f"CaseFacts: {case_facts.procedure}, ₹{case_facts.total_claimed_amount:,.0f}, "
                          f"{case_facts.room_type.value}",
            tools_used=["CaseAgent (medical_term_normalizer → icd_procedure_lookup → "
                       "city_tier_classifier → hospital_cost_estimator)"],
            duration_ms=(t1 - t0) * 1000,
            metadata={"pipeline_run_id": run_id},
        )
        
        return {
            "case_facts": case_facts.model_dump(),
            "step": "decide",
            "error": None,
            "tools_invoked": state.get("tools_invoked", []) + [
                "medical_term_normalizer", "icd_procedure_lookup",
                "city_tier_classifier", "hospital_cost_estimator",
            ],
        }
    except Exception as e:
        t1 = time.time()
        logger.error(f"[Orchestrator:{run_id}] Case analysis failed: {e}")
        audit_trail_logger(
            agent_name="Orchestrator", action="analyze_case",
            input_summary=f"Raw case with {len(state['case_input'])} fields",
            output_summary=f"FAILED: {str(e)[:200]}",
            tools_used=["CaseAgent"],
            duration_ms=(t1 - t0) * 1000,
            status="failure",
            metadata={"pipeline_run_id": run_id},
        )
        return {
            "error": f"Failed to analyze case details: {str(e)}",
            "step": "error",
            "tools_invoked": state.get("tools_invoked", []),
        }


async def decision_node(state: PipelineState) -> dict:
    """Run deterministic decision engine (IS a tool itself — no LLM)."""
    run_id = state["pipeline_run_id"]
    logger.info(f"[Orchestrator:{run_id}] Step 3: Running Decision Engine (deterministic)")
    
    t0 = time.time()
    try:
        policy = state["policy_data"]
        facts = CaseFacts(**state["case_facts"])
        rules = policy["rules"]
        sum_insured = policy["sum_insured"]
        
        verdict = evaluate(rules, facts, sum_insured)
        t1 = time.time()
        
        audit_trail_logger(
            agent_name="Orchestrator", action="decision_engine",
            input_summary=f"{len(rules)} rules vs {facts.procedure} (₹{facts.total_claimed_amount:,.0f})",
            output_summary=f"Verdict: {verdict.overall_verdict.value}, "
                          f"coverage: {verdict.coverage_percentage}%, "
                          f"eligible: ₹{verdict.total_eligible:,.0f}",
            tools_used=["decision_engine (deterministic — no LLM)"],
            duration_ms=(t1 - t0) * 1000,
            metadata={"pipeline_run_id": run_id},
        )
        
        return {
            "verdict": verdict.model_dump(),
            "step": "explain",
            "error": None,
            "tools_invoked": state.get("tools_invoked", []) + ["decision_engine"],
        }
    except Exception as e:
        t1 = time.time()
        logger.error(f"[Orchestrator:{run_id}] Decision engine failed: {e}")
        return {
            "error": f"Decision engine error: {str(e)}",
            "step": "error",
            "tools_invoked": state.get("tools_invoked", []),
        }


async def explanation_node(state: PipelineState) -> dict:
    """
    Generate explanation using Explanation Agent (with tool pipeline):
    - clause_explainer
    - savings_calculator (which internally uses what_if_analyzer)
    - LLM generation
    """
    run_id = state["pipeline_run_id"]
    logger.info(f"[Orchestrator:{run_id}] Step 4: Generating explanation with tools")
    
    t0 = time.time()
    try:
        verdict = Verdict(**state["verdict"])
        policy = state["policy_data"]
        
        result = await generate_explanation(
            verdict=verdict,
            policy_name=policy["plan_name"],
            insurer=policy["insurer"],
            rules=policy.get("rules"),
            original_facts=state.get("case_facts"),
            sum_insured=policy.get("sum_insured", 0),
        )
        t1 = time.time()
        
        # Save to history
        await save_eligibility_check(
            policy_id=state["policy_id"],
            case_json=json.dumps(state["case_facts"]),
            verdict_json=json.dumps(state["verdict"]),
            explanation=result["explanation"],
        )
        
        audit_trail_logger(
            agent_name="Orchestrator", action="generate_explanation",
            input_summary=f"Verdict: {verdict.overall_verdict.value}, "
                         f"coverage: {verdict.coverage_percentage}%",
            output_summary=f"Explanation: {len(result['explanation'])} chars, "
                          f"{len(result['suggestions'])} suggestions",
            tools_used=["ExplanationAgent (clause_explainer → savings_calculator → "
                       "what_if_analyzer → LLM)"],
            duration_ms=(t1 - t0) * 1000,
            metadata={"pipeline_run_id": run_id},
        )
        
        return {
            "explanation": result["explanation"],
            "suggestions": result["suggestions"],
            "step": "done",
            "error": None,
            "tools_invoked": state.get("tools_invoked", []) + [
                "clause_explainer", "savings_calculator", "what_if_analyzer",
            ],
        }
    except Exception as e:
        t1 = time.time()
        logger.error(f"[Orchestrator:{run_id}] Explanation failed: {e}")
        verdict = Verdict(**state["verdict"])
        return {
            "explanation": verdict.summary,
            "suggestions": ["Please consult your insurance provider for more details."],
            "step": "done",
            "error": None,
            "tools_invoked": state.get("tools_invoked", []),
        }


# --- Routing ---

def route_after_policy(state: PipelineState) -> str:
    if state.get("error"):
        return "end"
    return "analyze_case"


def route_after_case(state: PipelineState) -> str:
    if state.get("error"):
        return "end"
    return "decide"


def route_after_decision(state: PipelineState) -> str:
    if state.get("error"):
        return "end"
    return "explain"


# --- Build Graph ---

def build_pipeline() -> StateGraph:
    """Build the LangGraph agentic pipeline."""
    
    workflow = StateGraph(PipelineState)
    
    # Add nodes
    workflow.add_node("load_policy", load_policy_node)
    workflow.add_node("analyze_case", analyze_case_node)
    workflow.add_node("decide", decision_node)
    workflow.add_node("explain", explanation_node)
    
    # Set entry point
    workflow.set_entry_point("load_policy")
    
    # Conditional edges
    workflow.add_conditional_edges("load_policy", route_after_policy, {
        "analyze_case": "analyze_case",
        "end": END,
    })
    workflow.add_conditional_edges("analyze_case", route_after_case, {
        "decide": "decide",
        "end": END,
    })
    workflow.add_conditional_edges("decide", route_after_decision, {
        "explain": "explain",
        "end": END,
    })
    workflow.add_edge("explain", END)
    
    return workflow.compile()


# Singleton pipeline
pipeline = build_pipeline()


async def run_eligibility_check(policy_id: int, case_input: dict) -> EligibilityResponse:
    """
    Run the full agentic eligibility check pipeline.
    
    Total tools invoked across the pipeline:
    - get_policy (DB)
    - medical_term_normalizer → icd_procedure_lookup → city_tier_classifier → hospital_cost_estimator
    - decision_engine (deterministic)
    - clause_explainer → savings_calculator → what_if_analyzer
    - LLM calls (case structuring + explanation generation)
    
    All steps are audit-logged for compliance.
    """
    run_id = str(uuid.uuid4())[:8]
    pipeline_start = time.time()
    
    logger.info(f"[Orchestrator:{run_id}] ▶▶ Starting agentic pipeline for policy #{policy_id}")
    
    audit_trail_logger(
        agent_name="Orchestrator", action="pipeline_start",
        input_summary=f"Policy ID: {policy_id}, case fields: {list(case_input.keys())}",
        output_summary="Pipeline initiated",
        tools_used=[],
        metadata={"pipeline_run_id": run_id},
    )
    
    initial_state: PipelineState = {
        "pipeline_run_id": run_id,
        "policy_id": policy_id,
        "case_input": case_input,
        "policy_data": None,
        "case_facts": None,
        "verdict": None,
        "explanation": "",
        "suggestions": [],
        "error": None,
        "tools_invoked": [],
        "step": "start",
    }
    
    # Run the pipeline
    final_state = await pipeline.ainvoke(initial_state)
    pipeline_end = time.time()
    total_ms = (pipeline_end - pipeline_start) * 1000
    
    tools_used = final_state.get("tools_invoked", [])
    
    if final_state.get("error"):
        audit_trail_logger(
            agent_name="Orchestrator", action="pipeline_failed",
            input_summary=f"Policy #{policy_id}",
            output_summary=f"FAILED: {final_state['error'][:200]}",
            tools_used=tools_used,
            duration_ms=total_ms,
            status="failure",
            metadata={"pipeline_run_id": run_id},
        )
        raise Exception(final_state["error"])
    
    verdict = Verdict(**final_state["verdict"])
    policy = final_state["policy_data"]
    
    audit_trail_logger(
        agent_name="Orchestrator", action="pipeline_complete",
        input_summary=f"Policy #{policy_id}",
        output_summary=f"Verdict: {verdict.overall_verdict.value}, "
                      f"coverage: {verdict.coverage_percentage}%, "
                      f"tools used: {len(tools_used)}",
        tools_used=tools_used,
        duration_ms=total_ms,
        metadata={"pipeline_run_id": run_id, "total_tools": len(tools_used)},
    )
    
    logger.info(f"[Orchestrator:{run_id}] ✓✓ Pipeline complete in {total_ms:.0f}ms — "
                f"{len(tools_used)} tools invoked — {verdict.overall_verdict.value}")
    
    return EligibilityResponse(
        verdict=verdict,
        explanation=final_state["explanation"],
        suggestions=final_state["suggestions"],
        policy_name=policy["plan_name"],
        insurer=policy["insurer"],
    )
