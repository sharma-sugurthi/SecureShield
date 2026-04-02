import logging
import base64
import os

logger = logging.getLogger(__name__)

from google.cloud import vision
import io
import os

logger = logging.getLogger(__name__)

# Note: GOOGLE_APPLICATION_CREDENTIALS should be set in .env or environment
# and points to the JSON key file.

def google_vision_ocr(image_bytes: bytes) -> dict:
    """
    Perform real OCR using Google Vision API (1000 free requests/month).
    Extracts text from images (Medical bills, prescriptions).
    """
    try:
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_bytes)
        
        response = client.text_detection(image=image)
        texts = response.text_annotations
        
        if response.error.message:
            raise Exception(f"{response.error.message}")

        full_text = ""
        if texts:
            full_text = texts[0].description
            
        logger.info(f"[Tool:google_vision_ocr] Successfully processed image ({len(image_bytes)/1024:.0f}KB)")
        
        return {
            "text": full_text,
            "confidence": 1.0, # Vision API doesn't provide a single confidence score for the whole block easily
            "labels": [label.description for label in getattr(response, 'label_annotations', [])]
        }
    except Exception as e:
        logger.error(f"[Tool:google_vision_ocr] API Error: {e}")
        return {
            "text": f"Error during OCR: {e}",
            "confidence": 0.0,
            "labels": []
        }

def is_image(filename: str) -> bool:
    """Check if file is an image based on extension."""
    ext = filename.lower().split('.')[-1]
    return ext in ['jpg', 'jpeg', 'png', 'webp']
