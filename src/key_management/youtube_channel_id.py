import os
from googleapiclient.discovery import build



def load_channel_id():
    channel_key = os.getenv("CHANNEL_ID")
    
    if not channel_key:
        raise ValueError(
            "CHANNEL_ID nicht gefunden! Bitte stelle sicher, dass der Channel id in der .env-Datei definiert ist."
        )

    return channel_key

