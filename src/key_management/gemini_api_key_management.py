import os
from dotenv import load_dotenv

load_dotenv()

try:
    api_key = os.getenv("TOKEN_GOOGLEAPI")
except:
    raise ValueError(
        "API_KEY nicht gefunden! Bitte stelle sicher, dass der API-Schlüssel in der .env-Datei definiert ist."
    )
