import logging
import time
import json
from agents.model_router import router
from tools.faq_tools import faq_lookup
from tools.audit_tools import audit_trail_logger

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """You are SecureShield's Medical Chat Assistant. 
You help Indian patients understand their health insurance coverage and medical terms.

GUIDELINES:
1. Be professional, empathetic, and concise.
2. If the user asks about specific policy rules, mention IRDAI standards where applicable.
3. Keep answers under 3 paragraphs.
4. STRICT MODERATION: You must completely refuse to answer questions involving abusive language, romantic advances, harmful/dangerous activities (e.g., jumping from a building, self-harm), or security threats. If asked such questions, reply politely and firmly: "I am a medical insurance assistant and cannot respond to requests involving harm, abuse, or unrelated personal matters."
5. OFF-TOPIC: If a question is entirely non-contextual (e.g., asking for recipes, writing code, or general chatting unrelated to health/insurance), reply: "I specialize in health insurance and medical claims. How can I assist you with your policy today?"

{user_context}
"""

async def handle_chat_query(query: str, history: list = None, user_id: str = None) -> dict:
    """
    Optimized Multi-Tier Chat logic:
    Tier 1: Local FAQ Cache (Instant, Free)
    Tier 2: Cerebras / Fast LLM (Fast, Cheap)
    Tier 3: Complex Reasoning (Gemini/Groq)
    """
    start_time = time.time()
    
    # Tier 1: Local FAQ Cache
    faq_result = faq_lookup(query)
    if faq_result:
        duration = (time.time() - start_time) * 1000
        audit_trail_logger(
            agent_name="ChatAgent",
            action="faq_hit",
            input_summary=query,
            output_summary=faq_result["answer"][:100] + "...",
            tools_used=["faq_lookup"],
            duration_ms=duration
        )
        return {
            "answer": faq_result["answer"],
            "method": "cache",
            "duration_ms": duration
        }
        
    # Build User Context (RAG)
    user_context = ""
    if user_id:
        from db.database import get_all_policies, get_check_history
        try:
            # Fetch up to 100 checks to provide comprehensive history
            policies = await get_all_policies(user_id=user_id)
            history_checks = await get_check_history(limit=100, user_id=user_id)
            
            ctx_lines = ["\n--- SECURESHIELD USER DATA CONTEXT ---"]
            ctx_lines.append("CRITICAL: You have access to the user's REAL uploaded policies and claim checks below.")
            ctx_lines.append("DO NOT hallucinate templates like '[insert policy number]'. Use the real data below to answer precisely. You DO NOT have access to their password or profile info; state this if asked.")
            
            if policies:
                ctx_lines.append("\nACTIVE POLICIES:")
                for p in policies:
                    ctx_lines.append(f"- ID: #{p['id']}, Insurer: {p['insurer']}, Plan: {p['plan_name']}, Sum Insured: ₹{p['sum_insured']:,.2f}, Type: {p['policy_type']}")
            else:
                ctx_lines.append("\nACTIVE POLICIES: None uploaded yet.")
                
            if history_checks:
                ctx_lines.append("\nPAST CLAIMS / ELIGIBILITY CHECKS:")
                # We cap context to 15 recent checks to avoid LLM token limits while answering "tell me about my claims"
                for c in history_checks[:15]:
                    try:
                        case_data = json.loads(c['case_json'])
                        verdict_data = json.loads(c['verdict_json'])
                        proc = case_data.get('procedure', 'Unknown')
                        hosp = case_data.get('hospital_name', 'Unknown')
                        claimed = case_data.get('total_claimed_amount', 0)
                        status = verdict_data.get('overall_verdict', 'UNKNOWN')
                        ctx_lines.append(f"- Check #{c['id']}: Procedure: {proc} at {hosp}. Claimed: ₹{claimed:,.2f}. Status: {status}.")
                    except Exception:
                        pass
            else:
                ctx_lines.append("\nPAST CLAIMS: No previous checks found.")
                
            ctx_lines.append("--------------------------------------")
            user_context = "\n".join(ctx_lines)
            
        except Exception as e:
            logger.warning(f"[ChatAgent] Failed to retrieve user context: {e}")
            user_context = ""
            
    system_prompt = SYSTEM_PROMPT_TEMPLATE.replace("{user_context}", user_context)
        
    # Context integration for LLM
    user_prompt = query
    if history and len(history) > 0:
        context_str = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history])
        user_prompt = f"--- Previous Conversation ---\n{context_str}\n\n--- Current Query ---\nUser: {query}"

    # Tier 2: LLM (Cerebras / Groq / Gemini via Router)
    # The router will automatically try the best available provider.
    try:
        t0 = time.time()
        response = await router.call(
            role="chat", # Router will use DEFAULT_ROUTING which starts with Cerebras
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.4,
            max_tokens=1024
        )
        
        # Output Sanitization (XSS prevention for markdown rendering)
        import re
        response = re.sub(r'<\s*script[^>]*>.*?(</\s*script\s*>|$)', '', response, flags=re.IGNORECASE | re.DOTALL)
        response = re.sub(r'\b(on\w+)\s*=', '', response, flags=re.IGNORECASE)
        
        duration = (time.time() - t0) * 1000
        
        audit_trail_logger(
            agent_name="ChatAgent",
            action="llm_chat",
            input_summary=query,
            output_summary=response[:100] + "...",
            tools_used=["model_router"],
            duration_ms=duration
        )
        
        return {
            "answer": response,
            "method": "llm",
            "duration_ms": duration
        }
    except Exception as e:
        logger.error(f"[ChatAgent] LLM failed: {e}")
        return {
            "answer": "I'm sorry, I encountered an error while processing your request. Please try again later.",
            "method": "error",
            "duration_ms": (time.time() - start_time) * 1000
        }
