import pandas as pd
import re
from .key_management.api_key_management import get_api_key, create_youtube_client


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


def get_category_name(youtube, category_id):
    request = youtube.videoCategories().list(part="snippet", regionCode="DE")

    response = request.execute()

    categories = {item["id"]: item["snippet"]["title"] for item in response["items"]}

    return categories.get(category_id, "Unbekannte Kategorie")


def get_trending_videos(youtube):
    request = youtube.videos().list(
        part="snippet,contentDetails",
        chart="mostPopular",
        regionCode="DE",
        maxResults=50,
    )

    response = request.execute()

    video_data = []
    for index, item in enumerate(response["items"], start=1):
        title = item["snippet"]["title"]
        category_id = item["snippet"]["categoryId"]
        tags = item["snippet"].get("tags", [])
        video_duration = item["contentDetails"]["duration"]
        formatted_duration = parse_duration(video_duration)
        category_name = get_category_name(youtube, category_id)
        video_id = item["id"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        video_data.append(
            {
                "Platz": index,
                "Titel": title,
                "Dauer": formatted_duration,
                "Tags": ", ".join(tags) if tags else "Keine Tags",
                "Kategorie": category_name,
                "Video_URL": video_url,
                "Video-ID": video_id
            }
        )

    df = pd.DataFrame(video_data)

    with pd.option_context("display.max_rows", None, "display.max_columns", None):
        print("\nTrending Videos:")
        print(df)
    return df


def get_trending_videos_stats(df):
    category_counts = df["Kategorie"].value_counts().reset_index()
    category_counts.columns = ["Kategorie", "Anzahl"]

    print("\nHäufigste Kategorien:")
    print(category_counts)


if __name__ == "__main__":
    try:
        # Ändere die API-Key-Ladung, um die neuen Funktionen zu verwenden
        api_key = get_api_key("YOUTUBE_API_KEY")  # API-Schlüssel aus den Umgebungsvariablen laden
        youtube = create_youtube_client(api_key)  # YouTube API-Client erstellen

        df = get_trending_videos(youtube)  # Trending Videos abrufen
        get_trending_videos_stats(df)  # Statistik der Kategorien anzeigen

    except ValueError as e:
        print(f"Fehler: {e}")

    except Exception as e:
        print(f"Ein unerwarteter Fehler ist aufgetreten: {e}")
