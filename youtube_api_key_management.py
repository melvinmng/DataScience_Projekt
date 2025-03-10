import os
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Lade die Umgebungsvariablen aus der .env-Datei
load_dotenv()

# Greife auf den API-Schlüssel zu, der in der .env-Datei gespeichert ist
api_key = os.getenv("YOUTUBE_API_KEY")

if not api_key:
    raise ValueError("API_KEY nicht gefunden! Bitte stelle sicher, dass der API-Schlüssel in der .env-Datei definiert ist.")

print(api_key)

api_service_name = "youtube"
api_version = "v3"

# Erstelle den API-Client
youtube = build(api_service_name, api_version, developerKey=api_key)

request = youtube.channels().list(
    part="snippet,contentDetails,statistics", id="UC_x5XG1OV2P6uZZ5FSM9Ttw"
)
response = request.execute()

print(response)
