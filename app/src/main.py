from sqlite3 import IntegrityError
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, url_for, request, redirect, session
from markupsafe import escape

from savestates import *
from gemini import *
import os

# Load environment variables from the .env file located in the same working directory
load_dotenv(".env")

# Initialize Flask app
# - static files live in ../front
# - templates also live in ../front
app: Flask = Flask(
    __name__,
    static_folder="../front",
    static_url_path="/static",
    template_folder="../front/"
)
app.secret_key = "prettySecret"


@app.route("/")
def index():
    """
    Render the application's main page.
    """
    return render_template("index.html")


@app.route("/pick-side", methods=["POST"])
async def pickSide():
    """
    Set the player's chosen side for a specific case.

    Expected JSON payload:
        {
            "activeCase": <int>,
            "side": "prosecution" | "defense"
        }

    Returns:
        - success response with updated case metadata
        - error response if required fields are missing
    """
    data = request.get_json()
    if not data:
        return jsonify(response="error", message="Missing request data"), 400

    activeCase = int(data["activeCase"])
    court: Court = loadedCases[activeCase]

    court.playerSide = (
        Side.PROSECUTION if data["side"] == "prosecution" else Side.DEFENSE
    )

    return jsonify(response="success", case=court.to_dict()), 200


@app.route("/create_case", methods=["GET"])
async def createCase():
    """
    Create a new court case using AI-generated case information.

    Workflow:
        1. Request structured case data from Gemini.
        2. Construct a new Court instance.
        3. Register witnesses.
        4. Store the case in savestates.
        5. Return case metadata.

    Returns:
        JSON containing:
            - the case index (caseNum)
            - the full serialized case object
    """
    case_info = generate_case()

    # Build Court object from Gemini-generated fields
    court = Court(
        case_title=case_info["case_title"],
        description=case_info["description"],
        judge_name=case_info["judge_name"],
        prosecution_name=case_info["prosecution_name"],
        defendant_name=case_info["defense_name"],
        side=Side[case_info["player_side"].upper()]
    )

    loadedCases.append(court)
    activeCase = len(loadedCases) - 1

    # Register witnesses
    for w in case_info.get("witnesses", []):
        court.witnesses[w] = Witness(w)

    return jsonify(
        response="success",
        caseNum=activeCase,
        case=court.to_dict()
    ), 200


@app.route("/ai-event", methods=["POST"])
async def addEvent():
    """
    Add an AI-generated event (dialogue, testimony, etc.) to the case timeline.

    Expected JSON payload:
        {
            "case_index": <int>,
            "speaker": <str>,
            "prompt": <optional str>
        }

    Behavior:
        - Validate request
        - Request event generation from Gemini
        - Append the new event to the timeline
        - Return the updated case
    """
    data = request.get_json()
    if not data:
        return jsonify(response="error", message="Missing request data"), 400
    if "case_index" not in data or "speaker" not in data:
        return jsonify(response="error", message="Missing case_index or speaker"), 400

    case_index = data["case_index"]
    extra_prompt = data.get("prompt", "")

    if case_index < 0 or case_index >= len(loadedCases):
        return jsonify(response="error", message="Invalid case_index"), 400

    court: Court = loadedCases[case_index]

    # Generate event using AI
    try:
        event_data = generate_event(court, extra_prompt)
        event_type = event_data["type"]
        content = event_data["content"]
        speaker = event_data["speaker"]
    except Exception as e:
        return jsonify(response="error", message=f"Failed to generate AI event: {str(e)}"), 500

    # Append event to timeline
    court.addEvent(speaker=speaker, event_type=event_type, content=content)

    return jsonify(response="success", case=court.to_dict()), 200


@app.route("/select_case", methods=["POST"])
async def caseSelect():
    """
    Return metadata for an existing case.

    Expected JSON payload:
        {
            "activeCase": <int>
        }

    Returns:
        Serialized case object.
    """
    data = request.get_json()
    if not data:
        return jsonify(response="error", message="Missing request data"), 400

    activeCase = int(data["activeCase"])
    court = loadedCases[activeCase]

    return jsonify(response="success", case=court.to_dict()), 200


@app.route("/object", methods=["POST"])
async def objection():
    """
    Register an objection and generate a ruling from the judge via AI.

    Expected JSON payload:
        {
            "case_index": <int>,
            "speaker": <str>,
            "objection_type": <str>,
            "content": <str>
        }

    Behavior:
        - Validate the objection's speaker
        - Add the objection to the timeline
        - Request the judge’s ruling from Gemini
        - Append ruling
        - Return updated case + ruling
    """
    data = request.get_json()
    if not data:
        return jsonify(response="error", message="Missing request data"), 400

    # Validate required fields
    for key in ["case_index", "speaker", "objection_type", "content"]:
        if key not in data:
            return jsonify(response="error", message=f"Missing field: {key}"), 400

    activeCase = data["case_index"]
    speaker = data["speaker"]
    objection_type = data["objection_type"]
    content = data["content"]

    court = loadedCases[activeCase]

    # Ensure speaker is a valid participant
    if speaker not in court.witnesses and speaker not in [
        court.judge, court.prosecution_name, court.defense_name
    ]:
        return jsonify(response="error", message="Speaker not valid for this court case"), 400

    # Append objection event
    objection_event = TimelineEvent(
        speaker=speaker,
        event_type=TimelineEventType.OBJECTION,
        content=f"[{objection_type}] {content}"
    )
    court.timeline.append(objection_event)

    # Generate judge's ruling
    try:
        ruling_data = generate_ruling(court, objection_type)
        ruling_event = TimelineEvent(
            speaker=court.judge,
            event_type=TimelineEventType.RULING,
            content=ruling_data["content"]
        )
        court.timeline.append(ruling_event)
    except Exception as e:
        return jsonify(response="error", message=f"Failed to generate ruling: {str(e)}"), 500

    ruling = ruling_event.to_dict()
    ruling["decision"] = ruling_data["decision"]

    return jsonify(
        response="success",
        case=court.to_dict(),
        ruling=ruling
    ), 200


@app.route("/ping")
async def ping():
    """
    Simple liveness check for monitoring and testing.
    """
    return jsonify(response="success", message="pong"), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6767, debug=True, threaded=False)
