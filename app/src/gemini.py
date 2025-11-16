import os

from google import genai
from dotenv import load_dotenv
from savestates import *
import json


"""
Gemini AI interaction module for generating court cases,
events, and rulings used by the Court engine.
"""

load_dotenv(".env")
MODEL = 'gemini-2.0-flash-lite'

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def generate_case(query: str = None) -> dict:
    """
    Generate initial court case information using Gemini AI.

    Returns:
        dict: A dictionary containing:
            - case_title
            - description
            - judge_name
            - prosecution_name
            - defense_name
            - player_side ("PROSECUTION" or "DEFENSE")
            - witnesses (list of witness names)
    """

    query = (
        "Generate a simulated court case in JSON format exactly like this:\n"
        "{\n"
        '  "case_title": "<string>",\n'
        '  "description": "<string>",\n'
        '  "judge_name": "<string>",\n'
        '  "prosecution_name": "<string>",\n'
        '  "defense_name": "<string>",\n'
        '  "player_side": "<PROSECUTION or DEFENSE>",\n'
        '  "witnesses": ["<string>", "<string>", ...]\n'
        "}\n\n"
        "Ensure the JSON is valid and parsable. Provide names for judge, prosecution, defense, "
        "and at least 1-3 witness names. Make it a realistic but fictional court case."
    )

    prompt = [
        # {
        #     "file_data": {
        #         "file_uri": "https://generativelanguage.googleapis.com/v1beta/files/0dihmu62o5ah",
        #         "mime_type": "application/pdf"
        #     }
        # },
        {
            "text": query
        }
    ]

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )

    case_data = json.loads(str(response.text)[7:-3])

    expected_keys = [
        "case_title",
        "description",
        "judge_name",
        "prosecution_name",
        "defense_name",
        "player_side",
        "witnesses"
    ]
    for key in expected_keys:
        if key not in case_data:
            raise ValueError(f"Gemini did not return expected key: {key}")

    return case_data


def generate_event(court_obj, extra_prompt: str = "") -> dict:
    """
    Generate a new court event for the given Court instance.

    Args:
        court_obj: The Court object whose state drives event generation.
        extra_prompt (str): Optional additional instructions for Gemini.

    Returns:
        dict: A dictionary containing:
            - type (OPENING, CLOSING, RULING, STATEMENT, GENERAL)
            - content (string)
            - speaker (non-player side)
    """

    context = {
        "case_title": court_obj.case_title,
        "description": court_obj.description,
        "judge_name": court_obj.judge,
        "prosecution_name": court_obj.prosecution_name,
        "defense_name": court_obj.defense_name,
        "player_side": court_obj.playerSide.name,
        "witnesses": list(court_obj.witnesses.keys()),
        "timeline": [e.to_dict() for e in court_obj.timeline]
    }

    query = (
        f"You are generating the next court event for the following case:\n"
        f"{json.dumps(context, indent=2)}\n\n"
        f"{extra_prompt}\n"
        "Return a single JSON object with keys:\n"
        "  - type: one of OPENING, CLOSING, RULING, STATEMENT, GENERAL\n"
        "  - content: string containing the statement or action\n"
        f"  - speaker: a speaker or witness that is NOT {court_obj.playerSide.name}"
        "Do not include anything else, only a JSON object."
        "Do not include anything else, only a JSON object."
        "THE SPEAKER MUST NOT BE THE PLAYER'S SIDE. DO NOT MAKE AN OBJECTION HERE UNDER ANY CIRCUMSTANCES."
        "REMINDER: IF THE PLAYER IS PROSECUTION, THE SPEAKER MUST BE DEFENSE OR A WITNESS, AND VICE VERSA."
        "DO NOT REPEAT YOURSELF FOR NO REASON."
        "IF WHAT YOU ARE GENERATING IS AN OPENING, CLOSING, OR RULING, MAKE SURE TO LABEL IT AS SUCH."
    )

    prompt = [
        # {
        #     "file_data": {
        #         "file_uri": "https://generativelanguage.googleapis.com/v1beta/files/0dihmu62o5ah",
        #         "mime_type": "application/pdf"
        #     }
        # },
        {
            "text": query
        }
    ]

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )

    event_data = json.loads(str(response.text)[7:-3])

    if "type" not in event_data or "content" not in event_data:
        raise ValueError("Gemini did not return valid event JSON")

    if event_data["type"].upper() not in TimelineEventType.__members__:
        raise ValueError(f"Invalid event type from Gemini: {event_data['type']}")

    return event_data


def generate_ruling(court_obj, objection_type, extra_prompt: str = "") -> dict:
    """
    Generate a ruling for an objection within the court case.

    Args:
        court_obj: The Court instance.
        objection_type (str): The type of objection raised by the player.
        extra_prompt (str): Optional additional instructions.

    Returns:
        dict: A dictionary containing:
            - type: "RULING"
            - decision: "SUSTAINED" or "OVERRULED"
            - content: explanation of the ruling
    """

    context = {
        "case_title": court_obj.case_title,
        "description": court_obj.description,
        "judge_name": court_obj.judge,
        "prosecution_name": court_obj.prosecution_name,
        "defense_name": court_obj.defense_name,
        "player_side": court_obj.playerSide.name,
        "witnesses": list(court_obj.witnesses.keys()),
        "timeline": [e.to_dict() for e in court_obj.timeline]
    }

    query = (
        f"You are generating the next ruling for the following objection in this court case:\n"
        f"{json.dumps(context, indent=2)}\n\n"
        f"A ruling needs to be made for the following objection in the court case:\n"
        f"Objection by {court_obj.playerSide.name}: [{objection_type}]\n\n"
        "Provide the ruling as a JSON object with keys:\n"
        "  - type: RULING\n"
        "  - decision: either SUSTAINED or OVERRULED based on the objection. NOT ALL OBJECTIONS ARE MEANT TO BE SUSTAINED.\n"
        "  - content: string explaining the judge's ruling\n"
        "Return only the JSON object."
        "Also make sure that the ruling is accurate in relation to the objection provided, and the context of the case."
    )

    prompt = [
        # {
        #     "file_data": {
        #         "file_uri": "https://generativelanguage.googleapis.com/v1beta/files/0dihmu62o5ah",
        #         "mime_type": "application/pdf"
        #     }
        # },
        {
            "text": query
        }
    ]

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )

    event_data = json.loads(str(response.text)[7:-3])

    if "type" not in event_data or "content" not in event_data:
        raise ValueError("Gemini did not return valid event JSON")

    if event_data["type"].upper() not in TimelineEventType.__members__:
        raise ValueError(f"Invalid event type from Gemini: {event_data['type']}")

    return event_data


if __name__ == "__main__":
    print(generate_case())
