import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from .key_management.api_key_management import get_api_key, create_youtube_client
from typing import Optional

SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]


def authenticate() -> Optional[object]:
    """Authenticates user via Google AUth0. For test cases only!

    Returns:
        Optional[object]: YouTube client
    """
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "client_secret_587929800669-bijuer10mhg8fbuf2bjkhpg0mq4r6d3k.apps.googleusercontent.com.json",
                SCOPES,
            )
            creds = flow.run_local_server(port=0)

        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    try:
        api_key: Optional[str] = get_api_key()
        youtube = create_youtube_client(api_key)

    except ValueError as e:
        print(f"Fehler: {e}")

    except Exception as e:
        print(f"Ein unerwarteter Fehler ist aufgetreten: {e}")
    return youtube


def get_subscriptions(youtube: object) -> None:
    """Gets user's subscriptions. For test cases only!

    Args:
        youtube (object): YouTube API client
    """
    request = youtube.subscriptions().list(
        part="snippet",
        mine=True,
        maxResults=50,
    )
    response = request.execute()

    # Ausgabe der Abonnenten
    subscriptions = response.get("items", [])
    if not subscriptions:
        print("Du hast keine Abonnements.")
    else:
        print(f"Du hast {len(subscriptions)} Abonnement(s):")
        for subscription in subscriptions:
            channel_title = subscription["snippet"]["title"]
            channel_id = subscription["snippet"]["resourceId"]["channelId"]
            print(f"- {channel_title} (Channel ID: {channel_id})")


def main() -> None:
    youtube = authenticate()
    get_subscriptions(youtube)


if __name__ == "__main__":
    main()
