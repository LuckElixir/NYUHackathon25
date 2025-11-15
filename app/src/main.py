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
    return jsonify(response="success", caseNum=activeCase, case=court.to_dict()), 200



@app.route("/ai-event", methods=["POST"])
async def addEvent():
    data = request.get_json()
    if not data:
        return jsonify(response="error", message="Missing request data"), 400

    if "case_index" not in data or "speaker" not in data:
        return jsonify(response="error", message="Missing case_index or speaker"), 400

    case_index = data["case_index"]
    extra_prompt = data.get("prompt", "")

    if case_index < 0 or case_index >= len(loadedCases):
        return jsonify(response="error", message="Invalid case_index"), 400

    court : Court = loadedCases[case_index]


    # Call Gemini to generate the event
    try:
        event_data = generate_event(court, extra_prompt)
        event_type = event_data["type"]
        content = event_data["content"]
        speaker = event_data["speaker"]
    except Exception as e:
        return jsonify(response="error", message=f"Failed to generate AI event: {str(e)}"), 500

    # Append new event
    court.addEvent(speaker=speaker, event_type=event_type, content=content)

    # Return updated court case
    return jsonify(response="success", case=court.to_dict()), 200

@app.route("/select_case", methods=["POST"])
async def caseSelect():
    data = request.get_json()
    if not data:
        return jsonify(response="error", message="Missing request data"), 400
    activeCase = int(data["activeCase"])
    court = loadedCases[activeCase]
    return jsonify(response="success", case=court.to_dict()), 200

@app.route("/object", methods=["POST"])
async def objection():
    data = request.get_json()
    if not data:
        return jsonify(response="error", message="Missing request data"), 400

    for key in ["case_index", "speaker", "objection_type", "content"]:
        if key not in data:
            return jsonify(response="error", message=f"Missing field: {key}"), 400

    activeCase = data["case_index"]
    speaker = data["speaker"]
    objection_type = data["objection_type"]
    content = data["content"]


    court = loadedCases[activeCase]

    # Validate speaker
    if speaker not in court.witnesses and speaker not in [
        court.judge, court.prosecution_name, court.defense_name
    ]:
        return jsonify(response="error", message="Speaker not valid for this court case"), 400

    objection_event = TimelineEvent(
        speaker=speaker,
        event_type=TimelineEventType.OBJECTION,
        content=f"[{objection_type}] {content}"
    )
    court.timeline.append(objection_event)

    # ---------------------------------------------
    # Generate the ruling using gemini.generate_ruling
    # ---------------------------------------------
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

    return jsonify(
        response="success",
        case=court.to_dict(),
        ruling=ruling_event.to_dict()
    ), 200
    
