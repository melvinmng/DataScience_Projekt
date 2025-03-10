from typing import Optional
from .settings import (
    ai_client,
    ai_model,
    ai_generate_content_config,
    interests,
    languages,
)
from .youtube_transcript import get_transcript

# from ... get_video_id / video_id


def get_summary(
    transcript: str
) -> str:
    """
    Offers a summary of a YouTube video using its transcript. Spoilers possible.

    Args:
        transcript (str): Transcript of the YouTube video

    Returns:
        str: summary of the YouTube video
    """
    response = ai_client.models.generate_content(
        model=ai_model,
        config=ai_generate_content_config,
        contents=f"Fasse mir dieses Video zusammen: {transcript}",
    )

    return response.text


def get_summary_without_spoiler(
    transcript: str
) -> str:
    """
    Offers a summary of a YouTube video using its transcript. Spoilers prevented.

    Args:
        transcript (str): Transcript of the YouTube video

    Returns:
        str: summary of the YouTube video without spoilers
    """
    response = ai_client.models.generate_content(
        model=ai_model,
        config=ai_generate_content_config,
        contents=f"Fasse mir dieses Video zusammen: {transcript}. Achte dabei darauf, keinen Inhalt zu spoilern",
    )

    return response.text


def get_recommendation(
    interests: Optional[str] = interests, todays_free_time: Optional[float] = None
) -> str:
    pass


def check_for_clickbait():
    pass


def live_conversation() -> str:
    """
    Allows a live interaction with Gemini. For test cases only!

    Returns:
        str: Gemini's response to the user's question/prompt as text in terminal
    """
    print("Starte Konversation")
    question = input("Was kann ich für dich tun?")
    response = ai_client.models.generate_content(
        model=ai_model, config=ai_generate_content_config, contents=question
    )
    print(response.text)


if __name__ == "__main__":
    print(get_summary())
