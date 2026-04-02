import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_FAQ_FILE = Path(__file__).parent.parent / "knowledge" / "faq.json"

def faq_lookup(query: str) -> dict | None:
    """
    Search for a question in the local FAQ knowledge base.
    Uses simple keyword matching for speed.
    """
    try:
        if not _FAQ_FILE.exists():
            return None
            
        with open(_FAQ_FILE, "r") as f:
            data = json.load(f)
            
        query_lower = query.lower()
        
        # Simple keyword matching
        for item in data.get("faq", []):
            for q in item["questions"]:
                if query_lower in q.lower() or any(word in q.lower() for word in query_lower.split() if len(word) > 4):
                    logger.info(f"[Tool:faq_lookup] Match found for: '{query}'")
                    return {
                        "answer": item["answer"],
                        "category": item["category"],
                        "source": "local_faq_cache"
                    }
                    
        return None
    except Exception as e:
        logger.error(f"[Tool:faq_lookup] Error: {e}")
        return None
