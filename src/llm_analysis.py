from typing import Callable
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


def get_summary(transcript: str) -> str:
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
        contents=f"Fasse mir dieses Video zusammen: {transcript}. Gehe dabei nur auf den Inhalt und mögliche Clickbait-Elemente ein.",
    )

    return response.text


def get_summary_without_spoiler(transcript: str) -> str:
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
        contents=f"Fasse mir dieses Video zusammen: {transcript}. Gehe dabei nur auf den Inhalt und mögliche Clickbait-Elemente ein und achte darauf, keinen Inhalt zu spoilern.",
    )

    return response.text


def get_recommendation(
    video_ids_titles_and_transcripts: list[str],
    interests: str | None = interests,
    todays_free_time: float | None = None,
    abonnements: DataFrame | None = None,
) -> str:
    prompt = (
        f"Du erhältst eine Liste von Videos in folgendem Python-Format:\n"
        f"[('Titel': 'Titel1'\n'Transkript': 'Transkript1'\n'Video-ID': 'Video-ID1'\n), ('Titel': 'Titel2'\n'Transkript': 'Transkript2'\n'Video-ID': 'Video-ID2'\n), ...]\n"
        f"Bitte wähle aus dieser Liste genau ein Video als Empfehlung aus, das am besten zu meinen Interessen passt: {interests}.\n"
        f"Antworte ausschließlich mit einer Python-Liste, die genau ein Element enthält, das genau folgende Struktur einhalten muss (achte vor allem auf die Keywords 'Titel', 'Video-ID' und 'Begründung' - sie müssen enthalten und richtig geschrieben sein) "
        f"z.B. [('Titel': 'Titelx'\n'Video-ID': 'Video-IDx'\n'Begründung': 'Begründungx wieso diese Video von dir empfohlen wird')].\n"
        f"Hier ist die Liste der Videos: {video_ids_titles_and_transcripts}"
    )

    response = ai_client.models.generate_content(
        model=ai_model,
        config=ai_generate_content_config,
        contents=prompt,
    )

    return response.text


def combine_video_id_title_and_transcript(videos: DataFrame) -> list[str]:
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
        title = video["Titel"]
        video_id = video["Video-ID"]
        if video_id:
            transcript = get_transcript(video_id)

            if transcript != "":
                video_id_title_and_transcript.append(
                    f"Titel: {title}\nTranskript: {transcript}\nVideo-ID: {video_id}\n"
                )
        else:
            raise KeyError("Keine Video-ID gefunden")

    return video_id_title_and_transcript


def extract_video_id_title_and_reason(
    text: str, on_fail: Callable | None = None
) -> dict[str, str] | None:

    def extract_field(fieldname: str, text: str) -> str | None:
        """
        Sucht nach einem Feld wie 'Titel', 'Video-ID' oder 'Begründung' und gibt den Inhalt zurück.
        Akzeptiert einfache oder doppelte Anführungszeichen (aber nur, wenn sie korrekt paaren).
        """
        pattern = rf"'?{fieldname}'?:\s*(?P<q>['\"])(.+?)(?P=q)"
        match = re.search(pattern, text, re.DOTALL)
        return match.group(2).strip() if match else None

    # Einzelne Felder extrahieren
    title = extract_field("Titel", text)
    video_id = extract_field("Video-ID", text)
    reason = extract_field("Begründung", text)

    if title and video_id and reason:
        return {"Titel": title, "Video-ID": video_id, "Begründung": reason}
    else:
        if on_fail:
            on_fail()
        return None


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
