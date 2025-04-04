import re
from googleapiclient.discovery import build, Resource
import pandas as pd
from datetime import datetime
import streamlit as st
import feedparser
import yt_dlp
from streamlit.runtime.scriptrunner import get_script_run_ctx
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import os
from typing import Any
import concurrent.futures
from youtube_transcript_api import YouTubeTranscriptApi


def get_transcript(video_id: str, required_languages: list[str] = ["de", "en"]) -> str:
    """
    Gets the transcript of a YouTube video in the specified languages.

    Args:
        video_id (str): YouTube video ID
        required_languages (list): list of Language codes. Defaults to ["en", "de"].

    Returns:
        str: video transcript as a single string
    """
    try:

        transcript = YouTubeTranscriptApi.get_transcript(
            video_id, languages=required_languages
        )
        transcript_text = " ".join([entry["text"] for entry in transcript])
        return transcript_text
    except:
        print(f"Video {video_id} hat kein Transkript und wird ignoriert")
        return ""


def parse_duration(duration: str) -> str:
    """
    Wandelt eine YouTube-Videodauer (ISO 8601 Format) in ein lesbares Format (MM:SS) um.

    Args:
        duration (str): Die ISO 8601-Dauerzeichenkette (z. B. "PT5M10S").

    Returns:
        str: Die formatierte Dauer im Format "MM:SS".

    Falls keine Minuten oder Sekunden angegeben sind, wird "00:00" zurückgegeben.
    """
    pattern = re.compile(r"PT(\d+M)?(\d+S)?")
    match = pattern.match(duration)

    minutes = 0
    seconds = 0

    if match:
        if match.group(1):
            minutes = int(match.group(1)[:-1])
        if match.group(2):
            seconds = int(match.group(2)[:-1])

    return f"{minutes:02}:{seconds:02}"


def get_video_length(youtube: Resource, video_id: str) -> str:
    """
    Ruft die Dauer eines YouTube-Videos ab.

    Args:
        youtube (object): Der YouTube API-Client.
        video_id (str): Die ID des YouTube-Videos.

    Returns:
        str: Die formatierte Videodauer im Format "MM:SS".

    Falls das Video nicht gefunden wird oder ein Fehler auftritt, wird "00:00" zurückgegeben.
    """
    request = youtube.videos().list(part="snippet,contentDetails", id=video_id)
    response = request.execute()
    if "items" not in response or len(response["items"]) == 0:
        print(f"Fehler: Kein Video gefunden für ID {video_id}")
        return "00:00"  # Oder eine Default-Wert wie 00:00 zurückgeben

    duration = response["items"][0]["contentDetails"]["duration"]
    return parse_duration(duration)


def get_video_length_dlp(video_id: str) -> str:
    """
    Holt die Dauer eines YouTube-Videos ohne API, basierend auf der Video-ID.

    Args:
        video_id (str): Die YouTube-Video-ID.

    Returns:
        str: Die Videodauer im Format "MM:SS".
    """
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "force_generic_extractor": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            duration = info.get("duration")  # Dauer in Sekunden

            if duration:
                return f"{duration // 60:02}:{duration % 60:02}"
            else:
                return "00:00"  # Falls keine Dauer gefunden wurde
    except Exception as e:
        print(f"Fehler beim Abrufen der Videolänge für {video_id}: {e}")
        return "00:00"


