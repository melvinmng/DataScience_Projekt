from google import genai
from google.genai import types
import os
from .key_management.api_key_management import get_api_key

## GEMINI
try:
    ai_client = genai.Client(api_key=get_api_key("TOKEN_GOOGLEAPI"))
except:
    raise ValueError("Kein API_KEY gefunden.")
else:
    print("API_KEY gefunden")
ai_model = "gemini-2.0-flash"
ai_generate_content_config = types.GenerateContentConfig(
    temperature=1,
    top_p=0.95,
    top_k=40,
    max_output_tokens=8192,
    response_mime_type="text/plain",
    system_instruction=[
        types.Part.from_text(
            text="""Du bist ein Experte im Bereich Datenanalyse und For-You-Pages. Im Folgenden wirst du immer wieder YouTube-Videos und ihre Transkripte zugeschickt bekommen und ausgehend von diesen Inhalte zusammenffassen, Clickbait erkennen und ausgehend von der verbleibenden Zeit des Users, Vorschläge machen, welche der Videos er sich am ehesten anschauen sollte (kein Clickbait, seinen Interessen entsprechend)."""
        ),
    ],
)

## Personal Settings
interests = "chess, ..."
languages = ["de", "en"]
