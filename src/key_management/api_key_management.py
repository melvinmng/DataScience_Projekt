import os
from googleapiclient.discovery import build
from typing import Optional



def get_api_key(env_var: str) -> Optional[str]:
    try:
        api_key = os.getenv(env_var)
    except:
        raise ValueError(
            "API_KEY nicht gefunden! Bitte stelle sicher, dass der API-Schlüssel in der .env-Datei definiert ist."
        )
    return api_key


def create_youtube_client(api_key: str) -> object:
    api_service_name = "youtube"
    api_version = "v3"
    return build(api_service_name, api_version, developerKey=api_key)


if __name__ == "__main__":
    try:
        google_api_key: Optional[str] = get_api_key("TOKEN_GOOGLEAPI")
        print("Google API Key geladen:", google_api_key)

        youtube_api_key: Optional[str] = get_api_key("YOUTUBE_API_KEY")
        youtube_client: object = create_youtube_client(youtube_api_key)
        print("YouTube API Client erfolgreich erstellt.")
    except ValueError as e:
        print(e)
