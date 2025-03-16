import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# Die erforderlichen SCOPES für die YouTube API, um Abonnenten und Kanalinformationen abzurufen
SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']

def authenticate():
    """Authentifizierung mit OAuth2 und Rückgabe des API-Clients."""
    creds = None
    # Die Token-Datei speichert den Zugriffstoken und wird bei der ersten Authentifizierung erzeugt.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # Wenn keine gültigen Anmeldeinformationen vorhanden sind, muss der Benutzer sich anmelden.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # OAuth 2.0-Flow mit der richtigen client_secrets.json
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret_587929800669-bijuer10mhg8fbuf2bjkhpg0mq4r6d3k.apps.googleusercontent.com.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Speichern der Anmeldeinformationen für zukünftige Verwendungen
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    # Erstelle den YouTube API-Client
    youtube = build('youtube', 'v3', credentials=creds)
    return youtube

def get_subscriptions(youtube):
    """Abrufen der Abonnements des YouTube-Kanals des authentifizierten Nutzers."""
    request = youtube.subscriptions().list(
        part='snippet',
        mine=True,  # Nur für den authentifizierten Benutzer
        maxResults=50  # Anzahl der Ergebnisse pro Anfrage (max. 50)
    )
    response = request.execute()

    # Ausgabe der Abonnenten
    subscriptions = response.get('items', [])
    if not subscriptions:
        print("Du hast keine Abonnenten.")
    else:
        print(f"Du hast {len(subscriptions)} Abonnent(en):")
        for subscription in subscriptions:
            channel_title = subscription['snippet']['title']
            channel_id = subscription['snippet']['resourceId']['channelId']
            print(f"- {channel_title} (Channel ID: {channel_id})")

def main():
    """Hauptfunktion, die das Skript ausführt."""
    youtube = authenticate()
    get_subscriptions(youtube)

if __name__ == '__main__':
    main()
