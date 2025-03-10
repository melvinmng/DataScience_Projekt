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

## How to create a Gemini API
1. Erstelle einen Account für das Google AI Studio: https://aistudio.google.com/app/apikey?_gl=1*e137ex*_ga*MTE4NjE1OTYwLjE3NDE2MDM4Mzk.*_ga_P1DBVKWT6V*MTc0MTYwNTEyMS4xLjEuMTc0MTYwNTIzMy4wLjAuMTgyNDY0NDU1Nw..
2. Klicke auf "Get API Key"
3. Klicke auf "API Schlüssel erstellen"
4. Falls Sie ein Projekt erstellen müssen, erstellen sie ein Projekt und wählen Sie dieses für den API-Schlüssel aus
5. Klicken Sie auf "API Schlüssel in bestehendem Projekt erstellen"
6. Kopieren Sie ihren API-Schlüssel und fügen ihn in ihre lokale .env-Datei ein, damit der Code auf diesen zugreifen kann