# Feedback-Chat-Agent-for-Experimental-Designs-in-Human-Subject-Research
KI-basiertes Tool, das Forschende dabei unterstützt, ihr ökonomisches experimentelles Design systematisch zu reflektieren. Grundlage des Tools ist ein Chat-Agent, der Nutzer:innen gezielt Feedback zu einem bereitgestellten experimentellen Design gibt und dabei auf eine RAG-gestützte Wissensbasis zurückgreift.


Paar Steps zum Starten:

Docker App starten
starte docker container: docker run -d -p 3000:8080 -v open-webui:/app/backend/data --name open-webui ghcr.io/open-webui/open-webui:main
auf localhost:3000 gehen
bei open web ui anmelden
(evtl unter direktverbindung "http://localhost:5000" hinzufügen)
mit visual studio code das projekt öffen
pull von github, um auf dem neusten stand zu sein
in dev container öffnen
main.py starten
ggf localhost:5000 öffnen
jetzt sollte die anwendung auf localhost:3000 = open web ui laufen
SEHR WICHTIG !!!! Bei Open Web UI oben rechts unter Steuerung "Chat-Antwort streamen" auf "Aus" stellen, sonst wird nichts angezeigt! Muss man jedes Mal aufs neue machen! (können wir langfristig evtl auch noch besser lösen)


Aktuelles Thema:
läuft soweit und gibt die Antwort auf
nicht mit Streaming - kann man noch implementieren (unter openwebui_proxy copy.py ist eine Methode, von der aus man weiter probieren kann)


evtl fehlt noch "pip install flask-cors" und "pip install langdetect" in requirements