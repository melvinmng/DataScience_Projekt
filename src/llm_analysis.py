from typing import Callable
from .settings import (
    ai_client,
    ai_model,
    ai_generate_content_config,
    interests,
    languages,
)
from .youtube_transcript import get_transcript
from pandas import DataFrame
import re
import concurrent.futures
import multiprocessing
import json


def get_summary(transcript: str, title) -> str | None:
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
        contents=f"Fasse mir dieses Video unglaublich kurz und prägnant zusammen, sodass nur das Hauptthema des Videos klar wird: {transcript}. Gehe dabei nur auf die Kernaussage ein. Vergleiche zudem den Inhalt des Videos mit dem Titel: {title} und untersuche diesen auf potenziellen Clickbait.",
    )
    if response.text:
        return response.text
    else:
        return None


def get_summary_without_spoiler(transcript: str) -> str | None:
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

    if response.text:
        return response.text
    else:
        return None


def get_recommendation(
    video_ids_titles_and_transcripts: list[str],
    interests: str | None = interests,
    todays_free_time: float | None = None,
    abonnements: DataFrame | None = None,
) -> str | None:
    prompt = (
        f"Du erhältst eine Liste von Videos in folgendem Python-Format:\n"
        f"[('Titel': 'Titel1'\n'Transkript': 'Transkript1'\n'Video-ID': 'Video-ID1'\n), ('Titel': 'Titel2'\n'Transkript': 'Transkript2'\n'Video-ID': 'Video-ID2'\n), ...]\n"
        f"Bitte wähle aus dieser Liste genau ein Video als Empfehlung aus, das am besten zu meinen Interessen passt: {interests}. Falls kein Video zu meinen Interessen passt, wähle eins aus, welches am ehesten passen würde.\n"
        f"Deine Antowrt muss folgendermaßen sturkturiert sein: 'video_id': 'video_id'\n'Begründung': 'Begründung wieso diese Video von dir empfohlen wird'(achte vor allem auf die Keywords 'video_id' und 'Begründung' - sie müssen enthalten und richtig geschrieben sein)\n"
        f"Hier ist die Liste der Videos: {video_ids_titles_and_transcripts}"
    )

    response = ai_client.models.generate_content(
        model=ai_model,
        config=ai_generate_content_config,
        contents=prompt,
    )

    print(f"\n{response.text}\n")

    if response.text:
        return response.text
    else:
        return None



def get_transcript_safe(video_id):
    """ Wrapper-Funktion, um Fehler bei einzelnen Videos zu vermeiden. """
    try:
        return get_transcript(video_id)
    except Exception as e:
        return f"Fehler beim Abrufen des Transkripts: {e}"

def combine_video_id_title_and_transcript(videos: list) -> list[str]:
    """
    Holt die Transkripte parallel mit Threads.
    """
    num_videos = len(videos)
    num_threads = min(num_videos, multiprocessing.cpu_count() * 2) 
    video_id_title_and_transcript = []

    # Mapping von Video-IDs auf Titel
    video_map = {video["video_id"]: video["title"] for video in videos if "video_id" in video}

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        future_to_video_id = {
            executor.submit(get_transcript_safe, video_id): video_id
            for video_id in video_map
        }

        for future in concurrent.futures.as_completed(future_to_video_id):
            video_id = future_to_video_id[future]
            title = video_map[video_id]
            transcript = future.result()

            if transcript and transcript.strip():
                video_id_title_and_transcript.append(
                    f"Titel: {title}\nTranskript: {transcript}\nVideo-ID: {video_id}\n"
                )

    return video_id_title_and_transcript



def extract_video_id_and_reason(text: str, on_fail: Callable ):
    def extract_field(fieldname: str, text: str) -> str | None:
        pattern = rf'"{fieldname}":\s*"(.*?)"'
        match = re.search(pattern, text)
        return match.group(1).strip() if match else None

    video_id = extract_field("video_id", text)
    reason = extract_field("Begründung", text)

    if video_id and reason:
        return {"video_id": video_id, "Begründung": reason}
    else:
        if on_fail:
            on_fail()
        return None



def check_for_clickbait(transcript: str, title: str) -> str:

    if transcript:
        response = ai_client.models.generate_content(
            model=ai_model,
            config=ai_generate_content_config,
            contents=f"Analysiere dieses Video auf Clickbait-Elemente: {transcript}. Achte darauf, nicht inhaltlich zu spoilern, aber gebe dennoch alle Clickbait-Elemente, die dir auffallen aus und vergleiche den Ihnalt mit dem Titel: {title}.",
        )

        if response.text:
            return response.text
        else:
            return "no response"
    else:
        return "no transcript"


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


def get_subscriptions_based_on_interests(
    subscriptions: str, interests: str, number_of_channels: int
) -> list:
    prompt = (
        f"Du erhälts einen String an Kanalnamen und ihrer zugehörigen beschreibung die ich mit meinem Youtube Account abonniert habe.\n"
        f"Hier ein Bespiel: 'channel_1:description_1,channel_2:description_2,....'"
        f"Zudem übergebe ich dir meine aktuellen Interessen.\n"
        f"Anschließend sollt du bassierend auf meinen Interessen aus dieser Liste {number_of_channels} Youtube Kanäle filtern, die zu meinen aktuellen Interessen passen. Es dürfen ausschließlich nur Kanäle sein, die in meiner Liste stehen. Falls du in dieser Liste keine {number_of_channels} Kanäle findest die zu meinen Interessen passen, dann wähle aus meiner Liste Kanäle aus, die nah verwandt mit meinen Interessen sind.\n"
        f"Um die richtigen Kanäle aus der Liste auszuwählen, solltest du dir zu jedem Kanal in meiner Liste eine Kanalbeschreibung beschaffen."
        f"Gebe mir auschließlich nur einen String zurück mit den {number_of_channels} von dir ausgwählten Kanälen. Nur die Liste. Keine Beschreibung, warum du die Kanäle ausgewählt hast, etc. Die Kanäle müssen hintereinander geschrieben werden.\n"
        f"Der Kanalname muss zudem exakt so geschrieben sein, wie er im string heißt. ALso nichts am Namen verändern."
        "Hier ist ein Bepsiel für den String: 'Kanal1, Kanal2,...'\n"
        f"Hier ist die Liste an Youtube Kanälen die ich abonniert habe: {subscriptions}\n"
        f"Hier sind meine Interessen: {interests}"
    )

    response = ai_client.models.generate_content(
        model=ai_model, config=ai_generate_content_config, contents=prompt
    )

    return response.text


if __name__ == "__main__":
    get_recommendation()
