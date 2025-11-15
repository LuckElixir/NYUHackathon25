from sqlite3 import IntegrityError
from dotenv import load_dotenv
from flask import Flask, jsonify
from flask import render_template, url_for, request, redirect
from flask import session
from markupsafe import escape
import os

load_dotenv(".env")
app: Flask = Flask(__name__, static_folder="../front/static/", static_url_path="/static", 
                   template_folder="../front/pages/")
app.secret_key = "prettySecret"

@app.route("/update", methods=["POST"])
async def updateDB():
    return "test"


