# als BackUp gedacht ...

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
# if you register blueprint on app, call: CORS(app, origins=["http://localhost:3000"])
# or enable for blueprint:
# CORS(openwebui_bp, origins=["http://localhost:3000"])

# Minimal in-memory chat store (for demo)
# chat_store[chat_id] = {
#   "id": chat_id,
#   "title": "...",
#   "models": [...],
#   "messages": [...],
#   "history": {"current_id": <assistant_id>, "messages": {<msg_id>: msg_obj, ...}}
# }
chat_store = {}

def now_ms():
    return int(time.time() * 1000)

def make_assistant_placeholder(user_msg_id: str, model_name: str = "My-Chat-AI"):
    aid = str(uuid.uuid4())
    assistant = {
        "id": aid,
        "role": "assistant",
        "content": "",           # empty placeholder — CRITICAL!
        "parentId": user_msg_id,
        "modelName": model_name,
        "modelIdx": 0,
        "timestamp": now_ms()
    }
    return assistant

### 1) Create chat (Step 1 & optionally Step 2 combined)
@openwebui_bp.route("/v1/chats/new", methods=["POST"])
def new_chat():
    payload = request.json or {}
    chat = payload.get("chat")
    # if frontend already supplied a chat object, we accept it; otherwise make minimal
    if not chat:
        chat_id = str(uuid.uuid4())
        user_msg_id = str(uuid.uuid4())
        user_content = payload.get("user_message", "Hello")
        # create minimal chat structure
        chat = {
            "id": chat_id,
            "title": "",
            "models": payload.get("models", ["My-Chat-AI"]),
            "messages": [
                {
                    "id": user_msg_id,
                    "role": "user",
                    "content": user_content,
                    "timestamp": now_ms(),
                    "models": payload.get("models", ["My-Chat-AI"])
                }
            ],
            "history": {
                "current_id": user_msg_id,
                "messages": {
                    user_msg_id: {
                        "id": user_msg_id,
                        "role": "user",
                        "content": user_content,
                        "timestamp": now_ms(),
                        "models": payload.get("models", ["My-Chat-AI"])
                    }
                }
            }
        }
    else:
        # ensure ids exist
        chat_id = chat.get("id", str(uuid.uuid4()))
        chat["id"] = chat_id

    # Create assistant placeholder and enrich chat (Step 2)
    user_msg_id = chat["messages"][-1]["id"]
    assistant = make_assistant_placeholder(user_msg_id, model_name=chat.get("models", ["My-Chat-AI"])[0])
    # append to messages and history
    chat["messages"].append(assistant)
    if "history" not in chat:
        chat["history"] = {"current_id": assistant["id"], "messages": {}}
    chat["history"]["current_id"] = assistant["id"]
    chat["history"].setdefault("messages", {})
    chat["history"]["messages"][assistant["id"]] = assistant
    # store
    chat_store[chat_id] = chat

    return jsonify({"chat": chat})

### 2) Update chat (Step 3) - optional endpoint frontend may call
@openwebui_bp.route("/v1/chats/<chat_id>", methods=["POST"])
def update_chat(chat_id):
    body = request.json or {}
    chat = body.get("chat")
    if not chat:
        return jsonify({"error":"missing chat payload"}), 400
    chat_store[chat_id] = chat
    return jsonify({"chat": chat})

