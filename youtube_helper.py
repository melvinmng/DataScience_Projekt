import re
import isodate
import streamlit as st


def parse_duration(duration):
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


def get_video_length(youtube, video_id):
    request = youtube.videos().list(part="snippet,contentDetails", id=video_id)
    response = request.execute()
    if "items" not in response or len(response["items"]) == 0:
        print(f"Fehler: Kein Video gefunden für ID {video_id}")
        return 0  # Oder eine Default-Wert wie 0 zurückgeben

    duration = response["items"][0]["contentDetails"]["duration"]
    return parse_duration(duration)


# @st.cache_data
def get_video_data(
    youtube, response
):  # @AdriSieDS Was ist response?? Kann ich damit Zugriff auf den Titel eines bestimmten Videos bekommen?

    videos = []
    for index, item in enumerate(response["items"], start=1):
        video_id = item["id"]["videoId"]
        title = item["snippet"]["title"]
        tags = item["snippet"].get("tags", [])
        thumbnail = item["snippet"]["thumbnails"]["medium"]["url"]
        length = get_video_length(youtube, video_id)

        videos.append(
            {
                "place": index,
                "title": title,
                "tags": ", ".join(tags) if tags else "Keine Tags",
                "video_id": video_id,
                "thumbnail": thumbnail,
                "length": length,
            }
        )

    return videos


def extract_video_id_from_url(url: str) -> str | None:
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11})"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None
