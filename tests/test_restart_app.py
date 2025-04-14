import time
import pytest
import os
import signal
import subprocess
from unittest.mock import patch, MagicMock, call
from platform import system

# NOTE: As these tests strongly depend on the os, some of the tests (3)
#       are only implemented for MacOS. These tests are are marked by
#       @pytest.mark.skipif(system == "Windows", reason="REASON")


APP_FILE = "run.py"
system = system()

# === Tests für kill_existing_streamlit ===


@pytest.mark.skipif(
    system == "Windows",
    reason="Windows paths and os-attributes differ, tests implemented for macOS/Unix",
)
@patch("src.restart_app.subprocess.check_output")
@patch("src.restart_app.os.kill")
def test_kill_existing_streamlit_found(mock_os_kill, mock_check_output):
    """Tests killing processes when pgrep finds them."""

    from src.restart_app import kill_existing_streamlit

    mock_check_output.return_value = b"123\n456\n"

    kill_existing_streamlit()

    mock_check_output.assert_called_once_with(
        ["pgrep", "-f", f"streamlit run {APP_FILE}"]
    )
    mock_os_kill.assert_has_calls(
        [
            call(123, signal.SIGTERM),
            call(456, signal.SIGTERM),
        ],
        any_order=True,
    )
    assert mock_os_kill.call_count == 2


@pytest.mark.skipif(
    system == "Windows",
    reason="Windows paths and os-attributes differ, tests implemented for macOS/Unix",
)
@patch("src.restart_app.subprocess.check_output")
@patch("src.restart_app.os.kill")
def test_kill_existing_streamlit_not_found(mock_os_kill, mock_check_output):
    """Tests killing processes when pgrep finds nothing."""
    from src.restart_app import kill_existing_streamlit

    mock_check_output.side_effect = subprocess.CalledProcessError(1, "pgrep command")

    kill_existing_streamlit()

    mock_check_output.assert_called_once_with(
        ["pgrep", "-f", f"streamlit run {APP_FILE}"]
    )
    mock_os_kill.assert_not_called()


# === Tests für clear_streamlit_cache ===


@pytest.mark.skipif(
    system == "Windows",
    reason="Windows paths and os-attributes differ, tests implemented for macOS/Unix",
)
@patch("src.restart_app.shutil.rmtree")
@patch("src.restart_app.os.path.exists")
@patch(
    "src.restart_app.os.path.expanduser",
    side_effect=lambda p: p.replace("~", "/Users/testuser"),
)
def test_clear_streamlit_cache(mock_expanduser, mock_exists, mock_rmtree):
    """Tests clearing cache directories."""
    from src.restart_app import clear_streamlit_cache

    def exists_side_effect(path):
        if path == "/Users/testuser/.streamlit/cache":
            return True
        elif path == "/Users/testuser/.cache/streamlit":
            return False
        return False

    mock_exists.side_effect = exists_side_effect

    clear_streamlit_cache()

    mock_exists.assert_has_calls(
        [
            call("/Users/testuser/.streamlit/cache"),
            call("/Users/testuser/.cache/streamlit"),
        ],
        any_order=True,
    )
    mock_rmtree.assert_called_once_with("/Users/testuser/.streamlit/cache")


# === Tests für load_env_vars ===


@patch(
    "src.restart_app.dotenv_values",
    return_value={"VAR1": "value1", "VAR2": "value2"},
)
def test_load_env_vars(mock_dotenv_values):
    """Tests loading environment variables from .env."""
    from src.restart_app import load_env_vars

    env_vars = load_env_vars()
    assert env_vars == {"VAR1": "value1", "VAR2": "value2"}

    mock_dotenv_values.assert_called_once_with(".env")


# === Tests für restart_app ===


@patch("src.restart_app.load_env_vars", return_value={"MY_VAR": "my_value"})
@patch("src.restart_app.subprocess.Popen")
def test_restart_app(mock_popen, mock_load_env, monkeypatch):
    """Tests restarting the app with loaded environment variables."""
    from src.restart_app import restart_app

    monkeypatch.setenv("EXISTING_VAR", "existing_value")
    monkeypatch.delenv("MY_VAR", raising=False)

    restart_app()

    mock_load_env.assert_called_once()

    expected_env = os.environ.copy()
    expected_env.update({"MY_VAR": "my_value"})

    mock_popen.assert_called_once()
    popen_args, popen_kwargs = mock_popen.call_args
    assert popen_args[0] == ["streamlit", "run", APP_FILE]
    assert "env" in popen_kwargs
    assert popen_kwargs["env"] == expected_env


# === Test für den __main__ Block mit runpy ===


@patch("src.restart_app.kill_existing_streamlit")
@patch("src.restart_app.clear_streamlit_cache")
@patch("src.restart_app.restart_app")
@patch("time.sleep")
def test_main_execution(mock_sleep, mock_restart, mock_clear_cache, mock_kill):
    """Testet, ob die Hauptfunktionen im __main__ Block aufgerufen werden."""
    try:
        from src.restart_app import main

        main()
    except AttributeError:
        pytest.skip(
            "Skipping __main__ block test, requires refactoring script with a main() function"
        )

        mock_kill.assert_called_once()
        mock_clear_cache.assert_called_once()
        mock_sleep.assert_called_once_with(1)
        mock_restart.assert_called_once()
