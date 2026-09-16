import os
import re
import json
import logging
from pathlib import Path

logger = logging.getLogger("GeminiService")

def clean_filename_to_title(filename: str) -> str:
    """Derives a readable title from filename."""
    stem = Path(filename).stem
    # Replace separators with spaces
    title = re.sub(r"[_\-\.]+", " ", stem)
    # Remove leading numbers or hash prefixes
    title = re.sub(r"^\d+\s*", "", title)
    return title.strip().title()

def generate_video_copy_and_hashtags(file_path: str, filename: str, file_size_mb: float = 0.0) -> dict:
    """
    Pipes video metadata to Google Gemini API to generate optimized description copy
    and 3 to 5 structural hashtags.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    derived_title = clean_filename_to_title(filename)
    
    prompt = (
        f"You are a short-form content growth expert specializing in viral TikTok videos and Instagram Reels.\n"
        f"Analyze the following video metadata:\n"
        f"- Filename: {filename}\n"
        f"- Derived Concept: {derived_title}\n"
        f"- File Size: {file_size_mb:.2f} MB\n\n"
        f"Task:\n"
        f"1. Generate a compelling, high-converting short-form video description copy (1-3 sentences) optimized for retention.\n"
        f"2. Generate exactly 3 to 5 structural, relevant, high-velocity hashtags formatted with '#' prefix.\n\n"
        f"Return strictly valid JSON with no markdown backticks, with exactly this structure:\n"
        f'{{"description": "...", "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4"]}}'
    )

    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            logger.info(f"[GEMINI] Querying Gemini model '{model_name}' for metadata: {filename}")
            
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            
            raw_text = response.text.strip()
            # Remove any markdown code fence if returned
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()
            
            parsed = json.loads(raw_text)
            description = parsed.get("description", "").strip()
            hashtags = parsed.get("hashtags", [])
            
            # Ensure 3-5 hashtags
            if isinstance(hashtags, list) and len(hashtags) >= 3:
                hashtags = [t if t.startswith("#") else f"#{t}" for t in hashtags[:5]]
                logger.info(f"[GEMINI] Successfully generated metadata for {filename}")
                return {
                    "description": description or f"Exploring {derived_title}. Watch until the end.",
                    "hashtags": hashtags,
                    "model_used": model_name
                }
        except Exception as e:
            logger.warning(f"[GEMINI] API request failed ({e}). Falling back to local algorithmic generator.")
    else:
        logger.info(f"[GEMINI] GEMINI_API_KEY not configured. Generating algorithmic structural copy for {filename}.")

    # Algorithmic fallback generator (zero external dependencies)
    tags_pool = ["#Shorts", "#Trending", "#Creator", "#Viral", "#WatchTillTheEnd", "#Tech"]
    clean_words = [w.capitalize() for w in derived_title.split() if len(w) > 2]
    custom_tags = [f"#{w}" for w in clean_words[:2]]
    combined_tags = list(dict.fromkeys(custom_tags + tags_pool))[:4]
    
    fallback_desc = f"{derived_title} - Everything you need to know in under 60 seconds."
    
    return {
        "description": fallback_desc,
        "hashtags": combined_tags,
        "model_used": "local-fallback (API key absent or offline)"
    }
