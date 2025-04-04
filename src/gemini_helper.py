from typing import Callable
from google import genai
from google.genai import types
from pandas import DataFrame
import re
import concurrent.futures
import multiprocessing
import json
from .youtube_helper import get_transcript
from .key_management.api_key_management import get_api_key


################# Initialization ###############################
api_key = get_api_key("TOKEN_GOOGLEAPI")

if not api_key:
    raise ValueError("API Key nicht gefunden (leer oder nicht vorhanden).")
else:
    print("API Key erfolgreich geladen.")

try:
    print("Versuche Gemini Client zu erstellen...")
    ai_client = genai.Client(api_key)
    print("Client erfolgreich erstellt.")
except Exception as e:
    raise RuntimeError(
        f"Fehler beim Erstellen des genai Clients mit gefundenem Key: {e}"
    ) from e
else:
    print("API_KEY gefunden")

ai_model = "gemini-2.0-flash"
ai_generate_content_config = types.GenerateContentConfig(
    temperature=1,
    top_p=0.95,
    top_k=40,
    max_output_tokens=8192,
    response_mime_type="text/plain",
    system_instruction=[
        types.Part.from_text(
            text="""Du bist ein Experte im Bereich Datenanalyse und For-You-Pages. 
            Im Folgenden wirst du immer wieder YouTube-Videos und ihre Transkripte
            zugeschickt bekommen und ausgehend von diesen Inhalte zusammenfassen, 
            Clickbait erkennen und ausgehend von der verbleibenden Zeit des Users, 
            Vorschläge machen, welche der Videos er sich am ehesten anschauen sollte 
            (kein Clickbait, seinen Interessen entsprechend)."""
        ),
    ],
)


def get_short_summary_for_watch_list(
    transcript: str, title: str, channel: str
) -> str | None:
    """Briefly summarizes video for watch list.

    Args:
        transcript (str): transcript of YouTube video
        title (str): title of YouTube video
        channel (str): YouTube Channel ID

    Raises:
        ValueError: Key not found.

    Returns:
        str | none: Gemini AI response
    """
    try:
        response = ai_client.models.generate_content(
            model=ai_model,
            config=ai_generate_content_config,
            contents=f"""
            Fasse mir dieses Video unglaublich kurz und prägnant zusammen,
            sodass nur das Hauptthema des Videos klar wird. Transkript: {transcript}. 
            Zusätzlich gebe ich dir noch den Titel des Videos und den Kanalnamen. 
            Titel:{title}, Channel:{channel}. 
            Gebe mir zudem nur die Zusammenfassung zurück. Keine Überschriften etc.""",
        )
        if response.text:
            return response.text
        else:
            return None
    except:
        return transcript


def get_channel_recommondations(
    history, channels, number_of_recommendations, interests
) -> list[str] | str:
    """Reccomends YouTube Channels based on user preferences.

    Args:
        history (_type_): @Adrian
        channels (_type_): @Adrian
        number_of_recommendations (_type_): @Adrian
        interests (_type_): @Adrian

    Returns:
        _type_: @Adrian
    """
    response = ai_client.models.generate_content(
        model=ai_model,
        config=ai_generate_content_config,
        contents=(
            f"Gebe mir anhand meiner Video History {history} genau {number_of_recommendations} Kanalvorschläge die mir gefallen könnten. DIE KANÄLE DIE DU MIR VORSCHLÄGST MÜSSEN NEUE KANÄLE SEIN. SIE DÜRFEN NICHT IN MEINER HISTORY STEHEN. Gebe mir AUSSCHLIESLICH nur die Namen der Kanäle in reiner Textform und Kommagetrent zurück.\n"
            f"Zusätzlich erhälts du meine Abos umd noch genauere Empfehlungen zu geben. Abos: {channels}. Deine Empfehlungen müssen Kanäle sein, die ich noch nicht abonniert habe.\n"
            f"Berücksichtige außerdem noch meine aktuellen Interessen: {interests} und gewichte diese besonders in deiner Auswahl. Es sollte für jede Interesse ein Kanal in deiner Auswahl dabei sein."
            f"Gebe wirklich außschließlich nur die Kanäle kommagetrennt zurück. Bsp: Kanal1, Kanal2, Kanal3, etc...WIRKLICH NUR DIE KANÄLE NICHTS ANDERES."
        ),
    )
    if response.text:
        print(response.text)
        return response.text.split(",")
    else:
        return "Fehler"


def get_summary(transcript: str, title) -> str | None:
    """
    Offers a summary of a YouTube video using its transcript. Spoilers possible.

    Args:
        transcript (str): transcript of YouTube video
        title (str): title of YouTube video

    Returns:
        str: summary of YouTube video
    """
    response = ai_client.models.generate_content(
        model=ai_model,
        config=ai_generate_content_config,
        contents=f"""Fasse mir dieses Video unglaublich 
        kurz und prägnant zusammen, sodass nur das Hauptthema des Videos 
        klar wird: {transcript}. Gehe dabei nur auf die Kernaussage ein. 
        Vergleiche zudem den Inhalt des Videos mit dem Titel: {title} und 
        untersuche diesen auf potenziellen Clickbait.
        """,
    )
    if response.text:
        return response.text
    else:
        return None


