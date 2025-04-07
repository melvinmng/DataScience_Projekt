import os
from googleapiclient.discovery import build


def load_channel_id() -> str:
    """Load the YouTube channel ID from the .env file.

    Retrieves the 'CHANNEL_ID' environment variable. Raises a ValueError if:
      - The environment variable is missing.
      - The value does not have exactly 24 characters (which may indicate that a user ID was provided instead of a channel ID).

    Raises:
        ValueError: If 'CHANNEL_ID' is missing.
        ValueError: If the channel ID is not exactly 24 characters long.

    Returns:
        str: The YouTube channel ID.
    """
    channel_key = os.getenv("CHANNEL_ID")

    if not channel_key:
        raise ValueError(
            "CHANNEL_ID nicht gefunden! Bitte stelle sicher, dass die Channel-ID in der .env-Datei definiert ist."
        )
    elif len(channel_key) == 24:
        return channel_key
    else:
        raise ValueError(
            "Stelle sicher, dass du die Channel-ID und nicht die Nutzer-ID verwendest. (Der Key muss 24 Zeichen lang sein.)"
        )