def get_video_data_dlp(video_id: str) -> dict[str, Any]:
    """
    Ruft Metadaten zu einem YouTube-Video mit yt-dlp ab.

    Args:
        video_id (str): Die ID des YouTube-Videos.

    Returns:
        dict[str, Any]: Ein Dictionary mit folgenden Video-Informationen:
            - video_id (str): Die ID des Videos.
            - title (str): Der Titel des Videos.
            - tags (str): Eine durch Komma getrennte Liste von Tags oder "Keine Tags".
            - thumbnail (str): Die URL des Thumbnails oder "Keine Thumbnail-URL".
            - length (str): Die Videolänge im Format MM:SS.
            - upload_date (datetime | None): Das Upload-Datum oder None, falls unbekannt.
            - channel_name (str): Der Name des Kanals oder "Unbekannter Kanal".
            - views (int): Die Anzahl der Aufrufe.

    Falls ein Fehler auftritt, wird ein leeres Dictionary zurückgegeben.
    """
    ydl_opts = {"quiet": True, "noplaylist": True, "no_warnings": True}

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(
                f"https://www.youtube.com/watch?v={video_id}", download=False
            )
            length_str = (
                f"{info.get('duration', 0) // 60:02}:{info.get('duration', 0) % 60:02}"
            )
            upload_date = info.get("upload_date", "")
            formatted_date = (
                datetime.strptime(upload_date, "%Y%m%d") if upload_date else None
            )

            video_dict = {
                "video_id": video_id,
                "title": info.get("title", "Unbekannter Titel"),
                "tags": (
                    ", ".join(info.get("tags", []))
                    if info.get("tags")
                    else "Keine Tags"
                ),
                "thumbnail": info.get("thumbnail", "Keine Thumbnail-URL"),
                "length": length_str,
                "upload_date": formatted_date,
                "channel_name": info.get("uploader", "Unbekannter Kanal"),
                "views": info.get("view_count", 0),
            }
        except Exception:
            print("Fehler beim Abrufen der Video-Metadaten")

    return video_dict


def get_video_data(
    youtube: Resource, response: dict[str, Any], mode: str | None = None
) -> list[dict[str, Any]]:
    """
    Extrahiert Videodaten aus einer YouTube API-Antwort und zieht zusätzlich die Views mit yt-dlp.

    Args:
        youtube (Resource): Der YouTube API-Client.
        response (dict[str, Any]): Die Antwort einer YouTube API-Suchanfrage.
        mode (str | None): Bestimmt das Parsing-Verhalten (z. B. "trends" für Trend-Videos).

    Returns:
        list[dict[str, Any]]: Eine Liste mit Video-Metadaten, inkl.:
            - place (int): Position des Videos in der Ergebnisliste.
            - title (str): Titel des Videos.
            - tags (str): Komma-separierte Liste von Tags oder "Keine Tags".
            - video_id (str): Die eindeutige ID des Videos.
            - thumbnail (str): URL des Thumbnails oder ein leerer String, falls nicht verfügbar.
            - length (str): Länge des Videos oder "Unknown", falls nicht abrufbar.
            - channel_name (str): Name des Kanals oder "Unknown Channel".
            - views (Union[str, int]): Anzahl der Aufrufe oder "Unknown", falls nicht abrufbar.
            - upload_date (str | None): Das Upload-Datum im Format "YYYY-MM-DD" oder "Unknown", falls nicht verfügbar.

    Falls ein unerwartetes API-Response-Format erkannt wird, wird eine alternative Verarbeitung versucht.
    """

    def get_views_with_youtube_api(youtube: Resource, video_id: str) -> str:
        """
        Verwendet die YouTube API, um die Views eines Videos zu extrahieren.
        """
        try:
            # Anfrage an die YouTube API, um Video-Daten abzurufen
            request = youtube.videos().list(
                part="statistics", id=video_id  # Nur Statistiken (einschließlich Views)
            )
            response = request.execute()

            # Die Anzahl der Aufrufe aus der Antwort extrahieren
            view_count = response["items"][0]["statistics"].get("viewCount", "Unknown")
            return view_count
        except Exception as e:
            print(
                f"Fehler beim Abrufen der Views für Video {video_id} mit der YouTube API: {e}"
            )
            return "Unknown"

    videos = []

    for index, item in enumerate(response.get("items", []), start=1):
        try:
            if mode == "trends":
                video_id = item["id"]
            else:
                video_id = item["id"]["videoId"]
            title = item["snippet"]["title"]
            channel_name = item["snippet"]["channelTitle"]
            tags = item["snippet"].get("tags", [])
            thumbnail = item["snippet"]["thumbnails"]["medium"]["url"]
            length = get_video_length(youtube, video_id)
            views = get_views_with_youtube_api(
                youtube, video_id
            )  # Hole die Views mit yt_dlp
            upload_date = item["snippet"].get(
                "publishedAt", "Unknown"
            )  # Das Upload-Datum wird hier extrahiert

        except KeyError:
            # Alternative Methode zur Verarbeitung
            print(
                f"Warnung: Unerwartete API-Struktur für Item {index}, alternative Verarbeitung wird versucht."
            )
            try:
                video_id = item.get("id", {}).get("videoId", "Unknown")
                title = item.get("snippet", {}).get("title", "Unknown Title")
                channel_name = item.get("snippet", {}).get(
                    "channelTitle", "Unknown Channel"
                )
                tags = item.get("snippet", {}).get("tags", [])
                thumbnail = (
                    item.get("snippet", {})
                    .get("thumbnails", {})
                    .get("medium", {})
                    .get("url", "")
                )
                length = "Unknown"
                views = get_views_with_youtube_api(youtube, video_id)
                upload_date = item.get("snippet", {}).get("publishedAt", "Unknown")
            except Exception as e:
                print(f"Fehler beim Verarbeiten des Items {index}: {e}")
                continue  # Falls auch die alternative Methode fehlschlägt, überspringe das Item

        videos.append(
            {
                "place": index,
                "title": title,
                "tags": ", ".join(tags) if tags else "Keine Tags",
                "video_id": video_id,
                "thumbnail": thumbnail,
                "length": length,
                "channel_name": channel_name,
                "views": views,
                "upload_date": upload_date,
            }
        )

        # Entfernen der leeren Dictionaries
        videos = [d for d in videos if d]  # Ein leeres Dictionary ist falsy in Python

    # Sortieren nach Upload-Datum (neueste zuerst)
    return sorted(videos, key=lambda v: v["upload_date"] or datetime.min, reverse=True)


