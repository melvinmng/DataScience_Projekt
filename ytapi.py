from googleapiclient.discovery import build

# Dein API-Schlüssel hier einfügen
API_KEY = 'AIzaSyB7DvFs_Yqq9GpFM2hUyEvWfgYv7jJ20xs'

youtube = build('youtube', 'v3', developerKey=API_KEY)

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
