import pandas as pd
from googleapiclient.discovery import build
import youtube_api_key_management as yt_key_management
import re

youtube = yt_key_management.create_api_client()

def parse_duration(duration):
    pattern = re.compile(r'PT(\d+M)?(\d+S)?')
    match = pattern.match(duration)
    
    minutes = 0
    seconds = 0
    
    if match:
        if match.group(1):
            minutes = int(match.group(1)[:-1])
        if match.group(2):
            seconds = int(match.group(2)[:-1])
    
    return f'{minutes:02}:{seconds:02}'

def get_category_name(category_id):
    request = youtube.videoCategories().list(
        part="snippet",
        regionCode="DE"
    )
    
    response = request.execute()
    
    categories = {item['id']: item['snippet']['title'] for item in response['items']}
    
    return categories.get(category_id, 'Unbekannte Kategorie')

def get_trending_videos():
    request = youtube.videos().list(
        part="snippet,contentDetails",
        chart="mostPopular",
        regionCode="DE",
        maxResults=50
    )
    
    response = request.execute()

    video_data = []
    for index, item in enumerate(response['items'], start=1):
        title = item['snippet']['title']
        category_id = item['snippet']['categoryId']
        tags = item['snippet'].get('tags', [])
        video_duration = item['contentDetails']['duration']
        formatted_duration = parse_duration(video_duration)
        category_name = get_category_name(category_id)
        
        video_data.append({
            'Platz': index,
            'Titel': title,
            'Dauer': formatted_duration,
            'Tags': ', '.join(tags) if tags else 'Keine Tags',
            'Kategorie': category_name
        })
    
    df = pd.DataFrame(video_data)
    
    with pd.option_context('display.max_rows', None, 'display.max_columns', None):  
        print("Trending Videos:")
        print(df)
    return df

def get_trending_videos_stats(df):
    category_counts = df['Kategorie'].value_counts().reset_index()
    category_counts.columns = ['Kategorie', 'Anzahl']
    
    print("\nHäufigste Kategorien")
    print(category_counts)

if __name__ == '__main__':
    df = get_trending_videos()
    get_trending_videos_stats(df)
