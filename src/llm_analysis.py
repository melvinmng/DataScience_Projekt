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
import re

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
     video_ids_titles_and_transcripts : list[str], interests: Optional[str] = interests, todays_free_time: Optional[float] = None, abonnements : Optional[DataFrame] = None
) -> dict[str, str]:
    prompt = (
            f"Du erhältst eine Liste von Videos in folgendem Python-Format:\n"
            f"[('Titel': 'Titel1'\n'Transkript': 'Transkript1'\n'Video-ID': 'Video-ID1'\n), ('Titel': 'Titel2'\n'Transkript': 'Transkript2'\n'Video-ID': 'Video-ID2'\n), ...]\n"
            f"Bitte wähle aus dieser Liste genau ein Video als Empfehlung aus, das am besten zu meinen Interessen passt: {interests}.\n"
            f"Antworte ausschließlich mit einer Python-Liste, die genau ein Element enthält, "
            f"z.B. [('Titel': 'Titelx'\n'Transkript': 'Transkriptx'\n'Video-ID': 'Video-IDx'\n'Begründung': 'Begründungx wieso diese Video von dir empfohlen wird')].\n"
            f"Hier ist die Liste der Videos: {video_ids_titles_and_transcripts}")

    response = ai_client.models.generate_content(
        model=ai_model,
        config=ai_generate_content_config,
        contents=prompt,
    )

    return extract_video_id_title_and_transcript(response.text)

def combine_video_id_title_and_transcript(
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
    video_id_title_and_transcript = []

    for _, video in videos.iterrows():
        title = video['Titel']
        video_id = video["Video-ID"]
        if video_id:
            transcript = get_transcript(video_id, ['de', 'en'])

            if transcript != "":
                video_id_title_and_transcript.append(f"Titel: {title}\nTranskript: {transcript}\nVideo-ID: {video_id}\n")
        else:
            raise KeyError("Keine Video-ID gefunden")
        
    return video_id_title_and_transcript

def extract_video_id_title_and_transcript(text: str) -> dict[str, str]:

    title_match = re.search(r"'?Titel'?:\s*\"(.+?)\"", text)
    title = title_match.group(1) if title_match else None

    transkript_match = re.search(
        r"'?Transkript'?:\s*\"(.+?)\"\s*,\s*'?Video-ID'?:", text, re.DOTALL
    )
    transkript = transkript_match.group(1).strip() if transkript_match else None

    video_id_match = re.search(r"'?Video-ID'?:\s*'(.+?)'", text)
    video_id = video_id_match.group(1) if video_id_match else None

    reason_match = re.search(r"'?Begründung'?:\s*'(.+?)'", text)
    reason = reason_match.group(1) if reason_match else None

    return {
        "Titel": title,
        "Transkript": transkript,
        "Video-ID": video_id,
        "Begründung": reason
    }



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
