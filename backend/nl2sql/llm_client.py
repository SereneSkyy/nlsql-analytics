from google import genai
from backend.config import GEMINI_API_KEY

_client = genai.Client(api_key=GEMINI_API_KEY)
_MODEL = "gemini-3.6-flash"

def generate_text(prompt: str) -> str:
    """Send a prompt to Gemini and return the raw text response."""
    response = _client.models.generate_content(
        model=_MODEL,
        contents=prompt,
    )
    return response.text.strip()