@st.cache_data(ttl=3600)
def search_videos_dlp(query: str, max_results: int = 100) -> list[dict[str, Any]]:
    """
    Führt eine YouTube-Suche mit yt-dlp durch und gibt eine Liste von Video-Metadaten zurück.

    Args:
        query (str): Der Suchbegriff.
        max_results (int, optional): Maximale Anzahl der Ergebnisse (max. 1000). Standard: 100.

    Returns:
        list[dict[str, Any]]: Eine liste mit Video-Metadaten, inkl.:
            - place (int): Position in der Ergebnisliste.
            - title (str): Videotitel.
            - video_id (str | None): Die Video-ID oder None.
            - thumbnail (str | None): URL des Thumbnails oder None.
            - channel_name (str): Name des Kanals oder "Unbekannter Kanal".
            - length (str): Videolänge im Format MM:SS.
            - tags (str): Komma-separierte Tags oder "Keine Tags".
            - upload_date (datetime | None): Upload-Datum als `datetime`-Objekt oder None.
            - views (int): Anzahl der Aufrufe.
    """
    max_results = min(max_results, 1000)  # Begrenze auf max. 1000
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "default_search": "ytsearch",
        "noplaylist": True,
        "extract_flat": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        search_results = ydl.extract_info(
            f"ytsearch{max_results}:{query}", download=False
        )

    videos = []
    if "entries" in search_results:
        for index, entry in enumerate(search_results["entries"], start=1):
            upload_date = entry.get("upload_date", "")
            formatted_date = (
                datetime.strptime(upload_date, "%Y%m%d") if upload_date else None
            )
            view_count = entry.get("view_count", 0)  # 👈 Views hinzufügen

            videos.append(
                {
                    "place": index,
                    "title": entry.get("title", "Unbekannter Titel"),
                    "video_id": entry.get("id"),
                    "thumbnail": entry.get("thumbnail"),
                    "channel_name": entry.get("uploader", "Unbekannter Kanal"),
                    "length": f"{int(entry.get('duration', 0)) // 60:02}:{int(entry.get('duration', 0)) % 60:02}",
                    "tags": (
                        ", ".join(entry.get("tags", []))
                        if entry.get("tags")
                        else "Keine Tags"
                    ),
                    "upload_date": formatted_date,
                    "views": view_count,  # ✅ Views integriert!
                }
            )

    # Entfernen der leeren Dictionaries
    videos = [d for d in videos if d]  # Ein leeres Dictionary ist falsy in Python
    return sorted(videos, key=lambda v: v["upload_date"] or datetime.min, reverse=True)


