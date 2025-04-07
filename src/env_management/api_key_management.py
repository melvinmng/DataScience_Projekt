import os
from googleapiclient.discovery import build, Resource

GoogleApiResource = Resource


def get_api_key(env_var: str) -> str | None:
    """Fetches the value of a specified environment variable with basic error handling.

    This function retrieves the value of an environment variable using `os.getenv()`.
    If an exception occurs during the retrieval process, it prints an error message
    and returns `None`.

    Args:
        env_var (str): The name of the environment variable to retrieve.

    Returns:
        str | None: The value of the environment variable as a string if it is set,
        or `None` if it is not set or an exception occurs.

    Side Effects:
        Prints error messages to standard output if an exception occurs.
    """
    try:
        api_key = os.getenv(env_var)
    except ValueError as e:
        print(f"Configuration error: {e}. Please check your .env file.")
    except Exception as e:
        print(f"Unexpected error: {e}")
    else:
        return api_key
    return None


def create_youtube_client(api_key: str) -> Resource:
    """Creates a YouTube Data API v3 client.

    This function initializes and returns a client for interacting with the
    YouTube Data API v3 using the provided API key.

    Args:
        api_key (str): The API key for authenticating with the YouTube Data API.

    Returns:
        Resource: A YouTube API client instance.

    Raises:
        googleapiclient.errors.Error: If the client creation fails.
    """
    api_service_name: str = "youtube"
    api_version: str = "v3"
    return build(api_service_name, api_version, developerKey=api_key)


if __name__ == "__main__":
    """Main execution block for testing API key retrieval and YouTube client creation."""
    try:
        google_api_key: str | None = get_api_key("TOKEN_GOOGLEAPI")
        print("Google API Key loaded:", google_api_key)

        youtube_api_key: str | None = get_api_key("YOUTUBE_API_KEY")
        if youtube_api_key:
            youtube_client: Resource = create_youtube_client(youtube_api_key)
            print("YouTube API Client successfully created.")
        else:
            print("YouTube API Key not found or is None.")
    except ValueError as e:
        print(f"Error: {e}")
