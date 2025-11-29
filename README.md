# Feedback-Chat-Agent-for-Experimental-Designs-in-Human-Subject-Research
KI-basiertes Tool, das Forschende dabei unterstützt, ihr ökonomisches experimentelles Design systematisch zu reflektieren. Grundlage des Tools ist ein Chat-Agent, der Nutzer:innen gezielt Feedback zu einem bereitgestellten experimentellen Design gibt und dabei auf eine RAG-gestützte Wissensbasis zurückgreift.


Paar Steps zum Starten:

Docker App starten
starte docker container: docker run -d -p 3000:8080 -v open-webui:/app/backend/data --name open-webui ghcr.io/open-webui/open-webui:main
auf localhost:3000 gehen
bei open web ui anmelden
mit visual studio code das projekt öffen
pull von github, um auf dem neusten stand zu sein
in dev container öffnen
main.py starten
ggf localhost:5000 öffnen
jetzt sollte die anwendung auf localhost:3000 = open web ui laufen



Aktuelles Problem

bei openwebui_proxy.py

insbesondere bei

@openwebui_bp.route("/chat/completions", methods=["POST"])
def chat_completions_nonstream():
    ...

open web ui schickt die Anfrage ans Backend
Backend schickt die Anfrage an AI
Backend schickt die Antwort an Open Web UI
Open Web UI bekommt die Antwort (json file - sieh webseite debuggen - request completions - antwort)
aber die Antwort wird nicht in der UI angezeigt

das ganze läuft erstmal ohne streaming, da die methode mit streaming noch viel mehr ganz andere Probleme gemacht hat...

die openwebui_proxy datei ist aktuell ein ziemliches schlachtfeld aus tagelangen rumprobieren... sorry