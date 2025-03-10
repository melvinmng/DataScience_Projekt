from googleapiclient.discovery import build
import googleapiclient.discovery
import pandas as pd

def get_subscriptions(channel_Id: str, API_KEY: str) -> pd.DataFrame:
    """
    Retrieves all YouTube channel subscriptions for a given channel ID.

    Args:
        channel_Id (str): The YouTube channel ID.
        API_KEY (str): The API key for authentication.

    Returns:
        pd.DataFrame: A DataFrame containing subscription details.
    """
    
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=API_KEY)

    subscriptions = []
    next_page_token = None

    while True:
        request = youtube.subscriptions().list(
            part = "snippet,contentDetails",
            channelId= channel_Id,
            maxResults=50,  # Maximum pro Anfrage
            pageToken=next_page_token
        )
        response = request.execute()

        #
        subscriptions.extend(response["items"])

        # Prüfen, ob es noch mehr Seiten gibt
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break  # Keine weiteren Seiten → Beende die Schleife

    channels = []
    for item in subscriptions:
        snippet = item["snippet"]
        content_details = item["contentDetails"]

        channels.append({
            "channel_name": snippet["title"],
            "channel_id": snippet["resourceId"]["channelId"],
            "published_at": snippet["publishedAt"],
            "description": snippet["description"],
            "subscription_id": item["id"],
            "total_videos": content_details["totalItemCount"],
            "new_videos": content_details["newItemCount"],
            "thumbnail_url": snippet["thumbnails"]["default"]["url"]
        })

    # DataFrame erstellen
    subs = pd.DataFrame(channels)

    return subs

