import pytest
from unittest.mock import patch
import os


@patch("dotenv.load_dotenv")
def test_load_dotenv_called(mock_load_dotenv):
    """
    Tests if dotenv.load_dotenv is called when config_env is imported or run.
    """
    try:
        import src.env_management.config_env
    except ImportError:
        pytest.fail("Failed to import src.config_env")

    mock_load_dotenv.assert_called_once()
