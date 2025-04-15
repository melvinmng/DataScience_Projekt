import pytest
from unittest.mock import patch
import os


# === Deprecated ===

# NOTE: In order to prevent FileNotFoundErrors during tests, the global patch prevent_load_dotenv_globally has been implemented.
#       As this patch conflicts with the former test_load_dotenv_called, this test has to be skipped now and
#       can only be tested when the global patch is deactivated.
#       To learn more, read the Docstring of prevent_load_dotenv_globally in tests/conftest.py


@pytest.mark.skip(
    reason="Not used anymore as it conflicts with the global patch 'prevent_load_dotenv_globally' used to prevent FileNotFoundErrors"
)
@patch("dotenv.load_dotenv")
def test_load_dotenv_called(mock_load_dotenv):
    """
    Tests if dotenv.load_dotenv is called when config_env is imported or run.

    Not used anymore as it conflicts with the global patch
    'prevent_load_dotenv_globally' used to prevent FileNotFoundErrors

    """
    try:
        import src.env_management.config_env
    except ImportError:
        pytest.fail("Failed to import src.config_env")

    mock_load_dotenv.assert_called_once()
