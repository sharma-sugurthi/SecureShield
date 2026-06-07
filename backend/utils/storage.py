"""
Supabase Storage utility for SecureShield.

Handles uploading and downloading policy PDFs to/from Supabase Storage.
This replaces local disk storage with cloud-hosted, CDN-served file storage.

Bucket: policy-pdfs (public, created via Supabase dashboard)
"""

import os
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
BUCKET_NAME = "policy-pdfs"


def _get_client():
    """Lazy-init Supabase client."""
    from supabase import create_client
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_KEY must be set in .env"
        )
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def upload_pdf(pdf_bytes: bytes, original_filename: str) -> dict:
    """
    Upload a PDF to Supabase Storage.

    Args:
        pdf_bytes: Raw PDF content
        original_filename: Original name of the uploaded file

    Returns:
        {
            "storage_path": str,      # Path within the bucket
            "public_url": str,        # CDN-served public URL
            "size_kb": float,
        }
    """
    client = _get_client()

    # Generate a unique filename to avoid collisions
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = original_filename.replace(" ", "_").lower()
    storage_path = f"{timestamp}_{uuid.uuid4().hex[:8]}_{safe_name}"

    # Upload to Supabase Storage
    client.storage.from_(BUCKET_NAME).upload(
        path=storage_path,
        file=pdf_bytes,
        file_options={"content-type": "application/pdf"},
    )

    # Get public URL
    public_url = client.storage.from_(BUCKET_NAME).get_public_url(storage_path)

    size_kb = len(pdf_bytes) / 1024

    logger.info(
        f"[Storage] Uploaded {safe_name} to Supabase "
        f"({size_kb:.1f}KB) → {storage_path}"
    )

    return {
        "storage_path": storage_path,
        "public_url": public_url,
        "size_kb": round(size_kb, 1),
    }


def download_pdf(storage_path: str) -> bytes:
    """
    Download a PDF from Supabase Storage.

    Args:
        storage_path: Path within the bucket (from upload_pdf return value)

    Returns:
        Raw PDF bytes
    """
    client = _get_client()
    data = client.storage.from_(BUCKET_NAME).download(storage_path)
    logger.info(f"[Storage] Downloaded {storage_path} ({len(data)/1024:.1f}KB)")
    return data


def delete_pdf(storage_path: str) -> bool:
    """Delete a PDF from Supabase Storage."""
    try:
        client = _get_client()
        client.storage.from_(BUCKET_NAME).remove([storage_path])
        logger.info(f"[Storage] Deleted {storage_path}")
        return True
    except Exception as e:
        logger.error(f"[Storage] Delete failed for {storage_path}: {e}")
        return False
