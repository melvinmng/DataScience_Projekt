from typing import Callable, Any
from google import genai
from google.genai import types
from pandas import DataFrame
import re
import concurrent.futures
import multiprocessing
import json
from .youtube_helper import get_transcript
from ..env_management.api_key_management import get_api_key


################# Initialization ###############################
api_key = get_api_key("TOKEN_GOOGLEAPI")

if not api_key:
    raise ValueError("API Key nicht gefunden (leer oder nicht vorhanden).")
else:
    print("API Key erfolgreich geladen.")

try:
    print("Versuche Gemini Client zu erstellen...")
    ai_client = genai.Client(api_key=api_key)
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
    """Generates a brief video summary suitable for a watch list using Gemini.

    Args:
        transcript (str): The transcript text of the YouTube video.
        title (str): The title of the YouTube video.
        channel (str): The name or ID of the YouTube channel.

    Returns:
        str | None: The generated summary text from Gemini, or None if the
                       API call yields no text. Returns the original transcript
                       if an exception occurs during the API call.
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


def get_channel_recommendations(
    history: Any,
    channels: Any,
    number_of_recommendations: int,
    interests: str,
) -> list[str] | str:
    """Recommends new YouTube channels based on user preferences and history using Gemini.

    Args:
        history (Any): User's video watch history data. The exact format depends
                       on how it's provided to the function. Used within the prompt.
        channels (Any): User's current subscriptions or channel data. The exact format
                        depends on how it's provided. Used within the prompt.
        number_of_recommendations (int): The exact number of channel names to recommend.
        interests (str): A string describing the user's interests, used to guide
                         recommendations.

    Returns:
        list[str] | str: A list of recommended channel names if successful,
                         otherwise the string "Fehler" if the API call yields no text.
                         Returns "Fehler" also if an exception occurs.
    """
    try:
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
    except Exception as e:
        return "Fehler"


def get_summary(transcript: str, title: str) -> str | None:
    """Generates a summary of a YouTube video transcript using Gemini.

    May include spoilers. Compares content to title to check for clickbait.

    Args:
        transcript (str): The transcript text of the YouTube video.
        title (str): The title of the YouTube video.

    Returns:
        str | None: The generated summary and clickbait analysis text,
                       or None if the API call yields no text or an error occurs.
    """
    try:
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
    except Exception as e:
        return f"Fehler beim Erzeugen der Zusammenfassung: {e}"


def get_summary_without_spoiler(transcript: str, title: str) -> str | None:
    """Generates a non-spoiler summary of a YouTube video transcript using Gemini.

    Focuses on content description and potential clickbait elements without
    revealing key plot points or outcomes.

    Args:
        transcript (str): The transcript text of the YouTube video.
        title (str): The title of the YouTube video.


    Returns:
        str | None: The generated non-spoiler summary text, or None if the
                       API call yields no text or an error occurs.
    """
    try:
        response = ai_client.models.generate_content(
            model=ai_model,
            config=ai_generate_content_config,
            contents=(
                f"""Fasse mir dieses Video unglaublich 
            kurz und prägnant zusammen, sodass nur das Hauptthema des Videos 
            klar wird: {transcript}. Gehe dabei nur auf die Kernaussage ein. 
            Vergleiche zudem den Inhalt des Videos mit dem Titel: {title} und 
            untersuche diesen auf potenziellen Clickbait. Achte dabei darauf,
            keinen Inhalt zu spoilern!
            """
            ),
        )

        if response.text:
            return response.text
        else:
            return None
    except Exception as e:
        return f"Fehler beim Erzeugen der Zusammenfassung: {e}"


def get_recommendation(
    video_ids_titles_and_transcripts: list[str],
    interests: str | None = None,
    todays_free_time: float | None = None,
    subscriptions: DataFrame | None = None,
) -> str | None:
    """Gets a single video recommendation from a list based on user preferences using Gemini.

    Selects one video from the provided list that best matches the user's interests.
    The response is expected in a specific string format including 'video_id' and 'explanation'.

    Args:
        video_ids_titles_and_transcripts (list[str]): A list of strings, each containing
                                                      title, transcript, and video ID
                                                      for a single video.
        interests (str | None, optional): User interests to guide selection. Defaults to None.
        todays_free_time (float | None, optional): User's available time (currently unused
                                                     in the prompt). Defaults to None.
        subscriptions (DataFrame | None, optional): User's subscriptions data (currently unused
                                                        in the prompt). Defaults to None.

    Returns:
        str | None: The raw Gemini response string containing the recommended
                       video_id and explanation, or None if the API call fails or
                       yields no text. The string requires further parsing by
                       extract_video_id_and_reason.
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


