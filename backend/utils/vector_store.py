"""
Vector Store utility for SecureShield.

Uses Supabase PostgreSQL with pgvector extension for semantic search
over IRDAI regulations and policy knowledge base.

This replaces the keyword-based irdai_regulation_lookup with true
semantic (meaning-based) search. For example:
  - Query: "how long before diabetes is covered?"
  - Matches: "pre_existing_disease_waiting_period" (48 months max)

Embedding model: Uses a lightweight local model via sentence-transformers
so there are no API costs for embeddings.
"""

import os
import json
import logging
import hashlib
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Path to the IRDAI knowledge base
_KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"

# Embedding model — small, fast, free (runs locally, no API cost)
_EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
_embedder = None


def _get_embedder():
    """Lazy-load the sentence-transformers model."""
    global _embedder
    if _embedder is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedder = SentenceTransformer(_EMBED_MODEL_NAME)
            logger.info(f"[VectorStore] Loaded embedding model: {_EMBED_MODEL_NAME}")
        except ImportError:
            logger.warning(
                "[VectorStore] sentence-transformers not installed. "
                "Falling back to keyword search."
            )
            return None
    return _embedder


def _get_client():
    """Lazy-init Supabase client."""
    from supabase import create_client
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def _embed(text: str) -> list:
    """Generate an embedding vector for a text string."""
    model = _get_embedder()
    if model is None:
        return []
    vec = model.encode(text).tolist()
    return vec


def create_vector_table():
    """
    Create the irdai_knowledge table with pgvector column in Supabase.
    Call this once during setup.
    """
    client = _get_client()
    sql = """
    CREATE TABLE IF NOT EXISTS irdai_knowledge (
        id SERIAL PRIMARY KEY,
        chunk_id TEXT UNIQUE NOT NULL,
        category TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        embedding vector(384),
        metadata JSONB DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- Create an index for fast similarity search
    CREATE INDEX IF NOT EXISTS idx_irdai_knowledge_embedding
    ON irdai_knowledge
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 10);
    """
    client.postgrest.rpc("exec_sql", {"query": sql}).execute()
    logger.info("[VectorStore] Created irdai_knowledge table with pgvector index")


def _chunk_knowledge_base() -> list[dict]:
    """
    Break the IRDAI knowledge base JSON into searchable chunks.
    Each chunk gets a unique ID, category, title, and content string.
    """
    with open(_KNOWLEDGE_DIR / "irdai_rules.json", "r") as f:
        kb = json.load(f)

    chunks = []

    # Standard definitions
    for term, definition in kb.get("standard_definitions", {}).items():
        title = term.replace("_", " ").title()
        chunks.append({
            "chunk_id": f"def_{term}",
            "category": "standard_definition",
            "title": title,
            "content": f"{title}: {definition}",
            "metadata": {"term": term},
        })

    # Mandated limits
    for key, data in kb.get("mandated_limits", {}).items():
        title = key.replace("_", " ").title()
        content_parts = [f"{title}: {data.get('description', '')}"]
        if "maximum_days" in data:
            content_parts.append(f"Maximum: {data['maximum_days']} days")
        if "maximum_months" in data:
            content_parts.append(f"Maximum: {data['maximum_months']} months")
        if "years" in data:
            content_parts.append(f"Period: {data['years']} years")
        if "regulation" in data:
            content_parts.append(f"Regulation: {data['regulation']}")
        if "common_diseases" in data:
            content_parts.append(
                f"Common diseases: {', '.join(data['common_diseases'])}"
            )
        chunks.append({
            "chunk_id": f"limit_{key}",
            "category": "mandated_limit",
            "title": title,
            "content": " | ".join(content_parts),
            "metadata": data,
        })

    # Standard exclusions (permanent)
    for i, excl in enumerate(kb.get("standard_exclusions", {}).get("permanent", [])):
        name = excl["name"]
        content = f"Permanent Exclusion: {name}"
        if "exception" in excl:
            content += f" (Exception: {excl['exception']})"
        chunks.append({
            "chunk_id": f"excl_perm_{i}",
            "category": "exclusion_permanent",
            "title": name,
            "content": content,
            "metadata": excl,
        })

    # Standard exclusions (conditional)
    for i, excl in enumerate(kb.get("standard_exclusions", {}).get("conditional", [])):
        name = excl["name"]
        content = f"Conditional Exclusion: {name}"
        if "note" in excl:
            content += f" ({excl['note']})"
        if "typical_waiting_months" in excl:
            content += f" | Typical waiting: {excl['typical_waiting_months']} months"
        chunks.append({
            "chunk_id": f"excl_cond_{i}",
            "category": "exclusion_conditional",
            "title": name,
            "content": content,
            "metadata": excl,
        })

    # Room rent guidelines
    for i, structure in enumerate(
        kb.get("room_rent_guidelines", {}).get("common_structures", [])
    ):
        content = f"Room Rent: {structure['description']}"
        if "typical_value" in structure:
            content += f" (Typical: {structure['typical_value']}%)"
        chunks.append({
            "chunk_id": f"room_rent_{i}",
            "category": "room_rent",
            "title": f"Room Rent — {structure['type'].replace('_', ' ').title()}",
            "content": content,
            "metadata": structure,
        })

    # Copay guidelines
    for i, copay_type in enumerate(
        kb.get("copay_guidelines", {}).get("types", [])
    ):
        content = f"Co-payment: {copay_type.get('description', copay_type.get('type', 'N/A'))}"
        chunks.append({
            "chunk_id": f"copay_{i}",
            "category": "copay",
            "title": f"Copay — {copay_type['type'].replace('_', ' ').title()}",
            "content": content,
            "metadata": copay_type,
        })

    # Compliance guardrails
    for key, value in kb.get("compliance_guardrails", {}).items():
        title = key.replace("_", " ").title()
        chunks.append({
            "chunk_id": f"guardrail_{key}",
            "category": "compliance_guardrail",
            "title": title,
            "content": f"Compliance: {title} — {value}",
            "metadata": {"key": key, "value": value},
        })

    logger.info(f"[VectorStore] Chunked IRDAI knowledge base into {len(chunks)} chunks")
    return chunks