def get_category_name(youtube: Resource, category_id: str) -> str:
    """
    Get the name of a YouTube video category by its ID.

    Args:
        youtube (object): The YouTube API client.
        category_id (str): The category ID.

    Returns:
        str: The category name or "Unbekannte Kategorie" if not found.
    """
    request = youtube.videoCategories().list(part="snippet", regionCode="DE")

    response = request.execute()

    categories = {item["id"]: item["snippet"]["title"] for item in response["items"]}

    return categories.get(category_id, "Unbekannte Kategorie")


def get_subscriptions(
    channel_Id: str,
    youtube: Resource,
    csv_filename="subscriptions.csv",
    gitignore_path=".gitignore",
) -> pd.DataFrame:
    """
    Holt YouTube-Abonnements für eine gegebene Kanal-ID.
    Falls die CSV-Datei existiert, werden die Daten aus der Datei gelesen.
    Falls nicht, werden die Daten von der API abgerufen und gespeichert.

    Args:
        channel_Id (str): Die YouTube-Kanal-ID.
        youtube (object): YouTube API Client.
        csv_filename (str): Name der CSV-Datei zum Speichern.
        gitignore_path (str): Pfad zur .gitignore-Datei.

    Returns:
        pd.DataFrame: Ein DataFrame mit den Abonnementdetails.
    """
    # Falls CSV existiert, lese Daten daraus und returne
    if os.path.isfile(csv_filename):
        return pd.read_csv(csv_filename)

    subscriptions = []
    next_page_token = None

    while True:
        try:
            request = youtube.subscriptions().list(
                part="snippet,contentDetails",
                channelId=channel_Id,
                maxResults=50,
                pageToken=next_page_token,
            )
            response = request.execute()
        except Exception as e:
            st.write("API Tokens aufgebraucht oder Fehler aufgetreten:", str(e))
            return pd.DataFrame()  # Leeres DataFrame zurückgeben

        subscriptions.extend(response.get("items", []))
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    channels = []
    for item in subscriptions:
        snippet = item["snippet"]
        content_details = item["contentDetails"]

        channels.append(
            {
                "channel_name": snippet["title"],
                "channel_id": snippet["resourceId"]["channelId"],
                "published_at": snippet["publishedAt"],
                "description": snippet["description"],
                "subscription_id": item["id"],
                "total_videos": content_details["totalItemCount"],
                "new_videos": content_details["newItemCount"],
                "thumbnail_url": snippet["thumbnails"]["default"]["url"],
            }
        )

    # DataFrame erstellen
    subs = pd.DataFrame(channels)

    # Daten in CSV speichern
    subs.to_csv(csv_filename, index=False, encoding="utf-8")

    # Falls die .gitignore existiert, prüfen ob die CSV bereits eingetragen ist
    if os.path.isfile(gitignore_path):
        with open(gitignore_path, "r", encoding="utf-8") as gitignore_file:
            gitignore_content = gitignore_file.readlines()

        if csv_filename not in [line.strip() for line in gitignore_content]:
            with open(gitignore_path, "a", encoding="utf-8") as gitignore_file:
                gitignore_file.write(f"\n{csv_filename}\n")
    else:
        # Falls .gitignore nicht existiert, erstelle sie und füge die Datei hinzu
        with open(gitignore_path, "w", encoding="utf-8") as gitignore_file:
            gitignore_file.write(f"{csv_filename}\n")

    return subs


