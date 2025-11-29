from flask import Flask, render_template, request
from openai import OpenAI
from dotenv import load_dotenv
import os
import utils
from openwebui_proxy import openwebui_bp
from flask_cors import CORS

app = Flask(__name__)

CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": "*"
    }
})

app.register_blueprint(openwebui_bp)

@app.after_request
def after_request(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response

# CORS(openwebui_bp, origins=["http://localhost:3000"])
# CORS(app, origins=["http://localhost:3000"]) # Cross iwas Anfrage erlauben, damit OpenWebUI Anfragen kann


# .env api_key laden
load_dotenv()

# AI Client Setup
API_KEY = os.getenv("API_KEY")
BASE_URL = "https://chat-ai.academiccloud.de/v1"
MODEL = "meta-llama-3.1-8b-instruct"

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL
)

@app.route("/<path:path>", methods=["OPTIONS"])
def options_handler(path):
    return '', 200

# Hauptsächliche Funktion
@app.route('/', methods=["GET", "POST"])
def index():
    output = ""

    if request.method == "POST":
        
        # iwie Input auch als Datei ...
        user_input = request.form.get("user_input")

        # Falsches Thema abfangen
        if utils.DetectDiffTopic(user_input):
            output = "Bitte nur zum richtigen Thema fragen."
            return render_template("index.html", output=output)

        # Sprache erkennen
        lang = utils.DetectLanguage(user_input)

        # Modell nach Sprache wählen
        MODEL = utils.ChooseModel(lang)

        # Prompt erstellen
        prompt = utils.CraftPrompt(user_input, lang)

        # Anfrage an die AI
        chat_completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}]
        )

        output = chat_completion.choices[0].message.content

    return render_template("index.html", output=output)

# Input = Output
@app.route('/basic', methods=["GET", "POST"])
def basic():
    output = ""
    if request.method == "POST":
        user_input = request.form.get("user_input")
        output = user_input  # einfaches Echo
    return render_template("index.html", output=output)

@app.route('/home')
def home():
    return "Hello from our Chat Tool!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)