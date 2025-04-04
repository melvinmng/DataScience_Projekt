from youtube_transcript_api import YouTubeTranscriptApi


def get_transcript(video_id: str, required_languages: list[str] = ["de", "en"]) -> str:
    """
    Gets the transcript of a YouTube video in the specified languages.

    Args:
        video_id (str): YouTube video ID
        required_languages (list): list of Language codes. Defaults to ["en", "de"].

    Returns:
        str: video transcript as a single string
    """
    try:

        transcript = YouTubeTranscriptApi.get_transcript(
            video_id, languages=required_languages
        )
        transcript_text = " ".join([entry["text"] for entry in transcript])
        return transcript_text
    except:
        print(f"Video {video_id} hat kein Transkript und wird ignoriert")
        return ""
