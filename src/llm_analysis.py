from typing import Optional
from .settings import (
    ai_client,
    ai_model,
    ai_generate_content_config,
    interests,
    languages,
)
from .youtube_transcript import get_transcript
import googleapiclient
from pandas import DataFrame

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
     video_ids_and_transcripts : list[str], interests: Optional[str] = interests, todays_free_time: Optional[float] = None, abonnements : Optional[DataFrame] = None
) -> str:

    response = ai_client.models.generate_content(
        model=ai_model,
        config=ai_generate_content_config,
        contents=f"Empfehle mir eins dieser Videos anhand ihrer Transkripte. Beachte dabei meine Interessen {interests}. Du erhälst die Video Ids und die zugehörigen Transkripte in Form einer Python Liste. Gib mir als Empfehlung wieder eine Python Liste zurück, die Tupel mit der Video Id und dem zugehörigen Transkript enthält.: {video_ids_and_transcripts}",
    )

    return response.text

def combine_video_id_and_transcript(
    videos: DataFrame
) -> str:
    """
    Erstellt eine Empfehlungsliste, in der für jedes Video der Titel 
    und das zugehörige Transkript (in den angegebenen Sprachen) angezeigt werden.

    Args:
        videos (DataFrame): DataFrame mit Trend-Videos; erwartet Spalten "Titel" und "VideoID".

    Returns:
        str: Formatierter String mit Titeln und Transkripten der Videos.
    """
    video_id_and_transcript = []

    for _, video in videos.iterrows():
        title = video['Titel']
        video_id = video["Video-ID"]
        if video_id:
            transcript = get_transcript(video_id, ['de', 'en'])
        else:
            raise KeyError("Keine Video-ID gefunden")
        
        video_id_and_transcript.append(f"Titel: {title}\nTranskript: {transcript}\n")
    
    return video_id_and_transcript



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

    return response.text


if __name__ == "__main__":
    get_recommendation()
