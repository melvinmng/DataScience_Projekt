from typing import Optional
from settings import ai_client, ai_model, ai_generate_content_config, interests

# from ... import transcript, creator


def get_summary(transcript: str) -> str:
    """_summary_

    Args:
        transcript (str): _description_

    Returns:
        str: _description_
    """
    response = ai_client.models.generate_content(
        model=ai_model,
        config=ai_generate_content_config,
        contents=f"Fasse mir dieses Video zusammen: {transcript}",
    )

    return response.text


def get_summary_without_spoiler(transcript: str) -> str:
    """_summary_

    Args:
        transcript (str): _description_

    Returns:
        str: _description_
    """
    response = ai_client.models.generate_content(
        model=ai_model,
        config=ai_generate_content_config,
        contents=f"Fasse mir dieses Video zusammen: {transcript}. Achte dabei darauf, keinen Inhalt zu spoilern",
    )

    return response.text


def get_recommendation(interests: Optional[str] = interests) -> str:
    pass


def check_for_clickbait():
    pass


"""
if __name__ == "__main__":
    print("Starte Konversation")
    question = input("Was kann ich für dich tun?")
    response = ai_client.models.generate_content(
        model=ai_model, config=ai_generate_content_config, contents=question
    )
    print(response.text)
"""
