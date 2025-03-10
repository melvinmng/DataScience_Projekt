from youtube_transcript_api import YouTubeTranscriptApi


def get_transcript(video_id: str, required_languages: list[str]) -> str:
    """
    Fetches the transcript of a YouTube video in the specified languages.

    Args:
        video_id (str): YouTube video ID.
        required_languages (list): Language codes (e.g., ["en", "de"]).

    Returns:
        str: The transcript as a single string.
    """
    transcript = YouTubeTranscriptApi.get_transcript(
        video_id, languages=required_languages
    )
    # Ausgabe in lesbarer Form
    transcript_text = " ".join([entry["text"] for entry in transcript])

    return transcript_text
