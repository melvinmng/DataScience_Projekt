import re
import isodate
from typing import List, Dict


def parse_duration(duration: str) -> str:
    """
    Parse a YouTube video duration string into a human-readable format (MM:SS).

    Args:
        duration (str): The ISO 8601 duration string (e.g., "PT5M10S").

    Returns:
        str: The formatted duration in the format "MM:SS".
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


def get_video_length(youtube: object, video_id: str) -> str:
    """
    Get the duration of a YouTube video.

    Args:
        youtube (object): The YouTube API client.
        video_id (str): The YouTube video ID.

    Returns:
        str: The formatted video duration in the format "MM:SS".
    """
    request = youtube.videos().list(
        part="snippet,contentDetails",
        id=video_id
    )
    response = request.execute()
    if "items" not in response or len(response["items"]) == 0:
        print(f"Fehler: Kein Video gefunden für ID {video_id}")
        return "00:00"  # Oder eine Default-Wert wie 00:00 zurückgeben

    duration = response["items"][0]["contentDetails"]["duration"]
    return parse_duration(duration)
    

def get_video_data(youtube: object, response: Dict) -> List[Dict[str, str]]:
    """
    Extract video data from a YouTube API response.

    Args:
        youtube (object): The YouTube API client.
        response (dict): The response from a YouTube API search query.

    Returns:
        list: A list of dictionaries containing video metadata such as title, tags, video ID, etc.
    """
    videos = []
    for index, item in enumerate(response["items"], start=1):
        video_id = item["id"]["videoId"]
        title = item["snippet"]["title"]
        tags = item["snippet"].get("tags", [])
        thumbnail = item["snippet"]["thumbnails"]["medium"]["url"]
        length = get_video_length(youtube, video_id)

        videos.append(
            {
                "place": str(index),
                "title": title,
                "tags": ", ".join(tags) if tags else "Keine Tags",
                "video_id": video_id,  
                "thumbnail": thumbnail,
                "length": length
            }
        )
    
    return videos


def get_category_name(youtube: object, category_id: str) -> str:
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
