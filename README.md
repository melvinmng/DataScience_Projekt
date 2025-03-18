# DataScience_Projekt
Repository für unser Data-Science-Projekt

## How to work with .env-files
### Required packages
- os
- dotenv

### Instructions
1. Erstellen Sie eine .env-Datei in Ihrem Projektordner
2. Speichern Sie Ihre Passwörter in folgender Form in Ihrer .env-Datei: NAME_DES_PASSWORTS (später zum Aufrufen benötigt) = "Passwort/Key"
3. Importieren Sie die notwendigen Packages in das Modul, in welchem Sie auf Ihre Passwörter/Keys zugreifen möchten
4. Rufen Sie ihre Passwörter mit folgendem Befehl auf: os.getenv("NAME_DES_PASSWORTS")

## How to create a Gemini API Key
1. Erstellen Sie einen Account für das Google AI Studio: https://aistudio.google.com/app/apikey?_gl=1*e137ex*_ga*MTE4NjE1OTYwLjE3NDE2MDM4Mzk.*_ga_P1DBVKWT6V*MTc0MTYwNTEyMS4xLjEuMTc0MTYwNTIzMy4wLjAuMTgyNDY0NDU1Nw..
2. Klicken Sie auf "Get API Key"
3. Klicken Sie auf "API Schlüssel erstellen"
4. Falls nötig, erstellen Sie ein Projekt und wählen Sie dieses für den API-Schlüssel aus
5. Klicken Sie auf "API Schlüssel in bestehendem Projekt erstellen"
6. Kopieren Sie ihren API-Schlüssel und fügen ihn in ihre lokale .env-Datei ein, damit der Code auf diesen zugreifen kann (halten Sie dabei folgende Struktur ein: TOKEN_GOOGLEAPI = "YOUR_KEY")

## How to create a YouTube API Key
1. Melden Sie sich mit ihrem Google Account bei Google Cloud Platform an: https://console.cloud.google.com/
2. Falls nötig, erstellen Sie ein Projekt und wählen Sie dieses für den API-Schlüssel aus
3. Aktivieren Sie für Ihr Projekt die YouTube Data API v3 über "API und Dienste" oder direkt über die Suchzeile.
4. Klicken Sie auf "Anmeldedaten"
5. Klicken Sie auf "Anmeldedaten erstellen" und wählen Sie "API Schlüssel" aus
6. Kopieren Sie ihren API-Schlüssel und fügen ihn in ihre lokale .env-Datei ein, damit der Code auf diesen zugreifen kann (halten Sie dabei folgende Struktur ein: YOUTUBE_API_KEY = "YOUR_KEY")

## Das muss später in die requirements.txt
Um die benötigten Pakete zu installieren, führen Sie folgende Befehle aus:

```bash
pip install --upgrade google-api-python-client
pip install --upgrade google-auth-oauthlib google-auth-httplib2
```

## Zugriff auf YouTube Abonnements einrichten
> Das Nachfolgende würde ich am Ende mit einer neuen E-Mail Adresse machen. Wenn wir es abgeben, müssen wir diejenigen, die es testen sollen als Tester mit ihren Adressen eintragen. So muss unser Projekt nicht von Google geprüft werden.

1. Gehe zu deiner Google Cloud Console und navigiere zu deinem Projekt.
2. Klicke auf APIs & Dienste > Anmeldedaten.
3. Klicke auf Anmeldedaten erstellen und wähle OAuth-Client-ID.
Wähle Desktop-App und gib einen Namen ein.
4. Klicke auf Erstellen, und lade die Client-ID-Datei (JSON) herunter. Du benötigst diese Datei für die Authentifizierung.
Speichere die heruntergeladene JSON-Datei an einem sicheren Ort, z.B. unter credentials.json.

> Hinweis zu 4.
> 
> Man braucht wirklich die ganze JSON, es sei denn, wir kriegen das auch in die .env integriert, aber da gab es bisher noch Fehler mit dem Format. Dann muss man im Code einmal die Variable auf den Pfad setzen, wo die JSON lokal gespeichert ist.
>
> Wenn man sich einmal mit dem 0auth angemeldet hat wird ein `token.pickle` erstellt, sodass man sich danach nicht mehr authentifizieren muss. Wenn ihr also das Anmelden absichtlich auslösen wollt, müsst ihr vorher `token.pickle` löschen.
>
> In eure `.env` muss also noch ein `.*json`und ein `*.pickle`.