from flask import Flask, render_template, request
from openai import OpenAI
from dotenv import load_dotenv
import os

app = Flask(__name__)

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

# Hauptsächliche Funktion
@app.route('/', methods=["GET", "POST"])
def index():
    output = ""

    if request.method == "POST":
        user_input = request.form.get("user_input")

        # Anfrage an die AI
        chat_completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": user_input}]
        )

        output = chat_completion.choices[0].message["content"]

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