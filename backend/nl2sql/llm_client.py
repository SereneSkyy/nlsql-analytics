from google import genai
from google.genai import errors as genai_errors
from backend.config import GEMINI_API_KEY
import os
import time

_client = genai.Client(api_key=GEMINI_API_KEY)

# Configurable via env var so eval runs can use the higher-quota Flash-Lite
# tier without code changes, while day-to-day dev/demo use can stay on the
# stronger default model. Free tier quotas differ sharply between these
# (Flash: 20 requests/day, Flash-Lite: ~1000/day as of testing) -- documented
# in the README as a real constraint of building on free-tier LLM access.
_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

def generate_text(prompt: str, max_retries: int = 3) -> str:
    """Send a prompt to Gemini and return the raw text response. Retries with
    backoff on transient server errors (e.g. 503 'high demand'). Does NOT
    retry on 429 quota-exhausted errors, since those won't resolve within
    a short backoff window -- that error should surface to the caller."""
    last_error = None
    for attempt in range(max_retries):
        try:
            response = _client.models.generate_content(
                model=_MODEL,
                contents=prompt,
            )
            return response.text.strip()
        except genai_errors.ServerError as e:
            last_error = e
            wait = 2 ** attempt
            print(f"  Gemini server error (attempt {attempt + 1}/{max_retries}), retrying in {wait}s...")
            time.sleep(wait)
    raise last_error
