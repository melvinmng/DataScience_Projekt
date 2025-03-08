from googleapiclient.discovery import build
import json

with open("youtube_api_config.json") as f:
    config = json.load(f)
youtube_api_key = config["api_key"]

youtube = build('youtube', 'v3', developerKey=youtube_api_key)

def get_video_info(video_id):
    # Abrufen der Video-Details
    request = youtube.videos().list(
        part="snippet", 
        id=video_id      
    )
    response = request.execute()

    if 'items' in response and len(response['items']) > 0:
        video_data = response['items'][0]['snippet']
        
        title = video_data['title']  # Titel des Videos
        creator = video_data['channelTitle']  # Kanalname des Erstellers
        publish_date = video_data['publishedAt']  # Veröffentlichungsdatum
        
        return {
            'Title': title,
            'Creator': creator,
            'Publish Date': publish_date
        }
    else:
        return None
