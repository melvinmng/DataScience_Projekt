import os
import signal
import subprocess
import time
import shutil

APP_FILE = "run.py"

def kill_existing_streamlit():
    try:
        result = subprocess.check_output(["pgrep", "-f", f"streamlit run {APP_FILE}"])
        pids = result.decode().split()
        for pid in pids:
            print(f"🔪 Beende Streamlit-Prozess {pid}")
            os.kill(int(pid), signal.SIGTERM)
    except subprocess.CalledProcessError:
        print("ℹ️ Kein laufender Streamlit-Prozess gefunden.")

def clear_streamlit_cache():
    paths = [
        os.path.expanduser("~/.streamlit/cache"),
        os.path.expanduser("~/.cache/streamlit"),
    ]
    for path in paths:
        if os.path.exists(path):
            shutil.rmtree(path)
            print(f"🧹 Gelöscht: {path}")

def load_env_vars():
    from dotenv import dotenv_values
    return dotenv_values(".env")

def restart_app():
    env_vars = load_env_vars()
    print(f"🌍 Starte App mit Environment: {env_vars}")
    subprocess.Popen(
        ["streamlit", "run", APP_FILE],
        env={**os.environ, **env_vars}
    )

if __name__ == "__main__":
    kill_existing_streamlit()
    clear_streamlit_cache()
    time.sleep(1)
    restart_app()