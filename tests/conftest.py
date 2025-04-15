import pytest


@pytest.fixture(autouse=True)
def prevent_load_dotenv_globally(monkeypatch):
    """
    Prevent dotenv.load_dotenv from reading files during the test session.

    This autouse, session-scoped fixture uses monkeypatch to replace the original
    dotenv.load_dotenv function with a no-op lambda *before* any tests run.
    This is necessary because some modules (like config_env) call load_dotenv
    at the module level upon import. Patching at the source ensures the dummy
    function is used, avoiding FileNotFoundError if a .env file is not present
    during test collection or setup.
    """
    try:
        import src.env_management.config_env

        monkeypatch.setattr(
            src.env_management.config_env, "load_dotenv", lambda *args, **kwargs: None
        )
        print("\nINFO: Patched load_dotenv in config_env globally for test session.")
    except ImportError:
        print(
            "\nWARNING: Could not patch load_dotenv in src.env_management.config_env (ImportError)."
        )
    except AttributeError:
        print(
            "\nWARNING: Could not patch load_dotenv in src.env_management.config_env (AttributeError)."
        )
