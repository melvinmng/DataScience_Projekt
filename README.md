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