### 3) Streaming completion trigger (Step 4..6) — SSE expected by Open WebUI
# This endpoint implements stream: true behavior. Open WebUI will call it with:
# {
#   "chat_id":"<chatId>",
#   "id":"<assistant_msg_id>",
#   "messages":[...],
#   "model":"My-Chat-AI",
#   "stream": true
# }
@openwebui_bp.route("/chat/completions", methods=["POST"])
def chat_completions_nonstream():
    req = request.json or {}

    logging.error(f"Request: req={req}")
    # try to obtain chat_id from common places
    chat_id = req.get("chat_id") or req.get("chat", {}).get("id") or req.get("meta", {}).get("chat_id")
    logging.error(f"chat_completions_nonstream: chat_id={chat_id}")
    if not chat_id:
        # create a chat if none exists (UI sometimes expects this)
        chat_id = str(uuid.uuid4())
        chat_store.setdefault(chat_id, {"id": chat_id, "messages": [], "history": {"messages": {}, "current_id": None}, "models": ["My-Chat-AI"]})

    chat = chat_store.get(chat_id)
    logging.error(f"chat_id={chat_id}, chat={chat}")
    messages = req.get("messages") or []
    user_input = messages[-1]["content"] if messages else ""

    # topic check
    if utils.DetectDiffTopic(user_input):
        out_text = "Bitte nur zum richtigen Thema fragen."
        content_blocks = [{"type": "text", "text": out_text}]
    else:
        lang = utils.DetectLanguage(user_input)
        model = utils.ChooseModel(lang)
        prompt = utils.CraftPrompt(user_input, lang)

        # synchronous (non-streaming) call - simpler for debugging
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )

        # extract text safely (the API may return list or string)
        msg_content = completion.choices[0].message.content
        # if the client returns a list of blocks, join their text; otherwise use string
        if isinstance(msg_content, list):
            # e.g. [{"type":"text","text":"..."}]
            out_text = "".join([block.get("text", "") if isinstance(block, dict) else str(block) for block in msg_content])
        else:
            out_text = str(msg_content)

        
        # nicht mehr genutzt... - content_blocks = [{"type": "text", "text": out_text}]

    # update chat store: find or add assistant placeholder
    assistant_msg_id = req.get("id")
    logging.error(f"assistant_msg_id={assistant_msg_id}")
    if not assistant_msg_id:
        # try to find last assistant placeholder
        assistant_msg = next((m for m in chat["messages"] if m["role"] == "assistant" and (not m.get("content"))), None)
        if assistant_msg:
            assistant_msg_id = assistant_msg["id"]
        else:
            logging.error("no assisteent message id...")
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

    # set assistant content to array-of-blocks (Open WebUI expects this)
    assistant_obj = chat["history"]["messages"].get(assistant_msg_id)
    logging.error(f"assistant_obj before update={assistant_obj}")

    if assistant_obj is None:
        assistant_obj = {
            "id": assistant_msg_id,
            "role": "assistant",
            "content": [],
            "parentId": None,
            "modelName": chat.get("models", ["My-Chat-AI"])[0],
            "modelIdx": 0,
            "timestamp": now_ms()
        }
        chat["messages"].append(assistant_obj)
        chat["history"]["messages"][assistant_msg_id] = assistant_obj

    # assistant_obj["content"] = [{"type": "text", "text": out_text}] # vorher: content_blocks
    assistant_obj["content"] = out_text
    assistant_obj["timestamp"] = now_ms()
    # NICHT erneut append – nur updaten!
    chat["history"]["messages"][assistant_msg_id] = assistant_obj
  
    # Sync back into messages[]
    for i, msg in enumerate(chat["messages"]):
        if msg["id"] == assistant_msg_id:
            chat["messages"][i] = assistant_obj
            break
    # chat["messages"].append(assistant_obj)
    # chat["history"]["messages"][assistant_msg_id] = assistant_obj
    # chat["history"]["messages"][assistant_msg_id] = assistant_obj
    # chat["history"]["current_id"] = assistant_msg_id
    logging.error(f"assistant_obj after update={assistant_obj}")
    # Build and return the Open WebUI-compatible "final" completion JSON
    payload = {
        "id": assistant_msg_id, # str(uuid.uuid4()), # evtl MUSS HIER RICHITGE ID ?????????????????
        "object": "chat.completion",
        "model": chat.get("models", ["My-Chat-AI"])[0],
        "chat" : chat,
        "stream": False,
        "choices": [
            {
                "index": 0,
                #"message": assistant_obj,
                "message": {
                    "id": assistant_msg_id,
                    "role": "assistant",
                    "content": out_text # vorher: content_blocks
                },
                "finish_reason": "stop"
            }
        ]
    }
    # return JSON (not Python objects)
    return jsonify(payload)

