from youtube_transcript_api import YouTubeTranscriptApi


def get_transcript(video_id, required_languages):
    """
    """ 
    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages = required_languages)
    # Ausgabe in lesbarer Form
    transcript_text = " ".join([entry["text"] for entry in transcript])

    return transcript_text
    


