import os

from git import Optional
from src import config_env


def get_api_key() -> Optional[str]:
    try:
        api_key = os.getenv("TOKEN_GOOGLEAPI")
    except:
        raise ValueError(
            "API_KEY nicht gefunden! Bitte stelle sicher, dass der API-Schlüssel in der .env-Datei definiert ist."
        )
    return api_key


if __name__ == "__main__":
    print(get_api_key())
