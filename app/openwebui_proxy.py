# openwebui_proxy.py
from flask import Blueprint, request, jsonify, Response, stream_with_context, current_app
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import os, json, uuid, time
import utils
import logging

load_dotenv()

API_KEY = os.getenv("API_KEY")
BASE_URL = "https://chat-ai.academiccloud.de/v1"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

openwebui_bp = Blueprint("openwebui_bp", __name__)

chat_store = {}

def now_ms():
    return int(time.time() * 1000)

def make_assistant_placeholder(user_msg_id: str, model_name: str = "My-Chat-AI"):
    aid = str(uuid.uuid4())
    assistant = {
        "id": aid,
        "role": "assistant",
        "content": "",
        "parentId": user_msg_id,
        "modelName": model_name,
        "modelIdx": 0,
        "timestamp": now_ms()
    }
    return assistant


@openwebui_bp.route("/chat/completions", methods=["POST"])
def chat_completions_nonstream():
    req = request.json or {}

    chat_id = req.get("chat_id") or req.get("chat", {}).get("id") or req.get("meta", {}).get("chat_id")
    if not chat_id:
        chat_id = str(uuid.uuid4())
        chat_store.setdefault(chat_id, {"id": chat_id, "messages": [], "history": {"messages": {}, "current_id": None}, "models": ["My-Chat-AI"]})

    chat = chat_store.get(chat_id)

    messages = req.get("messages") or []
    user_input = messages[-1]["content"] if messages else ""

    # erstmal auf falsches Theme prüfen
    if utils.DetectDiffTopic(user_input):
        out_text = "Bitte nur zum richtigen Thema fragen."
    else:

        # Sprache erkennen - falls nicht de/en Fehler
        lang = utils.DetectLanguage(user_input)
        if lang == -1: return return_error_to_ui("Bitte in Deutsch oder Englisch schreiben.")

        # bestes Modell nach Sprache wählen
        model = utils.ChooseModel(lang)

        # Prompt nach Sprache bauen
        prompt = utils.CraftPrompt(user_input, lang)

        # Anfrage an die AI
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )

        msg_content = completion.choices[0].message.content
        
        if isinstance(msg_content, list):
            out_text = "".join([block.get("text", "") if isinstance(block, dict) else str(block) for block in msg_content])
        else:
            out_text = str(msg_content)

    
    assistant_msg_id = req.get("id")

    if not assistant_msg_id:
        assistant_msg = next((m for m in chat["messages"] if m["role"] == "assistant" and (not m.get("content"))), None)
        if assistant_msg:
            assistant_msg_id = assistant_msg["id"]
        else:
            assistant_msg_id = str(uuid.uuid4())
            assistant_msg = {
                "id": assistant_msg_id,
                "role": "assistant",
                "content": "",
                "parentId": chat["messages"][-1]["id"] if chat["messages"] else None,
                "modelName": chat.get("models", ["My-Chat-AI"])[0],
                "modelIdx": 0,
                "timestamp": now_ms()
            }
            chat["messages"].append(assistant_msg)
            chat["history"]["messages"][assistant_msg_id] = assistant_msg
            chat["history"]["current_id"] = assistant_msg_id

    
    assistant_obj = chat["history"]["messages"].get(assistant_msg_id)
    
    assistant_obj["content"] = out_text
    assistant_obj["timestamp"] = now_ms()
    
    chat["history"]["messages"][assistant_msg_id] = assistant_obj
  
    for i, msg in enumerate(chat["messages"]):
        if msg["id"] == assistant_msg_id:
            chat["messages"][i] = assistant_obj
            break
    
    payload = {
        "id": assistant_msg_id,
        "object": "chat.completion",
        "model": chat.get("models", ["My-Chat-AI"])[0],
        "chat" : chat,
        "stream": False,
        "choices": [
            {
                "index": 0,
                "message": {
                    "id": assistant_msg_id,
                    "role": "assistant",
                    "content": out_text
                },
                "finish_reason": "stop"
            }
        ]
    }
    return jsonify(payload)


@openwebui_bp.route("/models", methods=["GET", "OPTIONS"])
def models():
    if request.method == "OPTIONS":
        return ('', 204)

    return jsonify({
        "data": [{
            "id": "My-Chat-AI",
            "object": "model",
            "name": "My-Chat-AI",
            "type": "chat"
        }]
    })

def return_error_to_ui(message: str):
    return jsonify({
        "id": str(uuid.uuid4()),
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": message
                },
                "finish_reason": "stop"
            }
        ]
    })