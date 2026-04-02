import logging
import time
from agents.model_router import router
from tools.faq_tools import faq_lookup
from tools.audit_tools import audit_trail_logger

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are SecureShield's Medical Chat Assistant. 
You help Indian patients understand their health insurance coverage and medical terms.

GUIDELINES:
1. Be professional, empathetic, and concise.
2. If the user asks about specific policy rules, mention IRDAI standards where applicable.
3. Keep answers under 3 paragraphs.
4. Always include a disclaimer: 'This is an AI summary; always refer to your specific policy document for final details.'
"""

async def handle_chat_query(query: str) -> dict:
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
        
    # Tier 2: LLM (Cerebras / Groq / Gemini via Router)
    # The router will automatically try the best available provider.
    try:
        t0 = time.time()
        response = await router.call(
            role="chat", # Router will use DEFAULT_ROUTING which starts with Cerebras
            system_prompt=SYSTEM_PROMPT,
            user_prompt=query,
            temperature=0.4,
            max_tokens=1024
        )
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