def get_transcript_safe(video_id: str) -> str:
    """Safely retrieves a video transcript, returning an error message string on failure.

    Acts as a wrapper around get_transcript() to catch exceptions.

    Args:
        video_id (str): The YouTube video ID.

    Returns:
        str: The video transcript if successful, otherwise an error message string.
    """
    try:
        return get_transcript(video_id)
    except Exception as e:
        return f"Fehler beim Abrufen des Transkripts: {e}"


def combine_video_id_title_and_transcript(
    videos: list[dict[str, Any]],
) -> list[str]:
    """Combines video ID, title, and transcript into formatted strings using threads.

    Fetches transcripts concurrently for efficiency.

    Args:
        videos (list[dict[str, Any]]): A list of dictionaries, where each dictionary
                                       represents a video and must contain at least
                                       'video_id' and 'title' keys.

    Returns:
        list[str]: A list of formatted strings, each containing the title,
                   transcript, and video ID for one video where a transcript
                   was successfully retrieved.
    """
    num_videos = len(videos)
    num_threads = min(num_videos, multiprocessing.cpu_count() * 2)
    video_id_title_and_transcript = []

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
    """Extracts video ID and explanation from a string using regex.

    Expects the string to contain '"video_id": "..."' and
    '"explanation": "..."' patterns, likely from a Gemini response.

    Args:
        json_str (str): The raw string potentially containing the video ID
                      and explanation.
        on_fail (Callable | None, optional): A function to call if parsing fails
                                               (i.e., if video_id or explanation
                                               cannot be extracted). Defaults to None.

    Returns:
        dict[str, str] | None: A dictionary with keys "video_id" and "explanation"
    """

    def extract_field(fieldname: str, text: str) -> str | None:
        """Extracts a double-quoted string value associated with a fieldname key.

        Uses regex to find patterns like '"fieldname": "value"'. Handles escaped
        quotes within the value.

        Args:
            fieldname (str): The key name (e.g., "video_id", "explanation") to search for.
                             Assumed to be enclosed in double quotes in the pattern.
            text (str): The text string to search within.

        Returns:
            str | None: The extracted string value (unescaped) if found, otherwise None.
        """
        pattern = (
            rf"(?:'{fieldname}'|\"{fieldname}\")\s*:\s*(?P<quote>['\"])(.*?)(?P=quote)"
        )
        match = re.search(pattern, text, re.DOTALL)
        return match.group(2).strip() if match else None

    video_id = extract_field("video_id", json_str)
    explanation = extract_field("explanation", json_str)

    if video_id and explanation:
        return {"video_id": video_id, "Begründung": explanation}
    else:
        if on_fail:
            on_fail()
        return None


def check_for_clickbait(transcript: str, title: str) -> str:
    """Analyzes a video transcript and title for clickbait elements using Gemini.

    Args:
        transcript (str): The transcript text of the YouTube video. Can be empty.
        title (str): The title of the YouTube video.

    Returns:
        str: The analysis result from Gemini. Returns "no response" if Gemini
             fails to provide text, or "no transcript" if the input transcript
             is empty or None. Returns the analysis string otherwise.
    """
    try:
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
    except Exception as e:
        return f"Fehler beim Erzeugen der Clickbait-Einordnung: {e}"


def live_conversation() -> str:
    """Starts a simple interactive command-line conversation with the Gemini model.

    For testing purposes only. Prints prompts and responses to the console.

    Returns:
        str: The last response text from the Gemini model.
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
    """Filters out a comma-separated String of subscribed channels based on user interests using Gemini.

    Takes a string representation of subscriptions and interests, asks Gemini
    to select a specified number of channels matching the interests.

    Args:
        subscriptions (str): A string containing subscribed channels, potentially
                             with descriptions (e.g., "channel1:desc1,channel2:desc2").
        interests (str): A string describing the user's interests.
        number_of_channels (int): The desired number of channel names to return.

    Returns:
        str | None: A comma-separated string of selected channel names,
                       or None if the API call fails or returns no text.
    """
    try:
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
    except Exception as e:
        return f"Fehler beim Erzeugen der Empfehlung: {e}"


if __name__ == "__main__":
    pass
