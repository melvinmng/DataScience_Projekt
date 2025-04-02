import os
from googleapiclient.discovery import build



def load_channel_id():
    channel_key = os.getenv("CHANNEL_ID")
    
    if not channel_key:
        raise ValueError(
            "CHANNEL_ID nicht gefunden! Bitte stelle sicher, dass der Channel id in der .env-Datei definiert ist."
        )
    else:
        if len(channel_key) == 24:
            return channel_key
        else:
            raise ValueError(
                "Stelle sicher, dass du die Channel_id und nicht die Nutzer_id verwendest. (Der Key muss 24 Zeichen lang sein.)"
            )
