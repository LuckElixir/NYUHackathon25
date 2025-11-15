from sqlite3 import IntegrityError
from dotenv import load_dotenv
from flask import Flask, jsonify
from flask import render_template, url_for, request, redirect
from flask import session
from markupsafe import escape
from savestates import *
from gemini import *
import os

load_dotenv(".env")
app: Flask = Flask(__name__, static_folder="../front/static/", static_url_path="/static", 
                   template_folder="../front/pages/")
app.secret_key = "prettySecret"

@app.route("/update", methods=["POST"])
async def updateDB():
    return "test"


@app.route("/create_case", methods=["GET"])
async def createCase():
    # Generate case information via Gemini
    case_info = generate_case()

    # Build Court object
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


    # Add witnesses
    for w in case_info.get("witnesses", []):
        court.witnesses[w] = Witness(w)

    # Return savestate
    return jsonify(response="success", case=court.to_dict()), 200



@app.route("/ai-event", methods=["POST"])
async def addEvent():
    data = request.get_json()
    if not data:
        return jsonify(response="error", message="Missing request data"), 400

    if "case_index" not in data or "speaker" not in data:
        return jsonify(response="error", message="Missing case_index or speaker"), 400

    case_index = data["case_index"]
    speaker = data["speaker"]
    extra_prompt = data.get("prompt", "")

    if case_index < 0 or case_index >= len(loadedCases):
        return jsonify(response="error", message="Invalid case_index"), 400

    court = loadedCases[case_index]

    # Validate speaker
    if speaker not in court.witnesses and speaker not in [
        court.judge, court.prosecution_name, court.defense_name
    ]:
        return jsonify(response="error", message="Speaker not valid for this court case"), 400

    # Call Gemini to generate the event
    try:
        event_data = generate_event(court, speaker, extra_prompt)
        event_type = TimelineEventType[event_data["type"].upper()]
        content = event_data["content"]
    except Exception as e:
        return jsonify(response="error", message=f"Failed to generate AI event: {str(e)}"), 500

    # Append new event
    new_event = TimelineEvent(speaker=speaker, event_type=event_type, content=content)
    court.timeline.append(new_event)

    # Return updated court case
    return jsonify(response="success", case=court.to_dict()), 200