def chat_completions_stream():
    req = request.json or {}

    # ---------- FIX: Hole chat_id sicher ----------
    chat_id = (
        req.get("chat_id")
        or req.get("chat", {}).get("id")
        or req.get("meta", {}).get("chat_id")    # OpenWebUI schickt es oft hier!
    )

    # ---------- FIX: Wenn keins da → selbst erzeugen ----------
    if not chat_id:
        chat_id = str(uuid.uuid4())

    # ---------- FIX: Stelle sicher, dass Chat im Speicher existiert ----------
    if chat_id not in chat_store:
        chat_store[chat_id] = {
            "id": chat_id,
            "models": [req.get("model") or "My-Chat-AI"],
            "messages": [],
            "history": {"messages": {}, "current_id": None},
        }

    chat = chat_store[chat_id]

    # assistant message ID
    assistant_msg_id = req.get("id")

    # ---------- FIX: Wenn UI keins liefert → selbst erzeugen ----------
    if not assistant_msg_id:
        new_id = str(uuid.uuid4())
        placeholder = {
            "id": new_id,
            "role": "assistant",
            "content": "",
            "parentId": None,
            "modelName": chat["models"][0],
            "modelIdx": 0,
            "timestamp": now_ms()
        }
        chat["messages"].append(placeholder)
        chat["history"]["messages"][new_id] = placeholder
        chat["history"]["current_id"] = new_id
        assistant_msg_id = new_id

    # User prompt extrahieren
    messages = req.get("messages") or []
    user_input = messages[-1]["content"] if messages else ""

    # Prompt bauen
    lanugage = utils.DetectLanguage(user_input)
    prompt = utils.CraftPrompt(user_input, lanugage)
    # model = req.get("model") or chat["models"][0]
    model = utils.ChooseModel(lanugage)

    # STREAMING: Server Sent Events
    def event_stream():
        chunks = []

        try:
            # OpenAI Streaming API
            stream = client.chat.completions.create(
                stream=True,
                model=model,
                messages=[{"role": "user", "content": "Hello"}] # TODO: richtiger content
            )
            logging.error(f"prompt={prompt}")
            
            # logging.error(f"Stream={stream}")
            for event in stream:
                if getattr(event, "type", None) == "response.output_text.delta":
                    delta = str(event.delta)
                    chunks.append(delta)

                    # Open Web UI-kompatibles SSE-Format
                    sse_payload = {
                        "id": assistant_msg_id,
                        "object": "chat.completion.chunk",  # <- wichtig
                        "model": "My-Chat-AI", # richtiges Modell !?
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": delta}
                            }
                        ]
                    }
                    logging.error(f"payload={sse_payload}")
                    yield "data: " + json.dumps(sse_payload) + "\n\n"


            """ sse_payload = {
                "id": assistant_msg_id,
                "object": "chat.completion.chunk",  # <- wichtig
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": [{"type": "text", "text": "Hello Bjarne"}]
                    }
                ]
            } """
            # yield json.dumps(sse_payload)

            # Finaltext zusammenführen
            #final_txt = "".join(chunks)
            final_txt = "Hello world"
            logging.error(f"final_txt={final_txt}")

            # Update des Chat-Store
            assistant_msg = chat["history"]["messages"].get(assistant_msg_id)
            if assistant_msg:
                assistant_msg["content"] = [{'type':'text','text': final_txt}]
                chat["history"]["messages"][assistant_msg_id] = assistant_msg

            # Abschließender SSE-Chuck mit finish_reason
            final_chunk = {
                "id": assistant_msg_id,
                "object": "chat.completion.chunk",
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"type": "text", "text": "__END__"},
                        "finish_reason": "stop"
                    }
                ]
            }

            #ret = [sse_payload, final_chunk]
            #yield json.dumps(ret)
            yield "data: " + json.dumps(final_chunk) + "\n\n"
            
        except Exception as e:
            
            logging.error(f"My Error during streaming completion: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            

    logging.error(f"Starting streaming completion for chat_id={chat_id}")
    # return Response(stream_with_context(event_stream()), mimetype="text/event-stream")
    
    resp = Response(stream_with_context(event_stream()), mimetype="text/event-stream")
    # recommended headers to avoid proxies buffering / transformations
    resp.headers["Cache-Control"] = "no-cache, no-transform"
    resp.headers["X-Accel-Buffering"] = "no"  # for nginx
    return resp
    #return event_stream() # das ist kein streaming mehr!



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