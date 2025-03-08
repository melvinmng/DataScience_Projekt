from googleapiclient.discovery import build
import youtube_api_key_management as yt_key_management

youtube = yt_key_management.create_api_client()

def get_trending_videos():
    request = youtube.videos().list(
        part="snippet",
        chart="mostPopular",
        regionCode="DE",
        maxResults=50
    )
    
    response = request.execute()
    
    for index, item in enumerate(response['items'], start=1):
        title = item['snippet']['title']
        print(f"Platz {index}:\t{title}")

if __name__ == '__main__':
    get_trending_videos()
