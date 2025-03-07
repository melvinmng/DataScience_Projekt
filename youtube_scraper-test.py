import ytapi as yt
from youtube_transcript_api import YouTubeTranscriptApi


video_id = "sGE4i_v5JrQ"  # Beispiel-Video-ID


transcript = YouTubeTranscriptApi.get_transcript(video_id, languages =['de','en'])
#print(transcript)
# Ausgabe in lesbarer Form
transcript_text = " ".join([entry["text"] for entry in transcript])
#print(transcript_text)


info = yt.get_video_info(video_id)
#AIzaSyD9zfzJajkNxGSG0pFHrGZ1jwQN2F9NQC8

from google import genai

client = genai.Client(api_key="AIzaSyD9zfzJajkNxGSG0pFHrGZ1jwQN2F9NQC8")
response = client.models.generate_content(
    model="gemini-2.0-flash", contents=f"Kannst du mir das Video von '{info['Creator']}' mit dem Titel '{info['Title']}' welches am {info['Publish Date']} erschienen ist knapp und przise in 2-3 Stzen zusammenfassen? Das ist der zugehörige Transskript:'{transcript_text}'"
)
print(response.text)