def get_summary_without_spoiler(transcript: str) -> str | None:
    """
    Offers a summary of a YouTube video using its transcript. Spoilers prevented.

    Args:
        transcript (str): transcript of YouTube video

    Returns:
        str: summary of YouTube video without spoilers
    """
    response = ai_client.models.generate_content(
        model=ai_model,
        config=ai_generate_content_config,
        contents=(
            f"Fasse mir dieses Video zusammen: {transcript}. Gehe dabei nur auf den Inhalt und mögliche Clickbait-Elemente ein und achte darauf, keinen Inhalt zu spoilern."
        ),
    )

    if response.text:
        return response.text
    else:
        return None


def get_recommendation(
    video_ids_titles_and_transcripts: list[str],
    interests: str | None = None,
    todays_free_time: float | None = None,
    subscriptions: DataFrame | None = None,
) -> str | None:
    """Gets video recommendations based on user preferences.

    Args:
        video_ids_titles_and_transcripts (list[str]): List of YouTube video IDs, titles, transcripts
        interests (str | None, optional): User interests. Defaults to None.
        todays_free_time (float | None, optional): User's free time. Defaults to None.
        subscriptions (DataFrame | None, optional): User's subsricptions. Defaults to None.

    Returns:
        str | None: Gemini AI response
    """
    prompt = (
        f"Du erhältst eine Liste von Videos in folgendem Python-Format:\n"
        f"[('Titel': 'Titel1'\n'Transkript': 'Transkript1'\n'Video-ID': 'Video-ID1'\n), ('Titel': 'Titel2'\n'Transkript': 'Transkript2'\n'Video-ID': 'Video-ID2'\n), ...]\n"
        f"Bitte wähle aus dieser Liste genau ein Video als Empfehlung aus, das am besten zu meinen Interessen passt: {interests}. Falls kein Video zu meinen Interessen passt, wähle eins aus, welches am ehesten passen würde.\n"
        f"Deine Antowrt muss folgendermaßen sturkturiert sein: 'video_id': 'video_id'\n'explanation': 'Begründung wieso diese Video von dir empfohlen wird'(achte vor allem auf die Keywords 'video_id' und 'explanation' - sie müssen enthalten und richtig geschrieben sein)\n"
        f"DU MUSST DIR ABSOULT SICHER SEIN, DASS DIE VIDEO_ID ZUR BEGRÜNDUNG UMD ZUM TRANSCRIPT PASST.\n"
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


def get_transcript_safe(video_id: str):
    """Wrapper function to avoid errors when handling transcripts.

    Args:
        video_id (str): YouTube video ID

    Returns:
        _type_: _description_ @Adrian @Melvin
    """
    # Wrapper-Funktion, um Fehler bei einzelnen Videos zu vermeiden.
    try:
        return get_transcript(video_id)
    except Exception as e:
        return f"Fehler beim Abrufen des Transkripts: {e}"


def combine_video_id_title_and_transcript(videos: list) -> list[str]:
    """Combines YouTube video id, title and transcript with threads.

    Args:
        videos (list): List of YouTube videos

    Returns:
        list[str]: List of YouTube videos combined with key features
    """
    # Holt die Transkripte parallel mit Threads.
    num_videos = len(videos)
    num_threads = min(num_videos, multiprocessing.cpu_count() * 2)
    video_id_title_and_transcript = []

    # Mapping von Video-IDs auf Titel
    video_map = {
        video["video_id"]: video["title"] for video in videos if "video_id" in video
    }

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


def extract_video_id_and_reason(
    json_str: str, on_fail: Callable | None = None
) -> dict[str, str] | None:
    """Extracts video ID and reason from a string (normally a response from Gemini) using regex.

    Args:
        json_str (str): Gemini's response.
        on_fail (Callable): a function to call if parsing fails.

    Returns:
        dict[str, str]: Dict containing the video_id and an explanation
        None if extraction fails
    """

    def extract_field(fieldname: str, text: str) -> str | None:
        """Extracts a certain snippet from a String (following the structure used by Gemini)

        Args:
            fieldname (str): Name of the category to extract (e. g. video_id, explanation)
            text (str): _description_

        Returns:
            str: Extracted snippet
            None: Snippet is not included in given text
        """
        pattern = rf'"{fieldname}":\s*"((?:\\.|[^"\\])*)"'
        match = re.search(pattern, text, re.DOTALL)
        return match.group(1).strip() if match else None

    video_id = extract_field("video_id", json_str)
    explanation = extract_field("explanation", json_str)

    if video_id and explanation:
        return {"video_id": video_id, "Begründung": explanation}
    else:
        if on_fail:
            on_fail()
        return None


def check_for_clickbait(transcript: str, title: str) -> str:
    """Checks a video for clickbait based on transcript and title.

    Args:
        transcript (str): Transcript of YouTube video
        title (str): Title of YOuTube video

    Returns:
        str: Gemini AI response
    """
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
    """Allows a live interaction with Gemini. For test cases only!

    Returns:
        str: Gemini AI response to the user's input in terminal
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
) -> str | None:
    """Gets subscriptions based on user's preferences.

    Args:
        subscriptions (str): @Adrian
        interests (str): @Adrian
        number_of_channels (int): @Adrian

    Returns:
        str | None: Gemini's response as string or None
    """
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
    if response.text:
        return response.text
    else:
        return None


if __name__ == "__main__":
    pass