def get_recent_videos_from_subscriptions(
    youtube: Resource, channel_ids: list[str], number_of_videos: int
) -> list[dict[str, Any]]:
    """
    Ruft die neuesten Videos von einer Liste abonnierter YouTube-Kanäle über die YouTube API ab.

    Args:
        youtube (Resource): Der YouTube API-Client.
        channel_ids (list[str]): Eine Liste von YouTube-Kanal-IDs.
        number_of_videos (int): Anzahl der gewünschten neuesten Videos pro Kanal.

    Returns:
        list[dict[str, Any]]: Eine Liste mit Video-Metadaten, inkl.:
            - place (int): Position des Videos in der Ergebnisliste.
            - title (str): Titel des Videos.
            - tags (str): Komma-separierte Liste von Tags oder "Keine Tags".
            - video_id (str): Die eindeutige ID des Videos.
            - thumbnail (str): URL des Thumbnails oder ein leerer String, falls nicht verfügbar.
            - length (str): Länge des Videos oder "Unknown", falls nicht abrufbar.
            - channel_name (str): Name des Kanals oder "Unknown Channel".
            - views (Union[str, int]): Anzahl der Aufrufe oder "Unknown", falls nicht abrufbar.
    """
    videos = []
    # API-Anfragen minimieren: 1 Request pro Kanal
    for channel_id in channel_ids:
        try:
            request = youtube.search().list(
                part="id,snippet",
                channelId=channel_id,
                maxResults=number_of_videos,  # Maximal 10 neueste Videos abrufen
                order="date",  # Neueste zuerst
                type="video",  # Nur Videos (keine Streams oder Playlists)
            )
            response = request.execute()
            print()
            print(channel_id)
            print(f"------------------\n{response}--------------------\n")
            video_data = get_video_data(youtube, response)
            for video in video_data:
                videos.append(video)
        except Exception as e:
            st.warning(f"Fehler beim Abrufen der Videos für Kanal {channel_id}: {e}")

    return videos


@st.cache_data(ttl=3600)
def get_recent_videos_from_channels_RSS(
    channel_ids: list[str], max_videos: int = 1
) -> list[list[str]]:
    """
    Ruft die neuesten Videos von einer Liste von YouTube-Kanälen über deren RSS-Feeds ab.

    Args:
        channel_ids (list[str]): Eine Liste von YouTube-Kanal-IDs.
        max_videos (int, optional): Die maximale Anzahl an Videos pro Kanal (Standard: 1).

    Returns:
        list[list[str]]: Eine Liste von Listen, wobei jede innere Liste die Video-IDs eines Kanals enthält.

    Die Funktion nutzt Multithreading, um mehrere Feeds gleichzeitig zu verarbeiten.
    Falls ein Fehler auftritt, wird eine Warnung in Streamlit ausgegeben.
    """
    videos = []
    num_threads = min(len(channel_ids), multiprocessing.cpu_count() * 2)

    ctx = get_script_run_ctx()  # 🔥 Streamlit-Thread-Kontext sichern

    def fetch_videos(channel_id: str):
        """Holt die neuesten Videos für einen Kanal."""
        try:
            feed_url = (
                f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
            )
            feed = feedparser.parse(feed_url)
            video_urls = [entry.link for entry in feed.entries[:max_videos]]

            video_ids = []
            for video in video_urls:
                match = re.search(
                    r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)",
                    video,
                )
                if match:
                    video_ids.append(match.group(1))

            return list(set(video_ids))

        except Exception as e:
            # Einfach ohne 'with ctx:' arbeiten
            st.warning(f"Fehler beim Abrufen der Videos für Kanal {channel_id}: {e}")
            return []

    video_id_lists = []
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        future_to_channel = {
            executor.submit(fetch_videos, channel): channel for channel in channel_ids
        }
        for future in future_to_channel:
            video_id_lists.append(future.result())

    video_ids = [video_id for sublist in video_id_lists for video_id in sublist]

    def fetch_video_data(video_id: str):
        """Holt die Metadaten eines Videos."""
        try:
            return get_video_data_dlp(video_id)
        except Exception as e:
            st.warning(f"Fehler beim Abrufen der Metadaten für Video {video_id}: {e}")
            return {}

    video_data_list = []
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        future_to_video = {
            executor.submit(fetch_video_data, video_id): video_id
            for video_id in video_ids
        }
        for future in future_to_video:
            video_data_list.append(future.result())

    # Entfernen der leeren Dictionaries
    video_data_list = [
        d for d in video_data_list if d
    ]  # Ein leeres Dictionary ist falsy in Python
    videos = sorted(
        video_data_list, key=lambda v: v.get("upload_date", datetime.min), reverse=True
    )

    return videos