def index_irdai_knowledge():
    """
    Embed and store all IRDAI knowledge chunks into Supabase pgvector.
    This is an idempotent operation — chunks with existing IDs are skipped.
    """
    embedder = _get_embedder()
    if embedder is None:
        logger.warning("[VectorStore] No embedder available, skipping indexing")
        return 0

    client = _get_client()
    chunks = _chunk_knowledge_base()
    indexed = 0

    for chunk in chunks:
        embedding = _embed(chunk["content"])
        if not embedding:
            continue

        # Upsert: insert or skip if chunk_id exists
        try:
            client.table("irdai_knowledge").upsert(
                {
                    "chunk_id": chunk["chunk_id"],
                    "category": chunk["category"],
                    "title": chunk["title"],
                    "content": chunk["content"],
                    "embedding": embedding,
                    "metadata": json.dumps(chunk["metadata"]),
                },
                on_conflict="chunk_id",
            ).execute()
            indexed += 1
        except Exception as e:
            logger.warning(f"[VectorStore] Failed to index {chunk['chunk_id']}: {e}")

    logger.info(f"[VectorStore] Indexed {indexed}/{len(chunks)} IRDAI knowledge chunks")
    return indexed


def semantic_search(query: str, top_k: int = 5) -> list[dict]:
    """
    Perform semantic similarity search over the IRDAI knowledge base.

    Args:
        query: Natural language question (e.g., "is diabetes covered?")
        top_k: Number of results to return

    Returns:
        List of matching chunks with similarity scores
    """
    embedding = _embed(query)
    if not embedding:
        # Fallback to basic text search
        return _fallback_text_search(query, top_k)

    client = _get_client()

    # Use Supabase RPC for vector similarity search
    try:
        result = client.rpc(
            "search_irdai_knowledge",
            {
                "query_embedding": embedding,
                "match_threshold": 0.3,
                "match_count": top_k,
            },
        ).execute()

        matches = []
        for row in result.data or []:
            matches.append({
                "chunk_id": row.get("chunk_id"),
                "category": row.get("category"),
                "title": row.get("title"),
                "content": row.get("content"),
                "similarity": round(row.get("similarity", 0), 4),
                "metadata": row.get("metadata", {}),
            })

        logger.info(
            f"[VectorStore] Semantic search for '{query[:50]}...' "
            f"→ {len(matches)} results"
        )
        return matches

    except Exception as e:
        logger.warning(f"[VectorStore] Semantic search failed: {e}, using fallback")
        return _fallback_text_search(query, top_k)


def _fallback_text_search(query: str, top_k: int = 5) -> list[dict]:
    """Fallback: simple keyword search over local JSON if pgvector unavailable."""
    chunks = _chunk_knowledge_base()
    query_lower = query.lower()
    scored = []

    for chunk in chunks:
        content_lower = chunk["content"].lower()
        # Simple keyword overlap score
        words = query_lower.split()
        score = sum(1 for w in words if w in content_lower) / max(len(words), 1)
        if score > 0:
            scored.append({**chunk, "similarity": round(score, 4)})

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:top_k]


# SQL function that needs to be created in Supabase for semantic search
SEARCH_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION search_irdai_knowledge(
    query_embedding vector(384),
    match_threshold float DEFAULT 0.3,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    chunk_id text,
    category text,
    title text,
    content text,
    similarity float,
    metadata jsonb
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ik.chunk_id,
        ik.category,
        ik.title,
        ik.content,
        1 - (ik.embedding <=> query_embedding) AS similarity,
        ik.metadata::jsonb
    FROM irdai_knowledge ik
    WHERE 1 - (ik.embedding <=> query_embedding) > match_threshold
    ORDER BY ik.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
"""
