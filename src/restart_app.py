import os
import signal
import subprocess
import time
import shutil
import platform
from dotenv import dotenv_values

APP_FILE = "run.py"


def kill_existing_streamlit() -> None:
    """Beendet existierende Streamlit-Prozesse basierend auf Betriebssystem."""
    system = platform.system()

    if system == "Windows":
        try:
            result = subprocess.check_output(["tasklist"], text=True)
            for line in result.splitlines():
                if "streamlit.exe" in line.lower():
                    print(f"🔪 Beende Streamlit-Prozess (Windows): streamlit.exe")
                    subprocess.run(
                        ["taskkill", "/f", "/im", "streamlit.exe"], check=True
                    )
        except subprocess.CalledProcessError:
            print("ℹ️ Kein laufender Streamlit-Prozess unter Windows gefunden.")
    else:
        try:
            result = subprocess.check_output(
                ["pgrep", "-f", f"streamlit run {APP_FILE}"]
            )
            pids = result.decode().split()
            for pid in pids:
                print(f"🔪 Beende Streamlit-Prozess {pid}")
                os.kill(int(pid), signal.SIGTERM)
        except subprocess.CalledProcessError:
            print("ℹ️ Kein laufender Streamlit-Prozess unter Unix/macOS gefunden.")


def clear_streamlit_cache() -> None:
    """Löscht bekannte Cache-Ordner von Streamlit."""
    cache_paths = [
        os.path.expanduser("~/.streamlit/cache"),
        os.path.expanduser("~/.cache/streamlit"),
    ]
    for path in cache_paths:
        if os.path.exists(path):
            shutil.rmtree(path)
            print(f"🧹 Gelöscht: {path}")


def load_env_vars() -> dict[str, str]:
    """Lädt .env-Datei, wenn vorhanden."""
    return dotenv_values(".env")


def restart_app() -> None:
    """Startet die Streamlit App neu mit geladenen .env Variablen."""
    env_vars = load_env_vars()
    print(f"🌍 Starte App mit Environment: {env_vars}")
    subprocess.Popen(["streamlit", "run", APP_FILE], env={**os.environ, **env_vars})


if __name__ == "__main__":
    kill_existing_streamlit()
    clear_streamlit_cache()
    time.sleep(1)
    restart_app()