def extract_video_id_from_url(url: str) -> str | None:
    """
    Extrahiert die Video-ID aus einer YouTube-URL.

    Args:
        url (str): Die YouTube-Video-URL.

    Returns:
        str oder None: Die extrahierte Video-ID oder None, falls keine ID gefunden wurde.
    """
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11})"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None


def create_youtube_client(api_key: str) -> object:
    api_service_name = "youtube"
    api_version = "v3"
    return build(api_service_name, api_version, developerKey=api_key)


def get_trending_videos(youtube: Resource, region_code: str) -> pd.DataFrame:
    """
    Ruft die aktuellen Trending-Videos von YouTube ab und formatiert die Daten als DataFrame.

    Args:
        youtube (object): Der authentifizierte YouTube API-Client.
        region_code (str): Der Ländercode für den die Trending-Videos abgerufen werden sollen.

    Returns:
        list[dict[str, Any]]: Eine Liste mit Video-Metadaten, inkl.:
            - place (int): Position des Videos in der Ergebnisliste.
            - title (str): Titel des Videos.
            - tags (str): Komma-separierte Liste von Tags oder "Keine Tags".
            - video_id (str): Die eindeutige ID des Videos.
            - thumbnail (str): URL des Thumbnails oder ein leerer String, falls nicht verfügbar.
            - length (str): Länge des Videos oder "Unknown", falls nicht abrufbar.
            - channel_name (str): Name des Kanals oder "Unknown Channel".
            - views (Union[str, int]): Anzahl der Aufrufe oder "Unknown", falls nicht abrufbar.
            - upload_date

    Die Funktion ruft bis zu 50 der beliebtesten Videos aus der angegebenen Region ab.
    """
    request = youtube.videos().list(
        part="snippet,contentDetails",
        chart="mostPopular",
        regionCode=region_code,
        maxResults=50,
    )

    response = request.execute()

    return get_video_data(youtube, response, "trends")


def get_trending_videos_dlp(
    region_code: str = "DE", max_results: int = 50
) -> list[dict[str, Any]]:
    """
    Ruft die aktuell angesagten (Trending) Videos von YouTube mit yt-dlp ab.

    Args:
        region_code (str, optional): Der Ländercode (ISO 3166-1 Alpha-2), für den die Trending-Videos abgerufen werden sollen. Standard ist "DE" (Deutschland).
        max_results (int, optional): Die maximale Anzahl an Trending-Videos, die zurückgegeben werden sollen. Standard ist 50.

    Returns:
        list[dict[str, Any]]: Eine Liste von Dictionaries mit Metadaten der Trending-Videos, darunter:
            - video_id (str): Die ID des Videos.
            - title (str): Der Titel des Videos.
            - tags (str): Eine durch Komma getrennte Liste von Tags oder "Keine Tags".
            - thumbnail (str): Die URL des Thumbnails oder "Keine Thumbnail-URL".
            - length (str): Die Videolänge im Format MM:SS.
            - upload_date (datetime | None): Das Upload-Datum oder None, falls unbekannt.
            - channel_name (str): Der Name des Kanals oder "Unbekannter Kanal".
            - views (int): Die Anzahl der Aufrufe.

    Die Funktion nutzt yt-dlp, um die Trending-Videos ohne API abzurufen. Anschließend werden die Videodaten mit `get_video_data_dlp` in parallelen Threads extrahiert.

    Falls keine Trending-Videos gefunden werden, wird eine leere Liste zurückgegeben.
    """
    url = f"https://www.youtube.com/feed/trending?gl={region_code}"

    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "force_generic_extractor": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)

    trending_video_ids = [
        entry.get("id") for entry in info_dict.get("entries", []) if entry.get("id")
    ][:max_results]

    if not trending_video_ids:
        print("Keine Trend-Videos gefunden.")
        return []

    videos = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_video_id = {
            executor.submit(get_video_data_dlp, video_id): video_id
            for video_id in trending_video_ids
        }

        for future in concurrent.futures.as_completed(future_to_video_id):
            try:
                videos.append(future.result())
            except Exception as e:
                print(f"Fehler beim Abrufen von Videodaten: {e}")

    return videos
